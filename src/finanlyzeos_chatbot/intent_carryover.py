"""Intent carryover for follow-up questions.

When users ask follow-up questions, this module helps carry over the intent
from the previous query to maintain conversational flow.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


# Patterns that indicate a follow-up with same intent
FOLLOW_UP_PATTERNS = {
    'same_intent': [
        r'^what about\b',
        r'^how about\b',
        r'^and\b',
        r'^also\b',
    ],
    'continuation': [
        r'^tell me more',
        r'^more details',
        r'^elaborate',
        r'^continue',
    ],
}


def should_carry_over_intent(query: str, last_intent: Optional[str]) -> bool:
    """
    Determine if we should carry over the intent from the last query.
    
    Args:
        query: Current user query
        last_intent: Intent from previous query
        
    Returns:
        True if intent should be carried over
    """
    if not last_intent:
        return False
    
    lowered = query.lower().strip()
    
    # Check for follow-up patterns
    for pattern in FOLLOW_UP_PATTERNS['same_intent']:
        if re.search(pattern, lowered):
            return True
    
    # Check for continuation patterns
    for pattern in FOLLOW_UP_PATTERNS['continuation']:
        if re.search(pattern, lowered):
            return True
    
    return False


def augment_query_with_intent(
    query: str,
    last_intent: Optional[str],
    last_query: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Augment the current query with context from the last intent.
    
    Args:
        query: Current user query
        last_intent: Intent from previous query
        last_query: Previous query text
        
    Returns:
        (augmented_query, was_augmented)
    """
    if not should_carry_over_intent(query, last_intent):
        return query, False
    
    lowered = query.lower().strip()
    
    # Map intents to question templates
    intent_templates = {
        'risk_analysis': 'What are the risks of',
        'valuation': 'Is',
        'forecast': 'What will',
        'recommend': 'Should I invest in',
        'quality_check': "What's the financial health of",
    }
    
    # If query starts with "what about X", try to infer the intent question
    if re.match(r'^what about\b', lowered):
        if last_intent in intent_templates:
            # Extract the subject from "what about X"
            match = re.search(r'^what about\s+(.+?)[\?]?$', query, re.IGNORECASE)
            if match:
                subject = match.group(1).strip().rstrip('?')
                template = intent_templates[last_intent]
                augmented = f"{template} {subject}?"
                return augmented, True
    
    # If query starts with "how about X", similar logic
    if re.match(r'^how about\b', lowered):
        if last_intent in intent_templates:
            match = re.search(r'^how about\s+(.+?)[\?]?$', query, re.IGNORECASE)
            if match:
                subject = match.group(1).strip().rstrip('?')
                # For "how about", use appropriate phrasing
                if last_intent == 'risk_analysis':
                    augmented = f"How risky is {subject}?"
                elif last_intent == 'valuation':
                    augmented = f"Is {subject} overvalued?"
                elif last_intent == 'forecast':
                    augmented = f"What's the outlook for {subject}?"
                else:
                    augmented = f"Tell me about {subject}"
                return augmented, True
    
    return query, False


__all__ = [
    'should_carry_over_intent',
    'augment_query_with_intent',
]

