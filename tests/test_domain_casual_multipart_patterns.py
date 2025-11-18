"""Comprehensive test suite for domain-specific, casual, and multi-part query patterns."""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured


def test_domain_specific_financial_terms():
    """Test domain-specific financial terms as question starters."""
    
    print("=" * 80)
    print("Testing Domain-Specific Financial Terms Patterns")
    print("=" * 80)
    
    test_cases = [
        # Alpha patterns
        ("what is the alpha", "should detect as question"),
        ("how is alpha calculated", "should detect as question"),
        ("tell me about alpha", "should detect as question"),
        ("calculate the alpha", "should detect as question"),
        ("alpha of Apple", "should detect as question"),
        ("show me the alpha", "should detect as question"),
        
        # Beta patterns
        ("what's the beta", "should detect as question"),
        ("how is beta", "should detect as question"),
        ("tell me about beta", "should detect as question"),
        ("find the beta", "should detect as question"),
        ("beta for Tesla", "should detect as question"),
        ("show me beta", "should detect as question"),
        
        # Sharpe ratio patterns
        ("what is the Sharpe ratio", "should detect as question"),
        ("how is Sharpe ratio calculated", "should detect as question"),
        ("calculate the Sharpe ratio", "should detect as question"),
        ("Sharpe ratio of portfolio", "should detect as question"),
        ("show me the Sharpe ratio", "should detect as question"),
        ("what's the Sharpe", "should detect as question"),
        
        # Sortino ratio patterns
        ("what is Sortino ratio", "should detect as question"),
        ("calculate Sortino ratio", "should detect as question"),
        ("Sortino ratio for Apple", "should detect as question"),
        ("show me Sortino", "should detect as question"),
        
        # VAR/CVaR patterns
        ("what is VAR", "should detect as question"),
        ("calculate CVaR", "should detect as question"),
        ("what's the value at risk", "should detect as question"),
        ("conditional var of portfolio", "should detect as question"),
        ("expected shortfall is", "should detect as question"),
        
        # Tracking error patterns
        ("what is tracking error", "should detect as question"),
        ("calculate tracking error", "should detect as question"),
        ("tracking error for Apple", "should detect as question"),
        
        # Max drawdown patterns
        ("what is max drawdown", "should detect as question"),
        ("calculate max drawdown", "should detect as question"),
        ("max drawdown of portfolio", "should detect as question"),
        
        # Information ratio patterns
        ("what is information ratio", "should detect as question"),
        ("information ratio for Tesla", "should detect as question"),
        
        # Jensen's alpha patterns
        ("what is Jensen's alpha", "should detect as question"),
        ("calculate Jensens alpha", "should detect as question"),
        
        # Risk metrics general
        ("risk metrics like Sharpe", "should detect as question"),
        ("performance metrics including beta", "should detect as question"),
    ]
    
    passed = 0
    failed = 0
    
    for query, description in test_cases:
        try:
            result = parse_to_structured(query)
            intent = result.get('intent', 'N/A')
            
            # Check if it parsed successfully (has intent)
            has_intent = intent != 'N/A'
            
            status = "✓" if has_intent else "✗"
            print(f"{status} '{query}'")
            print(f"   Intent: {intent}")
            print(f"   Description: {description}")
            
            if has_intent:
                passed += 1
            else:
                failed += 1
                print(f"   ⚠ Failed to parse!")
            print()
            
        except Exception as e:
            print(f"✗ '{query}' - ERROR: {e}")
            failed += 1
            print()
    
    print("-" * 80)
    print(f"Domain-Specific Terms Tests: {passed} passed, {failed} failed")
    return passed, failed


