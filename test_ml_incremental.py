"""
Incremental ML forecasting test - saves results as it goes.
Can be interrupted and resumed.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings

# All possible prompt variations
ALL_PROMPTS = [
    # Basic
    "Forecast Apple's revenue",
    "Predict Microsoft's revenue",
    "What's Tesla's revenue forecast?",
    "Show me Amazon's revenue forecast",
    "Forecast Google's earnings",
    
    # With models
    "Forecast Apple's revenue using Prophet",
    "Predict Microsoft's revenue using ARIMA",
    "Forecast Tesla's earnings using LSTM",
    "What's Amazon's revenue forecast using GRU?",
    "Forecast Google's revenue using Transformer",
    "Predict Apple's revenue using ETS",
    "Forecast Microsoft's revenue using ensemble",
    "What's Tesla's revenue forecast using the best ML model?",
    
    # With time
    "Forecast Apple's revenue for next 3 years",
    "Predict Microsoft's revenue for 2025-2027",
    "What's Tesla's revenue forecast for next 3 years using Prophet?",
    
    # Different metrics
    "Forecast Apple's net income using LSTM",
    "Predict Microsoft's free cash flow using Prophet",
    "What's Tesla's EBITDA forecast using ARIMA?",
    "Forecast Amazon's gross profit using ensemble",
    
    # Questions
    "Can you forecast Apple's revenue?",
    "How much will Microsoft's revenue be?",
    "What do you think Tesla's revenue will be?",
    "Can you predict Apple's revenue using LSTM?",
    
    # Imperative
    "Forecast Apple revenue now",
    "Run a forecast for Microsoft revenue",
    "Generate forecast for Tesla earnings",
    
    # Variations
    "What will Apple's revenue be?",
    "Project Microsoft's revenue",
    "Estimate Tesla's revenue",
    "What's the outlook for Amazon revenue?",
]

RESULTS_FILE = Path("ml_test_results_incremental.json")

def load_existing_results():
    """Load results from previous run."""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"results": [], "tested_prompts": set()}

def save_results(results_data):
    """Save results incrementally."""
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2)

def check_quality(response):
    """Quick quality check."""
    q = {
        "has_values": bool(re.search(r'\$\d+\.?\d*\s*[BM]', response)),
        "has_model": bool(re.search(r'\b(lstm|prophet|arima|ets|gru|transformer|ensemble)\b', response.lower())),
        "has_ci": bool(re.search(r'95%\s*confidence|confidence\s*interval', response.lower())),
        "has_years": bool(re.search(r'\b(202[4-9]|203[0-5])\b', response)),
        "has_snapshot": any([
            "phase1 kpis" in response.lower(),
            "growth snapshot" in response.lower() and "forecast" not in response.lower()[:500],
        ]),
        "has_error": any([
            "apologize" in response.lower() and "forecast" not in response.lower()[:200],
            "error" in response.lower() and "forecast" not in response.lower()[:200],
        ]),
    }
    q["passed"] = q["has_values"] and q["has_model"] and not q["has_snapshot"] and not q["has_error"]
    return q

def main():
    """Run incremental tests."""
    print("=" * 80)
    print("ML FORECASTING - INCREMENTAL TEST")
    print("=" * 80)
    
    # Load existing results
    existing = load_existing_results()
    tested = existing.get("tested_prompts", set())
    results = existing.get("results", [])
    
    print(f"\nAlready tested: {len(tested)} prompts")
    print(f"Remaining: {len(ALL_PROMPTS) - len(tested)} prompts\n")
    
    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)
    
    for i, prompt in enumerate(ALL_PROMPTS, 1):
        if prompt in tested:
            print(f"[{i}/{len(ALL_PROMPTS)}] {prompt} - SKIPPED (already tested)")
            continue
        
        print(f"[{i}/{len(ALL_PROMPTS)}] {prompt}")
        
        try:
            response = bot.ask(prompt)
            
            if response:
                quality = check_quality(response)
                status = "[PASS]" if quality["passed"] else "[FAIL]"
                print(f"  {status} | Values: {quality['has_values']} | Model: {quality['has_model']} | Snapshot: {quality['has_snapshot']} | Error: {quality['has_error']}")
                
                results.append({
                    "prompt": prompt,
                    "passed": quality["passed"],
                    "quality": quality,
                    "timestamp": datetime.now().isoformat(),
                })
                tested.add(prompt)
                
                # Save after each test
                save_results({
                    "results": results,
                    "tested_prompts": list(tested),
                    "last_updated": datetime.now().isoformat(),
                })
            else:
                print(f"  [FAIL] No response")
                results.append({"prompt": prompt, "passed": False, "error": "No response"})
                tested.add(prompt)
                save_results({
                    "results": results,
                    "tested_prompts": list(tested),
                    "last_updated": datetime.now().isoformat(),
                })
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            results.append({"prompt": prompt, "passed": False, "error": str(e)})
            tested.add(prompt)
            save_results({
                "results": results,
                "tested_prompts": list(tested),
                "last_updated": datetime.now().isoformat(),
            })
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.get("passed"))
    print(f"\nTotal Tested: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {len(results) - passed}")
    
    if results:
        qualities = [r["quality"] for r in results if r.get("quality")]
        if qualities:
            print(f"\nQuality Metrics:")
            print(f"  Has Forecast Values: {sum(1 for q in qualities if q['has_values']) / len(qualities) * 100:.1f}%")
            print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model']) / len(qualities) * 100:.1f}%")
            print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_ci']) / len(qualities) * 100:.1f}%")
            print(f"  Has Years: {sum(1 for q in qualities if q['has_years']) / len(qualities) * 100:.1f}%")
            print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
            print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    print(f"\nResults saved to: {RESULTS_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()

