"""Verify which database the chatbot is actually using."""
from finanlyzeos_chatbot import load_settings
import sqlite3
from pathlib import Path

print("=" * 70)
print("🔗 CHATBOT DATABASE CONNECTION VERIFICATION")
print("=" * 70)

# Get chatbot settings
settings = load_settings()
db_path = Path(settings.database_path)

print(f"\n1. Chatbot Configuration:")
print(f"   Database Path: {settings.database_path}")
print(f"   File Exists: {db_path.exists()}")

if db_path.exists():
    print(f"   File Size: {db_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Check data in that database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n2. Data in Chatbot Database:")
    companies = cursor.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
    financial_facts = cursor.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0]
    metric_snapshots = cursor.execute("SELECT COUNT(*) FROM metric_snapshots").fetchone()[0]
    market_quotes = cursor.execute("SELECT COUNT(*) FROM market_quotes").fetchone()[0]
    
    print(f"   Companies: {companies:,}")
    print(f"   Financial Facts: {financial_facts:,}")
    print(f"   Metric Snapshots: {metric_snapshots:,}")
    print(f"   Market Quotes: {market_quotes:,}")
    
    total = financial_facts + metric_snapshots + market_quotes
    print(f"   Total Key Rows: {total:,}")
    
    print(f"\n3. Connection Status:")
    if companies > 500:
        print(f"   ✅ YES - Chatbot is connected to FULL database!")
        print(f"   ✅ You have {companies} companies (expected 500+)")
        print(f"   ✅ Database has {total:,} rows of data")
    else:
        print(f"   ⚠️  Chatbot is connected to SMALL database")
        print(f"   ⚠️  Only {companies} companies found")
    
    conn.close()
else:
    print(f"\n❌ Database file not found!")
    print(f"   The chatbot cannot connect to the database")

print("\n" + "=" * 70)

