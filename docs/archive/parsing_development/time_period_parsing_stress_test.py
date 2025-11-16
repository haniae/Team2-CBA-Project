#!/usr/bin/env python3
"""
Time Period Parsing Stress Test - 200 Test Cases
Comprehensive testing of time period parsing with various formats and edge cases
"""

import sys
import os
import random
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured
from finanlyzeos_chatbot.parsing.time_grammar import parse_periods

class TimePeriodStressTester:
    """Stress test suite for time period parsing with 200 test cases."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def generate_test_cases(self) -> List[Dict[str, Any]]:
        """Generate 200 comprehensive test cases for time period parsing."""
        test_cases = []
        
        # Basic year tests (20 cases)
        years = [2020, 2021, 2022, 2023, 2024, 2025]
        for year in years:
            test_cases.extend([
                {
                    'input': f'Apple revenue {year}',
                    'expected_type': 'single',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Basic year {year}'
                },
                {
                    'input': f'Apple revenue FY{year}',
                    'expected_type': 'single',
                    'expected_granularity': 'fiscal_year',
                    'expected_fiscal': True,
                    'description': f'Fiscal year FY{year}'
                },
                {
                    'input': f'Apple revenue CY{year}',
                    'expected_type': 'single',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Calendar year CY{year}'
                },
                {
                    'input': f'Apple revenue calendar {year}',
                    'expected_type': 'single',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Explicit calendar {year}'
                }
            ])
        
        # Two-digit years (10 cases)
        two_digit_years = [20, 21, 22, 23, 24, 25, 30, 31, 32, 33]
        for year in two_digit_years:
            test_cases.append({
                'input': f'Apple revenue {year}',
                'expected_type': 'single',
                'expected_granularity': 'calendar_year',
                'expected_fiscal': False,
                'description': f'Two-digit year {year}'
            })
        
        # Year ranges (20 cases)
        year_pairs = [(2020, 2023), (2021, 2024), (2022, 2025), (2019, 2022), (2020, 2024)]
        for start_year, end_year in year_pairs:
            test_cases.extend([
                {
                    'input': f'Apple revenue {start_year}-{end_year}',
                    'expected_type': 'range',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Year range {start_year}-{end_year}'
                },
                {
                    'input': f'Apple revenue FY{start_year}-FY{end_year}',
                    'expected_type': 'range',
                    'expected_granularity': 'fiscal_year',
                    'expected_fiscal': True,
                    'description': f'Fiscal year range FY{start_year}-FY{end_year}'
                },
                {
                    'input': f'Apple revenue CY{start_year}-CY{end_year}',
                    'expected_type': 'range',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Calendar year range CY{start_year}-CY{end_year}'
                },
                {
                    'input': f'Apple revenue {start_year} to {end_year}',
                    'expected_type': 'range',
                    'expected_granularity': 'calendar_year',
                    'expected_fiscal': False,
                    'description': f'Year range with "to" {start_year} to {end_year}'
                }
            ])
        
        # Quarter tests (40 cases)
        quarters = [1, 2, 3, 4]
        years = [2023, 2024, 2025]
        for year in years:
            for quarter in quarters:
                test_cases.extend([
                    {
                        'input': f'Apple revenue Q{quarter} {year}',
                        'expected_type': 'single',
                        'expected_granularity': 'calendar_quarter',
                        'expected_fiscal': False,
                        'description': f'Quarter Q{quarter} {year}'
                    },
                    {
                        'input': f'Apple revenue Q{quarter} FY{year}',
                        'expected_type': 'single',
                        'expected_granularity': 'fiscal_quarter',
                        'expected_fiscal': True,
                        'description': f'Fiscal quarter Q{quarter} FY{year}'
                    },
                    {
                        'input': f'Apple revenue Q{quarter} CY{year}',
                        'expected_type': 'single',
                        'expected_granularity': 'calendar_quarter',
                        'expected_fiscal': False,
                        'description': f'Calendar quarter Q{quarter} CY{year}'
                    },
                    {
                        'input': f'Apple revenue Q{quarter} calendar {year}',
                        'expected_type': 'single',
                        'expected_granularity': 'calendar_quarter',
                        'expected_fiscal': False,
                        'description': f'Explicit calendar quarter Q{quarter} {year}'
                    }
                ])
        
        # Quarter ranges (20 cases)
        quarter_ranges = [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]
        for start_q, end_q in quarter_ranges:
            test_cases.extend([
                {
                    'input': f'Apple revenue Q{start_q}-Q{end_q} 2024',
                    'expected_type': 'multi',
                    'expected_granularity': 'calendar_quarter',
                    'expected_fiscal': False,
                    'description': f'Quarter range Q{start_q}-Q{end_q} 2024'
                },
                {
                    'input': f'Apple revenue Q{start_q}-Q{end_q} FY2024',
                    'expected_type': 'multi',
                    'expected_granularity': 'fiscal_quarter',
                    'expected_fiscal': True,
                    'description': f'Fiscal quarter range Q{start_q}-Q{end_q} FY2024'
                },
                {
                    'input': f'Apple revenue Q{start_q} to Q{end_q} 2024',
                    'expected_type': 'multi',
                    'expected_granularity': 'calendar_quarter',
                    'expected_fiscal': False,
                    'description': f'Quarter range with "to" Q{start_q} to Q{end_q} 2024'
                }
            ])
        
        # Relative time tests (20 cases)
        relative_tests = [
            ('last 1 quarter', 'relative', 'calendar_quarter', False),
            ('last 2 quarters', 'relative', 'calendar_quarter', False),
            ('last 3 quarters', 'relative', 'calendar_quarter', False),
            ('last 4 quarters', 'relative', 'calendar_quarter', False),
            ('last 1 year', 'relative', 'calendar_year', False),
            ('last 2 years', 'relative', 'calendar_year', False),
            ('last 3 years', 'relative', 'calendar_year', False),
            ('last 5 years', 'relative', 'calendar_year', False),
            ('past 1 quarter', 'relative', 'calendar_quarter', False),
            ('past 2 quarters', 'relative', 'calendar_quarter', False),
            ('past 1 year', 'relative', 'calendar_year', False),
            ('past 2 years', 'relative', 'calendar_year', False),
            ('previous 1 quarter', 'relative', 'calendar_quarter', False),
            ('previous 2 quarters', 'relative', 'calendar_quarter', False),
            ('previous 1 year', 'relative', 'calendar_year', False),
            ('previous 2 years', 'relative', 'calendar_year', False),
            ('recent 1 quarter', 'relative', 'calendar_quarter', False),
            ('recent 2 quarters', 'relative', 'calendar_quarter', False),
            ('recent 1 year', 'relative', 'calendar_year', False),
            ('recent 2 years', 'relative', 'calendar_year', False)
        ]
        
        for input_text, expected_type, expected_granularity, expected_fiscal in relative_tests:
            test_cases.append({
                'input': f'Apple revenue {input_text}',
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': expected_fiscal,
                'description': f'Relative time: {input_text}'
            })
        
        # Complex combinations (20 cases)
        complex_tests = [
            'Apple revenue 2023 and 2024',
            'Apple revenue Q1 2023 and Q2 2024',
            'Apple revenue 2020, 2021, 2022',
            'Apple revenue Q1, Q2, Q3 2024',
            'Apple revenue 2023 vs 2024',
            'Apple revenue Q1 2023 vs Q1 2024',
            'Apple revenue 2020-2022 and 2023-2024',
            'Apple revenue Q1-Q2 2023 and Q3-Q4 2024',
            'Apple revenue 2023 annual',
            'Apple revenue Q1 2024 quarterly',
            'Apple revenue 2023 yearly',
            'Apple revenue Q1 2024 quarterly results',
            'Apple revenue 2023 annual results',
            'Apple revenue Q1 2024 quarterly earnings',
            'Apple revenue 2023 yearly performance',
            'Apple revenue Q1 2024 quarterly growth',
            'Apple revenue 2023 annual growth',
            'Apple revenue Q1 2024 quarterly revenue',
            'Apple revenue 2023 annual revenue',
            'Apple revenue Q1 2024 quarterly profit'
        ]
        
        for input_text in complex_tests:
            test_cases.append({
                'input': input_text,
                'expected_type': 'multi',  # Most complex cases are multi
                'expected_granularity': 'calendar_year',  # Default assumption
                'expected_fiscal': False,
                'description': f'Complex: {input_text}'
            })
        
        # Edge cases (20 cases)
        edge_cases = [
            'Apple revenue',
            'Apple revenue latest',
            'Apple revenue current',
            'Apple revenue most recent',
            'Apple revenue recent',
            'Apple revenue latest quarter',
            'Apple revenue latest year',
            'Apple revenue current quarter',
            'Apple revenue current year',
            'Apple revenue this quarter',
            'Apple revenue this year',
            'Apple revenue present',
            'Apple revenue now',
            'Apple revenue today',
            'Apple revenue 2023-2023',  # Same year range
            'Apple revenue Q1-Q1 2024',  # Same quarter range
            'Apple revenue 2023-2022',  # Reverse range
            'Apple revenue Q4-Q1 2024',  # Reverse quarter range
            'Apple revenue 2023-2023-2024',  # Invalid format
            'Apple revenue Q1-Q2-Q3 2024'  # Invalid format
        ]
        
        for input_text in edge_cases:
            test_cases.append({
                'input': input_text,
                'expected_type': 'latest',  # Most edge cases default to latest
                'expected_granularity': 'calendar_year',
                'expected_fiscal': False,
                'description': f'Edge case: {input_text}'
            })
        
        # Mixed company and metric tests (20 cases)
        companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'Tesla']
        metrics = ['revenue', 'earnings', 'profit', 'EBITDA', 'cash flow']
        years = [2023, 2024]
        quarters = [1, 2, 3, 4]
        
        for company in companies:
            for metric in metrics:
                for year in years:
                    test_cases.append({
                        'input': f'{company} {metric} {year}',
                        'expected_type': 'single',
                        'expected_granularity': 'calendar_year',
                        'expected_fiscal': False,
                        'description': f'Company metric: {company} {metric} {year}'
                    })
        
        # Ensure we have exactly 200 test cases
        return test_cases[:200]
    
    def run_single_test(self, test_case: Dict[str, Any]) -> bool:
        """Run a single test case."""
        self.total_tests += 1
        
        try:
            result = parse_to_structured(test_case['input'])
            periods = result.get('periods', {})
            
            # Check results
            actual_type = periods.get('type')
            actual_granularity = periods.get('granularity')
            actual_fiscal = periods.get('normalize_to_fiscal')
            
            expected_type = test_case['expected_type']
            expected_granularity = test_case['expected_granularity']
            expected_fiscal = test_case['expected_fiscal']
            
            # Determine if test passed
            type_match = actual_type == expected_type
            granularity_match = actual_granularity == expected_granularity
            fiscal_match = actual_fiscal == expected_fiscal
            
            passed = type_match and granularity_match and fiscal_match
            
            if passed:
                self.passed_tests += 1
                status = "✅ PASS"
            else:
                self.failed_tests += 1
                status = "❌ FAIL"
            
            # Store result
            self.test_results.append({
                'input': test_case['input'],
                'description': test_case['description'],
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': expected_fiscal,
                'actual_type': actual_type,
                'actual_granularity': actual_granularity,
                'actual_fiscal': actual_fiscal,
                'type_match': type_match,
                'granularity_match': granularity_match,
                'fiscal_match': fiscal_match,
                'passed': passed,
                'status': status
            })
            
            return passed
            
        except Exception as e:
            self.failed_tests += 1
            self.test_results.append({
                'input': test_case['input'],
                'description': test_case['description'],
                'expected_type': test_case['expected_type'],
                'expected_granularity': test_case['expected_granularity'],
                'expected_fiscal': test_case['expected_fiscal'],
                'actual_type': None,
                'actual_granularity': None,
                'actual_fiscal': None,
                'type_match': False,
                'granularity_match': False,
                'fiscal_match': False,
                'passed': False,
                'status': f"❌ ERROR: {str(e)}"
            })
            
            return False
    
    def run_stress_test(self):
        """Run the complete stress test with 200 test cases."""
        print("=" * 80)
        print("TIME PERIOD PARSING STRESS TEST - 200 TEST CASES")
        print("=" * 80)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Generate test cases
        test_cases = self.generate_test_cases()
        print(f"Generated {len(test_cases)} test cases")
        print()
        
        # Run tests
        for i, test_case in enumerate(test_cases, 1):
            if i % 50 == 0 or i <= 10:
                print(f"Running test {i}/200: {test_case['description']}")
            
            self.run_single_test(test_case)
        
        # Print results
        self.print_results()
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 80)
        print("STRESS TEST RESULTS")
        print("=" * 80)
        
        print(f"Total tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)")
        print(f"Failed: {self.failed_tests} ({self.failed_tests/self.total_tests*100:.1f}%)")
        print()
        
        # Group by test type
        by_type = {}
        for result in self.test_results:
            if 'Basic year' in result['description']:
                test_type = 'Basic Years'
            elif 'Fiscal year' in result['description']:
                test_type = 'Fiscal Years'
            elif 'Calendar year' in result['description']:
                test_type = 'Calendar Years'
            elif 'Two-digit year' in result['description']:
                test_type = 'Two-digit Years'
            elif 'Year range' in result['description']:
                test_type = 'Year Ranges'
            elif 'Quarter' in result['description']:
                test_type = 'Quarters'
            elif 'Quarter range' in result['description']:
                test_type = 'Quarter Ranges'
            elif 'Relative time' in result['description']:
                test_type = 'Relative Time'
            elif 'Complex' in result['description']:
                test_type = 'Complex Cases'
            elif 'Edge case' in result['description']:
                test_type = 'Edge Cases'
            elif 'Company metric' in result['description']:
                test_type = 'Company Metrics'
            else:
                test_type = 'Other'
            
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
                for failed_test in stats['failed'][:5]:  # Show first 5 failures
                    print(f"      - {failed_test['description']}: {failed_test['input']}")
                    if not failed_test['type_match']:
                        print(f"        Type: got '{failed_test['actual_type']}', expected '{failed_test['expected_type']}'")
                    if not failed_test['granularity_match']:
                        print(f"        Granularity: got '{failed_test['actual_granularity']}', expected '{failed_test['expected_granularity']}'")
                    if not failed_test['fiscal_match']:
                        print(f"        Fiscal: got {failed_test['actual_fiscal']}, expected {failed_test['expected_fiscal']}")
                if len(stats['failed']) > 5:
                    print(f"      ... and {len(stats['failed']) - 5} more failures")
        print()
        
        # Overall assessment
        if self.passed_tests / self.total_tests >= 0.95:
            print("🎉 EXCELLENT: Time period parsing is highly accurate!")
        elif self.passed_tests / self.total_tests >= 0.90:
            print("✅ VERY GOOD: Time period parsing is mostly accurate with minor issues.")
        elif self.passed_tests / self.total_tests >= 0.80:
            print("⚠️  GOOD: Time period parsing has some accuracy issues that need attention.")
        else:
            print("❌ NEEDS IMPROVEMENT: Time period parsing has significant accuracy issues.")
        
        print("=" * 80)

def main():
    """Main test runner."""
    tester = TimePeriodStressTester()
    tester.run_stress_test()
    return 0 if tester.passed_tests == tester.total_tests else 1

if __name__ == "__main__":
    sys.exit(main())
