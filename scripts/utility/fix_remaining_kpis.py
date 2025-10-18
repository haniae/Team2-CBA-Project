#!/usr/bin/env python3
"""
Script to fix remaining KPI issues:
1. TSR - fetch historical price data
2. ev_ebitda - improve EBITDA calculation
3. pe_ratio - improve EPS calculation
4. pb_ratio - ensure market quotes are available
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine


def fetch_historical_quotes(db_path: str, tickers: list, days_back: int = 365) -> None:
    """Fetch historical quotes for TSR calculation."""
    print(f"Fetching historical quotes for {len(tickers)} tickers...")
    
    con = sqlite3.connect(db_path)
    
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(tickers)}")
        
        try:
            # Get historical data
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                continue
            
            # Get price from 1 year ago
            one_year_ago = datetime.now() - timedelta(days=days_back)
            hist_data = hist[hist.index <= one_year_ago]
            
            if hist_data.empty:
                continue
            
            # Get the closest date to 1 year ago
            closest_date = hist_data.index[-1]
            price = hist_data['Close'].iloc[-1]
            
            # Insert historical quote
            con.execute("""
            INSERT OR REPLACE INTO market_quotes 
            (ticker, price, currency, quote_time, source, raw)
            VALUES (?, ?, 'USD', ?, 'yfinance_historical', ?)
            """, (ticker, float(price), closest_date.isoformat(), 
                  f'{{"historical": true, "date": "{closest_date.isoformat()}"}}'))
            
        except Exception as e:
            print(f"    Error fetching {ticker}: {e}")
            continue
    
    con.commit()
    con.close()
    print("Historical quotes fetch completed")


def improve_ebitda_calculation(db_path: str) -> None:
    """Improve EBITDA calculation by using alternative methods."""
    print("Improving EBITDA calculation...")
    
    con = sqlite3.connect(db_path)
    
    # Find tickers missing EBITDA
    missing_ebitda = con.execute("""
    SELECT DISTINCT ticker FROM financial_facts 
    WHERE ticker NOT IN (
        SELECT DISTINCT ticker FROM metric_snapshots 
        WHERE metric='ebitda' AND value IS NOT NULL
    )
    """).fetchall()
    
    print(f"Found {len(missing_ebitda)} tickers missing EBITDA")
    
    for (ticker,) in missing_ebitda:
        # Try to calculate EBITDA from available data
        data = con.execute("""
        SELECT metric, value FROM financial_facts 
        WHERE ticker=? AND metric IN ('operating_income', 'depreciation_and_amortization', 'ebit', 'net_income', 'interest_expense', 'income_tax_expense')
        ORDER BY fiscal_year DESC LIMIT 10
        """, (ticker,)).fetchall()
        
        metrics = {row[0]: row[1] for row in data}
        
        ebitda = None
        
        # Method 1: operating_income + depreciation
        if 'operating_income' in metrics and 'depreciation_and_amortization' in metrics:
            ebitda = metrics['operating_income'] + metrics['depreciation_and_amortization']
        
        # Method 2: net_income + interest + tax + depreciation
        elif all(k in metrics for k in ['net_income', 'interest_expense', 'income_tax_expense', 'depreciation_and_amortization']):
            ebitda = (metrics['net_income'] + 
                     metrics['interest_expense'] + 
                     metrics['income_tax_expense'] + 
                     metrics['depreciation_and_amortization'])
        
        # Method 3: ebit + depreciation
        elif 'ebit' in metrics and 'depreciation_and_amortization' in metrics:
            ebitda = metrics['ebit'] + metrics['depreciation_and_amortization']
        
        if ebitda is not None:
            # Store as derived metric
            con.execute("""
            INSERT OR REPLACE INTO metric_snapshots 
            (ticker, metric, period, value, source, updated_at, start_year, end_year)
            VALUES (?, 'ebitda', 'FY2024', ?, 'derived_improved', datetime('now'), 2024, 2024)
            """, (ticker, ebitda))
            print(f"  {ticker}: Calculated EBITDA = {ebitda:,.0f}")
    
    con.commit()
    con.close()
    print("EBITDA calculation improvement completed")


def improve_eps_calculation(db_path: str) -> None:
    """Improve EPS calculation for better P/E ratio coverage."""
    print("Improving EPS calculation...")
    
    con = sqlite3.connect(db_path)
    
    # Find tickers missing EPS
    missing_eps = con.execute("""
    SELECT DISTINCT ticker FROM financial_facts 
    WHERE ticker NOT IN (
        SELECT DISTINCT ticker FROM metric_snapshots 
        WHERE metric IN ('pe_ratio') AND value IS NOT NULL
    )
    """).fetchall()
    
    print(f"Found {len(missing_eps)} tickers missing P/E ratio")
    
    for (ticker,) in missing_eps:
        # Get latest data
        data = con.execute("""
        SELECT metric, value FROM financial_facts 
        WHERE ticker=? AND metric IN ('net_income', 'shares_outstanding', 'weighted_avg_diluted_shares')
        ORDER BY fiscal_year DESC LIMIT 5
        """, (ticker,)).fetchall()
        
        metrics = {row[0]: row[1] for row in data}
        
        # Calculate EPS
        net_income = metrics.get('net_income')
        shares = metrics.get('weighted_avg_diluted_shares') or metrics.get('shares_outstanding')
        
        if net_income is not None and shares is not None and shares > 0:
            eps = net_income / shares
            
            # Store calculated EPS
            con.execute("""
            INSERT OR REPLACE INTO metric_snapshots 
            (ticker, metric, period, value, source, updated_at, start_year, end_year)
            VALUES (?, 'eps_diluted', 'FY2024', ?, 'derived_improved', datetime('now'), 2024, 2024)
            """, (ticker, eps))
            print(f"  {ticker}: Calculated EPS = {eps:.2f}")
    
    con.commit()
    con.close()
    print("EPS calculation improvement completed")


def ensure_market_quotes(db_path: str) -> None:
    """Ensure all tickers have market quotes for P/B ratio calculation."""
    print("Ensuring market quotes availability...")
    
    con = sqlite3.connect(db_path)
    
    # Find tickers without quotes
    missing_quotes = con.execute("""
    SELECT DISTINCT f.ticker FROM financial_facts f
    LEFT JOIN market_quotes m ON f.ticker = m.ticker
    WHERE m.ticker IS NULL
    """).fetchall()
    
    print(f"Found {len(missing_quotes)} tickers missing market quotes")
    
    if missing_quotes:
        tickers = [row[0] for row in missing_quotes]
        print(f"Fetching quotes for: {', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}")
        
        # Use yfinance to fetch current quotes
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                if 'currentPrice' in info:
                    price = info['currentPrice']
                    currency = info.get('currency', 'USD')
                    
                    con.execute("""
                    INSERT INTO market_quotes 
                    (ticker, price, currency, quote_time, source, raw)
                    VALUES (?, ?, ?, datetime('now'), 'yfinance_fix', ?)
                    """, (ticker, price, currency, str(info)))
                    print(f"  {ticker}: {price} {currency}")
                
            except Exception as e:
                print(f"    Error fetching {ticker}: {e}")
                continue
    
    con.commit()
    con.close()
    print("Market quotes fix completed")


def main():
    """Main function to fix remaining KPI issues."""
    settings = load_settings()
    db_path = settings.database_path
    
    print("=== FIXING REMAINING KPI ISSUES ===")
    
    # 1. Improve EBITDA calculation
    improve_ebitda_calculation(db_path)
    
    # 2. Improve EPS calculation
    improve_eps_calculation(db_path)
    
    # 3. Ensure market quotes
    ensure_market_quotes(db_path)
    
    # 4. Fetch historical quotes for TSR (sample of tickers)
    con = sqlite3.connect(db_path)
    sample_tickers = [row[0] for row in con.execute("""
    SELECT DISTINCT ticker FROM financial_facts 
    ORDER BY ticker LIMIT 50
    """).fetchall()]
    con.close()
    
    fetch_historical_quotes(db_path, sample_tickers)
    
    # 5. Refresh metrics
    print("\n=== REFRESHING METRICS ===")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("Metrics refreshed with all improvements")
    
    # 6. Show final results
    print(f"\n=== FINAL RESULTS ===")
    con = sqlite3.connect(db_path)
    total_tickers = con.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
    
    key_kpis = ['pe_ratio', 'ev_ebitda', 'pb_ratio', 'tsr', 'dividend_yield']
    
    for kpi in key_kpis:
        count = con.execute("""
        SELECT COUNT(DISTINCT ticker) FROM metric_snapshots 
        WHERE metric=? AND value IS NOT NULL
        """, (kpi,)).fetchone()[0]
        percentage = (count / total_tickers) * 100
        print(f"{kpi:15}: {count:3d}/{total_tickers} ({percentage:5.1f}%)")
    
    con.close()


if __name__ == "__main__":
    main()
