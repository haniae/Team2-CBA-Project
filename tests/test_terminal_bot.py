#!/usr/bin/env python3
"""Test the chatbot directly in terminal to verify backend logic."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import FinanlyzeOSChatbot, load_settings

def main():
    """Run chatbot in terminal with test queries."""
    print("=" * 80)
    print("BenchmarkOS Chatbot - Terminal Test")
    print("=" * 80)
    print()
    
    # Create chatbot instance
    settings = load_settings()
    bot = FinanlyzeOSChatbot.create(settings)
    
    # Test queries
    test_queries = [
        "What's Amazon trading at?",
        "What's Microsoft's sales figures?",
        "How profitable is Microsoft?",
        "How fast is Microsoft growing?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print("=" * 80)
        
        # Track progress events
        progress_events = []
        def progress_callback(stage, detail):
            progress_events.append(f"{stage}: {detail}")
        
        # Ask the question
        try:
            reply = bot.ask(query, progress_callback=progress_callback)
            
            # Check dashboard status
            dashboard = bot.last_structured_response.get("dashboard")
            
            print(f"\n📊 Dashboard Status: {dashboard}")
            print(f"\n💬 Reply Preview (first 300 chars):")
            print("-" * 80)
            print(reply[:300] + "..." if len(reply) > 300 else reply)
            print("-" * 80)
            
            print(f"\n🔍 Progress Events:")
            for event in progress_events[-10:]:
                print(f"  • {event}")
            
            # Verify
            if dashboard is None:
                print(f"\n✅ PASS: Dashboard is None (correct for question)")
            else:
                print(f"\n❌ FAIL: Dashboard is not None (should be None for questions)")
                print(f"   Dashboard: {dashboard}")
            
            # Check if reply mentions correct company
            query_lower = query.lower()
            if "amazon" in query_lower:
                if "amazon" in reply.lower() or "amzn" in reply.lower():
                    print(f"✅ PASS: Reply mentions Amazon (correct company)")
                else:
                    print(f"❌ FAIL: Reply doesn't mention Amazon")
            elif "microsoft" in query_lower:
                if "microsoft" in reply.lower() or "msft" in reply.lower():
                    print(f"✅ PASS: Reply mentions Microsoft (correct company)")
                else:
                    print(f"❌ FAIL: Reply doesn't mention Microsoft")
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Terminal Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()

