#!/usr/bin/env python3
"""Diagnose why real chatbot responses get low confidence."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.response_verifier import extract_financial_numbers, verify_fact
from benchmarkos_chatbot.confidence_scorer import calculate_confidence
import re

print("="*80)
print("DIAGNOSING REAL CHATBOT RESPONSE CONFIDENCE")
print("="*80)

# PASTE YOUR ACTUAL CHATBOT RESPONSE HERE
# This is an example - replace with the actual response you're seeing low confidence on
actual_chatbot_response = """
Apple's revenue for FY2024 reached $391.0 billion, representing strong growth 
in its core product lines. The company reported net income of $99.8 billion, 
reflecting a net margin of 25.5%.

Key financial highlights:
- Revenue: $391.0B (up 7.2% YoY)
- Gross Margin: 46.2%
- Operating Margin: 31.6%
- Net Margin: 25.5%
- Free Cash Flow: $104.0B

The company maintains a strong balance sheet with total assets of $352.7B and
shareholders' equity of $62.1B. The current ratio stands at 1.07.

[10-K FY2024](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193)
"""

print("\n📋 ANALYZING CHATBOT RESPONSE\n")
print("Response length:", len(actual_chatbot_response), "characters")
print("Response preview:", actual_chatbot_response[:150], "...\n")

settings = load_settings()
engine = AnalyticsEngine(settings)

# Step 1: Extract facts
print("STEP 1: FACT EXTRACTION")
print("-"*80)
facts = extract_financial_numbers(actual_chatbot_response)
print(f"Total facts extracted: {len(facts)}\n")

print("Facts breakdown:")
print(f"{'#':<4}{'Value':<12}{'Unit':<8}{'Metric':<25}{'Ticker':<10}{'Can Verify?':<12}")
print("-"*80)

verifiable_count = 0
for i, fact in enumerate(facts, 1):
    can_verify = "Yes" if (fact.ticker and fact.metric) else "No (missing ticker/metric)"
    if fact.ticker and fact.metric:
        verifiable_count += 1
    print(f"{i:<4}{fact.value:<12.1f}{fact.unit or '?':<8}{(fact.metric or 'NONE'):<25}{(fact.ticker or 'NONE'):<10}{can_verify:<12}")

print(f"\nVerifiable facts: {verifiable_count}/{len(facts)}")

if verifiable_count < len(facts):
    print(f"\n⚠️ WARNING: {len(facts) - verifiable_count} facts cannot be verified!")
    print("   This will reduce confidence by:", (len(facts) - verifiable_count) * 10, "%")

# Step 2: Verify each fact
print(f"\nSTEP 2: FACT VERIFICATION")
print("-"*80)

verification_results = []
for i, fact in enumerate(facts, 1):
    if fact.ticker and fact.metric:
        result = verify_fact(fact, engine, str(settings.database_path))
        verification_results.append(result)
        
        status = "✓" if result.is_correct else "✗"
        db_val_str = f"{result.actual_value:.1f}" if result.actual_value else "N/A"
        print(f"{i}. [{status}] {fact.metric:<25s} {fact.value:>8.1f}{fact.unit:<3s} vs DB: {db_val_str:<10s} (dev: {result.deviation:6.2f}%)")
    else:
        print(f"{i}. [SKIP] Cannot verify (missing ticker or metric)")

# Step 3: Calculate confidence
print(f"\nSTEP 3: CONFIDENCE CALCULATION")
print("-"*80)

source_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', actual_chatbot_response))
print(f"Sources cited: {source_count}")

if verification_results:
    conf = calculate_confidence(actual_chatbot_response, verification_results, source_count=source_count)
    
    print(f"\nConfidence Score: {conf.score*100:.1f}%")
    print(f"Verified Facts: {conf.verified_facts}/{conf.total_facts}")
    print(f"Unverified: {conf.unverified_facts}")
    print(f"Discrepancies: {conf.discrepancies}")
    
    print("\nConfidence Factors:")
    for factor in conf.factors:
        print(f"  {factor}")
    
    print(f"\n" + "="*80)
    print("DIAGNOSIS")
    print("="*80)
    
    if conf.score >= 0.95:
        print(f"\n✅ EXCELLENT: {conf.score*100:.0f}% confidence - production-ready!")
    elif conf.score >= 0.85:
        print(f"\n✓ GOOD: {conf.score*100:.0f}% confidence - meets threshold")
    elif conf.score >= 0.70:
        print(f"\n⚠️ MODERATE: {conf.score*100:.0f}% confidence - investigate issues below")
    else:
        print(f"\n❌ LOW: {conf.score*100:.0f}% confidence - significant issues found")
    
    # Detailed diagnosis
    print(f"\nIssue Breakdown:")
    
    if conf.unverified_facts > 0:
        print(f"\n1. UNVERIFIED FACTS: {conf.unverified_facts}")
        print(f"   Impact: -{conf.unverified_facts * 10}% to confidence")
        print(f"   Cause: Facts missing ticker or metric identification")
        print(f"   Fix: Improve ticker/metric extraction from context")
        
        unverified = [f for f in facts if not (f.ticker and f.metric)]
        for i, fact in enumerate(unverified[:5], 1):
            print(f"      {i}. {fact.value}{fact.unit} - ticker:{fact.ticker or 'MISSING'}, metric:{fact.metric or 'MISSING'}")
    
    if conf.discrepancies > 0:
        print(f"\n2. DISCREPANCIES: {conf.discrepancies}")
        print(f"   Impact: -{conf.discrepancies * 20}% to confidence")
        print(f"   Cause: Extracted value doesn't match database")
        print(f"   Fix: Check unit conversion or use database values")
        
        failed = [(f, r) for f, r in zip(facts, verification_results) if not r.is_correct and r.actual_value]
        for i, (fact, result) in enumerate(failed[:5], 1):
            print(f"      {i}. {fact.metric}: extracted {fact.value}{fact.unit}, DB has {result.actual_value:.1f} (dev: {result.deviation:.1f}%)")
    
    if source_count < 3:
        print(f"\n3. FEW SOURCES: {source_count}")
        print(f"   Impact: -5% to confidence")
        print(f"   Fix: Include more source citations in response")
    
    print(f"\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if conf.unverified_facts > 0:
        print("\n→ PRIMARY ISSUE: Ticker/metric extraction")
        print("   The main problem is facts aren't getting ticker or metric assigned")
        print("   This prevents verification even if the data is correct")
    elif conf.discrepancies > 0:
        print("\n→ PRIMARY ISSUE: Value mismatch")
        print("   Facts are extracted but values don't match database")
        print("   Check if LLM is using different data source or values")
    else:
        print("\n→ Minor optimization needed for sources")
        print("   System is working well, just add more source citations")

else:
    print("\n❌ NO VERIFICATION RESULTS")
    print("   All facts are missing ticker or metric")
    print("   Ticker/metric extraction is completely failing")

print("\n" + "="*80)

