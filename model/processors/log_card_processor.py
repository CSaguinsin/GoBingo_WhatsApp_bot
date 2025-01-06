from base_processor import BaseDocumentProcessor
from PIL import Image
import torch
import logging
import os
from datetime import datetime
import re
from difflib import SequenceMatcher
from typing import Optional, Dict, Any, Tuple

# Add this at the very top of the file
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger(__name__)

class LogCardProcessor(BaseDocumentProcessor):
    def __init__(self):
        super().__init__()
        self._validate_environment()
        self._initialize_patterns()
        
    def _validate_environment(self) -> None:
        """Validate environment variables."""
        self.prompt = os.getenv('LOG_CARD_PROMPT')
        if not self.prompt:
            logger.error("LOG_CARD_PROMPT environment variable is required but not set")
            raise ValueError("LOG_CARD_PROMPT environment variable is required")

    def _initialize_patterns(self):
        """Initialize field mappings and expected fields."""
        self.field_mapping = {
            "Vehicle No.": "Vehicle No",
            "Vehicle Number": "Vehicle No",
            "Registration No.": "Vehicle No",
            "Make / Model": "Make/Model",
            "Make & Model": "Make/Model",
            "Vehicle Make/Model": "Make/Model",
            "Engine No.": "Engine No",
            "Engine Number": "Engine No",
            "Chassis No.": "Chassis No",
            "Chassis Number": "Chassis No",
            "Original Registration Date": "Original Registration Date",
            "First Registration Date": "Original Registration Date"
        }
        
        self.fields = [
            "Vehicle No",
            "Make/Model",
            "Vehicle Type",
            "Vehicle Attachment 1",
            "Vehicle Scheme",
            "Chassis No",
            "Propellant",
            "Engine No",
            "Motor No",
            "Engine Capacity",
            "Power Rating",
            "Maximum Power Output",
            "Maximum Laden Weight",
            "Unladen Weight",
            "Year Of Manufacture",
            "Original Registration Date",
            "Lifespan Expiry Date",
            "COE Category",
            "PQP Paid",
            "COE Expiry Date",
            "Road Tax Expiry Date",
            "PARF Eligibility Expiry Date",
            "Inspection Due Date",
            "Intended Transfer Date"
        ]

    def process_with_model(self, image: Image.Image) -> Optional[str]:
        """Process image with SmolVLM model."""
        try:
            if not hasattr(self, 'processor') or not hasattr(self, 'model'):
                logger.error("Model or processor not initialized")
                return None

            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')

            inputs = self.processor(
                text=[self.prompt],
                images=[image],
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                try:
                    output_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=256,
                        num_beams=3,
                        temperature=0.3,
                        do_sample=True,
                        length_penalty=1.0,
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=2
                    )
                    
                    return self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
                    
                except torch.cuda.OutOfMemoryError:
                    logger.error("CUDA out of memory error during model inference")
                    torch.cuda.empty_cache()
                    return None
                    
        except Exception as e:
            logger.error(f"Model processing failed: {str(e)}")
            return None

    def find_closest_field(self, key: str) -> Optional[str]:
        """Find the closest matching field name using fuzzy matching."""
        key = key.lower()
        best_match = None
        best_ratio = 0
        
        for field in self.fields:
            ratio = SequenceMatcher(None, key, field.lower()).ratio()
            if ratio > best_ratio and ratio > 0.8:
                best_ratio = ratio
                best_match = field
        
        return best_match

    def format_text(self, text: str) -> str:
        """Format the extracted text into a structured output."""
        try:
            lines = text.split('\n')
            formatted_data = {field: None for field in self.fields}
            
            current_field = None
            current_value = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line is a field label
                if ':' in line:
                    # Save previous field if exists
                    if current_field and current_value:
                        formatted_data[current_field] = ' '.join(current_value).strip()
                        current_value = []
                    
                    # Process new field
                    key, value = line.split(':', 1)
                    key = key.strip()
                    
                    # Check for known field mappings
                    if key in self.field_mapping:
                        key = self.field_mapping[key]
                    elif key not in formatted_data:
                        key = self.find_closest_field(key)
                    
                    if key in formatted_data:
                        current_field = key
                        if value.strip():
                            current_value = [value.strip()]
                        else:
                            current_value = []
                elif current_field:  # Continue previous field
                    current_value.append(line)
            
            # Save last field
            if current_field and current_value:
                formatted_data[current_field] = ' '.join(current_value).strip()
            
            # Post-process specific fields
            for field, value in formatted_data.items():
                if value is None or value.strip() == '' or value.lower() == 'not found':
                    formatted_data[field] = '-'
                else:
                    value = value.strip()
                    
                    # Handle dates
                    if any(date_field in field for date_field in ['Date', 'Expiry']):
                        try:
                            # Try to parse and standardize date format
                            if value != '-':
                                # Handle various date formats
                                date_patterns = [
                                    '%d %b %Y',
                                    '%d-%b-%Y',
                                    '%d/%m/%Y',
                                    '%Y-%m-%d',
                                    '%d.%m.%Y'
                                ]
                                
                                parsed_date = None
                                for pattern in date_patterns:
                                    try:
                                        parsed_date = datetime.strptime(value, pattern)
                                        break
                                    except ValueError:
                                        continue
                                
                                if parsed_date:
                                    value = parsed_date.strftime('%d %b %Y')
                                
                        except Exception as e:
                            logger.warning(f"Could not parse date: {value} for field {field}")
                    
                    # Handle monetary values
                    elif field == 'PQP Paid' and value != '-':
                        try:
                            # Remove any existing currency symbols and commas
                            cleaned = re.sub(r'[^\d.]', '', value)
                            amount = float(cleaned)
                            value = f"${amount:,.2f}"
                        except ValueError:
                            logger.warning(f"Could not parse monetary value: {value}")
                    
                    # Handle weights
                    elif 'Weight' in field and value != '-':
                        try:
                            # Extract numeric value and add 'kg' if missing
                            weight = re.search(r'\d+', value)
                            if weight:
                                value = f"{weight.group()} kg"
                        except Exception as e:
                            logger.warning(f"Could not parse weight: {value}")
                    
                    formatted_data[field] = value
            
            # Format output
            output_lines = []
            for field in self.fields:
                value = formatted_data.get(field, '-')
                output_lines.append(f"{field}: {value}")
            
            return '\n'.join(output_lines)
                
        except Exception as e:
            logger.error(f"Error formatting text: {str(e)}")
            return text

    def process_image(self, image_path: str) -> Tuple[str, str]:
        """Main image processing pipeline using SmolVLM."""
        try:
            logger.info(f"Processing log card image: {image_path}")
            
            # Verify and load image
            original_image = self.verify_image(image_path)
            if original_image is None:
                return "Image verification failed", ""
            
            try:
                # Process with SmolVLM model
                raw_text = self.process_with_model(original_image)
                if not raw_text:
                    return "Text extraction failed", ""
                
                # Format the extracted text
                formatted_text = self.format_text(raw_text)
                return formatted_text, raw_text
                
            except Exception as e:
                logger.error(f"Error during text extraction: {str(e)}")
                return "Text extraction failed", ""
            
        except Exception as e:
            logger.error(f"General error in process_image: {str(e)}")
            return "Image processing failed", ""
        finally:
            # Cleanup
            if 'original_image' in locals():
                original_image.close()
            self.cleanup()


# Usage example
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set environment variable
    os.environ['LOG_CARD_PROMPT'] = "Extract information from this vehicle log card"

    # Initialize processor
    try:
        processor = LogCardProcessor()
        
        # Process an image
        image_path = "path/to/your/image.jpg"
        result = processor.process_image(image_path)
        
        print("Extracted Information:")
        print(result)
        
    except Exception as e:
        logger.error(f"Failed to process image: {str(e)}")