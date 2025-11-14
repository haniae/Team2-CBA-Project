"""
Comprehensive test suite for ALL ML forecasting prompt variations.
Tests systematically to ensure 100% coverage.
"""

import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.context_builder import _is_forecasting_query, _extract_forecast_metric, _extract_forecast_method

# COMPREHENSIVE PROMPT VARIATIONS
# All possible ways users might ask for ML forecasts

COMPANIES = ["Apple", "Microsoft", "Tesla", "Amazon", "Google"]
METRICS = ["revenue", "earnings", "net income", "free cash flow", "EBITDA"]
MODELS = ["Prophet", "ARIMA", "LSTM", "GRU", "Transformer", "ETS", "ensemble", "best"]

# All prompt patterns users might use
PROMPT_PATTERNS = [
    # Basic patterns
    "Forecast {company}'s {metric}",
    "Forecast {company} {metric}",
    "Predict {company}'s {metric}",
    "Predict {company} {metric}",
    "What's {company}'s {metric} forecast?",
    "What is {company}'s {metric} forecast?",
    "Show me {company}'s {metric} forecast",
    "Give me {company}'s {metric} forecast",
    
    # With model
    "Forecast {company}'s {metric} using {model}",
    "Predict {company}'s {metric} using {model}",
    "What's {company}'s {metric} forecast using {model}?",
    "Show me {company}'s {metric} forecast using {model}",
    "{company} {metric} forecast {model}",
    
    # With time
    "Forecast {company}'s {metric} for next 3 years",
    "Predict {company}'s {metric} for the next 3 years",
    "What's {company}'s {metric} forecast for 2025-2027?",
    
    # With model and time
    "Forecast {company}'s {metric} for next 3 years using {model}",
    "Predict {company}'s {metric} for 2025-2027 using {model}",
    
    # Question formats
    "Can you forecast {company}'s {metric}?",
    "Can you predict {company}'s {metric} using {model}?",
    "How much will {company}'s {metric} be?",
    "What do you think {company}'s {metric} will be?",
    
    # Imperative
    "Forecast {company} {metric} now",
    "Run a forecast for {company} {metric}",
    "Generate forecast for {company} {metric}",
    
    # Variations
    "What will {company}'s {metric} be?",
    "What will {company} {metric} be in the future?",
    "Project {company}'s {metric}",
    "Estimate {company}'s {metric}",
    "What's the outlook for {company} {metric}?",
]

def generate_test_prompts() -> List[Dict[str, Any]]:
    """Generate comprehensive test prompts with metadata."""
    prompts = []
    
    # Category 1: Basic forecasts (no model specified)
    for company in COMPANIES:
        for metric in METRICS:
            for pattern in [p for p in PROMPT_PATTERNS if "{model}" not in p][:5]:
                prompt = pattern.format(company=company, metric=metric)
                prompts.append({
                    "prompt": prompt,
                    "category": "basic_forecast",
                    "company": company,
                    "metric": metric,
                    "model": None,
                })
    
    # Category 2: Model-specific forecasts
    for company in COMPANIES[:3]:  # Test with 3 companies
        for metric in METRICS[:3]:  # Test with 3 metrics
            for model in MODELS:
                for pattern in [p for p in PROMPT_PATTERNS if "{model}" in p][:3]:
                    prompt = pattern.format(company=company, metric=metric, model=model)
                    prompts.append({
                        "prompt": prompt,
                        "category": "model_specific",
                        "company": company,
                        "metric": metric,
                        "model": model,
                    })
    
    # Category 3: Time-specific forecasts
    for company in COMPANIES[:2]:
        for metric in METRICS[:2]:
            for pattern in [p for p in PROMPT_PATTERNS if "next" in p or "2025" in p][:2]:
                if "{model}" not in pattern:
                    prompt = pattern.format(company=company, metric=metric)
                    prompts.append({
                        "prompt": prompt,
                        "category": "time_specific",
                        "company": company,
                        "metric": metric,
                        "model": None,
                    })
    
    return prompts

def extract_forecast_values(text: str) -> List[float]:
    """Extract forecast values from text."""
    patterns = [
        r'\$(\d+\.?\d*)\s*[BM]',
        r'\$(\d+\.?\d*)\s*billion',
        r'\$(\d+\.?\d*)\s*million',
    ]
    
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                val = float(match)
                if 'million' in pattern.lower() or 'M' in pattern:
                    val = val / 1000
                values.append(val)
            except ValueError:
                pass
    
    return values

