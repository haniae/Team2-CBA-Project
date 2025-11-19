"""Setup S&P 1500 ticker list - combines S&P 500 with additional sources."""

import sys
from pathlib import Path
import requests

def load_sp500():
    """Load S&P 500 from existing file."""
    sp500_path = Path(__file__).parent / "data" / "tickers" / "universe_sp500.txt"
    if sp500_path.exists():
        tickers = []
        with open(sp500_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        return sorted(set(tickers))
    return []

def fetch_yahoo_sp1500():
    """Try to fetch S&P 1500 from Yahoo Finance or similar."""
    # Yahoo Finance doesn't have direct API, but we can try other methods
    return None

def create_sp1500_file(sp500_tickers, additional_tickers=None):
    """Create S&P 1500 file."""
    all_tickers = set(sp500_tickers)
    
    if additional_tickers:
        all_tickers.update(additional_tickers)
    
    output_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ticker in sorted(all_tickers):
            f.write(f"{ticker}\n")
    
    return len(all_tickers), output_path

def main():
    """Main setup function."""
    print("=" * 80)
    print("S&P 1500 Setup")
    print("=" * 80)
    
    # Load S&P 500
    print("\n1. Loading S&P 500 tickers...")
    sp500 = load_sp500()
    print(f"   Loaded {len(sp500)} S&P 500 tickers")
    
    if len(sp500) < 400:
        print("   [WARNING] S&P 500 file seems incomplete")
    
    # For now, create file with S&P 500
    # User can manually add S&P 400 and 600 later
    print("\n2. Creating S&P 1500 file...")
    count, file_path = create_sp1500_file(sp500)
    
    print(f"\n[SUCCESS] Created {file_path}")
    print(f"   Total tickers: {count}")
    
    if count < 1400:
        print(f"\n[INFO] File created with {count} tickers (S&P 500)")
        print("   To complete S&P 1500, you need to add:")
        print("   - S&P 400 (Mid-Cap): ~400 tickers")
        print("   - S&P 600 (Small-Cap): ~600 tickers")
        print("\n   Options:")
        print("   1. Manually add tickers to the file")
        print("   2. Download from S&P Dow Jones Indices website")
        print("   3. Use ETF holdings (SPTM ticker)")
        print("   4. Use financial data APIs")
    
    print("\n3. Testing the file...")
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from finanlyzeos_chatbot.parsing.alias_builder import _load_universe
        loaded = _load_universe()
        print(f"   System loaded {len(loaded)} tickers")
        
        if len(loaded) == count:
            print("   [SUCCESS] System is using the new file!")
        else:
            print(f"   [INFO] System loaded {len(loaded)} (may be using different file)")
    except Exception as e:
        print(f"   [ERROR] Could not test: {e}")
    
    print("\n" + "=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("1. Add S&P 400 and S&P 600 tickers to complete the list")
    print("2. Run: python test_sp1500_comprehensive.py")
    print("3. Verify all tickers work with natural language queries")

if __name__ == "__main__":
    main()

