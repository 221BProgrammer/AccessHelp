"""
Enhanced OCR Module for AccessHelp
Supports multiple languages, document scanning, and real-time text recognition
"""

import os
import sys
import cv2
import numpy as np
from PIL import Image
import pytesseract
from deep_translator import GoogleTranslator
import easyocr
import re
from datetime import datetime

# Add root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

class EnhancedOCR:
    """Advanced OCR with multiple backends and language support"""
    
    def __init__(self):
        """Initialize OCR engines"""
        # Initialize EasyOCR (supports 80+ languages)
        # CORRECTED: Use proper language codes
        # 'ch_sim' = Simplified Chinese, 'ch_tra' = Traditional Chinese
        try:
            self.reader = easyocr.Reader(['en', 'hi', 'ja', 'ch_sim', 'fr', 'de', 'es'], gpu=False)
            print("✅ EasyOCR initialized successfully")
        except Exception as e:
            print(f"⚠️ EasyOCR initialization error: {e}")
            self.reader = None
        
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            print("✅ Tesseract OCR available")
        except:
            self.tesseract_available = False
            print("⚠️ Tesseract not installed. Install with: sudo apt-get install tesseract-ocr")
        
        self.translator = GoogleTranslator()
    
    def extract_text_from_image(self, image_path, language='en'):
        """
        Extract text from image using multiple methods
        
        Args:
            image_path: Path to image file or numpy array
            language: Language code (en, hi, ja, ch_sim, fr, de, es)
        
        Returns:
            Extracted text
        """
        # Load image
        if isinstance(image_path, str):
            image = cv2.imread(image_path)
        else:
            image = image_path
        
        if image is None:
            return "Error: Could not load image"
        
        # Preprocess image for better OCR
        processed = self._preprocess_image(image)
        
        # Try EasyOCR first (better for complex scripts)
        if self.reader:
            try:
                # Map simple language codes to EasyOCR codes
                lang_map = {
                    'en': 'en',
                    'hi': 'hi',
                    'ja': 'ja',
                    'zh': 'ch_sim',  # Map 'zh' to 'ch_sim'
                    'fr': 'fr',
                    'de': 'de',
                    'es': 'es'
                }
                easyocr_lang = lang_map.get(language, 'en')
                
                results = self.reader.readtext(processed, detail=0, paragraph=True)
                text = ' '.join(results)
                if text.strip():
                    return text
            except Exception as e:
                print(f"EasyOCR error: {e}")
        
        # Fallback to Tesseract if EasyOCR fails
        if self.tesseract_available:
            try:
                # Convert to PIL Image
                pil_image = Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
                
                # Map language for Tesseract
                tesseract_lang_map = {
                    'en': 'eng',
                    'hi': 'hin',
                    'ja': 'jpn',
                    'zh': 'chi_sim',
                    'fr': 'fra',
                    'de': 'deu',
                    'es': 'spa'
                }
                tesseract_lang = tesseract_lang_map.get(language, 'eng')
                
                # Configure Tesseract
                custom_config = f'--oem 3 --psm 6 -l {tesseract_lang}'
                text = pytesseract.image_to_string(pil_image, config=custom_config)
                
                if text.strip():
                    return text
            except Exception as e:
                print(f"Tesseract error: {e}")
        
        return "No text detected in image"
    
    def _preprocess_image(self, image):
        """
        Preprocess image for better OCR results.

        BUG FIX: old version returned a single-channel (grayscale/binary)
        image.  Callers that passed it back into cv2.cvtColor(...,
        COLOR_BGR2RGB) crashed with an assertion error because they expected
        3 channels.  This version always returns a 3-channel BGR image so
        downstream code works regardless of whether deskewing ran or not.
        """
        # Convert to grayscale for processing
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive thresholding (better for varying lighting than global Otsu)
        thresh = cv2.threshold(blurred, 0, 255,
                               cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        # Denoise
        denoised = cv2.medianBlur(thresh, 3)

        # Deskew
        coords = np.column_stack(np.where(denoised > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle

            (h, w) = denoised.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            denoised = cv2.warpAffine(
                denoised, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

        # Convert back to 3-channel BGR so callers always get the same type
        return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    
    def extract_text_from_camera(self, language='en'):
        """Real-time OCR from camera"""
        cap = cv2.VideoCapture(0)
        results = []
        
        print("📷 Starting camera OCR. Press 'q' to quit, 's' to capture text")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Show frame
            cv2.imshow('OCR Scanner - Press s to capture, q to quit', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Extract text from current frame
                text = self.extract_text_from_image(frame, language)
                if text and text != "No text detected in image":
                    print(f"\n📝 Detected Text: {text}")
                    results.append(text)
                else:
                    print("No text detected in this frame")
        
        cap.release()
        cv2.destroyAllWindows()
        return results
    
    def scan_document(self, image_path, output_path=None):
        """Scan document with edge detection and perspective correction"""
        # Load image
        image = cv2.imread(image_path)
        original = image.copy()
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply blur and edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)
        
        # Find contours
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        # Find document contour
        document_contour = None
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                document_contour = approx
                break
        
        if document_contour is not None:
            # Apply perspective transform
            warped = self._four_point_transform(original, document_contour.reshape(4, 2))
            
            # Save warped image
            if output_path:
                cv2.imwrite(output_path, warped)
                print(f"✅ Scanned document saved to {output_path}")
            
            return warped
        else:
            print("Could not find document boundaries")
            return image
    
    def _four_point_transform(self, image, pts):
        """Apply perspective transform to get bird's eye view"""
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect
        
        # Compute width
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        # Compute height
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # Destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # Apply transform
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
        return warped
    
    def _order_points(self, pts):
        """Order points for perspective transform"""
        rect = np.zeros((4, 2), dtype="float32")
        
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def extract_text_multiple_languages(self, image_path):
        """Extract text and detect languages"""
        text = self.extract_text_from_image(image_path)
        
        # Detect language (simple method)
        lang_keywords = {
            'hi': ['मैं', 'है', 'और', 'यह'],
            'ja': ['です', 'ます', 'です', 'こと'],
            'zh': ['的', '是', '了', '我'],
            'fr': ['le', 'la', 'et', 'est'],
            'es': ['el', 'la', 'y', 'es']
        }
        
        detected_lang = 'en'
        for lang, keywords in lang_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                detected_lang = lang
                break
        
        return text, detected_lang

# Initialize global OCR
try:
    ocr_enhanced = EnhancedOCR()
    print("✅ OCR Enhanced module initialized successfully")
except Exception as e:
    print(f"⚠️ Error initializing OCR Enhanced: {e}")
    ocr_enhanced = None