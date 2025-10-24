"""
Verify 100% Source Attribution Completeness
Shows that ALL sources have either:
1. Direct SEC URL
2. Calculation formula
3. Market data attribution
"""
import json

with open('test_single_company_payload.json', 'r') as f:
    data = json.load(f)

sources = data.get('sources', [])

print("=" * 80)
print("100% SOURCE ATTRIBUTION VERIFICATION")
print("=" * 80)
print(f"\nTotal Sources: {len(sources)}\n")

# Categorize sources
sec_urls = []
calculated = []
market_data = []
incomplete = []

for source in sources:
    label = source.get('label', 'Unknown')
    has_url = bool(source.get('url'))
    has_calc = bool(source.get('calculation'))
    source_type = source.get('source', 'unknown')
    has_note = bool(source.get('note'))
    
    if has_url:
        sec_urls.append(label)
    elif has_calc:
        calculated.append((label, source.get('calculation', {}).get('display', 'N/A')))
    elif source_type in ('IMF', 'market_data', 'imf') or has_note:
        market_data.append((label, source.get('note', 'Market data')))
    else:
        incomplete.append(label)

# Print summary
print(f"✅ SEC URLs (Direct filing links):     {len(sec_urls)}")
print(f"✅ Calculated (With formulas):         {len(calculated)}")
print(f"✅ Market Data (External sources):     {len(market_data)}")
print(f"❌ Incomplete (No attribution):        {len(incomplete)}")
print(f"\n{'=' * 80}")
print(f"TOTAL ATTRIBUTED: {len(sec_urls) + len(calculated) + len(market_data)}/{len(sources)}")

completeness = ((len(sec_urls) + len(calculated) + len(market_data)) / len(sources)) * 100
print(f"COMPLETENESS: {completeness:.1f}%")
print(f"{'=' * 80}\n")

# Show details
if sec_urls:
    print(f"\n📄 SEC URLs ({len(sec_urls)} sources):")
    for label in sec_urls[:5]:
        print(f"  ✓ {label}")
    if len(sec_urls) > 5:
        print(f"  ... and {len(sec_urls) - 5} more")

if calculated:
    print(f"\n🧮 Calculated Metrics ({len(calculated)} sources):")
    for label, formula in calculated[:5]:
        print(f"  ✓ {label}: {formula}")
    if len(calculated) > 5:
        print(f"  ... and {len(calculated) - 5} more")

if market_data:
    print(f"\n📊 Market Data ({len(market_data)} sources):")
    for label, note in market_data:
        print(f"  ✓ {label}: {note}")

if incomplete:
    print(f"\n❌ INCOMPLETE ({len(incomplete)} sources):")
    for label in incomplete:
        print(f"  ✗ {label}")

print(f"\n{'=' * 80}")
if completeness == 100:
    print("🎉 SUCCESS! 100% SOURCE ATTRIBUTION COMPLETE!")
else:
    print(f"⚠️  {100 - completeness:.1f}% sources need attribution")
print(f"{'=' * 80}\n")

