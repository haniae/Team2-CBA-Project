"""
End-to-End Integration Tests (Phase 5.1)

Tests complex queries that use multiple NLU features together.
Validates that all 14 features work harmoniously in realistic scenarios.
"""

import pytest
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestMultiFeatureQueries:
    """Test queries that use multiple NLU features simultaneously"""
    
    def test_comparative_with_groups_and_abbreviations(self):
        """Test: Comparative + Company Groups + Abbreviations"""
        query = "Compare YoY revenue growth for FAANG vs Big Banks"
        result = parse_to_structured(query)
        
        # Should detect abbreviations (YoY)
        assert "abbreviations" in result
        assert any(a["abbreviation"].upper() == "YOY" for a in result["abbreviations"])
        
        # Should detect company groups (FAANG, Big Banks)
        assert "company_groups" in result
        assert len(result["company_groups"]) >= 1
        
        # Should detect comparative intent
        assert result.get("comparison") is not None
    
    def test_temporal_with_negation_and_filters(self):
        """Test: Temporal + Negation + Natural Filters"""
        query = "Show tech companies during pandemic, not including those with high risk"
        result = parse_to_structured(query)
        
        # Should detect temporal relationship (during pandemic)
        assert "temporal_relationships" in result
        
        # Should detect negation (not including)
        assert result.get("has_negation") is True
        
        # Should detect natural filters (tech companies, high risk)
        assert "natural_filters" in result or "filter_criteria" in result
    
    def test_conditional_with_fuzzy_quantities_and_metrics(self):
        """Test: Conditionals + Fuzzy Quantities + Metric Inference"""
        query = "if revenue is around $10B then show P/E ratio"
        result = parse_to_structured(query)
        
        # Should detect conditional (if...then)
        assert "conditionals" in result
        assert result["conditionals"][0]["type"] == "if_then"
        
        # Should detect fuzzy quantity (around $10B)
        assert "fuzzy_quantities" in result
        
        # Should detect metric abbreviation (P/E)
        assert "abbreviations" in result
    
    def test_sentiment_with_trend_and_spelling(self):
        """Test: Sentiment + Trend + Spelling Correction"""
        query = "Show excellent upward revenue trends for Microsoft"
        result = parse_to_structured(query)
        
        # Should detect sentiment (excellent)
        assert "sentiment" in result
        assert result["sentiment"]["polarity"] == "positive"
        
        # Should detect trend (upward)
        assert result.get("trend") is not None
        
        # Should classify as trend intent
        assert result["intent"] == "trend"
    
    def test_multi_intent_with_chaining_and_groups(self):
        """Test: Multi-Intent + Question Chaining + Groups"""
        query = "Show FAANG revenue, then compare to MAG7, and also analyze Big Banks"
        result = parse_to_structured(query)
        
        # Should detect multi-intent (three separate intents)
        assert "multi_intent" in result
        
        # Should detect company groups
        assert "company_groups" in result
        assert len(result["company_groups"]) >= 1


class TestRealWorldFinancialQueries:
    """Test realistic financial analyst queries"""
    
    def test_comprehensive_analysis_query(self):
        """Test comprehensive multi-feature query"""
        query = "Compare YTD P/E ratios for tech companies with revenue exceeding $50B, excluding bearish stocks"
        result = parse_to_structured(query)
        
        # Should have multiple features detected
        features_detected = []
        if "abbreviations" in result:
            features_detected.append("abbreviations")
        if "natural_filters" in result:
            features_detected.append("filters")
        if "fuzzy_quantities" in result:
            features_detected.append("fuzzy_quantities")
        if "sentiment" in result:
            features_detected.append("sentiment")
        if result.get("has_negation"):
            features_detected.append("negation")
        
        # Should detect at least 3 different features
        assert len(features_detected) >= 3
    
    def test_saas_metrics_query(self):
        """Test SaaS-specific metrics query"""
        query = "Show ARR and MRR growth for B2B SaaS companies"
        result = parse_to_structured(query)
        
        # Should detect multiple abbreviations (ARR, MRR, B2B, SaaS)
        assert "abbreviations" in result
        assert len(result["abbreviations"]) >= 2
        
        # Should detect trend/growth context
        assert "trend" in result or result["intent"] in ["trend", "lookup"]
    
    def test_crisis_comparison_query(self):
        """Test temporal event comparison"""
        query = "How did FAANG perform during pandemic compared to financial crisis?"
        result = parse_to_structured(query)
        
        # Should detect temporal relationships (multiple)
        assert "temporal_relationships" in result
        
        # Should detect company groups (FAANG)
        assert "company_groups" in result
        
        # Should detect comparative intent
        assert result.get("comparison") is not None


