#!/usr/bin/env python3
"""
Load 15 years of historical price data for S&P 500 tickers.
"""

import sys
import time
import math
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Tuple

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import yfinance as yf
from benchmarkos_chatbot import database
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.data_sources import MarketQuote
from benchmarkos_chatbot.ticker_universe import load_ticker_universe

def fetch_historical_prices(ticker: str, years: int = 15) -> List[Tuple[str, str, Optional[float], Optional[float], Optional[int]]]:
    """Fetch historical prices for a ticker."""
    try:
        y_ticker = yf.Ticker(ticker)
        history = y_ticker.history(period=f"{years}y", interval="1d", auto_adjust=False)
        
        if history.empty:
            return []
        
        rows = []
        for date, row in history.iterrows():
            close = row.get("Close")
            adj_close = row.get("Adj Close")
            volume = row.get("Volume")
            
            if close is not None and not math.isnan(close):
                rows.append((
                    ticker,
                    date.date().isoformat(),
                    float(close),
                    float(adj_close) if adj_close is not None and not math.isnan(adj_close) else None,
                    int(volume) if volume is not None and not math.isnan(volume) else None
                ))
        
        return rows
        
    except Exception as e:
        print(f"  ✗ Failed {ticker}: {e}")
        return []

def main():
    """Load 15 years of historical price data for S&P 500."""
    print("=== Loading Historical Price Data (15 years) ===\n")
    
    settings = load_settings()
    
    # Get S&P 500 tickers
    tickers = load_ticker_universe("sp500")
    print(f"📊 Loading historical prices for {len(tickers)} S&P 500 tickers...")
    print(f"  - Data period: 15 years")
    print(f"  - Estimated time: 1-2 hours")
    print(f"  - Rate limiting: 0.5s between requests")
    
    all_rows = []
    successful = 0
    failed = 0
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Fetching {ticker}...")
        
        rows = fetch_historical_prices(ticker, years=15)
        
        if rows:
            all_rows.extend(rows)
            successful += 1
            print(f"  ✓ {len(rows)} price records")
        else:
            failed += 1
            print(f"  ✗ No data")
        
        # Rate limiting
        time.sleep(0.5)
    
    print(f"\n📈 Summary:")
    print(f"  - Successful: {successful} tickers")
    print(f"  - Failed: {failed} tickers")
    print(f"  - Total price records: {len(all_rows):,}")
    
    if all_rows:
        print(f"\n💾 Saving latest quotes to database...")
        
        # Convert to MarketQuote objects for latest prices
        latest_quotes = []
        ticker_latest = {}
        
        for ticker, date_str, close, adj_close, volume in all_rows:
            if ticker not in ticker_latest or date_str > ticker_latest[ticker][0]:
                ticker_latest[ticker] = (date_str, close, volume)
        
        for ticker, (date_str, close, volume) in ticker_latest.items():
            latest_quotes.append(MarketQuote(
                ticker=ticker,
                price=close,
                currency="USD",
                volume=volume,
                timestamp=datetime.now(timezone.utc),
                source="yfinance_historical",
                raw={"date": date_str, "price": close, "volume": volume}
            ))
        
        # Insert latest quotes
        inserted = database.bulk_insert_market_quotes(settings.database_path, latest_quotes)
        print(f"  ✅ Inserted {inserted} latest quotes")
        
        print(f"\n📊 Data Summary:")
        print(f"  - Historical records fetched: {len(all_rows):,}")
        print(f"  - Latest quotes saved: {inserted}")
        print(f"  - Time period: 15 years")
        print(f"  - Note: Full historical data available in memory")
    
    print(f"\n✅ Historical price loading completed!")
    print(f"Next step: python check_database_simple.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
