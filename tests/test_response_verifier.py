"""Tests for response verifier - fact extraction and verification."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from benchmarkos_chatbot.response_verifier import (
    extract_financial_numbers,
    verify_fact,
    verify_response,
    FinancialFact,
    VerificationResult,
    VerifiedResponse
)
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.config import Settings


class TestExtractFinancialNumbers:
    """Test financial number extraction from responses."""
    
    def test_extract_currency_billions(self):
        """Test extraction of currency values in billions."""
        response = "Apple's revenue is $394.3B in FY2024"
        facts = extract_financial_numbers(response)
        
        assert len(facts) > 0
        assert any(f.value == 394.3 and f.unit == "B" for f in facts)
    
    def test_extract_currency_millions(self):
        """Test extraction of currency values in millions."""
        response = "Microsoft's cash flow is $85.2M"
        facts = extract_financial_numbers(response)
        
        assert len(facts) > 0
        assert any(f.unit == "B" for f in facts)  # Should be normalized to billions
    
    def test_extract_percentages(self):
        """Test extraction of percentage values."""
        response = "Tesla's profit margin is 25.3%"
        facts = extract_financial_numbers(response)
        
        assert len(facts) > 0
        assert any(f.unit == "%" and f.value == 25.3 for f in facts)
    
    def test_extract_multiples(self):
        """Test extraction of ratio/multiple values."""
        response = "Apple's P/E ratio is 39.8x"
        facts = extract_financial_numbers(response)
        
        assert len(facts) > 0
        assert any(f.unit == "x" and f.value == 39.8 for f in facts)
    
    def test_extract_multiple_numbers(self):
        """Test extraction of multiple numbers in one response."""
        response = "Apple's revenue is $394.3B with a margin of 25.3% and P/E of 39.8x"
        facts = extract_financial_numbers(response)
        
        assert len(facts) >= 3
    
    def test_identify_metric_from_context(self):
        """Test metric identification from context."""
        response = "Apple's revenue reached $394.3B in FY2024"
        facts = extract_financial_numbers(response)
        
        assert any(f.metric == "revenue" for f in facts)
    
    def test_identify_ticker_from_context(self):
        """Test ticker identification from context."""
        response = "AAPL revenue is $394.3B"
        facts = extract_financial_numbers(response)
        
        assert any(f.ticker == "AAPL" for f in facts)
    
    def test_identify_period_from_context(self):
        """Test period identification from context."""
        response = "Apple's revenue in FY2024 is $394.3B"
        facts = extract_financial_numbers(response)
        
        assert any("2024" in f.period for f in facts if f.period)


class TestVerifyFact:
    """Test fact verification against database."""
    
    @pytest.fixture
    def mock_analytics_engine(self):
        """Create mock analytics engine."""
        engine = Mock(spec=AnalyticsEngine)
        return engine
    
    @pytest.fixture
    def sample_fact(self):
        """Create sample financial fact."""
        return FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $394.3B",
            position=0
        )
    
    def test_verify_correct_fact(self, mock_analytics_engine, sample_fact):
        """Test verification of correct fact."""
        # Mock metric record
        from benchmarkos_chatbot.database import MetricRecord
        from datetime import datetime
        
        mock_record = MetricRecord(
            ticker="AAPL",
            metric="revenue",
            period="2024-FY",
            value=394.3,
            source="SEC",
            updated_at=datetime.now(),
            start_year=2024,
            end_year=2024
        )
        
        mock_analytics_engine.get_metrics.return_value = [mock_record]
        
        result = verify_fact(
            sample_fact,
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.is_correct is True
        assert result.actual_value == 394.3
        assert result.deviation < 5.0  # Within 5% tolerance
    
    def test_verify_incorrect_fact(self, mock_analytics_engine, sample_fact):
        """Test verification of incorrect fact."""
        from benchmarkos_chatbot.database import MetricRecord
        from datetime import datetime
        
        # Actual value is different
        mock_record = MetricRecord(
            ticker="AAPL",
            metric="revenue",
            period="2024-FY",
            value=400.0,  # Different from fact value
            source="SEC",
            updated_at=datetime.now(),
            start_year=2024,
            end_year=2024
        )
        
        mock_analytics_engine.get_metrics.return_value = [mock_record]
        
        result = verify_fact(
            sample_fact,
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.is_correct is False
        assert result.actual_value == 400.0
        assert result.deviation > 0
    
    def test_verify_missing_metric(self, mock_analytics_engine, sample_fact):
        """Test verification when metric is missing."""
        mock_analytics_engine.get_metrics.return_value = []
        
        result = verify_fact(
            sample_fact,
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.is_correct is False
        assert result.actual_value is None
        assert "not found" in result.message.lower()
    
    def test_verify_missing_ticker(self, mock_analytics_engine):
        """Test verification when ticker is missing."""
        fact = FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker=None,  # Missing ticker
            period="2024",
            context="Revenue is $394.3B",
            position=0
        )
        
        result = verify_fact(
            fact,
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.is_correct is False
        assert "missing" in result.message.lower()


class TestVerifyResponse:
    """Test full response verification."""
    
    @pytest.fixture
    def mock_analytics_engine(self):
        """Create mock analytics engine."""
        engine = Mock(spec=AnalyticsEngine)
        return engine
    
    def test_verify_response_with_facts(self, mock_analytics_engine):
        """Test verification of response with multiple facts."""
        response = "Apple's revenue is $394.3B with a margin of 25.3%"
        context = "Context with financial data"
        user_input = "What is Apple's revenue?"
        
        # Mock metrics
        from benchmarkos_chatbot.database import MetricRecord
        from datetime import datetime
        
        mock_records = [
            MetricRecord(
                ticker="AAPL",
                metric="revenue",
                period="2024-FY",
                value=394.3,
                source="SEC",
                updated_at=datetime.now(),
                start_year=2024,
                end_year=2024
            ),
            MetricRecord(
                ticker="AAPL",
                metric="gross_margin",
                period="2024-FY",
                value=25.3,
                source="SEC",
                updated_at=datetime.now(),
                start_year=2024,
                end_year=2024
            )
        ]
        
        mock_analytics_engine.get_metrics.return_value = mock_records
        
        result = verify_response(
            response,
            context,
            user_input,
            mock_analytics_engine,
            "test.db"
        )
        
        assert isinstance(result, VerifiedResponse)
        assert result.total_facts > 0
        assert result.correct_facts >= 0
    
    def test_verify_response_no_facts(self, mock_analytics_engine):
        """Test verification of response with no financial facts."""
        response = "This is a general response with no numbers"
        context = "Context"
        user_input = "Hello"
        
        result = verify_response(
            response,
            context,
            user_input,
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.total_facts == 0
        assert result.has_errors is False
        assert result.confidence_score == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

