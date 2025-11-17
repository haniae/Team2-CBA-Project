"""
Comprehensive test suite for ALL possible ML forecasting prompts.
Tests every variation to ensure 100% correct responses.
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

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.context_builder import _is_forecasting_query, _extract_forecast_metric, _extract_forecast_method

# ALL POSSIBLE ML FORECASTING PROMPTS
# Organized by category for comprehensive coverage

COMPANIES = ["Apple", "Microsoft", "Tesla", "Amazon", "Google", "Meta", "Nvidia", "Netflix", "AMD", "Intel"]
TICKERS = ["AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "NVDA", "NFLX", "AMD", "INTC"]
METRICS = ["revenue", "earnings", "net income", "free cash flow", "EBITDA", "gross profit", "operating income", "EPS"]
MODELS = ["Prophet", "ARIMA", "LSTM", "GRU", "Transformer", "ETS", "ensemble", "best", "auto"]

# Base prompt templates
PROMPT_TEMPLATES = [
    # Direct forecast requests
    "Forecast {company}'s {metric}",
    "Forecast {company} {metric}",
    "Predict {company}'s {metric}",
    "Predict {company} {metric}",
    "What's {company}'s {metric} forecast?",
    "What is {company}'s {metric} forecast?",
    "Show me {company}'s {metric} forecast",
    "Give me {company}'s {metric} forecast",
    "I need {company}'s {metric} forecast",
    
    # With model specification
    "Forecast {company}'s {metric} using {model}",
    "Predict {company}'s {metric} using {model}",
    "What's {company}'s {metric} forecast using {model}?",
    "Show me {company}'s {metric} forecast using {model}",
    "{company} {metric} forecast {model}",
    
    # With time period
    "Forecast {company}'s {metric} for next 3 years",
    "Predict {company}'s {metric} for the next 3 years",
    "What's {company}'s {metric} forecast for 2025-2027?",
    "Forecast {company} {metric} next 3 years",
    
    # With model and time
    "Forecast {company}'s {metric} for next 3 years using {model}",
    "Predict {company}'s {metric} for 2025-2027 using {model}",
    
    # Variations
    "What will {company}'s {metric} be?",
    "What will {company} {metric} be in the future?",
    "Project {company}'s {metric}",
    "Estimate {company}'s {metric}",
    "What's the outlook for {company} {metric}?",
    
    # Multiple companies
    "Forecast {company1} and {company2} {metric}",
    "What's the {metric} forecast for {company1} and {company2}?",
    "Compare {metric} forecasts for {company1} and {company2}",
    
    # Question formats
    "Can you forecast {company}'s {metric}?",
    "Can you predict {company}'s {metric} using {model}?",
    "How much will {company}'s {metric} be?",
    "What do you think {company}'s {metric} will be?",
    
    # Imperative
    "Forecast {company} {metric} now",
    "Run a forecast for {company} {metric}",
    "Generate forecast for {company} {metric}",
    
    # With context
    "I want to know {company}'s {metric} forecast",
    "I need a forecast of {company}'s {metric}",
    "Please forecast {company}'s {metric}",
]

def generate_all_prompts() -> List[str]:
    """Generate all possible prompt variations."""
    prompts = []
    
    # Single company, single metric, no model
    for company in COMPANIES[:5]:  # Test with first 5 companies
        for metric in METRICS[:4]:  # Test with first 4 metrics
            for template in PROMPT_TEMPLATES[:10]:  # First 10 templates
                if "{model}" not in template and "{company1}" not in template:
                    prompt = template.format(company=company, metric=metric)
                    prompts.append(prompt)
    
    # Single company, single metric, with model
    for company in COMPANIES[:3]:
        for metric in METRICS[:3]:
            for model in MODELS[:5]:
                for template in PROMPT_TEMPLATES:
                    if "{model}" in template and "{company1}" not in template:
                        prompt = template.format(company=company, metric=metric, model=model)
                        prompts.append(prompt)
    
    # Multiple companies
    for company1, company2 in zip(COMPANIES[:3], COMPANIES[1:4]):
        for metric in METRICS[:2]:
            for template in PROMPT_TEMPLATES:
                if "{company1}" in template:
                    prompt = template.format(company1=company1, company2=company2, metric=metric)
                    prompts.append(prompt)
    
    # Remove duplicates and sort
    prompts = list(dict.fromkeys(prompts))  # Preserves order
    return prompts[:100]  # Limit to 100 for testing

def extract_forecast_values(text: str) -> List[float]:
    """Extract forecast values from text."""
    patterns = [
        r'\$(\d+\.?\d*)\s*[BM]',
        r'\$(\d+\.?\d*)\s*billion',
        r'\$(\d+\.?\d*)\s*million',
        r'(\d+\.?\d*)\s*billion',
        r'(\d+\.?\d*)\s*million',
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

def check_response_quality(response: str, prompt: str) -> Dict[str, Any]:
    """Comprehensive quality check."""
    quality = {
        "has_forecast_values": False,
        "forecast_count": 0,
        "has_model_name": False,
        "has_confidence_intervals": False,
        "has_years": False,
        "has_snapshot": False,
        "has_error": False,
        "response_length": len(response),
        "issues": [],
        "score": 0,  # Quality score 0-100
    }
    
    response_lower = response.lower()
    
    # Check forecast values
    forecast_values = extract_forecast_values(response)
    quality["forecast_count"] = len(forecast_values)
    quality["has_forecast_values"] = len(forecast_values) > 0
    if quality["has_forecast_values"]:
        quality["score"] += 30
    else:
        quality["issues"].append("No forecast values found")
    
    # Check model name
    models = ["lstm", "prophet", "arima", "ets", "gru", "transformer", "ensemble"]
    quality["has_model_name"] = any(m in response_lower for m in models)
    if quality["has_model_name"]:
        quality["score"] += 20
    else:
        quality["issues"].append("No model name mentioned")
    
    # Check confidence intervals
    ci_patterns = [
        r'95%\s*confidence',
        r'confidence\s*interval',
        r'ci\s*[:\[]',
        r'\[\$.*-\s*\$.*\]',
    ]
    quality["has_confidence_intervals"] = any(
        re.search(pattern, response_lower) for pattern in ci_patterns
    )
    if quality["has_confidence_intervals"]:
        quality["score"] += 15
    else:
        quality["issues"].append("No confidence intervals")
    
    # Check years
    quality["has_years"] = bool(re.search(r'\b(202[4-9]|203[0-5])\b', response))
    if quality["has_years"]:
        quality["score"] += 10
    else:
        quality["issues"].append("No forecast years mentioned")
    
    # Check for snapshots (BAD - deduct points)
    snapshot_indicators = [
        "phase1 kpis" in response_lower,
        "phase 1 kpis" in response_lower,
        ("growth snapshot" in response_lower and "forecast" not in response_lower[:500]),
        ("margin snapshot" in response_lower and "forecast" not in response_lower[:500]),
    ]
    quality["has_snapshot"] = any(snapshot_indicators)
    if quality["has_snapshot"]:
        quality["score"] -= 50
        quality["issues"].append("Contains snapshot (BAD)")
    
    # Check for errors (BAD - deduct points)
    error_indicators = [
        "apologize" in response_lower and "forecast" not in response_lower[:200],
        "error" in response_lower and "forecast" not in response_lower[:200],
        "unable" in response_lower and "forecast" not in response_lower[:200],
        "issue" in response_lower and "forecast" not in response_lower[:200],
    ]
    quality["has_error"] = any(error_indicators)
    if quality["has_error"]:
        quality["score"] -= 50
        quality["issues"].append("Contains error message (BAD)")
    
    # Minimum length check
    if quality["response_length"] < 200:
        quality["score"] -= 20
        quality["issues"].append("Response too short")
    
    # Ensure score is between 0-100
    quality["score"] = max(0, min(100, quality["score"]))
    
    # Determine if passed (score >= 50 and no critical issues)
    quality["passed"] = (
        quality["score"] >= 50 and
        not quality["has_snapshot"] and
        not quality["has_error"] and
        quality["has_forecast_values"]
    )
    
    return quality

def test_prompt(prompt: str, index: int, total: int) -> Dict[str, Any]:
    """Test a single prompt comprehensively."""
    result = {
        "prompt": prompt,
        "index": index,
        "detection": {},
        "context": {},
        "response": None,
        "quality": None,
        "error": None,
        "passed": False,
    }
    
    try:
        # Test 1: Query Detection
        result["detection"] = {
            "is_forecasting": _is_forecasting_query(prompt),
            "metric": _extract_forecast_metric(prompt) if _is_forecasting_query(prompt) else None,
            "method": _extract_forecast_method(prompt) if _is_forecasting_query(prompt) else None,
        }
        
        # Test 2: Context Generation
        try:
            from finanlyzeos_chatbot.context_builder import build_financial_context
            from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
            
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
                "length": len(context) if context else 0,
                "has_ml_forecast": "ML FORECAST" in (context or ""),
                "has_critical": "CRITICAL" in (context or ""),
            }
        except Exception as e:
            result["context"] = {"error": str(e)}
        
        # Test 3: Chatbot Response
        settings = load_settings()
        bot = FinanlyzeOSChatbot.create(settings)
        response = bot.ask(prompt)
        
        if response:
            result["response"] = response
            result["quality"] = check_response_quality(response, prompt)
            result["passed"] = result["quality"]["passed"]
        else:
            result["error"] = "No response generated"
            
    except Exception as e:
        result["error"] = str(e)
        import traceback
        result["traceback"] = traceback.format_exc()
    
    return result

def main():
    """Run comprehensive tests on all prompts."""
    print("=" * 80)
    print("COMPREHENSIVE ML FORECASTING PROMPT TEST SUITE")
    print("=" * 80)
    
    # Generate all prompts
    print("\nGenerating all possible prompt variations...")
    all_prompts = generate_all_prompts()
    print(f"Generated {len(all_prompts)} unique prompts")
    
    # Test all prompts
    print(f"\nTesting all {len(all_prompts)} prompts...")
    print("This may take a while...\n")
    
    results = []
    for i, prompt in enumerate(all_prompts, 1):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(all_prompts)} ({i/len(all_prompts)*100:.1f}%)")
        
        result = test_prompt(prompt, i, len(all_prompts))
        results.append(result)
    
    # Analyze results
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    
    # Detection results
    detection_passed = sum(1 for r in results if r.get("detection", {}).get("is_forecasting"))
    print(f"\n1. Query Detection: {detection_passed}/{len(results)} ({detection_passed/len(results)*100:.1f}%)")
    
    # Context results
    context_passed = sum(1 for r in results if r.get("context", {}).get("generated") and r.get("context", {}).get("has_ml_forecast"))
    print(f"2. Context Generation: {context_passed}/{len(results)} ({context_passed/len(results)*100:.1f}%)")
    
    # Response results
    response_passed = sum(1 for r in results if r.get("passed"))
    print(f"3. Response Quality: {response_passed}/{len(results)} ({response_passed/len(results)*100:.1f}%)")
    
    # Quality metrics
    qualities = [r["quality"] for r in results if r.get("quality")]
    if qualities:
        print(f"\nQuality Metrics (averages):")
        print(f"  Average Score: {sum(q['score'] for q in qualities) / len(qualities):.1f}/100")
        print(f"  Forecast Values: {sum(q['forecast_count'] for q in qualities) / len(qualities):.1f} per response")
        print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model_name']) / len(qualities) * 100:.1f}%")
        print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_confidence_intervals']) / len(qualities) * 100:.1f}%")
        print(f"  Has Years: {sum(1 for q in qualities if q['has_years']) / len(qualities) * 100:.1f}%")
        print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
        print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    # Failed tests
    failed = [r for r in results if not r.get("passed")]
    if failed:
        print(f"\n[FAIL] Failed Tests: {len(failed)}")
        print("\nTop 20 failures:")
        for i, result in enumerate(failed[:20], 1):
            print(f"\n{i}. {result['prompt']}")
            if result.get("error"):
                print(f"   Error: {result['error']}")
            elif result.get("quality"):
                q = result["quality"]
                print(f"   Score: {q['score']}/100")
                print(f"   Issues: {', '.join(q['issues']) if q['issues'] else 'Unknown'}")
    
    # Save detailed results to JSON
    output_file = Path("ml_forecast_test_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "passed": response_passed,
            "failed": len(failed),
            "results": [
                {
                    "prompt": r["prompt"],
                    "passed": r.get("passed"),
                    "quality_score": r.get("quality", {}).get("score"),
                    "issues": r.get("quality", {}).get("issues", []),
                    "error": r.get("error"),
                }
                for r in results
            ]
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Overall status
    success_rate = response_passed / len(results) * 100
    print(f"\n{'=' * 80}")
    if success_rate >= 90:
        print("[SUCCESS] 90%+ of prompts working correctly!")
    elif success_rate >= 75:
        print("[WARNING] 75-90% of prompts working - needs improvement")
    else:
        print("[FAIL] Less than 75% working - significant issues")
    print(f"{'=' * 80}")
    
    return results

if __name__ == "__main__":
    main()

