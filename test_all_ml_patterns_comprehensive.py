"""
Comprehensive test of ALL ML forecasting prompt patterns.
Tests every possible variation to identify which patterns are failing.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings

# ALL POSSIBLE PROMPT PATTERNS - Comprehensive coverage
PROMPT_PATTERNS = {
    "basic_forecast": [
        "Forecast Apple's revenue",
        "Forecast Microsoft's revenue",
        "Forecast Tesla's earnings",
        "Forecast Amazon's revenue",
        "Forecast Google's revenue",
    ],
    "basic_predict": [
        "Predict Apple's revenue",
        "Predict Microsoft's revenue",
        "Predict Tesla's earnings",
        "Predict Amazon's revenue",
    ],
    "basic_whats": [
        "What's Apple's revenue forecast?",
        "What's Microsoft's revenue forecast?",
        "What's Tesla's revenue forecast?",
        "What's Amazon's revenue forecast?",
    ],
    "basic_show": [
        "Show me Apple's revenue forecast",
        "Show me Microsoft's revenue forecast",
        "Show me Tesla's revenue forecast",
    ],
    "with_model_prophet": [
        "Forecast Apple's revenue using Prophet",
        "Predict Microsoft's revenue using Prophet",
        "What's Tesla's revenue forecast using Prophet?",
    ],
    "with_model_arima": [
        "Forecast Apple's revenue using ARIMA",
        "Predict Microsoft's revenue using ARIMA",
        "What's Tesla's revenue forecast using ARIMA?",
    ],
    "with_model_lstm": [
        "Forecast Apple's revenue using LSTM",
        "Forecast Tesla's earnings using LSTM",
        "Predict Microsoft's revenue using LSTM",
        "What's Amazon's revenue forecast using LSTM?",
    ],
    "with_model_gru": [
        "Forecast Apple's revenue using GRU",
        "Forecast Tesla's earnings using GRU",
        "Predict Microsoft's revenue using GRU",
    ],
    "with_model_transformer": [
        "Forecast Apple's revenue using Transformer",
        "Forecast Tesla's earnings using Transformer",
        "Predict Microsoft's revenue using Transformer",
    ],
    "with_model_ets": [
        "Forecast Apple's revenue using ETS",
        "Forecast Tesla's earnings using ETS",
        "Predict Microsoft's revenue using ETS",
    ],
    "with_model_ensemble": [
        "Forecast Apple's revenue using ensemble",
        "Forecast Tesla's earnings using ensemble methods",
        "Predict Microsoft's revenue using ensemble",
        "What's Amazon's revenue forecast using ensemble methods?",
    ],
    "with_model_best": [
        "Forecast Apple's revenue using the best ML model",
        "Forecast Tesla's earnings using the best model",
        "What's Microsoft's revenue forecast using the best ML model?",
    ],
    "with_time_years": [
        "Forecast Apple's revenue for next 3 years",
        "Predict Microsoft's revenue for next 3 years",
        "What's Tesla's revenue forecast for next 3 years?",
    ],
    "with_time_period": [
        "Forecast Apple's revenue for 2025-2027",
        "Predict Microsoft's revenue for 2025-2027",
        "What's Tesla's revenue forecast for 2025-2027?",
    ],
    "different_metrics": [
        "Forecast Apple's net income",
        "Forecast Microsoft's free cash flow",
        "Forecast Tesla's EBITDA",
        "Forecast Amazon's gross profit",
        "Forecast Google's operating income",
        "Forecast Apple's EPS",
    ],
    "different_metrics_with_model": [
        "Forecast Apple's net income using LSTM",
        "Forecast Microsoft's free cash flow using Prophet",
        "Forecast Tesla's EBITDA using ARIMA",
        "Forecast Amazon's gross profit using ensemble",
    ],
    "question_formats": [
        "Can you forecast Apple's revenue?",
        "How much will Microsoft's revenue be?",
        "What do you think Tesla's revenue will be?",
        "Can you predict Apple's revenue using LSTM?",
        "What will Apple's revenue be?",
    ],
    "imperative": [
        "Forecast Apple revenue now",
        "Run a forecast for Microsoft revenue",
        "Generate forecast for Tesla earnings",
        "Forecast Apple revenue using LSTM now",
    ],
    "variations_project": [
        "Project Apple's revenue",
        "Project Microsoft's revenue",
        "Project Tesla's revenue",
    ],
    "variations_estimate": [
        "Estimate Apple's revenue",
        "Estimate Microsoft's revenue",
        "Estimate Tesla's revenue",
    ],
    "variations_outlook": [
        "What's the outlook for Apple revenue?",
        "What's the outlook for Microsoft revenue?",
        "What's the outlook for Amazon revenue?",
    ],
    "variations_forecast_for": [
        "Forecast revenue for Apple",
        "Forecast revenue for Microsoft",
        "Forecast earnings for Tesla",
    ],
    "variations_predict_for": [
        "Predict revenue for Apple",
        "Predict revenue for Microsoft",
        "Predict earnings for Tesla",
    ],
    "complex_combinations": [
        "Forecast Apple's revenue for next 3 years using LSTM",
        "Predict Microsoft's revenue for 2025-2027 using Prophet",
        "What's Tesla's revenue forecast for next 3 years using ensemble?",
        "Forecast Apple's net income using the best ML model",
        "Predict Microsoft's free cash flow for next 3 years",
    ],
    "edge_cases": [
        "forecast apple revenue",  # lowercase
        "FORECAST APPLE REVENUE",  # uppercase
        "Forecast Apple Revenue",  # no apostrophe
        "Forecast Apple's Revenue",  # capital R
        "Forecast Apple revenue using lstm",  # lowercase model
        "Forecast Apple revenue using LSTM model",  # with "model"
    ],
}

RESULTS_FILE = Path("ml_patterns_test_results.json")

def extract_forecast_values(text: str) -> List[float]:
    """Extract forecast values from text."""
    # Match $X.XB, $X.XM, $X.XK patterns
    matches = re.findall(r'\$(\d+\.?\d*)\s*([BMK])', text, re.IGNORECASE)
    values = []
    for num, unit in matches:
        try:
            val = float(num)
            if unit.upper() == 'B':
                val *= 1e9
            elif unit.upper() == 'M':
                val *= 1e6
            elif unit.upper() == 'K':
                val *= 1e3
            values.append(val)
        except:
            pass
    return values

def check_response_quality(response: str, prompt: str) -> Dict:
    """Comprehensive quality check."""
    # Import re at function level to avoid closure issues
    import re
    
    if not response:
        return {
            "passed": False,
            "has_response": False,
            "has_values": False,
            "has_model": False,
            "has_ci": False,
            "has_years": False,
            "has_snapshot": False,
            "has_error": False,
            "length": 0,
            "issues": ["No response generated"],
        }
    
    response_lower = response.lower()
    
    # Check for forecast values
    values = extract_forecast_values(response)
    has_values = len(values) > 0
    
    # Check for model name
    models = ['prophet', 'arima', 'ets', 'lstm', 'gru', 'transformer', 'ensemble']
    has_model = any(model in response_lower for model in models)
    
    # Check for confidence intervals
    has_ci = bool(re.search(r'95%\s*confidence|confidence\s*interval|\[\$.*-\s*\$.*\]', response_lower))
    
    # Check for forecast years
    has_years = bool(re.search(r'\b(202[4-9]|203[0-5])\b', response))
    
    # Check for snapshots (BAD)
    has_snapshot = any([
        "growth snapshot" in response_lower,
        "margin snapshot" in response_lower,
        "phase1 kpis" in response_lower,
        "phase 1 kpis" in response_lower,
    ])
    
    # Check for errors (BAD)
    has_error = any([
        "apologize" in response_lower and "forecast" not in response_lower[:200],
        "error" in response_lower and "forecast" not in response_lower[:200],
        "encountered an issue" in response_lower,
        "unable to" in response_lower and "forecast" not in response_lower[:200],
    ])
    
    # Determine if passed
    passed = has_values and has_model and not has_snapshot and not has_error
    
    # Collect issues
    issues = []
    if not has_values:
        issues.append("No forecast values found")
    if not has_model:
        issues.append("No model name mentioned")
    if has_snapshot:
        issues.append("Contains snapshot (forbidden)")
    if has_error:
        issues.append("Contains error message")
    if not has_ci:
        issues.append("No confidence intervals")
    if not has_years:
        issues.append("No forecast years mentioned")
    
    return {
        "passed": passed,
        "has_response": True,
        "has_values": has_values,
        "value_count": len(values),
        "has_model": has_model,
        "has_ci": has_ci,
        "has_years": has_years,
        "has_snapshot": has_snapshot,
        "has_error": has_error,
        "length": len(response),
        "issues": issues,
    }

def test_prompt(bot: BenchmarkOSChatbot, prompt: str) -> Tuple[bool, Dict, str]:
    """Test a single prompt."""
    try:
        response = bot.ask(prompt)
        quality = check_response_quality(response or "", prompt)
        return quality["passed"], quality, response or ""
    except Exception as e:
        return False, {"error": str(e), "passed": False}, ""

def main():
    """Run comprehensive pattern testing."""
    print("=" * 100)
    print("COMPREHENSIVE ML FORECASTING PATTERN TEST")
    print("=" * 100)
    print(f"\nTesting {sum(len(prompts) for prompts in PROMPT_PATTERNS.values())} prompts across {len(PROMPT_PATTERNS)} pattern categories...\n")
    
    # Load existing results
    existing_results = {}
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_results = {r["prompt"]: r for r in existing_data.get("results", [])}
    
    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)
    
    all_results = []
    category_results = {}
    
    total_tested = 0
    total_passed = 0
    
    for category, prompts in PROMPT_PATTERNS.items():
        print(f"\n{'='*100}")
        print(f"Testing Category: {category.upper().replace('_', ' ')} ({len(prompts)} prompts)")
        print(f"{'='*100}\n")
        
        category_passed = 0
        category_failed = []
        
        for i, prompt in enumerate(prompts, 1):
            # Skip if already tested
            if prompt in existing_results:
                result = existing_results[prompt]
                passed = result.get("passed", False)
                quality = result.get("quality", {})
                response = result.get("response", "")
                print(f"[{i}/{len(prompts)}] {prompt} - {'[PASS]' if passed else '[FAIL]'} (cached)")
            else:
                print(f"[{i}/{len(prompts)}] {prompt}")
                passed, quality, response = test_prompt(bot, prompt)
                
                result = {
                    "prompt": prompt,
                    "category": category,
                    "passed": passed,
                    "quality": quality,
                    "response": response[:500] if response else "",  # Store preview
                    "timestamp": datetime.now().isoformat(),
                }
                all_results.append(result)
                existing_results[prompt] = result
                
                # Save incrementally
                with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"results": list(existing_results.values()), "last_updated": datetime.now().isoformat()}, f, indent=2)
            
            if passed:
                category_passed += 1
                total_passed += 1
                print(f"  [PASS] | Values: {quality.get('has_values')} | Model: {quality.get('has_model')} | Snapshot: {quality.get('has_snapshot')} | Error: {quality.get('has_error')}")
            else:
                category_failed.append((prompt, quality))
                issues = quality.get("issues", [])
                print(f"  [FAIL] | Issues: {', '.join(issues) if issues else 'Unknown'}")
            
            total_tested += 1
        
        category_results[category] = {
            "total": len(prompts),
            "passed": category_passed,
            "failed": len(prompts) - category_passed,
            "success_rate": (category_passed / len(prompts) * 100) if prompts else 0,
            "failed_prompts": category_failed,
        }
        
        print(f"\nCategory Summary: {category_passed}/{len(prompts)} passed ({category_passed/len(prompts)*100:.1f}%)")
    
    # Final Summary
    print("\n" + "=" * 100)
    print("FINAL SUMMARY")
    print("=" * 100)
    
    print(f"\nTotal Tested: {total_tested}")
    print(f"Total Passed: {total_passed} ({total_passed/total_tested*100:.1f}%)")
    print(f"Total Failed: {total_tested - total_passed} ({(total_tested-total_passed)/total_tested*100:.1f}%)")
    
    # Category breakdown
    print(f"\n{'='*100}")
    print("CATEGORY BREAKDOWN")
    print(f"{'='*100}\n")
    
    for category, stats in sorted(category_results.items(), key=lambda x: x[1]["success_rate"]):
        print(f"{category.replace('_', ' ').title()}:")
        print(f"  Passed: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        if stats['failed'] > 0:
            print(f"  Failed Prompts:")
            for prompt, quality in stats['failed_prompts']:
                issues = quality.get("issues", [])
                print(f"    - {prompt}")
                print(f"      Issues: {', '.join(issues) if issues else 'Unknown'}")
        print()
    
    # Failed patterns analysis
    all_failed = [(p, q) for cat, stats in category_results.items() for p, q in stats['failed_prompts']]
    if all_failed:
        print(f"\n{'='*100}")
        print("FAILED PATTERNS ANALYSIS")
        print(f"{'='*100}\n")
        
        # Group by issue type
        issue_groups = {}
        for prompt, quality in all_failed:
            issues = quality.get("issues", [])
            for issue in issues:
                if issue not in issue_groups:
                    issue_groups[issue] = []
                issue_groups[issue].append(prompt)
        
        for issue, prompts in sorted(issue_groups.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"{issue}: {len(prompts)} prompts")
            for prompt in prompts[:5]:  # Show first 5
                print(f"  - {prompt}")
            if len(prompts) > 5:
                print(f"  ... and {len(prompts) - 5} more")
            print()
    
    # Overall status
    success_rate = total_passed / total_tested * 100
    print(f"\n{'='*100}")
    if success_rate >= 90:
        print("[SUCCESS] 90%+ of prompts working correctly!")
    elif success_rate >= 75:
        print("[WARNING] 75-90% working - some improvements needed")
    else:
        print("[FAIL] Less than 75% working - significant issues")
    print(f"{'='*100}\n")
    
    print(f"Results saved to: {RESULTS_FILE}")
    
    return all_results

if __name__ == "__main__":
    main()

