"""Test script to verify metric name matching handles various user input variations."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import resolve_metrics, normalize
from finanlyzeos_chatbot.parsing.ontology import METRIC_SYNONYMS

def test_metric_variations():
    """Test various ways users might write metric names."""
    
    # Test cases: (user_input, expected_metric_id)
    test_cases = [
        # Revenue variations
        ("revenue", "revenue"),
        ("Revenue", "revenue"),
        ("REVENUE", "revenue"),
        ("sales", "revenue"),
        ("top line", "revenue"),
        ("topline", "revenue"),
        ("rev", "revenue"),
        ("total revenue", "revenue"),
        ("net revenue", "revenue"),
        
        # Net income variations
        ("net income", "net_income"),
        ("netincome", "net_income"),
        ("net profit", "net_income"),
        ("profit", "net_income"),
        ("earnings", "net_income"),
        ("bottom line", "net_income"),
        ("net earnings", "net_income"),
        
        # EPS variations
        ("earnings per share", "eps_diluted"),
        ("EPS", "eps_diluted"),
        ("eps", "eps_diluted"),
        ("diluted eps", "eps_diluted"),
        ("earnings a share", "eps_diluted"),
        ("profit per share", "eps_diluted"),
        
        # P/E ratio variations
        ("pe", "pe_ratio"),
        ("P/E", "pe_ratio"),
        ("p/e", "pe_ratio"),
        ("p e", "pe_ratio"),
        ("P E", "pe_ratio"),
        ("price to earnings", "pe_ratio"),
        ("pe ratio", "pe_ratio"),
        ("price earnings", "pe_ratio"),
        ("price earnings ratio", "pe_ratio"),
        ("earnings multiple", "pe_ratio"),
        ("p e ratio", "pe_ratio"),
        ("p to e", "pe_ratio"),
        ("price-to-earnings", "pe_ratio"),  # Hyphenated
        ("price-to-earnings ratio", "pe_ratio"),  # Hyphenated with ratio
        
        # EBITDA variations
        ("ebitda", "ebitda"),
        ("EBITDA", "ebitda"),
        ("Ebitda", "ebitda"),
        
        # Operating income variations
        ("operating income", "operating_income"),
        ("operating profit", "operating_income"),
        ("ebit", "operating_income"),
        
        # Gross profit variations
        ("gross profit", "gross_profit"),
        ("grossprofit", "gross_profit"),
        
        # Margin variations
        ("gross margin", "gross_margin"),
        ("operating margin", "operating_margin"),
        ("net margin", "net_margin"),
        ("profit margin", "net_margin"),
        ("margins", "net_margin"),
        ("margin", "net_margin"),
        
        # Cash flow variations
        ("free cash flow", "free_cash_flow"),
        ("FCF", "free_cash_flow"),
        ("fcf", "free_cash_flow"),
        ("cash generated", "free_cash_flow"),
        ("free cash", "free_cash_flow"),
        ("operating cash flow", "cash_operations"),
        ("cash from operations", "cash_operations"),
        ("OCF", "cash_operations"),
        
        # Return metrics
        ("return on equity", "roe"),
        ("ROE", "roe"),
        ("roe", "roe"),
        ("return on assets", "roa"),
        ("ROA", "roa"),
        ("roa", "roa"),
        ("return on invested capital", "roic"),
        ("ROIC", "roic"),
        ("roic", "roic"),
        ("ROI", "roic"),
        
        # Valuation metrics
        ("market cap", "market_cap"),
        ("marketcap", "market_cap"),
        ("market capitalization", "market_cap"),
        ("market value", "market_cap"),
        ("valuation", "market_cap"),
        
        # EV/EBITDA variations
        ("ev/ebitda", "ev_ebitda"),
        ("EV/EBITDA", "ev_ebitda"),
        ("ev ebitda", "ev_ebitda"),
        ("enterprise value to ebitda", "ev_ebitda"),
        ("enterprise value", "ev_ebitda"),
        
        # P/B variations
        ("pb", "pb_ratio"),
        ("P/B", "pb_ratio"),
        ("p/b", "pb_ratio"),
        ("price to book", "pb_ratio"),
        ("price book", "pb_ratio"),
        ("price-to-book", "pb_ratio"),  # Hyphenated
        
        # PEG variations
        ("peg", "peg_ratio"),
        ("peg ratio", "peg_ratio"),
        ("price earnings growth", "peg_ratio"),
        
        # Dividend variations
        ("dividend yield", "dividend_yield"),
        ("dividends", "dividend_yield"),
        ("dividend", "dividend_yield"),
        ("div yield", "dividend_yield"),
        
        # Debt variations
        ("debt to equity", "debt_equity"),
        ("debt-to-equity", "debt_equity"),  # Hyphenated
        ("debt equity ratio", "debt_equity"),
        ("d/e", "debt_equity"),
        ("D/E", "debt_equity"),
        ("leverage", "debt_equity"),
        ("leverage ratio", "debt_equity"),
        
        # Liquidity variations
        ("current ratio", "current_ratio"),
        ("currentratio", "current_ratio"),
        ("quick ratio", "quick_ratio"),
        ("quickratio", "quick_ratio"),
        ("acid test", "quick_ratio"),
        ("working capital", "working_capital"),
        ("workingcapital", "working_capital"),
        ("wc", "working_capital"),
        
        # Interest coverage
        ("interest coverage", "interest_coverage"),
        ("times interest earned", "interest_coverage"),
        
        # Turnover variations
        ("asset turnover", "asset_turnover"),
        ("assetturnover", "asset_turnover"),
        ("inventory turnover", "inventory_turnover"),
        ("inventoryturnover", "inventory_turnover"),
        
        # Price to sales
        ("price to sales", "price_to_sales"),
        ("P/S", "price_to_sales"),
        ("p/s", "price_to_sales"),
        ("price sales", "price_to_sales"),
        ("price-to-sales", "price_to_sales"),  # Hyphenated
        
        # Operating expenses
        ("operating expenses", "operating_expenses"),
        ("opex", "operating_expenses"),
        ("operating costs", "operating_expenses"),
        
        # R&D variations
        ("R&D", "rd_expenses"),
        ("r&d", "rd_expenses"),
        ("research and development", "rd_expenses"),
        ("R&D expenses", "rd_expenses"),
        
        # CAPEX variations
        ("capex", "capex"),
        ("CAPEX", "capex"),
        ("capital expenditure", "capex"),
        ("capital spending", "capex"),
        
        # Share buyback variations
        ("buyback", "share_buyback_intensity"),
        ("buybacks", "share_buyback_intensity"),
        ("share repurchase", "share_buyback_intensity"),
        ("stock buyback", "share_buyback_intensity"),
        
        # Growth variations
        ("growth", "revenue_growth"),
        ("growth rate", "revenue_growth"),
        ("revenue growth", "revenue_growth"),
        ("sales growth", "revenue_growth"),
        
        # Cash variations
        ("cash", "cash_and_equivalents"),
        ("cash on hand", "cash_and_equivalents"),
        ("cash reserves", "cash_and_equivalents"),
        
        # Stock price
        ("stock price", "stock_price"),
        ("share price", "stock_price"),
        ("price", "stock_price"),
        
        # Beta/Volatility
        ("beta", "beta"),
        ("volatility", "beta"),
        ("stock volatility", "beta"),
        
        # Assets
        ("assets", "total_assets"),
        ("total assets", "total_assets"),
        
        # Liabilities
        ("liabilities", "total_liabilities"),
        ("total liabilities", "total_liabilities"),
        
        # Equity
        ("equity", "shareholders_equity"),
        ("shareholders equity", "shareholders_equity"),
        ("shareholder equity", "shareholders_equity"),
        ("book value", "shareholders_equity"),
    ]
    
    print("=" * 80)
    print("Testing Metric Name Variations")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    failures = []
    
    for user_input, expected_metric_id in test_cases:
        # Create a test query with the metric name
        test_query = f"What is Apple's {user_input}?"
        
        # Normalize and resolve
        normalized = normalize(test_query)
        matches = resolve_metrics(test_query, normalized)
        
        # Check if we found the expected metric
        found_metric = None
        if matches:
            for match in matches:
                if match.get("metric_id") == expected_metric_id:
                    found_metric = match.get("metric_id")
                    break
        
        if found_metric == expected_metric_id:
            print(f"[PASS] '{user_input}' -> {expected_metric_id}")
            passed += 1
        else:
            found_ids = [m.get("metric_id") for m in matches] if matches else []
            print(f"[FAIL] '{user_input}' -> Expected: {expected_metric_id}, Got: {found_ids}")
            failed += 1
            failures.append((user_input, expected_metric_id, found_ids))
    
    print()
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    if failures:
        print("\nFailures:")
        for user_input, expected, found in failures:
            print(f"  - '{user_input}': Expected {expected}, Found {found}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_metric_variations()
    sys.exit(0 if success else 1)

