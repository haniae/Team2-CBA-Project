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
    
    def fuse_sparse_dense(
        self,
        dense_hits: List[RetrievedDocument],
        sparse_hits: List[RetrievedDocument],
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
    ) -> List[RetrievedDocument]:
        """
        Fuse sparse (BM25) and dense (embedding) retrieval results.
        
        Args:
            dense_hits: Documents from dense (embedding) retrieval
            sparse_hits: Documents from sparse (BM25) retrieval
            dense_weight: Weight for dense scores (default 0.6)
            sparse_weight: Weight for sparse scores (default 0.4)
        
        Returns:
            Fused list of documents sorted by combined score
        """
        # Create document ID -> document mapping
        # Use text + metadata as unique identifier
        doc_map: Dict[str, RetrievedDocument] = {}
        
        # Add dense hits
        for doc in dense_hits:
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
                # Normalize dense score (assume it's similarity 0-1 or distance)
                if doc.score is not None:
                    # If score > 1, it's likely a distance - convert to similarity
                    if doc.score > 1.0:
                        dense_score = 1.0 / (1.0 + doc.score)
                    else:
                        dense_score = doc.score
                else:
                    dense_score = 0.0
                doc_map[doc_id].metadata["_dense_score"] = dense_score
                doc_map[doc_id].metadata["_sparse_score"] = 0.0
        
        # Add sparse hits
        for doc in sparse_hits:
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc
                doc_map[doc_id].metadata["_dense_score"] = 0.0
                doc_map[doc_id].metadata["_sparse_score"] = 0.0
            
            # Normalize sparse score (BM25 scores can be any positive number)
            if doc.score is not None:
                # Normalize BM25 score (use sigmoid-like normalization)
                # BM25 scores are typically 0-20, normalize to 0-1
                sparse_score = min(1.0, doc.score / 10.0)  # Rough normalization
            else:
                sparse_score = 0.0
            
            doc_map[doc_id].metadata["_sparse_score"] = max(
                doc_map[doc_id].metadata.get("_sparse_score", 0.0),
                sparse_score
            )
        
        # Compute fused scores
        fused_docs = []
        for doc_id, doc in doc_map.items():
            dense_score = doc.metadata.get("_dense_score", 0.0)
            sparse_score = doc.metadata.get("_sparse_score", 0.0)
            
            # Fuse scores
            fused_score = (dense_score * dense_weight) + (sparse_score * sparse_weight)
            
            # Update document with fused score
            doc.score = fused_score
            doc.metadata["_fused_score"] = fused_score
            doc.metadata["_dense_contrib"] = dense_score * dense_weight
            doc.metadata["_sparse_contrib"] = sparse_score * sparse_weight
            
            fused_docs.append(doc)
        
        # Sort by fused score (descending)
        fused_docs.sort(key=lambda x: x.score or 0.0, reverse=True)
        
        LOGGER.debug(
            f"Sparse-dense fusion: {len(dense_hits)} dense + {len(sparse_hits)} sparse "
            f"→ {len(fused_docs)} unique, {len([d for d in fused_docs if d.metadata.get('_dense_score', 0) > 0])} with dense, "
            f"{len([d for d in fused_docs if d.metadata.get('_sparse_score', 0) > 0])} with sparse"
        )
        
        return fused_docs
    
    def _get_doc_id(self, doc: RetrievedDocument) -> str:
        """Generate unique document ID from text and metadata."""
        # Use text hash + source type + key metadata as ID
        text_hash = hash(doc.text[:100])  # First 100 chars
        metadata_str = str(sorted(doc.metadata.items())) if doc.metadata else ""
        return f"{doc.source_type}_{text_hash}_{hash(metadata_str)}"

    
    def get_confidence_instruction(self, confidence: float) -> str:
        """
        Get instruction for LLM based on retrieval confidence.
        
        Args:
            confidence: Overall retrieval confidence (0-1)
        
        Returns:
            Instruction string for LLM
        """
        if confidence >= 0.7:
            return None  # Let model handle high confidence naturally
        elif confidence >= 0.4:
            return None  # Let model handle medium confidence naturally
        else:
            return None  # Let model handle low confidence naturally

