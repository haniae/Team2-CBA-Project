#!/usr/bin/env python3
"""
Comprehensive Data Coverage Checker

Shows detailed statistics about your database:
- Total records per table
- Company/ticker counts
- Year range coverage
- Data volume and size
- Coverage percentages
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from finanlyzeos_chatbot.config import load_settings
    from finanlyzeos_chatbot.ticker_universe import load_ticker_universe
except ImportError:
    print("⚠️  Could not import finanlyzeos_chatbot modules")
    print("   Using default database path...")
    load_settings = None
    load_ticker_universe = None


def get_database_path():
    """Get database path from settings or use default."""
    if load_settings:
        try:
            settings = load_settings()
            return Path(settings.database_path)
        except Exception as e:
            print(f"⚠️  Error loading settings: {e}")
    
    # Try common database locations
    possible_paths = [
        Path("benchmarkos_chatbot.sqlite3"),
        Path("finanlyzeos_chatbot.sqlite3"),
        Path.cwd() / "benchmarkos_chatbot.sqlite3",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def format_number(num):
    """Format number with commas."""
    return f"{num:,}"


def format_size(bytes_size):
    """Format file size."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.2f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def get_table_counts(conn):
    """Get row counts for all tables."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except Exception as e:
            counts[table] = 0
    
    return counts


def get_ticker_statistics(conn):
    """Get detailed ticker statistics."""
    stats = {
        "total_tickers": 0,
        "tickers_with_facts": set(),
        "tickers_with_prices": set(),
        "tickers_with_filings": set(),
        "tickers_with_metrics": set(),
    }
    
    try:
        # Tickers with financial facts
        cursor = conn.execute("SELECT DISTINCT ticker FROM financial_facts WHERE ticker IS NOT NULL")
        stats["tickers_with_facts"] = {row[0].upper() for row in cursor.fetchall()}
        
        # Tickers with market quotes
        try:
            cursor = conn.execute("SELECT DISTINCT ticker FROM market_quotes WHERE ticker IS NOT NULL")
            stats["tickers_with_prices"] = {row[0].upper() for row in cursor.fetchall()}
        except:
            pass
        
        # Tickers with filings
        try:
            cursor = conn.execute("SELECT DISTINCT ticker FROM company_filings WHERE ticker IS NOT NULL")
            stats["tickers_with_filings"] = {row[0].upper() for row in cursor.fetchall()}
        except:
            pass
        
        # Tickers with metrics
        try:
            cursor = conn.execute("SELECT DISTINCT ticker FROM metric_snapshots WHERE ticker IS NOT NULL")
            stats["tickers_with_metrics"] = {row[0].upper() for row in cursor.fetchall()}
        except:
            pass
        
        # Total unique tickers
        all_tickers = (
            stats["tickers_with_facts"] |
            stats["tickers_with_prices"] |
            stats["tickers_with_filings"] |
            stats["tickers_with_metrics"]
        )
        stats["total_tickers"] = len(all_tickers)
        
    except Exception as e:
        print(f"⚠️  Error getting ticker stats: {e}")
    
    return stats


def get_year_coverage(conn):
    """Get fiscal year coverage statistics."""
    try:
        cursor = conn.execute("""
            SELECT 
                MIN(fiscal_year) as min_year,
                MAX(fiscal_year) as max_year,
                COUNT(DISTINCT fiscal_year) as year_count,
                COUNT(DISTINCT ticker) as ticker_count
            FROM financial_facts 
            WHERE fiscal_year IS NOT NULL
        """)
        result = cursor.fetchone()
        
        if result and result[0]:
            return {
                "min_year": result[0],
                "max_year": result[1],
                "year_count": result[2],
                "ticker_count": result[3],
            }
    except Exception as e:
        print(f"⚠️  Error getting year coverage: {e}")
    
    return None


def get_year_distribution(conn):
    """Get distribution of data across years."""
    try:
        cursor = conn.execute("""
            SELECT 
                fiscal_year,
                COUNT(DISTINCT ticker) as ticker_count,
                COUNT(*) as fact_count
            FROM financial_facts
            WHERE fiscal_year IS NOT NULL
            GROUP BY fiscal_year
            ORDER BY fiscal_year DESC
        """)
        return cursor.fetchall()
    except:
        return []


def get_metric_statistics(conn):
    """Get statistics about metrics."""
    try:
        # Total unique metrics
        cursor = conn.execute("SELECT COUNT(DISTINCT metric) FROM metric_snapshots WHERE metric IS NOT NULL")
        unique_metrics = cursor.fetchone()[0]
        
        # Metrics with most data
        cursor = conn.execute("""
            SELECT metric, COUNT(*) as count
            FROM metric_snapshots
            WHERE metric IS NOT NULL
            GROUP BY metric
            ORDER BY count DESC
            LIMIT 10
        """)
        top_metrics = cursor.fetchall()
        
        return {
            "unique_metrics": unique_metrics,
            "top_metrics": top_metrics,
        }
    except:
        return {"unique_metrics": 0, "top_metrics": []}


def get_detailed_coverage_analysis(conn, ticker_stats):
    """Get detailed coverage analysis showing missing, partial, and complete coverage."""
    if not load_ticker_universe:
        return None
    
    try:
        sp500_tickers = set(load_ticker_universe("sp500"))
        db_tickers = ticker_stats["tickers_with_facts"]
        
        # Get year coverage for each ticker
        cursor = conn.execute("""
            SELECT ticker, COUNT(DISTINCT fiscal_year) as year_count
            FROM financial_facts
            WHERE ticker IS NOT NULL AND fiscal_year IS NOT NULL
            GROUP BY ticker
        """)
        
        ticker_year_counts = {}
        for row in cursor.fetchall():
            ticker_year_counts[row[0].upper()] = row[1]
        
        # Calculate expected years (last 15 years)
        current_year = datetime.now().year
        expected_years = 15
        min_expected_years = 8  # Minimum for "complete" coverage (more realistic)
        
        missing = []
        partial = []
        complete = []
        
        for ticker in sp500_tickers:
            if ticker not in db_tickers:
                missing.append(ticker)
            elif ticker not in ticker_year_counts:
                missing.append(ticker)
            else:
                year_count = ticker_year_counts[ticker]
                if year_count == 0:
                    missing.append(ticker)
                elif year_count < min_expected_years:
                    partial.append(ticker)
                else:
                    complete.append(ticker)
        
        # Also check all database tickers (not just S&P 500)
        all_db_tickers = set(ticker_year_counts.keys())
        all_missing = []
        all_partial = []
        all_complete = []
        
        for ticker in all_db_tickers:
            year_count = ticker_year_counts[ticker]
            if year_count == 0:
                all_missing.append(ticker)
            elif year_count < min_expected_years:
                all_partial.append(ticker)
            else:
                all_complete.append(ticker)
        
        # Tickers in database but not in S&P 500
        non_sp500 = all_db_tickers - sp500_tickers
        
        return {
            "sp500_total": len(sp500_tickers),
            "sp500_missing": len(missing),
            "sp500_partial": len(partial),
            "sp500_complete": len(complete),
            "sp500_coverage_pct": (len(complete) + len(partial)) / len(sp500_tickers) * 100 if sp500_tickers else 0,
            "all_tickers_total": len(all_db_tickers),
            "all_missing": len(all_missing),
            "all_partial": len(all_partial),
            "all_complete": len(all_complete),
            "non_sp500_count": len(non_sp500),
            "missing_list": sorted(missing),
            "partial_list": sorted(partial),
        }
    except Exception as e:
        print(f"⚠️  Error in coverage analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to display database statistics."""
    print("=" * 80)
    print("📊 DATABASE DATA COVERAGE REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get database path
    db_path = get_database_path()
    if not db_path:
        print("❌ Database not found!")
        print("\nTried locations:")
        print("  - benchmarkos_chatbot.sqlite3")
        print("  - finanlyzeos_chatbot.sqlite3")
        print("  - Current directory")
        print("\nPlease ensure the database exists or update the path in settings.")
        return 1
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return 1
    
    print(f"📁 Database: {db_path}")
    print(f"💾 Size: {format_size(db_path.stat().st_size)}")
    print()
    
    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 1
    
    # Table counts
    print("=" * 80)
    print("📋 TABLE STATISTICS")
    print("=" * 80)
    table_counts = get_table_counts(conn)
    
    total_rows = 0
    for table, count in sorted(table_counts.items()):
        if count > 0:
            print(f"  {table:30s} {format_number(count):>15} rows")
            total_rows += count
    
    print("-" * 80)
    print(f"  {'TOTAL ROWS':30s} {format_number(total_rows):>15}")
    print()
    
    # Ticker statistics
    print("=" * 80)
    print("🎯 TICKER COVERAGE")
    print("=" * 80)
    ticker_stats = get_ticker_statistics(conn)
    
    print(f"  Total unique tickers: {ticker_stats['total_tickers']}")
    print(f"  • With financial facts: {len(ticker_stats['tickers_with_facts'])}")
    print(f"  • With market quotes: {len(ticker_stats['tickers_with_prices'])}")
    print(f"  • With filings: {len(ticker_stats['tickers_with_filings'])}")
    print(f"  • With metrics: {len(ticker_stats['tickers_with_metrics'])}")
    
    # Detailed coverage analysis
    coverage_info = get_detailed_coverage_analysis(conn, ticker_stats)
    if coverage_info:
        print()
        print(f"  S&P 500 Coverage Breakdown:")
        print(f"    Total S&P 500 tickers: {coverage_info['sp500_total']}")
        print(f"    ❌ Missing coverage: {coverage_info['sp500_missing']} tickers")
        print(f"    ⚠️  Partial coverage: {coverage_info['sp500_partial']} tickers")
        print(f"    ✅ Complete coverage: {coverage_info['sp500_complete']} tickers")
        print(f"    Coverage rate: {coverage_info['sp500_coverage_pct']:.1f}%")
        
        print()
        print(f"  All Tickers Coverage Breakdown:")
        print(f"    Total tickers in database: {coverage_info['all_tickers_total']}")
        print(f"    ❌ Missing coverage: {coverage_info['all_missing']} tickers")
        print(f"    ⚠️  Partial coverage: {coverage_info['all_partial']} tickers")
        print(f"    ✅ Complete coverage: {coverage_info['all_complete']} tickers")
        print(f"    Non-S&P 500 tickers: {coverage_info['non_sp500_count']}")
        
        # Show some examples
        if coverage_info['missing_list']:
            print()
            print(f"  Missing Coverage Examples (first 10):")
            for ticker in coverage_info['missing_list'][:10]:
                print(f"    • {ticker}")
            if len(coverage_info['missing_list']) > 10:
                print(f"    ... and {len(coverage_info['missing_list']) - 10} more")
        
        if coverage_info['partial_list']:
            print()
            print(f"  Partial Coverage Examples (first 10):")
            for ticker in coverage_info['partial_list'][:10]:
                print(f"    • {ticker}")
            if len(coverage_info['partial_list']) > 10:
                print(f"    ... and {len(coverage_info['partial_list']) - 10} more")
    print()
    
    # Year coverage
    print("=" * 80)
    print("📅 YEAR COVERAGE")
    print("=" * 80)
    year_coverage = get_year_coverage(conn)
    
    if year_coverage:
        print(f"  Year Range: {year_coverage['min_year']} to {year_coverage['max_year']}")
        print(f"  Total Years: {year_coverage['year_count']}")
        print(f"  Tickers with Data: {year_coverage['ticker_count']}")
        print()
        
        # Year distribution
        year_dist = get_year_distribution(conn)
        if year_dist:
            print("  Year Distribution (Top 10):")
            print(f"    {'Year':<8} {'Tickers':<12} {'Facts':<12}")
            print("    " + "-" * 32)
            for year, ticker_count, fact_count in year_dist[:10]:
                print(f"    {year:<8} {format_number(ticker_count):<12} {format_number(fact_count):<12}")
            if len(year_dist) > 10:
                print(f"    ... and {len(year_dist) - 10} more years")
            print()
    
    # Metric statistics
    print("=" * 80)
    print("📊 METRIC STATISTICS")
    print("=" * 80)
    metric_stats = get_metric_statistics(conn)
    
    print(f"  Unique metrics: {metric_stats['unique_metrics']}")
    if metric_stats['top_metrics']:
        print()
        print("  Top 10 Metrics by Count:")
        for metric, count in metric_stats['top_metrics']:
            print(f"    {metric:30s} {format_number(count):>15}")
    print()
    
    # Data quality summary
    print("=" * 80)
    print("✨ DATA QUALITY SUMMARY")
    print("=" * 80)
    
    facts_count = table_counts.get('financial_facts', 0)
    metrics_count = table_counts.get('metric_snapshots', 0)
    quotes_count = table_counts.get('market_quotes', 0)
    filings_count = table_counts.get('company_filings', 0)
    
    if ticker_stats['total_tickers'] > 0:
        avg_facts = facts_count / ticker_stats['total_tickers'] if ticker_stats['total_tickers'] > 0 else 0
        avg_metrics = metrics_count / ticker_stats['total_tickers'] if ticker_stats['total_tickers'] > 0 else 0
        
        print(f"  Average facts per ticker: {avg_facts:.1f}")
        print(f"  Average metrics per ticker: {avg_metrics:.1f}")
        print()
    
    # Coverage assessment
    print("=" * 80)
    print("📈 COVERAGE ASSESSMENT")
    print("=" * 80)
    
    if coverage_info:
        # Calculate true coverage (complete + partial)
        total_with_data = coverage_info['sp500_complete'] + coverage_info['sp500_partial']
        true_coverage_pct = (total_with_data / coverage_info['sp500_total']) * 100 if coverage_info['sp500_total'] > 0 else 0
        
        if true_coverage_pct >= 95 and coverage_info['sp500_missing'] < 20:
            status = "✅ EXCELLENT"
        elif true_coverage_pct >= 80:
            status = "✅ GOOD"
        elif true_coverage_pct >= 50:
            status = "⚠️  PARTIAL"
        else:
            status = "❌ INCOMPLETE"
        
        print(f"  S&P 500 Coverage: {status}")
        print(f"    Total: {coverage_info['sp500_total']} tickers")
        print(f"    ✅ Complete: {coverage_info['sp500_complete']} tickers")
        print(f"    ⚠️  Partial: {coverage_info['sp500_partial']} tickers")
        print(f"    ❌ Missing: {coverage_info['sp500_missing']} tickers")
        print(f"    Coverage Rate: {true_coverage_pct:.1f}% (with data)")
        
        print()
        print(f"  All Database Tickers:")
        print(f"    Total: {coverage_info['all_tickers_total']} tickers")
        print(f"    ✅ Complete: {coverage_info['all_complete']} tickers")
        print(f"    ⚠️  Partial: {coverage_info['all_partial']} tickers")
        print(f"    ❌ Missing: {coverage_info['all_missing']} tickers")
    
    if year_coverage:
        years_span = year_coverage['max_year'] - year_coverage['min_year'] + 1
        if years_span >= 15:
            year_status = "✅ EXCELLENT (15+ years)"
        elif years_span >= 10:
            year_status = "✅ GOOD (10+ years)"
        elif years_span >= 5:
            year_status = "⚠️  PARTIAL (5+ years)"
        else:
            year_status = "❌ LIMITED (<5 years)"
        
        print(f"  Historical Coverage: {year_status}")
        print(f"    {year_coverage['year_count']} years of data ({year_coverage['min_year']}-{year_coverage['max_year']})")
    
    print()
    print("=" * 80)
    print("✅ Report Complete")
    print("=" * 80)
    
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

