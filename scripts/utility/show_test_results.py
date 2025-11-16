"""Display ML forecast test results."""
import json
from pathlib import Path

results_file = Path("ml_test_results_incremental.json")
if results_file.exists():
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("ML FORECAST TEST RESULTS")
    print("=" * 80)
    print(f"\nTotal Tested: {len(data['tested_prompts'])}")
    print(f"Last Updated: {data.get('last_updated', 'N/A')}\n")
    
    passed = sum(1 for r in data['results'] if r.get('passed'))
    failed = len(data['results']) - passed
    
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/len(data['results'])*100:.1f}%\n" if data['results'] else "\n")
    
    print("Results:")
    for i, r in enumerate(data['results'], 1):
        status = "PASS" if r.get('passed') else "FAIL"
        print(f"\n{i}. {r['prompt']}")
        print(f"   Status: {status}")
        if r.get('quality'):
            q = r['quality']
            print(f"   Has Forecast Values: {q.get('has_values')}")
            print(f"   Has Model Name: {q.get('has_model')}")
            print(f"   Has Confidence Intervals: {q.get('has_ci')}")
            print(f"   Has Years: {q.get('has_years')}")
            print(f"   Has Snapshot (BAD): {q.get('has_snapshot')}")
            print(f"   Has Error (BAD): {q.get('has_error')}")
        if r.get('error'):
            print(f"   Error: {r['error']}")
else:
    print("No test results found. Run test_ml_incremental.py first.")

