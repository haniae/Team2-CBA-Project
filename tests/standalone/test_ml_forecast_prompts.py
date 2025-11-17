"""
Comprehensive test script for ML forecasting prompts.
Tests all example prompts to ensure they work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.context_builder import _is_forecasting_query, _extract_forecast_metric, _extract_forecast_method

# Test prompts from the documentation
TEST_PROMPTS = [
    "What's the revenue forecast for Microsoft?",
    "Forecast Apple's revenue for next 3 years",
    "Predict Tesla's revenue using Prophet",
    "What's Amazon's revenue forecast using ARIMA?",
    "Show me Microsoft's revenue forecast using ensemble methods",
    "Forecast Apple's net income using LSTM",
    "Predict Microsoft's revenue using Transformer",
    "What's Tesla's revenue forecast using GRU?",
    "Forecast Apple's revenue using the best ML model",
    "What's the revenue forecast for Apple, Microsoft, and Tesla?",
    # Additional variations
    "Forecast Tesla's earnings using LSTM",
    "Forecast Microsoft's free cash flow using Prophet",
    "Predict Apple's EBITDA using ARIMA",
    "What's the revenue forecast for Tesla using ETS?",
]

def test_query_detection(prompt: str) -> dict:
    """Test if a prompt is correctly detected as a forecasting query."""
    result = {
        "prompt": prompt,
        "is_forecasting": False,
        "metric": None,
        "method": None,
        "detection_ok": False,
    }
    
    try:
        result["is_forecasting"] = _is_forecasting_query(prompt)
        if result["is_forecasting"]:
            result["metric"] = _extract_forecast_metric(prompt)
            result["method"] = _extract_forecast_method(prompt)
            result["detection_ok"] = True
    except Exception as e:
        result["error"] = str(e)
    
    return result

def test_context_generation(prompt: str) -> dict:
    """Test if forecast context is generated correctly."""
    result = {
        "prompt": prompt,
        "context_generated": False,
        "has_ml_forecast": False,
        "has_critical": False,
        "context_length": 0,
        "error": None,
    }
    
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
        
        if context:
            result["context_generated"] = True
            result["context_length"] = len(context)
            result["has_ml_forecast"] = "ML FORECAST" in context or "ML forecast" in context
            result["has_critical"] = "CRITICAL: THIS IS THE PRIMARY ANSWER" in context or "CRITICAL" in context
    except Exception as e:
        result["error"] = str(e)
    
    return result

def test_chatbot_response(prompt: str) -> dict:
    """Test if chatbot generates a valid forecast response."""
    result = {
        "prompt": prompt,
        "response_generated": False,
        "response_length": 0,
        "has_forecast_values": False,
        "has_model_details": False,
        "has_snapshot": False,
        "has_error": False,
        "response_preview": None,
        "error": None,
    }
    
    try:
        settings = load_settings()
        bot = FinanlyzeOSChatbot.create(settings)
        reply = bot.ask(prompt)
        
        if reply:
            result["response_generated"] = True
            result["response_length"] = len(reply)
            result["response_preview"] = reply[:500] if len(reply) > 500 else reply
            
            reply_lower = reply.lower()
            
            # Check for forecast indicators
            forecast_indicators = [
                "forecast" in reply_lower,
                "projected" in reply_lower,
                "predicted" in reply_lower,
                "$" in reply,  # Currency values
                "billion" in reply_lower or "million" in reply_lower,
            ]
            result["has_forecast_values"] = any(forecast_indicators)
            
            # Check for model details
            model_indicators = [
                "lstm" in reply_lower,
                "prophet" in reply_lower,
                "arima" in reply_lower,
                "ets" in reply_lower,
                "gru" in reply_lower,
                "transformer" in reply_lower,
                "ensemble" in reply_lower,
                "model" in reply_lower,
            ]
            result["has_model_details"] = any(model_indicators)
            
            # Check for snapshot indicators (should NOT be present)
            snapshot_indicators = [
                "phase1 kpis" in reply_lower,
                "phase 1 kpis" in reply_lower,
                "growth snapshot" in reply_lower and "forecast" not in reply_lower,
                "margin snapshot" in reply_lower and "forecast" not in reply_lower,
            ]
            result["has_snapshot"] = any(snapshot_indicators)
            
            # Check for error messages
            result["has_error"] = (
                "apologize" in reply_lower or
                "error" in reply_lower or
                "issue" in reply_lower or
                "unable" in reply_lower
            ) and "forecast" not in reply_lower[:200]
            
    except Exception as e:
        result["error"] = str(e)
        result["has_error"] = True
    
    return result

def print_test_results(results: list, test_type: str):
    """Print formatted test results."""
    print(f"\n{'='*80}")
    print(f"TEST RESULTS: {test_type}")
    print(f"{'='*80}\n")
    
    passed = 0
    failed = 0
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result.get("detection_ok") or result.get("context_generated") or result.get("response_generated") else "❌ FAIL"
        
        if status == "✅ PASS":
            passed += 1
        else:
            failed += 1
        
        print(f"{i}. {status} - {result['prompt']}")
        
        if "error" in result:
            print(f"   ERROR: {result['error']}")
        elif test_type == "Query Detection":
            print(f"   Is Forecasting: {result.get('is_forecasting')}")
            print(f"   Metric: {result.get('metric')}")
            print(f"   Method: {result.get('method')}")
        elif test_type == "Context Generation":
            print(f"   Context Generated: {result.get('context_generated')}")
            print(f"   Has ML Forecast: {result.get('has_ml_forecast')}")
            print(f"   Has Critical: {result.get('has_critical')}")
            print(f"   Context Length: {result.get('context_length')}")
        elif test_type == "Chatbot Response":
            print(f"   Response Generated: {result.get('response_generated')}")
            print(f"   Has Forecast Values: {result.get('has_forecast_values')}")
            print(f"   Has Model Details: {result.get('has_model_details')}")
            print(f"   Has Snapshot (BAD): {result.get('has_snapshot')}")
            print(f"   Has Error: {result.get('has_error')}")
            if result.get('response_preview'):
                print(f"   Preview: {result['response_preview'][:200]}...")
        
        print()
    
    print(f"{'='*80}")
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests")
    print(f"{'='*80}\n")

def main():
    """Run all tests."""
    print("="*80)
    print("ML FORECASTING PROMPTS - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Test 1: Query Detection
    print("\n[1/3] Testing Query Detection...")
    detection_results = [test_query_detection(prompt) for prompt in TEST_PROMPTS]
    print_test_results(detection_results, "Query Detection")
    
    # Test 2: Context Generation
    print("\n[2/3] Testing Context Generation...")
    context_results = [test_context_generation(prompt) for prompt in TEST_PROMPTS]
    print_test_results(context_results, "Context Generation")
    
    # Test 3: Chatbot Response (only test first 5 to avoid long runtime)
    print("\n[3/3] Testing Chatbot Responses (first 5 prompts)...")
    chatbot_results = [test_chatbot_response(prompt) for prompt in TEST_PROMPTS[:5]]
    print_test_results(chatbot_results, "Chatbot Response")
    
    # Overall summary
    print("\n" + "="*80)
    print("OVERALL SUMMARY")
    print("="*80)
    
    detection_ok = sum(1 for r in detection_results if r.get("detection_ok"))
    context_ok = sum(1 for r in context_results if r.get("context_generated") and r.get("has_ml_forecast"))
    chatbot_ok = sum(1 for r in chatbot_results if r.get("response_generated") and r.get("has_forecast_values") and not r.get("has_snapshot") and not r.get("has_error"))
    
    print(f"Query Detection: {detection_ok}/{len(detection_results)} passed")
    print(f"Context Generation: {context_ok}/{len(context_results)} passed")
    print(f"Chatbot Response: {chatbot_ok}/{len(chatbot_results)} passed")
    
    if detection_ok == len(detection_results) and context_ok == len(context_results) and chatbot_ok == len(chatbot_results):
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check details above")
    
    print("="*80)

if __name__ == "__main__":
    main()

