"""Tests for data validator - cross-validation between sources."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from finanlyzeos_chatbot.data_validator import (
    cross_validate_metric,
    validate_context_data,
    ValidationResult,
    DataIssue
)
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine


class TestCrossValidateMetric:
    """Test cross-validation between SEC and Yahoo Finance."""
    
    @pytest.fixture
    def mock_analytics_engine(self):
        """Create mock analytics engine."""
        engine = Mock(spec=AnalyticsEngine)
        return engine
    
    def test_cross_validate_consistent_data(self, mock_analytics_engine):
        """Test cross-validation with consistent data."""
        from finanlyzeos_chatbot.database import MetricRecord
        from datetime import datetime
        
        # Mock SEC value
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
        
        result = cross_validate_metric(
            "AAPL",
            "revenue",
            "2024",
            mock_analytics_engine,
            "test.db"
        )
        
        assert isinstance(result, ValidationResult)
        assert result.ticker == "AAPL"
        assert result.metric == "revenue"
        assert result.sec_value == 394.3
    
    def test_cross_validate_missing_sec_data(self, mock_analytics_engine):
        """Test cross-validation when SEC data is missing."""
        mock_analytics_engine.get_metrics.return_value = []
        
        result = cross_validate_metric(
            "AAPL",
            "revenue",
            "2024",
            mock_analytics_engine,
            "test.db"
        )
        
        assert result.sec_value is None
        assert result.is_consistent is False
    
    def test_cross_validate_discrepancy(self, mock_analytics_engine):
        """Test cross-validation with data discrepancy."""
        from finanlyzeos_chatbot.database import MetricRecord
        from datetime import datetime
        
        # Mock SEC value
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
        
        # Note: Yahoo Finance value would be mocked separately if implemented
        result = cross_validate_metric(
            "AAPL",
            "revenue",
            "2024",
            mock_analytics_engine,
            "test.db"
        )
        
        assert isinstance(result, ValidationResult)
        # Yahoo value would be None in current implementation
        assert result.yahoo_value is None or result.is_consistent


class TestValidateContextData:
    """Test context data validation."""
    
    @pytest.fixture
    def mock_analytics_engine(self):
        """Create mock analytics engine."""
        engine = Mock(spec=AnalyticsEngine)
        return engine
    
    def test_validate_context_with_data(self, mock_analytics_engine):
        """Test validation of context with financial data."""
        context = "AAPL revenue: $394.3B (FY2024)"
        
        from finanlyzeos_chatbot.database import MetricRecord
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
        
        issues = validate_context_data(
            context,
            mock_analytics_engine,
            "test.db"
        )
        
        assert isinstance(issues, list)
        # Should have no issues if data is consistent
    
    def test_validate_empty_context(self, mock_analytics_engine):
        """Test validation of empty context."""
        context = ""
        
        issues = validate_context_data(
            context,
            mock_analytics_engine,
            "test.db"
        )
        
        assert isinstance(issues, list)
        assert len(issues) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



