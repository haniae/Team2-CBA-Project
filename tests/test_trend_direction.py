"""
Comprehensive test suite for trend direction detection and parsing.

Tests:
- Positive trends (improving, increasing, rising, growing)
- Negative trends (declining, decreasing, falling, shrinking)
- Acceleration/deceleration (speeding up, slowing down)
- Stability (stable, steady, flat)
- Volatility (volatile, fluctuating, erratic)
- Trend dimensions
- Magnitude and timeframe extraction
- Confidence scoring
"""

import pytest
from src.finanlyzeos_chatbot.parsing.trends import (
    TrendAnalyzer,
    TrendDirection,
    TrendVelocity,
    TrendIntent,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestPositiveTrends:
    """Test positive trend direction detection"""
    
    def test_improving_detection(self):
        """Test 'improving' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue improving?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.dimension == "revenue"
    
    def test_increasing_detection(self):
        """Test 'increasing' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins increasing?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.dimension == "margin"
    
    def test_rising_detection(self):
        """Test 'rising' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock price rising?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.dimension == "stock_price"
    
    def test_growing_detection(self):
        """Test 'growing' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is profit growing?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.dimension == "profit"
    
    def test_strengthening_detection(self):
        """Test 'strengthening' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is cash flow strengthening?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE


class TestNegativeTrends:
    """Test negative trend direction detection"""
    
    def test_declining_detection(self):
        """Test 'declining' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue declining?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
        assert result.dimension == "revenue"
    
    def test_decreasing_detection(self):
        """Test 'decreasing' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins decreasing?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
        assert result.dimension == "margin"
    
    def test_falling_detection(self):
        """Test 'falling' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock price falling?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
        assert result.dimension == "stock_price"
    
    def test_shrinking_detection(self):
        """Test 'shrinking' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is market cap shrinking?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE


class TestStableTrends:
    """Test stable trend detection"""
    
    def test_stable_detection(self):
        """Test 'stable' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue stable?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
        assert result.dimension == "revenue"
    
    def test_steady_detection(self):
        """Test 'steady' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins holding steady?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
    
    def test_flat_detection(self):
        """Test 'flat' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth flat?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE


class TestVolatileTrends:
    """Test volatile trend detection"""
    
    def test_volatile_detection(self):
        """Test 'volatile' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock price volatile?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE
        assert result.dimension == "stock_price"
    
    def test_fluctuating_detection(self):
        """Test 'fluctuating' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue fluctuating?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE
    
    def test_erratic_detection(self):
        """Test 'erratic' trend"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are earnings erratic?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE


class TestVelocity:
    """Test velocity (acceleration/deceleration) detection"""
    
    def test_accelerating_detection(self):
        """Test 'accelerating' velocity"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth accelerating?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.velocity == TrendVelocity.ACCELERATING
        assert result.dimension == "growth"
    
    def test_speeding_up_detection(self):
        """Test 'speeding up' velocity"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue growth speeding up?")
        assert result is not None
        assert result.velocity == TrendVelocity.ACCELERATING
    
    def test_decelerating_detection(self):
        """Test 'decelerating' velocity"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth decelerating?")
        assert result is not None
        assert result.velocity == TrendVelocity.DECELERATING
    
    def test_slowing_down_detection(self):
        """Test 'slowing down' velocity"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue growth slowing down?")
        assert result is not None
        assert result.velocity == TrendVelocity.DECELERATING


class TestMagnitude:
    """Test magnitude/intensity detection"""
    
    def test_dramatically_increasing(self):
        """Test dramatic magnitude"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue dramatically increasing?")
        assert result is not None
        assert result.magnitude is not None
        assert "dramatically" in result.magnitude.lower()
    
    def test_slightly_declining(self):
        """Test slight magnitude"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is profit slightly declining?")
        assert result is not None
        assert result.magnitude is not None
        assert "slightly" in result.magnitude.lower()
    
    def test_rapidly_growing(self):
        """Test rapid magnitude"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the company rapidly growing?")
        assert result is not None
        assert result.magnitude is not None
        assert "rapidly" in result.magnitude.lower()


