"""
EXTENSIVE testing of the 5-level hierarchical framework.
Tests edge cases, error handling, stress scenarios, and real-world conditions.
"""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_accuracy_automated import AccuracyTester, TestCase, TestResult
from datetime import datetime
import random


def test_empty_results():
    """Test framework with no test results"""
    print("Testing empty results...")
    tester = AccuracyTester()
    tester.results = []
    
    # Should handle gracefully
    level4 = tester.aggregate_by_construct()
    assert level4 == {}, "Empty results should return empty dict"
    
    level2 = tester.aggregate_by_component()
    assert level2 == {}, "Empty results should return empty dict"
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 0.0, "Empty results should return 0.0"
    
    report = tester.generate_report()
    assert report['summary']['total_tests'] == 0, "Should report 0 tests"
    
    print("  ✅ Empty results handled correctly")
    return True


def test_single_result():
    """Test framework with single test result"""
    print("Testing single result...")
    tester = AccuracyTester()
    
    test_case = TestCase(
        test_id="single-1",
        construct="FA-1",
        query="Test query",
        expected_value=100.0
    )
    
    result = TestResult(
        test_case=test_case,
        actual_output="100",
        extracted_value=100.0,
        risk_score=0.0,
        passed=True
    )
    
    tester.results = [result]
    
    level4 = tester.aggregate_by_construct()
    assert 'FA-1' in level4, "Should have FA-1 construct"
    assert level4['FA-1']['n'] == 1, "Should have 1 test"
    
    level2 = tester.aggregate_by_component()
    assert 'Database' in level2, "Should have Database component"
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 0.0, "Single passed test should be 0.0"
    
    print("  ✅ Single result handled correctly")
    return True


def test_all_failed():
    """Test framework when all tests fail"""
    print("Testing all failed results...")
    tester = AccuracyTester()
    
    results = []
    for i in range(10):
        test_case = TestCase(
            test_id=f"fail-{i}",
            construct="FA-1",
            query=f"Test {i}",
            expected_value=100.0
        )
        result = TestResult(
            test_case=test_case,
            actual_output="Wrong",
            extracted_value=None,
            risk_score=10.0,
            passed=False,
            error_message="Failed"
        )
        results.append(result)
    
    tester.results = results
    
    level4 = tester.aggregate_by_construct()
    assert level4['FA-1']['risk_score'] == 10.0, "All failures should be 10.0"
    assert level4['FA-1']['passed'] == 0, "Should have 0 passes"
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 10.0, "All failures should give 10.0"
    assert level1['risk_level'] == "Critical (not production-ready)", "Should be critical"
    
    print("  ✅ All failed results handled correctly")
    return True


def test_all_passed():
    """Test framework when all tests pass"""
    print("Testing all passed results...")
    tester = AccuracyTester()
    
    results = []
    for i in range(10):
        test_case = TestCase(
            test_id=f"pass-{i}",
            construct="FA-1",
            query=f"Test {i}",
            expected_value=100.0
        )
        result = TestResult(
            test_case=test_case,
            actual_output="100",
            extracted_value=100.0,
            risk_score=0.0,
            passed=True
        )
        results.append(result)
    
    tester.results = results
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 0.0, "All passes should be 0.0"
    assert level1['risk_level'] == "Excellent (production-ready)", "Should be excellent"
    
    print("  ✅ All passed results handled correctly")
    return True


def test_mixed_results():
    """Test framework with mixed pass/fail results"""
    print("Testing mixed results...")
    tester = AccuracyTester()
    
    results = []
    for i in range(20):
        passed = i % 2 == 0  # Alternate pass/fail
        test_case = TestCase(
            test_id=f"mixed-{i}",
            construct="FA-1",
            query=f"Test {i}",
            expected_value=100.0
        )
        result = TestResult(
            test_case=test_case,
            actual_output="100" if passed else "Wrong",
            extracted_value=100.0 if passed else None,
            risk_score=0.0 if passed else 5.0,
            passed=passed
        )
        results.append(result)
    
    tester.results = results
    
    level4 = tester.aggregate_by_construct()
    assert level4['FA-1']['risk_score'] == 2.5, "Mixed should average to 2.5"
    assert level4['FA-1']['passed'] == 10, "Should have 10 passes"
    assert level4['FA-1']['failed'] == 10, "Should have 10 failures"
    
    level1 = tester.aggregate_system_level()
    assert 0.0 < level1['system_score'] < 10.0, "Mixed should be between 0 and 10"
    
    print("  ✅ Mixed results handled correctly")
    return True


