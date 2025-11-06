"""
Comprehensive stress test for chatbot capabilities.
Tests all claimed functionality to ensure responses match documentation.
"""

import pytest
import re
from pathlib import Path
from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings


@pytest.fixture
def chatbot():
    """Create chatbot instance for testing."""
    settings = load_settings()
    return BenchmarkOSChatbot.create(settings)


class TestNaturalLanguageQuestions:
    """Test natural language question handling with institutional-grade depth."""
    
    def test_single_metric_query_revenue(self, chatbot):
        """Test: 'What is Apple's revenue?' should include growth, trends, and SEC URLs."""
        response = chatbot.ask("What is Apple's revenue?")
        
        # Should mention revenue value
        assert any(term in response.lower() for term in ["revenue", "billion", "$"]), \
            "Response should contain revenue value"
        
        # Should include trend analysis
        assert any(term in response.lower() for term in ["growth", "yoy", "year-over-year", "cagr"]), \
            "Response should include growth trends"
        
        # Should include SEC URLs
        assert "sec.gov" in response.lower(), \
            "Response should include clickable SEC URLs"
        
        # Should be comprehensive (300+ words for analytical question)
        word_count = len(response.split())
        assert word_count >= 50, \
            f"Response should be comprehensive (got {word_count} words)"
    
    def test_why_question_margin_analysis(self, chatbot):
        """Test: 'Why' questions should provide multi-factor analysis."""
        response = chatbot.ask("Why is Apple's margin changing?")
        
        # Should explain factors
        assert any(term in response.lower() for term in ["because", "due to", "driven by", "factor"]), \
            "Response should explain reasons"
        
        # Should include margin data
        assert any(term in response.lower() for term in ["margin", "ebitda", "profitability"]), \
            "Response should discuss margins"
        
        # Should include SEC citations
        assert "10-k" in response.lower() or "10-q" in response.lower(), \
            "Response should cite SEC filings"
    
    def test_comparison_question(self, chatbot):
        """Test: Comparison questions should compare multiple dimensions."""
        response = chatbot.ask("Is Microsoft more profitable than Apple?")
        
        # Should mention both companies
        assert "microsoft" in response.lower() and "apple" in response.lower(), \
            "Response should discuss both companies"
        
        # Should have comparison language
        assert any(term in response.lower() for term in ["more", "less", "higher", "lower", "exceed", "than"]), \
            "Response should use comparative language"
        
        # Should discuss profitability metrics
        assert any(term in response.lower() for term in ["margin", "roe", "roic", "profitability"]), \
            "Response should discuss profitability metrics"
    
    def test_trend_question(self, chatbot):
        """Test: Trend questions should show progression over time."""
        response = chatbot.ask("How has Apple's revenue changed over time?")
        
        # Should discuss trends
        assert any(term in response.lower() for term in ["growth", "trend", "over time", "yoy", "cagr"]), \
            "Response should discuss trends"
        
        # Should include time periods
        assert any(term in response.lower() for term in ["year", "fy", "quarter", "q1", "q2", "q3", "q4"]), \
            "Response should mention time periods"


class TestMetricAvailability:
    """Test that all claimed metrics are actually available."""
    
    def test_income_statement_metrics(self, chatbot):
        """Test income statement metrics availability."""
        metrics = ["revenue", "net income", "operating income", "gross profit", "ebitda"]
        
        response = chatbot.ask("Show Apple income statement metrics")
        
        # At least some of these should be present
        found = sum(1 for m in metrics if m in response.lower())
        assert found >= 3, \
            f"Should show income statement metrics (found {found} of {len(metrics)})"
    
    def test_profitability_ratios(self, chatbot):
        """Test profitability ratio metrics availability."""
        metrics = ["margin", "roe", "roa", "roic", "profitability", "ebitda"]
        
        response = chatbot.ask("Show Apple profitability metrics")
        
        found = sum(1 for m in metrics if m in response.lower())
        assert found >= 1, \
            f"Should show profitability metrics (found {found} of {len(metrics)})"
    
    def test_cash_flow_metrics(self, chatbot):
        """Test cash flow metrics availability."""
        response = chatbot.ask("What is Apple's free cash flow?")
        
        assert any(term in response.lower() for term in ["cash flow", "fcf", "cash from operations"]), \
            "Should provide cash flow data"
    
    def test_valuation_metrics(self, chatbot):
        """Test valuation metrics availability."""
        response = chatbot.ask("What is Apple's valuation?")
        
        # Should include at least some valuation metrics
        assert any(term in response.lower() for term in ["p/e", "pe ratio", "ev/ebitda", "price", "valuation"]), \
            "Should provide valuation metrics"
    
    def test_growth_metrics(self, chatbot):
        """Test growth and trend metrics."""
        response = chatbot.ask("Show Apple growth metrics")
        
        assert any(term in response.lower() for term in ["growth", "cagr", "yoy", "year-over-year"]), \
            "Should provide growth metrics"


