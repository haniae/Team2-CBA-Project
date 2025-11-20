"""
RAG Orchestrator - Complete RAG Pipeline with All Features

Orchestrates the full RAG pipeline:
1. Query parsing
2. Multi-hop decomposition (if complex)
3. Retrieval with reranking
4. Source fusion
5. Grounded decision
6. Memory tracking
7. Prompt building with confidence
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .rag_retriever import RAGRetriever, RetrievalResult
from .rag_reranker import Reranker
from .rag_observability import RAGObserver, RAGGuardrails
from .rag_controller import RAGController, QueryComplexity
from .rag_fusion import SourceFusion
from .rag_grounded_decision import GroundedDecisionLayer
from .rag_memory import MemoryAugmentedRAG
from .rag_prompt_template import build_rag_prompt
from .parsing.parse import parse_to_structured

LOGGER = logging.getLogger(__name__)


class RAGOrchestrator:
    """
    Complete RAG orchestrator with all production-grade features.
    
    Implements:
    - Cross-encoder reranking
    - Multi-hop retrieval
    - Source fusion
    - Grounded decision layer
    - Memory-augmented RAG
    - Confidence scoring
    """
    
    def __init__(
        self,
        database_path: Path,
        analytics_engine: Any,  # AnalyticsEngine
        *,
        use_reranking: bool = True,
        use_multi_hop: bool = True,
        use_fusion: bool = True,
        use_grounded_decision: bool = True,
        use_memory: bool = True,
    ):
        """
        Initialize RAG orchestrator.
        
        Args:
            database_path: Path to database
            analytics_engine: AnalyticsEngine instance
            use_reranking: Enable reranking (default True)
            use_multi_hop: Enable multi-hop for complex queries (default True)
            use_fusion: Enable source fusion (default True)
            use_grounded_decision: Enable grounded decision layer (default True)
            use_memory: Enable memory-augmented RAG (default True)
        """
        self.database_path = database_path
        self.analytics_engine = analytics_engine
        
        # Initialize components
        self.retriever = RAGRetriever(database_path, analytics_engine)
        self.reranker = Reranker(use_reranking=use_reranking) if use_reranking else None
        self.observer = RAGObserver(RAGGuardrails(min_relevance_score=0.25))
        self.controller = RAGController(self.retriever) if use_multi_hop else None
        self.fusion = SourceFusion() if use_fusion else None
        self.grounded_decision = GroundedDecisionLayer() if use_grounded_decision else None
        self.memory = MemoryAugmentedRAG() if use_memory else None
        
        # Feature flags
        self.use_reranking = use_reranking
        self.use_multi_hop = use_multi_hop
        self.use_fusion = use_fusion
        self.use_grounded_decision = use_grounded_decision
        self.use_memory = use_memory
    
    def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[str, RetrievalResult, Dict[str, Any]]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            query: User query
            conversation_id: Conversation ID for filtering
            user_id: User ID for memory tracking
        
        Returns:
            Tuple of (prompt, retrieval_result, metadata)
        """
        # 1. Parse query
        structured = parse_to_structured(query)
        tickers = [t["ticker"] for t in structured.get("tickers", [])][:3]
        
        # 2. Detect complexity and decide on multi-hop
        use_multi_hop = False
        if self.use_multi_hop and self.controller:
            decomposed = self.controller.decompose_query(query, tickers)
            use_multi_hop = decomposed.complexity != QueryComplexity.SIMPLE
        
        # 3. Retrieve (with or without multi-hop)
        if use_multi_hop and self.controller:
            LOGGER.info(f"Using multi-hop retrieval for complex query: {query[:100]}")
            result = self.controller.execute_multi_hop(
                query=query,
                tickers=tickers,
                use_reranking=self.use_reranking,
            )
        else:
            result = self.retriever.retrieve(
                query=query,
                tickers=tickers,
                use_reranking=self.use_reranking,
                conversation_id=conversation_id,
                reranker=self.reranker,
                observer=self.observer,
            )
        
        # 4. Source fusion (if enabled)
        overall_confidence = None
        if self.use_fusion and self.fusion:
            fused_docs, overall_confidence = self.fusion.fuse_all_sources(result)
            result.fused_documents = fused_docs
            result.overall_confidence = overall_confidence
        
        # 5. Grounded decision (if enabled)
        grounded_decision = None
        grounded_instruction = None
        if self.use_grounded_decision and self.grounded_decision:
            grounded_decision = self.grounded_decision.make_decision(
                query=query,
                result=result,
                overall_confidence=overall_confidence or 0.0,
                parsed_tickers=tickers,
            )
            
            # If decision says don't answer, return early
            if not grounded_decision.should_answer:
                return (
                    grounded_decision.suggested_response or "I don't have enough information to answer this question.",
                    result,
                    {
                        "grounded_decision": grounded_decision,
                        "confidence": overall_confidence,
                        "should_answer": False,
                    }
                )
            
            grounded_instruction = self.grounded_decision.get_grounded_prompt_instruction(
                grounded_decision,
                overall_confidence or 0.0,
            )
        
        # 6. Memory tracking (if enabled)
        if self.use_memory and self.memory and conversation_id:
            # Update access for retrieved documents
            for doc in result.uploaded_docs:
                doc_id = doc.metadata.get("document_id") or doc.metadata.get("filename", "")
                if doc_id:
                    self.memory.update_access(doc_id, conversation_id)
            
            # Cluster documents by topic
            if result.uploaded_docs:
                clusters = self.memory.cluster_documents_by_topic(conversation_id, result.uploaded_docs)
                LOGGER.debug(f"Document clusters: {list(clusters.keys())}")
        
        # 7. Get confidence instruction
        confidence_instruction = None
        if overall_confidence is not None and self.fusion:
            confidence_instruction = self.fusion.get_confidence_instruction(overall_confidence)
        
        # 8. Build prompt
        prompt = build_rag_prompt(
            user_query=query,
            retrieval_result=result,
            confidence_instruction=confidence_instruction,
            grounded_instruction=grounded_instruction,
        )
        
        # 9. Prepare metadata
        metadata = {
            "tickers": tickers,
            "complexity": "complex" if use_multi_hop else "simple",
            "confidence": overall_confidence,
            "num_sec_docs": len(result.sec_narratives),
            "num_uploaded_docs": len(result.uploaded_docs),
            "num_metrics": len(result.metrics),
            "grounded_decision": grounded_decision.reason if grounded_decision else None,
            "should_answer": grounded_decision.should_answer if grounded_decision else True,
        }
        
        return prompt, result, metadata

