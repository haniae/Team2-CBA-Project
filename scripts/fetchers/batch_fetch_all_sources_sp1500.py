"""
Batch fetch all document types for S&P 1500 companies.

This script processes all tickers in the S&P 1500 universe and indexes:
- Earnings transcripts
- Financial news
- Analyst reports
- Press releases

Industry research is handled separately by sector.
"""

import sys
import io
import argparse
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

try:
    from finanlyzeos_chatbot.ticker_universe import load_ticker_universe
except ImportError:
    print("❌ Error: Could not import load_ticker_universe")
    sys.exit(1)

# Import all fetchers - import directly from the fetchers directory
try:
    # Import using importlib to handle the module path correctly
    import importlib.util
    
    earnings_path = Path(__file__).parent / "fetch_earnings_transcripts.py"
    spec = importlib.util.spec_from_file_location("fetch_earnings_transcripts", earnings_path)
    earnings_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(earnings_module)
    index_earnings_transcripts = earnings_module.index_earnings_transcripts
    EARNINGS_AVAILABLE = True
except Exception as e:
    EARNINGS_AVAILABLE = False
    print(f"⚠️  Warning: Earnings transcripts fetcher not available: {e}")

try:
    news_path = Path(__file__).parent / "fetch_financial_news.py"
    spec = importlib.util.spec_from_file_location("fetch_financial_news", news_path)
    news_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(news_module)
    index_financial_news = news_module.index_financial_news
    NEWS_AVAILABLE = True
except Exception as e:
    NEWS_AVAILABLE = False
    print(f"⚠️  Warning: Financial news fetcher not available: {e}")

try:
    analyst_path = Path(__file__).parent / "fetch_analyst_reports.py"
    spec = importlib.util.spec_from_file_location("fetch_analyst_reports", analyst_path)
    analyst_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyst_module)
    index_analyst_reports = analyst_module.index_analyst_reports
    ANALYST_AVAILABLE = True
except Exception as e:
    ANALYST_AVAILABLE = False
    print(f"⚠️  Warning: Analyst reports fetcher not available: {e}")

try:
    press_path = Path(__file__).parent / "fetch_press_releases.py"
    spec = importlib.util.spec_from_file_location("fetch_press_releases", press_path)
    press_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(press_module)
    index_press_releases = press_module.index_press_releases
    PRESS_AVAILABLE = True
except Exception as e:
    PRESS_AVAILABLE = False
    print(f"⚠️  Warning: Press releases fetcher not available: {e}")


