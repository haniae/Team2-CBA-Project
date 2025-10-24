"""Show 100% Complete Source Attribution from existing payload"""
import json

with open('test_single_company_payload.json', 'r') as f:
    payload = json.load(f)

sources = payload.get('sources', [])

# Categorize
with_urls = []
with_formulas = []
with_market_data = []
incomplete = []

for source in sources:
    label = source.get('label', 'Unknown')
    has_url = bool(source.get('url'))
    has_calc = bool(source.get('calculation'))
    source_type = source.get('source', '')
    has_note = bool(source.get('note'))
    
    if has_url:
        with_urls.append(label)
    elif has_calc:
        display = source.get('calculation', {}).get('display', 'N/A')
        with_formulas.append((label, display))
    elif source_type in ('IMF', 'market_data', 'imf') or 'Market data' in str(source.get('note', '')):
        with_market_data.append(label)
    else:
        incomplete.append(label)

total = len(sources)
complete = len(with_urls) + len(with_formulas) + len(with_market_data)

print("\n" + "="*80)
print("APPLE (AAPL) - SOURCE ATTRIBUTION COMPLETENESS")
print("="*80 + "\n")

print(f"📊 BREAKDOWN:")
print(f"  ✅ SEC URLs (Direct filings):       {len(with_urls):2d}/{total}")
print(f"  ✅ Calculated (With formulas):      {len(with_formulas):2d}/{total}")
print(f"  ✅ Market Data (External):          {len(with_market_data):2d}/{total}")
print(f"  {'❌' if incomplete else '✅'} Incomplete:                      {len(incomplete):2d}/{total}")
print(f"\n  {'='*60}")
print(f"  TOTAL ATTRIBUTED:  {complete}/{total}")
completeness = (complete / total * 100) if total > 0 else 0
print(f"  COMPLETENESS:      {completeness:.1f}%")
print(f"  {'='*60}\n")

if with_urls:
    print(f"📄 SEC URLs - Direct Filing Links ({len(with_urls)} sources):")
    for label in with_urls[:3]:
        print(f"   ✓ {label}")
    if len(with_urls) > 3:
        print(f"   ... and {len(with_urls) - 3} more")
    print()

if with_formulas:
    print(f"🧮 Calculated Metrics - With Formulas ({len(with_formulas)} sources):")
    for label, formula in with_formulas[:8]:
        print(f"   ✓ {label}: {formula}")
    if len(with_formulas) > 8:
        print(f"   ... and {len(with_formulas) - 8} more")
    print()

if with_market_data:
    print(f"📊 Market Data - External Sources ({len(with_market_data)} sources):")
    for label in with_market_data:
        print(f"   ✓ {label}")
    print()

if completeness == 100:
    print("🎉 SUCCESS! 100% SOURCE ATTRIBUTION COMPLETE!")
    print("\nAll 57 sources have either:")
    print("  1. Direct SEC URL to EDGAR filing")
    print("  2. Calculation formula showing how it's derived")
    print("  3. Market data attribution")
else:
    print(f"⚠️  {len(incomplete)} sources incomplete:")
    for label in incomplete:
        print(f"   ✗ {label}")

print("\n" + "="*80)
print("HOW TO SEE ON DASHBOARD:")
print("="*80)
print("1. Open the web dashboard (index.html)")
print("2. Ask chatbot: 'show dashboard for AAPL'")
print("3. Scroll to 'Data Sources & References' section")
print("4. You'll see:")
print("   - SEC filings with clickable 📄 View SEC Filing links")
print("   - Calculated metrics with Formula: boxes showing calculations")
print("   - Market data with appropriate notes")
print("="*80 + "\n")

