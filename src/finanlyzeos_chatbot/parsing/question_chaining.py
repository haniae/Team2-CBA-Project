"""
Question chaining detection for natural language queries.

Handles:
- Sequential questions: "And what about...", "Then show me..."
- Comparative chains: "How does that compare to..."
- Exploratory chains: "What about...", "How about..."
- Continuation signals: "Also...", "Additionally..."
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class ChainType(Enum):
    """Types of question chains"""
    SEQUENTIAL = "sequential"         # "And what about...", "Then..."
    COMPARATIVE = "comparative"       # "How does that compare to..."
    EXPLORATORY = "exploratory"       # "What about...", "How about..."
    CONTINUATION = "continuation"     # "Also...", "Additionally..."
    ELABORATION = "elaboration"       # "Tell me more...", "Explain..."


@dataclass
class QuestionChain:
    """
    Represents a detected question chain.
    """
    chain_type: ChainType
    signal_phrase: str           # The phrase indicating chaining (e.g., "and what about")
    is_followup: bool           # Whether this is a follow-up question
    requires_context: bool      # Whether this needs previous context
    confidence: float           # Confidence score (0.0 to 1.0)
    position: int              # Position in text
    
    def __repr__(self):
        return (f"QuestionChain(type={self.chain_type.value}, "
                f"signal='{self.signal_phrase}', "
                f"followup={self.is_followup}, "
                f"confidence={self.confidence:.2f})")


class QuestionChainDetector:
    """
    Detect question chaining and conversation flow patterns.
    """
    
    # Sequential chain patterns (ordered follow-ups) - EXPANDED
    SEQUENTIAL_PATTERNS = [
        r'\b(and\s+what\s+about|and\s+how\s+about)\b',
        r'\b(then\s+(?:show|tell|give|get|analyze|display))\b',
        r'\b(next,?\s+(?:show|tell|what|how|get|display))\b',
        r'\b(after\s+that,?\s+(?:show|tell|what|display))\b',
        # NEW: More sequential patterns
        r'\b(now\s+(?:show|tell|what|how))\b',
        r'\b(following\s+that,?\s+(?:show|tell))\b',
        r'\b(subsequently,?\s+(?:show|tell))\b',
        r'\b(afterwards,?\s+(?:show|tell|what|how))\b',
        r'\b(later,?\s+(?:show|tell|what|how))\b',
        r'\b(secondly,?\s+(?:show|tell|what|how))\b',
        r'\b(thirdly,?\s+(?:show|tell|what|how))\b',
        r'\b(moving\s+on,?\s+(?:show|tell|what|how))\b',
        r'\b(proceeding\s+to,?\s+(?:show|tell|what|how|analyze|check))\b',  # "proceeding to analyze"
    ]
    
    # Comparative chain patterns (comparing to previous) - EXPANDED
    COMPARATIVE_PATTERNS = [
        r'\bhow\s+(?:does|do)\s+(?:that|this|it|they)\s+compare\b',
        r'\bcompared\s+to\s+(?:that|the\s+previous|the\s+last)\b',
        r'\b(?:versus|vs)\s+(?:that|the\s+last|the\s+previous)\b',
        r'\bhow\s+(?:does|do)\s+\w+\s+stack\s+up\b',
        # NEW: More comparative patterns
        r'\b(?:in\s+)?comparison\s+to\s+(?:that|the\s+previous)\b',
        r'\bagainst\s+(?:that|the\s+previous|the\s+last)\b',
        r'\bhow\s+(?:does|do)\s+(?:that|this|it)\s+(?:differ|vary)\b',
        r'\b(?:relative\s+to|compared\s+with)\s+(?:that|the\s+previous|the\s+last)\b',
        r'\b(?:is|are)\s+(?:that|this|it|they)\s+(?:better|worse|more|less|higher|lower)\s+than\s+(?:the\s+previous|the\s+last)\b',
        r'\b(?:how|what)\s+(?:about|is)\s+(?:that|this|it)\s+(?:versus|vs|compared\s+to)\s+(?:the\s+previous|the\s+last)\b',
        r'\b(?:same|similar|different)\s+(?:as|from)\s+(?:that|the\s+previous|the\s+last)\b',
    ]
    
    # Exploratory chain patterns (exploring related topics) - EXPANDED
    EXPLORATORY_PATTERNS = [
        r'\b(?:what|how)\s+about\b',
        r'\bhow\s+about\s+(?:looking\s+at|checking|trying)\b',
        r'\b(?:and|also)\s+(?:what|how)\s+about\b',
        # NEW: More exploratory patterns
        r'\b(?:what|how)\s+if\s+(?:we|I)\s+(?:look|check)\b',
        r'\b(?:maybe|perhaps)\s+(?:check|look\s+at)\b',
        r'\b(?:let\'s|let\s+us)\s+(?:also|also\s+look|check|see)\b',
        r'\b(?:i\'d\s+also\s+like|i\s+would\s+also\s+like)\s+(?:to\s+know|to\s+see|to\s+check)\b',
        r'\b(?:can\s+we|could\s+we)\s+(?:also|also\s+look|check|see)\b',
        r'\b(?:another|one\s+more)\s+(?:thing|question|query)\b',
        r'\b(?:speaking\s+of|on\s+that\s+note|while\s+we\'re\s+at\s+it)\b',
    ]
    
    # Continuation patterns (adding to previous) - EXPANDED
    CONTINUATION_PATTERNS = [
        r'\b(also,?\s+(?:show|tell|get|analyze|display))\b',
        r'\b(additionally,?\s+(?:show|tell|display))\b',
        r'\b(furthermore|moreover|besides)\b',
        r'\b(in\s+addition,?\s+(?:show|tell|display))\b',
        # NEW: More continuation patterns
        r'\b(plus,?\s+(?:show|tell|get))\b',
        r'\b(as\s+well,?\s+(?:show|tell))\b',
        r'\b(on\s+top\s+of\s+that)\b',
        r'\b(and\s+also|and\s+additionally)\b',
        r'\b(not\s+only\s+that,?\s+but\s+also)\b',
        r'\b(along\s+with\s+that)\b',
        r'\b(while\s+we\'re\s+at\s+it)\b',
        r'\b(by\s+the\s+way)\b',
    ]
    
    # Elaboration patterns (asking for more detail) - EXPANDED
    ELABORATION_PATTERNS = [
        r'\btell\s+me\s+more\s+(?:about|on)\b',
        r'\b(?:explain|elaborate)\s+(?:on\s+)?(?:that|this|it)\b',
        r'\b(?:more\s+details?|further\s+information)\s+(?:on|about)\b',
        r'\bgo\s+(?:deeper|into\s+more\s+detail)\b',
        # NEW: More elaboration patterns
        r'\b(?:expand|dive\s+deeper)\s+(?:on|into)\b',
        r'\b(?:break|drill)\s+(?:down|into)\s+(?:that|this)\b',
        r'\bdrill\s+down\s+into\b',  # "drill down into profit"
        r'\bcan\s+you\s+(?:elaborate|explain\s+more)\b',
        r'\b(?:i\s+need|i\'d\s+like)\s+(?:more|further|additional)\s+(?:info|information|details?|data)\s+(?:on|about|regarding)\b',
        r'\b(?:can|could|would)\s+you\s+(?:provide|give)\s+(?:more|further|additional)\s+(?:info|information|details?)\b',
        r'\b(?:what\s+else|anything\s+else)\s+(?:can|could)\s+you\s+(?:tell|say|share)\s+(?:about|on|regarding)\b',
        r'\b(?:dig\s+deeper|go\s+into\s+detail|provide\s+more\s+context)\b',
        r'\b(?:break\s+it\s+down|break\s+down\s+that|break\s+down\s+this)\b',
    ]
    
    # NEW: False positive patterns (DON'T detect as chains)
    FALSE_POSITIVE_PATTERNS = [
        # Questions asking about the concept of comparison (not comparing)
        r'\bwhat\s+(?:does|is)\s+(?:compare|comparison)\b',
        # Generic "also" without action
        r'\balso\s*$',
    ]
    
    def __init__(self):
        """Initialize the question chain detector"""
        self._sequential_patterns = [re.compile(p, re.IGNORECASE) for p in self.SEQUENTIAL_PATTERNS]
        self._comparative_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMPARATIVE_PATTERNS]
        self._exploratory_patterns = [re.compile(p, re.IGNORECASE) for p in self.EXPLORATORY_PATTERNS]
        self._continuation_patterns = [re.compile(p, re.IGNORECASE) for p in self.CONTINUATION_PATTERNS]
        self._elaboration_patterns = [re.compile(p, re.IGNORECASE) for p in self.ELABORATION_PATTERNS]
        self._false_positive_patterns = [re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS]
    
    def detect_chain(self, text: str) -> Optional[QuestionChain]:
        """
        Detect question chaining in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            QuestionChain object or None if no chaining detected
        """
        if not text:
            return None
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return None
        
        # Check each chain type (order matters - most specific first)
        
        # Check sequential chains
        for pattern in self._sequential_patterns:
            match = pattern.search(text)
            if match:
                return QuestionChain(
                    chain_type=ChainType.SEQUENTIAL,
                    signal_phrase=match.group(0),
                    is_followup=True,
                    requires_context=True,
                    confidence=self._calculate_confidence_enhanced(text, "sequential", match.group(0)),
                    position=match.start()
                )
        
        # Check comparative chains
        for pattern in self._comparative_patterns:
            match = pattern.search(text)
            if match:
                return QuestionChain(
                    chain_type=ChainType.COMPARATIVE,
                    signal_phrase=match.group(0),
                    is_followup=True,
                    requires_context=True,
                    confidence=self._calculate_confidence_enhanced(text, "comparative", match.group(0)),
                    position=match.start()
                )
        
        # Check exploratory chains
        for pattern in self._exploratory_patterns:
            match = pattern.search(text)
            if match:
                return QuestionChain(
                    chain_type=ChainType.EXPLORATORY,
                    signal_phrase=match.group(0),
                    is_followup=True,
                    requires_context=False,  # Exploratory can be independent
                    confidence=self._calculate_confidence_enhanced(text, "exploratory", match.group(0)),
                    position=match.start()
                )
        
        # Check continuation chains
        for pattern in self._continuation_patterns:
            match = pattern.search(text)
            if match:
                return QuestionChain(
                    chain_type=ChainType.CONTINUATION,
                    signal_phrase=match.group(0),
                    is_followup=True,
                    requires_context=True,
                    confidence=self._calculate_confidence_enhanced(text, "continuation", match.group(0)),
                    position=match.start()
                )
        
        # Check elaboration chains
        for pattern in self._elaboration_patterns:
            match = pattern.search(text)
            if match:
                return QuestionChain(
                    chain_type=ChainType.ELABORATION,
                    signal_phrase=match.group(0),
                    is_followup=True,
                    requires_context=True,
                    confidence=self._calculate_confidence_enhanced(text, "elaboration", match.group(0)),
                    position=match.start()
                )
        
        return None
    
    def _is_false_positive(self, text: str) -> bool:
        """Check if text contains false positive patterns"""
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _calculate_confidence(self, text: str, chain_type: str, signal_phrase: str) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, chain_type, signal_phrase)
    
    def _calculate_confidence_enhanced(self, text: str, chain_type: str, signal_phrase: str) -> float:
        """
        Calculate confidence for question chain detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-4 features.
        """
        confidence = 0.83  # Base confidence (chain signals are usually explicit)
        
        # Boost for explicit sequential signals
        if chain_type == "sequential":
            explicit_signals = ['then', 'next', 'after', 'following', 'now']
            matches = sum(1 for word in explicit_signals if word in signal_phrase.lower())
            if matches > 0:
                confidence += min(0.10, matches * 0.05)
        
        # Boost for comparative signals with pronouns
        if chain_type == "comparative":
            pronouns = ['that', 'this', 'it', 'they', 'previous', 'last']
            pronoun_matches = sum(1 for word in pronouns if word in text.lower())
            if pronoun_matches > 0:
                confidence += min(0.10, pronoun_matches * 0.05)
        
        # Boost for elaboration with pronouns and detail words
        if chain_type == "elaboration":
            detail_words = ['that', 'this', 'it', 'more', 'detail', 'information', 'deeper']
            matches = sum(1 for word in detail_words if word in text.lower())
            if matches > 0:
                confidence += min(0.08, matches * 0.04)
        
        # Boost for continuation with clear continuation words
        if chain_type == "continuation":
            if any(word in signal_phrase.lower() for word in ['also', 'additionally', 'furthermore', 'plus']):
                confidence += 0.06
        
        # Boost for question/action context
        action_context = ['show', 'tell', 'what', 'how', 'analyze', 'display', 'get']
        action_matches = sum(1 for word in action_context if word in text.lower())
        if action_matches > 0:
            confidence += min(0.06, action_matches * 0.03)
        
        # NEW: Boost for financial context (chain is about financial data)
        financial_context = ['revenue', 'profit', 'earnings', 'performance', 'stock', 'company']
        if any(term in text.lower() for term in financial_context):
            confidence += 0.04
        
        return min(1.0, max(0.7, confidence))
    
    def is_chained_question(self, text: str) -> bool:
        """
        Quick check if text is a chained question.
        
        Returns:
            True if chaining detected, False otherwise
        """
        if not text:
            return False
        
        chain = self.detect_chain(text)
        return chain is not None
    
    def requires_previous_context(self, text: str) -> bool:
        """
        Check if question requires context from previous query.
        
        Returns:
            True if previous context required, False otherwise
        """
        if not text:
            return False
        
        chain = self.detect_chain(text)
        return chain is not None and chain.requires_context

