"""Comprehensive test: Verify dashboards work for ALL S&P 500 companies with SEC URLs and financial data."""
import sys
import sqlite3
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Fix encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import Settings

# Setup
settings = Settings(database_path=Path("data/sqlite/finanlyzeos_chatbot.sqlite3"))
print("Creating chatbot...")
chatbot = FinanlyzeOSChatbot.create(settings)

# Get ALL companies from database
print("\nFetching all S&P 500 companies from database...")
conn = sqlite3.connect(str(settings.database_path))
cursor = conn.execute("""
    SELECT DISTINCT ticker, company_name 
    FROM financial_facts 
    WHERE company_name IS NOT NULL AND company_name != ''
    ORDER BY ticker
""")
all_companies = [(row[0], row[1]) for row in cursor]
conn.close()

total_companies = len(all_companies)
print(f"Found {total_companies} companies with data\n")

# Track detailed results
results = {
    "success": [],
    "failed": [],
    "errors": [],
    "no_sec_urls": [],
    "incomplete_data": []
}

print("="*80)
print("TESTING DASHBOARD GENERATION FOR ALL COMPANIES")
print("="*80)
print(f"Testing {total_companies} companies (showing progress every 50 companies)...\n")

# Test each company
for idx, (ticker, company_name) in enumerate(all_companies, 1):
    try:
        # Create query
        query = f"show comprehensive financial summary for {company_name}"
        
        # Reset and ask
        chatbot.last_structured_response = {}
        response = chatbot.ask(query)
        
        # Check if dashboard was generated
        dashboard = chatbot.last_structured_response.get("dashboard")
        if not dashboard:
            results["failed"].append((ticker, company_name, "No dashboard generated"))
            print(f"X {ticker:6} - {company_name[:50]:50} -> NO DASHBOARD")
            continue
            
        payload = dashboard.get("payload", {})
        detected_ticker = dashboard.get("ticker")
        
        # Check ticker match
        if detected_ticker != ticker:
            results["failed"].append((ticker, company_name, detected_ticker))
            print(f"X {ticker:6} - {company_name[:50]:50} -> Wrong ticker: {detected_ticker}")
            continue
        
        # Check for SEC URLs in sources
        sources = payload.get("sources", [])
        has_sec_urls = any(s.get("url") or s.get("urls") for s in sources)
        
        # Check for key financial data
        key_financials = payload.get("key_financials", {})
        has_financial_data = bool(key_financials.get("rows"))
        kpi_summary = payload.get("kpi_summary", [])
        has_kpis = len(kpi_summary) > 0
        
        # Categorize results
        if not has_sec_urls:
            results["no_sec_urls"].append((ticker, company_name, len(sources)))
            print(f"! {ticker:6} - {company_name[:40]:40} -> NO SEC URLs ({len(sources)} sources)")
        
        if not has_financial_data or not has_kpis:
            results["incomplete_data"].append((ticker, company_name, 
                                              f"rows={len(key_financials.get('rows', []))}, kpis={len(kpi_summary)}"))
            print(f"! {ticker:6} - {company_name[:40]:40} -> Incomplete data")
        
        # If everything looks good
        if has_sec_urls and has_financial_data and has_kpis:
            results["success"].append((ticker, company_name))
            status = "+"
        
        # Progress indicator
        if idx % 50 == 0:
            success_rate = 100 * len(results["success"]) / idx
            print(f"\nProgress: {idx}/{total_companies} tested ({success_rate:.1f}% fully working)")
    
    except Exception as e:
        error_msg = str(e)
        results["errors"].append((ticker, company_name, error_msg))
        print(f"X {ticker:6} - {company_name[:30]:30} - ERROR: {error_msg[:60]}")

# Final Results
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)
print(f"+ Fully Working:        {len(results['success']):4} / {total_companies} ({100*len(results['success'])/total_companies:.1f}%)")
print(f"! Missing SEC URLs:    {len(results['no_sec_urls']):4} / {total_companies}")
print(f"! Incomplete Data:     {len(results['incomplete_data']):4} / {total_companies}")
print(f"X Failed:              {len(results['failed']):4} / {total_companies}")
print(f"! Errors:              {len(results['errors']):4} / {total_companies}")
print("="*80)

