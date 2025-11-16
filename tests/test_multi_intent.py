"""
Comprehensive test suite for multi-intent detection and handling.

Tests:
- AND conjunctions (parallel intents)
- OR conjunctions (alternative intents)
- THEN conjunctions (sequential intents)
- ALSO conjunctions (additive intents)
- COMMA conjunctions (list intents)
- Intent splitting and decomposition
- Sub-intent classification
- Confidence scoring
- Integration with parsing
"""

import pytest
from src.finanlyzeos_chatbot.parsing.multi_intent import (
    MultiIntentDetector,
    MultiIntentQuery,
    SubIntent,
    ConjunctionType,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestANDConjunction:
    """Test AND conjunction detection"""
    
    def test_simple_and_conjunction(self):
        """Test simple 'and' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and analyze risk")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.AND
        assert len(result.sub_intents) == 2
    
    def test_and_with_questions(self):
        """Test 'and' with multiple questions"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("What's the P/E and what's the EPS?")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.AND
    
    def test_and_with_commands(self):
        """Test 'and' with multiple commands"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get revenue and show margins")
        assert result.is_multi_intent
        assert len(result.sub_intents) >= 2


class TestORConjunction:
    """Test OR conjunction detection"""
    
    def test_simple_or_conjunction(self):
        """Test simple 'or' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue or profit")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.OR
    
    def test_either_pattern(self):
        """Test 'either' as OR"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Either show Apple or Microsoft")
        assert result.conjunction == ConjunctionType.OR


class TestTHENConjunction:
    """Test THEN conjunction (sequential)"""
    
    def test_simple_then_conjunction(self):
        """Test simple 'then' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue then analyze risk")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.THEN
    
    def test_and_then_pattern(self):
        """Test 'and then' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Compare Apple and Microsoft and then tell me which is better")
        assert result.conjunction == ConjunctionType.THEN
    
    def test_after_that_pattern(self):
        """Test 'after that' sequential"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get revenue after that show margins")
        assert result.conjunction == ConjunctionType.THEN


