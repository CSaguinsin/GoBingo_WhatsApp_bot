class MessageController:
    def _handle_image_message(self, chat_id, message):
        """Handle document image uploads"""
        media_url = message.get('media', {}).get('url')
        if not media_url:
            return {'error': 'No media URL found'}
            
        # Process the document
        image_data = self.whapi_client.download_media(media_url)
        if not image_data:
            return {'error': 'Failed to download media'}
            
        # Process with appropriate document processor
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