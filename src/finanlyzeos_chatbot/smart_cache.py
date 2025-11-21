"""Smart caching system for expensive chatbot operations."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple, Callable
from functools import wraps
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class SmartCache:
    """Intelligent caching system for expensive operations."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._access_times: Dict[str, float] = {}  # key -> last_access_time
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired."""
        return time.time() - timestamp > self.ttl_seconds
    
    def _evict_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            # Remove oldest accessed entries
            sorted_keys = sorted(
                self._access_times.items(), 
                key=lambda x: x[1]
            )
            keys_to_remove = [key for key, _ in sorted_keys[:len(sorted_keys)//4]]  # Remove 25%
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if not self._is_expired(timestamp):
                self._access_times[key] = time.time()
                return value
            else:
                # Remove expired entry
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._evict_expired()
        self._evict_lru()
        
        current_time = time.time()
        self._cache[key] = (value, current_time)
        self._access_times[key] = current_time
    
    def cache_function(self, func: Callable) -> Callable:
        """Decorator to cache function results."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{self._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = self.get(cache_key)
            if cached_result is not None:
                LOGGER.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            LOGGER.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            self.set(cache_key, result)
            return result
        
        return wrapper
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        expired_count = sum(
            1 for _, timestamp in self._cache.values()
            if current_time - timestamp > self.ttl_seconds
        )
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "expired_entries": expired_count,
            "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
        }


# Global cache instances for different types of operations
embedding_cache = SmartCache(max_size=500, ttl_seconds=7200)  # 2 hours for embeddings
retrieval_cache = SmartCache(max_size=200, ttl_seconds=1800)  # 30 minutes for retrieval
context_cache = SmartCache(max_size=100, ttl_seconds=900)     # 15 minutes for context


def cache_embeddings(func: Callable) -> Callable:
    """Cache embedding computations (expensive)."""
    return embedding_cache.cache_function(func)


def cache_retrieval(func: Callable) -> Callable:
    """Cache retrieval results (moderately expensive)."""
    return retrieval_cache.cache_function(func)


def cache_context(func: Callable) -> Callable:
    """Cache context building (expensive)."""
    return context_cache.cache_function(func)


def clear_all_caches() -> None:
    """Clear all smart caches."""
    embedding_cache.clear()
    retrieval_cache.clear()
    context_cache.clear()
    LOGGER.info("All smart caches cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches."""
    return {
        "embedding_cache": embedding_cache.stats(),
        "retrieval_cache": retrieval_cache.stats(),
        "context_cache": context_cache.stats()
    }
