#!/usr/bin/env python3
"""
Quick progress monitor - run this while ingestion is happening.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import database, load_settings

def monitor():
    settings = load_settings()
    db_path = settings.database_path
    
    try:
        with database.temporary_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM financial_facts")
            facts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM market_quotes")
            quotes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts")
            tickers_facts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT ticker) FROM market_quotes")
            tickers_quotes = cursor.fetchone()[0]
            
            # Get total rows
            cursor.execute("""
                SELECT SUM(cnt) FROM (
                    SELECT COUNT(*) as cnt FROM financial_facts
                    UNION ALL SELECT COUNT(*) FROM market_quotes
                    UNION ALL SELECT COUNT(*) FROM company_filings
                    UNION ALL SELECT COUNT(*) FROM metric_snapshots
                    UNION ALL SELECT COUNT(*) FROM kpi_values
                    UNION ALL SELECT COUNT(*) FROM audit_events
                    UNION ALL SELECT COUNT(*) FROM conversations
                    UNION ALL SELECT COUNT(*) FROM ticker_aliases
                )
            """)
            total = cursor.fetchone()[0]
            
            print(f"\n{'='*60}")
            print(f"  📊 Database Progress Monitor")
            print(f"{'='*60}")
            print(f"\n  Total Rows: {total:,}")
            print(f"\n  Financial Facts: {facts:,}")
            print(f"    • Tickers: {tickers_facts}")
            print(f"\n  Market Quotes: {quotes:,}")
            print(f"    • Tickers: {tickers_quotes}")
            print(f"\n  Price Data Coverage: {tickers_quotes}/482 ({tickers_quotes/482*100:.1f}%)")
            print(f"\n{'='*60}\n")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        monitor()
        print("  Checking again in 30 seconds... (Ctrl+C to stop)")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n  Monitoring stopped.")
            sys.exit(0)

