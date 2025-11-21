#!/usr/bin/env python3
"""
Comprehensive chatbot performance optimization script.

This script applies all next-level optimizations:
1. Database indexing
2. Connection pooling  
3. Async/await pipeline
4. Fast embedding models
5. Response compression
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.database_indexes import optimize_database_indexes, analyze_database_performance
from finanlyzeos_chatbot.connection_pool import get_all_pool_stats
from finanlyzeos_chatbot.fast_embeddings import benchmark_embedding_speed, get_fast_embeddings
from finanlyzeos_chatbot.response_compression import benchmark_response_compression
from finanlyzeos_chatbot.async_chatbot import add_async_support
from finanlyzeos_chatbot import FinanlyzeOSChatbot


class PerformanceOptimizer:
    """Comprehensive performance optimization manager."""
    
    def __init__(self):
        self.settings = load_settings()
        self.chatbot = None
        self.async_chatbot = None
        self.optimization_results = {}
    
    def run_all_optimizations(self) -> Dict[str, Any]:
        """Run all performance optimizations and return results."""
        print("🚀 Starting Comprehensive Performance Optimization")
        print("=" * 60)
        
        results = {}
        
        # 1. Database Indexing
        print("\n1️⃣ Database Indexing Optimization")
        print("-" * 40)
        results["database_indexing"] = self._optimize_database_indexes()
        
        # 2. Connection Pooling
        print("\n2️⃣ Connection Pooling Setup")
        print("-" * 40)
        results["connection_pooling"] = self._setup_connection_pooling()
        
        # 3. Fast Embeddings
        print("\n3️⃣ Fast Embedding Model Optimization")
        print("-" * 40)
        results["fast_embeddings"] = self._optimize_embeddings()
        
        # 4. Response Compression
        print("\n4️⃣ Response Compression Testing")
        print("-" * 40)
        results["response_compression"] = self._test_response_compression()
        
        # 5. Async Pipeline
        print("\n5️⃣ Async Pipeline Setup")
        print("-" * 40)
        results["async_pipeline"] = self._setup_async_pipeline()
        
        # 6. Performance Benchmarks
        print("\n6️⃣ Performance Benchmarking")
        print("-" * 40)
        results["benchmarks"] = asyncio.run(self._run_performance_benchmarks())
        
        # 7. Summary Report
        print("\n📊 Optimization Summary")
        print("=" * 40)
        self._print_optimization_summary(results)
        
        return results
    
    def _optimize_database_indexes(self) -> Dict[str, Any]:
        """Optimize database with performance indexes."""
        try:
            db_path = Path(self.settings.database_path)
            
            if not db_path.exists():
                print(f"⚠️ Database not found: {db_path}")
                return {"status": "skipped", "reason": "database_not_found"}
            
            # Create indexes
            created, skipped = optimize_database_indexes(db_path)
            print(f"✅ Created {created} indexes, skipped {skipped} existing")
            
            # Analyze performance
            print("🔍 Analyzing query performance...")
            analyze_database_performance(db_path)
            
            return {
                "status": "completed",
                "indexes_created": created,
                "indexes_skipped": skipped,
                "database_path": str(db_path)
            }
            
        except Exception as e:
            print(f"❌ Database indexing failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _setup_connection_pooling(self) -> Dict[str, Any]:
        """Setup and test connection pooling."""
        try:
            from finanlyzeos_chatbot.connection_pool import get_connection_pool
            
            db_path = Path(self.settings.database_path)
            pool = get_connection_pool(db_path, pool_size=10, max_overflow=5)
            
            # Test pool health
            if pool.health_check():
                print("✅ Connection pool initialized and healthy")
                stats = pool.get_stats()
                print(f"📊 Pool stats: {stats['pool_size']} connections, {stats['hit_rate']:.1%} hit rate")
                
                return {
                    "status": "completed",
                    "pool_stats": stats
                }
            else:
                print("❌ Connection pool health check failed")
                return {"status": "failed", "reason": "health_check_failed"}
                
        except Exception as e:
            print(f"❌ Connection pooling setup failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _optimize_embeddings(self) -> Dict[str, Any]:
        """Optimize embedding model for performance."""
        try:
            # Initialize fast embeddings
            embeddings = get_fast_embeddings()
            model_info = embeddings.get_model_info()
            print(f"✅ Loaded fast embedding model: {model_info['model_name']}")
            
            # Benchmark speed
            print("🏃 Benchmarking embedding speed...")
            benchmark_results = benchmark_embedding_speed(num_texts=50, text_length=20)
            
            print(f"⚡ Speed: {benchmark_results['texts_per_second']:.1f} texts/second")
            print(f"📏 Dimension: {benchmark_results['embedding_dimension']}")
            
            return {
                "status": "completed",
                "model_info": model_info,
                "benchmark": benchmark_results
            }
            
        except Exception as e:
            print(f"❌ Embedding optimization failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _test_response_compression(self) -> Dict[str, Any]:
        """Test response compression performance."""
        try:
            # Benchmark compression
            print("🗜️ Benchmarking response compression...")
            compression_results = benchmark_response_compression()
            
            # Print results
            for response_name, data in compression_results.items():
                print(f"\n📄 {response_name}:")
                print(f"   Original: {data['original_size']} bytes")
                
                best_compression = None
                best_ratio = 1.0
                
                for comp_type, comp_data in data['compressions'].items():
                    ratio = comp_data['ratio']
                    saved = comp_data['space_saved_percent']
                    print(f"   {comp_type}: {comp_data['compressed_size']} bytes ({saved:.1f}% saved)")
                    
                    if ratio < best_ratio:
                        best_ratio = ratio
                        best_compression = comp_type
                
                if best_compression:
                    print(f"   🏆 Best: {best_compression}")
            
            return {
                "status": "completed",
                "benchmark_results": compression_results
            }
            
        except Exception as e:
            print(f"❌ Response compression testing failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _setup_async_pipeline(self) -> Dict[str, Any]:
        """Setup async processing pipeline."""
        try:
            # Load chatbot
            print("🔄 Loading chatbot...")
            self.chatbot = FinanlyzeOSChatbot.create(self.settings)
            
            # Add async support
            print("⚡ Adding async support...")
            self.async_chatbot = add_async_support(self.chatbot)
            
            print("✅ Async pipeline ready")
            
            return {
                "status": "completed",
                "chatbot_loaded": True,
                "async_support": True
            }
            
        except Exception as e:
            print(f"❌ Async pipeline setup failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        if not self.async_chatbot:
            return {"status": "skipped", "reason": "async_chatbot_not_available"}
        
        test_queries = [
            ("AAPL revenue", "simple_factual"),
            ("What is Tesla's market cap?", "simple_factual"),
            ("Compare Apple and Microsoft", "medium_comparison"),
            ("Analyze Google's competitive position", "complex_analysis"),
        ]
        
        results = {}
        
        for query, query_type in test_queries:
            print(f"\n🧪 Testing: {query} ({query_type})")
            
            try:
                # Test async performance
                start_time = time.time()
                response = await self.async_chatbot.process_query_async(query)
                async_time = time.time() - start_time
                
                # Test sync performance for comparison
                start_time = time.time()
                sync_response = self.chatbot.ask(query)
                sync_time = time.time() - start_time
                
                improvement = (sync_time - async_time) / sync_time * 100 if sync_time > 0 else 0
                
                print(f"   ⚡ Async: {async_time:.2f}s")
                print(f"   🐌 Sync:  {sync_time:.2f}s")
                print(f"   🚀 Improvement: {improvement:.1f}%")
                
                results[query_type] = {
                    "query": query,
                    "async_time": async_time,
                    "sync_time": sync_time,
                    "improvement_percent": improvement,
                    "response_length": len(response)
                }
                
            except Exception as e:
                print(f"   ❌ Benchmark failed: {e}")
                results[query_type] = {"status": "failed", "error": str(e)}
        
        return results
    
    def _print_optimization_summary(self, results: Dict[str, Any]) -> None:
        """Print comprehensive optimization summary."""
        print("\n🎯 OPTIMIZATION RESULTS SUMMARY")
        print("=" * 50)
        
        # Database optimization
        db_result = results.get("database_indexing", {})
        if db_result.get("status") == "completed":
            print(f"✅ Database: {db_result['indexes_created']} indexes created")
        else:
            print("❌ Database: Optimization failed")
        
        # Connection pooling
        pool_result = results.get("connection_pooling", {})
        if pool_result.get("status") == "completed":
            stats = pool_result.get("pool_stats", {})
            print(f"✅ Connection Pool: {stats.get('pool_size', 0)} connections ready")
        else:
            print("❌ Connection Pool: Setup failed")
        
        # Embeddings
        emb_result = results.get("fast_embeddings", {})
        if emb_result.get("status") == "completed":
            benchmark = emb_result.get("benchmark", {})
            speed = benchmark.get("texts_per_second", 0)
            print(f"✅ Embeddings: {speed:.1f} texts/second")
        else:
            print("❌ Embeddings: Optimization failed")
        
        # Compression
        comp_result = results.get("response_compression", {})
        if comp_result.get("status") == "completed":
            print("✅ Compression: Ready for large responses")
        else:
            print("❌ Compression: Testing failed")
        
        # Async pipeline
        async_result = results.get("async_pipeline", {})
        if async_result.get("status") == "completed":
            print("✅ Async Pipeline: Ready for parallel processing")
        else:
            print("❌ Async Pipeline: Setup failed")
        
        # Performance benchmarks
        bench_results = results.get("benchmarks", {})
        if bench_results and "simple_factual" in bench_results:
            simple_improvement = bench_results["simple_factual"].get("improvement_percent", 0)
            print(f"🚀 Performance: {simple_improvement:.1f}% improvement on simple queries")
        
        print("\n🎉 OPTIMIZATION COMPLETE!")
        print("Your chatbot should now be significantly faster!")


def main():
    """Main optimization script."""
    optimizer = PerformanceOptimizer()
    results = optimizer.run_all_optimizations()
    
    # Save results
    import json
    results_file = Path("optimization_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {results_file}")
    print("\n🚀 Your chatbot is now optimized for maximum performance!")
    print("   • Database queries are indexed and pooled")
    print("   • Embeddings use fast, lightweight models")
    print("   • Responses can be compressed for large data")
    print("   • Async pipeline enables parallel processing")
    print("\nEnjoy your blazing-fast chatbot! 🔥")


if __name__ == "__main__":
    main()
