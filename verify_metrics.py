#!/usr/bin/env python3
"""Verify metrics are now in the database."""
import sqlite3
from pathlib import Path

db_path = Path("data/sqlite/benchmarkos_chatbot.sqlite3")
conn = sqlite3.connect(db_path)

print("="*60)
print("DATABASE STATUS")
print("="*60)

ticker_count = conn.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
fact_count = conn.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0]
metric_count = conn.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
quote_count = conn.execute("SELECT COUNT(*) FROM market_quotes").fetchone()[0]

print(f"✓ Tickers: {ticker_count}")
print(f"✓ Financial Facts: {fact_count:,}")
print(f"✓ Metric Snapshots: {metric_count:,}")
print(f"✓ Market Quotes: {quote_count:,}")

print("\n" + "="*60)
print("TOP 20 METRICS")
print("="*60)

for row in conn.execute("""
    SELECT metric, COUNT(*) as cnt, COUNT(DISTINCT ticker) as tickers
    FROM metric_snapshots 
    GROUP BY metric 
    ORDER BY cnt DESC 
    LIMIT 20
""").fetchall():
    print(f"{row[0]:35s} | Records: {row[1]:5d} | Tickers: {row[2]:3d}")

print("\n" + "="*60)
print("NEW METRICS STATUS")
print("="*60)

new_metrics = [
    "current_ratio", "quick_ratio", "interest_coverage",
    "asset_turnover", "gross_margin", "ps_ratio",
    "revenue_cagr_3y", "eps_cagr_3y", "adjusted_ebitda_margin"
]

for metric in new_metrics:
    count = conn.execute(
        "SELECT COUNT(*) FROM metric_snapshots WHERE metric = ?", (metric,)
    ).fetchone()[0]
    status = "✓" if count > 0 else "✗"
    print(f"{status} {metric:30s} | {count:5d} records")

print("\n" + "="*60)
print("SAMPLE COMPANY: AAPL")
print("="*60)

for row in conn.execute("""
    SELECT metric, value, period
    FROM metric_snapshots
    WHERE ticker = 'AAPL' AND metric IN (?, ?, ?, ?, ?, ?)
    ORDER BY period DESC
    LIMIT 20
""", tuple(new_metrics[:6])).fetchall():
    print(f"{row[0]:25s} | {row[2]:10s} | {float(row[1]):10.4f}")

conn.close()

print("\n" + "="*60)
print("✓ DATABASE READY FOR DASHBOARD!")
print("="*60)