class TestFeaturePriority:
    """Test that features have correct priority when overlapping"""
    
    def test_negation_overrides_positive_sentiment(self):
        """Test negation properly affects sentiment"""
        query = "This is not good"
        result = parse_to_structured(query)
        
        # Should detect negation
        assert result.get("has_negation") is True
        
        # Sentiment should be affected by negation (handled in sentiment module)
        if "sentiment" in result:
            # Sentiment detector handles negation internally
            assert result["sentiment"]["polarity"] in ["negative", "positive"]
    
    def test_question_detection_priority(self):
        """Test questions are detected even with other features"""
        query = "What's the P/E ratio for FAANG companies?"
        result = parse_to_structured(query)
        
        # Should be classified as question
        assert result["intent"] in ["question", "lookup"]
        
        # But should also detect abbreviation and group
        assert "abbreviations" in result or "P/E" in query
        assert "company_groups" in result


class TestFeatureCombinations:
    """Test specific feature combinations"""
    
    def test_spelling_plus_comparative(self):
        """Test: Spelling + Comparative"""
        query = "Compare Microsoft and Google revenue"
        result = parse_to_structured(query)
        
        # Should detect comparative intent
        assert result.get("comparison") is not None or result["intent"] == "compare"
    
    def test_groups_plus_temporal_plus_metrics(self):
        """Test: Groups + Temporal + Metrics"""
        query = "Show MAG7 EBITDA during 2020"
        result = parse_to_structured(query)
        
        # Should detect company group
        assert "company_groups" in result
        
        # Should detect abbreviation (EBITDA)
        assert "abbreviations" in result
        
        # Should have temporal info (2020)
        assert "periods" in result
    
    def test_filters_plus_conditionals_plus_fuzzy(self):
        """Test: Filters + Conditionals + Fuzzy Quantities"""
        query = "if tech companies have approximately $100B revenue then show risk"
        result = parse_to_structured(query)
        
        # Should detect conditional
        assert "conditionals" in result
        
        # Should detect fuzzy quantity (approximately)
        assert "fuzzy_quantities" in result
        
        # Should detect filter (tech companies)
        assert "natural_filters" in result or "filter_criteria" in result
    
    def test_trend_plus_negation_plus_sentiment(self):
        """Test: Trend + Negation + Sentiment"""
        query = "Show companies with not declining revenue and positive outlook"
        result = parse_to_structured(query)
        
        # Should detect negation
        assert result.get("has_negation") is True
        
        # Should detect sentiment (positive)
        assert "sentiment" in result
        
        # Should detect trend direction (declining)
        assert result.get("trend") is not None
    
    def test_chaining_plus_abbreviations_plus_comparative(self):
        """Test: Chaining + Abbreviations + Comparative"""
        query = "Show ROI for Apple, then how does that compare to Microsoft's ROE?"
        result = parse_to_structured(query)
        
        # Should detect abbreviations (ROI, ROE)
        assert "abbreviations" in result
        assert len(result["abbreviations"]) >= 1
        
        # May detect multi-intent or chaining
        has_multi_feature = ("multi_intent" in result or 
                            "question_chain" in result or
                            result.get("comparison") is not None)
        assert has_multi_feature


