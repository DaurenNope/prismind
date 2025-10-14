#!/usr/bin/env python3
"""
Media OCR Analyzer for PrisMind
Handles OCR and basic image analysis
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# Optional imports for media analysis
TESSERACT_AVAILABLE = False
REQUESTS_AVAILABLE = False
PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    logging.warning("pytesseract not available - OCR features disabled")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    logging.warning("requests not available - image download disabled")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    logging.warning("PIL not available - image processing disabled")

logger = logging.getLogger(__name__)


class MediaOCRAnalyzer:
    """Handles OCR and basic image analysis"""
    
    def __init__(self):
        self.temp_dir = Path("temp/media")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_single_media(self, media_url: str, media_id: str) -> Optional[Dict]:
        """Analyze a single media item (image)"""
        if not REQUESTS_AVAILABLE or not PIL_AVAILABLE:
            logger.warning("Required dependencies not available for media analysis")
            return None
        
        try:
            # Download image
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            
            # Save to temp file
            file_extension = self._get_file_extension(media_url)
            temp_file = self.temp_dir / f"{media_id}{file_extension}"
            
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # Analyze the image
            analysis = self._analyze_image_file(str(temp_file))
            
            # Clean up temp file
            temp_file.unlink(missing_ok=True)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing media {media_url}: {e}")
            return None
    
    def _analyze_image_file(self, file_path: str) -> Dict:
        """Analyze an image file for text and basic properties"""
        analysis = {
            'media_type': 'image',
            'text_content': '',
            'text_confidence': 0.0,
            'image_properties': {},
            'analysis_quality': 'basic'
        }
        
        try:
            if PIL_AVAILABLE:
                # Get image properties
                with Image.open(file_path) as img:
                    analysis['image_properties'] = {
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                        'size_bytes': os.path.getsize(file_path)
                    }
            
            # Extract text using OCR
            if TESSERACT_AVAILABLE:
                try:
                    # Extract text with confidence scores
                    text_data = pytesseract.image_to_data(file_path, output_type=pytesseract.Output.DICT)
                    
                    # Combine text with confidence > 30
                    text_parts = []
                    confidences = []
                    
                    for i, conf in enumerate(text_data['conf']):
                        if int(conf) > 30:  # Only include text with >30% confidence
                            text_parts.append(text_data['text'][i])
                            confidences.append(int(conf))
                    
                    if text_parts:
                        analysis['text_content'] = ' '.join(text_parts).strip()
                        analysis['text_confidence'] = sum(confidences) / len(confidences) / 100.0
                        analysis['analysis_quality'] = 'enhanced'
                    
                except Exception as e:
                    logger.warning(f"OCR failed for {file_path}: {e}")
            
            # Basic image analysis
            if analysis['text_content']:
                analysis['has_text'] = True
                analysis['text_length'] = len(analysis['text_content'])
                analysis['word_count'] = len(analysis['text_content'].split())
            else:
                analysis['has_text'] = False
                analysis['text_length'] = 0
                analysis['word_count'] = 0
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image file {file_path}: {e}")
            return analysis
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL"""
        try:
            # Extract extension from URL
            if '.' in url:
                ext = url.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                    return f'.{ext}'
            return '.jpg'  # Default
        except:
            return '.jpg'
    
    def is_available(self) -> bool:
        """Check if OCR analysis is available"""
        return TESSERACT_AVAILABLE and PIL_AVAILABLE and REQUESTS_AVAILABLE
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get available capabilities"""
        return {
            'ocr': TESSERACT_AVAILABLE,
            'image_processing': PIL_AVAILABLE,
            'image_download': REQUESTS_AVAILABLE,
            'full_analysis': self.is_available()
        }





