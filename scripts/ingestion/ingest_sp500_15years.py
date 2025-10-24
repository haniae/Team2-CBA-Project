#!/usr/bin/env python3
"""
Simple S&P 500 ingestion script for team members.
Ingests 15 years of data for all S&P 500 companies.
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import List

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot import AnalyticsEngine, load_settings
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers
from benchmarkos_chatbot.ticker_universe import load_ticker_universe

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
        return set(data.get("completed", []))
    except json.JSONDecodeError:
        return set()

def save_progress(progress_file: Path, completed: set) -> None:
    """Persist the current checkpoint metadata so runs can resume later."""
    progress_file.write_text(json.dumps({"completed": sorted(completed)}, indent=2))

def main():
    """Ingest S&P 500 tickers with 15 years of data."""
    print("=== S&P 500 Data Ingestion (15 years) ===\n")
    
    print("📊 Loading S&P 500 tickers...")
    tickers = load_ticker_universe("sp500")
    print(f"Found {len(tickers)} S&P 500 tickers")
    
    print("⚙️ Loading settings...")
    settings = load_settings()
    
    # Configuration for 15 years
    chunk_size = 20  # Process 20 tickers at a time
    sleep_seconds = 2.0  # Sleep between chunks
    years = 15  # 15 years of data
    progress_file = Path(".ingestion_progress.json")
    
    # Load existing progress
    completed = load_progress(progress_file)
    todo = [ticker for ticker in tickers if ticker not in completed]
    
    print(f"\n📈 Progress Status:")
    print(f"  - Total tickers: {len(tickers)}")
    if completed:
        print(f"  - Already completed: {len(completed)}")
    print(f"  - Remaining: {len(todo)}")
    
    if not todo:
        print("\n✅ All tickers already ingested!")
        print("Run 'python load_historical_prices_15years.py' to load price data")
        return 0
    
    failures = []
    total_chunks = math.ceil(len(todo) / chunk_size)
    
    print(f"\n🚀 Starting ingestion...")
    print(f"  - Processing {len(todo)} tickers in {total_chunks} chunks")
    print(f"  - Each chunk: {chunk_size} tickers")
    print(f"  - Data period: {years} years")
    print(f"  - Estimated time: {total_chunks * 2} minutes")
    
    for chunk_index, chunk in enumerate(chunked(todo, chunk_size), start=1):
        print(f"\n[{chunk_index}/{total_chunks}] Processing {len(chunk)} tickers: {chunk}")
        
        try:
            report = ingest_live_tickers(settings, chunk, years=years)
            
            # Update progress
            for ticker in report.companies:
                completed.add(ticker)
            save_progress(progress_file, completed)
            
            print(f"  ✓ Loaded {report.records_loaded} records for {len(report.companies)} companies")
            
        except Exception as exc:
            print(f"  ✗ Failed chunk {chunk}: {exc}")
            for ticker in chunk:
                failures.append((ticker, str(exc)))
            continue
        
        # Sleep between chunks to respect rate limits
        if sleep_seconds and chunk_index < total_chunks:
            print(f"  Sleeping {sleep_seconds}s before next chunk...")
            time.sleep(sleep_seconds)
    
    # Final report
    if failures:
        print(f"\n⚠️  {len(failures)} tickers failed:")
        for ticker, reason in failures:
            print(f"  - {ticker}: {reason}")
    else:
        print("\n✅ All tickers ingested successfully!")
    
    print(f"\n📊 Final Status:")
    print(f"  - Completed: {len(completed)}/{len(tickers)} tickers")
    print(f"  - Progress saved to: {progress_file}")
    
    print(f"\n🔄 Refreshing cached metrics...")
    try:
        engine = AnalyticsEngine(settings)
        engine.refresh_metrics(force=True)
        print("  ✅ Metrics refreshed")
    except Exception as e:
        print(f"  ⚠️ Could not refresh metrics: {e}")
    
    print(f"\n🎉 S&P 500 ingestion completed!")
    print(f"Next step: python load_historical_prices_15years.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