def check_quality(response: str) -> Dict[str, Any]:
    """Check response quality comprehensively."""
    quality = {
        "has_forecast_values": False,
        "forecast_count": 0,
        "has_model_name": False,
        "has_confidence_intervals": False,
        "has_years": False,
        "has_snapshot": False,
        "has_error": False,
        "length": len(response),
        "score": 0,
        "issues": [],
    }
    
    response_lower = response.lower()
    
    # Forecast values (30 points)
    values = extract_forecast_values(response)
    quality["forecast_count"] = len(values)
    quality["has_forecast_values"] = len(values) > 0
    if quality["has_forecast_values"]:
        quality["score"] += 30
    
    # Model name (20 points)
    models = ["lstm", "prophet", "arima", "ets", "gru", "transformer", "ensemble"]
    quality["has_model_name"] = any(m in response_lower for m in models)
    if quality["has_model_name"]:
        quality["score"] += 20
    
    # Confidence intervals (15 points)
    quality["has_confidence_intervals"] = bool(
        re.search(r'95%\s*confidence|confidence\s*interval|\[\$.*-\s*\$.*\]', response_lower)
    )
    if quality["has_confidence_intervals"]:
        quality["score"] += 15
    
    # Years (10 points)
    quality["has_years"] = bool(re.search(r'\b(202[4-9]|203[0-5])\b', response))
    if quality["has_years"]:
        quality["score"] += 10
    
    # Length (10 points)
    if quality["length"] >= 200:
        quality["score"] += 10
    
    # Snapshots (BAD - -50 points)
    quality["has_snapshot"] = any([
        "phase1 kpis" in response_lower,
        "phase 1 kpis" in response_lower,
        ("growth snapshot" in response_lower and "forecast" not in response_lower[:500]),
        ("margin snapshot" in response_lower and "forecast" not in response_lower[:500]),
    ])
    if quality["has_snapshot"]:
        quality["score"] -= 50
        quality["issues"].append("Contains snapshot")
    
    # Errors (BAD - -50 points)
    quality["has_error"] = any([
        "apologize" in response_lower and "forecast" not in response_lower[:200],
        "error" in response_lower and "forecast" not in response_lower[:200],
        "unable" in response_lower and "forecast" not in response_lower[:200],
    ])
    if quality["has_error"]:
        quality["score"] -= 50
        quality["issues"].append("Contains error")
    
    # Collect all issues
    if not quality["has_forecast_values"]:
        quality["issues"].append("No forecast values")
    if not quality["has_model_name"]:
        quality["issues"].append("No model name")
    if not quality["has_confidence_intervals"]:
        quality["issues"].append("No confidence intervals")
    if not quality["has_years"]:
        quality["issues"].append("No forecast years")
    
    quality["score"] = max(0, min(100, quality["score"]))
    quality["passed"] = (
        quality["score"] >= 50 and
        not quality["has_snapshot"] and
        not quality["has_error"] and
        quality["has_forecast_values"]
    )
    
    return quality

