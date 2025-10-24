#!/usr/bin/env python3
"""
Check ingestion status and available universes.
Usage: python check_ingestion_status.py
"""

import json
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.ticker_universe import load_ticker_universe, available_universes

def main():
    """Check ingestion status and show available options."""
    print("=== BenchmarkOS Ingestion Status ===\n")
    
    # Show available universes
    print("Available universes:")
    for universe in available_universes():
        tickers = load_ticker_universe(universe)
        print(f"  - {universe}: {len(tickers)} tickers")
    
    # Check progress file
    progress_file = Path(".ingestion_progress.json")
    if progress_file.exists():
        try:
            data = json.loads(progress_file.read_text())
            completed = set(data.get("completed", []))
            print(f"\nProgress file found: {len(completed)} tickers completed")
            
            if completed:
                print("Sample completed tickers:")
                for ticker in sorted(list(completed))[:10]:
                    print(f"  - {ticker}")
                if len(completed) > 10:
                    print(f"  ... and {len(completed) - 10} more")
        except json.JSONDecodeError:
            print("\nProgress file exists but is corrupted")
    else:
        print("\nNo progress file found - no previous ingestion")
    
    print("\n=== Available Commands ===")
    print("1. Ingest all S&P 500 at once:")
    print("   python ingest_sp500.py")
    print("\n2. Ingest S&P 500 with chunking (recommended):")
    print("   python ingest_sp500_chunked.py")
    print("\n3. Use original script with custom parameters:")
    print("   python scripts/ingestion/ingest_universe.py --universe sp500 --years 5 --chunk-size 25 --sleep 2 --resume")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
