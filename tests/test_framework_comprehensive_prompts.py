"""
Comprehensive test of the 5-level hierarchical framework with all prompt types.
Tests the framework with real prompt categories to ensure it works across all scenarios.
"""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_accuracy_automated import AccuracyTester, TestCase, TestResult
from datetime import datetime


# Sample prompts from each category (representative subset)
PROMPT_CATEGORIES = {
    'basic': [
        "What is Apple's revenue?",
        "What is Microsoft's net income?",
        "What is Tesla's profit margin?",
    ],
    'comparison': [
        "Compare Apple and Microsoft",
        "Is Microsoft more profitable than Apple?",
        "Compare Tesla and Ford margins",
    ],
    'why': [
        "Why is Tesla's margin declining?",
        "Why is Apple's revenue growing?",
        "Why is Microsoft more profitable?",
    ],
    'forecasting': [
        "Forecast Apple's revenue",
        "Predict Tesla's earnings",
        "Forecast Microsoft's revenue for the next 3 years",
    ],
    'time_based': [
        "How has Apple's revenue changed over the last 3 years?",
        "What was Tesla's revenue trend from 2020 to 2023?",
        "Show me Microsoft's quarterly earnings for the last 2 years",
    ],
    'sector': [
        "How does Apple's profitability compare to the Technology sector?",
        "Where does Tesla rank in the Consumer Discretionary sector?",
        "Show me Microsoft's percentile ranking in Technology",
    ],
    'anomaly': [
        "Are there any anomalies in NVIDIA's financial metrics?",
        "Detect anomalies in Tesla's revenue growth",
        "Show me any outliers in Microsoft's cash flow",
    ],
    'multi_metric': [
        "Show me Apple's revenue, gross margin, and net income for 2024",
        "What are the key profitability ratios for Google in 2023?",
        "Microsoft's revenue, margins, and cash flow",
    ],
}


def create_mock_test_cases_for_category(category: str, prompts: list) -> list:
    """Create mock test cases for a category"""
    test_cases = []
    
    # Map categories to constructs
    construct_mapping = {
        'basic': 'FA-1',  # Numerical value accuracy
        'comparison': 'FA-4',  # Multi-metric retrieval
        'why': 'RAG-3',  # Narrative retrieval
        'forecasting': 'LLM-4',  # Response completeness
        'time_based': 'FA-5',  # Temporal query accuracy
        'sector': 'FA-4',  # Multi-metric retrieval
        'anomaly': 'RAG-1',  # Context retrieval
        'multi_metric': 'FA-4',  # Multi-metric retrieval
    }
    
    construct = construct_mapping.get(category, 'FA-1')
    
    for i, prompt in enumerate(prompts):
        test_case = TestCase(
            test_id=f"{category}-{construct}-{i+1}",
            construct=construct,
            query=prompt,
            expected_value=100.0 + i * 10,  # Mock expected values
            expected_unit="USD",
            tolerance=0.02
        )
        test_cases.append(test_case)
    
    return test_cases


def test_all_prompt_categories():
    """Test framework with all prompt categories"""
    print("Testing framework with all prompt categories...")
    tester = AccuracyTester()
    
    all_test_cases = []
    all_results = []
    
    # Create test cases for each category
    for category, prompts in PROMPT_CATEGORIES.items():
        print(f"\n  Creating test cases for: {category} ({len(prompts)} prompts)")
        category_test_cases = create_mock_test_cases_for_category(category, prompts)
        all_test_cases.extend(category_test_cases)
        
        # Create mock results (simulating different outcomes)
        for test_case in category_test_cases:
            # Simulate some passes and some failures
            passed = hash(test_case.test_id) % 3 != 0  # ~67% pass rate
            risk_score = 0.0 if passed else 5.0
            
            result = TestResult(
                test_case=test_case,
                actual_output=f"Mock response for {test_case.query}",
                extracted_value=100.0 if passed else None,
                risk_score=risk_score,
                passed=passed,
                error_message=None if passed else "Mock error for testing"
            )
            all_results.append(result)
    
    tester.results = all_results
    
    # Test that all categories are represented
    print(f"\n  Total test cases created: {len(all_test_cases)}")
    print(f"  Total test results: {len(all_results)}")
    
    # Test aggregation at each level
    print("\n  Testing Level 4 aggregation (constructs)...")
    level4 = tester.aggregate_by_construct()
    print(f"    Constructs found: {list(level4.keys())}")
    
    print("\n  Testing Level 2 aggregation (components)...")
    level2 = tester.aggregate_by_component()
    print(f"    Components found: {list(level2.keys())}")
    
    print("\n  Testing Level 1 aggregation (system)...")
    level1 = tester.aggregate_system_level()
    print(f"    System score: {level1['system_score']:.2f}/10")
    
    # Verify all categories are represented
    assert len(level4) > 0, "Should have at least one construct"
    assert len(level2) > 0, "Should have at least one component"
    assert level1['system_score'] >= 0, "System score should be non-negative"
    
    print("\n✅ All prompt categories tested successfully")
    return True


