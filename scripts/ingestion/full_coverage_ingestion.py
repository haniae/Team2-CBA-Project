#!/usr/bin/env python3
"""
Comprehensive Full Coverage Ingestion Script

This script ensures FULL coverage for ALL tickers by:
1. Identifying all tickers (from S&P 500 universe and database)
2. Ingesting 20 years of historical data for each ticker
3. Filling all data gaps
4. Refreshing all metrics

Usage:
    python scripts/ingestion/full_coverage_ingestion.py
    python scripts/ingestion/full_coverage_ingestion.py --years 25  # For 25 years
    python scripts/ingestion/full_coverage_ingestion.py --dry-run   # Test first
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot import AnalyticsEngine, load_settings
from finanlyzeos_chatbot.data_ingestion import ingest_live_tickers
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe

RATE_LIMIT_SECONDS = 0.15  # SEC allows 10 requests per second
MAX_RETRIES = 3
BATCH_SIZE = 10  # Smaller batches for reliability


class _NoopYahooClient:
    """Stub Yahoo client to bypass quote fetching during large backfills."""
    @staticmethod
    def fetch_quotes(tickers):
        return []


def get_all_target_tickers(settings) -> Set[str]:
    """Get all tickers that need ingestion (S&P 500 + any in database)."""
    # Start with S&P 500 universe
    sp500_tickers = set(load_ticker_universe("sp500"))
    print(f"📊 Loaded {len(sp500_tickers)} S&P 500 tickers from universe")
    
    # Also check database for any additional tickers
    db_path = Path(settings.database_path)
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM financial_facts WHERE ticker IS NOT NULL")
        db_tickers = {row[0].upper() for row in cursor.fetchall()}
        conn.close()
        
        print(f"📊 Found {len(db_tickers)} tickers in database")
        all_tickers = sp500_tickers | db_tickers
        print(f"📊 Total unique tickers: {len(all_tickers)}")
    else:
        all_tickers = sp500_tickers
    
    return all_tickers


def analyze_coverage(settings, tickers: Set[str], years: int) -> dict:
    """Analyze current coverage to identify gaps."""
    db_path = Path(settings.database_path)
    if not db_path.exists():
        return {
            "missing": list(tickers),
            "partial": [],
            "complete": []
        }
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all fiscal years in database
    cursor.execute("""
        SELECT DISTINCT ticker, fiscal_year 
        FROM financial_facts 
        WHERE ticker IS NOT NULL AND fiscal_year IS NOT NULL
    """)
    
    ticker_years = {}
    for ticker, year in cursor.fetchall():
        ticker = ticker.upper()
        if ticker not in ticker_years:
            ticker_years[ticker] = set()
        ticker_years[ticker].add(year)
    
    conn.close()
    
    # Calculate expected year range (last 20 years)
    current_year = datetime.now().year
    expected_years = set(range(current_year - years + 1, current_year + 1))
    
    missing = []
    partial = []
    complete = []
    
    for ticker in tickers:
        if ticker not in ticker_years:
            missing.append(ticker)
        else:
            ticker_coverage = ticker_years[ticker]
            coverage_pct = len(ticker_coverage & expected_years) / len(expected_years) * 100
            
            if coverage_pct == 0:
                missing.append(ticker)
            elif coverage_pct < 80:  # Less than 80% coverage
                partial.append(ticker)
            else:
                complete.append(ticker)
    
    return {
        "missing": missing,
        "partial": partial,
        "complete": complete,
        "stats": {
            "total": len(tickers),
            "missing_count": len(missing),
            "partial_count": len(partial),
            "complete_count": len(complete)
        }
    }


def chunk(items: List, size: int):
    """Divide a list into chunks of specified size."""
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    parser = argparse.ArgumentParser(
        description="Full coverage ingestion for all tickers with extended historical data."
    )
    parser.add_argument(
        "--years",
        type=int,
        default=20,
        help="Number of years of historical data to fetch (default: 20)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Number of tickers per batch (default: {BATCH_SIZE})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually ingesting"
    )
    parser.add_argument(
        "--skip-complete",
        action="store_true",
        help="Skip tickers that already have complete coverage"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 FULL COVERAGE INGESTION")
    print("=" * 80)
    print(f"\nTarget: Full coverage for all tickers")
    print(f"Historical period: {args.years} years")
    print(f"Batch size: {args.batch_size}")
    print(f"Started at: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC\n")
    
    settings = load_settings()
    
    # Get all target tickers
    print("📊 Identifying all tickers...")
    all_tickers = get_all_target_tickers(settings)
    tickers_list = sorted(all_tickers)
    
    # Analyze current coverage
    print(f"\n🔍 Analyzing current coverage...")
    coverage = analyze_coverage(settings, all_tickers, args.years)
    stats = coverage["stats"]
    
    print(f"\n📈 Coverage Analysis:")
    print(f"  Total tickers: {stats['total']}")
    print(f"  ❌ Missing coverage: {stats['missing_count']} ({stats['missing_count']/stats['total']*100:.1f}%)")
    print(f"  ⚠️  Partial coverage: {stats['partial_count']} ({stats['partial_count']/stats['total']*100:.1f}%)")
    print(f"  ✅ Complete coverage: {stats['complete_count']} ({stats['complete_count']/stats['total']*100:.1f}%)")
    
    # Determine which tickers to process
    if args.skip_complete:
        tickers_to_process = sorted(set(coverage["missing"] + coverage["partial"]))
        print(f"\n⏭️  Skipping {len(coverage['complete'])} tickers with complete coverage")
    else:
        tickers_to_process = tickers_list
        print(f"\n🔄 Processing all {len(tickers_to_process)} tickers (including complete ones)")
    
    if not tickers_to_process:
        print("\n✅ All tickers already have complete coverage!")
        return 0
    
    if args.dry_run:
        print(f"\n🏃 DRY RUN - showing what would be done:")
        print(f"\nWould ingest {len(tickers_to_process)} tickers in batches of {args.batch_size}")
        total_batches = (len(tickers_to_process) + args.batch_size - 1) // args.batch_size
        print(f"Total batches: {total_batches}")
        estimated_time = len(tickers_to_process) * RATE_LIMIT_SECONDS * 1.5 / 60  # Account for processing
        print(f"Estimated time: ~{estimated_time:.1f} minutes ({estimated_time/60:.1f} hours)")
        print(f"\nFirst 20 tickers to process: {tickers_to_process[:20]}")
        return 0
    
    # Perform ingestion
    print(f"\n🚀 Starting ingestion of {len(tickers_to_process)} tickers...")
    estimated_time = len(tickers_to_process) * RATE_LIMIT_SECONDS * 1.5 / 60
    print(f"   Estimated time: ~{estimated_time:.1f} minutes ({estimated_time/60:.1f} hours)")
    print()
    
    yahoo_stub = _NoopYahooClient()
    failures = {}
    successes = {}
    total_records = 0
    
    batches = list(chunk(tickers_to_process, args.batch_size))
    total_batches = len(batches)
    
    for batch_idx, batch in enumerate(batches, 1):
        time.sleep(RATE_LIMIT_SECONDS)
        
        tickers_str = ", ".join(batch)
        progress_pct = (batch_idx / total_batches) * 100
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[{batch_idx}/{total_batches} - {progress_pct:.1f}%] Processing: {tickers_str}")
                
                report = ingest_live_tickers(
                    settings,
                    batch,
                    years=args.years,
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
            print(f"   Batches processed: {batch_idx}/{total_batches} ({progress_pct:.1f}%)")
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
        "years": args.years,
        "total_tickers": len(tickers_to_process),
        "successes": sorted(successes.keys()),
        "failures": failures,
        "total_records_loaded": total_records,
        "coverage_before": stats,
    }
    
    summary_path = Path("full_coverage_summary.json")
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
        print("\nFailure details (first 20):")
        for ticker, msg in list(failures.items())[:20]:
            print(f"   • {ticker}: {msg}")
        if len(failures) > 20:
            print(f"   ... and {len(failures) - 20} more")
    else:
        print("\n🎉 All companies ingested successfully!")
    
    print(f"\n💾 Database updated: {settings.database_path}")
    print(f"📊 Run 'python scripts/utility/check_ingestion_status.py' to verify coverage\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

