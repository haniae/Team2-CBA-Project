"""
Validation test for the complete 5-level hierarchical testing framework.
Tests all new functionality without requiring a running chatbot.
"""

import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

from test_accuracy_automated import AccuracyTester, TestCase, TestResult
from datetime import datetime


def test_component_mapping():
    """Test that component mapping works correctly"""
    print("Testing component mapping...")
    tester = AccuracyTester()
    
    # Test known constructs
    assert tester.get_component_for_construct('FA-1') == 'Database'
    assert tester.get_component_for_construct('FA-3') == 'Database'
    assert tester.get_component_for_construct('RAG-1') == 'RAG'
    assert tester.get_component_for_construct('LLM-1') == 'LLM'
    
    # Test unknown construct (should default to Database)
    assert tester.get_component_for_construct('UNKNOWN-1') == 'Database'
    
    print("✅ Component mapping works correctly")


def test_level5_to_level4():
    """Test Level 5 (test cases) to Level 4 (construct) aggregation"""
    print("\nTesting Level 5 → Level 4 aggregation...")
    tester = AccuracyTester()
    
    # Create mock test results
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
        TestCase(test_id="FA-1-2", construct="FA-1", query="Test 2", expected_value=200.0),
        TestCase(test_id="FA-3-1", construct="FA-3", query="Test 3", expected_value=5.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[1], actual_output="200", extracted_value=200.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[2], actual_output="5", extracted_value=5.0, risk_score=0.0, passed=True),
    ]
    
    tester.results = test_results
    
    # Test aggregation
    level4 = tester.aggregate_by_construct()
    
    assert 'FA-1' in level4
    assert 'FA-3' in level4
    assert level4['FA-1']['n'] == 2
    assert level4['FA-3']['n'] == 1
    assert level4['FA-1']['risk_score'] == 0.0
    assert level4['FA-1']['passed'] == 2
    
    print("✅ Level 4 aggregation works correctly")


def test_level4_to_level2():
    """Test Level 4 (construct) to Level 2 (component) aggregation"""
    print("\nTesting Level 4 → Level 2 aggregation...")
    tester = AccuracyTester()
    
    # Create mock test results with different constructs
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
        TestCase(test_id="FA-3-1", construct="FA-3", query="Test 2", expected_value=5.0),
        TestCase(test_id="RAG-1-1", construct="RAG-1", query="Test 3", expected_value=10.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[1], actual_output="5", extracted_value=5.0, risk_score=1.0, passed=True),
        TestResult(test_case=test_cases[2], actual_output="10", extracted_value=10.0, risk_score=0.0, passed=True),
    ]
    
    tester.results = test_results
    
    # Test aggregation
    level2 = tester.aggregate_by_component()
    
    assert 'Database' in level2
    assert 'RAG' in level2
    assert level2['Database']['n'] == 2  # FA-1 and FA-3 both map to Database
    assert level2['RAG']['n'] == 1
    assert level2['Database']['risk_score'] == 0.5  # Mean of 0.0 and 1.0
    assert 'FA-1' in level2['Database']['constructs']
    assert 'FA-3' in level2['Database']['constructs']
    
    print("✅ Level 2 aggregation works correctly")


def test_level2_to_level1():
    """Test Level 2 (component) to Level 1 (system) aggregation"""
    print("\nTesting Level 2 → Level 1 aggregation...")
    tester = AccuracyTester()
    
    # Create mock test results
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
        TestCase(test_id="LLM-1-1", construct="LLM-1", query="Test 2", expected_value=10.0),
        TestCase(test_id="RAG-1-1", construct="RAG-1", query="Test 3", expected_value=5.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[1], actual_output="10", extracted_value=10.0, risk_score=2.0, passed=True),
        TestResult(test_case=test_cases[2], actual_output="5", extracted_value=5.0, risk_score=1.0, passed=True),
    ]
    
    tester.results = test_results
    
    # Test aggregation
    level1 = tester.aggregate_system_level()
    
    assert 'system_score' in level1
    assert 'risk_level' in level1
    assert 'component_scores' in level1
    assert level1['system_score'] > 0  # Should be mean of component scores
    assert 'Database' in level1['component_scores']
    assert 'LLM' in level1['component_scores']
    assert 'RAG' in level1['component_scores']
    
    print("✅ Level 1 aggregation works correctly")


def test_complete_report():
    """Test that complete report generation works with all 5 levels"""
    print("\nTesting complete report generation...")
    tester = AccuracyTester()
    
    # Create mock test results
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
        TestCase(test_id="FA-3-1", construct="FA-3", query="Test 2", expected_value=5.0),
        TestCase(test_id="LLM-1-1", construct="LLM-1", query="Test 3", expected_value=10.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[1], actual_output="5", extracted_value=5.0, risk_score=0.0, passed=True),
        TestResult(test_case=test_cases[2], actual_output="10", extracted_value=10.0, risk_score=0.0, passed=True),
    ]
    
    tester.results = test_results
    
    # Generate report
    report = tester.generate_report()
    
    # Check all levels are present
    assert 'level1_score' in report
    assert 'level2_scores' in report
    assert 'level3_score' in report
    assert 'level4_scores' in report
    assert 'by_component' in report
    assert 'by_construct' in report
    assert 'system_level' in report
    assert 'summary' in report
    
    # Check Level 1
    assert report['level1_score'] >= 0
    assert report['system_level']['system_score'] >= 0
    
    # Check Level 2
    assert isinstance(report['level2_scores'], dict)
    assert len(report['level2_scores']) > 0
    
    # Check Level 3
    assert report['level3_score'] >= 0
    
    # Check Level 4
    assert isinstance(report['level4_scores'], dict)
    assert len(report['level4_scores']) > 0
    
    print("✅ Complete report generation works correctly")


def test_print_summary():
    """Test that print_summary doesn't crash"""
    print("\nTesting print_summary()...")
    tester = AccuracyTester()
    
    # Create minimal test results
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
    ]
    
    tester.results = test_results
    
    # This should not crash
    try:
        tester.print_summary()
        print("✅ print_summary() works correctly")
    except Exception as e:
        print(f"❌ print_summary() failed: {e}")
        raise


def test_backwards_compatibility():
    """Test that existing functionality still works"""
    print("\nTesting backwards compatibility...")
    tester = AccuracyTester()
    
    # Test that old methods still work
    test_cases = [
        TestCase(test_id="FA-1-1", construct="FA-1", query="Test 1", expected_value=100.0),
    ]
    
    test_results = [
        TestResult(test_case=test_cases[0], actual_output="100", extracted_value=100.0, risk_score=0.0, passed=True),
    ]
    
    tester.results = test_results
    
    # Test old methods
    level4 = tester.aggregate_by_construct()
    assert level4 is not None
    
    report = tester.generate_report()
    assert report is not None
    assert 'summary' in report
    assert 'by_construct' in report
    
    print("✅ Backwards compatibility maintained")


def main():
    """Run all validation tests"""
    print("=" * 80)
    print("VALIDATING 5-LEVEL HIERARCHICAL TESTING FRAMEWORK")
    print("=" * 80)
    
    tests = [
        test_component_mapping,
        test_level5_to_level4,
        test_level4_to_level2,
        test_level2_to_level1,
        test_complete_report,
        test_print_summary,
        test_backwards_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Framework is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

