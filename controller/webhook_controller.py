import os
import logging
import json
import requests
from flask import Blueprint, request, jsonify
from enum import Enum
from typing import Dict, Any
from transformers import pipeline
from huggingface_hub import model_info
import time

# Create blueprint
webhook_blueprint = Blueprint('webhook', __name__)

# Define document processing states
class ProcessingState(Enum):
    WAITING_FOR_ID = "waiting_for_id"
    WAITING_FOR_LICENSE = "waiting_for_license"
    WAITING_FOR_LOGCARD = "waiting_for_logcard"
    COMPLETED = "completed"

# Store user states (in real application, use a database)
user_states = {}

# Helper function for model validation
def validate_model_availability(model_name: str, token: str) -> bool:
    try:
        # Check model availability on Hugging Face
        model_info(model_name, token=token)
        return True
    except Exception as e:
        logging.error(f"Model validation failed: {e}")
        return False

class DocumentProcessor:
    def __init__(self):
        self.model = None
        self.monday_api_token = os.getenv('MONDAY_API_TOKEN')
        self.monday_api_url = os.getenv('MONDAY_API_URL')
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN')  
        self._initialize_model_with_retry()

    def _initialize_model_with_retry(self, max_retries: int = 3, retry_delay: int = 5):
        for attempt in range(max_retries):
            try:
                if not validate_model_availability("smolvlm/smolvlm-base", self.hf_token):
                    raise RuntimeError("The specified model is unavailable or inaccessible.")

                # Initialize the Hugging Face pipeline
                self.model = pipeline("image-to-text", model="smolvlm/smolvlm-base", use_auth_token=self.hf_token)
                logging.info("Model initialized successfully.")
                return
            except Exception as e:
                logging.error(f"Model initialization attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError("Failed to initialize Hugging Face model after multiple attempts.")

    def extract_data_from_image(self, image_url: str, document_type: str) -> Dict:
        """Extract data from image using the Hugging Face model."""
        try:
            response = requests.get(image_url)
            response.raise_for_status()  # Ensure the request was successful

            if not self.model:
                raise RuntimeError("Model is not initialized. Unable to process the image.")

            result = self.model(response.content)

            if document_type == "identity_card":
                return self._parse_id_card(result)
            elif document_type == "drivers_license":
                return self._parse_drivers_license(result)
            elif document_type == "log_card":
                return self._parse_log_card(result)
            return {}
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Image download failed: {req_err}")
            return {}
        except Exception as e:
            logging.error(f"Error during data extraction: {e}")
            return {}

    def _parse_id_card(self, result: str) -> Dict:
        return {"type": "id_card", "extracted_data": result}

    def _parse_drivers_license(self, result: str) -> Dict:
        return {"type": "drivers_license", "extracted_data": result}

    def _parse_log_card(self, result: str) -> Dict:
        return {"type": "log_card", "extracted_data": result}

    def save_to_monday(self, data: Dict) -> bool:
        """Save extracted data to Monday.com."""
        try:
            query = """
            mutation ($myItemName: String!, $columnValues: JSON!) {
                create_item (
                    board_id: <your_board_id>,
                    item_name: $myItemName,
                    column_values: $columnValues
                ) {
                    id
                }
            }
            """
            variables = {
                "myItemName": f"Document Processing - {data['type']}",
                "columnValues": json.dumps(data['extracted_data'])
            }
            headers = {
                'Authorization': self.monday_api_token,
                'Content-Type': 'application/json'
            }
            response = requests.post(self.monday_api_url, json={'query': query, 'variables': variables}, headers=headers)

            if response.status_code == 200:
                logging.info("Data saved to Monday.com successfully.")
                return True
            logging.error(f"Failed to save data to Monday.com: {response.text}")
            return False
        except Exception as e:
            logging.error(f"Error saving to Monday.com: {e}")
            return False

def get_next_state(current_state: ProcessingState) -> ProcessingState:
    """Get the next state in the processing flow."""
    state_flow = {
        ProcessingState.WAITING_FOR_ID: ProcessingState.WAITING_FOR_LICENSE,
        ProcessingState.WAITING_FOR_LICENSE: ProcessingState.WAITING_FOR_LOGCARD,
        ProcessingState.WAITING_FOR_LOGCARD: ProcessingState.COMPLETED
    }
    return state_flow.get(current_state, ProcessingState.COMPLETED)

def process_message(message_data: Dict[Any, Any]) -> Dict[str, str]:
    """Process incoming message data."""
    try:
        user_id = message_data.get('from')

        if not user_id:
            return {"status": "error", "message": "User ID not found"}

        if user_id not in user_states:
            user_states[user_id] = ProcessingState.WAITING_FOR_ID
            return {"status": "success", "message": "Please upload your ID card photo"}

        if not message_data.get('media_url'):
            return {"status": "success", "message": "Please upload a photo of the required document"}

        current_state = user_states[user_id]

        doc_processor = DocumentProcessor()
        if current_state == ProcessingState.WAITING_FOR_ID:
            data = doc_processor.extract_data_from_image(message_data['media_url'], "identity_card")
        elif current_state == ProcessingState.WAITING_FOR_LICENSE:
            data = doc_processor.extract_data_from_image(message_data['media_url'], "drivers_license")
        elif current_state == ProcessingState.WAITING_FOR_LOGCARD:
            data = doc_processor.extract_data_from_image(message_data['media_url'], "log_card")
        else:
            return {"status": "success", "message": "All documents have been processed"}

        if data:
            doc_processor.save_to_monday(data)

        next_state = get_next_state(current_state)
        user_states[user_id] = next_state

        if next_state == ProcessingState.COMPLETED:
            return {"status": "success", "message": "All documents have been processed successfully!"}
        elif next_state == ProcessingState.WAITING_FOR_LICENSE:
            return {"status": "success", "message": "ID card processed. Please upload your driver's license photo"}
        elif next_state == ProcessingState.WAITING_FOR_LOGCARD:
            return {"status": "success", "message": "Driver's license processed. Please upload your log card photo"}
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        return {"status": "error", "message": f"Failed to process message: {e}"}

@webhook_blueprint.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming webhook events."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        logging.info(f"Received webhook event: {json.dumps(data, indent=2)}")

        result = process_message(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        return jsonify({"status": "error", "message": f"Webhook processing failed: {e}"}), 500

@webhook_blueprint.route('/webhook', methods=['GET'])
def verify_webhook():
    """Endpoint for webhook verification."""
    return jsonify({"status": "success", "message": "Webhook endpoint is active"}), 200
