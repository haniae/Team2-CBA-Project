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

# Import smart caching for performance optimization
try:
    from .smart_cache import cache_embeddings, cache_retrieval
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    # Fallback decorators that do nothing
    def cache_embeddings(func): return func
    def cache_retrieval(func): return func

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
    earnings_transcripts: Optional[List[RetrievedDocument]] = None  # Earnings call transcripts
    financial_news: Optional[List[RetrievedDocument]] = None  # Financial news articles
    analyst_reports: Optional[List[RetrievedDocument]] = None  # Analyst research reports
    press_releases: Optional[List[RetrievedDocument]] = None  # Company press releases
    industry_research: Optional[List[RetrievedDocument]] = None  # Industry research reports
    
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
        
        # Initialize embedding model (use shared model for team consistency)
        LOGGER.info(f"Loading embedding model: {embedding_model}")
        try:
            from .shared_embeddings import get_shared_embedding_model
            self.embedding_model = get_shared_embedding_model()
            LOGGER.info("✅ Using shared team embedding model for consistency")
        except Exception as e:
            LOGGER.warning(f"Shared embedding model not available: {e}")
            LOGGER.info("Falling back to individual model download")
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
        """Initialize separate collections for different document types."""
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
        
        # Earnings transcripts collection
        try:
            self.earnings_collection = self.client.get_collection(name=f"{self.collection_name}_earnings")
        except Exception:
            self.earnings_collection = self.client.create_collection(
                name=f"{self.collection_name}_earnings",
                metadata={"description": "Earnings call transcripts (management commentary, Q&A)"}
            )
        
        # Financial news collection
        try:
            self.news_collection = self.client.get_collection(name=f"{self.collection_name}_news")
        except Exception:
            self.news_collection = self.client.create_collection(
                name=f"{self.collection_name}_news",
                metadata={"description": "Financial news articles (market sentiment, breaking news)"}
            )
        
        # Analyst reports collection
        try:
            self.analyst_collection = self.client.get_collection(name=f"{self.collection_name}_analyst")
        except Exception:
            self.analyst_collection = self.client.create_collection(
                name=f"{self.collection_name}_analyst",
                metadata={"description": "Analyst research reports (equity research, price targets)"}
            )
        
        # Press releases collection
        try:
            self.press_collection = self.client.get_collection(name=f"{self.collection_name}_press")
        except Exception:
            self.press_collection = self.client.create_collection(
                name=f"{self.collection_name}_press",
                metadata={"description": "Company press releases (announcements, strategic updates)"}
            )
        
        # Industry research collection
        try:
            self.industry_collection = self.client.get_collection(name=f"{self.collection_name}_industry")
        except Exception:
            self.industry_collection = self.client.create_collection(
                name=f"{self.collection_name}_industry",
                metadata={"description": "Industry research reports (sector analysis, market trends)"}
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
    
    def add_earnings_transcripts(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add earnings call transcripts to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.earnings_collection, batch_size)
    
    def add_financial_news(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add financial news articles to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.news_collection, batch_size)
    
    def add_analyst_reports(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add analyst research reports to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.analyst_collection, batch_size)
    
    def add_press_releases(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add company press releases to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.press_collection, batch_size)
    
    def add_industry_research(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """Add industry research reports to vector store."""
        if not self._available:
            return 0
        return self._add_documents(documents, self.industry_collection, batch_size)
    
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
            metadatas_raw = [doc.get("metadata", {}) for doc in batch]
            
            # Clean metadata: Remove None values (ChromaDB doesn't accept None)
            metadatas = []
            for meta in metadatas_raw:
                cleaned_meta = {k: v for k, v in meta.items() if v is not None}
                metadatas.append(cleaned_meta)
            
            # Generate embeddings: "Text → Tokens → Embeddings"
            embeddings = self.embedding_model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist()
            
            # Generate IDs based on source type
            ids = []
            for j, meta in enumerate(metadatas_raw):  # Use raw metadata for ID generation
                source_type = meta.get('source_type', 'doc')
                ticker = meta.get('ticker', 'unknown')
                
                if source_type == 'sec_filing':
                    doc_id = f"{ticker}_{meta.get('filing_type', 'doc')}_{meta.get('fiscal_year', 'unknown')}_{meta.get('section', 'unknown')}_{i+j}"
                elif source_type == 'earnings_transcript':
                    doc_id = f"{ticker}_earnings_{meta.get('date', 'unknown')}_{meta.get('quarter', 'unknown')}_{i+j}"
                elif source_type == 'news':
                    doc_id = f"{ticker}_news_{meta.get('date', 'unknown')}_{meta.get('publisher', 'unknown')}_{i+j}"
                elif source_type == 'analyst_report':
                    doc_id = f"{ticker}_analyst_{meta.get('date', 'unknown')}_{meta.get('analyst', 'unknown')}_{i+j}"
                elif source_type == 'press_release':
                    doc_id = f"{ticker}_press_{meta.get('date', 'unknown')}_{i+j}"
                elif source_type == 'industry_research':
                    doc_id = f"industry_{meta.get('sector', 'unknown')}_{meta.get('date', 'unknown')}_{i+j}"
                else:
                    doc_id = f"{source_type}_{ticker}_{meta.get('date', 'unknown')}_{i+j}"
                
                ids.append(doc_id)
            
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,  # Use cleaned metadata without None values
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
    
    def search_earnings_transcripts(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over earnings call transcripts."""
        if not self._available:
            return []
        return self._search(query, self.earnings_collection, n_results, filter_metadata, "earnings_transcript")
    
    def search_financial_news(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over financial news articles."""
        if not self._available:
            return []
        return self._search(query, self.news_collection, n_results, filter_metadata, "news")
    
    def search_analyst_reports(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over analyst research reports."""
        if not self._available:
            return []
        return self._search(query, self.analyst_collection, n_results, filter_metadata, "analyst_report")
    
    def search_press_releases(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over company press releases."""
        if not self._available:
            return []
        return self._search(query, self.press_collection, n_results, filter_metadata, "press_release")
    
    def search_industry_research(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """Semantic search over industry research reports."""
        if not self._available:
            return []
        return self._search(query, self.industry_collection, n_results, filter_metadata, "industry_research")
    
    def search_all_sources(
        self,
        query: str,
        n_results_per_source: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[RetrievedDocument]]:
        """Search across all document collections and return results by source."""
        if not self._available:
            return {}
        
        results = {
            "sec_filings": self.search_sec_narratives(query, n_results_per_source, filter_metadata),
            "uploaded_docs": self.search_uploaded_docs(query, n_results_per_source, filter_metadata),
            "earnings_transcripts": self.search_earnings_transcripts(query, n_results_per_source, filter_metadata),
            "financial_news": self.search_financial_news(query, n_results_per_source, filter_metadata),
            "analyst_reports": self.search_analyst_reports(query, n_results_per_source, filter_metadata),
            "press_releases": self.search_press_releases(query, n_results_per_source, filter_metadata),
            "industry_research": self.search_industry_research(query, n_results_per_source, filter_metadata),
        }
        
        return results
    
    @cache_retrieval
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
        max_earnings_results: int = 3,
        max_news_results: int = 3,
        max_analyst_results: int = 3,
        max_press_results: int = 3,
        max_industry_results: int = 2,
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
            max_earnings_results: Max earnings transcripts to retrieve (before reranking)
            max_news_results: Max financial news articles to retrieve (before reranking)
            max_analyst_results: Max analyst reports to retrieve (before reranking)
            max_press_results: Max press releases to retrieve (before reranking)
            max_industry_results: Max industry research to retrieve (before reranking)
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
        
        # 2. PARALLEL Hybrid retrieval (sparse + dense) over SEC narratives
        sec_narratives = []
        if use_semantic_search and tickers:
            # PERFORMANCE OPTIMIZATION: Parallel retrieval instead of sequential
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def retrieve_for_ticker(ticker: str):
                """Retrieve SEC narratives for a single ticker."""
                filter_metadata = {"ticker": ticker.upper()}
                
                if self.use_hybrid_retrieval and self.hybrid_retriever:
                    # Use hybrid retrieval (sparse + dense)
                    try:
                        results = self.hybrid_retriever.retrieve_sec_narratives(
                            query=query,
                            n_results=max_sec_results * 2,  # Retrieve more for reranking
                            filter_metadata=filter_metadata,
                        )
                        LOGGER.debug(f"Hybrid retrieval: {len(results)} SEC documents for {ticker}")
                        return results
                    except Exception as e:
                        LOGGER.warning(f"Hybrid retrieval failed for {ticker}, falling back to dense-only: {e}")
                        # Fallback to dense-only
                        if self.vector_store and self.vector_store._available:
                            results = self.vector_store.search_sec_narratives(
                                query=query,
                                n_results=max_sec_results * 2,
                                filter_metadata=filter_metadata,
                            )
                            return results
                elif self.vector_store and self.vector_store._available:
                    # Dense-only retrieval (fallback)
                    results = self.vector_store.search_sec_narratives(
                        query=query,
                        n_results=max_sec_results * 2,
                        filter_metadata=filter_metadata,
                    )
                    return results
                return []
            
            # Execute retrievals in parallel (3-5x faster than sequential)
            max_workers = min(len(tickers), 4)  # Limit concurrent requests
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all ticker retrievals
                future_to_ticker = {
                    executor.submit(retrieve_for_ticker, ticker): ticker 
                    for ticker in tickers
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    try:
                        results = future.result()
                        if results:
                            sec_narratives.extend(results)
                    except Exception as e:
                        LOGGER.warning(f"Parallel retrieval failed for {ticker}: {e}")
            
            LOGGER.debug(f"Parallel SEC retrieval completed: {len(sec_narratives)} total documents")
        
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
        
        # 4. Retrieve from additional collections (earnings, news, analyst, press, industry)
        earnings_transcripts = []
        financial_news = []
        analyst_reports = []
        press_releases = []
        industry_research = []
        
        if use_semantic_search and tickers and self.vector_store and self.vector_store._available:
            # Use parallel retrieval for all additional collections
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def retrieve_additional_sources():
                """Retrieve from all additional collections in parallel."""
                results = {
                    "earnings": [],
                    "news": [],
                    "analyst": [],
                    "press": [],
                    "industry": [],
                }
                
                def search_collection(collection_name: str, search_func, max_results: int):
                    """Helper to search a collection for all tickers."""
                    all_results = []
                    # Retrieve max_results per ticker to get diverse results across tickers
                    results_per_ticker = max(2, max_results // max(len(tickers), 1))
                    for ticker in tickers:
                        try:
                            filter_metadata = {"ticker": ticker.upper()}
                            ticker_results = search_func(
                                query=query,
                                n_results=results_per_ticker,
                                filter_metadata=filter_metadata,
                            )
                            all_results.extend(ticker_results)
                        except Exception as e:
                            LOGGER.debug(f"Retrieval from {collection_name} failed for {ticker}: {e}")
                    return all_results
                
                # Search all collections in parallel
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = {
                        executor.submit(
                            search_collection,
                            "earnings",
                            self.vector_store.search_earnings_transcripts,
                            max_earnings_results
                        ): "earnings",
                        executor.submit(
                            search_collection,
                            "news",
                            self.vector_store.search_financial_news,
                            max_news_results
                        ): "news",
                        executor.submit(
                            search_collection,
                            "analyst",
                            self.vector_store.search_analyst_reports,
                            max_analyst_results
                        ): "analyst",
                        executor.submit(
                            search_collection,
                            "press",
                            self.vector_store.search_press_releases,
                            max_press_results
                        ): "press",
                        executor.submit(
                            search_collection,
                            "industry",
                            self.vector_store.search_industry_research,
                            max_industry_results
                        ): "industry",
                    }
                    
                    for future in as_completed(futures):
                        collection_name = futures[future]
                        try:
                            results[collection_name] = future.result()
                            LOGGER.debug(f"Retrieved {len(results[collection_name])} documents from {collection_name}")
                        except Exception as e:
                            LOGGER.warning(f"Retrieval from {collection_name} failed: {e}")
                
                return results
            
            try:
                additional_results = retrieve_additional_sources()
                earnings_transcripts = additional_results["earnings"]
                financial_news = additional_results["news"]
                analyst_reports = additional_results["analyst"]
                press_releases = additional_results["press"]
                industry_research = additional_results["industry"]
                
                LOGGER.debug(
                    f"Additional collections retrieval: "
                    f"{len(earnings_transcripts)} earnings, "
                    f"{len(financial_news)} news, "
                    f"{len(analyst_reports)} analyst, "
                    f"{len(press_releases)} press, "
                    f"{len(industry_research)} industry"
                )
            except Exception as e:
                LOGGER.warning(f"Additional collections retrieval failed: {e}")
                import traceback
                LOGGER.debug(f"Additional collections retrieval traceback: {traceback.format_exc()}")
                # Ensure lists are initialized even if retrieval fails
                earnings_transcripts = []
                financial_news = []
                analyst_reports = []
                press_releases = []
                industry_research = []
        
        retrieval_time_ms = (time.time() - start_time) * 1000
        
        # 5. Limit results before reranking (if reranking disabled, this is the final limit)
        # Limit SEC and uploaded docs if reranking is disabled
        if not use_reranking:
            sec_narratives = sec_narratives[:max_sec_results] if sec_narratives else []
            uploaded_docs = uploaded_docs[:max_uploaded_results] if uploaded_docs else []
        
        # 6. Reranking stage (if enabled)
        # Note: Reranker currently supports SEC and uploaded docs only
        # Additional collections are returned as-is (can be enhanced later)
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
                    # Fallback: limit results if reranking fails
                    sec_narratives = sec_narratives[:max_sec_results] if sec_narratives else []
                    uploaded_docs = uploaded_docs[:max_uploaded_results] if uploaded_docs else []
        
        # 7. Limit results from additional collections (simple top-k, no reranking yet)
        # Apply limits after retrieval to respect max_*_results parameters
        earnings_transcripts = earnings_transcripts[:max_earnings_results] if earnings_transcripts else []
        financial_news = financial_news[:max_news_results] if financial_news else []
        analyst_reports = analyst_reports[:max_analyst_results] if analyst_reports else []
        press_releases = press_releases[:max_press_results] if press_releases else []
        industry_research = industry_research[:max_industry_results] if industry_research else []
        
        # 8. Apply guardrails (if observer provided)
        # Return empty lists instead of None for consistency (dataclass allows None, but lists are better)
        result = RetrievalResult(
            metrics=metrics,
            facts=facts,
            sec_narratives=sec_narratives,
            uploaded_docs=uploaded_docs,
            earnings_transcripts=earnings_transcripts,  # Already a list (empty if no results)
            financial_news=financial_news,  # Already a list (empty if no results)
            analyst_reports=analyst_reports,  # Already a list (empty if no results)
            press_releases=press_releases,  # Already a list (empty if no results)
            industry_research=industry_research,  # Already a list (empty if no results)
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

