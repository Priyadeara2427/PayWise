import fitz  # PyMuPDF
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pdfplumber
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.counterparty_classifier import CounterpartyClassifier, CounterpartyCategory

logger = logging.getLogger(__name__)

class PDFParser:
    """Enhanced PDF parser with multiple extraction methods, intelligent classification, and partial payment extraction"""
    
    @classmethod
    def parse(cls, file_path: str, use_pdfplumber: bool = True) -> Dict[str, Any]:
        """
        Parse PDF and extract structured data with intelligent classification and partial payment terms
        
        Args:
            file_path: Path to PDF file
            use_pdfplumber: Use pdfplumber for better table extraction
        
        Returns:
            Dictionary with extracted data
        """
        try:
            extracted_data = {
                'raw_text': '',
                'pages': [],
                'tables': [],
                'obligations': [],
                'gst_numbers': [],
                'pan_numbers': [],
                'partial_payment_info': {},
                'source_type': 'pdf'
            }
            
            # Extract text and tables
            if use_pdfplumber:
                text, tables = cls._extract_with_pdfplumber(file_path)
                extracted_data['tables'] = tables
            else:
                text = cls._extract_with_pymupdf(file_path)
            
            extracted_data['raw_text'] = text
            
            # Extract GST and PAN numbers
            extracted_data['gst_numbers'] = cls._extract_gst_numbers(text)
            extracted_data['pan_numbers'] = cls._extract_pan_numbers(text)
            
            # Extract partial payment information
            extracted_data['partial_payment_info'] = cls._extract_partial_payment_info(text)
            
            # Parse text to extract obligations with classification and partial terms
            obligations = cls._parse_text_to_obligations(
                text, 
                extracted_data['gst_numbers'],
                extracted_data['pan_numbers'],
                extracted_data['partial_payment_info']
            )
            extracted_data['obligations'] = obligations
            extracted_data['record_count'] = len(obligations)
            
            # Extract metadata
            metadata = cls._extract_metadata(file_path)
            extracted_data['metadata'] = metadata
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise
    
    @classmethod
    def _extract_partial_payment_info(cls, text: str) -> Dict[str, Any]:
        """Extract partial payment related information from PDF text"""
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
            r'pay\s*(\d+)%\s*now',
            r'(\d+)%\s*deposit'
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
            r'at least\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'minimum\s*payment\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)'
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
            r'(\d+)\s*equal\s*payments?',
            r'(\d+)\s*monthly\s*payments?'
        ]
        
        for pattern in install_patterns:
            match = re.search(pattern, text_lower)
            if match:
                info['max_installments'] = int(match.group(1))
                info['has_terms'] = True
                break
        
        # Look for payment terms like "Net 30", "Net 45"
        net_match = re.search(r'net\s*(\d+)', text_lower)
        if net_match:
            info['installment_days'] = int(net_match.group(1))
            info['has_terms'] = True
        
        # Look for discount terms
        discount_match = re.search(r'(\d+)%\s*discount\s*if\s*paid\s*within\s*(\d+)\s*days', text_lower)
        if discount_match:
            info['discount_pct'] = float(discount_match.group(1))
            info['discount_days'] = int(discount_match.group(2))
            info['has_terms'] = True
        
        # Store the terms text for reference
        terms_sentences = []
        term_keywords = ['terms', 'payment terms', 'partial', 'installment', 'net', 'due', 'discount']
        sentences = re.split(r'[.!?\n]', text)
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in term_keywords):
                terms_sentences.append(sentence.strip())
        
        if terms_sentences:
            info['terms_text'] = ' '.join(terms_sentences[:5])
        
        return info
    
    @staticmethod
    def _extract_with_pymupdf(file_path: str) -> str:
        """Extract text using PyMuPDF with better layout preservation"""
        doc = fitz.open(file_path)
        full_text = ""
        
        for page_num, page in enumerate(doc):
            # Try different extraction methods
            text_methods = [
                page.get_text("text"),      # Simple text
                page.get_text("words"),     # Word-level with positions
                page.get_text("blocks")     # Block-level with positions
            ]
            
            # Use the longest text (usually most complete)
            page_text = max(text_methods, key=lambda x: len(str(x)))
            
            if isinstance(page_text, list):
                # Convert to string if it's a list
                page_text = ' '.join([str(item) for item in page_text])
            
            full_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        
        doc.close()
        return full_text
    
    @staticmethod
    def _extract_with_pdfplumber(file_path: str) -> tuple:
        """Extract text and tables using pdfplumber with better extraction"""
        text = ""
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text with better layout
                page_text = page.extract_text(layout=True) or ""
                text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                
                # Extract tables with better detection
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table and len(table) > 1:  # At least header + one row
                        # Clean table data
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                            if any(cleaned_row):  # Skip empty rows
                                cleaned_table.append(cleaned_row)
                        
                        if cleaned_table:
                            tables.append({
                                'page': page_num + 1,
                                'data': cleaned_table,
                                'rows': len(cleaned_table),
                                'columns': len(cleaned_table[0]) if cleaned_table else 0
                            })
        
        return text, tables
    
    @classmethod
    def _get_partial_terms_for_type(cls, counterparty_type: str, amount: float, 
                                     pdf_terms: Dict) -> Dict[str, Any]:
        """Get partial payment terms based on counterparty type and PDF extraction"""
        
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
        
        # Override with PDF-extracted terms if present
        accepts_partial = defaults['accepts_partial']
        if pdf_terms.get('has_terms'):
            accepts_partial = pdf_terms.get('accepts_partial', accepts_partial)
        
        min_pct = pdf_terms.get('minimum_pct', defaults['min_pct'])
        min_amount = pdf_terms.get('minimum_amount', defaults['min_amount'])
        
        # Adjust minimum amount if it's higher than the obligation amount
        if min_amount > amount:
            min_amount = amount * (min_pct / 100)
        
        return {
            'accepts_partial': accepts_partial,
            'minimum_partial_pct': min_pct,
            'minimum_partial_amount': min_amount,
            'suggested_pct': min(max(min_pct, 30), 70),
            'max_installments': pdf_terms.get('max_installments', defaults['max_inst']),
            'installment_days': pdf_terms.get('installment_days', defaults['days']),
            'notes': pdf_terms.get('terms_text', defaults.get('notes', '')),
            'history': []
        }
    
    @classmethod
    def _parse_text_to_obligations(cls, text: str, gst_numbers: List = None, 
                                   pan_numbers: List = None, 
                                   pdf_terms: Dict = None) -> List[Dict[str, Any]]:
        """Parse text to extract obligation information with intelligent classification and partial terms"""
        obligations = []
        lines = text.split('\n')
        
        # Enhanced patterns for better extraction
        amount_pattern = r'(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{2})?)\s*(?:Rs\.?|INR|₹)?'
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        
        # Track if we've found table headers
        in_table = False
        table_headers = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Detect table headers
            if any(keyword in line_stripped.lower() for keyword in ['amount', 'due date', 'description', 'invoice']):
                if 'amount' in line_stripped.lower() and 'date' in line_stripped.lower():
                    in_table = True
                    table_headers = [h.strip().lower() for h in re.split(r'\s{2,}', line_stripped)]
                    continue
            
            # Extract amounts and dates
            amounts = re.findall(amount_pattern, line_stripped)
            dates = re.findall(date_pattern, line_stripped)
            
            if amounts and dates:
                # Process each amount found
                for amount_str in amounts:
                    try:
                        # Clean amount string
                        amount_str_clean = amount_str.replace(',', '')
                        amount = float(amount_str_clean)
                        
                        # Filter out very small amounts (likely page numbers)
                        if amount < 10:
                            continue
                        
                        # Get context around the line
                        context = cls._get_context(lines, i, window=3)
                        
                        # Extract counterparty name
                        counterparty_name, counterparty_context = cls._extract_counterparty_from_line(
                            line_stripped, context
                        )
                        
                        # Determine due date
                        due_date = cls._parse_date(dates[0]) if dates else None
                        
                        # Determine if payable or receivable
                        txn_type = cls._determine_transaction_type(line_stripped, context)
                        
                        # Classify counterparty type
                        classified_type, confidence = cls._classify_counterparty(
                            counterparty_name,
                            context,
                            gst_numbers,
                            pan_numbers,
                            txn_type
                        )
                        
                        # Get partial payment terms
                        partial_terms = cls._get_partial_terms_for_type(
                            classified_type, amount, pdf_terms or {}
                        )
                        
                        # Build obligation
                        obligation = {
                            'amount': amount,
                            'due_date': due_date,
                            'counterparty': {
                                'name': counterparty_name,
                                'type': classified_type,
                                'classification_confidence': confidence
                            },
                            'partial_payment': partial_terms,
                            'source_line': line_stripped,
                            'line_number': i + 1,
                            'context': context,
                            'txn_type': txn_type
                        }
                        
                        # Add metadata if available
                        if 'invoice' in line_stripped.lower():
                            invoice_match = re.search(r'invoice\s*(?:no|number)[:\s]*([A-Z0-9\-]+)', line_stripped, re.IGNORECASE)
                            if invoice_match:
                                obligation['invoice_number'] = invoice_match.group(1)
                        
                        # Extract payment terms from line
                        payment_terms_match = re.search(r'payment\s*terms?[:\s]+([^.\n]+)', line_stripped, re.IGNORECASE)
                        if payment_terms_match:
                            obligation['payment_terms'] = payment_terms_match.group(1).strip()
                        
                        obligations.append(obligation)
                        
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse amount: {amount_str}, error: {e}")
                        continue
        
        return obligations
    
    @classmethod
    def _get_context(cls, lines: List[str], current_idx: int, window: int = 3) -> str:
        """Get context around the current line"""
        start = max(0, current_idx - window)
        end = min(len(lines), current_idx + window + 1)
        context_lines = lines[start:end]
        return '\n'.join(context_lines)
    
    @staticmethod
    def _extract_counterparty_from_line(line: str, context: str) -> Tuple[str, str]:
        """Extract counterparty name from text line with context"""
        combined_text = f"{line} {context}"
        
        # Patterns for different counterparty types
        patterns = [
            # Business/Company patterns
            r'\b(?:to|from|vendor|customer|party|payee|payer|supplier|client)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Enterprises|Industries|Trading|Fabrics|Corp|Ltd|LLC|Technologies|Solutions|Services|Company)))\b',
            r'(?:bill\s*to|ship\s*to|invoice\s*to|billed\s*to)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Government/Tax patterns
            r'\b(?:GST|Tax|Income Tax|Government|Govt|Department)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Personal patterns
            r'(?:paid\s*to|received\s*from|payment\s*to)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            
            # Name patterns with titles
            r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2 and name.lower() not in ['date', 'amount', 'total', 'due', 'invoice']:
                    return name, combined_text
        
        # If no pattern matches, try to extract potential company name
        company_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,})\b'
        match = re.search(company_pattern, line)
        if match:
            name = match.group(1).strip()
            if len(name) > 5:  # Reasonable length for company name
                return name, combined_text
        
        return 'Unknown', combined_text
    
    @staticmethod
    def _determine_transaction_type(line: str, context: str) -> str:
        """Determine if transaction is payable or receivable"""
        combined = f"{line} {context}".lower()
        
        payable_keywords = ['payable', 'vendor', 'supplier', 'purchase', 'bill', 'expense', 'due to']
        receivable_keywords = ['receivable', 'customer', 'client', 'sale', 'income', 'due from']
        
        if any(keyword in combined for keyword in payable_keywords):
            return 'payable'
        elif any(keyword in combined for keyword in receivable_keywords):
            return 'receivable'
        
        return 'unknown'
    
    @classmethod
    def _classify_counterparty(cls, name: str, context: str, gst_numbers: List = None,
                               pan_numbers: List = None, txn_type: str = None) -> Tuple[str, float]:
        """
        Classify counterparty type using intelligent rules
        
        Args:
            name: Counterparty name
            context: Additional context from the PDF
            gst_numbers: List of extracted GST numbers
            pan_numbers: List of extracted PAN numbers
            txn_type: Transaction type (payable/receivable)
        
        Returns:
            Tuple of (type_string, confidence_score)
        """
        # Check for GST numbers in context
        if gst_numbers:
            for gst in gst_numbers:
                if gst['gstin'] in context:
                    return 'tax_authority', 0.95
        
        # Check for PAN numbers
        if pan_numbers:
            for pan in pan_numbers:
                if pan['pan'] in context:
                    return 'vendor', 0.9
        
        # Use transaction type as hint
        if txn_type == 'payable':
            # Payables are typically vendors, tax authorities, utilities
            if any(word in context.lower() for word in ['tax', 'gst', 'govt']):
                return 'tax_authority', 0.85
            elif any(word in context.lower() for word in ['electricity', 'water', 'gas']):
                return 'utility', 0.85
            else:
                return 'vendor', 0.8
        elif txn_type == 'receivable':
            return 'customer', 0.8
        
        # Use intelligent classifier
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
    
    @staticmethod
    def _parse_date(date_str: str):
        """Parse date string with multiple format support"""
        formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
            '%d/%m/%y', '%m/%d/%y', '%d-%m-%y', '%m-%d-%y',
            '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def _extract_metadata(file_path: str) -> Dict[str, Any]:
        """Extract PDF metadata"""
        doc = fitz.open(file_path)
        metadata = doc.metadata
        doc.close()
        
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'keywords': metadata.get('keywords', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', '')
        }