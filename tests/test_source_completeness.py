"""
Comprehensive Source Completeness Test
Shows URLs, Formulas, and Market Data attribution
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
import json

def test_company(ticker="AAPL", company_name="Apple Inc."):
    print(f"\n{'='*80}")
    print(f"TESTING: {company_name} ({ticker})")
    print(f"{'='*80}\n")
    
    # Create chatbot
    print("Creating chatbot...")
    from src.benchmarkos_chatbot.settings import load_settings
    from src.benchmarkos_chatbot.llm import AnthropicClient
    from src.benchmarkos_chatbot.analytics_engine import AnalyticsEngine
    from src.benchmarkos_chatbot import database
    
    settings = load_settings()
    db = database.get_default_connection()
    llm_client = AnthropicClient(settings)
    analytics_engine = AnalyticsEngine(db)
    
    bot = BenchmarkOSChatbot(settings, llm_client, analytics_engine)
    
    # Generate dashboard
    print(f"Generating dashboard for {ticker}...")
    response = bot.ask(f"show dashboard for {ticker}")
    
    # Get the last generated payload
    if not hasattr(bot, '_last_cfi_payload') or not bot._last_cfi_payload:
        print(f"❌ No dashboard generated for {ticker}")
        return False
    
    payload = bot._last_cfi_payload
    sources = payload.get('sources', [])
    
    if not sources:
        print(f"❌ No sources in payload")
        return False
    
    # Categorize sources
    with_urls = []
    with_formulas = []
    with_market_data = []
    incomplete = []
    
    for source in sources:
        label = source.get('label', 'Unknown')
        has_url = bool(source.get('url'))
        has_calc = bool(source.get('calculation'))
        source_type = source.get('source', '')
        has_note = bool(source.get('note'))
        
        if has_url:
            with_urls.append(label)
        elif has_calc:
            display = source.get('calculation', {}).get('display', 'N/A')
            with_formulas.append((label, display))
        elif source_type in ('IMF', 'market_data', 'imf') or 'Market data' in str(has_note):
            with_market_data.append(label)
        else:
            incomplete.append(label)
    
    # Print results
    total = len(sources)
    complete = len(with_urls) + len(with_formulas) + len(with_market_data)
    
    print(f"📊 SOURCES BREAKDOWN:")
    print(f"  ✅ SEC URLs (Direct filings):       {len(with_urls):2d}/{total}")
    print(f"  ✅ Calculated (With formulas):      {len(with_formulas):2d}/{total}")
    print(f"  ✅ Market Data (External):          {len(with_market_data):2d}/{total}")
    print(f"  {'❌' if incomplete else '✅'} Incomplete:                      {len(incomplete):2d}/{total}")
    print(f"\n  {'='*60}")
    print(f"  TOTAL ATTRIBUTED:  {complete}/{total}")
    completeness = (complete / total * 100) if total > 0 else 0
    print(f"  COMPLETENESS:      {completeness:.1f}%")
    print(f"  {'='*60}\n")
    
    # Show examples
    if with_urls:
        print(f"📄 SEC URLs (showing first 3):")
        for label in with_urls[:3]:
            print(f"   ✓ {label}")
        if len(with_urls) > 3:
            print(f"   ... and {len(with_urls) - 3} more\n")
    
    if with_formulas:
        print(f"🧮 Calculated Metrics (showing first 5):")
        for label, formula in with_formulas[:5]:
            print(f"   ✓ {label}: {formula}")
        if len(with_formulas) > 5:
            print(f"   ... and {len(with_formulas) - 5} more\n")
    
    if with_market_data:
        print(f"📊 Market Data:")
        for label in with_market_data:
            print(f"   ✓ {label}\n")
    
    if incomplete:
        print(f"❌ INCOMPLETE ({len(incomplete)} sources):")
        for label in incomplete:
            print(f"   ✗ {label}")
        print()
    
    # Final verdict
    if completeness == 100:
        print(f"🎉 SUCCESS! 100% SOURCE ATTRIBUTION COMPLETE!\n")
        return True
    else:
        print(f"⚠️  {100 - completeness:.1f}% sources still need attribution\n")
        return False

if __name__ == "__main__":
    success = test_company("AAPL", "Apple Inc.")
    sys.exit(0 if success else 1)

