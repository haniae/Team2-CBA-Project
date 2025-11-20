"""
RAG Source Fusion - Score Normalization and Confidence Fusion

Implements source fusion layer that:
- Normalizes similarity scores across sources
- Weights by source reliability
- Merges into single ranked result list
- Computes retrieval confidence scores
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .rag_retriever import RetrievedDocument, RetrievalResult

LOGGER = logging.getLogger(__name__)


# Source reliability weights (higher = more trusted)
SOURCE_WEIGHTS = {
    "sql_metrics": 1.0,      # Structured data - most reliable
    "sql_facts": 1.0,        # Structured facts - most reliable
    "sec_narratives": 0.9,   # SEC filings - highly reliable
    "uploaded_docs": 0.7,    # User uploads - less reliable
    "macro_data": 0.6,       # Economic indicators - context only
    "ml_forecasts": 0.5,     # Forecasts - predictions, not facts
    "portfolio_data": 0.8,   # Portfolio data - user-specific
}


@dataclass
class FusedDocument:
    """Document with fused score and source weighting."""
    document: RetrievedDocument
    source_weight: float
    normalized_score: float
    fused_score: float  # normalized_score * source_weight
    confidence_level: str  # "high", "medium", "low"


class SourceFusion:
    """
    Source fusion layer for RAG retrieval.
    
    Normalizes scores across sources and applies reliability weights.
    """
    
    def __init__(self, source_weights: Optional[Dict[str, float]] = None):
        """
        Initialize source fusion.
        
        Args:
            source_weights: Custom source weights (defaults to SOURCE_WEIGHTS)
        """
        self.source_weights = source_weights or SOURCE_WEIGHTS
    
    def normalize_scores(self, documents: List[RetrievedDocument], source_type: str) -> List[FusedDocument]:
        """
        Normalize scores for a single source.
        
        Args:
            documents: Retrieved documents from one source
            source_type: Type of source (e.g., "sec_narratives", "uploaded_docs")
        
        Returns:
            List of FusedDocuments with normalized scores
        """
        if not documents:
            return []
        
        # Get source weight
        source_weight = self.source_weights.get(source_type, 0.5)
        
        # Extract scores
        scores = [doc.score if doc.score is not None else 0.0 for doc in documents]
        
        # Normalize scores to [0, 1] range
        # For cosine similarity: higher is better (1.0 = identical, 0.0 = orthogonal)
        # For distance: lower is better (0.0 = identical, higher = different)
        # ChromaDB returns distances, so we need to convert
        
        if scores:
            # Check if scores are distances (higher = worse) or similarities (higher = better)
            # ChromaDB typically returns distances, so we normalize by inverting
            max_score = max(scores)
            min_score = min(scores)
            
            if max_score > 1.0:
                # Likely distances - normalize by inverting
                normalized = [(1.0 / (1.0 + score)) for score in scores]
            else:
                # Likely similarities - normalize to [0, 1]
                if max_score > min_score:
                    normalized = [(score - min_score) / (max_score - min_score) for score in scores]
                else:
                    normalized = [1.0 for _ in scores]
        else:
            normalized = [0.0 for _ in documents]
        
        # Create fused documents
        fused = []
        for doc, norm_score in zip(documents, normalized):
            fused_score = norm_score * source_weight
            
            # Determine confidence level
            if fused_score >= 0.7:
                confidence = "high"
            elif fused_score >= 0.4:
                confidence = "medium"
            else:
                confidence = "low"
            
            fused.append(FusedDocument(
                document=doc,
                source_weight=source_weight,
                normalized_score=norm_score,
                fused_score=fused_score,
                confidence_level=confidence,
            ))
        
        return fused
    
    def fuse_all_sources(self, result: RetrievalResult) -> Tuple[List[FusedDocument], float]:
        """
        Fuse all retrieval sources into single ranked list.
        
        Args:
            result: RetrievalResult from RAGRetriever
        
        Returns:
            Tuple of (fused_documents, overall_confidence)
        """
        all_fused = []
        
        # Fuse SEC narratives
        sec_fused = self.normalize_scores(result.sec_narratives, "sec_narratives")
        all_fused.extend(sec_fused)
        
        # Fuse uploaded docs
        uploaded_fused = self.normalize_scores(result.uploaded_docs, "uploaded_docs")
        all_fused.extend(uploaded_fused)
        
        # Sort by fused score (descending)
        all_fused.sort(key=lambda x: x.fused_score, reverse=True)
        
        # Compute overall confidence (weighted average of top-K)
        top_k = min(5, len(all_fused))
        if top_k > 0:
            top_scores = [f.fused_score for f in all_fused[:top_k]]
            overall_confidence = sum(top_scores) / len(top_scores)
        else:
            overall_confidence = 0.0
        
        LOGGER.debug(
            f"Source fusion: {len(all_fused)} documents, "
            f"confidence={overall_confidence:.3f}"
        )
        
        return all_fused, overall_confidence
    
    def get_confidence_instruction(self, confidence: float) -> str:
        """
        Get instruction for LLM based on retrieval confidence.
        
        Args:
            confidence: Overall retrieval confidence (0-1)
        
        Returns:
            Instruction string for LLM
        """
        if confidence >= 0.7:
            return (
                "High confidence: The retrieved documents are highly relevant. "
                "You can provide a confident, detailed answer."
            )
        elif confidence >= 0.4:
            return (
                "Medium confidence: The retrieved documents are moderately relevant. "
                "Provide a helpful answer but acknowledge any uncertainties."
            )
        else:
            return (
                "Low confidence: The retrieved documents have limited relevance. "
                "Be cautious and explicit about information gaps. "
                "If the retrieved data doesn't contain enough information, say so explicitly."
            )

