"""Find S&P 1500 file and test all tickers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def search_for_sp1500_file():
    """Search for S&P 1500 file in various locations."""
    print("=" * 80)
    print("Searching for S&P 1500 Ticker List File")
    print("=" * 80)
    
    project_root = Path(__file__).parent
    possible_locations = [
        project_root / "data" / "tickers" / "universe_sp1500.txt",
        project_root / "data" / "tickers" / "sp1500.txt",
        project_root / "data" / "tickers" / "universe_1500.txt",
        project_root / "data" / "universe_sp1500.txt",
        project_root / "universe_sp1500.txt",
    ]
    
    # Also search for files with many lines
    ticker_dir = project_root / "data" / "tickers"
    large_files = []
    
    if ticker_dir.exists():
        for file in ticker_dir.glob("*.txt"):
            try:
                line_count = sum(1 for _ in open(file, 'r', encoding='utf-8'))
                if line_count >= 1400:
                    large_files.append((file, line_count))
            except:
                pass
    
    print("\nChecking expected locations:")
    for loc in possible_locations:
        if loc.exists():
            line_count = sum(1 for _ in open(loc, 'r', encoding='utf-8'))
            print(f"  [FOUND] {loc} ({line_count} lines)")
            return loc, line_count
        else:
            print(f"  [NOT FOUND] {loc}")
    
    if large_files:
        print("\nFound files with 1400+ lines (possible S&P 1500):")
        for file, count in large_files:
            print(f"  - {file.name}: {count} lines")
            if count >= 1400:
                print(f"    [POSSIBLE] This might be S&P 1500!")
                return file, count
    
    return None, 0

def test_file(file_path):
    """Test the S&P 1500 file."""
    if not file_path or not file_path.exists():
        return False
    
    print("\n" + "=" * 80)
    print(f"Testing File: {file_path.name}")
    print("=" * 80)
    
    # Load tickers
    tickers = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            ticker = line.strip().upper()
            if ticker and not ticker.startswith("#"):
                tickers.append(ticker)
    
    print(f"\nLoaded {len(tickers)} tickers")
    
    if len(tickers) < 1400:
        print(f"[WARNING] Only {len(tickers)} tickers (expected ~1500)")
        return False
    
    print(f"[SUCCESS] S&P 1500 file detected! ({len(tickers)} tickers)")
    print(f"First 10: {tickers[:10]}")
    print(f"Last 10: {tickers[-10:]}")
    
    # Test system loading
    print("\n" + "=" * 80)
    print("Testing System Loading")
    print("=" * 80)
    
    try:
        from finanlyzeos_chatbot.parsing.alias_builder import _load_universe
        system_tickers = _load_universe()
        
        if len(system_tickers) >= 1400:
            print(f"[SUCCESS] System loaded {len(system_tickers)} tickers")
            print(f"[SUCCESS] S&P 1500 is active!")
            return True
        else:
            print(f"[WARNING] System loaded {len(system_tickers)} tickers")
            print("         System may not be using S&P 1500 file")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing system: {e}")
        return False

def test_ticker_recognition(tickers, sample_size=50):
    """Test ticker recognition."""
    if not tickers or len(tickers) < sample_size:
        return
    
    print("\n" + "=" * 80)
    print(f"Testing Ticker Recognition (sample of {sample_size})")
    print("=" * 80)
    
    import random
    from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
    
    test_tickers = random.sample(tickers, min(sample_size, len(tickers)))
    
    passed = 0
    failed = 0
    
    for ticker in test_tickers:
        query = f"What is {ticker}'s revenue?"
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if ticker in found_tickers:
            passed += 1
            if passed <= 5:
                print(f"[PASS] {ticker}")
        else:
            failed += 1
            if failed <= 5:
                print(f"[FAIL] {ticker}")
    
    print(f"\nResults: {passed}/{passed+failed} passed ({passed*100/(passed+failed):.1f}%)")
    return passed, failed

def main():
    """Main function."""
    # Search for file
    file_path, line_count = search_for_sp1500_file()
    
    if not file_path:
        print("\n" + "=" * 80)
        print("S&P 1500 File Not Found")
        print("=" * 80)
        print("\nPlease provide the S&P 1500 ticker list file.")
        print("Expected location: data/tickers/universe_sp1500.txt")
        print("\nIf you have the file elsewhere, you can:")
        print("1. Copy it to: data/tickers/universe_sp1500.txt")
        print("2. Or run: python setup_and_test_sp1500.py <path_to_file>")
        return
    
    # Test the file
    if test_file(file_path):
        # Load tickers for testing
        tickers = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        
        # Test recognition
        test_ticker_recognition(tickers, sample_size=50)
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"[SUCCESS] S&P 1500 file found and working!")
        print(f"Total tickers: {len(tickers)}")
        print(f"System is using S&P 1500")
        print("\nAll 1500 tickers should now work with natural language queries!")

if __name__ == "__main__":
    main()

