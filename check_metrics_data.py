#!/usr/bin/env python3
"""Quick diagnostic script to check what metrics have data."""

import sqlite3
from pathlib import Path

db_path = Path("data/sqlite/benchmarkos_chatbot.sqlite3")

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("DATABASE STATISTICS")
print("=" * 60)

# Basic counts
ticker_count = cursor.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
fact_count = cursor.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0]
metric_count = cursor.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
quote_count = cursor.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]

print(f"📊 Tickers: {ticker_count}")
print(f"📊 Financial Facts: {fact_count}")
print(f"📊 Metric Records: {metric_count}")
print(f"📊 Quote Records: {quote_count}")

print("\n" + "=" * 60)
print("METRICS BY TYPE (Top 30)")
print("=" * 60)

metrics_by_type = cursor.execute("""
    SELECT metric, COUNT(*) as count, COUNT(DISTINCT ticker) as tickers
    FROM metrics 
    GROUP BY metric 
    ORDER BY count DESC 
    LIMIT 30
""").fetchall()

for metric, count, ticker_count in metrics_by_type:
    print(f"{metric:35s} | Records: {count:4d} | Tickers: {ticker_count:3d}")

print("\n" + "=" * 60)
print("MISSING KEY METRICS")
print("=" * 60)

# Check for key metrics we just added
key_metrics = [
    "current_ratio", "quick_ratio", "interest_coverage", 
    "asset_turnover", "gross_margin", "ps_ratio",
    "revenue_cagr_3y", "eps_cagr_3y", "adjusted_ebitda_margin"
]

for metric in key_metrics:
    count = cursor.execute(
        "SELECT COUNT(*) FROM metrics WHERE metric = ?", 
        (metric,)
    ).fetchone()[0]
    
    status = "✅" if count > 0 else "❌"
    print(f"{status} {metric:30s} | {count:4d} records")

print("\n" + "=" * 60)
print("SAMPLE TICKER METRICS")
print("=" * 60)

# Get a sample ticker
sample_ticker = cursor.execute(
    "SELECT ticker FROM metrics GROUP BY ticker ORDER BY COUNT(*) DESC LIMIT 1"
).fetchone()

if sample_ticker:
    ticker = sample_ticker[0]
    print(f"\n📈 Sample: {ticker}")
    ticker_metrics = cursor.execute("""
        SELECT metric, value, period 
        FROM metrics 
        WHERE ticker = ? 
        ORDER BY metric, period DESC
    """, (ticker,)).fetchall()
    
    current_metric = None
    for metric, value, period in ticker_metrics[:50]:  # Limit output
        if metric != current_metric:
            print(f"\n{metric}:")
            current_metric = metric
        print(f"  {period}: {value:.2f}")

conn.close()

print("\n" + "=" * 60)
print("RECOMMENDATION")
print("=" * 60)
print("Run these commands to populate missing metrics:")
print("1. cd C:\\Users\\Hania\\Desktop\\Team2-CBA-Project")
print("2. python -m benchmarkos_chatbot.cli refresh-metrics")
print("   (This will compute all derived metrics from financial facts)")

