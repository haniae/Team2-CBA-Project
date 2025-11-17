"""Fast unit tests for advanced follow-up features (no LLM calls)."""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.followup_context import (
    ConversationContext,
    detect_ambiguity,
    resolve_implicit_entities,
    calculate_resolution_confidence,
    should_ask_clarification,
)
from finanlyzeos_chatbot.intent_carryover import (
    should_carry_over_intent,
    augment_query_with_intent,
)

def test_ambiguity_detection():
    """Test ambiguity detection logic."""
    print("\n" + "=" * 80)
    print("Test: Ambiguity Detection")
    print("=" * 80)
    
    tests = [
        ("Tell me about it", ['AAPL', 'MSFT'], True, "Singular pronoun with 2 tickers"),
        ("Tell me about it", ['AAPL'], False, "Singular pronoun with 1 ticker"),
        ("Tell me about them", ['AAPL', 'MSFT'], False, "Plural pronoun with 2 tickers"),
        ("Tell me about them", ['AAPL'], False, "Plural with 1 ticker (OK)"),
    ]
    
    passed = 0
    for query, tickers, should_be_ambiguous, desc in tests:
        ctx = ConversationContext(tickers=tickers, timestamp=datetime.utcnow())
        is_ambiguous, msg = detect_ambiguity(query, ctx)
        if is_ambiguous == should_be_ambiguous:
            print(f"✅ {desc}")
            passed += 1
        else:
            print(f"❌ {desc} - Expected ambiguous={should_be_ambiguous}, got={is_ambiguous}")
    
    return passed, len(tests)

def test_implicit_entity_resolution():
    """Test implicit entity resolution."""
    print("\n" + "=" * 80)
    print("Test: Implicit Entity Resolution")
    print("=" * 80)
    
    tests = [
        ("What about margins?", ['AAPL'], ['revenue'], True, "Metric query without ticker"),
        ("Show me MSFT data", ['AAPL'], [], False, "Explicit ticker, no carryover"),
        ("Tell me more", ['AAPL'], [], False, "Generic follow-up"),
    ]
    
    passed = 0
    for query, tickers, metrics, should_carry_tickers, desc in tests:
        ctx = ConversationContext(tickers=tickers, metrics=metrics, timestamp=datetime.utcnow())
        resolved = resolve_implicit_entities(query, ctx)
        carried_over = 'tickers' in resolved['carried_over']
        
        if carried_over == should_carry_tickers:
            print(f"✅ {desc}")
            passed += 1
        else:
            print(f"❌ {desc} - Expected carry_over={should_carry_tickers}, got={carried_over}")
    
    return passed, len(tests)

def test_confidence_scoring():
    """Test confidence scoring logic."""
    print("\n" + "=" * 80)
    print("Test: Confidence Scoring")
    print("=" * 80)
    
    tests = [
        (ConversationContext(tickers=['AAPL'], timestamp=datetime.utcnow()), ['it'], ">0.8", "Recent + clear"),
        (ConversationContext(tickers=[], timestamp=None), ['it'], "=0.0", "No context"),
        (ConversationContext(tickers=['AAPL', 'MSFT'], timestamp=datetime.utcnow()), ['it', 'that'], "<0.7", "Multiple pronouns + tickers"),
    ]
    
    passed = 0
    for ctx, pronouns, expected_range, desc in tests:
        confidence = calculate_resolution_confidence("test query", ctx, pronouns)
        
        if expected_range.startswith(">"):
            threshold = float(expected_range[1:])
            success = confidence > threshold
        elif expected_range.startswith("<"):
            threshold = float(expected_range[1:])
            success = confidence < threshold
        else:  # "="
            threshold = float(expected_range[1:])
            success = abs(confidence - threshold) < 0.1
        
        if success:
            print(f"✅ {desc} (confidence={confidence:.2f})")
            passed += 1
        else:
            print(f"❌ {desc} - Expected {expected_range}, got {confidence:.2f}")
    
    return passed, len(tests)

def test_intent_carryover_detection():
    """Test intent carryover detection."""
    print("\n" + "=" * 80)
    print("Test: Intent Carryover Detection")
    print("=" * 80)
    
    tests = [
        ("What about Microsoft?", "risk_analysis", True, "Follow-up with 'what about'"),
        ("How about Tesla?", "valuation", True, "Follow-up with 'how about'"),
        ("Tell me more", "forecast", True, "Continuation phrase"),
        ("Show me Apple", None, False, "No intent to carry over"),
        ("Compare them", "compare", False, "New query, not carry over"),
    ]
    
    passed = 0
    for query, last_intent, should_carry, desc in tests:
        result = should_carry_over_intent(query, last_intent)
        if result == should_carry:
            print(f"✅ {desc}")
            passed += 1
        else:
            print(f"❌ {desc} - Expected {should_carry}, got {result}")
    
    return passed, len(tests)

def test_intent_query_augmentation():
    """Test intent-based query augmentation."""
    print("\n" + "=" * 80)
    print("Test: Intent Query Augmentation")
    print("=" * 80)
    
    tests = [
        ("What about Tesla?", "risk_analysis", "risks of Tesla", "Augment with risk question"),
        ("How about Microsoft?", "valuation", "overvalued", "Augment with valuation"),
        ("What about Amazon?", "forecast", "What will Amazon", "Augment with forecast"),
    ]
    
    passed = 0
    for query, last_intent, expected_substring, desc in tests:
        augmented, was_augmented = augment_query_with_intent(query, last_intent, None)
        if was_augmented and expected_substring.lower() in augmented.lower():
            print(f"✅ {desc}")
            print(f"   Augmented: {augmented}")
            passed += 1
        else:
            print(f"❌ {desc}")
            print(f"   Expected substring: '{expected_substring}'")
            print(f"   Got: '{augmented}'")
    
    return passed, len(tests)

def main():
    """Run all tests."""
    total_passed = 0
    total_tests = 0
    
    p, t = test_ambiguity_detection()
    total_passed += p
    total_tests += t
    
    p, t = test_implicit_entity_resolution()
    total_passed += p
    total_tests += t
    
    p, t = test_confidence_scoring()
    total_passed += p
    total_tests += t
    
    p, t = test_intent_carryover_detection()
    total_passed += p
    total_tests += t
    
    p, t = test_intent_query_augmentation()
    total_passed += p
    total_tests += t
    
    print("\n" + "=" * 80)
    print("OVERALL RESULTS")
    print("=" * 80)
    print(f"Total: {total_passed}/{total_tests} tests passed")
    print(f"Success Rate: {total_passed / total_tests * 100:.1f}%")
    print("=" * 80)
    
    if total_passed == total_tests:
        print("✅ All advanced follow-up features working!")
        return True
    else:
        print(f"⚠️  {total_tests - total_passed} tests need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

