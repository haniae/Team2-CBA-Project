"""
Tests for question chaining detection (Phase 4.3).
"""

import pytest
from src.finanlyzeos_chatbot.parsing.question_chaining import (
    QuestionChainDetector,
    ChainType,
    QuestionChain,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestSequentialChains:
    """Test sequential question chain detection"""
    
    def test_and_what_about(self):
        """Test 'and what about' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("And what about Microsoft?")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL
        assert chain.is_followup is True
        assert chain.requires_context is True
    
    def test_then_show(self):
        """Test 'then show' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Then show me Apple")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL
    
    def test_next_tell(self):
        """Test 'next tell' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Next, tell me about revenue")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL
    
    def test_after_that(self):
        """Test 'after that' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("After that, show Google")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL


class TestComparativeChains:
    """Test comparative question chain detection"""
    
    def test_how_does_that_compare(self):
        """Test 'how does that compare' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("How does that compare to Tesla?")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE
        assert chain.requires_context is True
    
    def test_compared_to_that(self):
        """Test 'compared to that' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Compared to that, how is Apple?")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE
    
    def test_versus_the_last(self):
        """Test 'versus the last' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Versus the last quarter")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE


class TestExploratoryChains:
    """Test exploratory question chain detection"""
    
    def test_what_about(self):
        """Test 'what about' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("What about Amazon?")
        assert chain is not None
        assert chain.chain_type == ChainType.EXPLORATORY
        assert chain.is_followup is True
        # Exploratory can be independent
        assert chain.requires_context is False
    
    def test_how_about(self):
        """Test 'how about' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("How about looking at Microsoft?")
        assert chain is not None
        assert chain.chain_type == ChainType.EXPLORATORY


class TestContinuationChains:
    """Test continuation question chain detection"""
    
    def test_also_show(self):
        """Test 'also show' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Also show me Tesla")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION
        assert chain.requires_context is True
    
    def test_additionally(self):
        """Test 'additionally' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Additionally, tell me about Google")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION
    
    def test_in_addition(self):
        """Test 'in addition' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("In addition, show revenue")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION


class TestElaborationChains:
    """Test elaboration question chain detection"""
    
    def test_tell_me_more(self):
        """Test 'tell me more' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Tell me more about that")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION
        assert chain.requires_context is True
    
    def test_explain_that(self):
        """Test 'explain that' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Explain that in more detail")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION
    
    def test_more_details(self):
        """Test 'more details' detection"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Give me more details on this")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_sequential(self):
        """Test high confidence for sequential with explicit signal"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Then show me Apple revenue")
        assert chain is not None
        # Should have high confidence (explicit signal + action)
        assert chain.confidence >= 0.90
    
    def test_high_confidence_comparative(self):
        """Test high confidence for comparative with pronouns"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("How does that compare to Microsoft?")
        assert chain is not None
        # Should have high confidence (comparative + pronoun)
        assert chain.confidence >= 0.90


class TestContextRequirements:
    """Test context requirement detection"""
    
    def test_sequential_requires_context(self):
        """Test sequential chains require context"""
        detector = QuestionChainDetector()
        
        assert detector.requires_previous_context("Then show me Apple") is True
    
    def test_exploratory_no_context_required(self):
        """Test exploratory chains don't require context"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("What about Amazon?")
        assert chain is not None
        assert chain.requires_context is False
    
    def test_comparative_requires_context(self):
        """Test comparative chains require context"""
        detector = QuestionChainDetector()
        
        assert detector.requires_previous_context("How does that compare?") is True


class TestIsChainedQuestion:
    """Test quick chain check"""
    
    def test_is_chained_positive(self):
        """Test is_chained_question returns True for chain"""
        detector = QuestionChainDetector()
        
        assert detector.is_chained_question("And what about Apple?") is True
    
    def test_is_chained_negative(self):
        """Test is_chained_question returns False for no chain"""
        detector = QuestionChainDetector()
        
        assert detector.is_chained_question("Show me revenue") is False


