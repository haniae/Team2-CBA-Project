#!/usr/bin/env python3
"""Test to prove 100% confidence is achieved with all fixes applied."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.response_verifier import extract_financial_numbers, verify_response
from benchmarkos_chatbot.confidence_scorer import calculate_confidence

print("="*80)
print("100% CONFIDENCE ACHIEVEMENT TEST")
print("="*80)

settings = load_settings()
engine = AnalyticsEngine(settings)

# Get real data from database
print("\nStep 1: Getting real database values...")
metrics_aapl = engine.get_metrics("AAPL")
revenue_metric = next((m for m in metrics_aapl if m.metric == "revenue"), None)

if not revenue_metric:
    print("[ERROR] No revenue data for AAPL in database")
    sys.exit(1)

revenue_b = revenue_metric.value / 1_000_000_000
period = revenue_metric.period

print(f"  Database revenue: ${revenue_b:.1f}B ({period})")

# Simulate a complex response with segments (like real chatbot would generate)
complex_response = f"""Apple's revenue for {period} reached ${revenue_b:.1f} billion, up 7.2% YoY.

The revenue growth was driven by:
- iPhone sales: $201.2B (up 5.1%)
- Services: $85.2B (up 14.2%)  
- Mac: $29.4B (down 2.3%)
- iPad: $28.3B (flat)
- Wearables: $39.8B (up 3.5%)

Apple's gross margin improved to 45.9%, and operating margin reached 30.7%.

[10-K {period}](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000123)
"""

print("\nStep 2: Extracting facts from response...")
facts = extract_financial_numbers(complex_response, ticker_resolver=None)

print(f"  Total facts extracted: {len(facts)}")
print(f"  Facts with ticker: {sum(1 for f in facts if f.ticker)}/{len(facts)}")
print(f"  Facts with metric: {sum(1 for f in facts if f.metric)}/{len(facts)}")
print(f"  Verifiable facts: {sum(1 for f in facts if f.ticker and f.metric)}/{len(facts)}")

# Show first 10 facts
print("\n  First 10 facts:")
print(f"  {'#':<4}{'Value':<12}{'Unit':<8}{'Metric':<20}{'Ticker':<10}")
print("  " + "-"*60)
for i, fact in enumerate(facts[:10], 1):
    print(f"  {i:<4}{fact.value:<12.1f}{fact.unit or 'None':<8}{fact.metric or 'None':<20}{fact.ticker or 'None':<10}")

# Verify the response
print("\nStep 3: Verifying response...")
verification_result = verify_response(
    complex_response,
    "",  # Empty context - testing extraction only
    "What is Apple's revenue?",
    engine,
    str(settings.database_path),
    ticker_resolver=None
)

print(f"  Total facts: {verification_result.total_facts}")
print(f"  Correct facts: {verification_result.correct_facts}")
print(f"  Verification rate: {verification_result.correct_facts/verification_result.total_facts*100:.1f}%" if verification_result.total_facts > 0 else "N/A")

# Show verification details
print("\n  Verification details (first 5):")
for i, result in enumerate(verification_result.results[:5], 1):
    status = "VERIFIED" if result.is_correct else "FAILED"
    print(f"  {i}. {result.fact.metric or 'Unknown'}: {status} (dev: {result.deviation:.2f}%)")

# Calculate confidence
import re
source_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', complex_response))

confidence = calculate_confidence(
    complex_response,
    verification_result.results,
    source_count=source_count
)

print(f"\nStep 4: Confidence Calculation...")
print(f"  Verified facts: {confidence.verified_facts}/{confidence.total_facts}")
print(f"  Source count: {source_count}")
print(f"  Confidence score: {confidence.score*100:.1f}%")

if confidence.factors:
    print(f"\n  Confidence factors:")
    for factor in confidence.factors:
        print(f"    {factor}")

print("\n" + "="*80)
print("FINAL RESULT")
print("="*80)

if confidence.score >= 0.95:
    print(f"\n[SUCCESS] {confidence.score*100:.0f}% CONFIDENCE ACHIEVED!")
    print(f"  - {confidence.verified_facts}/{confidence.total_facts} facts verified")
    print(f"  - {source_count} sources cited")
    print(f"  - System ready for production")
elif confidence.score >= 0.85:
    print(f"\n[GOOD] {confidence.score*100:.0f}% confidence achieved")
    print(f"  - Above 85% threshold")
    print(f"  - {confidence.verified_facts}/{confidence.total_facts} facts verified")
else:
    print(f"\n[NEEDS WORK] {confidence.score*100:.0f}% confidence")
    print(f"  - Below 85% threshold")
    print(f"  - {confidence.verified_facts}/{confidence.total_facts} facts verified")
    print(f"  - Unverified: {confidence.unverified_facts}")

print("\n" + "="*80)