# Show missing SEC URLs if any
if results["no_sec_urls"]:
    print(f"\n! MISSING SEC URLs ({len(results['no_sec_urls'])}):")
    print("-"*80)
    for ticker, name, source_count in results["no_sec_urls"][:20]:
        print(f"  {ticker:6} - {name[:45]:45} ({source_count} sources)")
    if len(results["no_sec_urls"]) > 20:
        print(f"  ... and {len(results['no_sec_urls']) - 20} more")

# Show incomplete data if any
if results["incomplete_data"]:
    print(f"\n! INCOMPLETE DATA ({len(results['incomplete_data'])}):")
    print("-"*80)
    for ticker, name, details in results["incomplete_data"][:20]:
        print(f"  {ticker:6} - {name[:40]:40} - {details}")
    if len(results["incomplete_data"]) > 20:
        print(f"  ... and {len(results['incomplete_data']) - 20} more")

# Show failures if any
if results["failed"]:
    print(f"\nX FAILED DETECTIONS ({len(results['failed'])}):")
    print("-"*80)
    for ticker, name, detected in results["failed"][:20]:
        print(f"  {ticker:6} - {name[:45]:45} -> {detected or 'NONE'}")
    if len(results["failed"]) > 20:
        print(f"  ... and {len(results['failed']) - 20} more")

# Show errors if any
if results["errors"]:
    print(f"\n! ERRORS ({len(results['errors'])}):")
    print("-"*80)
    for ticker, name, error in results["errors"][:10]:
        print(f"  {ticker:6} - {name[:30]:30} - {error[:50]}")
    if len(results["errors"]) > 10:
        print(f"  ... and {len(results['errors']) - 10} more")

# Final verdict
print("\n" + "="*80)
if len(results["success"]) == total_companies:
    print("SUCCESS! ALL S&P 500 COMPANIES HAVE COMPLETE DASHBOARDS WITH SEC URLs!")
elif len(results["success"]) >= total_companies * 0.95:
    print(f"EXCELLENT! {100*len(results['success'])/total_companies:.1f}% fully working")
elif len(results["success"]) >= total_companies * 0.90:
    print(f"GOOD! {100*len(results['success'])/total_companies:.1f}% fully working")
else:
    print(f"NEEDS IMPROVEMENT: {100*len(results['success'])/total_companies:.1f}% fully working")
print("="*80)

# Save detailed results
results_file = Path("sp500_dashboard_test_results.txt")
with open(results_file, "w", encoding="utf-8") as f:
    f.write("S&P 500 Dashboard Test Results\n")
    f.write("="*80 + "\n\n")
    f.write(f"Total Companies: {total_companies}\n")
    f.write(f"Fully Working: {len(results['success'])} ({100*len(results['success'])/total_companies:.1f}%)\n")
    f.write(f"Missing SEC URLs: {len(results['no_sec_urls'])}\n")
    f.write(f"Incomplete Data: {len(results['incomplete_data'])}\n")
    f.write(f"Failed: {len(results['failed'])}\n")
    f.write(f"Errors: {len(results['errors'])}\n\n")
    
    if results["no_sec_urls"]:
        f.write("\nMissing SEC URLs:\n")
        f.write("-"*80 + "\n")
        for ticker, name, source_count in results["no_sec_urls"]:
            f.write(f"{ticker:6} - {name[:50]:50} ({source_count} sources)\n")
    
    if results["incomplete_data"]:
        f.write("\nIncomplete Data:\n")
        f.write("-"*80 + "\n")
        for ticker, name, details in results["incomplete_data"]:
            f.write(f"{ticker:6} - {name[:50]:50} - {details}\n")
    
    if results["failed"]:
        f.write("\nFailed Companies:\n")
        f.write("-"*80 + "\n")
        for ticker, name, detected in results["failed"]:
            f.write(f"{ticker:6} - {name[:50]:50} -> {detected or 'NONE'}\n")
    
    if results["errors"]:
        f.write("\nErrors:\n")
        f.write("-"*80 + "\n")
        for ticker, name, error in results["errors"]:
            f.write(f"{ticker:6} - {name} - {error}\n")

print(f"\nDetailed results saved to: {results_file}")
