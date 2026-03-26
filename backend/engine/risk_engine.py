"""
Enhanced Risk Engine for Financial Obligations with Partial Payment Support
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

def calculate_risk(processed_data, consider_partial: bool = True):
    """
    Enhanced risk calculation using all factors including partial payments
    
    Args:
        processed_data: Processed financial data
        consider_partial: Whether to consider partial payment options
    
    Returns:
        Risk assessment dictionary
    """
    
    cash = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    today = datetime.today().date()
    
    # Initialize counters
    total_payables = 0
    overdue_payables = 0
    upcoming_payables = 0
    incoming_cash = 0
    
    # Partial payment tracking
    partial_available_count = 0
    partial_minimum_total = 0
    partial_suggested_total = 0
    
    # Track risk by category
    risk_by_category = {}
    high_risk_items = []
    critical_items = []
    
    # ---------- Enhanced Payables Analysis with Partial Payment ----------
    for p in payables:
        amount = p["amount"]
        due_date = p.get("due_date")
        counterparty_type = p.get("type", "unknown")
        days_late = p.get("days_late", 0)
        risk_score_individual = p.get("risk_score", 0)
        priority = p.get("priority", "medium")
        urgency = p.get("urgency", "none")
        category = p.get("category", "other")
        
        # Get partial payment info
        partial = p.get("partial_payment", {})
        accepts_partial = partial.get("accepts_partial", False)
        min_pct = partial.get("minimum_pct", 50)
        min_amount = partial.get("minimum_amount", amount * min_pct / 100)
        
        if accepts_partial and consider_partial:
            partial_available_count += 1
            partial_minimum_total += max(min_amount, amount * min_pct / 100)
            partial_suggested_total += amount * partial.get("suggested_pct", 50) / 100
        
        total_payables += amount
        
        # Parse due date
        if due_date:
            if isinstance(due_date, str):
                due = datetime.strptime(due_date, "%Y-%m-%d").date()
            else:
                due = due_date
            
            if due < today:
                overdue_payables += amount
                days_overdue = (today - due).days
                
                # Track high risk items
                high_risk_items.append({
                    "party": p["party"],
                    "amount": amount,
                    "type": counterparty_type,
                    "days_overdue": days_overdue,
                    "risk_score": risk_score_individual,
                    "penalty": p.get("penalty", 0),
                    "accepts_partial": accepts_partial,
                    "min_partial": min_amount
                })
            else:
                upcoming_payables += amount
        else:
            upcoming_payables += amount
        
        # Track risk by category
        if category not in risk_by_category:
            risk_by_category[category] = {
                "total_amount": 0,
                "count": 0,
                "overdue_amount": 0,
                "risk_score": 0,
                "partial_available": 0
            }
        
        risk_by_category[category]["total_amount"] += amount
        risk_by_category[category]["count"] += 1
        if days_late > 0:
            risk_by_category[category]["overdue_amount"] += amount
        risk_by_category[category]["risk_score"] += risk_score_individual
        if accepts_partial:
            risk_by_category[category]["partial_available"] += 1
        
        # Track critical items (tax, government, etc.)
        if counterparty_type in ['tax_authority', 'government'] and days_late > 0:
            critical_items.append({
                "party": p["party"],
                "type": counterparty_type,
                "amount": amount,
                "days_late": days_late,
                "penalty": p.get("penalty", 0),
                "accepts_partial": accepts_partial
            })
    
    # Normalize risk scores by category
    for category in risk_by_category:
        if risk_by_category[category]["count"] > 0:
            risk_by_category[category]["risk_score"] /= risk_by_category[category]["count"]
    
    # ---------- Receivables Analysis ----------
    for r in receivables:
        incoming_cash += r["amount"]
        expected_date = r.get("expected_date")
        
        if expected_date:
            if isinstance(expected_date, str):
                expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
            else:
                expected = expected_date
            
            if expected < today:
                days_overdue = (today - expected).days
                if days_overdue > 30:
                    risk_by_category.setdefault("overdue_receivables", {
                        "total_amount": 0,
                        "count": 0,
                        "overdue_amount": 0,
                        "risk_score": 0.8
                    })
                    risk_by_category["overdue_receivables"]["total_amount"] += r["amount"]
                    risk_by_category["overdue_receivables"]["count"] += 1
    
    # ---------- Cash Flow Projection with Partial Payment ----------
    weighted_payables = 0
    for p in payables:
        amount = p["amount"]
        days_late = p.get("days_late", 0)
        partial = p.get("partial_payment", {})
        accepts_partial = partial.get("accepts_partial", False)
        
        priority_weight = {
            'critical': 1.0,
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3
        }.get(p.get("priority", "medium"), 0.5)
        
        # If partial payment available, reduce effective payment
        if consider_partial and accepts_partial:
            min_payment = max(
                partial.get("minimum_amount", 0),
                amount * partial.get("minimum_pct", 50) / 100
            )
            effective_amount = min_payment  # Use minimum required for risk calculation
        else:
            effective_amount = amount
        
        # Add urgency multiplier
        urgency_multiplier = 1.0
        if days_late > 30:
            urgency_multiplier = 1.5
        elif days_late > 15:
            urgency_multiplier = 1.3
        elif days_late > 7:
            urgency_multiplier = 1.1
        
        weighted_payables += effective_amount * priority_weight * urgency_multiplier
    
    projected_cash = cash + incoming_cash - weighted_payables
    
    # Calculate alternative projection with partial payments
    partial_projected_cash = None
    if consider_partial:
        # Projection using suggested partial payments
        weighted_partial_payables = 0
        for p in payables:
            amount = p["amount"]
            days_late = p.get("days_late", 0)
            partial = p.get("partial_payment", {})
            accepts_partial = partial.get("accepts_partial", False)
            
            priority_weight = {
                'critical': 1.0,
                'high': 0.9,
                'medium': 0.6,
                'low': 0.3
            }.get(p.get("priority", "medium"), 0.5)
            
            if accepts_partial:
                effective_amount = amount * partial.get("suggested_pct", 50) / 100
            else:
                effective_amount = amount
            
            urgency_multiplier = 1.0
            if days_late > 30:
                urgency_multiplier = 1.5
            elif days_late > 15:
                urgency_multiplier = 1.3
            elif days_late > 7:
                urgency_multiplier = 1.1
            
            weighted_partial_payables += effective_amount * priority_weight * urgency_multiplier
        
        partial_projected_cash = cash + incoming_cash - weighted_partial_payables
    
    # ---------- Enhanced Risk Score Calculation ----------
    total_liabilities = total_payables
    total_assets = cash + incoming_cash
    
    if total_assets == 0:
        financial_risk = 1.0
    else:
        financial_risk = min(1.0, total_liabilities / total_assets)
    
    if total_payables == 0:
        overdue_risk = 0
    else:
        overdue_risk = min(1.0, overdue_payables / total_payables)
    
    counterparty_risk = 0
    for p in payables:
        cp_type = p.get("type", "unknown")
        type_risk = {
            'tax_authority': 1.0,
            'government': 0.9,
            'bank': 0.85,
            'vendor': 0.7,
            'employee': 0.8,
            'utility': 0.6,
            'rent': 0.5,
            'customer': 0.3,
            'friend': 0.2,
            'family': 0.1,
            'unknown': 0.4
        }.get(cp_type, 0.5)
        
        amount_weight = p["amount"] / total_payables if total_payables > 0 else 0
        counterparty_risk += type_risk * amount_weight
    
    critical_risk = min(1.0, len(critical_items) / max(len(payables), 1))
    
    risk_score = (
        financial_risk * 0.4 +
        overdue_risk * 0.3 +
        counterparty_risk * 0.2 +
        critical_risk * 0.1
    )
    
    # ---------- Risk Level Determination ----------
    if projected_cash < 0 or risk_score > 0.7 or len(critical_items) > 0:
        risk_level = "HIGH"
        risk_summary = "Critical risk - Immediate action required"
    elif risk_score > 0.4 or overdue_payables > cash * 0.5:
        risk_level = "MEDIUM"
        risk_summary = "Moderate risk - Monitor closely"
    else:
        risk_level = "LOW"
        risk_summary = "Low risk - Stable cash position"
    
    # ---------- Days to Zero Cash ----------
    days_to_zero = None
    if projected_cash < 0:
        days_to_zero = "Immediate Risk - Cash Shortfall"
    elif cash > 0 and weighted_payables > 0:
        daily_burn = weighted_payables / 30
        if daily_burn > 0:
            days_to_zero = int(cash / daily_burn)
        else:
            days_to_zero = "Unlimited"
    
    # ---------- Partial Payment Recommendations ----------
    partial_recommendations = []
    if consider_partial and partial_available_count > 0:
        if partial_projected_cash and partial_projected_cash > projected_cash:
            partial_recommendations.append(f"💡 Using partial payments could improve cash position by ₹{partial_projected_cash - projected_cash:,.2f}")
        
        if partial_minimum_total > cash:
            shortfall = partial_minimum_total - cash
            partial_recommendations.append(f"⚠️ Even with minimum partial payments, shortfall of ₹{shortfall:,.2f}")
        
        partial_recommendations.append(f"💳 {partial_available_count} obligations accept partial payments")
        partial_recommendations.append(f"   Minimum total: ₹{partial_minimum_total:,.2f}")
        partial_recommendations.append(f"   Suggested total: ₹{partial_suggested_total:,.2f}")
    
    # ---------- Generate Recommendations ----------
    recommendations = []
    
    if len(critical_items) > 0:
        recommendations.append(f"🚨 Critical: Pay {len(critical_items)} tax/government obligations immediately")
    
    if overdue_payables > cash * 0.3:
        recommendations.append("⚠️ High overdue payments - Negotiate extensions")
    
    if len(high_risk_items) > 0:
        recommendations.append(f"⚠️ {len(high_risk_items)} high-risk items need immediate attention")
    
    if risk_score > 0.6:
        recommendations.append("⚠️ Consider arranging additional funds or restructuring payments")
    
    recommendations.extend(partial_recommendations)
    
    # ---------- Return Enhanced Risk Report ----------
    return {
        "cash_balance": cash,
        "total_payables": total_payables,
        "overdue_payables": overdue_payables,
        "upcoming_payables": upcoming_payables,
        "incoming_cash": incoming_cash,
        "projected_cash": round(projected_cash, 2),
        "partial_projected_cash": round(partial_projected_cash, 2) if partial_projected_cash else None,
        "weighted_payables": round(weighted_payables, 2),
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "days_to_zero": days_to_zero,
        "financial_ratio": round(financial_risk, 2),
        "overdue_ratio": round(overdue_risk, 2),
        "counterparty_risk": round(counterparty_risk, 2),
        "critical_risk": round(critical_risk, 2),
        "partial_payment_stats": {
            "available_count": partial_available_count,
            "minimum_total": partial_minimum_total,
            "suggested_total": partial_suggested_total,
            "percentage": (partial_available_count / len(payables) * 100) if payables else 0
        },
        "risk_by_category": risk_by_category,
        "high_risk_items": high_risk_items[:5],
        "critical_items": critical_items,
        "recommendations": recommendations,
        "summary": {
            "total_obligations": len(payables),
            "critical_count": len(critical_items),
            "high_risk_count": len(high_risk_items),
            "cash_position": "positive" if projected_cash > 0 else "negative"
        }
    }


def print_risk_report(report):
    """Pretty print the risk report with partial payment info"""
    
    print("\n" + "="*60)
    print("RISK ASSESSMENT REPORT")
    print("="*60)
    
    print(f"\n💰 Cash Balance: ₹{report['cash_balance']:,.2f}")
    print(f"📤 Total Payables: ₹{report['total_payables']:,.2f}")
    print(f"📥 Incoming Cash: ₹{report['incoming_cash']:,.2f}")
    print(f"⚠️ Overdue Payables: ₹{report['overdue_payables']:,.2f}")
    print(f"🎯 Projected Cash: ₹{report['projected_cash']:,.2f}")
    
    if report.get('partial_projected_cash'):
        improvement = report['partial_projected_cash'] - report['projected_cash']
        print(f"💳 With Partial Payments: ₹{report['partial_projected_cash']:,.2f} (Improvement: ₹{improvement:,.2f})")
    
    print(f"\n📊 Risk Score: {report['risk_score']} ({report['risk_level']})")
    print(f"📝 Risk Summary: {report['risk_summary']}")
    
    print(f"\n📈 Risk Factors:")
    print(f"   - Financial Ratio: {report['financial_ratio']}")
    print(f"   - Overdue Ratio: {report['overdue_ratio']}")
    print(f"   - Counterparty Risk: {report['counterparty_risk']}")
    print(f"   - Critical Items Risk: {report['critical_risk']}")
    
    # Partial Payment Stats
    partial_stats = report.get('partial_payment_stats', {})
    if partial_stats:
        print(f"\n💳 Partial Payment Availability:")
        print(f"   - Obligations accepting partial: {partial_stats['available_count']} ({partial_stats['percentage']:.1f}%)")
        print(f"   - Minimum total required: ₹{partial_stats['minimum_total']:,.2f}")
        print(f"   - Suggested total: ₹{partial_stats['suggested_total']:,.2f}")
    
    if report['critical_items']:
        print(f"\n🚨 CRITICAL ITEMS:")
        for item in report['critical_items']:
            partial_indicator = " [Partial OK]" if item.get('accepts_partial') else ""
            print(f"   - {item['party']} ({item['type']}): ₹{item['amount']:,.2f} (Late: {item['days_late']} days){partial_indicator}")
    
    if report['high_risk_items']:
        print(f"\n⚠️ HIGH RISK ITEMS:")
        for item in report['high_risk_items'][:3]:
            partial_indicator = " [Partial OK]" if item.get('accepts_partial') else ""
            print(f"   - {item['party']}: ₹{item['amount']:,.2f} (Overdue: {item['days_overdue']} days){partial_indicator}")
    
    if report['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"   {rec}")
    
    print("\n" + "="*60)


# Keep existing cash flow functions (create_cash_flow_dataframe, print_cash_flow_table, 
# create_cash_flow_graph, create_cash_flow_analysis) as they are - they work with the same structure