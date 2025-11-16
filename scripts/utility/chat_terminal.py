#!/usr/bin/env python3
"""Interactive terminal chatbot interface."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import FinanlyzeOSChatbot, load_settings

def main():
    """Run interactive chatbot in terminal."""
    print("=" * 80)
    print("BenchmarkOS Chatbot - Terminal Mode")
    print("=" * 80)
    print()
    print("Loading chatbot...")
    
    # Create chatbot instance
    settings = load_settings()
    bot = FinanlyzeOSChatbot.create(settings)
    
    print("✅ Chatbot ready!")
    print()
    print("Type your questions below. Type 'quit' or 'exit' to quit.")
    print("=" * 80)
    print()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Show progress
            def progress_callback(stage, detail):
                if stage in ['start', 'intent_question', 'llm_query_start', 'llm_query_complete', 'complete']:
                    print(f"  📍 {detail}")
            
            print("\n🤖 BenchmarkOS:")
            print("-" * 80)
            
            # Get reply
            reply = bot.ask(user_input, progress_callback=progress_callback)
            
            # Show reply
            print(reply)
            print("-" * 80)
            
            # Show dashboard status (for debugging)
            dashboard = bot.last_structured_response.get("dashboard")
            if dashboard:
                print(f"\n⚠️  Dashboard: {dashboard.get('kind', 'unknown')} - {dashboard.get('ticker', 'no ticker')}")
            else:
                print(f"\n✅ Dashboard: None (correct for questions)")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

