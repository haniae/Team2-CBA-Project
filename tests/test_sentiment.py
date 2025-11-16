"""
Tests for sentiment detection (Phase 3.4).
"""

import pytest
from src.finanlyzeos_chatbot.parsing.sentiment import (
    SentimentDetector,
    SentimentPolarity,
    SentimentIntensity,
    FinancialSentiment,
    SentimentAnalysis,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestPositiveSentiment:
    """Test positive sentiment detection"""
    
    def test_strong_positive(self):
        """Test strong positive sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This stock looks excellent and outstanding")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_mild_positive(self):
        """Test mild positive sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("The company seems good")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.MILD
    
    def test_positive_with_intensifier(self):
        """Test positive with intensifier makes it strong"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is very good")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.STRONG


class TestNegativeSentiment:
    """Test negative sentiment detection"""
    
    def test_strong_negative(self):
        """Test strong negative sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This stock is terrible and awful")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_mild_negative(self):
        """Test mild negative sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("The results are disappointing")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.MILD
    
    def test_negative_with_intensifier(self):
        """Test negative with intensifier makes it strong"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is very bad")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.STRONG


class TestFinancialSentiment:
    """Test financial-specific sentiment"""
    
    def test_bullish_sentiment(self):
        """Test bullish sentiment detection"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("I'm bullish on this stock and ready to buy")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BULLISH
    
    def test_bearish_sentiment(self):
        """Test bearish sentiment detection"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("I'm bearish and thinking about selling")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BEARISH
    
    def test_bullish_with_positive(self):
        """Test bullish aligns with positive"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This looks great, very bullish opportunity")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.financial_sentiment == FinancialSentiment.BULLISH
        # Should have high confidence due to alignment
        assert sentiment.confidence >= 0.85
    
    def test_bearish_with_negative(self):
        """Test bearish aligns with negative"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This looks bad, very bearish risk")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.financial_sentiment == FinancialSentiment.BEARISH
        # Should have high confidence due to alignment
        assert sentiment.confidence >= 0.85


class TestNegation:
    """Test negation handling"""
    
    def test_negation_flips_positive(self):
        """Test negation flips positive to negative"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is not good")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
    
    def test_negation_flips_negative(self):
        """Test negation flips negative to positive"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is not bad")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE


class TestIntensityLevels:
    """Test sentiment intensity detection"""
    
    def test_strong_intensity(self):
        """Test strong intensity detection"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Absolutely fantastic performance")
        assert sentiment is not None
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_mild_intensity(self):
        """Test mild intensity detection"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("The results are okay")
        assert sentiment is not None
        assert sentiment.intensity == SentimentIntensity.MILD


class TestSentimentIndicators:
    """Test sentiment indicator extraction"""
    
    def test_indicators_extracted(self):
        """Test that indicators are extracted"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This stock looks excellent and amazing")
        assert sentiment is not None
        assert len(sentiment.indicators) > 0
        # Should contain positive words
        assert any(word in ['excellent', 'amazing'] for word in sentiment.indicators)


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_multiple_indicators(self):
        """Test high confidence with multiple indicators"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is excellent, outstanding, and fantastic")
        assert sentiment is not None
        # Multiple strong indicators should give high confidence
        assert sentiment.confidence >= 0.85
    
    def test_good_confidence_aligned_sentiment(self):
        """Test good confidence with aligned financial sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Great opportunity, very bullish")
        assert sentiment is not None
        # Positive + bullish alignment should boost confidence
        assert sentiment.confidence >= 0.85


class TestHasSentiment:
    """Test quick sentiment check"""
    
    def test_has_sentiment_positive(self):
        """Test has_sentiment returns True for sentiment"""
        detector = SentimentDetector()
        
        assert detector.has_sentiment("This is excellent") is True
    
    def test_has_sentiment_negative(self):
        """Test has_sentiment returns False for no sentiment"""
        detector = SentimentDetector()
        
        assert detector.has_sentiment("Show me revenue for Apple") is False


class TestIntegrationWithParsing:
    """Test integration with parsing pipeline"""
    
    def test_parsing_detects_sentiment(self):
        """Test that parsing detects sentiment"""
        result = parse_to_structured("This stock looks excellent")
        
        assert "sentiment" in result
        assert result["sentiment"]["polarity"] == "positive"
    
    def test_parsing_populates_details(self):
        """Test that parsing populates sentiment details"""
        result = parse_to_structured("I'm very bullish on this stock")
        
        assert "sentiment" in result
        sent = result["sentiment"]
        assert sent["polarity"] == "positive"
        assert sent["intensity"] == "strong"
        assert sent["financial_sentiment"] == "bullish"
        assert sent["confidence"] > 0
        assert len(sent["indicators"]) > 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("")
        assert sentiment is None
    
    def test_no_sentiment(self):
        """Test text without sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Show me revenue")
        assert sentiment is None
    
    def test_mixed_sentiment(self):
        """Test mixed sentiment (positive and negative)"""
        detector = SentimentDetector()
        
        # More positive than negative
        sentiment = detector.detect_sentiment("Good revenue but bad margins")
        assert sentiment is not None
        # Should detect whichever is stronger


