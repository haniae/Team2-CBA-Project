"""Test script to verify metric name recognition handles various user input formats."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import resolve_metrics, normalize

# Test cases: (user_input, expected_metric_id)
TEST_CASES = [
    # Revenue variations
    ("revenue", "revenue"),
    ("Revenue", "revenue"),
    ("REVENUE", "revenue"),
    ("sales", "revenue"),
    ("Sales", "revenue"),
    ("top line", "revenue"),
    ("topline", "revenue"),
    ("rev", "revenue"),
    
    # Net income variations
    ("net income", "net_income"),
    ("netincome", "net_income"),
    ("net income", "net_income"),
    ("Net Income", "net_income"),
    ("NET INCOME", "net_income"),
    ("net profit", "net_income"),
    ("profit", "net_income"),
    ("earnings", "net_income"),
    ("bottom line", "net_income"),
    
    # EPS variations
    ("eps", "eps_diluted"),
    ("EPS", "eps_diluted"),
    ("earnings per share", "eps_diluted"),
    ("Earnings Per Share", "eps_diluted"),
    ("diluted eps", "eps_diluted"),
    ("EPS diluted", "eps_diluted"),
    
    # P/E ratio variations
    ("pe", "pe_ratio"),
    ("PE", "pe_ratio"),
    ("p/e", "pe_ratio"),
    ("P/E", "pe_ratio"),
    ("p e", "pe_ratio"),
    ("P E", "pe_ratio"),
    ("price to earnings", "pe_ratio"),
    ("price-to-earnings", "pe_ratio"),
    ("pe ratio", "pe_ratio"),
    ("P/E ratio", "pe_ratio"),
    
    # EBITDA variations
    ("ebitda", "ebitda"),
    ("EBITDA", "ebitda"),
    ("Ebitda", "ebitda"),
    
    # Free cash flow variations
    ("free cash flow", "free_cash_flow"),
    ("Free Cash Flow", "free_cash_flow"),
    ("fcf", "free_cash_flow"),
    ("FCF", "free_cash_flow"),
    
    # ROE variations
    ("roe", "roe"),
    ("ROE", "roe"),
    ("return on equity", "roe"),
    ("Return On Equity", "roe"),
    
    # ROA variations
    ("roa", "roa"),
    ("ROA", "roa"),
    ("return on assets", "roa"),
    
    # ROIC variations
    ("roic", "roic"),
    ("ROIC", "roic"),
    ("return on invested capital", "roic"),
    ("roi", "roic"),
    
    # Debt to equity variations
    ("debt to equity", "debt_equity"),
    ("debt-to-equity", "debt_equity"),
    ("debt/equity", "debt_equity"),
    ("d/e", "debt_equity"),
    ("D/E", "debt_equity"),
    ("debt equity ratio", "debt_equity"),
    
    # EV/EBITDA variations
    ("ev/ebitda", "ev_ebitda"),
    ("EV/EBITDA", "ev_ebitda"),
    ("ev ebitda", "ev_ebitda"),
    ("enterprise value to ebitda", "ev_ebitda"),
    
    # P/B variations
    ("pb", "pb_ratio"),
    ("P/B", "pb_ratio"),
    ("p/b", "pb_ratio"),
    ("price to book", "pb_ratio"),
    ("price-to-book", "pb_ratio"),
    
    # Margin variations
    ("margin", "net_margin"),
    ("margins", "net_margin"),
    ("profit margin", "net_margin"),
    ("operating margin", "operating_margin"),
    ("gross margin", "gross_margin"),
    
    # Market cap variations
    ("market cap", "market_cap"),
    ("market capitalization", "market_cap"),
    ("marketcap", "market_cap"),
    ("market value", "market_cap"),
    
    # Dividend variations
    ("dividend yield", "dividend_yield"),
    ("dividend", "dividend_yield"),
    ("dividends", "dividend_yield"),
    
    # Working capital variations
    ("working capital", "working_capital"),
    ("workingcapital", "working_capital"),
    ("wc", "working_capital"),
    
    # Current ratio variations
    ("current ratio", "current_ratio"),
    ("currentratio", "current_ratio"),
    
    # Quick ratio variations
    ("quick ratio", "quick_ratio"),
    ("quickratio", "quick_ratio"),
    ("acid test", "quick_ratio"),
    
    # Operating income variations
    ("operating income", "operating_income"),
    ("operating profit", "operating_income"),
    ("ebit", "operating_income"),
    ("EBIT", "operating_income"),
    
    # Gross profit variations
    ("gross profit", "gross_profit"),
    ("grossprofit", "gross_profit"),
    
    # Cash flow variations
    ("cash from operations", "cash_operations"),
    ("operating cash flow", "cash_operations"),
    ("OCF", "cash_operations"),
    
    # Price to sales variations
    ("price to sales", "price_to_sales"),
    ("P/S", "price_to_sales"),
    ("p/s", "price_to_sales"),
    ("price-to-sales", "price_to_sales"),
    
    # Interest coverage variations
    ("interest coverage", "interest_coverage"),
    ("times interest earned", "interest_coverage"),
    
    # Inventory turnover variations
    ("inventory turnover", "inventory_turnover"),
    ("inventoryturnover", "inventory_turnover"),
    
    # Asset turnover variations
    ("asset turnover", "asset_turnover"),
    ("assetturnover", "asset_turnover"),
    
    # Dividend per share variations
    ("dividend per share", "dividend_per_share"),
    ("DPS", "dividend_per_share"),
    
    # Payout ratio variations
    ("payout ratio", "payout_ratio"),
    ("dividend payout ratio", "payout_ratio"),
    
    # Operating expenses variations
    ("operating expenses", "operating_expenses"),
    ("opex", "operating_expenses"),
    ("OPEX", "operating_expenses"),
    
    # R&D variations
    ("R&D", "r_and_d"),
    ("r&d", "r_and_d"),
    ("research and development", "r_and_d"),
    ("research and development", "r_and_d"),
    
    # CAPEX variations
    ("capex", "capex"),
    ("CAPEX", "capex"),
    ("capital expenditure", "capex"),
    ("capital expenditures", "capex"),
    
    # Test with context (should still match)
    ("What is Apple's revenue?", "revenue"),
    ("Show me the net income", "net_income"),
    ("How much is the P/E ratio?", "pe_ratio"),
    ("Tell me about free cash flow", "free_cash_flow"),
    ("What's their ROE?", "roe"),
]

def test_metric_recognition():
    """Test metric recognition with various input formats."""
    print("Testing metric name recognition...")
    print("=" * 80)
    
    passed = 0
    failed = 0
    failures = []
    
    for user_input, expected_metric_id in TEST_CASES:
        # Normalize the input
        lowered_full = normalize(user_input)
        
        # Resolve metrics
        matches = resolve_metrics(user_input, lowered_full)
        
        # Check if we found the expected metric
        found_metric_ids = [m.get("metric_id") for m in matches if m.get("metric_id")]
        
        if expected_metric_id in found_metric_ids:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
            failures.append((user_input, expected_metric_id, found_metric_ids))
            print(f"{status} '{user_input}' -> Expected: {expected_metric_id}, Got: {found_metric_ids}")
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    
    if failures:
        print("\nFailures:")
        for user_input, expected, found in failures:
            print(f"  Input: '{user_input}'")
            print(f"    Expected: {expected}")
            print(f"    Found: {found}")
            print()
    
    return failed == 0

if __name__ == "__main__":
    success = test_metric_recognition()
    sys.exit(0 if success else 1)

