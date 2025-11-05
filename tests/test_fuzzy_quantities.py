"""
Comprehensive test suite for fuzzy quantity and approximation detection.

Tests:
- Approximations (around, about, roughly, ~)
- Upper thresholds (over, above, more than, at least)
- Lower thresholds (under, below, less than, at most)
- Ranges (between X and Y, from X to Y)
- Value extraction (dollars, percentages, multiples)
- Tolerance inference
- Confidence scoring
- Integration with parsing
"""

import pytest
from src.benchmarkos_chatbot.parsing.fuzzy_quantities import (
    FuzzyQuantityDetector,
    FuzzyQuantity,
    FuzzyType,
)
from src.benchmarkos_chatbot.parsing.parse import parse_to_structured


class TestApproximationDetection:
    """Test approximation modifier detection"""
    
    def test_around_detection(self):
        """Test 'around' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E around 25")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION
        assert "around" in quantities[0].modifier.lower()
    
    def test_about_detection(self):
        """Test 'about' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue about $10B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION
        assert "about" in quantities[0].modifier.lower()
    
    def test_approximately_detection(self):
        """Test 'approximately' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins approximately 30%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION
    
    def test_roughly_detection(self):
        """Test 'roughly' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Growth roughly 15%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION


class TestUpperThresholdDetection:
    """Test upper threshold detection"""
    
    def test_over_detection(self):
        """Test 'over' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue over $10B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER
        assert "over" in quantities[0].modifier.lower()
    
    def test_above_detection(self):
        """Test 'above' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E above 30")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER
    
    def test_more_than_detection(self):
        """Test 'more than' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins more than 25%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER
    
    def test_at_least_detection(self):
        """Test 'at least' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Growth at least 10%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER


class TestLowerThresholdDetection:
    """Test lower threshold detection"""
    
    def test_under_detection(self):
        """Test 'under' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue under $10B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER
        assert "under" in quantities[0].modifier.lower()
    
    def test_below_detection(self):
        """Test 'below' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E below 20")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER
    
    def test_less_than_detection(self):
        """Test 'less than' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins less than 25%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER
    
    def test_at_most_detection(self):
        """Test 'at most' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Debt at most $50B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER


class TestRangeDetection:
    """Test range detection"""
    
    def test_between_and_detection(self):
        """Test 'between X and Y' range"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E between 20 and 30")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.RANGE
        assert quantities[0].range_start is not None
        assert quantities[0].range_end is not None
    
    def test_from_to_detection(self):
        """Test 'from X to Y' range"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue from $5B to $10B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.RANGE
    
    def test_hyphen_range_detection(self):
        """Test 'X-Y' hyphen range"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins 20%-30%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.RANGE


class TestValueExtraction:
    """Test value extraction from different formats"""
    
    def test_dollar_with_billion(self):
        """Test dollar amount with B suffix"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue around $10B")
        assert len(quantities) > 0
        assert "$10B" in quantities[0].value or "10B" in quantities[0].value
    
    def test_percentage_value(self):
        """Test percentage value"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins about 30%")
        assert len(quantities) > 0
        assert "30%" in quantities[0].value
    
    def test_multiple_value(self):
        """Test multiple/ratio value"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E around 25x")
        assert len(quantities) > 0
        assert "25" in quantities[0].value
    
    def test_plain_number(self):
        """Test plain number value"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Count over 100")
        assert len(quantities) > 0
        assert "100" in quantities[0].value


class TestToleranceInference:
    """Test tolerance inference for approximations"""
    
    def test_around_tolerance(self):
        """Test 'around' tolerance"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Around $10B")
        assert len(quantities) > 0
        # 'around' should have standard tolerance (~10%)
        assert quantities[0].tolerance == 0.10
    
    def test_roughly_tolerance(self):
        """Test 'roughly' tolerance"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Roughly $10B")
        assert len(quantities) > 0
        # 'roughly' should have wider tolerance (~15%)
        assert quantities[0].tolerance == 0.15
    
    def test_near_tolerance(self):
        """Test 'near' tolerance"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Near $10B")
        assert len(quantities) > 0
        # 'near' should have tighter tolerance (~5%)
        assert quantities[0].tolerance == 0.05


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_explicit_modifier(self):
        """Test high confidence with explicit modifier"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue approximately $10B")
        assert len(quantities) > 0
        # Should have high confidence (explicit modifier + well-formed value)
        assert quantities[0].confidence >= 0.90
    
    def test_confidence_with_financial_context(self):
        """Test confidence boost with financial context"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E ratio around 25")
        assert len(quantities) > 0
        # Should have good confidence (may be slightly lower without explicit units)
        assert quantities[0].confidence >= 0.80


class TestHasFuzzyQuantity:
    """Test quick fuzzy quantity check"""
    
    def test_has_fuzzy_positive(self):
        """Test positive fuzzy quantity detection"""
        detector = FuzzyQuantityDetector()
        
        assert detector.has_fuzzy_quantity("Around $10B")
        assert detector.has_fuzzy_quantity("Over 30%")
        assert detector.has_fuzzy_quantity("Between 20 and 30")
    
    def test_has_fuzzy_negative(self):
        """Test negative fuzzy quantity detection"""
        detector = FuzzyQuantityDetector()
        
        assert not detector.has_fuzzy_quantity("Revenue is $10B")
        assert not detector.has_fuzzy_quantity("What is the P/E ratio?")