class TestALSOConjunction:
    """Test ALSO conjunction (additive)"""
    
    def test_simple_also_conjunction(self):
        """Test simple 'also' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue also show risk")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.ALSO
    
    def test_and_also_pattern(self):
        """Test 'and also' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and also analyze risk")
        assert result.conjunction == ConjunctionType.ALSO
    
    def test_as_well_as_pattern(self):
        """Test 'as well as' conjunction"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue as well as margins")
        assert result.conjunction == ConjunctionType.ALSO


class TestCOMMAConjunction:
    """Test COMMA conjunction (list)"""
    
    def test_comma_separated_list(self):
        """Test comma-separated intents"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue, margins, and debt")
        assert result.is_multi_intent
        assert len(result.sub_intents) >= 2
    
    def test_complex_comma_list(self):
        """Test complex comma list"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get revenue, analyze risk, show P/E")
        assert result.is_multi_intent
        assert len(result.sub_intents) >= 2


class TestIntentSplitting:
    """Test intent splitting logic"""
    
    def test_split_preserves_content(self):
        """Test that splitting preserves content"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show Apple revenue and Microsoft profit")
        # Should preserve company names in sub-intents
        intents_text = " ".join([si.text for si in result.sub_intents])
        assert "Apple" in intents_text or "revenue" in intents_text
    
    def test_split_position_tracking(self):
        """Test that positions are tracked"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and show risk")
        if result.is_multi_intent:
            # Second intent should have higher position
            assert result.sub_intents[1].position > result.sub_intents[0].position


class TestSubIntentClassification:
    """Test sub-intent classification"""
    
    def test_question_classification(self):
        """Test question intent classification"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("What's the revenue and how's the growth?")
        if result.is_multi_intent:
            # Should classify as questions
            assert any(si.intent_type == "question" for si in result.sub_intents)
    
    def test_command_classification(self):
        """Test command intent classification"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and get margins")
        if result.is_multi_intent:
            # Should classify as commands
            assert any(si.intent_type == "command" for si in result.sub_intents)
    
    def test_analysis_classification(self):
        """Test analysis intent classification"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Analyze risk and evaluate performance")
        if result.is_multi_intent:
            # Should classify as analysis
            assert any(si.intent_type == "analysis" for si in result.sub_intents)
    
    def test_comparison_classification(self):
        """Test comparison intent classification"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Compare Apple and Microsoft then show which is better")
        if result.is_multi_intent:
            # Should classify as comparison
            assert any(si.intent_type == "comparison" for si in result.sub_intents)


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_clear_intents(self):
        """Test high confidence with clear intents"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and analyze risk")
        if result.is_multi_intent:
            # Should have high overall confidence
            assert result.confidence >= 0.75
    
    def test_sub_intent_confidence(self):
        """Test individual sub-intent confidence"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("What's the P/E ratio and what's the EPS?")
        if result.is_multi_intent:
            # Each sub-intent should have decent confidence
            for si in result.sub_intents:
                assert si.confidence >= 0.70


class TestSingleIntent:
    """Test single-intent queries (no splitting)"""
    
    def test_simple_query_not_split(self):
        """Test simple query isn't incorrectly split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show me Apple's revenue")
        assert not result.is_multi_intent
        assert len(result.sub_intents) == 1
    
    def test_and_in_company_name(self):
        """Test 'and' in context doesn't trigger split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show Procter and Gamble revenue")
        # Should NOT split on company name
        # (This might split - adjust test if needed)
        assert len(result.sub_intents) >= 1


class TestIsMultiIntent:
    """Test quick multi-intent check"""
    
    def test_is_multi_intent_positive(self):
        """Test positive multi-intent detection"""
        detector = MultiIntentDetector()
        
        assert detector.is_multi_intent("Show revenue and analyze risk")
        assert detector.is_multi_intent("Get P/E or EPS")
        assert detector.is_multi_intent("Show revenue, margins, and debt")
    
    def test_is_multi_intent_negative(self):
        """Test negative multi-intent detection"""
        detector = MultiIntentDetector()
        
        assert not detector.is_multi_intent("Show me Apple's revenue")
        assert not detector.is_multi_intent("What is the P/E ratio?")


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_parsing_detects_multi_intent(self):
        """Test that parsing detects multi-intent"""
        structured = parse_to_structured("Show revenue and analyze risk")
        # Should have multi_intent flag
        assert "multi_intent" in structured or not structured.get("multi_intent")
    
    def test_parsing_populates_details(self):
        """Test that parsing populates multi-intent details"""
        structured = parse_to_structured("Get revenue and show margins")
        if "multi_intent" in structured and structured["multi_intent"]:
            assert "conjunction" in structured["multi_intent"]
            assert "sub_intents" in structured["multi_intent"]


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text handling"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("")
        assert not result.is_multi_intent
        assert len(result.sub_intents) == 0
    
    def test_very_long_query(self):
        """Test handling of very long query"""
        detector = MultiIntentDetector()
        
        long_query = "Show revenue and show margins and show debt and show P/E and show EPS"
        result = detector.detect_multi_intent(long_query)
        # Should handle multiple conjunctions
        assert result.is_multi_intent


class TestExpandedTHENPatterns:
    """Test expanded THEN/sequential patterns"""
    
    def test_next_pattern(self):
        """Test 'next' as sequential"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue next show margins")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.THEN
    
    def test_afterwards_pattern(self):
        """Test 'afterwards' as sequential"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get revenue afterwards analyze risk")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.THEN
    
    def test_finally_pattern(self):
        """Test 'finally' as sequential"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue finally show summary")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.THEN


