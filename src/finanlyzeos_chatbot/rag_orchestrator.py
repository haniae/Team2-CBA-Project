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
from .rag_intent_policies import IntentPolicyManager, RetrievalIntent
from .rag_temporal import TemporalQueryParser, TimeFilter
from .rag_claim_verifier import ClaimVerifier
from .rag_structure_aware import TableAwareRetriever, StructureAwareParser
from .rag_feedback import FeedbackCollector, ScoreCalibrator
from .rag_knowledge_graph import KnowledgeGraph, KGRAGHybrid

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
        use_hybrid_retrieval: bool = True,  # Sparse + dense
        use_intent_policies: bool = True,  # Intent-specific retrieval
        use_temporal: bool = True,  # Time-aware retrieval
        use_claim_verification: bool = True,  # Claim-level verification
        use_structure_aware: bool = True,  # Table-aware retrieval
        use_feedback: bool = True,  # Online feedback
        use_knowledge_graph: bool = False,  # KG+RAG hybrid (optional)
        llm_client: Optional[Any] = None,  # For claim verification
    ):
        """
        Initialize RAG orchestrator with all advanced features.
        
        Args:
            database_path: Path to database
            analytics_engine: AnalyticsEngine instance
            use_reranking: Enable reranking (default True)
            use_multi_hop: Enable multi-hop for complex queries (default True)
            use_fusion: Enable source fusion (default True)
            use_grounded_decision: Enable grounded decision layer (default True)
            use_memory: Enable memory-augmented RAG (default True)
            use_hybrid_retrieval: Enable hybrid sparse+dense retrieval (default True)
            use_intent_policies: Enable intent-specific retrieval policies (default True)
            use_temporal: Enable time-aware retrieval (default True)
            use_claim_verification: Enable claim-level verification (default True)
            use_structure_aware: Enable table-aware retrieval (default True)
            use_feedback: Enable online feedback collection (default True)
            use_knowledge_graph: Enable KG+RAG hybrid (default False, optional)
            llm_client: LLM client for claim verification (optional)
        """
        self.database_path = database_path
        self.analytics_engine = analytics_engine
        
        # Initialize core components
        self.retriever = RAGRetriever(
            database_path,
            analytics_engine,
            use_hybrid_retrieval=use_hybrid_retrieval,
        )
        self.reranker = Reranker(use_reranking=use_reranking) if use_reranking else None
        self.observer = RAGObserver(RAGGuardrails(min_relevance_score=0.25))
        self.controller = RAGController(self.retriever) if use_multi_hop else None
        self.fusion = SourceFusion() if use_fusion else None
        self.grounded_decision = GroundedDecisionLayer() if use_grounded_decision else None
        self.memory = MemoryAugmentedRAG() if use_memory else None
        
        # Initialize advanced features
        self.intent_manager = IntentPolicyManager() if use_intent_policies else None
        self.temporal_parser = TemporalQueryParser() if use_temporal else None
        self.claim_verifier = ClaimVerifier(llm_client) if use_claim_verification else None
        self.structure_parser = StructureAwareParser() if use_structure_aware else None
        self.table_retriever = TableAwareRetriever(self.structure_parser) if use_structure_aware else None
        self.feedback_collector = FeedbackCollector() if use_feedback else None
        self.score_calibrator = ScoreCalibrator(self.feedback_collector) if use_feedback else None
        self.knowledge_graph = KnowledgeGraph() if use_knowledge_graph else None
        self.kg_rag_hybrid = KGRAGHybrid(self.knowledge_graph, self.retriever) if (use_knowledge_graph and self.knowledge_graph) else None
        
        # Feature flags
        self.use_reranking = use_reranking
        self.use_multi_hop = use_multi_hop
        self.use_fusion = use_fusion
        self.use_grounded_decision = use_grounded_decision
        self.use_memory = use_memory
        self.use_hybrid_retrieval = use_hybrid_retrieval
        self.use_intent_policies = use_intent_policies
        self.use_temporal = use_temporal
        self.use_claim_verification = use_claim_verification
        self.use_structure_aware = use_structure_aware
        self.use_feedback = use_feedback
        self.use_knowledge_graph = use_knowledge_graph
    
    def process_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Tuple[str, RetrievalResult, Dict[str, Any]]:
        """
        Process a query through the complete RAG pipeline with all advanced features.
        
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
        
        # 2. Detect intent and get retrieval policy
        intent = RetrievalIntent.GENERAL
        policy = None
        if self.use_intent_policies and self.intent_manager:
            intent = self.intent_manager.detect_intent(query, structured)
            policy = self.intent_manager.get_policy(intent)
            # Rewrite query based on intent
            query = self.intent_manager.rewrite_query(query, intent)
            LOGGER.info(f"Detected intent: {intent.value}, policy: use_multi_hop={policy.use_multi_hop}, k_docs={policy.k_docs}")
        
        # 3. Parse temporal filter
        time_filter = None
        if self.use_temporal and self.temporal_parser:
            time_filter = self.temporal_parser.parse_time_filter(query)
            if time_filter:
                LOGGER.info(f"Time filter: {time_filter.fiscal_years or 'all years'}")
        
        # 4. Check for table queries
        is_table_query = False
        table_data = []
        if self.use_structure_aware and self.table_retriever:
            is_table_query = self.table_retriever.is_table_query(query)
            if is_table_query:
                table_data = self.table_retriever.retrieve_tables(
                    query,
                    ticker=tickers[0] if tickers else None,
                    period=None,  # Could extract from time_filter
                )
                LOGGER.info(f"Table query detected: retrieved {len(table_data)} tables")
        
        # 5. Check for relationship queries (KG+RAG)
        kg_entities = []
        if self.use_knowledge_graph and self.kg_rag_hybrid:
            if self.kg_rag_hybrid.is_relationship_query(query):
                kg_entities, _ = self.kg_rag_hybrid.retrieve_hybrid(query, tickers)
                LOGGER.info(f"KG+RAG hybrid: found {len(kg_entities)} related entities")
        
        # 6. Detect complexity and decide on multi-hop (use policy if available)
        use_multi_hop = False
        if policy:
            use_multi_hop = policy.use_multi_hop
        elif self.use_multi_hop and self.controller:
            decomposed = self.controller.decompose_query(query, tickers)
            use_multi_hop = decomposed.complexity != QueryComplexity.SIMPLE
        
        # 7. Retrieve (with or without multi-hop, using policy if available)
        if use_multi_hop and self.controller:
            LOGGER.info(f"Using multi-hop retrieval for complex query: {query[:100]}")
            result = self.controller.execute_multi_hop(
                query=query,
                tickers=tickers,
                use_reranking=policy.use_reranking if policy else self.use_reranking,
            )
        else:
            # Apply policy settings if available
            max_sec = policy.max_sec_results if policy else 5
            max_uploaded = policy.max_uploaded_results if policy else 3
            use_rerank = policy.use_reranking if policy else self.use_reranking
            
            result = self.retriever.retrieve(
                query=query,
                tickers=tickers,
                max_sec_results=max_sec,
                max_uploaded_results=max_uploaded,
                use_reranking=use_rerank,
                conversation_id=conversation_id,
                reranker=self.reranker,
                observer=self.observer,
            )
        
        # 8. Apply time filter to retrieved documents
        if time_filter and self.temporal_parser:
            result.sec_narratives = self.temporal_parser.apply_time_filter(
                result.sec_narratives, time_filter
            )
            result.uploaded_docs = self.temporal_parser.apply_time_filter(
                result.uploaded_docs, time_filter
            )
        
        # 9. Add table data to result if table query
        if is_table_query and table_data:
            # Add table data as special documents
            for table_text in table_data:
                from .rag_retriever import RetrievedDocument
                result.uploaded_docs.append(RetrievedDocument(
                    text=table_text,
                    source_type="table",
                    metadata={"source": "table_retriever"},
                    score=1.0,  # High score for table data
                ))
        
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
                    grounded_decision.suggested_response or "Unable to provide a response based on available information.",
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
        
        # 10. Build prompt
        prompt = build_rag_prompt(
            user_query=query,
            retrieval_result=result,
            confidence_instruction=confidence_instruction,
            grounded_instruction=grounded_instruction,
        )
        
        # 11. Prepare metadata with all feature information
        metadata = {
            "tickers": tickers,
            "intent": intent.value if intent else "general",
            "complexity": "complex" if use_multi_hop else "simple",
            "confidence": overall_confidence,
            "num_sec_docs": len(result.sec_narratives),
            "num_uploaded_docs": len(result.uploaded_docs),
            "num_metrics": len(result.metrics),
            "grounded_decision": grounded_decision.reason if grounded_decision else None,
            "should_answer": grounded_decision.should_answer if grounded_decision else True,
            "time_filter": {
                "fiscal_years": time_filter.fiscal_years if time_filter else None,
                "start_date": time_filter.start_date if time_filter else None,
                "end_date": time_filter.end_date if time_filter else None,
            } if time_filter else None,
            "is_table_query": is_table_query,
            "num_tables": len(table_data),
            "kg_entities": kg_entities,
        }
        
        return prompt, result, metadata
    
    def verify_answer_claims(
        self,
        answer: str,
        retrieval_result: RetrievalResult,
    ) -> Optional[Any]:  # ClaimVerificationResult
        """
        Verify claims in generated answer (post-generation verification).
        
        Args:
            answer: Generated answer
            retrieval_result: RetrievalResult used to generate answer
        
        Returns:
            ClaimVerificationResult if verification enabled, None otherwise
        """
        if not self.use_claim_verification or not self.claim_verifier:
            return None
        
        # Extract document texts
        retrieved_docs = [
            doc.text for doc in retrieval_result.sec_narratives + retrieval_result.uploaded_docs
        ]
        
        # Verify claims
        verification = self.claim_verifier.verify_answer(
            answer=answer,
            retrieved_docs=retrieved_docs,
        )
        
        LOGGER.info(
            f"Claim verification: {verification.num_supported} supported, "
            f"{verification.num_contradicted} contradicted, "
            f"{verification.num_not_found} not found, "
            f"confidence={verification.overall_confidence:.2f}"
        )
        
        return verification
    
    def record_feedback(
        self,
        query: str,
        answer: str,
        retrieval_result: RetrievalResult,
        label: str,  # "good", "bad", "partial"
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """
        Record user feedback for learning.
        
        Args:
            query: User query
            answer: Generated answer
            retrieval_result: RetrievalResult used
            label: Feedback label ("good", "bad", "partial")
            user_id: Optional user ID
            conversation_id: Optional conversation ID
            reason: Optional reason for feedback
        """
        if not self.use_feedback or not self.feedback_collector:
            return
        
        # Extract document IDs and scores
        doc_ids = []
        doc_scores = []
        
        for doc in retrieval_result.sec_narratives + retrieval_result.uploaded_docs:
            doc_id = doc.metadata.get("document_id") or doc.metadata.get("filing_id") or "unknown"
            doc_ids.append(doc_id)
            doc_scores.append(doc.score or 0.0)
        
        # Record feedback
        from .rag_feedback import FeedbackLabel
        feedback_label = FeedbackLabel(label.lower())
        
        self.feedback_collector.record_feedback(
            query=query,
            doc_ids=doc_ids,
            doc_scores=doc_scores,
            answer=answer,
            label=feedback_label,
            user_id=user_id,
            conversation_id=conversation_id,
            reason=reason,
        )
        
        # Update score calibrator
        if self.score_calibrator:
            self.score_calibrator.update_from_feedback()

