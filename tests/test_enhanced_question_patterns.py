"""Quick test for enhanced question pattern detection."""

import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_question_patterns():
    """Test that new question patterns are detected correctly."""
    
    # Patterns from chatbot.py (the new enhanced patterns)
    question_patterns = [
        # Basic question starters (expanded)
        r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would|about|does|did)\b',
        r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would|about|to|do|did)\b',
        r'\bwhy\b',
        r'\bexplain\b',
        r'\btell\s+me\s+(?:about|why|how)\b',
        r'\bis\s+\w+\s+(?:more|less|better|worse|higher|lower)',
        r'\bwhich\s+(?:company|stock|one|is|has|have)\b',  # "which has", "which have"
        r'\bcan\s+you\b',
        r'\bdoes\s+\w+\s+have\b',
        r'\bshould\s+i\b',
        r'\bwhen\s+(?:is|are|was|were|did|will)\b',
        r'\bwhere\s+(?:is|are|can|do)\b',
        
        # Polite request patterns
        r'\b(?:tell|show|give)\s+me\s+(?:about|why|how|what)',
        r'\b(?:please|can you|would you)\s+(?:show|tell|explain|help)',
        r'\b(?:can|could|would)\s+you\s+(?:tell|explain|show|help)',
        
        # Implicit question patterns
        r'\b(?:i\s+)?(?:want|need|would like)\s+to\s+know',
        r'\b(?:is|are|was|were)\s+(?:there|it)\s+(?:any|a|an)',
        r'\b(?:i wonder|i\'m curious|interesting|wondering)',
        r'\b(?:help me|guide me|assist me)',
        
        # Change/improvement queries
        r'\b(?:what|which|who)\s+(?:happened|changed|improved|declined|increased|decreased)',
        r'\b(?:why|how)\s+(?:did|does|do|has|have|was|were|is|are)',
        
        # Recommendation/suggestion patterns
        r'\b(?:should|would|could)\s+(?:i|we|they)',
        
        # Comparison variations
        r'\b(?:better|worse|more|less|higher|lower|stronger|weaker)\s+(?:than|compared)',
        r'\b(?:similar|different|same|alike)\s+(?:to|as|from)',
        
        # Follow-up question patterns
        r'^\s*(?:what|how)\s+about\b',
        r'\b(?:their|its|theirs|it|they)\b',
        r'\b(?:them|it|those|these|that|this)\s+(?:compare|versus|vs|against)',
        r'\bcompare\s+(?:them|those|these|that|this|it)\b',
    ]
    
    # Test queries that should be detected as questions
    test_queries = [
        # Polite requests
        ("Please show me Apple's revenue", True),
        ("Can you tell me about Tesla's margins?", True),
        ("Would you help me understand Microsoft's P/E ratio?", True),
        ("Could you explain Apple's growth?", True),
        
        # Implicit questions
        ("I want to know why Apple's margin decreased", True),
        ("I'm curious about Tesla's growth", True),
        ("Help me understand Microsoft's valuation", True),
        ("Need to know Amazon's revenue", True),
        
        # Change queries
        ("What changed in Apple's revenue?", True),
        ("Which improved more: Tesla or Microsoft?", True),
        ("How did Amazon's margins decline?", True),
        ("Why did Microsoft's revenue increase?", True),
        
        # Recommendation queries
        ("Should I invest in Tesla?", True),
        ("Would they be a good investment?", True),
        ("Could we compare Apple and Microsoft?", True),
        
        # Comparison queries
        ("Is Apple better than Microsoft?", True),
        ("Which has higher margins?", True),
        ("Are they similar to each other?", True),
        
        # Basic questions (should still work)
        ("What is Apple's revenue?", True),
        ("How much did Tesla make?", True),
        ("Why did Microsoft's margin decrease?", True),
        ("Explain Tesla's growth", True),
        
        # Non-questions (should NOT be detected)
        ("Show me Apple's revenue", False),
        ("Apple revenue", False),
        ("Compare Apple and Microsoft", False),  # This is a command, not a question
    ]
    
    print("=" * 80)
    print("Testing Enhanced Question Pattern Detection")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, should_be_question in test_queries:
        lowered = query.lower()
        is_question = any(re.search(pattern, lowered) for pattern in question_patterns)
        
        status = "✓" if is_question == should_be_question else "✗"
        result = "PASS" if is_question == should_be_question else "FAIL"
        
        print(f"{status} {result}: '{query}'")
        print(f"   Expected: {'Question' if should_be_question else 'Not a question'}")
        print(f"   Detected: {'Question' if is_question else 'Not a question'}")
        
        if is_question == should_be_question:
            passed += 1
        else:
            failed += 1
            print(f"   ⚠ Pattern mismatch!")
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_queries)} tests")
    print(f"Success Rate: {passed / len(test_queries) * 100:.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print(f"✗ {failed} tests failed. Review patterns above.")
        return False

if __name__ == "__main__":
    success = test_question_patterns()
    sys.exit(0 if success else 1)

