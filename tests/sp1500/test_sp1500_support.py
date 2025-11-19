"""Test S&P 1500 ticker support."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform

def test_current_support():
    """Test what tickers are currently supported."""
    print("=" * 80)
    print("S&P 1500 Support Analysis")
    print("=" * 80)
    
    # Check current universe
    try:
        current_tickers = _load_universe()
        print(f"\nCurrent universe file: S&P 500")
        print(f"Total tickers in universe: {len(current_tickers)}")
        print(f"\nFirst 10 tickers: {current_tickers[:10]}")
        print(f"Last 10 tickers: {current_tickers[-10:]}")
    except Exception as e:
        print(f"Error loading universe: {e}")
        return
    
    # Test some S&P 1500 tickers (mid-cap and small-cap examples)
    # S&P 1500 = S&P 500 + S&P 400 (Mid-Cap) + S&P 600 (Small-Cap)
    sp1500_test_tickers = [
        # Some mid-cap examples (S&P 400)
        "ZION", "FNB", "WAL", "CFR", "ONB",  # Regional banks
        "TECH", "ALKS", "IONS", "RGNX",  # Biotech
        # Some small-cap examples (S&P 600)
        "AAN", "ABG", "ACAD", "ACHC", "ACIW",  # Various sectors
    ]
    
    print("\n" + "=" * 80)
    print("Testing S&P 1500 Ticker Recognition")
    print("=" * 80)
    
    found = 0
    not_found = []
    
    for ticker in sp1500_test_tickers:
        query = f"What is {ticker}'s revenue?"
        matches, warnings = resolve_tickers_freeform(query)
        
        found_tickers = [m.get("ticker") for m in matches]
        if ticker in found_tickers:
            print(f"[FOUND] {ticker}")
            found += 1
        else:
            print(f"[NOT FOUND] {ticker} - Matches: {found_tickers}")
            not_found.append(ticker)
    
    print(f"\nResults: {found}/{len(sp1500_test_tickers)} S&P 1500 tickers recognized")
    print(f"Not found: {not_found}")
    
    print("\n" + "=" * 80)
    print("Conclusion")
    print("=" * 80)
    print("Current system supports: S&P 500 only")
    print("S&P 1500 support: NOT FULLY SUPPORTED")
    print("\nTo add S&P 1500 support:")
    print("1. Create universe_sp1500.txt file with all 1500 tickers")
    print("2. Update alias_builder.py to load S&P 1500 universe")
    print("3. Generate aliases for all S&P 1500 tickers")

if __name__ == "__main__":
    test_current_support()

