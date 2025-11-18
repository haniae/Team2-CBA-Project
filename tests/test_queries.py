#!/usr/bin/env python3
"""
Quick test script to verify queries work with the enhanced chatbot.
Run this to test if the natural language understanding improvements are working.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import normalize, parse_to_structured
from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from finanlyzeos_chatbot.context_builder import _extract_partial_info_from_query

# Test queries from the test suite - including complex longer sentences
TEST_QUERIES = [
    # Basic
    "what's apple's revenue",
    "show me tesla margins",
    "is nvidia profitable",
    "apple revenue",
    
    # With typos
    "whats apples revenu",
    "microsft margens",
    "nvida profit",
    
    # Conversational
    "how's apple doing",
    "what's up with tesla",
    "is microsoft good",
    
    # Comparisons
    "apple vs microsoft",
    "which is better apple or microsoft",
    "compare apple microsoft google",
    
    # Why questions
    "why did tesla margins drop",
    "what caused apple revenue to drop",
    "why is nvidia expensive",
    
    # Forecasting
    "what will apple revenue be next year",
    "forecast tesla revenue",
    "nvidia outlook",
    
    # Follow-ups (single word)
    "revenue",
    "margins",
    "cash flow",
    
    # Ambiguous
    "how are they doing",
    "what's the financial situation",
]

# Complex longer sentence queries
COMPLEX_QUERIES = [
    # Multi-part analysis
    "can you show me apple's revenue growth over the last five years and compare it to microsoft's growth during the same period",
    "i want to understand why tesla's gross margins declined in 2023 and what factors contributed to this decline including price cuts competition and production costs",
    "what happened to nvidia's revenue between 2020 and 2024 and when did the acceleration start and what caused the inflection point",
    "analyze amazon's financial health including revenue trends for the last ten years profitability margins roe roic cash flow balance sheet strength and valuation metrics",
    
    # Causal reasoning
    "why did tesla's margins drop in 2023 and what does that mean for investors and is this a temporary issue or a long term trend",
    "what caused apple's revenue to decline in the last quarter and how does this compare to historical patterns and what should investors expect going forward",
    "explain why microsoft's cloud revenue is growing so fast and what factors are driving this growth and how sustainable is this trend",
    "why is nvidia so expensive relative to other tech stocks and what metrics justify this valuation and is it overvalued or fairly valued",
    
    # Complex comparisons
    "compare apple microsoft and google on revenue growth profit margins cash flow generation debt levels and overall financial health to determine which is the best investment",
    "which tech company has better financial metrics apple or microsoft when looking at revenue growth margins cash flow and return on equity over the past five years",
    "how does tesla's profitability compare to traditional automakers like ford and gm in terms of margins cash flow and growth potential",
    "compare nvidia's financial performance to amd and intel across multiple metrics including revenue growth margins and market position",
    
    # Multi-metric deep dives
    "give me a comprehensive analysis of apple including revenue trends profitability margins cash flow balance sheet debt levels valuation metrics and future outlook",
    "i need a complete financial picture of tesla covering revenue growth margins cash generation debt structure profitability and how it compares to the industry",
    "analyze microsoft's financials in detail including all key metrics trends over time comparisons to peers and investment thesis",
    "show me everything about nvidia's financial health from revenue and margins to cash flow debt valuation and growth prospects",
    
    # Temporal and trend analysis
    "what's the trend for apple's revenue over the past decade and how has it changed over time and what are the key drivers of growth",
    "how has tesla's profitability evolved since 2020 and what were the major inflection points and what caused those changes",
    "show me microsoft's revenue growth trajectory over the last ten years with year over year changes and identify any significant patterns or anomalies",
    "analyze nvidia's earnings history to identify trends cycles and what factors have influenced the company's financial performance over time",
    
    # Forecasting with context
    "what will apple's revenue be for the next five years based on current trends and how does this compare to analyst estimates and what are the key assumptions",
    "forecast tesla's revenue growth for 2025 through 2027 considering current market conditions competition and the company's expansion plans",
    "predict microsoft's cloud revenue for the next three years based on historical growth rates market trends and competitive positioning",
    "what's nvidia's revenue outlook for the next five years given the ai boom and how sustainable is this growth trajectory",
    
    # Scenario analysis
    "what if apple's revenue grows at 15 percent annually for the next five years what would their market cap be and how does this compare to current valuation",
    "if tesla's margins improve to 20 percent what would their net income be and how would this affect their valuation and stock price",
    "scenario analysis for microsoft if cloud growth slows to 10 percent what would total revenue be in 2026 and how does this affect their p e ratio",
    "what happens if nvidia's revenue drops by 20 percent next year how would this impact their margins cash flow and overall financial health",
    
    # Relationship and correlation
    "how does r and d spending relate to revenue growth for tech companies like apple microsoft and google and is there a correlation",
    "what's the relationship between capex and revenue growth for tesla and how does this compare to other automakers and what does it mean for future growth",
    "analyze the correlation between microsoft's cloud investments and revenue growth and how long it takes for investments to pay off",
    "how does nvidia's research spending correlate with product launches and revenue growth and what's the typical lag time",
    
    # Benchmark and industry analysis
    "how does microsoft's profitability compare to the tech sector average and where do they rank among peers and what makes them different",
    "where does apple rank in terms of financial metrics compared to other tech giants and what are their relative strengths and weaknesses",
    "is tesla's financial performance above or below the automotive industry average and how do they compare on key metrics like margins and growth",
    "how does nvidia's valuation compare to the semiconductor industry and what metrics justify any premium or discount to peers",
    
    # Investment analysis
    "should i invest in apple based on their financial metrics revenue growth margins cash flow and valuation compared to the market and peers",
    "is tesla a good investment right now considering their financial health growth prospects profitability and current valuation",
    "evaluate microsoft as an investment opportunity using financial analysis including all key metrics trends and competitive position",
    "is nvidia worth buying at current prices based on their financials growth outlook and how the stock is valued relative to earnings and growth",
    
    # Complex conditional
    "if apple continues to grow revenue at current rates and maintains margins what would their market cap be in five years and is this realistic",
    "assuming tesla achieves their production targets and margins improve what would their financials look like in 2026 and how does this affect valuation",
    "if microsoft's cloud growth accelerates to 30 percent annually how would this impact total revenue margins and overall financial performance",
    "what would nvidia's financials look like if ai demand slows down and how would this affect their revenue margins and stock valuation",
    
    # Multi-company complex
    "compare the top five tech companies by market cap on revenue growth margins cash flow and return metrics to identify the best investment opportunity",
    "analyze apple microsoft google amazon and meta across multiple financial dimensions to determine which has the strongest financial position and growth outlook",
    "which of the big tech companies has the best combination of growth profitability and financial health and why",
    "compare tesla to other ev companies like rivian and lucid on financial metrics to see who's in the best position",
    
    # Very long complex queries
    "i need a comprehensive financial analysis of apple including historical revenue trends over the past decade current profitability metrics including gross operating and net margins cash flow generation both operating and free cash flow balance sheet strength including debt levels and current ratio return metrics like roe roic and roa valuation multiples such as p e ev ebitda and price to sales and how all of this compares to microsoft and google to help me make an investment decision",
    "can you explain why tesla's gross margins declined from 25 percent to 18 percent in 2023 what specific factors caused this including price cuts competition production scaling issues r and d spending and supply chain costs and what does this mean for the company's long term profitability and should investors be concerned",
    "i want to understand nvidia's financial trajectory show me revenue growth over the last five years with year over year changes identify when the ai boom started affecting their numbers analyze their profitability trends including margin expansion or compression examine their cash flow generation and debt levels compare their current valuation to historical averages and peers and provide a forecast for the next three years with different scenarios",
]

def test_normalize():
    """Test the normalize function handles queries correctly."""
    print("=" * 80)
    print("Testing normalize() function...")
    print("=" * 80)
    
    for query in TEST_QUERIES[:5]:  # Test first 5
        normalized = normalize(query)
        print(f"Query: {query[:60]}..." if len(query) > 60 else f"Query: {query}")
        print(f"Normalized: {normalized[:60]}..." if len(normalized) > 60 else f"Normalized: {normalized}")
        print()
    
    # Test complex queries
    print("\n" + "-" * 80)
    print("Testing COMPLEX queries...")
    print("-" * 80 + "\n")
    
    for query in COMPLEX_QUERIES[:3]:  # Test first 3 complex
        normalized = normalize(query)
        print(f"Query length: {len(query)} chars")
        print(f"Query: {query[:80]}...")
        print(f"Normalized length: {len(normalized)} chars")
        print(f"Normalized: {normalized[:80]}...")
        print()

def test_ticker_extraction():
    """Test ticker extraction with typos and complex queries."""
    print("=" * 80)
    print("Testing ticker extraction (with typos)...")
    print("=" * 80)
    
    typo_queries = [
        "whats apples revenu",
        "microsft margens",
        "nvida profit",
        "googl earnings",
    ]
    
    for query in typo_queries:
        try:
            tickers, warnings = resolve_tickers_freeform(query)
            print(f"Query: {query}")
            print(f"Extracted tickers: {[t.get('ticker') for t in tickers]}")
            print(f"Warnings: {warnings}")
            print()
        except Exception as e:
            print(f"Query: {query}")
            print(f"Error: {e}")
            print()
    
    # Test complex queries
    print("\n" + "-" * 80)
    print("Testing COMPLEX query ticker extraction...")
    print("-" * 80 + "\n")
    
    complex_ticker_queries = [
        "compare apple microsoft and google on revenue growth",
        "why did tesla's margins drop and what does that mean",
        "analyze nvidia's financial health including revenue margins and cash flow",
    ]
    
    for query in complex_ticker_queries:
        try:
            tickers, warnings = resolve_tickers_freeform(query)
            print(f"Query: {query[:70]}...")
            print(f"Extracted tickers: {[t.get('ticker') for t in tickers]}")
            print(f"Warnings: {len(warnings)} warnings")
            print()
        except Exception as e:
            print(f"Query: {query[:70]}...")
            print(f"Error: {e}")
            print()

def test_partial_extraction():
    """Test partial information extraction."""
    print("=" * 80)
    print("Testing partial information extraction...")
    print("=" * 80)
    
    test_cases = [
        "whats apples revenu",
        "how's apple doing",
        "why did tesla margins drop",
        "apple vs microsoft",
        "forecast tesla revenue",
    ]
    
    for query in test_cases:
        try:
            info = _extract_partial_info_from_query(query)
            print(f"Query: {query}")
            print(f"  Tickers: {info.get('tickers', [])}")
            print(f"  Metrics: {info.get('metrics', [])}")
            print(f"  Concepts: {info.get('concepts', [])}")
            print(f"  Question Type: {info.get('question_type')}")
            print()
        except Exception as e:
            print(f"Query: {query}")
            print(f"Error: {e}")
            print()
    
    # Test complex queries
    print("\n" + "-" * 80)
    print("Testing COMPLEX query partial extraction...")
    print("-" * 80 + "\n")
    
    complex_cases = [
        "can you show me apple's revenue growth over the last five years and compare it to microsoft",
        "i want to understand why tesla's gross margins declined in 2023 and what factors contributed",
        "analyze amazon's financial health including revenue trends profitability margins and cash flow",
        "compare the top five tech companies by market cap on revenue growth margins and cash flow",
    ]
    
    for query in complex_cases:
        try:
            info = _extract_partial_info_from_query(query)
            print(f"Query length: {len(query)} chars")
            print(f"Query: {query[:80]}...")
            print(f"  Tickers: {info.get('tickers', [])}")
            print(f"  Metrics: {info.get('metrics', [])}")
            print(f"  Concepts: {info.get('concepts', [])}")
            print(f"  Question Type: {info.get('question_type')}")
            print(f"  Time Periods: {info.get('time_periods', [])}")
            print()
        except Exception as e:
            print(f"Query: {query[:80]}...")
            print(f"Error: {e}")
            print()

def test_structured_parsing():
    """Test structured parsing."""
    print("=" * 80)
    print("Testing structured parsing...")
    print("=" * 80)
    
    test_cases = [
        "apple revenue",
        "whats apples revenu",  # With typo
        "apple vs microsoft",
        "why did tesla margins drop",
    ]
    
    for query in test_cases:
        try:
            structured = parse_to_structured(query)
            print(f"Query: {query}")
            print(f"  Tickers: {[t.get('ticker') for t in structured.get('tickers', [])]}")
            print(f"  Metrics: {[m.get('metric') for m in structured.get('metrics', [])]}")
            print(f"  Intent: {structured.get('intent')}")
            print()
        except Exception as e:
            print(f"Query: {query}")
            print(f"Error: {e}")
            print()
    
    # Test complex queries
    print("\n" + "-" * 80)
    print("Testing COMPLEX query structured parsing...")
    print("-" * 80 + "\n")
    
    complex_cases = [
        "compare apple microsoft and google on revenue growth profit margins and cash flow",
        "why did tesla's margins drop in 2023 and what does that mean for investors",
        "analyze nvidia's financial health including revenue margins cash flow and valuation",
        "what will apple's revenue be for the next five years based on current trends",
    ]
    
    for query in complex_cases:
        try:
            structured = parse_to_structured(query)
            print(f"Query length: {len(query)} chars")
            print(f"Query: {query[:80]}...")
            print(f"  Tickers: {[t.get('ticker') for t in structured.get('tickers', [])]}")
            print(f"  Metrics: {[m.get('metric') for m in structured.get('metrics', [])]}")
            print(f"  Intent: {structured.get('intent')}")
            print()
        except Exception as e:
            print(f"Query: {query[:80]}...")
            print(f"Error: {e}")
            print()

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("QUERY TESTING SUITE")
    print("=" * 80 + "\n")
    
    try:
        test_normalize()
        test_ticker_extraction()
        test_partial_extraction()
        test_structured_parsing()
        
        print("=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)
        print("\nNote: These tests verify the parsing/extraction logic.")
        print("For full end-to-end testing, run the chatbot and try the queries.")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

