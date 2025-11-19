"""Test specific company names that were failing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform

def test_specific_cases():
    """Test specific failing cases."""
    test_cases = [
        ("ACT", "Enact Holdings Inc."),
        ("BKNG", "Booking Holdings Inc."),
        ("BFH", "Bread Financial Holdings Inc."),
        ("BILL", "Bill Holdings Inc."),
        ("BJ", "BJ's Wholesale Club Holdings Inc."),
        ("AHL", "Aspen Insurance Holdings Ltd."),
        ("ADTN", "ADTRAN Holdings Inc."),
        ("AMTM", "Amentum Holdings Inc."),
        ("CCK", "Crown Holdings Inc."),
        ("CELH", "Celsius Holdings Inc."),
    ]
    
    print("=" * 80)
    print("Testing Specific Company Names")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for ticker, company_name in test_cases:
        queries = [
            f"What is {company_name}'s revenue?",
            f"Show me {company_name} revenue",
            f"{company_name} revenue",
        ]
        
        found = False
        for query in queries:
            matches, warnings = resolve_tickers_freeform(query)
            found_tickers = [m.get("ticker") for m in matches]
            
            if ticker in found_tickers:
                found = True
                print(f"[PASS] {ticker}: {company_name}")
                passed += 1
                break
        
        if not found:
            print(f"[FAIL] {ticker}: {company_name}")
            # Show what was found
            matches, warnings = resolve_tickers_freeform(f"What is {company_name}'s revenue?")
            found_tickers = [m.get("ticker") for m in matches]
            print(f"       Found instead: {found_tickers}")
            failed += 1
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")

if __name__ == "__main__":
    test_specific_cases()

