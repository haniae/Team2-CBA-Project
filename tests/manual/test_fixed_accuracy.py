#!/usr/bin/env python3
"""Test if the mandatory data block fix works."""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).parent / "src"))

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.context_builder import build_financial_context

print("="*80)
print("TESTING MANDATORY DATA BLOCK FIX")
print("="*80)

settings = load_settings()
engine = AnalyticsEngine(settings)

# Build context for Apple
print("\nBuilding context for Apple (AAPL)...")
context = build_financial_context(
    query="What is Apple's revenue?",
    analytics_engine=engine,
    database_path=str(settings.database_path),
    max_tickers=1
)

if context:
    print("\nChecking for mandatory data block...")
    
    # Check if mandatory block is present
    if "🚨 CRITICAL: USE THESE EXACT VALUES" in context:
        print("✅ Mandatory data block found!")
        
        # Extract and show the mandatory block
        start = context.find("🚨 CRITICAL:")
        end = context.find("="*80, start + 10)
        mandatory_section = context[start:end+80]
        
        print("\nMandatory Data Block:")
        print("-"*80)
        print(mandatory_section)
        print("-"*80)
        
        # Check for critical elements
        checks = {
            'Has period': 'Period:' in mandatory_section or 'FY202' in mandatory_section,
            'Has revenue': 'Revenue:' in mandatory_section,
            'Has warnings': '⚠️ WARNING:' in mandatory_section,
            'Has DO NOT use training': 'DO NOT use' in mandatory_section,
        }
        
        print("\nValidation:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
        
        if all(checks.values()):
            print("\n[SUCCESS] Mandatory data block is complete and should prevent LLM from using training data!")
        else:
            print("\n[PARTIAL] Some elements missing from mandatory block")
    else:
        print("❌ Mandatory data block NOT found!")
        print("   Context doesn't have the explicit data instructions")
    
    # Check for FRED warnings
    if "⚠️ CRITICAL: These are economic indicators" in context:
        print("\n✅ FRED warning block found!")
    
    print(f"\nTotal context length: {len(context)} characters")
else:
    print("❌ No context built")

print("\n" + "="*80)


