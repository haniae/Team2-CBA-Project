"""
Test script to see exactly what the chatbot is doing with questions.
This will help diagnose why it's not answering like ChatGPT.
"""

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings


def test_question_understanding():
    """Test how the chatbot handles natural language questions."""
    
    print("=" * 80)
    print("TESTING CHATBOT QUESTION UNDERSTANDING")
    print("=" * 80)
    print()
    
    # Load chatbot
    settings = load_settings()
    print(f"1. Configuration:")
    print(f"   - LLM Provider: {settings.llm_provider}")
    print(f"   - Model: {settings.openai_model}")
    print(f"   - Enhanced Routing: {settings.enable_enhanced_routing}")
    print(f"   - Conversational Mode: {settings.prefer_conversational_mode}")
    print()
    
    chatbot = BenchmarkOSChatbot.create(settings)
    
    # Test questions
    test_cases = [
        {
            "question": "What is Apple's revenue?",
            "expected": "Should give conversational answer with revenue value, growth, and sources"
        },
        {
            "question": "Why is Tesla's margin declining?",
            "expected": "Should explain multiple factors conversationally"
        },
        {
            "question": "Is Microsoft more profitable than Apple?",
            "expected": "Should compare with conversational explanation"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['question']}")
        print(f"Expected: {test['expected']}")
        print("=" * 80)
        print()
        
        try:
            response = chatbot.ask(test['question'])
            
            print("RESPONSE:")
            print("-" * 80)
            # Handle unicode for Windows console
            try:
                print(response)
            except UnicodeEncodeError:
                print(response.encode('ascii', 'replace').decode('ascii'))
            print("-" * 80)
            print()
            
            # Check response quality
            print("QUALITY CHECKS:")
            checks = {
                "Has conversational tone": not any(word in response[:200].lower() for word in ["trailing twelve months", "represents a", "per 10-k filed"]),
                "Uses bold formatting": "**" in response,
                "Has section headers": any(h in response for h in ["**What", "**Why", "**How", "**The ", "**Looking"]),
                "Has markdown links": "](" in response and "sec.gov" in response.lower(),
                "Not just data dump": len(response.split('\n\n')) >= 3,  # Multiple paragraphs
                "Answers question directly": True,  # Would need NLP to really check
            }
            
            for check, passed in checks.items():
                status = "[PASS]" if passed else "[FAIL]"
                print(f"  {status} {check}")
            
            # Check routing info
            print()
            print("ROUTING INFO:")
            structured = chatbot.last_structured_response
            if structured:
                print(f"  - Parser intent: {structured.get('parser', {}).get('intent', 'N/A')}")
                print(f"  - Dashboard built: {structured.get('dashboard') is not None}")
                if 'enhanced_routing' in structured:
                    print(f"  - Enhanced intent: {structured['enhanced_routing'].get('intent', 'N/A')}")
                    print(f"  - Confidence: {structured['enhanced_routing'].get('confidence', 'N/A')}")
            
            passed_checks = sum(checks.values())
            total_checks = len(checks)
            
            print()
            print(f"RESULT: {passed_checks}/{total_checks} checks passed")
            
            if passed_checks < 4:
                print()
                print("[WARNING] Response quality is low")
                print("This might indicate:")
                print("  1. LLM is not being invoked (going straight to structured handler)")
                print("  2. System prompt not being followed")
                print("  3. LLM model quality is insufficient")
                print("  4. Context not being provided properly")
            
        except Exception as e:
            print(f"[ERROR]: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        input("Press Enter to continue to next test...")
    
    print()
    print("=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_question_understanding()

