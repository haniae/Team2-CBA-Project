"""
Conditional statement detection for natural language queries.

Handles:
- If-then statements: "if revenue > $10B then show risk"
- When-then statements: "when P/E < 20 then buy"
- Unless statements: "unless debt > $50B, show details"
- Conditional operators: >, <, =, >=, <=, !=
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class ConditionalType(Enum):
    """Types of conditional statements"""
    IF_THEN = "if_then"           # if X then Y
    WHEN_THEN = "when_then"       # when X then Y
    UNLESS = "unless"             # unless X, Y
    WHENEVER = "whenever"         # whenever X, Y


class ComparisonOperator(Enum):
    """Comparison operators in conditions"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUALS = "="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="


@dataclass
class ConditionalStatement:
    """
    Represents a conditional statement in text.
    """
    conditional_type: ConditionalType
    condition: str               # The condition clause (e.g., "revenue > $10B")
    action: str                  # The action clause (e.g., "show risk")
    operator: Optional[ComparisonOperator]  # Detected operator if any
    confidence: float            # Confidence score (0.0 to 1.0)
    position: int               # Position in text
    
    def __repr__(self):
        return (f"ConditionalStatement(type={self.conditional_type.value}, "
                f"condition='{self.condition}', "
                f"action='{self.action}', "
                f"confidence={self.confidence:.2f})")