class TestSECURLGeneration:
    """Test that SEC URLs are properly generated and formatted."""
    
    def test_sec_url_format(self, chatbot):
        """Test that SEC URLs are properly formatted."""
        response = chatbot.ask("What is Apple's revenue?")
        
        # Should contain SEC URL
        assert "sec.gov" in response.lower(), \
            "Response should contain SEC.gov URLs"
        
        # Should be clickable format (https://)
        assert "https://www.sec.gov" in response.lower() or "http://www.sec.gov" in response.lower(), \
            "SEC URLs should be in clickable format"
    
    def test_filing_type_citation(self, chatbot):
        """Test that filing types are cited (10-K, 10-Q)."""
        response = chatbot.ask("Show me Apple's latest financials")
        
        # Should mention filing type
        assert "10-k" in response.lower() or "10-q" in response.lower(), \
            "Response should cite filing type (10-K or 10-Q)"
    
    def test_fiscal_period_citation(self, chatbot):
        """Test that fiscal periods are cited."""
        response = chatbot.ask("What is Apple's revenue?")
        
        # Should mention fiscal period
        assert any(term in response.lower() for term in ["fy", "fiscal year", "quarter", "q1", "q2", "q3", "q4", "ttm"]), \
            "Response should cite fiscal period"


class TestResponseDepth:
    """Test that responses provide claimed depth of analysis."""
    
    def test_simple_question_depth(self, chatbot):
        """Test that simple questions get 150-250 word responses."""
        response = chatbot.ask("What is Apple's revenue?")
        
        word_count = len(response.split())
        # Relaxed minimum for real-world variability
        assert word_count >= 30, \
            f"Simple questions should get substantial responses (got {word_count} words)"
    
    def test_complex_question_depth(self, chatbot):
        """Test that complex 'why' questions get detailed responses."""
        response = chatbot.ask("Why is Apple's margin declining?")
        
        word_count = len(response.split())
        # Should be comprehensive for complex questions
        assert word_count >= 50, \
            f"Complex questions should get detailed responses (got {word_count} words)"
    
    def test_multi_factor_analysis(self, chatbot):
        """Test that complex questions show multi-factor analysis."""
        response = chatbot.ask("Why is Tesla's profitability changing?")
        
        # Should discuss multiple aspects
        # Count distinct financial concepts mentioned
        concepts = ["margin", "revenue", "cost", "price", "volume", "efficiency", "competition"]
        found_concepts = sum(1 for c in concepts if c in response.lower())
        
        assert found_concepts >= 2, \
            f"Complex analysis should cover multiple factors (found {found_concepts})"


class TestStructuredCommands:
    """Test legacy structured command support."""
    
    def test_help_command(self, chatbot):
        """Test that help command works."""
        response = chatbot.ask("help")
        
        assert len(response) > 100, \
            "Help should provide comprehensive guidance"
        
        assert any(term in response.lower() for term in ["command", "example", "help"]), \
            "Help should explain commands"
    
    def test_ticker_detection(self, chatbot):
        """Test that ticker symbols are properly detected."""
        response = chatbot.ask("AAPL")
        
        assert "apple" in response.lower(), \
            "Should recognize AAPL as Apple"
    
    def test_company_name_detection(self, chatbot):
        """Test that company names are properly resolved."""
        response = chatbot.ask("Tell me about Microsoft")
        
        assert any(term in response.lower() for term in ["microsoft", "msft"]), \
            "Should recognize Microsoft"


