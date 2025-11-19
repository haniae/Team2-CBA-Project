"""Detailed test to identify all failing cases."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

# Company name spelling mistakes
company_tests = [
    ("What is Microsft's revenue?", "MSFT", "Microsoft -> Microsft"),
    ("Show me Appel revenue", "AAPL", "Apple -> Appel"),
    ("What is Amazn's revenue?", "AMZN", "Amazon -> Amazn"),
    ("Show me Googl revenue", "GOOGL", "Google -> Googl"),
    ("What is Tesl's revenue?", "TSLA", "Tesla -> Tesl"),
    ("Show me Nvida revenue", "NVDA", "NVIDIA -> Nvida"),
    ("What is Bookng Holdings revenue?", "BKNG", "Booking -> Bookng"),
    ("Show me Enact Holdngs revenue", "ACT", "Enact Holdings -> Enact Holdngs"),
    ("What is Bread Financal revenue?", "BFH", "Bread Financial -> Bread Financal"),
    ("Show me Bill Holdngs revenue", "BILL", "Bill Holdings -> Bill Holdngs"),
]

# Metric spelling mistakes
metric_tests = [
    ("What is AAPL's revenu?", "revenue", "revenue -> revenu"),
    ("Show me net incom", "net_income", "net income -> net incom"),
    ("What is operatng income?", "operating_income", "operating -> operatng"),
    ("Show me earnngs per share", "eps_diluted", "earnings -> earnngs"),
    ("What is price to earnngs?", "pe_ratio", "earnings -> earnngs"),
    ("Show me retrn on equity", "roe", "return -> retrn"),
    ("What is deb to equity?", "debt_to_equity", "debt -> deb"),
    ("Show me free cash flow margn", "free_cash_flow_margin", "margin -> margn"),
    ("What is gross profi?", "gross_profit", "profit -> profi"),
    ("Show me operatng margin", "operating_margin", "operating -> operatng"),
]

print("=" * 80)
print("DETAILED FAILURE ANALYSIS")
print("=" * 80)

print("\nCompany Name Failures:")
for query, expected_ticker, description in company_tests:
    matches, warnings = resolve_tickers_freeform(query)
    found_tickers = [m.get("ticker") for m in matches]
    
    if expected_ticker not in found_tickers:
        print(f"\n[FAIL] {description}")
        print(f"  Query: {query}")
        print(f"  Expected: {expected_ticker}")
        print(f"  Found: {found_tickers}")
        print(f"  Warnings: {warnings}")

print("\n" + "=" * 80)
print("Metric Failures:")
for query, expected_metric, description in metric_tests:
    structured = parse_to_structured(query)
    found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
    
    if expected_metric not in found_metrics:
        print(f"\n[FAIL] {description}")
        print(f"  Query: {query}")
        print(f"  Expected: {expected_metric}")
        print(f"  Found: {found_metrics}")

