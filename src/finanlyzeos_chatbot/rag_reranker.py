"""
RAG Reranking Module - Second-Pass Relevance Scoring

Implements reranking stage for production-grade RAG:
- Cross-encoder reranking (more accurate than bi-encoder similarity)
- LLM-based reranking (optional, for complex queries)
- Score normalization and fusion across sources
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .rag_retriever import RetrievedDocument

LOGGER = logging.getLogger(__name__)

# Optional imports for reranking
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None


@dataclass
class RerankedDocument(RetrievedDocument):
    """Retrieved document with reranking scores."""
    initial_score: Optional[float] = None  # Original similarity score
    rerank_score: Optional[float] = None   # Reranking score
    final_score: Optional[float] = None   # Combined/final score


class Reranker:
    """
    Reranker for retrieved documents.
    
    Uses cross-encoder to score (query, document) pairs for true relevance.
    More accurate than bi-encoder cosine similarity but slower.
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_reranking: bool = True,
    ):
        """
        Initialize reranker.
        
        Args:
            model_name: Cross-encoder model for reranking
            use_reranking: Whether to enable reranking (can be disabled for speed)
        """
        self.use_reranking = use_reranking and CROSS_ENCODER_AVAILABLE
        
        if self.use_reranking:
            try:
                LOGGER.info(f"Loading reranking model: {model_name}")
                self.model = CrossEncoder(model_name)
                LOGGER.info("Reranker initialized successfully")
            except Exception as e:
                LOGGER.warning(f"Failed to load reranking model: {e}")
                self.use_reranking = False
                self.model = None
        else:
            self.model = None
            if not CROSS_ENCODER_AVAILABLE:
                LOGGER.debug("Cross-encoder not available. Install: pip install sentence-transformers")
    
    def rerank(
        self,
        query: str,
        documents: List[RetrievedDocument],
        top_k: Optional[int] = None,
        score_threshold: float = 0.0,
    ) -> List[RerankedDocument]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: User query
            documents: Initial retrieved documents
            top_k: Return top K documents (None = return all)
            score_threshold: Minimum rerank score to include
        
        Returns:
            Reranked documents sorted by relevance (highest first)
        """
        if not documents:
            return []
        
        if not self.use_reranking or not self.model:
            # No reranking: return documents as-is with original scores
            return [
                RerankedDocument(
                    text=doc.text,
                    source_type=doc.source_type,
                    metadata=doc.metadata,
                    score=doc.score,
                    initial_score=doc.score,
                    rerank_score=None,
                    final_score=doc.score,
                )
                for doc in documents
            ]
        
        # Prepare (query, document) pairs for cross-encoder
        pairs = [(query, doc.text) for doc in documents]
        
        try:
            # Score all pairs (cross-encoder is slower but more accurate)
            rerank_scores = self.model.predict(pairs)
            
            # Convert to list if single value
            if not isinstance(rerank_scores, list):
                rerank_scores = rerank_scores.tolist() if hasattr(rerank_scores, 'tolist') else [rerank_scores]
        except Exception as e:
            LOGGER.warning(f"Reranking failed: {e}, using original scores")
            rerank_scores = [doc.score or 0.0 for doc in documents]
        
        # Create reranked documents with combined scores
        reranked = []
        for doc, rerank_score in zip(documents, rerank_scores):
            # Normalize rerank score (cross-encoder outputs can vary)
            # Combine with initial score if available
            initial_score = doc.score if doc.score is not None else 0.0
            
            # Weighted combination: 70% rerank, 30% initial (tunable)
            final_score = 0.7 * float(rerank_score) + 0.3 * initial_score
            
            if final_score >= score_threshold:
                reranked.append(RerankedDocument(
                    text=doc.text,
                    source_type=doc.source_type,
                    metadata=doc.metadata,
                    score=final_score,  # Final combined score
                    initial_score=initial_score,
                    rerank_score=float(rerank_score),
                    final_score=final_score,
                ))
        
        # Sort by final score (descending)
        reranked.sort(key=lambda x: x.final_score or 0.0, reverse=True)
        
        # Return top K
        if top_k is not None:
            reranked = reranked[:top_k]
        
        LOGGER.debug(f"Reranked {len(documents)} documents -> {len(reranked)} above threshold")
        
        return reranked
    
    def rerank_multi_source(
        self,
        query: str,
        sec_docs: List[RetrievedDocument],
        uploaded_docs: List[RetrievedDocument],
        *,
        max_sec: int = 5,
        max_uploaded: int = 3,
        score_threshold: float = 0.0,
    ) -> Tuple[List[RerankedDocument], List[RerankedDocument]]:
        """
        Rerank documents from multiple sources with score normalization.
        
        Args:
            query: User query
            sec_docs: SEC filing documents
            uploaded_docs: Uploaded document chunks
            max_sec: Max SEC documents to return
            max_uploaded: Max uploaded documents to return
            score_threshold: Minimum score threshold
        
        Returns:
            Tuple of (reranked_sec_docs, reranked_uploaded_docs)
        """
        # Rerank each source separately
        reranked_sec = self.rerank(query, sec_docs, top_k=max_sec, score_threshold=score_threshold)
        reranked_uploaded = self.rerank(query, uploaded_docs, top_k=max_uploaded, score_threshold=score_threshold)
        
        return reranked_sec, reranked_uploaded

