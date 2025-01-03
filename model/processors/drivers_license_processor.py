from base_processor import BaseDocumentProcessor


class DriversLicenseProcessor(BaseDocumentProcessor):
    def __init__(self):
        super().__init__()
        self.required_fields = ['license', 'expiry', 'class']

    def validate(self, extracted_text):
        """Validate driver's license specific fields"""
        text_lower = extracted_text.lower()
        # Check for driver's license specific keywords and patterns
        is_valid = (
            ('driver' in text_lower or 'license' in text_lower) and
            any(field in text_lower for field in self.required_fields)
        )
        return is_valid

    def process(self, image_data):
        """Process driver's license image"""
        extracted_text = self.extract_text(image_data)
        if not extracted_text:
            return {
                'success': False,
                'error': 'Failed to extract text from image'
            }

        if self.validate(extracted_text):
            return {
                'success': True,
                'doc_type': 'drivers_license',
                'text': extracted_text
            }
        return {
            'success': False,
            'error': 'Invalid driver\'s license format'
        }