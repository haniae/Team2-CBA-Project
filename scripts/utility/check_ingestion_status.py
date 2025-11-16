#!/usr/bin/env python3
"""
Check the status of S&P 500 data ingestion with detailed progress tracking.
Shows what's completed, what's remaining, and provides resume capability.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import database, load_settings
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe


def load_progress(progress_file: Path = Path(".ingestion_progress.json")) -> Set[str]:
    """Load completed tickers from progress file."""
    if not progress_file.exists():
        return set()
    try:
        data = json.loads(progress_file.read_text())
        return set(data.get("completed", []))
    except json.JSONDecodeError:
        return set()


def get_ingested_tickers(db_path: Path) -> Set[str]:
    """Get tickers that have data in the database."""
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT ticker FROM financial_facts WHERE ticker IS NOT NULL")
            return {row[0].upper() for row in cursor.fetchall()}
    except Exception:
        return set()


def get_ticker_stats(db_path: Path) -> Dict[str, Dict]:
    """Get detailed statistics for each ticker in the database."""
    stats = {}
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    ticker,
                    COUNT(*) as fact_count,
                    COUNT(DISTINCT metric) as metric_count,
                    MIN(fiscal_year) as earliest_year,
                    MAX(fiscal_year) as latest_year
                FROM financial_facts 
                WHERE ticker IS NOT NULL
                GROUP BY ticker
            """)
            for row in cursor.fetchall():
                ticker, fact_count, metric_count, earliest_year, latest_year = row
                stats[ticker.upper()] = {
                    "facts": fact_count,
                    "metrics": metric_count,
                    "years": f"{earliest_year}-{latest_year}" if earliest_year and latest_year else "N/A"
                }
    except Exception:
        pass
    return stats


def get_price_data_status(db_path: Path) -> Dict[str, int]:
    """Get count of tickers with price data."""
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM market_quotes WHERE ticker IS NOT NULL")
            count = cursor.fetchone()[0]
            return {"tickers_with_prices": count}
    except Exception:
        return {"tickers_with_prices": 0}


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def main():
    """Main status check function."""
    print_section("📊 S&P 500 Data Ingestion Status Check")
    
    # Load settings and universe
    try:
        settings = load_settings()
        db_path = settings.database_path
    except Exception as e:
        print(f"\n❌ Error loading settings: {e}")
        return 1
    
    sp500_tickers = set(load_ticker_universe("sp500"))
    progress_completed = load_progress()
    db_tickers = get_ingested_tickers(db_path)
    ticker_stats = get_ticker_stats(db_path)
    price_status = get_price_data_status(db_path)
    
    # Calculate status
    in_progress_file = progress_completed & sp500_tickers
    in_database = db_tickers & sp500_tickers
    remaining = sp500_tickers - in_database
    
    # Print overall status
    print_section("📈 Overall Progress")
    print(f"\n  Total S&P 500 tickers: {len(sp500_tickers)}")
    print(f"  ✅ Ingested to database: {len(in_database)} ({len(in_database)/len(sp500_tickers)*100:.1f}%)")
    print(f"  ⏳ Remaining: {len(remaining)} ({len(remaining)/len(sp500_tickers)*100:.1f}%)")
    print(f"  📝 Progress file records: {len(in_progress_file)}")
    
    # Progress bar
    progress_pct = (len(in_database) / len(sp500_tickers)) * 100
    bar_length = 50
    filled = int(bar_length * progress_pct / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\n  Progress: [{bar}] {progress_pct:.1f}%")
    
    # Price data status
    print_section("💰 Price Data Status")
    print(f"\n  Tickers with price data: {price_status['tickers_with_prices']}")
    if price_status['tickers_with_prices'] > 0:
        print(f"  Coverage: {price_status['tickers_with_prices']/len(sp500_tickers)*100:.1f}%")
    
    # Data quality metrics
    if ticker_stats:
        print_section("📊 Data Quality Metrics")
        total_facts = sum(s["facts"] for s in ticker_stats.values())
        avg_facts = total_facts / len(ticker_stats) if ticker_stats else 0
        avg_metrics = sum(s["metrics"] for s in ticker_stats.values()) / len(ticker_stats) if ticker_stats else 0
        
        print(f"\n  Total financial facts: {total_facts:,}")
        print(f"  Average facts per ticker: {avg_facts:.0f}")
        print(f"  Average metrics per ticker: {avg_metrics:.0f}")
    
    # Sample of ingested tickers
    if in_database:
        print_section("✅ Sample of Ingested Tickers")
        sample = sorted(list(in_database))[:10]
        for ticker in sample:
            if ticker in ticker_stats:
                stats = ticker_stats[ticker]
                print(f"  {ticker:6s} - {stats['facts']:4d} facts, {stats['metrics']:2d} metrics, {stats['years']}")
            else:
                print(f"  {ticker:6s} - (details unavailable)")
        if len(in_database) > 10:
            print(f"  ... and {len(in_database) - 10} more")
    
    # Remaining tickers
    if remaining:
        print_section("⏳ Remaining Tickers")
        sample = sorted(list(remaining))[:20]
        print(f"\n  Next to ingest: {', '.join(sample)}")
        if len(remaining) > 20:
            print(f"  ... and {len(remaining) - 20} more")
    
    # Next steps
    print_section("🚀 Next Steps")
    if remaining:
        print("\n  To resume ingestion:")
        print("  $ python scripts/ingestion/ingest_sp500_15years.py")
        print("\n  This will automatically continue from where you left off.")
    else:
        print("\n  ✅ All S&P 500 tickers ingested!")
        if price_status['tickers_with_prices'] < len(sp500_tickers):
            print("\n  To load historical prices:")
            print("  $ python scripts/ingestion/load_historical_prices_15years.py")
        else:
            print("\n  ✅ Price data is also loaded!")
            print("\n  To verify data:")
            print("  $ python check_database_simple.py")
    
    # File locations
    print_section("📁 File Locations")
    print(f"\n  Database: {db_path}")
    print(f"  Progress file: {Path('.ingestion_progress.json').absolute()}")
    
    print("\n" + "=" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

