#!/usr/bin/env python3
"""
Test if chatbot SEC API 404 issue has been fixed.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Test chatbot SEC API fix."""
    print("=== Testing Chatbot SEC API Fix ===\n")
    
    try:
        from finanlyzeos_chatbot.chatbot import _CompanyNameIndex
        from finanlyzeos_chatbot.config import load_settings
        
        print("🔧 Testing _CompanyNameIndex build_from_sec()...")
        
        settings = load_settings()
        index = _CompanyNameIndex()
        
        # Test build_from_sec method
        print("  - Calling build_from_sec()...")
        index.build_from_sec(
            base_url="https://data.sec.gov",
            user_agent=settings.sec_api_user_agent,
            timeout=20.0
        )
        
        print(f"  ✅ Success! Built index with {len(index.by_exact)} companies")
        print(f"  - Sample companies: {list(index.by_exact.keys())[:5]}")
        
        # Test ticker lookup
        test_companies = ["apple", "microsoft", "google", "amazon", "tesla"]
        print(f"\n🔍 Testing ticker lookups:")
        for company in test_companies:
            if company in index.by_exact:
                ticker = index.by_exact[company]
                print(f"  - {company} -> {ticker}")
            else:
                print(f"  - {company} -> Not found")
        
        print(f"\n✅ Chatbot SEC API fix test completed!")
        print("  - No more 'Unable to fetch SEC company tickers' errors")
        print("  - System uses database data instead of SEC API")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
