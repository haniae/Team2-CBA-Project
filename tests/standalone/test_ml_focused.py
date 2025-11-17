"""
Focused test on key ML forecasting prompts.
Tests critical variations and shows detailed results.
"""

import sys
import re
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import load_settings

# Critical test prompts - representative of all variations
TEST_PROMPTS = [
    "Forecast Tesla's earnings using LSTM",
    "Predict Apple's revenue using Prophet",
    "What's Microsoft's revenue forecast using ARIMA?",
    "Forecast Amazon's revenue using ensemble methods",
    "Forecast Apple's net income",
    "Predict Tesla's revenue",
    "What's Microsoft's revenue forecast?",
    "Forecast Google's earnings using GRU",
]

def extract_values(text):
    """Extract forecast values."""
    matches = re.findall(r'\$(\d+\.?\d*)\s*[BM]', text, re.IGNORECASE)
    return [float(m) for m in matches if m.replace('.', '').isdigit()]

def check_quality(response, prompt):
    """Check response quality."""
    q = {
        "has_values": len(extract_values(response)) > 0,
        "value_count": len(extract_values(response)),
        "has_model": bool(re.search(r'\b(lstm|prophet|arima|ets|gru|transformer|ensemble)\b', response.lower())),
        "has_ci": bool(re.search(r'95%\s*confidence|confidence\s*interval|\[\$.*-\s*\$.*\]', response.lower())),
        "has_years": bool(re.search(r'\b(202[4-9]|203[0-5])\b', response)),
        "has_snapshot": any([
            "phase1 kpis" in response.lower(),
            "growth snapshot" in response.lower() and "forecast" not in response.lower()[:500],
        ]),
        "has_error": any([
            "apologize" in response.lower() and "forecast" not in response.lower()[:200],
            "error" in response.lower() and "forecast" not in response.lower()[:200],
        ]),
        "length": len(response),
    }
    q["passed"] = q["has_values"] and q["has_model"] and not q["has_snapshot"] and not q["has_error"]
    return q

def main():
    """Run focused tests."""
    print("=" * 80)
    print("ML FORECASTING - FOCUSED TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_PROMPTS)} critical prompts...\n")
    
    settings = load_settings()
    bot = FinanlyzeOSChatbot.create(settings)
    
    results = []
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"[{i}/{len(TEST_PROMPTS)}] {prompt}")
        print("-" * 80)
        
        try:
            response = bot.ask(prompt)
            
            if response:
                quality = check_quality(response, prompt)
                status = "[PASS]" if quality["passed"] else "[FAIL]"
                
                print(f"Status: {status}")
                print(f"  Length: {quality['length']} chars")
                print(f"  Forecast Values: {quality['value_count']} found")
                print(f"  Has Model Name: {'YES' if quality['has_model'] else 'NO'}")
                print(f"  Has Confidence Intervals: {'YES' if quality['has_ci'] else 'NO'}")
                print(f"  Has Years: {'YES' if quality['has_years'] else 'NO'}")
                print(f"  Has Snapshot (BAD): {'YES' if quality['has_snapshot'] else 'NO'}")
                print(f"  Has Error (BAD): {'YES' if quality['has_error'] else 'NO'}")
                
                # Show preview
                preview = response[:400] + "..." if len(response) > 400 else response
                print(f"\n  Response Preview:\n  {preview}\n")
                
                results.append({
                    "prompt": prompt,
                    "passed": quality["passed"],
                    "quality": quality,
                    "response": response,
                })
            else:
                print("[FAIL] No response generated\n")
                results.append({"prompt": prompt, "passed": False, "error": "No response"})
                
        except Exception as e:
            print(f"[FAIL] Error: {e}\n")
            results.append({"prompt": prompt, "passed": False, "error": str(e)})
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"[PASS] Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"[FAIL] Failed: {failed} ({failed/len(results)*100:.1f}%)")
    
    if results:
        qualities = [r["quality"] for r in results if r.get("quality")]
        if qualities:
            print(f"\nQuality Metrics:")
            print(f"  Average Forecast Values: {sum(q['value_count'] for q in qualities) / len(qualities):.1f} per response")
            print(f"  Has Forecast Values: {sum(1 for q in qualities if q['has_values']) / len(qualities) * 100:.1f}%")
            print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model']) / len(qualities) * 100:.1f}%")
            print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_ci']) / len(qualities) * 100:.1f}%")
            print(f"  Has Years: {sum(1 for q in qualities if q['has_years']) / len(qualities) * 100:.1f}%")
            print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
            print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    # Failed tests
    failed_results = [r for r in results if not r.get("passed")]
    if failed_results:
        print(f"\n[FAIL] Failed Tests ({len(failed_results)}):")
        for i, r in enumerate(failed_results, 1):
            print(f"\n{i}. {r['prompt']}")
            if r.get("error"):
                print(f"   Error: {r['error']}")
            elif r.get("quality"):
                q = r["quality"]
                issues = []
                if not q["has_values"]:
                    issues.append("No forecast values")
                if not q["has_model"]:
                    issues.append("No model name")
                if q["has_snapshot"]:
                    issues.append("Contains snapshot")
                if q["has_error"]:
                    issues.append("Contains error")
                print(f"   Issues: {', '.join(issues) if issues else 'Unknown'}")
                if r.get("response"):
                    print(f"   Response: {r['response'][:200]}...")
    
    print("\n" + "=" * 80)
    
    # Overall status
    success_rate = passed / len(results) * 100
    if success_rate >= 90:
        print("[SUCCESS] 90%+ of prompts working correctly!")
    elif success_rate >= 75:
        print("[WARNING] 75-90% working - some improvements needed")
    else:
        print("[FAIL] Less than 75% working - significant issues")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    main()

