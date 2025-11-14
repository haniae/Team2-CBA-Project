"""
Comprehensive quality test for ML forecasting responses.
Tests actual response quality, not just technical functionality.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings

# Test prompts - all variations
TEST_PROMPTS = [
    # Basic revenue forecasts
    "What's the revenue forecast for Microsoft?",
    "Forecast Apple's revenue for next 3 years",
    "Predict Tesla's revenue using Prophet",
    "What's Amazon's revenue forecast using ARIMA?",
    "Show me Microsoft's revenue forecast using ensemble methods",
    
    # Specific model requests
    "Forecast Apple's net income using LSTM",
    "Predict Microsoft's revenue using Transformer",
    "What's Tesla's revenue forecast using GRU?",
    "Forecast Apple's revenue using the best ML model",
    
    # Multiple companies
    "What's the revenue forecast for Apple, Microsoft, and Tesla?",
    
    # Other metrics
    "Forecast Tesla's earnings using LSTM",
    "Forecast Microsoft's free cash flow using Prophet",
    "Predict Apple's EBITDA using ARIMA",
    "What's the revenue forecast for Tesla using ETS?",
    
    # Variations
    "Forecast Microsoft revenue",
    "Predict Apple earnings",
    "What's Tesla's revenue going to be?",
    "Show me a forecast for Amazon revenue",
]

def extract_forecast_values(text: str) -> List[float]:
    """Extract forecast values from text (currency amounts)."""
    # Pattern: $X.XB, $X.XM, $X.X billion, etc.
    patterns = [
        r'\$(\d+\.?\d*)\s*[BM]',  # $100B, $50.5M
        r'\$(\d+\.?\d*)\s*billion',  # $100 billion
        r'\$(\d+\.?\d*)\s*million',  # $50 million
        r'(\d+\.?\d*)\s*billion',  # 100 billion
        r'(\d+\.?\d*)\s*million',  # 50 million
    ]
    
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                val = float(match)
                # Normalize to billions
                if 'million' in pattern.lower() or 'M' in pattern:
                    val = val / 1000
                values.append(val)
            except ValueError:
                pass
    
    return values

def check_response_quality(response: str, prompt: str) -> Dict[str, Any]:
    """Comprehensive quality check for forecast responses."""
    quality = {
        "has_forecast_values": False,
        "forecast_count": 0,
        "has_confidence_intervals": False,
        "has_model_details": False,
        "has_model_name": False,
        "has_year_mentions": False,
        "has_snapshot": False,
        "has_error": False,
        "has_sources": False,
        "response_length": len(response),
        "issues": [],
    }
    
    response_lower = response.lower()
    
    # Check for forecast values
    forecast_values = extract_forecast_values(response)
    quality["forecast_count"] = len(forecast_values)
    quality["has_forecast_values"] = len(forecast_values) > 0
    
    if not quality["has_forecast_values"]:
        quality["issues"].append("No forecast values found (no $ amounts)")
    
    # Check for confidence intervals
    ci_patterns = [
        r'95%\s*confidence',
        r'confidence\s*interval',
        r'ci\s*[:\[]',
        r'\[\$.*-\s*\$.*\]',  # [$X - $Y] format
    ]
    quality["has_confidence_intervals"] = any(
        re.search(pattern, response_lower) for pattern in ci_patterns
    )
    if not quality["has_confidence_intervals"]:
        quality["issues"].append("No confidence intervals mentioned")
    
    # Check for model details
    model_keywords = [
        "lstm", "prophet", "arima", "ets", "gru", "transformer", "ensemble",
        "model", "forecast", "prediction", "algorithm"
    ]
    quality["has_model_details"] = any(
        keyword in response_lower for keyword in model_keywords
    )
    if not quality["has_model_details"]:
        quality["issues"].append("No model details mentioned")
    
    # Check for specific model name
    specific_models = ["lstm", "prophet", "arima", "ets", "gru", "transformer", "ensemble"]
    quality["has_model_name"] = any(
        model in response_lower for model in specific_models
    )
    if not quality["has_model_name"]:
        quality["issues"].append("No specific model name mentioned")
    
    # Check for year mentions (2025, 2026, 2027, etc.)
    year_pattern = r'\b(202[4-9]|203[0-5])\b'
    quality["has_year_mentions"] = bool(re.search(year_pattern, response))
    if not quality["has_year_mentions"]:
        quality["issues"].append("No forecast years mentioned")
    
    # Check for snapshots (should NOT be present)
    snapshot_indicators = [
        "phase1 kpis" in response_lower,
        "phase 1 kpis" in response_lower,
        "phase 2 kpis" in response_lower,
        ("growth snapshot" in response_lower and "forecast" not in response_lower[:500]),
        ("margin snapshot" in response_lower and "forecast" not in response_lower[:500]),
    ]
    quality["has_snapshot"] = any(snapshot_indicators)
    if quality["has_snapshot"]:
        quality["issues"].append("Contains snapshot data (should be forecast only)")
    
    # Check for errors
    error_indicators = [
        "apologize" in response_lower and "forecast" not in response_lower[:200],
        "error" in response_lower and "forecast" not in response_lower[:200],
        "unable" in response_lower and "forecast" not in response_lower[:200],
        "issue" in response_lower and "forecast" not in response_lower[:200],
    ]
    quality["has_error"] = any(error_indicators)
    if quality["has_error"]:
        quality["issues"].append("Contains error message")
    
    # Check for sources
    quality["has_sources"] = (
        "source" in response_lower or
        "📊" in response or
        "http" in response_lower or
        "[10-k" in response_lower or
        "[10-q" in response_lower
    )
    if not quality["has_sources"]:
        quality["issues"].append("No sources cited")
    
    return quality

def test_prompt_quality(prompt: str, index: int, total: int) -> Dict[str, Any]:
    """Test a single prompt and return quality metrics."""
    print(f"\n[{index}/{total}] Testing: {prompt}")
    print("-" * 80)
    
    result = {
        "prompt": prompt,
        "response": None,
        "quality": None,
        "error": None,
        "passed": False,
    }
    
    try:
        settings = load_settings()
        bot = BenchmarkOSChatbot.create(settings)
        response = bot.ask(prompt)
        
        if response:
            result["response"] = response
            result["quality"] = check_response_quality(response, prompt)
            
            # Determine if passed (must meet minimum criteria)
            quality = result["quality"]
            result["passed"] = (
                quality["has_forecast_values"] and
                quality["has_model_name"] and
                not quality["has_snapshot"] and
                not quality["has_error"] and
                quality["response_length"] > 200  # Not too short
            )
            
            # Print quality summary
            print(f"[OK] Response Generated: {len(response)} chars")
            print(f"   Forecast Values: {quality['forecast_count']} found")
            print(f"   Model Name: {'[OK]' if quality['has_model_name'] else '[FAIL]'}")
            print(f"   Confidence Intervals: {'[OK]' if quality['has_confidence_intervals'] else '[FAIL]'}")
            print(f"   Years Mentioned: {'[OK]' if quality['has_year_mentions'] else '[FAIL]'}")
            print(f"   Sources: {'[OK]' if quality['has_sources'] else '[FAIL]'}")
            print(f"   Has Snapshot: {'[FAIL] YES (BAD)' if quality['has_snapshot'] else '[OK] NO'}")
            print(f"   Has Error: {'[FAIL] YES (BAD)' if quality['has_error'] else '[OK] NO'}")
            
            if quality["issues"]:
                print(f"   Issues: {', '.join(quality['issues'])}")
            
            print(f"   Status: {'[PASS]' if result['passed'] else '[FAIL]'}")
            
            # Show preview
            preview = response[:300] + "..." if len(response) > 300 else response
            print(f"\n   Preview:\n   {preview}\n")
        else:
            result["error"] = "No response generated"
            print(f"[FAIL] No response generated")
            
    except Exception as e:
        result["error"] = str(e)
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
    
    return result

def main():
    """Run comprehensive quality tests."""
    print("=" * 80)
    print("ML FORECASTING - COMPREHENSIVE QUALITY TEST")
    print("=" * 80)
    print(f"\nTesting {len(TEST_PROMPTS)} prompts...")
    
    results = []
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        result = test_prompt_quality(prompt, i, len(TEST_PROMPTS))
        results.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("QUALITY TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Success Rate: {passed/len(results)*100:.1f}%")
    
    # Quality metrics summary
    if results:
        qualities = [r["quality"] for r in results if r.get("quality")]
        if qualities:
            print(f"\nQuality Metrics (averages):")
            print(f"  Forecast Values: {sum(q['forecast_count'] for q in qualities) / len(qualities):.1f} per response")
            print(f"  Has Model Name: {sum(1 for q in qualities if q['has_model_name']) / len(qualities) * 100:.1f}%")
            print(f"  Has Confidence Intervals: {sum(1 for q in qualities if q['has_confidence_intervals']) / len(qualities) * 100:.1f}%")
            print(f"  Has Years: {sum(1 for q in qualities if q['has_year_mentions']) / len(qualities) * 100:.1f}%")
            print(f"  Has Sources: {sum(1 for q in qualities if q['has_sources']) / len(qualities) * 100:.1f}%")
            print(f"  Has Snapshots (BAD): {sum(1 for q in qualities if q['has_snapshot']) / len(qualities) * 100:.1f}%")
            print(f"  Has Errors (BAD): {sum(1 for q in qualities if q['has_error']) / len(qualities) * 100:.1f}%")
    
    # Failed tests details
    failed_results = [r for r in results if not r.get("passed")]
    if failed_results:
        print(f"\n[FAIL] FAILED TESTS ({len(failed_results)}):")
        for i, result in enumerate(failed_results, 1):
            print(f"\n{i}. {result['prompt']}")
            if result.get("error"):
                print(f"   Error: {result['error']}")
            elif result.get("quality"):
                q = result["quality"]
                print(f"   Issues: {', '.join(q['issues']) if q['issues'] else 'Unknown'}")
                print(f"   Response length: {q['response_length']} chars")
                if result.get("response"):
                    preview = result["response"][:200] + "..." if len(result["response"]) > 200 else result["response"]
                    print(f"   Preview: {preview}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if failed > 0:
        print("\n[WARN] Issues found:")
        if any(r.get("quality", {}).get("has_snapshot") for r in results):
            print("  - Some responses contain snapshots instead of forecasts")
            print("    → Fix: Ensure LLM instructions emphasize forecast-only responses")
        
        if any(r.get("quality", {}).get("has_error") for r in results):
            print("  - Some responses contain error messages")
            print("    → Fix: Check error handling and fallback mechanisms")
        
        if any(not r.get("quality", {}).get("has_forecast_values") for r in results):
            print("  - Some responses lack forecast values")
            print("    → Fix: Ensure forecast context is properly formatted and visible to LLM")
        
        if any(not r.get("quality", {}).get("has_model_name") for r in results):
            print("  - Some responses don't mention the model used")
            print("    → Fix: Strengthen system prompt to require model name")
    else:
        print("\n[OK] All tests passed! Quality is good.")
    
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    main()