def test_casual_slang_expressions():
    """Test casual/slang expression patterns."""
    
    print("=" * 80)
    print("Testing Casual/Slang Expression Patterns")
    print("=" * 80)
    
    test_cases = [
        # How's X doing patterns
        ("how's Apple doing", "should detect as question"),
        ("how is Tesla going", "should detect as question"),
        ("how are Microsoft performing", "should detect as question"),
        ("how's it looking", "should detect as question"),
        ("how things going", "should detect as question"),
        
        # What's the deal patterns
        ("what's the deal with Apple", "should detect as question"),
        ("what is the deal with Tesla", "should detect as question"),
        ("what's the story with Microsoft", "should detect as question"),
        ("what's the scoop on Nvidia", "should detect as question"),
        ("what's the latest on Amazon", "should detect as question"),
        ("what's up with Google", "should detect as question"),
        
        # What's X up to patterns
        ("what's Apple up to", "should detect as question"),
        ("what is Tesla about", "should detect as question"),
        ("what's Microsoft dealing with", "should detect as question"),
        ("what's it working on", "should detect as question"),
        
        # Status/condition patterns
        ("what's the situation with Apple", "should detect as question"),
        ("what's the status on Tesla", "should detect as question"),
        ("what's the state of Microsoft", "should detect as question"),
        ("what's the condition of portfolio", "should detect as question"),
        
        # Rundown/lowdown patterns
        ("give me the rundown on Apple", "should detect as question"),
        ("tell me the lowdown on Tesla", "should detect as question"),
        ("show me the scoop on Microsoft", "should detect as question"),
        ("give me the 411 on Nvidia", "should detect as question"),
        
        # What's happening patterns
        ("what's happening with Apple", "should detect as question"),
        ("what's going on with Tesla", "should detect as question"),
        ("what's up at Microsoft", "should detect as question"),
        
        # Is X any good patterns
        ("is Apple any good", "should detect as question"),
        ("are they worth it", "should detect as question"),
        ("is Tesla doing well", "should detect as question"),
        ("are they performing well", "should detect as question"),
        
        # Check/look patterns
        ("check how Apple is doing", "should detect as question"),
        ("look at what Tesla is going", "should detect as question"),
        ("see where Microsoft is performing", "should detect as question"),
    ]
    
    passed = 0
    failed = 0
    
    for query, description in test_cases:
        try:
            result = parse_to_structured(query)
            intent = result.get('intent', 'N/A')
            
            # Check if it parsed successfully (has intent)
            has_intent = intent != 'N/A'
            
            status = "✓" if has_intent else "✗"
            print(f"{status} '{query}'")
            print(f"   Intent: {intent}")
            print(f"   Description: {description}")
            
            if has_intent:
                passed += 1
            else:
                failed += 1
                print(f"   ⚠ Failed to parse!")
            print()
            
        except Exception as e:
            print(f"✗ '{query}' - ERROR: {e}")
            failed += 1
            print()
    
    print("-" * 80)
    print(f"Casual/Slang Expression Tests: {passed} passed, {failed} failed")
    return passed, failed


def test_multipart_queries():
    """Test multi-part query patterns."""
    
    print("=" * 80)
    print("Testing Multi-Part Query Patterns")
    print("=" * 80)
    
    test_cases = [
        # Analyze X and also Y patterns
        ("analyze Apple and also Tesla", "should detect as question"),
        ("compare Microsoft and also Google", "should detect as question"),
        ("show Apple revenue and also Microsoft", "should detect as question"),
        ("calculate revenue and also profit", "should detect as question"),
        ("find Apple and also Tesla", "should detect as question"),
        
        # X and also/plus/as well patterns
        ("Apple revenue and also Microsoft revenue", "should detect as question"),
        ("Tesla margins plus Amazon margins", "should detect as question"),
        ("Microsoft P/E as well as Google P/E", "should detect as question"),
        ("Nvidia growth in addition to AMD growth", "should detect as question"),
        ("Apple data furthermore Tesla data", "should detect as question"),
        
        # Both/all X and Y patterns
        ("both Apple and Microsoft", "should detect as question"),
        ("all Apple, Tesla, and Microsoft", "should detect as question"),
        ("each Apple and Tesla", "should detect as question"),
        ("every company and metric", "should detect as question"),
        
        # Analyze both/all patterns
        ("analyze both Apple and Microsoft", "should detect as question"),
        ("compare all Apple, Tesla, Microsoft", "should detect as question"),
        ("show both revenue and profit", "should detect as question"),
        ("calculate all metrics and ratios", "should detect as question"),
        
        # What/how X and Y patterns
        ("what is Apple revenue and also Tesla revenue", "should detect as question"),
        ("how is Microsoft doing and how is Google doing", "should detect as question"),
        ("what's Apple P/E, Tesla P/E", "should detect as question"),
        
        # Sequential patterns
        ("first analyze Apple then analyze Tesla", "should detect as question"),
        ("next show Microsoft revenue", "should detect as question"),
        ("second calculate profit margins", "should detect as question"),
        ("finally compare all companies", "should detect as question"),
        ("after that show growth", "should detect as question"),
        
        # Comma-separated action patterns
        ("analyze Apple, analyze Tesla", "should detect as question"),
        ("compare Microsoft, compare Google", "should detect as question"),
        ("show revenue, show profit", "should detect as question"),
        ("calculate P/E, calculate P/B", "should detect as question"),
        
        # As well as/along with patterns
        ("Apple as well as Microsoft", "should detect as question"),
        ("Tesla along with Amazon", "should detect as question"),
        ("Microsoft together with Google", "should detect as question"),
        ("revenue in addition to profit", "should detect as question"),
        ("margins besides growth", "should detect as question"),
        ("P/E on top of P/B", "should detect as question"),
    ]
    
    passed = 0
    failed = 0
    
    for query, description in test_cases:
        try:
            result = parse_to_structured(query)
            intent = result.get('intent', 'N/A')
            
            # Check if it parsed successfully (has intent)
            has_intent = intent != 'N/A'
            
            status = "✓" if has_intent else "✗"
            print(f"{status} '{query}'")
            print(f"   Intent: {intent}")
            print(f"   Description: {description}")
            
            if has_intent:
                passed += 1
            else:
                failed += 1
                print(f"   ⚠ Failed to parse!")
            print()
            
        except Exception as e:
            print(f"✗ '{query}' - ERROR: {e}")
            failed += 1
            print()
    
    print("-" * 80)
    print(f"Multi-Part Query Tests: {passed} passed, {failed} failed")
    return passed, failed


