#!/usr/bin/env python3
"""Quick test to verify patterns are working."""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test a few key patterns
test_queries = [
    ("Imperative", "show me apple revenue"),
    ("Request", "i'd like to see microsoft margins"),
    ("Quantitative", "apple is 2 times more profitable"),
    ("Negation", "isn't tesla growing"),
    ("Causal", "because of nvidia success"),
    ("Aggregation", "sum of all revenue"),
    ("Percentage", "50% of revenue"),
    ("Change", "increase by 20%"),
    ("State", "is currently profitable"),
    ("Relative", "above average performance"),
]

print("Testing Pattern Detection")
print("="*60)

try:
    from finanlyzeos_chatbot.parsing.parse import parse_to_structured
    
    passed = 0
    total = len(test_queries)
    
    for category, query in test_queries:
        try:
            result = parse_to_structured(query)
            intent = result.get('intent', 'N/A')
            tickers = [t.get('ticker', '') for t in result.get('tickers', [])]
            print(f"\n{category}: '{query}'")
            print(f"  Intent: {intent}")
            print(f"  Tickers: {tickers if tickers else 'None'}")
            print("  Status: OK")
            passed += 1
        except Exception as e:
            print(f"\n{category}: '{query}'")
            print(f"  Error: {e}")
            print("  Status: FAILED")
    
    print("\n" + "="*60)
    print(f"Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    print("="*60)
    
except Exception as e:
    print(f"Error importing: {e}")

