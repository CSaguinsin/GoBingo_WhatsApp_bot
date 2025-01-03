from abc import ABC, abstractmethod
from transformers import VisionEncoderDecoderModel, AutoTokenizer, AutoImageProcessor
from PIL import Image
import io

class BaseDocumentProcessor(ABC):
    def __init__(self):
        # Initialize the AI models
        self.model = VisionEncoderDecoderModel.from_pretrained("google/siglip-base-patch16-224")
        self.tokenizer = AutoTokenizer.from_pretrained("google/siglip-base-patch16-224")
        self.image_processor = AutoImageProcessor.from_pretrained("google/siglip-base-patch16-224")

    def extract_text(self, image_data):
        """Extract text from image using smolVLM"""
        try:
            image = Image.open(io.BytesIO(image_data))
            inputs = self.image_processor(image, return_tensors="pt")
            outputs = self.model.generate(
                pixel_values=inputs.pixel_values,
                max_length=50,
                num_beams=5
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return None

    @abstractmethod
    def validate(self, extracted_text):
        """Validate the extracted text for specific document type"""
        pass

    @abstractmethod
    def process(self, image_data):
        """Process the document"""
        pass