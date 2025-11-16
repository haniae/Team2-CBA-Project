"""
Tests for conditional statement detection (Phase 3.3).
"""

import pytest
from src.finanlyzeos_chatbot.parsing.conditionals import (
    ConditionalDetector,
    ConditionalType,
    ComparisonOperator,
    ConditionalStatement,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestIfThenStatements:
    """Test IF-THEN conditional statements"""
    
    def test_basic_if_then(self):
        """Test basic if-then statement"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue > $10B then show risk")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.IF_THEN
        assert "revenue > $10B" in conditionals[0].condition
        assert "show risk" in conditionals[0].action
    
    def test_if_then_with_operator(self):
        """Test if-then with explicit operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if P/E < 20 then buy")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_THAN
    
    def test_if_then_with_comma(self):
        """Test if-then with comma separator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if debt > $50B, show warning")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.IF_THEN


class TestWhenThenStatements:
    """Test WHEN-THEN conditional statements"""
    
    def test_basic_when_then(self):
        """Test basic when-then statement"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("when profit margin > 20% then analyze")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHEN_THEN
    
    def test_when_then_equals(self):
        """Test when-then with equals operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("when sector = technology then display")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.EQUALS


class TestUnlessStatements:
    """Test UNLESS conditional statements"""
    
    def test_basic_unless(self):
        """Test basic unless statement"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("unless revenue < $1B, show details")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.UNLESS
    
    def test_unless_with_then(self):
        """Test unless with 'then' keyword"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("unless debt > $100B then proceed")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.UNLESS


class TestWheneverStatements:
    """Test WHENEVER conditional statements"""
    
    def test_basic_whenever(self):
        """Test basic whenever statement"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("whenever EPS > $5, alert me")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHENEVER


class TestComparisonOperators:
    """Test comparison operator detection"""
    
    def test_greater_than_symbol(self):
        """Test > operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue > $10B then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_less_than_symbol(self):
        """Test < operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if P/E < 15 then buy")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_THAN
    
    def test_greater_equal(self):
        """Test >= operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin >= 25% then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_EQUAL
    
    def test_less_equal(self):
        """Test <= operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if debt <= $50B then analyze")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_EQUAL
    
    def test_not_equal(self):
        """Test != operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if sector != healthcare then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.NOT_EQUAL
    
    def test_equals_symbol(self):
        """Test = operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if rating = AAA then display")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.EQUALS


class TestNaturalLanguageOperators:
    """Test natural language comparison operators"""
    
    def test_greater_than_text(self):
        """Test 'greater than' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue greater than $10B then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_less_than_text(self):
        """Test 'less than' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if P/E less than 20 then analyze")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_THAN
    
    def test_above_operator(self):
        """Test 'above' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin above 30% then display")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_below_operator(self):
        """Test 'below' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if debt below $25B then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_THAN
    
    def test_exceeds_operator(self):
        """Test 'exceeds' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue exceeds $100B then alert")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_at_least_operator(self):
        """Test 'at least' as operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if EPS at least $3 then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_EQUAL


class TestConfidenceScoring:
    """Test confidence scoring for conditionals"""
    
    def test_high_confidence_with_symbol(self):
        """Test high confidence with symbol operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue > $10B then show risk")
        assert len(conditionals) > 0
        # Should have high confidence (explicit operator + financial term + action verb)
        assert conditionals[0].confidence >= 0.95
    
    def test_good_confidence_basic(self):
        """Test good confidence for basic conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin higher then display")
        assert len(conditionals) > 0
        # Should have at least base confidence
        assert conditionals[0].confidence >= 0.85


class TestHasConditional:
    """Test quick conditional check"""
    
    def test_has_conditional_positive(self):
        """Test has_conditional returns True for conditional"""
        detector = ConditionalDetector()
        
        assert detector.has_conditional("if revenue > $10B then show risk") is True
    
    def test_has_conditional_negative(self):
        """Test has_conditional returns False for non-conditional"""
        detector = ConditionalDetector()
        
        assert detector.has_conditional("show me revenue for Apple") is False


class TestIntegrationWithParsing:
    """Test integration with parsing pipeline"""
    
    def test_parsing_detects_conditional(self):
        """Test that parsing detects conditionals"""
        result = parse_to_structured("if revenue > $10B then show risk")
        
        assert "conditionals" in result
        assert len(result["conditionals"]) > 0
    
    def test_parsing_populates_details(self):
        """Test that parsing populates conditional details"""
        result = parse_to_structured("if P/E < 20 then buy")
        
        assert "conditionals" in result
        cond = result["conditionals"][0]
        assert cond["type"] == "if_then"
        assert "P/E" in cond["condition"]
        assert "buy" in cond["action"]
        assert cond["operator"] == "<"


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("")
        assert len(conditionals) == 0
    
    def test_no_conditional(self):
        """Test text without conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("show me revenue for Apple")
        assert len(conditionals) == 0
    
    def test_multiple_conditionals(self):
        """Test multiple conditionals in one query"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals(
            "if revenue > $10B then show risk, and if debt < $5B then buy"
        )
        # Should detect at least one (possibly two depending on parsing)
        assert len(conditionals) >= 1


