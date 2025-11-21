"""
Grounded Decision Layer - Safety Module for RAG

Implements grounded decision-making before answering:
- Low confidence detection
- Source contradiction detection
- Partial parse fallback
- Information sufficiency checks
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .rag_retriever import RetrievalResult

LOGGER = logging.getLogger(__name__)


@dataclass
class GroundedDecision:
    """Decision about whether to answer or request clarification."""
    should_answer: bool
    confidence: float
    reason: str
    suggested_response: Optional[str] = None
    contradictions: List[str] = None
    missing_info: List[str] = None


class GroundedDecisionLayer:
    """
    Grounded decision layer for RAG safety.
    
    Checks retrieval quality and data consistency before answering.
    """
    
    def __init__(
        self,
        min_confidence_threshold: float = 0.25,
        require_min_docs: int = 1,
        check_contradictions: bool = True,
    ):
        """
        Initialize grounded decision layer.
        
        Args:
            min_confidence_threshold: Minimum confidence to answer (default 0.25)
            require_min_docs: Minimum documents required (default 1)
            check_contradictions: Check for source contradictions (default True)
        """
        self.min_confidence_threshold = min_confidence_threshold
        self.require_min_docs = require_min_docs
        self.check_contradictions = check_contradictions
    
    def make_decision(
        self,
        query: str,
        result: RetrievalResult,
        overall_confidence: float,
        parsed_tickers: List[str],
    ) -> GroundedDecision:
        """
        Make grounded decision about whether to answer.
        
        Args:
            query: User query
            result: Retrieval result
            overall_confidence: Overall retrieval confidence (from fusion)
            parsed_tickers: Tickers extracted from query
        
        Returns:
            GroundedDecision with recommendation
        """
        reasons = []
        contradictions = []
        missing_info = []
        should_answer = True
        
        # Check 1: Low confidence threshold
        if overall_confidence < self.min_confidence_threshold:
            should_answer = False
            reasons.append(
                f"Retrieval confidence ({overall_confidence:.2f}) below threshold "
                f"({self.min_confidence_threshold:.2f})"
            )
            suggested = None  # Let the system handle low confidence naturally
            return GroundedDecision(
                should_answer=False,
                confidence=overall_confidence,
                reason="; ".join(reasons),
                suggested_response=suggested,
            )
        
        # Check 2: Minimum documents required
        total_docs = len(result.sec_narratives) + len(result.uploaded_docs)
        if total_docs < self.require_min_docs:
            should_answer = False
            reasons.append(f"Insufficient documents retrieved ({total_docs} < {self.require_min_docs})")
            suggested = None  # Let the system handle insufficient documents naturally
            return GroundedDecision(
                should_answer=False,
                confidence=overall_confidence,
                reason="; ".join(reasons),
                suggested_response=suggested,
            )
        
        # Check 3: Source contradictions (if enabled)
        if self.check_contradictions:
            contradictions = self._detect_contradictions(result)
            if contradictions:
                reasons.append(f"Found {len(contradictions)} potential contradictions")
                # Don't block answer, but flag it
        
        # Check 4: Missing information (tickers parsed but no data)
        if parsed_tickers and not result.metrics:
            missing_info.append(f"No metrics found for tickers: {', '.join(parsed_tickers)}")
            reasons.append("Tickers identified but no metric data retrieved")
            # Don't block answer, but flag it
        
        # Check 5: Query parsing quality
        if not parsed_tickers and any(keyword in query.lower() for keyword in ["revenue", "earnings", "profit", "stock"]):
            missing_info.append("Query mentions financial terms but no tickers identified")
            reasons.append("Query may be incomplete or ambiguous")
            # Don't block answer, but flag it
        
        # Determine suggested response if issues found
        suggested = None  # Let the system handle contradictions naturally without generic messages
        
        return GroundedDecision(
            should_answer=should_answer,
            confidence=overall_confidence,
            reason="; ".join(reasons) if reasons else "All checks passed",
            suggested_response=suggested,
            contradictions=contradictions,
            missing_info=missing_info,
        )
    
    def _detect_contradictions(self, result: RetrievalResult) -> List[str]:
        """
        Detect contradictions between sources.
        
        Example: SQL says revenue = $100B, but SEC narrative says revenue declined to $80B
        """
        contradictions = []
        
        # Check SQL metrics vs SEC narratives for same metric
        # This is a simplified check - in production, you'd do more sophisticated comparison
        
        # Extract revenue mentions from narratives
        revenue_mentions = []
        for doc in result.sec_narratives:
            text_lower = doc.text.lower()
            if "revenue" in text_lower or "sales" in text_lower:
                # Look for numbers near revenue mentions
                import re
                numbers = re.findall(r'\$?[\d,]+\.?\d*\s*[BM]?', text_lower)
                if numbers:
                    revenue_mentions.append((doc.text[:200], numbers))
        
        # Compare with SQL metrics
        sql_revenue = None
        for metric in result.metrics:
            if metric.get("metric") in ["revenue", "total_revenue", "net_sales"]:
                sql_revenue = metric.get("value")
                break
        
        # Simple contradiction check (can be enhanced)
        if sql_revenue and revenue_mentions:
            # In production, you'd parse and compare numbers more carefully
            # This is a placeholder for the concept
            pass
        
        return contradictions
    
    def get_grounded_prompt_instruction(
        self,
        decision: GroundedDecision,
        overall_confidence: float,
    ) -> str:
        """
        Get instruction for LLM based on grounded decision.
        
        Args:
            decision: GroundedDecision from make_decision
            overall_confidence: Overall retrieval confidence
        
        Returns:
            Instruction string to add to prompt
        """
        instructions = []
        
        # Confidence-based tone
        if overall_confidence >= 0.7:
            instructions.append("HIGH CONFIDENCE: You have highly relevant information. Provide a confident, detailed answer.")
        elif overall_confidence >= 0.4:
            instructions.append("MEDIUM CONFIDENCE: You have moderately relevant information. Provide a helpful answer but acknowledge any uncertainties.")
        else:
            instructions.append("LOW CONFIDENCE: You have limited relevant information. Be cautious and explicit about information gaps.")
        
        # Contradictions
        if decision.contradictions:
            instructions.append(f"⚠️ SOURCE CONTRADICTIONS DETECTED: {len(decision.contradictions)} potential contradictions found. Acknowledge disagreements in your response.")
        
        # Missing info
        if decision.missing_info:
            instructions.append(f"⚠️ MISSING INFORMATION: {len(decision.missing_info)} information gaps detected. Mention what information is unavailable.")
        
        return "\n".join(instructions)

