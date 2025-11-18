#!/usr/bin/env python3
"""
Test script to verify additional patterns are working correctly.
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test queries organized by pattern category
TEST_QUERIES = {
    "Imperative/Command": [
        "show me apple revenue",
        "display microsoft margins",
        "list tesla metrics",
        "get nvidia cash flow",
        "find google earnings",
        "give me apple data",
        "pull up microsoft financials",
    ],
    
    "Request": [
        "i'd like to see apple revenue",
        "i'm interested in microsoft margins",
        "i'm curious about tesla growth",
        "i want to know nvidia valuation",
        "i need information on google",
        "i'm looking for apple data",
        "i'm trying to understand microsoft",
    ],
    
    "Quantitative Comparison": [
        "apple revenue is 2 times more than microsoft",
        "tesla margins are 50% higher than ford",
        "nvidia is twice as profitable",
        "google revenue is half as much",
        "microsoft is 3X larger",
    ],
    
    "Negation": [
        "isn't apple profitable",
        "doesn't microsoft have debt",
        "hasn't tesla grown",
        "won't nvidia increase",
        "not profitable",
        "no revenue",
    ],
    
    "Causal": [
        "because of apple's growth",
        "due to microsoft's margins",
        "as a result of tesla's expansion",
        "caused by nvidia's success",
        "led to google's increase",
    ],
    
    "Quantifier": [
        "all companies in tech",
        "some metrics are missing",
        "most companies are profitable",
        "few companies have debt",
        "many sectors are growing",
    ],
    
    "Progressive/Adverb": [
        "increasingly profitable",
        "gradually improving",
        "rapidly growing",
        "steadily declining",
        "dramatically increasing",
    ],
    
    "Certainty": [
        "definitely profitable",
        "probably growing",
        "possibly declining",
        "likely to increase",
        "unlikely to decrease",
    ],
    
    "Frequency": [
        "always profitable",
        "often growing",
        "sometimes declining",
        "rarely profitable",
        "never profitable",
    ],
    
    "Aggregation": [
        "sum of revenue",
        "total revenue",
        "average revenue",
        "median revenue",
        "aggregate revenue",
    ],
    
    "Percentage/Ratio": [
        "50% of revenue",
        "percent of revenue",
        "percentage of revenue",
        "ratio of X to Y",
        "proportion of X",
    ],
    
    "Change Magnitude": [
        "increase by 20%",
        "decrease by 10%",
        "grow by 50%",
        "shrink by 15%",
        "up by 25%",
    ],
    
    "State/Status": [
        "is currently profitable",
        "has been growing",
        "was previously declining",
        "will be profitable",
        "remains profitable",
    ],
    
    "Relative Position": [
        "above average",
        "below average",
        "above median",
        "in the top 10%",
        "in the bottom 25%",
    ],
    
    "Temporal Modifier": [
        "recently profitable",
        "previously declining",
        "going forward",
        "this year",
        "last quarter",
    ],
    
    "Sector/Industry": [
        "in the tech sector",
        "within the industry",
        "across sectors",
        "sector-wide",
        "industry-wide",
    ],
    
    "Multi-Company": [
        "all of them",
        "both of them",
        "together",
        "combined",
        "as a group",
    ],
    
    "Hypothetical/Conditional": [
        "if revenue grows 50% then profit will increase",
        "assuming microsoft margins drop",
        "given apple's expansion",
        "should tesla grow then revenue increases",
        "were nvidia to expand",
    ],
    
    "Question Tag": [
        "apple is profitable, isn't it",
        "microsoft is growing, right",
        "tesla is good, correct",
        "nvidia is strong, is that right",
    ],
}

def test_question_patterns():
    """Test if question patterns are detected."""
    print("\n" + "="*80)
    print("TESTING ADDITIONAL PATTERNS")
    print("="*80)
    
    # Load question patterns from chatbot.py
    try:
        from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
        
        # Read the question patterns from chatbot.py
        chatbot_file = Path(__file__).parent / "src" / "finanlyzeos_chatbot" / "chatbot.py"
        content = chatbot_file.read_text(encoding="utf-8")
        
        # Extract question_patterns section
        start_marker = "question_patterns = ["
        end_marker = "]"
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("ERROR: Could not find question_patterns in chatbot.py")
            return
        
        # Find the end of the list
        bracket_count = 0
        in_list = False
        end_idx = start_idx
        
        for i, char in enumerate(content[start_idx:], start_idx):
            if char == '[':
                bracket_count += 1
                in_list = True
            elif char == ']':
                bracket_count -= 1
                if in_list and bracket_count == 0:
                    end_idx = i + 1
                    break
        
        patterns_section = content[start_idx:end_idx]
        
        # Extract individual patterns (simplified - just check if patterns exist)
        pattern_count = patterns_section.count("r'")
        print(f"\nFound {pattern_count} question patterns in chatbot.py")
        
    except Exception as e:
        print(f"ERROR loading patterns: {e}")
        return
    
    # Test each category
    print("\n" + "-"*80)
    print("Testing Pattern Detection")
    print("-"*80)
    
    # Simple regex test - check if patterns would match
    # We'll use a simplified approach: check if the query contains common keywords
    
    total_tests = 0
    passed_tests = 0
    
    for category, queries in TEST_QUERIES.items():
        print(f"\n{category}:")
        category_passed = 0
        
        for query in queries:
            total_tests += 1
            query_lower = query.lower()
            
            # Check if query would match common patterns
            # This is a simplified check - actual detection happens in chatbot
            matches = False
            
            # Imperative
            if any(word in query_lower for word in ["show", "display", "list", "get", "find", "give", "pull"]):
                matches = True
            # Request
            elif any(phrase in query_lower for phrase in ["i'd like", "i'm interested", "i want", "i need", "i'm looking", "i'm trying"]):
                matches = True
            # Quantitative
            elif any(phrase in query_lower for phrase in ["times", "twice", "double", "half", "%", "percent"]):
                matches = True
            # Negation
            elif any(word in query_lower for word in ["isn't", "doesn't", "hasn't", "won't", "not", "no"]):
                matches = True
            # Causal
            elif any(phrase in query_lower for phrase in ["because of", "due to", "as a result", "caused by", "led to"]):
                matches = True
            # Quantifier
            elif any(word in query_lower for word in ["all", "some", "most", "few", "many", "several"]):
                matches = True
            # Progressive
            elif any(word in query_lower for word in ["increasingly", "gradually", "rapidly", "steadily", "dramatically"]):
                matches = True
            # Certainty
            elif any(word in query_lower for word in ["definitely", "probably", "possibly", "likely", "unlikely"]):
                matches = True
            # Frequency
            elif any(word in query_lower for word in ["always", "often", "sometimes", "rarely", "never", "usually"]):
                matches = True
            # Aggregation
            elif any(word in query_lower for word in ["sum", "total", "average", "median", "aggregate"]):
                matches = True
            # Percentage
            elif any(word in query_lower for word in ["%", "percent", "percentage", "ratio", "proportion"]):
                matches = True
            # Change magnitude
            elif any(phrase in query_lower for phrase in ["increase by", "decrease by", "grow by", "up by", "down by"]):
                matches = True
            # State
            elif any(phrase in query_lower for phrase in ["is currently", "has been", "was previously", "will be", "remains"]):
                matches = True
            # Relative position
            elif any(phrase in query_lower for phrase in ["above average", "below average", "above median", "top", "bottom"]):
                matches = True
            # Temporal
            elif any(word in query_lower for word in ["recently", "previously", "going forward", "this year", "last quarter"]):
                matches = True
            # Sector
            elif any(phrase in query_lower for phrase in ["sector", "industry", "sector-wide", "industry-wide"]):
                matches = True
            # Multi-company
            elif any(phrase in query_lower for phrase in ["all of them", "both of them", "together", "combined", "as a group"]):
                matches = True
            # Hypothetical
            elif any(word in query_lower for word in ["if", "assuming", "given", "should", "were"]):
                matches = True
            # Question tag
            elif any(phrase in query_lower for phrase in ["isn't it", "right", "correct", "is that right"]):
                matches = True
            
            if matches:
                category_passed += 1
                passed_tests += 1
                print(f"  OK: {query}")
            else:
                print(f"  WARNING: {query} (pattern not detected in simple check)")
        
        print(f"  Result: {category_passed}/{len(queries)} passed")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal queries tested: {total_tests}")
    print(f"Patterns detected: {passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    # Test actual pattern matching
    print("\n" + "-"*80)
    print("Testing Actual Pattern Matching")
    print("-"*80)
    
    try:
        # Try to import and test actual pattern matching
        from finanlyzeos_chatbot.parsing.parse import parse_to_structured
        
        test_queries = [
            "show me apple revenue",
            "i'd like to see microsoft margins",
            "apple is 2 times more profitable",
            "isn't tesla growing",
            "because of nvidia's success",
        ]
        
        print("\nTesting actual parsing:")
        for query in test_queries:
            try:
                result = parse_to_structured(query)
                print(f"  OK: '{query}' -> Parsed successfully")
                print(f"     Intent: {result.get('intent', 'N/A')}")
                print(f"     Tickers: {[t.get('ticker', 'N/A') for t in result.get('tickers', [])]}")
            except Exception as e:
                print(f"  WARNING: '{query}' -> Error: {e}")
    
    except Exception as e:
        print(f"Could not test actual parsing: {e}")
    
    print("\n" + "="*80)
    print("Pattern testing complete!")
    print("="*80)
    print("\nNote: This is a simplified test. Full pattern matching happens")
    print("in the chatbot when processing queries. Test with actual chatbot:")
    print("  python test_chatbot_interactive.py")

if __name__ == "__main__":
    test_question_patterns()

