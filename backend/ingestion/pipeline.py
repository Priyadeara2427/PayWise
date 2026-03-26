import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .csv_parser import CSVParser
from .ocr_parser import OCRParser
from .pdf_parser import PDFParser
from ..engine.normalizer import DataNormalizer
from ..engine.decision_engine import DecisionEngine
from ..models.obligation import Obligation, FinancialState, Decision, PartialPaymentTerms

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """Main ingestion pipeline for processing various input formats with intelligent classification and partial payment support"""
    
    SUPPORTED_FORMATS = {
        '.csv': CSVParser,
        '.xlsx': CSVParser,  # Excel support
        '.xls': CSVParser,   # Excel support
        '.jpg': OCRParser,
        '.jpeg': OCRParser,
        '.png': OCRParser,
        '.pdf': PDFParser
    }
    
    def __init__(self, mongo_client=None, enable_decisions: bool = True):
        """
        Initialize the ingestion pipeline
        
        Args:
            mongo_client: MongoDB client for storage (optional)
            enable_decisions: Whether to generate decisions for obligations
        """
        self.mongo_client = mongo_client
        self.normalizer = DataNormalizer()
        self.decision_engine = DecisionEngine() if enable_decisions else None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.enable_decisions = enable_decisions
    
    async def process_file(self, file_path: str, generate_decisions: bool = True) -> Dict[str, Any]:
        """
        Process a single file through the pipeline
        
        Args:
            file_path: Path to input file
            generate_decisions: Whether to generate decisions for obligations
        
        Returns:
            Dictionary with processing results
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported: {list(self.SUPPORTED_FORMATS.keys())}")
        
        logger.info(f"Processing file: {file_path} (type: {file_ext})")
        
        # Parse file based on format
        parser_class = self.SUPPORTED_FORMATS[file_ext]
        parsed_data = await self._parse_async(parser_class, file_path)
        
        # Log parsing results
        logger.info(f"Parsed {len(parsed_data.get('obligations', []))} obligations from {file_path}")
        logger.debug(f"Parsed data keys: {parsed_data.keys()}")
        
        # Check for partial payment info in parsed data
        if parsed_data.get('partial_payment_info'):
            logger.debug(f"Found partial payment terms: {parsed_data['partial_payment_info']}")
        
        # Normalize obligations with enhanced classification
        obligations = self.normalizer.normalize_batch(
            parsed_data.get('obligations', []),
            source_file=os.path.basename(file_path)
        )
        
        logger.info(f"Normalized {len(obligations)} obligations")
        
        # Log partial payment availability
        partial_count = sum(1 for o in obligations if o.partial_payment.accepts_partial)
        logger.info(f"Partial payment available for {partial_count}/{len(obligations)} obligations")
        
        # Generate decisions if enabled
        decisions = []
        if generate_decisions and self.decision_engine and obligations:
            decisions = self.decision_engine.make_decisions(obligations)
            logger.info(f"Generated decisions for {len(decisions)} obligations")
        
        # Create financial state
        cash_balance = parsed_data.get('cash_balance', 0.0)
        financial_state = self.normalizer.create_financial_state(obligations, cash_balance)
        
        # Add decisions to financial state if generated
        if decisions:
            financial_state.decisions = decisions
        
        # Store in MongoDB if client provided
        if self.mongo_client:
            await self._store_in_mongodb(financial_state, parsed_data, decisions)
        
        # Prepare response with enhanced data
        response = {
            'file': os.path.basename(file_path),
            'file_type': file_ext,
            'record_count': len(obligations),
            'financial_state': financial_state.dict(),
            'partial_payment_summary': {
                'total_obligations': len(obligations),
                'accept_partial_count': partial_count,
                'accept_partial_percentage': (partial_count / len(obligations) * 100) if obligations else 0,
                'minimum_partial_total': sum(o.partial_payment.minimum_partial_amount for o in obligations if o.partial_payment.accepts_partial)
            },
            'raw_data_summary': {
                'source_type': parsed_data.get('source_type', file_ext[1:]),
                'record_count': parsed_data.get('record_count', len(obligations)),
                'has_gst_numbers': bool(parsed_data.get('gst_numbers')),
                'has_pan_numbers': bool(parsed_data.get('pan_numbers')),
                'has_partial_terms': bool(parsed_data.get('partial_payment_info', {}).get('has_terms')),
                'tables_extracted': len(parsed_data.get('tables', []))
            },
            'processed_at': datetime.now().isoformat()
        }
        
        # Add decisions to response if generated
        if decisions:
            response['decisions'] = decisions
        
        # Add warnings if any
        warnings = []
        if len(obligations) == 0:
            warnings.append("No obligations were extracted from the file")
        if parsed_data.get('confidence', 1.0) < 0.5:
            warnings.append(f"Low OCR confidence: {parsed_data.get('confidence', 0)}")
        
        if warnings:
            response['warnings'] = warnings
        
        logger.info(f"Successfully processed {file_path}: {len(obligations)} obligations")
        
        return response
    
    async def _parse_async(self, parser_class, file_path: str) -> Dict[str, Any]:
        """Parse file asynchronously with error handling"""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                self.executor,
                parser_class.parse,
                file_path
            )
        except Exception as e:
            logger.error(f"Error parsing {file_path} with {parser_class.__name__}: {e}")
            raise
    
    async def _store_in_mongodb(self, financial_state: FinancialState, 
                                raw_data: Dict[str, Any], 
                                decisions: List[Dict[str, Any]] = None):
        """Store processed data in MongoDB with enhanced metadata including partial payment info"""
        if not self.mongo_client:
            return
        
        try:
            db = self.mongo_client['fintech_assistant']
            
            # Store financial state in a collection
            financial_collection = db['financial_states']
            financial_doc = financial_state.dict()
            financial_doc['raw_data_summary'] = {
                'source_type': raw_data.get('source_type'),
                'record_count': raw_data.get('record_count', 0),
                'has_tables': bool(raw_data.get('tables')),
                'has_partial_terms': bool(raw_data.get('partial_payment_info', {}).get('has_terms'))
            }
            financial_doc['partial_payment_info'] = raw_data.get('partial_payment_info', {})
            financial_doc['decisions'] = decisions or []
            financial_doc['created_at'] = datetime.now()
            
            await financial_collection.insert_one(financial_doc)
            logger.info(f"Stored financial state with {len(financial_state.obligations)} obligations")
            
            # Store each obligation as a separate document for easier querying
            obligations_collection = db['obligations']
            for i, obligation in enumerate(financial_state.obligations):
                doc = obligation.dict()
                doc['financial_state_id'] = financial_doc['_id']
                doc['decision'] = decisions[i] if decisions and i < len(decisions) else None
                doc['source_file'] = raw_data.get('source_file', 'unknown')
                doc['created_at'] = datetime.now()
                
                # Add classification metadata
                doc['classification'] = {
                    'type': obligation.counterparty.get('type'),
                    'confidence': obligation.counterparty.get('classification_confidence', 0)
                }
                
                # Add partial payment metadata
                doc['partial_payment_summary'] = {
                    'accepts_partial': obligation.partial_payment.accepts_partial,
                    'minimum_percentage': obligation.partial_payment.minimum_partial_pct,
                    'minimum_amount': obligation.partial_payment.minimum_partial_amount,
                    'suggested_percentage': obligation.partial_payment.suggested_pct,
                    'max_installments': obligation.partial_payment.max_installments,
                    'installment_days': obligation.partial_payment.installment_days
                }
                
                await obligations_collection.insert_one(doc)
            
            logger.info(f"Stored {len(financial_state.obligations)} obligations in database")
            
        except Exception as e:
            logger.error(f"Failed to store data in MongoDB: {e}")
            # Don't raise - we don't want to fail the whole pipeline if storage fails
    
    async def process_batch(self, file_paths: List[str], generate_decisions: bool = True) -> Dict[str, Any]:
        """Process multiple files concurrently with partial payment tracking"""
        tasks = [self.process_file(file_path, generate_decisions) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed = []
        failed = []
        
        for file_path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {file_path}: {result}")
                failed.append({
                    'file': file_path,
                    'error': str(result)
                })
            else:
                processed.append(result)
        
        # Aggregate partial payment statistics
        total_partial_available = 0
        total_obligations_with_partial = 0
        
        for p in processed:
            partial_summary = p.get('partial_payment_summary', {})
            total_partial_available += partial_summary.get('accept_partial_count', 0)
            total_obligations_with_partial += partial_summary.get('total_obligations', 0)
        
        # Return comprehensive results
        return {
            'successful': processed,
            'failed': failed,
            'total_files': len(file_paths),
            'successful_count': len(processed),
            'failed_count': len(failed),
            'total_obligations': sum(p.get('record_count', 0) for p in processed),
            'partial_payment_stats': {
                'total_obligations': total_obligations_with_partial,
                'partial_available_count': total_partial_available,
                'partial_available_percentage': (total_partial_available / total_obligations_with_partial * 100) if total_obligations_with_partial > 0 else 0
            },
            'processed_at': datetime.now().isoformat()
        }
    
    def save_to_json(self, results: Dict[str, Any], output_path: str, pretty: bool = True):
        """
        Save results to JSON file with optional pretty printing
        
        Args:
            results: Results to save
            output_path: Path to output file
            pretty: Whether to pretty print JSON
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(results, f, indent=2, default=str, ensure_ascii=False)
                else:
                    json.dump(results, f, default=str, ensure_ascii=False)
            logger.info(f"Results saved to {output_path} ({os.path.getsize(output_path)} bytes)")
        except Exception as e:
            logger.error(f"Failed to save results to {output_path}: {e}")
            raise
    
    async def process_directory(self, directory_path: str, extensions: List[str] = None) -> Dict[str, Any]:
        """
        Process all supported files in a directory
        
        Args:
            directory_path: Path to directory
            extensions: List of file extensions to process (None for all supported)
        
        Returns:
            Processing results
        """
        if not os.path.isdir(directory_path):
            raise ValueError(f"Directory not found: {directory_path}")
        
        # Get all files in directory
        all_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_ext = Path(file).suffix.lower()
                if file_ext in self.SUPPORTED_FORMATS:
                    if extensions is None or file_ext in extensions:
                        all_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(all_files)} files to process in {directory_path}")
        
        # Process files
        results = await self.process_batch(all_files)
        
        # Add directory info
        results['directory'] = directory_path
        results['files_processed'] = len(all_files)
        
        return results
    
    def get_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics from processing results including partial payment info
        
        Args:
            results: Results from process_batch or process_directory
        
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_files': results.get('total_files', 0),
            'successful_files': results.get('successful_count', 0),
            'failed_files': results.get('failed_count', 0),
            'total_obligations': results.get('total_obligations', 0),
            'by_type': {},
            'by_priority': {},
            'partial_payment': {
                'total_available': 0,
                'by_type': {}
            }
        }
        
        # Analyze successful results
        for result in results.get('successful', []):
            financial_state = result.get('financial_state', {})
            partial_summary = result.get('partial_payment_summary', {})
            
            # Track partial payment stats
            stats['partial_payment']['total_available'] += partial_summary.get('accept_partial_count', 0)
            
            # Count by counterparty type with partial info
            for obligation in financial_state.get('obligations', []):
                cp_type = obligation.get('counterparty', {}).get('type', 'unknown')
                stats['by_type'][cp_type] = stats['by_type'].get(cp_type, 0) + 1
                
                # Track partial by type
                partial = obligation.get('partial_payment', {})
                if partial.get('accepts_partial', False):
                    if cp_type not in stats['partial_payment']['by_type']:
                        stats['partial_payment']['by_type'][cp_type] = 0
                    stats['partial_payment']['by_type'][cp_type] += 1
            
            # Count by decision priority
            for decision in result.get('decisions', []):
                priority = decision.get('priority', 'unknown')
                stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
        
        return stats
    
    def get_partial_payment_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a detailed report on partial payment availability
        
        Args:
            results: Results from process_batch or process_directory
        
        Returns:
            Partial payment report
        """
        report = {
            'summary': {
                'total_obligations': 0,
                'accept_partial': 0,
                'reject_partial': 0,
                'by_type': {}
            },
            'recommendations': []
        }
        
        for result in results.get('successful', []):
            for obligation in result.get('financial_state', {}).get('obligations', []):
                cp_type = obligation.get('counterparty', {}).get('type', 'unknown')
                partial = obligation.get('partial_payment', {})
                
                report['summary']['total_obligations'] += 1
                
                if partial.get('accepts_partial', False):
                    report['summary']['accept_partial'] += 1
                    if cp_type not in report['summary']['by_type']:
                        report['summary']['by_type'][cp_type] = {'accept': 0, 'reject': 0}
                    report['summary']['by_type'][cp_type]['accept'] += 1
                    
                    # Add recommendation for high-value partial payments
                    if obligation.get('amount', 0) > 50000:
                        report['recommendations'].append({
                            'party': obligation.get('counterparty', {}).get('name'),
                            'type': cp_type,
                            'amount': obligation.get('amount'),
                            'minimum_payment': partial.get('minimum_partial_amount', 0),
                            'suggestion': f"Consider partial payment of at least {partial.get('minimum_partial_pct', 0)}% (₹{partial.get('minimum_partial_amount', 0):,.2f})"
                        })
                else:
                    report['summary']['reject_partial'] += 1
                    if cp_type not in report['summary']['by_type']:
                        report['summary']['by_type'][cp_type] = {'accept': 0, 'reject': 0}
                    report['summary']['by_type'][cp_type]['reject'] += 1
        
        # Calculate percentages
        if report['summary']['total_obligations'] > 0:
            report['summary']['accept_percentage'] = (report['summary']['accept_partial'] / report['summary']['total_obligations']) * 100
            report['summary']['reject_percentage'] = (report['summary']['reject_partial'] / report['summary']['total_obligations']) * 100
        
        return report
    
    def close(self):
        """Close the thread pool executor"""
        self.executor.shutdown(wait=True)
        logger.info("Ingestion pipeline closed")