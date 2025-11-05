"""
Performance Benchmarks (Phase 5.2)

Measures parsing performance for various query types.
Target: <100ms for typical queries, <200ms for complex queries.
"""

import pytest
import time
from src.benchmarkos_chatbot.parsing.parse import parse_to_structured


class TestParsingPerformance:
    """Test parsing performance for various query types"""
    
    def test_simple_query_performance(self):
        """Test simple query parses quickly"""
        query = "Show revenue for Apple"
        
        start = time.time()
        for _ in range(100):  # Run 100 times
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 100
        print(f"\nSimple query avg: {avg_time*1000:.2f}ms")
        
        # Should be very fast (under 50ms on average)
        assert avg_time < 0.050, f"Simple query took {avg_time*1000:.2f}ms (target: <50ms)"
    
    def test_abbreviation_query_performance(self):
        """Test query with abbreviations"""
        query = "Show YoY EPS growth and P/E ratio"
        
        start = time.time()
        for _ in range(100):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 100
        print(f"\nAbbreviation query avg: {avg_time*1000:.2f}ms")
        
        # Should be fast (under 100ms)
        assert avg_time < 0.100, f"Abbreviation query took {avg_time*1000:.2f}ms (target: <100ms)"
    
    def test_group_query_performance(self):
        """Test query with company groups"""
        query = "Compare FAANG vs Big Banks revenue"
        
        start = time.time()
        for _ in range(100):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 100
        print(f"\nGroup query avg: {avg_time*1000:.2f}ms")
        
        # Should be fast (under 100ms)
        assert avg_time < 0.100, f"Group query took {avg_time*1000:.2f}ms (target: <100ms)"
    
    def test_complex_query_performance(self):
        """Test complex multi-feature query"""
        query = "Compare YoY EBITDA for tech companies during pandemic, excluding bearish stocks with P/E > 30"
        
        start = time.time()
        for _ in range(50):  # Fewer iterations for complex queries
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 50
        print(f"\nComplex query avg: {avg_time*1000:.2f}ms")
        
        # Complex queries can be slower but should still be reasonable (under 200ms)
        assert avg_time < 0.200, f"Complex query took {avg_time*1000:.2f}ms (target: <200ms)"
    
    def test_very_complex_query_performance(self):
        """Test very complex query with many features"""
        query = "Show growth stocks with YoY revenue exceeding 20%, P/E under 30, not in tech sector, from S&P 500 leaders, during H1 2023, if sentiment is bullish then analyze"
        
        start = time.time()
        for _ in range(50):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 50
        print(f"\nVery complex query avg: {avg_time*1000:.2f}ms")
        
        # Very complex queries (under 300ms is acceptable)
        assert avg_time < 0.300, f"Very complex query took {avg_time*1000:.2f}ms (target: <300ms)"


class TestPerformanceScalability:
    """Test performance with varying query lengths"""
    
    def test_short_query_performance(self):
        """Test very short queries"""
        query = "Show AAPL"
        
        start = time.time()
        for _ in range(200):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 200
        print(f"\nShort query avg: {avg_time*1000:.2f}ms")
        
        # Very short queries should be fastest
        assert avg_time < 0.030, f"Short query took {avg_time*1000:.2f}ms (target: <30ms)"
    
    def test_medium_query_performance(self):
        """Test medium-length queries"""
        query = "Compare Apple and Microsoft revenue growth over the last 4 quarters"
        
        start = time.time()
        for _ in range(100):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 100
        print(f"\nMedium query avg: {avg_time*1000:.2f}ms")
        
        # Medium queries should be under 100ms
        assert avg_time < 0.100, f"Medium query took {avg_time*1000:.2f}ms (target: <100ms)"
    
    def test_long_query_performance(self):
        """Test long, detailed queries"""
        query = "Show me the year over year revenue growth for FAANG companies during the pandemic period, compared to their performance before the pandemic, and tell me which companies had the highest earnings per share"
        
        start = time.time()
        for _ in range(50):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 50
        print(f"\nLong query avg: {avg_time*1000:.2f}ms")
        
        # Long queries can be slower (under 250ms)
        assert avg_time < 0.250, f"Long query took {avg_time*1000:.2f}ms (target: <250ms)"


class TestFeatureSpecificPerformance:
    """Test performance of specific features"""
    
    def test_spelling_correction_overhead(self):
        """Test spelling correction doesn't add significant overhead"""
        query_correct = "Show revenue for Microsoft"
        query_typo = "Show revenue for Microsft"  # Intentional typo
        
        # Measure correct spelling
        start = time.time()
        for _ in range(100):
            result = parse_to_structured(query_correct)
        time_correct = (time.time() - start) / 100
        
        # Measure with typo (spelling correction)
        start = time.time()
        for _ in range(100):
            result = parse_to_structured(query_typo)
        time_typo = (time.time() - start) / 100
        
        print(f"\nCorrect spelling: {time_correct*1000:.2f}ms")
        print(f"With typo: {time_typo*1000:.2f}ms")
        print(f"Overhead: {(time_typo-time_correct)*1000:.2f}ms")
        
        # Spelling correction overhead should be minimal (under 50ms)
        assert time_typo - time_correct < 0.050, "Spelling correction adds too much overhead"
    
    def test_multi_group_expansion_performance(self):
        """Test multiple group expansions don't slow down parsing"""
        query = "Compare FAANG vs MAG7 vs Big Banks vs Big Pharma"
        
        start = time.time()
        for _ in range(50):
            result = parse_to_structured(query)
        end = time.time()
        
        avg_time = (end - start) / 50
        print(f"\nMulti-group expansion avg: {avg_time*1000:.2f}ms")
        
        # Multiple groups should still be fast (under 150ms)
        assert avg_time < 0.150, f"Multi-group query took {avg_time*1000:.2f}ms (target: <150ms)"


class TestPerformanceRegression:
    """Ensure performance doesn't degrade"""
    
    def test_baseline_performance(self):
        """Establish baseline performance metrics"""
        test_queries = [
            "Show revenue",
            "Compare Apple and Microsoft",
            "What's the P/E ratio for FAANG?",
            "Show YoY growth for tech companies",
            "Analyze Big Banks during pandemic",
        ]
        
        total_time = 0
        for query in test_queries:
            start = time.time()
            for _ in range(20):
                result = parse_to_structured(query)
            total_time += (time.time() - start) / 20
        
        avg_time = total_time / len(test_queries)
        print(f"\nBaseline avg across {len(test_queries)} queries: {avg_time*1000:.2f}ms")
        
        # Average should be under 100ms
        assert avg_time < 0.100, f"Baseline avg {avg_time*1000:.2f}ms exceeds 100ms target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print output

