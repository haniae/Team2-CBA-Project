"""
Comparative language analyzer for detecting and parsing comparative statements.

Handles:
- Basic comparatives (better, worse, higher, lower)
- Superlatives (best, worst, highest, lowest, most, least)
- Relative magnitude (twice as much, 50% more)
- Directional performance (outperforming, lagging behind)
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class ComparisonType(Enum):
    """Types of comparisons"""
    BINARY = "binary"          # A vs B (two entities)
    SUPERLATIVE = "superlative"  # Top N, best M (ranked list)
    THRESHOLD = "threshold"    # Above/below a value
    IMPLICIT = "implicit"      # "Which is better?" (entities from context)


class ComparisonDirection(Enum):
    """Direction of comparison"""
    HIGHER = "higher"    # More, better, higher, stronger
    LOWER = "lower"      # Less, worse, lower, weaker
    NEUTRAL = "neutral"  # Equal, same, similar


@dataclass
class ComparisonIntent:
    """
    Represents a detected comparison in a query.
    """
    type: ComparisonType
    direction: ComparisonDirection
    dimension: Optional[str]  # What's being compared (revenue, profit, etc.)
    entities: List[str]       # Companies/tickers being compared
    magnitude: Optional[str]  # "twice", "50%", "significantly", etc.
    confidence: float         # How confident we are (0.0 to 1.0)
    
    def __repr__(self):
        return (f"ComparisonIntent(type={self.type.value}, "
                f"direction={self.direction.value}, "
                f"dimension={self.dimension}, "
                f"entities={self.entities}, "
                f"magnitude={self.magnitude}, "
                f"confidence={self.confidence:.2f})")


class ComparativeAnalyzer:
    """
    Detect and parse comparative language in financial queries.
    """
    
    # Basic comparative patterns (EXPANDED)
    COMPARATIVE_PATTERNS = {
        'positive': [
            r'\b(better|superior|stronger|greater|higher|larger|bigger|faster|more)\b',
            r'\b(improved|improving|enhanced|increased|increasing|rising|growing)\b',
            # Informal/colloquial
            r'\b(hotter|cooler|nicer|prettier|sweeter|tougher|richer|healthier)\b',
            # Intensified
            r'\b(much better|far better|way better|even better|still better)\b',
            r'\b(a lot more|significantly more|substantially more|considerably more)\b',
            # Performance-focused
            r'\b(more successful|more efficient|more effective|more competitive)\b',
            r'\b(more attractive|more appealing|more promising|more favorable)\b',
        ],
        'negative': [
            r'\b(worse|inferior|weaker|lesser|lower|smaller|slower|less)\b',
            r'\b(declined|declining|decreased|decreasing|falling|shrinking)\b',
            # Informal/colloquial
            r'\b(uglier|weaker|poorer|sicker|rougher|cheaper)\b',
            # Intensified
            r'\b(much worse|far worse|way worse|even worse|still worse)\b',
            r'\b(a lot less|significantly less|substantially less|considerably less)\b',
            # Performance-focused
            r'\b(less successful|less efficient|less effective|less competitive)\b',
            r'\b(less attractive|less appealing|less promising|less favorable)\b',
        ],
        'superlative_positive': [
            r'\b(best|top|highest|largest|biggest|fastest|most|strongest|greatest)\b',
            r'\b(leading|dominant|premier|superior|foremost|primary)\b',
            # Informal/colloquial
            r'\b(hottest|coolest|nicest|prettiest|sweetest|toughest|richest)\b',
            # Top N patterns
            r'\b(top\s+\d+|top\s+\w+|number\s+one|#1|no\.\s*1)\b',
            # Excellence markers
            r'\b(finest|ultimate|supreme|optimal|ideal|perfect|champion)\b',
        ],
        'superlative_negative': [
            r'\b(worst|bottom|lowest|smallest|slowest|least|weakest)\b',
            r'\b(lagging|trailing|inferior|poorest)\b',
            # Informal/colloquial
            r'\b(ugliest|weakest|sickest|roughest|cheapest)\b',
            # Bottom N patterns
            r'\b(bottom\s+\d+|last\s+place|dead\s+last)\b',
        ],
    }
    
    # Directional performance patterns (EXPANDED)
    PERFORMANCE_PATTERNS = {
        'outperforming': [
            r'\b(outperform(?:s|ing|ed)?|beat(?:s|ing)?|exceed(?:s|ing|ed)?)\b',
            r'\b(ahead\s+of|leading|dominating|crushing|destroying)\b',
            # Market performance
            r'\b(outpacing|surpassing|overtaking|topping)\b',
            # Competitive advantage
            r'\b(winning\s+against|beating\s+out|pulling\s+ahead)\b',
            r'\b(leaving\s+behind|running\s+circles\s+around)\b',
        ],
        'underperforming': [
            r'\b(underperform(?:s|ing|ed)?|lag(?:s|ging|ged)?(?:\s+behind)?)\b',
            r'\b(behind|trailing|losing\s+to|falling\s+behind)\b',
            # Market performance
            r'\b(missing\s+the\s+mark|coming\s+up\s+short|disappointing)\b',
            # Competitive disadvantage
            r'\b(struggling\s+against|getting\s+beat|falling\s+back)\b',
            r"\b(left\s+in\s+the\s+dust|can't\s+keep\s+up|cannot\s+keep\s+up)\b",
        ],
    }
    
    # Relative magnitude patterns (EXPANDED)
    MAGNITUDE_PATTERNS = [
        r'\b(twice|double|triple|quadruple|quintuple|half|quarter|third)\s+(?:as\s+)?(?:much|many|high|low|large|small)?\b',
        r'\b(\d+(?:\.\d+)?)[xX×]\s+(?:more|less|higher|lower|as\s+(?:much|many))?\b',
        r'\b(\d+(?:\.\d+)?)%\s+(?:more|less|higher|lower|better|worse|greater|smaller)\b',
        # Qualitative magnitude
        r'\b(significantly|substantially|considerably|marginally|slightly|barely)\s+(?:more|less|higher|lower|better|worse)\b',
        r'\b(much|far|way|even|still|a\s+lot|a\s+bit)\s+(?:more|less|higher|lower|better|worse)\b',
        # Order of magnitude
        r'\b(order\s+of\s+magnitude|orders\s+of\s+magnitude)\s+(?:more|less|higher|lower)\b',
        # Percentage ranges
        r'\b(about|around|approximately|roughly|nearly)\s+\d+%\s+(?:more|less|higher|lower)\b',
        # Fractional
        r'\b(one\s+half|one\s+third|one\s+quarter|two\s+thirds)\s+(?:as\s+)?(?:much|many)?\b',
        # Comparative degree
        r'\b(dramatically|vastly|enormously|tremendously|immensely)\s+(?:more|less|higher|lower|better|worse)\b',
        r'\b(moderately|somewhat|relatively|comparatively)\s+(?:more|less|higher|lower|better|worse)\b',
    ]
    
    # Comparison connector patterns (vs, versus, compared to, etc.)
    CONNECTOR_PATTERNS = [
        r'\b(?:vs\.?|versus|compared\s+(?:to|with|against)|against|relative\s+to)\b',
        r'\b(?:than|over|vis-a-vis)\b',
    ]
    
    # Question patterns for comparisons
    QUESTION_PATTERNS = [
        r'\b(?:which|who)\s+(?:is|are|has|have)\s+(?:more|less|better|worse|higher|lower)\b',
        r'\b(?:which|who)\s+(?:is|are)\s+(?:the\s+)?(?:most|least|best|worst)\b',
        r'\bwhat(?:\'s|\s+is)\s+(?:better|worse|higher|lower)\b',
        r'\b(?:is|are)\s+[\w\s]+?\s+(?:better|worse|higher|lower)\s+than\b',
        r'\b(?:does|do)\s+[\w\s]+?\s+have\s+(?:more|less|twice|double|triple|half)\b',
    ]
    
    # FALSE POSITIVE PREVENTION
    # Words/phrases that look comparative but aren't in financial context
    FALSE_POSITIVE_PATTERNS = {
        # Time expressions (not comparisons)
        'before', 'after', 'later', 'earlier', 'previous', 'next', 'following',
        'prior', 'subsequent', 'former', 'latter',
        
        # Location/position (not comparisons)
        'above', 'below', 'under', 'over', 'beyond', 'within', 'inside', 'outside',
        
        # Degree/extent (not necessarily comparisons)
        'more information', 'more details', 'more data', 'more about',
        'less information', 'less detail', 'tell me more', 'show me more',
        
        # Common phrases that aren't comparisons
        'no more', 'no less', 'nothing more', 'nothing less',
        'more or less', 'sooner or later', 'higher up', 'lower down',
        
        # Quantity expressions (not comparisons)
        'a few more', 'some more', 'a bit more', 'one more',
    }
    
    def __init__(self):
        """Initialize the comparative analyzer"""
        # Pre-compile regex patterns for efficiency
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile all regex patterns"""
        compiled = {}
        
        # Compile comparative patterns
        for category, patterns in self.COMPARATIVE_PATTERNS.items():
            compiled[category] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile performance patterns
        for category, patterns in self.PERFORMANCE_PATTERNS.items():
            compiled[f'performance_{category}'] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile magnitude patterns
        compiled['magnitude'] = [re.compile(p, re.IGNORECASE) for p in self.MAGNITUDE_PATTERNS]
        
        # Compile connector patterns
        compiled['connector'] = [re.compile(p, re.IGNORECASE) for p in self.CONNECTOR_PATTERNS]
        
        # Compile question patterns
        compiled['question'] = [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS]
        
        return compiled
    
    def detect_comparison(self, text: str, entities: Optional[List[str]] = None) -> Optional[ComparisonIntent]:
        """
        Detect if text contains a comparison and extract details.
        
        Args:
            text: The query text to analyze
            entities: Optional list of entities (companies/tickers) mentioned
            
        Returns:
            ComparisonIntent if comparison detected, None otherwise
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # TIGHTENING: Check for false positives first
        if self._is_false_positive(text_lower):
            return None
        
        # Detect comparison type and direction
        comparison_type = self._detect_comparison_type(text_lower, entities)
        if not comparison_type:
            return None
        
        direction = self._detect_direction(text_lower)
        dimension = self.extract_comparison_dimension(text_lower)
        magnitude = self._extract_magnitude(text_lower)
        
        # ENHANCED: Context-aware confidence scoring
        confidence = self._calculate_confidence_enhanced(
            text_lower, 
            comparison_type, 
            direction, 
            dimension,
            entities
        )
        
        return ComparisonIntent(
            type=comparison_type,
            direction=direction,
            dimension=dimension,
            entities=entities or [],
            magnitude=magnitude,
            confidence=confidence
        )
    
    def _detect_comparison_type(self, text: str, entities: Optional[List[str]]) -> Optional[ComparisonType]:
        """Detect the type of comparison"""
        # Check for superlative patterns FIRST (best, worst, top N, etc.)
        for pattern in (self._compiled_patterns['superlative_positive'] + 
                       self._compiled_patterns['superlative_negative']):
            if pattern.search(text):
                return ComparisonType.SUPERLATIVE
        
        # Check for comparative questions SECOND (which is better, who has more, etc.)
        # These need to be checked before basic comparatives to properly classify single-entity comparisons
        for pattern in self._compiled_patterns['question']:
            if pattern.search(text):
                if entities and len(entities) >= 2:
                    return ComparisonType.BINARY
                elif entities and len(entities) == 1:
                    # Single entity with question pattern = threshold comparison
                    return ComparisonType.THRESHOLD
                else:
                    return ComparisonType.IMPLICIT
        
        # Check for binary comparison connectors (A vs B)
        for pattern in self._compiled_patterns['connector']:
            if pattern.search(text):
                if entities and len(entities) >= 2:
                    return ComparisonType.BINARY
                # Connector present but not enough entities - might be implicit
                return ComparisonType.IMPLICIT
        
        # Check for basic comparative patterns (better, worse, higher, lower)
        for category in ['positive', 'negative']:
            for pattern in self._compiled_patterns[category]:
                if pattern.search(text):
                    if entities and len(entities) >= 2:
                        return ComparisonType.BINARY
                    elif entities and len(entities) == 1:
                        # Check if comparing to a standard/average/threshold
                        if re.search(r'\b(than|average|benchmark|standard|norm)\b', text, re.IGNORECASE):
                            return ComparisonType.THRESHOLD
                        else:
                            return ComparisonType.THRESHOLD  # Single entity comparisons are typically threshold
                    else:
                        return ComparisonType.IMPLICIT
        
        # Check for performance patterns
        for category in ['performance_outperforming', 'performance_underperforming']:
            for pattern in self._compiled_patterns[category]:
                if pattern.search(text):
                    return ComparisonType.BINARY if entities and len(entities) >= 2 else ComparisonType.IMPLICIT
        
        return None
    
    def _detect_direction(self, text: str) -> ComparisonDirection:
        """Detect the direction of comparison (higher/lower/neutral)"""
        # Check for positive direction
        for pattern_list in [self._compiled_patterns['positive'], 
                            self._compiled_patterns['superlative_positive'],
                            self._compiled_patterns['performance_outperforming']]:
            for pattern in pattern_list:
                if pattern.search(text):
                    return ComparisonDirection.HIGHER
        
        # Check for negative direction
        for pattern_list in [self._compiled_patterns['negative'],
                            self._compiled_patterns['superlative_negative'],
                            self._compiled_patterns['performance_underperforming']]:
            for pattern in pattern_list:
                if pattern.search(text):
                    return ComparisonDirection.LOWER
        
        # Check for neutral/equality patterns
        if re.search(r'\b(same|equal|similar|comparable|on\s+par)\b', text, re.IGNORECASE):
            return ComparisonDirection.NEUTRAL
        
        # Default to higher if we can't determine
        return ComparisonDirection.HIGHER
    
    def extract_comparison_dimension(self, text: str) -> Optional[str]:
        """
        Extract what dimension is being compared (revenue, profit, margins, etc.)
        
        Examples:
        "Which has higher margins?" → 'margins'
        "Who is more profitable?" → 'profitability'
        "Compare their revenue" → 'revenue'
        """
        # Financial metric patterns (MASSIVELY EXPANDED)
        metric_patterns = {
            # Revenue/Sales
            'revenue': r'\b(revenue|sales|income|earnings|topline|top\s+line|gross\s+sales|net\s+sales|total\s+revenue)\b',
            # Profitability
            'profit': r'\b(profit|profitability|profitable|bottom\s+line|net\s+income|net\s+profit|earnings|income)\b',
            'margin': r'\b(margins?|profitability|profit\s+margins?|operating\s+margin|gross\s+margin|net\s+margin|ebitda\s+margin)\b',
            # Growth
            'growth': r'\b(growth|growing|grow|increase|expansion|faster|accelerating|compounding|cagr|yoy\s+growth|revenue\s+growth|earnings\s+growth)\b',
            # Valuation
            'valuation': r'\b(valuation|valued|value|p/e|pe\s+ratio|price|multiple|multiples|enterprise\s+value|ev|market\s+value)\b',
            # Size/Scale
            'size': r'\b(size|large|larger|largest|small|smaller|smallest|big|bigger|biggest|market\s+cap|capitalization|scale)\b',
            # Performance/Returns
            'performance': r'\b(performance|performing|perform|returns?|stock\s+price|share\s+price|total\s+return|shareholder\s+return)\b',
            # Cash Flow
            'cash_flow': r'\b(cash\s+flow|cash|liquidity|fcf|free\s+cash\s+flow|operating\s+cash\s+flow|ocf|cash\s+generation)\b',
            # Debt/Leverage
            'debt': r'\b(debt|leverage|leveraged|liabilities|debt\s+to\s+equity|debt\s+ratio|total\s+debt|net\s+debt|borrowing)\b',
            # Efficiency/Productivity
            'efficiency': r'\b(efficiency|efficient|productivity|productive|turnover|asset\s+turnover|inventory\s+turnover|operating\s+efficiency)\b',
            # Dividends/Payouts
            'dividend': r'\b(dividend|dividends|payout|yield|dividend\s+yield|dividend\s+per\s+share|distribution)\b',
            # Earnings Per Share
            'eps': r'\b(eps|earnings\s+per\s+share|earnings\s+per\s+share)\b',
            # Return Metrics
            'returns': r'\b(roe|roa|roic|return\s+on\s+equity|return\s+on\s+assets|return\s+on\s+invested\s+capital|returns)\b',
            # Balance Sheet
            'assets': r'\b(assets|total\s+assets|asset\s+base|balance\s+sheet\s+strength)\b',
            'equity': r'\b(equity|shareholders?\s+equity|book\s+value|tangible\s+book\s+value)\b',
            # Quality/Health
            'quality': r'\b(quality|health|financial\s+health|strength|strong|weak|solid|stable|stability)\b',
            # Risk
            'risk': r'\b(risk|risky|riskier|riskiest|volatile|volatility|beta|downside|uncertainty)\b',
            # Innovation/R&D
            'innovation': r'\b(innovation|innovative|r&d|research|development|technology|tech\s+spending)\b',
            # Market Position
            'market_position': r'\b(market\s+share|market\s+position|competitive\s+position|leadership|dominance|penetration)\b',
            # Operational
            'operational': r'\b(operational|operations|operating\s+income|ebit|ebitda|operating\s+profit)\b',
            # Momentum
            'momentum': r'\b(momentum|trending|trend|trajectory|direction|moving)\b',
            # Attractiveness
            'attractiveness': r'\b(attractive|attractiveness|appealing|compelling|interesting|opportunity)\b',
        }
        
        # Check each pattern
        for dimension, pattern in metric_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return dimension
        
        # If no specific dimension found, return None
        return None
    
    def _extract_magnitude(self, text: str) -> Optional[str]:
        """Extract relative magnitude if present"""
        # Check each magnitude pattern
        for pattern in self._compiled_patterns['magnitude']:
            match = pattern.search(text)
            if match:
                return match.group(0)
        
        # Additional check for simple magnitude words
        simple_magnitude = re.search(
            r'\b(twice|double|triple|half|significantly|substantially|considerably|marginally|slightly)\b',
            text,
            re.IGNORECASE
        )
        if simple_magnitude:
            return simple_magnitude.group(0)
        
        return None
    
    def _is_false_positive(self, text: str) -> bool:
        """
        Check if text contains false positive comparative patterns.
        
        Returns True if this is likely NOT a comparison despite having comparative words.
        """
        # Check for false positive phrases
        for fp_pattern in self.FALSE_POSITIVE_PATTERNS:
            if fp_pattern in text:
                return True
        
        # Check for informational requests (not comparisons)
        if re.search(r'\b(tell\s+me\s+more|show\s+me\s+more|more\s+(?:information|details|data)\s+(?:about|on))\b', text):
            return True
        
        # Check for time expressions that look comparative
        if re.search(r'\b(before|after)\s+(?:the|this|that|it)\b', text):
            return True
        
        return False
    
    def _calculate_confidence(
        self,
        text: str,
        comparison_type: ComparisonType,
        direction: ComparisonDirection,
        dimension: Optional[str]
    ) -> float:
        """Calculate confidence score for the detected comparison (legacy)"""
        confidence = 0.5  # Base confidence
        
        # Boost for explicit comparison type
        if comparison_type == ComparisonType.SUPERLATIVE:
            confidence += 0.2  # Superlatives are very clear
        elif comparison_type == ComparisonType.BINARY:
            confidence += 0.15  # Binary comparisons are clear
        
        # Boost for explicit dimension
        if dimension:
            confidence += 0.15
        
        # Boost for strong comparison words
        strong_patterns = [
            r'\bcompare\b', r'\bversus\b', r'\bvs\.?\b',
            r'\bbetter\b', r'\bworse\b', r'\bbest\b', r'\bworst\b',
        ]
        for pattern in strong_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                confidence += 0.1
                break
        
        # Cap at 1.0
        return min(1.0, confidence)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        comparison_type: ComparisonType,
        direction: ComparisonDirection,
        dimension: Optional[str],
        entities: Optional[List[str]] = None
    ) -> float:
        """
        Calculate confidence score with context awareness.
        
        Similar to spelling correction's context-aware scoring.
        """
        confidence = 0.5  # Base confidence
        
        # Boost for explicit comparison type
        if comparison_type == ComparisonType.SUPERLATIVE:
            confidence += 0.2  # Superlatives are very clear
        elif comparison_type == ComparisonType.BINARY:
            confidence += 0.15  # Binary comparisons are clear
        elif comparison_type == ComparisonType.THRESHOLD:
            confidence += 0.10  # Threshold comparisons are moderately clear
        
        # Boost for explicit dimension
        if dimension:
            confidence += 0.15
        
        # Boost for multiple entities (makes comparison more likely)
        if entities and len(entities) >= 2:
            confidence += 0.10
        
        # Boost for strong comparison words
        strong_patterns = [
            r'\bcompare\b', r'\bversus\b', r'\bvs\.?\b',
            r'\bbetter\b', r'\bworse\b', r'\bbest\b', r'\bworst\b',
            r'\bhigher\b', r'\blower\b', r'\bmore\b', r'\bless\b',
        ]
        for pattern in strong_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                confidence += 0.08
                break
        
        # Boost for question format (very clear intent)
        if re.search(r'\b(which|who|what).*\?(.*(?:better|worse|higher|lower|more|less|best|worst))?', text):
            confidence += 0.10
        
        # Boost for explicit financial context
        financial_keywords = [
            'revenue', 'profit', 'margin', 'earnings', 'growth', 'valuation',
            'stock', 'company', 'investment', 'performance', 'return'
        ]
        if any(keyword in text for keyword in financial_keywords):
            confidence += 0.05
        
        # Penalty for ambiguous language
        if re.search(r'\b(maybe|perhaps|possibly|might|could)\b', text):
            confidence -= 0.05
        
        # Cap at 1.0
        return min(1.0, max(0.0, confidence))
    
    def is_comparative_query(self, text: str) -> bool:
        """
        Quick check if text is a comparative query.
        
        Returns:
            True if text appears to be a comparison, False otherwise
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check all comparative pattern categories
        for category in ['positive', 'negative', 'superlative_positive', 'superlative_negative']:
            for pattern in self._compiled_patterns[category]:
                if pattern.search(text_lower):
                    return True
        
        # Check performance patterns
        for category in ['performance_outperforming', 'performance_underperforming']:
            for pattern in self._compiled_patterns[category]:
                if pattern.search(text_lower):
                    return True
        
        # Check connector patterns
        for pattern in self._compiled_patterns['connector']:
            if pattern.search(text_lower):
                return True
        
        # Check question patterns
        for pattern in self._compiled_patterns['question']:
            if pattern.search(text_lower):
                return True
        
        return False

