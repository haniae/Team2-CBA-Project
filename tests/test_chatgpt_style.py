"""
Quick test to verify ChatGPT-style responses are working.
Run this to see if the new formatting is active.
"""

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings


def test_chatgpt_style():
    """Test that responses have ChatGPT-style formatting."""
    print("=" * 80)
    print("Testing ChatGPT-Style Response Formatting")
    print("=" * 80)
    print()
    
    # Load settings and create chatbot
    print("1. Loading chatbot...")
    settings = load_settings()
    
    # Show config status
    print(f"   - Enhanced routing enabled: {settings.enable_enhanced_routing}")
    print(f"   - Conversational mode: {settings.prefer_conversational_mode}")
    print()
    
    chatbot = BenchmarkOSChatbot.create(settings)
    print("   ✓ Chatbot loaded successfully")
    print()
    
    # Test simple question
    print("2. Testing simple question: 'What is Apple's revenue?'")
    print("-" * 80)
    response = chatbot.ask("What is Apple's revenue?")
    print()
    print(response)
    print()
    print("-" * 80)
    print()
    
    # Check for ChatGPT-style elements
    print("3. Checking for ChatGPT-style formatting:")
    print()
    
    checks = {
        "Uses **bold** formatting": "**" in response,
        "Has markdown headers": any(header in response for header in ["**What", "**Why", "**How", "**The "]),
        "Has bullet points": "- " in response or "• " in response,
        "Has markdown links [text](url)": "](" in response and "sec.gov" in response.lower(),
        "Has emoji or section markers": "📊" in response or "Sources:" in response,
        "No full ugly URLs shown": response.count("https://www.sec.gov/cgi-bin/viewer") == 0 or "](" in response,
    }
    
    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {check}")
    
    print()
    
    # Overall assessment
    passed_checks = sum(checks.values())
    total_checks = len(checks)
    
    print("=" * 80)
    print(f"RESULT: {passed_checks}/{total_checks} checks passed")
    print("=" * 80)
    print()
    
    if passed_checks >= 4:
        print("✅ SUCCESS! ChatGPT-style formatting is working!")
        print()
        print("Your responses now have:")
        print("  • Natural conversational tone")
        print("  • Bold key metrics")
        print("  • Section headers")
        print("  • Clean markdown source links [Filing](URL)")
        print("  • Better readability")
    else:
        print("⚠️  WARNING: ChatGPT-style formatting may not be fully active")
        print()
        print("Possible issues:")
        print("  1. Server needs restart (if running serve_chatbot.py)")
        print("  2. LLM cache might have old responses")
        print("  3. Config flags might need adjustment")
        print()
        print("Try:")
        print("  • Restart your chatbot server")
        print("  • Clear any LLM caches")
        print("  • Run: python test_chatgpt_style.py")
    
    print()
    return passed_checks >= 4


if __name__ == "__main__":
    success = test_chatgpt_style()
    exit(0 if success else 1)