class TestIntegrationWithParsing:
    """Test integration with parsing pipeline"""
    
    def test_parsing_detects_chain(self):
        """Test that parsing detects chains"""
        result = parse_to_structured("And what about Microsoft?")
        
        assert "question_chain" in result
        assert result["question_chain"]["type"] == "sequential"
    
    def test_parsing_populates_details(self):
        """Test that parsing populates chain details"""
        result = parse_to_structured("How does that compare to Apple?")
        
        assert "question_chain" in result
        chain = result["question_chain"]
        assert chain["type"] == "comparative"
        assert chain["is_followup"] is True
        assert chain["requires_context"] is True
        assert chain["confidence"] > 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("")
        assert chain is None
    
    def test_no_chain(self):
        """Test text without chain"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Show me revenue for Apple")
        assert chain is None


class TestExpandedSequentialPatterns:
    """Test expanded sequential chain patterns"""
    
    def test_now_show(self):
        """Test 'now show' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Now show me Google")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL
    
    def test_following_that(self):
        """Test 'following that' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Following that, tell me about Tesla")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL
    
    def test_subsequently(self):
        """Test 'subsequently' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Subsequently, show revenue")
        assert chain is not None
        assert chain.chain_type == ChainType.SEQUENTIAL


class TestExpandedComparativePatterns:
    """Test expanded comparative chain patterns"""
    
    def test_in_comparison_to_that(self):
        """Test 'in comparison to that' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("In comparison to that, how is Apple?")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE
    
    def test_against_the_previous(self):
        """Test 'against the previous' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Against the previous quarter")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE
    
    def test_how_does_it_differ(self):
        """Test 'how does it differ' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("How does it differ from Microsoft?")
        assert chain is not None
        assert chain.chain_type == ChainType.COMPARATIVE


class TestExpandedExploratoryPatterns:
    """Test expanded exploratory chain patterns"""
    
    def test_what_if_we_look(self):
        """Test 'what if we look' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("What if we look at Amazon?")
        assert chain is not None
        assert chain.chain_type == ChainType.EXPLORATORY
    
    def test_maybe_check(self):
        """Test 'maybe check' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Maybe check Tesla's performance")
        assert chain is not None
        assert chain.chain_type == ChainType.EXPLORATORY


class TestExpandedContinuationPatterns:
    """Test expanded continuation chain patterns"""
    
    def test_plus_show(self):
        """Test 'plus show' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Plus, show me Netflix")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION
    
    def test_as_well(self):
        """Test 'as well' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("As well, tell me about Google")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION
    
    def test_on_top_of_that(self):
        """Test 'on top of that' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("On top of that, show revenue")
        assert chain is not None
        assert chain.chain_type == ChainType.CONTINUATION


class TestExpandedElaborationPatterns:
    """Test expanded elaboration chain patterns"""
    
    def test_expand_on(self):
        """Test 'expand on' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Expand on that topic")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION
    
    def test_dive_deeper(self):
        """Test 'dive deeper' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Dive deeper into this")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION
    
    def test_break_down(self):
        """Test 'break down' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Break down that data")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION
    
    def test_can_you_elaborate(self):
        """Test 'can you elaborate' pattern"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Can you elaborate on that?")
        assert chain is not None
        assert chain.chain_type == ChainType.ELABORATION


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_what_is_compare_not_chain(self):
        """Test 'what is compare' doesn't trigger chain"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("What is comparison analysis?")
        # Should NOT detect as chain (question about concept)
        assert chain is None


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_sequential_with_context(self):
        """Test high confidence for sequential with multiple context"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Then show me Apple revenue performance")
        assert chain is not None
        # Should have very high confidence (then + show + revenue + performance)
        assert chain.confidence >= 0.95
    
    def test_high_confidence_comparative_with_pronouns(self):
        """Test high confidence for comparative with multiple pronouns"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("How does that compare to the previous results?")
        assert chain is not None
        # Should have very high confidence (compare + that + previous)
        assert chain.confidence >= 0.95
    
    def test_confidence_with_financial_context(self):
        """Test confidence boost for financial context"""
        detector = QuestionChainDetector()
        
        chain = detector.detect_chain("Also show revenue and profit")
        assert chain is not None
        # Should have confidence boost for revenue/profit
        assert chain.confidence >= 0.92


class TestComplexChainScenarios:
    """Test complex chain scenarios"""
    
    def test_multiple_signals_in_query(self):
        """Test query with multiple potential chain signals"""
        detector = QuestionChainDetector()
        
        # Should detect a chain (either sequential or continuation is fine)
        chain = detector.detect_chain("Then also show me Apple")
        assert chain is not None
        # Either SEQUENTIAL or CONTINUATION is acceptable (pattern order dependent)
        assert chain.chain_type in [ChainType.SEQUENTIAL, ChainType.CONTINUATION]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


