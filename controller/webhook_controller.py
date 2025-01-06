from flask import Blueprint, request, jsonify
import logging
import json
from typing import Dict, Any
import os
from enum import Enum
import requests
from transformers import pipeline

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

class DocumentProcessor:
    def __init__(self):
        # Initialize smolVLM model
        self.model = pipeline("image-to-text", model="smolvlm/smolvlm-base")
        self.monday_api_token = os.getenv('MONDAY_API_TOKEN')
        self.monday_api_url = os.getenv('MONDAY_API_URL')

    def extract_data_from_image(self, image_url: str, document_type: str) -> Dict:
        """Extract data from image using smolVLM"""
        try:
            # Download image from URL
            response = requests.get(image_url)
            # Process with smolVLM
            result = self.model(response.content)
            
            # Parse results based on document type
            if document_type == "identity_card":
                return self._parse_id_card(result)
            elif document_type == "drivers_license":
                return self._parse_drivers_license(result)
            elif document_type == "log_card":
                return self._parse_log_card(result)
                
            return {}
            
        except Exception as e:
            logging.error(f"Error extracting data: {str(e)}")
            return {}

    def _parse_id_card(self, result: str) -> Dict:
        # Add specific parsing logic for ID card
        return {"type": "id_card", "extracted_data": result}

    def _parse_drivers_license(self, result: str) -> Dict:
        # Add specific parsing logic for driver's license
        return {"type": "drivers_license", "extracted_data": result}

    def _parse_log_card(self, result: str) -> Dict:
        # Add specific parsing logic for log card
        return {"type": "log_card", "extracted_data": result}

    def save_to_monday(self, data: Dict) -> bool:
        """Save extracted data to Monday.com"""
        try:
            # Define the Monday.com mutation query
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
            
            # Prepare the data for Monday.com
            variables = {
                "myItemName": f"Document Processing - {data['type']}",
                "columnValues": json.dumps(data['extracted_data'])
            }
            
            # Make the API call to Monday.com
            headers = {
                'Authorization': self.monday_api_token,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.monday_api_url,
                json={'query': query, 'variables': variables},
                headers=headers
            )
            
            if response.status_code == 200:
                return True
            return False
            
        except Exception as e:
            logging.error(f"Error saving to Monday.com: {str(e)}")
            return False

# Initialize document processor
doc_processor = DocumentProcessor()

def get_next_state(current_state: ProcessingState) -> ProcessingState:
    """Get the next state in the processing flow"""
    state_flow = {
        ProcessingState.WAITING_FOR_ID: ProcessingState.WAITING_FOR_LICENSE,
        ProcessingState.WAITING_FOR_LICENSE: ProcessingState.WAITING_FOR_LOGCARD,
        ProcessingState.WAITING_FOR_LOGCARD: ProcessingState.COMPLETED
    }
    return state_flow.get(current_state, ProcessingState.COMPLETED)

def process_message(message_data: Dict[Any, Any]) -> Dict[str, str]:
    """Process incoming message data"""
    try:
        # Extract user ID from the message
        user_id = message_data.get('from')
        
        if not user_id:
            return {"status": "error", "message": "User ID not found"}
            
        # Initialize user state if not exists
        if user_id not in user_states:
            user_states[user_id] = ProcessingState.WAITING_FOR_ID
            return {
                "status": "success",
                "message": "Please upload your ID card photo"
            }
            
        # Check if message contains media
        if not message_data.get('media_url'):
            return {
                "status": "success",
                "message": "Please upload a photo of the required document"
            }
            
        current_state = user_states[user_id]
        
        # Process document based on current state
        if current_state == ProcessingState.WAITING_FOR_ID:
            data = doc_processor.extract_data_from_image(
                message_data['media_url'],
                "identity_card"
            )
        elif current_state == ProcessingState.WAITING_FOR_LICENSE:
            data = doc_processor.extract_data_from_image(
                message_data['media_url'],
                "drivers_license"
            )
        elif current_state == ProcessingState.WAITING_FOR_LOGCARD:
            data = doc_processor.extract_data_from_image(
                message_data['media_url'],
                "log_card"
            )
        else:
            return {
                "status": "success",
                "message": "All documents have been processed"
            }
            
        # Save extracted data to Monday.com
        if data:
            doc_processor.save_to_monday(data)
            
        # Update user state
        next_state = get_next_state(current_state)
        user_states[user_id] = next_state
        
        # Prepare response message
        if next_state == ProcessingState.COMPLETED:
            return {
                "status": "success",
                "message": "All documents have been processed successfully!"
            }
        elif next_state == ProcessingState.WAITING_FOR_LICENSE:
            return {
                "status": "success",
                "message": "ID card processed. Please upload your driver's license photo"
            }
        elif next_state == ProcessingState.WAITING_FOR_LOGCARD:
            return {
                "status": "success",
                "message": "Driver's license processed. Please upload your log card photo"
            }
            
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to process message: {str(e)}"
        }

@webhook_blueprint.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming webhook events"""
    try:
        # Get the request data
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        # Log the webhook event
        logging.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        
        # Process the message
        result = process_message(data)
        return jsonify(result), 200
        
    except Exception as e:
        logging.error(f"Error handling webhook: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Webhook processing failed: {str(e)}"
        }), 500

@webhook_blueprint.route('/webhook', methods=['GET'])
def verify_webhook():
    """Endpoint for webhook verification"""
    return jsonify({"status": "success", "message": "Webhook endpoint is active"}), 200