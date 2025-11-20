"""
RAG Observability Module - Logging, Metrics, and Guardrails

Provides:
- Detailed logging of retrieval process
- Context window management
- Anomaly detection and guardrails
- Performance metrics
"""

from __future__ import annotations

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .rag_retriever import RetrievedDocument, RetrievalResult

LOGGER = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Metrics for a single retrieval operation."""
    query: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Retrieval counts
    num_sec_docs: int = 0
    num_uploaded_docs: int = 0
    num_metrics: int = 0
    num_facts: int = 0
    
    # Scores
    sec_scores: List[float] = field(default_factory=list)
    uploaded_scores: List[float] = field(default_factory=list)
    
    # Hybrid retrieval stats (sparse vs dense)
    dense_sec_count: int = 0  # Number of SEC docs from dense retrieval
    sparse_sec_count: int = 0  # Number of SEC docs from sparse retrieval
    dense_uploaded_count: int = 0  # Number of uploaded docs from dense retrieval
    sparse_uploaded_count: int = 0  # Number of uploaded docs from sparse retrieval
    dense_contributions: List[float] = field(default_factory=list)  # Dense score contributions
    sparse_contributions: List[float] = field(default_factory=list)  # Sparse score contributions
    
    # Timing
    retrieval_time_ms: float = 0.0
    reranking_time_ms: float = 0.0
    
    # Context window
    total_context_chars: int = 0
    context_truncated: bool = False
    
    # Anomalies
    low_score_warning: bool = False
    empty_retrieval: bool = False
    
    # Document IDs for traceability
    retrieved_doc_ids: List[str] = field(default_factory=list)


@dataclass
class RAGGuardrails:
    """Guardrails and thresholds for RAG system."""
    min_relevance_score: float = 0.3  # Minimum score to include document
    max_context_chars: int = 15000     # Max context length before truncation
    max_documents: int = 10            # Max documents to include
    warn_on_low_scores: bool = True   # Warn if all scores below threshold
    require_min_docs: int = 0         # Minimum documents required (0 = no requirement)


class RAGObserver:
    """Observer for RAG operations - logging, metrics, guardrails."""
    
    def __init__(self, guardrails: Optional[RAGGuardrails] = None):
        """Initialize observer with guardrails."""
        self.guardrails = guardrails or RAGGuardrails()
        self.metrics: List[RetrievalMetrics] = []
    
    def log_retrieval(
        self,
        query: str,
        result: RetrievalResult,
        retrieval_time_ms: float = 0.0,
        reranking_time_ms: float = 0.0,
    ) -> RetrievalMetrics:
        """Log a retrieval operation and return metrics."""
        metrics = RetrievalMetrics(
            query=query,
            num_sec_docs=len(result.sec_narratives),
            num_uploaded_docs=len(result.uploaded_docs),
            num_metrics=len(result.metrics),
            num_facts=len(result.facts),
            retrieval_time_ms=retrieval_time_ms,
            reranking_time_ms=reranking_time_ms,
        )
        
        # Extract scores
        metrics.sec_scores = [doc.score for doc in result.sec_narratives if doc.score is not None]
        metrics.uploaded_scores = [doc.score for doc in result.uploaded_docs if doc.score is not None]
        
        # Extract hybrid retrieval stats (sparse vs dense)
        for doc in result.sec_narratives:
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filing_id", "unknown")
            metrics.retrieved_doc_ids.append(f"sec:{doc_id}")
            
            # Check if document has sparse/dense contribution metadata
            dense_contrib = doc.metadata.get("_dense_contrib", 0.0)
            sparse_contrib = doc.metadata.get("_sparse_contrib", 0.0)
            
            if dense_contrib > 0:
                metrics.dense_sec_count += 1
                metrics.dense_contributions.append(dense_contrib)
            if sparse_contrib > 0:
                metrics.sparse_sec_count += 1
                metrics.sparse_contributions.append(sparse_contrib)
        
        for doc in result.uploaded_docs:
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filename", "unknown")
            metrics.retrieved_doc_ids.append(f"uploaded:{doc_id}")
            
            # Check if document has sparse/dense contribution metadata
            dense_contrib = doc.metadata.get("_dense_contrib", 0.0)
            sparse_contrib = doc.metadata.get("_sparse_contrib", 0.0)
            
            if dense_contrib > 0:
                metrics.dense_uploaded_count += 1
                metrics.dense_contributions.append(dense_contrib)
            if sparse_contrib > 0:
                metrics.sparse_uploaded_count += 1
                metrics.sparse_contributions.append(sparse_contrib)
        
        # Check for anomalies
        all_scores = metrics.sec_scores + metrics.uploaded_scores
        if all_scores:
            max_score = max(all_scores)
            if max_score < self.guardrails.min_relevance_score:
                metrics.low_score_warning = True
                if self.guardrails.warn_on_low_scores:
                    LOGGER.warning(
                        f"Low relevance scores detected (max={max_score:.3f} < {self.guardrails.min_relevance_score}). "
                        f"Query: {query[:100]}"
                    )
        
        if metrics.num_sec_docs == 0 and metrics.num_uploaded_docs == 0:
            metrics.empty_retrieval = True
            LOGGER.warning(f"Empty retrieval for query: {query[:100]}")
        
        # Store metrics
        self.metrics.append(metrics)
        
        # Log summary with hybrid retrieval stats
        hybrid_info = ""
        if metrics.dense_sec_count > 0 or metrics.sparse_sec_count > 0:
            avg_dense = sum(metrics.dense_contributions) / len(metrics.dense_contributions) if metrics.dense_contributions else 0.0
            avg_sparse = sum(metrics.sparse_contributions) / len(metrics.sparse_contributions) if metrics.sparse_contributions else 0.0
            hybrid_info = (
                f" | Hybrid: {metrics.dense_sec_count + metrics.dense_uploaded_count} dense, "
                f"{metrics.sparse_sec_count + metrics.sparse_uploaded_count} sparse "
                f"(dense_contrib={avg_dense:.2f}, sparse_contrib={avg_sparse:.2f})"
            )
        
        LOGGER.info(
            f"Retrieval: {metrics.num_sec_docs} SEC docs, {metrics.num_uploaded_docs} uploaded docs, "
            f"{metrics.num_metrics} metrics, {retrieval_time_ms:.1f}ms{hybrid_info}"
        )
        
        return metrics
    
    def apply_guardrails(
        self,
        result: RetrievalResult,
        query: str,
    ) -> RetrievalResult:
        """
        Apply guardrails to retrieval result.
        
        - Filter low-scoring documents
        - Truncate context if too long
        - Warn on anomalies
        """
        # Filter by minimum score
        filtered_sec = [
            doc for doc in result.sec_narratives
            if doc.score is None or doc.score >= self.guardrails.min_relevance_score
        ]
        
        filtered_uploaded = [
            doc for doc in result.uploaded_docs
            if doc.score is None or doc.score >= self.guardrails.min_relevance_score
        ]
        
        # Limit document count
        if len(filtered_sec) > self.guardrails.max_documents:
            filtered_sec = filtered_sec[:self.guardrails.max_documents]
            LOGGER.debug(f"Truncated SEC docs to {self.guardrails.max_documents}")
        
        if len(filtered_uploaded) > self.guardrails.max_documents:
            filtered_uploaded = filtered_uploaded[:self.guardrails.max_documents]
            LOGGER.debug(f"Truncated uploaded docs to {self.guardrails.max_documents}")
        
        # Check minimum document requirement
        total_docs = len(filtered_sec) + len(filtered_uploaded)
        if self.guardrails.require_min_docs > 0 and total_docs < self.guardrails.require_min_docs:
            LOGGER.warning(
                f"Insufficient documents retrieved ({total_docs} < {self.guardrails.require_min_docs}) "
                f"for query: {query[:100]}"
            )
        
        # Create filtered result
        filtered_result = RetrievalResult(
            metrics=result.metrics,
            facts=result.facts,
            sec_narratives=filtered_sec,
            uploaded_docs=filtered_uploaded,
            macro_data=result.macro_data,
            portfolio_data=result.portfolio_data,
            ml_forecasts=result.ml_forecasts,
        )
        
        return filtered_result
    
    def truncate_context(
        self,
        documents: List[RetrievedDocument],
        max_chars: int,
    ) -> Tuple[List[RetrievedDocument], bool]:
        """
        Truncate context by dropping low-scoring documents first.
        
        Returns:
            (truncated_documents, was_truncated)
        """
        # Sort by score (descending) to keep best documents
        sorted_docs = sorted(
            documents,
            key=lambda x: x.score if x.score is not None else 0.0,
            reverse=True
        )
        
        total_chars = 0
        kept_docs = []
        
        for doc in sorted_docs:
            doc_chars = len(doc.text)
            if total_chars + doc_chars <= max_chars:
                kept_docs.append(doc)
                total_chars += doc_chars
            else:
                # Can't fit this document
                break
        
        was_truncated = len(kept_docs) < len(documents)
        
        if was_truncated:
            LOGGER.debug(
                f"Context truncated: {len(documents)} -> {len(kept_docs)} docs, "
                f"{total_chars}/{max_chars} chars"
            )
        
        return kept_docs, was_truncated
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all logged retrievals."""
        if not self.metrics:
            return {}
        
        total_retrievals = len(self.metrics)
        avg_sec_docs = sum(m.num_sec_docs for m in self.metrics) / total_retrievals
        avg_uploaded_docs = sum(m.num_uploaded_docs for m in self.metrics) / total_retrievals
        avg_retrieval_time = sum(m.retrieval_time_ms for m in self.metrics) / total_retrievals
        
        low_score_count = sum(1 for m in self.metrics if m.low_score_warning)
        empty_count = sum(1 for m in self.metrics if m.empty_retrieval)
        
        return {
            "total_retrievals": total_retrievals,
            "avg_sec_docs": avg_sec_docs,
            "avg_uploaded_docs": avg_uploaded_docs,
            "avg_retrieval_time_ms": avg_retrieval_time,
            "low_score_warnings": low_score_count,
            "empty_retrievals": empty_count,
            "low_score_rate": low_score_count / total_retrievals if total_retrievals > 0 else 0.0,
            "empty_retrieval_rate": empty_count / total_retrievals if total_retrievals > 0 else 0.0,
        }