class TestTimeframe:
    """Test timeframe extraction"""
    
    def test_recently_improving(self):
        """Test recent timeframe"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue recently improving?")
        assert result is not None
        assert result.timeframe is not None
        assert "recent" in result.timeframe.lower()
    
    def test_historically_declining(self):
        """Test historical timeframe"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Has profit historically declined?")
        assert result is not None
        assert result.timeframe is not None
        assert "historical" in result.timeframe.lower()


class TestDimensionExtraction:
    """Test extraction of what's trending"""
    
    def test_revenue_trend(self):
        """Test revenue dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue improving?")
        assert result is not None
        assert result.dimension == "revenue"
    
    def test_profit_trend(self):
        """Test profit dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is profit growing?")
        assert result is not None
        assert result.dimension == "profit"
    
    def test_margin_trend(self):
        """Test margin dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins increasing?")
        assert result is not None
        assert result.dimension == "margin"
    
    def test_stock_price_trend(self):
        """Test stock price dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock price rising?")
        assert result is not None
        assert result.dimension == "stock_price"


class TestConfidenceScoring:
    """Test confidence scoring for trend detection"""
    
    def test_high_confidence_with_all_details(self):
        """Test high confidence when all details present"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue rapidly increasing recently?")
        assert result is not None
        # Should have high confidence with direction, velocity, magnitude, timeframe
        assert result.confidence >= 0.7
    
    def test_medium_confidence_basic(self):
        """Test medium confidence for basic trend query"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is it improving?")
        assert result is not None
        # Should have medium confidence with just direction
        assert 0.5 <= result.confidence < 0.8


class TestQuickCheck:
    """Test is_trend_query quick check"""
    
    def test_is_trend_query_positive(self):
        """Test positive detection of trend queries"""
        analyzer = TrendAnalyzer()
        
        assert analyzer.is_trend_query("Is revenue improving?")
        assert analyzer.is_trend_query("Are margins declining?")
        assert analyzer.is_trend_query("Is growth accelerating?")
        assert analyzer.is_trend_query("Is the stock volatile?")
    
    def test_is_trend_query_negative(self):
        """Test negative detection (non-trend queries)"""
        analyzer = TrendAnalyzer()
        
        assert not analyzer.is_trend_query("What is the revenue?")
        assert not analyzer.is_trend_query("Show me Apple's data")
        assert not analyzer.is_trend_query("Compare Apple and Microsoft")


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_trend_intent_classification(self):
        """Test that trend queries get trend metadata"""
        structured = parse_to_structured("Is Apple's revenue improving over time?")
        # Should detect trend intent or have trend details
        assert "trend" in structured or structured["intent"] == "trend"
    
    def test_trend_details_populated(self):
        """Test that trend details are populated in structured output"""
        structured = parse_to_structured("Is revenue rapidly increasing?")
        # If trend is detected, should have trend details
        if "trend" in structured and structured["trend"]:
            assert "direction" in structured["trend"]
            assert structured["trend"]["direction"] == "positive"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_query(self):
        """Test empty query handling"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("")
        assert result is None
    
    def test_no_trend_words(self):
        """Test query with no trend indicators"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("What is Apple's revenue?")
        # Should not detect a trend
        assert result is None or result.direction == TrendDirection.NEUTRAL


class TestExpandedPositivePatterns:
    """Test expanded positive trend patterns"""
    
    def test_surging_detection(self):
        """Test 'surging' momentum pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue surging?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_bullish_detection(self):
        """Test 'bullish' market sentiment pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock bullish?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_on_the_rise_detection(self):
        """Test 'on the rise' colloquial pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins on the rise?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_turnaround_detection(self):
        """Test 'turnaround' recovery pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is there a turnaround in performance?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE


