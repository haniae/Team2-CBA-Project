"""Test that the improved question patterns work correctly."""

import re

# The updated patterns
question_patterns = [
    r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would)\b',
    r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would)\b',
    r'\bwhy\b',
    r'\bexplain\b',
    r'\btell\s+me\s+(?:about|why|how)\b',
    r'\bis\s+\w+\s+(?:more|less|better|worse|higher|lower)',
    r'\bwhich\s+(?:company|stock|one|is)\b',
    r'\bcan\s+you\b',
    r'\bdoes\s+\w+\s+have\b',
    r'\bshould\s+i\b',
    r'\bwhen\s+(?:is|are|was|were|did|will)\b',
    r'\bwhere\s+(?:is|are|can|do)\b',
]

# Test cases
test_queries = [
    ("How has Apple's revenue changed over time?", True, "User's exact query"),
    ("What is Apple's revenue?", True, "Simple what question"),
    ("How much did Microsoft earn?", True, "How much question"),
    ("Why is Tesla profitable?", True, "Why question"),
    ("Show Apple KPIs", False, "Explicit table request"),
    ("AAPL", False, "Bare ticker"),
    ("Dashboard AAPL", False, "Dashboard request"),
    ("Compare AAPL MSFT", False, "Legacy compare"),
    ("Is Amazon more profitable than Google?", True, "Comparison question"),
    ("What are the key metrics for NVDA?", True, "What are question"),
    ("How will Intel perform?", True, "Future question"),
    ("When did Ford report earnings?", True, "When question"),
    ("Where can I find Tesla's financials?", True, "Where question"),
]

print("=" * 80)
print("QUESTION DETECTION TEST - IMPROVED PATTERNS")
print("=" * 80)
print()

passed = 0
failed = 0

for query, expected_is_question, description in test_queries:
    lowered = query.lower()
    is_question = any(re.search(pattern, lowered) for pattern in question_patterns)
    
    status = "[PASS]" if is_question == expected_is_question else "[FAIL]"
    result = "QUESTION" if is_question else "NOT QUESTION"
    expected = "QUESTION" if expected_is_question else "NOT QUESTION"
    
    if is_question == expected_is_question:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} {description}")
    print(f"      Query: '{query}'")
    print(f"      Detected as: {result} (expected: {expected})")
    print()

print("=" * 80)
print(f"RESULTS: {passed}/{passed+failed} tests passed")
print("=" * 80)

if failed > 0:
    print(f"\n[WARNING] {failed} test(s) failed!")
else:
    print("\n[SUCCESS] All question patterns working correctly!")

