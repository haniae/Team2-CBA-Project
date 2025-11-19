"""Comprehensive test for spelling mistakes in company names and metrics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_comprehensive():
    """Test comprehensive spelling mistake scenarios."""
    print("=" * 80)
    print("Comprehensive Spelling Mistake Test")
    print("=" * 80)
    
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
    
    print("\n1. Testing Company Name Spelling Mistakes:")
    company_passed = 0
    company_failed = 0
    
    for query, expected_ticker, description in company_tests:
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if expected_ticker in found_tickers:
            print(f"  [PASS] {description}")
            company_passed += 1
        else:
            print(f"  [FAIL] {description} -> Found: {found_tickers}")
            company_failed += 1
    
    print(f"\n  Results: {company_passed}/{company_passed+company_failed} passed ({company_passed*100/(company_passed+company_failed):.1f}%)")
    
    print("\n2. Testing Metric Spelling Mistakes:")
    metric_passed = 0
    metric_failed = 0
    
    for query, expected_metric, description in metric_tests:
        structured = parse_to_structured(query)
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if expected_metric in found_metrics:
            print(f"  [PASS] {description}")
            metric_passed += 1
        else:
            print(f"  [FAIL] {description} -> Found: {found_metrics}")
            metric_failed += 1
    
    print(f"\n  Results: {metric_passed}/{metric_passed+metric_failed} passed ({metric_passed*100/(metric_passed+metric_failed):.1f}%)")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Company name spelling mistakes: {company_passed}/{company_passed+company_failed} ({company_passed*100/(company_passed+company_failed):.1f}%)")
    print(f"Metric spelling mistakes: {metric_passed}/{metric_passed+metric_failed} ({metric_passed*100/(metric_passed+metric_failed):.1f}%)")
    
    if company_passed / (company_passed + company_failed) >= 0.70:
        print("\n[SUCCESS] Company name spelling mistake handling is working well!")
    else:
        print("\n[INFO] Company name spelling mistake handling needs improvement")
    
    if metric_passed / (metric_passed + metric_failed) >= 0.70:
        print("[SUCCESS] Metric spelling mistake handling is working well!")
    else:
        print("[INFO] Metric spelling mistake handling needs improvement")

if __name__ == "__main__":
    test_comprehensive()

