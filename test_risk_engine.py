#!/usr/bin/env python
"""
Test script for Risk Engine with Interactive Selection
"""

import json
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the risk engine
from backend.engine.risk_engine import calculate_risk, print_risk_report
# Import cash flow functions from preprocessing
from backend.preprocessing.financial_processor import create_cash_flow_analysis

def test_with_processed_data():
    """Test risk engine with your processed data"""
    
    processed_file = "processed_financial_state.json"
    
    if not os.path.exists(processed_file):
        print(f"❌ Processed data file not found: {processed_file}")
        return None
    
    print("📂 Loading processed financial data...")
    with open(processed_file, 'r', encoding='utf-8') as f:
        processed_data = json.load(f)
    
    print(f"✅ Loaded data with {len(processed_data['payables'])} payables and {len(processed_data['receivables'])} receivables")
    
    return processed_data

def test_with_sample_data():
    """Return sample data"""
    
    sample_processed = {
        "cash_balance": 20000,
        "payables": [
            {"party": "raj fabrics", "amount": 45000, "due_date": "2026-03-20", "type": "vendor", "category": "supplier", "priority": "high", "days_late": 5, "risk_score": 0.4, "penalty": 1125},
            {"party": "tech solutions", "amount": 25000, "due_date": "2026-03-15", "type": "vendor", "category": "supplier", "priority": "high", "days_late": 10, "risk_score": 0.41, "penalty": 11250},
            {"party": "income tax department", "amount": 5000, "due_date": "2026-03-01", "type": "tax_authority", "category": "tax", "priority": "critical", "days_late": 24, "risk_score": 0.85, "penalty": 250}
        ],
        "receivables": [
            {"party": "xyz corp", "amount": 35000, "expected_date": "2026-03-18", "type": "customer"}
        ]
    }
    
    return sample_processed

def test_with_your_actual_data():
    """Return your actual data"""
    
    your_data = {
        "cash_balance": 100000,
        "payables": [
            {
                "party": "Raj Fabrics",
                "amount": 45000.0,
                "due_date": "2026-03-20",
                "type": "vendor",
                "category": "supplier",
                "risk_score": 0.4,
                "penalty": 1125.0,
                "priority": "high",
                "days_late": 5
            },
            {
                "party": "Tech Solutions Pvt Ltd",
                "amount": 25000.0,
                "due_date": "2026-03-15",
                "type": "vendor",
                "category": "supplier",
                "risk_score": 0.41,
                "penalty": 11250.0,
                "priority": "high",
                "days_late": 10
            },
            {
                "party": "ABC Enterprises",
                "amount": 75000.0,
                "due_date": "2026-03-10",
                "type": "vendor",
                "category": "supplier",
                "risk_score": 0.62,
                "penalty": 20625.0,
                "priority": "high",
                "days_late": 15
            }
        ],
        "receivables": [
            {
                "party": "XYZ Corp",
                "amount": 35000.0,
                "expected_date": "2026-03-18",
                "type": "customer"
            }
        ]
    }
    
    return your_data

def main():
    """Interactive main function"""
    
    print("\n" + "🚀" * 30)
    print("RISK ENGINE TEST SUITE")
    print("🚀" * 30)
    
    print("\nSelect a data source:")
    print("1. Your Processed Data (from preprocessing)")
    print("2. Sample Data (with tax authority)")
    print("3. Your Actual Data (from JSON)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        processed_data = test_with_processed_data()
        if not processed_data:
            return
        data_name = "Processed Data"
    elif choice == '2':
        processed_data = test_with_sample_data()
        data_name = "Sample Data"
    elif choice == '3':
        processed_data = test_with_your_actual_data()
        data_name = "Your Actual Data"
    elif choice == '4':
        print("\n👋 Goodbye!")
        return
    else:
        print("\n❌ Invalid choice!")
        return
    
    print(f"\n📊 Analyzing: {data_name}")
    print("="*60)
    
    # Calculate risk
    risk_report = calculate_risk(processed_data)
    
    # Print risk report
    print_risk_report(risk_report)
    
    # Ask if user wants to see cash flow analysis
    print("\n" + "="*60)
    show_graph = input("\n📊 Show Cash Flow Analysis with Graph? (y/n): ").strip().lower()
    
    if show_graph == 'y':
        print("\n🔄 Generating cash flow analysis...")
        try:
            cash_flow_analysis = create_cash_flow_analysis(processed_data, risk_report)
            
            # Print additional statistics
            print("\n📊 CASH FLOW STATISTICS:")
            print(f"   Upcoming Payments: ₹{cash_flow_analysis['upcoming_payments']:,.2f}")
            print(f"   Upcoming Receipts: ₹{cash_flow_analysis['upcoming_receipts']:,.2f}")
            print(f"   Net Cash Flow: ₹{cash_flow_analysis['net_future_cashflow']:,.2f}")
            
            if cash_flow_analysis['days_to_zero']:
                print(f"   ⚠️ Days to Zero Cash: {cash_flow_analysis['days_to_zero']} days")
            else:
                print(f"   ✅ Cash position remains positive")
            
            print(f"   Lowest Cash Point: ₹{cash_flow_analysis['lowest_cash']:,.2f}")
            print(f"   Highest Cash Point: ₹{cash_flow_analysis['highest_cash']:,.2f}")
            
            # Show the graph
            import matplotlib.pyplot as plt
            plt.show()
            
        except Exception as e:
            print(f"❌ Error generating cash flow analysis: {e}")
            import traceback
            traceback.print_exc()
    
    # Save report
    output_file = f"risk_report_{data_name.replace(' ', '_').lower()}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(risk_report, f, indent=2, default=str)
    
    print(f"\n✅ Risk report saved to: {output_file}")
    
    # Ask if user wants to run another test
    another = input("\n🔄 Run another analysis? (y/n): ").strip().lower()
    if another == 'y':
        main()
    else:
        print("\n🎉 Analysis complete!")

if __name__ == "__main__":
    main()