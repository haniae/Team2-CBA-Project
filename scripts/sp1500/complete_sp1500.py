"""Complete S&P 1500 by adding S&P 400 and 600 tickers."""

import sys
from pathlib import Path
import requests
import re

def load_existing_sp1500():
    """Load existing S&P 1500 file."""
    sp1500_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    if sp1500_path.exists():
        tickers = []
        with open(sp1500_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        return set(tickers)
    return set()

def fetch_from_wikipedia(url, expected_count):
    """Fetch tickers from Wikipedia page."""
    try:
        print(f"   Fetching from Wikipedia...")
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            # Look for ticker patterns in table cells
            patterns = [
                r'<td[^>]*><a[^>]*>([A-Z]{1,5})</a></td>',
                r'<td[^>]*>([A-Z]{1,5})</td>',
                r'ticker["\']?\s*[:=]\s*["\']?([A-Z]{1,5})["\']?',
            ]
            tickers = set()
            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                tickers.update(m.upper() for m in matches if len(m) <= 5 and m.isalpha())
            
            if len(tickers) >= expected_count * 0.8:  # At least 80% of expected
                print(f"   Found {len(tickers)} tickers")
                return tickers
            else:
                print(f"   Found only {len(tickers)} tickers (expected ~{expected_count})")
    except Exception as e:
        print(f"   Error: {e}")
    return set()

def get_sp400_tickers():
    """Get S&P 400 tickers."""
    print("\nFetching S&P 400 (Mid-Cap) tickers...")
    # Try multiple sources
    tickers = set()
    
    # Try Wikipedia
    urls = [
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "https://en.wikipedia.org/wiki/S%26P_400",
    ]
    for url in urls:
        found = fetch_from_wikipedia(url, 400)
        if found:
            tickers.update(found)
            if len(tickers) >= 350:
                break
    
    return tickers

def get_sp600_tickers():
    """Get S&P 600 tickers."""
    print("\nFetching S&P 600 (Small-Cap) tickers...")
    tickers = set()
    
    # Try Wikipedia
    urls = [
        "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        "https://en.wikipedia.org/wiki/S%26P_600",
    ]
    for url in urls:
        found = fetch_from_wikipedia(url, 600)
        if found:
            tickers.update(found)
            if len(tickers) >= 550:
                break
    
    return tickers

def save_sp1500(all_tickers):
    """Save complete S&P 1500 file."""
    output_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    sorted_tickers = sorted(all_tickers)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ticker in sorted_tickers:
            f.write(f"{ticker}\n")
    
    return len(sorted_tickers), output_path

def main():
    """Main function."""
    print("=" * 80)
    print("Completing S&P 1500 Ticker List")
    print("=" * 80)
    
    # Load existing
    existing = load_existing_sp1500()
    print(f"\nExisting tickers: {len(existing)}")
    
    # Get S&P 400
    sp400 = get_sp400_tickers()
    print(f"   S&P 400 tickers: {len(sp400)}")
    
    # Get S&P 600
    sp600 = get_sp600_tickers()
    print(f"   S&P 600 tickers: {len(sp600)}")
    
    # Combine all
    all_tickers = existing | sp400 | sp600
    
    print(f"\nTotal unique tickers: {len(all_tickers)}")
    print(f"  - Existing: {len(existing)}")
    print(f"  - S&P 400: {len(sp400)}")
    print(f"  - S&P 600: {len(sp600)}")
    print(f"  - New from S&P 400: {len(sp400 - existing)}")
    print(f"  - New from S&P 600: {len(sp600 - existing)}")
    
    # Save
    count, file_path = save_sp1500(all_tickers)
    print(f"\n[SUCCESS] Saved {count} tickers to {file_path}")
    
    if count >= 1400:
        print("[SUCCESS] S&P 1500 file is complete!")
    else:
        print(f"[INFO] File has {count} tickers (target: ~1500)")
        print("You may need to add more tickers manually or from another source")
    
    # Test
    print("\n" + "=" * 80)
    print("Testing System")
    print("=" * 80)
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from finanlyzeos_chatbot.parsing.alias_builder import _load_universe
        loaded = _load_universe()
        print(f"System loaded {len(loaded)} tickers")
        
        if len(loaded) >= 1400:
            print("[SUCCESS] S&P 1500 is active!")
        else:
            print(f"[INFO] System loaded {len(loaded)} tickers")
    except Exception as e:
        print(f"[ERROR] Could not test: {e}")
    
    print("\nNext: Run python test_sp1500_comprehensive.py")

if __name__ == "__main__":
    main()

