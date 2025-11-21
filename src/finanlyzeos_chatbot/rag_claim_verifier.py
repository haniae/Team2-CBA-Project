"""
Claim-Level Verification (Self-RAG / CoVe-Style)

Verifies each claim in generated answers against retrieved documents:
- Labels each sentence as: SUPPORTED / CONTRADICTED / NOT_FOUND
- Downgrades confidence if too many unsupported claims
- Optionally regenerates more cautious answers
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

LOGGER = logging.getLogger(__name__)


class ClaimStatus(Enum):
    """Status of a claim verification."""
    SUPPORTED = "supported"  # Claim is supported by retrieved documents
    CONTRADICTED = "contradicted"  # Claim contradicts retrieved documents
    NOT_FOUND = "not_found"  # No evidence found for claim
    UNCERTAIN = "uncertain"  # Ambiguous or unclear


@dataclass
class VerifiedClaim:
    """A verified claim from an answer."""
    sentence: str
    status: ClaimStatus
    supporting_docs: List[str]  # Document IDs or excerpts that support/contradict
    confidence: float  # 0-1 confidence in verification
    reasoning: Optional[str] = None  # Explanation of verification


@dataclass
class ClaimVerificationResult:
    """Result of claim-level verification."""
    claims: List[VerifiedClaim]
    num_supported: int
    num_contradicted: int
    num_not_found: int
    overall_confidence: float  # 0-1
    should_regenerate: bool  # Whether to regenerate answer
    suggested_response: Optional[str] = None  # Suggested response if confidence too low


class ClaimVerifier:
    """
    Verifies claims in generated answers against retrieved documents.
    
    Uses LLM to check each sentence against retrieved context.
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize claim verifier.
        
        Args:
            llm_client: LLM client for verification (optional, will use OpenAI if available)
        """
        self.llm_client = llm_client
    
    def verify_answer(
        self,
        answer: str,
        retrieved_docs: List[str],
        doc_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> ClaimVerificationResult:
        """
        Verify each claim in the answer against retrieved documents.
        
        Args:
            answer: Generated answer text
            retrieved_docs: List of retrieved document texts
            doc_metadata: Optional metadata for each document
        
        Returns:
            ClaimVerificationResult with verified claims
        """
        # Split answer into sentences
        sentences = self._split_into_sentences(answer)
        
        verified_claims = []
        for sentence in sentences:
            if not sentence.strip() or len(sentence.strip()) < 10:
                continue  # Skip very short sentences
            
            claim = self._verify_claim(sentence, retrieved_docs, doc_metadata)
            verified_claims.append(claim)
        
        # Compute statistics
        num_supported = sum(1 for c in verified_claims if c.status == ClaimStatus.SUPPORTED)
        num_contradicted = sum(1 for c in verified_claims if c.status == ClaimStatus.CONTRADICTED)
        num_not_found = sum(1 for c in verified_claims if c.status == ClaimStatus.NOT_FOUND)
        
        # Overall confidence: weighted average
        if verified_claims:
            overall_confidence = sum(c.confidence for c in verified_claims) / len(verified_claims)
        else:
            overall_confidence = 0.0
        
        # Decide if regeneration needed
        should_regenerate = (
            overall_confidence < 0.5 or
            num_contradicted > len(verified_claims) * 0.2 or
            num_not_found > len(verified_claims) * 0.5
        )
        
        suggested_response = None
        # Note: Removed automatic disclaimer generation
        # If confidence is low, the system will handle it contextually
        
        return ClaimVerificationResult(
            claims=verified_claims,
            num_supported=num_supported,
            num_contradicted=num_contradicted,
            num_not_found=num_not_found,
            overall_confidence=overall_confidence,
            should_regenerate=should_regenerate,
            suggested_response=suggested_response,
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with nltk)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _verify_claim(
        self,
        claim: str,
        retrieved_docs: List[str],
        doc_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> VerifiedClaim:
        """
        Verify a single claim against retrieved documents.
        
        Args:
            claim: Claim sentence to verify
            retrieved_docs: Retrieved document texts
            doc_metadata: Optional metadata
        
        Returns:
            VerifiedClaim
        """
        # Simple heuristic-based verification (can be enhanced with LLM)
        # Check if claim keywords appear in documents
        claim_lower = claim.lower()
        claim_keywords = set(re.findall(r'\b\w+\b', claim_lower))
        
        supporting_docs = []
        contradictions = []
        
        for i, doc in enumerate(retrieved_docs):
            doc_lower = doc.lower()
            doc_keywords = set(re.findall(r'\b\w+\b', doc_lower))
            
            # Check for keyword overlap
            overlap = claim_keywords & doc_keywords
            overlap_ratio = len(overlap) / len(claim_keywords) if claim_keywords else 0
            
            if overlap_ratio > 0.3:  # At least 30% keyword overlap
                # Check for contradiction keywords
                contradiction_keywords = ["not", "never", "no", "cannot", "unable", "failed"]
                has_contradiction = any(
                    keyword in doc_lower and keyword not in claim_lower
                    for keyword in contradiction_keywords
                )
                
                if has_contradiction:
                    contradictions.append(f"doc_{i}")
                else:
                    supporting_docs.append(f"doc_{i}")
        
        # Determine status
        if supporting_docs:
            status = ClaimStatus.SUPPORTED
            confidence = min(1.0, 0.5 + len(supporting_docs) * 0.1)
        elif contradictions:
            status = ClaimStatus.CONTRADICTED
            confidence = 0.3
        else:
            status = ClaimStatus.NOT_FOUND
            confidence = 0.2
        
        return VerifiedClaim(
            sentence=claim,
            status=status,
            supporting_docs=supporting_docs,
            confidence=confidence,
            reasoning=f"Found in {len(supporting_docs)} docs, contradicted in {len(contradictions)} docs",
        )
    
    def format_verification_for_ui(self, result: ClaimVerificationResult) -> str:
        """
        Format verification result for UI display.
        
        Args:
            result: ClaimVerificationResult
        
        Returns:
            Formatted string with verification status
        """
        lines = []
        lines.append(f"**Claim Verification**: {result.num_supported} supported, "
                    f"{result.num_contradicted} contradicted, {result.num_not_found} not found")
        lines.append(f"**Overall Confidence**: {result.overall_confidence:.1%}")
        
        if result.should_regenerate:
            lines.append("⚠️ **Warning**: Low confidence - consider regenerating answer")
        
        return "\n".join(lines)

