#!/usr/bin/env python3
"""Stress Test 2: All-Metrics Verification Test (68 Metrics)."""

import sys
import io
import json
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import (
    AnalyticsEngine, BASE_METRICS, DERIVED_METRICS,
    AGGREGATE_METRICS, SUPPLEMENTAL_METRICS, CURRENCY_METRICS,
    PERCENTAGE_METRICS, MULTIPLE_METRICS
)
from benchmarkos_chatbot.response_verifier import _identify_metric_from_context

print("="*80)
print("STRESS TEST 2: ALL-METRICS VERIFICATION (68 METRICS)")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

settings = load_settings()
engine = AnalyticsEngine(settings)

# Get all metrics
all_metrics = BASE_METRICS | DERIVED_METRICS | AGGREGATE_METRICS | SUPPLEMENTAL_METRICS

print(f"Total Metrics to Test: {len(all_metrics)}")
print(f"  - Base: {len(BASE_METRICS)}")
print(f"  - Derived: {len(DERIVED_METRICS)}")
print(f"  - Aggregate: {len(AGGREGATE_METRICS)}")
print(f"  - Supplemental: {len(SUPPLEMENTAL_METRICS)}\n")

# Test metric identification for each type
results = {
    'total_metrics': len(all_metrics),
    'identified': 0,
    'not_identified': 0,
    'by_type': {
        'currency': {'tested': 0, 'identified': 0},
        'percentage': {'tested': 0, 'identified': 0},
        'multiple': {'tested': 0, 'identified': 0},
        'other': {'tested': 0, 'identified': 0}
    },
    'failed_metrics': []
}

# Test sample contexts for each metric
test_contexts = {
    # Currency metrics
    'revenue': "Apple's revenue is $394.3B",
    'net_income': "Net income reached $99.8B",
    'free_cash_flow': "Free cash flow was $85.2B",
    'total_assets': "Total assets are $352.7B",
    'cash_from_operations': "Cash from operations: $104.0B",
    
    # Percentage metrics
    'gross_margin': "Gross margin improved to 45.9%",
    'operating_margin': "Operating margin reached 30.7%",
    'net_margin': "Net margin is 25.3%",
    'roe': "ROE stands at 160.5%",
    'roa': "ROA is 28.4%",
    'roic': "ROIC improved to 52.3%",
    'revenue_cagr': "Revenue CAGR is 8.5%",
    'ebitda_margin': "EBITDA margin is 35.2%",
    
    # Multiple metrics
    'pe_ratio': "P/E ratio is 32.5x",
    'debt_to_equity': "Debt to equity is 1.8x",
    'current_ratio': "Current ratio is 1.07x",
    'ev_ebitda': "EV/EBITDA multiple is 18.5x",
    'pb_ratio': "P/B ratio is 48.2x",
}

print("Testing metric identification...\n")

for metric in sorted(all_metrics):
    # Determine metric type
    if metric in CURRENCY_METRICS:
        metric_type = 'currency'
    elif metric in PERCENTAGE_METRICS:
        metric_type = 'percentage'
    elif metric in MULTIPLE_METRICS:
        metric_type = 'multiple'
    else:
        metric_type = 'other'
    
    results['by_type'][metric_type]['tested'] += 1
    
    # Test identification
    if metric in test_contexts:
        context = test_contexts[metric]
        identified = _identify_metric_from_context(context)
        
        if identified == metric:
            results['identified'] += 1
            results['by_type'][metric_type]['identified'] += 1
        else:
            results['not_identified'] += 1
            results['failed_metrics'].append(f"{metric} (identified as: {identified})")
    else:
        # Try generic context
        context = f"{metric.replace('_', ' ')} is 100"
        identified = _identify_metric_from_context(context)
        
        if identified == metric:
            results['identified'] += 1
            results['by_type'][metric_type]['identified'] += 1
        else:
            results['not_identified'] += 1
            results['failed_metrics'].append(f"{metric} (generic context)")

print("="*80)
print("METRIC IDENTIFICATION RESULTS")
print("="*80)

print(f"\nOverall:")
print(f"  Total Metrics: {results['total_metrics']}")
print(f"  Identified: {results['identified']}")
print(f"  Not Identified: {results['not_identified']}")
print(f"  Identification Rate: {results['identified']/results['total_metrics']*100:.1f}%")

print(f"\nBy Type:")
for metric_type, stats in results['by_type'].items():
    if stats['tested'] > 0:
        rate = stats['identified']/stats['tested']*100
        print(f"  {metric_type.capitalize():<15s}: {stats['identified']:2d}/{stats['tested']:2d} ({rate:5.1f}%)")

if results['failed_metrics']:
    print(f"\nFailed Metrics ({len(results['failed_metrics'])}):")
    for failed in results['failed_metrics'][:20]:
        print(f"  - {failed}")

# Save results
with open('stress_test_all_metrics_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

if results['identified'] / results['total_metrics'] >= 0.90:
    print(f"\n[SUCCESS] Metric identification test passed!")
    print(f"  - {results['identified']/results['total_metrics']*100:.1f}% metrics identified (target: 90%+)")
else:
    print(f"\n[NEEDS WORK] Below 90% target")
    print(f"  - {results['identified']/results['total_metrics']*100:.1f}% metrics identified (target: 90%+)")

print(f"\nResults saved to: stress_test_all_metrics_results.json")
print("="*80)

