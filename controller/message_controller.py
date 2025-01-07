import logging
from flask import Blueprint, request, jsonify

messages_blueprint = Blueprint('messages', __name__)

class MessageController:
    def __init__(self, document_processor, whapi_client, user_state, message_view):
        self.document_processor = document_processor
        self.whapi_client = whapi_client
        self.user_state = user_state
        self.message_view = message_view

        # Register route with instance method
        messages_blueprint.add_url_rule('/messages', 'handle_messages', self.handle_messages, methods=['POST'])

    def handle_messages(self):
        """Handle incoming messages."""
        try:
            # Parse incoming request
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            chat_id = data.get('chat_id')
            message = data.get('message')

            if not chat_id or not message:
                return jsonify({'error': 'Invalid request data'}), 400

            # Check if message contains media
            if 'media' in message:
                return jsonify(self._handle_image_message(chat_id, message))

            # Add handling for other message types if needed
            return jsonify({'status': 'success'})
        except Exception as e:
            logging.error(f"Error handling message: {e}")
            return jsonify({'error': str(e)}), 500

    def _handle_image_message(self, chat_id, message):
        """Handle document image uploads."""
        try:
            media_url = message.get('media', {}).get('url')
            if not media_url:
                logging.error("No media URL found in message.")
                return {'error': 'No media URL found'}

            # Download image from media URL
            image_data = self.whapi_client.download_media(media_url)
            if not image_data:
                logging.error("Failed to download media from URL.")
                return {'error': 'Failed to download media'}

            # Process the document using the document processor
            result = self.document_processor.process_document(image_data)
            if result['success']:
                # Update user state
                self.user_state.update_document_status(chat_id, result['doc_type'])

                # Send success response
                response_text = self.message_view.format_document_success(result['doc_type'])
                self.whapi_client.send_message(chat_id, response_text)

                # Check if all documents are complete
                if self.user_state.check_completion(chat_id):
                    completion_text = self.message_view.get_completion_message()
                    self.whapi_client.send_message(chat_id, completion_text)
                    self.user_state.clear_user(chat_id)
            else:
                # Send detailed error message
                error_text = self.message_view.format_document_error(result['error'])
                self.whapi_client.send_message(chat_id, error_text)

            return {'status': 'success'}
        except Exception as e:
            logging.error(f"Error processing image message: {e}")
            return {'error': str(e)}
