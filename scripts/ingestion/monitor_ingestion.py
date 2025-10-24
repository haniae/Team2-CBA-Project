"""Monitor the progress of data ingestion."""
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def get_db_stats():
    """Get current database statistics."""
    db_path = "data/sqlite/benchmarkos_chatbot.sqlite3"
    if not os.path.exists(db_path):
        print("Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print(f"INGESTION PROGRESS MONITOR - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Key metrics
    metrics = [
        ("Financial Facts", "SELECT COUNT(*) FROM financial_facts"),
        ("SEC Filings", "SELECT COUNT(*) FROM company_filings"),
        ("Metric Snapshots", "SELECT COUNT(*) FROM metric_snapshots"),
        ("Unique Companies", "SELECT COUNT(DISTINCT ticker) FROM ticker_aliases"),
    ]
    
    for name, query in metrics:
        count = cursor.execute(query).fetchone()[0]
        print(f"  {name:20s}: {count:,}")
    
    # Year range
    years = cursor.execute("""
        SELECT MIN(fiscal_year), MAX(fiscal_year)
        FROM financial_facts
        WHERE fiscal_year IS NOT NULL
    """).fetchone()
    
    if years[0]:
        print(f"\n  Data Year Range: {years[0]} to {years[1]}")
    
    # Recent activity
    recent = cursor.execute("""
        SELECT MAX(updated_at)
        FROM ticker_aliases
    """).fetchone()[0]
    
    if recent:
        print(f"  Last Update: {recent}")
    
    # Check progress file
    progress_file = Path(".ingestion_progress_extended.json")
    if progress_file.exists():
        completed = progress_file.read_text().count('\n')
        print(f"\n  Completed Tickers: {completed}/482")
    
    print()
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    get_db_stats()