class TestExpandedIfThenPatterns:
    """Test expanded IF-THEN patterns"""
    
    def test_provided_that_pattern(self):
        """Test 'provided that' as if-then"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("provided that revenue > $5B, show details")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.IF_THEN
    
    def test_assuming_pattern(self):
        """Test 'assuming' as if-then"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("assuming margin > 20%, display risk")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.IF_THEN


class TestExpandedWhenThenPatterns:
    """Test expanded WHEN-THEN patterns"""
    
    def test_once_pattern(self):
        """Test 'once' as when-then"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("once EPS > $3, buy")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHEN_THEN
    
    def test_as_soon_as_pattern(self):
        """Test 'as soon as' as when-then"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("as soon as debt < $10B, notify me")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHEN_THEN


class TestExpandedUnlessPatterns:
    """Test expanded UNLESS patterns"""
    
    def test_except_if_pattern(self):
        """Test 'except if' as unless"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("except if revenue < $1B, show report")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.UNLESS


class TestExpandedWheneverPatterns:
    """Test expanded WHENEVER patterns"""
    
    def test_each_time_pattern(self):
        """Test 'each time' as whenever"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("each time P/E > 25, alert")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHENEVER
    
    def test_every_time_pattern(self):
        """Test 'every time' as whenever"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("every time margin drops, warn")
        assert len(conditionals) > 0
        assert conditionals[0].conditional_type == ConditionalType.WHENEVER


class TestExpandedOperatorPatterns:
    """Test expanded operator patterns"""
    
    def test_surpasses_operator(self):
        """Test 'surpasses' as greater than"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue surpasses $100B then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_beats_operator(self):
        """Test 'beats' as greater than"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin beats 30% then buy")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_outperforms_operator(self):
        """Test 'outperforms' as greater than"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if growth outperforms 15% then alert")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_THAN
    
    def test_no_less_than_operator(self):
        """Test 'no less than' as greater equal"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if EPS no less than $5 then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_EQUAL
    
    def test_minimum_of_operator(self):
        """Test 'minimum of' as greater equal"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue minimum of $10B then analyze")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.GREATER_EQUAL
    
    def test_maximum_of_operator(self):
        """Test 'maximum of' as less equal"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if debt maximum of $50B then buy")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_EQUAL
    
    def test_no_more_than_operator(self):
        """Test 'no more than' as less equal"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if P/E no more than 20 then display")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_EQUAL
    
    def test_short_of_operator(self):
        """Test 'short of' as less than"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin short of 25% then warn")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.LESS_THAN
    
    def test_differs_from_operator(self):
        """Test 'differs from' as not equal"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if sector differs from tech then show")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.NOT_EQUAL
    
    def test_matches_operator(self):
        """Test 'matches' as equals"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if rating matches AAA then buy")
        assert len(conditionals) > 0
        assert conditionals[0].operator == ComparisonOperator.EQUALS


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_what_if_not_conditional(self):
        """Test 'what if' doesn't trigger conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("What if revenue declines?")
        # Should NOT detect as conditional (hypothetical question)
        assert len(conditionals) == 0
    
    def test_what_happens_if_not_conditional(self):
        """Test 'what happens if' doesn't trigger conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("What happens if the market crashes?")
        # Should NOT detect as conditional (question about outcome)
        assert len(conditionals) == 0
    
    def test_if_only_not_conditional(self):
        """Test 'if only' doesn't trigger conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("If only they had better margins")
        # Should NOT detect as conditional (wishful thinking)
        assert len(conditionals) == 0
    
    def test_even_if_not_conditional(self):
        """Test 'even if' doesn't trigger conditional"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("Show results even if incomplete")
        # Should NOT detect as conditional (not a true condition)
        assert len(conditionals) == 0


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_with_symbol_and_context(self):
        """Test high confidence with symbol, financial term, and action"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if revenue > $10B then show risk analysis")
        assert len(conditionals) > 0
        # Should have very high confidence (symbol + revenue + numeric + show)
        assert conditionals[0].confidence >= 0.98
    
    def test_confidence_with_natural_operator(self):
        """Test confidence with natural language operator"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if profit exceeds $5B then alert")
        assert len(conditionals) > 0
        # Should have high confidence (natural operator + profit + numeric + alert)
        assert conditionals[0].confidence >= 0.94
    
    def test_confidence_with_numeric_threshold(self):
        """Test confidence boost for numeric values"""
        detector = ConditionalDetector()
        
        conditionals = detector.detect_conditionals("if margin > 25% then buy")
        assert len(conditionals) > 0
        # Should have confidence boost for numeric threshold
        assert conditionals[0].confidence >= 0.92


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