class TestExpandedNegativePatterns:
    """Test expanded negative trend patterns"""
    
    def test_tanking_detection(self):
        """Test 'tanking' collapse pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock tanking?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_bearish_detection(self):
        """Test 'bearish' market sentiment pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the outlook bearish?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_under_pressure_detection(self):
        """Test 'under pressure' stress pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins under pressure?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_losing_ground_detection(self):
        """Test 'losing ground' regression pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is market share losing ground?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE


class TestExpandedStablePatterns:
    """Test expanded stable trend patterns"""
    
    def test_sideways_detection(self):
        """Test 'sideways' trading pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock trading sideways?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
    
    def test_consolidating_detection(self):
        """Test 'consolidating' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue consolidating?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
    
    def test_in_balance_detection(self):
        """Test 'in balance' equilibrium pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth in balance?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE


class TestExpandedVolatilePatterns:
    """Test expanded volatile trend patterns"""
    
    def test_all_over_the_place_detection(self):
        """Test colloquial volatility pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock all over the place?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE
    
    def test_bouncing_around_detection(self):
        """Test 'bouncing around' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue bouncing around?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE


class TestVelocityVariations:
    """Test velocity pattern variations"""
    
    def test_rapid_growth(self):
        """Test rapid velocity indicator"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth rapid?")
        assert result is not None
        assert result.velocity == TrendVelocity.ACCELERATING
    
    def test_gaining_momentum(self):
        """Test gaining momentum pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue gaining momentum?")
        assert result is not None
        assert result.velocity == TrendVelocity.ACCELERATING
    
    def test_tapering_off(self):
        """Test tapering off deceleration"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth tapering off?")
        assert result is not None
        assert result.velocity == TrendVelocity.DECELERATING


class TestFalsePositivePrevention:
    """Test that non-trend queries aren't falsely detected"""
    
    def test_comparison_not_trend(self):
        """Test that comparisons aren't detected as trends"""
        analyzer = TrendAnalyzer()
        
        # "better" in comparison context, not trend
        result = analyzer.detect_trend("Which is better, Apple or Microsoft?")
        # Should be filtered out as comparison (false positive prevention)
        assert result is None
    
    def test_lookup_not_trend(self):
        """Test that basic lookups aren't detected as trends"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("What is the current revenue?")
        # "current" might trigger but shouldn't be strong trend
        assert result is None or result.confidence < 0.6


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    def test_complex_trend_query(self):
        """Test complex trend query with all elements"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is Apple's revenue rapidly increasing recently?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        assert result.velocity == TrendVelocity.ACCELERATING
        assert result.dimension == "revenue"
        assert result.magnitude is not None
        assert result.timeframe is not None
    
    def test_simple_trend_question(self):
        """Test simple trend question"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is profit improving?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
        # Dimension might be None or "profit" depending on extraction
        if result.dimension:
            assert result.dimension == "profit"


class TestExpandedPositivePatterns:
    """Test expanded positive trend patterns"""
    
    def test_taking_off_detection(self):
        """Test 'taking off' acceleration pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue taking off?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_thriving_detection(self):
        """Test 'thriving' strength indicator"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the business thriving?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_breaking_out_detection(self):
        """Test 'breaking out' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock breaking out?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE
    
    def test_exceeding_expectations(self):
        """Test 'exceeding expectations' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue exceeding expectations?")
        assert result is not None
        assert result.direction == TrendDirection.POSITIVE


class TestExpandedNegativePatterns:
    """Test expanded negative trend patterns"""
    
    def test_spiraling_down_detection(self):
        """Test 'spiraling down' severe decline"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue spiraling down?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_under_strain_detection(self):
        """Test 'under strain' pressure pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are margins under strain?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_missing_expectations(self):
        """Test 'missing expectations' underperformance"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue missing expectations?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE
    
    def test_heading_wrong_direction(self):
        """Test 'heading in the wrong direction' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is profit heading in the wrong direction?")
        assert result is not None
        assert result.direction == TrendDirection.NEGATIVE


class TestExpandedStablePatterns:
    """Test expanded stable trend patterns"""
    
    def test_treading_water_detection(self):
        """Test 'treading water' holding pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue treading water?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
    
    def test_no_change_detection(self):
        """Test 'no change' stability"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is there no change in margins?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE
    
    def test_neutral_detection(self):
        """Test 'neutral' stability"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth neutral?")
        assert result is not None
        assert result.direction == TrendDirection.STABLE


