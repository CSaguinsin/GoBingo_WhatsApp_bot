from base_processor import BaseDocumentProcessor



class LogCardProcessor(BaseDocumentProcessor):
    def __init__(self):
        super().__init__()
        self.required_fields = ['vehicle', 'registration', 'owner']

    def validate(self, extracted_text):
        """Validate log card specific fields"""
        text_lower = extracted_text.lower()
        # Check for log card specific keywords and patterns
        is_valid = (
            'log' in text_lower and
            any(field in text_lower for field in self.required_fields)
        )
        return is_valid

    def process(self, image_data):
        """Process log card image"""
        extracted_text = self.extract_text(image_data)
        if not extracted_text:
            return {
                'success': False,
                'error': 'Failed to extract text from image'
            }

        if self.validate(extracted_text):
            return {
                'success': True,
                'doc_type': 'log_card',
                'text': extracted_text
            }
        return {
            'success': False,
            'error': 'Invalid log card format'
        }