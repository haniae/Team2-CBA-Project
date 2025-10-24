import json

with open('test_single_company_payload.json', 'r') as f:
    data = json.load(f)

sources = data.get('sources', [])

print(f"Total sources: {len(sources)}")
print("\nSources without URLs:")
for source in sources:
    if not source.get('url'):
        print(f"  - {source.get('label')} | Source: {source.get('source')} | Has calculation: {bool(source.get('calculation'))}")

