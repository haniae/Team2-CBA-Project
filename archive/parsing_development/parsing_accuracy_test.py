#!/usr/bin/env python3
"""
Comprehensive Parsing System Accuracy Test Suite
Tests the accuracy and reliability of the BenchmarkOS parsing system.
"""

import sys
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot.parsing.parse import parse_to_structured
from benchmarkos_chatbot.parsing.time_grammar import parse_periods
from benchmarkos_chatbot.parsing.alias_builder import resolve_tickers_freeform

class ParsingAccuracyTester:
    """Comprehensive test suite for parsing system accuracy."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_test(self, test_name: str, input_text: str, expected: Dict[str, Any], 
                 test_type: str = "general") -> bool:
        """Run a single parsing test."""
        self.total_tests += 1
        
        try:
            result = parse_to_structured(input_text)
            
            # Check each expected field
            passed = True
            issues = []
            
            # Check intent
            if 'intent' in expected:
                if result.get('intent') != expected['intent']:
                    passed = False
                    issues.append(f"Intent: got '{result.get('intent')}', expected '{expected['intent']}'")
            
            # Check tickers
            if 'tickers' in expected:
                expected_tickers = expected['tickers'] if isinstance(expected['tickers'], list) else [expected['tickers']]
                actual_tickers = [t['ticker'] for t in result.get('tickers', [])]
                
                if not all(ticker in actual_tickers for ticker in expected_tickers):
                    passed = False
                    issues.append(f"Tickers: got {actual_tickers}, expected {expected_tickers}")
            
            # Check metrics
            if 'metrics' in expected:
                expected_metrics = expected['metrics'] if isinstance(expected['metrics'], list) else [expected['metrics']]
                actual_metrics = [m['key'] for m in result.get('vmetrics', [])]
                
                if not all(metric in actual_metrics for metric in expected_metrics):
                    passed = False
                    issues.append(f"Metrics: got {actual_metrics}, expected {expected_metrics}")
            
            # Check warnings
            if 'warnings' in expected:
                expected_warnings = expected['warnings'] if isinstance(expected['warnings'], list) else [expected['warnings']]
                actual_warnings = result.get('warnings', [])
                
                if not all(warning in actual_warnings for warning in expected_warnings):
                    passed = False
                    issues.append(f"Warnings: got {actual_warnings}, expected {expected_warnings}")
            
            # Check period parsing
            if 'period_type' in expected:
                period_info = result.get('periods', {})
                if period_info.get('type') != expected['period_type']:
                    passed = False
                    issues.append(f"Period type: got '{period_info.get('type')}', expected '{expected['period_type']}'")
            
            if passed:
                self.passed_tests += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            self.test_results.append({
                'name': test_name,
                'input': input_text,
                'expected': expected,
                'actual': result,
                'passed': passed,
                'issues': issues,
                'status': status,
                'type': test_type
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Status: {status}")
            if issues:
                for issue in issues:
                    print(f"    Issue: {issue}")
            print()
            
            return passed
            
        except Exception as e:
            self.test_results.append({
                'name': test_name,
                'input': input_text,
                'expected': expected,
                'actual': None,
                'passed': False,
                'issues': [f"Exception: {str(e)}"],
                'status': "❌ ERROR",
                'type': test_type
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Status: ❌ ERROR - {str(e)}")
            print()
            
            return False
    
    def test_ticker_resolution(self):
        """Test ticker resolution accuracy."""
        print("=== TICKER RESOLUTION TESTS ===")
        print()
        
        # Basic ticker tests
        self.run_test("Apple ticker", "Apple revenue", {'tickers': 'AAPL', 'metrics': 'revenue'})
        self.run_test("Microsoft ticker", "Microsoft earnings", {'tickers': 'MSFT', 'metrics': 'net_income'})
        self.run_test("Google ticker", "Google revenue", {'tickers': 'GOOGL', 'metrics': 'revenue'})
        self.run_test("Amazon ticker", "Amazon profit", {'tickers': 'AMZN', 'metrics': 'net_income'})
        self.run_test("Tesla ticker", "Tesla stock", {'tickers': 'TSLA'})
        
        # Company name variations
        self.run_test("JPMorgan Chase", "JPMorgan Chase profit", {'tickers': 'JPM', 'metrics': 'net_income'})
        self.run_test("Berkshire Hathaway", "Berkshire Hathaway", {'tickers': 'BRK.B'})
        self.run_test("Alphabet Class A", "Alphabet Class A revenue", {'tickers': 'GOOGL', 'metrics': 'revenue'})
        self.run_test("Meta Platforms", "Meta Platforms earnings", {'tickers': 'META', 'metrics': 'net_income'})
        self.run_test("Facebook", "Facebook revenue", {'tickers': 'META', 'metrics': 'revenue'})
        
        # Multi-ticker tests
        self.run_test("Multiple tickers", "Apple and Microsoft revenue", 
                     {'tickers': ['AAPL', 'MSFT'], 'metrics': 'revenue'})
        self.run_test("Compare tickers", "Compare Google vs Amazon", 
                     {'tickers': ['GOOGL', 'AMZN'], 'intent': 'compare'})
    
    def test_metric_parsing(self):
        """Test metric parsing accuracy."""
        print("=== METRIC PARSING TESTS ===")
        print()
        
        # Revenue metrics
        self.run_test("Revenue metric", "Apple revenue", {'tickers': 'AAPL', 'metrics': 'revenue'})
        self.run_test("Sales metric", "Apple sales", {'tickers': 'AAPL', 'metrics': 'revenue'})
        self.run_test("Top line metric", "Apple top line", {'tickers': 'AAPL', 'metrics': 'revenue'})
        
        # Profitability metrics
        self.run_test("Net income metric", "Apple net income", {'tickers': 'AAPL', 'metrics': 'net_income'})
        self.run_test("Earnings metric", "Apple earnings", {'tickers': 'AAPL', 'metrics': 'net_income'})
        self.run_test("Profit metric", "Apple profit", {'tickers': 'AAPL', 'metrics': 'net_income'})
        self.run_test("EPS metric", "Apple EPS", {'tickers': 'AAPL', 'metrics': 'eps_diluted'})
        
        # Operating metrics
        self.run_test("EBITDA metric", "Apple EBITDA", {'tickers': 'AAPL', 'metrics': 'ebitda'})
        self.run_test("Operating income metric", "Apple operating income", {'tickers': 'AAPL', 'metrics': 'operating_income'})
        self.run_test("Gross profit metric", "Apple gross profit", {'tickers': 'AAPL', 'metrics': 'gross_profit'})
        
        # Cash flow metrics
        self.run_test("Free cash flow metric", "Apple free cash flow", {'tickers': 'AAPL', 'metrics': 'free_cash_flow'})
        self.run_test("FCF metric", "Apple FCF", {'tickers': 'AAPL', 'metrics': 'free_cash_flow'})
        
        # Return metrics
        self.run_test("ROE metric", "Apple ROE", {'tickers': 'AAPL', 'metrics': 'return_on_equity'})
        self.run_test("ROA metric", "Apple ROA", {'tickers': 'AAPL', 'metrics': 'return_on_assets'})
        self.run_test("ROIC metric", "Apple ROIC", {'tickers': 'AAPL', 'metrics': 'return_on_invested_capital'})
        
        # Valuation metrics
        self.run_test("PE ratio metric", "Apple PE ratio", {'tickers': 'AAPL', 'metrics': 'pe_ratio'})
        self.run_test("P/E metric", "Apple P/E", {'tickers': 'AAPL', 'metrics': 'pe_ratio'})
        self.run_test("PB ratio metric", "Apple PB ratio", {'tickers': 'AAPL', 'metrics': 'pb_ratio'})
        self.run_test("PEG ratio metric", "Apple PEG ratio", {'tickers': 'AAPL', 'metrics': 'peg_ratio'})
        
        # Shareholder metrics
        self.run_test("Dividend yield metric", "Apple dividend yield", {'tickers': 'AAPL', 'metrics': 'dividend_yield'})
        self.run_test("TSR metric", "Apple TSR", {'tickers': 'AAPL', 'metrics': 'tsr'})
    
    def test_time_parsing(self):
        """Test time period parsing accuracy."""
        print("=== TIME PERIOD PARSING TESTS ===")
        print()
        
        # Basic year tests
        self.run_test("Single year", "Apple revenue 2023", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'single'})
        self.run_test("Fiscal year", "Apple revenue FY2023", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'single'})
        self.run_test("Calendar year", "Apple revenue CY2023", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'single'})
        
        # Quarter tests
        self.run_test("Single quarter", "Apple revenue Q1 2024", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'single'})
        self.run_test("Fiscal quarter", "Apple revenue Q1 FY2024", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'single'})
        
        # Range tests
        self.run_test("Year range", "Apple revenue 2020-2023", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'range'})
        self.run_test("Quarter range", "Apple revenue Q1-Q4 2023", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'multi'})
        
        # Relative time tests
        self.run_test("Last quarters", "Apple revenue last 3 quarters", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'relative'})
        self.run_test("Last years", "Apple revenue last 2 years", 
                     {'tickers': 'AAPL', 'metrics': 'revenue', 'period_type': 'relative'})
    
    def test_intent_classification(self):
        """Test intent classification accuracy."""
        print("=== INTENT CLASSIFICATION TESTS ===")
        print()
        
        # Lookup intent
        self.run_test("Lookup intent", "Apple revenue 2023", 
                     {'intent': 'lookup', 'tickers': 'AAPL', 'metrics': 'revenue'})
        self.run_test("Lookup intent 2", "Microsoft earnings", 
                     {'intent': 'lookup', 'tickers': 'MSFT', 'metrics': 'net_income'})
        
        # Compare intent
        self.run_test("Compare intent", "Compare Apple and Microsoft revenue", 
                     {'intent': 'compare', 'tickers': ['AAPL', 'MSFT'], 'metrics': 'revenue'})
        self.run_test("Compare intent 2", "Apple vs Microsoft earnings", 
                     {'intent': 'compare', 'tickers': ['AAPL', 'MSFT'], 'metrics': 'net_income'})
        
        # Rank intent
        self.run_test("Rank intent", "Which company has highest revenue?", 
                     {'intent': 'rank', 'metrics': 'revenue'})
        self.run_test("Rank intent 2", "Top companies by profit margin", 
                     {'intent': 'rank', 'metrics': 'profit_margin'})
        
        # Explain intent
        self.run_test("Explain intent", "Explain EBITDA", 
                     {'intent': 'explain_metric', 'metrics': 'ebitda'})
        self.run_test("Explain intent 2", "What does ROE mean?", 
                     {'intent': 'explain_metric', 'metrics': 'return_on_equity'})
        
        # Trend intent
        self.run_test("Trend intent", "Apple revenue trend over time", 
                     {'intent': 'trend', 'tickers': 'AAPL', 'metrics': 'revenue'})
        self.run_test("Trend intent 2", "Microsoft earnings history", 
                     {'intent': 'trend', 'tickers': 'MSFT', 'metrics': 'net_income'})
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        print("=== EDGE CASE TESTS ===")
        print()
        
        # Missing ticker
        self.run_test("Missing ticker", "revenue 2023", 
                     {'warnings': ['missing_ticker', 'default_ticker:AAPL']})
        
        # Missing metric
        self.run_test("Missing metric", "Apple 2023", 
                     {'tickers': 'AAPL', 'warnings': ['missing_metric']})
        
        # Ambiguous company names
        self.run_test("Ambiguous name", "Apple Inc revenue", 
                     {'tickers': 'AAPL', 'metrics': 'revenue'})
        
        # Complex queries
        self.run_test("Complex query", "Compare Apple and Microsoft revenue growth over last 3 years", 
                     {'intent': 'compare', 'tickers': ['AAPL', 'MSFT'], 'metrics': 'revenue'})
        
        # Special characters
        self.run_test("Special characters", "Apple & Microsoft revenue", 
                     {'tickers': ['AAPL', 'MSFT'], 'metrics': 'revenue'})
    
    def run_all_tests(self):
        """Run all parsing accuracy tests."""
        print("=" * 80)
        print("BENCHMARKOS PARSING SYSTEM ACCURACY TEST SUITE")
        print("=" * 80)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all test categories
        self.test_ticker_resolution()
        self.test_metric_parsing()
        self.test_time_parsing()
        self.test_intent_classification()
        self.test_edge_cases()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = self.passed_tests
        total = self.total_tests
        failed = total - passed
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print()
        
        # Group by test type
        by_type = {}
        for result in self.test_results:
            test_type = result['type']
            if test_type not in by_type:
                by_type[test_type] = {'passed': 0, 'total': 0}
            by_type[test_type]['total'] += 1
            if result['passed']:
                by_type[test_type]['passed'] += 1
        
        print("Results by test type:")
        for test_type, stats in by_type.items():
            pct = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {test_type}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
        
        print()
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r['passed']]
        if failed_tests:
            print("FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['input']}")
                for issue in test['issues']:
                    print(f"    Issue: {issue}")
            print()
        
        # Overall assessment
        if passed / total >= 0.9:
            print("🎉 EXCELLENT: Parsing system is highly accurate!")
        elif passed / total >= 0.8:
            print("✅ GOOD: Parsing system is mostly accurate with minor issues.")
        elif passed / total >= 0.7:
            print("⚠️  FAIR: Parsing system has some accuracy issues that need attention.")
        else:
            print("❌ POOR: Parsing system has significant accuracy issues that need fixing.")
        
        print("=" * 80)

def main():
    """Main test runner."""
    tester = ParsingAccuracyTester()
    tester.run_all_tests()
    return 0 if tester.passed_tests == tester.total_tests else 1

if __name__ == "__main__":
    sys.exit(main())
