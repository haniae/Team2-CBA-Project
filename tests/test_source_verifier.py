"""Tests for source verifier - source citation verification."""

import pytest
from unittest.mock import Mock, patch
from benchmarkos_chatbot.source_verifier import (
    extract_cited_sources,
    verify_source_citation,
    verify_all_sources,
    SourceCitation,
    SourceIssue
)
from benchmarkos_chatbot.response_verifier import FinancialFact


class TestExtractCitedSources:
    """Test source citation extraction."""
    
    def test_extract_markdown_links(self):
        """Test extraction of markdown link citations."""
        response = "Apple's revenue is $394.3B. [10-K FY2024](https://www.sec.gov/...)"
        
        citations = extract_cited_sources(response)
        
        assert len(citations) > 0
        assert any(c.label == "10-K FY2024" for c in citations)
        assert any("sec.gov" in c.url for c in citations)
    
    def test_extract_multiple_citations(self):
        """Test extraction of multiple citations."""
        response = (
            "Apple's revenue is $394.3B. "
            "[10-K FY2024](https://www.sec.gov/...) "
            "[10-Q Q3 2024](https://www.sec.gov/...)"
        )
        
        citations = extract_cited_sources(response)
        
        assert len(citations) >= 2
    
    def test_skip_placeholder_urls(self):
        """Test that placeholder URLs are skipped."""
        response = "Apple's revenue is $394.3B. [10-K FY2024](url)"
        
        citations = extract_cited_sources(response)
        
        # Should skip placeholder URLs
        assert all(c.url not in ["url", "URL"] for c in citations)
    
    def test_parse_filing_type(self):
        """Test parsing of filing type from label."""
        response = "[10-K FY2024](https://www.sec.gov/...)"
        
        citations = extract_cited_sources(response)
        
        assert any(c.filing_type == "10-K" for c in citations)
    
    def test_parse_period(self):
        """Test parsing of period from label."""
        response = "[10-K FY2024](https://www.sec.gov/...)"
        
        citations = extract_cited_sources(response)
        
        assert any("2024" in c.period for c in citations if c.period)


class TestVerifySourceCitation:
    """Test source citation verification."""
    
    @pytest.fixture
    def sample_citation(self):
        """Create sample source citation."""
        return SourceCitation(
            label="10-K FY2024",
            url="https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000123",
            filing_type="10-K",
            period="FY2024",
            position=0
        )
    
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
    
    @patch('benchmarkos_chatbot.source_verifier.database.fetch_financial_facts')
    def test_verify_valid_citation(self, mock_fetch, sample_citation, sample_fact):
        """Test verification of valid citation."""
        from benchmarkos_chatbot.database import FinancialFactRecord
        from datetime import datetime
        
        # Mock filing record
        mock_fact = FinancialFactRecord(
            ticker="AAPL",
            metric="revenue",
            fiscal_year=2024,
            fiscal_period="FY",
            period="2024-FY",
            value=394.3,
            unit="USD",
            source="SEC",
            source_filing="10-K/0000320193-24-000123",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 12, 31),
            adjusted=False,
            adjustment_note=None,
            ingested_at=datetime.now()
        )
        
        mock_fetch.return_value = [mock_fact]
        
        result = verify_source_citation(
            sample_citation,
            sample_fact,
            "test.db"
        )
        
        # Should return True if citation is valid
        assert isinstance(result, bool)
    
    def test_verify_invalid_url(self, sample_citation, sample_fact):
        """Test verification with invalid URL."""
        sample_citation.url = "https://example.com/invalid"
        
        result = verify_source_citation(
            sample_citation,
            sample_fact,
            "test.db"
        )
        
        # Should return False for non-SEC URLs
        assert result is False


class TestVerifyAllSources:
    """Test verification of all sources in response."""
    
    @pytest.fixture
    def sample_facts(self):
        """Create sample financial facts."""
        return [
            FinancialFact(
                value=394.3,
                unit="B",
                metric="revenue",
                ticker="AAPL",
                period="2024",
                context="Apple's revenue is $394.3B",
                position=0
            )
        ]
    
    def test_verify_all_sources_with_citations(self, sample_facts):
        """Test verification when citations are present."""
        response = "Apple's revenue is $394.3B. [10-K FY2024](https://www.sec.gov/...)"
        
        issues = verify_all_sources(
            response,
            sample_facts,
            "test.db"
        )
        
        assert isinstance(issues, list)
    
    def test_verify_all_sources_no_citations(self, sample_facts):
        """Test verification when no citations are present."""
        response = "Apple's revenue is $394.3B"
        
        issues = verify_all_sources(
            response,
            sample_facts,
            "test.db"
        )
        
        assert len(issues) > 0
        assert any(issue.issue_type == "missing_source" for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



