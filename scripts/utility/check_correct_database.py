"""Check the correct database that was actually used for ingestion."""
import sqlite3
from pathlib import Path

# The actual database path from settings
db_path = Path(r'C:\Users\Hania\Documents\GitHub\Project\benchmarkos_chatbot.sqlite3')

if not db_path.exists():
    print(f"❌ Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("📊 CORRECT DATABASE ANALYSIS (The One You Actually Ingested)")
print("=" * 70)
print(f"\nDatabase: {db_path}")
print(f"Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
print(f"Size: {db_path.stat().st_size / (1024*1024*1024):.2f} GB\n")

# Get all tables
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()

print("=" * 70)
print("ALL TABLES - ROW COUNTS:")
print("=" * 70)

total_rows = 0
table_counts = {}

for (table_name,) in tables:
    try:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        table_counts[table_name] = count
        total_rows += count
        if count > 0:
            print(f"  {table_name:40} {count:>12,} rows")
    except Exception as e:
        table_counts[table_name] = 0

print("=" * 70)
print(f"  {'TOTAL ROWS':40} {total_rows:>12,}")
print("=" * 70)

# Key statistics
print("\n📈 KEY STATISTICS:")
print("-" * 70)

key_tables = {
    'financial_facts': 'Financial Facts',
    'metric_snapshots': 'Metric Snapshots',
    'market_quotes': 'Market Quotes',
    'kpi_values': 'KPI Values',
    'company_filings': 'Company Filings',
    'conversations': 'Conversations',
    'audit_events': 'Audit Events'
}

for table, name in key_tables.items():
    count = table_counts.get(table, 0)
    print(f"  {name:30} {count:>12,} rows")

# Company count
try:
    companies = cursor.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
    print(f"\n  {'Companies':30} {companies:>12}")
except:
    pass

# Year range
try:
    result = cursor.execute("""
        SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT fiscal_year)
        FROM financial_facts 
        WHERE fiscal_year IS NOT NULL
    """).fetchone()
    if result and result[0]:
        print(f"  {'Year Range':30} {result[0]} to {result[1]} ({result[2]} years)")
except:
    pass

print("\n" + "=" * 70)
print("✅ Analysis Complete")
print("=" * 70)

conn.close()