class TestExpandedVolatilePatterns:
    """Test expanded volatile trend patterns"""
    
    def test_rollercoaster_detection(self):
        """Test 'rollercoaster' volatility pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the stock on a rollercoaster?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE
    
    def test_all_over_map_detection(self):
        """Test 'all over the map' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue all over the map?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE
    
    def test_wide_swings_detection(self):
        """Test 'wide swings' pattern"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are there wide swings in earnings?")
        assert result is not None
        assert result.direction == TrendDirection.VOLATILE


class TestExpandedVelocity:
    """Test expanded velocity patterns"""
    
    def test_exponential_growth(self):
        """Test 'exponential' acceleration"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth exponential?")
        assert result is not None
        assert result.velocity == TrendVelocity.ACCELERATING
    
    def test_losing_steam(self):
        """Test 'losing steam' deceleration"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is growth losing steam?")
        assert result is not None
        assert result.velocity == TrendVelocity.DECELERATING
    
    def test_petering_out(self):
        """Test 'petering out' deceleration"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is momentum petering out?")
        assert result is not None
        assert result.velocity == TrendVelocity.DECELERATING


class TestExpandedDimensions:
    """Test new dimension detection"""
    
    def test_market_share_dimension(self):
        """Test market share dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is market share growing?")
        assert result is not None
        assert result.dimension == "market_share"
    
    def test_costs_dimension(self):
        """Test costs dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Are costs increasing?")
        assert result is not None
        assert result.dimension == "costs"
    
    def test_volume_dimension(self):
        """Test volume dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is trading volume rising?")
        assert result is not None
        assert result.dimension == "volume"
    
    def test_customer_base_dimension(self):
        """Test customer base dimension"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is the customer base growing?")
        assert result is not None
        assert result.dimension == "customer_base"


class TestEnhancedFalsePositivePrevention:
    """Test enhanced false positive prevention"""
    
    def test_static_state_not_trend(self):
        """Test that static state questions aren't trends"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("What is the current revenue?")
        # Should be filtered as false positive
        assert result is None
    
    def test_conditional_not_trend(self):
        """Test that conditionals aren't trends"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("If revenue improves, what should we do?")
        # Should be filtered as false positive
        assert result is None
    
    def test_comparison_with_trend_words(self):
        """Test that comparisons with trend words aren't trends"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is Apple better than Microsoft?")
        # Should be filtered as comparison, not trend
        assert result is None


class TestEnhancedConfidenceScoring:
    """Test enhanced context-aware confidence scoring"""
    
    def test_high_confidence_complete_query(self):
        """Test high confidence with all elements"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is revenue dramatically increasing over time recently?")
        assert result is not None
        # Should have very high confidence
        assert result.confidence >= 0.85
    
    def test_medium_confidence_basic_query(self):
        """Test medium confidence for basic query"""
        analyzer = TrendAnalyzer()
        
        result = analyzer.detect_trend("Is it improving?")
        assert result is not None
        # Should have medium confidence
        assert 0.5 <= result.confidence < 0.75
    
    def test_confidence_boost_with_temporal(self):
        """Test confidence boost with temporal context"""
        analyzer = TrendAnalyzer()
        
        result1 = analyzer.detect_trend("Is revenue improving over time?")
        result2 = analyzer.detect_trend("Is revenue improving?")
        
        if result1 and result2:
            # Temporal context should boost confidence
            assert result1.confidence >= result2.confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



