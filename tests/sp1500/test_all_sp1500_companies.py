"""Comprehensive test to verify all S&P 1500 companies are understood by the chatbot."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, load_aliases
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def load_ticker_names():
    """Load company names from ticker_names.md."""
    names_path = Path(__file__).parent / "docs" / "guides" / "ticker_names.md"
    if not names_path.exists():
        return {}
    
    name_map = {}
    pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z0-9.-]+)\)")
    
    with open(names_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                ticker = match.group("ticker").upper()
                name = match.group("name").strip()
                name_map[ticker] = name
    
    return name_map

def test_ticker_symbols(tickers, sample_size=None):
    """Test recognition using ticker symbols."""
    print("=" * 80)
    print("Testing Ticker Symbol Recognition")
    print("=" * 80)
    
    if sample_size:
        import random
        test_tickers = random.sample(tickers, min(sample_size, len(tickers)))
    else:
        test_tickers = tickers
    
    passed = 0
    failed = 0
    failures = []
    
    print(f"\nTesting {len(test_tickers)} tickers...")
    print("Progress: ", end="", flush=True)
    
    for idx, ticker in enumerate(test_tickers):
        if idx % 100 == 0 and idx > 0:
            print(".", end="", flush=True)
        
        query = f"What is {ticker}'s revenue?"
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if ticker in found_tickers:
            passed += 1
        else:
            failed += 1
            if len(failures) < 20:  # Keep first 20 failures
                failures.append(ticker)
    
    print("\n")
    print(f"Results: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    
    if failures:
        print(f"\nFirst 20 failures: {failures[:20]}")
    
    return passed, failed, failures

def test_company_names(tickers, name_map, sample_size=None):
    """Test recognition using company names."""
    print("\n" + "=" * 80)
    print("Testing Company Name Recognition")
    print("=" * 80)
    
    # Get tickers that have names
    tickers_with_names = [t for t in tickers if t in name_map]
    
    if sample_size:
        import random
        test_tickers = random.sample(tickers_with_names, min(sample_size, len(tickers_with_names)))
    else:
        test_tickers = tickers_with_names
    
    print(f"\nTesting {len(test_tickers)} companies with names...")
    print("Progress: ", end="", flush=True)
    
    passed = 0
    failed = 0
    failures = []
    
    for idx, ticker in enumerate(test_tickers):
        if idx % 100 == 0 and idx > 0:
            print(".", end="", flush=True)
        
        company_name = name_map[ticker]
        
        # Test different query formats
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
                break
        
        if found:
            passed += 1
        else:
            failed += 1
            if len(failures) < 20:
                failures.append((ticker, company_name))
    
    print("\n")
    print(f"Results: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    
    if failures:
        print(f"\nFirst 20 failures:")
        for ticker, name in failures[:20]:
            print(f"  {ticker}: {name}")
    
    return passed, failed, failures

def test_full_parsing(tickers, sample_size=100):
    """Test full parsing pipeline."""
    print("\n" + "=" * 80)
    print(f"Testing Full Parsing Pipeline (sample of {sample_size})")
    print("=" * 80)
    
    import random
    test_tickers = random.sample(tickers, min(sample_size, len(tickers)))
    
    passed = 0
    failed = 0
    
    print("Progress: ", end="", flush=True)
    
    for idx, ticker in enumerate(test_tickers):
        if idx % 20 == 0:
            print(".", end="", flush=True)
        
        query = f"What is {ticker}'s revenue?"
        structured = parse_to_structured(query)
        
        found_tickers = [t.get("ticker") for t in structured.get("tickers", [])]
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if ticker in found_tickers and "revenue" in found_metrics:
            passed += 1
        else:
            failed += 1
    
    print("\n")
    print(f"Results: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    
    return passed, failed

def main():
    """Main test function."""
    print("=" * 80)
    print("Comprehensive S&P 1500 Company Recognition Test")
    print("=" * 80)
    
    # Load tickers
    print("\n1. Loading S&P 1500 tickers...")
    tickers = _load_universe()
    print(f"   Loaded {len(tickers)} tickers")
    
    if len(tickers) < 1400:
        print(f"   [WARNING] Only {len(tickers)} tickers (expected ~1500)")
    
    # Load company names
    print("\n2. Loading company names...")
    name_map = load_ticker_names()
    print(f"   Found names for {len(name_map)} tickers")
    
    # Load aliases to verify they're built
    print("\n3. Loading aliases...")
    alias_map = load_aliases()
    print(f"   Loaded aliases for {len(alias_map)} tickers")
    
    # Test ticker symbols (test all)
    print("\n" + "=" * 80)
    ticker_passed, ticker_failed, ticker_failures = test_ticker_symbols(tickers)
    
    # Test company names (test all)
    name_passed, name_failed, name_failures = test_company_names(tickers, name_map)
    
    # Test full parsing (sample)
    parse_passed, parse_failed = test_full_parsing(tickers, sample_size=200)
    
    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total tickers in universe: {len(tickers)}")
    print(f"Tickers with company names: {len(name_map)}")
    print(f"Tickers with aliases: {len(alias_map)}")
    print()
    print("Recognition Results:")
    print(f"  Ticker symbols: {ticker_passed}/{ticker_passed+ticker_failed} ({ticker_passed*100/(ticker_passed+ticker_failed):.1f}%)")
    print(f"  Company names: {name_passed}/{name_passed+name_failed} ({name_passed*100/(name_passed+name_failed):.1f}%)")
    print(f"  Full parsing: {parse_passed}/{parse_passed+parse_failed} ({parse_passed*100/(parse_passed+parse_failed):.1f}%)")
    print()
    
    if ticker_passed + ticker_failed == len(tickers):
        print("[SUCCESS] All tickers tested!")
    else:
        print(f"[INFO] Tested {ticker_passed + ticker_failed} out of {len(tickers)} tickers")
    
    if ticker_passed / (ticker_passed + ticker_failed) >= 0.95:
        print("[SUCCESS] 95%+ ticker symbol recognition - Excellent!")
    elif ticker_passed / (ticker_passed + ticker_failed) >= 0.80:
        print("[GOOD] 80%+ ticker symbol recognition - Good coverage")
    else:
        print("[WARNING] Ticker symbol recognition below 80% - may need improvements")
    
    if name_passed / (name_passed + name_failed) >= 0.80:
        print("[SUCCESS] 80%+ company name recognition - Good!")
    else:
        print("[INFO] Company name recognition could be improved")
    
    print("\n[CONCLUSION]")
    if ticker_passed / (ticker_passed + ticker_failed) >= 0.90:
        print("[SUCCESS] The chatbot understands most/all S&P 1500 companies via ticker symbols")
    else:
        print("[WARNING] Some companies may not be recognized - check failures above")
    
    if name_passed / (name_passed + name_failed) >= 0.70:
        print("[SUCCESS] The chatbot understands most company names")
    else:
        print("[INFO] Company name recognition needs improvement")

if __name__ == "__main__":
    main()

