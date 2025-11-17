#!/usr/bin/env python3
"""Quick script to add test Apple data to verify percentage fix."""

import sqlite3
from datetime import datetime

db_path = "data/benchmarkos.db"

# Apple test data (realistic FY2023 and FY2024 figures)
test_data = [
    # FY2023
    ("AAPL", "Apple Inc.", "revenue", 383285000000.0, "2023-FY", "USD"),
    ("AAPL", "Apple Inc.", "net_income", 96995000000.0, "2023-FY", "USD"),
    ("AAPL", "Apple Inc.", "eps_diluted", 6.16, "2023-FY", "USD"),
    ("AAPL", "Apple Inc.", "operating_margin", 0.296, "2023-FY", "ratio"),
    ("AAPL", "Apple Inc.", "gross_margin", 0.443, "2023-FY", "ratio"),
    
    # FY2024
    ("AAPL", "Apple Inc.", "revenue", 391035000000.0, "2024-FY", "USD"),
    ("AAPL", "Apple Inc.", "net_income", 93736000000.0, "2024-FY", "USD"),
    ("AAPL", "Apple Inc.", "eps_diluted", 6.08, "2024-FY", "USD"),
    ("AAPL", "Apple Inc.", "operating_margin", 0.302, "2024-FY", "ratio"),
    ("AAPL", "Apple Inc.", "gross_margin", 0.456, "2024-FY", "ratio"),
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

now = datetime.utcnow().isoformat()

for ticker, company, metric, value, period, unit in test_data:
    fiscal_year = int(period.split("-")[0])
    cursor.execute(
        """
        INSERT INTO financial_facts 
        (cik, ticker, company_name, metric, value, period, fiscal_year, fiscal_period, unit, source, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("0000320193", ticker, company, metric, value, period, fiscal_year, "FY", unit, "TEST_DATA", now)
    )

conn.commit()
conn.close()

print("✅ Test data added successfully!")
print("\nAdded records:")
for ticker, company, metric, value, period, unit in test_data:
    if metric == "revenue":
        print(f"  {period}: {metric} = ${value/1e9:.1f}B")
    elif "margin" in metric:
        print(f"  {period}: {metric} = {value*100:.1f}%")
    else:
        print(f"  {period}: {metric} = {value}")

print("\nExpected calculation:")
print("  FY2024 revenue: $391.0B")
print("  FY2023 revenue: $383.3B")
print("  Growth: ((391.0 - 383.3) / 383.3) * 100 = 2.0%")
print("")
print("This should now show '2.0% increase' instead of '391,035,000,000% increase'!")

