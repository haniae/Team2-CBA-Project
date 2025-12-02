"""
Automated Accuracy Testing for BenchmarkOS Chatbot
Based on NIST Measurement Trees Framework (arXiv:2509.26632)

This script implements the complete 5-level hierarchical testing framework:
- Level 5: Individual test cases (leaf nodes)
- Level 4: Construct-level aggregation (FA-1, FA-3, etc.)
- Level 3: Overall automated testing score
- Level 2: Component-level aggregation (Database, LLM, RAG)
- Level 1: System-level score (Overall Chatbot Performance)
"""

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestCase:
    """Individual test case (Level 5 leaf node)"""
    test_id: str
    construct: str  # FA-1, FA-2, etc.
    query: str
    expected_value: Any
    expected_unit: Optional[str] = None
    tolerance: float = 0.02  # 2% tolerance for numerical values
    
    
@dataclass
class TestResult:
    """Result of a single test case"""
    test_case: TestCase
    actual_output: str
    extracted_value: Any
    risk_score: float  # 0-10 scale
    passed: bool
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AccuracyTester:
    """
    Implements automated accuracy testing using measurement tree framework.
    
    Complete 5-level hierarchical structure:
    - Level 5: Individual test cases
    - Level 4: Construct-level aggregation (FA-1, FA-3, etc.)
    - Level 3: Overall automated testing score
    - Level 2: Component-level aggregation (Database, LLM, RAG)
    - Level 1: System-level score (Overall Chatbot Performance)
    """
    
    # Component mapping: Maps constructs to system components
    COMPONENT_MAPPING = {
        # Database Component: Factual accuracy, data retrieval, calculations
        'FA-1': 'Database',  # Numerical Value Accuracy
        'FA-2': 'Database',  # Metric Calculation Accuracy
        'FA-3': 'Database',  # Growth Rate Calculation
        'FA-4': 'Database',  # Multi-Metric Retrieval
        'FA-5': 'Database',  # Temporal Query Accuracy
        # RAG Component: Context retrieval, source citations, narratives
        'RAG-1': 'RAG',  # Context Retrieval Quality
        'RAG-2': 'RAG',  # Source Citation Accuracy
        'RAG-3': 'RAG',  # Narrative Retrieval Quality
        'RAG-4': 'RAG',  # Multi-Hop Retrieval
        # LLM Component: Response generation, formatting, natural language
        'LLM-1': 'LLM',  # Response Format Quality
        'LLM-2': 'LLM',  # Natural Language Quality
        'LLM-3': 'LLM',  # Explanation Clarity
        'LLM-4': 'LLM',  # Response Completeness
    }
    
    def __init__(self, chatbot_api_url: str = "http://localhost:8000", 
                 database_path: str = "data/sqlite/finanlyzeos_chatbot.sqlite3"):
        self.api_url = chatbot_api_url
        self.database_path = Path(database_path)
        self.results: List[TestResult] = []
    
    def get_component_for_construct(self, construct: str) -> str:
        """
        Map a construct (FA-1, FA-3, etc.) to its component (Database, LLM, RAG).
        
        Defaults to 'Database' for unknown constructs as most accuracy tests
        are database-related.
        """
        return self.COMPONENT_MAPPING.get(construct, 'Database')
        
    def load_ground_truth(self) -> Dict[str, Any]:
        """Load ground truth values from database"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Query financial_facts for ground truth
        query = """
        SELECT ticker, metric, fiscal_year, value, unit
        FROM financial_facts
        WHERE fiscal_year IN (2022, 2023, 2024)
        ORDER BY ticker, fiscal_year DESC, metric
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        # Organize as: ground_truth[ticker][metric][year] = (value, unit)
        ground_truth = {}
        for ticker, metric, year, value, unit in rows:
            if ticker not in ground_truth:
                ground_truth[ticker] = {}
            if metric not in ground_truth[ticker]:
                ground_truth[ticker][metric] = {}
            ground_truth[ticker][metric][year] = (value, unit)
            
        return ground_truth
    
    def generate_test_cases(self) -> List[TestCase]:
        """Generate test cases from ground truth data"""
        ground_truth = self.load_ground_truth()
        test_cases = []
        
        # FA-1: Numerical Value Accuracy
        # Single metric retrieval tests
        for ticker in ['AAPL', 'MSFT', 'GOOGL'][:1]:  # Start with Apple
            if ticker not in ground_truth:
                continue
                
            for metric in ['revenue', 'net_income', 'operating_margin']:
                if metric not in ground_truth[ticker]:
                    continue
                    
                for year in [2024, 2023]:
                    if year not in ground_truth[ticker][metric]:
                        continue
                        
                    value, unit = ground_truth[ticker][metric][year]
                    
                    # Create natural language query
                    query = f"What was {ticker}'s {metric.replace('_', ' ')} in FY{year}?"
                    
                    test_cases.append(TestCase(
                        test_id=f"FA-1-{ticker}-{metric}-{year}",
                        construct="FA-1",
                        query=query,
                        expected_value=value,
                        expected_unit=unit,
                        tolerance=0.02
                    ))
        
        # FA-3: Growth Rate Calculation
        # Critical test for the percentage bug!
        for ticker in ['AAPL']:
            if ticker not in ground_truth or 'revenue' not in ground_truth[ticker]:
                continue
                
            # Calculate expected YoY growth
            if 2024 in ground_truth[ticker]['revenue'] and 2023 in ground_truth[ticker]['revenue']:
                rev_2024 = ground_truth[ticker]['revenue'][2024][0]
                rev_2023 = ground_truth[ticker]['revenue'][2023][0]
                expected_yoy = ((rev_2024 - rev_2023) / rev_2023) * 100  # Percentage
                
                test_cases.append(TestCase(
                    test_id=f"FA-3-{ticker}-revenue-yoy-2024",
                    construct="FA-3",
                    query=f"How did {ticker}'s revenue grow year-over-year in 2024?",
                    expected_value=expected_yoy,
                    expected_unit="%",
                    tolerance=0.02  # 2% tolerance (allows for rounding: 2.0% vs 2.02%)
                ))
        
        return test_cases
    
    def query_chatbot(self, query: str) -> str:
        """Send query to chatbot and get response"""
        import requests
        
        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json={"prompt": query, "conversation_id": "test_session"},
                timeout=60  # Increased for GPT-4o (slower but better quality)
            )
            response.raise_for_status()
            data = response.json()
            return data.get("reply", "")
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def extract_numerical_value(self, text: str, unit: Optional[str] = None) -> Optional[float]:
        """
        Extract numerical value from chatbot response.
        
        Handles formats like:
        - $391.04B
        - $391.04 billion
        - 391.04B
        - 2.1%
        - 30.7%
        """
        if not text:
            return None
            
        # Pattern for currency (billion/million)
        if unit in ['USD', 'dollars', None]:
            # Match: $391.04B, $391.04 billion, 391.04B
            patterns = [
                r'\$?([\d,]+\.?\d*)\s*[Bb]illion',
                r'\$?([\d,]+\.?\d*)\s*B\b',
                r'\$?([\d,]+\.?\d*)\s*[Mm]illion',
                r'\$?([\d,]+\.?\d*)\s*M\b',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    # Convert to absolute value (assuming billions)
                    if 'billion' in pattern.lower() or 'B' in pattern:
                        return value * 1_000_000_000
                    elif 'million' in pattern.lower() or 'M' in pattern:
                        return value * 1_000_000
                    return value
        
        # Pattern for percentages
        if unit == '%':
            # Match: 2.1%, 7.2%
            # DO NOT match astronomical percentages like 391035000000.0%
            pattern = r'(\d{1,3}(?:\.\d+)?)\s*%'
            matches = re.findall(pattern, text)
            if matches:
                # Take the first reasonable percentage (< 1000%)
                for match in matches:
                    value = float(match)
                    if value < 1000:  # Sanity check
                        return value
            
            # Check for astronomical percentage bug (CRITICAL!)
            astro_pattern = r'(\d{4,}(?:,\d{3})*(?:\.\d+)?)\s*%'
            if re.search(astro_pattern, text):
                # Return None to trigger failure
                return None
        
        # Fallback: just extract first number
        match = re.search(r'([\d,]+\.?\d*)', text)
        if match:
            value_str = match.group(1).replace(',', '')
            if value_str:  # Check if not empty
                try:
                    return float(value_str)
                except ValueError:
                    return None
        
        return None
    
    def calculate_risk_score(self, test_case: TestCase, actual_value: Optional[float]) -> Tuple[float, bool, Optional[str]]:
        """
        Calculate risk score (0-10) for a test case.
        
        Returns: (risk_score, passed, error_message)
        """
        if actual_value is None:
            return (10.0, False, "Could not extract value from response")
        
        expected = test_case.expected_value
        
        # Check for astronomical percentage bug (CRITICAL)
        if test_case.construct == "FA-3" and actual_value > 1000:
            return (10.0, False, f"ASTRONOMICAL PERCENTAGE BUG: {actual_value}%")
        
        # Calculate error
        try:
            error = abs(actual_value - expected) / abs(expected)
        except ZeroDivisionError:
            error = abs(actual_value - expected)
        
        # Score based on error and tolerance
        if error <= test_case.tolerance:
            return (0.0, True, None)  # Perfect
        elif error <= 0.05:  # 5%
            return (5.0, False, f"Moderate error: {error*100:.1f}% off")
        else:
            return (10.0, False, f"Large error: {error*100:.1f}% off")
    
    def run_tests(self, test_cases: Optional[List[TestCase]] = None) -> List[TestResult]:
        """Run all test cases and collect results (Level 5 data)"""
        if test_cases is None:
            test_cases = self.generate_test_cases()
        
        print(f"Running {len(test_cases)} test cases...")
        self.results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"[{i+1}/{len(test_cases)}] {test_case.test_id}: {test_case.query}")
            
            # Query chatbot
            response = self.query_chatbot(test_case.query)
            
            # Debug: show first 200 chars of response
            print(f"  Response: {response[:200]}...")
            
            # Extract value
            extracted = self.extract_numerical_value(response, test_case.expected_unit)
            
            # Calculate risk score
            risk_score, passed, error_msg = self.calculate_risk_score(test_case, extracted)
            
            # Create result
            result = TestResult(
                test_case=test_case,
                actual_output=response,
                extracted_value=extracted,
                risk_score=risk_score,
                passed=passed,
                error_message=error_msg
            )
            
            self.results.append(result)
            
            # Print immediate feedback
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} (risk: {risk_score:.1f}/10)")
            if error_msg:
                print(f"  {error_msg}")
            print()
        
        return self.results
    
    def aggregate_by_construct(self) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate Level 5 results to Level 4 (construct level).
        
        Returns dict: {construct_id: {score, n, passed, failed}}
        """
        from collections import defaultdict
        
        construct_results = defaultdict(list)
        
        for result in self.results:
            construct_results[result.test_case.construct].append(result)
        
        aggregated = {}
        for construct, results in construct_results.items():
            risk_scores = [r.risk_score for r in results]
            passed_count = sum(1 for r in results if r.passed)
            failed_count = len(results) - passed_count
            
            aggregated[construct] = {
                'construct': construct,
                'risk_score': sum(risk_scores) / len(risk_scores),  # Mean
                'n': len(results),
                'passed': passed_count,
                'failed': failed_count,
                'pass_rate': passed_count / len(results) if results else 0
            }
        
        return aggregated
    
    def aggregate_by_component(self) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate Level 4 results to Level 2 (component level).
        
        Groups constructs by component (Database, LLM, RAG) and aggregates scores.
        
        Returns dict: {component: {risk_score, n, passed, failed, constructs}}
        """
        from collections import defaultdict
        
        # First, get Level 4 aggregates
        level4_aggregates = self.aggregate_by_construct()
        
        # Group constructs by component
        component_constructs = defaultdict(list)
        for construct, data in level4_aggregates.items():
            component = self.get_component_for_construct(construct)
            component_constructs[component].append((construct, data))
        
        # Aggregate by component
        component_results = {}
        for component, construct_list in component_constructs.items():
            # Collect all test results for this component
            component_tests = []
            for construct, construct_data in construct_list:
                # Get all results for this construct
                construct_results = [
                    r for r in self.results 
                    if r.test_case.construct == construct
                ]
                component_tests.extend(construct_results)
            
            if component_tests:
                risk_scores = [r.risk_score for r in component_tests]
                passed_count = sum(1 for r in component_tests if r.passed)
                failed_count = len(component_tests) - passed_count
                
                component_results[component] = {
                    'component': component,
                    'risk_score': sum(risk_scores) / len(risk_scores) if risk_scores else 0,  # Mean
                    'n': len(component_tests),
                    'passed': passed_count,
                    'failed': failed_count,
                    'pass_rate': passed_count / len(component_tests) if component_tests else 0,
                    'constructs': [c for c, _ in construct_list],
                    'construct_count': len(construct_list)
                }
            else:
                component_results[component] = {
                    'component': component,
                    'risk_score': 0.0,
                    'n': 0,
                    'passed': 0,
                    'failed': 0,
                    'pass_rate': 0.0,
                    'constructs': [],
                    'construct_count': 0
                }
        
        return component_results
    
    def aggregate_system_level(self) -> Dict[str, Any]:
        """
        Aggregate Level 2 results to Level 1 (system level).
        
        Calculates overall chatbot performance score as the mean of component scores.
        
        Returns dict: {system_score, component_scores, risk_level}
        """
        # Get Level 2 aggregates
        component_aggregates = self.aggregate_by_component()
        
        # Calculate system-level score (mean of all component scores)
        component_risk_scores = [
            data['risk_score'] for data in component_aggregates.values()
            if data['n'] > 0  # Only include components with tests
        ]
        
        if component_risk_scores:
            system_score = sum(component_risk_scores) / len(component_risk_scores)
        else:
            system_score = 0.0
        
        return {
            'system_score': system_score,
            'risk_level': self._risk_level(system_score),
            'component_scores': {
                comp: data['risk_score'] 
                for comp, data in component_aggregates.items()
                if data['n'] > 0
            },
            'total_components': len([c for c in component_aggregates.values() if c['n'] > 0]),
            'total_tests': sum(data['n'] for data in component_aggregates.values())
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report with all 5 levels"""
        # Level 4: Construct-level aggregation
        level4_aggregates = self.aggregate_by_construct()
        level4_scores = {k: v['risk_score'] for k, v in level4_aggregates.items()}
        
        # Level 3: Overall automated testing score (mean of constructs)
        level3_score = sum(level4_scores.values()) / len(level4_scores) if level4_scores else 0
        
        # Level 2: Component-level aggregation
        level2_aggregates = self.aggregate_by_component()
        level2_scores = {k: v['risk_score'] for k, v in level2_aggregates.items() if v['n'] > 0}
        
        # Level 1: System-level aggregation
        level1_result = self.aggregate_system_level()
        
        # Identify critical failures
        critical_failures = [
            r for r in self.results 
            if not r.passed and r.risk_score >= 8.0
        ]
        
        report = {
            'summary': {
                'total_tests': len(self.results),
                'passed': sum(1 for r in self.results if r.passed),
                'failed': sum(1 for r in self.results if not r.passed),
                'pass_rate': sum(1 for r in self.results if r.passed) / len(self.results) if self.results else 0,
                'overall_risk_score': level3_score,
                'risk_level': self._risk_level(level3_score)
            },
            # Level 5: Individual test results (implicit in results list)
            'by_construct': level4_aggregates,  # Level 4
            'by_component': level2_aggregates,  # Level 2
            'system_level': level1_result,  # Level 1
            'critical_failures': [
                {
                    'test_id': r.test_case.test_id,
                    'query': r.test_case.query,
                    'expected': r.test_case.expected_value,
                    'actual': r.extracted_value,
                    'risk_score': r.risk_score,
                    'error': r.error_message,
                    'response_snippet': r.actual_output[:200] + '...'
                }
                for r in critical_failures
            ],
            # Scores for each level
            'level4_scores': level4_scores,  # Level 4
            'level3_score': level3_score,  # Level 3
            'level2_scores': level2_scores,  # Level 2
            'level1_score': level1_result['system_score'],  # Level 1
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _risk_level(self, score: float) -> str:
        """Convert risk score to human-readable level"""
        if score <= 2.0:
            return "Excellent (production-ready)"
        elif score <= 4.0:
            return "Good (minor issues)"
        elif score <= 6.0:
            return "Moderate (needs improvement)"
        elif score <= 8.0:
            return "Poor (significant issues)"
        else:
            return "Critical (not production-ready)"
    
    def save_results(self, output_path: str = "test_results.json"):
        """Save results to JSON file"""
        report = self.generate_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Results saved to {output_path}")
    
    def print_summary(self):
        """Print human-readable summary with all 5 levels"""
        report = self.generate_report()
        
        print("=" * 80)
        print("AUTOMATED ACCURACY TEST RESULTS")
        print("NIST Measurement Trees Framework - Complete 5-Level Hierarchy")
        print("=" * 80)
        print()
        
        summary = report['summary']
        
        # Level 1: System-Level Score
        level1 = report['system_level']
        print("=" * 80)
        print("LEVEL 1: SYSTEM-LEVEL SCORE (Overall Chatbot Performance)")
        print("=" * 80)
        print(f"System Risk Score: {level1['system_score']:.2f}/10 - {level1['risk_level']}")
        print(f"Total Tests: {level1['total_tests']}")
        print(f"Components Tested: {level1['total_components']}")
        print()
        
        # Level 2: Component-Level Aggregation
        print("=" * 80)
        print("LEVEL 2: COMPONENT-LEVEL AGGREGATION (Database, LLM, RAG)")
        print("=" * 80)
        for component in ['Database', 'LLM', 'RAG']:
            if component in report['by_component']:
                data = report['by_component'][component]
                status = "✅" if data['risk_score'] <= 2.0 else "⚠️" if data['risk_score'] <= 5.0 else "❌"
                print(f"{status} {component:12s}: {data['risk_score']:.2f}/10 "
                      f"({data['passed']}/{data['n']} passed, {data['pass_rate']*100:.1f}%)")
                print(f"   Constructs: {', '.join(data['constructs']) if data['constructs'] else 'None'}")
        print()
        
        # Level 3: Overall Automated Testing Score
        print("=" * 80)
        print("LEVEL 3: OVERALL AUTOMATED TESTING SCORE")
        print("=" * 80)
        print(f"Overall Risk Score: {report['level3_score']:.2f}/10")
        print(f"Tests Passed: {summary['passed']}/{summary['total_tests']} ({summary['pass_rate']*100:.1f}%)")
        print()
        
        # Level 4: Construct-Level Aggregation
        print("=" * 80)
        print("LEVEL 4: CONSTRUCT-LEVEL AGGREGATION (FA-1, FA-3, etc.)")
        print("=" * 80)
        for construct, data in sorted(report['by_construct'].items()):
            component = self.get_component_for_construct(construct)
            status = "✅" if data['risk_score'] <= 2.0 else "⚠️" if data['risk_score'] <= 5.0 else "❌"
            print(f"{status} {construct:8s} ({component:8s}): {data['risk_score']:.2f}/10 "
                  f"({data['passed']}/{data['n']} passed, {data['pass_rate']*100:.1f}%)")
        print()
        
        # Level 5: Individual Test Cases (summary)
        print("=" * 80)
        print("LEVEL 5: INDIVIDUAL TEST CASES (Leaf Nodes)")
        print("=" * 80)
        print(f"Total Test Cases: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']*100:.1f}%")
        print()
        
        # Critical Failures
        if report['critical_failures']:
            print("=" * 80)
            print("CRITICAL FAILURES (Risk ≥ 8.0)")
            print("=" * 80)
            for failure in report['critical_failures']:
                print(f"❌ {failure['test_id']}")
                print(f"   Query: {failure['query']}")
                print(f"   Expected: {failure['expected']}, Got: {failure['actual']}")
                print(f"   Error: {failure['error']}")
                print()
        else:
            print("✅ No critical failures!")
            print()
        
        # Hierarchy Summary
        print("=" * 80)
        print("HIERARCHY SUMMARY")
        print("=" * 80)
        print(f"Level 1 (System):       {report['level1_score']:.2f}/10")
        print(f"Level 2 (Components):   {', '.join([f'{k}: {v:.2f}' for k, v in report['level2_scores'].items()])}")
        print(f"Level 3 (Overall):      {report['level3_score']:.2f}/10")
        print(f"Level 4 (Constructs):   {len(report['level4_scores'])} constructs")
        print(f"Level 5 (Test Cases):   {summary['total_tests']} cases")
        print()
        
        print("=" * 80)


def main():
    """Run automated accuracy tests"""
    tester = AccuracyTester()
    
    print("Generating test cases from ground truth data...")
    test_cases = tester.generate_test_cases()
    print(f"Generated {len(test_cases)} test cases\n")
    
    print("Running tests...")
    tester.run_tests(test_cases)
    
    print("\n")
    tester.print_summary()
    
    tester.save_results("test_results_automated.json")


if __name__ == "__main__":
    main()

