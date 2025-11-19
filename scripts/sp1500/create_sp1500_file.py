"""Create S&P 1500 ticker list file from multiple sources."""

import sys
from pathlib import Path
import requests
import json

def fetch_sp500_tickers():
    """Fetch S&P 500 tickers from Wikipedia."""
    print("Fetching S&P 500 tickers...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Parse HTML to extract tickers (simplified)
            import re
            # Look for ticker patterns in table
            tickers = re.findall(r'<td><a[^>]*>([A-Z]{1,5})</a></td>', response.text)
            if len(tickers) >= 400:
                print(f"Found {len(tickers)} S&P 500 tickers from Wikipedia")
                return list(set(tickers))[:500]
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
    return None

def get_sp500_from_file():
    """Get S&P 500 from existing file."""
    sp500_path = Path(__file__).parent / "data" / "tickers" / "universe_sp500.txt"
    if sp500_path.exists():
        tickers = []
        with open(sp500_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        print(f"Loaded {len(tickers)} S&P 500 tickers from file")
        return tickers
    return None

def fetch_sp400_tickers():
    """Fetch S&P 400 (Mid-Cap) tickers."""
    print("Fetching S&P 400 (Mid-Cap) tickers...")
    # Try Wikipedia or other public source
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            import re
            tickers = re.findall(r'<td><a[^>]*>([A-Z]{1,5})</a></td>', response.text)
            if len(tickers) >= 350:
                print(f"Found {len(tickers)} S&P 400 tickers")
                return list(set(tickers))[:400]
    except Exception as e:
        print(f"Error fetching S&P 400: {e}")
    return None

def fetch_sp600_tickers():
    """Fetch S&P 600 (Small-Cap) tickers."""
    print("Fetching S&P 600 (Small-Cap) tickers...")
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            import re
            tickers = re.findall(r'<td><a[^>]*>([A-Z]{1,5})</a></td>', response.text)
            if len(tickers) >= 550:
                print(f"Found {len(tickers)} S&P 600 tickers")
                return list(set(tickers))[:600]
    except Exception as e:
        print(f"Error fetching S&P 600: {e}")
    return None

def create_from_known_sources():
    """Create S&P 1500 from known ticker sources."""
    print("=" * 80)
    print("Creating S&P 1500 Ticker List")
    print("=" * 80)
    
    all_tickers = set()
    
    # Get S&P 500
    sp500 = get_sp500_from_file()
    if sp500:
        all_tickers.update(sp500)
        print(f"Added {len(sp500)} S&P 500 tickers")
    
    # Try to get S&P 400 and 600
    sp400 = fetch_sp400_tickers()
    if sp400:
        all_tickers.update(sp400)
        print(f"Added {len(sp400)} S&P 400 tickers")
    
    sp600 = fetch_sp600_tickers()
    if sp600:
        all_tickers.update(sp600)
        print(f"Added {len(sp600)} S&P 600 tickers")
    
    return sorted(all_tickers)

def create_sp1500_file(tickers):
    """Create the S&P 1500 file."""
    output_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for ticker in sorted(tickers):
            f.write(f"{ticker}\n")
    
    print(f"\n[SUCCESS] Created S&P 1500 file: {output_path}")
    print(f"Total tickers: {len(tickers)}")
    
    if len(tickers) >= 1400:
        print("[SUCCESS] S&P 1500 file created successfully!")
    else:
        print(f"[WARNING] Only {len(tickers)} tickers (expected ~1500)")
        print("You may need to add more tickers manually")

def main():
    """Main function."""
    print("S&P 1500 File Creator")
    print("=" * 80)
    
    # Try to create from known sources
    tickers = create_from_known_sources()
    
    if len(tickers) >= 1400:
        create_sp1500_file(tickers)
        print("\n[SUCCESS] S&P 1500 file created!")
        print("Now run: python test_sp1500_comprehensive.py")
    else:
        print(f"\n[INFO] Only found {len(tickers)} tickers")
        print("\nOptions:")
        print("1. The file will be created with available tickers")
        print("2. You can manually add more tickers to reach 1500")
        print("3. Or provide a complete S&P 1500 list from another source")
        
        if tickers:
            create_sp1500_file(tickers)
            print(f"\n[INFO] Created file with {len(tickers)} tickers")
            print("You can edit data/tickers/universe_sp1500.txt to add more")

if __name__ == "__main__":
    main()

