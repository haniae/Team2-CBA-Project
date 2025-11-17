#!/usr/bin/env python3
"""
Ingest 20+ years of S&P 500 financial data.
This will dramatically expand the database with historical data.
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import List

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import AnalyticsEngine, load_settings
from finanlyzeos_chatbot.data_ingestion import ingest_live_tickers
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe

def chunked(iterable, size: int):
    """Yield fixed-size chunks from the iterable."""
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

def load_progress(progress_file: Path) -> set:
    """Read the ingestion progress checkpoint metadata from disk."""
    if not progress_file.exists():
        return set()
    try:
        data = json.loads(progress_file.read_text())
        return set(data.get("completed_20years", []))
    except json.JSONDecodeError:
        return set()

def save_progress(progress_file: Path, completed: set) -> None:
    """Persist the current checkpoint metadata so runs can resume later."""
    # Read existing progress to preserve other keys
    existing = {}
    if progress_file.exists():
        try:
            existing = json.loads(progress_file.read_text())
        except:
            pass
    
    existing["completed_20years"] = sorted(completed)
    progress_file.write_text(json.dumps(existing, indent=2))

def main():
    """Ingest S&P 500 tickers with 20+ years of data."""
    print("=== S&P 500 Data Ingestion (20+ YEARS) ===\n")
    
    print("📊 Loading S&P 500 tickers...")
    tickers = load_ticker_universe("sp500")
    print(f"Found {len(tickers)} S&P 500 tickers")
    
    print("⚙️ Loading settings...")
    settings = load_settings()
    
    # Configuration for 20+ years
    chunk_size = 15  # Smaller chunks for larger time period
    sleep_seconds = 2.5  # Longer sleep to respect rate limits
    years = 25  # Request 25 years to get 20+ years of data
    progress_file = Path(".ingestion_progress.json")
    
    # Load existing progress for 20-year ingestion
    completed = load_progress(progress_file)
    todo = [ticker for ticker in tickers if ticker not in completed]
    
    print(f"\n📈 Progress Status:")
    print(f"  - Total tickers: {len(tickers)}")
    if completed:
        print(f"  - Already completed (20+ years): {len(completed)}")
    print(f"  - Remaining: {len(todo)}")
    print(f"  - Years requested: {years}")
    
    if not todo:
        print("\n✅ All tickers already ingested with 20+ years!")
        print("Run 'python check_database_simple.py' to verify")
        return 0
    
    failures = []
    total_chunks = math.ceil(len(todo) / chunk_size)
    
    print(f"\n🚀 Starting deep historical ingestion...")
    print(f"  - Processing {len(todo)} tickers in {total_chunks} chunks")
    print(f"  - Each chunk: {chunk_size} tickers")
    print(f"  - Data period: {years} years (will get ~20+ years actual data)")
    print(f"  - Estimated time: {total_chunks * 3} minutes ({total_chunks * 3 / 60:.1f} hours)")
    print(f"\n⚠️  This is a DEEP ingestion - it will take several hours!")
    print(f"  - You can stop anytime (Ctrl+C) and resume later")
    print(f"  - Progress is saved after each chunk\n")
    
    records_added = 0
    
    for chunk_index, chunk in enumerate(chunked(todo, chunk_size), start=1):
        print(f"\n[{chunk_index}/{total_chunks}] Processing {len(chunk)} tickers: {chunk}")
        
        try:
            report = ingest_live_tickers(settings, chunk, years=years)
            
            # Update progress
            for ticker in report.companies:
                completed.add(ticker)
            save_progress(progress_file, completed)
            
            records_added += report.records_loaded
            print(f"  ✓ Loaded {report.records_loaded:,} records for {len(report.companies)} companies")
            print(f"  ✓ Total added so far: {records_added:,} records")
            
        except Exception as exc:
            print(f"  ✗ Failed chunk {chunk}: {exc}")
            for ticker in chunk:
                failures.append((ticker, str(exc)))
            continue
        
        # Sleep between chunks to respect rate limits
        if sleep_seconds and chunk_index < total_chunks:
            print(f"  ⏳ Sleeping {sleep_seconds}s before next chunk...")
            time.sleep(sleep_seconds)
        
        # Progress update
        completion_pct = (len(completed) / len(tickers)) * 100
        print(f"  📊 Overall progress: {len(completed)}/{len(tickers)} ({completion_pct:.1f}%)")
    
    # Final report
    if failures:
        print(f"\n⚠️  {len(failures)} tickers failed:")
        for ticker, reason in failures[:10]:  # Show first 10
            print(f"  - {ticker}: {reason}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
    else:
        print("\n✅ All tickers ingested successfully!")
    
    print(f"\n📊 Final Status:")
    print(f"  - Completed: {len(completed)}/{len(tickers)} tickers")
    print(f"  - Total records added: {records_added:,}")
    print(f"  - Progress saved to: {progress_file}")
    
    print(f"\n🔄 Refreshing cached metrics...")
    try:
        engine = AnalyticsEngine(settings)
        engine.refresh_metrics(force=True)
        print("  ✅ Metrics refreshed")
    except Exception as e:
        print(f"  ⚠️ Could not refresh metrics: {e}")
    
    print(f"\n🎉 20+ year ingestion completed!")
    print(f"Total new records: {records_added:,}")
    print(f"\nNext step: python check_database_simple.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