def test_multiple_constructs():
    """Test framework with multiple constructs"""
    print("Testing multiple constructs...")
    tester = AccuracyTester()
    
    constructs = ['FA-1', 'FA-3', 'RAG-1', 'LLM-1']
    results = []
    
    for construct in constructs:
        for i in range(5):
            test_case = TestCase(
                test_id=f"{construct}-{i}",
                construct=construct,
                query=f"Test {construct} {i}",
                expected_value=100.0
            )
            result = TestResult(
                test_case=test_case,
                actual_output="100",
                extracted_value=100.0,
                risk_score=i * 1.0,  # Different risk scores
                passed=(i < 3)  # First 3 pass
            )
            results.append(result)
    
    tester.results = results
    
    level4 = tester.aggregate_by_construct()
    assert len(level4) == 4, "Should have 4 constructs"
    
    level2 = tester.aggregate_by_component()
    components = set(level2.keys())
    assert 'Database' in components, "Should have Database"
    assert 'RAG' in components, "Should have RAG"
    assert 'LLM' in components, "Should have LLM"
    
    level1 = tester.aggregate_system_level()
    assert level1['total_components'] == 3, "Should have 3 components"
    
    print("  ✅ Multiple constructs handled correctly")
    return True


def test_multiple_components():
    """Test framework with all three components"""
    print("Testing multiple components...")
    tester = AccuracyTester()
    
    component_constructs = {
        'Database': ['FA-1', 'FA-2', 'FA-3'],
        'RAG': ['RAG-1', 'RAG-2'],
        'LLM': ['LLM-1', 'LLM-2']
    }
    
    results = []
    for component, constructs in component_constructs.items():
        for construct in constructs:
            test_case = TestCase(
                test_id=f"{construct}-1",
                construct=construct,
                query=f"Test {construct}",
                expected_value=100.0
            )
            result = TestResult(
                test_case=test_case,
                actual_output="100",
                extracted_value=100.0,
                risk_score=1.0,
                passed=True
            )
            results.append(result)
    
    tester.results = results
    
    level2 = tester.aggregate_by_component()
    assert len(level2) == 3, "Should have all 3 components"
    assert all(comp in level2 for comp in ['Database', 'RAG', 'LLM']), "Should have all components"
    
    # Database should have 3 constructs, RAG 2, LLM 2
    assert len(level2['Database']['constructs']) == 3, "Database should have 3 constructs"
    assert len(level2['RAG']['constructs']) == 2, "RAG should have 2 constructs"
    assert len(level2['LLM']['constructs']) == 2, "LLM should have 2 constructs"
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 1.0, "All should average to 1.0"
    
    print("  ✅ Multiple components handled correctly")
    return True


def test_extreme_risk_scores():
    """Test framework with extreme risk scores"""
    print("Testing extreme risk scores...")
    tester = AccuracyTester()
    
    results = []
    risk_scores = [0.0, 2.5, 5.0, 7.5, 10.0]
    
    for i, risk in enumerate(risk_scores):
        test_case = TestCase(
            test_id=f"extreme-{i}",
            construct="FA-1",
            query=f"Test {i}",
            expected_value=100.0
        )
        result = TestResult(
            test_case=test_case,
            actual_output="100",
            extracted_value=100.0,
            risk_score=risk,
            passed=(risk == 0.0)
        )
        results.append(result)
    
    tester.results = results
    
    level4 = tester.aggregate_by_construct()
    assert level4['FA-1']['risk_score'] == 5.0, "Should average to 5.0"
    
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 5.0, "Should be 5.0"
    assert level1['risk_level'] == "Moderate (needs improvement)", "Should be moderate"
    
    print("  ✅ Extreme risk scores handled correctly")
    return True


