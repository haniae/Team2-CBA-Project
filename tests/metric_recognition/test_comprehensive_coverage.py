"""Comprehensive test to verify all metrics and tickers work with natural language."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import resolve_metrics, parse_to_structured, normalize
from finanlyzeos_chatbot.parsing.ontology import METRIC_SYNONYMS
from finanlyzeos_chatbot.analytics_engine import (
    BASE_METRICS, DERIVED_METRICS, AGGREGATE_METRICS, 
    SUPPLEMENTAL_METRICS, METRIC_NAME_ALIASES
)

def get_all_supported_metrics():
    """Get all metrics supported by the system."""
    all_metrics = set()
    
    # Base metrics
    all_metrics.update(BASE_METRICS)
    
    # Derived metrics
    all_metrics.update(DERIVED_METRICS)
    
    # Aggregate metrics
    all_metrics.update(AGGREGATE_METRICS)
    
    # Supplemental metrics
    all_metrics.update(SUPPLEMENTAL_METRICS)
    
    # Metric name aliases (values)
    all_metrics.update(METRIC_NAME_ALIASES.values())
    
    # All synonyms from ontology (values)
    all_metrics.update(METRIC_SYNONYMS.values())
    
    return sorted(all_metrics)

def get_all_tickers():
    """Get all supported tickers."""
    ticker_file = Path(__file__).parent / "data" / "tickers" / "universe_sp500.txt"
    if not ticker_file.exists():
        return []
    
    tickers = []
    for line in ticker_file.read_text(encoding="utf-8").splitlines():
        ticker = line.strip().upper()
        if ticker and not ticker.startswith("#"):
            tickers.append(ticker)
    
    return sorted(tickers)

def test_metric_coverage():
    """Test that all metrics have natural language support."""
    all_metrics = get_all_supported_metrics()
    
    print("=" * 80)
    print("Testing Metric Natural Language Coverage")
    print("=" * 80)
    print(f"\nTotal metrics found: {len(all_metrics)}")
    print()
    
    # Get all metric IDs that have synonyms
    metrics_with_synonyms = set(METRIC_SYNONYMS.values())
    
    # Find metrics without synonyms
    metrics_without_synonyms = []
    for metric in all_metrics:
        if metric not in metrics_with_synonyms:
            # Check if it's a canonical form that should have synonyms
            if metric not in ["employee_count", "r_and_d"]:  # These might be edge cases
                metrics_without_synonyms.append(metric)
    
    print(f"Metrics with natural language synonyms: {len(metrics_with_synonyms)}")
    print(f"Metrics without natural language synonyms: {len(metrics_without_synonyms)}")
    
    if metrics_without_synonyms:
        print("\nMetrics missing natural language support:")
        for metric in sorted(metrics_without_synonyms):
            print(f"  - {metric}")
    
    # Test a sample of metrics
    print("\n" + "=" * 80)
    print("Testing Sample Metric Queries")
    print("=" * 80)
    
    test_queries = [
        ("What is Apple's revenue?", "revenue"),
        ("What is Apple's net income?", "net_income"),
        ("What is Apple's EPS?", "eps_diluted"),
        ("What is Apple's P/E?", "pe_ratio"),
        ("What is Apple's EBITDA?", "ebitda"),
        ("What is Apple's free cash flow?", "free_cash_flow"),
        ("What is Apple's ROE?", "roe"),
        ("What is Apple's market cap?", "market_cap"),
        ("What is Apple's debt to equity?", "debt_to_equity"),
        ("What is Apple's current ratio?", "current_ratio"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric in test_queries:
        structured = parse_to_structured(query)
        found_metrics = [m.get("key") for m in structured.get("vmetrics", [])]
        
        if expected_metric in found_metrics:
            print(f"[PASS] {query} -> {expected_metric}")
            passed += 1
        else:
            print(f"[FAIL] {query} -> Expected: {expected_metric}, Got: {found_metrics}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return metrics_without_synonyms

def test_ticker_coverage():
    """Test that ticker resolution works for all tickers."""
    all_tickers = get_all_tickers()
    
    print("\n" + "=" * 80)
    print("Testing Ticker Natural Language Coverage")
    print("=" * 80)
    print(f"\nTotal tickers found: {len(all_tickers)}")
    
    # Test a sample of tickers
    sample_tickers = all_tickers[:20]  # Test first 20
    
    print(f"\nTesting sample of {len(sample_tickers)} tickers...")
    
    passed = 0
    failed = 0
    
    for ticker in sample_tickers:
        # Try different query formats
        queries = [
            f"What is {ticker}'s revenue?",
            f"What is {ticker} revenue?",
            f"Show me {ticker} revenue",
        ]
        
        found = False
        for query in queries:
            structured = parse_to_structured(query)
            found_tickers = [t.get("ticker") for t in structured.get("tickers", [])]
            
            if ticker in found_tickers:
                found = True
                break
        
        if found:
            print(f"[PASS] {ticker} recognized")
            passed += 1
        else:
            print(f"[FAIL] {ticker} not recognized")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(sample_tickers)}")
    
    return len(all_tickers)

def generate_missing_synonyms(metrics_without_synonyms):
    """Generate natural language synonyms for metrics that don't have them."""
    print("\n" + "=" * 80)
    print("Generating Missing Natural Language Synonyms")
    print("=" * 80)
    
    suggestions = {}
    
    for metric in metrics_without_synonyms:
        # Generate natural language variations based on metric name
        metric_parts = metric.split("_")
        
        # Basic variations
        variations = [
            metric,  # Canonical form
            " ".join(metric_parts),  # Space separated
            "-".join(metric_parts),  # Hyphenated
        ]
        
        # Add common abbreviations
        if len(metric_parts) == 2:
            abbrev = "".join([p[0].upper() for p in metric_parts])
            variations.append(abbrev.lower())
            variations.append(abbrev)
        
        suggestions[metric] = variations
    
    print("\nSuggested synonyms to add:")
    for metric, variations in suggestions.items():
        print(f"\n{metric}:")
        for var in variations[:5]:  # Show first 5
            print(f"  '{var}': '{metric}',")
    
    return suggestions

if __name__ == "__main__":
    print("Comprehensive Coverage Test")
    print("=" * 80)
    
    # Test metrics
    missing_metrics = test_metric_coverage()
    
    # Test tickers
    total_tickers = test_ticker_coverage()
    
    # Generate suggestions
    if missing_metrics:
        generate_missing_synonyms(missing_metrics)
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total metrics: {len(get_all_supported_metrics())}")
    print(f"Total tickers: {total_tickers}")
    print(f"Metrics missing synonyms: {len(missing_metrics)}")
    print("\nTest complete!")

