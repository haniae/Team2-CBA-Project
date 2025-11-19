"""Comprehensive test for metric spelling mistakes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_all_metric_spelling():
    """Test comprehensive metric spelling mistakes."""
    print("=" * 80)
    print("Comprehensive Metric Spelling Mistake Test")
    print("=" * 80)
    
    test_cases = [
        # Single word misspellings
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
        # Multi-word misspellings
        ("What is net incom?", "net_income", "net income -> net incom"),
        ("Show me operatng cash flow", "operating_cash_flow", "operating -> operatng"),
        ("What is retrn on assets?", "roa", "return -> retrn"),
        ("Show me price to sales rati", "ps_ratio", "ratio -> rati"),
        ("What is deb to equity rati?", "debt_to_equity", "ratio -> rati"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric, description in test_cases:
        structured = parse_to_structured(query)
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if expected_metric in found_metrics:
            print(f"  [PASS] {description}")
            passed += 1
        else:
            print(f"  [FAIL] {description} -> Found: {found_metrics}")
            failed += 1
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    return passed, failed

if __name__ == "__main__":
    passed, failed = test_all_metric_spelling()
    print("\n" + "=" * 80)
    if passed / (passed + failed) >= 0.90:
        print("[SUCCESS] Metric spelling mistake handling is excellent!")
    elif passed / (passed + failed) >= 0.70:
        print("[SUCCESS] Metric spelling mistake handling is good!")
    else:
        print("[INFO] Metric spelling mistake handling needs improvement")

