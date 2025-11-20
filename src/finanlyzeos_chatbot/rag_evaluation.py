"""
RAG Evaluation Harness - Metrics for Retrieval and QA Quality

Provides:
- Retrieval metrics: Recall@K, MRR, nDCG
- QA metrics: Answer accuracy, factual consistency
- Evaluation dataset support
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import math

from .rag_retriever import RetrievedDocument, RetrievalResult

LOGGER = logging.getLogger(__name__)


@dataclass
class RetrievalEvaluation:
    """Evaluation result for a single retrieval."""
    query: str
    relevant_doc_ids: Set[str]  # Ground truth relevant document IDs
    retrieved_doc_ids: List[str]  # Retrieved document IDs (in order)
    retrieved_scores: List[float]  # Scores for retrieved documents
    
    # Metrics
    recall_at_1: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0


@dataclass
class QAEvaluation:
    """Evaluation result for QA accuracy."""
    query: str
    expected_answer: str  # Ground truth answer
    actual_answer: str    # Generated answer
    retrieved_sources: List[str]  # Sources used
    
    # Metrics
    exact_match: bool = False
    contains_key_facts: bool = False
    factual_consistency: float = 0.0  # 0-1 score
    source_citation_accuracy: float = 0.0  # 0-1 score


class RAGEvaluator:
    """Evaluator for RAG system quality."""
    
    def evaluate_retrieval(
        self,
        query: str,
        result: RetrievalResult,
        relevant_doc_ids: Set[str],
    ) -> RetrievalEvaluation:
        """
        Evaluate retrieval quality.
        
        Args:
            query: User query
            result: Retrieval result
            relevant_doc_ids: Set of relevant document IDs (ground truth)
        
        Returns:
            RetrievalEvaluation with metrics
        """
        # Collect all retrieved document IDs
        retrieved_ids = []
        retrieved_scores = []
        
        for doc in result.sec_narratives:
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filing_id", "")
            retrieved_ids.append(f"sec:{doc_id}")
            retrieved_scores.append(doc.score or 0.0)
        
        for doc in result.uploaded_docs:
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filename", "")
            retrieved_ids.append(f"uploaded:{doc_id}")
            retrieved_scores.append(doc.score or 0.0)
        
        # Calculate metrics
        eval_result = RetrievalEvaluation(
            query=query,
            relevant_doc_ids=relevant_doc_ids,
            retrieved_doc_ids=retrieved_ids,
            retrieved_scores=retrieved_scores,
        )
        
        # Recall@K
        relevant_retrieved = set(retrieved_ids) & relevant_doc_ids
        num_relevant = len(relevant_doc_ids)
        
        if num_relevant > 0:
            eval_result.recall_at_1 = len(set(retrieved_ids[:1]) & relevant_doc_ids) / num_relevant
            eval_result.recall_at_5 = len(set(retrieved_ids[:5]) & relevant_doc_ids) / num_relevant
            eval_result.recall_at_10 = len(set(retrieved_ids[:10]) & relevant_doc_ids) / num_relevant
        
        # MRR (Mean Reciprocal Rank)
        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_doc_ids:
                eval_result.mrr = 1.0 / rank
                break
        
        # nDCG@K (Normalized Discounted Cumulative Gain)
        eval_result.ndcg_at_5 = self._ndcg(retrieved_ids[:5], relevant_doc_ids)
        eval_result.ndcg_at_10 = self._ndcg(retrieved_ids[:10], relevant_doc_ids)
        
        return eval_result
    
    def _ndcg(self, retrieved_ids: List[str], relevant_ids: Set[str], k: Optional[int] = None) -> float:
        """Calculate nDCG (Normalized Discounted Cumulative Gain)."""
        if k is not None:
            retrieved_ids = retrieved_ids[:k]
        
        if not relevant_ids:
            return 0.0
        
        # DCG (Discounted Cumulative Gain)
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_ids:
                dcg += 1.0 / math.log2(i + 1)
        
        # IDCG (Ideal DCG) - perfect ranking
        num_relevant = min(len(relevant_ids), len(retrieved_ids))
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, num_relevant + 1))
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def evaluate_qa(
        self,
        query: str,
        expected_answer: str,
        actual_answer: str,
        retrieved_sources: List[str],
        key_facts: Optional[List[str]] = None,
    ) -> QAEvaluation:
        """
        Evaluate QA quality.
        
        Args:
            query: User query
            expected_answer: Ground truth answer
            actual_answer: Generated answer
            retrieved_sources: List of source document IDs
            key_facts: List of key facts that should be in answer
        
        Returns:
            QAEvaluation with metrics
        """
        eval_result = QAEvaluation(
            query=query,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            retrieved_sources=retrieved_sources,
        )
        
        # Exact match (case-insensitive)
        eval_result.exact_match = (
            expected_answer.lower().strip() == actual_answer.lower().strip()
        )
        
        # Contains key facts
        if key_facts:
            actual_lower = actual_answer.lower()
            facts_found = sum(1 for fact in key_facts if fact.lower() in actual_lower)
            eval_result.contains_key_facts = facts_found == len(key_facts)
            eval_result.factual_consistency = facts_found / len(key_facts) if key_facts else 0.0
        else:
            # Simple word overlap as proxy
            expected_words = set(expected_answer.lower().split())
            actual_words = set(actual_answer.lower().split())
            overlap = len(expected_words & actual_words)
            total = len(expected_words)
            eval_result.factual_consistency = overlap / total if total > 0 else 0.0
        
        return eval_result
    
    def evaluate_batch(
        self,
        evaluations: List[RetrievalEvaluation],
    ) -> Dict[str, float]:
        """Calculate aggregate metrics over a batch of evaluations."""
        if not evaluations:
            return {}
        
        return {
            "recall_at_1": sum(e.recall_at_1 for e in evaluations) / len(evaluations),
            "recall_at_5": sum(e.recall_at_5 for e in evaluations) / len(evaluations),
            "recall_at_10": sum(e.recall_at_10 for e in evaluations) / len(evaluations),
            "mrr": sum(e.mrr for e in evaluations) / len(evaluations),
            "ndcg_at_5": sum(e.ndcg_at_5 for e in evaluations) / len(evaluations),
            "ndcg_at_10": sum(e.ndcg_at_10 for e in evaluations) / len(evaluations),
        }