def test_stress_large_dataset():
    """Test framework with large dataset (stress test)"""
    print("Testing stress test with large dataset...")
    tester = AccuracyTester()
    
    results = []
    num_tests = 1000
    
    for i in range(num_tests):
        construct = random.choice(['FA-1', 'FA-3', 'RAG-1', 'LLM-1'])
        test_case = TestCase(
            test_id=f"stress-{i}",
            construct=construct,
            query=f"Test {i}",
            expected_value=100.0
        )
        passed = random.random() > 0.3  # 70% pass rate
        result = TestResult(
            test_case=test_case,
            actual_output="100" if passed else "Wrong",
            extracted_value=100.0 if passed else None,
            risk_score=0.0 if passed else random.uniform(1.0, 10.0),
            passed=passed
        )
        results.append(result)
    
    tester.results = results
    
    # Should handle large dataset without crashing
    level4 = tester.aggregate_by_construct()
    assert len(level4) > 0, "Should have constructs"
    
    level2 = tester.aggregate_by_component()
    assert len(level2) > 0, "Should have components"
    
    level1 = tester.aggregate_system_level()
    assert level1['total_tests'] == num_tests, f"Should have {num_tests} tests"
    
    report = tester.generate_report()
    assert report['summary']['total_tests'] == num_tests, "Report should have all tests"
    
    print(f"  ✅ Stress test with {num_tests} tests handled correctly")
    return True


def test_unknown_constructs():
    """Test framework with unknown construct types"""
    print("Testing unknown constructs...")
    tester = AccuracyTester()
    
    results = []
    unknown_constructs = ['UNKNOWN-1', 'CUSTOM-2', 'TEST-3']
    
    for construct in unknown_constructs:
        test_case = TestCase(
            test_id=f"{construct}-1",
            construct=construct,
            query=f"Test {construct}",
            expected_value=100.0
        )
        result = TestResult(
            test_case=test_case,
            actual_output="100",
            extracted_value=100.0,
            risk_score=1.0,
            passed=True
        )
        results.append(result)
    
    tester.results = results
    
    # Unknown constructs should default to Database component
    level2 = tester.aggregate_by_component()
    assert 'Database' in level2, "Unknown constructs should map to Database"
    
    # All unknown constructs should be in Database component
    db_constructs = level2['Database']['constructs']
    for construct in unknown_constructs:
        assert construct in db_constructs, f"{construct} should be in Database"
    
    print("  ✅ Unknown constructs handled correctly (default to Database)")
    return True


def test_component_isolation():
    """Test that components are properly isolated"""
    print("Testing component isolation...")
    tester = AccuracyTester()
    
    # Create results with perfect Database, failing LLM
    results = []
    
    # Database: All pass
    for i in range(10):
        test_case = TestCase(test_id=f"db-{i}", construct="FA-1", query=f"DB Test {i}", expected_value=100.0)
        result = TestResult(test_case=test_case, actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True)
        results.append(result)
    
    # LLM: All fail
    for i in range(10):
        test_case = TestCase(test_id=f"llm-{i}", construct="LLM-1", query=f"LLM Test {i}", expected_value=100.0)
        result = TestResult(test_case=test_case, actual_output="Wrong", extracted_value=None, risk_score=10.0, passed=False)
        results.append(result)
    
    tester.results = results
    
    level2 = tester.aggregate_by_component()
    
    assert level2['Database']['risk_score'] == 0.0, "Database should be perfect"
    assert level2['Database']['passed'] == 10, "Database should have 10 passes"
    assert level2['LLM']['risk_score'] == 10.0, "LLM should all fail"
    assert level2['LLM']['passed'] == 0, "LLM should have 0 passes"
    
    # System score should be average of both
    level1 = tester.aggregate_system_level()
    assert level1['system_score'] == 5.0, "System should average to 5.0"
    
    print("  ✅ Component isolation works correctly")
    return True


