"""Test specific spelling failure cases to debug."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

# Test cases that are currently failing
failing_company_tests = [
    ("What is Microsft's revenue?", "MSFT", "Microsoft -> Microsft"),
    ("What is Amazn's revenue?", "AMZN", "Amazon -> Amazn"),
    ("What is Tesl's revenue?", "TSLA", "Tesla -> Tesl"),
    ("Show me Nvida revenue", "NVDA", "NVIDIA -> Nvida"),
    ("What is Bookng Holdings revenue?", "BKNG", "Booking -> Bookng"),
]

failing_metric_tests = [
    ("Show me earnngs per share", "eps_diluted", "earnings -> earnngs"),
    ("What is price to earnngs?", "pe_ratio", "earnings -> earnngs"),
    ("Show me retrn on equity", "roe", "return -> retrn"),
    ("What is deb to equity?", "debt_to_equity", "debt -> deb"),
    ("Show me free cash flow margn", "free_cash_flow_margin", "margin -> margn"),
]

print("Testing failing company name cases:")
for query, expected, desc in failing_company_tests:
    matches, warnings = resolve_tickers_freeform(query)
    found = [m.get("ticker") for m in matches]
    status = "[PASS]" if expected in found else "[FAIL]"
    print(f"{status} {desc}")
    if expected not in found:
        print(f"  Expected: {expected}, Found: {found}")
        print(f"  Warnings: {warnings}")

print("\nTesting failing metric cases:")
for query, expected, desc in failing_metric_tests:
    structured = parse_to_structured(query)
    found = [m.get("key") for m in structured.get("vmetrics", [])]
    status = "[PASS]" if expected in found else "[FAIL]"
    print(f"{status} {desc}")
    if expected not in found:
        print(f"  Expected: {expected}, Found: {found}")

