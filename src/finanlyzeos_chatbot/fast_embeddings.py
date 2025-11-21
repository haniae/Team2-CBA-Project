"""Fast, lightweight embedding models optimized for financial domain."""

from __future__ import annotations

import logging
import numpy as np
import time
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class FastFinancialEmbeddings:
    """Lightweight embedding model optimized for financial queries."""
    
    def __init__(self, model_name: str = "fast-financial", cache_size: int = 1000):
        self.model_name = model_name
        self.cache_size = cache_size
        self.embedding_cache: Dict[str, np.ndarray] = {}
        self.model = None
        self.tokenizer = None
        
        # Financial domain vocabulary for better embeddings
        self.financial_vocab = {
            # Core financial terms
            "revenue", "earnings", "profit", "loss", "margin", "ebitda", "cash", "debt",
            "equity", "assets", "liabilities", "dividend", "yield", "ratio", "growth",
            "valuation", "market", "cap", "price", "stock", "share", "volume", "volatility",
            
            # Metrics and KPIs
            "pe", "pb", "roe", "roa", "roi", "fcf", "operating", "net", "gross", "current",
            "quick", "debt-to-equity", "interest", "coverage", "turnover", "efficiency",
            
            # Time periods
            "quarterly", "annual", "fy", "q1", "q2", "q3", "q4", "ytd", "ttm", "yoy",
            
            # Company types and sectors
            "technology", "healthcare", "financial", "energy", "consumer", "industrial",
            "materials", "utilities", "telecommunications", "real estate",
        }
        
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the embedding model."""
        try:
            # Try to use a fast, small model first
            self._try_fast_model()
        except Exception as e:
            LOGGER.warning(f"Fast model initialization failed: {e}")
            try:
                # Fallback to standard model
                self._try_standard_model()
            except Exception as e2:
                LOGGER.warning(f"Standard model initialization failed: {e2}")
                # Ultimate fallback to simple embeddings
                self._initialize_simple_embeddings()
    
    def _try_fast_model(self) -> None:
        """Try to initialize a fast, lightweight model."""
        try:
            # Try sentence-transformers with a small model
            from sentence_transformers import SentenceTransformer
            
            # Use a small, fast model (only 22MB vs 90MB for all-MiniLM-L6-v2)
            model_candidates = [
                "all-MiniLM-L12-v1",      # Faster than L6-v2
                "paraphrase-MiniLM-L3-v2", # Very small and fast
                "all-distilroberta-v1",    # Distilled model
            ]
            
            for model_name in model_candidates:
                try:
                    LOGGER.info(f"Trying fast embedding model: {model_name}")
                    self.model = SentenceTransformer(model_name)
                    self.model_name = model_name
                    LOGGER.info(f"✅ Loaded fast embedding model: {model_name}")
                    return
                except Exception as e:
                    LOGGER.debug(f"Failed to load {model_name}: {e}")
                    continue
            
            raise Exception("No fast models available")
            
        except ImportError:
            raise Exception("sentence-transformers not available")
    
    def _try_standard_model(self) -> None:
        """Fallback to standard model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.model_name = "all-MiniLM-L6-v2"
            LOGGER.info("✅ Loaded standard embedding model")
        except Exception:
            raise Exception("Standard model not available")
    
    def _initialize_simple_embeddings(self) -> None:
        """Initialize simple TF-IDF based embeddings as ultimate fallback."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Create a simple TF-IDF vectorizer with financial vocabulary
            self.model = TfidfVectorizer(
                max_features=384,  # Match standard embedding dimension
                ngram_range=(1, 2),
                vocabulary=list(self.financial_vocab) if self.financial_vocab else None,
                lowercase=True,
                stop_words='english'
            )
            
            # Fit on financial vocabulary
            if self.financial_vocab:
                sample_docs = [" ".join(self.financial_vocab)]
                self.model.fit(sample_docs)
            
            self.model_name = "simple-tfidf"
            LOGGER.info("✅ Loaded simple TF-IDF embeddings")
            
        except ImportError:
            # Final fallback - random embeddings (for testing only)
            self.model = None
            self.model_name = "random"
            LOGGER.warning("⚠️ Using random embeddings - install sentence-transformers for better performance")
    
    def encode(
        self, 
        texts: Union[str, List[str]], 
        batch_size: int = 32,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        Encode texts to embeddings with caching and optimization.
        
        Args:
            texts: Single text or list of texts to encode
            batch_size: Batch size for processing
            show_progress_bar: Whether to show progress
            
        Returns:
            Numpy array of embeddings
        """
        start_time = time.time()
        
        # Handle single text
        if isinstance(texts, str):
            texts = [texts]
        
        # Check cache first
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self.embedding_cache:
                cached_embeddings.append((i, self.embedding_cache[cache_key]))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Compute embeddings for uncached texts
        new_embeddings = []
        if uncached_texts:
            new_embeddings = self._compute_embeddings(uncached_texts, batch_size)
            
            # Cache new embeddings
            for text, embedding in zip(uncached_texts, new_embeddings):
                cache_key = self._get_cache_key(text)
                self._add_to_cache(cache_key, embedding)
        
        # Combine cached and new embeddings
        all_embeddings = [None] * len(texts)
        
        # Add cached embeddings
        for idx, embedding in cached_embeddings:
            all_embeddings[idx] = embedding
        
        # Add new embeddings
        for i, embedding in enumerate(new_embeddings):
            original_idx = uncached_indices[i]
            all_embeddings[original_idx] = embedding
        
        result = np.array(all_embeddings)
        
        # Log performance
        elapsed = time.time() - start_time
        cache_hit_rate = len(cached_embeddings) / len(texts) if texts else 0
        LOGGER.debug(
            f"Encoded {len(texts)} texts in {elapsed:.3f}s "
            f"(cache hit rate: {cache_hit_rate:.1%})"
        )
        
        return result
    
    def _compute_embeddings(self, texts: List[str], batch_size: int) -> List[np.ndarray]:
        """Compute embeddings for texts using the loaded model."""
        if self.model is None:
            # Random embeddings fallback
            return [np.random.randn(384).astype(np.float32) for _ in texts]
        
        if self.model_name == "simple-tfidf":
            # TF-IDF embeddings
            try:
                embeddings = self.model.transform(texts).toarray()
                return [emb.astype(np.float32) for emb in embeddings]
            except Exception as e:
                LOGGER.warning(f"TF-IDF encoding failed: {e}")
                return [np.random.randn(384).astype(np.float32) for _ in texts]
        
        else:
            # Sentence transformer embeddings
            try:
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                return [emb.astype(np.float32) for emb in embeddings]
            except Exception as e:
                LOGGER.warning(f"Sentence transformer encoding failed: {e}")
                return [np.random.randn(384).astype(np.float32) for _ in texts]
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        # Simple hash-based key
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def _add_to_cache(self, key: str, embedding: np.ndarray) -> None:
        """Add embedding to cache with LRU eviction."""
        if len(self.embedding_cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self.embedding_cache))
            del self.embedding_cache[oldest_key]
        
        self.embedding_cache[key] = embedding
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        embeddings = self.encode([text1, text2])
        
        # Cosine similarity
        dot_product = np.dot(embeddings[0], embeddings[1])
        norm1 = np.linalg.norm(embeddings[0])
        norm2 = np.linalg.norm(embeddings[1])
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "cache_size": len(self.embedding_cache),
            "max_cache_size": self.cache_size,
            "model_type": type(self.model).__name__ if self.model else "None",
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.embedding_cache.clear()
        LOGGER.info("Embedding cache cleared")


