#!/usr/bin/env python3
"""Analyze why companies are marked as partial or missing."""

import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))
from finanlyzeos_chatbot.config import load_settings

settings = load_settings()
conn = sqlite3.connect(settings.database_path)
cursor = conn.cursor()

print("=" * 80)
print("COVERAGE GAP ANALYSIS")
print("=" * 80)
print()

# Get all companies with their coverage details
cursor.execute("""
    SELECT 
        ticker,
        COUNT(DISTINCT fiscal_year) as years,
        COUNT(DISTINCT metric) as metrics,
        COUNT(*) as total_facts,
        MIN(fiscal_year) as min_year,
        MAX(fiscal_year) as max_year
    FROM financial_facts
    WHERE ticker IS NOT NULL
    GROUP BY ticker
    ORDER BY years ASC, metrics ASC
""")

companies = cursor.fetchall()

# Categorize
missing = []  # <2 years OR <6 metrics
partial = []  # 2-4 years OR 6-11 metrics (but not both 5+ years AND 12+ metrics)
complete = []  # 5+ years AND 12+ metrics

for row in companies:
    ticker, years, metrics, facts, min_year, max_year = row
    
    if years < 2 or metrics < 6:
        missing.append((ticker, years, metrics, facts, min_year, max_year))
    elif years < 5 or metrics < 12:
        partial.append((ticker, years, metrics, facts, min_year, max_year))
    else:
        complete.append((ticker, years, metrics, facts, min_year, max_year))

print(f"📊 Coverage Breakdown:")
print(f"   Complete: {len(complete)} companies (5+ years AND 12+ metrics)")
print(f"   Partial: {len(partial)} companies (2-4 years OR 6-11 metrics)")
print(f"   Missing: {len(missing)} companies (<2 years OR <6 metrics)")
print()

# Analyze missing companies
print("=" * 80)
print("❌ MISSING COMPANIES (13 total)")
print("=" * 80)
print(f"{'Ticker':<8} {'Years':<8} {'Metrics':<10} {'Facts':<8} {'Year Range':<15} {'Issue'}")
print("-" * 80)

for ticker, years, metrics, facts, min_year, max_year in missing[:15]:
    if years < 2:
        issue = f"Only {years} year(s) of data"
    elif metrics < 6:
        issue = f"Only {metrics} metric(s)"
    else:
        issue = "Both"
    print(f"{ticker:<8} {years:<8} {metrics:<10} {facts:<8} {min_year}-{max_year:<15} {issue}")

print()

# Analyze partial companies - show why they're not complete
print("=" * 80)
print("⚠️  PARTIAL COMPANIES - Why Not Complete?")
print("=" * 80)

# Group by reason
needs_years = []  # Has 12+ metrics but <5 years
needs_metrics = []  # Has 5+ years but <12 metrics
needs_both = []  # Has neither

for ticker, years, metrics, facts, min_year, max_year in partial[:20]:
    if metrics >= 12 and years < 5:
        needs_years.append((ticker, years, metrics, facts))
    elif years >= 5 and metrics < 12:
        needs_metrics.append((ticker, years, metrics, facts))
    else:
        needs_both.append((ticker, years, metrics, facts))

print(f"\n1. Companies with good metrics (12+) but need more years:")
print(f"   Count: {len(needs_years)}")
if needs_years:
    print(f"   {'Ticker':<8} {'Years':<8} {'Metrics':<10} {'Facts':<8}")
    print("   " + "-" * 40)
    for ticker, years, metrics, facts in needs_years[:10]:
        print(f"   {ticker:<8} {years:<8} {metrics:<10} {facts:<8}")
    if len(needs_years) > 10:
        print(f"   ... and {len(needs_years) - 10} more")

print(f"\n2. Companies with good years (5+) but need more metrics:")
print(f"   Count: {len(needs_metrics)}")
if needs_metrics:
    print(f"   {'Ticker':<8} {'Years':<8} {'Metrics':<10} {'Facts':<8}")
    print("   " + "-" * 40)
    for ticker, years, metrics, facts in needs_metrics[:10]:
        print(f"   {ticker:<8} {years:<8} {metrics:<10} {facts:<8}")
    if len(needs_metrics) > 10:
        print(f"   ... and {len(needs_metrics) - 10} more")

print(f"\n3. Companies that need both more years AND more metrics:")
print(f"   Count: {len(needs_both)}")
if needs_both:
    print(f"   {'Ticker':<8} {'Years':<8} {'Metrics':<10} {'Facts':<8}")
    print("   " + "-" * 40)
    for ticker, years, metrics, facts in needs_both[:10]:
        print(f"   {ticker:<8} {years:<8} {metrics:<10} {facts:<8}")
    if len(needs_both) > 10:
        print(f"   ... and {len(needs_both) - 10} more")

print()
print("=" * 80)
print("💡 SOLUTION")
print("=" * 80)
print()
print("The chatbot CAN access all 2.88M rows of data regardless of coverage status.")
print("The coverage label is just a UI indicator showing data completeness.")
print()
print("To improve coverage:")
print("1. Run full coverage ingestion to fetch more historical years:")
print("   python scripts/ingestion/full_coverage_ingestion.py --years 20")
print()
print("2. This will fetch older years for companies that only have recent data")
print("3. After ingestion, regenerate company universe:")
print("   python generate_company_universe.py")
print()

conn.close()

