#!/usr/bin/env python3
"""Stress Test 5: Performance and Speed Test."""

import sys
import io
import json
import time
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from finanlyzeos_chatbot.response_verifier import extract_financial_numbers, verify_response
from finanlyzeos_chatbot.confidence_scorer import calculate_confidence

print("="*80)
print("STRESS TEST 5: PERFORMANCE AND SPEED")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

settings = load_settings()
engine = AnalyticsEngine(settings)

# Test response
test_response = "Apple's revenue for FY2025 is $296.1B with margin of 45.9%."

print("Running 100 verification cycles...\n")

times = []
for i in range(100):
    start = time.time()
    
    # Extract facts
    facts = extract_financial_numbers(test_response)
    
    # Verify
    verification = verify_response(
        test_response,
        "",
        "Test",
        engine,
        str(settings.database_path)
    )
    
    # Calculate confidence
    conf = calculate_confidence(test_response, verification.results, source_count=1)
    
    end = time.time()
    elapsed_ms = (end - start) * 1000
    times.append(elapsed_ms)
    
    if (i + 1) % 20 == 0:
        print(f"[{i+1:3d}/100] Avg time: {sum(times)/len(times):.1f}ms")

print(f"\n" + "="*80)
print("PERFORMANCE RESULTS")
print("="*80)

avg_time = sum(times) / len(times)
min_time = min(times)
max_time = max(times)
p50_time = sorted(times)[len(times)//2]
p95_time = sorted(times)[int(len(times)*0.95)]
p99_time = sorted(times)[int(len(times)*0.99)]

print(f"\nVerification Time (100 iterations):")
print(f"  Average: {avg_time:.1f}ms")
print(f"  Median (p50): {p50_time:.1f}ms")
print(f"  p95: {p95_time:.1f}ms")
print(f"  p99: {p99_time:.1f}ms")
print(f"  Min: {min_time:.1f}ms")
print(f"  Max: {max_time:.1f}ms")

results = {
    'iterations': 100,
    'average_ms': avg_time,
    'median_ms': p50_time,
    'p95_ms': p95_time,
    'p99_ms': p99_time,
    'min_ms': min_time,
    'max_ms': max_time,
}

# Save results
with open('stress_test_performance_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n" + "="*80)
print("CONCLUSION")
print("="*80)

if avg_time < 500:
    print(f"\n[SUCCESS] Performance test passed!")
    print(f"  - Average: {avg_time:.1f}ms (target: <500ms)")
    print(f"  - p95: {p95_time:.1f}ms")
    print(f"  - Meets performance requirements")
else:
    print(f"\n[NEEDS WORK] Performance below target")
    print(f"  - Average: {avg_time:.1f}ms (target: <500ms)")

print(f"\nResults saved to: stress_test_performance_results.json")
print("="*80)


