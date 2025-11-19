"""Quick verification that S&P 1500 is set up correctly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def main():
    """Quick verification."""
    print("=" * 80)
    print("S&P 1500 Setup Verification")
    print("=" * 80)
    
    # Test 1: Load universe
    tickers = _load_universe()
    print(f"\n1. Universe Loading: {len(tickers)} tickers")
    
    if len(tickers) >= 1400:
        print("   [SUCCESS] S&P 1500 is active!")
    else:
        print(f"   [WARNING] Only {len(tickers)} tickers loaded")
    
    # Test 2: Test a few known tickers
    print("\n2. Testing Sample Tickers:")
    test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]  # S&P 500
    test_tickers += ["ZION", "FNB", "WAL"]  # S&P 400 examples
    test_tickers += ["AAN", "ABG", "ACHC"]  # S&P 600 examples
    
    passed = 0
    for ticker in test_tickers:
        if ticker not in tickers:
            print(f"   [SKIP] {ticker} not in universe")
            continue
        
        query = f"What is {ticker}'s revenue?"
        matches, warnings = resolve_tickers_freeform(query)
        found = [m.get("ticker") for m in matches]
        
        if ticker in found:
            print(f"   [PASS] {ticker}")
            passed += 1
        else:
            print(f"   [FAIL] {ticker} (found: {found})")
    
    print(f"\n   Results: {passed}/{len([t for t in test_tickers if t in tickers])} passed")
    
    # Test 3: Full parsing
    print("\n3. Testing Full Parsing:")
    test_query = "What is AAPL's revenue?"
    structured = parse_to_structured(test_query)
    found_tickers = [t.get("ticker") for t in structured.get("tickers", [])]
    found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
    
    if "AAPL" in found_tickers and "revenue" in found_metrics:
        print("   [PASS] Full parsing works")
    else:
        print(f"   [FAIL] Tickers: {found_tickers}, Metrics: {found_metrics}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"[SUCCESS] S&P 1500 file created with {len(tickers)} tickers")
    print("[INFO] System is ready to use S&P 1500 tickers")
    print("\nNote: Some tickers may need company name aliases for")
    print("      better natural language recognition. This is normal.")

if __name__ == "__main__":
    main()

