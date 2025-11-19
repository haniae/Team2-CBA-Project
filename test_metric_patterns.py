"""Test metric inference patterns directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.metric_inference import MetricInferenceEngine
import re

engine = MetricInferenceEngine()

test_cases = [
    '$25B in operating cash flow',
    '$8B working capital',
    'dividend yield of 2.5%',
    'dividend yield 3.0%',
    'payout ratio 40%',
    'dividend payout 35%',
    '$80B gross profit',
    '$25B operating expenses',
    'OPEX $20B',
    '$12B R&D expenses',
    '$15B CAPEX',
]

print("Testing metric inference patterns:")
print("=" * 60)

for case in test_cases:
    result = engine.infer_metrics(case)
    metric_ids = [r.metric_id for r in result]
    print(f"{case:40} -> {metric_ids}")

# Test patterns directly
print("\n" + "=" * 60)
print("Testing patterns directly:")
print("=" * 60)

# Test operating cash flow pattern
pattern1 = re.compile(r'\$[\d\.,]+[BMK]?\s+in\s+operating\s+cash\s+flow', re.IGNORECASE)
test1 = '$25B in operating cash flow'
print(f"Pattern: {pattern1.pattern}")
print(f"Text: {test1}")
print(f"Match: {pattern1.search(test1)}")

# Test working capital pattern
pattern2 = re.compile(r'\$[\d\.,]+[BMK]?\s+working\s+capital', re.IGNORECASE)
test2 = '$8B working capital'
print(f"\nPattern: {pattern2.pattern}")
print(f"Text: {test2}")
print(f"Match: {pattern2.search(test2)}")

# Test dividend yield pattern
pattern3 = re.compile(r'\bdividend\s+yield\s+(\d+(?:\.\d+)?)%', re.IGNORECASE)
test3 = 'dividend yield 3.0%'
print(f"\nPattern: {pattern3.pattern}")
print(f"Text: {test3}")
print(f"Match: {pattern3.search(test3)}")

pattern4 = re.compile(r'\bdividend\s+yield\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)%', re.IGNORECASE)
test4 = 'dividend yield of 2.5%'
print(f"\nPattern: {pattern4.pattern}")
print(f"Text: {test4}")
print(f"Match: {pattern4.search(test4)}")

