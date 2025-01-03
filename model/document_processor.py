from .processors.id_card_processor import IDCardProcessor
from .processors.drivers_license_processor import DriversLicenseProcessor
from .processors.log_card_processor import LogCardProcessor

class DocumentProcessor:
    def __init__(self):
        self.processors = {
            'id_card': IDCardProcessor(),
            'drivers_license': DriversLicenseProcessor(),
            'log_card': LogCardProcessor()
        }

    def process_document(self, image_data):
        """Try processing document with all available processors"""
        errors = []
        
        # Try each processor until we find a match
        for processor in self.processors.values():
            result = processor.process(image_data)
            if result['success']:
                return result
            errors.append(result['error'])

        # If no processor succeeded, return error
        return {
            'success': False,
            'error': 'Could not identify document type. Errors: ' + '; '.join(errors)
        }