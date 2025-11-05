"""
Sentiment detection for natural language queries.

Handles:
- Positive/negative/neutral sentiment
- Intensity levels (strong, mild)
- Financial-specific sentiment (bullish, bearish)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class SentimentPolarity(Enum):
    """Sentiment polarity"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentIntensity(Enum):
    """Sentiment intensity"""
    STRONG = "strong"
    MILD = "mild"
    MODERATE = "moderate"


class FinancialSentiment(Enum):
    """Financial-specific sentiment"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SentimentAnalysis:
    """
    Represents sentiment analysis result.
    """
    polarity: SentimentPolarity
    intensity: SentimentIntensity
    financial_sentiment: Optional[FinancialSentiment]
    confidence: float
    indicators: List[str]  # Words/phrases that contributed to sentiment
    
    def __repr__(self):
        return (f"SentimentAnalysis(polarity={self.polarity.value}, "
                f"intensity={self.intensity.value}, "
                f"financial={self.financial_sentiment.value if self.financial_sentiment else None}, "
                f"confidence={self.confidence:.2f})")


class SentimentDetector:
    """
    Detect sentiment in natural language queries.
    """
    
    # Positive sentiment patterns - MASSIVELY EXPANDED
    POSITIVE_STRONG = [
        r'\b(excellent|outstanding|exceptional|superb|fantastic|amazing|brilliant)\b',
        r'\b(love|adore|thrilled|excited|delighted)\b',
        r'\b(best|strongest|highest|top)\b',
        # NEW: More strong positive
        r'\b(magnificent|spectacular|phenomenal|incredible|remarkable)\b',
        r'\b(stellar|impressive|extraordinary|tremendous)\b',
        r'\b(perfect|flawless|optimal|ideal)\b',
    ]
    
    POSITIVE_MILD = [
        r'\b(good|nice|decent|solid|fine|ok|okay)\b',
        r'\b(like|prefer|appreciate|enjoy)\b',
        r'\b(better|improved|improving|positive|favorable)\b',
        r'\b(up|gain|growth|increase|rise|surge)\b',
        r'\b(great|opportunity|potential)\b',
        # NEW: More mild positive
        r'\b(healthy|strong|robust|stable|sound)\b',
        r'\b(attractive|appealing|promising|encouraging)\b',
        r'\b(benefit|advantage|upbeat|hopeful)\b',
        r'\b(outperform|exceed|beat)\b',
    ]
    
    # Negative sentiment patterns - MASSIVELY EXPANDED
    NEGATIVE_STRONG = [
        r'\b(terrible|awful|horrible|disaster|catastrophic|abysmal)\b',
        r'\b(hate|despise|detest|loathe)\b',
        r'\b(worst|weakest|lowest|bottom)\b',
        r'\b(collapse|crash|plunge|plummet)\b',
        # NEW: More strong negative
        r'\b(devastating|disastrous|dreadful|appalling|horrendous)\b',
        r'\b(atrocious|miserable|pathetic|dismal)\b',
        r'\b(failed|failure|failing|broken)\b',
    ]
    
    NEGATIVE_MILD = [
        r'\b(bad|poor|disappointing|concerning|worrying)\b',
        r'\b(dislike|concern|worry|doubt)\b',
        r'\b(worse|declining|decreasing|negative|unfavorable)\b',
        r'\b(down|loss|drop|fall|decline)\b',
        r'\b(risk|risky|volatile|unstable)\b',
        # NEW: More mild negative
        r'\b(weak|soft|sluggish|slow|flat)\b',
        r'\b(challenged|pressured|strained|troubled)\b',
        r'\b(uncertain|questionable|problematic|difficult)\b',
        r'\b(underperform|miss|disappoint|lag)\b',
    ]
    
    # Financial sentiment patterns (also contribute to general sentiment) - EXPANDED
    BULLISH_PATTERNS = [
        r'\b(bullish|optimistic|confident|promising)\b',
        r'\b(buy|invest|long|accumulate)\b',
        r'\b(upside)\b',
        # NEW: More bullish patterns
        r'\b(rally|rebound|recovery|turnaround)\b',
        r'\b(momentum|strength|conviction)\b',
        r'\b(upgrade|overweight|outperform)\b',
    ]
    
    BEARISH_PATTERNS = [
        r'\b(bearish|pessimistic|cautious|worried)\b',
        r'\b(sell|short|divest|exit)\b',
        r'\b(downside|threat|danger)\b',
        # NEW: More bearish patterns
        r'\b(correction|pullback|retreat|selloff)\b',
        r'\b(weakness|pressure|headwind)\b',
        r'\b(downgrade|underweight|underperform)\b',
    ]
    
    # Intensifiers - EXPANDED
    INTENSIFIERS = [
        r'\b(very|extremely|highly|incredibly|really|so|too)\b',
        r'\b(absolutely|completely|totally|entirely)\b',
        # NEW: More intensifiers
        r'\b(remarkably|exceptionally|significantly|substantially)\b',
        r'\b(particularly|especially|quite|fairly)\b',
    ]
    
    # NEW: Diminishers (reduce intensity)
    DIMINISHERS = [
        r'\b(slightly|somewhat|relatively|fairly|rather)\b',
        r'\b(moderately|mildly|a\s+bit|a\s+little)\b',
        r'\b(kind\s+of|sort\s+of|pretty)\b',
    ]
    
    # Negation patterns (flip sentiment) - EXPANDED
    NEGATION_PATTERNS = [
        r'\b(not|no|never|nothing|none|nobody)\b',
        r'\b(neither|nor|without|lacking)\b',
        r'\bnot\s+',
        # NEW: More negation patterns
        r'\b(hardly|barely|scarcely|rarely)\b',
        r'\b(doesn\'t|don\'t|didn\'t|won\'t|can\'t)\b',
    ]
    
    # NEW: False positive patterns (DON'T detect as sentiment)
    FALSE_POSITIVE_PATTERNS = [
        # Neutral financial terms that aren't sentiment
        r'\b(?:revenue|profit|earnings|sales)\s+(?:report|data|numbers?|results?)\b',
        r'\b(?:financial|quarterly|annual)\s+(?:report|statement|results?)\b',
        # Questions about sentiment
        r'\b(?:what|how)\s+(?:is|was)\s+the\s+sentiment\b',
        r'\bsentiment\s+(?:analysis|score|rating)\b',
    ]
    
    def __init__(self):
        """Initialize the sentiment detector"""
        self._positive_strong = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_STRONG]
        self._positive_mild = [re.compile(p, re.IGNORECASE) for p in self.POSITIVE_MILD]
        self._negative_strong = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_STRONG]
        self._negative_mild = [re.compile(p, re.IGNORECASE) for p in self.NEGATIVE_MILD]
        self._bullish_patterns = [re.compile(p, re.IGNORECASE) for p in self.BULLISH_PATTERNS]
        self._bearish_patterns = [re.compile(p, re.IGNORECASE) for p in self.BEARISH_PATTERNS]
        self._intensifiers = [re.compile(p, re.IGNORECASE) for p in self.INTENSIFIERS]
        self._diminishers = [re.compile(p, re.IGNORECASE) for p in self.DIMINISHERS]
        self._negation_patterns = [re.compile(p, re.IGNORECASE) for p in self.NEGATION_PATTERNS]
        self._false_positive_patterns = [re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS]
    
    def detect_sentiment(self, text: str) -> Optional[SentimentAnalysis]:
        """
        Detect sentiment in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            SentimentAnalysis object or None if no sentiment detected
        """
        if not text:
            return None
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return None
        
        # Count sentiment indicators
        positive_strong_count, pos_strong_indicators = self._count_matches(text, self._positive_strong)
        positive_mild_count, pos_mild_indicators = self._count_matches(text, self._positive_mild)
        negative_strong_count, neg_strong_indicators = self._count_matches(text, self._negative_strong)
        negative_mild_count, neg_mild_indicators = self._count_matches(text, self._negative_mild)
        
        # Financial sentiment also contributes to general sentiment
        bullish_count, bullish_indicators = self._count_matches(text, self._bullish_patterns)
        bearish_count, bearish_indicators = self._count_matches(text, self._bearish_patterns)
        
        # Check for negation (can flip sentiment)
        has_negation = self._has_negation(text)
        
        # Check for intensifiers and diminishers
        has_intensifier = self._has_intensifier(text)
        has_diminisher = self._has_diminisher(text)
        
        # Calculate scores (financial sentiment contributes to general sentiment)
        positive_score = (positive_strong_count * 2) + positive_mild_count + bullish_count
        negative_score = (negative_strong_count * 2) + negative_mild_count + bearish_count
        
        # Apply negation (flip scores)
        if has_negation:
            positive_score, negative_score = negative_score, positive_score
            # Swap indicators too
            pos_strong_indicators, neg_strong_indicators = neg_strong_indicators, pos_strong_indicators
            pos_mild_indicators, neg_mild_indicators = neg_mild_indicators, pos_mild_indicators
        
        # Determine polarity
        if positive_score == 0 and negative_score == 0:
            return None  # No sentiment detected
        
        if positive_score > negative_score:
            polarity = SentimentPolarity.POSITIVE
            indicators = pos_strong_indicators + pos_mild_indicators + bullish_indicators
            intensity = self._determine_intensity(
                positive_strong_count + (bullish_count if bullish_count > 0 else 0), 
                positive_mild_count, 
                has_intensifier,
                has_diminisher
            )
        elif negative_score > positive_score:
            polarity = SentimentPolarity.NEGATIVE
            indicators = neg_strong_indicators + neg_mild_indicators + bearish_indicators
            intensity = self._determine_intensity(
                negative_strong_count + (bearish_count if bearish_count > 0 else 0), 
                negative_mild_count, 
                has_intensifier,
                has_diminisher
            )
        else:
            polarity = SentimentPolarity.NEUTRAL
            indicators = (pos_strong_indicators + pos_mild_indicators + 
                         neg_strong_indicators + neg_mild_indicators +
                         bullish_indicators + bearish_indicators)
            intensity = SentimentIntensity.MODERATE
        
        # Detect financial sentiment
        financial_sentiment = self._detect_financial_sentiment(text)
        
        # Calculate confidence (enhanced)
        confidence = self._calculate_confidence_enhanced(
            polarity, positive_score, negative_score, 
            has_intensifier, has_diminisher, financial_sentiment, len(indicators)
        )
        
        return SentimentAnalysis(
            polarity=polarity,
            intensity=intensity,
            financial_sentiment=financial_sentiment,
            confidence=confidence,
            indicators=indicators
        )
    
    def _count_matches(self, text: str, patterns: List[re.Pattern]) -> tuple[int, List[str]]:
        """Count pattern matches and return matching words"""
        count = 0
        indicators = []
        for pattern in patterns:
            matches = pattern.findall(text)
            count += len(matches)
            indicators.extend(matches)
        return count, indicators
    
    def _has_negation(self, text: str) -> bool:
        """Check if text contains negation"""
        for pattern in self._negation_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _has_intensifier(self, text: str) -> bool:
        """Check if text contains intensifiers"""
        for pattern in self._intensifiers:
            if pattern.search(text):
                return True
        return False
    
    def _has_diminisher(self, text: str) -> bool:
        """Check if text contains diminishers"""
        for pattern in self._diminishers:
            if pattern.search(text):
                return True
        return False
    
    def _is_false_positive(self, text: str) -> bool:
        """Check if text contains false positive patterns"""
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _determine_intensity(
        self, 
        strong_count: int, 
        mild_count: int,
        has_intensifier: bool,
        has_diminisher: bool = False
    ) -> SentimentIntensity:
        """Determine sentiment intensity (ENHANCED)"""
        # Diminisher reduces intensity
        if has_diminisher:
            return SentimentIntensity.MILD
        # Strong indicators or intensifiers -> strong intensity
        elif strong_count > 0 or has_intensifier:
            return SentimentIntensity.STRONG
        # Only mild indicators -> mild intensity
        elif mild_count > 0:
            return SentimentIntensity.MILD
        else:
            return SentimentIntensity.MODERATE
    
    def _detect_financial_sentiment(self, text: str) -> Optional[FinancialSentiment]:
        """Detect financial-specific sentiment"""
        bullish_count = sum(1 for pattern in self._bullish_patterns if pattern.search(text))
        bearish_count = sum(1 for pattern in self._bearish_patterns if pattern.search(text))
        
        if bullish_count > bearish_count:
            return FinancialSentiment.BULLISH
        elif bearish_count > bullish_count:
            return FinancialSentiment.BEARISH
        elif bullish_count > 0 or bearish_count > 0:
            return FinancialSentiment.NEUTRAL
        else:
            return None
    
    def _calculate_confidence(
        self,
        polarity: SentimentPolarity,
        positive_score: int,
        negative_score: int,
        has_intensifier: bool,
        financial_sentiment: Optional[FinancialSentiment]
    ) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(
            polarity, positive_score, negative_score, 
            has_intensifier, False, financial_sentiment, positive_score + negative_score
        )
    
    def _calculate_confidence_enhanced(
        self,
        polarity: SentimentPolarity,
        positive_score: int,
        negative_score: int,
        has_intensifier: bool,
        has_diminisher: bool,
        financial_sentiment: Optional[FinancialSentiment],
        indicator_count: int
    ) -> float:
        """
        Calculate confidence for sentiment detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-3 features.
        """
        confidence = 0.65  # Base confidence
        
        # Boost for clear sentiment dominance
        total_score = positive_score + negative_score
        if total_score > 0:
            sentiment_ratio = max(positive_score, negative_score) / total_score
            confidence += sentiment_ratio * 0.18
        
        # Boost for multiple indicators
        if indicator_count >= 2:
            confidence += 0.06
        if indicator_count >= 3:
            confidence += 0.05
        if indicator_count >= 4:
            confidence += 0.04
        
        # Boost for intensifiers (stronger signal)
        if has_intensifier:
            confidence += 0.06
        
        # Penalty for diminishers (weaker signal)
        if has_diminisher:
            confidence -= 0.03
        
        # Boost for financial sentiment alignment
        if financial_sentiment:
            if (polarity == SentimentPolarity.POSITIVE and 
                financial_sentiment == FinancialSentiment.BULLISH):
                confidence += 0.10
            elif (polarity == SentimentPolarity.NEGATIVE and 
                  financial_sentiment == FinancialSentiment.BEARISH):
                confidence += 0.10
            else:
                # Misalignment penalty
                confidence -= 0.02
        
        return min(1.0, max(0.5, confidence))
    
    def has_sentiment(self, text: str) -> bool:
        """
        Quick check if text contains sentiment.
        
        Returns:
            True if sentiment detected, False otherwise
        """
        if not text:
            return False
        
        sentiment = self.detect_sentiment(text)
        return sentiment is not None