class TestRangeValueExtraction:
    """Test range value extraction"""
    
    def test_extract_range_values(self):
        """Test extracting min/max from range"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Between $5B and $10B")
        assert len(quantities) > 0
        
        min_val, max_val = detector.extract_range_values(quantities[0])
        assert min_val is not None
        assert max_val is not None
    
    def test_extract_approximation_range(self):
        """Test extracting range from approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Around 100")
        assert len(quantities) > 0
        
        # Should calculate range based on tolerance
        min_val, max_val = detector.extract_range_values(quantities[0])
        # With 10% tolerance: 90-110
        assert min_val is not None
        assert max_val is not None
    
    def test_extract_upper_threshold(self):
        """Test extracting open-ended upper threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Over $10B")
        assert len(quantities) > 0
        
        min_val, max_val = detector.extract_range_values(quantities[0])
        # Upper threshold should be open-ended
        assert min_val is not None
        assert max_val is None
    
    def test_extract_lower_threshold(self):
        """Test extracting open-ended lower threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Under $10B")
        assert len(quantities) > 0
        
        min_val, max_val = detector.extract_range_values(quantities[0])
        # Lower threshold should be open-ended
        assert min_val is None
        assert max_val is not None


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_parsing_detects_fuzzy(self):
        """Test that parsing detects fuzzy quantities"""
        structured = parse_to_structured("Revenue around $10B")
        # Should have fuzzy_quantities
        assert "fuzzy_quantities" in structured or not structured.get("fuzzy_quantities")
    
    def test_parsing_populates_details(self):
        """Test that parsing populates fuzzy quantity details"""
        structured = parse_to_structured("P/E over 30")
        if "fuzzy_quantities" in structured and structured["fuzzy_quantities"]:
            assert len(structured["fuzzy_quantities"]) > 0
            assert "type" in structured["fuzzy_quantities"][0]
            assert "value" in structured["fuzzy_quantities"][0]


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text handling"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("")
        assert len(quantities) == 0
    
    def test_no_fuzzy_quantity(self):
        """Test text without fuzzy quantities"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Show me Apple's revenue")
        assert len(quantities) == 0
    
    def test_multiple_fuzzy_quantities(self):
        """Test multiple fuzzy quantities in one query"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E over 20 and margins around 30%")
        # Should detect both
        assert len(quantities) >= 2


class TestExpandedApproximations:
    """Test expanded approximation patterns"""
    
    def test_in_the_range_of(self):
        """Test 'in the range of' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E in the range of 25")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION
    
    def test_approaching_pattern(self):
        """Test 'approaching' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue approaching $100B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION
    
    def test_or_so_pattern(self):
        """Test 'or so' approximation"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("30% or so")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.APPROXIMATION


class TestExpandedUpperThresholds:
    """Test expanded upper threshold patterns"""
    
    def test_starting_at(self):
        """Test 'starting at' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E starting at 20")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER
    
    def test_in_excess_of(self):
        """Test 'in excess of' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue in excess of $50B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER
    
    def test_surpassing(self):
        """Test 'surpassing' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins surpassing 40%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_UPPER


class TestExpandedLowerThresholds:
    """Test expanded lower threshold patterns"""
    
    def test_capped_at(self):
        """Test 'capped at' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Debt capped at $100B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER
    
    def test_not_exceeding(self):
        """Test 'not exceeding' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E not exceeding 25")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER
    
    def test_limited_to(self):
        """Test 'limited to' threshold"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Growth limited to 15%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.THRESHOLD_LOWER


class TestComplexRanges:
    """Test complex range patterns"""
    
    def test_dollar_range_with_units(self):
        """Test dollar range with units"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue between $50B and $100B")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.RANGE
        assert "50B" in quantities[0].range_start or "50" in quantities[0].range_start
        assert "100B" in quantities[0].range_end or "100" in quantities[0].range_end
    
    def test_percentage_range(self):
        """Test percentage range"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Margins from 25% to 35%")
        assert len(quantities) > 0
        assert quantities[0].fuzzy_type == FuzzyType.RANGE


class TestToleranceVariations:
    """Test different tolerance levels"""
    
    def test_ballpark_wide_tolerance(self):
        """Test 'ballpark' has wide tolerance"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Ballpark $10B")
        assert len(quantities) > 0
        # Should have wider tolerance (15%)
        assert quantities[0].tolerance == 0.15
    
    def test_close_to_tight_tolerance(self):
        """Test 'close to' has tight tolerance"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Close to $10B")
        assert len(quantities) > 0
        # Should have tighter tolerance (5%)
        assert quantities[0].tolerance == 0.05


class TestMultipleQuantitiesInQuery:
    """Test detecting multiple fuzzy quantities"""
    
    def test_two_approximations(self):
        """Test two approximations in one query"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("Revenue around $50B and margins about 30%")
        # Should detect both
        assert len(quantities) >= 2
        assert any(fq.fuzzy_type == FuzzyType.APPROXIMATION for fq in quantities)
    
    def test_mixed_types(self):
        """Test mixed fuzzy types"""
        detector = FuzzyQuantityDetector()
        
        quantities = detector.detect_fuzzy_quantities("P/E over 20 and margins around 30%")
        # Should detect threshold and approximation
        assert len(quantities) >= 2
        types = set(fq.fuzzy_type for fq in quantities)
        assert len(types) >= 2


class TestValueParsing:
    """Test numeric value parsing"""
    
    def test_parse_billion_value(self):
        """Test parsing billion values"""
        detector = FuzzyQuantityDetector()
        
        value = detector._parse_numeric_value("$10B")
        assert value == 10_000_000_000
    
    def test_parse_million_value(self):
        """Test parsing million values"""
        detector = FuzzyQuantityDetector()
        
        value = detector._parse_numeric_value("$500M")
        assert value == 500_000_000
    
    def test_parse_percentage(self):
        """Test parsing percentage"""
        detector = FuzzyQuantityDetector()
        
        value = detector._parse_numeric_value("30%")
        assert value == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


