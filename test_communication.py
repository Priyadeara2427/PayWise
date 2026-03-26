#!/usr/bin/env python
"""
Test script for Communication Engine
"""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.engine.communication_engine import create_action_communications

def test_communication():
    """Test communication engine"""
    
    print("\n" + "="*80)
    print("COMMUNICATION ENGINE TEST")
    print("="*80)
    
    # Sample data
    sample_payables = [
        {
            "party": "Income Tax Department",
            "amount": 50000,
            "due_date": "2026-03-20",
            "type": "tax_authority",
            "days_late": 10
        },
        {
            "party": "Raj Fabrics",
            "amount": 45000,
            "due_date": "2026-03-15",
            "type": "vendor",
            "days_late": 5,
            "accepts_partial": True
        },
        {
            "party": "Friend Loan",
            "amount": 10000,
            "due_date": "2026-03-25",
            "type": "friend",
            "days_late": 0
        }
    ]
    
    sample_receivables = [
        {
            "party": "XYZ Corp",
            "amount": 35000,
            "expected_date": "2026-03-18",
            "type": "customer",
            "days_late": 7
        }
    ]
    
    sample_decisions = [
        {"action": "pay_immediately", "priority": "critical"},
        {"action": "pay_partially", "suggested_terms": {"percentage": 50, "remaining_days": 15}},
        {"action": "negotiate_deadline_extension", "suggested_terms": {"requested_days": 10}}
    ]
    
    # Get API key from environment
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("\n⚠️ No API key found. Using template-based generation.")
        print("   Set OPENROUTER_API_KEY in .env file for AI-generated content.\n")
    
    # Create communications
    communications = create_action_communications(
        cash_balance=50000,
        payables=sample_payables,
        receivables=sample_receivables,
        decisions=sample_decisions,
        api_key=api_key
    )
    
    # Print results
    print(f"\n📧 Generated {communications['summary']['total_communications']} communications")
    
    print("\n" + "="*80)
    print("PAYABLE COMMUNICATIONS:")
    print("="*80)
    
    for comm in communications['payables']:
        print(f"\n--- TO: {comm['party']} ({comm['type']}) ---")
        print(comm['email'])
        print("-" * 50)
    
    print("\n" + "="*80)
    print("RECEIVABLE COMMUNICATIONS:")
    print("="*80)
    
    for comm in communications['receivables']:
        print(f"\n--- TO: {comm['party']} ({comm['type']}) ---")
        print(comm['email'])
        print("-" * 50)
    
    # Save to file
    output_file = "output/communications_output.json"
    os.makedirs("output", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(communications, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n✅ Communications saved to: {output_file}")
    print("\n" + "="*80)

if __name__ == "__main__":
    test_communication()