class ConditionalDetector:
    """
    Detect and parse conditional statements in natural language queries.
    """
    
    # IF-THEN patterns - EXPANDED
    IF_THEN_PATTERNS = [
        r'\bif\s+(.*?)\s+then\s+(.*?)(?:\.|$)',
        r'\bif\s+(.*?),\s*(.*?)(?:\.|$)',
        # NEW: More if variations
        r'\bshould\s+(.*?)\s+then\s+(.*?)(?:\.|$)',
        r'\bprovided\s+(?:that\s+)?(.*?),\s*(.*?)(?:\.|$)',
        r'\bassuming\s+(?:that\s+)?(.*?),\s*(.*?)(?:\.|$)',
    ]
    
    # WHEN-THEN patterns - EXPANDED
    WHEN_THEN_PATTERNS = [
        r'\bwhen\s+(.*?)\s+then\s+(.*?)(?:\.|$)',
        r'\bwhen\s+(.*?),\s*(.*?)(?:\.|$)',
        # NEW: More when variations
        r'\bonce\s+(.*?),\s*(.*?)(?:\.|$)',
        r'\bas\s+soon\s+as\s+(.*?),\s*(.*?)(?:\.|$)',
    ]
    
    # UNLESS patterns - EXPANDED
    UNLESS_PATTERNS = [
        r'\bunless\s+(.*?),\s*(.*?)(?:\.|$)',
        r'\bunless\s+(.*?)\s+then\s+(.*?)(?:\.|$)',
        # NEW: More unless variations
        r'\bexcept\s+(?:if|when)\s+(.*?),\s*(.*?)(?:\.|$)',
    ]
    
    # WHENEVER patterns - EXPANDED
    WHENEVER_PATTERNS = [
        r'\bwhenever\s+(.*?),\s*(.*?)(?:\.|$)',
        r'\bwhenever\s+(.*?)\s+then\s+(.*?)(?:\.|$)',
        # NEW: More whenever variations
        r'\beach\s+time\s+(.*?),\s*(.*?)(?:\.|$)',
        r'\bevery\s+time\s+(.*?),\s*(.*?)(?:\.|$)',
    ]
    
    # NEW: False positive patterns (DON'T detect as conditionals)
    FALSE_POSITIVE_PATTERNS = [
        # Questions about conditions
        r'\bwhat\s+if\b',
        r'\bwhat\s+happens\s+(?:if|when)\b',
        # Hypotheticals without action
        r'\bif\s+only\b',
        r'\bif\s+possible\b',
        # Common phrases
        r'\beven\s+if\b',
        r'\bas\s+if\b',
    ]
    
    # Comparison operator patterns - MASSIVELY EXPANDED
    OPERATOR_PATTERNS = {
        ComparisonOperator.GREATER_EQUAL: [
            r'>=|≥|greater\s+than\s+or\s+equal\s+to|at\s+least',
            # NEW: More variations
            r'no\s+less\s+than|minimum\s+of|not\s+below',
        ],
        ComparisonOperator.LESS_EQUAL: [
            r'<=|≤|less\s+than\s+or\s+equal\s+to|at\s+most',
            # NEW: More variations
            r'no\s+more\s+than|maximum\s+of|not\s+above|up\s+to',
        ],
        ComparisonOperator.NOT_EQUAL: [
            r'!=|≠|not\s+equal\s+to|different\s+from',
            # NEW: More variations
            r'not\s+the\s+same\s+as|differs\s+from|other\s+than',
        ],
        ComparisonOperator.GREATER_THAN: [
            r'>|greater\s+than|more\s+than|above|over|exceeds?|higher\s+than',
            # NEW: More variations
            r'surpasses|tops|beats|outperforms|beyond',
            r'in\s+excess\s+of|upwards?\s+of',
        ],
        ComparisonOperator.LESS_THAN: [
            r'<|less\s+than|under|below|fewer\s+than|lower\s+than',
            # NEW: More variations
            r'short\s+of|beneath|inferior\s+to|shy\s+of',
        ],
        ComparisonOperator.EQUALS: [
            r'=|equals?|is|are|==',
            # NEW: More variations
            r'matches|same\s+as|identical\s+to|equivalent\s+to',
        ],
    }
    
    def __init__(self):
        """Initialize the conditional detector"""
        self._if_then_patterns = [re.compile(p, re.IGNORECASE) for p in self.IF_THEN_PATTERNS]
        self._when_then_patterns = [re.compile(p, re.IGNORECASE) for p in self.WHEN_THEN_PATTERNS]
        self._unless_patterns = [re.compile(p, re.IGNORECASE) for p in self.UNLESS_PATTERNS]
        self._whenever_patterns = [re.compile(p, re.IGNORECASE) for p in self.WHENEVER_PATTERNS]
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
        self._operator_patterns = {
            op: [re.compile(p, re.IGNORECASE) for p in patterns]
            for op, patterns in self.OPERATOR_PATTERNS.items()
        }
    
    def detect_conditionals(self, text: str) -> List[ConditionalStatement]:
        """
        Detect all conditional statements in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of ConditionalStatement objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        conditionals = []
        
        # Check each conditional type
        conditionals.extend(self._detect_if_then(text))
        conditionals.extend(self._detect_when_then(text))
        conditionals.extend(self._detect_unless(text))
        conditionals.extend(self._detect_whenever(text))
        
        # Sort by position
        conditionals.sort(key=lambda x: x.position)
        
        return conditionals
    
    def _detect_if_then(self, text: str) -> List[ConditionalStatement]:
        """Detect IF-THEN statements"""
        conditionals = []
        
        for pattern in self._if_then_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    condition = groups[0].strip()
                    action = groups[1].strip()
                    
                    # NEW: Skip if this specific match is a false positive
                    context_start = max(0, match.start() - 15)
                    context_end = min(len(text), match.end() + 15)
                    local_context = text[context_start:context_end]
                    if self._is_false_positive(local_context):
                        continue
                    
                    # Extract operator from condition
                    operator = self._extract_operator(condition)
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence_enhanced(
                        text, "if_then", condition, action, operator
                    )
                    
                    conditionals.append(ConditionalStatement(
                        conditional_type=ConditionalType.IF_THEN,
                        condition=condition,
                        action=action,
                        operator=operator,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        return conditionals
    
    def _detect_when_then(self, text: str) -> List[ConditionalStatement]:
        """Detect WHEN-THEN statements"""
        conditionals = []
        
        for pattern in self._when_then_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    condition = groups[0].strip()
                    action = groups[1].strip()
                    
                    operator = self._extract_operator(condition)
                    confidence = self._calculate_confidence_enhanced(
                        text, "when_then", condition, action, operator
                    )
                    
                    conditionals.append(ConditionalStatement(
                        conditional_type=ConditionalType.WHEN_THEN,
                        condition=condition,
                        action=action,
                        operator=operator,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        return conditionals
    
    def _detect_unless(self, text: str) -> List[ConditionalStatement]:
        """Detect UNLESS statements"""
        conditionals = []
        
        for pattern in self._unless_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    condition = groups[0].strip()
                    action = groups[1].strip()
                    
                    operator = self._extract_operator(condition)
                    confidence = self._calculate_confidence_enhanced(
                        text, "unless", condition, action, operator
                    )
                    
                    conditionals.append(ConditionalStatement(
                        conditional_type=ConditionalType.UNLESS,
                        condition=condition,
                        action=action,
                        operator=operator,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        return conditionals
    
    def _detect_whenever(self, text: str) -> List[ConditionalStatement]:
        """Detect WHENEVER statements"""
        conditionals = []
        
        for pattern in self._whenever_patterns:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    condition = groups[0].strip()
                    action = groups[1].strip()
                    
                    operator = self._extract_operator(condition)
                    confidence = self._calculate_confidence_enhanced(
                        text, "whenever", condition, action, operator
                    )
                    
                    conditionals.append(ConditionalStatement(
                        conditional_type=ConditionalType.WHENEVER,
                        condition=condition,
                        action=action,
                        operator=operator,
                        confidence=confidence,
                        position=match.start()
                    ))
        
        return conditionals
    
    def _extract_operator(self, condition: str) -> Optional[ComparisonOperator]:
        """
        Extract comparison operator from condition clause.
        
        Returns:
            ComparisonOperator if found, None otherwise
        """
        if not condition:
            return None
        
        # Check each operator type (order matters - most specific first)
        for operator, patterns in self._operator_patterns.items():
            for pattern in patterns:
                if pattern.search(condition):
                    return operator
        
        return None
    
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
        conditional_type: str,
        condition: str,
        action: str
    ) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, conditional_type, condition, action, None)
    
    def _calculate_confidence_enhanced(
        self,
        text: str,
        conditional_type: str,
        condition: str,
        action: str,
        operator: Optional[ComparisonOperator]
    ) -> float:
        """
        Calculate confidence for conditional detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-3 features.
        """
        confidence = 0.80  # Base confidence (conditionals are usually explicit)
        
        # Boost for explicit symbol operators
        if any(op in condition for op in ['>', '<', '=', '>=', '<=', '!=']):
            confidence += 0.12
        elif operator:  # Natural language operator detected
            confidence += 0.08
        
        # Boost for financial terms in condition
        financial_terms = ['revenue', 'profit', 'margin', 'P/E', 'EPS', 'debt', 'growth', 
                          'earnings', 'ROE', 'ROA', 'cash', 'valuation']
        financial_matches = sum(1 for term in financial_terms if term.lower() in condition.lower())
        if financial_matches > 0:
            confidence += min(0.08, financial_matches * 0.04)
        
        # Boost for clear action verbs
        action_verbs = ['show', 'display', 'analyze', 'get', 'find', 'buy', 'sell', 
                       'alert', 'notify', 'flag', 'warn', 'recommend']
        if any(verb in action.lower() for verb in action_verbs):
            confidence += 0.06
        
        # NEW: Boost for specific conditional types
        if conditional_type in ['if_then', 'unless']:
            confidence += 0.02  # More explicit conditionals
        
        # NEW: Boost for numeric values in condition (specific thresholds)
        if re.search(r'\b\d+(?:\.\d+)?(?:[BMK]|%|\$)?\b', condition):
            confidence += 0.04
        
        return min(1.0, max(0.5, confidence))
    
    def has_conditional(self, text: str) -> bool:
        """
        Quick check if text contains conditional statements.
        
        Returns:
            True if conditional detected, False otherwise
        """
        if not text:
            return False
        
        conditionals = self.detect_conditionals(text)
        return len(conditionals) > 0