# Global instance for reuse
_global_embeddings: Optional[FastFinancialEmbeddings] = None


def get_fast_embeddings(model_name: str = "fast-financial") -> FastFinancialEmbeddings:
    """Get or create the global fast embeddings instance."""
    global _global_embeddings
    
    if _global_embeddings is None or _global_embeddings.model_name != model_name:
        _global_embeddings = FastFinancialEmbeddings(model_name)
    
    return _global_embeddings


def encode_texts(texts: Union[str, List[str]], **kwargs) -> np.ndarray:
    """Convenience function to encode texts with fast embeddings."""
    embeddings = get_fast_embeddings()
    return embeddings.encode(texts, **kwargs)


def text_similarity(text1: str, text2: str) -> float:
    """Convenience function to compute text similarity."""
    embeddings = get_fast_embeddings()
    return embeddings.similarity(text1, text2)


def benchmark_embedding_speed(num_texts: int = 100, text_length: int = 50) -> Dict[str, float]:
    """Benchmark embedding speed for performance testing."""
    import random
    import string
    
    # Generate random texts
    texts = []
    for _ in range(num_texts):
        text = " ".join([
            "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
            for _ in range(text_length)
        ])
        texts.append(text)
    
    embeddings = get_fast_embeddings()
    
    # Benchmark
    start_time = time.time()
    result = embeddings.encode(texts)
    end_time = time.time()
    
    total_time = end_time - start_time
    texts_per_second = num_texts / total_time
    
    return {
        "total_time": total_time,
        "texts_per_second": texts_per_second,
        "model_name": embeddings.model_name,
        "embedding_dimension": result.shape[1] if len(result.shape) > 1 else 0,
    }
