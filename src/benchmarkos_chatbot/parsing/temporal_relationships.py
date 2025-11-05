"""
Temporal relationship detection for natural language queries.

Handles:
- Before/After: "before 2020", "after Q1", "prior to 2019"
- During/Within: "during 2020", "within Q4", "in 2019"
- Event-based: "during crisis", "pre-pandemic", "post-recession"
- Relative: "since last year", "until next quarter"
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class TemporalRelationType(Enum):
    """Types of temporal relationships"""
    BEFORE = "before"       # Before a point in time
    AFTER = "after"         # After a point in time
    DURING = "during"       # During a period
    WITHIN = "within"       # Within a timeframe
    SINCE = "since"         # Since a point (ongoing)
    UNTIL = "until"         # Until a point (ending)
    BETWEEN = "between"     # Between two points


class EventType(Enum):
    """Known historical/economic events"""
    PANDEMIC = "pandemic"           # COVID-19 pandemic (2020-2021)
    FINANCIAL_CRISIS = "financial_crisis"  # 2008 financial crisis
    RECESSION = "recession"         # Economic recession
    DOT_COM_BUBBLE = "dot_com_bubble"  # 2000 dot-com bubble
    CRISIS = "crisis"               # Generic crisis


@dataclass
class TemporalRelationship:
    """
    Represents a temporal relationship in text.
    """
    relation_type: TemporalRelationType
    time_reference: str              # The time being referenced (e.g., "2020", "Q1")
    event: Optional[EventType]       # Event reference if applicable
    modifier: str                    # The temporal modifier (e.g., "before", "during")
    raw_text: str                   # Original matched text
    confidence: float               # Confidence score (0.0 to 1.0)
    position: int                   # Position in text
    
    def __repr__(self):
        return (f"TemporalRelationship(type={self.relation_type.value}, "
                f"ref='{self.time_reference}', "
                f"event={self.event.value if self.event else None}, "
                f"confidence={self.confidence:.2f})")


class TemporalRelationshipDetector:
    """
    Detect temporal relationships in natural language queries.
    """
    
    # BEFORE patterns - EXPANDED
    BEFORE_PATTERNS = [
        r'\b(before|prior\s+to|ahead\s+of|pre-)\b',
        r'\b(earlier\s+than|preceding)\b',
        r'\b(up\s+until|up\s+to)\b',
        # NEW: More before variations
        r'\b(in\s+advance\s+of|leading\s+up\s+to)\b',
        r'\b(in\s+front\s+of|previously|formerly)\b',
    ]
    
    # AFTER patterns - EXPANDED
    AFTER_PATTERNS = [
        r'\b(after|following|post-|subsequent\s+to)\b',
        r'\b(later\s+than|beyond)\b',
        r'\b(starting\s+from|from\s+\w+\s+onwards?)\b',
        # NEW: More after variations
        r'\b(in\s+the\s+wake\s+of|succeeding)\b',
        r'\b(once\s+\w+\s+ended|once\s+\w+\s+finished)\b',
        r'\b(coming\s+after|in\s+the\s+aftermath\s+of)\b',
    ]
    
    # DURING patterns - EXPANDED
    DURING_PATTERNS = [
        r'\b(during|throughout|amid|amidst)\b',
        r'\b(in\s+the\s+course\s+of|over\s+the\s+course\s+of)\b',
        r'\b(through|across)\b',
        # NEW: More during variations
        r'\b(while|whilst|as)\b',
        r'\b(in\s+the\s+middle\s+of|in\s+the\s+midst\s+of)\b',
        r'\b(at\s+the\s+time\s+of|when)\b',
    ]
    
    # WITHIN patterns - EXPANDED
    WITHIN_PATTERNS = [
        r'\b(within|inside|in)\b',
        # NEW: More within variations
        r'\b(over|for\s+the\s+period\s+of)\b',
    ]
    
    # SINCE patterns - EXPANDED
    SINCE_PATTERNS = [
        r'\b(since|from|starting\s+from)\b',
        r'\b(ever\s+since|beginning)\b',
        # NEW: More since variations
        r'\b(as\s+of|commencing)\b',
        r'\b(from\s+the\s+time\s+of)\b',
    ]
    
    # UNTIL patterns - EXPANDED
    UNTIL_PATTERNS = [
        r'\b(until|till|up\s+to|through)\b',
        r'\b(ending|concluding)\b',
        # NEW: More until variations
        r'\b(as\s+far\s+as|no\s+later\s+than)\b',
        r'\b(before\s+reaching|stopping\s+at)\b',
    ]
    
    # BETWEEN patterns
    BETWEEN_PATTERNS = [
        r'\b(between)\s+([\w\s\d-]+)\s+and\s+([\w\s\d-]+)\b',
        r'\b(from)\s+([\w\s\d-]+)\s+to\s+([\w\s\d-]+)\b',
    ]
    
    # Event reference patterns - MASSIVELY EXPANDED
    EVENT_PATTERNS = {
        EventType.PANDEMIC: [
            r'\b(pandemic|COVID|COVID-19|coronavirus)\b',
            # NEW: More pandemic variations
            r'\b(lockdown|quarantine|outbreak)\b',
            r'\b(health\s+crisis|global\s+pandemic)\b',
        ],
        EventType.FINANCIAL_CRISIS: [
            r'\b(financial\s+crisis|2008\s+crisis|great\s+recession|banking\s+crisis)\b',
            # NEW: More crisis variations
            r'\b(subprime\s+crisis|mortgage\s+crisis|credit\s+crunch)\b',
            r'\b(Lehman\s+(?:collapse|bankruptcy))\b',
        ],
        EventType.RECESSION: [
            r'\b(recession|downturn|economic\s+crisis)\b',
            # NEW: More recession variations
            r'\b(economic\s+downturn|slump|contraction)\b',
            r'\b(bear\s+market|market\s+downturn)\b',
        ],
        EventType.DOT_COM_BUBBLE: [
            r'\b(dot-?com\s+(?:bubble|crash|burst)|2000\s+crash)\b',
            # NEW: More bubble variations
            r'\b(tech\s+bubble|internet\s+bubble)\b',
        ],
        EventType.CRISIS: [
            r'\b(crisis|crash|collapse)\b',
            # NEW: More crisis variations
            r'\b(market\s+(?:crash|correction|turmoil))\b',
            r'\b(volatility\s+spike|sell-off|meltdown)\b',
        ],
    }
    
    # NEW: False positive patterns (DON'T detect as temporal relationships)
    FALSE_POSITIVE_PATTERNS = [
        # Questions about time aren't temporal filters
        r'\bwhen\s+(?:is|was|will|did)\b',
        r'\bwhat\s+(?:time|year|quarter|period)\b',
        r'\bhow\s+long\b',
        # Unrelated "before" usage
        r'\bbefore\s+(?:you|we|I|they)\b',
        # Common phrases
        r'\blong\s+before\b',
        r'\bnot\s+long\s+after\b',
    ]
    
    # Time reference patterns (what comes after the modifier) - EXPANDED
    # Order matters - most specific first
    TIME_REFERENCE_PATTERNS = [
        r'\bH[12]\s*\d{4}\b',               # Half-year: H1 2023 (CHECK FIRST)
        r'\bQ[1-4]\s*\d{4}\b',              # Quarter with year: Q1 2023
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
        r'\b(early|mid|late)\s+\d{4}\b',    # Early 2020, late 2019
        r'\b(FY|fiscal\s+year)\s*\d{4}\b',
        r'\b(\d{1,2})/(\d{4})\b',           # Month/Year: 03/2020
        r'\b(the\s+)?(\d{4})s\b',           # The 2010s
        r'\bQ[1-4]\b',                      # Quarter without year: Q4
        r'\b(last|next|this)\s+(year|quarter|month|week)\b',
        r'\b(\d{4})\b',                      # Year: 2020 (CHECK LAST - most general)
    ]
    
    def __init__(self):
        """Initialize the temporal relationship detector"""
        self._compiled_patterns = self._compile_patterns()
        self._time_ref_patterns = [re.compile(p, re.IGNORECASE) for p in self.TIME_REFERENCE_PATTERNS]
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile all regex patterns for efficiency"""
        compiled = {}
        
        compiled['before'] = [re.compile(p, re.IGNORECASE) for p in self.BEFORE_PATTERNS]
        compiled['after'] = [re.compile(p, re.IGNORECASE) for p in self.AFTER_PATTERNS]
        compiled['during'] = [re.compile(p, re.IGNORECASE) for p in self.DURING_PATTERNS]
        compiled['within'] = [re.compile(p, re.IGNORECASE) for p in self.WITHIN_PATTERNS]
        compiled['since'] = [re.compile(p, re.IGNORECASE) for p in self.SINCE_PATTERNS]
        compiled['until'] = [re.compile(p, re.IGNORECASE) for p in self.UNTIL_PATTERNS]
        compiled['between'] = [re.compile(p, re.IGNORECASE) for p in self.BETWEEN_PATTERNS]
        
        # Compile event patterns
        compiled['events'] = {}
        for event_type, patterns in self.EVENT_PATTERNS.items():
            compiled['events'][event_type] = [re.compile(p, re.IGNORECASE) for p in patterns]
        
        return compiled
    
    def detect_temporal_relationships(self, text: str) -> List[TemporalRelationship]:
        """
        Detect all temporal relationships in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of TemporalRelationship objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        relationships = []
        
        # Check for BETWEEN first (most specific)
        for pattern in self._compiled_patterns['between']:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 3:
                    modifier = groups[0]
                    start_ref = groups[1].strip()
                    end_ref = groups[2].strip()
                    
                    confidence = self._calculate_confidence(
                        text, "between", start_ref, match.start()
                    )
                    
                    relationships.append(TemporalRelationship(
                        relation_type=TemporalRelationType.BETWEEN,
                        time_reference=f"{start_ref} and {end_ref}",
                        event=None,
                        modifier=modifier,
                        raw_text=match.group(0),
                        confidence=confidence,
                        position=match.start()
                    ))
        
        # Check each temporal relation type
        for rel_type in ['before', 'after', 'during', 'within', 'since', 'until']:
            for pattern in self._compiled_patterns[rel_type]:
                for match in pattern.finditer(text):
                    modifier = match.group(0)
                    
                    # NEW: Skip if this specific match is a false positive
                    context_start = max(0, match.start() - 20)
                    context_end = min(len(text), match.end() + 20)
                    local_context = text[context_start:context_end]
                    if self._is_false_positive(local_context):
                        continue
                    
                    # Look for time reference after the modifier
                    remaining_text = text[match.end():]
                    time_ref, event = self._extract_time_reference(remaining_text)
                    
                    if time_ref or event:
                        confidence = self._calculate_confidence_enhanced(
                            text, rel_type, time_ref or event.value if event else "", match.start()
                        )
                        
                        relationships.append(TemporalRelationship(
                            relation_type=TemporalRelationType[rel_type.upper()],
                            time_reference=time_ref or "",
                            event=event,
                            modifier=modifier,
                            raw_text=f"{modifier} {time_ref or (event.value if event else '')}",
                            confidence=confidence,
                            position=match.start()
                        ))
        
        # Sort by position
        relationships.sort(key=lambda x: x.position)
        
        return relationships
    
    def _extract_time_reference(self, text: str) -> tuple[Optional[str], Optional[EventType]]:
        """
        Extract time reference or event from text.
        
        Returns:
            Tuple of (time_reference, event_type)
        """
        if not text:
            return (None, None)
        
        # Check for event references first
        for event_type, patterns in self._compiled_patterns['events'].items():
            for pattern in patterns:
                match = pattern.search(text[:50])  # Check first 50 chars
                if match:
                    return (None, event_type)
        
        # Check for time references
        for pattern in self._time_ref_patterns:
            match = pattern.search(text[:50])  # Check first 50 chars
            if match:
                return (match.group(0).strip(), None)
        
        return (None, None)
    
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
        relation_type: str,
        time_reference: str,
        position: int
    ) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, relation_type, time_reference, position)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        relation_type: str,
        time_reference: str,
        position: int
    ) -> float:
        """
        Calculate confidence for temporal relationship detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-3 features.
        """
        confidence = 0.75  # Base confidence
        
        # Boost for explicit time references
        if re.search(r'\b\d{4}\b', time_reference):  # Year
            confidence += 0.12
        if re.search(r'\bQ[1-4]', time_reference):  # Quarter
            confidence += 0.10
        if re.search(r'\bH[12]', time_reference):  # Half-year
            confidence += 0.10
        if re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', 
                    time_reference, re.IGNORECASE):
            confidence += 0.10
        
        # Boost for event references
        event_keywords = ['pandemic', 'crisis', 'recession', 'crash', 'downturn', 'bubble']
        event_matches = sum(1 for event in event_keywords if event in time_reference.lower())
        if event_matches > 0:
            confidence += min(0.12, event_matches * 0.06)
        
        # Boost for clear temporal context in query
        financial_context = ['revenue', 'profit', 'performance', 'data', 'results', 'earnings', 'growth']
        context_matches = sum(1 for term in financial_context if term in text.lower())
        if context_matches > 0:
            confidence += min(0.08, context_matches * 0.04)
        
        # NEW: Boost for specific temporal relation types
        if relation_type in ['before', 'after']:
            confidence += 0.03  # Clear directional relationships
        elif relation_type == 'between':
            confidence += 0.05  # Ranges are very specific
        
        # NEW: Penalty for ambiguous modifiers
        weak_modifiers = ['in', 'at', 'for', 'while']
        if any(weak in relation_type for weak in weak_modifiers):
            confidence -= 0.03
        
        return min(1.0, max(0.5, confidence))
    
    def has_temporal_relationship(self, text: str) -> bool:
        """
        Quick check if text contains temporal relationships.
        
        Returns:
            True if temporal relationship detected, False otherwise
        """
        if not text:
            return False
        
        relationships = self.detect_temporal_relationships(text)
        return len(relationships) > 0
    
    def get_event_timeframe(self, event: EventType) -> Optional[Dict[str, Any]]:
        """
        Get approximate timeframe for known events (EXPANDED).
        
        Returns:
            Dict with year/period info, or None
        """
        event_timeframes = {
            EventType.PANDEMIC: {
                'start_year': 2020, 
                'end_year': 2021, 
                'description': 'COVID-19 Pandemic',
                'quarters': ['Q1 2020', 'Q2 2020', 'Q3 2020', 'Q4 2020', 'Q1 2021', 'Q2 2021']
            },
            EventType.FINANCIAL_CRISIS: {
                'start_year': 2008, 
                'end_year': 2009, 
                'description': '2008 Financial Crisis / Great Recession',
                'quarters': ['Q3 2008', 'Q4 2008', 'Q1 2009', 'Q2 2009']
            },
            EventType.DOT_COM_BUBBLE: {
                'start_year': 2000, 
                'end_year': 2002, 
                'description': 'Dot-com Bubble Burst',
                'quarters': ['Q1 2000', 'Q2 2000', 'Q3 2000', 'Q4 2000', 'Q1 2001', 'Q2 2001']
            },
            EventType.RECESSION: {
                'start_year': None, 
                'end_year': None, 
                'description': 'Economic Recession (generic)',
                'quarters': None
            },
            EventType.CRISIS: {
                'start_year': None, 
                'end_year': None, 
                'description': 'Crisis (generic)',
                'quarters': None
            },
        }
        
        return event_timeframes.get(event)

