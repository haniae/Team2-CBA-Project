#!/usr/bin/env python3
"""Test the global ticker extraction fix."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.response_verifier import extract_financial_numbers

print("="*80)
print("GLOBAL TICKER EXTRACTION FIX TEST")
print("="*80)

response = """Apple's revenue for FY2024 reached $394.3 billion, up 7.2% YoY from $368.1B in FY2023.

The revenue growth was driven by:
- iPhone sales: $201.2B (up 5.1%)
- Services: $85.2B (up 14.2%)  
- Mac: $29.4B (down 2.3%)
- iPad: $28.3B (flat)
- Wearables: $39.8B (up 3.5%)

Apple's gross margin improved to 45.9%, and operating margin reached 30.7%.
Net income was $99.8B, representing a net margin of 25.3%.

The P/E ratio stands at 32.5x, with ROE of 160.5%.
"""

print("\nExtracting facts with global ticker...")
facts = extract_financial_numbers(response)

print(f"\nTotal facts extracted: {len(facts)}")

# Check how many have AAPL as ticker
aapl_facts = sum(1 for f in facts if f.ticker == "AAPL")
other_tickers = sum(1 for f in facts if f.ticker and f.ticker != "AAPL")
no_ticker = sum(1 for f in facts if not f.ticker)

print(f"\nTicker distribution:")
print(f"  AAPL: {aapl_facts}")
print(f"  Other: {other_tickers}")
print(f"  None: {no_ticker}")

if aapl_facts == len(facts):
    print(f"\n[SUCCESS] All {len(facts)} facts have AAPL ticker!")
elif aapl_facts > len(facts) * 0.8:
    print(f"\n[GOOD] {aapl_facts}/{len(facts)} facts have AAPL ticker (>80%)")
else:
    print(f"\n[ISSUE] Only {aapl_facts}/{len(facts)} facts have AAPL ticker")

# Show first 5 facts
print(f"\nFirst 5 facts:")
print(f"{'#':<4}{'Value':<12}{'Unit':<8}{'Metric':<20}{'Ticker':<10}")
print("-"*60)
for i, fact in enumerate(facts[:5], 1):
    print(f"{i:<4}{fact.value:<12.1f}{fact.unit or 'None':<8}{fact.metric or 'None':<20}{fact.ticker or 'None':<10}")

# Count verifiable facts
verifiable = sum(1 for f in facts if f.ticker and f.metric)
print(f"\nVerifiable facts: {verifiable}/{len(facts)}")

if verifiable == len(facts):
    print(f"\n[SUCCESS] All facts can be verified!")
    print(f"          Expected confidence: >95%")
elif verifiable > len(facts) * 0.8:
    print(f"\n[GOOD] {verifiable}/{len(facts)} facts can be verified (>80%)")
    print(f"       Expected confidence: ~{100 - (len(facts) - verifiable) * 10}%")
else:
    print(f"\n[ISSUE] Only {verifiable}/{len(facts)} facts can be verified")
    print(f"        Expected confidence: ~{100 - (len(facts) - verifiable) * 10}%")

print("\n" + "="*80)


