"""Comprehensive test for all S&P 1500 tickers - verifies natural language support."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_sp1500_universe():
    """Test that S&P 1500 universe loads correctly."""
    print("=" * 80)
    print("S&P 1500 Universe Loading Test")
    print("=" * 80)
    
    try:
        tickers = _load_universe()
        print(f"\n[OK] Successfully loaded {len(tickers)} tickers")
        print(f"First 10: {tickers[:10]}")
        print(f"Last 10: {tickers[-10:]}")
        
        # Check if it's S&P 1500 or S&P 500
        if len(tickers) >= 1400:
            print(f"\n[SUCCESS] S&P 1500 detected! ({len(tickers)} tickers)")
            return True, tickers
        elif len(tickers) >= 480:
            print(f"\n[WARNING] S&P 500 detected ({len(tickers)} tickers)")
            print("   S&P 1500 file not found - using S&P 500 as fallback")
            return False, tickers
        else:
            print(f"\n[ERROR] Unexpected ticker count: {len(tickers)}")
            return False, tickers
    except Exception as e:
        print(f"\n[ERROR] Error loading universe: {e}")
        return False, []

def test_ticker_recognition(tickers, sample_size=100):
    """Test that tickers are recognized in natural language queries."""
    print("\n" + "=" * 80)
    print(f"Testing Ticker Recognition (sample of {sample_size})")
    print("=" * 80)
    
    if not tickers:
        print("No tickers to test")
        return
    
    # Test a sample of tickers
    import random
    test_tickers = random.sample(tickers, min(sample_size, len(tickers)))
    
    passed = 0
    failed = 0
    failures = []
    
    for ticker in test_tickers:
        # Test different query formats
        queries = [
            f"What is {ticker}'s revenue?",
            f"What is {ticker} revenue?",
            f"Show me {ticker} revenue",
        ]
        
        found = False
        for query in queries:
            matches, warnings = resolve_tickers_freeform(query)
            found_tickers = [m.get("ticker") for m in matches]
            
            if ticker in found_tickers:
                found = True
                break
        
        if found:
            passed += 1
            if passed <= 10:  # Show first 10 successes
                print(f"[PASS] {ticker}")
        else:
            failed += 1
            failures.append(ticker)
            if failed <= 10:  # Show first 10 failures
                print(f"[FAIL] {ticker}")
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_tickers)}")
    
    if failures and len(failures) <= 20:
        print(f"\nFailed tickers: {failures}")
    
    return passed, failed, failures

def test_full_parsing(tickers, sample_size=50):
    """Test full parsing pipeline with natural language."""
    print("\n" + "=" * 80)
    print(f"Testing Full Parsing Pipeline (sample of {sample_size})")
    print("=" * 80)
    
    if not tickers:
        print("[ERROR] No tickers to test")
        return
    
    import random
    test_tickers = random.sample(tickers, min(sample_size, len(tickers)))
    
    passed = 0
    failed = 0
    
    for ticker in test_tickers:
        query = f"What is {ticker}'s revenue?"
        structured = parse_to_structured(query)
        
        found_tickers = [t.get("ticker") for t in structured.get("tickers", [])]
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if ticker in found_tickers and "revenue" in found_metrics:
            passed += 1
            if passed <= 10:
                print(f"[PASS] {ticker} - Found ticker and metric")
        else:
            failed += 1
            if failed <= 10:
                print(f"[FAIL] {ticker} - Ticker: {ticker in found_tickers}, Metric: {'revenue' in found_metrics}")
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_tickers)}")
    return passed, failed

def test_specific_sp1500_tickers():
    """Test specific S&P 1500 tickers (mid-cap and small-cap examples)."""
    print("\n" + "=" * 80)
    print("Testing Specific S&P 1500 Tickers")
    print("=" * 80)
    
    # Known S&P 1500 tickers (mid-cap and small-cap)
    sp1500_test_tickers = [
        # Mid-cap examples
        "ZION", "FNB", "WAL", "CFR", "ONB",
        "ALKS", "IONS", "RGNX", "ACAD",
        # Small-cap examples  
        "AAN", "ABG", "ACHC", "ACIW", "ACMR",
    ]
    
    passed = 0
    failed = 0
    failures = []
    
    for ticker in sp1500_test_tickers:
        query = f"What is {ticker}'s revenue?"
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if ticker in found_tickers:
            print(f"[PASS] {ticker}")
            passed += 1
        else:
            print(f"[FAIL] {ticker} - Found: {found_tickers}")
            failed += 1
            failures.append(ticker)
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed, failures

def main():
    """Run all tests."""
    print("S&P 1500 Comprehensive Test Suite")
    print("=" * 80)
    
    # Test 1: Load universe
    is_sp1500, tickers = test_sp1500_universe()
    
    if not tickers:
        print("\n[ERROR] Cannot proceed - no tickers loaded")
        return
    
    # Test 2: Ticker recognition
    if is_sp1500:
        passed, failed, failures = test_ticker_recognition(tickers, sample_size=100)
        
        # Test 3: Full parsing
        parse_passed, parse_failed = test_full_parsing(tickers, sample_size=50)
        
        # Test 4: Specific S&P 1500 tickers
        sp1500_passed, sp1500_failed, sp1500_failures = test_specific_sp1500_tickers()
        
        # Summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"[OK] Universe loaded: {len(tickers)} tickers")
        print(f"[OK] Ticker recognition: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
        print(f"[OK] Full parsing: {parse_passed}/{parse_passed+parse_failed} passed ({parse_passed*100/(parse_passed+parse_failed):.1f}%)")
        print(f"[OK] S&P 1500 specific: {sp1500_passed}/{sp1500_passed+sp1500_failed} passed")
        
        if sp1500_failures:
            print(f"\n[WARNING] Some S&P 1500 tickers not recognized: {sp1500_failures[:10]}")
            print("   This may be normal if company names aren't in alias database")
    else:
        print("\n[WARNING] S&P 500 file detected - S&P 1500 file not found")
        print("   Please create data/tickers/universe_sp1500.txt with all 1500 tickers")
        print("   The system will automatically use it once the file exists")

if __name__ == "__main__":
    main()

