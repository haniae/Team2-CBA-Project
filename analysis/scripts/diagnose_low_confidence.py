#!/usr/bin/env python3
"""Diagnose why confidence is low - debug fact extraction."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.response_verifier import extract_financial_numbers

# Example response that might have low confidence
response = """
Apple's revenue for FY2024 reached $394.3 billion, up 7.2% YoY from $368.1B in FY2023.

The revenue growth was driven by:
- iPhone sales: $201.2B (up 5.1%)
- Services: $85.2B (up 14.2%)  
- Mac: $29.4B (down 2.3%)
- iPad: $28.3B (flat)
- Wearables: $39.8B (up 3.5%)

Apple's gross margin improved to 45.9%, and operating margin reached 30.7%.
Net income was $99.8B, representing a net margin of 25.3%.

The P/E ratio stands at 32.5x, with ROE of 160.5%.

[10-K FY2024](https://sec.gov/...)
[10-Q Q3](https://sec.gov/...)
"""

print("="*80)
print("DIAGNOSING LOW CONFIDENCE ISSUE")
print("="*80)

print("\nSample Response:")
print("-"*80)
print(response[:300] + "...")
print("-"*80)

print("\nExtracting facts...")
facts = extract_financial_numbers(response)

print(f"\nTotal facts extracted: {len(facts)}")
print("\nDet")
print(f"{'#':<4}{'Value':<15}{'Unit':<8}{'Metric':<20}{'Ticker':<10}{'Period':<12}{'Position':<10}")
print("-"*80)

for i, fact in enumerate(facts, 1):
    print(f"{i:<4}{fact.value:<15.1f}{fact.unit or 'None':<8}{fact.metric or 'None':<20}{fact.ticker or 'None':<10}{fact.period or 'None':<12}{fact.position:<10}")

# Count how many have ticker and metric
facts_with_ticker = sum(1 for f in facts if f.ticker)
facts_with_metric = sum(1 for f in facts if f.metric)
facts_verifiable = sum(1 for f in facts if f.ticker and f.metric)

print(f"\nSummary:")
print(f"  Facts with ticker: {facts_with_ticker}/{len(facts)}")
print(f"  Facts with metric: {facts_with_metric}/{len(facts)}")
print(f"  Facts verifiable: {facts_verifiable}/{len(facts)}")

if facts_verifiable < len(facts):
    print(f"\n[PROBLEM] Only {facts_verifiable}/{len(facts)} facts can be verified!")
    print(f"          {len(facts) - facts_verifiable} facts are missing ticker or metric.")
    print(f"\nThis is why confidence is low:")
    print(f"  - Unverified facts: {len(facts) - facts_verifiable} × 10% = {(len(facts) - facts_verifiable) * 10}% penalty")
    print(f"  - Base: 100% - {(len(facts) - facts_verifiable) * 10}% = {100 - (len(facts) - facts_verifiable) * 10}% confidence")
else:
    print(f"\n[OK] All facts have ticker and metric - should verify successfully")

print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

# Analyze why ticker/metric identification fails
print("\nChecking metric identification...")
for i, fact in enumerate(facts[:5], 1):
    print(f"\n{i}. Context: \"{fact.context[:80]}...\"")
    print(f"   Metric identified: {fact.metric or '[NONE]'}")
    if not fact.metric:
        print(f"   [ISSUE] Could not identify metric from context")

print("\nChecking ticker identification...")
for i, fact in enumerate(facts[:5], 1):
    print(f"\n{i}. Context: \"{fact.context[:80]}...\"")
    print(f"   Ticker identified: {fact.ticker or '[NONE]'}")
    if not fact.ticker:
        print(f"   [ISSUE] Could not identify ticker from context")

print("\n" + "="*80)
print("SOLUTION")
print("="*80)
print("""
The low confidence is caused by poor ticker/metric identification.

To fix this, we need to:
1. Use the full response text (not just local context) for ticker identification
2. Infer ticker from earlier in the response ("Apple's revenue" at start)
3. Carry forward ticker to subsequent facts
4. Improve metric keyword matching

The verification system works - it's the extraction that needs improvement.
""")
print("="*80)