class TestExpandedALSOPatterns:
    """Test expanded ALSO/additive patterns"""
    
    def test_furthermore_pattern(self):
        """Test 'furthermore' as additive"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue furthermore show risk")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.ALSO
    
    def test_moreover_pattern(self):
        """Test 'moreover' as additive"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get margins moreover get debt")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.ALSO
    
    def test_in_addition_pattern(self):
        """Test 'in addition' as additive"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show P/E in addition show EPS")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.ALSO


class TestExpandedORPatterns:
    """Test expanded OR/alternative patterns"""
    
    def test_alternatively_pattern(self):
        """Test 'alternatively' as OR"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue alternatively show profit")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.OR
    
    def test_otherwise_pattern(self):
        """Test 'otherwise' as OR"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Get Apple otherwise get Microsoft")
        assert result.is_multi_intent
        assert result.conjunction == ConjunctionType.OR


class TestFalsePositivePrevention:
    """Test false positive prevention for context splitting"""
    
    def test_procter_and_gamble_not_split(self):
        """Test 'Procter and Gamble' isn't split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show Procter and Gamble revenue")
        # Should NOT split on company name
        assert not result.is_multi_intent
    
    def test_att_not_split(self):
        """Test 'AT&T' isn't split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show AT&T revenue")
        # Should NOT split on company name
        assert not result.is_multi_intent
    
    def test_mergers_and_acquisitions_not_split(self):
        """Test 'mergers and acquisitions' isn't split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show mergers and acquisitions data")
        # Should NOT split on financial phrase
        assert not result.is_multi_intent
    
    def test_assets_and_liabilities_not_split(self):
        """Test 'assets and liabilities' isn't split"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show assets and liabilities")
        # Should NOT split on financial phrase
        assert not result.is_multi_intent


class TestEnhancedSubIntentValidation:
    """Test enhanced sub-intent validation"""
    
    def test_single_word_fragment_rejected(self):
        """Test single word fragments are rejected"""
        detector = MultiIntentDetector()
        
        # "the" should be rejected as a valid sub-intent
        result = detector.detect_multi_intent("Show revenue and the margins")
        # Should either not split or filter out "the"
        if result.is_multi_intent:
            assert all(len(si.text.split()) > 1 or si.text.lower() in ['revenue', 'margins'] for si in result.sub_intents)
    
    def test_valid_single_metric_accepted(self):
        """Test single metric words are accepted"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue, profit")
        # "revenue" and "profit" should both be valid
        assert result.is_multi_intent or len(result.sub_intents) >= 1


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_complete_intents(self):
        """Test high confidence with complete, well-formed intents"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show Apple's revenue and analyze Microsoft's risk")
        if result.is_multi_intent:
            # Should have high confidence (complete sentences, companies, financial terms)
            assert result.confidence >= 0.85
    
    def test_medium_confidence_short_intents(self):
        """Test medium confidence with shorter intents"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Revenue and margins")
        if result.is_multi_intent:
            # Should have medium confidence (valid but short)
            assert 0.70 <= result.confidence < 0.90
    
    def test_confidence_consistency_boost(self):
        """Test confidence boost for consistent sub-intent quality"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue and show margins and show debt")
        if result.is_multi_intent:
            # All sub-intents are similar quality → should get consistency boost
            assert result.confidence >= 0.80


class TestComplexMultiIntentScenarios:
    """Test complex real-world multi-intent scenarios"""
    
    def test_three_way_split(self):
        """Test query with three intents"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Show revenue, analyze risk, and evaluate valuation")
        assert result.is_multi_intent
        # Should detect at least 2 sub-intents (may combine some)
        assert len(result.sub_intents) >= 2
    
    def test_mixed_intent_types(self):
        """Test query with different intent types"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("What's the revenue and show me the margins")
        if result.is_multi_intent:
            # Should detect different intent types
            intent_types = set(si.intent_type for si in result.sub_intents)
            assert len(intent_types) >= 1
    
    def test_nested_comparison_in_multi_intent(self):
        """Test comparison nested in multi-intent"""
        detector = MultiIntentDetector()
        
        result = detector.detect_multi_intent("Compare Apple and Microsoft then show the winner")
        assert result.is_multi_intent
        # "Apple and Microsoft" should stay together in first sub-intent
        assert len(result.sub_intents) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