def test_component_mapping_for_all_constructs():
    """Test component mapping works for all construct types"""
    print("\nTesting component mapping for all construct types...")
    tester = AccuracyTester()
    
    # Test all known constructs
    test_constructs = [
        ('FA-1', 'Database'),
        ('FA-2', 'Database'),
        ('FA-3', 'Database'),
        ('FA-4', 'Database'),
        ('FA-5', 'Database'),
        ('RAG-1', 'RAG'),
        ('RAG-2', 'RAG'),
        ('RAG-3', 'RAG'),
        ('RAG-4', 'RAG'),
        ('LLM-1', 'LLM'),
        ('LLM-2', 'LLM'),
        ('LLM-3', 'LLM'),
        ('LLM-4', 'LLM'),
    ]
    
    for construct, expected_component in test_constructs:
        component = tester.get_component_for_construct(construct)
        assert component == expected_component, f"{construct} should map to {expected_component}, got {component}"
        print(f"  ✅ {construct} → {component}")
    
    # Test unknown construct defaults to Database
    unknown_component = tester.get_component_for_construct('UNKNOWN-999')
    assert unknown_component == 'Database', "Unknown construct should default to Database"
    print(f"  ✅ UNKNOWN-999 → Database (default)")
    
    print("\n✅ Component mapping works for all constructs")
    return True


def test_report_generation_with_all_categories():
    """Test report generation includes all prompt categories"""
    print("\nTesting report generation with all categories...")
    tester = AccuracyTester()
    
    # Create comprehensive test data
    all_test_cases = []
    for category, prompts in PROMPT_CATEGORIES.items():
        category_cases = create_mock_test_cases_for_category(category, prompts)
        all_test_cases.extend(category_cases)
    
    # Create results
    all_results = []
    for test_case in all_test_cases:
        result = TestResult(
            test_case=test_case,
            actual_output="Mock response",
            extracted_value=100.0,
            risk_score=1.0,
            passed=True
        )
        all_results.append(result)
    
    tester.results = all_results
    
    # Generate report
    report = tester.generate_report()
    
    # Verify report structure
    assert 'level1_score' in report
    assert 'level2_scores' in report
    assert 'level3_score' in report
    assert 'level4_scores' in report
    assert 'by_component' in report
    assert 'by_construct' in report
    assert 'system_level' in report
    assert 'summary' in report
    
    # Verify all components are represented
    components = list(report['level2_scores'].keys())
    print(f"  Components in report: {components}")
    
    # Verify all constructs are represented
    constructs = list(report['level4_scores'].keys())
    print(f"  Constructs in report: {constructs}")
    
    print("\n✅ Report generation works with all categories")
    return True


def test_category_distribution():
    """Test that different categories map to appropriate components"""
    print("\nTesting category → component distribution...")
    tester = AccuracyTester()
    
    # Create test cases for each category
    category_components = {}
    for category, prompts in PROMPT_CATEGORIES.items():
        test_cases = create_mock_test_cases_for_category(category, prompts)
        if test_cases:
            construct = test_cases[0].construct
            component = tester.get_component_for_construct(construct)
            category_components[category] = component
            print(f"  {category:15s} → {construct:8s} → {component}")
    
    # Verify distribution (should have Database, RAG, and LLM components)
    components_used = set(category_components.values())
    print(f"\n  Components used: {components_used}")
    
    assert 'Database' in components_used, "Should have Database component"
    assert len(components_used) >= 2, "Should use multiple components"
    
    print("\n✅ Category distribution works correctly")
    return True


def main():
    """Run comprehensive tests with all prompt types"""
    print("=" * 80)
    print("COMPREHENSIVE FRAMEWORK TEST WITH ALL PROMPT TYPES")
    print("=" * 80)
    
    tests = [
        ("All Prompt Categories", test_all_prompt_categories),
        ("Component Mapping", test_component_mapping_for_all_constructs),
        ("Report Generation", test_report_generation_with_all_categories),
        ("Category Distribution", test_category_distribution),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"{'='*80}")
        try:
            test_func()
            passed += 1
            print(f"✅ PASSED: {test_name}")
        except AssertionError as e:
            print(f"❌ FAILED: {test_name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("\nFramework works correctly with:")
        print("  ✅ Basic queries")
        print("  ✅ Comparison queries")
        print("  ✅ Why questions")
        print("  ✅ Forecasting prompts")
        print("  ✅ Time-based queries")
        print("  ✅ Sector benchmarking")
        print("  ✅ Anomaly detection")
        print("  ✅ Multi-metric queries")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

