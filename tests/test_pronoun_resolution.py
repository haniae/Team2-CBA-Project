"""Test suite for pronoun resolution (Step 4)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmarkos_chatbot import BenchmarkOSChatbot, load_settings

def test_pronoun_resolution():
    """Test that pronouns are resolved to last mentioned tickers."""
    
    print("=" * 80)
    print("Testing Pronoun Resolution (Step 4)")
    print("=" * 80)
    print()
    
    # Create chatbot instance
    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)
    
    test_scenarios = [
        {
            "name": "Singular pronoun (it)",
            "queries": [
                ("Tell me about Apple", "Apple"),
                ("What about it?", "AAPL"),  # "it" should resolve to Apple
            ]
        },
        {
            "name": "Singular pronoun (that)",
            "queries": [
                ("Show me Microsoft data", "Microsoft"),
                ("How's that doing?", "MSFT"),  # "that" should resolve to Microsoft
            ]
        },
        {
            "name": "Plural pronoun (them)",
            "queries": [
                ("Compare Apple and Microsoft", "Apple.*Microsoft|Microsoft.*Apple"),
                ("What about them?", "AAPL.*MSFT|MSFT.*AAPL"),  # "them" should resolve to both
            ]
        },
        {
            "name": "Possessive pronoun (its)",
            "queries": [
                ("What's Tesla's revenue?", "Tesla"),
                ("Show me its growth", "TSLA"),  # "its" should resolve to Tesla
            ]
        },
    ]
    
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario['name']}")
        print('='*80)
        
        # Reset bot for each scenario
        bot = BenchmarkOSChatbot.create(settings)
        
        for i, (query, expected_pattern) in enumerate(scenario['queries'], 1):
            print(f"\nQuery {i}: {query}")
            
            # Resolve pronouns
            resolved = bot._resolve_pronouns(query)
            print(f"Resolved: {resolved}")
            
            # Update tickers after first query
            if i == 1:
                bot._update_mentioned_tickers(query)
                print(f"Last mentioned tickers: {bot._last_mentioned_tickers}")
            
            # Check resolution for second query
            if i == 2:
                import re
                if re.search(expected_pattern, resolved, re.IGNORECASE):
                    print(f"✅ PASS: Pronoun correctly resolved")
                    passed += 1
                else:
                    print(f"❌ FAIL: Expected pattern '{expected_pattern}' not found in '{resolved}'")
                    failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_scenarios)} scenarios")
    print(f"Success Rate: {passed / len(test_scenarios) * 100:.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print(f"✗ {failed} tests failed.")
        return False

if __name__ == "__main__":
    success = test_pronoun_resolution()
    sys.exit(0 if success else 1)

