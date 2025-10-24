#!/usr/bin/env python3
"""
Simple database analysis script.
"""

import sqlite3
import sys
from pathlib import Path

def main():
    """Check database contents."""
    db_path = Path("data/sqlite/benchmarkos_chatbot.sqlite3")
    
    if not db_path.exists():
        print("❌ Database not found!")
        return 1
    
    print("=== BenchmarkOS Database Analysis ===\n")
    
    conn = sqlite3.connect(str(db_path))
    
    # Check all tables and their row counts
    print("📊 Table Statistics:")
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    
    for (table_name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  - {table_name}: {count:,} rows")
    
    print("\n🏢 Company Coverage:")
    
    # Check unique companies
    companies = conn.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
    print(f"  - Unique companies with financial data: {companies}")
    
    # Check market quotes
    quotes = conn.execute("SELECT COUNT(*) FROM market_quotes").fetchone()[0]
    print(f"  - Market quotes: {quotes:,}")
    
    # Check KPI values
    kpis = conn.execute("SELECT COUNT(*) FROM kpi_values").fetchone()[0]
    print(f"  - KPI values: {kpis:,}")
    
    # Check metric snapshots
    snapshots = conn.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
    print(f"  - Metric snapshots: {snapshots:,}")
    
    print("\n📈 Top Companies by Data Volume:")
    sample_companies = conn.execute("""
        SELECT ticker, COUNT(*) as fact_count 
        FROM financial_facts 
        GROUP BY ticker 
        ORDER BY fact_count DESC 
        LIMIT 10
    """).fetchall()
    
    for ticker, count in sample_companies:
        print(f"  - {ticker}: {count:,} facts")
    
    print("\n💬 Chat History:")
    conversations = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    print(f"  - Total conversations: {conversations}")
    
    # Check table schemas
    print("\n🔍 Table Schemas:")
    for (table_name,) in tables:
        if table_name != 'sqlite_sequence':
            print(f"\n{table_name}:")
            schema = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            for col in schema:
                print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    
    print("\n✅ Database analysis complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
