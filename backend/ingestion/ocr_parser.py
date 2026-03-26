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
    """Enhanced OCR parser with preprocessing, intelligent classification, and partial payment extraction"""
    
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
            
            # Extract partial payment information
            partial_payment_info = cls._extract_partial_payment_info(text)
            
            # Parse into obligations with classification and partial terms
            obligations = cls._create_obligations_with_classification(
                amounts, dates, counterparties, gst_numbers, pan_numbers, 
                partial_payment_info, text
            )
            
            return {
                'raw_text': text,
                'amounts': amounts,
                'dates': dates,
                'counterparties': counterparties,
                'gst_numbers': gst_numbers,
                'pan_numbers': pan_numbers,
                'partial_payment_info': partial_payment_info,
                'obligations': obligations,
                'source_type': 'image',
                'record_count': len(obligations),
                'confidence': cls._get_confidence_score(text)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse image {file_path}: {e}")
            raise
    
    @classmethod
    def _extract_partial_payment_info(cls, text: str) -> Dict[str, Any]:
        """Extract partial payment related information from text"""
        text_lower = text.lower()
        
        info = {
            'accepts_partial': True,
            'minimum_pct': 50.0,
            'minimum_amount': 5000.0,
            'max_installments': 1,
            'installment_days': 15,
            'has_terms': False,
            'terms_text': ''
        }
        
        # Check for partial payment indicators
        if 'no partial' in text_lower or 'full payment only' in text_lower:
            info['accepts_partial'] = False
        elif 'partial accepted' in text_lower or 'partial payment allowed' in text_lower:
            info['accepts_partial'] = True
        
        # Look for percentage requirements
        pct_patterns = [
            r'min(?:imum)?\s*(\d+)%',
            r'at least\s*(\d+)%',
            r'(\d+)%\s*minimum',
            r'pay\s*(\d+)%\s*now'
        ]
        
        for pattern in pct_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['minimum_pct'] = float(match.group(1))
                info['has_terms'] = True
                break
        
        # Look for minimum amount requirements
        amount_patterns = [
            r'min(?:imum)?\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'minimum amount\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'at least\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount_str = match.group(1).replace(',', '')
                info['minimum_amount'] = float(amount_str)
                info['has_terms'] = True
                break
        
        # Look for installment information
        install_patterns = [
            r'(\d+)\s*installments?',
            r'pay in (\d+)\s*parts?',
            r'(\d+)\s*equal\s*payments?'
        ]
        
        for pattern in install_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['max_installments'] = int(match.group(1))
                info['has_terms'] = True
                break
        
        # Look for payment terms like "Net 30"
        net_match = re.search(r'net\s*(\d+)', text_lower)
        if net_match:
            info['installment_days'] = int(net_match.group(1))
            info['has_terms'] = True
        
        # Store the terms text for reference
        terms_sentences = []
        term_keywords = ['terms', 'payment terms', 'partial', 'installment', 'net', 'due']
        sentences = re.split(r'[.!?\n]', text)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in term_keywords):
                terms_sentences.append(sentence.strip())
        
        if terms_sentences:
            info['terms_text'] = ' '.join(terms_sentences[:3])
        
        return info
    
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
    def _classify_counterparty(cls, name: str, context: str, gst_numbers: List = None, 
                               pan_numbers: List = None) -> Tuple[str, float]:
        """Classify counterparty type using intelligent rules"""
        # Check for GST numbers nearby
        if gst_numbers:
            for gst in gst_numbers:
                if abs(gst['position'] - len(context)) < 500:
                    if any(word in context.lower() for word in ['tax', 'gst', 'invoice']):
                        return 'tax_authority', 0.9
        
        # Check for PAN numbers
        if pan_numbers:
            for pan in pan_numbers:
                if abs(pan['position'] - len(context)) < 500:
                    return 'vendor', 0.85
        
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
    def _get_partial_terms_for_type(cls, counterparty_type: str, amount: float, 
                                     ocr_terms: Dict) -> Dict[str, Any]:
        """Get partial payment terms based on counterparty type and OCR extraction"""
        
        # Default terms by type
        type_defaults = {
            'vendor': {'accepts_partial': True, 'min_pct': 50, 'min_amount': 5000, 'max_inst': 2, 'days': 15},
            'customer': {'accepts_partial': True, 'min_pct': 30, 'min_amount': 1000, 'max_inst': 3, 'days': 10},
            'tax_authority': {'accepts_partial': False, 'min_pct': 100, 'min_amount': amount, 'max_inst': 1, 'days': 0},
            'government': {'accepts_partial': False, 'min_pct': 100, 'min_amount': amount, 'max_inst': 1, 'days': 0},
            'bank': {'accepts_partial': False, 'min_pct': 100, 'min_amount': amount, 'max_inst': 1, 'days': 0},
            'employee': {'accepts_partial': False, 'min_pct': 100, 'min_amount': amount, 'max_inst': 1, 'days': 0},
            'utility': {'accepts_partial': True, 'min_pct': 70, 'min_amount': 500, 'max_inst': 2, 'days': 7},
            'rent': {'accepts_partial': True, 'min_pct': 60, 'min_amount': 5000, 'max_inst': 2, 'days': 15},
            'friend': {'accepts_partial': True, 'min_pct': 20, 'min_amount': 1000, 'max_inst': 4, 'days': 7},
            'family': {'accepts_partial': True, 'min_pct': 10, 'min_amount': 500, 'max_inst': 6, 'days': 7},
            'insurance': {'accepts_partial': False, 'min_pct': 100, 'min_amount': amount, 'max_inst': 1, 'days': 0},
            'investment': {'accepts_partial': True, 'min_pct': 50, 'min_amount': 5000, 'max_inst': 3, 'days': 15},
            'charity': {'accepts_partial': True, 'min_pct': 25, 'min_amount': 1000, 'max_inst': 4, 'days': 30},
            'unknown': {'accepts_partial': True, 'min_pct': 50, 'min_amount': 5000, 'max_inst': 2, 'days': 15}
        }
        
        defaults = type_defaults.get(counterparty_type, type_defaults['unknown'])
        
        # Override with OCR-extracted terms if present
        accepts_partial = defaults['accepts_partial']
        if ocr_terms.get('has_terms'):
            accepts_partial = ocr_terms.get('accepts_partial', accepts_partial)
        
        min_pct = ocr_terms.get('minimum_pct', defaults['min_pct'])
        min_amount = ocr_terms.get('minimum_amount', defaults['min_amount'])
        
        # Adjust minimum amount if it's higher than the obligation amount
        if min_amount > amount:
            min_amount = amount * (min_pct / 100)
        
        return {
            'accepts_partial': accepts_partial,
            'minimum_partial_pct': min_pct,
            'minimum_partial_amount': min_amount,
            'suggested_pct': min(max(min_pct, 30), 70),
            'max_installments': ocr_terms.get('max_installments', defaults['max_inst']),
            'installment_days': ocr_terms.get('installment_days', defaults['days']),
            'notes': ocr_terms.get('terms_text', defaults.get('notes', '')),
            'history': []
        }
    
    @classmethod
    def _create_obligations_with_classification(cls, amounts: List, dates: List, 
                                                counterparties: List, gst_numbers: List,
                                                pan_numbers: List, partial_info: Dict,
                                                text: str) -> List[Dict[str, Any]]:
        """Create obligation dictionaries from extracted data with classification and partial terms"""
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
            
            if closest_date and min_distance < 500:
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
                obligation['counterparty']['context'] = closest_cp['context']
            
            # Classify counterparty type
            cp_name = obligation['counterparty']['name']
            cp_context = obligation.get('context', '')
            
            if 'counterparty' in obligation and 'context' in obligation['counterparty']:
                cp_context += " " + obligation['counterparty']['context']
            
            classified_type, confidence = cls._classify_counterparty(
                cp_name, cp_context, gst_numbers, pan_numbers
            )
            
            obligation['counterparty']['type'] = classified_type
            obligation['counterparty']['classification_confidence'] = confidence
            
            # Get partial payment terms based on type and OCR extraction
            partial_terms = cls._get_partial_terms_for_type(
                classified_type, amount['value'], partial_info
            )
            obligation['partial_payment'] = partial_terms
            
            # Add invoice metadata if found
            invoice_match = re.search(r'invoice\s*(?:no|number)[:\s]*([A-Z0-9\-]+)', text, re.IGNORECASE)
            if invoice_match:
                obligation['invoice_number'] = invoice_match.group(1)
            
            # Add payment terms from text if found
            payment_terms_match = re.search(r'payment\s*terms?[:\s]+([^.\n]+)', text, re.IGNORECASE)
            if payment_terms_match:
                obligation['payment_terms'] = payment_terms_match.group(1).strip()
            
            obligations.append(obligation)
        
        return obligations
    
    @staticmethod
    def _get_confidence_score(text: str) -> float:
        """Calculate OCR confidence score based on text quality"""
        if not text:
            return 0.0
        
        words = text.split()
        has_numbers = bool(re.search(r'\d+', text))
        financial_terms = ['invoice', 'amount', 'total', 'due', 'date', 'payment', 'receipt']
        has_financial_terms = any(term in text.lower() for term in financial_terms)
        
        word_score = min(len(words) / 100, 1.0) * 0.4
        number_score = 0.3 if has_numbers else 0.0
        financial_score = 0.3 if has_financial_terms else 0.0
        
        confidence = word_score + number_score + financial_score
        return round(min(confidence, 1.0), 2)