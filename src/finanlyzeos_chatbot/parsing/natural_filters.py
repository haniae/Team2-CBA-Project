"""
Natural language filter detection for financial queries.

Handles:
- Sector/Industry: "tech stocks", "financial sector", "energy companies"
- Quality: "high-quality", "blue-chip", "stable companies"
- Risk: "low-risk", "safe", "risky investments"
- Size: "large-cap", "small-cap", "mega-cap"
- Performance: "profitable", "growing", "undervalued"
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class FilterType(Enum):
    """Types of natural language filters"""
    SECTOR = "sector"           # Industry/sector filter
    QUALITY = "quality"         # Quality/stability filter
    RISK = "risk"              # Risk level filter
    SIZE = "size"              # Market cap size filter
    PERFORMANCE = "performance" # Performance filter
    VALUATION = "valuation"    # Valuation filter


@dataclass
class NaturalFilter:
    """
    Represents a natural language filter expression.
    """
    filter_type: FilterType
    value: str                  # The filter value (e.g., "tech", "high-quality")
    raw_text: str              # Original matched text
    confidence: float          # Confidence score (0.0 to 1.0)
    position: int              # Position in text
    
    def __repr__(self):
        return (f"NaturalFilter(type={self.filter_type.value}, "
                f"value='{self.value}', "
                f"confidence={self.confidence:.2f})")


class NaturalFilterDetector:
    """
    Detect natural language filter expressions.
    """
    
    # Sector/Industry patterns - MASSIVELY EXPANDED
    SECTOR_PATTERNS = {
        'Technology': [
            r'\b(tech|technology|software|hardware|semiconductor|internet)\b',
            r'\b(IT|information\s+technology)\b',
            r'\b(SaaS|cloud|cybersecurity)\b',
            # NEW: More tech variations
            r'\b(digital|online|web|mobile|app)\b',
            r'\b(AI|artificial\s+intelligence|machine\s+learning|ML)\b',
            r'\b(data|analytics|big\s+data)\b',
            r'\b(chip|chipmaker|silicon)\b',
        ],
        'Financials': [
            r'\b(financial|financials|banking|banks?|insurance)\b',
            r'\b(fintech|investment\s+(?:banking|firms?))\b',
            # NEW: More financial variations
            r'\b(brokerage|asset\s+management|wealth\s+management)\b',
            r'\b(credit\s+card|payment|payments)\b',
            r'\b(mortgage|lending|loan)\b',
        ],
        'Healthcare': [
            r'\b(healthcare|health\s+care|medical|pharma|pharmaceutical|biotech)\b',
            r'\b(hospital|drug)\b',
            # NEW: More healthcare variations
            r'\b(life\s+sciences|med\s+tech|medical\s+device)\b',
            r'\b(clinical|diagnostic|therapeutics?)\b',
            r'\b(health|wellness)\b',
        ],
        'Energy': [
            r'\b(energy|oil|gas|petroleum|renewable)\b',
            r'\b(utilities|power)\b',
            # NEW: More energy variations
            r'\b(solar|wind|clean\s+energy|green\s+energy)\b',
            r'\b(electric|electricity|nuclear)\b',
            r'\b(coal|natural\s+gas)\b',
        ],
        'Consumer': [
            r'\b(consumer|retail|e-commerce|ecommerce)\b',
            r'\b(consumer\s+(?:discretionary|staples|goods))\b',
            # NEW: More consumer variations
            r'\b(restaurant|food|beverage|apparel|clothing)\b',
            r'\b(luxury|fashion|beauty|cosmetics)\b',
            r'\b(automotive|auto|cars?)\b',
        ],
        'Industrial': [
            r'\b(industrial|manufacturing|aerospace|defense)\b',
            r'\b(machinery|equipment)\b',
            # NEW: More industrial variations
            r'\b(construction|engineering|infrastructure)\b',
            r'\b(logistics|transportation|shipping)\b',
            r'\b(materials|chemicals)\b',
        ],
        'Telecom': [
            r'\b(telecom|telecommunications?|wireless|broadband)\b',
            # NEW: More telecom variations
            r'\b(mobile|cellular|5G|network)\b',
            r'\b(cable|satellite|fiber)\b',
        ],
        'Real Estate': [
            r'\b(real\s+estate|REIT|property)\b',
            # NEW: More real estate variations
            r'\b(commercial\s+real\s+estate|residential|housing)\b',
            r'\b(landlord|developer)\b',
        ],
        # NEW: Additional sectors
        'Materials': [
            r'\b(materials|mining|metals|commodities)\b',
            r'\b(steel|copper|aluminum|gold|silver)\b',
        ],
        'Media': [
            r'\b(media|entertainment|streaming|content)\b',
            r'\b(broadcasting|publishing|gaming)\b',
        ],
    }
    
    # Quality level patterns - EXPANDED
    QUALITY_PATTERNS = {
        'high': [
            r'\b(high-quality|high\s+quality|quality|premium|top-tier|blue-chip|blue\s+chip)\b',
            r'\b(established|reputable|leading|best-in-class)\b',
            r'\b(stable|solid|strong|reliable|dependable)\b',
            # NEW: More high-quality variations
            r'\b(top|elite|premier|first-class|grade-A)\b',
            r'\b(trusted|credible|proven|well-established)\b',
            r'\b(robust|resilient|sound|healthy)\b',
            r'\b(dominant|market-leading|industry-leading)\b',
        ],
        'low': [
            r'\b(low-quality|low\s+quality|poor|weak|struggling)\b',
            r'\b(distressed|troubled|risky|speculative)\b',
            # NEW: More low-quality variations
            r'\b(questionable|dubious|shaky|unstable)\b',
            r'\b(failing|deteriorating|declining)\b',
            r'\b(subpar|mediocre|inferior)\b',
        ],
    }
    
    # Risk level patterns - EXPANDED
    RISK_PATTERNS = {
        'low': [
            r'\b(low-risk|low\s+risk|safe|conservative|defensive)\b',
            r'\b(stable|secure|protected|less\s+risky)\b',
            # NEW: More low-risk variations
            r'\b(cautious|prudent|careful)\b',
            r'\b(low-volatility|low\s+volatility|steady)\b',
            r'\b(predictable|consistent|dependable)\b',
        ],
        'high': [
            r'\b(high-risk|high\s+risk|risky|aggressive|volatile)\b',
            r'\b(speculative|dangerous|unsafe)\b',
            # NEW: More high-risk variations
            r'\b(high-volatility|high\s+volatility|unpredictable)\b',
            r'\b(turbulent|unstable|uncertain)\b',
            r'\b(adventurous|bold|daring)\b',
        ],
    }
    
    # Size/Market cap patterns - EXPANDED
    SIZE_PATTERNS = {
        'large': [
            r'\b(large-cap|large\s+cap|mega-cap|mega\s+cap|big|large)\b',
            r'\b(established|major|leading)\b',
            # NEW: More large-cap variations
            r'\b(giant|massive|huge|enormous)\b',
            r'\b(blue-chip|market\s+leader|dominant)\b',
            r'\b(trillion-dollar|multi-billion)\b',
        ],
        'mid': [
            r'\b(mid-cap|mid\s+cap|medium|middle)\b',
            # NEW: More mid-cap variations
            r'\b(mid-size|mid-sized|medium-sized)\b',
        ],
        'small': [
            r'\b(small-cap|small\s+cap|micro-cap|micro\s+cap|small)\b',
            # NEW: More small-cap variations
            r'\b(tiny|emerging|startup|young)\b',
            r'\b(nano-cap|nano\s+cap)\b',
        ],
    }
    
    # Performance patterns - EXPANDED
    PERFORMANCE_PATTERNS = {
        'profitable': [
            r'\b(profitable|profit-making|money-making|earning)\b',
            # NEW: More profitable variations
            r'\b(in\s+the\s+black|cash-positive|revenue-generating)\b',
            r'\b(successful|thriving|flourishing)\b',
        ],
        'unprofitable': [
            r'\b(unprofitable|loss-making|losing\s+money)\b',
            # NEW: More unprofitable variations
            r'\b(in\s+the\s+red|cash-negative|burning\s+cash)\b',
            r'\b(failing|struggling|hemorrhaging)\b',
        ],
        'growing': [
            r'\b(growing|growth|expanding|high-growth)\b',
            # NEW: More growth variations
            r'\b(fast-growing|rapidly\s+growing|accelerating)\b',
            r'\b(scaling|emerging|rising)\b',
            r'\b(booming|surging|soaring)\b',
        ],
        'declining': [
            r'\b(declining|shrinking|contracting)\b',
            # NEW: More decline variations
            r'\b(falling|dropping|slowing)\b',
            r'\b(stagnant|flat|plateauing)\b',
        ],
    }
    
    # Valuation patterns - EXPANDED
    VALUATION_PATTERNS = {
        'undervalued': [
            r'\b(undervalued|cheap|bargain|discounted|value)\b',
            # NEW: More undervalued variations
            r'\b(underpriced|trading\s+below|on\s+sale)\b',
            r'\b(attractively\s+priced|good\s+deal|steal)\b',
            r'\b(value\s+(?:stock|investment|play))\b',
        ],
        'overvalued': [
            r'\b(overvalued|expensive|pricey|overpriced)\b',
            # NEW: More overvalued variations
            r'\b(trading\s+above|inflated|bubble|frothy)\b',
            r'\b(overhyped|overextended|stretched)\b',
            r'\b(rich|lofty|elevated)\b',
        ],
        'fairly_valued': [
            r'\b(fairly\s+valued|fair\s+value|reasonably\s+priced)\b',
            # NEW: More fairly-valued variations
            r'\b(appropriately\s+valued|at\s+fair\s+value)\b',
            r'\b(trading\s+at\s+value|market\s+value)\b',
        ],
    }
    
    # NEW: False positive patterns (DON'T detect as filters)
    FALSE_POSITIVE_PATTERNS = [
        # Company names that might match sector patterns
        r'\bApple\s+(?:Inc|Computer)\b',
        r'\bMicrosoft\s+Corporation\b',
        r'\bAmazon\b',
        # Context where words aren't filters
        r'\b(?:Apple|Microsoft|Google|Amazon|Tesla|Meta)\'s\s+(?:tech|technology)\b',
        # Questions about filters aren't filters themselves
        r'\bwhat\s+(?:is|are)\s+(?:tech|technology|financial)\b',
        r'\bhow\s+(?:is|are)\s+(?:tech|healthcare)\b',
    ]
    
    def __init__(self):
        """Initialize the natural filter detector"""
        self._compiled_patterns = self._compile_patterns()
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def _compile_patterns(self) -> Dict[str, Dict[str, List[re.Pattern]]]:
        """Pre-compile all regex patterns for efficiency"""
        compiled = {}
        
        # Compile sector patterns
        compiled['sector'] = {}
        for sector, patterns in self.SECTOR_PATTERNS.items():
            compiled['sector'][sector] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile quality patterns
        compiled['quality'] = {}
        for quality, patterns in self.QUALITY_PATTERNS.items():
            compiled['quality'][quality] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile risk patterns
        compiled['risk'] = {}
        for risk, patterns in self.RISK_PATTERNS.items():
            compiled['risk'][risk] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile size patterns
        compiled['size'] = {}
        for size, patterns in self.SIZE_PATTERNS.items():
            compiled['size'][size] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile performance patterns
        compiled['performance'] = {}
        for perf, patterns in self.PERFORMANCE_PATTERNS.items():
            compiled['performance'][perf] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        # Compile valuation patterns
        compiled['valuation'] = {}
        for val, patterns in self.VALUATION_PATTERNS.items():
            compiled['valuation'][val] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        return compiled
    
    def detect_filters(self, text: str) -> List[NaturalFilter]:
        """
        Detect all natural language filters in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of NaturalFilter objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        filters = []
        
        # Detect each filter type
        for filter_type in ['sector', 'quality', 'risk', 'size', 'performance', 'valuation']:
            for filter_value, patterns in self._compiled_patterns[filter_type].items():
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        matched_text = match.group(0)
                        
                        # NEW: Check if this specific match is a false positive
                        context_start = max(0, match.start() - 15)
                        context_end = min(len(text), match.end() + 15)
                        local_context = text[context_start:context_end]
                        if self._is_false_positive(local_context):
                            continue
                        
                        # Calculate confidence
                        confidence = self._calculate_confidence_enhanced(
                            text,
                            filter_type,
                            filter_value,
                            matched_text,
                            match.start()
                        )
                        
                        filters.append(NaturalFilter(
                            filter_type=FilterType[filter_type.upper()],
                            value=filter_value,
                            raw_text=matched_text,
                            confidence=confidence,
                            position=match.start()
                        ))
        
        # Remove duplicates (keep highest confidence for each type)
        filters = self._deduplicate_filters(filters)
        
        # Sort by position
        filters.sort(key=lambda x: x.position)
        
        return filters
    
    def _deduplicate_filters(self, filters: List[NaturalFilter]) -> List[NaturalFilter]:
        """Remove duplicate filters, keeping highest confidence for each type+value"""
        seen = {}
        for f in filters:
            key = (f.filter_type, f.value)
            if key not in seen or f.confidence > seen[key].confidence:
                seen[key] = f
        return list(seen.values())
    
    def _is_false_positive(self, text: str) -> bool:
        """
        Check if text contains false positive patterns.
        
        Returns:
            True if false positive detected, False otherwise
        """
        if not text:
            return False
        
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def _calculate_confidence(
        self,
        text: str,
        filter_type: str,
        filter_value: str,
        matched_text: str,
        position: int
    ) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, filter_type, filter_value, matched_text, position)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        filter_type: str,
        filter_value: str,
        matched_text: str,
        position: int
    ) -> float:
        """
        Calculate confidence for filter detection (ENHANCED context-aware scoring).
        Similar to other Phase 1-3 confidence scoring.
        """
        confidence = 0.75  # Base confidence
        
        # Boost for explicit filter type words
        if filter_type == 'sector':
            if re.search(r'\b(sector|industry|space|field)\b', text, re.IGNORECASE):
                confidence += 0.10
        elif filter_type == 'quality':
            if re.search(r'\b(quality|tier|class|grade)\b', text, re.IGNORECASE):
                confidence += 0.10
        elif filter_type == 'risk':
            if re.search(r'\b(risk|risky|safe|safety|volatility)\b', text, re.IGNORECASE):
                confidence += 0.10
        elif filter_type == 'size':
            if re.search(r'\b(cap|size|large|small|big)\b', text, re.IGNORECASE):
                confidence += 0.10
        elif filter_type == 'valuation':
            if re.search(r'\b(valuation|valued|value|price|priced)\b', text, re.IGNORECASE):
                confidence += 0.10
        
        # Boost for context words
        context_words = ['companies', 'stocks', 'firms', 'businesses', 'investments', 'securities']
        context_matches = sum(1 for word in context_words if word in text.lower())
        if context_matches > 0:
            confidence += min(0.08, context_matches * 0.04)
        
        # Boost for multi-word matches (more specific)
        if len(matched_text.split()) >= 2:
            confidence += 0.05
        
        # NEW: Boost for question/command context
        if re.search(r'\b(show|find|get|list|give)\b', text, re.IGNORECASE):
            confidence += 0.05
        
        # NEW: Boost if filter is part of a clear phrase
        if re.search(rf'\b{re.escape(matched_text)}\s+(?:companies|stocks|firms)\b', text, re.IGNORECASE):
            confidence += 0.05
        
        # NEW: Penalty for ambiguous context
        if filter_type == 'sector' and 'Apple' in text:
            # "Apple" company might confuse sector detection
            confidence -= 0.03
        
        return min(1.0, max(0.5, confidence))
    
    def has_filters(self, text: str) -> bool:
        """
        Quick check if text contains natural language filters.
        
        Returns:
            True if filters detected, False otherwise
        """
        if not text:
            return False
        
        filters = self.detect_filters(text)
        return len(filters) > 0
    
    def to_structured_filters(self, filters: List[NaturalFilter]) -> Dict[str, Any]:
        """
        Convert natural filters to structured filter dict.
        
        Returns:
            Structured filter dict for downstream processing
        """
        structured = {}
        
        for f in filters:
            if f.filter_type == FilterType.SECTOR:
                structured.setdefault('sectors', []).append(f.value)
            elif f.filter_type == FilterType.QUALITY:
                structured['quality_level'] = f.value
            elif f.filter_type == FilterType.RISK:
                structured['risk_level'] = f.value
            elif f.filter_type == FilterType.SIZE:
                structured['size'] = f.value
            elif f.filter_type == FilterType.PERFORMANCE:
                structured['performance'] = f.value
            elif f.filter_type == FilterType.VALUATION:
                structured['valuation'] = f.value
        
        return structured

