"""Analyze which metrics are missing SEC URLs and why."""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import Settings

# Setup
settings = Settings(database_path=Path("data/sqlite/benchmarkos_chatbot.sqlite3"))
chatbot = BenchmarkOSChatbot.create(settings)

# Test Apple
ticker = "AAPL"
print(f"Analyzing source completeness for {ticker}...")

query = f"show comprehensive financial summary for Apple Inc."
chatbot.last_structured_response = {}
response = chatbot.ask(query)

dashboard = chatbot.last_structured_response.get("dashboard")
if not dashboard:
    print("No dashboard generated!")
    sys.exit(1)

payload = dashboard.get("payload", {})
sources = payload.get("sources", [])

print(f"\nTotal sources: {len(sources)}")
print("="*80)

# Categorize by source type
by_source_type = {}
with_urls = {}
without_urls = {}

for s in sources:
    source_type = s.get("source", "unknown")
    metric = s.get("metric")
    has_url = bool(s.get("url") or s.get("urls"))
    
    by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
    
    if has_url:
        with_urls[source_type] = with_urls.get(source_type, 0) + 1
    else:
        if source_type not in without_urls:
            without_urls[source_type] = []
        without_urls[source_type].append(metric)

print("\nBy Source Type:")
for source_type, count in sorted(by_source_type.items()):
    urls_count = with_urls.get(source_type, 0)
    print(f"  {source_type:15} {urls_count:3}/{count:3} have URLs ({100*urls_count/count:.0f}%)")

print("\n" + "="*80)
print("EDGAR-sourced metrics WITHOUT URLs:")
print("="*80)
if "edgar" in without_urls:
    for metric in sorted(without_urls["edgar"]):
        print(f"  - {metric}")
else:
    print("  (none - all EDGAR metrics have URLs!)")

print("\n" + "="*80)
print("Derived metrics WITHOUT URLs (expected):")
print("="*80)
if "derived" in without_urls:
    for metric in sorted(without_urls["derived"]):
        print(f"  - {metric}")
else:
    print("  (all derived metrics have URLs)")

# Check financial_facts availability
print("\n" + "="*80)
print("Checking financial_facts availability for EDGAR metrics without URLs:")
print("="*80)

if "edgar" in without_urls:
    conn = sqlite3.connect(str(settings.database_path))
    for metric in sorted(without_urls["edgar"]):
        cursor = conn.execute("""
            SELECT COUNT(*), MAX(fiscal_year)
            FROM financial_facts
            WHERE ticker = ? AND metric = ?
        """, (ticker, metric))
        count, max_year = cursor.fetchone()
        print(f"  {metric:30} -> {count:3} records, latest FY{max_year or 'N/A'}")
    conn.close()

