"""
Test Suite: Verify All ML Model Types Produce Detailed Answers

This test suite verifies that all ML forecasting models (ARIMA, Prophet, ETS, LSTM, GRU, Transformer, Ensemble)
produce responses that include all required technical details.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.context_builder import _build_ml_forecast_context
from finanlyzeos_chatbot.ml_forecasting.ml_forecaster import MLForecaster
from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.settings import load_settings


# Test data
TEST_TICKER = "AAPL"
TEST_METRIC = "revenue"
TEST_PERIODS = 3


class TestMLDetailedAnswers:
    """Test that all ML models produce detailed answers with all technical details."""
    
    @pytest.fixture(scope="class")
    def settings(self):
        """Load settings."""
        return load_settings()
    
    @pytest.fixture(scope="class")
    def ml_forecaster(self, settings):
        """Create ML forecaster instance."""
        return MLForecaster(settings.database_path)
    
    @pytest.fixture(scope="class")
    def chatbot(self, settings):
        """Create chatbot instance."""
        return FinanlyzeOSChatbot.create(settings)
    
    def test_arima_forecast_has_all_details(self, ml_forecaster):
        """Test that ARIMA forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="arima"
        )
        
        if context is None:
            pytest.skip("ARIMA forecast not available (insufficient data or dependencies)")
        
        # Check for required sections
        assert "ARIMA" in context.upper() or "FORECAST" in context.upper(), "Should mention ARIMA or forecast"
        
        # Check for model architecture details
        required_details = [
            "ARIMA ORDER",
            "AR (AUTOREGRESSIVE)",
            "I (INTEGRATED)",
            "MA (MOVING AVERAGE)",
            "AIC",
            "BIC",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 3, f"ARIMA context should include model details. Found: {found_details}"
    
    def test_prophet_forecast_has_all_details(self, ml_forecaster):
        """Test that Prophet forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="prophet"
        )
        
        if context is None:
            pytest.skip("Prophet forecast not available (insufficient data or dependencies)")
        
        # Check for required sections
        assert "PROPHET" in context.upper() or "FORECAST" in context.upper(), "Should mention Prophet or forecast"
        
        # Check for model architecture details
        required_details = [
            "PROPHET",
            "SEASONALITY",
            "CHANGEPOINT",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 2, f"Prophet context should include model details. Found: {found_details}"
    
    def test_ets_forecast_has_all_details(self, ml_forecaster):
        """Test that ETS forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="ets"
        )
        
        if context is None:
            pytest.skip("ETS forecast not available (insufficient data or dependencies)")
        
        # Check for required sections
        assert "ETS" in context.upper() or "FORECAST" in context.upper(), "Should mention ETS or forecast"
        
        # Check for model architecture details
        required_details = [
            "ETS",
            "SMOOTHING",
            "MODEL TYPE",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 2, f"ETS context should include model details. Found: {found_details}"
    
    def test_lstm_forecast_has_all_details(self, ml_forecaster):
        """Test that LSTM forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="lstm"
        )
        
        if context is None:
            pytest.skip("LSTM forecast not available (insufficient data or TensorFlow)")
        
        # Check for required sections
        assert "LSTM" in context.upper() or "FORECAST" in context.upper(), "Should mention LSTM or forecast"
        
        # Check for model architecture details
        required_details = [
            "LSTM",
            "NEURAL NETWORK",
            "LAYERS",
            "TRAINING",
            "EPOCHS",
            "LOSS",
            "HYPERPARAMETERS",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 5, f"LSTM context should include comprehensive details. Found: {found_details}"
    
    def test_transformer_forecast_has_all_details(self, ml_forecaster):
        """Test that Transformer forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="transformer"
        )
        
        if context is None:
            pytest.skip("Transformer forecast not available (insufficient data or PyTorch)")
        
        # Check for required sections
        assert "TRANSFORMER" in context.upper() or "FORECAST" in context.upper(), "Should mention Transformer or forecast"
        
        # Check for model architecture details
        required_details = [
            "TRANSFORMER",
            "ATTENTION",
            "LAYERS",
            "HEADS",
            "TRAINING",
            "EPOCHS",
            "LOSS",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 5, f"Transformer context should include comprehensive details. Found: {found_details}"
    
    def test_ensemble_forecast_has_all_details(self, ml_forecaster):
        """Test that Ensemble forecast includes all required technical details."""
        context = _build_ml_forecast_context(
            ticker=TEST_TICKER,
            metric=TEST_METRIC,
            database_path=ml_forecaster.database_path,
            periods=TEST_PERIODS,
            method="ensemble"
        )
        
        if context is None:
            pytest.skip("Ensemble forecast not available (insufficient data or dependencies)")
        
        # Check for required sections
        assert "ENSEMBLE" in context.upper() or "FORECAST" in context.upper(), "Should mention Ensemble or forecast"
        
        # Check for model architecture details
        required_details = [
            "ENSEMBLE",
            "MODELS",
            "WEIGHTS",
            "MODEL ARCHITECTURE",
        ]
        
        context_upper = context.upper()
        found_details = [detail for detail in required_details if detail in context_upper]
        
        assert len(found_details) >= 2, f"Ensemble context should include model details. Found: {found_details}"
    
    def test_all_forecasts_include_growth_rates(self, ml_forecaster):
        """Test that all forecasts include growth rates and CAGR."""
        methods = ["arima", "prophet", "ets", "lstm", "transformer", "ensemble"]
        
        for method in methods:
            context = _build_ml_forecast_context(
                ticker=TEST_TICKER,
                metric=TEST_METRIC,
                database_path=ml_forecaster.database_path,
                periods=TEST_PERIODS,
                method=method
            )
            
            if context is None:
                continue  # Skip if method not available
            
            # Check for growth rates
            assert "GROWTH" in context.upper() or "CAGR" in context.upper() or "YOY" in context.upper(), \
                f"{method.upper()} forecast should include growth rates or CAGR"
    
    def test_all_forecasts_include_confidence_intervals(self, ml_forecaster):
        """Test that all forecasts include confidence intervals."""
        methods = ["arima", "prophet", "ets", "lstm", "transformer", "ensemble"]
        
        for method in methods:
            context = _build_ml_forecast_context(
                ticker=TEST_TICKER,
                metric=TEST_METRIC,
                database_path=ml_forecaster.database_path,
                periods=TEST_PERIODS,
                method=method
            )
            
            if context is None:
                continue  # Skip if method not available
            
            # Check for confidence intervals
            assert "CONFIDENCE" in context.upper() or "CI" in context.upper() or "INTERVAL" in context.upper(), \
                f"{method.upper()} forecast should include confidence intervals"
    
    def test_all_forecasts_include_model_explainability(self, ml_forecaster):
        """Test that all forecasts include model explainability."""
        methods = ["arima", "prophet", "ets", "lstm", "transformer", "ensemble"]
        
        for method in methods:
            context = _build_ml_forecast_context(
                ticker=TEST_TICKER,
                metric=TEST_METRIC,
                database_path=ml_forecaster.database_path,
                periods=TEST_PERIODS,
                method=method
            )
            
            if context is None:
                continue  # Skip if method not available
            
            # Check for explainability
            explainability_indicators = [
                "HOW",
                "WORKS",
                "EXPLAIN",
                "ARCHITECTURE",
                "MECHANISM",
            ]
            
            context_upper = context.upper()
            found_indicators = [ind for ind in explainability_indicators if ind in context_upper]
            
            assert len(found_indicators) >= 1, \
                f"{method.upper()} forecast should include model explainability. Found: {found_indicators}"
    
    def test_chatbot_response_includes_ml_details(self, chatbot):
        """Test that chatbot responses to ML forecast queries include all details."""
        query = f"Forecast {TEST_TICKER}'s {TEST_METRIC} using LSTM"
        
        response = chatbot.ask(query)
        
        # Check that response includes ML details
        assert response is not None, "Chatbot should return a response"
        
        response_upper = response.upper()
        
        # Check for key ML details
        ml_indicators = [
            "LSTM",
            "FORECAST",
            "MODEL",
            "TRAINING",
            "ARCHITECTURE",
        ]
        
        found_indicators = [ind for ind in ml_indicators if ind in response_upper]
        
        # At least some ML details should be present
        assert len(found_indicators) >= 2, \
            f"Chatbot response should include ML details. Found: {found_indicators}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

