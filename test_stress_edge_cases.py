#!/usr/bin/env python3
"""Stress Test 3: Edge Cases and Error Scenarios."""

import sys
import io
import json
import re
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.response_verifier import extract_financial_numbers, verify_response
from benchmarkos_chatbot.confidence_scorer import calculate_confidence

print("="*80)
print("STRESS TEST 3: EDGE CASES AND ERROR SCENARIOS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

settings = load_settings()
engine = AnalyticsEngine(settings)

# Define edge case scenarios
edge_cases = [
    {
        'name': 'Multiple companies in one response',
        'response': "Apple's revenue is $394.3B while Microsoft's revenue is $245.1B, making Apple 61% larger.",
        'expected_facts': 3,
        'expected_tickers': ['AAPL', 'MSFT']
    },
    {
        'name': 'Mixed metrics (revenue + margins + ratios)',
        'response': "AAPL revenue is $394.3B with gross margin of 45.9% and P/E ratio of 32.5x.",
        'expected_facts': 3,
        'expected_metrics': ['revenue', 'gross_margin', 'pe_ratio']
    },
    {
        'name': 'No sources cited',
        'response': "Apple's revenue is $394.3B.",
        'expected_facts': 1,
        'check_confidence_penalty': True
    },
    {
        'name': 'Malformed numbers with commas',
        'response': "Tesla's revenue is $1,234.5M in Q3.",
        'expected_facts': 1
    },
    {
        'name': 'Very large numbers (trillions)',
        'response': "Apple's market cap is $3.2T.",
        'expected_facts': 1
    },
    {
        'name': 'Very small percentages',
        'response': "Interest rate is 0.5%.",
        'expected_facts': 1
    },
    {
        'name': 'Multiple periods mentioned',
        'response': "Apple's revenue in FY2024 was $394.3B, up from $383.2B in FY2023.",
        'expected_facts': 2
    },
    {
        'name': 'Ambiguous metric (margin without qualifier)',
        'response': "The margin is 25.3%.",
        'expected_facts': 1
    },
]

results = {
    'total_cases': len(edge_cases),
    'passed': 0,
    'failed': 0,
    'details': []
}

print("Testing edge cases...\n")

for i, test_case in enumerate(edge_cases, 1):
    print(f"{i}. {test_case['name']}")
    
    try:
        # Extract facts
        facts = extract_financial_numbers(test_case['response'])
        
        # Check expectations
        test_passed = True
        issues = []
        
        if 'expected_facts' in test_case:
            if len(facts) != test_case['expected_facts']:
                test_passed = False
                issues.append(f"Expected {test_case['expected_facts']} facts, got {len(facts)}")
        
        if 'expected_tickers' in test_case:
            found_tickers = set(f.ticker for f in facts if f.ticker)
            expected_tickers = set(test_case['expected_tickers'])
            if found_tickers != expected_tickers:
                test_passed = False
                issues.append(f"Expected tickers {expected_tickers}, got {found_tickers}")
        
        if 'expected_metrics' in test_case:
            found_metrics = set(f.metric for f in facts if f.metric)
            expected_metrics = set(test_case['expected_metrics'])
            if not expected_metrics.issubset(found_metrics):
                test_passed = False
                issues.append(f"Missing metrics: {expected_metrics - found_metrics}")
        
        # Verify response
        verification = verify_response(
            test_case['response'],
            "",
            "Test query",
            engine,
            str(settings.database_path)
        )
        
        # Calculate confidence
        source_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', test_case['response']))
        conf = calculate_confidence(test_case['response'], verification.results, source_count=source_count)
        
        if 'check_confidence_penalty' in test_case and test_case['check_confidence_penalty']:
            if source_count == 0 and conf.score >= 1.0:
                test_passed = False
                issues.append("No sources but confidence is 100% (should be penalized)")
        
        # Report
        status = "PASS" if test_passed else "FAIL"
        print(f"   [{status}] Facts: {len(facts)}, Verified: {verification.correct_facts}/{verification.total_facts}, Confidence: {conf.score*100:.0f}%")
        
        if issues:
            for issue in issues:
                print(f"        Issue: {issue}")
        
        if test_passed:
            results['passed'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append({
            'name': test_case['name'],
            'passed': test_passed,
            'facts_extracted': len(facts),
            'facts_verified': verification.correct_facts,
            'confidence': conf.score,
            'issues': issues
        })
    
    except Exception as e:
        print(f"   [ERROR] {str(e)}")
        results['failed'] += 1
        results['details'].append({
            'name': test_case['name'],
            'passed': False,
            'error': str(e)
        })

print(f"\n" + "="*80)
print("EDGE CASE TEST RESULTS")
print("="*80)

print(f"\nTotal Cases: {results['total_cases']}")
print(f"Passed: {results['passed']}")
print(f"Failed: {results['failed']}")
print(f"Success Rate: {results['passed']/results['total_cases']*100:.1f}%")

# Save results
with open('stress_test_edge_cases_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

if results['passed'] / results['total_cases'] >= 0.80:
    print(f"\n[SUCCESS] Edge case test passed!")
    print(f"  - {results['passed']}/{results['total_cases']} cases handled successfully")
    print(f"  - System is robust")
else:
    print(f"\n[NEEDS WORK] Some edge cases failed")
    print(f"  - {results['passed']}/{results['total_cases']} cases passed (target: 80%+)")

print(f"\nResults saved to: stress_test_edge_cases_results.json")
print("="*80)

