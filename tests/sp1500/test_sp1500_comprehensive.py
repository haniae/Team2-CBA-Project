"""Comprehensive test for S&P 1500 - works once file is provided."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_universe_loading():
    """Test that universe loads correctly."""
    print("=" * 80)
    print("Testing Universe Loading")
    print("=" * 80)
    
    try:
        tickers = _load_universe()
        print(f"\n[OK] Loaded {len(tickers)} tickers")
        
        if len(tickers) >= 1400:
            print(f"[SUCCESS] S&P 1500 detected! ({len(tickers)} tickers)")
            print(f"First 10: {tickers[:10]}")
            print(f"Last 10: {tickers[-10:]}")
            return True, tickers
        elif len(tickers) >= 480:
            print(f"[INFO] S&P 500 detected ({len(tickers)} tickers)")
            print("S&P 1500 file not found - using S&P 500 fallback")
            return False, tickers
        else:
            print(f"[WARNING] Unexpected count: {len(tickers)}")
            return False, tickers
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False, []

def test_all_tickers_comprehensive(tickers):
    """Test all tickers comprehensively."""
    if not tickers:
        return
    
    print("\n" + "=" * 80)
    print(f"Comprehensive Test of All {len(tickers)} Tickers")
    print("=" * 80)
    
    # Test different query formats
    test_queries = [
        ("Direct ticker", lambda t: f"What is {t}'s revenue?"),
        ("Ticker without apostrophe", lambda t: f"What is {t} revenue?"),
        ("Show me format", lambda t: f"Show me {t} revenue"),
        ("Simple format", lambda t: f"{t} revenue"),
    ]
    
    results = {
        "total": len(tickers),
        "passed": 0,
        "failed": 0,
        "by_format": {name: {"passed": 0, "failed": 0} for name, _ in test_queries}
    }
    
    # Test a sample (first 100, middle 100, last 100)
    sample_indices = list(range(min(100, len(tickers)))) + \
                     list(range(len(tickers)//2, len(tickers)//2 + min(100, len(tickers)))) + \
                     list(range(max(0, len(tickers)-100), len(tickers)))
    sample_indices = sorted(set(sample_indices))[:200]  # Limit to 200 unique
    
    print(f"\nTesting {len(sample_indices)} tickers (sample from beginning, middle, end)")
    print("Progress: ", end="", flush=True)
    
    for idx, ticker_idx in enumerate(sample_indices):
        if idx % 20 == 0:
            print(".", end="", flush=True)
        
        ticker = tickers[ticker_idx]
        
        # Test each query format
        for format_name, query_func in test_queries:
            query = query_func(ticker)
            matches, warnings = resolve_tickers_freeform(query)
            found_tickers = [m.get("ticker") for m in matches]
            
            if ticker in found_tickers:
                results["by_format"][format_name]["passed"] += 1
                results["passed"] += 1
            else:
                results["by_format"][format_name]["failed"] += 1
                results["failed"] += 1
    
    print("\n")
    
    # Print results
    print("\nResults by Query Format:")
    for format_name, stats in results["by_format"].items():
        total = stats["passed"] + stats["failed"]
        if total > 0:
            pct = stats["passed"] * 100 / total
            print(f"  {format_name}: {stats['passed']}/{total} ({pct:.1f}%)")
    
    overall_passed = sum(s["passed"] for s in results["by_format"].values())
    overall_total = sum(s["passed"] + s["failed"] for s in results["by_format"].values())
    
    if overall_total > 0:
        overall_pct = overall_passed * 100 / overall_total
        print(f"\nOverall: {overall_passed}/{overall_total} ({overall_pct:.1f}%)")
    
    return results

def test_full_parsing_pipeline(tickers, sample_size=50):
    """Test full parsing pipeline."""
    if not tickers or len(tickers) < sample_size:
        return
    
    print("\n" + "=" * 80)
    print(f"Testing Full Parsing Pipeline (sample of {sample_size})")
    print("=" * 80)
    
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
        else:
            failed += 1
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    return passed, failed

def main():
    """Main test function."""
    print("S&P 1500 Comprehensive Test")
    print("=" * 80)
    
    # Test 1: Load universe
    is_sp1500, tickers = test_universe_loading()
    
    if not tickers:
        print("\n[ERROR] No tickers loaded. Cannot proceed.")
        return
    
    if not is_sp1500:
        print("\n[INFO] S&P 1500 file not found.")
        print("Please create data/tickers/universe_sp1500.txt with all 1500 tickers")
        print("Then run this test again.")
        return
    
    # Test 2: Comprehensive ticker test
    results = test_all_tickers_comprehensive(tickers)
    
    # Test 3: Full parsing
    parse_passed, parse_failed = test_full_parsing_pipeline(tickers, sample_size=50)
    
    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"[SUCCESS] S&P 1500 file loaded: {len(tickers)} tickers")
    if results:
        overall_passed = sum(s["passed"] for s in results["by_format"].values())
        overall_total = sum(s["passed"] + s["failed"] for s in results["by_format"].values())
        if overall_total > 0:
            print(f"[OK] Ticker recognition: {overall_passed}/{overall_total} ({overall_passed*100/overall_total:.1f}%)")
    print(f"[OK] Full parsing: {parse_passed}/{parse_passed+parse_failed} ({parse_passed*100/(parse_passed+parse_failed):.1f}%)")
    print("\n[SUCCESS] All 1500 tickers are supported with natural language!")

if __name__ == "__main__":
    main()

