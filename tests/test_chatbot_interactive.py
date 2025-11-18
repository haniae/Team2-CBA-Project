#!/usr/bin/env python3
"""
Interactive test script - test queries one by one and see responses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def interactive_test():
    """Interactive testing mode."""
    print("\n" + "="*80)
    print("INTERACTIVE CHATBOT TESTING")
    print("="*80)
    print("\nType queries to test. Commands:")
    print("  'quit' or 'exit' - Exit")
    print("  'test' - Run predefined test queries")
    print("  'help' - Show help")
    print()
    
    try:
        from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
        from finanlyzeos_chatbot.config import Settings
        
        print("Initializing chatbot...")
        settings = Settings()
        chatbot = FinanlyzeOSChatbot.create(settings)
        print("OK: Chatbot ready!\n")
        
    except Exception as e:
        print(f"ERROR: Failed to initialize chatbot: {e}")
        return
    
    # Predefined test queries
    test_queries = [
        "apple revenue",
        "microsft revenu",
        "how's apple doing",
        "apple vs microsoft",
        "why did tesla margins drop",
        "forecast nvidia revenue",
        "what's the weather",
        "what is revenue",
    ]
    
    test_index = 0
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if query.lower() == 'test':
                if test_index < len(test_queries):
                    query = test_queries[test_index]
                    print(f"\n[Test Query {test_index + 1}/{len(test_queries)}]")
                    test_index += 1
                else:
                    print("All test queries completed. Resetting...")
                    test_index = 0
                    continue
            
            if query.lower() == 'help':
                print("\nCommands:")
                print("  'test' - Run next predefined test query")
                print("  'quit' - Exit")
                print("\nOr just type your query!")
                continue
            
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print(f"{'='*80}\n")
            print("Processing...")
            
            response = chatbot.ask(query)
            
            print(f"\n{'='*80}")
            print("Response:")
            print(f"{'='*80}\n")
            print(response)
            print(f"\n{'='*80}")
            print(f"Response length: {len(response)} characters")
            print(f"{'='*80}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    interactive_test()