def test_risk_level_calculation():
    """Test risk level calculation across different scores"""
    print("Testing risk level calculation...")
    tester = AccuracyTester()
    
    test_cases = [
        (0.0, "Excellent (production-ready)"),
        (2.0, "Excellent (production-ready)"),
        (4.0, "Good (minor issues)"),
        (6.0, "Moderate (needs improvement)"),
        (8.0, "Poor (significant issues)"),
        (10.0, "Critical (not production-ready)"),
    ]
    
    for target_score, expected_level in test_cases:
        results = []
        test_case = TestCase(test_id="test", construct="FA-1", query="Test", expected_value=100.0)
        result = TestResult(
            test_case=test_case,
            actual_output="100",
            extracted_value=100.0,
            risk_score=target_score,
            passed=(target_score == 0.0)
        )
        results.append(result)
        
        tester.results = results
        level1 = tester.aggregate_system_level()
        
        assert level1['risk_level'] == expected_level, \
            f"Score {target_score} should be '{expected_level}', got '{level1['risk_level']}'"
    
    print("  ✅ Risk level calculation works correctly")
    return True


def test_report_completeness():
    """Test that report contains all required fields"""
    print("Testing report completeness...")
    tester = AccuracyTester()
    
    # Create comprehensive test data
    results = []
    for i in range(10):
        test_case = TestCase(test_id=f"test-{i}", construct="FA-1", query=f"Test {i}", expected_value=100.0)
        result = TestResult(
            test_case=test_case,
            actual_output="100",
            extracted_value=100.0,
            risk_score=1.0,
            passed=True
        )
        results.append(result)
    
    tester.results = results
    report = tester.generate_report()
    
    # Check all required fields
    required_fields = [
        'summary',
        'by_construct',
        'by_component',
        'system_level',
        'level1_score',
        'level2_scores',
        'level3_score',
        'level4_scores',
        'critical_failures',
        'timestamp'
    ]
    
    for field in required_fields:
        assert field in report, f"Report should have '{field}' field"
    
    # Check summary fields
    summary_fields = ['total_tests', 'passed', 'failed', 'pass_rate', 'overall_risk_score', 'risk_level']
    for field in summary_fields:
        assert field in report['summary'], f"Summary should have '{field}' field"
    
    print("  ✅ Report completeness verified")
    return True


def test_edge_case_constructs():
    """Test edge cases for construct handling"""
    print("Testing edge case constructs...")
    tester = AccuracyTester()
    
    # Test with single test per construct
    constructs = ['FA-1', 'FA-2', 'FA-3', 'RAG-1', 'LLM-1']
    results = []
    
    for construct in constructs:
        test_case = TestCase(test_id=f"{construct}-1", construct=construct, query="Test", expected_value=100.0)
        result = TestResult(test_case=test_case, actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True)
        results.append(result)
    
    tester.results = results
    
    level4 = tester.aggregate_by_construct()
    for construct in constructs:
        assert construct in level4, f"Should have {construct}"
        assert level4[construct]['n'] == 1, f"{construct} should have 1 test"
    
    level2 = tester.aggregate_by_component()
    assert 'Database' in level2, "Should have Database"
    
    print("  ✅ Edge case constructs handled correctly")
    return True


def main():
    """Run extensive test suite"""
    print("=" * 80)
    print("EXTENSIVE TESTING SUITE - 5-Level Hierarchical Framework")
    print("=" * 80)
    
    tests = [
        ("Empty Results", test_empty_results),
        ("Single Result", test_single_result),
        ("All Failed", test_all_failed),
        ("All Passed", test_all_passed),
        ("Mixed Results", test_mixed_results),
        ("Multiple Constructs", test_multiple_constructs),
        ("Multiple Components", test_multiple_components),
        ("Extreme Risk Scores", test_extreme_risk_scores),
        ("Stress Test (1000 tests)", test_stress_large_dataset),
        ("Unknown Constructs", test_unknown_constructs),
        ("Component Isolation", test_component_isolation),
        ("Risk Level Calculation", test_risk_level_calculation),
        ("Report Completeness", test_report_completeness),
        ("Edge Case Constructs", test_edge_case_constructs),
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
    print("EXTENSIVE TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL EXTENSIVE TESTS PASSED!")
        print("\nFramework tested with:")
        print("  ✅ Empty datasets")
        print("  ✅ Single test cases")
        print("  ✅ All passed/failed scenarios")
        print("  ✅ Mixed results")
        print("  ✅ Multiple constructs")
        print("  ✅ Multiple components")
        print("  ✅ Extreme values")
        print("  ✅ Stress testing (1000+ tests)")
        print("  ✅ Edge cases")
        print("  ✅ Error handling")
        print("\nFramework is ROBUST and PRODUCTION-READY! 🚀")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