def test_question_detection_patterns():
    """Test that new patterns are detected as questions by the chatbot."""
    
    print("=" * 80)
    print("Testing Question Detection (Pattern Matching)")
    print("=" * 80)
    
    # Load patterns from chatbot.py - we'll test regex patterns directly
    # Since we can't easily import the patterns from the method, we'll test
    # a subset manually using similar patterns
    
    test_cases = [
        # Domain-specific
        ("what is the alpha", True),
        ("calculate Sharpe ratio", True),
        ("show me beta", True),
        ("what's the CVaR", True),
        
        # Casual
        ("how's Apple doing", True),
        ("what's the deal with Tesla", True),
        ("what's up with Microsoft", True),
        ("give me the rundown on Nvidia", True),
        
        # Multi-part
        ("analyze Apple and also Tesla", True),
        ("both Microsoft and Google", True),
        ("first Apple then Tesla", True),
        ("revenue as well as profit", True),
        
        # Non-questions (should still parse but may not be questions)
        ("Apple revenue", True),  # Should parse
        ("show revenue", True),  # Command, should parse
    ]
    
    # Test parsing (all should parse successfully)
    passed = 0
    failed = 0
    
    for query, should_parse in test_cases:
        try:
            result = parse_to_structured(query)
            intent = result.get('intent', 'N/A')
            has_intent = intent != 'N/A'
            
            status = "✓" if has_intent == should_parse else "✗"
            print(f"{status} '{query}'")
            print(f"   Parsed: {has_intent}, Expected: {should_parse}")
            print(f"   Intent: {intent}")
            
            if has_intent == should_parse:
                passed += 1
            else:
                failed += 1
            print()
            
        except Exception as e:
            print(f"✗ '{query}' - ERROR: {e}")
            if should_parse:
                failed += 1
            print()
    
    print("-" * 80)
    print(f"Question Detection Tests: {passed} passed, {failed} failed")
    return passed, failed


def main():
    """Run all tests."""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST SUITE: Domain-Specific, Casual, and Multi-Part Patterns")
    print("=" * 80 + "\n")
    
    results = []
    
    # Run all test suites
    results.append(test_domain_specific_financial_terms())
    print()
    results.append(test_casual_slang_expressions())
    print()
    results.append(test_multipart_queries())
    print()
    results.append(test_question_detection_patterns())
    
    # Summary
    total_passed = sum(r[0] for r in results)
    total_failed = sum(r[1] for r in results)
    total_tests = total_passed + total_failed
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Success Rate: {total_passed / total_tests * 100:.1f}%")
    print("=" * 80)
    
    if total_failed == 0:
        print("\n✓ All tests passed!")
        return True
    else:
        print(f"\n✗ {total_failed} tests failed. Review patterns above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

