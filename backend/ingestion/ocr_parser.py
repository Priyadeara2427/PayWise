# backend/ingestion/ocr_parser.py
import pytesseract
from PIL import Image
import re
import logging
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.counterparty_classifier import CounterpartyClassifier, CounterpartyCategory

logger = logging.getLogger(__name__)

# Explicitly set Tesseract path for Windows
if sys.platform == 'win32':
    # Common installation paths
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\prart\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
    ]
    
    tesseract_found = False
    for tesseract_path in possible_paths:
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract configured at: {tesseract_path}")
            tesseract_found = True
            break
    
    if not tesseract_found:
        logger.warning("Tesseract not found in common locations. OCR may not work.")

class OCRParser:
    """Enhanced OCR parser with preprocessing, intelligent extraction, and classification"""
    
    @classmethod
    def parse(cls, file_path: str, preprocess: bool = True) -> Dict[str, Any]:
        """
        Parse image using OCR with preprocessing and intelligent classification
        
        Args:
            file_path: Path to image file
            preprocess: Whether to preprocess image for better OCR
        
        Returns:
            Dictionary with extracted data
        """
        try:
            # Verify Tesseract is working
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                logger.error(f"Tesseract not configured properly: {e}")
                # Try to set path again
                if sys.platform == 'win32':
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # Read and preprocess image
            image = cls._load_image(file_path)
            
            if preprocess:
                image = cls._preprocess_image(image)
            
            # Extract text using Tesseract with multiple PSM modes for better results
            text = cls._extract_text_with_multiple_modes(image)
            
            # Extract structured information
            amounts = cls._extract_amounts(text)
            dates = cls._extract_dates(text)
            counterparties = cls._extract_counterparties_with_context(text)
            gst_numbers = cls._extract_gst_numbers(text)
            pan_numbers = cls._extract_pan_numbers(text)
            
            # Parse into obligations with classification
            obligations = cls._create_obligations_with_classification(
                amounts, dates, counterparties, gst_numbers, pan_numbers, text
            )
            
            return {
                'raw_text': text,
                'amounts': amounts,
                'dates': dates,
                'counterparties': counterparties,
                'gst_numbers': gst_numbers,
                'pan_numbers': pan_numbers,
                'obligations': obligations,
                'source_type': 'image',
                'record_count': len(obligations),
                'confidence': cls._get_confidence_score(text)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse image {file_path}: {e}")
            raise
    
    @classmethod
    def _extract_text_with_multiple_modes(cls, image: np.ndarray) -> str:
        """Extract text using multiple OCR modes for better results"""
        texts = []
        
        # Try different PSM modes
        psm_modes = [
            '--psm 6',   # Assume a single uniform block of text
            '--psm 3',   # Fully automatic page segmentation
            '--psm 4',   # Assume a single column of text
            '--psm 11'   # Sparse text
        ]
        
        for psm in psm_modes:
            try:
                text = pytesseract.image_to_string(image, config=psm)
                if len(text.strip()) > len(''.join(texts)):
                    texts.append(text)
            except:
                continue
        
        # Return the longest text (usually the most complete)
        if texts:
            return max(texts, key=len)
        return ""
    
    @staticmethod
    def _load_image(file_path: str) -> np.ndarray:
        """Load image from file"""
        image = cv2.imread(file_path)
        if image is None:
            raise ValueError(f"Could not load image: {file_path}")
        return image
    
    @classmethod
    def _preprocess_image(cls, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding for better text extraction
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Denoise
        denoised = cv2.medianBlur(thresh, 3)
        
        # Enhance contrast
        denoised = cv2.equalizeHist(denoised)
        
        # Deskew if needed
        coords = np.column_stack(np.where(denoised > 0))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:
                (h, w) = denoised.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                denoised = cv2.warpAffine(denoised, M, (w, h), 
                                          flags=cv2.INTER_CUBIC, 
                                          borderMode=cv2.BORDER_REPLICATE)
        
        # Resize image for better OCR (if too small)
        height, width = denoised.shape
        if height < 500 or width < 500:
            scale = max(1000/height, 1000/width)
            new_height = int(height * scale)
            new_width = int(width * scale)
            denoised = cv2.resize(denoised, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return denoised
    
    @staticmethod
    def _extract_amounts(text: str) -> List[Dict[str, Any]]:
        """Extract amounts with context and better pattern matching"""
        amount_patterns = [
            r'(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)',
            r'(?:amount|total|due|payable|receivable|balance)[:\s]*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:Rs\.?|INR|₹)',
            r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
            r'(\d+(?:\.\d{2})?)\s*(?:rupees|only)',
            r'total\s*:?\s*([\d,]+(?:\.\d{2})?)',
            r'grand\s*total\s*:?\s*([\d,]+(?:\.\d{2})?)'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    # Filter out very small amounts that are likely not real (like page numbers)
                    if amount > 10:  # Minimum amount threshold
                        amounts.append({
                            'value': amount,
                            'context': match.group(0),
                            'position': match.start()
                        })
                except ValueError:
                    continue
        
        # Remove duplicates while preserving order and keep largest amounts
        seen = set()
        unique_amounts = []
        for amount in sorted(amounts, key=lambda x: x['value'], reverse=True):
            if amount['value'] not in seen:
                seen.add(amount['value'])
                unique_amounts.append(amount)
        
        return unique_amounts[:10]  # Limit to top 10 amounts
    
    @staticmethod
    def _extract_dates(text: str) -> List[Dict[str, Any]]:
        """Extract dates with context and Indian format support"""
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b',
            r'\b(?:due|payment|invoice|bill|date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(1)
                try:
                    parsed_date = cls._parse_date(date_str)
                    dates.append({
                        'value': parsed_date,
                        'original': date_str,
                        'context': match.group(0),
                        'position': match.start()
                    })
                except:
                    continue
        
        return dates
    
    @staticmethod
    def _parse_date(date_str: str):
        """Parse date string to date object with multiple format support"""
        formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
            '%d/%m/%y', '%m/%d/%y', '%d-%m-%y', '%m-%d-%y',
            '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y',
            '%d %b %y', '%d %B %y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date: {date_str}")
    
    @classmethod
    def _extract_counterparties_with_context(cls, text: str) -> List[Dict[str, Any]]:
        """Extract counterparty names with rich context for classification"""
        patterns = [
            # Business/Company patterns
            r'(?:to|from|vendor|customer|party|payee|payer|supplier|client)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Enterprises|Industries|Trading|Fabrics|Corp|Ltd|LLC|Technologies|Solutions|Services|Company)))\b',
            r'(?:bill\s*to|ship\s*to|invoice\s*to|billed\s*to)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Government/Tax patterns
            r'\b(?:GST|Tax|Income Tax|Government|Govt)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Personal patterns
            r'(?:paid\s*to|received\s*from)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        counterparties = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                if len(name) > 2 and name.lower() not in ['date', 'amount', 'total', 'due', 'invoice']:
                    # Get context around the match
                    context = cls._extract_context(text, match.start())
                    counterparties.append({
                        'name': name,
                        'context': context,
                        'position': match.start(),
                        'matched_text': match.group(0)
                    })
        
        # Remove duplicates
        seen = set()
        unique_counterparties = []
        for cp in counterparties:
            if cp['name'] not in seen:
                seen.add(cp['name'])
                unique_counterparties.append(cp)
        
        return unique_counterparties
    
    @staticmethod
    def _extract_context(text: str, position: int, window: int = 300) -> str:
        """Extract context around a position for better classification"""
        start = max(0, position - window)
        end = min(len(text), position + window)
        return text[start:end]
    
    @staticmethod
    def _extract_gst_numbers(text: str) -> List[Dict[str, Any]]:
        """Extract GST numbers from text"""
        # GSTIN pattern: 15 characters, first 2 digits state code, next 10 PAN, then 1 checksum, then 1 for entity, then 1 for check
        gst_pattern = r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d{1}[A-Z]{1}[Z]{1}[A-Z\d]{1}\b'
        
        gst_numbers = []
        matches = re.finditer(gst_pattern, text, re.IGNORECASE)
        for match in matches:
            context = text[max(0, match.start()-100):min(len(text), match.end()+100)]
            gst_numbers.append({
                'gstin': match.group(0),
                'context': context,
                'position': match.start()
            })
        
        return gst_numbers
    
    @staticmethod
    def _extract_pan_numbers(text: str) -> List[Dict[str, Any]]:
        """Extract PAN numbers from text"""
        # PAN pattern: 5 letters, 4 digits, 1 letter
        pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
        
        pan_numbers = []
        matches = re.finditer(pan_pattern, text)
        for match in matches:
            context = text[max(0, match.start()-100):min(len(text), match.end()+100)]
            pan_numbers.append({
                'pan': match.group(0),
                'context': context,
                'position': match.start()
            })
        
        return pan_numbers
    
    @classmethod
    def _classify_counterparty(cls, name: str, context: str, gst_numbers: List = None, pan_numbers: List = None) -> Tuple[str, float]:
        """
        Classify counterparty type using intelligent rules
        
        Args:
            name: Counterparty name
            context: Additional context from the image
            gst_numbers: List of extracted GST numbers
            pan_numbers: List of extracted PAN numbers
        
        Returns:
            Tuple of (type_string, confidence_score)
        """
        # Check for GST numbers nearby - indicates tax authority or registered business
        if gst_numbers:
            for gst in gst_numbers:
                if abs(gst['position'] - len(context)) < 500:  # Within 500 chars
                    # If GST number present, it's likely a registered business
                    if any(word in context.lower() for word in ['tax', 'gst', 'invoice']):
                        return 'tax_authority', 0.9
        
        # Check for PAN numbers
        if pan_numbers:
            for pan in pan_numbers:
                if abs(pan['position'] - len(context)) < 500:
                    return 'vendor', 0.85  # Registered business
        
        # Use the intelligent classifier
        category, confidence = CounterpartyClassifier.classify(name, context)
        
        # Map category to string
        type_mapping = {
            CounterpartyCategory.VENDOR: 'vendor',
            CounterpartyCategory.CUSTOMER: 'customer',
            CounterpartyCategory.GOVERNMENT: 'government',
            CounterpartyCategory.TAX_AUTHORITY: 'tax_authority',
            CounterpartyCategory.EMPLOYEE: 'employee',
            CounterpartyCategory.FRIEND: 'friend',
            CounterpartyCategory.FAMILY: 'family',
            CounterpartyCategory.BANK: 'bank',
            CounterpartyCategory.UTILITY: 'utility',
            CounterpartyCategory.RENT: 'rent',
            CounterpartyCategory.INSURANCE: 'insurance',
            CounterpartyCategory.INVESTMENT: 'investment',
            CounterpartyCategory.CHARITY: 'charity',
            CounterpartyCategory.UNKNOWN: 'unknown'
        }
        
        return type_mapping.get(category, 'unknown'), confidence
    
    @classmethod
    def _create_obligations_with_classification(cls, amounts: List, dates: List, 
                                                counterparties: List, gst_numbers: List,
                                                pan_numbers: List, text: str) -> List[Dict[str, Any]]:
        """Create obligation dictionaries from extracted data with classification"""
        obligations = []
        
        # Match amounts with dates and counterparties based on proximity
        for amount in amounts:
            # Get context around the amount
            amount_context = cls._extract_context(text, amount['position'])
            
            obligation = {
                'amount': amount['value'],
                'counterparty': {'name': 'Unknown', 'type': 'unknown'},
                'note': f"Extracted from image: {amount['context']}",
                'context': amount_context
            }
            
            # Find closest date
            closest_date = None
            min_distance = float('inf')
            for date_info in dates:
                distance = abs(date_info['position'] - amount['position'])
                if distance < min_distance:
                    min_distance = distance
                    closest_date = date_info
            
            if closest_date and min_distance < 500:  # Within 500 characters
                obligation['due_date'] = closest_date['value']
            
            # Find closest counterparty
            closest_cp = None
            min_distance = float('inf')
            for cp in counterparties:
                distance = abs(cp['position'] - amount['position'])
                if distance < min_distance:
                    min_distance = distance
                    closest_cp = cp
            
            if closest_cp and min_distance < 500:
                obligation['counterparty']['name'] = closest_cp['name']
                # Add context from counterparty for classification
                obligation['counterparty']['context'] = closest_cp['context']
            
            # Classify counterparty type
            cp_name = obligation['counterparty']['name']
            cp_context = obligation.get('context', '')
            
            # Add counterparty context if available
            if 'counterparty' in obligation and 'context' in obligation['counterparty']:
                cp_context += " " + obligation['counterparty']['context']
            
            # Classify with available data
            classified_type, confidence = cls._classify_counterparty(
                cp_name, 
                cp_context,
                gst_numbers,
                pan_numbers
            )
            
            obligation['counterparty']['type'] = classified_type
            obligation['counterparty']['classification_confidence'] = confidence
            
            # Add invoice metadata if found
            invoice_match = re.search(r'invoice\s*(?:no|number)[:\s]*([A-Z0-9\-]+)', text, re.IGNORECASE)
            if invoice_match:
                obligation['invoice_number'] = invoice_match.group(1)
            
            obligations.append(obligation)
        
        return obligations
    
    @staticmethod
    def _get_confidence_score(text: str) -> float:
        """Calculate OCR confidence score based on text quality"""
        if not text:
            return 0.0
        
        # Check for common OCR artifacts
        text_length = len(text)
        words = text.split()
        
        # Check for presence of numbers (good indicator)
        has_numbers = bool(re.search(r'\d+', text))
        
        # Check for presence of common financial terms
        financial_terms = ['invoice', 'amount', 'total', 'due', 'date', 'payment', 'receipt']
        has_financial_terms = any(term in text.lower() for term in financial_terms)
        
        # Score based on various factors
        word_score = min(len(words) / 100, 1.0) * 0.4
        number_score = 0.3 if has_numbers else 0.0
        financial_score = 0.3 if has_financial_terms else 0.0
        
        confidence = word_score + number_score + financial_score
        
        return round(min(confidence, 1.0), 2)