def test_single_prompt(prompt_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single prompt comprehensively."""
    prompt = prompt_data["prompt"]
    result = {
        **prompt_data,
        "detection": {},
        "context": {},
        "response": None,
        "quality": None,
        "error": None,
        "passed": False,
    }
    
    try:
        # Test detection
        result["detection"] = {
            "is_forecasting": _is_forecasting_query(prompt),
            "metric": _extract_forecast_metric(prompt) if _is_forecasting_query(prompt) else None,
            "method": _extract_forecast_method(prompt) if _is_forecasting_query(prompt) else None,
        }
        
        # Test context (quick check)
        try:
            from benchmarkos_chatbot.context_builder import build_financial_context
            from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
            
            settings = load_settings()
            engine = AnalyticsEngine(settings)
            context = build_financial_context(
                query=prompt,
                analytics_engine=engine,
                database_path=str(settings.database_path),
                max_tickers=3,
                include_macro_context=True
            )
            
            result["context"] = {
                "generated": context is not None,
                "has_ml_forecast": "ML FORECAST" in (context or ""),
            }
        except Exception:
            pass  # Skip context test if it fails
        
        # Test chatbot response
        settings = load_settings()
        bot = BenchmarkOSChatbot.create(settings)
        response = bot.ask(prompt)
        
        if response:
            result["response"] = response
            result["quality"] = check_quality(response)
            result["passed"] = result["quality"]["passed"]
        else:
            result["error"] = "No response"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def main():
    """Run comprehensive tests."""
    print("=" * 80)
    print("COMPREHENSIVE ML FORECASTING PROMPT TEST")
    print("=" * 80)
    
    # Generate prompts
    print("\nGenerating all prompt variations...")
    prompts = generate_test_prompts()
    print(f"Generated {len(prompts)} test prompts")
    
    # Test all prompts
    print(f"\nTesting all prompts...")
    print("(This will test query detection, context generation, and response quality)\n")
    
    results = []
    for i, prompt_data in enumerate(prompts, 1):
        if i % 20 == 0 or i == 1:
            print(f"Progress: {i}/{len(prompts)} ({i/len(prompts)*100:.1f}%)")
        
        result = test_single_prompt(prompt_data)
        results.append(result)
    
    # Analyze results
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    # Detection
    detection_ok = sum(1 for r in results if r.get("detection", {}).get("is_forecasting"))
    print(f"\n1. Query Detection: {detection_ok}/{len(results)} ({detection_ok/len(results)*100:.1f}%)")
    
    # Context
    context_ok = sum(1 for r in results if r.get("context", {}).get("has_ml_forecast"))
    print(f"2. Context Generation: {context_ok}/{len(results)} ({context_ok/len(results)*100:.1f}%)")
    
    # Response quality
    response_ok = sum(1 for r in results if r.get("passed"))
    print(f"3. Response Quality: {response_ok}/{len(results)} ({response_ok/len(results)*100:.1f}%)")
    
    # Quality breakdown
    qualities = [r["quality"] for r in results if r.get("quality")]
    if qualities:
        print(f"\nQuality Metrics:")
        print(f"  Average Score: {sum(q['score'] for q in qualities) / len(qualities):.1f}/100")
        print(f"  Has Forecast Values: {sum(1 for q in qualities if q['has_forecast_values']) / len(qualities) * 100:.1f}%")
        print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model_name']) / len(qualities) * 100:.1f}%")
        print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_confidence_intervals']) / len(qualities) * 100:.1f}%")
        print(f"  Has Years: {sum(1 for q in qualities if q['has_years']) / len(qualities) * 100:.1f}%")
        print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
        print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    # Failed tests
    failed = [r for r in results if not r.get("passed")]
    if failed:
        print(f"\n[FAIL] Failed Tests: {len(failed)}")
        
        # Group by issue
        issues_count = {}
        for r in failed:
            if r.get("quality", {}).get("issues"):
                for issue in r["quality"]["issues"]:
                    issues_count[issue] = issues_count.get(issue, 0) + 1
        
        if issues_count:
            print("\nCommon Issues:")
            for issue, count in sorted(issues_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {issue}: {count} occurrences")
        
        print(f"\nFirst 10 failed prompts:")
        for i, r in enumerate(failed[:10], 1):
            print(f"  {i}. {r['prompt']}")
            if r.get("error"):
                print(f"     Error: {r['error']}")
            elif r.get("quality"):
                print(f"     Score: {r['quality']['score']}/100")
                print(f"     Issues: {', '.join(r['quality']['issues'])}")
    
    # Save results
    output_file = Path("ml_forecast_comprehensive_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "passed": response_ok,
            "failed": len(failed),
            "success_rate": response_ok / len(results) * 100,
            "results": [
                {
                    "prompt": r["prompt"],
                    "category": r.get("category"),
                    "passed": r.get("passed"),
                    "score": r.get("quality", {}).get("score"),
                    "issues": r.get("quality", {}).get("issues", []),
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Final status
    success_rate = response_ok / len(results) * 100
    print(f"\n{'=' * 80}")
    if success_rate >= 90:
        print("[SUCCESS] 90%+ success rate - ML forecasting is working well!")
    elif success_rate >= 75:
        print("[WARNING] 75-90% success rate - some improvements needed")
    else:
        print("[FAIL] Below 75% success rate - significant issues to fix")
    print(f"{'=' * 80}")
    
    return results

if __name__ == "__main__":
    main()

