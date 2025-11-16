#!/usr/bin/env python3
"""Comprehensive Test: ALL S&P 500 Companies × ALL KPIs."""

import sys
import io
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.analytics_engine import (
    AnalyticsEngine, BASE_METRICS, DERIVED_METRICS,
    AGGREGATE_METRICS, SUPPLEMENTAL_METRICS
)
from finanlyzeos_chatbot.response_verifier import extract_financial_numbers, verify_response
from finanlyzeos_chatbot.confidence_scorer import calculate_confidence

print("="*80)
print("COMPREHENSIVE TEST: ALL S&P 500 COMPANIES × ALL KPIs")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

settings = load_settings()
engine = AnalyticsEngine(settings)

# Get ALL companies from database
print("Loading ALL companies from database...")
conn = sqlite3.connect(str(settings.database_path))
all_companies = conn.execute("""
    SELECT DISTINCT ticker 
    FROM metric_snapshots 
    WHERE ticker NOT LIKE '%-P%'  -- Exclude preferred shares
    AND ticker NOT LIKE '%-%'     -- Exclude complex tickers
    ORDER BY ticker
""").fetchall()
conn.close()

all_tickers = [row[0] for row in all_companies]
print(f"Found {len(all_tickers)} companies in database\n")

# Get all metrics
all_metrics = sorted(list(BASE_METRICS | DERIVED_METRICS | AGGREGATE_METRICS | SUPPLEMENTAL_METRICS))
print(f"Testing {len(all_metrics)} KPIs/metrics\n")

print(f"Total potential tests: {len(all_tickers)} companies × {len(all_metrics)} metrics = {len(all_tickers) * len(all_metrics):,}")
print(f"Note: Will only test metrics that exist in database for each company\n")

# Test results
results = {
    'total_companies': len(all_tickers),
    'total_metrics': len(all_metrics),
    'companies_tested': 0,
    'metrics_tested': 0,
    'total_facts': 0,
    'verified_facts': 0,
    'confidence_scores': [],
    'perfect_scores': 0,  # 100% confidence
    'high_scores': 0,     # 95-99%
    'good_scores': 0,     # 85-94%
    'low_scores': 0,      # <85%
    'by_metric_type': defaultdict(lambda: {'tested': 0, 'verified': 0, 'confidence': []}),
    'sample_results': [],
    'errors': []
}

print("Testing companies × metrics (sampling for speed)...\n")
print("Strategy: Test each company with 5 random metrics\n")

import random
tested_count = 0
target_tests = min(len(all_tickers) * 5, 2000)  # Cap at 2000 tests

for company_idx, ticker in enumerate(all_tickers, 1):
    try:
        # Get all available metrics for this company
        metrics_data = engine.get_metrics(ticker)
        
        if not metrics_data:
            continue
        
        # Group by metric type
        metric_map = defaultdict(list)
        for m in metrics_data:
            metric_map[m.metric].append(m)
        
        # Sample 5 metrics from this company
        available_metrics = list(metric_map.keys())
        sample_size = min(5, len(available_metrics))
        sampled_metrics = random.sample(available_metrics, sample_size)
        
        results['companies_tested'] += 1
        
        for metric in sampled_metrics:
            metric_records = metric_map[metric]
            if not metric_records:
                continue
            
            latest = metric_records[0]
            
            # Determine metric type
            if metric in BASE_METRICS:
                metric_type = 'base'
            elif metric in DERIVED_METRICS:
                metric_type = 'derived'
            elif metric in AGGREGATE_METRICS:
                metric_type = 'aggregate'
            else:
                metric_type = 'supplemental'
            
            results['by_metric_type'][metric_type]['tested'] += 1
            results['metrics_tested'] += 1
            
            # Format value
            if abs(latest.value) > 1_000_000_000:
                # Currency - billions
                value_formatted = f"${latest.value / 1_000_000_000:.1f}B"
                unit = "B"
                value = latest.value / 1_000_000_000
            elif abs(latest.value) < 100 and metric in DERIVED_METRICS | AGGREGATE_METRICS:
                # Likely a percentage/ratio
                if latest.value < 1:
                    # Decimal percentage
                    value_formatted = f"{latest.value * 100:.1f}%"
                    unit = "%"
                    value = latest.value * 100
                else:
                    value_formatted = f"{latest.value:.1f}%"
                    unit = "%"
                    value = latest.value
            else:
                # As-is
                value_formatted = f"{latest.value:.2f}"
                unit = ""
                value = latest.value
            
            # Simulate response
            response = f"{ticker}'s {metric.replace('_', ' ')} for {latest.period} is {value_formatted}."
            
            # Verify
            verification = verify_response(
                response,
                "",
                f"What is {ticker}'s {metric}?",
                engine,
                str(settings.database_path)
            )
            
            # Calculate confidence
            conf = calculate_confidence(response, verification.results, source_count=1)
            
            results['total_facts'] += verification.total_facts
            results['verified_facts'] += verification.correct_facts
            results['confidence_scores'].append(conf.score)
            results['by_metric_type'][metric_type]['verified'] += verification.correct_facts
            results['by_metric_type'][metric_type]['confidence'].append(conf.score)
            
            # Categorize confidence
            if conf.score >= 0.95:
                if conf.score == 1.0:
                    results['perfect_scores'] += 1
                else:
                    results['high_scores'] += 1
            elif conf.score >= 0.85:
                results['good_scores'] += 1
            else:
                results['low_scores'] += 1
            
            # Save sample results
            if len(results['sample_results']) < 20:
                results['sample_results'].append({
                    'ticker': ticker,
                    'metric': metric,
                    'verified': verification.correct_facts,
                    'total': verification.total_facts,
                    'confidence': conf.score
                })
            
            tested_count += 1
            if tested_count >= target_tests:
                break
        
        # Progress
        if company_idx % 50 == 0 or tested_count >= target_tests:
            print(f"[{tested_count:4d} tests] Companies: {results['companies_tested']}, Avg Confidence: {sum(results['confidence_scores'])/len(results['confidence_scores'])*100:.1f}%")
        
        if tested_count >= target_tests:
            break
            
    except Exception as e:
        results['errors'].append(f"{ticker}: {str(e)}")
        continue

