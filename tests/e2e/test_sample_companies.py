"""Quick sample test: Verify dashboards work for a sample of 10 companies."""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import Settings

# Setup
settings = Settings(database_path=Path("data/sqlite/finanlyzeos_chatbot.sqlite3"))
print("Creating chatbot...")
chatbot = FinanlyzeOSChatbot.create(settings)

# Test a diverse sample of companies
test_companies = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("AMZN", "Amazon.com, Inc."),
    ("TSLA", "Tesla, Inc."),
    ("JPM", "JPMorgan Chase & Co"),
    ("V", "Visa Inc."),
    ("WMT", "Walmart Inc."),
    ("JNJ", "Johnson & Johnson"),
    ("PG", "Procter & Gamble Co"),
]

print(f"\nTesting {len(test_companies)} sample companies...")
print("="*80)

results = {"success": 0, "with_urls": 0, "total_urls": 0, "total_sources": 0}

for ticker, company_name in test_companies:
    try:
        query = f"show comprehensive financial summary for {company_name}"
        chatbot.last_structured_response = {}
        response = chatbot.ask(query)
        
        dashboard = chatbot.last_structured_response.get("dashboard")
        if not dashboard:
            print(f"X {ticker:6} - {company_name[:30]:30} -> NO DASHBOARD")
            continue
        
        payload = dashboard.get("payload", {})
        sources = payload.get("sources", [])
        urls_count = sum(1 for s in sources if s.get("url") or s.get("urls"))
        
        key_financials = payload.get("key_financials", {})
        rows = len(key_financials.get("rows", []))
        kpi_summary = payload.get("kpi_summary", [])
        kpis = len(kpi_summary)
        
        results["total_sources"] += len(sources)
        results["total_urls"] += urls_count
        if urls_count > 0:
            results["with_urls"] += 1
        
        if rows > 0 and kpis > 0 and urls_count > 0:
            results["success"] += 1
            print(f"+ {ticker:6} - {company_name[:30]:30} -> {urls_count:2}/{len(sources):2} URLs, {rows} rows, {kpis} KPIs")
        else:
            print(f"! {ticker:6} - {company_name[:30]:30} -> {urls_count:2}/{len(sources):2} URLs, {rows} rows, {kpis} KPIs")
    
    except Exception as e:
        print(f"X {ticker:6} - {company_name[:30]:30} -> ERROR: {str(e)[:40]}")

# Results
print("="*80)
print(f"\nResults:")
print(f"  Complete dashboards:    {results['success']}/{len(test_companies)} ({100*results['success']/len(test_companies):.0f}%)")
print(f"  Companies with URLs:    {results['with_urls']}/{len(test_companies)}")
print(f"  Total SEC URLs:         {results['total_urls']}")
print(f"  Total sources:          {results['total_sources']}")
print(f"  Avg URLs per company:   {results['total_urls']/len(test_companies):.1f}")
print(f"  Avg sources per company:{results['total_sources']/len(test_companies):.1f}")

if results["success"] == len(test_companies):
    print("\n>>> SUCCESS! All sample companies have complete dashboards with SEC URLs!")
elif results["success"] >= len(test_companies) * 0.8:
    print(f"\n>>> GOOD! {100*results['success']/len(test_companies):.0f}% of sample companies working")
else:
    print(f"\n>>> NEEDS WORK: Only {100*results['success']/len(test_companies):.0f}% of sample companies working")

