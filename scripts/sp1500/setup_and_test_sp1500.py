"""Setup and test S&P 1500 support - helps locate file or create it."""

import sys
from pathlib import Path

def find_ticker_files():
    """Search for ticker list files in the project."""
    print("=" * 80)
    print("Searching for S&P 1500 Ticker List File")
    print("=" * 80)
    
    project_root = Path(__file__).parent
    ticker_dir = project_root / "data" / "tickers"
    
    # Check expected location
    sp1500_path = ticker_dir / "universe_sp1500.txt"
    if sp1500_path.exists():
        print(f"\n[FOUND] S&P 1500 file at: {sp1500_path}")
        return sp1500_path
    
    # Search for files that might contain S&P 1500
    print(f"\nSearching in: {ticker_dir}")
    print(f"\nFiles found:")
    for file in ticker_dir.glob("*.txt"):
        size = file.stat().st_size
        line_count = sum(1 for _ in open(file, 'r', encoding='utf-8'))
        print(f"  - {file.name}: {line_count} lines, {size} bytes")
        
        # Check if it might be S&P 1500
        if line_count >= 1400:
            print(f"    [POSSIBLE] This might be S&P 1500 ({line_count} lines)")
    
    # Search entire project for files with "1500" in name
    print(f"\nSearching entire project for files with '1500' in name...")
    found_files = []
    for file in project_root.rglob("*1500*"):
        if file.is_file() and file.suffix in ['.txt', '.csv', '.json']:
            found_files.append(file)
            print(f"  - {file.relative_to(project_root)}")
    
    if not found_files:
        print("  [NOT FOUND] No files with '1500' in name")
    
    return None

def check_file_format(file_path):
    """Check if a file looks like a ticker list."""
    if not file_path or not file_path.exists():
        return False, 0
    
    tickers = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    # Check if it looks like a ticker (1-5 uppercase letters, maybe with dash/dot)
                    if len(ticker) <= 6 and ticker.replace('-', '').replace('.', '').isalnum():
                        tickers.append(ticker)
    except Exception as e:
        print(f"[ERROR] Error reading file: {e}")
        return False, 0
    
    return True, len(tickers)

def setup_sp1500_file(source_file=None):
    """Help set up S&P 1500 file."""
    print("\n" + "=" * 80)
    print("Setting Up S&P 1500 File")
    print("=" * 80)
    
    target_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    
    if source_file and Path(source_file).exists():
        print(f"\n[INFO] Copying from: {source_file}")
        print(f"[INFO] To: {target_path}")
        
        # Read source
        tickers = []
        with open(source_file, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        
        # Write to target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            for ticker in tickers:
                f.write(f"{ticker}\n")
        
        print(f"[SUCCESS] Created S&P 1500 file with {len(tickers)} tickers")
        return True
    else:
        print(f"\n[INFO] To create S&P 1500 file:")
        print(f"1. Get S&P 1500 ticker list (S&P 500 + S&P 400 + S&P 600)")
        print(f"2. Save as: {target_path}")
        print(f"3. Format: One ticker per line (e.g., AAPL, MSFT, etc.)")
        print(f"4. Run this script again to verify")
        return False

def main():
    """Main function."""
    print("S&P 1500 Setup and Verification")
    print("=" * 80)
    
    # Search for file
    found_file = find_ticker_files()
    
    # Check if S&P 1500 file exists in expected location
    expected_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    
    if expected_path.exists():
        print(f"\n" + "=" * 80)
        print("S&P 1500 File Found - Verifying")
        print("=" * 80)
        
        is_valid, ticker_count = check_file_format(expected_path)
        if is_valid:
            print(f"[SUCCESS] File is valid with {ticker_count} tickers")
            
            if ticker_count >= 1400:
                print(f"[SUCCESS] S&P 1500 file looks correct!")
                print("\nNext steps:")
                print("1. Run: python test_all_sp1500_tickers.py")
                print("2. This will test that all tickers work with natural language")
            else:
                print(f"[WARNING] File has {ticker_count} tickers (expected ~1500)")
        else:
            print("[ERROR] File format is invalid")
    else:
        print(f"\n" + "=" * 80)
        print("S&P 1500 File Not Found")
        print("=" * 80)
        
        # Check if user provided a source file
        if len(sys.argv) > 1:
            source = sys.argv[1]
            setup_sp1500_file(source)
        else:
            print("\n[INFO] S&P 1500 file not found in expected location")
            print(f"Expected: {expected_path}")
            print("\nOptions:")
            print("1. If you have the file elsewhere, run:")
            print(f"   python setup_and_test_sp1500.py <path_to_your_file>")
            print("2. Or manually create the file at the expected location")
            print("3. Then run: python test_all_sp1500_tickers.py")

if __name__ == "__main__":
    main()

