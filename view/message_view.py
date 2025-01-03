
class MessageView:
    def format_document_error(self, error_message):
        """Format document error message with details"""
        return (
            "❌ Document validation failed.\n\n"
            f"Details: {error_message}\n\n"
            "Please ensure:\n"
            "- The image is clear and readable\n"
            "- The document is properly oriented\n"
            "- All required information is visible"
        )
        
    def get_welcome_message(self):
        """Get welcome message"""
        return ("Welcome to GoBingo WhatsApp AI Bot! 👋\n\n"
                "Please upload the following documents:\n"
                "1. Identity Card\n"
                "2. Driver's License\n"
                "3. Log Card\n\n"
                "Type 'CHECK_STATUS' to see your progress.\n"
                "Type 'HELP' for available commands.")
                
    def get_help_message(self):
        """Get help message"""
        return "Available commands:\n\n" + \
               "\n".join(f"• {cmd}: {desc}" for cmd, desc in self.commands.items())
               
    def format_status(self, status):
        """Format document status message"""
        return ("Document Upload Status:\n"
                f"✅ Identity Card: {'Uploaded' if status.get('id_card') else 'Missing'}\n"
                f"✅ Driver's License: {'Uploaded' if status.get('drivers_license') else 'Missing'}\n"
                f"✅ Log Card: {'Uploaded' if status.get('log_card') else 'Missing'}")
                
    def format_document_success(self, doc_type):
        """Format document success message"""
        doc_names = {
            'id_card': 'Identity Card',
            'drivers_license': "Driver's License",
            'log_card': 'Log Card'
        }
        return f"✅ {doc_names.get(doc_type)} processed successfully!"
        
    def format_document_error(self):
        """Format document error message"""
        return "❌ Could not identify document type. Please try again."
        
    def get_completion_message(self):
        """Get completion message"""
        return "🎉 All required documents have been uploaded and processed!"
        
    def get_unknown_type_message(self):
        """Get unknown message type response"""
        return "Please send a document image or use one of the available commands. Type 'HELP' for more information."