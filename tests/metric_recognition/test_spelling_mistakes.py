"""Test spelling mistake handling for company names and metrics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import resolve_metrics, parse_to_structured

def test_company_spelling_mistakes():
    """Test company name spelling mistakes."""
    print("=" * 80)
    print("Testing Company Name Spelling Mistakes")
    print("=" * 80)
    
    test_cases = [
        # (query with spelling mistake, expected ticker)
        ("What is Microsft's revenue?", "MSFT"),  # Microsoft -> Microsft
        ("Show me Appel revenue", "AAPL"),  # Apple -> Appel
        ("What is Amazn's revenue?", "AMZN"),  # Amazon -> Amazn
        ("Show me Googl revenue", "GOOGL"),  # Google -> Googl
        ("What is Tesl's revenue?", "TSLA"),  # Tesla -> Tesl
        ("Show me Nvida revenue", "NVDA"),  # NVIDIA -> Nvida
        ("What is Bookng Holdings revenue?", "BKNG"),  # Booking -> Bookng
        ("Show me Enact Holdngs revenue", "ACT"),  # Enact Holdings -> Enact Holdngs
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_ticker in test_cases:
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if expected_ticker in found_tickers:
            print(f"[PASS] '{query}' -> {expected_ticker}")
            passed += 1
        else:
            print(f"[FAIL] '{query}' -> Expected: {expected_ticker}, Found: {found_tickers}")
            failed += 1
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    return passed, failed

def test_metric_spelling_mistakes():
    """Test metric spelling mistakes."""
    print("\n" + "=" * 80)
    print("Testing Metric Spelling Mistakes")
    print("=" * 80)
    
    test_cases = [
        # (query with spelling mistake, expected metric)
        ("What is AAPL's revenu?", "revenue"),  # revenue -> revenu
        ("Show me net incom", "net_income"),  # net income -> net incom
        ("What is operatng income?", "operating_income"),  # operating -> operatng
        ("Show me earnngs per share", "eps_diluted"),  # earnings -> earnngs
        ("What is price to earnngs?", "pe_ratio"),  # earnings -> earnngs
        ("Show me retrn on equity", "roe"),  # return -> retrn
        ("What is deb to equity?", "debt_to_equity"),  # debt -> deb
        ("Show me free cash flow margn", "free_cash_flow_margin"),  # margin -> margn
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric in test_cases:
        structured = parse_to_structured(query)
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if expected_metric in found_metrics:
            print(f"[PASS] '{query}' -> {expected_metric}")
            passed += 1
        else:
            print(f"[FAIL] '{query}' -> Expected: {expected_metric}, Found: {found_metrics}")
            failed += 1
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    return passed, failed

if __name__ == "__main__":
    company_passed, company_failed = test_company_spelling_mistakes()
    metric_passed, metric_failed = test_metric_spelling_mistakes()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Company name spelling mistakes: {company_passed}/{company_passed+company_failed} ({company_passed*100/(company_passed+company_failed):.1f}%)")
    print(f"Metric spelling mistakes: {metric_passed}/{metric_passed+metric_failed} ({metric_passed*100/(metric_passed+metric_failed):.1f}%)")

