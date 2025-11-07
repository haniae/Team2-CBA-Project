#!/usr/bin/env python3
"""Show which facts are failing verification."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.response_verifier import extract_financial_numbers, verify_fact

settings = load_settings()
engine = AnalyticsEngine(settings)

# Get real data
metrics_aapl = engine.get_metrics("AAPL")
revenue_metric = next((m for m in metrics_aapl if m.metric == "revenue"), None)
revenue_b = revenue_metric.value / 1_000_000_000
period = revenue_metric.period

response = f"""Apple's revenue for {period} reached ${revenue_b:.1f} billion, up 7.2% YoY.

The revenue growth was driven by:
- iPhone sales: $201.2B (up 5.1%)
- Services: $85.2B (up 14.2%)  
- Mac: $29.4B (down 2.3%)

Apple's gross margin improved to 45.9%, and operating margin reached 30.7%.
"""

print("Extracting and verifying facts...\n")
facts = extract_financial_numbers(response)

failed_facts = []
for i, fact in enumerate(facts, 1):
    result = verify_fact(fact, engine, str(settings.database_path))
    status = "OK" if result.is_correct else "FAIL"
    db_val = f"{result.actual_value:.1f}" if result.actual_value else "N/A"
    print(f"{i:2d}. [{status}] {fact.metric:<20s} {fact.value:>8.1f}{fact.unit:<3s} " +
          f"DB: {db_val:<10s} Dev: {result.deviation:6.2f}%")
    
    if not result.is_correct:
        failed_facts.append((fact, result))

print(f"\n{'='*80}")
print(f"FAILED FACTS ANALYSIS")
print(f"{'='*80}\n")

for fact, result in failed_facts:
    print(f"Metric: {fact.metric}")
    print(f"  Extracted: {fact.value}{fact.unit}")
    print(f"  Database: {result.actual_value}")
    print(f"  Deviation: {result.deviation:.2f}%")
    print(f"  Context: {fact.context[:80]}")
    print(f"  Message: {result.message}")
    print()

# Check what metrics are available in database
print(f"Available metrics in database for AAPL:")
unique_metrics = sorted(set(m.metric for m in metrics_aapl))
print(f"  Total: {len(unique_metrics)}")
print(f"  Metrics: {', '.join(unique_metrics[:20])}")

