"""Show detailed test results."""
import json
from pathlib import Path

results_file = Path("ml_patterns_test_results.json")

if results_file.exists():
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get("results", [])
    
    print("=" * 80)
    print("DETAILED TEST RESULTS")
    print("=" * 80)
    print(f"\nTotal Tested: {len(results)}")
    
    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed
    
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)\n")
    
    print("Recent Results:")
    for i, r in enumerate(results[-10:], 1):
        status = "PASS" if r.get("passed") else "FAIL"
        quality = r.get("quality", {})
        print(f"\n{i}. {r.get('prompt', 'N/A')}")
        print(f"   Status: {status}")
        if quality:
            print(f"   Values: {quality.get('value_count', 0)}")
            print(f"   Has Model: {quality.get('has_model', False)}")
            print(f"   Has CI: {quality.get('has_ci', False)}")
            print(f"   Has Years: {quality.get('has_years', False)}")
            print(f"   Has Snapshot: {quality.get('has_snapshot', False)} (BAD)")
            print(f"   Has Error: {quality.get('has_error', False)} (BAD)")
            issues = quality.get("issues", [])
            if issues:
                print(f"   Issues: {', '.join(issues)}")
        if r.get("response"):
            preview = r["response"][:200].replace('\n', ' ')
            # Remove Unicode characters that can't be encoded
            preview = preview.encode('ascii', 'ignore').decode('ascii')
            print(f"   Preview: {preview}...")
else:
    print("No results file found yet.")

