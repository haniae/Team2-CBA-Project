#!/usr/bin/env python3
"""
Advanced Deep Parsing Test Suite
Comprehensive testing for Time Period Parsing and Edge Cases
"""

import sys
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured
from finanlyzeos_chatbot.parsing.time_grammar import parse_periods
from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform

class AdvancedParsingTester:
    """Advanced test suite for deep parsing analysis."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def run_time_parsing_test(self, test_name: str, input_text: str, expected: Dict[str, Any]) -> bool:
        """Test time period parsing specifically."""
        self.total_tests += 1
        
        try:
            # Test the time_grammar module directly
            time_result = parse_periods(input_text, prefer_fiscal=True)
            
            # Test the full parsing pipeline
            full_result = parse_to_structured(input_text)
            
            passed = True
            issues = []
            
            # Check time parsing results
            if 'period_type' in expected:
                actual_type = time_result.get('type')
                if actual_type != expected['period_type']:
                    passed = False
                    issues.append(f"Period type: got '{actual_type}', expected '{expected['period_type']}'")
            
            if 'granularity' in expected:
                actual_granularity = time_result.get('granularity')
                if actual_granularity != expected['granularity']:
                    passed = False
                    issues.append(f"Granularity: got '{actual_granularity}', expected '{expected['granularity']}'")
            
            if 'items_count' in expected:
                actual_count = len(time_result.get('items', []))
                if actual_count != expected['items_count']:
                    passed = False
                    issues.append(f"Items count: got {actual_count}, expected {expected['items_count']}")
            
            # Check if fiscal preference is working
            if 'fiscal_preference' in expected:
                actual_fiscal = time_result.get('normalize_to_fiscal')
                if actual_fiscal != expected['fiscal_preference']:
                    passed = False
                    issues.append(f"Fiscal preference: got {actual_fiscal}, expected {expected['fiscal_preference']}")
            
            if passed:
                self.passed_tests += 1
                status = "✅ PASS"
            else:
                status = "❌ FAIL"
            
            self.test_results.append({
                'name': test_name,
                'input': input_text,
                'expected': expected,
                'time_result': time_result,
                'full_result': full_result,
                'passed': passed,
                'issues': issues,
                'status': status,
                'type': 'time_parsing'
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Time Result: {time_result}")
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
                'time_result': None,
                'full_result': None,
                'passed': False,
                'issues': [f"Exception: {str(e)}"],
                'status': "❌ ERROR",
                'type': 'time_parsing'
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Status: ❌ ERROR - {str(e)}")
            print()
            
            return False
    
    def run_edge_case_test(self, test_name: str, input_text: str, expected: Dict[str, Any]) -> bool:
        """Test edge cases specifically."""
        self.total_tests += 1
        
        try:
            result = parse_to_structured(input_text)
            
            passed = True
            issues = []
            
            # Check ticker resolution
            if 'expected_tickers' in expected:
                expected_tickers = expected['expected_tickers'] if isinstance(expected['expected_tickers'], list) else [expected['expected_tickers']]
                actual_tickers = [t['ticker'] for t in result.get('tickers', [])]
                
                if not all(ticker in actual_tickers for ticker in expected_tickers):
                    passed = False
                    issues.append(f"Tickers: got {actual_tickers}, expected {expected_tickers}")
            
            # Check metric resolution
            if 'expected_metrics' in expected:
                expected_metrics = expected['expected_metrics'] if isinstance(expected['expected_metrics'], list) else [expected['expected_metrics']]
                actual_metrics = [m['key'] for m in result.get('vmetrics', [])]
                
                if not all(metric in actual_metrics for metric in expected_metrics):
                    passed = False
                    issues.append(f"Metrics: got {actual_metrics}, expected {expected_metrics}")
            
            # Check intent
            if 'expected_intent' in expected:
                if result.get('intent') != expected['expected_intent']:
                    passed = False
                    issues.append(f"Intent: got '{result.get('intent')}', expected '{expected['expected_intent']}'")
            
            # Check warnings
            if 'expected_warnings' in expected:
                expected_warnings = expected['expected_warnings'] if isinstance(expected['expected_warnings'], list) else [expected['expected_warnings']]
                actual_warnings = result.get('warnings', [])
                
                if not all(warning in actual_warnings for warning in expected_warnings):
                    passed = False
                    issues.append(f"Warnings: got {actual_warnings}, expected {expected_warnings}")
            
            # Check error handling
            if 'should_have_errors' in expected:
                has_errors = len(result.get('warnings', [])) > 0
                if has_errors != expected['should_have_errors']:
                    passed = False
                    issues.append(f"Error handling: got {has_errors}, expected {expected['should_have_errors']}")
            
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
                'type': 'edge_case'
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Result: {result}")
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
                'type': 'edge_case'
            })
            
            print(f"{self.total_tests:2d}. {test_name}")
            print(f"    Input: \"{input_text}\"")
            print(f"    Status: ❌ ERROR - {str(e)}")
            print()
            
            return False
    
    def test_time_parsing_deep(self):
        """Deep test of time period parsing."""
        print("=== DEEP TIME PERIOD PARSING TESTS ===")
        print()
        
        # Test year range parsing (the failing case)
        self.run_time_parsing_test("Year range 2020-2023", "2020-2023", {
            'period_type': 'range',
            'granularity': 'calendar_year',
            'items_count': 2,
            'fiscal_preference': False
        })
        
        self.run_time_parsing_test("Year range FY2020-FY2023", "FY2020-FY2023", {
            'period_type': 'range',
            'granularity': 'fiscal_year',
            'items_count': 2,
            'fiscal_preference': True
        })
        
        # Test single year parsing
        self.run_time_parsing_test("Single year 2023", "2023", {
            'period_type': 'single',
            'granularity': 'calendar_year',
            'items_count': 1,
            'fiscal_preference': False
        })
        
        self.run_time_parsing_test("Single fiscal year FY2023", "FY2023", {
            'period_type': 'single',
            'granularity': 'fiscal_year',
            'items_count': 1,
            'fiscal_preference': True
        })
        
        # Test quarter parsing
        self.run_time_parsing_test("Single quarter Q1 2024", "Q1 2024", {
            'period_type': 'single',
            'granularity': 'calendar_quarter',
            'items_count': 1,
            'fiscal_preference': False
        })
        
        self.run_time_parsing_test("Fiscal quarter Q1 FY2024", "Q1 FY2024", {
            'period_type': 'single',
            'granularity': 'fiscal_quarter',
            'items_count': 1,
            'fiscal_preference': True
        })
        
        # Test quarter range parsing
        self.run_time_parsing_test("Quarter range Q1-Q4 2023", "Q1-Q4 2023", {
            'period_type': 'multi',
            'granularity': 'calendar_quarter',
            'items_count': 4,
            'fiscal_preference': False
        })
        
        # Test relative time parsing
        self.run_time_parsing_test("Last 3 quarters", "last 3 quarters", {
            'period_type': 'relative',
            'granularity': 'calendar_quarter',
            'fiscal_preference': False
        })
        
        self.run_time_parsing_test("Last 2 years", "last 2 years", {
            'period_type': 'relative',
            'granularity': 'calendar_year',
            'fiscal_preference': False
        })
        
        # Test complex time expressions
        self.run_time_parsing_test("Complex: Q1-Q3 2024", "Q1-Q3 2024", {
            'period_type': 'multi',
            'granularity': 'calendar_quarter',
            'items_count': 3,
            'fiscal_preference': False
        })
        
        # Test edge cases in time parsing
        self.run_time_parsing_test("Two digit year 23", "23", {
            'period_type': 'single',
            'granularity': 'calendar_year',
            'items_count': 1,
            'fiscal_preference': False
        })
        
        self.run_time_parsing_test("Calendar explicit 2023", "calendar 2023", {
            'period_type': 'single',
            'granularity': 'calendar_year',
            'items_count': 1,
            'fiscal_preference': False
        })
    
    def test_edge_cases_deep(self):
        """Deep test of edge cases."""
        print("=== DEEP EDGE CASE TESTS ===")
        print()
        
        # Test missing ticker scenarios
        self.run_edge_case_test("Missing ticker - revenue only", "revenue 2023", {
            'expected_warnings': ['missing_ticker', 'default_ticker:AAPL'],
            'should_have_errors': True
        })
        
        self.run_edge_case_test("Missing ticker - metric only", "EBITDA", {
            'expected_warnings': ['missing_ticker', 'default_ticker:AAPL'],
            'should_have_errors': True
        })
        
        # Test missing metric scenarios
        self.run_edge_case_test("Missing metric - ticker only", "Apple 2023", {
            'expected_tickers': 'AAPL',
            'expected_warnings': ['missing_metric'],
            'should_have_errors': True
        })
        
        # Test ambiguous company names
        self.run_edge_case_test("Ambiguous - Apple Inc", "Apple Inc revenue", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
        
        self.run_edge_case_test("Ambiguous - The Apple Company", "The Apple Company revenue", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
        
        # Test special characters
        self.run_edge_case_test("Special chars - Ampersand", "Apple & Microsoft revenue", {
            'expected_tickers': ['AAPL', 'MSFT'],
            'expected_metrics': 'revenue'
        })
        
        self.run_edge_case_test("Special chars - Parentheses", "Apple (AAPL) revenue", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
        
        # Test case sensitivity
        self.run_edge_case_test("Case sensitivity - lowercase", "apple revenue", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
        
        self.run_edge_case_test("Case sensitivity - mixed case", "ApPlE rEvEnUe", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
        
        # Test punctuation handling
        self.run_edge_case_test("Punctuation - Commas", "Apple, Microsoft revenue", {
            'expected_tickers': ['AAPL', 'MSFT'],
            'expected_metrics': 'revenue'
        })
        
        self.run_edge_case_test("Punctuation - Periods", "Apple. Microsoft. Revenue.", {
            'expected_tickers': ['AAPL', 'MSFT'],
            'expected_metrics': 'revenue'
        })
        
        # Test very long company names
        self.run_edge_case_test("Long name - JPMorgan Chase", "JPMorgan Chase & Co revenue", {
            'expected_tickers': 'JPM',
            'expected_metrics': 'revenue'
        })
        
        # Test numbers in company names
        self.run_edge_case_test("Numbers in name - 3M", "3M revenue", {
            'expected_tickers': 'MMM',
            'expected_metrics': 'revenue'
        })
        
        # Test empty or minimal input
        self.run_edge_case_test("Empty input", "", {
            'expected_warnings': ['missing_ticker', 'missing_metric'],
            'should_have_errors': True
        })
        
        self.run_edge_case_test("Minimal input - single word", "revenue", {
            'expected_warnings': ['missing_ticker'],
            'should_have_errors': True
        })
        
        # Test very complex queries
        self.run_edge_case_test("Complex query - multiple elements", 
                               "Compare Apple and Microsoft revenue growth over last 3 years", {
            'expected_tickers': ['AAPL', 'MSFT'],
            'expected_metrics': 'revenue',
            'expected_intent': 'compare'
        })
        
        # Test malformed input
        self.run_edge_case_test("Malformed - random characters", "asdfghjkl", {
            'expected_warnings': ['missing_ticker', 'missing_metric'],
            'should_have_errors': True
        })
        
        # Test unicode characters
        self.run_edge_case_test("Unicode - accented characters", "Apple révénue", {
            'expected_tickers': 'AAPL',
            'expected_metrics': 'revenue'
        })
    
    def test_berkshire_hathaway_issue(self):
        """Test the specific Berkshire Hathaway ticker issue."""
        print("=== BERKSHIRE HATHAWAY TICKER ISSUE ===")
        print()
        
        # Test different variations of Berkshire Hathaway
        variations = [
            "Berkshire Hathaway",
            "Berkshire Hathaway Inc",
            "Berkshire Hathaway Class B",
            "Berkshire Class B",
            "Berkshire B",
            "BRK.B",
            "BRK-B"
        ]
        
        for variation in variations:
            self.run_edge_case_test(f"Berkshire variation: {variation}", variation, {
                'expected_tickers': 'BRK.B'
            })
    
    def run_all_deep_tests(self):
        """Run all deep parsing tests."""
        print("=" * 80)
        print("ADVANCED DEEP PARSING ANALYSIS")
        print("=" * 80)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run deep tests
        self.test_time_parsing_deep()
        self.test_edge_cases_deep()
        self.test_berkshire_hathaway_issue()
        
        # Print detailed summary
        self.print_detailed_summary()
    
    def print_detailed_summary(self):
        """Print detailed test summary."""
        print("=" * 80)
        print("DETAILED TEST SUMMARY")
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
                by_type[test_type] = {'passed': 0, 'total': 0, 'failed': []}
            by_type[test_type]['total'] += 1
            if result['passed']:
                by_type[test_type]['passed'] += 1
            else:
                by_type[test_type]['failed'].append(result)
        
        print("Results by test type:")
        for test_type, stats in by_type.items():
            pct = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"  {test_type}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
            
            # Show failed tests for this type
            if stats['failed']:
                print(f"    Failed tests:")
                for failed_test in stats['failed']:
                    print(f"      - {failed_test['name']}: {failed_test['input']}")
                    for issue in failed_test['issues']:
                        print(f"        Issue: {issue}")
        print()
        
        # Root cause analysis
        print("ROOT CAUSE ANALYSIS:")
        print("=" * 40)
        
        time_failures = [r for r in self.test_results if r['type'] == 'time_parsing' and not r['passed']]
        edge_failures = [r for r in self.test_results if r['type'] == 'edge_case' and not r['passed']]
        
        if time_failures:
            print("Time Parsing Issues:")
            for failure in time_failures:
                print(f"  - {failure['name']}: {failure['input']}")
                print(f"    Expected: {failure['expected']}")
                print(f"    Actual: {failure['time_result']}")
                print()
        
        if edge_failures:
            print("Edge Case Issues:")
            for failure in edge_failures:
                print(f"  - {failure['name']}: {failure['input']}")
                print(f"    Expected: {failure['expected']}")
                print(f"    Actual: {failure['actual']}")
                print()
        
        print("=" * 80)

def main():
    """Main test runner."""
    tester = AdvancedParsingTester()
    tester.run_all_deep_tests()
    return 0 if tester.passed_tests == tester.total_tests else 1

if __name__ == "__main__":
    sys.exit(main())
