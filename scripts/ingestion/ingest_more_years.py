#!/usr/bin/env python
"""Quick script to re-ingest with more historical years."""

import sys
from pathlib import Path
from finanlyzeos_chatbot import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from finanlyzeos_chatbot.data_ingestion import ingest_live_tickers
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe

def main():
    """Re-ingest existing companies with extended history."""
    
    # Configuration
    YEARS = 25  # Fetch 25 years of data (back to ~2000)
    CHUNK_SIZE = 10  # Smaller chunks for better progress visibility
    
    print("=" * 80)
    print(f"DATA INGESTION - {YEARS} YEARS OF HISTORICAL DATA")
    print("=" * 80)
    print()
    
    settings = load_settings()
    
    # Option 1: Load from a specific universe file
    universe_file = "data/tickers/universe_sp500.txt"
    
    if Path(universe_file).exists():
        with open(universe_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"Loaded {len(tickers)} tickers from {universe_file}")
    else:
        # Fallback to predefined universe
        tickers = load_ticker_universe("sp500")
        print(f"Loaded {len(tickers)} tickers from sp500 universe")
    
    # Remove duplicates and sort
    tickers = sorted(set(tickers))
    
    print(f"Will ingest {len(tickers)} tickers with {YEARS} years of history")
    print(f"Chunk size: {CHUNK_SIZE} tickers per batch")
    print()
    
    total_batches = (len(tickers) + CHUNK_SIZE - 1) // CHUNK_SIZE
    completed_count = 0
    failed_tickers = []
    
    for batch_idx in range(total_batches):
        start = batch_idx * CHUNK_SIZE
        chunk = tickers[start:start + CHUNK_SIZE]
        
        print(f"[{batch_idx + 1}/{total_batches}] Processing {len(chunk)} tickers: {chunk}")
        
        try:
            report = ingest_live_tickers(settings, chunk, years=YEARS)
            completed_count += len(report.companies)
            print(f"  ✓ Loaded {report.records_loaded} records for: {', '.join(report.companies)}")
        except Exception as exc:
            print(f"  ✗ Batch failed: {exc}")
            failed_tickers.extend(chunk)
            continue
        
        # Show progress
        progress_pct = (completed_count / len(tickers)) * 100
        print(f"  Progress: {completed_count}/{len(tickers)} ({progress_pct:.1f}%)")
        print()
    
    print("=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
    print(f"Successfully ingested: {completed_count}/{len(tickers)} tickers")
    
    if failed_tickers:
        print(f"\nFailed tickers ({len(failed_tickers)}):")
        for ticker in failed_tickers:
            print(f"  - {ticker}")
    
    print("\nRefreshing analytics metrics...")
    AnalyticsEngine(settings).refresh_metrics(force=True)
    print("✓ Analytics cache refreshed")
    print("\nDone!")

if __name__ == "__main__":
    main()

