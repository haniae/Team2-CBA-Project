#!/usr/bin/env python3
"""
Simple database status checker for S&P 500 data.
Provides a quick overview of database contents and data quality.
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot import database, load_settings
from benchmarkos_chatbot.ticker_universe import load_ticker_universe


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {text}")
    print('=' * 80 + '\n')


def get_table_counts(db_path: Path) -> Dict[str, int]:
    """Get row counts for all major tables."""
    counts = {}
    tables = [
        "financial_facts",
        "market_quotes",
        "filings",
        "audit_log",
        "cached_metrics",
        "messages"
    ]
    
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except Exception:
                    counts[table] = 0
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return {}
    
    return counts


def get_ticker_coverage(db_path: Path) -> Dict[str, any]:
    """Get detailed ticker coverage statistics."""
    stats = {
        "total_tickers": 0,
        "with_facts": 0,
        "with_prices": 0,
        "with_filings": 0,
        "tickers": set()
    }
    
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Tickers with facts
            cursor.execute("SELECT DISTINCT ticker FROM financial_facts WHERE ticker IS NOT NULL")
            facts_tickers = {row[0].upper() for row in cursor.fetchall()}
            
            # Tickers with prices
            cursor.execute("SELECT DISTINCT ticker FROM market_quotes WHERE ticker IS NOT NULL")
            price_tickers = {row[0].upper() for row in cursor.fetchall()}
            
            # Tickers with filings
            try:
                cursor.execute("SELECT DISTINCT ticker FROM filings WHERE ticker IS NOT NULL")
                filing_tickers = {row[0].upper() for row in cursor.fetchall()}
            except Exception:
                filing_tickers = set()
            
            all_tickers = facts_tickers | price_tickers | filing_tickers
            
            stats["total_tickers"] = len(all_tickers)
            stats["with_facts"] = len(facts_tickers)
            stats["with_prices"] = len(price_tickers)
            stats["with_filings"] = len(filing_tickers)
            stats["tickers"] = all_tickers
            
    except Exception as e:
        print(f"⚠️ Error getting ticker coverage: {e}")
    
    return stats


def get_metric_distribution(db_path: Path) -> List[Tuple[str, int]]:
    """Get distribution of metrics in the database."""
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT metric, COUNT(*) as count
                FROM financial_facts
                WHERE metric IS NOT NULL
                GROUP BY metric
                ORDER BY count DESC
                LIMIT 20
            """)
            return cursor.fetchall()
    except Exception:
        return []


def get_year_coverage(db_path: Path) -> List[Tuple[int, int]]:
    """Get data coverage by year."""
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fiscal_year, COUNT(DISTINCT ticker) as ticker_count
                FROM financial_facts
                WHERE fiscal_year IS NOT NULL
                GROUP BY fiscal_year
                ORDER BY fiscal_year DESC
                LIMIT 20
            """)
            return cursor.fetchall()
    except Exception:
        return []


def get_data_quality_metrics(db_path: Path) -> Dict[str, any]:
    """Calculate data quality metrics."""
    metrics = {
        "avg_facts_per_ticker": 0,
        "avg_years_per_ticker": 0,
        "avg_metrics_per_ticker": 0,
        "completeness_score": 0
    }
    
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Average facts per ticker
            cursor.execute("""
                SELECT AVG(fact_count) 
                FROM (
                    SELECT COUNT(*) as fact_count 
                    FROM financial_facts 
                    WHERE ticker IS NOT NULL 
                    GROUP BY ticker
                )
            """)
            result = cursor.fetchone()
            metrics["avg_facts_per_ticker"] = result[0] if result and result[0] else 0
            
            # Average years per ticker
            cursor.execute("""
                SELECT AVG(year_count)
                FROM (
                    SELECT COUNT(DISTINCT fiscal_year) as year_count
                    FROM financial_facts
                    WHERE ticker IS NOT NULL AND fiscal_year IS NOT NULL
                    GROUP BY ticker
                )
            """)
            result = cursor.fetchone()
            metrics["avg_years_per_ticker"] = result[0] if result and result[0] else 0
            
            # Average metrics per ticker
            cursor.execute("""
                SELECT AVG(metric_count)
                FROM (
                    SELECT COUNT(DISTINCT metric) as metric_count
                    FROM financial_facts
                    WHERE ticker IS NOT NULL
                    GROUP BY ticker
                )
            """)
            result = cursor.fetchone()
            metrics["avg_metrics_per_ticker"] = result[0] if result and result[0] else 0
            
    except Exception as e:
        print(f"⚠️ Error calculating quality metrics: {e}")
    
    return metrics


def get_recent_activity(db_path: Path) -> List[Tuple[str, int]]:
    """Get recent ingestion activity."""
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    DATE(ingested_at) as date,
                    COUNT(DISTINCT ticker) as ticker_count
                FROM financial_facts
                WHERE ingested_at IS NOT NULL
                GROUP BY DATE(ingested_at)
                ORDER BY date DESC
                LIMIT 10
            """)
            return cursor.fetchall()
    except Exception:
        return []


