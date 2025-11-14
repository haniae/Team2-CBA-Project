"""Check progress of ML pattern testing."""
import json
from pathlib import Path

results_file = Path("ml_patterns_test_results.json")

if results_file.exists():
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get("results", [])
    last_updated = data.get("last_updated", "N/A")
    
    print("=" * 80)
    print("ML PATTERN TEST PROGRESS")
    print("=" * 80)
    print(f"\nTotal Tested: {len(results)}")
    print(f"Last Updated: {last_updated}\n")
    
    if results:
        passed = sum(1 for r in results if r.get("passed"))
        failed = len(results) - passed
        
        print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
        print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
        
        # Group by category
        categories = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "failed": 0}
            categories[cat]["total"] += 1
            if r.get("passed"):
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        print(f"\nCategory Breakdown:")
        for cat, stats in sorted(categories.items()):
            rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  {cat.replace('_', ' ').title()}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        # Show recent failures
        recent_failures = [r for r in results[-10:] if not r.get("passed")]
        if recent_failures:
            print(f"\nRecent Failures (last 10):")
            for r in recent_failures:
                issues = r.get("quality", {}).get("issues", [])
                print(f"  - {r.get('prompt', 'N/A')}")
                if issues:
                    print(f"    Issues: {', '.join(issues[:3])}")
    else:
        print("No results yet - test is still running...")
else:
    print("Test results file not found. Test may still be starting...")

print("\n" + "=" * 80)

