"""
Trend direction language analyzer for detecting and parsing trend-related queries.

Handles:
- Growth/Improvement (improving, increasing, rising, growing)
- Decline (declining, decreasing, falling, shrinking)
- Acceleration/Deceleration (speeding up, slowing down)
- Stability (stable, steady, flat, consistent)
- Volatility (volatile, fluctuating, erratic)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class TrendDirection(Enum):
    """Direction of trend movement"""
    POSITIVE = "positive"      # Improving, increasing, rising
    NEGATIVE = "negative"      # Declining, decreasing, falling
    STABLE = "stable"          # Flat, steady, consistent
    VOLATILE = "volatile"      # Fluctuating, erratic, variable
    NEUTRAL = "neutral"        # No clear direction


class TrendVelocity(Enum):
    """Rate of change in trend"""
    ACCELERATING = "accelerating"    # Speeding up, faster
    DECELERATING = "decelerating"    # Slowing down, slower
    CONSTANT = "constant"            # Steady rate
    UNKNOWN = "unknown"              # Not specified


@dataclass
class TrendIntent:
    """
    Represents a detected trend query.
    """
    direction: TrendDirection
    velocity: TrendVelocity
    dimension: Optional[str]  # What's trending (revenue, profit, etc.)
    magnitude: Optional[str]  # How much (dramatically, slightly, etc.)
    timeframe: Optional[str]  # When (recently, historically, etc.)
    confidence: float         # Confidence score (0.0 to 1.0)
    
    def __repr__(self):
        return (f"TrendIntent(direction={self.direction.value}, "
                f"velocity={self.velocity.value}, "
                f"dimension={self.dimension}, "
                f"magnitude={self.magnitude}, "
                f"timeframe={self.timeframe}, "
                f"confidence={self.confidence:.2f})")


class TrendAnalyzer:
    """
    Detect and parse trend direction language in financial queries.
    """
    
    # Growth/Improvement patterns (POSITIVE direction) - MASSIVELY EXPANDED
    DIRECTION_PATTERNS = {
        'positive': [
            # Basic growth
            r'\b(improv(?:e|es|ed|ing)|increas(?:e|es|ed|ing)|ris(?:e|es|ing|en)|climb(?:s|ed|ing)?)\b',
            r'\b(grow(?:s|n|ing)?|gain(?:s|ed|ing)?|strengthen(?:s|ed|ing)?|boost(?:s|ed|ing)?)\b',
            # Directional movement
            r'\b(up|upward|uptrend|uptick|ascending|advancing|northward)\b',
            r'\b(better|improving|getting\s+better|becoming\s+stronger|turning\s+around)\b',
            # Expansion
            r'\b(expand(?:s|ed|ing)?|expansion|enlarg(?:e|es|ed|ing)|swell(?:s|ed|ing)?)\b',
            # Recovery
            r'\b(recover(?:s|ed|ing)?|recovery|rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)\s+back)\b',
            r'\b(resurg(?:e|es|ed|ing)|revival|comeback|turnaround|picking\s+up)\b',
            # Enhancement
            r'\b(enhanc(?:e|es|ed|ing)|upgrade(?:s|d|ing)?|elevat(?:e|es|ed|ing)|amplify(?:ing)?)\b',
            # Momentum
            r'\b(surging|soaring|rocketing|skyrocketing|exploding)\b',
            r'\b(bullish|optimistic|positive\s+momentum|upside\s+momentum)\b',
            # Progression
            r'\b(progress(?:ing)?|advancing|moving\s+forward|heading\s+up)\b',
            r'\b(on\s+the\s+rise|on\s+an\s+upswing|trending\s+up|trending\s+upward)\b',
            # NEW: Acceleration indicators
            r'\b(taking\s+off|taking\s+flight|gaining\s+traction|gaining\s+steam)\b',
            r'\b(picking\s+up\s+speed|gathering\s+momentum|building\s+momentum)\b',
            # NEW: Strength indicators
            r'\b(strengthening|robust|vigorous|healthy|thriving|flourishing)\b',
            r'\b(booming|blooming|blossoming|burgeoning)\b',
            # NEW: Positive trajectory
            r'\b(upward\s+trajectory|positive\s+trajectory|favorable\s+trend)\b',
            r'\b(heading\s+in\s+the\s+right\s+direction|going\s+in\s+the\s+right\s+direction)\b',
            # NEW: Outperformance trends
            r'\b(outpacing|outperforming|exceeding\s+expectations|beating\s+forecasts)\b',
            r'\b(breaking\s+out|breakout|breaking\s+through|pushing\s+higher)\b',
        ],
        'negative': [
            # Basic decline
            r'\b(declin(?:e|es|ed|ing)|decreas(?:e|es|ed|ing)|fall(?:s|ing|en)?|drop(?:s|ped|ping)?)\b',
            r'\b(shrink(?:s|ing)?|weaken(?:s|ed|ing)?|deteriorat(?:e|es|ed|ing)|worsen(?:s|ed|ing)?)\b',
            # Directional movement
            r'\b(down|downward|downtrend|downtick|descending|retreating|southward)\b',
            r'\b(worse|worsening|getting\s+worse|becoming\s+weaker|turning\s+sour)\b',
            # Contraction
            r'\b(contract(?:s|ed|ing)?|contraction|reduc(?:e|es|ed|ing)|dwindl(?:e|es|ed|ing))\b',
            # Collapse
            r'\b(collaps(?:e|es|ed|ing)|crash(?:es|ed|ing)?|plummet(?:s|ed|ing)?|plunge(?:s|d|ing)?)\b',
            r'\b(tank(?:s|ed|ing)?|crater(?:s|ed|ing)?|nosediv(?:e|es|ed|ing)|freefalling)\b',
            # Erosion
            r'\b(erod(?:e|es|ed|ing)|erosion|degrad(?:e|es|ed|ing)|slip(?:s|ped|ping)?)\b',
            # Pressure
            r'\b(under\s+pressure|suffering|struggling|hemorrhaging|bleeding)\b',
            r'\b(bearish|pessimistic|negative\s+momentum|downside\s+pressure)\b',
            # Regression
            r'\b(regress(?:ing)?|sliding|backsliding|losing\s+ground|going\s+backwards)\b',
            r'\b(on\s+the\s+decline|on\s+a\s+downswing|trending\s+down|trending\s+downward)\b',
            # NEW: Severe decline
            r'\b(diving|tumbling|spiraling|spiraling\s+down|in\s+freefall)\b',
            r'\b(melting\s+down|meltdown|imploding|disintegrating)\b',
            # NEW: Weakness indicators
            r'\b(weakening|softening|sagging|wilting|fading)\b',
            r'\b(flagging|faltering|stumbling|slumping)\b',
            # NEW: Negative trajectory
            r'\b(downward\s+trajectory|negative\s+trajectory|unfavorable\s+trend)\b',
            r'\b(heading\s+in\s+the\s+wrong\s+direction|going\s+in\s+the\s+wrong\s+direction)\b',
            # NEW: Underperformance trends
            r'\b(underperforming|missing\s+expectations|missing\s+forecasts|disappointing)\b',
            r'\b(breaking\s+down|breakdown|losing\s+altitude|sinking)\b',
            # NEW: Compression/squeeze
            r'\b(compressing|compression|squeezed|squeezing|tightening)\b',
            r'\b(under\s+strain|strained|stressed)\b',
        ],
        'stable': [
            # Stability
            r'\b(stable|stability|steady|steadily|flat|plateau|plateauing)\b',
            r'\b(consistent(?:ly)?|constant(?:ly)?|unchang(?:ed|ing)|maintain(?:s|ed|ing)?)\b',
            # Level
            r'\b(level|leveling\s+off|holding\s+steady|staying\s+flat|staying\s+constant)\b',
            r'\b(static|stagnant|stagnating|stagnation)\b',
            # Equilibrium
            r'\b(equilibrium|balanced|in\s+balance|holding\s+pattern)\b',
            r'\b(sideways|range-bound|rangebound|consolidating|consolidation)\b',
            # Predictable
            r'\b(predictable|regular|uniform|even)\b',
            # NEW: Holding patterns
            r'\b(holding|holding\s+up|holding\s+firm|staying\s+put)\b',
            r'\b(treading\s+water|marking\s+time|at\s+a\s+standstill)\b',
            # NEW: Stability language
            r'\b(stabiliz(?:e|ed|ing)|anchored|entrenched|settled)\b',
            r'\b(no\s+change|little\s+change|minimal\s+change)\b',
            # NEW: Neutral zone
            r'\b(neutral|neither\s+up\s+nor\s+down|middling|average)\b',
        ],
        'volatile': [
            # Volatility
            r'\b(volatile|volatility|fluctuat(?:e|es|ed|ing)|variable|varying)\b',
            r'\b(erratic|unpredictable|inconsistent|irregular|choppy)\b',
            # Swinging
            r'\b(swing(?:s|ing)?|oscillat(?:e|es|ed|ing)|waver(?:s|ed|ing)?)\b',
            r'\b(unstable|turbulent|chaotic|wild|all\s+over\s+the\s+place)\b',
            # Unpredictability
            r'\b(uncertain|unreliable|patchy|uneven|jumpy)\b',
            r'\b(whipsaw(?:ing)?|yo-yoing|bouncing\s+around)\b',
            # NEW: High variance
            r'\b(high\s+variance|wide\s+swings?|large\s+fluctuations?)\b',
            r'\b(up\s+and\s+down|zigzag(?:ging)?|rollercoaster)\b',
            # NEW: Instability
            r'\b(shaky|shaking|trembling|jittery|nervous)\b',
            r'\b(all\s+over\s+the\s+map|hit\s+or\s+miss|touch\s+and\s+go)\b',
        ],
    }
    
    # Velocity patterns (ACCELERATION/DECELERATION) - EXPANDED
    VELOCITY_PATTERNS = {
        'accelerating': [
            # Speeding up
            r'\b(accelerat(?:e|es|ed|ing)|speed(?:s|ed|ing)?\s+up|faster|quicken(?:s|ed|ing)?)\b',
            r'\b(rapid(?:ly)?|swift(?:ly)?|sharp(?:ly)?|steep(?:ly)?)\b',
            # Gaining momentum
            r'\b(gaining\s+(?:speed|momentum)|picking\s+up\s+(?:speed|pace)|ramping\s+up)\b',
            r'\b(surging|surg(?:e|es|ed|ing)|soaring|skyrocketing)\b',
            # NEW: Intensifying
            r'\b(intensify(?:ing)?|intensifying|heating\s+up|warming\s+up)\b',
            r'\b(building|building\s+speed|gathering\s+pace)\b',
            # NEW: Explosive growth
            r'\b(exponential(?:ly)?|explosive|exploding|erupting)\b',
            r'\b(going\s+parabolic|parabolic|hockey\s+stick)\b',
        ],
        'decelerating': [
            # Slowing down
            r'\b(decelerat(?:e|es|ed|ing)|slow(?:s|ed|ing)?\s+down|slower|taper(?:s|ed|ing)?\s+off)\b',
            r'\b(gradual(?:ly)?|moderate(?:ly)?|temper(?:s|ed|ing)?)\b',
            # Losing momentum
            r'\b(losing\s+(?:speed|momentum)|cooling\s+off|easing)\b',
            r'\b(leveling\s+off|flattening)\b',
            # NEW: Moderating
            r'\b(moderat(?:e|es|ed|ing)|normaliz(?:e|es|ed|ing)|settling\s+down)\b',
            r'\b(losing\s+steam|running\s+out\s+of\s+steam|fizzling)\b',
            # NEW: Weakening pace
            r'\b(petering\s+out|winding\s+down|cooling\s+down)\b',
            r'\b(decaying|fading\s+out|dying\s+down)\b',
        ],
    }
    
    # Magnitude patterns (intensity of trend)
    MAGNITUDE_PATTERNS = [
        # Strong/dramatic
        r'\b(dramatically|drastically|significantly|substantially|considerably|massively|enormously)\b',
        r'\b(sharply|steeply|rapidly|swiftly|quickly|fast)\b',
        # Moderate
        r'\b(moderately|noticeably|measurably|appreciably)\b',
        # Weak/slight
        r'\b(slightly|marginally|barely|minimally|incrementally)\b',
        r'\b(gradually|slowly|gently)\b',
    ]
    
    # Timeframe patterns (when the trend is happening) - EXPANDED
    TIMEFRAME_PATTERNS = [
        r'\b(recent(?:ly)?|latest|current(?:ly)?|now|today|this\s+(?:year|quarter|month|week))\b',
        r'\b(historical(?:ly)?|past|previous(?:ly)?|last\s+(?:year|quarter|few\s+years|decade))\b',
        r'\b(ongoing|continuing|persistent(?:ly)?|sustained|continuous(?:ly)?)\b',
        r'\b(short-term|near-term|long-term|over\s+time|through\s+time)\b',
        # NEW: Specific timeframes
        r'\b(ytd|year\s+to\s+date|qtd|quarter\s+to\s+date)\b',
        r'\b(in\s+the\s+past|in\s+recent\s+(?:weeks|months|years))\b',
        r'\b(for\s+the\s+past|over\s+the\s+past|during\s+the\s+past)\b',
        r'\b(lately|as\s+of\s+late|of\s+late)\b',
    ]
    
    # FALSE POSITIVE PREVENTION
    # Patterns that look like trends but aren't
    FALSE_POSITIVE_PATTERNS = {
        # Static descriptions (not trends)
        'is high', 'is low', 'is good', 'is bad',
        'was high', 'was low', 'was good', 'was bad',
        
        # Comparisons (not trends)
        'better than', 'worse than', 'higher than', 'lower than',
        'more than', 'less than',
        
        # Questions about current state (not trend)
        'what is', 'what are', 'how much', 'how many',
        
        # Conditional (not trend assertion)
        'if it improves', 'if it increases', 'when it rises',
        'should it grow', 'could it decline',
    }
    
    def __init__(self):
        """Initialize the trend analyzer"""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile all regex patterns for efficiency"""
        compiled = {}
        
        # Compile direction patterns
        for direction, patterns in self.DIRECTION_PATTERNS.items():
            compiled[f'direction_{direction}'] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile velocity patterns
        for velocity, patterns in self.VELOCITY_PATTERNS.items():
            compiled[f'velocity_{velocity}'] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile magnitude patterns
        compiled['magnitude'] = [re.compile(p, re.IGNORECASE) for p in self.MAGNITUDE_PATTERNS]
        
        # Compile timeframe patterns
        compiled['timeframe'] = [re.compile(p, re.IGNORECASE) for p in self.TIMEFRAME_PATTERNS]
        
        return compiled
    
    def detect_trend(self, text: str, dimension: Optional[str] = None) -> Optional[TrendIntent]:
        """
        Detect if text contains a trend direction query.
        
        Args:
            text: The query text to analyze
            dimension: Optional dimension hint (revenue, profit, etc.)
            
        Returns:
            TrendIntent if trend detected, None otherwise
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # TIGHTENING: Check for false positives first
        if self._is_false_positive(text_lower):
            return None
        
        # Detect velocity FIRST (to avoid false detection as direction)
        # "accelerating" should be detected as velocity, not just positive direction
        velocity = self._detect_velocity(text_lower)
        
        # Detect direction
        direction = self._detect_direction(text_lower)
        if direction == TrendDirection.NEUTRAL and velocity == TrendVelocity.UNKNOWN:
            return None  # No clear trend indicators
        
        # If we have velocity but no direction, infer direction from velocity
        if velocity == TrendVelocity.ACCELERATING and direction == TrendDirection.NEUTRAL:
            direction = TrendDirection.POSITIVE  # Accelerating implies positive
        elif velocity == TrendVelocity.DECELERATING and direction == TrendDirection.NEUTRAL:
            # Decelerating could be slowing growth (still positive) or declining
            # Check context for clues
            if re.search(r'\b(growth|revenue|profit|sales)\b', text_lower):
                direction = TrendDirection.POSITIVE  # Slowing growth
            else:
                direction = TrendDirection.NEGATIVE  # Generic deceleration
        
        # Extract dimension if not provided
        if not dimension:
            dimension = self._extract_dimension(text_lower)
        
        # Extract magnitude
        magnitude = self._extract_magnitude(text_lower)
        
        # Extract timeframe
        timeframe = self._extract_timeframe(text_lower)
        
        # Calculate confidence (enhanced)
        confidence = self._calculate_confidence_enhanced(
            text_lower,
            direction,
            velocity,
            dimension,
            magnitude,
            timeframe
        )
        
        return TrendIntent(
            direction=direction,
            velocity=velocity,
            dimension=dimension,
            magnitude=magnitude,
            timeframe=timeframe,
            confidence=confidence
        )
    
    def _detect_direction(self, text: str) -> TrendDirection:
        """Detect the direction of the trend"""
        # Check for positive direction
        for pattern in self._compiled_patterns['direction_positive']:
            if pattern.search(text):
                return TrendDirection.POSITIVE
        
        # Check for negative direction
        for pattern in self._compiled_patterns['direction_negative']:
            if pattern.search(text):
                return TrendDirection.NEGATIVE
        
        # Check for stability
        for pattern in self._compiled_patterns['direction_stable']:
            if pattern.search(text):
                return TrendDirection.STABLE
        
        # Check for volatility
        for pattern in self._compiled_patterns['direction_volatile']:
            if pattern.search(text):
                return TrendDirection.VOLATILE
        
        return TrendDirection.NEUTRAL
    
    def _detect_velocity(self, text: str) -> TrendVelocity:
        """Detect the velocity (rate of change) of the trend"""
        # Check for acceleration
        for pattern in self._compiled_patterns['velocity_accelerating']:
            if pattern.search(text):
                return TrendVelocity.ACCELERATING
        
        # Check for deceleration
        for pattern in self._compiled_patterns['velocity_decelerating']:
            if pattern.search(text):
                return TrendVelocity.DECELERATING
        
        # Check for constant velocity indicators
        if re.search(r'\b(steady|consistent(?:ly)?|constant(?:ly)?|regular(?:ly)?)\b', text, re.IGNORECASE):
            return TrendVelocity.CONSTANT
        
        return TrendVelocity.UNKNOWN
    
    def _extract_dimension(self, text: str) -> Optional[str]:
        """
        Extract what dimension is trending (revenue, profit, margins, etc.)
        
        Uses same patterns as comparative analyzer for consistency.
        """
        # Priority order matters: check most specific patterns first
        # Using list of tuples to preserve order - MASSIVELY EXPANDED
        metric_patterns = [
            # Stock price MUST come before valuation to avoid overlap
            ('stock_price', r'\b(stock\s+prices?|share\s+prices?|trading\s+prices?|stock)\b'),
            ('revenue', r'\b(revenues?|sales|topline|top\s+line|gross\s+sales)\b'),
            ('profit', r'\b(profits?|profitability|profitable|bottom\s+line|net\s+incomes?)\b'),
            ('margin', r'\b(margins?|profit\s+margins?|operating\s+margins?|gross\s+margins?|net\s+margins?)\b'),
            ('earnings', r'\b(earnings|eps|earnings\s+per\s+share)\b'),
            ('cash_flow', r'\b(cash\s+flows?|cash|liquidity|fcf|free\s+cash\s+flows?|operating\s+cash\s+flows?)\b'),
            ('debt', r'\b(debts?|leverage|liabilities|debt\s+levels?|borrowing)\b'),
            ('market_cap', r'\b(market\s+caps?|capitalization|market\s+value)\b'),
            ('dividend', r'\b(dividends?|payouts?|yields?|dividend\s+yields?)\b'),
            # NEW dimensions
            ('market_share', r'\b(market\s+shares?|share\s+of\s+market|penetration)\b'),
            ('operating_income', r'\b(operating\s+incomes?|ebit|ebitda|operating\s+profits?)\b'),
            ('costs', r'\b(costs?|expenses?|operating\s+expenses?|cost\s+structure)\b'),
            ('efficiency', r'\b(efficiency|productivity|operating\s+efficiency|efficiency\s+ratios?)\b'),
            ('returns', r'\b(returns?|roe|roa|roic|return\s+on\s+equity|return\s+on\s+assets)\b'),
            ('volume', r'\b(volumes?|trading\s+volumes?|transaction\s+volumes?)\b'),
            ('customer_base', r'\b(customers?|customer\s+bases?|user\s+bases?|subscribers?)\b'),
            ('growth', r'\b(growth|growth\s+rates?|expansion)\b'),
            # Valuation comes last to avoid matching "price" in "stock price"
            ('valuation', r'\b(valuations?|valued|value|p/e|pe\s+ratio|multiples?)\b'),
            ('performance', r'\b(performance|returns?|shareholder\s+returns?|total\s+returns?)\b'),
        ]
        
        # Check patterns in order (first match wins)
        for dimension, pattern in metric_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return dimension
        
        return None
    
    def _extract_magnitude(self, text: str) -> Optional[str]:
        """Extract magnitude/intensity of the trend"""
        for pattern in self._compiled_patterns['magnitude']:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None
    
    def _extract_timeframe(self, text: str) -> Optional[str]:
        """Extract timeframe when the trend is happening"""
        for pattern in self._compiled_patterns['timeframe']:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None
    
    def _calculate_confidence(
        self,
        text: str,
        direction: TrendDirection,
        velocity: TrendVelocity,
        dimension: Optional[str],
        magnitude: Optional[str],
        timeframe: Optional[str]
    ) -> float:
        """Calculate confidence score for trend detection"""
        confidence = 0.5  # Base confidence
        
        # Boost for clear direction
        if direction in [TrendDirection.POSITIVE, TrendDirection.NEGATIVE]:
            confidence += 0.15
        elif direction in [TrendDirection.STABLE, TrendDirection.VOLATILE]:
            confidence += 0.10
        
        # Boost for velocity information
        if velocity in [TrendVelocity.ACCELERATING, TrendVelocity.DECELERATING]:
            confidence += 0.10
        elif velocity == TrendVelocity.CONSTANT:
            confidence += 0.05
        
        # Boost for explicit dimension
        if dimension:
            confidence += 0.15
        
        # Boost for magnitude
        if magnitude:
            confidence += 0.05
        
        # Boost for timeframe
        if timeframe:
            confidence += 0.05
        
        # Boost for trend-related keywords
        if re.search(r'\b(trend|trending|trajectory|direction|pattern|movement)\b', text, re.IGNORECASE):
            confidence += 0.10
        
        return min(1.0, confidence)
    
    def _is_false_positive(self, text: str) -> bool:
        """
        Check if text contains false positive trend patterns.
        
        Returns True if this is likely NOT a trend despite having trend-like words.
        """
        # Check for false positive phrases
        for fp_pattern in self.FALSE_POSITIVE_PATTERNS:
            if fp_pattern in text:
                return True
        
        # Explicit comparisons aren't trends
        if re.search(r'\b(which|who)\s+(?:is|are|has|have)\s+(better|worse|higher|lower)\b', text):
            return True
        if re.search(r'\b(vs\.?|versus|compared\s+(?:to|with))\b', text):
            return True
        
        # Conditional questions aren't trend assertions
        if re.search(r'\b(if|when|should|could|would|might)\s+(?:it|they|revenue|profit|growth|margins?|earnings)\s+(improve|increase|decline|decrease)\b', text):
            return True
        # More general conditional patterns
        if re.search(r'^if\s+', text):  # Starts with "if"
            return True
        
        # Static state questions aren't trends
        if re.search(r'\b(?:what|how)\s+(?:is|are)\s+the\s+(?:current|latest)\b', text):
            return True
        
        return False
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        direction: TrendDirection,
        velocity: TrendVelocity,
        dimension: Optional[str],
        magnitude: Optional[str],
        timeframe: Optional[str]
    ) -> float:
        """
        Enhanced confidence scoring with context awareness.
        
        Similar to spelling and comparative context-aware scoring.
        """
        confidence = 0.50  # Base confidence
        
        # Boost for clear direction
        if direction in [TrendDirection.POSITIVE, TrendDirection.NEGATIVE]:
            confidence += 0.15  # Clear directional trend
        elif direction in [TrendDirection.STABLE, TrendDirection.VOLATILE]:
            confidence += 0.12  # Clear but different type
        
        # Boost for velocity information
        if velocity in [TrendVelocity.ACCELERATING, TrendVelocity.DECELERATING]:
            confidence += 0.12  # Velocity adds clarity
        elif velocity == TrendVelocity.CONSTANT:
            confidence += 0.06  # Some clarity
        
        # Boost for explicit dimension
        if dimension:
            confidence += 0.15  # Knowing what's trending is important
        
        # Boost for magnitude
        if magnitude:
            confidence += 0.06  # Intensity adds clarity
        
        # Boost for timeframe
        if timeframe:
            confidence += 0.06  # Temporal context adds clarity
        
        # Boost for trend-related keywords
        if re.search(r'\b(trend|trending|trajectory|direction|pattern|movement)\b', text, re.IGNORECASE):
            confidence += 0.10
        
        # Boost for question format asking about trends
        if re.search(r'\b(is|are|has|have)\s+\w+\s+(improving|declining|growing|shrinking)\b', text, re.IGNORECASE):
            confidence += 0.08
        
        # Boost for temporal context (over time, etc.)
        if re.search(r'\b(over\s+time|through\s+time|in\s+recent|lately)\b', text, re.IGNORECASE):
            confidence += 0.05
        
        # Penalty for ambiguous language
        if re.search(r'\b(maybe|perhaps|possibly|might|could)\b', text, re.IGNORECASE):
            confidence -= 0.05
        
        # Cap at 1.0
        return min(1.0, max(0.0, confidence))
    
    def is_trend_query(self, text: str) -> bool:
        """
        Quick check if text is a trend-related query.
        
        Returns:
            True if text appears to be about trends, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check all direction patterns
        for direction in ['positive', 'negative', 'stable', 'volatile']:
            for pattern in self._compiled_patterns[f'direction_{direction}']:
                if pattern.search(text_lower):
                    return True
        
        # Check velocity patterns
        for velocity in ['accelerating', 'decelerating']:
            for pattern in self._compiled_patterns[f'velocity_{velocity}']:
                if pattern.search(text_lower):
                    return True
        
        # Check for trend keywords
        if re.search(r'\b(trend|trending|trajectory|direction|pattern|movement)\b', text_lower):
            return True
        
        return False