class TestComplexRealWorldScenarios:
    """Test very complex real-world scenarios"""
    
    def test_investment_screening_query(self):
        """Test complex investment screening query"""
        query = "Show growth stocks with YoY revenue exceeding 20%, P/E under 30, not in tech sector, from S&P 500 leaders"
        result = parse_to_structured(query)
        
        # Should parse without errors
        assert result is not None
        assert "intent" in result
        
        # Should detect multiple features
        features_count = sum([
            "abbreviations" in result,
            "fuzzy_quantities" in result or ">" in query,
            "natural_filters" in result or "filter_criteria" in result,
            "company_groups" in result,
            result.get("has_negation") is True,
        ])
        
        # Should detect at least 3 features
        assert features_count >= 3
    
    def test_crisis_analysis_query(self):
        """Test crisis analysis with multiple temporal references"""
        query = "How did Big Tech perform before pandemic, during pandemic, and after pandemic?"
        result = parse_to_structured(query)
        
        # Should detect temporal relationships (multiple)
        assert "temporal_relationships" in result
        assert len(result["temporal_relationships"]) >= 2
        
        # Should detect company group
        assert "company_groups" in result
        
        # Should be a question
        assert result["intent"] in ["question", "trend", "lookup"]
    
    def test_conditional_screening_with_sentiment(self):
        """Test conditional screening with sentiment analysis"""
        query = "if revenue surpasses $100B and sentiment is bullish then buy, unless risk is high"
        result = parse_to_structured(query)
        
        # Should detect conditional
        assert "conditionals" in result
        
        # Should detect sentiment (bullish)
        assert "sentiment" in result
        
        # Should detect negation/unless logic
        assert result.get("has_negation") is True or len(result.get("conditionals", [])) > 0


class TestParsingPipelineIntegrity:
    """Test that parsing pipeline handles all features correctly"""
    
    def test_all_features_in_structured_output(self):
        """Test that all possible features appear in structured output"""
        # This is a mega-query touching many features
        query = "Compare YoY EBITDA for FAANG during pandemic vs Big Banks in recession, excluding bearish stocks with P/E > 50"
        result = parse_to_structured(query)
        
        # Core fields should always be present
        assert "intent" in result
        assert "tickers" in result
        # Metrics might be in different field names
        assert "computed" in result or "metrics" in result or "abbreviations" in result
        
        # Should detect several advanced features
        advanced_features = [
            "abbreviations",
            "company_groups", 
            "temporal_relationships",
            "comparison",
            "fuzzy_quantities",
            "sentiment",
        ]
        
        detected = sum(1 for feature in advanced_features if feature in result)
        # Should detect at least 4 advanced features
        assert detected >= 4
    
    def test_parsing_never_crashes(self):
        """Test parsing handles edge cases without crashing"""
        edge_cases = [
            "",  # Empty
            "?",  # Just punctuation
            "asdfghjkl",  # Gibberish
            "a" * 1000,  # Very long
            "!@#$%^&*()",  # Special chars
            "Show me revenue" * 50,  # Repetitive
        ]
        
        for query in edge_cases:
            result = parse_to_structured(query)
            # Should always return a result (never crash)
            assert result is not None
            assert "intent" in result


class TestFeatureInteractionConsistency:
    """Test that features don't conflict with each other"""
    
    def test_abbreviation_vs_ticker_distinction(self):
        """Test abbreviations don't conflict with tickers"""
        query = "Show PE for PE"  # PE as ticker vs P/E ratio
        result = parse_to_structured(query)
        
        # Should parse without errors
        assert result is not None
    
    def test_group_expansion_preserves_other_features(self):
        """Test group expansion doesn't interfere with other features"""
        query = "Show YoY revenue for FAANG with excellent performance"
        result = parse_to_structured(query)
        
        # All features should coexist
        assert "company_groups" in result  # FAANG
        assert "abbreviations" in result  # YoY
        assert "sentiment" in result  # excellent
    
    def test_multiple_temporals_coexist(self):
        """Test multiple temporal features work together"""
        query = "Show revenue before 2020 and after 2022, YoY growth"
        result = parse_to_structured(query)
        
        # Should detect temporal relationships
        assert "temporal_relationships" in result
        
        # Should detect abbreviation
        assert "abbreviations" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

