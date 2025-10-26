"""Tests for enhanced routing system."""

import pytest
from benchmarkos_chatbot.routing import (
    enhance_structured_parse,
    should_build_dashboard,
    EnhancedIntent,
    EnhancedRouting,
)
from benchmarkos_chatbot.parsing.parse import parse_to_structured


class TestEnhancedRouting:
    """Test cases for enhanced routing system."""
    
    def test_metrics_single_pattern(self):
        """Test single-ticker metrics pattern."""
        text = "Show Apple KPIs"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.METRICS_SINGLE
        assert routing.confidence >= 0.8
        assert routing.force_dashboard is False
        assert routing.force_text_only is False
    
    def test_metrics_multi_pattern(self):
        """Test multi-ticker metrics pattern."""
        text = "Show Apple and Microsoft KPIs"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.METRICS_MULTI
        assert routing.confidence >= 0.8
        assert routing.force_text_only is True
    
    def test_compare_two_pattern(self):
        """Test two-company comparison pattern."""
        text = "Compare Apple vs Microsoft"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.COMPARE_TWO
        assert routing.confidence == 1.0
        assert routing.force_text_only is True
    
    def test_compare_multi_pattern(self):
        """Test multi-company comparison pattern."""
        text = "Compare Apple, Microsoft, and Google"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.COMPARE_MULTI
        assert routing.confidence == 1.0
        assert routing.force_text_only is True
    
    def test_dashboard_explicit_pattern(self):
        """Test explicit dashboard request."""
        text = "Dashboard AAPL"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.DASHBOARD_EXPLICIT
        assert routing.force_dashboard is True
        assert routing.confidence == 1.0
    
    def test_legacy_command_fact(self):
        """Test legacy fact command pass-through."""
        text = "fact AAPL 2022"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.LEGACY_COMMAND
        assert routing.legacy_command == text
        assert routing.confidence == 1.0
    
    def test_legacy_command_scenario(self):
        """Test legacy scenario command pass-through."""
        text = "scenario AAPL Bull rev=+8%"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.LEGACY_COMMAND
        assert routing.legacy_command == text
    
    def test_legacy_command_ingest(self):
        """Test legacy ingest command pass-through."""
        text = "ingest AAPL 5"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.LEGACY_COMMAND
    
    def test_legacy_command_audit(self):
        """Test legacy audit command pass-through."""
        text = "audit AAPL 2022"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.LEGACY_COMMAND
    
    def test_natural_language_fallback(self):
        """Test that complex queries fall back to natural language."""
        text = "Tell me about Apple's competitive position"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        # Should have low confidence for LLM fallback
        assert routing.confidence < 0.7
    
    def test_should_build_dashboard_force_true(self):
        """Test dashboard forced to build."""
        routing = EnhancedRouting(
            intent=EnhancedIntent.DASHBOARD_EXPLICIT,
            force_dashboard=True
        )
        
        # Should override existing decision
        assert should_build_dashboard(routing, False) is True
        assert should_build_dashboard(routing, True) is True
    
    def test_should_build_dashboard_force_false(self):
        """Test dashboard forced to text only."""
        routing = EnhancedRouting(
            intent=EnhancedIntent.COMPARE_TWO,
            force_text_only=True
        )
        
        # Should override existing decision
        assert should_build_dashboard(routing, False) is False
        assert should_build_dashboard(routing, True) is False
    
    def test_should_build_dashboard_respect_existing(self):
        """Test that existing logic is respected when no override."""
        routing = EnhancedRouting(
            intent=EnhancedIntent.METRICS_SINGLE,
            force_dashboard=False,
            force_text_only=False
        )
        
        # Should respect existing decision
        assert should_build_dashboard(routing, True) is True
        assert should_build_dashboard(routing, False) is False
    
    def test_metrics_single_with_period(self):
        """Test single-ticker metrics with period specification."""
        text = "Show Apple KPIs for 2023"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.METRICS_SINGLE
        assert routing.force_text_only is False
    
    def test_compare_case_insensitive(self):
        """Test that comparison matching is case-insensitive."""
        text = "COMPARE AAPL VS MSFT"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        assert routing.intent == EnhancedIntent.COMPARE_TWO
    
    def test_fallback_to_existing_parser(self):
        """Test fallback to existing parser for ambiguous queries."""
        text = "What are Apple's metrics?"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        # Should use existing parser classification
        # Confidence should be moderate (0.6-0.8)
        assert 0.5 <= routing.confidence <= 0.9


class TestPatternEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_input(self):
        """Test handling of empty input."""
        text = ""
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        # Should not crash, should have low confidence
        assert routing.confidence <= 1.0
    
    def test_single_word_input(self):
        """Test handling of single word input."""
        text = "AAPL"
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        # Should handle gracefully
        assert routing is not None
    
    def test_very_long_input(self):
        """Test handling of very long natural language input."""
        text = (
            "I would like to understand the comprehensive financial performance "
            "of Apple Inc. including revenue trends, profitability metrics, and "
            "valuation ratios compared to industry peers over the last five years."
        )
        structured = parse_to_structured(text)
        routing = enhance_structured_parse(text, structured)
        
        # Should fall back to natural language
        assert routing.confidence < 0.7 or routing.intent == EnhancedIntent.NATURAL_LANGUAGE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

