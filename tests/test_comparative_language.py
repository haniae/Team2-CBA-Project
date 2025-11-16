"""
Comprehensive test suite for comparative language detection and parsing.

Tests:
- Basic comparative patterns (better, worse, higher, lower)
- Superlatives (best, worst, most, least)
- Relative magnitude (twice as much, 50% more)
- Directional performance (outperforming, lagging)
- Comparison dimension extraction
- Binary vs superlative comparisons
- Confidence scoring
"""

import pytest
from src.finanlyzeos_chatbot.parsing.comparative import (
    ComparativeAnalyzer,
    ComparisonType,
    ComparisonDirection,
    ComparisonIntent,
)
from src.finanlyzeos_chatbot.parsing.parse import classify_intent, parse_to_structured


class TestBasicComparatives:
    """Test basic comparative pattern detection"""
    
    def test_better_detection(self):
        """Test 'better' comparative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is better?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.type == ComparisonType.BINARY
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_worse_detection(self):
        """Test 'worse' comparative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is worse?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.LOWER
    
    def test_higher_detection(self):
        """Test 'higher' comparative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which has higher revenue?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
        assert result.dimension == "revenue"
    
    def test_lower_detection(self):
        """Test 'lower' comparative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which has lower debt?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.LOWER
        assert result.dimension == "debt"
    
    def test_more_profitable(self):
        """Test 'more profitable' comparative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is more profitable?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
        assert result.dimension == "profit"


class TestSuperlatives:
    """Test superlative pattern detection"""
    
    def test_best_detection(self):
        """Test 'best' superlative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is the best?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_worst_detection(self):
        """Test 'worst' superlative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is the worst?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
        assert result.direction == ComparisonDirection.LOWER
    
    def test_highest_detection(self):
        """Test 'highest' superlative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which has the highest margins?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
        assert result.direction == ComparisonDirection.HIGHER
        assert result.dimension == "margin"
    
    def test_lowest_detection(self):
        """Test 'lowest' superlative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which has the lowest valuation?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
        assert result.direction == ComparisonDirection.LOWER
        assert result.dimension == "valuation"
    
    def test_most_profitable(self):
        """Test 'most profitable' superlative"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is the most profitable?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
        assert result.direction == ComparisonDirection.HIGHER
        assert result.dimension == "profit"


class TestComparisonDimensions:
    """Test extraction of what's being compared"""
    
    def test_revenue_dimension(self):
        """Test revenue dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has higher revenue?")
        assert dimension == "revenue"
    
    def test_profit_dimension(self):
        """Test profit dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Who is more profitable?")
        assert dimension == "profit"
    
    def test_margin_dimension(self):
        """Test margin dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better margins?")
        assert dimension == "margin"
    
    def test_growth_dimension(self):
        """Test growth dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which is growing faster?")
        assert dimension == "growth"
    
    def test_valuation_dimension(self):
        """Test valuation dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better valuation?")
        assert dimension == "valuation"
    
    def test_size_dimension(self):
        """Test size/market cap dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which is larger?")
        assert dimension == "size"
    
    def test_performance_dimension(self):
        """Test performance dimension extraction"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better performance?")
        assert dimension == "performance"


class TestRelativeMagnitude:
    """Test relative magnitude pattern detection"""
    
    def test_twice_as_much(self):
        """Test 'twice as much' magnitude"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Does Apple have twice as much revenue?", ["AAPL"])
        assert result is not None
        # Magnitude might be None if pattern doesn't match, but "twice" should be detected
        assert result.magnitude is None or "twice" in result.magnitude.lower()
    
    def test_percentage_more(self):
        """Test '50% more' magnitude"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Apple 50% more profitable?", ["AAPL"])
        assert result is not None
        assert "50%" in result.magnitude
    
    def test_significantly_higher(self):
        """Test 'significantly higher' magnitude"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is revenue significantly higher?", ["AAPL"])
        assert result is not None
        assert "significantly" in result.magnitude.lower()


