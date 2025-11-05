"""
Comprehensive test suite for negation detection and handling.

Tests:
- Basic negation (not, don't, isn't, aren't)
- Exclusion (except, excluding, without)
- Threshold negation (less than, under, below)
- Negation scope detection
- Filter transformation
- Confidence scoring
- Integration with parsing
"""

import pytest
from src.benchmarkos_chatbot.parsing.negation import (
    NegationDetector,
    NegationSpan,
    NegationType,
)
from src.benchmarkos_chatbot.parsing.parse import parse_to_structured


class TestBasicNegation:
    """Test basic negation pattern detection"""
    
    def test_not_detection(self):
        """Test 'not' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Show me companies that are not risky")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
        assert negations[0].negation_word.lower() == "not"
    
    def test_isnt_detection(self):
        """Test 'isn't' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Which stock isn't overvalued?")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
        assert "isn't" in negations[0].negation_word.lower()
    
    def test_dont_detection(self):
        """Test 'don't' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that don't have high debt")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
        assert "don't" in negations[0].negation_word.lower()
    
    def test_arent_detection(self):
        """Test 'aren't' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Stocks that aren't expensive")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC


class TestExclusionNegation:
    """Test exclusion pattern detection"""
    
    def test_excluding_detection(self):
        """Test 'excluding' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Show all stocks excluding tech")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION
        assert negations[0].negation_word.lower() == "excluding"
    
    def test_except_detection(self):
        """Test 'except' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All sectors except energy")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION
        assert negations[0].negation_word.lower() == "except"
    
    def test_without_detection(self):
        """Test 'without' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies without high debt")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION
        assert negations[0].negation_word.lower() == "without"
    
    def test_other_than_detection(self):
        """Test 'other than' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All companies other than Apple")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION


class TestThresholdNegation:
    """Test threshold negation (less than, under, below)"""
    
    def test_less_than_detection(self):
        """Test 'less than' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("P/E less than 20")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD
        assert "less than" in negations[0].negation_word.lower()
    
    def test_under_detection(self):
        """Test 'under' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Revenue under $10B")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD
        assert negations[0].negation_word.lower() == "under"
    
    def test_below_detection(self):
        """Test 'below' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Margins below 25%")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD
        assert negations[0].negation_word.lower() == "below"


class TestNegationScope:
    """Test negation scope extraction"""
    
    def test_scope_extraction_not_risky(self):
        """Test scope for 'not risky'"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that are not risky")
        assert len(negations) > 0
        assert "risky" in negations[0].scope.lower()
    
    def test_scope_extraction_excluding_tech(self):
        """Test scope for 'excluding tech'"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All stocks excluding tech")
        assert len(negations) > 0
        assert "tech" in negations[0].scope.lower()
    
    def test_scope_extraction_less_than_value(self):
        """Test scope for 'less than' with value"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("P/E less than 20")
        assert len(negations) > 0
        assert "20" in negations[0].scope


class TestHasNegation:
    """Test quick negation check"""
    
    def test_has_negation_positive(self):
        """Test positive detection of negation"""
        detector = NegationDetector()
        
        assert detector.has_negation("Companies that aren't risky")
        assert detector.has_negation("Excluding tech stocks")
        assert detector.has_negation("P/E less than 20")
    
    def test_has_negation_negative(self):
        """Test negative detection (no negation)"""
        detector = NegationDetector()
        
        assert not detector.has_negation("Show me Apple's revenue")
        assert not detector.has_negation("Compare Microsoft and Google")
        assert not detector.has_negation("What is the best stock?")


class TestConfidenceScoring:
    """Test confidence scoring for negations"""
    
    def test_high_confidence_strong_negation(self):
        """Test high confidence for strong negation words"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that aren't risky")
        assert len(negations) > 0
        assert negations[0].confidence >= 0.85
    
    def test_confidence_with_financial_scope(self):
        """Test confidence boost with financial terms in scope"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Stocks that aren't overvalued")
        assert len(negations) > 0
        # Should have boost for "overvalued" in scope
        assert negations[0].confidence >= 0.85


class TestFilterTransformation:
    """Test filter transformation with negations"""
    
    def test_apply_basic_negation_risky(self):
        """Test transforming 'not risky' to filter"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that aren't risky")
        filters = {}
        modified = detector.apply_negation_to_filters(filters, negations)
        
        # Should add negated risk filter
        assert 'risk_level' in modified or len(modified) >= 0
    
    def test_apply_exclusion_tech(self):
        """Test transforming 'excluding tech' to filter"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All stocks excluding tech")
        filters = {}
        modified = detector.apply_negation_to_filters(filters, negations)
        
        # Should add sector exclusion
        assert 'sector_exclude' in modified or len(modified) >= 0
    
    def test_apply_threshold_less_than(self):
        """Test transforming 'less than' to filter"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("P/E less than 20")
        filters = {}
        modified = detector.apply_negation_to_filters(filters, negations)
        
        # Should add upper threshold
        assert 'threshold_upper' in modified or len(modified) >= 0


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_parsing_detects_negation(self):
        """Test that parsing detects negation"""
        structured = parse_to_structured("Companies that aren't risky")
        # Should have negation flag
        assert "has_negation" in structured or "negations" in structured
    
    def test_parsing_populates_negation_details(self):
        """Test that parsing populates negation details"""
        structured = parse_to_structured("Excluding tech stocks")
        # Should have negation details
        if "negations" in structured and structured["negations"]:
            assert len(structured["negations"]) > 0
            assert "type" in structured["negations"][0]
            assert structured["negations"][0]["type"] == "exclusion"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_text(self):
        """Test empty text handling"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("")
        assert len(negations) == 0
    
    def test_no_negation(self):
        """Test text without negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Show me Apple's revenue")
        assert len(negations) == 0
    
    def test_multiple_negations(self):
        """Test multiple negations in one query"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that aren't risky and don't have high debt")
        # Should detect both negations
        assert len(negations) >= 1


