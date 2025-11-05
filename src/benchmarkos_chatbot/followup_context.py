"""Advanced context tracking for follow-up questions.

This module provides comprehensive context tracking beyond simple ticker resolution,
enabling sophisticated follow-up question handling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class ConversationContext:
    """Comprehensive context tracking for follow-up questions."""
    
    # Core entities
    tickers: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    
    # Intent and query type
    intent: Optional[str] = None
    query_type: Optional[str] = None  # 'question', 'command', 'lookup'
    
    # Time/period context
    time_period: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    
    # Metadata
    timestamp: Optional[datetime] = None
    confidence: float = 1.0
    
    def is_empty(self) -> bool:
        """Check if context is empty."""
        return not (self.tickers or self.metrics or self.intent)
    
    def get_primary_ticker(self) -> Optional[str]:
        """Get the most relevant ticker (usually the first/last mentioned)."""
        return self.tickers[-1] if self.tickers else None
    
    def get_all_tickers(self) -> List[str]:
        """Get all tickers in context (up to 3)."""
        return self.tickers[:3]
    
    def has_multiple_tickers(self) -> bool:
        """Check if multiple tickers are in context."""
        return len(self.tickers) >= 2
    
    def update(self, **kwargs) -> None:
        """Update context fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.timestamp = datetime.utcnow()


def detect_ambiguity(
    query: str,
    context: ConversationContext
) -> Tuple[bool, Optional[str]]:
    """
    Detect if a pronoun reference is ambiguous and needs clarification.
    
    Returns:
        (is_ambiguous, clarification_message)
    """
    lowered = query.lower()
    
    # Check for singular pronouns with multiple tickers in context
    singular_pronouns = r'\b(it|its|that|this)\b'
    has_singular = re.search(singular_pronouns, lowered)
    
    if has_singular and len(context.tickers) >= 2:
        # Ambiguous: user said "it" but we have multiple tickers
        ticker_list = ", ".join(context.tickers[:-1]) + f", or {context.tickers[-1]}"
        return True, f"Which company are you asking about? {ticker_list}?"
    
    # Check for plural pronouns with only one ticker
    plural_pronouns = r'\b(them|they|their|those|these)\b'
    has_plural = re.search(plural_pronouns, lowered)
    
    if has_plural and len(context.tickers) == 1:
        # Slightly ambiguous but probably OK - user might mean just the one company
        return False, None
    
    return False, None


def resolve_implicit_entities(
    query: str,
    context: ConversationContext
) -> Dict[str, Any]:
    """
    Resolve implicit entities from context when not explicitly mentioned.
    
    For example:
    - "What about margins?" → Adds tickers from context
    - "Show me next quarter" → Carries over tickers from context
    
    Returns:
        Dictionary with resolved entities (tickers, metrics, periods)
    """
    lowered = query.lower()
    resolved = {
        'tickers': [],
        'metrics': [],
        'time_period': None,
        'carried_over': []
    }
    
    # Check if query has explicit tickers
    has_ticker_words = bool(re.search(
        r'\b(AAPL|MSFT|GOOGL|AMZN|TSLA|NVDA|META|apple|microsoft|google|amazon|tesla|nvidia|meta)\b',
        query,
        re.IGNORECASE
    ))
    
    # Check if query has metrics but no tickers
    metric_keywords = [
        'revenue', 'profit', 'margin', 'earnings', 'growth', 'pe', 'p/e',
        'valuation', 'debt', 'cash', 'income', 'ebitda', 'roi', 'roe'
    ]
    has_metric = any(keyword in lowered for keyword in metric_keywords)
    
    # If query has metric but no ticker, carry over tickers
    if has_metric and not has_ticker_words and context.tickers:
        resolved['tickers'] = context.tickers
        resolved['carried_over'].append('tickers')
    
    # Check for time period keywords
    time_keywords = [
        'next quarter', 'next year', 'last quarter', 'last year',
        'this quarter', 'this year', 'q1', 'q2', 'q3', 'q4'
    ]
    has_time = any(keyword in lowered for keyword in time_keywords)
    
    # If no explicit time but context has one, carry it over for metric queries
    if has_metric and not has_time and context.time_period:
        resolved['time_period'] = context.time_period
        resolved['carried_over'].append('time_period')
    
    return resolved


def calculate_resolution_confidence(
    query: str,
    context: ConversationContext,
    pronouns_found: List[str]
) -> float:
    """
    Calculate confidence score for pronoun resolution (0.0 to 1.0).
    
    Lower confidence = should ask for clarification
    Higher confidence = safe to auto-resolve
    """
    confidence = 1.0
    
    # Reduce confidence if context is old (>5 messages ago)
    if context.timestamp:
        age_seconds = (datetime.utcnow() - context.timestamp).total_seconds()
        if age_seconds > 300:  # 5 minutes
            confidence -= 0.3
    
    # Reduce confidence if multiple singular pronouns with multiple tickers
    if len(pronouns_found) > 1 and len(context.tickers) > 1:
        confidence -= 0.4
    
    # Reduce confidence if no strong context
    if context.is_empty():
        confidence = 0.0
    
    # Increase confidence if recent and clear
    if len(context.tickers) == 1 and context.timestamp:
        age_seconds = (datetime.utcnow() - context.timestamp).total_seconds()
        if age_seconds < 60:  # Within 1 minute
            confidence = min(1.0, confidence + 0.2)
    
    return max(0.0, min(1.0, confidence))


def should_ask_clarification(confidence: float, ambiguous: bool) -> bool:
    """Determine if we should ask for clarification instead of auto-resolving."""
    if ambiguous:
        return True
    if confidence < 0.5:
        return True
    return False


__all__ = [
    'ConversationContext',
    'detect_ambiguity',
    'resolve_implicit_entities',
    'calculate_resolution_confidence',
    'should_ask_clarification',
]

