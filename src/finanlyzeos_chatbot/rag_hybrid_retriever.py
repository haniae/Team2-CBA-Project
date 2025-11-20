"""
Hybrid Retriever - Combines Sparse (BM25) and Dense (Embedding) Retrieval

Implements hybrid retrieval that fuses:
- Dense retrieval: Semantic search using embeddings (sentence-transformers)
- Sparse retrieval: Keyword-based search using BM25

This provides robustness for:
- Exact phrases and keywords (sparse)
- Semantic meaning (dense)
- Ticker variants and misspellings (sparse)
- Contextual understanding (dense)
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .rag_retriever import RetrievedDocument, VectorStore
from .rag_sparse_retriever import SparseRetriever
from .rag_fusion import SourceFusion

LOGGER = logging.getLogger(__name__)


@dataclass
class HybridRetrievalConfig:
    """Configuration for hybrid retrieval."""
    k_dense: int = 20  # Number of dense results to retrieve
    k_sparse: int = 20  # Number of sparse results to retrieve
    k_final: int = 10  # Final number of results after fusion
    dense_weight: float = 0.6  # Weight for dense scores
    sparse_weight: float = 0.4  # Weight for sparse scores
    use_hybrid: bool = True  # Enable hybrid retrieval


class HybridRetriever:
    """
    Hybrid retriever that combines sparse (BM25) and dense (embedding) retrieval.
    
    Fuses results from both methods to get the best of both worlds:
    - Dense: Semantic understanding, contextual similarity
    - Sparse: Exact keyword matching, ticker variants, misspellings
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        fusion: Optional[SourceFusion] = None,
        config: Optional[HybridRetrievalConfig] = None,
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: VectorStore for dense retrieval
            sparse_retriever: SparseRetriever for BM25 retrieval
            fusion: SourceFusion for fusing sparse and dense results
            config: HybridRetrievalConfig
        """
        self.vector_store = vector_store
        self.sparse_retriever = sparse_retriever
        self.fusion = fusion or SourceFusion()
        self.config = config or HybridRetrievalConfig()
    
    def retrieve_sec_narratives(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """
        Retrieve SEC narratives using hybrid sparse+dense retrieval.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
        
        Returns:
            List of RetrievedDocument with fused scores
        """
        if not self.config.use_hybrid:
            # Fallback to dense-only if hybrid disabled
            if self.vector_store:
                return self.vector_store.search_sec_narratives(
                    query, n_results, filter_metadata
                )
            return []
        
        dense_hits = []
        sparse_hits = []
        
        # Dense retrieval (embeddings)
        if self.vector_store and self.vector_store._available:
            try:
                dense_hits = self.vector_store.search_sec_narratives(
                    query,
                    n_results=self.config.k_dense,
                    filter_metadata=filter_metadata,
                )
                LOGGER.debug(f"Dense retrieval: {len(dense_hits)} SEC documents")
            except Exception as e:
                LOGGER.warning(f"Dense retrieval failed: {e}")
        
        # Sparse retrieval (BM25)
        if self.sparse_retriever:
            try:
                sparse_hits = self.sparse_retriever.search_sec(
                    query,
                    n_results=self.config.k_sparse,
                    filter_metadata=filter_metadata,
                )
                LOGGER.debug(f"Sparse retrieval: {len(sparse_hits)} SEC documents")
            except Exception as e:
                LOGGER.warning(f"Sparse retrieval failed: {e}")
        
        # Fuse results
        if dense_hits or sparse_hits:
            fused = self.fusion.fuse_sparse_dense(
                dense_hits=dense_hits,
                sparse_hits=sparse_hits,
                dense_weight=self.config.dense_weight,
                sparse_weight=self.config.sparse_weight,
            )
            
            # Return top k_final
            return fused[:self.config.k_final]
        
        return []
    
    def retrieve_uploaded_docs(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedDocument]:
        """
        Retrieve uploaded documents using hybrid sparse+dense retrieval.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
        
        Returns:
            List of RetrievedDocument with fused scores
        """
        if not self.config.use_hybrid:
            # Fallback to dense-only if hybrid disabled
            if self.vector_store:
                return self.vector_store.search_uploaded_docs(
                    query, n_results, filter_metadata
                )
            return []
        
        dense_hits = []
        sparse_hits = []
        
        # Dense retrieval (embeddings)
        if self.vector_store and self.vector_store._available:
            try:
                dense_hits = self.vector_store.search_uploaded_docs(
                    query,
                    n_results=self.config.k_dense,
                    filter_metadata=filter_metadata,
                )
                LOGGER.debug(f"Dense retrieval: {len(dense_hits)} uploaded documents")
            except Exception as e:
                LOGGER.warning(f"Dense retrieval failed: {e}")
        
        # Sparse retrieval (BM25)
        if self.sparse_retriever:
            try:
                # Build index from vector store if not already built
                if not self.sparse_retriever._index_built:
                    self.sparse_retriever.build_index_from_vector_store()
                
                sparse_hits = self.sparse_retriever.search_uploaded(
                    query,
                    n_results=self.config.k_sparse,
                    filter_metadata=filter_metadata,
                )
                LOGGER.debug(f"Sparse retrieval: {len(sparse_hits)} uploaded documents")
            except Exception as e:
                LOGGER.warning(f"Sparse retrieval failed: {e}")
                sparse_hits = []
        
        # Fuse results
        if dense_hits or sparse_hits:
            fused = self.fusion.fuse_sparse_dense(
                dense_hits=dense_hits,
                sparse_hits=sparse_hits,
                dense_weight=self.config.dense_weight,
                sparse_weight=self.config.sparse_weight,
            )
            
            # Return top k_final
            return fused[:self.config.k_final]
        
        return []
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retrieval method usage.
        
        Returns:
            Dictionary with retrieval statistics
        """
        return {
            "use_hybrid": self.config.use_hybrid,
            "dense_weight": self.config.dense_weight,
            "sparse_weight": self.config.sparse_weight,
            "dense_available": self.vector_store is not None and self.vector_store._available,
            "sparse_available": self.sparse_retriever is not None,
        }

