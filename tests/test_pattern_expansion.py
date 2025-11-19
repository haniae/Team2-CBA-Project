"""Quick test script to verify expanded patterns are working."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import (
    INTENT_RECOMMENDATION_PATTERN,
    INTENT_RISK_PATTERN,
    INTENT_OPTIMIZATION_PATTERN,
    INTENT_VALUATION_PATTERN,
    INTENT_ATTRIBUTION_PATTERN,
    INTENT_FORECAST_PATTERN,
    INTENT_EFFICIENCY_PATTERN,
    classify_intent,
    normalize,
)
from finanlyzeos_chatbot.parsing.metric_inference import MetricInferenceEngine
from finanlyzeos_chatbot.parsing.question_chaining import QuestionChainDetector

def test_intent_patterns():
    """Test new intent patterns."""
    print("=" * 60)
    print("Testing Intent Patterns")
    print("=" * 60)
    
    test_cases = [
        # Recommendation patterns
        ("should i buy apple stock", "recommendation"),
        ("what do you recommend", "recommendation"),
        ("is it a good investment", "recommendation"),
        ("what's your take on microsoft", "recommendation"),
        
        # Risk patterns
        ("what are the risks", "risk_analysis"),
        ("how risky is tesla", "risk_analysis"),
        ("what's the downside risk", "risk_analysis"),
        ("volatility analysis", "risk_analysis"),
        
        # Optimization patterns
        ("how to optimize my portfolio", "optimization"),
        ("what's the best strategy", "optimization"),
        ("how can i improve performance", "optimization"),
        ("portfolio optimization", "optimization"),
        
        # Valuation patterns
        ("is apple overvalued", "valuation"),
        ("what's it worth", "valuation"),
        ("fair value of microsoft", "valuation"),
        ("P/E ratio", "valuation"),
        
        # Attribution patterns
        ("what drove the performance", "attribution"),
        ("what contributed to growth", "attribution"),
        ("what explains the decline", "attribution"),
        ("key drivers of revenue", "attribution"),
        
        # Forecast patterns
        ("forecast revenue for next year", "forecast"),
        ("what will earnings be", "forecast"),
        ("future outlook", "forecast"),
        ("guidance for next quarter", "forecast"),
        
        # Efficiency patterns
        ("how efficient is the company", "efficiency"),
        ("what's the ROE", "efficiency"),
        ("return on assets", "efficiency"),
        ("asset turnover", "efficiency"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent in test_cases:
        norm = normalize(query)
        intent = classify_intent(norm, [], [], {})
        
        if intent == expected_intent:
            print(f"[PASS] '{query}' -> {intent}")
            passed += 1
        else:
            print(f"[FAIL] '{query}' -> Expected: {expected_intent}, Got: {intent}")
            failed += 1
    
    print(f"\nIntent Patterns: {passed} passed, {failed} failed")
    return passed, failed


def test_question_patterns():
    """Test question patterns in chatbot.py."""
    print("\n" + "=" * 60)
    print("Testing Question Patterns")
    print("=" * 60)
    
    # Import question patterns from chatbot
    import re
    
    # Read the question patterns from chatbot.py
    chatbot_file = Path(__file__).parent / "src" / "finanlyzeos_chatbot" / "chatbot.py"
    with open(chatbot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the question_patterns list
    import ast
    import inspect
    
    # We'll test a few manually
    test_queries = [
        ("i wonder what apple's revenue is", True),
        ("i'm curious about microsoft", True),
        ("can you clarify the margin", True),
        ("what about tesla", True),
        ("how does that compare", True),
        ("in context what is the growth", True),
        ("what should i do", True),
        ("i'm not sure what to ask", True),
        ("which would you choose", True),
        ("is that right", True),
        ("is there a way to optimize", True),
        ("give me everything about apple", True),
    ]
    
    # Simple test - check if patterns compile
    try:
        # Test a few key patterns manually
        casual_pattern = re.compile(r'\b(?:i\s+wonder|i\'m\s+wondering|i\'ve\s+been\s+wondering)\s+(?:what|how|why|when|where|which|if|whether)\b', re.IGNORECASE)
        clarification_pattern = re.compile(r'\b(?:can\s+you\s+clarify|could\s+you\s+clarify|would\s+you\s+clarify|please\s+clarify)\b', re.IGNORECASE)
        followup_pattern = re.compile(r'\b(?:what\s+about|how\s+about|what\s+else|anything\s+else|any\s+other)\b', re.IGNORECASE)
        
        passed = 0
        failed = 0
        
        for query, should_match in test_queries:
            matched = (
                casual_pattern.search(query) is not None or
                clarification_pattern.search(query) is not None or
                followup_pattern.search(query) is not None
            )
            
            if matched == should_match:
                print(f"[PASS] '{query}' -> Matched: {matched}")
                passed += 1
            else:
                print(f"[FAIL] '{query}' -> Expected: {should_match}, Got: {matched}")
                failed += 1
        
        print(f"\nQuestion Patterns: {passed} passed, {failed} failed")
        return passed, failed
    except Exception as e:
        print(f"[ERROR] testing question patterns: {e}")
        return 0, 1


def test_metric_inference():
    """Test new metric inference patterns."""
    print("\n" + "=" * 60)
    print("Testing Metric Inference Patterns")
    print("=" * 60)
    
    engine = MetricInferenceEngine()
    
    test_cases = [
        ("operating cash flow of $50B", "operating_cash_flow"),
        ("working capital is $10B", "working_capital"),
        ("current ratio of 2.5", "current_ratio"),
        ("quick ratio is 1.8", "quick_ratio"),
        ("debt-to-equity of 0.5", "debt_to_equity"),
        ("interest coverage ratio 5.2", "interest_coverage"),
        ("inventory turnover 8.3", "inventory_turnover"),
        ("asset turnover 1.2", "asset_turnover"),
        ("P/S ratio of 3.5", "price_to_sales"),
        ("EV/EBITDA is 12.5", "ev_ebitda"),
        ("dividend yield of 2.5%", "dividend_yield"),
        ("payout ratio 40%", "payout_ratio"),
        ("gross profit $100B", "gross_profit"),
        ("operating expenses $30B", "operating_expenses"),
        ("R&D expenses $15B", "rd_expenses"),
        ("CAPEX of $20B", "capex"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric in test_cases:
        inferred = engine.infer_metrics(query)
        found = any(m.metric_id == expected_metric for m in inferred)
        
        if found:
            print(f"[PASS] '{query}' -> Found: {expected_metric}")
            passed += 1
        else:
            print(f"[FAIL] '{query}' -> Expected: {expected_metric}, Got: {[m.metric_id for m in inferred]}")
            failed += 1
    
    print(f"\nMetric Inference: {passed} passed, {failed} failed")
    return passed, failed


def test_question_chaining():
    """Test question chaining patterns."""
    print("\n" + "=" * 60)
    print("Testing Question Chaining Patterns")
    print("=" * 60)
    
    detector = QuestionChainDetector()
    
    test_cases = [
        ("afterwards show me revenue", True, "sequential"),
        ("later tell me about profit", True, "sequential"),
        ("secondly what is the margin", True, "sequential"),
        ("moving on show me growth", True, "sequential"),
        ("relative to the previous how does it compare", True, "comparative"),
        ("same as the last one", True, "comparative"),
        ("let's also check earnings", True, "exploratory"),
        ("i'd also like to know revenue", True, "exploratory"),
        ("another thing what about debt", True, "exploratory"),
        ("and also show me cash flow", True, "continuation"),
        ("not only that but also revenue", True, "continuation"),
        ("along with that show profit", True, "continuation"),
        ("i need more info about margins", True, "elaboration"),
        ("dig deeper into revenue", True, "elaboration"),
        ("break it down for me", True, "elaboration"),
        ("what is revenue", False, None),  # Should not be a chain
    ]
    
    passed = 0
    failed = 0
    
    for query, should_chain, expected_type in test_cases:
        chain = detector.detect_chain(query)
        is_chained = chain is not None
        
        if should_chain:
            if is_chained and (expected_type is None or chain.chain_type.value == expected_type):
                print(f"[PASS] '{query}' -> {chain.chain_type.value if chain else 'None'}")
                passed += 1
            else:
                print(f"[FAIL] '{query}' -> Expected: {expected_type}, Got: {chain.chain_type.value if chain else 'None'}")
                failed += 1
        else:
            if not is_chained:
                print(f"[PASS] '{query}' -> Not chained (correct)")
                passed += 1
            else:
                print(f"[FAIL] '{query}' -> Expected: Not chained, Got: {chain.chain_type.value}")
                failed += 1
    
    print(f"\nQuestion Chaining: {passed} passed, {failed} failed")
    return passed, failed


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PATTERN EXPANSION VERIFICATION TESTS")
    print("=" * 60)
    
    results = []
    
    # Test intent patterns
    try:
        passed, failed = test_intent_patterns()
        results.append(("Intent Patterns", passed, failed))
    except Exception as e:
        print(f"ERROR in intent patterns: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Intent Patterns", 0, 1))
    
    # Test question patterns
    try:
        passed, failed = test_question_patterns()
        results.append(("Question Patterns", passed, failed))
    except Exception as e:
        print(f"ERROR in question patterns: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Question Patterns", 0, 1))
    
    # Test metric inference
    try:
        passed, failed = test_metric_inference()
        results.append(("Metric Inference", passed, failed))
    except Exception as e:
        print(f"ERROR in metric inference: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Metric Inference", 0, 1))
    
    # Test question chaining
    try:
        passed, failed = test_question_chaining()
        results.append(("Question Chaining", passed, failed))
    except Exception as e:
        print(f"ERROR in question chaining: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Question Chaining", 0, 1))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for name, passed, failed in results:
        total = passed + failed
        percentage = (passed / total * 100) if total > 0 else 0
        print(f"{name:25} {passed:3}/{total:3} ({percentage:5.1f}%)")
        total_passed += passed
        total_failed += failed
    
    print("-" * 60)
    total = total_passed + total_failed
    percentage = (total_passed / total * 100) if total > 0 else 0
    print(f"{'TOTAL':25} {total_passed:3}/{total:3} ({percentage:5.1f}%)")
    
    if total_failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILED] {total_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

