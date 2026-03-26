#!/usr/bin/env python
"""
Test script for the Fintech Decision Assistant Parser
"""

import os
import sys
import json
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import parsers
from backend.ingestion.csv_parser import CSVParser
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.ocr_parser import OCRParser
from backend.engine.normalizer import DataNormalizer
from backend.models.obligation import Obligation
from backend.ingestion.pipeline import IngestionPipeline

def create_sample_csv():
    """Create a sample CSV file with FUTURE DATES for testing"""
    # Calculate future dates (from today)
    today = datetime.today().date()
    future_dates = {
        'pay1': today + timedelta(days=5),   # 5 days from now
        'pay2': today + timedelta(days=10),  # 10 days from now
        'pay3': today + timedelta(days=15),  # 15 days from now
        'rec1': today + timedelta(days=12),  # 12 days from now
        'rec2': today + timedelta(days=20),  # 20 days from now
    }
    
    csv_content = f"""counterparty,amount,due_date,type,description,payment_date
Raj Fabrics,45000,{future_dates['pay1']},payable,Invoice INV-001,
Tech Solutions Pvt Ltd,25000,{future_dates['pay2']},payable,Software license,
Retail Store,15000,{future_dates['rec1']},receivable,Sales invoice,
ABC Enterprises,75000,{future_dates['pay3']},payable,Equipment purchase,
XYZ Corp,35000,{future_dates['rec2']},receivable,Consulting fees,
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(csv_content)
        return f.name

def create_sample_pdf():
    """Create a sample PDF with FUTURE DATES for testing"""
    today = datetime.today().date()
    future_dates = {
        'pay1': today + timedelta(days=5),
        'pay2': today + timedelta(days=10),
        'rec1': today + timedelta(days=12),
    }
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        print("   ⚠ reportlab not installed, using simple PDF creation")
        import fitz
        pdf_path = tempfile.mktemp(suffix='.pdf')
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 750), "INVOICE", fontsize=12)
        page.insert_text((50, 700), f"Vendor: Raj Fabrics", fontsize=10)
        page.insert_text((50, 680), f"Amount: ₹45,000.00", fontsize=10)
        page.insert_text((50, 660), f"Due Date: {future_dates['pay1'].strftime('%d/%m/%Y')}", fontsize=10)
        page.insert_text((50, 640), "Invoice Number: INV-001", fontsize=10)
        page.insert_text((50, 600), "Tech Solutions", fontsize=10)
        page.insert_text((50, 580), f"Amount: ₹25,000.00", fontsize=10)
        page.insert_text((50, 560), f"Due Date: {future_dates['pay2'].strftime('%d/%m/%Y')}", fontsize=10)
        doc.save(pdf_path)
        doc.close()
        return pdf_path
    
    pdf_path = tempfile.mktemp(suffix='.pdf')
    c = canvas.Canvas(pdf_path, pagesize=letter)
    
    c.drawString(100, 750, "INVOICE")
    c.drawString(100, 700, f"Vendor: Raj Fabrics")
    c.drawString(100, 680, f"Amount: ₹45,000.00")
    c.drawString(100, 660, f"Due Date: {future_dates['pay1'].strftime('%d/%m/%Y')}")
    c.drawString(100, 640, "Invoice Number: INV-001")
    
    c.drawString(100, 600, "Tech Solutions")
    c.drawString(100, 580, f"Amount: ₹25,000.00")
    c.drawString(100, 560, f"Due Date: {future_dates['pay2'].strftime('%d/%m/%Y')}")
    
    c.save()
    return pdf_path

def create_sample_image():
    """Create a sample image with FUTURE DATES for testing"""
    from PIL import Image, ImageDraw, ImageFont
    
    today = datetime.today().date()
    future_date = (today + timedelta(days=7)).strftime('%d %B %Y')
    
    # Create a larger image with better resolution
    img = Image.new('RGB', (1200, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a larger font
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw text with future dates
    draw.text((50, 50), "INVOICE", fill='black', font=font)
    draw.text((50, 120), "Vendor: Raj Fabrics", fill='black', font=font_small)
    draw.text((50, 170), "Amount: INR 45,000.00", fill='black', font=font_small)
    draw.text((50, 220), f"Due Date: {future_date}", fill='black', font=font_small)
    draw.text((50, 270), "Invoice Number: INV-001", fill='black', font=font_small)
    
    # Add another vendor
    draw.text((50, 350), "Tech Solutions", fill='black', font=font_small)
    draw.text((50, 400), "Amount: INR 25,000.00", fill='black', font=font_small)
    draw.text((50, 450), f"Due Date: {future_date}", fill='black', font=font_small)
    
    # Add a simple table
    draw.rectangle([50, 500, 1100, 550], outline='black')
    draw.text((60, 510), "Item", fill='black', font=font_small)
    draw.text((400, 510), "Amount", fill='black', font=font_small)
    draw.text((700, 510), "Due Date", fill='black', font=font_small)
    draw.text((60, 530), "Services", fill='black', font=font_small)
    draw.text((400, 530), "45,000", fill='black', font=font_small)
    draw.text((700, 530), future_date, fill='black', font=font_small)
    
    img_path = tempfile.mktemp(suffix='.png')
    img.save(img_path, dpi=(300, 300))
    return img_path

def test_csv_parser():
    """Test CSV parser"""
    print("\n" + "="*50)
    print("Testing CSV Parser")
    print("="*50)
    
    csv_file = create_sample_csv()
    print(f"📄 Testing with file: {csv_file}")
    
    try:
        parsed_data = CSVParser.parse(csv_file)
        print(f"✅ CSV parsed successfully!")
        print(f"   - Cash balance: ₹{parsed_data.get('cash_balance', 0)}")
        print(f"   - Obligations found: {len(parsed_data.get('obligations', []))}")
        
        # Display first obligation
        if parsed_data.get('obligations'):
            first_obligation = parsed_data['obligations'][0]
            print(f"\n   Sample obligation:")
            print(f"   - Counterparty: {first_obligation.get('counterparty', {}).get('name')}")
            print(f"   - Amount: ₹{first_obligation.get('amount')}")
            print(f"   - Due Date: {first_obligation.get('due_date')}")
        
        return parsed_data
        
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)

def test_pdf_parser():
    """Test PDF parser"""
    print("\n" + "="*50)
    print("Testing PDF Parser")
    print("="*50)
    
    pdf_file = create_sample_pdf()
    print(f"📄 Testing with file: {pdf_file}")
    
    try:
        parsed_data = PDFParser.parse(pdf_file)
        print(f"✅ PDF parsed successfully!")
        print(f"   - Text length: {len(parsed_data.get('raw_text', ''))} characters")
        print(f"   - Obligations found: {len(parsed_data.get('obligations', []))}")
        print(f"   - Pages processed: {len(parsed_data.get('pages', []))}")
        
        if parsed_data.get('obligations'):
            first_obligation = parsed_data['obligations'][0]
            print(f"\n   Sample obligation:")
            print(f"   - Amount: ₹{first_obligation.get('amount')}")
            print(f"   - Due Date: {first_obligation.get('due_date')}")
        
        return parsed_data
        
    except Exception as e:
        print(f"❌ PDF parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(pdf_file):
            os.unlink(pdf_file)

def test_ocr_parser():
    """Test OCR parser"""
    print("\n" + "="*50)
    print("Testing OCR Parser")
    print("="*50)
    
    image_file = create_sample_image()
    print(f"📄 Testing with file: {image_file}")
    
    try:
        parsed_data = OCRParser.parse(image_file)
        print(f"✅ OCR parsing successful!")
        print(f"   - Text extracted: {len(parsed_data.get('raw_text', ''))} characters")
        print(f"   - Amounts found: {len(parsed_data.get('amounts', []))}")
        print(f"   - Dates found: {len(parsed_data.get('dates', []))}")
        print(f"   - Confidence: {parsed_data.get('confidence', 0)}")
        
        if parsed_data.get('raw_text'):
            print(f"\n   Extracted text preview:")
            preview = parsed_data['raw_text'][:300].replace('\n', ' ')
            print(f"   {preview}...")
        
        if parsed_data.get('amounts'):
            print(f"\n   Extracted amounts:")
            for amount in parsed_data['amounts'][:3]:
                print(f"   - ₹{amount.get('value')}: {amount.get('context')}")
        
        return parsed_data
        
    except Exception as e:
        print(f"❌ OCR parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(image_file):
            os.unlink(image_file)

def test_normalizer():
    """Test data normalizer"""
    print("\n" + "="*50)
    print("Testing Data Normalizer")
    print("="*50)
    
    today = datetime.today().date()
    future_dates = {
        'pay1': today + timedelta(days=5),
        'pay2': today + timedelta(days=10),
    }
    
    raw_data = {
        "obligations": [
            {
                "amount": "45000",
                "due_date": future_dates['pay1'].isoformat(),
                "counterparty": {"name": "Raj Fabrics", "type": "unknown"},
                "note": "Sample obligation"
            },
            {
                "amount": "25000",
                "due_date": future_dates['pay2'].isoformat(),
                "counterparty": {"name": "Tech Solutions", "type": "vendor"}
            }
        ],
        "cash_balance": 100000
    }
    
    print(f"📊 Testing normalization of {len(raw_data['obligations'])} obligations")
    
    try:
        normalizer = DataNormalizer()
        
        obligations = normalizer.normalize_batch(
            raw_data['obligations'],
            source_file="test.csv"
        )
        
        print(f"✅ Normalization successful!")
        print(f"   - Processed: {len(obligations)} obligations")
        
        for i, ob in enumerate(obligations[:2]):
            print(f"\n   Obligation {i+1}:")
            print(f"   - ID: {ob.transaction_id}")
            print(f"   - Counterparty: {ob.counterparty.get('name')}")
            print(f"   - Amount: ₹{ob.amount}")
            print(f"   - Due Date: {ob.due_date}")
            print(f"   - Days Late: {ob.days_late}")
            print(f"   - Risk Score: {ob.risk_score}")
            print(f"   - Penalty: ₹{ob.penalty.total}")
        
        financial_state_obj = normalizer.create_financial_state(
            obligations,
            raw_data['cash_balance']
        )
        
        print(f"\n   Financial Summary:")
        print(f"   - Total Payables: ₹{financial_state_obj.total_payables}")
        print(f"   - Total Receivables: ₹{financial_state_obj.total_receivables}")
        print(f"   - Total Penalties: ₹{financial_state_obj.total_penalties}")
        print(f"   - High Risk Items: {financial_state_obj.high_risk_count}")
        
        return financial_state_obj
        
    except Exception as e:
        print(f"❌ Normalization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_pipeline_async():
    """Test complete ingestion pipeline asynchronously"""
    print("\n" + "="*50)
    print("Testing Complete Pipeline (Async)")
    print("="*50)
    
    csv_file = create_sample_csv()
    pdf_file = create_sample_pdf()
    
    print(f"📁 Testing pipeline with: {csv_file}")
    
    try:
        pipeline = IngestionPipeline()
        
        print(f"\n🔄 Processing single CSV file...")
        result = await pipeline.process_file(csv_file)
        
        print(f"✅ Single file processed!")
        print(f"   - File: {result['file']}")
        print(f"   - Records: {result['record_count']}")
        print(f"   - File type: {result['file_type']}")
        
        print(f"\n🔄 Processing batch of files...")
        batch_results = await pipeline.process_batch([csv_file, pdf_file])
        
        print(f"✅ Batch processing complete!")
        if isinstance(batch_results, dict):
            print(f"   - Successful files: {batch_results.get('successful_count', 0)}")
            print(f"   - Failed files: {batch_results.get('failed_count', 0)}")
            print(f"   - Total obligations: {batch_results.get('total_obligations', 0)}")
        else:
            print(f"   - Total files: {len(batch_results)}")
        
        output_file = "test_output.json"
        pipeline.save_to_json(batch_results, output_file)
        print(f"   - Results saved to: {output_file}")
        
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"   - JSON size: {len(str(data))} bytes")
        
        return batch_results
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(csv_file):
            os.unlink(csv_file)
        if os.path.exists(pdf_file):
            os.unlink(pdf_file)

def test_full_pipeline():
    """Wrapper to run async pipeline test"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_pipeline_async())
        loop.close()
        return result
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function"""
    print("\n" + "🚀" * 20)
    print("Fintech Decision Assistant - Parser Test Suite (with FUTURE DATES)")
    print("🚀" * 20)
    
    results = {}
    
    results['csv'] = test_csv_parser()
    results['pdf'] = test_pdf_parser()
    results['ocr'] = test_ocr_parser()
    results['normalizer'] = test_normalizer()
    results['pipeline'] = test_full_pipeline()
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.upper()}: {status}")
    
    successful = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n📊 Success Rate: {successful}/{total} tests passed")
    
    if successful == total:
        print("\n🎉 All tests passed! Your parser is ready to use!")
        print("\n📅 NOTE: All dates are set to FUTURE dates for cash flow visualization")
        print("\nTo run the API server:")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("\nTo test with a real file:")
        print("  curl -X POST \"http://localhost:8000/upload\" -F \"file=@your_file.csv\"")
        print("\nAccess API docs:")
        print("  http://localhost:8000/docs")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        print("\n💡 Tip: If pipeline test fails, try running the individual tests first.")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    main()