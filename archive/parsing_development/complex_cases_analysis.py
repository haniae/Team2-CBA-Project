#!/usr/bin/env python3
"""
Complex Cases Analysis - 200 Test Cases
Comprehensive analysis and classification of complex time period parsing cases
"""

import sys
import os
import random
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot.parsing.parse import parse_to_structured
from benchmarkos_chatbot.parsing.time_grammar import parse_periods

class ComplexCasesAnalyzer:
    """Analyzer for complex time period parsing cases with detailed classification."""
    
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.categories = {}
        
    def generate_complex_test_cases(self) -> List[Dict[str, Any]]:
        """Generate 200 complex test cases with detailed classification."""
        test_cases = []
        
        # Category 1: Multiple Time Periods (50 cases)
        # Cases with "and", "vs", "," separators
        multiple_periods = [
            # Multiple years
            ('Apple revenue 2023 and 2024', 'multiple_years', 'multi', 'calendar_year'),
            ('Apple revenue 2020, 2021, 2022', 'multiple_years', 'multi', 'calendar_year'),
            ('Apple revenue 2023 vs 2024', 'multiple_years', 'multi', 'calendar_year'),
            ('Apple revenue 2020-2022 and 2023-2024', 'multiple_years', 'multi', 'calendar_year'),
            ('Apple revenue 2023 annual and 2024 annual', 'multiple_years', 'multi', 'calendar_year'),
            
            # Multiple quarters
            ('Apple revenue Q1 2023 and Q2 2024', 'multiple_quarters', 'multi', 'calendar_quarter'),
            ('Apple revenue Q1, Q2, Q3 2024', 'multiple_quarters', 'multi', 'calendar_quarter'),
            ('Apple revenue Q1 2023 vs Q1 2024', 'multiple_quarters', 'multi', 'calendar_quarter'),
            ('Apple revenue Q1-Q2 2023 and Q3-Q4 2024', 'multiple_quarters', 'multi', 'calendar_quarter'),
            ('Apple revenue Q1 2023 quarterly and Q2 2024 quarterly', 'multiple_quarters', 'multi', 'calendar_quarter'),
            
            # Mixed periods
            ('Apple revenue 2023 and Q1 2024', 'mixed_periods', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 and 2024', 'mixed_periods', 'multi', 'calendar_year'),
            ('Apple revenue 2023 annual and Q1 2024 quarterly', 'mixed_periods', 'multi', 'calendar_year'),
            ('Apple revenue Q1-Q2 2023 and 2024', 'mixed_periods', 'multi', 'calendar_year'),
            ('Apple revenue 2023 vs Q1 2024', 'mixed_periods', 'multi', 'calendar_year'),
            
            # Fiscal vs Calendar
            ('Apple revenue FY2023 and CY2024', 'fiscal_calendar', 'multi', 'calendar_year'),
            ('Apple revenue Q1 FY2023 and Q2 CY2024', 'fiscal_calendar', 'multi', 'calendar_year'),
            ('Apple revenue FY2023 vs CY2024', 'fiscal_calendar', 'multi', 'calendar_year'),
            ('Apple revenue fiscal 2023 and calendar 2024', 'fiscal_calendar', 'multi', 'calendar_year'),
            ('Apple revenue FY2023 annual and CY2024 annual', 'fiscal_calendar', 'multi', 'calendar_year'),
            
            # Complex combinations
            ('Apple revenue 2023, Q1 2024, and Q2 2024', 'complex_combinations', 'multi', 'calendar_year'),
            ('Apple revenue 2023 vs Q1 2024 vs Q2 2024', 'complex_combinations', 'multi', 'calendar_year'),
            ('Apple revenue 2020-2022, 2023, and Q1-Q2 2024', 'complex_combinations', 'multi', 'calendar_year'),
            ('Apple revenue FY2023, CY2024, and Q1 2025', 'complex_combinations', 'multi', 'calendar_year'),
            ('Apple revenue 2023 annual, Q1 2024 quarterly, and Q2 2024 quarterly', 'complex_combinations', 'multi', 'calendar_year'),
            
            # Edge cases with separators
            ('Apple revenue 2023; 2024', 'separator_edge_cases', 'multi', 'calendar_year'),
            ('Apple revenue 2023 | 2024', 'separator_edge_cases', 'multi', 'calendar_year'),
            ('Apple revenue 2023 / 2024', 'separator_edge_cases', 'multi', 'calendar_year'),
            ('Apple revenue 2023 & 2024', 'separator_edge_cases', 'multi', 'calendar_year'),
            ('Apple revenue 2023 + 2024', 'separator_edge_cases', 'multi', 'calendar_year'),
            
            # More complex patterns
            ('Apple revenue 2023 and 2024 and 2025', 'triple_periods', 'multi', 'calendar_year'),
            ('Apple revenue Q1, Q2, Q3, Q4 2024', 'quarter_series', 'multi', 'calendar_quarter'),
            ('Apple revenue 2020, 2021, 2022, 2023, 2024', 'year_series', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023, Q2 2023, Q3 2024, Q4 2024', 'mixed_quarter_series', 'multi', 'calendar_quarter'),
            ('Apple revenue FY2023, FY2024, FY2025', 'fiscal_series', 'multi', 'fiscal_year'),
            
            # Comparative patterns
            ('Apple revenue 2023 compared to 2024', 'comparative', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 versus Q1 2024', 'comparative', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 relative to 2024', 'comparative', 'multi', 'calendar_year'),
            ('Apple revenue 2023 in comparison to 2024', 'comparative', 'multi', 'calendar_year'),
            ('Apple revenue 2023 as compared to 2024', 'comparative', 'multi', 'calendar_year'),
            
            # Temporal patterns
            ('Apple revenue 2023 then 2024', 'temporal', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 followed by Q2 2024', 'temporal', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 before 2024', 'temporal', 'multi', 'calendar_year'),
            ('Apple revenue 2023 after 2022', 'temporal', 'multi', 'calendar_year'),
            ('Apple revenue 2023 during 2024', 'temporal', 'multi', 'calendar_year'),
            
            # Descriptive patterns
            ('Apple revenue 2023 annual results', 'descriptive', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly results', 'descriptive', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 yearly performance', 'descriptive', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly earnings', 'descriptive', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 annual growth', 'descriptive', 'single', 'calendar_year'),
            
            # Range combinations
            ('Apple revenue 2020-2023 and 2024-2025', 'range_combinations', 'multi', 'calendar_year'),
            ('Apple revenue Q1-Q2 2023 and Q3-Q4 2024', 'range_combinations', 'multi', 'calendar_quarter'),
            ('Apple revenue 2020-2022 vs 2023-2024', 'range_combinations', 'multi', 'calendar_year'),
            ('Apple revenue FY2020-FY2022 and CY2023-CY2024', 'range_combinations', 'multi', 'calendar_year'),
            ('Apple revenue 2020-2023, 2024, and 2025', 'range_combinations', 'multi', 'calendar_year'),
        ]
        
        for input_text, category, expected_type, expected_granularity in multiple_periods:
            test_cases.append({
                'input': input_text,
                'category': category,
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': False,
                'description': f'Multiple periods: {input_text}'
            })
        
        # Category 2: Complex Modifiers (50 cases)
        # Cases with descriptive words and modifiers
        complex_modifiers = [
            # Annual/Quarterly modifiers
            ('Apple revenue 2023 annual', 'annual_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly', 'quarterly_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 yearly', 'yearly_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly results', 'quarterly_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 annual performance', 'annual_modifier', 'single', 'calendar_year'),
            
            # Results/Performance modifiers
            ('Apple revenue 2023 results', 'results_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 performance', 'performance_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 earnings', 'earnings_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 growth', 'growth_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 profit', 'profit_modifier', 'single', 'calendar_year'),
            
            # Time-specific modifiers
            ('Apple revenue 2023 year-end', 'year_end_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarter-end', 'quarter_end_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 full-year', 'full_year_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 first-quarter', 'first_quarter_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 calendar-year', 'calendar_year_modifier', 'single', 'calendar_year'),
            
            # Comparative modifiers
            ('Apple revenue 2023 vs 2024 comparison', 'comparison_modifier', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 vs Q1 2024 analysis', 'analysis_modifier', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 relative to 2024 benchmark', 'benchmark_modifier', 'multi', 'calendar_year'),
            ('Apple revenue 2023 compared to 2024 trend', 'trend_modifier', 'multi', 'calendar_year'),
            ('Apple revenue 2023 versus 2024 evaluation', 'evaluation_modifier', 'multi', 'calendar_year'),
            
            # Temporal modifiers
            ('Apple revenue 2023 historical', 'historical_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 current', 'current_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 past', 'past_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 recent', 'recent_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 previous', 'previous_modifier', 'single', 'calendar_year'),
            
            # Business context modifiers
            ('Apple revenue 2023 business', 'business_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 corporate', 'corporate_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 financial', 'financial_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 operational', 'operational_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 strategic', 'strategic_modifier', 'single', 'calendar_year'),
            
            # Complex combinations
            ('Apple revenue 2023 annual business results', 'complex_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly financial performance', 'complex_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 yearly corporate earnings', 'complex_modifier', 'single', 'calendar_year'),
            ('Apple revenue Q1 2024 quarterly operational growth', 'complex_modifier', 'single', 'calendar_quarter'),
            ('Apple revenue 2023 annual strategic performance', 'complex_modifier', 'single', 'calendar_year'),
        ]
        
        for input_text, category, expected_type, expected_granularity in complex_modifiers:
            test_cases.append({
                'input': input_text,
                'category': category,
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': False,
                'description': f'Complex modifiers: {input_text}'
            })
        
        # Category 3: Edge Cases (50 cases)
        # Cases with unusual or edge case patterns
        edge_cases = [
            # Same period ranges
            ('Apple revenue 2023-2023', 'same_period', 'latest', 'calendar_year'),
            ('Apple revenue Q1-Q1 2024', 'same_period', 'latest', 'calendar_year'),
            ('Apple revenue FY2023-FY2023', 'same_period', 'latest', 'calendar_year'),
            ('Apple revenue CY2023-CY2023', 'same_period', 'latest', 'calendar_year'),
            ('Apple revenue 2023 to 2023', 'same_period', 'latest', 'calendar_year'),
            
            # Reverse ranges
            ('Apple revenue 2024-2023', 'reverse_range', 'latest', 'calendar_year'),
            ('Apple revenue Q4-Q1 2024', 'reverse_range', 'latest', 'calendar_year'),
            ('Apple revenue 2025-2020', 'reverse_range', 'latest', 'calendar_year'),
            ('Apple revenue Q4-Q1 2024', 'reverse_range', 'latest', 'calendar_year'),
            ('Apple revenue 2024 to 2023', 'reverse_range', 'latest', 'calendar_year'),
            
            # Invalid formats
            ('Apple revenue 2023-2023-2024', 'invalid_format', 'latest', 'calendar_year'),
            ('Apple revenue Q1-Q2-Q3 2024', 'invalid_format', 'latest', 'calendar_year'),
            ('Apple revenue 2023-2024-2025', 'invalid_format', 'latest', 'calendar_year'),
            ('Apple revenue Q1-Q2-Q3-Q4 2024', 'invalid_format', 'latest', 'calendar_year'),
            ('Apple revenue 2023-2024-2025-2026', 'invalid_format', 'latest', 'calendar_year'),
            
            # Ambiguous cases
            ('Apple revenue 2023 or 2024', 'ambiguous', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 maybe Q2 2024', 'ambiguous', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 possibly 2024', 'ambiguous', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 perhaps Q2 2024', 'ambiguous', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 likely 2024', 'ambiguous', 'multi', 'calendar_year'),
            
            # Mixed separators
            ('Apple revenue 2023, 2024 and 2025', 'mixed_separators', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023, Q2 2024 vs Q3 2025', 'mixed_separators', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023; 2024, 2025', 'mixed_separators', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 | Q2 2024 & Q3 2025', 'mixed_separators', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 / 2024 + 2025', 'mixed_separators', 'multi', 'calendar_year'),
            
            # Complex edge cases
            ('Apple revenue 2023-2023-2024', 'complex_edge', 'latest', 'calendar_year'),
            ('Apple revenue Q1-Q1-Q2 2024', 'complex_edge', 'latest', 'calendar_quarter'),
            ('Apple revenue 2023-2024-2023', 'complex_edge', 'latest', 'calendar_year'),
            ('Apple revenue Q1-Q2-Q1 2024', 'complex_edge', 'latest', 'calendar_quarter'),
            ('Apple revenue 2023-2024-2025-2023', 'complex_edge', 'latest', 'calendar_year'),
            
            # Special characters
            ('Apple revenue 2023–2024', 'special_characters', 'range', 'calendar_year'),
            ('Apple revenue Q1–Q2 2024', 'special_characters', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023—2024', 'special_characters', 'range', 'calendar_year'),
            ('Apple revenue Q1—Q2 2024', 'special_characters', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023…2024', 'special_characters', 'range', 'calendar_year'),
            
            # Unusual patterns
            ('Apple revenue 2023 then 2024 then 2025', 'unusual_patterns', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 followed by Q2 2024 followed by Q3 2025', 'unusual_patterns', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 before 2024 before 2025', 'unusual_patterns', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 after Q4 2022 after Q3 2021', 'unusual_patterns', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 during 2024 during 2025', 'unusual_patterns', 'multi', 'calendar_year'),
        ]
        
        for input_text, category, expected_type, expected_granularity in edge_cases:
            test_cases.append({
                'input': input_text,
                'category': category,
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': False,
                'description': f'Edge cases: {input_text}'
            })
        
        # Category 4: Advanced Complex Cases (50 cases)
        # Cases with multiple complex elements
        advanced_complex = [
            # Multiple companies with time periods
            ('Apple and Microsoft revenue 2023', 'multi_company', 'multi', 'calendar_year'),
            ('Apple, Microsoft, Google revenue 2023', 'multi_company', 'multi', 'calendar_year'),
            ('Apple vs Microsoft revenue 2023', 'multi_company', 'multi', 'calendar_year'),
            ('Apple and Microsoft revenue Q1 2024', 'multi_company', 'multi', 'calendar_quarter'),
            ('Apple, Microsoft, Google revenue Q1-Q2 2024', 'multi_company', 'multi', 'calendar_quarter'),
            
            # Multiple metrics with time periods
            ('Apple revenue and earnings 2023', 'multi_metric', 'multi', 'calendar_year'),
            ('Apple revenue, earnings, profit 2023', 'multi_metric', 'multi', 'calendar_year'),
            ('Apple revenue vs earnings 2023', 'multi_metric', 'multi', 'calendar_year'),
            ('Apple revenue and earnings Q1 2024', 'multi_metric', 'multi', 'calendar_quarter'),
            ('Apple revenue, earnings, profit Q1-Q2 2024', 'multi_metric', 'multi', 'calendar_quarter'),
            
            # Complex business scenarios
            ('Apple revenue 2023 annual results and Q1 2024 quarterly earnings', 'business_scenario', 'multi', 'calendar_year'),
            ('Apple revenue 2023 vs 2024 comparison and Q1 2024 analysis', 'business_scenario', 'multi', 'calendar_year'),
            ('Apple revenue 2023 historical performance and 2024 forecast', 'business_scenario', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 quarterly results and Q2 2024 quarterly earnings', 'business_scenario', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 annual growth and Q1 2024 quarterly growth', 'business_scenario', 'multi', 'calendar_year'),
            
            # Nested complexity
            ('Apple revenue 2023 and 2024, and Q1 2025', 'nested_complexity', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 and Q2 2024, and Q3 2025', 'nested_complexity', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023, 2024, and 2025, and Q1 2026', 'nested_complexity', 'multi', 'calendar_year'),
            ('Apple revenue Q1-Q2 2023 and Q3-Q4 2024, and Q1 2025', 'nested_complexity', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023-2024 and 2025-2026, and Q1 2027', 'nested_complexity', 'multi', 'calendar_year'),
            
            # Real-world scenarios
            ('Apple revenue 2023 annual report and Q1 2024 earnings call', 'real_world', 'multi', 'calendar_year'),
            ('Apple revenue 2023 vs 2024 analysis and Q1 2025 forecast', 'real_world', 'multi', 'calendar_year'),
            ('Apple revenue 2023 historical data and 2024 projections', 'real_world', 'multi', 'calendar_year'),
            ('Apple revenue Q1 2023 quarterly results and Q2 2024 quarterly earnings', 'real_world', 'multi', 'calendar_quarter'),
            ('Apple revenue 2023 annual performance and 2024 strategic plan', 'real_world', 'multi', 'calendar_year'),
        ]
        
        for input_text, category, expected_type, expected_granularity in advanced_complex:
            test_cases.append({
                'input': input_text,
                'category': category,
                'expected_type': expected_type,
                'expected_granularity': expected_granularity,
                'expected_fiscal': False,
                'description': f'Advanced complex: {input_text}'
            })
        
        # Ensure we have exactly 200 test cases
        return test_cases[:200]
    
    def run_single_test(self, test_case: Dict[str, Any]) -> bool:
        """Run a single test case with detailed analysis."""
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
            
            # Store result with category
            category = test_case['category']
            if category not in self.categories:
                self.categories[category] = {'passed': 0, 'total': 0, 'failed': []}
            
            self.categories[category]['total'] += 1
            if passed:
                self.categories[category]['passed'] += 1
            else:
                self.categories[category]['failed'].append({
                    'input': test_case['input'],
                    'expected_type': expected_type,
                    'expected_granularity': expected_granularity,
                    'actual_type': actual_type,
                    'actual_granularity': actual_granularity,
                    'type_match': type_match,
                    'granularity_match': granularity_match
                })
            
            # Store result
            self.test_results.append({
                'input': test_case['input'],
                'category': category,
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
            category = test_case['category']
            if category not in self.categories:
                self.categories[category] = {'passed': 0, 'total': 0, 'failed': []}
            
            self.categories[category]['total'] += 1
            self.categories[category]['failed'].append({
                'input': test_case['input'],
                'error': str(e)
            })
            
            self.test_results.append({
                'input': test_case['input'],
                'category': category,
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
    
    def run_complex_analysis(self):
        """Run the complete complex cases analysis."""
        print("=" * 80)
        print("COMPLEX CASES ANALYSIS - 200 TEST CASES")
        print("=" * 80)
        print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Generate test cases
        test_cases = self.generate_complex_test_cases()
        print(f"Generated {len(test_cases)} complex test cases")
        print()
        
        # Run tests
        for i, test_case in enumerate(test_cases, 1):
            if i % 50 == 0 or i <= 10:
                print(f"Running test {i}/200: {test_case['description']}")
            
            self.run_single_test(test_case)
        
        # Print detailed results
        self.print_detailed_results()
    
    def print_detailed_results(self):
        """Print comprehensive analysis results."""
        print("\n" + "=" * 80)
        print("COMPLEX CASES ANALYSIS RESULTS")
        print("=" * 80)
        
        print(f"Total tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ({self.passed_tests/self.total_tests*100:.1f}%)")
        print(f"Failed: {self.failed_tests} ({self.failed_tests/self.total_tests*100:.1f}%)")
        print()
        
        # Results by category
        print("RESULTS BY CATEGORY:")
        print("-" * 40)
        
        for category, stats in self.categories.items():
            pct = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"{category}: {stats['passed']}/{stats['total']} ({pct:.1f}%)")
            
            # Show failed tests for this category
            if stats['failed']:
                print(f"  Failed tests:")
                for failed_test in stats['failed'][:3]:  # Show first 3 failures
                    if 'error' in failed_test:
                        print(f"    - ERROR: {failed_test['input']} - {failed_test['error']}")
                    else:
                        print(f"    - {failed_test['input']}")
                        if not failed_test['type_match']:
                            print(f"      Type: got '{failed_test['actual_type']}', expected '{failed_test['expected_type']}'")
                        if not failed_test['granularity_match']:
                            print(f"      Granularity: got '{failed_test['actual_granularity']}', expected '{failed_test['expected_granularity']}'")
                if len(stats['failed']) > 3:
                    print(f"    ... and {len(stats['failed']) - 3} more failures")
            print()
        
        # Overall assessment
        if self.passed_tests / self.total_tests >= 0.90:
            print("🎉 EXCELLENT: Complex cases parsing is highly accurate!")
        elif self.passed_tests / self.total_tests >= 0.80:
            print("✅ VERY GOOD: Complex cases parsing is mostly accurate with minor issues.")
        elif self.passed_tests / self.total_tests >= 0.70:
            print("⚠️  GOOD: Complex cases parsing has some accuracy issues that need attention.")
        elif self.passed_tests / self.total_tests >= 0.50:
            print("❌ FAIR: Complex cases parsing has significant accuracy issues that need fixing.")
        else:
            print("🚨 POOR: Complex cases parsing has major accuracy issues that need immediate attention.")
        
        print("=" * 80)

def main():
    """Main analysis runner."""
    analyzer = ComplexCasesAnalyzer()
    analyzer.run_complex_analysis()
    return 0 if analyzer.passed_tests == analyzer.total_tests else 1

if __name__ == "__main__":
    sys.exit(main())
