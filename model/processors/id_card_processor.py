from base_processor import BaseDocumentProcessor

class IDCardProcessor(BaseDocumentProcessor):
    def __init__(self):
        super().__init__()
        self.required_fields = ['name', 'id', 'date']

    def validate(self, extracted_text):
        """Validate ID card specific fields"""
        text_lower = extracted_text.lower()
        # Check for ID card specific keywords and patterns
        is_valid = (
            ('identity' in text_lower or 'id card' in text_lower) and
            any(field in text_lower for field in self.required_fields)
        )
        return is_valid

    def process(self, image_data):
        """Process ID card image"""
        extracted_text = self.extract_text(image_data)
        if not extracted_text:
            return {
                'success': False,
                'error': 'Failed to extract text from image'
            }

        if self.validate(extracted_text):
            return {
                'success': True,
                'doc_type': 'id_card',
                'text': extracted_text
            }
        return {
            'success': False,
            'error': 'Invalid ID card format'
        }