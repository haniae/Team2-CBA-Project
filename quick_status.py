#!/usr/bin/env python3
"""Quick database status check."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot import load_settings
import sqlite3

settings = load_settings()
db_path = settings.database_path

print(f"\n📊 DATABASE STATUS")
print("="*70)
print(f"Database: {db_path}")
print(f"Size: {Path(db_path).stat().st_size / (1024*1024):.2f} MB")
print("="*70)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

tables = [
    'financial_facts',
    'market_quotes', 
    'company_filings',
    'metric_snapshots',
    'kpi_values',
    'audit_events',
    'conversations',
    'ticker_aliases'
]

total = 0
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        total += count
        status = "✅" if count > 0 else "  "
        print(f"{status} {table:25s}: {count:>12,} rows")
    except Exception as e:
        print(f"   {table:25s}: ERROR - {e}")

print("="*70)
print(f"   {'TOTAL':25s}: {total:>12,} rows")
print("="*70)

# Price data details
cur.execute("SELECT COUNT(DISTINCT ticker) FROM market_quotes")
tickers_with_prices = cur.fetchone()[0]
print(f"\n💰 Price Data: {tickers_with_prices} tickers have quotes")

# Financial facts details  
cur.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts")
tickers_with_facts = cur.fetchone()[0]
print(f"📊 Financial Data: {tickers_with_facts} tickers have facts")

# Year range
cur.execute("SELECT MIN(fiscal_year), MAX(fiscal_year) FROM financial_facts WHERE fiscal_year IS NOT NULL")
min_year, max_year = cur.fetchone()
print(f"📅 Year Range: {min_year} - {max_year}")

print("\n" + "="*70 + "\n")

conn.close()

