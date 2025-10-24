"""Quick test: Verify a single company has complete dashboard with SEC URLs."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import Settings

# Setup
settings = Settings(database_path=Path("data/sqlite/benchmarkos_chatbot.sqlite3"))
print("Creating chatbot...")
chatbot = BenchmarkOSChatbot.create(settings)

# Test with a well-known company (Apple)
ticker = "AAPL"
company_name = "Apple Inc."

print(f"\n{'='*80}")
print(f"Testing dashboard for {company_name} ({ticker})")
print(f"{'='*80}\n")

# Query for dashboard
query = f"show comprehensive financial summary for {company_name}"
chatbot.last_structured_response = {}
response = chatbot.ask(query)

print(f"Response: {response}\n")

# Check dashboard
dashboard = chatbot.last_structured_response.get("dashboard")
if not dashboard:
    print("❌ FAILED: No dashboard generated")
    sys.exit(1)

payload = dashboard.get("payload", {})
detected_ticker = dashboard.get("ticker")

print(f"✓ Dashboard generated for ticker: {detected_ticker}")

# Check sources with SEC URLs
sources = payload.get("sources", [])
print(f"\n📊 Sources: {len(sources)} total")

has_urls = 0
for source in sources:
    if source.get("url") or source.get("urls"):
        has_urls += 1
        print(f"  ✓ {source.get('label', source.get('metric'))}: {source.get('url', 'Multiple URLs')[:80]}...")
    else:
        print(f"  ⚠ {source.get('label', source.get('metric'))}: NO URL")

print(f"\n{'='*80}")
print(f"SEC URLs: {has_urls}/{len(sources)} sources have clickable URLs")

# Check key financial data
key_financials = payload.get("key_financials", {})
rows = key_financials.get("rows", [])
print(f"Financial Data Rows: {len(rows)}")

kpi_summary = payload.get("kpi_summary", [])
print(f"KPI Summary: {len(kpi_summary)} metrics")

# Check for essential sections
sections_to_check = [
    ("meta", "Meta Information"),
    ("price", "Price Data"),
    ("overview", "Overview"),
    ("key_stats", "Key Statistics"),
    ("market_data", "Market Data"),
    ("valuation_table", "Valuation Table"),
    ("key_financials", "Key Financials"),
    ("charts", "Charts"),
    ("kpi_summary", "KPI Summary"),
    ("kpi_series", "KPI Series"),
    ("sources", "Sources"),
]

print(f"\n{'='*80}")
print("Dashboard Sections:")
for section_key, section_name in sections_to_check:
    section_data = payload.get(section_key)
    if section_data:
        if isinstance(section_data, list):
            print(f"  ✓ {section_name}: {len(section_data)} items")
        elif isinstance(section_data, dict):
            print(f"  ✓ {section_name}: {len(section_data)} keys")
        else:
            print(f"  ✓ {section_name}: present")
    else:
        print(f"  ⚠ {section_name}: MISSING")

# Final verdict
print(f"\n{'='*80}")
if has_urls > 0 and len(rows) > 0 and len(kpi_summary) > 0:
    print(f"✅ SUCCESS! Dashboard is complete with {has_urls} clickable SEC URLs")
else:
    print(f"⚠ INCOMPLETE: URLs={has_urls}, Rows={len(rows)}, KPIs={len(kpi_summary)}")
print(f"{'='*80}\n")

# Save payload for inspection
output_file = Path("test_single_company_payload.json")
with open(output_file, "w") as f:
    json.dump(payload, f, indent=2, default=str)
print(f"Full payload saved to: {output_file}")

