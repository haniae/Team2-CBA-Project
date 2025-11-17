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
from finanlyzeos_chatbot import database
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.data_sources import MarketQuote
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe

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
        print(f"\n💾 Saving ALL historical quotes to database...")
        
        # Convert ALL historical data to MarketQuote objects
        all_quotes = []
        
        for ticker, date_str, close, adj_close, volume in all_rows:
            # Parse the date string to create a proper timestamp
            date_obj = datetime.fromisoformat(date_str)
            timestamp = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=timezone.utc)
            
            all_quotes.append(MarketQuote(
                ticker=ticker,
                price=close,
                currency="USD",
                volume=volume,
                timestamp=timestamp,
                source="yfinance_historical",
                raw={"date": date_str, "close": close, "adj_close": adj_close, "volume": volume}
            ))
        
        print(f"  📦 Prepared {len(all_quotes):,} market quotes for insertion...")
        
        # Insert all historical quotes in batches to avoid memory issues
        batch_size = 10000
        total_inserted = 0
        
        for i in range(0, len(all_quotes), batch_size):
            batch = all_quotes[i:i+batch_size]
            inserted = database.bulk_insert_market_quotes(settings.database_path, batch)
            total_inserted += inserted
            print(f"  ✅ Inserted batch {i//batch_size + 1}/{math.ceil(len(all_quotes)/batch_size)}: {inserted:,} quotes (Total: {total_inserted:,})")
        
        print(f"\n📊 Data Summary:")
        print(f"  - Historical records fetched: {len(all_rows):,}")
        print(f"  - Total quotes saved to database: {total_inserted:,}")
        print(f"  - Time period: 15 years")
        print(f"  - ✅ Full historical data now persisted in database!")
    
    print(f"\n✅ Historical price loading completed!")
    print(f"Next step: python check_database_simple.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
