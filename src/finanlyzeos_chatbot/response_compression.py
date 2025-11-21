"""Response compression for large chatbot responses."""

from __future__ import annotations

import gzip
import json
import logging
import zlib
from typing import Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

LOGGER = logging.getLogger(__name__)


class CompressionType(Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    BROTLI = "brotli"


@dataclass
class CompressionResult:
    """Result of compression operation."""
    compressed_data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_type: CompressionType
    encoding: str = "utf-8"
    
    @property
    def space_saved(self) -> int:
        """Bytes saved by compression."""
        return self.original_size - self.compressed_size
    
    @property
    def space_saved_percent(self) -> float:
        """Percentage of space saved."""
        if self.original_size == 0:
            return 0.0
        return (self.space_saved / self.original_size) * 100


class ResponseCompressor:
    """High-performance response compression for chatbot responses."""
    
    def __init__(self, min_size_threshold: int = 1024, default_compression: CompressionType = CompressionType.GZIP):
        self.min_size_threshold = min_size_threshold
        self.default_compression = default_compression
        
        # Check available compression libraries
        self.available_compressions = {CompressionType.NONE, CompressionType.GZIP, CompressionType.ZLIB}
        
        try:
            import brotli
            self.available_compressions.add(CompressionType.BROTLI)
        except ImportError:
            pass
    
    def should_compress(self, data: Union[str, bytes, Dict[str, Any]]) -> bool:
        """Determine if data should be compressed based on size."""
        if isinstance(data, dict):
            data = json.dumps(data, separators=(',', ':'))
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return len(data) >= self.min_size_threshold
    
    def compress_response(
        self, 
        response: Union[str, Dict[str, Any]], 
        compression_type: Optional[CompressionType] = None,
        level: int = 6
    ) -> CompressionResult:
        """
        Compress a chatbot response.
        
        Args:
            response: Response to compress (string or dict)
            compression_type: Type of compression to use
            level: Compression level (1-9, higher = better compression)
            
        Returns:
            CompressionResult with compressed data and statistics
        """
        # Convert response to string if needed
        if isinstance(response, dict):
            response_str = json.dumps(response, separators=(',', ':'), ensure_ascii=False)
        else:
            response_str = str(response)
        
        # Encode to bytes
        original_data = response_str.encode('utf-8')
        original_size = len(original_data)
        
        # Choose compression type
        if compression_type is None:
            compression_type = self._choose_best_compression(original_data)
        
        # Skip compression if data is too small
        if not self.should_compress(original_data):
            return CompressionResult(
                compressed_data=original_data,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=1.0,
                compression_type=CompressionType.NONE
            )
        
        # Compress data
        compressed_data = self._compress_data(original_data, compression_type, level)
        compressed_size = len(compressed_data)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        return CompressionResult(
            compressed_data=compressed_data,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_type=compression_type
        )
    
    def decompress_response(self, result: CompressionResult) -> str:
        """
        Decompress a compressed response.
        
        Args:
            result: CompressionResult from compress_response
            
        Returns:
            Original response string
        """
        if result.compression_type == CompressionType.NONE:
            return result.compressed_data.decode(result.encoding)
        
        decompressed_data = self._decompress_data(result.compressed_data, result.compression_type)
        return decompressed_data.decode(result.encoding)
    
    def _choose_best_compression(self, data: bytes) -> CompressionType:
        """Choose the best compression type for the data."""
        # For text data (which chatbot responses are), Brotli usually works best
        if CompressionType.BROTLI in self.available_compressions:
            return CompressionType.BROTLI
        elif CompressionType.GZIP in self.available_compressions:
            return CompressionType.GZIP
        else:
            return CompressionType.ZLIB
    
    def _compress_data(self, data: bytes, compression_type: CompressionType, level: int) -> bytes:
        """Compress data using specified compression type."""
        try:
            if compression_type == CompressionType.GZIP:
                return gzip.compress(data, compresslevel=level)
            
            elif compression_type == CompressionType.ZLIB:
                return zlib.compress(data, level)
            
            elif compression_type == CompressionType.BROTLI:
                try:
                    import brotli
                    return brotli.compress(data, quality=level)
                except ImportError:
                    LOGGER.warning("Brotli not available, falling back to gzip")
                    return gzip.compress(data, compresslevel=level)
            
            else:
                return data  # No compression
                
        except Exception as e:
            LOGGER.warning(f"Compression failed with {compression_type}: {e}")
            return data  # Return original data on failure
    
    def _decompress_data(self, data: bytes, compression_type: CompressionType) -> bytes:
        """Decompress data using specified compression type."""
        try:
            if compression_type == CompressionType.GZIP:
                return gzip.decompress(data)
            
            elif compression_type == CompressionType.ZLIB:
                return zlib.decompress(data)
            
            elif compression_type == CompressionType.BROTLI:
                try:
                    import brotli
                    return brotli.decompress(data)
                except ImportError:
                    raise ValueError("Brotli not available for decompression")
            
            else:
                return data  # No decompression needed
                
        except Exception as e:
            LOGGER.error(f"Decompression failed with {compression_type}: {e}")
            raise
    
    def benchmark_compression(self, test_data: str) -> Dict[CompressionType, CompressionResult]:
        """Benchmark different compression types on test data."""
        results = {}
        
        for compression_type in self.available_compressions:
            if compression_type == CompressionType.NONE:
                continue
                
            try:
                result = self.compress_response(test_data, compression_type)
                results[compression_type] = result
            except Exception as e:
                LOGGER.warning(f"Benchmark failed for {compression_type}: {e}")
        
        return results


# Global compressor instance
_global_compressor: Optional[ResponseCompressor] = None


def get_compressor() -> ResponseCompressor:
    """Get or create the global response compressor."""
    global _global_compressor
    
    if _global_compressor is None:
        _global_compressor = ResponseCompressor()
    
    return _global_compressor


def compress_if_beneficial(
    response: Union[str, Dict[str, Any]], 
    min_compression_ratio: float = 0.8
) -> Tuple[Union[str, bytes], bool, Optional[CompressionResult]]:
    """
    Compress response only if it provides significant benefit.
    
    Args:
        response: Response to potentially compress
        min_compression_ratio: Only compress if ratio is below this threshold
        
    Returns:
        Tuple of (data, was_compressed, compression_result)
    """
    compressor = get_compressor()
    
    # Try compression
    result = compressor.compress_response(response)
    
    # Check if compression is beneficial
    if result.compression_ratio < min_compression_ratio:
        return result.compressed_data, True, result
    else:
        # Compression not beneficial, return original
        if isinstance(response, dict):
            response = json.dumps(response, separators=(',', ':'), ensure_ascii=False)
        return response, False, None


def add_compression_headers(compression_result: CompressionResult) -> Dict[str, str]:
    """Generate HTTP headers for compressed response."""
    headers = {}
    
    if compression_result.compression_type != CompressionType.NONE:
        if compression_result.compression_type == CompressionType.GZIP:
            headers["Content-Encoding"] = "gzip"
        elif compression_result.compression_type == CompressionType.BROTLI:
            headers["Content-Encoding"] = "br"
        elif compression_result.compression_type == CompressionType.ZLIB:
            headers["Content-Encoding"] = "deflate"
        
        headers["Content-Length"] = str(compression_result.compressed_size)
        headers["X-Original-Size"] = str(compression_result.original_size)
        headers["X-Compression-Ratio"] = f"{compression_result.compression_ratio:.3f}"
    
    return headers


def benchmark_response_compression(sample_responses: Optional[List[str]] = None) -> Dict[str, Any]:
    """Benchmark compression performance on sample responses."""
    if sample_responses is None:
        # Generate sample responses of different sizes
        sample_responses = [
            "Short response",
            "Medium response with some financial data like revenue of $1.2B and earnings of $0.5B for Apple Inc.",
            "Long response " * 100 + "with detailed financial analysis including revenue trends, profit margins, cash flow analysis, and competitive positioning in the technology sector.",
            json.dumps({
                "response": "Detailed financial analysis",
                "data": {
                    "metrics": [{"ticker": "AAPL", "revenue": 1200000000, "earnings": 500000000}] * 50,
                    "trends": ["growth"] * 20,
                    "analysis": "Comprehensive analysis " * 100
                }
            })
        ]
    
    compressor = get_compressor()
    results = {}
    
    for i, response in enumerate(sample_responses):
        response_results = compressor.benchmark_compression(response)
        
        results[f"response_{i+1}"] = {
            "original_size": len(response.encode('utf-8')),
            "compressions": {
                comp_type.value: {
                    "compressed_size": result.compressed_size,
                    "ratio": result.compression_ratio,
                    "space_saved_percent": result.space_saved_percent
                }
                for comp_type, result in response_results.items()
            }
        }
    
    return results


if __name__ == "__main__":
    # Demo compression
    sample_response = {
        "reply": "Apple Inc. (AAPL) has shown strong financial performance " * 20,
        "metrics": [{"ticker": "AAPL", "revenue": 1200000000}] * 10,
        "trends": ["growth", "profitability", "efficiency"] * 5
    }
    
    compressor = get_compressor()
    result = compressor.compress_response(sample_response)
    
    print(f"Original size: {result.original_size} bytes")
    print(f"Compressed size: {result.compressed_size} bytes")
    print(f"Compression ratio: {result.compression_ratio:.3f}")
    print(f"Space saved: {result.space_saved_percent:.1f}%")
    print(f"Compression type: {result.compression_type.value}")
    
    # Test decompression
    decompressed = compressor.decompress_response(result)
    print(f"Decompression successful: {len(decompressed) > 0}")
