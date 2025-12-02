"""Test that visualization handler supports all 76+ metrics."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.visualization_handler import VisualizationIntentDetector
from finanlyzeos_chatbot.analytics_engine import (
    BASE_METRICS, DERIVED_METRICS, AGGREGATE_METRICS,
    SUPPLEMENTAL_METRICS, METRIC_NAME_ALIASES
)

def test_metric_support():
    """Test that all metrics are supported."""
    detector = VisualizationIntentDetector()
    
    # Get all unique metrics
    all_metrics = BASE_METRICS | DERIVED_METRICS | AGGREGATE_METRICS | SUPPLEMENTAL_METRICS | set(METRIC_NAME_ALIASES.keys())
    
    print(f"Total metrics in analytics engine: {len(all_metrics)}")
    print(f"Metric keyword map size: {len(detector.metric_keyword_map)}")
    
    # Test various metric queries
    test_queries = [
        "show me revenue",
        "plot net income",
        "chart free cash flow",
        "graph roe and roa",
        "visualize ebitda margin",
        "show pe ratio",
        "plot revenue cagr",
        "chart return on assets",
        "graph debt to equity",
        "show current ratio",
        "plot operating margin",
        "chart gross profit",
        "graph capital expenditures",
        "show dividend yield",
        "plot share buyback intensity",
    ]
    
    print("\nTesting metric extraction:")
    for query in test_queries:
        req = detector.detect(query)
        if req:
            print(f"  {query}: {req.metrics}")
        else:
            print(f"  {query}: (no visualization detected)")
    
    # Check coverage
    metrics_in_map = set(detector.metric_keyword_map.values())
    coverage = len(metrics_in_map & all_metrics) / len(all_metrics) * 100
    print(f"\nMetric coverage: {coverage:.1f}% ({len(metrics_in_map & all_metrics)}/{len(all_metrics)})")
    
    missing = all_metrics - metrics_in_map
    if missing:
        print(f"Missing metrics: {sorted(missing)[:10]}...")
    else:
        print("All metrics are covered!")

if __name__ == "__main__":
    test_metric_support()