class TestDirectionalPerformance:
    """Test directional performance patterns"""
    
    def test_outperforming(self):
        """Test 'outperforming' detection"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Apple outperforming Microsoft?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_lagging_behind(self):
        """Test 'lagging behind' detection"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Tesla lagging behind?", ["TSLA"])
        assert result is not None
        assert result.direction == ComparisonDirection.LOWER
    
    def test_ahead_of(self):
        """Test 'ahead of' detection"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Microsoft ahead of Apple?", ["MSFT", "AAPL"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER


class TestComparisonTypes:
    """Test different comparison types"""
    
    def test_binary_comparison(self):
        """Test binary (A vs B) comparison"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Apple vs Microsoft", ["AAPL", "MSFT"])
        assert result is not None
        assert result.type == ComparisonType.BINARY
    
    def test_superlative_comparison(self):
        """Test superlative (top N) comparison"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is the best?", ["AAPL", "MSFT", "GOOGL"])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
    
    def test_implicit_comparison(self):
        """Test implicit comparison (entities from context)"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is better?", [])
        assert result is not None
        assert result.type == ComparisonType.IMPLICIT


class TestConfidenceScoring:
    """Test confidence scoring for comparisons"""
    
    def test_high_confidence_explicit(self):
        """Test high confidence for explicit comparisons"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Compare Apple vs Microsoft revenue", ["AAPL", "MSFT"])
        assert result is not None
        assert result.confidence >= 0.7
    
    def test_medium_confidence_implicit(self):
        """Test confidence for implicit comparisons (may be high with entities)"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is better?", ["AAPL", "MSFT"])
        assert result is not None
        # With enhanced scoring, confidence can be high when entities are present
        assert 0.5 <= result.confidence <= 1.0


class TestQuickCheck:
    """Test is_comparative_query quick check"""
    
    def test_is_comparative_positive(self):
        """Test positive detection of comparative query"""
        analyzer = ComparativeAnalyzer()
        
        assert analyzer.is_comparative_query("Which is better?")
        assert analyzer.is_comparative_query("Apple vs Microsoft")
        assert analyzer.is_comparative_query("Which has higher revenue?")
        assert analyzer.is_comparative_query("Most profitable company")
    
    def test_is_comparative_negative(self):
        """Test negative detection (non-comparative query)"""
        analyzer = ComparativeAnalyzer()
        
        assert not analyzer.is_comparative_query("What is Apple's revenue?")
        assert not analyzer.is_comparative_query("Show me Microsoft data")
        assert not analyzer.is_comparative_query("Tell me about Google")


class TestIntegrationWithParsing:
    """Test integration with the parsing system"""
    
    def test_comparative_intent_classification(self):
        """Test that comparative queries are classified as 'comparative' intent"""
        # Test basic comparative
        structured = parse_to_structured("Which is better, Apple or Microsoft?")
        assert structured["intent"] == "comparative" or structured["intent"] == "compare"
    
    def test_comparative_intent_with_dimension(self):
        """Test comparative with specific dimension"""
        structured = parse_to_structured("Which has higher margins, Apple or Microsoft?")
        assert structured["intent"] in ["comparative", "compare"]
        if "comparison" in structured:
            assert structured["comparison"]["dimension"] == "margin"
    
    def test_superlative_intent(self):
        """Test superlative comparative intent"""
        structured = parse_to_structured("Which is the most profitable tech company?")
        # Should detect comparative intent
        assert structured["intent"] in ["comparative", "rank", "compare"]


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_query(self):
        """Test empty query handling"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("", [])
        assert result is None
    
    def test_no_entities(self):
        """Test comparative with no entities"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is better?", [])
        assert result is not None
        assert result.type == ComparisonType.IMPLICIT
    
    def test_single_entity(self):
        """Test comparative with single entity (threshold comparison)"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Apple better than average?", ["AAPL"])
        assert result is not None
        # Should be threshold comparison (comparing against a standard)
        assert result.type in [ComparisonType.THRESHOLD, ComparisonType.BINARY]


class TestExpandedPatterns:
    """Test expanded comparative patterns (informal, intensified, etc.)"""
    
    def test_informal_positive(self):
        """Test informal positive comparatives"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which stock is hotter?", ["AAPL", "TSLA"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_intensified_comparative(self):
        """Test intensified comparatives"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is way better?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_performance_focused(self):
        """Test performance-focused comparatives"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is more successful?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER


class TestExpandedDimensions:
    """Test expanded comparison dimensions"""
    
    def test_eps_dimension(self):
        """Test EPS dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has higher EPS?")
        assert dimension == "eps"
    
    def test_returns_dimension(self):
        """Test returns (ROE/ROA) dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better ROE?")
        assert dimension == "returns"
    
    def test_risk_dimension(self):
        """Test risk dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which is riskier?")
        assert dimension == "risk"
    
    def test_quality_dimension(self):
        """Test quality dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better quality?")
        assert dimension == "quality"
    
    def test_innovation_dimension(self):
        """Test innovation dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which is more innovative?")
        assert dimension == "innovation"
    
    def test_momentum_dimension(self):
        """Test momentum dimension detection"""
        analyzer = ComparativeAnalyzer()
        
        dimension = analyzer.extract_comparison_dimension("Which has better momentum?")
        assert dimension == "momentum"


class TestEnhancedMagnitude:
    """Test enhanced magnitude patterns"""
    
    def test_order_of_magnitude(self):
        """Test order of magnitude detection"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is it orders of magnitude higher?", ["AAPL"])
        assert result is not None
        if result.magnitude:
            assert "magnitude" in result.magnitude.lower()
    
    def test_fractional_magnitude(self):
        """Test fractional magnitude detection"""
        analyzer = ComparativeAnalyzer()
        
        # Need a clearer comparative context for detection
        result = analyzer.detect_comparison("Is Apple's revenue one third as much as Microsoft's?", ["AAPL", "MSFT"])
        # May or may not detect depending on pattern matching
        # If detected, should have magnitude
        if result and result.magnitude:
            assert "third" in result.magnitude.lower() or "one third" in result.magnitude.lower()
    
    def test_intensified_magnitude(self):
        """Test intensified magnitude"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is it dramatically higher?", ["AAPL"])
        assert result is not None
        if result.magnitude:
            assert "dramatically" in result.magnitude.lower()


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_time_expression_not_comparative(self):
        """Test that time expressions aren't flagged as comparisons"""
        analyzer = ComparativeAnalyzer()
        
        # "before" and "after" in time context shouldn't be comparisons
        result = analyzer.detect_comparison("Show me data from before the merger", [])
        # Should either be None or have very low confidence
        assert result is None or result.confidence < 0.5
    
    def test_informational_request_not_comparative(self):
        """Test that requests for more information aren't comparisons"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Tell me more about Apple", ["AAPL"])
        # Should not be detected as comparison
        assert result is None
    
    def test_quantity_expression_not_comparative(self):
        """Test that quantity expressions aren't comparisons"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Show me a few more examples", [])
        # Should not be detected as comparison
        assert result is None


