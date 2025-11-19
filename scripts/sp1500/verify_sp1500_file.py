"""Helper script to verify S&P 1500 file exists and test all tickers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_file_exists():
    """Check if S&P 1500 file exists."""
    sp1500_path = Path(__file__).parent / "data" / "tickers" / "universe_sp1500.txt"
    sp500_path = Path(__file__).parent / "data" / "tickers" / "universe_sp500.txt"
    
    print("=" * 80)
    print("S&P 1500 File Verification")
    print("=" * 80)
    
    if sp1500_path.exists():
        print(f"\n[FOUND] S&P 1500 file: {sp1500_path}")
        
        # Count tickers
        tickers = []
        with open(sp1500_path, 'r', encoding='utf-8') as f:
            for line in f:
                ticker = line.strip().upper()
                if ticker and not ticker.startswith("#"):
                    tickers.append(ticker)
        
        print(f"[OK] Found {len(tickers)} tickers in file")
        
        if len(tickers) >= 1400:
            print(f"[SUCCESS] S&P 1500 file looks correct! ({len(tickers)} tickers)")
            print(f"First 10: {tickers[:10]}")
            print(f"Last 10: {tickers[-10:]}")
            return True, tickers
        else:
            print(f"[WARNING] File has {len(tickers)} tickers (expected ~1500)")
            return False, tickers
    else:
        print(f"\n[NOT FOUND] S&P 1500 file: {sp1500_path}")
        print(f"[FOUND] S&P 500 file: {sp500_path}")
        print("\nTo add S&P 1500 support:")
        print(f"1. Create file: {sp1500_path}")
        print("2. Add all 1500 tickers (one per line)")
        print("3. Run this script again to verify")
        return False, []

def test_system_loading():
    """Test that system loads the file correctly."""
    print("\n" + "=" * 80)
    print("Testing System File Loading")
    print("=" * 80)
    
    try:
        from finanlyzeos_chatbot.parsing.alias_builder import _load_universe
        tickers = _load_universe()
        
        print(f"[OK] System loaded {len(tickers)} tickers")
        
        if len(tickers) >= 1400:
            print(f"[SUCCESS] System is using S&P 1500! ({len(tickers)} tickers)")
            return True, tickers
        elif len(tickers) >= 480:
            print(f"[INFO] System is using S&P 500 ({len(tickers)} tickers)")
            print("       S&P 1500 file not found or not being used")
            return False, tickers
        else:
            print(f"[WARNING] Unexpected ticker count: {len(tickers)}")
            return False, tickers
    except Exception as e:
        print(f"[ERROR] Error loading universe: {e}")
        return False, []

if __name__ == "__main__":
    # Check if file exists
    file_exists, file_tickers = check_file_exists()
    
    # Test system loading
    system_loaded, system_tickers = test_system_loading()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if file_exists and system_loaded:
        print("[SUCCESS] S&P 1500 file exists and system is using it!")
        print(f"Total tickers: {len(system_tickers)}")
        print("\nNext step: Run test_all_sp1500_tickers.py to verify all tickers work")
    elif file_exists and not system_loaded:
        print("[WARNING] S&P 1500 file exists but system isn't loading it")
        print("Check that the file is in the correct location:")
        print("  data/tickers/universe_sp1500.txt")
    elif not file_exists:
        print("[INFO] S&P 1500 file not found")
        print("Please create data/tickers/universe_sp1500.txt with all 1500 tickers")
        print("The system will automatically use it once created")

