"""
Quick quality test for ML forecasting - tests key quality metrics.
Runs faster by testing fewer prompts but with comprehensive quality checks.
"""

import sys
import re
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings

# Key test prompts - representative sample
TEST_PROMPTS = [
    "Forecast Tesla's earnings using LSTM",
    "Predict Apple's revenue using Prophet",
    "What's Microsoft's revenue forecast using ARIMA?",
    "Forecast Amazon's revenue using ensemble methods",
]

def check_quality(response: str) -> dict:
    """Check response quality metrics."""
    quality = {
        "has_forecast_values": False,
        "forecast_count": 0,
        "has_model_name": False,
        "has_confidence_intervals": False,
        "has_years": False,
        "has_snapshot": False,
        "has_error": False,
        "length": len(response),
        "issues": [],
    }
    
    response_lower = response.lower()
    
    # Extract forecast values
    patterns = [r'\$(\d+\.?\d*)\s*[BM]', r'\$(\d+\.?\d*)\s*billion']
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        values.extend([float(m) for m in matches if m.replace('.', '').isdigit()])
    quality["forecast_count"] = len(values)
    quality["has_forecast_values"] = len(values) > 0
    
    # Check for model name
    models = ["lstm", "prophet", "arima", "ets", "gru", "transformer", "ensemble"]
    quality["has_model_name"] = any(m in response_lower for m in models)
    
    # Check for confidence intervals
    quality["has_confidence_intervals"] = bool(
        re.search(r'95%\s*confidence|confidence\s*interval|\[\$.*-\s*\$.*\]', response_lower)
    )
    
    # Check for years
    quality["has_years"] = bool(re.search(r'\b(202[4-9]|203[0-5])\b', response))
    
    # Check for snapshots (BAD)
    quality["has_snapshot"] = any([
        "phase1 kpis" in response_lower,
        "growth snapshot" in response_lower and "forecast" not in response_lower[:500],
        "margin snapshot" in response_lower and "forecast" not in response_lower[:500],
    ])
    
    # Check for errors (BAD)
    quality["has_error"] = any([
        "apologize" in response_lower and "forecast" not in response_lower[:200],
        "error" in response_lower and "forecast" not in response_lower[:200],
        "unable" in response_lower and "forecast" not in response_lower[:200],
    ])
    
    # Collect issues
    if not quality["has_forecast_values"]:
        quality["issues"].append("No forecast values")
    if not quality["has_model_name"]:
        quality["issues"].append("No model name")
    if not quality["has_confidence_intervals"]:
        quality["issues"].append("No confidence intervals")
    if not quality["has_years"]:
        quality["issues"].append("No forecast years")
    if quality["has_snapshot"]:
        quality["issues"].append("Contains snapshot (BAD)")
    if quality["has_error"]:
        quality["issues"].append("Contains error (BAD)")
    
    return quality

def main():
    """Run quick quality tests."""
    print("=" * 80)
    print("ML FORECASTING - QUICK QUALITY TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_PROMPTS)} key prompts...\n")
    
    results = []
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"[{i}/{len(TEST_PROMPTS)}] {prompt}")
        print("-" * 80)
        
        try:
            settings = load_settings()
            bot = BenchmarkOSChatbot.create(settings)
            response = bot.ask(prompt)
            
            if response:
                quality = check_quality(response)
                passed = (
                    quality["has_forecast_values"] and
                    quality["has_model_name"] and
                    not quality["has_snapshot"] and
                    not quality["has_error"] and
                    quality["length"] > 200
                )
                
                print(f"Status: {'[PASS]' if passed else '[FAIL]'}")
                print(f"  Length: {quality['length']} chars")
                print(f"  Forecast Values: {quality['forecast_count']} found")
                print(f"  Model Name: {'YES' if quality['has_model_name'] else 'NO'}")
                print(f"  Confidence Intervals: {'YES' if quality['has_confidence_intervals'] else 'NO'}")
                print(f"  Years: {'YES' if quality['has_years'] else 'NO'}")
                print(f"  Has Snapshot: {'YES (BAD)' if quality['has_snapshot'] else 'NO'}")
                print(f"  Has Error: {'YES (BAD)' if quality['has_error'] else 'NO'}")
                
                if quality["issues"]:
                    print(f"  Issues: {', '.join(quality['issues'])}")
                
                print(f"\n  Preview: {response[:250]}...\n")
                
                results.append({
                    "prompt": prompt,
                    "passed": passed,
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
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.get("passed"))
    print(f"\nPassed: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    
    if results:
        qualities = [r["quality"] for r in results if r.get("quality")]
        if qualities:
            print(f"\nQuality Metrics:")
            print(f"  Avg Forecast Values: {sum(q['forecast_count'] for q in qualities) / len(qualities):.1f}")
            print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model_name']) / len(qualities) * 100:.1f}%")
            print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_confidence_intervals']) / len(qualities) * 100:.1f}%")
            print(f"  Has Years: {sum(1 for q in qualities if q['has_years']) / len(qualities) * 100:.1f}%")
            print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
            print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    # Failed tests
    failed = [r for r in results if not r.get("passed")]
    if failed:
        print(f"\n[FAIL] Failed Tests:")
        for r in failed:
            print(f"  - {r['prompt']}")
            if r.get("error"):
                print(f"    Error: {r['error']}")
            elif r.get("quality"):
                print(f"    Issues: {', '.join(r['quality']['issues'])}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()