def batch_fetch_all_sources(
    database_path: Path,
    universe: str = "sp1500",
    start_from: Optional[str] = None,
    max_tickers: Optional[int] = None,
    skip_earnings: bool = False,
    skip_news: bool = False,
    skip_analyst: bool = False,
    skip_press: bool = False,
    news_limit: int = 10,
    analyst_limit: int = 10,
    press_limit: int = 20,
) -> int:
    """
    Batch fetch all document types for all tickers in a universe.
    
    Args:
        database_path: Path to database
        universe: Ticker universe name (default: "sp1500")
        start_from: Start from this ticker (useful for resuming)
        max_tickers: Maximum number of tickers to process
        skip_earnings: Skip earnings transcripts
        skip_news: Skip financial news
        skip_analyst: Skip analyst reports
        skip_press: Skip press releases
        news_limit: Maximum news articles per ticker
        analyst_limit: Maximum analyst reports per ticker
        press_limit: Maximum press releases per ticker
        
    Returns:
        Exit code (0 = success, 1 = error)
    """
    print("=" * 80)
    print("BATCH FETCH: All Document Types for S&P 1500")
    print("=" * 80)
    print(f"Database: {database_path}")
    print(f"Universe: {universe}")
    print(f"Start from: {start_from if start_from else 'Beginning'}")
    print(f"Max tickers: {max_tickers if max_tickers else 'All'}")
    print()
    
    # Load ticker universe
    try:
        tickers = load_ticker_universe(universe)
        print(f"✓ Loaded {len(tickers)} tickers from {universe}")
    except Exception as e:
        print(f"❌ Error loading ticker universe: {e}")
        return 1
    
    # Filter tickers if start_from is specified
    if start_from:
        try:
            start_idx = tickers.index(start_from.upper())
            tickers = tickers[start_idx:]
            print(f"✓ Starting from ticker {start_from.upper()} (skipped {start_idx} tickers)")
        except ValueError:
            print(f"⚠️  Warning: Ticker {start_from.upper()} not found in universe, starting from beginning")
    
    # Limit tickers if max_tickers is specified
    if max_tickers:
        tickers = tickers[:max_tickers]
        print(f"✓ Limited to {len(tickers)} tickers")
    
    print(f"\n📊 Processing {len(tickers)} tickers...")
    print("=" * 80)
    
    # Statistics
    stats = {
        "total": len(tickers),
        "processed": 0,
        "failed": 0,
        "earnings": {"success": 0, "failed": 0},
        "news": {"success": 0, "failed": 0},
        "analyst": {"success": 0, "failed": 0},
        "press": {"success": 0, "failed": 0},
    }
    
    start_time = time.time()
    
    # Process each ticker
    for idx, ticker in enumerate(tickers, 1):
        print(f"\n[{idx}/{len(tickers)}] Processing {ticker}...")
        print("-" * 80)
        
        ticker_success = True
        
        # 1. Earnings Transcripts
        if not skip_earnings and EARNINGS_AVAILABLE:
            try:
                print(f"  📞 Fetching earnings transcripts...")
                result = index_earnings_transcripts(database_path, ticker, source="all", limit=None)
                if result == 0:
                    stats["earnings"]["success"] += 1
                    print(f"  ✓ Earnings transcripts indexed")
                else:
                    stats["earnings"]["failed"] += 1
                    print(f"  ⚠️  Earnings transcripts failed")
            except Exception as e:
                stats["earnings"]["failed"] += 1
                print(f"  ❌ Earnings transcripts error: {e}")
        
        # 2. Financial News
        if not skip_news and NEWS_AVAILABLE:
            try:
                print(f"  📰 Fetching financial news...")
                result = index_financial_news(database_path, ticker=ticker, source="yahoo", limit=news_limit)
                if result == 0:
                    stats["news"]["success"] += 1
                    print(f"  ✓ Financial news indexed")
                else:
                    stats["news"]["failed"] += 1
                    print(f"  ⚠️  Financial news failed")
            except Exception as e:
                stats["news"]["failed"] += 1
                print(f"  ❌ Financial news error: {e}")
        
        # 3. Analyst Reports
        if not skip_analyst and ANALYST_AVAILABLE:
            try:
                print(f"  📊 Fetching analyst reports...")
                result = index_analyst_reports(database_path, ticker=ticker, source="seeking_alpha", limit=analyst_limit)
                if result == 0:
                    stats["analyst"]["success"] += 1
                    print(f"  ✓ Analyst reports indexed")
                else:
                    stats["analyst"]["failed"] += 1
                    print(f"  ⚠️  Analyst reports failed")
            except Exception as e:
                stats["analyst"]["failed"] += 1
                print(f"  ❌ Analyst reports error: {e}")
        
        # 4. Press Releases
        if not skip_press and PRESS_AVAILABLE:
            try:
                print(f"  📢 Fetching press releases...")
                result = index_press_releases(database_path, ticker=ticker, limit=press_limit)
                if result == 0:
                    stats["press"]["success"] += 1
                    print(f"  ✓ Press releases indexed")
                else:
                    stats["press"]["failed"] += 1
                    print(f"  ⚠️  Press releases failed")
            except Exception as e:
                stats["press"]["failed"] += 1
                print(f"  ❌ Press releases error: {e}")
        
        stats["processed"] += 1
        
        # Progress summary
        elapsed = time.time() - start_time
        avg_time = elapsed / idx
        remaining = (len(tickers) - idx) * avg_time
        
        print(f"\n  📈 Progress: {idx}/{len(tickers)} ({idx/len(tickers)*100:.1f}%)")
        print(f"  ⏱️  Elapsed: {elapsed/60:.1f} min | Est. remaining: {remaining/60:.1f} min")
        
        # Rate limiting - be nice to APIs
        if idx < len(tickers):
            print(f"  ⏸️  Waiting 2 seconds before next ticker...")
            time.sleep(2)
    
    # Final summary
    print("\n" + "=" * 80)
    print("BATCH FETCH COMPLETE")
    print("=" * 80)
    print(f"Total tickers processed: {stats['processed']}/{stats['total']}")
    print(f"Failed tickers: {stats['failed']}")
    print()
    print("Results by source:")
    print(f"  Earnings transcripts: {stats['earnings']['success']} success, {stats['earnings']['failed']} failed")
    print(f"  Financial news: {stats['news']['success']} success, {stats['news']['failed']} failed")
    print(f"  Analyst reports: {stats['analyst']['success']} success, {stats['analyst']['failed']} failed")
    print(f"  Press releases: {stats['press']['success']} success, {stats['press']['failed']} failed")
    print()
    total_time = time.time() - start_time
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch fetch all document types for S&P 1500 companies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all tickers with all sources
  python scripts/fetchers/batch_fetch_all_sources_sp1500.py --database data/financial.db

  # Test with first 10 tickers
  python scripts/fetchers/batch_fetch_all_sources_sp1500.py --database data/financial.db --max-tickers 10

  # Resume from a specific ticker
  python scripts/fetchers/batch_fetch_all_sources_sp1500.py --database data/financial.db --start-from MSFT

  # Skip certain sources
  python scripts/fetchers/batch_fetch_all_sources_sp1500.py --database data/financial.db --skip-earnings --skip-news

  # Use different universe
  python scripts/fetchers/batch_fetch_all_sources_sp1500.py --database data/financial.db --universe sp500
        """
    )
    
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--universe", type=str, default="sp1500", help="Ticker universe (default: sp1500)")
    parser.add_argument("--start-from", type=str, help="Start from this ticker (useful for resuming)")
    parser.add_argument("--max-tickers", type=int, help="Maximum number of tickers to process")
    parser.add_argument("--skip-earnings", action="store_true", help="Skip earnings transcripts")
    parser.add_argument("--skip-news", action="store_true", help="Skip financial news")
    parser.add_argument("--skip-analyst", action="store_true", help="Skip analyst reports")
    parser.add_argument("--skip-press", action="store_true", help="Skip press releases")
    parser.add_argument("--news-limit", type=int, default=10, help="Maximum news articles per ticker")
    parser.add_argument("--analyst-limit", type=int, default=10, help="Maximum analyst reports per ticker")
    parser.add_argument("--press-limit", type=int, default=20, help="Maximum press releases per ticker")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(batch_fetch_all_sources(
        args.database,
        args.universe,
        args.start_from,
        args.max_tickers,
        args.skip_earnings,
        args.skip_news,
        args.skip_analyst,
        args.skip_press,
        args.news_limit,
        args.analyst_limit,
        args.press_limit,
    ))

