"""
RAG Retriever Module - Explicit Retriever Component for RAG Pipeline

This module implements the "Retriever" component from Lecture 2's RAG framework:
- Semantic search over embedded documents (SEC narratives, uploaded docs)
- Deterministic SQL retrieval (metrics, facts)
- Multi-source aggregation

Architecture aligns with Lecture 2:
"Retriever (semantic search over embedded docs) → Generator (LLM)"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)

# Optional imports for semantic search
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


@dataclass
class RetrievedDocument:
    """Represents a retrieved document chunk with metadata."""
    text: str
    source_type: str  # "sec_filing", "uploaded_doc", "metric_context"
    metadata: Dict[str, Any]
    score: Optional[float] = None  # Similarity score for semantic search


@dataclass
class RetrievalResult:
    """Complete retrieval result from RAG Retriever."""
    # Deterministic SQL results
    metrics: List[Dict[str, Any]]
    facts: List[Dict[str, Any]]
    
    # Semantic search results (embedded documents)
    sec_narratives: List[RetrievedDocument]  # MD&A, Risk Factors, etc.
    uploaded_docs: List[RetrievedDocument]   # User-uploaded documents
    
    # Additional context
    macro_data: Optional[Dict[str, Any]] = None
    portfolio_data: Optional[Dict[str, Any]] = None
    ml_forecasts: Optional[Dict[str, Any]] = None
    
    # Fusion and confidence (added by source fusion)
    fused_documents: Optional[List[Any]] = None  # FusedDocument from rag_fusion
    overall_confidence: Optional[float] = None  # Overall retrieval confidence (0-1)


class VectorStore:
    """
    Document / Vector Store for RAG Pipeline
    
    Implements the "Document Store / Index" from Lecture 2:
    - Keys = embedded document representations
    - Values = underlying text chunks (docs/snippets)
    
    Process: "Text → Tokens → Embeddings" for documents
    """
    
    def __init__(
        self,
        database_path: Path,
        collection_name: str = "financial_documents",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """Initialize vector store for semantic search."""
        if not CHROMADB_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            self._available = False
            LOGGER.warning(
                "Vector store not available. Install: pip install chromadb sentence-transformers"
            )
            return
        
        self._available = True
        self.database_path = database_path
        self.collection_name = collection_name
        
        # Initialize embedding model
        LOGGER.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize ChromaDB
        chroma_db_path = database_path.parent / "chroma_db"
        chroma_db_path.mkdir(exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(chroma_db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collections
        self._init_collections()
    
    def _init_collections(self):
        """Initialize separate collections for SEC filings and uploaded docs."""
        # SEC narratives collection
        try:
            self.sec_collection = self.client.get_collection(name=f"{self.collection_name}_sec")
        except Exception:
            self.sec_collection = self.client.create_collection(
                name=f"{self.collection_name}_sec",
                metadata={"description": "SEC filing narratives (MD&A, Risk Factors, etc.)"}
            )
        
        # Uploaded documents collection
        try:
            self.uploaded_collection = self.client.get_collection(name=f"{self.collection_name}_uploaded")
        except Exception:
            self.uploaded_collection = self.client.create_collection(
                name=f"{self.collection_name}_uploaded",
                metadata={"description": "User-uploaded documents (PDFs, CSVs, etc.)"}
            )
    
    def add_sec_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add SEC filing documents to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.sec_collection, batch_size)
    
    def add_uploaded_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add uploaded documents to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.uploaded_collection, batch_size)
    
    def _add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection,
        batch_size: int = 100,
    ) -> int:
        """Internal method to add documents to a collection."""
        if not documents:
            return 0
        
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc["text"] for doc in batch]
            metadatas = [doc.get("metadata", {}) for doc in batch]
            
            # Generate embeddings: "Text → Tokens → Embeddings"
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist()
            
            # Generate IDs
            ids = [
                f"{meta.get('ticker', 'unknown')}_{meta.get('filing_type', 'doc')}_"
                f"{meta.get('fiscal_year', 'unknown')}_{meta.get('section', 'unknown')}_{i+j}"
                for j, meta in enumerate(metadatas)
            ]
            
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            total_added += len(texts)
        
        return total_added
    
    def search_sec_narratives(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over SEC filing narratives."""
        if not self._available:
            return []
        return self._search(query, self.sec_collection, n_results, filter_metadata, "sec_filing")
    
    def search_uploaded_docs(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over uploaded documents."""
        if not self._available:
            return []
        return self._search(query, self.uploaded_collection, n_results, filter_metadata, "uploaded_doc")
    
    def _search(
        self,
        query: str,
        collection,
        n_results: int,
        filter_metadata: Optional[Dict[str, Any]],
        source_type: str,
    ) -> List[RetrievedDocument]:
        """Internal semantic search method."""
        # Embed query and do nearest-neighbor search
        query_embedding = self.embedding_model.encode(
            query,
            convert_to_numpy=True,
        ).tolist()
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata,
        )
        
        retrieved = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                retrieved.append(RetrievedDocument(
                    text=results["documents"][0][i],
                    source_type=source_type,
                    metadata=results["metadatas"][0][i],
                    score=results["distances"][0][i] if results["distances"] else None,
                ))
        
        return retrieved


class RAGRetriever:
    """
    RAG Retriever Component
    
    Implements the "Retriever" from Lecture 2's RAG framework:
    - SQL deterministic retrieval (metric_snapshots, financial_facts)
    - Hybrid sparse+dense retrieval (BM25 + embeddings) for SEC narratives and uploaded docs
    - Macro data, portfolio data, ML forecast results
    """
    
    def __init__(
        self,
        database_path: Path,
        analytics_engine: Any,  # AnalyticsEngine
        use_hybrid_retrieval: bool = True,
    ):
        """
        Initialize RAG Retriever.
        
        Args:
            database_path: Path to database
            analytics_engine: AnalyticsEngine instance
            use_hybrid_retrieval: Enable hybrid sparse+dense retrieval (default True)
        """
        self.database_path = database_path
        self.analytics_engine = analytics_engine
        self.use_hybrid_retrieval = use_hybrid_retrieval
        
        # Initialize vector store for dense retrieval
        try:
            self.vector_store = VectorStore(database_path)
            if not self.vector_store._available:
                LOGGER.warning("Vector store not available (missing chromadb/sentence-transformers)")
        except Exception as e:
            LOGGER.warning(f"Vector store initialization failed: {e}")
            self.vector_store = None
        
        # Initialize hybrid retriever (sparse + dense)
        self.hybrid_retriever = None
        self.sparse_retriever = None
        if use_hybrid_retrieval:
            try:
                from .rag_hybrid_retriever import HybridRetriever, HybridRetrievalConfig
                from .rag_sparse_retriever import SparseRetriever
                from .rag_fusion import SourceFusion
                
                # Initialize sparse retriever (index will be built lazily)
                self.sparse_retriever = SparseRetriever(vector_store=self.vector_store)
                
                self.hybrid_retriever = HybridRetriever(
                    vector_store=self.vector_store,
                    sparse_retriever=self.sparse_retriever,
                    fusion=SourceFusion(),
                    config=HybridRetrievalConfig(use_hybrid=use_hybrid_retrieval),
                )
                LOGGER.info("Hybrid retriever initialized (sparse + dense)")
            except ImportError as e:
                LOGGER.warning(f"Hybrid retriever not available: {e}. Using dense-only retrieval.")
                self.use_hybrid_retrieval = False
    
    def retrieve(
        self,
        query: str,
        tickers: List[str],
        *,
        max_sec_results: int = 5,
        max_uploaded_results: int = 3,
        use_semantic_search: bool = True,
        conversation_id: Optional[str] = None,
        use_reranking: bool = True,
        reranker: Optional[Any] = None,  # Reranker from rag_reranker module
        observer: Optional[Any] = None,  # RAGObserver from rag_observability module
    ) -> RetrievalResult:
        """
        Main retrieval method - combines all retrieval sources with optional reranking.
        
        Args:
            query: User query
            tickers: List of ticker symbols
            max_sec_results: Max SEC documents to retrieve (before reranking)
            max_uploaded_results: Max uploaded documents to retrieve (before reranking)
            use_semantic_search: Enable semantic search
            conversation_id: Filter uploaded docs by conversation
            use_reranking: Enable reranking stage
            reranker: Reranker instance (optional, will create if None and use_reranking=True)
            observer: RAGObserver for logging/metrics (optional)
        
        Returns:
            RetrievalResult with all retrieved context
        """
        import time
        start_time = time.time()
        
        # 1. Deterministic SQL retrieval
        metrics, facts = self._retrieve_sql_data(tickers)
        
        # 2. Hybrid retrieval (sparse + dense) over SEC narratives
        sec_narratives = []
        if use_semantic_search and tickers:
            for ticker in tickers:
                filter_metadata = {"ticker": ticker.upper()}
                
                if self.use_hybrid_retrieval and self.hybrid_retriever:
                    # Use hybrid retrieval (sparse + dense)
                    try:
                        results = self.hybrid_retriever.retrieve_sec_narratives(
                            query=query,
                            n_results=max_sec_results * 2,  # Retrieve more for reranking
                            filter_metadata=filter_metadata,
                        )
                        sec_narratives.extend(results)
                        LOGGER.debug(f"Hybrid retrieval: {len(results)} SEC documents for {ticker}")
                    except Exception as e:
                        LOGGER.warning(f"Hybrid retrieval failed, falling back to dense-only: {e}")
                        # Fallback to dense-only
                        if self.vector_store and self.vector_store._available:
                            results = self.vector_store.search_sec_narratives(
                                query=query,
                                n_results=max_sec_results * 2,
                                filter_metadata=filter_metadata,
                            )
                            sec_narratives.extend(results)
                elif self.vector_store and self.vector_store._available:
                    # Dense-only retrieval (fallback)
                    results = self.vector_store.search_sec_narratives(
                        query=query,
                        n_results=max_sec_results * 2,
                        filter_metadata=filter_metadata,
                    )
                    sec_narratives.extend(results)
        
        # 3. Hybrid retrieval (sparse + dense) over uploaded documents
        uploaded_docs = []
        if use_semantic_search:
            filter_metadata = {"conversation_id": conversation_id} if conversation_id else None
            
            if self.use_hybrid_retrieval and self.hybrid_retriever:
                # Use hybrid retrieval (sparse + dense)
                try:
                    results = self.hybrid_retriever.retrieve_uploaded_docs(
                        query=query,
                        n_results=max_uploaded_results * 2,  # Retrieve more for reranking
                        filter_metadata=filter_metadata,
                    )
                    uploaded_docs.extend(results)
                    LOGGER.debug(f"Hybrid retrieval: {len(results)} uploaded documents")
                except Exception as e:
                    LOGGER.warning(f"Hybrid retrieval failed, falling back to dense-only: {e}")
                    # Fallback to dense-only
                    if self.vector_store and self.vector_store._available:
                        results = self.vector_store.search_uploaded_docs(
                            query=query,
                            n_results=max_uploaded_results * 2,
                            filter_metadata=filter_metadata,
                        )
                        uploaded_docs.extend(results)
            elif self.vector_store and self.vector_store._available:
                # Dense-only retrieval (fallback)
                results = self.vector_store.search_uploaded_docs(
                    query=query,
                    n_results=max_uploaded_results * 2,
                    filter_metadata=filter_metadata,
                )
                uploaded_docs.extend(results)
        
        retrieval_time_ms = (time.time() - start_time) * 1000
        
        # 4. Reranking stage (if enabled)
        reranking_time_ms = 0.0
        if use_reranking and (sec_narratives or uploaded_docs):
            rerank_start = time.time()
            
            if reranker is None:
                try:
                    from .rag_reranker import Reranker
                    reranker = Reranker(use_reranking=True)
                except ImportError:
                    LOGGER.debug("Reranker not available, skipping reranking")
                    reranker = None
            
            if reranker:
                try:
                    sec_narratives, uploaded_docs = reranker.rerank_multi_source(
                        query=query,
                        sec_docs=sec_narratives,
                        uploaded_docs=uploaded_docs,
                        max_sec=max_sec_results,
                        max_uploaded=max_uploaded_results,
                    )
                    reranking_time_ms = (time.time() - rerank_start) * 1000
                    LOGGER.debug(f"Reranking completed in {reranking_time_ms:.1f}ms")
                except Exception as e:
                    LOGGER.warning(f"Reranking failed: {e}, using original results")
        
        # 5. Apply guardrails (if observer provided)
        result = RetrievalResult(
            metrics=metrics,
            facts=facts,
            sec_narratives=sec_narratives,
            uploaded_docs=uploaded_docs,
        )
        
        # Note: Source fusion is handled by RAGOrchestrator or can be done separately
        # This keeps RAGRetriever focused on retrieval only
        
        if observer:
            result = observer.apply_guardrails(result, query)
            observer.log_retrieval(query, result, retrieval_time_ms, reranking_time_ms)
        
        return result
    
    def _retrieve_sql_data(
        self,
        tickers: List[str],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Retrieve deterministic data from SQL database."""
        from . import database
        
        metrics = []
        facts = []
        
        for ticker in tickers:
            try:
                # Fetch metric snapshots
                records = database.fetch_metric_snapshots(self.database_path, ticker)
                for record in records:
                    metrics.append({
                        "ticker": ticker,
                        "metric": record.metric,
                        "period": record.period,
                        "value": record.value,
                        "source": record.source,
                    })
            except Exception as e:
                # Database might not be initialized or table doesn't exist
                LOGGER.debug(f"Could not fetch metrics for {ticker}: {e}")
                continue
            
            # Fetch financial facts
            # (Add your fact retrieval logic here)
        
        return metrics, facts