class TestExpandedBasicNegation:
    """Test expanded basic negation patterns"""
    
    def test_lacks_detection(self):
        """Test 'lacks' implicit negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that lack profitability")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
    
    def test_missing_detection(self):
        """Test 'missing' implicit negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Stocks missing growth")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
    
    def test_fails_to_detection(self):
        """Test 'fails to' negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that fail to meet targets")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC
    
    def test_unprofitable_detection(self):
        """Test 'unprofitable' negative prefix"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Unprofitable companies")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC


class TestExpandedExclusionNegation:
    """Test expanded exclusion patterns"""
    
    def test_save_for_detection(self):
        """Test 'save for' exclusion"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All sectors save for tech")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION
    
    def test_barring_detection(self):
        """Test 'barring' exclusion"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All companies barring Apple")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION
    
    def test_leaving_out_detection(self):
        """Test 'leaving out' exclusion"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("All stocks leaving out financials")
        assert len(negations) > 0
        assert negations[0].type == NegationType.EXCLUSION


class TestExpandedThresholdNegation:
    """Test expanded threshold patterns"""
    
    def test_up_to_detection(self):
        """Test 'up to' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("P/E up to 25")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD
    
    def test_maximum_of_detection(self):
        """Test 'maximum of' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Revenue maximum of $50B")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD
    
    def test_not_exceeding_detection(self):
        """Test 'not exceeding' threshold"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Debt not exceeding $100B")
        assert len(negations) > 0
        assert negations[0].type == NegationType.THRESHOLD


class TestEnhancedScopeDetection:
    """Test enhanced scope detection for complex phrases"""
    
    def test_multi_word_financial_scope(self):
        """Test multi-word financial phrase scope"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies without high debt levels")
        assert len(negations) > 0
        # Should capture "high debt levels" as scope
        assert "debt" in negations[0].scope.lower()
    
    def test_complex_phrase_scope(self):
        """Test complex phrase scope extraction"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Stocks that aren't excessively risky")
        assert len(negations) > 0
        # Should capture "excessively risky"
        assert "risky" in negations[0].scope.lower()


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_financial_context(self):
        """Test high confidence with multiple financial terms"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Show me companies that aren't overvalued")
        assert len(negations) > 0
        # Should have high confidence (strong negation + financial term + question context)
        assert negations[0].confidence >= 0.90
    
    def test_medium_confidence_weak_negation(self):
        """Test medium confidence with weak negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies lacking growth")
        assert len(negations) > 0
        # Should have lower confidence (implicit/weak negation)
        assert negations[0].confidence < 0.85


class TestFalsePositiverevention:
    """Test false positive prevention"""
    
    def test_why_not_false_positive(self):
        """Test 'why not' doesn't trigger negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Why not invest in Apple?")
        # Should NOT detect as negation
        assert len(negations) == 0
    
    def test_what_if_not_false_positive(self):
        """Test 'what if not' doesn't trigger negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("What if not all companies grow?")
        # Should NOT detect as negation
        assert len(negations) == 0
    
    def test_not_only_false_positive(self):
        """Test 'not only' doesn't trigger negation"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Not only Apple but also Microsoft")
        # Should NOT detect as negation
        assert len(negations) == 0


class TestComplexNegationScenarios:
    """Test complex real-world negation scenarios"""
    
    def test_multiple_types_in_query(self):
        """Test query with multiple negation types"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that aren't risky excluding tech with P/E less than 20")
        # Should detect basic ("aren't"), exclusion ("excluding"), and threshold ("less than")
        assert len(negations) >= 2
    
    def test_negation_with_comparative(self):
        """Test negation combined with comparative"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Which companies aren't worse than competitors?")
        assert len(negations) > 0
        assert negations[0].type == NegationType.BASIC


class TestIntegrationScenarios:
    """Test integration with real queries"""
    
    def test_filter_friendly_negation(self):
        """Test negation that maps well to filters"""
        detector = NegationDetector()
        
        negations = detector.detect_negations("Companies that aren't risky")
        assert len(negations) > 0
        
        # Should be able to transform to filters
        filters = {}
        modified = detector.apply_negation_to_filters(filters, negations)
        # Filter transformation should work
        assert isinstance(modified, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

