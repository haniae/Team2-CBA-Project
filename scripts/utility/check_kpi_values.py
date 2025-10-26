"""Check KPI values for N/A or incorrect values"""
import json

with open('test_single_company_payload.json', 'r') as f:
    payload = json.load(f)

kpis = payload.get('kpi_summary', [])

print("\n" + "="*80)
print("KPI VALUE CHECK FOR APPLE (AAPL)")
print("="*80 + "\n")

na_kpis = []
valid_kpis = []

for kpi in kpis:
    label = kpi.get('label', 'Unknown')
    value = kpi.get('value')
    formatted = kpi.get('formatted_value', 'N/A')
    period = kpi.get('period', 'N/A')
    
    if value is None or formatted == 'N/A':
        na_kpis.append((label, formatted, period))
    else:
        valid_kpis.append((label, formatted, period))

print(f"Total KPIs: {len(kpis)}")
print(f"Valid KPIs: {len(valid_kpis)}")
print(f"N/A KPIs: {len(na_kpis)}\n")

if na_kpis:
    print("❌ KPIs WITH N/A VALUES:")
    print("-" * 80)
    for label, value, period in na_kpis:
        print(f"  • {label:40} = {value:15} ({period})")
    print()

if valid_kpis:
    print("✅ VALID KPIs (first 10):")
    print("-" * 80)
    for label, value, period in valid_kpis[:10]:
        print(f"  • {label:40} = {value:15} ({period})")
    if len(valid_kpis) > 10:
        print(f"  ... and {len(valid_kpis) - 10} more")
    print()

print("="*80)