def main():
    """Main database checking function."""
    print_header("📊 S&P 500 Database Status Report")
    
    # Load settings
    try:
        settings = load_settings()
        db_path = settings.database_path
        print(f"Database: {db_path}")
        
        if not db_path.exists():
            print(f"\n❌ Database not found at: {db_path}")
            print("Run 'python scripts/ingestion/ingest_sp500_15years.py' to start ingestion.")
            return 1
    except Exception as e:
        print(f"\n❌ Error loading settings: {e}")
        return 1
    
    # Get S&P 500 universe
    sp500_tickers = set(load_ticker_universe("sp500"))
    
    # Table counts
    print_header("📋 Database Tables")
    counts = get_table_counts(db_path)
    if counts:
        for table, count in sorted(counts.items()):
            icon = "✅" if count > 0 else "⚠️"
            print(f"  {icon} {table:20s}: {count:>10,} rows")
    
    # Ticker coverage
    print_header("🎯 Ticker Coverage")
    coverage = get_ticker_coverage(db_path)
    if coverage["total_tickers"] > 0:
        print(f"  Total unique tickers: {coverage['total_tickers']}")
        print(f"  S&P 500 target: {len(sp500_tickers)}")
        print(f"  Coverage: {len(coverage['tickers'] & sp500_tickers)}/{len(sp500_tickers)} " +
              f"({len(coverage['tickers'] & sp500_tickers)/len(sp500_tickers)*100:.1f}%)")
        print(f"\n  Breakdown:")
        print(f"    • With financial facts: {coverage['with_facts']}")
        print(f"    • With price data: {coverage['with_prices']}")
        print(f"    • With filings: {coverage['with_filings']}")
    else:
        print("  ⚠️ No tickers found in database")
    
    # Data quality
    print_header("✨ Data Quality Metrics")
    quality = get_data_quality_metrics(db_path)
    if quality["avg_facts_per_ticker"] > 0:
        print(f"  Average facts per ticker: {quality['avg_facts_per_ticker']:.0f}")
        print(f"  Average years per ticker: {quality['avg_years_per_ticker']:.1f}")
        print(f"  Average metrics per ticker: {quality['avg_metrics_per_ticker']:.0f}")
        
        # Quality score
        expected_years = 15
        expected_metrics = 20
        year_score = min(quality['avg_years_per_ticker'] / expected_years * 100, 100)
        metric_score = min(quality['avg_metrics_per_ticker'] / expected_metrics * 100, 100)
        overall_score = (year_score + metric_score) / 2
        
        print(f"\n  Quality Score: {overall_score:.0f}%")
        print(f"    • Year coverage: {year_score:.0f}%")
        print(f"    • Metric diversity: {metric_score:.0f}%")
    else:
        print("  ⚠️ No data available for quality analysis")
    
    # Metric distribution
    print_header("📊 Top Metrics")
    metrics = get_metric_distribution(db_path)
    if metrics:
        print("  Most common metrics in database:\n")
        for i, (metric, count) in enumerate(metrics[:10], 1):
            print(f"  {i:2d}. {metric:30s}: {count:>8,} records")
    
    # Year coverage
    print_header("📅 Year Coverage")
    years = get_year_coverage(db_path)
    if years:
        print("  Data availability by fiscal year:\n")
        for year, ticker_count in years[:15]:
            bar_length = int(ticker_count / len(sp500_tickers) * 50)
            bar = '█' * bar_length + '░' * (50 - bar_length)
            pct = (ticker_count / len(sp500_tickers) * 100) if sp500_tickers else 0
            print(f"  {year}: [{bar}] {ticker_count:3d} tickers ({pct:5.1f}%)")
    
    # Recent activity
    print_header("🕐 Recent Activity")
    activity = get_recent_activity(db_path)
    if activity:
        print("  Recent ingestion activity:\n")
        for date, ticker_count in activity:
            print(f"  {date}: {ticker_count} tickers ingested")
    else:
        print("  No recent activity recorded")
    
    # Sample tickers
    if coverage["tickers"]:
        print_header("🔍 Sample Tickers")
        sample = sorted(list(coverage["tickers"] & sp500_tickers))[:10]
        if sample:
            print("  S&P 500 tickers with data:\n")
            try:
                with database.temporary_connection(db_path) as conn:
                    cursor = conn.cursor()
                    for ticker in sample:
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as facts,
                                COUNT(DISTINCT metric) as metrics,
                                MIN(fiscal_year) as min_year,
                                MAX(fiscal_year) as max_year
                            FROM financial_facts
                            WHERE ticker = ?
                        """, (ticker,))
                        facts, metrics, min_year, max_year = cursor.fetchone()
                        years = f"{min_year}-{max_year}" if min_year and max_year else "N/A"
                        print(f"  {ticker:6s}: {facts:4d} facts, {metrics:2d} metrics, {years}")
            except Exception:
                for ticker in sample:
                    print(f"  {ticker}")
            
            if len(coverage["tickers"] & sp500_tickers) > 10:
                print(f"\n  ... and {len(coverage['tickers'] & sp500_tickers) - 10} more")
        else:
            for ticker in sample:
                print(f"  {ticker}")
    
    # Summary and next steps
    print_header("✅ Summary")
    
    total_facts = counts.get('financial_facts', 0)
    
    if coverage["total_tickers"] == 0 and total_facts == 0:
        print("  ❌ Database is empty")
        print("\n  Next step:")
        print("  $ python scripts/ingestion/ingest_sp500_15years.py")
    elif len(coverage["tickers"] & sp500_tickers) < len(sp500_tickers):
        remaining = len(sp500_tickers) - len(coverage["tickers"] & sp500_tickers)
        print(f"  ⏳ Ingestion in progress: {remaining} tickers remaining")
        print("\n  Next step:")
        print("  $ python scripts/ingestion/ingest_sp500_15years.py")
    elif coverage["with_prices"] < len(sp500_tickers):
        print("  ✅ All S&P 500 tickers ingested!")
        print(f"  ⏳ Price data: {coverage['with_prices']}/{len(sp500_tickers)}")
        print("\n  Next step:")
        print("  $ python scripts/ingestion/load_historical_prices_15years.py")
    else:
        print("  ✅ Database fully populated!")
        print(f"  • S&P 500 tickers: {len(coverage['tickers'] & sp500_tickers)}")
        print(f"  • Financial facts: {counts.get('financial_facts', 0):,}")
        print(f"  • Market quotes: {counts.get('market_quotes', 0):,}")
        print("\n  Ready to use! Try:")
        print("  $ python run_chatbot.py")
    
    print("\n" + "=" * 80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

