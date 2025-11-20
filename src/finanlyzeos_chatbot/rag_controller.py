"""
Multi-Hop RAG Controller - Decomposed Retrieval for Complex Questions

Implements agentic RAG with query decomposition and sequential retrieval.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .rag_retriever import RAGRetriever, RetrievalResult

LOGGER = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"  # Single-step retrieval
    MODERATE = "moderate"  # 2-3 retrieval steps
    COMPLEX = "complex"  # 4+ retrieval steps or multi-hop reasoning


@dataclass
class QueryStep:
    """A single retrieval step in a multi-hop query."""
    step_number: int
    sub_query: str
    retrieval_type: str  # "metrics", "sec_narratives", "uploaded_docs", "macro", "portfolio"
    tickers: List[str]
    results: Optional[RetrievalResult] = None


@dataclass
class DecomposedQuery:
    """Decomposed complex query with multiple retrieval steps."""
    original_query: str
    complexity: QueryComplexity
    steps: List[QueryStep]
    final_result: Optional[RetrievalResult] = None


class RAGController:
    """
    Controller for multi-hop RAG retrieval.
    
    Decomposes complex questions into sub-queries and performs sequential retrieval.
    """
    
    def __init__(self, retriever: RAGRetriever):
        """Initialize controller with a RAGRetriever."""
        self.retriever = retriever
    
    def decompose_query(self, query: str, tickers: List[str]) -> DecomposedQuery:
        """
        Decompose a complex query into retrieval steps.
        
        Simple heuristic-based decomposition (can be enhanced with LLM).
        """
        query_lower = query.lower()
        
        # Detect query complexity
        complexity = self._detect_complexity(query)
        
        steps = []
        
        # Step 1: Always retrieve metrics and facts
        steps.append(QueryStep(
            step_number=1,
            sub_query=query,
            retrieval_type="metrics",
            tickers=tickers,
        ))
        
        # Step 2: If query mentions narratives/explanations, retrieve SEC narratives
        narrative_keywords = ["why", "how", "explain", "reason", "cause", "impact", "effect"]
        if any(keyword in query_lower for keyword in narrative_keywords):
            steps.append(QueryStep(
                step_number=2,
                sub_query=query,
                retrieval_type="sec_narratives",
                tickers=tickers,
            ))
        
        # Step 3: If query mentions macro/economic context
        macro_keywords = ["economy", "economic", "inflation", "rates", "fed", "gdp", "market"]
        if any(keyword in query_lower for keyword in macro_keywords):
            steps.append(QueryStep(
                step_number=3,
                sub_query=query,
                retrieval_type="macro",
                tickers=tickers,
            ))
        
        # Step 4: If query mentions portfolio
        portfolio_keywords = ["portfolio", "holdings", "exposure", "allocation"]
        if any(keyword in query_lower for keyword in portfolio_keywords):
            steps.append(QueryStep(
                step_number=4,
                sub_query=query,
                retrieval_type="portfolio",
                tickers=tickers,
            ))
        
        # Step 5: If query mentions forecast/prediction
        forecast_keywords = ["forecast", "predict", "future", "outlook", "projection"]
        if any(keyword in query_lower for keyword in forecast_keywords):
            steps.append(QueryStep(
                step_number=5,
                sub_query=query,
                retrieval_type="ml_forecasts",
                tickers=tickers,
            ))
        
        return DecomposedQuery(
            original_query=query,
            complexity=complexity,
            steps=steps,
        )
    
    def _detect_complexity(self, query: str) -> QueryComplexity:
        """Detect query complexity based on keywords and structure."""
        query_lower = query.lower()
        
        # Count different query types
        count = 0
        if any(kw in query_lower for kw in ["why", "how", "explain"]):
            count += 1
        if any(kw in query_lower for kw in ["compare", "versus", "vs", "difference"]):
            count += 1
        if any(kw in query_lower for kw in ["forecast", "predict", "future"]):
            count += 1
        if any(kw in query_lower for kw in ["portfolio", "holdings"]):
            count += 1
        if any(kw in query_lower for kw in ["economy", "macro", "inflation"]):
            count += 1
        
        if count <= 1:
            return QueryComplexity.SIMPLE
        elif count <= 3:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.COMPLEX
    
    def execute_multi_hop(
        self,
        query: str,
        tickers: List[str],
        *,
        max_steps: int = 5,
        use_reranking: bool = True,
    ) -> RetrievalResult:
        """
        Execute multi-hop retrieval for a complex query.
        
        Args:
            query: User query
            tickers: List of ticker symbols
            max_steps: Maximum retrieval steps
            use_reranking: Enable reranking
        
        Returns:
            Combined RetrievalResult from all steps
        """
        # Decompose query
        decomposed = self.decompose_query(query, tickers)
        
        LOGGER.info(
            f"Multi-hop retrieval: {decomposed.complexity.value} query, {len(decomposed.steps)} steps"
        )
        
        # Execute steps sequentially
        all_metrics = []
        all_facts = []
        all_sec_narratives = []
        all_uploaded_docs = []
        macro_data = None
        portfolio_data = None
        ml_forecasts = None
        
        for step in decomposed.steps[:max_steps]:
            try:
                if step.retrieval_type == "metrics":
                    # Retrieve metrics and facts
                    result = self.retriever.retrieve(
                        query=step.sub_query,
                        tickers=step.tickers,
                        use_semantic_search=False,  # Metrics are SQL-only
                        use_reranking=False,
                    )
                    all_metrics.extend(result.metrics)
                    all_facts.extend(result.facts)
                
                elif step.retrieval_type == "sec_narratives":
                    # Retrieve SEC narratives
                    result = self.retriever.retrieve(
                        query=step.sub_query,
                        tickers=step.tickers,
                        max_sec_results=5,
                        use_reranking=use_reranking,
                    )
                    all_sec_narratives.extend(result.sec_narratives)
                
                elif step.retrieval_type == "uploaded_docs":
                    # Retrieve uploaded documents
                    result = self.retriever.retrieve(
                        query=step.sub_query,
                        tickers=step.tickers,
                        max_uploaded_results=3,
                        use_reranking=use_reranking,
                    )
                    all_uploaded_docs.extend(result.uploaded_docs)
                
                elif step.retrieval_type == "macro":
                    # Retrieve macro data (from context_builder or macro_data module)
                    # This would need integration with macro_data provider
                    LOGGER.debug("Macro data retrieval (placeholder)")
                
                elif step.retrieval_type == "portfolio":
                    # Portfolio data (from portfolio module)
                    LOGGER.debug("Portfolio data retrieval (placeholder)")
                
                elif step.retrieval_type == "ml_forecasts":
                    # ML forecasts (from ml_forecasting module)
                    LOGGER.debug("ML forecast retrieval (placeholder)")
                
                step.results = result if 'result' in locals() else None
                
            except Exception as e:
                LOGGER.warning(f"Step {step.step_number} ({step.retrieval_type}) failed: {e}")
                continue
        
        # Combine all results
        final_result = RetrievalResult(
            metrics=all_metrics,
            facts=all_facts,
            sec_narratives=all_sec_narratives,
            uploaded_docs=all_uploaded_docs,
            macro_data=macro_data,
            portfolio_data=portfolio_data,
            ml_forecasts=ml_forecasts,
        )
        
        decomposed.final_result = final_result
        
        LOGGER.info(
            f"Multi-hop complete: {len(all_metrics)} metrics, {len(all_sec_narratives)} SEC docs, "
            f"{len(all_uploaded_docs)} uploaded docs"
        )
        
        return final_result

