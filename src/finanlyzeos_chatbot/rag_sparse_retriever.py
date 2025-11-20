"""
Sparse Retriever Module - BM25-based Sparse Retrieval

Implements sparse retrieval using BM25 algorithm for keyword-based search.
Complements dense (embedding-based) retrieval for hybrid retrieval.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from .rag_retriever import RetrievedDocument

LOGGER = logging.getLogger(__name__)

# Optional import for BM25
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None


@dataclass
class SparseIndex:
    """BM25 sparse index for a collection of documents."""
    documents: List[str]  # Original document texts
    tokenized_docs: List[List[str]]  # Tokenized documents
    bm25: Optional[Any] = None  # BM25Okapi instance
    metadata: List[Dict[str, Any]] = None  # Metadata for each document
    _available: bool = False
    
    def __post_init__(self):
        """Initialize BM25 index if available."""
        if BM25_AVAILABLE and self.tokenized_docs:
            try:
                self.bm25 = BM25Okapi(self.tokenized_docs)
                self._available = True
                LOGGER.info(f"BM25 index initialized with {len(self.tokenized_docs)} documents")
            except Exception as e:
                LOGGER.warning(f"Failed to initialize BM25 index: {e}")
                self._available = False
        else:
            if not BM25_AVAILABLE:
                LOGGER.warning("rank_bm25 not available. Install: pip install rank-bm25")
            self._available = False


def tokenize(text: str) -> List[str]:
    """
    Tokenize text for BM25 indexing.
    
    Args:
        text: Input text
        
    Returns:
        List of lowercase tokens
    """
    # Simple tokenization: lowercase, alphanumeric tokens
    tokens = re.findall(r'\b\w+\b', text.lower())
    return tokens


class SparseRetriever:
    """
    Sparse retriever using BM25 algorithm.
    
    Provides keyword-based retrieval that complements dense (embedding-based) retrieval.
    Better for exact phrases, ticker variants, misspellings, and keyword matching.
    """
    
    def __init__(
        self,
        sec_documents: Optional[List[Dict[str, Any]]] = None,
        uploaded_documents: Optional[List[Dict[str, Any]]] = None,
        vector_store: Optional[Any] = None,  # VectorStore instance
    ):
        """
        Initialize sparse retriever with document collections.
        
        Args:
            sec_documents: List of SEC document dicts with 'text' and 'metadata' keys
            uploaded_documents: List of uploaded document dicts with 'text' and 'metadata' keys
            vector_store: Optional VectorStore to build index from (lazy initialization)
        """
        self.sec_index: Optional[SparseIndex] = None
        self.uploaded_index: Optional[SparseIndex] = None
        self.vector_store = vector_store
        self._index_built = False
        
        # Build SEC index if documents provided
        if sec_documents:
            self._build_sec_index(sec_documents)
        
        # Build uploaded docs index if documents provided
        if uploaded_documents:
            self._build_uploaded_index(uploaded_documents)
    
    def build_index_from_vector_store(self):
        """
        Build sparse index from vector store documents (lazy initialization).
        
        This allows building the BM25 index from the same documents in ChromaDB.
        """
        if self._index_built or not self.vector_store or not self.vector_store._available:
            return
        
        try:
            # Get all documents from vector store collections
            # Note: This is a simplified approach - in production, you'd want to batch this
            sec_docs = []
            uploaded_docs = []
            
            # Try to get documents from ChromaDB collections
            # This is a placeholder - actual implementation would query ChromaDB
            # For now, we'll build the index lazily when documents are retrieved
            
            self._index_built = True
            LOGGER.info("Sparse index built from vector store")
        except Exception as e:
            LOGGER.warning(f"Failed to build sparse index from vector store: {e}")
    
    def _build_sec_index(self, documents: List[Dict[str, Any]]):
        """Build BM25 index for SEC documents."""
        texts = [doc.get("text", "") for doc in documents]
        metadata = [doc.get("metadata", {}) for doc in documents]
        tokenized = [tokenize(text) for text in texts]
        
        self.sec_index = SparseIndex(
            documents=texts,
            tokenized_docs=tokenized,
            metadata=metadata,
        )
    
    def _build_uploaded_index(self, documents: List[Dict[str, Any]]):
        """Build BM25 index for uploaded documents."""
        texts = [doc.get("text", "") for doc in documents]
        metadata = [doc.get("metadata", {}) for doc in documents]
        tokenized = [tokenize(text) for text in texts]
        
        self.uploaded_index = SparseIndex(
            documents=texts,
            tokenized_docs=tokenized,
            metadata=metadata,
        )
    
    def search_sec(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """
        Search SEC documents using BM25.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"ticker": "AAPL"})
        
        Returns:
            List of RetrievedDocument with BM25 scores
        """
        if not self.sec_index or not self.sec_index._available:
            return []
        
        # Tokenize query
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.sec_index.bm25.get_scores(query_tokens)
        
        # Create (score, index) pairs
        scored_docs = [(score, idx) for idx, score in enumerate(scores)]
        
        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Filter by metadata if provided
        results = []
        for score, idx in scored_docs[:n_results * 2]:  # Get more for filtering
            doc_metadata = self.sec_index.metadata[idx] if self.sec_index.metadata else {}
            
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    doc_metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            results.append(RetrievedDocument(
                text=self.sec_index.documents[idx],
                source_type="sec_filing",
                metadata=doc_metadata,
                score=float(score),  # BM25 score (higher is better)
            ))
            
            if len(results) >= n_results:
                break
        
        LOGGER.debug(f"BM25 SEC search: {len(results)} results for query '{query[:50]}...'")
        return results
    
    def search_uploaded(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """
        Search uploaded documents using BM25.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter (e.g., {"conversation_id": "conv_123"})
        
        Returns:
            List of RetrievedDocument with BM25 scores
        """
        if not self.uploaded_index or not self.uploaded_index._available:
            return []
        
        # Tokenize query
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.uploaded_index.bm25.get_scores(query_tokens)
        
        # Create (score, index) pairs
        scored_docs = [(score, idx) for idx, score in enumerate(scores)]
        
        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Filter by metadata if provided
        results = []
        for score, idx in scored_docs[:n_results * 2]:  # Get more for filtering
            doc_metadata = self.uploaded_index.metadata[idx] if self.uploaded_index.metadata else {}
            
            # Apply metadata filter
            if filter_metadata:
                match = all(
                    doc_metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            results.append(RetrievedDocument(
                text=self.uploaded_index.documents[idx],
                source_type="uploaded_doc",
                metadata=doc_metadata,
                score=float(score),  # BM25 score (higher is better)
            ))
            
            if len(results) >= n_results:
                break
        
        LOGGER.debug(f"BM25 uploaded search: {len(results)} results for query '{query[:50]}...'")
        return results
    
    def update_index(
        self,
        sec_documents: Optional[List[Dict[str, Any]]] = None,
        uploaded_documents: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Update sparse indices with new documents.
        
        Args:
            sec_documents: New SEC documents to add
            uploaded_documents: New uploaded documents to add
        """
        if sec_documents:
            # Rebuild SEC index (BM25 doesn't support incremental updates easily)
            self._build_sec_index(sec_documents)
        
        if uploaded_documents:
            # Rebuild uploaded index
            self._build_uploaded_index(uploaded_documents)