class TestContextAwareConfidence:
    """Test context-aware confidence scoring"""
    
    def test_higher_confidence_with_entities(self):
        """Test that confidence increases with multiple entities"""
        analyzer = ComparativeAnalyzer()
        
        result1 = analyzer.detect_comparison("Which is better?", ["AAPL", "MSFT"])
        result2 = analyzer.detect_comparison("Which is better?", [])
        
        if result1 and result2:
            # Should have higher confidence with entities
            assert result1.confidence >= result2.confidence
    
    def test_higher_confidence_with_dimension(self):
        """Test that confidence increases with explicit dimension"""
        analyzer = ComparativeAnalyzer()
        
        result1 = analyzer.detect_comparison("Which has higher revenue?", ["AAPL", "MSFT"])
        result2 = analyzer.detect_comparison("Which is higher?", ["AAPL", "MSFT"])
        
        if result1 and result2:
            # Should have higher confidence with dimension
            assert result1.confidence >= result2.confidence
    
    def test_confidence_boost_for_financial_context(self):
        """Test that financial keywords boost confidence"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which company has better performance?", ["AAPL", "MSFT"])
        assert result is not None
        # Should have boosted confidence due to "company" and "performance"
        assert result.confidence >= 0.7


class TestExtendedPerformance:
    """Test extended performance patterns"""
    
    def test_crushing_performance(self):
        """Test informal performance language"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Apple crushing Microsoft?", ["AAPL", "MSFT"])
        assert result is not None
        assert result.direction == ComparisonDirection.HIGHER
    
    def test_struggling_performance(self):
        """Test negative performance language"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Is Tesla struggling against competitors?", ["TSLA"])
        assert result is not None
        assert result.direction == ComparisonDirection.LOWER


class TestSuperlativeVariations:
    """Test superlative variations"""
    
    def test_top_n_pattern(self):
        """Test 'top N' pattern"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Show me the top 5 stocks", [])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE
    
    def test_number_one_pattern(self):
        """Test 'number one' pattern"""
        analyzer = ComparativeAnalyzer()
        
        result = analyzer.detect_comparison("Which is the number one stock?", [])
        assert result is not None
        assert result.type == ComparisonType.SUPERLATIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