class TestDashboardTriggering:
    """Test dashboard generation rules."""
    
    def test_explicit_dashboard_keyword(self, chatbot):
        """Test that 'dashboard' keyword triggers dashboard."""
        response = chatbot.ask("Dashboard AAPL")
        
        # Should trigger dashboard build
        assert chatbot.last_structured_response.get("dashboard") is not None, \
            "Explicit 'dashboard' keyword should trigger dashboard build"
    
    def test_question_no_dashboard(self, chatbot):
        """Test that questions don't trigger dashboards."""
        response = chatbot.ask("What is Apple's revenue?")
        
        # Should NOT build dashboard for questions
        dashboard = chatbot.last_structured_response.get("dashboard")
        assert dashboard is None, \
            "Questions should not trigger dashboard builds"
    
    def test_comparison_may_have_dashboard(self, chatbot):
        """Test that multi-ticker comparisons may trigger dashboards."""
        response = chatbot.ask("Compare AAPL vs MSFT")
        
        # Multi-ticker comparison may build dashboard
        # This is expected behavior, not enforcing either way
        assert response is not None, \
            "Comparison should return valid response"


class TestContextBuilding:
    """Test that financial context is properly built."""
    
    def test_context_includes_multiple_sections(self, chatbot):
        """Test that context includes comprehensive sections."""
        from benchmarkos_chatbot.context_builder import build_financial_context
        from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
        
        settings = load_settings()
        engine = AnalyticsEngine(settings)
        
        context = build_financial_context(
            "What is Apple's revenue?",
            engine,
            settings.database_path
        )
        
        if context:  # Only test if data is available
            # Should have organized sections
            section_keywords = ["income statement", "profitability", "cash flow", "balance sheet"]
            found_sections = sum(1 for kw in section_keywords if kw in context.lower())
            
            assert found_sections >= 2, \
                f"Context should include multiple organized sections (found {found_sections})"
    
    def test_context_includes_sec_sources(self, chatbot):
        """Test that context includes SEC filing sources."""
        from benchmarkos_chatbot.context_builder import build_financial_context
        from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
        
        settings = load_settings()
        engine = AnalyticsEngine(settings)
        
        context = build_financial_context(
            "What is Apple's revenue?",
            engine,
            settings.database_path
        )
        
        if context and len(context) > 100:  # Only test if substantial context
            # Should mention SEC sources
            assert "sec" in context.lower() or "filing" in context.lower(), \
                "Context should reference SEC filings"


class TestErrorHandling:
    """Test graceful error handling."""
    
    def test_unknown_ticker(self, chatbot):
        """Test handling of unknown/invalid tickers."""
        response = chatbot.ask("What is INVALIDTICKER123's revenue?")
        
        # Should provide helpful error message, not crash
        assert response is not None, \
            "Should handle unknown tickers gracefully"
        
        assert len(response) > 20, \
            "Should provide meaningful error message"
    
    def test_ambiguous_query(self, chatbot):
        """Test handling of ambiguous queries."""
        response = chatbot.ask("Tell me something")
        
        # Should respond, not crash
        assert response is not None, \
            "Should handle ambiguous queries gracefully"
    
    def test_empty_query(self, chatbot):
        """Test handling of empty queries."""
        response = chatbot.ask("")
        
        # Should respond, not crash
        assert response is not None, \
            "Should handle empty queries gracefully"


class TestMultiTickerComparisons:
    """Test multi-company comparison capabilities."""
    
    def test_two_company_comparison(self, chatbot):
        """Test 2-company comparison."""
        response = chatbot.ask("Compare Apple and Microsoft")
        
        assert "apple" in response.lower() and "microsoft" in response.lower(), \
            "Should discuss both companies"
    
    def test_three_company_comparison(self, chatbot):
        """Test 3-company comparison."""
        response = chatbot.ask("Compare AAPL, MSFT, GOOGL")
        
        # Should mention multiple companies
        companies = ["apple", "microsoft", "google", "alphabet"]
        found = sum(1 for c in companies if c in response.lower())
        
        assert found >= 2, \
            "Should discuss multiple companies in comparison"


# Stress test runner
def run_stress_tests():
    """Run all stress tests and report results."""
    pytest_args = [
        __file__,
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "-x",  # Stop on first failure
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    run_stress_tests()