class TestFinancialKeywords:
    """Test financial-specific keywords"""
    
    def test_growth_positive(self):
        """Test growth is positive"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Strong growth in revenue")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
    
    def test_decline_negative(self):
        """Test decline is negative"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Declining profits")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
    
    def test_risk_negative(self):
        """Test risk is negative"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("High risk investment")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE


class TestComplexQueries:
    """Test complex sentiment scenarios"""
    
    def test_positive_with_bullish(self):
        """Test positive sentiment with bullish financial sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Excellent fundamentals make this very bullish")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.financial_sentiment == FinancialSentiment.BULLISH
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_negative_with_bearish(self):
        """Test negative sentiment with bearish financial sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Terrible earnings, very bearish outlook")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.financial_sentiment == FinancialSentiment.BEARISH
        assert sentiment.intensity == SentimentIntensity.STRONG


class TestExpandedPositivePatterns:
    """Test expanded positive sentiment patterns"""
    
    def test_strong_positive_expanded(self):
        """Test expanded strong positive words"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This stock is spectacular and phenomenal")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_mild_positive_expanded(self):
        """Test expanded mild positive words"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("The fundamentals look healthy and robust")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.MILD


class TestExpandedNegativePatterns:
    """Test expanded negative sentiment patterns"""
    
    def test_strong_negative_expanded(self):
        """Test expanded strong negative words"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("The earnings are devastating and disastrous")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_mild_negative_expanded(self):
        """Test expanded mild negative words"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Growth is sluggish and weak")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.MILD


class TestExpandedFinancialPatterns:
    """Test expanded financial sentiment patterns"""
    
    def test_bullish_rally(self):
        """Test 'rally' as bullish"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Expecting a strong rally in this stock")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BULLISH
    
    def test_bearish_correction(self):
        """Test 'correction' as bearish"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Market correction is coming")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BEARISH
    
    def test_upgrade_bullish(self):
        """Test 'upgrade' as bullish"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Analyst upgrade to outperform")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BULLISH
    
    def test_downgrade_bearish(self):
        """Test 'downgrade' as bearish"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Downgrade to underweight")
        assert sentiment is not None
        assert sentiment.financial_sentiment == FinancialSentiment.BEARISH


class TestDiminishers:
    """Test diminisher handling"""
    
    def test_slightly_positive(self):
        """Test diminisher reduces intensity"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is slightly good")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.MILD
    
    def test_somewhat_negative(self):
        """Test diminisher with negative"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Results are somewhat disappointing")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.MILD


class TestExpandedIntensifiers:
    """Test expanded intensifiers"""
    
    def test_remarkably_positive(self):
        """Test 'remarkably' as intensifier"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Remarkably good performance")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.POSITIVE
        assert sentiment.intensity == SentimentIntensity.STRONG
    
    def test_significantly_negative(self):
        """Test 'significantly' as intensifier"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Significantly worse than expected")
        assert sentiment is not None
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
        assert sentiment.intensity == SentimentIntensity.STRONG


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_revenue_report_not_sentiment(self):
        """Test revenue report doesn't trigger sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Show me the revenue report")
        # Should NOT detect as sentiment (neutral financial term)
        assert sentiment is None
    
    def test_earnings_data_not_sentiment(self):
        """Test earnings data doesn't trigger sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Get the earnings data for Q3")
        # Should NOT detect as sentiment
        assert sentiment is None
    
    def test_sentiment_analysis_question(self):
        """Test question about sentiment doesn't trigger"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("What is the sentiment analysis?")
        # Should NOT detect (meta question about sentiment)
        assert sentiment is None


class TestExpandedNegation:
    """Test expanded negation patterns"""
    
    def test_hardly_negation(self):
        """Test 'hardly' as negation"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This is hardly good")
        assert sentiment is not None
        # Negation should flip
        assert sentiment.polarity == SentimentPolarity.NEGATIVE
    
    def test_contraction_negation(self):
        """Test contraction negation"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("This doesn't look bad")
        assert sentiment is not None
        # Negation should flip
        assert sentiment.polarity == SentimentPolarity.POSITIVE


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_confidence_with_diminisher_penalty(self):
        """Test diminisher reduces confidence"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Somewhat good results")
        assert sentiment is not None
        # Should have lower confidence due to diminisher
        assert sentiment.confidence <= 0.80
    
    def test_confidence_with_multiple_indicators(self):
        """Test multiple indicators boost confidence"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Excellent, outstanding, and spectacular performance")
        assert sentiment is not None
        # Should have very high confidence (3+ indicators)
        assert sentiment.confidence >= 0.90
    
    def test_confidence_misaligned_sentiment(self):
        """Test misaligned sentiment has penalty"""
        detector = SentimentDetector()
        
        # Positive general sentiment with bearish financial sentiment
        sentiment_aligned = detector.detect_sentiment("Great opportunity, very bullish")
        sentiment_misaligned = detector.detect_sentiment("Great results but selling")
        
        # Aligned should have higher confidence
        assert sentiment_aligned.confidence > sentiment_misaligned.confidence


class TestComplexSentimentScenarios:
    """Test complex sentiment scenarios"""
    
    def test_diminisher_with_strong_word(self):
        """Test diminisher reduces strong sentiment"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Slightly excellent")
        assert sentiment is not None
        assert sentiment.intensity == SentimentIntensity.MILD
    
    def test_multiple_modifiers(self):
        """Test multiple modifiers together"""
        detector = SentimentDetector()
        
        sentiment = detector.detect_sentiment("Very remarkably good")
        assert sentiment is not None
        assert sentiment.intensity == SentimentIntensity.STRONG


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

