#!/usr/bin/env python
"""
Test script for financial preprocessing
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the preprocessing module
from backend.preprocessing.financial_processor import (
    process_json_file,
    print_financial_summary,
    process_ingested_data
)

def test_with_json_file():
    """Test preprocessing with your JSON file"""
    
    # Check if JSON file exists
    json_file = "test_output.json"
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        print("Please run test_parser.py first to generate the JSON file")
        return
    
    print("📂 Loading JSON file...")
    
    # Process the JSON file
    result = process_json_file(json_file, initial_balance=100000)
    
    # Print summary
    print_financial_summary(result)
    
    # Save processed result
    output_file = "processed_financial_state.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✅ Processed data saved to: {output_file}")
    
    # Print some statistics
    print("\n📊 Processing Statistics:")
    stats = result['processing_stats']
    print(f"   - Files processed: {stats['total_files_processed']}")
    print(f"   - Raw obligations: {stats['total_obligations_raw']}")
    print(f"   - Duplicates removed: {stats['duplicates_removed']}")
    print(f"   - Paid obligations skipped: {stats['paid_obligations_skipped']}")
    
    # Show payables by type
    print("\n📋 Payables by Type:")
    type_counts = {}
    for p in result['payables']:
        p_type = p.get('type', 'unknown')
        type_counts[p_type] = type_counts.get(p_type, 0) + 1
    
    for p_type, count in type_counts.items():
        print(f"   - {p_type}: {count}")

def test_with_your_json_data():
    """Test with the JSON data you provided"""
    
    # Your JSON data from the pipeline
    data = {
        "successful": [
            # Your JSON data here
        ]
    }
    
    # Process the data
    result = process_ingested_data(data, initial_balance=100000)
    
    # Print summary
    print_financial_summary(result)
    
    return result

if __name__ == "__main__":
    test_with_json_file()