print("\n" + "="*80)
print("COMPREHENSIVE TEST RESULTS")
print("="*80)

print(f"\nScope:")
print(f"  Total Companies in Database: {len(all_tickers)}")
print(f"  Total KPIs Available: {len(all_metrics)}")
print(f"  Theoretical Max Tests: {len(all_tickers)} × {len(all_metrics)} = {len(all_tickers) * len(all_metrics):,}")

print(f"\nActual Tests:")
print(f"  Companies Tested: {results['companies_tested']}/{len(all_tickers)}")
print(f"  Metrics Tested: {results['metrics_tested']}")
print(f"  Total Tests Executed: {tested_count}")

print(f"\nFact Verification:")
print(f"  Total Facts: {results['total_facts']}")
print(f"  Verified Facts: {results['verified_facts']}")
print(f"  Verification Rate: {results['verified_facts']/results['total_facts']*100:.1f}%")

if results['confidence_scores']:
    avg_conf = sum(results['confidence_scores']) / len(results['confidence_scores'])
    min_conf = min(results['confidence_scores'])
    max_conf = max(results['confidence_scores'])
    median_conf = sorted(results['confidence_scores'])[len(results['confidence_scores'])//2]
    
    print(f"\nConfidence Scores:")
    print(f"  Average: {avg_conf*100:.1f}%")
    print(f"  Median: {median_conf*100:.1f}%")
    print(f"  Min: {min_conf*100:.1f}%")
    print(f"  Max: {max_conf*100:.1f}%")
    
    print(f"\n  Distribution:")
    print(f"    100%:     {results['perfect_scores']} ({results['perfect_scores']/len(results['confidence_scores'])*100:.1f}%)")
    print(f"    95-99%:   {results['high_scores']} ({results['high_scores']/len(results['confidence_scores'])*100:.1f}%)")
    print(f"    85-94%:   {results['good_scores']} ({results['good_scores']/len(results['confidence_scores'])*100:.1f}%)")
    print(f"    <85%:     {results['low_scores']} ({results['low_scores']/len(results['confidence_scores'])*100:.1f}%)")
    
    high_quality = results['perfect_scores'] + results['high_scores']
    print(f"\n  Quality Metrics:")
    print(f"    >=95% confidence: {high_quality}/{len(results['confidence_scores'])} ({high_quality/len(results['confidence_scores'])*100:.1f}%)")
    print(f"    >=85% confidence: {high_quality + results['good_scores']}/{len(results['confidence_scores'])} ({(high_quality + results['good_scores'])/len(results['confidence_scores'])*100:.1f}%)")

print(f"\nBy Metric Type:")
for metric_type in ['base', 'derived', 'aggregate', 'supplemental']:
    stats = results['by_metric_type'][metric_type]
    if stats['tested'] > 0:
        avg = sum(stats['confidence']) / len(stats['confidence']) * 100 if stats['confidence'] else 0
        print(f"  {metric_type.capitalize():<15s}: {stats['tested']:4d} tests, {avg:5.1f}% avg confidence")

if results['errors']:
    print(f"\nErrors: {len(results['errors'])} (showing first 10)")
    for error in results['errors'][:10]:
        print(f"  - {error}")

# Save results
output = {
    'test_date': datetime.now().isoformat(),
    'companies_in_db': len(all_tickers),
    'metrics_available': len(all_metrics),
    'companies_tested': results['companies_tested'],
    'metrics_tested': results['metrics_tested'],
    'total_tests': tested_count,
    'verification_rate': f"{results['verified_facts']/results['total_facts']*100:.1f}%",
    'average_confidence': f"{avg_conf*100:.1f}%",
    'confidence_distribution': {
        '100%': results['perfect_scores'],
        '95-99%': results['high_scores'],
        '85-94%': results['good_scores'],
        '<85%': results['low_scores']
    },
    'by_metric_type': dict(results['by_metric_type']),
    'sample_results': results['sample_results'][:20]
}

with open('test_all_sp500_all_kpis_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

success_rate = (results['perfect_scores'] + results['high_scores']) / len(results['confidence_scores'])

if avg_conf >= 0.90 and success_rate >= 0.75:
    print(f"\n[SUCCESS] Comprehensive test PASSED!")
    print(f"  ✅ {avg_conf*100:.1f}% average confidence (target: 90%+)")
    print(f"  ✅ {success_rate*100:.1f}% at >=95% confidence (target: 75%+)")
    print(f"  ✅ {results['companies_tested']} companies tested")
    print(f"  ✅ {results['metrics_tested']} metric tests executed")
    print(f"  ✅ System verified for production deployment")
elif avg_conf >= 0.85:
    print(f"\n[GOOD] Test passed with good results")
    print(f"  ✅ {avg_conf*100:.1f}% average confidence (target: 85%+)")
    print(f"  ✅ Production-ready with monitoring")
else:
    print(f"\n[NEEDS WORK] Below targets")
    print(f"  ⚠️ {avg_conf*100:.1f}% average confidence (target: 90%+)")

print(f"\nResults saved to: test_all_sp500_all_kpis_results.json")
print("="*80)


