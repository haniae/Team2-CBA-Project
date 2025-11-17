#!/usr/bin/env python3
"""Fill data gaps for all years (2019-2025) to make coverage solid."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from finanlyzeos_chatbot import AnalyticsEngine, load_settings
from finanlyzeos_chatbot.data_ingestion import ingest_live_tickers
from finanlyzeos_chatbot.data_sources import EdgarClient

RATE_LIMIT_SECONDS = 0.15  # SEC allows 10 requests per second
MAX_RETRIES = 3

class _NoopYahooClient:
    """Stub Yahoo client to bypass quote fetching during large backfills."""
    @staticmethod
    def fetch_quotes(tickers):
        return []

def load_all_tickers_from_db(settings):
    """Get all tickers that currently exist in the database."""
    import sqlite3
    db_path = Path(settings.database_path)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM financial_facts ORDER BY ticker")
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers

def get_companies_missing_years(settings, target_years):
    """Identify which companies are missing data for target years."""
    import sqlite3
    db_path = Path(settings.database_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tickers
    cursor.execute("SELECT DISTINCT ticker FROM financial_facts ORDER BY ticker")
    all_tickers = [row[0] for row in cursor.fetchall()]
    
    # Get tickers that have data for target years
    placeholders = ','.join('?' * len(target_years))
    cursor.execute(f"""
        SELECT DISTINCT ticker 
        FROM financial_facts 
        WHERE fiscal_year IN ({placeholders})
    """, target_years)
    tickers_with_data = set(row[0] for row in cursor.fetchall())
    
    # Companies missing data for these years
    missing = [t for t in all_tickers if t not in tickers_with_data]
    
    conn.close()
    return all_tickers, missing

def chunk(items, size):
    """Divide a list into chunks of specified size."""
    for i in range(0, len(items), size):
        yield items[i:i + size]

def main():
    parser = argparse.ArgumentParser(
        description="Fill data gaps to make all years (2019-2025) solid."
    )
    parser.add_argument(
        "--target-years",
        default="2019,2020,2025",
        help="Comma-separated years to backfill (default: 2019,2020,2025)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of tickers per batch (default: 10)"
    )
    parser.add_argument(
        "--years-back",
        type=int,
        default=7,
        help="How many years back to fetch from SEC (default: 7, covers 2019-2025)"
    )
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=None,
        help="Maximum number of tickers to process (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually ingesting"
    )
    
    args = parser.parse_args()
    
    target_years = [int(y.strip()) for y in args.target_years.split(',')]
    
    print("=" * 80)
    print("FILLING DATA GAPS - MAKING ALL YEARS SOLID")
    print("=" * 80)
    print(f"\nTarget years: {', '.join(map(str, target_years))}")
    print(f"Years to fetch from SEC: {args.years_back}")
    print(f"Batch size: {args.batch_size}")
    print(f"Started at: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC\n")
    
    settings = load_settings()
    
    # Strategy: Ingest ALL tickers with years_back=7 to ensure we get 2019-2025
    print("📊 Loading existing tickers from database...")
    all_tickers = load_all_tickers_from_db(settings)
    print(f"   Found {len(all_tickers)} tickers in database")
    
    # Get which ones are missing data for target years
    print(f"\n🔍 Checking coverage for years: {', '.join(map(str, target_years))}...")
    _, missing_tickers = get_companies_missing_years(settings, target_years)
    print(f"   {len(missing_tickers)} companies missing data for these years")
    
    if args.max_tickers:
        all_tickers = all_tickers[:args.max_tickers]
        print(f"\n⚠️  Limited to first {args.max_tickers} tickers")
    
    if args.dry_run:
        print("\n🏃 DRY RUN - showing what would be done:")
        print(f"\nWould ingest {len(all_tickers)} tickers in batches of {args.batch_size}")
        print(f"Total batches: {len(list(chunk(all_tickers, args.batch_size)))}")
        print(f"Estimated time: ~{len(all_tickers) * RATE_LIMIT_SECONDS / 60:.1f} minutes")
        return
    
    # Perform ingestion
    print(f"\n🚀 Starting ingestion of {len(all_tickers)} tickers...")
    print(f"   This will take approximately {len(all_tickers) * RATE_LIMIT_SECONDS / 60:.1f} minutes")
    print()
    
    yahoo_stub = _NoopYahooClient()
    failures = {}
    successes = {}
    total_records = 0
    
    batches = list(chunk(all_tickers, args.batch_size))
    for batch_idx, batch in enumerate(batches, 1):
        time.sleep(RATE_LIMIT_SECONDS)
        
        tickers_str = ", ".join(batch)
        progress_pct = (batch_idx / len(batches)) * 100
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[{batch_idx}/{len(batches)} - {progress_pct:.1f}%] Processing: {tickers_str}")
                
                report = ingest_live_tickers(
                    settings,
                    batch,
                    years=args.years_back,
                    yahoo_client=yahoo_stub,
                )
                
                loaded = report.records_loaded
                total_records += loaded
                print(f"   ✅ Loaded {loaded} records (Total: {total_records:,})")
                
                for ticker in report.companies:
                    successes[ticker] = loaded
                    failures.pop(ticker, None)
                break
                
            except Exception as exc:
                error_msg = str(exc)
                print(f"   ❌ Attempt {attempt} failed: {error_msg}")
                
                for ticker in batch:
                    failures[ticker] = error_msg
                
                if attempt == MAX_RETRIES:
                    print(f"   ⚠️  Giving up after {MAX_RETRIES} attempts")
                    break
                
                time.sleep(RATE_LIMIT_SECONDS * 2)
        
        # Progress update every 10 batches
        if batch_idx % 10 == 0:
            print(f"\n📊 Progress Report:")
            print(f"   Batches processed: {batch_idx}/{len(batches)}")
            print(f"   Total records loaded: {total_records:,}")
            print(f"   Successes: {len(successes)}")
            print(f"   Failures: {len(failures)}")
            print()
    
    # Refresh derived metrics
    print("\n🔄 Refreshing derived metrics...")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("   ✅ Metrics refreshed")
    
    # Save summary
    summary = {
        "completed_at": datetime.utcnow().isoformat(),
        "target_years": target_years,
        "years_back": args.years_back,
        "total_tickers": len(all_tickers),
        "successes": sorted(successes.keys()),
        "failures": failures,
        "total_records_loaded": total_records,
    }
    
    summary_path = Path("fill_gaps_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\n📄 Summary saved to: {summary_path}")
    
    # Final report
    print("\n" + "=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
    print(f"\n✅ Successfully ingested: {len(successes)} companies")
    print(f"📊 Total records loaded: {total_records:,}")
    
    if failures:
        print(f"\n⚠️  Failed: {len(failures)} companies")
        print("\nFailure details:")
        for ticker, msg in list(failures.items())[:10]:
            print(f"   • {ticker}: {msg}")
        if len(failures) > 10:
            print(f"   ... and {len(failures) - 10} more")
    else:
        print("\n🎉 All companies ingested successfully!")
    
    print(f"\n💾 Database updated: {settings.database_path}")
    print(f"📊 Run 'python analyze_data_gaps.py' to verify coverage\n")

if __name__ == "__main__":
    main()

