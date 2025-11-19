"""Comprehensive test suite for financial query patterns and metric recognition."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import (
    parse_to_structured,
    classify_intent,
    normalize,
    INTENT_SECTOR_ANALYSIS_PATTERN,
    INTENT_MARKET_ANALYSIS_PATTERN,
    INTENT_MERGER_ACQUISITION_PATTERN,
    INTENT_IPO_PATTERN,
    INTENT_ESG_PATTERN,
    INTENT_CREDIT_ANALYSIS_PATTERN,
    INTENT_LIQUIDITY_PATTERN,
    INTENT_CAPITAL_STRUCTURE_PATTERN,
    INTENT_ECONOMIC_INDICATORS_PATTERN,
    INTENT_REGULATORY_PATTERN,
)
from finanlyzeos_chatbot.parsing.ontology import METRIC_SYNONYMS


def test_intent_patterns():
    """Test new financial intent patterns."""
    print("\n" + "="*80)
    print("TESTING NEW FINANCIAL INTENT PATTERNS")
    print("="*80)
    
    test_cases = [
        # Sector Analysis
        ("How is the tech sector performing?", "sector_analysis"),
        ("What's happening in the financial services industry?", "sector_analysis"),
        ("Sector analysis for healthcare", "sector_analysis"),
        ("Industry trends in energy", "sector_analysis"),
        
        # Market Analysis
        ("What's Apple's market share?", "market_analysis"),
        ("Competitive analysis of Microsoft", "market_analysis"),
        ("Market outlook for cloud computing", "market_analysis"),
        ("What's the addressable market for AI?", "market_analysis"),
        
        # M&A
        ("Has Apple acquired any companies recently?", "merger_acquisition"),
        ("What M&A deals has Microsoft done?", "merger_acquisition"),
        ("Is Tesla a takeover target?", "merger_acquisition"),
        ("Analyze Amazon's acquisition strategy", "merger_acquisition"),
        
        # IPO
        ("When did Tesla go public?", "ipo"),
        ("What was Apple's IPO price?", "ipo"),
        ("Is there an upcoming IPO in tech?", "ipo"),
        ("Analyze recent IPO performance", "ipo"),
        
        # ESG
        ("What's Apple's ESG score?", "esg"),
        ("How sustainable is Tesla's business?", "esg"),
        ("What's Microsoft's carbon footprint?", "esg"),
        ("ESG analysis of Amazon", "esg"),
        
        # Credit Analysis
        ("What's Apple's credit rating?", "credit_analysis"),
        ("How much debt does Tesla have?", "credit_analysis"),
        ("What's Microsoft's interest coverage ratio?", "credit_analysis"),
        ("Credit analysis of Google", "credit_analysis"),
        
        # Liquidity
        ("What's Apple's current ratio?", "liquidity_analysis"),
        ("How liquid is Tesla?", "liquidity_analysis"),
        ("What's Microsoft's working capital?", "liquidity_analysis"),
        ("Can Amazon pay its short-term obligations?", "liquidity_analysis"),
        
        # Capital Structure
        ("How is Apple allocating capital?", "capital_structure"),
        ("What's Tesla's share buyback program?", "capital_structure"),
        ("Microsoft's dividend policy", "capital_structure"),
        ("Analyze Google's capital structure", "capital_structure"),
        
        # Economic Indicators
        ("How does inflation affect tech stocks?", "economic_indicators"),
        ("What's the impact of interest rates on Apple?", "economic_indicators"),
        ("How does GDP growth affect Microsoft?", "economic_indicators"),
        ("Economic outlook for the tech sector", "economic_indicators"),
        
        # Regulatory
        ("What are the regulatory risks for Tesla?", "regulatory"),
        ("SEC filings for Apple", "regulatory"),
        ("Compliance issues for Microsoft", "regulatory"),
        ("Regulatory environment for tech", "regulatory"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent in test_cases:
        norm_text = normalize(query)
        structured = parse_to_structured(query)
        actual_intent = structured.get("intent", "unknown")
        
        if actual_intent == expected_intent:
            print(f"[PASS] {query[:60]:<60} -> {actual_intent}")
            passed += 1
        else:
            print(f"[FAIL] {query[:60]:<60} -> Expected: {expected_intent}, Got: {actual_intent}")
            failed += 1
    
    print(f"\nIntent Pattern Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_metric_synonyms():
    """Test that various ways of writing metric names are recognized."""
    print("\n" + "="*80)
    print("TESTING METRIC SYNONYM RECOGNITION")
    print("="*80)
    
    # Test cases: (query, expected_metric_id)
    test_cases = [
        # Revenue variations
        ("What is Apple's revenue?", "revenue"),
        ("What is Apple's sales?", "revenue"),
        ("What is Apple's top line?", "revenue"),
        ("How much money does Apple make?", "revenue"),
        ("What are Apple's sales figures?", "revenue"),
        
        # Profit variations
        ("What is Apple's profit?", "net_income"),
        ("What is Apple's net income?", "net_income"),
        ("What is Apple's earnings?", "net_income"),
        ("What is Apple's bottom line?", "net_income"),
        ("How much profit does Apple make?", "net_income"),
        
        # EPS variations
        ("What is Apple's EPS?", "eps_diluted"),
        ("What is Apple's earnings per share?", "eps_diluted"),
        ("What is Apple's diluted EPS?", "eps_diluted"),
        
        # P/E variations
        ("What is Apple's P/E ratio?", "pe_ratio"),
        ("What is Apple's price to earnings?", "pe_ratio"),
        ("What is Apple's PE?", "pe_ratio"),
        ("What is Apple's price earnings ratio?", "pe_ratio"),
        
        # Free cash flow variations
        ("What is Apple's free cash flow?", "free_cash_flow"),
        ("What is Apple's FCF?", "free_cash_flow"),
        ("How much cash does Apple generate?", "free_cash_flow"),
        
        # ROE variations
        ("What is Apple's ROE?", "roe"),
        ("What is Apple's return on equity?", "roe"),
        ("What's the ROE for Apple?", "roe"),
        
        # Debt variations
        ("What is Apple's debt?", "debt_equity"),
        ("What is Apple's debt to equity?", "debt_equity"),
        ("What is Apple's leverage?", "debt_equity"),
        ("How leveraged is Apple?", "debt_equity"),
        
        # Current ratio variations
        ("What is Apple's current ratio?", "current_ratio"),
        ("What is Apple's liquidity?", "current_ratio"),
        ("How liquid is Apple?", "current_ratio"),
        
        # Market cap variations
        ("What is Apple's market cap?", "market_cap"),
        ("What is Apple's market capitalization?", "market_cap"),
        ("How much is Apple worth?", "market_cap"),
        ("What is Apple's valuation?", "market_cap"),
        
        # EBITDA variations
        ("What is Apple's EBITDA?", "ebitda"),
        ("What is Apple's EBITDA margin?", "ebitda_margin"),
        
        # Gross margin variations
        ("What is Apple's gross margin?", "gross_margin"),
        ("What is Apple's gross profit margin?", "gross_margin"),
        
        # Operating margin variations
        ("What is Apple's operating margin?", "operating_margin"),
        ("What is Apple's operating profit margin?", "operating_margin"),
        
        # Dividend variations
        ("What is Apple's dividend yield?", "dividend_yield"),
        ("What is Apple's dividend?", "dividend_yield"),
        ("What are Apple's dividends?", "dividend_yield"),
        
        # Buyback variations
        ("What is Apple's share buyback?", "share_buyback_intensity"),
        ("What is Apple's stock buyback?", "share_buyback_intensity"),
        ("What is Apple's buyback program?", "share_buyback_intensity"),
        
        # CAPEX variations
        ("What is Apple's CAPEX?", "capex"),
        ("What is Apple's capital expenditure?", "capex"),
        ("What is Apple's capital spending?", "capex"),
        
        # R&D variations
        ("What is Apple's R&D?", "r_and_d"),
        ("What is Apple's research and development?", "r_and_d"),
        ("What is Apple's RD?", "r_and_d"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric in test_cases:
        structured = parse_to_structured(query)
        metrics = structured.get("vmetrics", [])
        
        found_metric = None
        if metrics:
            found_metric = metrics[0].get("metric_id")
        
        if found_metric == expected_metric:
            print(f"[PASS] {query[:60]:<60} -> {found_metric}")
            passed += 1
        else:
            print(f"[FAIL] {query[:60]:<60} -> Expected: {expected_metric}, Got: {found_metric}")
            failed += 1
            # Show what synonyms exist for this metric
            synonyms = [k for k, v in METRIC_SYNONYMS.items() if v == expected_metric]
            print(f"       Available synonyms: {', '.join(synonyms[:5])}...")
    
    print(f"\nMetric Synonym Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_metric_phrasing_variations():
    """Test that different phrasings of the same metric are recognized."""
    print("\n" + "="*80)
    print("TESTING METRIC PHRASING VARIATIONS")
    print("="*80)
    
    # Group similar phrasings that should all resolve to the same metric
    metric_groups = {
        "revenue": [
            "revenue",
            "sales",
            "top line",
            "topline",
            "rev",
            "total revenue",
            "net revenue",
            "gross revenue",
            "total sales",
            "sales figures",
        ],
        "net_income": [
            "net income",
            "net profit",
            "profit",
            "earnings",
            "bottom line",
            "net earnings",
            "total profit",
            "total earnings",
        ],
        "pe_ratio": [
            "pe",
            "p/e",
            "price to earnings",
            "pe ratio",
            "price earnings",
            "price earnings ratio",
            "p e ratio",
            "p to e",
        ],
        "free_cash_flow": [
            "free cash flow",
            "fcf",
            "cash generated",
            "cash they make",
            "cash they generate",
            "cash generation",
            "free cash",
        ],
        "debt_equity": [
            "debt",
            "debt level",
            "how much debt",
            "debt to equity",
            "debt equity ratio",
            "leverage",
            "leverage ratio",
            "financial leverage",
            "gearing",
            "gearing ratio",
        ],
        "current_ratio": [
            "current ratio",
            "liquidity",
            "how liquid",
            "liquid",
            "liquidity ratio",
        ],
        "market_cap": [
            "market cap",
            "market capitalization",
            "market value",
            "valuation",
            "how much they worth",
            "how much are they worth",
            "worth",
            "value",
        ],
    }
    
    passed = 0
    failed = 0
    
    for metric_id, phrasings in metric_groups.items():
        print(f"\nTesting {metric_id}:")
        for phrasing in phrasings:
            query = f"What is Apple's {phrasing}?"
            structured = parse_to_structured(query)
            metrics = structured.get("vmetrics", [])
            
            found_metric = None
            if metrics:
                found_metric = metrics[0].get("metric_id")
            
            if found_metric == metric_id:
                print(f"  [PASS] '{phrasing}' -> {found_metric}")
                passed += 1
            else:
                print(f"  [FAIL] '{phrasing}' -> Expected: {metric_id}, Got: {found_metric}")
                failed += 1
    
    print(f"\nMetric Phrasing Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_case_insensitivity():
    """Test that metric names work regardless of case."""
    print("\n" + "="*80)
    print("TESTING CASE INSENSITIVITY")
    print("="*80)
    
    test_cases = [
        "What is Apple's REVENUE?",
        "What is Apple's Revenue?",
        "What is Apple's revenue?",
        "What is Apple's ReVeNuE?",
        "What is Apple's P/E RATIO?",
        "What is Apple's p/e ratio?",
        "What is Apple's Pe RaTiO?",
        "What is Apple's EBITDA?",
        "What is Apple's ebitda?",
        "What is Apple's EbItDa?",
    ]
    
    passed = 0
    failed = 0
    
    for query in test_cases:
        structured = parse_to_structured(query)
        metrics = structured.get("vmetrics", [])
        
        if metrics:
            found_metric = metrics[0].get("metric_id")
            print(f"[PASS] {query[:60]:<60} -> {found_metric}")
            passed += 1
        else:
            print(f"[FAIL] {query[:60]:<60} -> No metric found")
            failed += 1
    
    print(f"\nCase Insensitivity Tests: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE FINANCIAL QUERY PATTERN TESTING")
    print("="*80)
    
    results = []
    
    # Test intent patterns
    results.append(("Intent Patterns", test_intent_patterns()))
    
    # Test metric synonyms
    results.append(("Metric Synonyms", test_metric_synonyms()))
    
    # Test metric phrasing variations
    results.append(("Metric Phrasing", test_metric_phrasing_variations()))
    
    # Test case insensitivity
    results.append(("Case Insensitivity", test_case_insensitivity()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:<30} {status}")
        if not passed:
            all_passed = False
    
    print("="*80)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - Review output above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

