# backend/preprocessing/__init__.py
"""
Preprocessing module for financial data processing
"""

from .financial_processor import (
    process_ingested_data,
    process_json_file,
    print_financial_summary,
    clean_name,
    clean_amount,
    clean_date,
    normalize_obligation,
    remove_duplicates,
    categorize,
    aggregate_by_category,
    get_payment_priorities,
    create_cash_flow_dataframe,
    create_cash_flow_graph,
    create_cash_flow_analysis,
    print_cash_flow_table,  # Add this
    filter_by_partial_availability,
    get_partial_payment_options,
    get_partial_payment_summary,
    print_partial_payment_summary
)

__all__ = [
    'process_ingested_data',
    'process_json_file',
    'print_financial_summary',
    'clean_name',
    'clean_amount',
    'clean_date',
    'normalize_obligation',
    'remove_duplicates',
    'categorize',
    'aggregate_by_category',
    'get_payment_priorities',
    'create_cash_flow_dataframe',
    'create_cash_flow_graph',
    'create_cash_flow_analysis',
    'print_cash_flow_table',
    'filter_by_partial_availability',
    'get_partial_payment_options',
    'get_partial_payment_summary',
    'print_partial_payment_summary'
]