"""Smart financial context builder for LLM-powered responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime
import os

from .parsing.parse import parse_to_structured
from . import database

if TYPE_CHECKING:
    from .analytics_engine import AnalyticsEngine

LOGGER = logging.getLogger(__name__)

# Try to import multi-source aggregator
try:
    from .multi_source_aggregator import get_multi_source_context
    MULTI_SOURCE_AVAILABLE = True
except ImportError:
    MULTI_SOURCE_AVAILABLE = False
    LOGGER.warning("Multi-source aggregator not available - only SEC data will be used")

# Try to import macro data provider
try:
    from .macro_data import get_macro_provider
    MACRO_DATA_AVAILABLE = True
except ImportError:
    MACRO_DATA_AVAILABLE = False
    LOGGER.warning("Macro data provider not available - economic context will not be included")

# Try to import ML forecasting
try:
    from .ml_forecasting import get_ml_forecaster
    ML_FORECASTING_AVAILABLE = True
except ImportError:
    ML_FORECASTING_AVAILABLE = False
    LOGGER.debug("ML forecasting not available - forecasting will use basic methods")

# Module-level storage for the latest forecast metadata (for interactive forecasting)
# This allows the chatbot to retrieve forecast details after context building
_LAST_FORECAST_METADATA: Optional[Dict[str, Any]] = None


def get_last_forecast_metadata() -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for the most recently generated forecast.
    
    Returns:
        Dictionary containing ticker, metric, method, forecast_result, explainability, parameters
    """
    global _LAST_FORECAST_METADATA
    return _LAST_FORECAST_METADATA


def _set_last_forecast_metadata(
    ticker: str,
    metric: str,
    method: str,
    periods: int,
    forecast_result: Any,
    explainability: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> None:
    """Store metadata for the latest forecast (internal use only)."""
    global _LAST_FORECAST_METADATA
    _LAST_FORECAST_METADATA = {
        "ticker": ticker,
        "metric": metric,
        "method": method,
        "periods": periods,
        "forecast_result": forecast_result,
        "explainability": explainability or {},
        "parameters": parameters or {},
    }
    LOGGER.debug(f"Stored forecast metadata for {ticker} {metric} using {method}")


def format_currency(value: Optional[float]) -> str:
    """Format currency value to human-readable string."""
    if value is None:
        return "N/A"
    
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"


def format_percent(value: Optional[float]) -> str:
    """Format percentage value with validation."""
    if value is None:
        return "N/A"
    
    # CRITICAL: Detect if value is absurdly large (likely a formatting bug)
    if abs(value) > 1000:
        LOGGER.error(f"❌ FORMATTING BUG: Value {value:,.0f} is too large for a percentage!")
        LOGGER.error(f"   This suggests an absolute value (like revenue $) is being treated as %")
        # Return error indicator instead of nonsensical percentage
        return f"[ERROR: {value:,.0f}]"
    
    return f"{value:.1f}%"


def format_multiple(value: Optional[float]) -> str:
    """Format multiple/ratio value."""
    if value is None:
        return "N/A"
    return f"{value:.1f}×"


def _format_period_label(record: database.MetricRecord) -> str:
    """Extract human-readable period label from metric record."""
    if not record.period:
        return "latest available"
    
    # Parse period string (e.g., "2023-Q3", "2023-FY")
    period_str = record.period
    if "-FY" in period_str:
        return f"FY{period_str.split('-')[0]}"
    elif "-Q" in period_str:
        parts = period_str.split("-")
        return f"{parts[1]} FY{parts[0]}"
    
    return period_str


def _build_sec_url(accession: str, cik: str) -> str:
    """Build clickable SEC EDGAR URL from accession number and CIK."""
    if not accession or not cik:
        return ""
    
    clean_cik = cik.lstrip("0") or cik
    acc_no_dash = accession.replace("-", "")
    
    # Interactive viewer URL (preferred for viewing the filing)
    return f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={clean_cik}&accession_number={accession}&xbrl_type=v"


def _get_filing_sources(
    ticker: str,
    database_path: str,
    fiscal_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetch filing metadata with SEC URLs for source citations."""
    try:
        facts = database.fetch_financial_facts(
            database_path,
            ticker=ticker,
            fiscal_year=fiscal_year,
            limit=100
        )
        
        # Extract unique filing sources with metadata
        filings_map: Dict[str, Dict[str, Any]] = {}
        for fact in facts:
            if fact.source_filing and fact.source_filing not in filings_map:
                # Parse source_filing format (typically "10-K/0001234567-23-000123" or just form type)
                parts = fact.source_filing.split("/")
                form_type = parts[0] if parts else "SEC filing"
                accession = parts[1] if len(parts) > 1 else None
                
                # Build SEC URL if we have accession and CIK
                sec_url = ""
                if accession and fact.cik:
                    sec_url = _build_sec_url(accession, fact.cik)
                
                filings_map[fact.source_filing] = {
                    "form_type": form_type,
                    "fiscal_year": fact.fiscal_year,
                    "fiscal_period": fact.fiscal_period,
                    "period_end": fact.period_end,
                    "accession": accession,
                    "sec_url": sec_url,
                }
        
        return list(filings_map.values())
    except Exception as e:
        LOGGER.debug(f"Could not fetch filing sources for {ticker}: {e}")
        return []


def _get_model_explanation(method: str) -> str:
    """
    Generate educational explanation of the ML forecasting model used.
    
    Args:
        method: Forecasting method name (arima, prophet, ets, lstm, gru, transformer, ensemble)
        
    Returns:
        Formatted explanation string with model details and references
    """
    method_lower = method.lower()
    
    explanations = {
        "arima": """
**📚 About ARIMA Models:**

ARIMA (AutoRegressive Integrated Moving Average) is a statistical time series forecasting model that combines:
- **AR (AutoRegressive)**: Uses past values to predict future values
- **I (Integrated)**: Applies differencing to make the series stationary (removes trends)
- **MA (Moving Average)**: Uses past forecast errors to improve predictions

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Historical revenue data is collected (e.g., 2015-2024 annual revenue)
   - The series is tested for stationarity (constant mean and variance)
   - If non-stationary, differencing is applied (e.g., subtracting previous year's value)

2. **Parameter Selection (Auto-ARIMA):**
   - The model automatically searches for optimal (p, d, q) parameters:
     - **p (AR order)**: How many past values to use (e.g., p=2 means use last 2 years)
     - **d (Differencing order)**: How many times to difference the data to make it stationary
     - **q (MA order)**: How many past forecast errors to consider
   - For seasonal data, seasonal parameters (P, D, Q, s) are also selected
   - Selection is based on AIC/BIC criteria (lower is better)

3. **Model Training:**
   - The model fits coefficients to historical data using maximum likelihood estimation
   - It learns patterns like: "Revenue tends to be 1.08 × previous year's revenue"
   - Captures autocorrelation: "Revenue in year t correlates with year t-1 and t-2"

4. **Forecast Generation:**
   - For each future period (e.g., 2025, 2026, 2027):
     - Uses the ARIMA equation: Y(t) = c + φ₁Y(t-1) + φ₂Y(t-2) + ... + θ₁ε(t-1) + θ₂ε(t-2) + ε(t)
     - Where Y(t) = forecast, φ = AR coefficients, θ = MA coefficients, ε = errors
     - Recursively generates forecasts: forecast for 2025 uses actual 2024, forecast for 2026 uses forecasted 2025
   - Example: If last year's revenue was $100B and model learned a 1.08 growth factor:
     - 2025 forecast = $100B × 1.08 = $108B
     - 2026 forecast = $108B × 1.08 = $116.64B

5. **Confidence Intervals:**
   - Calculated from residual standard deviation (how much past forecasts deviated from actuals)
   - 95% confidence interval = forecast ± 1.96 × standard error
   - Accounts for uncertainty: wider intervals for longer horizons

**Best for:**
- Financial time series with clear trends and seasonality
- Data with sufficient history (10+ periods recommended)
- Short to medium-term forecasts (1-3 years)

**Sources:**
- [Statsmodels ARIMA Documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html)
- [Time Series Forecasting: Principles and Practice](https://otexts.com/fpp3/arima.html)
- Box, G. E. P., & Jenkins, G. M. (1976). Time Series Analysis: Forecasting and Control
        """,
        
        "prophet": """
**📚 About Prophet Models:**

Prophet is Facebook's open-source forecasting tool designed for business time series with strong seasonal patterns.

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Historical data is formatted as (date, value) pairs (e.g., annual revenue from 2015-2024)
   - Prophet automatically handles missing dates and outliers
   - Data is normalized if needed

2. **Model Decomposition:**
   - Prophet decomposes the time series into three components:
     - **Trend g(t)**: Long-term growth/decline pattern
       - Uses piecewise linear or logistic growth models
       - Detects changepoints where trend changes (e.g., acceleration in 2020)
     - **Seasonality s(t)**: Recurring patterns
       - Uses Fourier series to model yearly seasonality
       - Captures patterns like "Q4 is typically 15% higher than Q1"
     - **Holidays h(t)**: Special events and anomalies
       - Models known events (earnings announcements, market events)

3. **Model Training:**
   - Fits the additive model: y(t) = g(t) + s(t) + h(t) + ε(t)
   - Or multiplicative model: y(t) = g(t) × (1 + s(t)) × (1 + h(t)) × ε(t)
   - Uses Bayesian methods to estimate parameters
   - Learns changepoint locations and seasonal amplitudes from historical data

4. **Forecast Generation:**
   - For each future date (e.g., 2025-12-31, 2026-12-31):
     - **Trend component**: Extrapolates the learned trend (e.g., "Revenue grows at 8% per year")
     - **Seasonal component**: Applies the learned seasonal pattern (e.g., "Year-end is typically 1.15× average")
     - **Holiday component**: Adds/subtracts effects for known future events
     - Combines components: Forecast = Trend + Seasonality + Holidays
   - Example calculation:
     - Base trend for 2025: $100B × 1.08 = $108B
     - Seasonal adjustment: $108B × 1.15 = $124.2B (if Q4)
     - Final 2025 forecast: $124.2B

5. **Confidence Intervals:**
   - Uses posterior predictive distribution from Bayesian inference
   - Accounts for uncertainty in trend, seasonality, and residuals
   - Wider intervals for longer horizons and when historical data is noisy

**Best for:**
- Financial metrics with strong seasonal patterns (quarterly earnings, annual revenue)
- Data with holiday effects or irregular events
- Robust forecasting when data has missing values or outliers

**Sources:**
- [Prophet Documentation](https://facebook.github.io/prophet/)
- Taylor, S. J., & Letham, B. (2018). Forecasting at scale. The American Statistician
- [Prophet Research Paper](https://peerj.com/preprints/3190/)
        """,
        
        "ets": """
**📚 About ETS Models:**

ETS (Error, Trend, Seasonality) is a state-space framework for exponential smoothing methods.

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Historical data is prepared (e.g., annual revenue from 2015-2024)
   - The model automatically tests for trend and seasonality
   - Selects optimal component structure (Error, Trend, Seasonality combinations)

2. **Model Component Selection:**
   - The model automatically selects from 30 possible ETS combinations:
     - **Error**: None, Additive (A), Multiplicative (M)
     - **Trend**: None (N), Additive (A), Multiplicative (M), Damped Additive (Ad), Damped Multiplicative (Md)
     - **Seasonality**: None (N), Additive (A), Multiplicative (M)
   - Example: ETS(A,Ad,N) = Additive errors, Damped additive trend, No seasonality
   - Selection based on AIC/BIC criteria (lower is better)

3. **Model Training (Exponential Smoothing):**
   - Uses exponential smoothing: gives more weight to recent observations
   - Smoothing equations:
     - **Level (L)**: L(t) = α × Y(t) + (1-α) × L(t-1)
     - **Trend (T)**: T(t) = β × (L(t) - L(t-1)) + (1-β) × T(t-1)
     - **Seasonal (S)**: S(t) = γ × (Y(t) - L(t)) + (1-γ) × S(t-m)
   - Where α, β, γ are smoothing parameters (0-1, learned from data)
   - Example: If α=0.3, level = 30% of current value + 70% of previous level
   - Damped trend: T(t) = β × (L(t) - L(t-1)) + φ × T(t-1), where φ < 1 (trend decays over time)

4. **Forecast Generation:**
   - For each future period (e.g., 2025, 2026, 2027):
     - **Level**: L(t+h) = L(t) (current level)
     - **Trend**: T(t+h) = φ^h × T(t) (damped trend, if applicable)
     - **Seasonal**: S(t+h) = S(t+h-m) (seasonal pattern, if applicable)
     - Forecast = Level + Trend + Seasonal (additive) or Level × Trend × Seasonal (multiplicative)
   - Example calculation (ETS(A,Ad,N) - Additive errors, Damped additive trend):
     - Current level: L(2024) = $100B
     - Current trend: T(2024) = $5B/year
     - Damping factor: φ = 0.9
     - 2025 forecast: L(2024) + φ^1 × T(2024) = $100B + 0.9 × $5B = $104.5B
     - 2026 forecast: L(2024) + φ^2 × T(2024) = $100B + 0.81 × $5B = $104.05B
     - Trend dampens over time (forecast growth slows)

5. **Confidence Intervals:**
   - Calculated from forecast errors (difference between forecast and actual)
   - Accounts for model uncertainty and residual variance
   - Formula: CI = forecast ± 1.96 × sqrt(variance_of_forecast_errors)

**Best for:**
- Smoothing noisy financial data
- Short-term forecasts with trend and seasonality
- When you need simple, interpretable models

**Sources:**
- [Rob Hyndman's Forecasting Textbook](https://otexts.com/fpp3/)
- Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: principles and practice
- [ETS Model Selection](https://otexts.com/fpp3/expsmooth.html)
        """,
        
        "lstm": """
**📚 About LSTM Models:**

LSTM (Long Short-Term Memory) is a type of recurrent neural network (RNN) designed to capture long-term dependencies in sequential data.

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Historical data is converted into sequences (e.g., use last 10 years to predict next year)
   - Data is normalized (scaled to 0-1 range) for neural network training
   - Creates input sequences: [2015, 2016, ..., 2024] → predict [2025]
   - Creates training examples by sliding window: [2014-2023] → [2024], [2013-2022] → [2023], etc.

2. **Model Architecture:**
   - LSTM uses "memory cells" with three gates:
     - **Forget gate**: Decides which information to discard from memory
     - **Input gate**: Decides which new information to store
     - **Output gate**: Decides which information to output
   - Each gate uses sigmoid/tanh functions to learn weights
   - Multiple LSTM layers can be stacked for complex patterns

3. **Model Training:**
   - Neural network learns weights through backpropagation
   - Training process:
     - Feed sequence [2015-2024] to network
     - Network predicts 2025 value
     - Compare prediction to actual 2025 value
     - Calculate error (e.g., mean squared error)
     - Adjust weights to reduce error
     - Repeat for all training sequences (epochs)
   - Learns patterns like: "If revenue grew 10% for 3 consecutive years, expect 8% growth next year"
   - Captures non-linear relationships: "Revenue acceleration in years 2-3 predicts higher growth in year 4"

4. **Forecast Generation:**
   - For each future period:
     - Feed last N years of data (e.g., [2015-2024]) to trained network
     - Network processes through LSTM layers:
       - Each layer applies learned transformations
       - Memory cells store relevant historical information
       - Gates filter and combine information
     - Output layer produces forecast value
     - Value is inverse-transformed back to original scale
   - Example: If normalized sequence [0.5, 0.55, 0.6, 0.65, 0.7] represents $50B-$70B:
     - Network processes sequence and outputs normalized value 0.75
     - Inverse transform: 0.75 × ($70B - $50B) + $50B = $65B forecast for 2025

5. **Confidence Intervals:**
   - Calculated from validation set prediction errors
   - Accounts for model uncertainty and historical prediction variance
   - Formula: CI = forecast ± 1.96 × std_deviation_of_validation_errors

**Best for:**
- Complex, non-linear patterns in financial data
- Capturing long-term dependencies and trends
- When traditional statistical methods fail to capture complex relationships

**Sources:**
- Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural computation
- [Understanding LSTM Networks](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)
- [TensorFlow LSTM Guide](https://www.tensorflow.org/guide/keras/rnn)
        """,
        
        "gru": """
**📚 About GRU Models:**

GRU (Gated Recurrent Unit) is a simplified variant of LSTM with fewer parameters but similar capabilities.

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Similar to LSTM: Historical data is converted into sequences (e.g., last 10 years to predict next year)
   - Data is normalized (scaled to 0-1 range) for neural network training
   - Creates input sequences: [2015, 2016, ..., 2024] → predict [2025]
   - Creates training examples by sliding window

2. **Model Architecture (Simplified vs LSTM):**
   - GRU uses **two gates** (vs LSTM's three):
     - **Reset gate (r)**: Controls how much past information to forget
       - Formula: r(t) = σ(W_r × [h(t-1), x(t)])
     - **Update gate (z)**: Controls how much new information to incorporate
       - Formula: z(t) = σ(W_z × [h(t-1), x(t)])
   - **Hidden state**: h(t) = (1-z(t)) × h(t-1) + z(t) × h̃(t)
     - Where h̃(t) = tanh(W × [r(t) × h(t-1), x(t)])
   - More efficient than LSTM (fewer parameters, faster training)

3. **Model Training:**
   - Similar to LSTM: Neural network learns weights through backpropagation
   - Training process:
     - Feed sequence [2015-2024] to network
     - GRU processes through gates (reset and update)
     - Network predicts 2025 value
     - Compare prediction to actual 2025 value
     - Calculate error and adjust weights
     - Repeat for all training sequences (epochs)
   - Learns patterns: "If revenue grew 10% for 3 consecutive years, expect 8% growth next year"
   - Typically trains faster than LSTM with comparable accuracy

4. **Forecast Generation:**
   - For each future period:
     - Feed last N years of data (e.g., [2015-2024]) to trained GRU network
     - Network processes through GRU cells:
       - Reset gate filters relevant past information
       - Update gate combines past and new information
       - Hidden state captures sequential patterns
     - Output layer produces forecast value
     - Value is inverse-transformed back to original scale
   - Example: Similar to LSTM, if normalized sequence [0.5, 0.55, 0.6, 0.65, 0.7]:
     - GRU processes sequence (faster than LSTM)
     - Outputs normalized value 0.75
     - Inverse transform: 0.75 × ($70B - $50B) + $50B = $65B forecast for 2025

5. **Confidence Intervals:**
   - Calculated from validation set prediction errors
   - Accounts for model uncertainty and historical prediction variance
   - Formula: CI = forecast ± 1.96 × std_deviation_of_validation_errors

**Advantages over LSTM:**
- Faster training (fewer parameters to learn)
- Lower memory usage
- Often achieves similar accuracy with less computation
- Better for real-time or frequent forecasting

**Best for:**
- Similar use cases to LSTM but with faster training
- When computational resources are limited
- Real-time or frequent forecasting needs

**Sources:**
- Cho, K., et al. (2014). Learning phrase representations using RNN encoder-decoder. arXiv preprint
- [GRU vs LSTM Comparison](https://towardsdatascience.com/illustrated-guide-to-lstms-and-gru-s-a-step-by-step-explanation-44e9eb85bf21)
- [PyTorch GRU Documentation](https://pytorch.org/docs/stable/generated/torch.nn.GRU.html)
        """,
        
        "transformer": """
**📚 About Transformer Models:**

Transformer models use attention mechanisms to capture relationships between all time steps, not just sequential dependencies.

**How Forecast Values Are Generated:**

1. **Data Preparation:**
   - Historical data is converted into sequences (e.g., last 12 years to predict next 3 years)
   - Data is normalized and embedded into vector representations
   - Positional encoding is added to preserve temporal order information

2. **Model Architecture:**
   - **Self-Attention Mechanism**: 
     - For each time step, calculates attention scores to all other time steps
     - Learns which historical periods are most relevant (e.g., "2019-2020 growth pattern is similar to 2024-2025")
     - Attention weights show: "When predicting 2025, the model focuses 40% on 2020, 30% on 2021, 20% on 2022, 10% on others"
   - **Multi-Head Attention**: Multiple attention heads capture different types of relationships
   - **Feed-Forward Networks**: Apply learned transformations to attention outputs
   - **Layer Normalization & Residual Connections**: Stabilize training

3. **Model Training:**
   - Training process:
     - Feed sequence [2013-2024] to Transformer
     - Model calculates attention between all pairs of years
     - Learns patterns: "Years with similar growth rates (2017-2018, 2021-2022) inform future predictions"
     - Predicts [2025, 2026, 2027] simultaneously
     - Compares predictions to actual values
     - Adjusts weights via backpropagation to minimize error
   - Learns complex relationships: "If revenue grew 15% in 2018 and 12% in 2019, and similar pattern occurred in 2021-2022, expect 10% growth in 2025"

4. **Forecast Generation:**
   - For future periods:
     - Input sequence [2015-2024] is embedded with positional encoding
     - Each year's representation attends to all other years:
       - Attention(Q, K, V) = softmax(QK^T / √d_k) × V
       - Where Q=query (target year), K=key (all years), V=value (all years)
     - Multiple attention heads capture different patterns
     - Outputs are combined through feed-forward layers
     - Final layer produces forecast values
   - Example: When predicting 2025:
     - Model calculates attention to 2020 (0.4), 2021 (0.3), 2022 (0.2), 2023 (0.1)
     - Combines these weighted historical patterns
     - Outputs forecast: $65B (weighted combination of similar historical growth patterns)

5. **Confidence Intervals:**
   - Based on validation set prediction errors
   - Accounts for model uncertainty and attention weight variance
   - Wider intervals when attention is spread across many years (less confident)

**Best for:**
- Capturing complex, non-linear patterns and relationships
- When you need to understand which historical periods drive forecasts (attention weights)
- State-of-the-art accuracy for complex time series

**Sources:**
- Vaswani, A., et al. (2017). Attention is all you need. NIPS
- [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/)
- [Time Series Forecasting with Transformers](https://huggingface.co/docs/transformers/tasks/time_series_forecasting)
        """,
        
        "ensemble": """
**📚 About Ensemble Forecasting:**

Ensemble methods combine predictions from multiple models to improve accuracy and reduce uncertainty.

**How Forecast Values Are Generated:**

1. **Individual Model Training:**
   - Each model (ARIMA, Prophet, ETS, LSTM, Transformer) is trained independently on historical data
   - Each model generates its own forecast for future periods
   - Example individual forecasts for 2025:
     - ARIMA: $62B
     - Prophet: $65B
     - ETS: $63B
     - LSTM: $66B
     - Transformer: $64B

2. **Ensemble Combination Methods:**

   **A. Equal-Weight Ensemble:**
   - Simple average: Forecast = (ARIMA + Prophet + ETS + LSTM + Transformer) / 5
   - Example: ($62B + $65B + $63B + $66B + $64B) / 5 = $64B
   - Assumes all models are equally reliable

   **B. Performance-Weighted Ensemble:**
   - Each model's historical accuracy (MAE/RMSE) is calculated on validation set
   - Models with lower errors get higher weights
   - Example weights: ARIMA (0.15), Prophet (0.25), ETS (0.20), LSTM (0.25), Transformer (0.15)
   - Weighted forecast: $62B×0.15 + $65B×0.25 + $63B×0.20 + $66B×0.25 + $64B×0.15 = $64.2B
   - Better models contribute more to final forecast

   **C. Stacked Ensemble:**
   - Meta-learner (e.g., linear regression) is trained on validation set
   - Learns optimal combination: "If ARIMA predicts high and LSTM predicts high, actual is high"
   - Meta-learner learns: Forecast = 0.1×ARIMA + 0.3×Prophet + 0.2×ETS + 0.25×LSTM + 0.15×Transformer
   - Applies learned weights to new forecasts

3. **Forecast Generation Process:**
   - Step 1: Train all base models on historical data
   - Step 2: Generate forecasts from each model
   - Step 3: Calculate ensemble weights (if performance-based)
   - Step 4: Combine forecasts using selected method
   - Step 5: Calculate ensemble confidence intervals (accounting for model agreement/disagreement)

4. **Confidence Intervals:**
   - Ensemble CI accounts for:
     - Individual model uncertainties
     - Model agreement (if all models agree, CI is narrower)
     - Model disagreement (if models disagree, CI is wider)
   - Formula: CI = ensemble_forecast ± 1.96 × sqrt(weighted_variance_of_individual_forecasts)

**Benefits:**
- Reduces overfitting (one model's bias is offset by others)
- Captures different patterns (ARIMA captures trends, LSTM captures non-linear patterns)
- More robust to outliers (one bad forecast doesn't ruin the ensemble)
- Typically 10-20% more accurate than individual models

**Best for:**
- When you want the most reliable forecasts
- Reducing model-specific biases
- Capturing different aspects of the data (trends, seasonality, non-linear patterns)

**Sources:**
- [Ensemble Methods in Machine Learning](https://scikit-learn.org/stable/modules/ensemble.html)
- [Ensemble Forecasting: Combining Forecasts for Improved Accuracy](https://otexts.com/fpp3/combinations.html)
- Clemen, R. T. (1989). Combining forecasts: A review and annotated bibliography
        """,
    }
    
    explanation = explanations.get(method_lower, "")
    
    if explanation:
        # Add general ML forecasting context
        explanation += """
        
**💡 Understanding Forecast Values:**

The forecast values you see are generated through a systematic process:

1. **Historical Data Analysis**: The model analyzes patterns in historical revenue data (e.g., 2015-2024)
2. **Pattern Learning**: Each model learns different patterns:
   - **Statistical models (ARIMA, Prophet, ETS)**: Learn linear trends, seasonality, and autocorrelation
   - **Neural networks (LSTM, GRU, Transformer)**: Learn complex non-linear relationships and interactions
3. **Mathematical Extrapolation**: The model uses learned patterns to project future values
4. **Uncertainty Quantification**: Confidence intervals account for:
   - Historical prediction errors (how much past forecasts deviated from actuals)
   - Model uncertainty (how confident the model is in its learned patterns)
   - Data uncertainty (variability in historical data)

**Important Notes:**
- Forecasts are **probabilistic predictions**, not certainties
- Confidence intervals show the **range** of likely outcomes (e.g., 95% chance revenue will be between $X and $Y)
- Different models may produce different forecasts because they capture different patterns
- Ensemble methods combine multiple models to reduce uncertainty and improve accuracy

**📖 General ML Forecasting Resources:**
- [Time Series Forecasting: A Comprehensive Guide](https://www.machinelearningmastery.com/time-series-forecasting/)
- [Financial Time Series Forecasting Best Practices](https://towardsdatascience.com/time-series-forecasting-in-python-an-introduction-cd8d73d0d0b6)
- Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: principles and practice (3rd ed.)
- [scikit-learn Time Series Guide](https://scikit-learn.org/stable/modules/time_series.html)
        """
    
    return explanation


def _is_forecasting_query(query: str) -> bool:
    """Check if query is asking for forecasting/prediction."""
    import re
    forecasting_keywords = [
        r'\bforecast\b',
        r'\bpredict\b',
        r'\bestimate\b',
        r'\bprojection\b',
        r'\bproject\b',
        r'\boutlook\b',
        r'\bfuture\b',
        r'\bnext\s+\d+\s+years?\b',
        r'\bupcoming\s+years?\b',
    ]
    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in forecasting_keywords)


def _extract_forecast_metric(query: str) -> Optional[str]:
    """Extract metric name from forecasting query."""
    import re
    query_lower = query.lower()
    
    # Common metric keywords
    metric_keywords = ['revenue', 'sales', 'income', 'earnings', 'cash flow', 'free cash flow', 
                       'net income', 'ebitda', 'profit', 'margin', 'eps', 'assets', 'liabilities']
    
    # Pattern 1: "Forecast Apple's revenue using LSTM" - extract after possessive
    match = re.search(r"(?:forecast|predict|estimate)\s+\w+\'?s?\s+(\w+(?:\s+\w+)?)\s*(?:using|with|$)", query_lower)
    if match:
        metric = match.group(1).strip()
        if metric in metric_keywords or any(kw in metric for kw in metric_keywords):
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(metric, metric.replace(' ', '_'))
    
    # Pattern 2: "Forecast revenue for Apple" - extract before "for"
    match = re.search(r"(?:forecast|predict|estimate)\s+(\w+(?:\s+\w+)?)\s+(?:for|of)", query_lower)
    if match:
        metric = match.group(1).strip()
        if metric in metric_keywords or any(kw in metric for kw in metric_keywords):
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(metric, metric.replace(' ', '_'))
    
    # Pattern 3: "What's the revenue forecast for Apple?" - extract metric before "forecast"
    match = re.search(r"(?:what'?s?|what\s+is)\s+(?:the\s+)?(\w+(?:\s+\w+)?)\s+(?:forecast|prediction|estimate|projection)", query_lower)
    if match:
        metric = match.group(1).strip()
        if metric in metric_keywords or any(kw in metric for kw in metric_keywords):
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(metric, metric.replace(' ', '_'))
    
    # Pattern 4: Look for metric keywords anywhere in query
    for keyword in metric_keywords:
        if keyword in query_lower:
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(keyword, keyword.replace(' ', '_'))
    
    # Default to revenue if no specific metric mentioned
    return 'revenue'


def _extract_forecast_method(query: str) -> str:
    """Extract forecasting method from query (ARIMA, Prophet, ETS, LSTM, GRU, Transformer, ensemble, or auto)."""
    import re
    query_lower = query.lower()
    
    # Check for specific method mentions (order matters - check specific methods first)
    if re.search(r'\b(?:using|with|via)\s+transformer', query_lower):
        return "transformer"
    elif re.search(r'\b(?:using|with|via)\s+lstm', query_lower):
        return "lstm"
    elif re.search(r'\b(?:using|with|via)\s+gru', query_lower):
        return "gru"
    elif re.search(r'\b(?:using|with|via)\s+arima', query_lower):
        return "arima"
    elif re.search(r'\b(?:using|with|via)\s+prophet', query_lower):
        return "prophet"
    elif re.search(r'\b(?:using|with|via)\s+ets', query_lower):
        return "ets"
    elif re.search(r'\b(?:using|with|via)\s+ensemble', query_lower):
        return "ensemble"
    elif re.search(r'\b(?:using|with|via)\s+(?:best|auto|automatic|ml)', query_lower):
        return "auto"
    # Check for direct method mentions without "using"
    elif re.search(r'\btransformer\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "transformer"
    elif re.search(r'\blstm\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "lstm"
    elif re.search(r'\bgru\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "gru"
    
    # Default to auto if no method specified
    return "auto"


def _build_mandatory_data_block(ticker: str, latest_records: dict, period_label: str) -> str:
    """
    Build a prominent mandatory data block that LLM MUST use.
    This prevents LLM from using training data instead of database values.
    """
    lines = [
        "\n" + "="*80,
        f"🚨 CRITICAL: USE THESE EXACT VALUES FOR {ticker} - DO NOT USE TRAINING DATA 🚨",
        "="*80,
        "",
        f"**MANDATORY DATA - Period: {period_label}**",
        "**⚠️ YOU MUST USE ONLY THESE VALUES IN YOUR RESPONSE ⚠️**",
        ""
    ]
    
    # Add key metrics with exact values
    priority_metrics = [
        ('revenue', 'Revenue'),
        ('net_income', 'Net Income'),
        ('gross_margin', 'Gross Margin'),
        ('operating_margin', 'Operating Margin'),
        ('net_margin', 'Net Margin'),
        ('total_assets', 'Total Assets'),
        ('shareholders_equity', 'Shareholders Equity'),
        ('free_cash_flow', 'Free Cash Flow'),
    ]
    
    for metric_key, metric_label in priority_metrics:
        if metric_key in latest_records:
            record = latest_records[metric_key]
            value = record.value
            
            # Format based on metric type
            if value is None:
                continue
            elif abs(value) > 1_000_000_000:
                # Currency in billions
                formatted = f"${value / 1_000_000_000:.1f}B"
            elif abs(value) < 1 and metric_key in ['gross_margin', 'operating_margin', 'net_margin', 'roe', 'roic', 'roa']:
                # Decimal percentage
                formatted = f"{value * 100:.1f}%"
            elif 'margin' in metric_key or metric_key in ['roe', 'roic', 'roa']:
                # Already percentage
                formatted = f"{value:.1f}%"
            else:
                formatted = f"{value:.2f}"
            
            lines.append(f"  • {metric_label}: {formatted} ({period_label})")
    
    lines.extend([
        "",
        "⚠️ WARNING: DO NOT use FY2024 or older data from your training",
        f"⚠️ WARNING: USE ONLY the {period_label} values listed above",
        f"⚠️ WARNING: Always include '{period_label}' when mentioning these values",
        "="*80,
        ""
    ])
    
    return "\n".join(lines)


def _build_ml_forecast_context(
    ticker: str,
    metric: str,
    database_path: str,
    periods: int = 3,
    method: str = "auto"
) -> Optional[str]:
    """Build ML forecasting context for a ticker and metric."""
    if not ML_FORECASTING_AVAILABLE:
        return None
    
    try:
        LOGGER.info(f"Generating ML forecast for {ticker} {metric} using {method}")
        ml_forecaster = get_ml_forecaster(database_path)
        
        # Check if requested method is available
        if method == "lstm" or method == "gru":
            if ml_forecaster.lstm_forecaster is None:
                LOGGER.warning(f"LSTM/GRU not available (TensorFlow missing), falling back to auto-select")
                method = "auto"
        elif method == "transformer":
            if ml_forecaster.transformer_forecaster is None:
                LOGGER.warning(f"Transformer not available (PyTorch missing), falling back to auto-select")
                method = "auto"
        
        # Validate we have a forecaster available
        if method == "auto":
            # Check what's available
            available_methods = []
            if ml_forecaster.arima_forecaster:
                available_methods.append("ARIMA")
            if ml_forecaster.prophet_forecaster:
                available_methods.append("Prophet")
            if ml_forecaster.ets_forecaster:
                available_methods.append("ETS")
            if ml_forecaster.lstm_forecaster:
                available_methods.append("LSTM")
            if ml_forecaster.transformer_forecaster:
                available_methods.append("Transformer")
            
            if not available_methods:
                LOGGER.error(f"No ML forecasting methods available - all dependencies missing")
                error_context = f"\n{'='*80}\n⚠️ ML FORECASTING UNAVAILABLE\n{'='*80}\n"
                error_context += f"**Reason:** No ML forecasting methods are available. Required dependencies are missing.\n"
                error_context += f"**Required:** Install pmdarima, statsmodels, prophet, tensorflow, or torch\n"
                error_context += f"**Fallback:** The system will use historical data analysis instead.\n"
                error_context += f"{'='*80}\n"
                return error_context
        
        forecast = ml_forecaster.forecast(
            ticker=ticker,
            metric=metric,
            periods=periods,
            method=method
        )
        
        if forecast is None:
            LOGGER.warning(f"ML forecast generation returned None for {ticker} {metric} using {method}")
            # Check if we can get more info about why it failed
            try:
                # Try to fetch data to see if that's the issue
                records = ml_forecaster.arima_forecaster._fetch_metric_records(ticker, metric, min_periods=2) if ml_forecaster.arima_forecaster else []
                if not records or len(records) < 5:
                    error_context = f"\n{'='*80}\n⚠️ ML FORECAST UNAVAILABLE - {ticker} {metric.upper()}\n{'='*80}\n"
                    error_context += f"**Reason:** Insufficient historical data for {ticker} {metric}.\n"
                    error_context += f"**Data Available:** {len(records) if records else 0} periods (need at least 5-10)\n"
                    error_context += f"**Recommendation:** Ensure historical data is ingested for this ticker and metric.\n"
                    error_context += f"{'='*80}\n"
                    LOGGER.warning(f"Returning error context due to insufficient data: {len(records) if records else 0} periods")
                    return error_context, None
                else:
                    error_context = f"\n{'='*80}\n⚠️ ML FORECAST GENERATION FAILED - {ticker} {metric.upper()}\n{'='*80}\n"
                    error_context += f"**Reason:** Forecast generation failed despite having {len(records)} data points.\n"
                    error_context += f"**Possible causes:** Model training errors, data format issues, or insufficient recent data.\n"
                    error_context += f"**Recommendation:** The system will use historical data analysis instead.\n"
                    error_context += f"{'='*80}\n"
                    LOGGER.warning(f"Returning error context despite having {len(records)} data points")
                    return error_context, None
            except Exception as e:
                LOGGER.exception(f"Error checking data availability: {e}")
                error_context = f"\n{'='*80}\n⚠️ ML FORECAST UNAVAILABLE - {ticker} {metric.upper()}\n{'='*80}\n"
                error_context += f"**Reason:** ML forecast generation failed for {ticker} {metric} using {method}.\n"
                error_context += f"**Possible causes:**\n"
                error_context += f"  - Insufficient historical data (need at least 5-10 periods)\n"
                error_context += f"  - Model dependencies missing (TensorFlow for LSTM, PyTorch for Transformer)\n"
                error_context += f"  - Model training/forecasting errors\n"
                error_context += f"**Recommendation:** The system will fall back to historical data analysis.\n"
                error_context += f"{'='*80}\n"
                LOGGER.warning(f"Returning error context due to exception: {e}")
                return error_context, None
        
        LOGGER.info(f"ML forecast generated successfully for {ticker} {metric}: {len(forecast.predicted_values)} periods")
        
        # Format forecast results with EXTREMELY EXPLICIT instructions
        forecast_lines = [
            f"\n{'='*80}",
            f"🚨🚨🚨 CRITICAL: THIS IS THE PRIMARY ANSWER - USE THESE FORECAST VALUES 🚨🚨🚨",
            f"📊 ML FORECAST ({forecast.method.upper()}) - {ticker} {metric.upper()}",
            f"{'='*80}\n",
            f"**Model Used:** {forecast.method.upper()}",
            f"**Confidence:** {forecast.confidence:.1%}\n",
            f"{'='*80}",
            f"🚨 MANDATORY INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY 🚨",
            f"{'='*80}\n",
            f"**⚠️ WARNING: IF YOU DO NOT INCLUDE ALL TECHNICAL DETAILS BELOW, YOUR RESPONSE IS INCOMPLETE ⚠️**\n",
            f"**⚠️ THE USER EXPECTS A HIGHLY DETAILED TECHNICAL RESPONSE WITH ALL MODEL SPECIFICATIONS ⚠️**\n",
            f"**⚠️ DO NOT PROVIDE A GENERIC SUMMARY - INCLUDE EVERY NUMBER, METRIC, AND DETAIL ⚠️**\n\n",
            f"**YOUR RESPONSE MUST INCLUDE ALL OF THE FOLLOWING - NO EXCEPTIONS:**\n\n",
            f"1. **FORECAST VALUES (REQUIRED):**",
            f"   - List ALL forecasted values for each year with exact numbers",
            f"   - Include confidence intervals for each year",
            f"   - Calculate and show year-over-year growth rates",
            f"   - Calculate and show multi-year CAGR\n",
            f"2. **MODEL ARCHITECTURE (REQUIRED):**",
            f"   - Network architecture: layers, units per layer, total parameters",
            f"   - Input shape and lookback window",
            f"   - Model type (LSTM/GRU) and how it works\n",
            f"3. **TRAINING DETAILS (REQUIRED):**",
            f"   - Training epochs (exact number)",
            f"   - Training loss (final value)",
            f"   - Validation loss (final value)",
            f"   - Overfitting analysis (val/train ratio)",
            f"   - Training time",
            f"   - Data points used\n",
            f"4. **HYPERPARAMETERS (REQUIRED):**",
            f"   - Learning rate (with explanation)",
            f"   - Batch size",
            f"   - Dropout rate (if applicable)",
            f"   - Optimizer used",
            f"   - All other hyperparameters\n",
            f"5. **PERFORMANCE METRICS (REQUIRED):**",
            f"   - Training loss (MSE)",
            f"   - Validation loss (MSE)",
            f"   - Model confidence score",
            f"   - Overfitting ratio\n",
            f"6. **FORECAST ANALYSIS (REQUIRED):**",
            f"   - Year-over-year growth rates for each period",
            f"   - Multi-year CAGR calculation",
            f"   - Confidence interval widths",
            f"   - Uncertainty level assessment",
            f"   - Trajectory analysis (accelerating/decelerating)\n",
            f"7. **MODEL EXPLAINABILITY (REQUIRED):**",
            f"   - Detailed explanation of how {forecast.method.upper()} works",
            f"   - Why this model is suitable for this forecast",
            f"   - Key concepts (memory cells, gates, etc.)",
            f"   - Training process explanation\n",
            f"8. **DATA PREPROCESSING (REQUIRED):**",
            f"   - Scaling method used",
            f"   - Feature engineering applied",
            f"   - Data points used",
            f"   - Train/test split\n",
            f"9. **COMPUTATIONAL DETAILS (REQUIRED):**",
            f"   - Training time",
            f"   - Total model parameters",
            f"   - Model complexity\n",
            f"10. **FORECAST INTERPRETATION (REQUIRED):**",
            f"    - Total growth projection",
            f"    - Trajectory pattern (consistent growth, declining, mixed)",
            f"    - Pattern detection (accelerating/decelerating)",
            f"    - Uncertainty level\n",
            f"{'='*80}",
            f"**CRITICAL: DO NOT SUMMARIZE - INCLUDE EVERY DETAIL BELOW IN YOUR RESPONSE**",
            f"{'='*80}\n\n",
            "**Forecasted Values:**\n",
        ]
        
        for i, year in enumerate(forecast.periods):
            value = forecast.predicted_values[i]
            low = forecast.confidence_intervals_low[i]
            high = forecast.confidence_intervals_high[i]
            
            # Format value based on magnitude
            if abs(value) >= 1_000_000_000:
                value_str = f"${value / 1_000_000_000:.2f}B"
                low_str = f"${low / 1_000_000_000:.2f}B"
                high_str = f"${high / 1_000_000_000:.2f}B"
            elif abs(value) >= 1_000_000:
                value_str = f"${value / 1_000_000:.2f}M"
                low_str = f"${low / 1_000_000:.2f}M"
                high_str = f"${high / 1_000_000:.2f}M"
            else:
                value_str = f"${value:,.0f}"
                low_str = f"${low:,.0f}"
                high_str = f"${high:,.0f}"
            
            forecast_lines.append(
                f"  • **{year}:** {value_str} (95% CI: {low_str} - {high_str})"
            )
        
        # Calculate and display growth rates IMMEDIATELY after forecast values
        if len(forecast.predicted_values) >= 2:
            forecast_lines.append("\n**📈 GROWTH RATES (CALCULATED - INCLUDE IN YOUR RESPONSE):**\n")
            last_historical = None  # Will be set from historical data if available
            for i in range(len(forecast.predicted_values)):
                if i == 0:
                    # First year: compare to last historical value (if available)
                    # For now, show YoY growth within forecast
                    if len(forecast.predicted_values) > 1:
                        prev = forecast.predicted_values[0]
                        curr = forecast.predicted_values[1]
                        if prev > 0:
                            growth = ((curr / prev) - 1) * 100
                            forecast_lines.append(f"  • **{forecast.periods[0]} to {forecast.periods[1]}:** {growth:+.2f}% YoY growth\n")
                else:
                    prev = forecast.predicted_values[i-1]
                    curr = forecast.predicted_values[i]
                    if prev > 0:
                        growth = ((curr / prev) - 1) * 100
                        forecast_lines.append(f"  • **{forecast.periods[i-1]} to {forecast.periods[i]}:** {growth:+.2f}% YoY growth\n")
            
            # Calculate CAGR
            if len(forecast.predicted_values) >= 3:
                first = forecast.predicted_values[0]
                last = forecast.predicted_values[-1]
                years = len(forecast.predicted_values) - 1
                if first > 0:
                    cagr = ((last / first) ** (1/years) - 1) * 100
                    forecast_lines.append(f"  • **Multi-Year CAGR ({years} years):** {cagr:.2f}%\n")
        
        # Add detailed model specifications - MAKE THIS VERY PROMINENT
        if forecast.model_details:
            forecast_lines.append(f"\n{'='*80}")
            forecast_lines.append("🔧 MODEL TECHNICAL SPECIFICATIONS (INCLUDE ALL IN YOUR RESPONSE)")
            forecast_lines.append(f"{'='*80}\n")
            
            # ARIMA details - MAKE VERY PROMINENT
            if forecast.method.upper() == 'ARIMA' or 'model_params' in forecast.model_details:
                forecast_lines.append(f"\n**📊 ARIMA MODEL ARCHITECTURE:**\n")
                if 'model_params' in forecast.model_details:
                    params = forecast.model_details['model_params']
                    if isinstance(params, dict) and 'order' in params:
                        order = params['order']
                        if isinstance(order, (list, tuple)) and len(order) >= 3:
                            forecast_lines.append(f"  - **ARIMA Order:** {order} (AR={order[0]}, I={order[1]}, MA={order[2]})")
                            forecast_lines.append(f"    - **AR (AutoRegressive) Order:** {order[0]} (number of lagged observations used)")
                            forecast_lines.append(f"    - **I (Integrated) Order:** {order[1]} (degree of differencing to make series stationary)")
                            forecast_lines.append(f"    - **MA (Moving Average) Order:** {order[2]} (number of lagged forecast errors used)")
                    if isinstance(params, dict) and 'seasonal_order' in params:
                        seasonal = params['seasonal_order']
                        if seasonal:
                            forecast_lines.append(f"  - **Seasonal Order (SARIMA):** {seasonal} (seasonal ARIMA components)")
                    if isinstance(params, dict) and 'ar_order' in params:
                        forecast_lines.append(f"  - **AR Order:** {params['ar_order']}")
                    if isinstance(params, dict) and 'diff_order' in params:
                        forecast_lines.append(f"  - **Differencing Order:** {params['diff_order']}")
                    if isinstance(params, dict) and 'ma_order' in params:
                        forecast_lines.append(f"  - **MA Order:** {params['ma_order']}")
                    if isinstance(params, dict) and 'is_seasonal' in params:
                        is_seasonal = params['is_seasonal']
                        forecast_lines.append(f"  - **Seasonal Model:** {'Yes (SARIMA)' if is_seasonal else 'No (ARIMA)'}")
                if 'aic' in forecast.model_details:
                    aic = forecast.model_details.get('aic', 'N/A')
                    if aic != 'N/A':
                        forecast_lines.append(f"  - **AIC (Akaike Information Criterion):** {aic:.2f} (lower is better - measures model quality)")
                if 'bic' in forecast.model_details:
                    bic = forecast.model_details.get('bic', 'N/A')
                    if bic != 'N/A':
                        forecast_lines.append(f"  - **BIC (Bayesian Information Criterion):** {bic:.2f} (lower is better - penalizes complexity)")
                if 'log_likelihood' in forecast.model_details:
                    ll = forecast.model_details.get('log_likelihood')
                    if ll is not None:
                        forecast_lines.append(f"  - **Log-Likelihood:** {ll:.2f} (higher is better - measures model fit)")
                forecast_lines.append(f"  - **Model Type:** ARIMA (AutoRegressive Integrated Moving Average)")
                forecast_lines.append(f"    - ARIMA models combine autoregression, differencing, and moving average components")
                forecast_lines.append(f"    - Suitable for time series with trends and seasonality")
                forecast_lines.append(f"    - Automatically selected optimal parameters using auto-ARIMA\n")
            
            # Prophet details - MAKE VERY PROMINENT
            if forecast.method.upper() == 'PROPHET' or 'seasonality_detected' in forecast.model_details:
                forecast_lines.append(f"\n**📈 PROPHET MODEL ARCHITECTURE:**\n")
                if 'seasonality_detected' in forecast.model_details:
                    seasonality = forecast.model_details['seasonality_detected']
                    if isinstance(seasonality, dict):
                        detected = [k for k, v in seasonality.items() if k in ['yearly', 'weekly', 'daily'] and v]
                        if detected:
                            forecast_lines.append(f"  - **Seasonality Detected:** {', '.join(detected)}")
                            forecast_lines.append(f"    - Prophet automatically detects and models seasonal patterns")
                            forecast_lines.append(f"    - Yearly seasonality captures annual patterns")
                            forecast_lines.append(f"    - Weekly seasonality captures weekly patterns")
                            forecast_lines.append(f"    - Daily seasonality captures daily patterns")
                if 'changepoints' in forecast.model_details:
                    changepoints = forecast.model_details['changepoints']
                    if changepoints:
                        forecast_lines.append(f"  - **Trend Changepoints:** {len(changepoints)} detected")
                        forecast_lines.append(f"    - Changepoints identify when trend direction changes")
                        forecast_lines.append(f"    - Prophet automatically detects these structural breaks")
                if 'changepoint_count' in forecast.model_details:
                    cp_count = forecast.model_details['changepoint_count']
                    forecast_lines.append(f"  - **Changepoint Count:** {cp_count} (number of trend changes detected)")
                if 'growth_model' in forecast.model_details:
                    growth = forecast.model_details['growth_model']
                    forecast_lines.append(f"  - **Growth Model:** {growth}")
                    forecast_lines.append(f"    - Linear growth: constant growth rate")
                    forecast_lines.append(f"    - Logistic growth: saturating growth with carrying capacity")
                if 'hyperparameters' in forecast.model_details:
                    hyperparams = forecast.model_details['hyperparameters']
                    if isinstance(hyperparams, dict):
                        forecast_lines.append(f"  - **Key Hyperparameters:**")
                        if 'changepoint_prior_scale' in hyperparams:
                            forecast_lines.append(f"    - Changepoint Prior Scale: {hyperparams['changepoint_prior_scale']} (controls flexibility of trend changes)")
                        if 'seasonality_prior_scale' in hyperparams:
                            forecast_lines.append(f"    - Seasonality Prior Scale: {hyperparams['seasonality_prior_scale']} (controls strength of seasonality)")
                        if 'seasonality_mode' in hyperparams:
                            forecast_lines.append(f"    - Seasonality Mode: {hyperparams['seasonality_mode']} (additive or multiplicative)")
                forecast_lines.append(f"  - **Model Type:** Prophet (Facebook's time series forecasting tool)")
                forecast_lines.append(f"    - Prophet decomposes time series into trend, seasonality, and holidays")
                forecast_lines.append(f"    - Handles missing data, outliers, and changepoints automatically")
                forecast_lines.append(f"    - Ideal for business time series with strong seasonality\n")
            
            # LSTM/GRU details - MAKE VERY PROMINENT
            if 'model_type' in forecast.model_details or 'layers' in forecast.model_details:
                model_type = forecast.model_details.get('model_type', 'lstm').upper()
                forecast_lines.append(f"\n**🧠 {model_type} NEURAL NETWORK ARCHITECTURE:**\n")
                if 'layers' in forecast.model_details:
                    layers = forecast.model_details['layers']
                    if isinstance(layers, list):
                        forecast_lines.append(f"  - **Network Architecture:** {len(layers)} layers with {layers} units per layer")
                        forecast_lines.append(f"    - Layer 1: {layers[0]} {model_type} units")
                        if len(layers) > 1:
                            for i, units in enumerate(layers[1:], 2):
                                forecast_lines.append(f"    - Layer {i}: {units} {model_type} units")
                    else:
                        forecast_lines.append(f"  - **Network Architecture:** {layers} layers")
                if 'units' in forecast.model_details:
                    units = forecast.model_details['units']
                    forecast_lines.append(f"  - **Hidden Units per Layer:** {units} (number of memory cells in each {model_type} layer)")
                if 'input_shape' in forecast.model_details:
                    input_shape = forecast.model_details['input_shape']
                    forecast_lines.append(f"  - **Input Shape:** {input_shape} (lookback_window x features)")
                forecast_lines.append(f"  - **Model Type:** {model_type} (Long Short-Term Memory / Gated Recurrent Unit)")
                forecast_lines.append(f"    - {model_type} networks use memory cells with gates (forget, input, output) to learn long-term dependencies")
                forecast_lines.append(f"    - Each memory cell can selectively remember or forget information over time")
                forecast_lines.append(f"    - This makes {model_type} ideal for time series forecasting with complex patterns\n")
            if 'epochs_trained' in forecast.model_details:
                epochs = forecast.model_details['epochs_trained']
                forecast_lines.append(f"  - **Training Epochs:** {epochs} (number of complete passes through training data)")
            if 'training_loss' in forecast.model_details:
                train_loss = forecast.model_details['training_loss']
                forecast_lines.append(f"  - **Final Training Loss (MSE):** {train_loss:.6f} (Mean Squared Error on training set - lower is better)")
            if 'validation_loss' in forecast.model_details:
                val_loss = forecast.model_details['validation_loss']
                forecast_lines.append(f"  - **Final Validation Loss (MSE):** {val_loss:.6f} (Mean Squared Error on validation set - measures generalization)")
                # Add overfitting analysis
                if 'training_loss' in forecast.model_details:
                    train_loss = forecast.model_details['training_loss']
                    overfit_ratio = val_loss / train_loss if train_loss > 0 else 1.0
                    if overfit_ratio > 1.5:
                        forecast_lines.append(f"  - **⚠️ Overfitting Detected:** Validation loss is {overfit_ratio:.2f}x training loss (model may be overfitting)")
                    elif overfit_ratio < 1.1:
                        forecast_lines.append(f"  - **✅ Good Generalization:** Validation loss is {overfit_ratio:.2f}x training loss (model generalizes well)")
                    else:
                        forecast_lines.append(f"  - **Overfitting Ratio:** {overfit_ratio:.2f} (val/train loss ratio)")
            if 'learning_rate' in forecast.model_details:
                lr = forecast.model_details['learning_rate']
                forecast_lines.append(f"  - **Learning Rate:** {lr:.6f} (controls step size in gradient descent - lower = more stable but slower convergence)")
            if 'batch_size' in forecast.model_details:
                batch = forecast.model_details['batch_size']
                forecast_lines.append(f"  - **Batch Size:** {batch} (number of samples per training iteration - affects memory usage and training speed)")
            if 'lookback_window' in forecast.model_details:
                window = forecast.model_details['lookback_window']
                forecast_lines.append(f"  - **Lookback Window:** {window} time steps (number of historical periods used to predict next value)")
            if 'optimizer' in forecast.model_details:
                optimizer = forecast.model_details['optimizer']
                forecast_lines.append(f"  - **Optimizer:** {optimizer} (algorithm used to update model weights during training)")
            if 'total_parameters' in forecast.model_details:
                params = forecast.model_details['total_parameters']
                forecast_lines.append(f"  - **Total Model Parameters:** {params:,} (total trainable weights in the network)")
            if 'training_time' in forecast.model_details:
                train_time = forecast.model_details['training_time']
                forecast_lines.append(f"  - **Training Time:** {train_time:.2f} seconds")
            if 'data_points_used' in forecast.model_details:
                data_points = forecast.model_details['data_points_used']
                forecast_lines.append(f"  - **Historical Data Points Used:** {data_points} periods")
            if 'train_test_split' in forecast.model_details:
                split = forecast.model_details['train_test_split']
                forecast_lines.append(f"  - **Train/Test Split:** {split} (training samples / validation samples)")
            if 'dropout' in forecast.model_details:
                dropout = forecast.model_details['dropout']
                forecast_lines.append(f"  - **Dropout Rate:** {dropout:.2f} (regularization to prevent overfitting - randomly sets {dropout*100:.0f}% of neurons to zero during training)")
            
            # ETS details - MAKE VERY PROMINENT
            if forecast.method.upper() == 'ETS' or 'model_type' in forecast.model_details:
                if 'model_type' in forecast.model_details and forecast.model_details['model_type']:
                    model_type = forecast.model_details['model_type']
                    forecast_lines.append(f"\n**📉 ETS MODEL ARCHITECTURE:**\n")
                    forecast_lines.append(f"  - **ETS Model Type:** {model_type}")
                    forecast_lines.append(f"    - ETS notation: Error-Trend-Seasonal (e.g., AAN = Additive Error, Additive Trend, No Seasonality)")
                    forecast_lines.append(f"    - First letter: Error type (A=Additive, M=Multiplicative)")
                    forecast_lines.append(f"    - Second letter: Trend type (A=Additive, M=Multiplicative, N=None)")
                    forecast_lines.append(f"    - Third letter: Seasonal type (A=Additive, M=Multiplicative, N=None)")
                    if 'smoothing_params' in forecast.model_details:
                        smoothing = forecast.model_details['smoothing_params']
                        if isinstance(smoothing, dict):
                            forecast_lines.append(f"  - **Smoothing Parameters:**")
                            if 'alpha' in smoothing and smoothing['alpha'] is not None:
                                forecast_lines.append(f"    - Alpha (Level): {smoothing['alpha']:.4f} (controls how quickly level adapts to new data)")
                            if 'beta' in smoothing and smoothing['beta'] is not None:
                                forecast_lines.append(f"    - Beta (Trend): {smoothing['beta']:.4f} (controls how quickly trend adapts)")
                            if 'gamma' in smoothing and smoothing['gamma'] is not None:
                                forecast_lines.append(f"    - Gamma (Seasonal): {smoothing['gamma']:.4f} (controls how quickly seasonality adapts)")
                    if 'trend' in forecast.model_details:
                        trend = forecast.model_details['trend']
                        forecast_lines.append(f"  - **Trend Component:** {trend} (additive or none)")
                    if 'seasonal' in forecast.model_details:
                        seasonal = forecast.model_details['seasonal']
                        forecast_lines.append(f"  - **Seasonal Component:** {seasonal} (additive or none)")
                    if 'error' in forecast.model_details:
                        error = forecast.model_details['error']
                        forecast_lines.append(f"  - **Error Component:** {error} (additive or multiplicative)")
                    forecast_lines.append(f"  - **Model Type:** ETS (Exponential Smoothing State Space Model)")
                    forecast_lines.append(f"    - ETS models use exponential smoothing to forecast time series")
                    forecast_lines.append(f"    - Automatically selects optimal model type and parameters")
                    forecast_lines.append(f"    - Suitable for time series with trends and optional seasonality\n")
            
            # Transformer details - MAKE VERY PROMINENT
            if forecast.method.upper() == 'TRANSFORMER' or 'num_layers' in forecast.model_details:
                forecast_lines.append(f"\n**🤖 TRANSFORMER MODEL ARCHITECTURE:**\n")
                if 'num_layers' in forecast.model_details:
                    layers = forecast.model_details['num_layers']
                    forecast_lines.append(f"  - **Transformer Encoder Layers:** {layers} (number of stacked encoder layers)")
                if 'num_heads' in forecast.model_details:
                    heads = forecast.model_details['num_heads']
                    forecast_lines.append(f"  - **Attention Heads:** {heads} (number of parallel attention mechanisms)")
                if 'd_model' in forecast.model_details:
                    d_model = forecast.model_details['d_model']
                    forecast_lines.append(f"  - **Model Dimension:** {d_model} (embedding dimension for each time step)")
                if 'dim_feedforward' in forecast.model_details:
                    ff_dim = forecast.model_details['dim_feedforward']
                    forecast_lines.append(f"  - **Feedforward Dimension:** {ff_dim} (dimension of feedforward network)")
                if 'lookback_window' in forecast.model_details:
                    window = forecast.model_details['lookback_window']
                    forecast_lines.append(f"  - **Lookback Window:** {window} time steps (historical periods used for prediction)")
                forecast_lines.append(f"  - **Model Type:** Transformer (Attention-based neural network)")
                forecast_lines.append(f"    - Transformers use self-attention to learn relationships between time steps")
                forecast_lines.append(f"    - Attention mechanism allows model to focus on relevant historical patterns")
                forecast_lines.append(f"    - Positional encoding preserves temporal order information")
                forecast_lines.append(f"    - Ideal for complex time series with long-range dependencies\n")
            
            # Ensemble details - MAKE VERY PROMINENT
            if forecast.method.upper() == 'ENSEMBLE' or 'models_used' in forecast.model_details:
                forecast_lines.append(f"\n**🎯 ENSEMBLE MODEL ARCHITECTURE:**\n")
                if 'models_used' in forecast.model_details:
                    models = forecast.model_details['models_used']
                    if isinstance(models, list):
                        forecast_lines.append(f"  - **Models Combined:** {', '.join([m.upper() for m in models])} ({len(models)} models)")
                        forecast_lines.append(f"    - Ensemble combines predictions from multiple models")
                        forecast_lines.append(f"    - Reduces individual model errors through averaging")
                if 'weights' in forecast.model_details:
                    weights = forecast.model_details['weights']
                    if isinstance(weights, dict):
                        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
                        forecast_lines.append(f"  - **Model Weights (Weighted Average):**")
                        for m, w in sorted_weights[:5]:
                            forecast_lines.append(f"    - {m.upper()}: {w:.1%} (contributes {w*100:.1f}% to final forecast)")
                        if len(sorted_weights) > 5:
                            forecast_lines.append(f"    - ... ({len(sorted_weights)} total models)")
                if 'ensemble_method' in forecast.model_details:
                    method = forecast.model_details['ensemble_method']
                    forecast_lines.append(f"  - **Ensemble Method:** {method}")
                    if method == 'weighted_average':
                        forecast_lines.append(f"    - Weighted average: Combines models based on validation performance")
                    elif method == 'stacking':
                        forecast_lines.append(f"    - Stacking: Uses meta-learner to combine base models")
                    elif method == 'simple_average':
                        forecast_lines.append(f"    - Simple average: Equal weights for all models")
                forecast_lines.append(f"  - **Model Type:** Ensemble (Combination of multiple forecasting models)")
                forecast_lines.append(f"    - Ensemble methods improve forecast accuracy by combining multiple models")
                forecast_lines.append(f"    - Reduces overfitting and increases robustness")
                forecast_lines.append(f"    - Each model contributes based on its validation performance\n")
            
            # Feature engineering
            if 'features_used' in forecast.model_details:
                features = forecast.model_details['features_used']
                if isinstance(features, list):
                    feature_str = ", ".join(features[:5])
                    if len(features) > 5:
                        feature_str += f", ... ({len(features)} total features)"
                    forecast_lines.append(f"  - Features Used: {feature_str}")
            
            # Hyperparameters
            if 'hyperparameters' in forecast.model_details:
                hyperparams = forecast.model_details['hyperparameters']
                if isinstance(hyperparams, dict):
                    hyper_str = ", ".join([f"{k}={v}" for k, v in list(hyperparams.items())[:3]])
                    if len(hyperparams) > 3:
                        hyper_str += f", ... ({len(hyperparams)} total)"
                    forecast_lines.append(f"  - Key Hyperparameters: {hyper_str}")
        
        # Add detailed forecast analysis
        forecast_lines.append("\n**Detailed Forecast Analysis:**\n")
        
        # Calculate year-over-year growth rates
        if len(forecast.predicted_values) >= 2:
            forecast_lines.append("**Year-over-Year Growth Rates:**\n")
            for i in range(1, len(forecast.predicted_values)):
                prev_value = forecast.predicted_values[i-1]
                curr_value = forecast.predicted_values[i]
                if prev_value > 0:
                    growth_rate = ((curr_value / prev_value) - 1) * 100
                    forecast_lines.append(f"  - {forecast.periods[i-1]} to {forecast.periods[i]}: {growth_rate:+.2f}%")
            
            # Calculate multi-year CAGR
            if len(forecast.predicted_values) >= 3:
                first_value = forecast.predicted_values[0]
                last_value = forecast.predicted_values[-1]
                years = len(forecast.predicted_values) - 1
                if first_value > 0:
                    cagr = ((last_value / first_value) ** (1/years) - 1) * 100
                    forecast_lines.append(f"\n**Multi-Year CAGR:** {cagr:.2f}% (over {years} years)")
        
        # Calculate confidence interval widths
        if forecast.confidence_intervals_low and forecast.confidence_intervals_high:
            forecast_lines.append("\n**Forecast Uncertainty Analysis:**\n")
            for i, year in enumerate(forecast.periods):
                value = forecast.predicted_values[i]
                low = forecast.confidence_intervals_low[i]
                high = forecast.confidence_intervals_high[i]
                interval_width = high - low
                interval_width_pct = (interval_width / value) * 100 if value > 0 else 0
                
                if abs(value) >= 1_000_000_000:
                    width_str = f"${interval_width / 1_000_000_000:.2f}B"
                elif abs(value) >= 1_000_000:
                    width_str = f"${interval_width / 1_000_000:.2f}M"
                else:
                    width_str = f"${interval_width:,.0f}"
                
                forecast_lines.append(f"  - {year}: 95% CI width = {width_str} ({interval_width_pct:.1f}% of forecast)")
        
        # Add model performance metrics if available
        if forecast.model_details:
            if 'mae' in forecast.model_details or 'rmse' in forecast.model_details or 'mape' in forecast.model_details:
                forecast_lines.append("\n**Model Performance Metrics (Validation):**\n")
                if 'mae' in forecast.model_details:
                    mae = forecast.model_details['mae']
                    forecast_lines.append(f"  - MAE (Mean Absolute Error): {mae:,.0f}")
                if 'rmse' in forecast.model_details:
                    rmse = forecast.model_details['rmse']
                    forecast_lines.append(f"  - RMSE (Root Mean Squared Error): {rmse:,.0f}")
                if 'mape' in forecast.model_details:
                    mape = forecast.model_details['mape']
                    forecast_lines.append(f"  - MAPE (Mean Absolute Percentage Error): {mape:.2f}%")
                if 'r2' in forecast.model_details:
                    r2 = forecast.model_details['r2']
                    forecast_lines.append(f"  - R² (Coefficient of Determination): {r2:.4f}")
                if 'directional_accuracy' in forecast.model_details:
                    dir_acc = forecast.model_details['directional_accuracy']
                    forecast_lines.append(f"  - Directional Accuracy: {dir_acc:.1%}")
            
            # Training process details
            if 'training_time' in forecast.model_details:
                train_time = forecast.model_details['training_time']
                forecast_lines.append(f"\n**Training Process:**\n")
                forecast_lines.append(f"  - Training Time: {train_time:.2f} seconds")
            if 'data_points_used' in forecast.model_details:
                data_points = forecast.model_details['data_points_used']
                forecast_lines.append(f"  - Historical Data Points Used: {data_points}")
            if 'train_test_split' in forecast.model_details:
                split = forecast.model_details['train_test_split']
                forecast_lines.append(f"  - Train/Test Split: {split}")
            if 'cross_validation_folds' in forecast.model_details:
                folds = forecast.model_details['cross_validation_folds']
                forecast_lines.append(f"  - Cross-Validation Folds: {folds}")
            
            # Data preprocessing details
            if 'preprocessing_applied' in forecast.model_details:
                preprocessing = forecast.model_details['preprocessing_applied']
                if preprocessing:
                    forecast_lines.append(f"\n**Data Preprocessing:**\n")
                    if isinstance(preprocessing, list):
                        for step in preprocessing:
                            forecast_lines.append(f"  - {step}")
                    elif isinstance(preprocessing, dict):
                        for step, applied in preprocessing.items():
                            if applied:
                                forecast_lines.append(f"  - {step}: Applied")
            if 'scaling_method' in forecast.model_details:
                scaling = forecast.model_details['scaling_method']
                forecast_lines.append(f"  - Scaling Method: {scaling}")
            if 'outlier_removal' in forecast.model_details:
                outlier_removal = forecast.model_details['outlier_removal']
                forecast_lines.append(f"  - Outlier Removal: {outlier_removal}")
            if 'missing_data_handling' in forecast.model_details:
                missing_handling = forecast.model_details['missing_data_handling']
                forecast_lines.append(f"  - Missing Data Handling: {missing_handling}")
            
            # Feature engineering details
            if 'features_engineered' in forecast.model_details:
                features = forecast.model_details['features_engineered']
                if features:
                    forecast_lines.append(f"\n**Feature Engineering:**\n")
                    if isinstance(features, list):
                        for feature in features[:10]:  # Show first 10
                            forecast_lines.append(f"  - {feature}")
                        if len(features) > 10:
                            forecast_lines.append(f"  - ... and {len(features) - 10} more features")
                    elif isinstance(features, dict):
                        for feature_type, count in features.items():
                            forecast_lines.append(f"  - {feature_type}: {count} features")
            
            # Model selection details
            if 'models_tested' in forecast.model_details:
                models_tested = forecast.model_details['models_tested']
                forecast_lines.append(f"\n**Model Selection Process:**\n")
                forecast_lines.append(f"  - Models Tested: {', '.join(models_tested) if isinstance(models_tested, list) else models_tested}")
            if 'selection_criteria' in forecast.model_details:
                criteria = forecast.model_details['selection_criteria']
                forecast_lines.append(f"  - Selection Criteria: {criteria}")
            if 'best_model_reason' in forecast.model_details:
                reason = forecast.model_details['best_model_reason']
                forecast_lines.append(f"  - Why This Model: {reason}")
        
        # Add EXPLICIT DATA DUMP section - ALL technical details in structured format
        # This is CRITICAL - the LLM MUST use these exact values
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("🚨🚨🚨 EXPLICIT DATA DUMP - USE THESE EXACT VALUES 🚨🚨🚨")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append("**⚠️ CRITICAL: The following section contains ALL technical details in a structured format.**")
        forecast_lines.append("**⚠️ YOU MUST INCLUDE EVERY SINGLE VALUE BELOW IN YOUR RESPONSE - NO EXCEPTIONS ⚠️**\n")
        
        if forecast.model_details:
            forecast_lines.append("**MODEL TECHNICAL DETAILS (EXACT VALUES - COPY THESE):**\n")
            
            # Model architecture
            if 'layers' in forecast.model_details:
                layers = forecast.model_details['layers']
                if isinstance(layers, list):
                    forecast_lines.append(f"- **Network Architecture:** {len(layers)} layers")
                    forecast_lines.append(f"- **Layers Configuration:** {layers}")
                    for i, units in enumerate(layers, 1):
                        forecast_lines.append(f"- **Layer {i} Units:** {units}")
                else:
                    forecast_lines.append(f"- **Network Architecture:** {layers} layers")
            if 'units' in forecast.model_details:
                forecast_lines.append(f"- **Hidden Units per Layer:** {forecast.model_details['units']}")
            if 'num_layers' in forecast.model_details:
                forecast_lines.append(f"- **Transformer Encoder Layers:** {forecast.model_details['num_layers']}")
            if 'num_heads' in forecast.model_details:
                forecast_lines.append(f"- **Attention Heads:** {forecast.model_details['num_heads']}")
            if 'd_model' in forecast.model_details:
                forecast_lines.append(f"- **Model Dimension:** {forecast.model_details['d_model']}")
            if 'total_parameters' in forecast.model_details:
                forecast_lines.append(f"- **Total Parameters:** {forecast.model_details['total_parameters']:,}")
            if 'input_shape' in forecast.model_details:
                forecast_lines.append(f"- **Input Shape:** {forecast.model_details['input_shape']}")
            
            # Training details
            if 'epochs_trained' in forecast.model_details:
                forecast_lines.append(f"- **Training Epochs:** {forecast.model_details['epochs_trained']}")
            if 'training_loss' in forecast.model_details:
                train_loss = forecast.model_details['training_loss']
                forecast_lines.append(f"- **Training Loss (MSE):** {train_loss:.6f}")
            if 'validation_loss' in forecast.model_details:
                val_loss = forecast.model_details['validation_loss']
                forecast_lines.append(f"- **Validation Loss (MSE):** {val_loss:.6f}")
                if 'training_loss' in forecast.model_details:
                    train_loss = forecast.model_details['training_loss']
                    if train_loss > 0:
                        overfit_ratio = val_loss / train_loss
                        forecast_lines.append(f"- **Overfitting Ratio (val/train):** {overfit_ratio:.2f}")
            
            # Hyperparameters
            if 'learning_rate' in forecast.model_details:
                forecast_lines.append(f"- **Learning Rate:** {forecast.model_details['learning_rate']:.6f}")
            if 'batch_size' in forecast.model_details:
                forecast_lines.append(f"- **Batch Size:** {forecast.model_details['batch_size']}")
            if 'optimizer' in forecast.model_details:
                forecast_lines.append(f"- **Optimizer:** {forecast.model_details['optimizer']}")
            if 'dropout' in forecast.model_details:
                forecast_lines.append(f"- **Dropout Rate:** {forecast.model_details['dropout']:.4f}")
            if 'lookback_window' in forecast.model_details:
                forecast_lines.append(f"- **Lookback Window:** {forecast.model_details['lookback_window']}")
            
            # Computational details
            if 'training_time' in forecast.model_details:
                forecast_lines.append(f"- **Training Time:** {forecast.model_details['training_time']:.2f} seconds")
            if 'data_points_used' in forecast.model_details:
                forecast_lines.append(f"- **Data Points Used:** {forecast.model_details['data_points_used']}")
            if 'train_test_split' in forecast.model_details:
                forecast_lines.append(f"- **Train/Test Split:** {forecast.model_details['train_test_split']}")
            
            # ARIMA specific
            if forecast.method.upper() == 'ARIMA' and 'model_params' in forecast.model_details:
                params = forecast.model_details['model_params']
                if isinstance(params, dict) and 'order' in params:
                    order = params['order']
                    if isinstance(order, (list, tuple)) and len(order) >= 3:
                        forecast_lines.append(f"- **ARIMA Order (p,d,q):** {order}")
                        forecast_lines.append(f"- **AR Order (p):** {order[0]}")
                        forecast_lines.append(f"- **Differencing Order (d):** {order[1]}")
                        forecast_lines.append(f"- **MA Order (q):** {order[2]}")
                if 'aic' in forecast.model_details:
                    forecast_lines.append(f"- **AIC:** {forecast.model_details['aic']:.2f}")
                if 'bic' in forecast.model_details:
                    forecast_lines.append(f"- **BIC:** {forecast.model_details['bic']:.2f}")
            
            # Prophet specific
            if forecast.method.upper() == 'PROPHET':
                if 'changepoint_count' in forecast.model_details:
                    forecast_lines.append(f"- **Changepoint Count:** {forecast.model_details['changepoint_count']}")
                if 'growth_model' in forecast.model_details:
                    forecast_lines.append(f"- **Growth Model:** {forecast.model_details['growth_model']}")
            
            # ETS specific
            if forecast.method.upper() == 'ETS':
                if 'model_type' in forecast.model_details:
                    forecast_lines.append(f"- **ETS Model Type:** {forecast.model_details['model_type']}")
                if 'smoothing_params' in forecast.model_details:
                    smoothing = forecast.model_details['smoothing_params']
                    if isinstance(smoothing, dict):
                        if 'alpha' in smoothing:
                            forecast_lines.append(f"- **Alpha (Level):** {smoothing['alpha']:.4f}")
                        if 'beta' in smoothing:
                            forecast_lines.append(f"- **Beta (Trend):** {smoothing['beta']:.4f}")
                        if 'gamma' in smoothing:
                            forecast_lines.append(f"- **Gamma (Seasonal):** {smoothing['gamma']:.4f}")
            
            # Transformer specific
            if forecast.method.upper() == 'TRANSFORMER':
                if 'dim_feedforward' in forecast.model_details:
                    forecast_lines.append(f"- **Feedforward Dimension:** {forecast.model_details['dim_feedforward']}")
            
            # Preprocessing
            if 'scaling_method' in forecast.model_details:
                forecast_lines.append(f"- **Scaling Method:** {forecast.model_details['scaling_method']}")
        
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("END OF EXPLICIT DATA DUMP")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append("**🚨 FINAL REMINDER: You MUST include ALL of the above values in your response.**")
        forecast_lines.append("**🚨 DO NOT summarize - list the EXACT numbers for each technical detail.**")
        forecast_lines.append("**🚨 If a value is shown above, you MUST mention it in your response.**\n")
        
        # Add model explanation
        model_explanation = _get_model_explanation(forecast.method)
        if model_explanation:
            forecast_lines.append("\n" + model_explanation)
        
        # Add comprehensive forecast interpretation
        forecast_lines.append(f"\n**Forecast Interpretation & Analysis:**\n")
        
        # Calculate total growth
        if len(forecast.predicted_values) >= 2:
            first_value = forecast.predicted_values[0]
            last_value = forecast.predicted_values[-1]
            total_growth = ((last_value / first_value) - 1) * 100 if first_value > 0 else 0
            forecast_lines.append(f"- **Total Growth Projection:** {total_growth:+.1f}% from {forecast.periods[0]} to {forecast.periods[-1]}\n")
        
        # Analyze forecast trajectory
        if len(forecast.predicted_values) >= 3:
            growth_rates = []
            for i in range(1, len(forecast.predicted_values)):
                prev = forecast.predicted_values[i-1]
                curr = forecast.predicted_values[i]
                if prev > 0:
                    growth_rates.append(((curr / prev) - 1) * 100)
            
            if growth_rates:
                avg_growth = sum(growth_rates) / len(growth_rates)
                if all(g > 0 for g in growth_rates):
                    forecast_lines.append(f"- **Trajectory:** Consistent positive growth (avg {avg_growth:.1f}% YoY)\n")
                elif all(g < 0 for g in growth_rates):
                    forecast_lines.append(f"- **Trajectory:** Declining trend (avg {avg_growth:.1f}% YoY)\n")
                else:
                    forecast_lines.append(f"- **Trajectory:** Mixed growth pattern (avg {avg_growth:.1f}% YoY)\n")
                
                # Check for acceleration/deceleration
                if len(growth_rates) >= 2:
                    early_avg = sum(growth_rates[:len(growth_rates)//2]) / (len(growth_rates)//2)
                    late_avg = sum(growth_rates[len(growth_rates)//2:]) / (len(growth_rates) - len(growth_rates)//2)
                    if late_avg > early_avg * 1.1:
                        forecast_lines.append(f"- **Pattern:** Accelerating growth (later years faster than early years)\n")
                    elif late_avg < early_avg * 0.9:
                        forecast_lines.append(f"- **Pattern:** Decelerating growth (later years slower than early years)\n")
        
        # Confidence interval analysis
        if forecast.confidence_intervals_low and forecast.confidence_intervals_high:
            avg_width_pct = 0
            for i in range(len(forecast.periods)):
                value = forecast.predicted_values[i]
                low = forecast.confidence_intervals_low[i]
                high = forecast.confidence_intervals_high[i]
                width_pct = ((high - low) / value) * 100 if value > 0 else 0
                avg_width_pct += width_pct
            avg_width_pct /= len(forecast.periods)
            
            if avg_width_pct < 20:
                forecast_lines.append(f"- **Uncertainty Level:** LOW (avg CI width: {avg_width_pct:.1f}% of forecast)\n")
            elif avg_width_pct < 40:
                forecast_lines.append(f"- **Uncertainty Level:** MODERATE (avg CI width: {avg_width_pct:.1f}% of forecast)\n")
            else:
                forecast_lines.append(f"- **Uncertainty Level:** HIGH (avg CI width: {avg_width_pct:.1f}% of forecast)\n")
        
        # Add comprehensive technical summary
        forecast_lines.append(f"\n**Technical Summary:**\n")
        forecast_lines.append(f"- **Forecast Method:** {forecast.method.upper()}\n")
        forecast_lines.append(f"- **Confidence Level:** {forecast.confidence:.1%}\n")
        forecast_lines.append(f"- **Forecast Horizon:** {len(forecast.periods)} years ({forecast.periods[0]} to {forecast.periods[-1]})\n")
        if forecast.model_details:
            if 'data_quality_score' in forecast.model_details:
                quality = forecast.model_details['data_quality_score']
                forecast_lines.append(f"- **Data Quality Score:** {quality:.2f}/1.00\n")
            if 'model_complexity' in forecast.model_details:
                complexity = forecast.model_details['model_complexity']
                forecast_lines.append(f"- **Model Complexity:** {complexity}\n")
            if 'forecast_reliability' in forecast.model_details:
                reliability = forecast.model_details['forecast_reliability']
                forecast_lines.append(f"- **Forecast Reliability:** {reliability}\n")
        
        # Add comprehensive summary of all details that MUST be included
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append(f"📋 COMPREHENSIVE TECHNICAL DETAILS SUMMARY - INCLUDE ALL IN YOUR RESPONSE")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append(f"**YOU MUST INCLUDE ALL OF THE FOLLOWING IN YOUR RESPONSE:**\n")
        forecast_lines.append(f"\n1. **Forecast Values & Analysis:**")
        forecast_lines.append(f"   - All forecasted values for each year")
        forecast_lines.append(f"   - Year-over-year growth rates")
        forecast_lines.append(f"   - Multi-year CAGR")
        forecast_lines.append(f"   - Confidence intervals and uncertainty analysis\n")
        
        forecast_lines.append(f"2. **Model Technical Specifications:**")
        if forecast.model_details:
            if 'model_params' in forecast.model_details:
                forecast_lines.append(f"   - ARIMA order and parameters")
            if 'num_layers' in forecast.model_details or 'layers' in forecast.model_details:
                forecast_lines.append(f"   - Network architecture (layers, units, dimensions)")
            if 'epochs_trained' in forecast.model_details:
                forecast_lines.append(f"   - Training epochs")
            if 'training_loss' in forecast.model_details:
                forecast_lines.append(f"   - Training and validation loss metrics")
            if 'hyperparameters' in forecast.model_details:
                forecast_lines.append(f"   - All hyperparameters with values and explanations")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"3. **Model Performance Metrics:**")
        if forecast.model_details:
            if 'mae' in forecast.model_details or 'rmse' in forecast.model_details:
                forecast_lines.append(f"   - MAE, RMSE, MAPE, R², directional accuracy")
            if 'cross_validation_results' in forecast.model_details:
                forecast_lines.append(f"   - Cross-validation results")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"4. **Training Process Details:**")
        if forecast.model_details:
            if 'training_time' in forecast.model_details:
                forecast_lines.append(f"   - Training time and computational details")
            if 'data_points_used' in forecast.model_details:
                forecast_lines.append(f"   - Data points used, train/test split")
            if 'preprocessing_applied' in forecast.model_details:
                forecast_lines.append(f"   - Data preprocessing steps")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"5. **Feature Engineering:**")
        if forecast.model_details:
            if 'features_used' in forecast.model_details or 'features_engineered' in forecast.model_details:
                forecast_lines.append(f"   - Features used and engineered")
            if 'feature_importance' in forecast.model_details:
                forecast_lines.append(f"   - Feature importance analysis")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"6. **Model Explainability:**")
        forecast_lines.append(f"   - How the model works (detailed explanation)")
        forecast_lines.append(f"   - Why this model was selected")
        forecast_lines.append(f"   - Model selection process")
        if forecast.model_details and 'alternative_models_performance' in forecast.model_details:
            forecast_lines.append(f"   - Comparison with alternative models")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"7. **Forecast Interpretation:**")
        forecast_lines.append(f"   - Total growth projection")
        forecast_lines.append(f"   - Trajectory analysis (accelerating/decelerating)")
        forecast_lines.append(f"   - Uncertainty level assessment")
        forecast_lines.append(f"\n")
        
        forecast_lines.append(f"**CRITICAL:** Do NOT summarize or skip any of these details. Include ALL technical information in your response.\n")
        forecast_lines.append(f"{'='*80}\n")
        
        # Final reminder with explicit checklist - MAKE THIS UNAVOIDABLE
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("🚨🚨🚨 FINAL REMINDER: THIS IS THE PRIMARY ANSWER 🚨🚨🚨")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append("**YOUR RESPONSE MUST INCLUDE ALL OF THE FOLLOWING - CHECK EACH ITEM:**\n")
        forecast_lines.append("✅ Forecast values for each year with exact numbers")
        forecast_lines.append("✅ Confidence intervals for each year")
        forecast_lines.append("✅ Year-over-year growth rates (calculated above)")
        forecast_lines.append("✅ Multi-year CAGR (calculated above)")
        forecast_lines.append("✅ Model architecture (layers, units, parameters)")
        forecast_lines.append("✅ Training details (epochs, training loss, validation loss)")
        forecast_lines.append("✅ Hyperparameters (learning rate, batch size, optimizer, dropout)")
        forecast_lines.append("✅ Performance metrics (training loss, validation loss, overfitting ratio)")
        forecast_lines.append("✅ Data preprocessing (scaling method, feature engineering, data points)")
        forecast_lines.append("✅ Computational details (training time, model size, parameters)")
        forecast_lines.append("✅ Model explainability (how LSTM/GRU works, why it's suitable)")
        forecast_lines.append("✅ Forecast interpretation (trajectory, pattern, uncertainty)")
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("**DO NOT SUMMARIZE - INCLUDE EVERY DETAIL ABOVE IN YOUR RESPONSE**")
        forecast_lines.append(f"{'='*80}\n")
        
        # Add explicit data dump section - ALL DETAILS THAT MUST BE INCLUDED
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("📋 EXPLICIT DATA DUMP - COPY THESE DETAILS INTO YOUR RESPONSE")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append("**The following details are PROVIDED BELOW - you MUST include them in your response:**\n\n")
        
        # List all available details explicitly
        if forecast.model_details:
            forecast_lines.append("**AVAILABLE MODEL DETAILS (MUST BE INCLUDED):**\n")
            
            # Model architecture
            if 'layers' in forecast.model_details:
                layers = forecast.model_details['layers']
                forecast_lines.append(f"- **Network Layers:** {layers}\n")
            if 'units' in forecast.model_details:
                units = forecast.model_details['units']
                forecast_lines.append(f"- **Hidden Units per Layer:** {units}\n")
            if 'total_parameters' in forecast.model_details:
                params = forecast.model_details['total_parameters']
                forecast_lines.append(f"- **Total Parameters:** {params:,}\n")
            if 'input_shape' in forecast.model_details:
                input_shape = forecast.model_details['input_shape']
                forecast_lines.append(f"- **Input Shape:** {input_shape}\n")
            
            # Training details
            if 'epochs_trained' in forecast.model_details:
                epochs = forecast.model_details['epochs_trained']
                forecast_lines.append(f"- **Training Epochs:** {epochs}\n")
            if 'training_loss' in forecast.model_details:
                train_loss = forecast.model_details['training_loss']
                forecast_lines.append(f"- **Training Loss (MSE):** {train_loss:.6f}\n")
            if 'validation_loss' in forecast.model_details:
                val_loss = forecast.model_details['validation_loss']
                forecast_lines.append(f"- **Validation Loss (MSE):** {val_loss:.6f}\n")
                if 'training_loss' in forecast.model_details:
                    train_loss = forecast.model_details['training_loss']
                    overfit_ratio = val_loss / train_loss if train_loss > 0 else 1.0
                    forecast_lines.append(f"- **Overfitting Ratio:** {overfit_ratio:.2f}\n")
            
            # Hyperparameters
            if 'learning_rate' in forecast.model_details:
                lr = forecast.model_details['learning_rate']
                forecast_lines.append(f"- **Learning Rate:** {lr:.6f}\n")
            if 'batch_size' in forecast.model_details:
                batch = forecast.model_details['batch_size']
                forecast_lines.append(f"- **Batch Size:** {batch}\n")
            if 'optimizer' in forecast.model_details:
                optimizer = forecast.model_details['optimizer']
                forecast_lines.append(f"- **Optimizer:** {optimizer}\n")
            if 'dropout' in forecast.model_details:
                dropout = forecast.model_details['dropout']
                forecast_lines.append(f"- **Dropout Rate:** {dropout:.2f}\n")
            if 'lookback_window' in forecast.model_details:
                window = forecast.model_details['lookback_window']
                forecast_lines.append(f"- **Lookback Window:** {window} time steps\n")
            
            # Computational details
            if 'training_time' in forecast.model_details:
                train_time = forecast.model_details['training_time']
                forecast_lines.append(f"- **Training Time:** {train_time:.2f} seconds\n")
            if 'data_points_used' in forecast.model_details:
                data_points = forecast.model_details['data_points_used']
                forecast_lines.append(f"- **Data Points Used:** {data_points} periods\n")
            if 'train_test_split' in forecast.model_details:
                split = forecast.model_details['train_test_split']
                forecast_lines.append(f"- **Train/Test Split:** {split}\n")
            
            # Preprocessing
            if 'scaling_method' in forecast.model_details:
                scaling = forecast.model_details['scaling_method']
                forecast_lines.append(f"- **Scaling Method:** {scaling}\n")
            if 'preprocessing_applied' in forecast.model_details:
                preprocessing = forecast.model_details['preprocessing_applied']
                if isinstance(preprocessing, list):
                    forecast_lines.append(f"- **Preprocessing Applied:** {', '.join(preprocessing)}\n")
        
        # Growth rates (already calculated above)
        if len(forecast.predicted_values) >= 2:
            forecast_lines.append("\n**GROWTH RATES (MUST BE INCLUDED):**\n")
            for i in range(1, len(forecast.predicted_values)):
                prev = forecast.predicted_values[i-1]
                curr = forecast.predicted_values[i]
                if prev > 0:
                    growth = ((curr / prev) - 1) * 100
                    forecast_lines.append(f"- **{forecast.periods[i-1]} to {forecast.periods[i]}:** {growth:+.2f}% YoY growth\n")
            if len(forecast.predicted_values) >= 3:
                first = forecast.predicted_values[0]
                last = forecast.predicted_values[-1]
                years = len(forecast.predicted_values) - 1
                if first > 0:
                    cagr = ((last / first) ** (1/years) - 1) * 100
                    forecast_lines.append(f"- **Multi-Year CAGR:** {cagr:.2f}%\n")
        
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("**CRITICAL: The above details are PROVIDED - you MUST include them in your response**")
        forecast_lines.append("**DO NOT say 'the model has X layers' - say 'the model has {layers} layers' with the actual number**")
        forecast_lines.append("**DO NOT say 'training loss is low' - say 'training loss is {training_loss:.6f}' with the actual value**")
        forecast_lines.append("**DO NOT summarize - include EVERY number and detail listed above**")
        forecast_lines.append(f"{'='*80}\n")
        
        # Add methodology note
        forecast_lines.append(f"\n**Methodology Note:**\n")
        forecast_lines.append(f"This forecast was generated using {forecast.method.upper()} methodology.\n")
        forecast_lines.append(f"All technical specifications, performance metrics, and model details are provided above.\n")
        forecast_lines.append(f"For detailed explanations of how the model works, see the Model Explainability section.\n")
        
        # Add one final explicit section with ALL values that MUST be included
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("🎯 FINAL CHECKLIST - COPY THESE EXACT VALUES INTO YOUR RESPONSE")
        forecast_lines.append(f"{'='*80}\n")
        forecast_lines.append("**The following values are EXACTLY what you must include in your response:**\n\n")
        
        # Forecast values
        forecast_lines.append("**FORECAST VALUES (MUST INCLUDE):**\n")
        for i, year in enumerate(forecast.periods):
            value = forecast.predicted_values[i]
            low = forecast.confidence_intervals_low[i]
            high = forecast.confidence_intervals_high[i]
            if abs(value) >= 1_000_000_000:
                value_str = f"${value / 1_000_000_000:.2f}B"
                low_str = f"${low / 1_000_000_000:.2f}B"
                high_str = f"${high / 1_000_000_000:.2f}B"
            elif abs(value) >= 1_000_000:
                value_str = f"${value / 1_000_000:.2f}M"
                low_str = f"${low / 1_000_000:.2f}M"
                high_str = f"${high / 1_000_000:.2f}M"
            else:
                value_str = f"${value:,.0f}"
                low_str = f"${low:,.0f}"
                high_str = f"${high:,.0f}"
            forecast_lines.append(f"- **{year}:** {value_str} (95% CI: {low_str} - {high_str})\n")
        
        # Growth rates
        if len(forecast.predicted_values) >= 2:
            forecast_lines.append("\n**GROWTH RATES (MUST INCLUDE):**\n")
            for i in range(1, len(forecast.predicted_values)):
                prev = forecast.predicted_values[i-1]
                curr = forecast.predicted_values[i]
                if prev > 0:
                    growth = ((curr / prev) - 1) * 100
                    forecast_lines.append(f"- **{forecast.periods[i-1]} to {forecast.periods[i]}:** {growth:+.2f}% YoY growth\n")
            if len(forecast.predicted_values) >= 3:
                first = forecast.predicted_values[0]
                last = forecast.predicted_values[-1]
                years = len(forecast.predicted_values) - 1
                if first > 0:
                    cagr = ((last / first) ** (1/years) - 1) * 100
                    forecast_lines.append(f"- **Multi-Year CAGR:** {cagr:.2f}%\n")
        
        # Model details - list ALL available values
        if forecast.model_details:
            forecast_lines.append("\n**MODEL TECHNICAL DETAILS (MUST INCLUDE):**\n")
            
            # Architecture
            if 'layers' in forecast.model_details:
                layers = forecast.model_details['layers']
                if isinstance(layers, list):
                    forecast_lines.append(f"- **Network Architecture:** {len(layers)} layers with {layers} units per layer\n")
                else:
                    forecast_lines.append(f"- **Network Architecture:** {layers} layers\n")
            if 'units' in forecast.model_details:
                units = forecast.model_details['units']
                forecast_lines.append(f"- **Hidden Units per Layer:** {units}\n")
            if 'total_parameters' in forecast.model_details:
                params = forecast.model_details['total_parameters']
                forecast_lines.append(f"- **Total Parameters:** {params:,}\n")
            if 'input_shape' in forecast.model_details:
                input_shape = forecast.model_details['input_shape']
                forecast_lines.append(f"- **Input Shape:** {input_shape}\n")
            
            # Training
            if 'epochs_trained' in forecast.model_details:
                epochs = forecast.model_details['epochs_trained']
                forecast_lines.append(f"- **Training Epochs:** {epochs}\n")
            if 'training_loss' in forecast.model_details:
                train_loss = forecast.model_details['training_loss']
                forecast_lines.append(f"- **Training Loss (MSE):** {train_loss:.6f}\n")
            if 'validation_loss' in forecast.model_details:
                val_loss = forecast.model_details['validation_loss']
                forecast_lines.append(f"- **Validation Loss (MSE):** {val_loss:.6f}\n")
                if 'training_loss' in forecast.model_details:
                    train_loss = forecast.model_details['training_loss']
                    overfit_ratio = val_loss / train_loss if train_loss > 0 else 1.0
                    forecast_lines.append(f"- **Overfitting Ratio:** {overfit_ratio:.2f}\n")
            
            # Hyperparameters
            if 'learning_rate' in forecast.model_details:
                lr = forecast.model_details['learning_rate']
                forecast_lines.append(f"- **Learning Rate:** {lr:.6f}\n")
            if 'batch_size' in forecast.model_details:
                batch = forecast.model_details['batch_size']
                forecast_lines.append(f"- **Batch Size:** {batch}\n")
            if 'optimizer' in forecast.model_details:
                optimizer = forecast.model_details['optimizer']
                forecast_lines.append(f"- **Optimizer:** {optimizer}\n")
            if 'dropout' in forecast.model_details:
                dropout = forecast.model_details['dropout']
                forecast_lines.append(f"- **Dropout Rate:** {dropout:.2f}\n")
            if 'lookback_window' in forecast.model_details:
                window = forecast.model_details['lookback_window']
                forecast_lines.append(f"- **Lookback Window:** {window} time steps\n")
            
            # Computational
            if 'training_time' in forecast.model_details:
                train_time = forecast.model_details['training_time']
                forecast_lines.append(f"- **Training Time:** {train_time:.2f} seconds\n")
            if 'data_points_used' in forecast.model_details:
                data_points = forecast.model_details['data_points_used']
                forecast_lines.append(f"- **Data Points Used:** {data_points} periods\n")
            if 'train_test_split' in forecast.model_details:
                split = forecast.model_details['train_test_split']
                forecast_lines.append(f"- **Train/Test Split:** {split}\n")
            
            # Preprocessing
            if 'scaling_method' in forecast.model_details:
                scaling = forecast.model_details['scaling_method']
                forecast_lines.append(f"- **Scaling Method:** {scaling}\n")
        
        forecast_lines.append(f"\n{'='*80}")
        forecast_lines.append("**🚨 CRITICAL: The above values are EXACT - you MUST include them in your response**")
        forecast_lines.append("**🚨 DO NOT say 'the model was trained' - say 'the model was trained for {epochs} epochs'**")
        forecast_lines.append("**🚨 DO NOT say 'training loss is low' - say 'training loss is {train_loss:.6f}'**")
        forecast_lines.append("**🚨 DO NOT say 'the model has layers' - say 'the model has {layers} layers with {units} units each'**")
        forecast_lines.append("**🚨 INCLUDE EVERY NUMBER, METRIC, AND DETAIL LISTED ABOVE - NO EXCEPTIONS**")
        forecast_lines.append(f"{'='*80}\n")
        
        forecast_lines.append(f"\n{'='*80}\n")
        
        # Extract explainability information for interactive forecasting
        explainability_data = {}
        try:
            if forecast and forecast.model_details:
                model_details = forecast.model_details
                
                # Extract forecast drivers (if available)
                drivers = {}
                if 'feature_importance' in model_details:
                    drivers['features'] = model_details['feature_importance']
                if 'component_breakdown' in model_details:
                    drivers['components'] = model_details['component_breakdown']
                if 'prophet_components' in model_details:
                    drivers['prophet'] = model_details['prophet_components']
                
                explainability_data['drivers'] = drivers
                
                # Extract model confidence and uncertainty
                explainability_data['confidence'] = forecast.confidence
                explainability_data['method'] = forecast.method
                
                # Extract parameter information
                params = {}
                if 'epochs' in model_details:
                    params['epochs'] = model_details['epochs']
                if 'learning_rate' in model_details:
                    params['learning_rate'] = model_details['learning_rate']
                if 'batch_size' in model_details:
                    params['batch_size'] = model_details['batch_size']
                if 'lookback' in model_details:
                    params['lookback'] = model_details['lookback']
                
                explainability_data['parameters'] = params
                
                # Extract performance metrics
                metrics = {}
                if 'training_loss' in model_details:
                    metrics['training_loss'] = model_details['training_loss']
                if 'validation_loss' in model_details:
                    metrics['validation_loss'] = model_details['validation_loss']
                if 'rmse' in model_details:
                    metrics['rmse'] = model_details['rmse']
                if 'mae' in model_details:
                    metrics['mae'] = model_details['mae']
                
                explainability_data['performance'] = metrics
                
                LOGGER.info(f"Extracted explainability data for {ticker} {metric}: {list(explainability_data.keys())}")
        except Exception as exp_error:
            LOGGER.warning(f"Failed to extract explainability data: {exp_error}")
            explainability_data = {}
        
        return "\n".join(forecast_lines), forecast, explainability_data
        
    except Exception as e:
        LOGGER.exception(f"Error building ML forecast context: {e}")
        return None, None, None


def _build_historical_forecast_comparison(
    ticker: str,
    metric: str,
    ts: Any,  # pd.Series
    forecast_result: Any
) -> str:
    """
    Build historical comparison context for forecast.
    
    Compares forecast to historical growth rates, CAGR, and volatility.
    """
    try:
        import numpy as np
        
        context_parts = []
        context_parts.append("\n📈 HISTORICAL CONTEXT & FORECAST COMPARISON:\n")
        
        # Calculate historical statistics
        if len(ts) >= 3:
            # Historical growth rates
            historical_values = ts.values
            recent_values = historical_values[-min(5, len(historical_values)):]
            
            # Calculate historical CAGR (3-year and 5-year if available)
            if len(historical_values) >= 4:
                cagr_3y = ((historical_values[-1] / historical_values[-4]) ** (1/3) - 1) * 100
                context_parts.append(f"- Historical 3-Year CAGR: {cagr_3y:.1f}%\n")
            
            if len(historical_values) >= 6:
                cagr_5y = ((historical_values[-1] / historical_values[-6]) ** (1/5) - 1) * 100
                context_parts.append(f"- Historical 5-Year CAGR: {cagr_5y:.1f}%\n")
            
            # Calculate historical volatility
            if len(recent_values) >= 3:
                pct_changes = np.diff(recent_values) / recent_values[:-1] * 100
                historical_volatility = np.std(pct_changes)
                context_parts.append(f"- Historical Volatility (std dev of YoY changes): {historical_volatility:.1f}%\n")
        
        # Calculate forecasted growth rates
        if len(forecast_result.predicted_values) >= 2:
            forecast_values = forecast_result.predicted_values
            last_historical = ts.values[-1]
            
            # Year-over-year growth in forecast
            forecast_growth_y1 = ((forecast_values[0] / last_historical) - 1) * 100 if last_historical > 0 else 0
            if len(forecast_values) >= 2:
                forecast_growth_y2 = ((forecast_values[1] / forecast_values[0]) - 1) * 100 if forecast_values[0] > 0 else 0
                context_parts.append(f"- Forecasted YoY Growth (Year 1): {forecast_growth_y1:.1f}%\n")
                context_parts.append(f"- Forecasted YoY Growth (Year 2): {forecast_growth_y2:.1f}%\n")
            
            # Forecast CAGR
            if len(forecast_values) >= 3:
                forecast_cagr = ((forecast_values[-1] / last_historical) ** (1/len(forecast_values)) - 1) * 100
                context_parts.append(f"- Forecasted CAGR ({len(forecast_values)}-year): {forecast_cagr:.1f}%\n")
        
        # Compare forecast to historical
        if len(historical_values) >= 4 and len(forecast_result.predicted_values) >= 3:
            cagr_3y = ((historical_values[-1] / historical_values[-4]) ** (1/3) - 1) * 100
            last_historical = ts.values[-1]
            forecast_cagr = ((forecast_result.predicted_values[-1] / last_historical) ** (1/len(forecast_result.predicted_values)) - 1) * 100
            
            if forecast_cagr > cagr_3y * 1.1:
                context_parts.append(f"- Trend: Forecast suggests ACCELERATING growth ({forecast_cagr:.1f}% vs {cagr_3y:.1f}% historical)\n")
            elif forecast_cagr < cagr_3y * 0.9:
                context_parts.append(f"- Trend: Forecast suggests DECELERATING growth ({forecast_cagr:.1f}% vs {cagr_3y:.1f}% historical)\n")
            else:
                context_parts.append(f"- Trend: Forecast suggests STABLE growth ({forecast_cagr:.1f}% vs {cagr_3y:.1f}% historical)\n")
        
        # Create comparison table
        context_parts.append("\n**Forecast vs Historical Comparison:**\n")
        context_parts.append(f"| Period | Value | Growth Rate |\n")
        context_parts.append(f"|--------|-------|-------------|\n")
        
        # Historical values
        if len(historical_values) >= 3:
            for i in range(max(0, len(historical_values) - 3), len(historical_values)):
                year = ts.index[i].year if hasattr(ts.index[i], 'year') else i
                value = historical_values[i]
                growth = ""
                if i > 0:
                    growth_pct = ((historical_values[i] / historical_values[i-1]) - 1) * 100
                    growth = f"{growth_pct:+.1f}%"
                
                if abs(value) >= 1_000_000_000:
                    value_str = f"${value / 1_000_000_000:.2f}B"
                elif abs(value) >= 1_000_000:
                    value_str = f"${value / 1_000_000:.2f}M"
                else:
                    value_str = f"${value:,.0f}"
                
                context_parts.append(f"| {year} (Historical) | {value_str} | {growth} |\n")
        
        # Forecast values
        last_historical = ts.values[-1]
        for i, forecast_value in enumerate(forecast_result.predicted_values):
            year = forecast_result.periods[i]
            growth_pct = ((forecast_value / last_historical) - 1) * 100 if i == 0 else ((forecast_value / forecast_result.predicted_values[i-1]) - 1) * 100
            last_historical = forecast_value
            
            if abs(forecast_value) >= 1_000_000_000:
                value_str = f"${forecast_value / 1_000_000_000:.2f}B"
            elif abs(forecast_value) >= 1_000_000:
                value_str = f"${forecast_value / 1_000_000:.2f}M"
            else:
                value_str = f"${forecast_value:,.0f}"
            
            context_parts.append(f"| {year} (Forecast) | {value_str} | {growth_pct:+.1f}% |\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Historical comparison context failed: {e}")
        return ""


def _build_sector_comparison_context(
    ticker: str,
    metric: str,
    forecast_result: Any,
    database_path: str
) -> str:
    """
    Build sector comparison context for forecast.
    
    Compares forecast to sector averages and peer companies.
    """
    try:
        context_parts = []
        
        # Try to get sector analytics
        try:
            from .sector_analytics import get_sector_analytics
            sector_analytics = get_sector_analytics(database_path)
            
            # Get company sector
            sector = sector_analytics.get_company_sector(ticker)
            if not sector:
                return ""
            
            # Get latest year from forecast or use current year
            latest_year = forecast_result.periods[0] if forecast_result.periods else 2024
            
            # Get sector benchmarks
            benchmarks = sector_analytics.calculate_sector_benchmarks(sector, latest_year)
            if not benchmarks:
                return ""
            
            # Get company vs sector comparison
            comparison = sector_analytics.compare_company_to_sector(ticker, latest_year)
            if not comparison:
                return ""
            
            context_parts.append(f"\n🏭 SECTOR & PEER COMPARISON:\n")
            context_parts.append(f"- Sector: {sector}\n")
            context_parts.append(f"- Sector Companies: {benchmarks.companies_count}\n")
            
            # Compare forecast to sector average
            if metric == "revenue" and benchmarks.avg_revenue > 0:
                forecast_value = forecast_result.predicted_values[0]
                sector_avg = benchmarks.avg_revenue
                vs_sector = (forecast_value / sector_avg) - 1
                
                if abs(forecast_value) >= 1_000_000_000:
                    forecast_str = f"${forecast_value / 1_000_000_000:.2f}B"
                    sector_str = f"${sector_avg / 1_000_000_000:.2f}B"
                else:
                    forecast_str = f"${forecast_value / 1_000_000:.2f}M"
                    sector_str = f"${sector_avg / 1_000_000:.2f}M"
                
                context_parts.append(f"- Forecasted {metric} ({forecast_result.periods[0]}): {forecast_str}\n")
                context_parts.append(f"- Sector Average: {sector_str}\n")
                context_parts.append(f"- vs Sector: {vs_sector:+.1%}\n")
            
            # Add percentile rank if available
            if metric in comparison.percentile_ranks:
                percentile = comparison.percentile_ranks[metric]
                context_parts.append(f"- Current Percentile Rank: {percentile:.0f}th percentile\n")
                if percentile >= 75:
                    context_parts.append(f"- Interpretation: Top quartile performer in sector\n")
                elif percentile >= 50:
                    context_parts.append(f"- Interpretation: Above median in sector\n")
                else:
                    context_parts.append(f"- Interpretation: Below median in sector\n")
            
        except ImportError:
            LOGGER.debug("Sector analytics not available")
        except Exception as e:
            LOGGER.debug(f"Sector comparison failed: {e}")
        
        if len(context_parts) > 1:
            return "".join(context_parts)
        return ""
    except Exception as e:
        LOGGER.debug(f"Sector comparison context failed: {e}")
        return ""


def _build_scenario_analysis(
    forecast_result: Any,
    ts: Optional[Any]  # Optional[pd.Series]
) -> str:
    """
    Build scenario analysis (bull/base/bear) from forecast.
    
    Uses confidence intervals to create scenarios.
    """
    try:
        context_parts = []
        context_parts.append(f"\n📊 SCENARIO ANALYSIS:\n")
        
        if not forecast_result.predicted_values or not forecast_result.confidence_intervals_low:
            return ""
        
        # Base scenario = forecast values
        # Bull scenario = upper confidence interval
        # Bear scenario = lower confidence interval
        
        context_parts.append(f"**Forecast Scenarios (based on 95% confidence intervals):**\n\n")
        context_parts.append(f"| Year | Base Scenario | Bull Scenario | Bear Scenario |\n")
        context_parts.append(f"|------|---------------|---------------|---------------|\n")
        
        for i, year in enumerate(forecast_result.periods):
            base = forecast_result.predicted_values[i]
            bear = forecast_result.confidence_intervals_low[i]
            bull = forecast_result.confidence_intervals_high[i]
            
            # Format values
            def format_val(v):
                if abs(v) >= 1_000_000_000:
                    return f"${v / 1_000_000_000:.2f}B"
                elif abs(v) >= 1_000_000:
                    return f"${v / 1_000_000:.2f}M"
                else:
                    return f"${v:,.0f}"
            
            context_parts.append(f"| {year} | {format_val(base)} | {format_val(bull)} | {format_val(bear)} |\n")
        
        # Calculate scenario spreads
        first_year_base = forecast_result.predicted_values[0]
        first_year_bull = forecast_result.confidence_intervals_high[0]
        first_year_bear = forecast_result.confidence_intervals_low[0]
        
        upside_potential = ((first_year_bull / first_year_base) - 1) * 100
        downside_risk = ((first_year_bear / first_year_base) - 1) * 100
        
        context_parts.append(f"\n**Scenario Implications:**\n")
        context_parts.append(f"- Upside Potential (Year 1): {upside_potential:+.1f}%\n")
        context_parts.append(f"- Downside Risk (Year 1): {downside_risk:.1f}%\n")
        context_parts.append(f"- Range Width: {upside_potential - downside_risk:.1f} percentage points\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Scenario analysis failed: {e}")
        return ""


def _build_risk_analysis(
    forecast_result: Any,
    ts: Optional[Any],  # Optional[pd.Series]
    ml_forecaster: Any
) -> str:
    """
    Build risk analysis for forecast.
    
    Identifies downside risks, upside opportunities, and model confidence.
    """
    try:
        context_parts = []
        context_parts.append(f"\n⚠️ RISK ANALYSIS:\n")
        
        # Model confidence assessment
        confidence = forecast_result.confidence
        if confidence >= 0.8:
            context_parts.append(f"- Model Confidence: HIGH ({confidence:.1%})\n")
        elif confidence >= 0.6:
            context_parts.append(f"- Model Confidence: MODERATE ({confidence:.1%})\n")
        else:
            context_parts.append(f"- Model Confidence: LOW ({confidence:.1%}) - Use with caution\n")
        
        # Downside risks
        if forecast_result.confidence_intervals_low:
            first_forecast = forecast_result.predicted_values[0]
            first_low = forecast_result.confidence_intervals_low[0]
            downside_pct = ((first_low / first_forecast) - 1) * 100
            
            context_parts.append(f"\n**Downside Risks:**\n")
            if abs(downside_pct) > 20:
                context_parts.append(f"- Significant downside risk: Forecast could be {abs(downside_pct):.1f}% lower\n")
            elif abs(downside_pct) > 10:
                context_parts.append(f"- Moderate downside risk: Forecast could be {abs(downside_pct):.1f}% lower\n")
            else:
                context_parts.append(f"- Limited downside risk: Forecast could be {abs(downside_pct):.1f}% lower\n")
        
        # Upside opportunities
        if forecast_result.confidence_intervals_high:
            first_forecast = forecast_result.predicted_values[0]
            first_high = forecast_result.confidence_intervals_high[0]
            upside_pct = ((first_high / first_forecast) - 1) * 100
            
            context_parts.append(f"\n**Upside Opportunities:**\n")
            if upside_pct > 20:
                context_parts.append(f"- Significant upside potential: Forecast could be {upside_pct:.1f}% higher\n")
            elif upside_pct > 10:
                context_parts.append(f"- Moderate upside potential: Forecast could be {upside_pct:.1f}% higher\n")
            else:
                context_parts.append(f"- Limited upside potential: Forecast could be {upside_pct:.1f}% higher\n")
        
        # Data quality warnings
        if ts is not None:
            if len(ts) < 10:
                context_parts.append(f"\n**Data Quality Warning:**\n")
                context_parts.append(f"- Limited historical data: Only {len(ts)} periods available\n")
                context_parts.append(f"- Forecast reliability may be reduced\n")
        
        # Confidence interval width as risk indicator
        if forecast_result.confidence_intervals_low and forecast_result.confidence_intervals_high:
            first_low = forecast_result.confidence_intervals_low[0]
            first_high = forecast_result.confidence_intervals_high[0]
            first_forecast = forecast_result.predicted_values[0]
            interval_width_pct = ((first_high - first_low) / first_forecast) * 100
            
            context_parts.append(f"\n**Forecast Uncertainty:**\n")
            context_parts.append(f"- 95% Confidence Interval Width: {interval_width_pct:.1f}% of forecast value\n")
            if interval_width_pct > 50:
                context_parts.append(f"- HIGH uncertainty: Wide confidence intervals suggest significant forecast risk\n")
            elif interval_width_pct > 30:
                context_parts.append(f"- MODERATE uncertainty: Confidence intervals indicate reasonable forecast range\n")
            else:
                context_parts.append(f"- LOW uncertainty: Narrow confidence intervals suggest reliable forecast\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Risk analysis failed: {e}")
        return ""


def _build_explainability_context(
    forecast_result: Any,
    ml_forecaster: Any,
    ts: Optional[Any]  # Optional[pd.Series]
) -> str:
    """
    Build comprehensive explainability context with detailed technical information.
    """
    try:
        context_parts = []
        context_parts.append(f"\n🔍 DETAILED MODEL EXPLAINABILITY & TECHNICAL SPECIFICATIONS:\n")
        
        method = forecast_result.method.lower()
        context_parts.append(f"**Model Architecture:** {method.upper()}\n")
        
        # Model-specific detailed explanations
        if method == "prophet":
            context_parts.append(f"\n**Prophet Model Details:**\n")
            context_parts.append(f"- **Algorithm:** Facebook Prophet - Additive time series decomposition\n")
            context_parts.append(f"- **Components:** Trend + Seasonality + Holidays + Error\n")
            context_parts.append(f"- **Mathematical Form:** y(t) = g(t) + s(t) + h(t) + ε(t)\n")
            context_parts.append(f"  where g(t) = trend, s(t) = seasonality, h(t) = holidays, ε(t) = error\n")
            
            if forecast_result.model_details:
                if 'seasonality_detected' in forecast_result.model_details:
                    seasonality = forecast_result.model_details['seasonality_detected']
                    if isinstance(seasonality, dict):
                        detected = [k for k, v in seasonality.items() if v]
                        if detected:
                            context_parts.append(f"- **Seasonality Detected:** {', '.join(detected)}\n")
                            context_parts.append(f"  - Prophet automatically detects and models seasonal patterns\n")
                            context_parts.append(f"  - Uses Fourier series to capture periodic components\n")
                if 'changepoints' in forecast_result.model_details:
                    changepoints = forecast_result.model_details['changepoints']
                    if changepoints:
                        context_parts.append(f"- **Trend Changepoints:** {len(changepoints)} detected\n")
                        context_parts.append(f"  - Changepoints allow the trend to change direction\n")
                        context_parts.append(f"  - Useful for capturing structural breaks in the data\n")
                if 'growth' in forecast_result.model_details:
                    growth = forecast_result.model_details['growth']
                    context_parts.append(f"- **Growth Model:** {growth}\n")
                if 'yearly_seasonality' in forecast_result.model_details:
                    context_parts.append(f"- **Yearly Seasonality:** {forecast_result.model_details['yearly_seasonality']}\n")
                if 'weekly_seasonality' in forecast_result.model_details:
                    context_parts.append(f"- **Weekly Seasonality:** {forecast_result.model_details['weekly_seasonality']}\n")
            
            context_parts.append(f"\n**How Prophet Works:**\n")
            context_parts.append(f"1. **Trend Component (g(t)):** Uses piecewise linear or logistic growth\n")
            context_parts.append(f"   - Automatically detects changepoints where trend changes\n")
            context_parts.append(f"   - Uses L1 regularization to control changepoint flexibility\n")
            context_parts.append(f"2. **Seasonality (s(t)):** Fourier series to model periodic patterns\n")
            context_parts.append(f"   - Captures yearly, weekly, and daily seasonality\n")
            context_parts.append(f"   - Automatically determines seasonality strength\n")
            context_parts.append(f"3. **Holidays (h(t)):** User-defined or automatically detected holidays\n")
            context_parts.append(f"4. **Forecasting:** Uses Bayesian inference with MCMC sampling\n")
            context_parts.append(f"   - Provides uncertainty estimates through posterior sampling\n")
        
        elif method == "arima":
            context_parts.append(f"\n**ARIMA Model Details:**\n")
            context_parts.append(f"- **Algorithm:** AutoRegressive Integrated Moving Average\n")
            context_parts.append(f"- **Mathematical Form:** ARIMA(p,d,q)\n")
            context_parts.append(f"  where p = AR order, d = differencing order, q = MA order\n")
            
            if forecast_result.model_details and 'model_params' in forecast_result.model_details:
                params = forecast_result.model_details['model_params']
                if 'order' in params:
                    order = params['order']
                    context_parts.append(f"- **Model Order:** ARIMA{order}\n")
                    context_parts.append(f"  - AR({order[0]}): Uses {order[0]} previous values\n")
                    context_parts.append(f"  - I({order[1]}): {order[1]} differencing step(s) for stationarity\n")
                    context_parts.append(f"  - MA({order[2]}): Uses {order[2]} previous error terms\n")
                if 'seasonal_order' in params:
                    seasonal = params['seasonal_order']
                    context_parts.append(f"- **Seasonal Order:** SARIMA{seasonal}\n")
                if 'aic' in forecast_result.model_details:
                    aic = forecast_result.model_details.get('aic', 'N/A')
                    context_parts.append(f"- **AIC (Akaike Information Criterion):** {aic:.2f}\n")
                    context_parts.append(f"  - Lower AIC indicates better model fit\n")
                    context_parts.append(f"  - Balances model complexity with goodness of fit\n")
                if 'bic' in forecast_result.model_details:
                    bic = forecast_result.model_details.get('bic', 'N/A')
                    context_parts.append(f"- **BIC (Bayesian Information Criterion):** {bic:.2f}\n")
            
            context_parts.append(f"\n**How ARIMA Works:**\n")
            context_parts.append(f"1. **AutoRegressive (AR) Component:**\n")
            context_parts.append(f"   - Uses linear combination of previous values\n")
            context_parts.append(f"   - Captures autocorrelation in the time series\n")
            context_parts.append(f"2. **Integrated (I) Component:**\n")
            context_parts.append(f"   - Differencing to make series stationary\n")
            context_parts.append(f"   - Removes trend and seasonality\n")
            context_parts.append(f"3. **Moving Average (MA) Component:**\n")
            context_parts.append(f"   - Uses linear combination of previous forecast errors\n")
            context_parts.append(f"   - Captures short-term dependencies\n")
            context_parts.append(f"4. **Model Selection:**\n")
            context_parts.append(f"   - Uses AIC/BIC to select optimal (p,d,q) parameters\n")
            context_parts.append(f"   - Tests for stationarity using ADF test\n")
        
        elif method in ["lstm", "gru"]:
            context_parts.append(f"\n**{method.upper()} Neural Network Details:**\n")
            context_parts.append(f"- **Architecture:** Recurrent Neural Network with {method.upper()} cells\n")
            
            if forecast_result.model_details:
                if 'epochs_trained' in forecast_result.model_details:
                    epochs = forecast_result.model_details['epochs_trained']
                    context_parts.append(f"- **Training Epochs:** {epochs}\n")
                    context_parts.append(f"  - Number of complete passes through the training data\n")
                if 'training_loss' in forecast_result.model_details:
                    train_loss = forecast_result.model_details['training_loss']
                    context_parts.append(f"- **Final Training Loss:** {train_loss:.6f}\n")
                    context_parts.append(f"  - Mean Squared Error (MSE) on training set\n")
                    context_parts.append(f"  - Lower values indicate better fit to training data\n")
                if 'validation_loss' in forecast_result.model_details:
                    val_loss = forecast_result.model_details['validation_loss']
                    context_parts.append(f"- **Final Validation Loss:** {val_loss:.6f}\n")
                    context_parts.append(f"  - MSE on held-out validation set\n")
                    context_parts.append(f"  - Measures generalization performance\n")
                    if 'training_loss' in forecast_result.model_details:
                        train_loss = forecast_result.model_details['training_loss']
                        overfit_ratio = val_loss / train_loss if train_loss > 0 else 1.0
                        if overfit_ratio > 1.5:
                            context_parts.append(f"  - ⚠️ Overfitting detected (val/train ratio: {overfit_ratio:.2f})\n")
                        elif overfit_ratio < 1.1:
                            context_parts.append(f"  - ✅ Good generalization (val/train ratio: {overfit_ratio:.2f})\n")
                if 'layers' in forecast_result.model_details:
                    layers = forecast_result.model_details['layers']
                    context_parts.append(f"- **Network Layers:** {layers}\n")
                if 'units' in forecast_result.model_details:
                    units = forecast_result.model_details['units']
                    context_parts.append(f"- **Hidden Units per Layer:** {units}\n")
                if 'dropout' in forecast_result.model_details:
                    dropout = forecast_result.model_details['dropout']
                    context_parts.append(f"- **Dropout Rate:** {dropout:.2f}\n")
                    context_parts.append(f"  - Regularization to prevent overfitting\n")
                if 'learning_rate' in forecast_result.model_details:
                    lr = forecast_result.model_details['learning_rate']
                    context_parts.append(f"- **Learning Rate:** {lr:.6f}\n")
                if 'batch_size' in forecast_result.model_details:
                    batch = forecast_result.model_details['batch_size']
                    context_parts.append(f"- **Batch Size:** {batch}\n")
                if 'lookback_window' in forecast_result.model_details:
                    window = forecast_result.model_details['lookback_window']
                    context_parts.append(f"- **Lookback Window:** {window} time steps\n")
                    context_parts.append(f"  - Number of historical periods used for prediction\n")
            
            context_parts.append(f"\n**How {method.upper()} Works:**\n")
            if method == "lstm":
                context_parts.append(f"1. **LSTM Cell Structure:**\n")
                context_parts.append(f"   - **Forget Gate:** Decides what information to discard\n")
                context_parts.append(f"   - **Input Gate:** Decides what new information to store\n")
                context_parts.append(f"   - **Cell State:** Long-term memory storage\n")
                context_parts.append(f"   - **Output Gate:** Decides what parts of cell state to output\n")
            else:  # GRU
                context_parts.append(f"1. **GRU Cell Structure:**\n")
                context_parts.append(f"   - **Update Gate:** Controls how much past information to keep\n")
                context_parts.append(f"   - **Reset Gate:** Controls how much past information to forget\n")
                context_parts.append(f"   - **Hidden State:** Combines past and current information\n")
            
            context_parts.append(f"2. **Training Process:**\n")
            context_parts.append(f"   - Uses backpropagation through time (BPTT)\n")
            context_parts.append(f"   - Optimizes weights using gradient descent\n")
            context_parts.append(f"   - Early stopping prevents overfitting\n")
            context_parts.append(f"3. **Forecasting:**\n")
            context_parts.append(f"   - Processes historical sequence through network\n")
            context_parts.append(f"   - Outputs prediction for next time step\n")
            context_parts.append(f"   - Can forecast multiple steps ahead iteratively\n")
        
        elif method == "transformer":
            context_parts.append(f"\n**Transformer Model Details:**\n")
            context_parts.append(f"- **Architecture:** Attention-based encoder-decoder model\n")
            
            if forecast_result.model_details:
                if 'num_layers' in forecast_result.model_details:
                    layers = forecast_result.model_details['num_layers']
                    context_parts.append(f"- **Encoder Layers:** {layers}\n")
                    context_parts.append(f"  - Each layer refines the representation\n")
                if 'num_heads' in forecast_result.model_details:
                    heads = forecast_result.model_details['num_heads']
                    context_parts.append(f"- **Attention Heads:** {heads}\n")
                    context_parts.append(f"  - Multi-head attention captures different relationships\n")
                if 'd_model' in forecast_result.model_details:
                    d_model = forecast_result.model_details['d_model']
                    context_parts.append(f"- **Model Dimension:** {d_model}\n")
                    context_parts.append(f"  - Embedding dimension for each time step\n")
                if 'dim_feedforward' in forecast_result.model_details:
                    ff_dim = forecast_result.model_details['dim_feedforward']
                    context_parts.append(f"- **Feedforward Dimension:** {ff_dim}\n")
                if 'dropout' in forecast_result.model_details:
                    dropout = forecast_result.model_details['dropout']
                    context_parts.append(f"- **Dropout Rate:** {dropout:.2f}\n")
                if 'epochs_trained' in forecast_result.model_details:
                    epochs = forecast_result.model_details['epochs_trained']
                    context_parts.append(f"- **Training Epochs:** {epochs}\n")
                if 'training_loss' in forecast_result.model_details:
                    train_loss = forecast_result.model_details['training_loss']
                    context_parts.append(f"- **Final Training Loss:** {train_loss:.6f}\n")
                if 'validation_loss' in forecast_result.model_details:
                    val_loss = forecast_result.model_details['validation_loss']
                    context_parts.append(f"- **Final Validation Loss:** {val_loss:.6f}\n")
                if 'lookback_window' in forecast_result.model_details:
                    window = forecast_result.model_details['lookback_window']
                    context_parts.append(f"- **Lookback Window:** {window} time steps\n")
            
            context_parts.append(f"\n**How Transformer Works:**\n")
            context_parts.append(f"1. **Self-Attention Mechanism:**\n")
            context_parts.append(f"   - Computes attention weights between all time steps\n")
            context_parts.append(f"   - Allows model to focus on relevant historical periods\n")
            context_parts.append(f"   - Formula: Attention(Q,K,V) = softmax(QK^T/√d_k)V\n")
            context_parts.append(f"2. **Multi-Head Attention:**\n")
            context_parts.append(f"   - Parallel attention heads capture different patterns\n")
            context_parts.append(f"   - Concatenates outputs for richer representation\n")
            context_parts.append(f"3. **Positional Encoding:**\n")
            context_parts.append(f"   - Adds position information to time steps\n")
            context_parts.append(f"   - Allows model to understand temporal order\n")
            context_parts.append(f"4. **Feedforward Networks:**\n")
            context_parts.append(f"   - Non-linear transformations between attention layers\n")
            context_parts.append(f"   - Adds model capacity for complex patterns\n")
            context_parts.append(f"5. **Layer Normalization & Residual Connections:**\n")
            context_parts.append(f"   - Stabilizes training and enables deep networks\n")
        
        elif method == "ets":
            context_parts.append(f"\n**ETS Model Details:**\n")
            context_parts.append(f"- **Algorithm:** Error, Trend, Seasonality (Exponential Smoothing)\n")
            context_parts.append(f"- **Components:** Error (E), Trend (T), Seasonality (S)\n")
            
            if forecast_result.model_details:
                if 'model_params' in forecast_result.model_details:
                    params = forecast_result.model_details['model_params']
                    if 'model' in params:
                        context_parts.append(f"- **ETS Model Type:** {params['model']}\n")
                        context_parts.append(f"  - Letters indicate presence of Error, Trend, Seasonality\n")
                    if 'alpha' in params:
                        context_parts.append(f"- **Alpha (Level Smoothing):** {params['alpha']:.4f}\n")
                    if 'beta' in params:
                        context_parts.append(f"- **Beta (Trend Smoothing):** {params['beta']:.4f}\n")
                    if 'gamma' in params:
                        context_parts.append(f"- **Gamma (Seasonal Smoothing):** {params['gamma']:.4f}\n")
            
            context_parts.append(f"\n**How ETS Works:**\n")
            context_parts.append(f"1. **Exponential Smoothing:**\n")
            context_parts.append(f"   - Gives more weight to recent observations\n")
            context_parts.append(f"   - Smoothing parameters control decay rate\n")
            context_parts.append(f"2. **State Space Model:**\n")
            context_parts.append(f"   - Models level, trend, and seasonal components\n")
            context_parts.append(f"   - Uses maximum likelihood estimation\n")
            context_parts.append(f"3. **Automatic Model Selection:**\n")
            context_parts.append(f"   - Tests all ETS model variants\n")
            context_parts.append(f"   - Selects best model using AIC\n")
        
        elif method == "ensemble":
            context_parts.append(f"\n**Ensemble Model Details:**\n")
            context_parts.append(f"- **Method:** Weighted combination of multiple models\n")
            
            if forecast_result.model_details and 'models_used' in forecast_result.model_details:
                models = forecast_result.model_details['models_used']
                context_parts.append(f"- **Models Combined:** {', '.join(models)}\n")
                context_parts.append(f"  - {len(models)} different forecasting models\n")
                
                if 'weights' in forecast_result.model_details:
                    weights = forecast_result.model_details['weights']
                    context_parts.append(f"\n**Model Weights (Contribution to Final Forecast):**\n")
                    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
                    for model_name, weight in sorted_weights:
                        context_parts.append(f"  - {model_name.upper()}: {weight:.1%} (contributes {weight:.1%} to final prediction)\n")
                
                if 'ensemble_method' in forecast_result.model_details:
                    ensemble_method = forecast_result.model_details['ensemble_method']
                    context_parts.append(f"- **Ensemble Method:** {ensemble_method}\n")
                    if ensemble_method == "weighted":
                        context_parts.append(f"  - Weights based on model confidence scores\n")
                    elif ensemble_method == "performance":
                        context_parts.append(f"  - Weights based on validation performance (RMSE/MAE)\n")
                    elif ensemble_method == "equal":
                        context_parts.append(f"  - Equal weights for all models\n")
            
            context_parts.append(f"\n**How Ensemble Works:**\n")
            context_parts.append(f"1. **Model Diversity:**\n")
            context_parts.append(f"   - Combines different model types (statistical + ML)\n")
            context_parts.append(f"   - Each model captures different patterns\n")
            context_parts.append(f"2. **Weighted Averaging:**\n")
            context_parts.append(f"   - Final forecast = Σ(weight_i × forecast_i)\n")
            context_parts.append(f"   - Better models get higher weights\n")
            context_parts.append(f"3. **Benefits:**\n")
            context_parts.append(f"   - Reduces individual model errors\n")
            context_parts.append(f"   - More robust and reliable predictions\n")
            context_parts.append(f"   - Better handles different data patterns\n")
        
        # Model selection rationale
        if forecast_result.model_details and 'ensemble_method' not in forecast_result.model_details:
            context_parts.append(f"\n**Model Selection Rationale:**\n")
            context_parts.append(f"- **Selection Method:** Cross-validation performance\n")
            context_parts.append(f"- **Evaluation Metrics:** MAE, RMSE, MAPE\n")
            context_parts.append(f"- **Why This Model:** Best suited for this data pattern and forecast horizon\n")
            if ts is not None:
                data_length = len(ts)
                if data_length < 10:
                    context_parts.append(f"- **Data Consideration:** Limited data ({data_length} periods) - simpler models preferred\n")
                else:
                    context_parts.append(f"- **Data Consideration:** Sufficient data ({data_length} periods) - complex models viable\n")
        
        # Feature engineering details (if available)
        if forecast_result.model_details and 'features_used' in forecast_result.model_details:
            features = forecast_result.model_details['features_used']
            context_parts.append(f"\n**Feature Engineering Details:**\n")
            if isinstance(features, list):
                context_parts.append(f"- **Total Features:** {len(features)}\n")
                context_parts.append(f"- **Features Used:** {', '.join(features[:10])}\n")
                if len(features) > 10:
                    context_parts.append(f"- **Additional Features:** {len(features) - 10} more features\n")
            elif isinstance(features, dict):
                for feature_type, feature_list in features.items():
                    if isinstance(feature_list, list):
                        context_parts.append(f"- **{feature_type}:** {len(feature_list)} features\n")
                    else:
                        context_parts.append(f"- **{feature_type}:** {feature_list}\n")
            context_parts.append(f"  - Engineered features improve model performance\n")
            context_parts.append(f"  - Features capture temporal patterns, trends, and seasonality\n")
        
        # Feature importance (if available)
        if forecast_result.model_details and 'feature_importance' in forecast_result.model_details:
            importance = forecast_result.model_details['feature_importance']
            if isinstance(importance, dict):
                context_parts.append(f"\n**Feature Importance Analysis:**\n")
                sorted_features = sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True)
                context_parts.append(f"- **Top Contributing Features:**\n")
                for feature, score in sorted_features[:5]:
                    context_parts.append(f"  - {feature}: {score:.4f} (contributes {abs(score)*100:.1f}% to forecast)\n")
        
        # Hyperparameter details (if available)
        if forecast_result.model_details and 'hyperparameters' in forecast_result.model_details:
            hyperparams = forecast_result.model_details['hyperparameters']
            context_parts.append(f"\n**Hyperparameter Configuration:**\n")
            if isinstance(hyperparams, dict):
                for param, value in hyperparams.items():
                    context_parts.append(f"- **{param}:** {value}\n")
                    # Add explanations for common hyperparameters
                    if param == 'learning_rate':
                        context_parts.append(f"  - Controls step size in gradient descent (lower = more stable, slower)\n")
                    elif param == 'dropout':
                        context_parts.append(f"  - Regularization to prevent overfitting (0-1, higher = more regularization)\n")
                    elif param == 'batch_size':
                        context_parts.append(f"  - Number of samples per training iteration (affects memory and speed)\n")
                    elif param == 'epochs':
                        context_parts.append(f"  - Number of complete passes through training data\n")
        
        # Model performance comparison (if available)
        if forecast_result.model_details and 'alternative_models_performance' in forecast_result.model_details:
            alt_models = forecast_result.model_details['alternative_models_performance']
            context_parts.append(f"\n**Model Performance Comparison:**\n")
            if isinstance(alt_models, dict):
                sorted_models = sorted(alt_models.items(), key=lambda x: x[1].get('rmse', float('inf')) if isinstance(x[1], dict) else float('inf'))
                context_parts.append(f"- **Models Tested and Their Performance:**\n")
                for model_name, metrics in sorted_models:
                    if isinstance(metrics, dict):
                        rmse = metrics.get('rmse', 'N/A')
                        mae = metrics.get('mae', 'N/A')
                        context_parts.append(f"  - {model_name.upper()}: RMSE={rmse}, MAE={mae}\n")
                    else:
                        context_parts.append(f"  - {model_name.upper()}: {metrics}\n")
                context_parts.append(f"- **Selected Model:** {method.upper()} (best performance)\n")
        
        # Cross-validation results (if available)
        if forecast_result.model_details and 'cross_validation_results' in forecast_result.model_details:
            cv_results = forecast_result.model_details['cross_validation_results']
            context_parts.append(f"\n**Cross-Validation Results:**\n")
            if isinstance(cv_results, dict):
                if 'mean_rmse' in cv_results:
                    context_parts.append(f"- **Mean RMSE:** {cv_results['mean_rmse']:.2f}\n")
                if 'std_rmse' in cv_results:
                    context_parts.append(f"- **Std RMSE:** {cv_results['std_rmse']:.2f}\n")
                if 'mean_mae' in cv_results:
                    context_parts.append(f"- **Mean MAE:** {cv_results['mean_mae']:.2f}\n")
                if 'folds' in cv_results:
                    context_parts.append(f"- **Number of Folds:** {cv_results['folds']}\n")
                context_parts.append(f"  - Cross-validation ensures model generalizes well to unseen data\n")
        
        # Training convergence details (if available)
        if forecast_result.model_details and 'training_convergence' in forecast_result.model_details:
            convergence = forecast_result.model_details['training_convergence']
            context_parts.append(f"\n**Training Convergence:**\n")
            if isinstance(convergence, dict):
                if 'converged' in convergence:
                    context_parts.append(f"- **Converged:** {convergence['converged']}\n")
                if 'iterations_to_convergence' in convergence:
                    context_parts.append(f"- **Iterations to Convergence:** {convergence['iterations_to_convergence']}\n")
                if 'final_loss' in convergence:
                    context_parts.append(f"- **Final Loss:** {convergence['final_loss']:.6f}\n")
        
        # Computational details
        if forecast_result.model_details:
            if 'training_time' in forecast_result.model_details:
                train_time = forecast_result.model_details['training_time']
                context_parts.append(f"\n**Computational Details:**\n")
                context_parts.append(f"- **Training Time:** {train_time:.2f} seconds\n")
            if 'prediction_time' in forecast_result.model_details:
                pred_time = forecast_result.model_details['prediction_time']
                context_parts.append(f"- **Prediction Time:** {pred_time:.4f} seconds\n")
            if 'model_size' in forecast_result.model_details:
                model_size = forecast_result.model_details['model_size']
                context_parts.append(f"- **Model Size:** {model_size}\n")
            if 'parameters_count' in forecast_result.model_details:
                params = forecast_result.model_details['parameters_count']
                context_parts.append(f"- **Total Parameters:** {params:,}\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Explainability context failed: {e}")
        return ""


def _build_uncertainty_context(
    forecast_result: Any,
    ml_forecaster: Any,
    ts: Optional[Any]  # Optional[pd.Series]
) -> str:
    """
    Build enhanced uncertainty quantification context.
    """
    try:
        context_parts = []
        
        if not ml_forecaster.uncertainty_quantifier:
            return ""
        
        try:
            # Calculate residuals from historical data if available
            residuals = None
            if ts is not None and len(ts) >= 3:
                try:
                    import numpy as np
                    # Simple residual calculation: use historical volatility as proxy
                    historical_values = ts.values
                    if len(historical_values) >= 3:
                        pct_changes = np.diff(historical_values) / historical_values[:-1]
                        residuals = (pct_changes - np.mean(pct_changes)).tolist()
                except Exception:
                    pass
            
            uncertainty_metrics = ml_forecaster.uncertainty_quantifier.calculate_uncertainty_metrics(
                forecast_result.predicted_values,
                residuals=residuals,
                ensemble_predictions=None
            )
            
            context_parts.append(f"\n📈 UNCERTAINTY QUANTIFICATION:\n")
            context_parts.append(f"- Uncertainty Score: {uncertainty_metrics.uncertainty_score:.2f} (0=low, 1=high)\n")
            
            if uncertainty_metrics.forecast_distribution:
                mean_val = uncertainty_metrics.forecast_distribution.get('mean')
                std_val = uncertainty_metrics.forecast_distribution.get('std')
                if mean_val is not None:
                    context_parts.append(f"- Forecast Distribution Mean: {mean_val:.2f}\n")
                if std_val is not None:
                    context_parts.append(f"- Forecast Distribution Std: {std_val:.2f}\n")
                    if mean_val and mean_val > 0:
                        cv = (std_val / mean_val) * 100
                        context_parts.append(f"- Coefficient of Variation: {cv:.1f}% (measure of relative uncertainty)\n")
            
            # Multiple confidence levels
            if uncertainty_metrics.prediction_intervals:
                context_parts.append(f"\n**Prediction Intervals (Multiple Confidence Levels):**\n")
                for level, intervals in uncertainty_metrics.prediction_intervals.items():
                    if 'low' in intervals and 'high' in intervals and intervals['low'] and intervals['high']:
                        first_low = intervals['low'][0]
                        first_high = intervals['high'][0]
                        first_forecast = forecast_result.predicted_values[0]
                        
                        if abs(first_forecast) >= 1_000_000_000:
                            low_str = f"${first_low / 1_000_000_000:.2f}B"
                            high_str = f"${first_high / 1_000_000_000:.2f}B"
                        elif abs(first_forecast) >= 1_000_000:
                            low_str = f"${first_low / 1_000_000:.2f}M"
                            high_str = f"${first_high / 1_000_000:.2f}M"
                        else:
                            low_str = f"${first_low:,.0f}"
                            high_str = f"${first_high:,.0f}"
                        
                        context_parts.append(f"- {float(level)*100:.0f}% Confidence: {low_str} - {high_str}\n")
        
        except Exception as e:
            LOGGER.debug(f"Uncertainty metrics calculation failed: {e}")
            # Fallback to basic confidence intervals
            if forecast_result.confidence_intervals_low and forecast_result.confidence_intervals_high:
                context_parts.append(f"\n📈 UNCERTAINTY QUANTIFICATION:\n")
                context_parts.append(f"- 95% Confidence Interval: Provided\n")
                first_low = forecast_result.confidence_intervals_low[0]
                first_high = forecast_result.confidence_intervals_high[0]
                first_forecast = forecast_result.predicted_values[0]
                
                if abs(first_forecast) >= 1_000_000_000:
                    low_str = f"${first_low / 1_000_000_000:.2f}B"
                    high_str = f"${first_high / 1_000_000_000:.2f}B"
                elif abs(first_forecast) >= 1_000_000:
                    low_str = f"${first_low / 1_000_000:.2f}M"
                    high_str = f"${first_high / 1_000_000:.2f}M"
                else:
                    low_str = f"${first_low:,.0f}"
                    high_str = f"${first_high:,.0f}"
                
                context_parts.append(f"- Year 1 Range: {low_str} - {high_str}\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Uncertainty context failed: {e}")
        return ""


def _build_actionable_insights(
    ticker: str,
    metric: str,
    forecast_result: Any,
    ts: Any,  # pd.Series
    database_path: str
) -> str:
    """
    Build actionable insights and recommendations from forecast.
    """
    try:
        context_parts = []
        context_parts.append(f"\n💡 ACTIONABLE INSIGHTS & RECOMMENDATIONS:\n")
        
        # Forecast interpretation
        if len(forecast_result.predicted_values) >= 2:
            first_forecast = forecast_result.predicted_values[0]
            last_forecast = forecast_result.predicted_values[-1]
            last_historical = ts.values[-1]
            
            # Growth interpretation
            forecast_growth = ((first_forecast / last_historical) - 1) * 100 if last_historical > 0 else 0
            multi_year_growth = ((last_forecast / last_historical) ** (1/len(forecast_result.predicted_values)) - 1) * 100 if last_historical > 0 else 0
            
            context_parts.append(f"**Forecast Interpretation:**\n")
            if forecast_growth > 15:
                context_parts.append(f"- Strong growth trajectory: {forecast_growth:.1f}% growth in Year 1 suggests robust expansion\n")
            elif forecast_growth > 5:
                context_parts.append(f"- Moderate growth trajectory: {forecast_growth:.1f}% growth in Year 1 suggests steady expansion\n")
            elif forecast_growth > 0:
                context_parts.append(f"- Slow growth trajectory: {forecast_growth:.1f}% growth in Year 1 suggests modest expansion\n")
            else:
                context_parts.append(f"- Declining trajectory: {forecast_growth:.1f}% change in Year 1 suggests contraction risk\n")
            
            if multi_year_growth > 10:
                context_parts.append(f"- Multi-year outlook: {multi_year_growth:.1f}% CAGR indicates strong long-term potential\n")
            elif multi_year_growth > 5:
                context_parts.append(f"- Multi-year outlook: {multi_year_growth:.1f}% CAGR indicates stable long-term growth\n")
            else:
                context_parts.append(f"- Multi-year outlook: {multi_year_growth:.1f}% CAGR indicates modest long-term growth\n")
        
        # Key metrics to monitor
        context_parts.append(f"\n**Key Metrics to Monitor:**\n")
        if metric == "revenue":
            context_parts.append(f"- Revenue growth rate vs forecast\n")
            context_parts.append(f"- Market share trends in key segments\n")
            context_parts.append(f"- Customer acquisition and retention rates\n")
        elif metric == "net_income" or metric == "earnings":
            context_parts.append(f"- Profit margin trends\n")
            context_parts.append(f"- Operating leverage impact\n")
            context_parts.append(f"- Tax rate changes\n")
        elif "cash" in metric.lower():
            context_parts.append(f"- Operating cash flow generation\n")
            context_parts.append(f"- Capital expenditure trends\n")
            context_parts.append(f"- Working capital management\n")
        
        # Potential red flags
        context_parts.append(f"\n**Potential Red Flags:**\n")
        if forecast_result.confidence < 0.6:
            context_parts.append(f"- ⚠️ Low model confidence ({forecast_result.confidence:.1%}) - forecast may be unreliable\n")
        if ts is not None and len(ts) < 10:
            context_parts.append(f"- ⚠️ Limited historical data ({len(ts)} periods) - forecast based on minimal information\n")
        if forecast_result.confidence_intervals_low and forecast_result.confidence_intervals_high:
            first_low = forecast_result.confidence_intervals_low[0]
            first_high = forecast_result.confidence_intervals_high[0]
            first_forecast = forecast_result.predicted_values[0]
            interval_width = ((first_high - first_low) / first_forecast) * 100
            if interval_width > 50:
                context_parts.append(f"- ⚠️ Wide confidence intervals ({interval_width:.1f}%) - high forecast uncertainty\n")
        
        # Strategic implications
        context_parts.append(f"\n**Strategic Implications:**\n")
        if len(forecast_result.predicted_values) >= 3:
            first_forecast = forecast_result.predicted_values[0]
            last_forecast = forecast_result.predicted_values[-1]
            last_historical = ts.values[-1]
            total_growth = ((last_forecast / last_historical) - 1) * 100 if last_historical > 0 else 0
            
            if total_growth > 30:
                context_parts.append(f"- Strong growth outlook suggests potential for market expansion and investment opportunities\n")
            elif total_growth > 15:
                context_parts.append(f"- Solid growth outlook supports continued investment in core business areas\n")
            elif total_growth > 0:
                context_parts.append(f"- Modest growth outlook suggests focus on operational efficiency and cost management\n")
            else:
                context_parts.append(f"- Declining outlook suggests need for strategic repositioning or cost restructuring\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Actionable insights failed: {e}")
        return ""


def _build_model_confidence_context(
    forecast_result: Any,
    ts: Optional[Any]  # Optional[pd.Series]
) -> str:
    """
    Build model confidence and limitations context.
    """
    try:
        context_parts = []
        context_parts.append(f"\n📋 MODEL CONFIDENCE & LIMITATIONS:\n")
        
        # Model confidence explanation
        confidence = forecast_result.confidence
        context_parts.append(f"- Overall Confidence: {confidence:.1%}\n")
        if confidence >= 0.8:
            context_parts.append(f"- Confidence Level: HIGH - Forecast is highly reliable\n")
        elif confidence >= 0.6:
            context_parts.append(f"- Confidence Level: MODERATE - Forecast is reasonably reliable\n")
        else:
            context_parts.append(f"- Confidence Level: LOW - Forecast should be used with caution\n")
        
        # Data limitations
        if ts is not None:
            context_parts.append(f"\n**Data Foundation:**\n")
            context_parts.append(f"- Historical Data Points: {len(ts)} periods\n")
            if len(ts) >= 10:
                context_parts.append(f"- Data Quality: EXCELLENT - Sufficient data for reliable forecasting\n")
            elif len(ts) >= 5:
                context_parts.append(f"- Data Quality: GOOD - Adequate data for reasonable forecasting\n")
            else:
                context_parts.append(f"- Data Quality: LIMITED - Insufficient data may reduce forecast reliability\n")
            
            # Data recency
            if hasattr(ts.index[-1], 'year'):
                latest_year = ts.index[-1].year
                current_year = 2024  # Could be dynamic
                years_since_latest = current_year - latest_year
                if years_since_latest <= 1:
                    context_parts.append(f"- Data Recency: CURRENT - Latest data from {latest_year}\n")
                elif years_since_latest <= 2:
                    context_parts.append(f"- Data Recency: RECENT - Latest data from {latest_year}\n")
                else:
                    context_parts.append(f"- Data Recency: OUTDATED - Latest data from {latest_year} (may affect forecast accuracy)\n")
        
        # Model assumptions
        method = forecast_result.method.lower()
        context_parts.append(f"\n**Model Assumptions:**\n")
        if method in ["arima", "prophet", "ets"]:
            context_parts.append(f"- Assumes historical patterns will continue\n")
            context_parts.append(f"- Does not account for structural breaks or regime changes\n")
        elif method in ["lstm", "gru", "transformer"]:
            context_parts.append(f"- Assumes learned patterns from training data generalize to future\n")
            context_parts.append(f"- May not capture black swan events or structural changes\n")
        
        # When to trust/doubt
        context_parts.append(f"\n**When to Trust This Forecast:**\n")
        if confidence >= 0.7 and ts and len(ts) >= 10:
            context_parts.append(f"- ✅ High confidence with sufficient historical data\n")
            context_parts.append(f"- ✅ Suitable for strategic planning and investment decisions\n")
        
        context_parts.append(f"\n**When to Use Caution:**\n")
        if confidence < 0.6:
            context_parts.append(f"- ⚠️ Low confidence score - consider alternative scenarios\n")
        if ts and len(ts) < 5:
            context_parts.append(f"- ⚠️ Limited historical data - forecast may not capture long-term patterns\n")
        if forecast_result.confidence_intervals_low and forecast_result.confidence_intervals_high:
            first_low = forecast_result.confidence_intervals_low[0]
            first_high = forecast_result.confidence_intervals_high[0]
            first_forecast = forecast_result.predicted_values[0]
            interval_width = ((first_high - first_low) / first_forecast) * 100
            if interval_width > 40:
                context_parts.append(f"- ⚠️ Wide confidence intervals - significant uncertainty in forecast\n")
        
        return "".join(context_parts)
    except Exception as e:
        LOGGER.debug(f"Model confidence context failed: {e}")
        return ""


def _build_enhanced_forecast_context(
    ticker: str,
    metric: str,
    forecast_result: Any,
    ml_forecaster: Any,
    database_path: str,
    analytics_engine: Optional["AnalyticsEngine"] = None
) -> str:
    """
    Build enhanced forecast context with explainability, regime info, uncertainty,
    historical comparisons, sector analysis, scenarios, and actionable insights.
    
    Args:
        ticker: Company ticker
        metric: Metric name
        forecast_result: MLForecast result
        ml_forecaster: MLForecaster instance
        database_path: Path to database
        analytics_engine: Optional analytics engine for historical data
        
    Returns:
        Enhanced context string
    """
    try:
        context_parts = []
        
        # Get historical data for analysis
        try:
            import pandas as pd
            records = ml_forecaster._fetch_metric_records(ticker, metric)
            ts = None
            if records:
                df = pd.DataFrame(records)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                else:
                    df['date'] = pd.to_datetime(df['period'], errors='coerce')
                df = df.dropna(subset=['date'])
                df = df.sort_values('date')
                ts = pd.Series(data=df['value'].values, index=df['date'], name=f"{ticker}_{metric}")
        except Exception as e:
            LOGGER.debug(f"Failed to get historical data: {e}")
            ts = None
        
        # === 1. HISTORICAL CONTEXT & COMPARISONS ===
        if ts is not None and len(ts) > 1 and forecast_result:
            try:
                historical_context = _build_historical_forecast_comparison(
                    ticker, metric, ts, forecast_result
                )
                if historical_context:
                    context_parts.append(historical_context)
            except Exception as e:
                LOGGER.debug(f"Historical comparison failed: {e}")
        
        # === 2. PEER & SECTOR COMPARISONS ===
        try:
            sector_context = _build_sector_comparison_context(
                ticker, metric, forecast_result, database_path
            )
            if sector_context:
                context_parts.append(sector_context)
        except Exception as e:
            LOGGER.debug(f"Sector comparison failed: {e}")
        
        # === 3. REGIME DETECTION ===
        if ts is not None and ml_forecaster.regime_detector:
            try:
                regime_info = ml_forecaster.regime_detector.detect_regime_simple(ts)
                context_parts.append(f"\n📊 MARKET REGIME DETECTION:\n")
                context_parts.append(f"- Current Regime: {regime_info.regime_type.upper()}\n")
                context_parts.append(f"- Confidence: {regime_info.confidence:.1%}\n")
                if regime_info.change_points:
                    context_parts.append(f"- Recent Change Points: {len(regime_info.change_points)} detected\n")
                # Add regime implications for forecast
                if regime_info.regime_type == "bull":
                    context_parts.append(f"- Forecast Context: Bull market conditions may support higher growth\n")
                elif regime_info.regime_type == "bear":
                    context_parts.append(f"- Forecast Context: Bear market conditions suggest caution\n")
                elif regime_info.regime_type == "volatile":
                    context_parts.append(f"- Forecast Context: High volatility increases forecast uncertainty\n")
            except Exception as e:
                LOGGER.debug(f"Regime detection failed: {e}")
                
        # === 4. SCENARIO ANALYSIS (BULL/BASE/BEAR) ===
        if forecast_result:
            try:
                scenario_context = _build_scenario_analysis(
                    forecast_result, ts
                )
                if scenario_context:
                    context_parts.append(scenario_context)
            except Exception as e:
                LOGGER.debug(f"Scenario analysis failed: {e}")
        
        # === 5. RISK ANALYSIS ===
        if forecast_result:
            try:
                risk_context = _build_risk_analysis(
                    forecast_result, ts, ml_forecaster
                )
                if risk_context:
                    context_parts.append(risk_context)
            except Exception as e:
                LOGGER.debug(f"Risk analysis failed: {e}")
        
        # === 6. EXPLAINABILITY (Enhanced with SHAP and Attention Weights) ===
        if ml_forecaster.model_explainer and forecast_result:
            try:
                explainability_context = _build_explainability_context(
                    forecast_result, ml_forecaster, ts
                )
                if explainability_context:
                    context_parts.append(explainability_context)
            except Exception as e:
                LOGGER.debug(f"Explainability analysis failed: {e}")
        
        # Add SHAP values and attention weights if available
        if forecast_result:
            try:
                from .ml_forecasting.explainability import ModelExplainer
                explainer = ModelExplainer()
                
                method = forecast_result.method.lower()
                
                # Get explainability results based on model type
                if method == 'transformer':
                    # Get attention weights from model_details if available
                    attention_weights = None
                    if hasattr(forecast_result, 'model_details') and isinstance(forecast_result.model_details, dict):
                        attention_weights = forecast_result.model_details.get('attention_weights')
                    
                    if attention_weights:
                        explain_result = explainer.explain_transformer(
                            model=None,  # Model not needed if attention_weights provided
                            attention_weights=attention_weights
                        )
                        
                        if explain_result and explain_result.attention_weights:
                            context_parts.append(f"\n**🔍 ATTENTION WEIGHTS ANALYSIS:**\n")
                            context_parts.append(f"- **Attention Mechanism:** Shows which historical time steps the model focuses on\n")
                            context_parts.append(f"- **Attention Weights Available:** {len(explain_result.attention_weights)} time steps analyzed\n")
                            
                            # Show top attended time steps
                            if explain_result.feature_importance:
                                sorted_attention = sorted(
                                    explain_result.feature_importance.items(),
                                    key=lambda x: x[1],
                                    reverse=True
                                )[:5]
                                context_parts.append(f"- **Top Attended Time Steps:**\n")
                                for time_step, importance in sorted_attention:
                                    context_parts.append(f"  - {time_step}: {importance:.4f} (model focuses {importance*100:.1f}% attention here)\n")
                
                elif method in ['lstm', 'gru']:
                    # For LSTM/GRU, note that SHAP can be computed
                    context_parts.append(f"\n**🔍 FEATURE IMPORTANCE (SHAP Available):**\n")
                    context_parts.append(f"- **SHAP Values:** Can be computed to show feature importance\n")
                    context_parts.append(f"- **Method:** DeepExplainer for neural networks\n")
                    context_parts.append(f"- **Note:** SHAP computation requires model and input data\n")
                    context_parts.append(f"- **Use Case:** Shows which features (time steps, engineered features) contribute most to forecast\n")
                    
            except Exception as e:
                LOGGER.debug(f"Enhanced explainability (SHAP/attention) failed: {e}")
        
        # === 7. UNCERTAINTY QUANTIFICATION ===
        if ml_forecaster.uncertainty_quantifier and forecast_result:
            try:
                uncertainty_context = _build_uncertainty_context(
                    forecast_result, ml_forecaster, ts
                )
                if uncertainty_context:
                    context_parts.append(uncertainty_context)
            except Exception as e:
                LOGGER.debug(f"Uncertainty quantification failed: {e}")
        
        # === 8. ACTIONABLE INSIGHTS ===
        if forecast_result and ts is not None:
            try:
                insights_context = _build_actionable_insights(
                    ticker, metric, forecast_result, ts, database_path
                )
                if insights_context:
                    context_parts.append(insights_context)
            except Exception as e:
                LOGGER.debug(f"Actionable insights failed: {e}")
        
        # === 9. MODEL CONFIDENCE & LIMITATIONS ===
        if forecast_result:
            try:
                confidence_context = _build_model_confidence_context(
                    forecast_result, ts
                )
                if confidence_context:
                    context_parts.append(confidence_context)
            except Exception as e:
                LOGGER.debug(f"Model confidence context failed: {e}")
        
        if context_parts:
            return "\n".join(context_parts)
        return ""
        
    except Exception as e:
        LOGGER.debug(f"Error building enhanced forecast context: {e}")
        return ""


def build_financial_context(
    query: str,
    analytics_engine: "AnalyticsEngine",
    database_path: str,
    max_tickers: int = 3
) -> str:
    """
    Build comprehensive financial context with SEC filing sources for LLM.
    
    Args:
        query: User's question
        analytics_engine: Analytics engine instance
        database_path: Path to database
        max_tickers: Maximum tickers to include in context
        
    Returns:
        Formatted financial context as natural language text with source citations
    """
    try:
        # Check if this is a forecasting query FIRST - forecasting queries need special handling
        is_forecasting = _is_forecasting_query(query)
        
        # Parse query to extract tickers and metrics
        structured = parse_to_structured(query)
        tickers = [t["ticker"] for t in structured.get("tickers", [])][:max_tickers]
        
        # For forecasting queries, if no tickers were extracted, try to extract manually
        # This handles cases like "Forecast Apple revenue using LSTM" where ticker might not be parsed
        if is_forecasting and not tickers:
            # Try to extract ticker from query using comprehensive regex patterns
            import re
            # Enhanced company name patterns for forecasting queries
            company_patterns = [
                # Pattern 1: "Forecast Apple revenue using LSTM" or "Forecast Apple's revenue"
                r'\b(?:forecast|predict|estimate|project)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)',
                # Pattern 2: "Forecast revenue for Apple" or "Forecast revenue of Apple"
                r'\b(?:forecast|predict|estimate|project)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                # Pattern 3: "Apple's revenue forecast" or "Apple revenue forecast"
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate)',
                # Pattern 4: "What's the revenue forecast for Apple?" - FIXED: Added case-insensitive flag handling
                r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate|projection)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                # Pattern 5: "What's Apple's revenue forecast?"
                r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate)',
                # Pattern 6: "Predict Apple revenue" (simple)
                r'\b(?:forecast|predict|estimate|project)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:revenue|sales|income|earnings)',
                # Pattern 7: "Forecast revenue Apple" (verb-object-subject)
                r'\b(?:forecast|predict|estimate|project)\s+(?:revenue|sales|income|earnings)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip()
                    LOGGER.info(f"Pattern matched for forecasting query: extracted company name '{company_name}' from query: {query}")
                    # Try to resolve company name to ticker
                    try:
                        from .parsing.alias_builder import resolve_tickers_freeform
                        ticker_matches, _ = resolve_tickers_freeform(company_name)
                        if ticker_matches and len(ticker_matches) > 0:
                            ticker = ticker_matches[0].get("ticker")
                            if ticker:
                                tickers = [ticker]
                                LOGGER.info(f"Extracted ticker {ticker} from company name '{company_name}' for forecasting query: {query}")
                                break
                            else:
                                LOGGER.warning(f"Ticker resolution returned empty ticker for company name '{company_name}'")
                        else:
                            LOGGER.warning(f"Ticker resolution returned no matches for company name '{company_name}'")
                    except Exception as e:
                        LOGGER.warning(f"Failed to resolve company name '{company_name}' to ticker: {e}", exc_info=True)
            
            # If still no ticker, try word position analysis (company name often comes after forecasting verb)
            if not tickers:
                words = query.split()
                for i, word in enumerate(words):
                    # Look for capitalized words (potential company names) near forecasting keywords
                    if word[0].isupper() and len(word) > 2:
                        # Check if it's near a forecasting keyword
                        context_start = max(0, i - 3)
                        context_end = min(len(words), i + 3)
                        context = ' '.join(words[context_start:context_end]).lower()
                        if any(kw in context for kw in ['forecast', 'predict', 'estimate', 'project']):
                            try:
                                from .parsing.alias_builder import resolve_tickers_freeform
                                ticker_matches, _ = resolve_tickers_freeform(word)
                                if ticker_matches and len(ticker_matches) > 0:
                                    ticker = ticker_matches[0].get("ticker")
                                    if ticker:
                                        tickers = [ticker]
                                        LOGGER.info(f"Extracted ticker {ticker} from word '{word}' using position analysis for forecasting query")
                                        break
                            except Exception:
                                pass
        
        if not tickers:
            # For forecasting queries, still try to build context even without ticker
            # The forecast context builder can handle missing tickers
            if is_forecasting:
                LOGGER.error(f"Forecasting query detected but no ticker extracted from: {query}")
                # Return a helpful error context instead of empty string
                # This ensures the LLM knows this is a forecasting query
                error_context = f"\n{'='*80}\n⚠️ FORECASTING QUERY DETECTED - TICKER EXTRACTION FAILED\n{'='*80}\n"
                error_context += f"**Query:** {query}\n"
                error_context += f"**Issue:** Unable to extract company ticker from query.\n"
                error_context += f"**Recommendation:** Please specify the company name more clearly (e.g., 'Forecast Microsoft revenue' or 'What's the revenue forecast for MSFT?').\n"
                error_context += f"{'='*80}\n"
                return error_context
            return ""
        
        context_parts = []
        
        # Add macro economic context at the beginning
        if MACRO_DATA_AVAILABLE:
            try:
                macro_provider = get_macro_provider()
                # Attempt to determine company sector (first ticker)
                company_sector = None
                if tickers:
                    # This could be enhanced to fetch actual sector from database
                    # For now, using generic GLOBAL benchmarks
                    pass
                
                macro_context = macro_provider.build_macro_context(company_sector)
                if macro_context:
                    context_parts.append(f"{'='*80}\n📊 MACRO ECONOMIC CONTEXT\n{'='*80}\n{macro_context}\n\n")
            except Exception as e:
                LOGGER.debug(f"Could not build macro context: {e}")
        
        for ticker in tickers:
            try:
                # Get company name
                company_name = analytics_engine.get_company_name(ticker) or ticker
                
                # Fetch metric records (not just values) to get period info
                all_metrics = [
                    "revenue", "net_income", "ebitda", "ebitda_margin", "gross_margin", 
                    "operating_margin", "net_margin", "free_cash_flow", "cash_operations",
                    "capex", "total_assets", "total_liabilities", "shareholders_equity",
                    "roe", "roic", "roa", "debt_equity", "current_ratio",
                    "eps_basic", "eps_diluted", "revenue_per_share",
                    "ev_ebitda", "pe", "pb", "ev_revenue", "price", "market_cap"
                ]
                
                records = analytics_engine.fetch_metrics(ticker, metrics=all_metrics)
                
                if not records:
                    continue
                
                # Group by period for comprehensive view
                latest_records = analytics_engine._select_latest_records(records)
                
                if not latest_records:
                    continue
                
                # Extract period information from a representative record
                period_label = "latest available"
                for record in latest_records.values():
                    if record.period:
                        period_label = _format_period_label(record)
                        break
                
                # Get filing sources for citation with SEC URLs
                filing_sources = _get_filing_sources(ticker, database_path)
                source_citation = ""
                sec_urls = []
                
                if filing_sources:
                    # Get most recent filings (up to 3) for comprehensive sourcing
                    recent_filings = filing_sources[:3]
                    
                    for filing in recent_filings:
                        form_type = filing.get("form_type", "SEC filing")
                        fy = filing.get("fiscal_year")
                        fp = filing.get("fiscal_period")
                        sec_url = filing.get("sec_url")
                        
                        if sec_url:
                            # Format as markdown link: [10-K FY2023](URL)
                            if fy and fp:
                                link_text = f"{form_type} FY{fy} {fp}"
                                sec_urls.append(f"[{link_text}]({sec_url})")
                            elif fy:
                                link_text = f"{form_type} FY{fy}"
                                sec_urls.append(f"[{link_text}]({sec_url})")
                            else:
                                sec_urls.append(f"[{form_type}]({sec_url})")
                    
                    # Use first filing for header citation
                    first_filing = recent_filings[0]
                    form_type = first_filing.get("form_type", "SEC filing")
                    fy = first_filing.get("fiscal_year")
                    fp = first_filing.get("fiscal_period")
                    if fy and fp:
                        source_citation = f" (per {form_type} FY{fy} {fp})"
                    elif fy:
                        source_citation = f" (per {form_type} FY{fy})"
                
                # Build mandatory data block FIRST - this is critical for accuracy
                mandatory_block = _build_mandatory_data_block(ticker, latest_records, period_label)
                
                # Build comprehensive ticker context with SEC URLs prominently displayed
                ticker_context = mandatory_block  # Start with mandatory block
                ticker_context += f"\n{'='*80}\n"
                ticker_context += f"{company_name} ({ticker}) - {period_label}{source_citation}\n"
                ticker_context += f"{'='*80}\n\n"
                
                # Add SEC Filing Sources section at the top for easy access
                if sec_urls:
                    ticker_context += "📄 **SEC FILING SOURCES (Markdown Links)** - Copy these to your Sources section:\n"
                    for url_info in sec_urls:
                        ticker_context += f"  • {url_info}\n"
                    ticker_context += "⚠️ These are already formatted as markdown [text](url). Copy them EXACTLY to your Sources section.\n\n"
                
                # Income Statement Metrics
                income_metrics = []
                if latest_records.get("revenue"):
                    income_metrics.append(f"Revenue: {format_currency(latest_records['revenue'].value)}")
                if latest_records.get("net_income"):
                    income_metrics.append(f"Net Income: {format_currency(latest_records['net_income'].value)}")
                if latest_records.get("ebitda"):
                    income_metrics.append(f"EBITDA: {format_currency(latest_records['ebitda'].value)}")
                
                if income_metrics:
                    ticker_context += "Income Statement:\n" + "\n".join(f"  • {m}" for m in income_metrics) + "\n\n"
                
                # Profitability Metrics
                margin_metrics = []
                if latest_records.get("ebitda_margin"):
                    margin_metrics.append(f"EBITDA Margin: {format_percent(latest_records['ebitda_margin'].value)}")
                if latest_records.get("gross_margin"):
                    margin_metrics.append(f"Gross Margin: {format_percent(latest_records['gross_margin'].value)}")
                if latest_records.get("operating_margin"):
                    margin_metrics.append(f"Operating Margin: {format_percent(latest_records['operating_margin'].value)}")
                if latest_records.get("net_margin"):
                    margin_metrics.append(f"Net Margin: {format_percent(latest_records['net_margin'].value)}")
                
                if margin_metrics:
                    ticker_context += "Profitability Margins:\n" + "\n".join(f"  • {m}" for m in margin_metrics) + "\n\n"
                
                # Cash Flow Metrics
                cf_metrics = []
                if latest_records.get("free_cash_flow"):
                    cf_metrics.append(f"Free Cash Flow: {format_currency(latest_records['free_cash_flow'].value)}")
                if latest_records.get("cash_operations"):
                    cf_metrics.append(f"Cash from Operations: {format_currency(latest_records['cash_operations'].value)}")
                if latest_records.get("capex"):
                    cf_metrics.append(f"Capital Expenditures: {format_currency(latest_records['capex'].value)}")
                
                if cf_metrics:
                    ticker_context += "Cash Flow:\n" + "\n".join(f"  • {m}" for m in cf_metrics) + "\n\n"
                
                # Balance Sheet Metrics
                bs_metrics = []
                if latest_records.get("total_assets"):
                    bs_metrics.append(f"Total Assets: {format_currency(latest_records['total_assets'].value)}")
                if latest_records.get("total_liabilities"):
                    bs_metrics.append(f"Total Liabilities: {format_currency(latest_records['total_liabilities'].value)}")
                if latest_records.get("shareholders_equity"):
                    bs_metrics.append(f"Shareholders' Equity: {format_currency(latest_records['shareholders_equity'].value)}")
                
                if bs_metrics:
                    ticker_context += "Balance Sheet:\n" + "\n".join(f"  • {m}" for m in bs_metrics) + "\n\n"
                
                # Returns & Efficiency
                returns_metrics = []
                if latest_records.get("roe"):
                    returns_metrics.append(f"Return on Equity: {format_percent(latest_records['roe'].value)}")
                if latest_records.get("roic"):
                    returns_metrics.append(f"Return on Invested Capital: {format_percent(latest_records['roic'].value)}")
                if latest_records.get("roa"):
                    returns_metrics.append(f"Return on Assets: {format_percent(latest_records['roa'].value)}")
                
                if returns_metrics:
                    ticker_context += "Returns & Efficiency:\n" + "\n".join(f"  • {m}" for m in returns_metrics) + "\n\n"
                
                # Valuation Metrics
                valuation_metrics = []
                if latest_records.get("market_cap"):
                    valuation_metrics.append(f"Market Cap: {format_currency(latest_records['market_cap'].value)}")
                if latest_records.get("ev_ebitda"):
                    valuation_metrics.append(f"EV/EBITDA: {format_multiple(latest_records['ev_ebitda'].value)}")
                if latest_records.get("pe"):
                    valuation_metrics.append(f"P/E Ratio: {format_multiple(latest_records['pe'].value)}")
                if latest_records.get("pb"):
                    valuation_metrics.append(f"P/B Ratio: {format_multiple(latest_records['pb'].value)}")
                if latest_records.get("price"):
                    valuation_metrics.append(f"Stock Price: ${latest_records['price'].value:.2f}")
                
                if valuation_metrics:
                    ticker_context += "Valuation:\n" + "\n".join(f"  • {m}" for m in valuation_metrics) + "\n\n"
                
                # Per Share Metrics
                per_share_metrics = []
                if latest_records.get("eps_basic"):
                    per_share_metrics.append(f"EPS (Basic): ${latest_records['eps_basic'].value:.2f}")
                if latest_records.get("eps_diluted"):
                    per_share_metrics.append(f"EPS (Diluted): ${latest_records['eps_diluted'].value:.2f}")
                if latest_records.get("revenue_per_share"):
                    per_share_metrics.append(f"Revenue per Share: ${latest_records['revenue_per_share'].value:.2f}")
                
                if per_share_metrics:
                    ticker_context += "Per Share Data:\n" + "\n".join(f"  • {m}" for m in per_share_metrics) + "\n\n"
                
                # Check if this is a forecasting query
                is_forecasting = _is_forecasting_query(query)
                forecast_metric = None
                forecast_method = "auto"
                if is_forecasting:
                    forecast_metric = _extract_forecast_metric(query)
                    forecast_method = _extract_forecast_method(query)
                    LOGGER.info(f"Forecasting query detected for {ticker} {forecast_metric} using {forecast_method}")
                
                # Add ML forecasting context FIRST if this is a forecasting query (prioritize it)
                if is_forecasting and forecast_metric:
                    LOGGER.info(f"Building ML forecast context for {ticker} {forecast_metric} using {forecast_method}")
                    LOGGER.info(f"  - Ticker: {ticker}")
                    LOGGER.info(f"  - Metric: {forecast_metric}")
                    LOGGER.info(f"  - Method: {forecast_method}")
                    ml_forecast_context, forecast_result, explainability_data = _build_ml_forecast_context(
                        ticker=ticker,
                        metric=forecast_metric,
                        database_path=database_path,
                        periods=3,
                        method=forecast_method
                    )
                    if ml_forecast_context:
                        # CRITICAL: For forecasting queries, ONLY include ML forecast context
                        # DO NOT include historical snapshot data - it will confuse the LLM
                        # The forecast IS the answer, not historical data
                        context_parts.insert(0, ml_forecast_context)
                        LOGGER.info(f"ML forecast context generated and inserted at top of context for {ticker} {forecast_metric}")
                        
                        # Store forecast metadata for interactive forecasting
                        if forecast_result:
                            parameters = {
                                "periods": 3,
                                "method": forecast_method,
                            }
                            _set_last_forecast_metadata(
                                ticker=ticker,
                                metric=forecast_metric,
                                method=forecast_method,
                                periods=3,
                                forecast_result=forecast_result,
                                explainability=explainability_data,
                                parameters=parameters
                            )
                        LOGGER.info(f"  - Context length: {len(ml_forecast_context)} characters")
                        LOGGER.info(f"  - Contains 'ML FORECAST': {'ML FORECAST' in ml_forecast_context or 'CRITICAL: THIS IS THE PRIMARY ANSWER' in ml_forecast_context}")
                    else:
                        LOGGER.warning(f"ML forecast context generation returned None for {ticker} {forecast_metric} using {forecast_method}")
                        LOGGER.warning(f"  - This might be because ML forecasting dependencies are missing or forecast generation failed")
                        # Even if forecast generation failed, we should still try to provide some context
                        # Add an error context explaining what happened
                        error_context = f"\n{'='*80}\n⚠️ ML FORECAST UNAVAILABLE - {ticker} {forecast_metric.upper()}\n{'='*80}\n"
                        error_context += f"**Query:** Forecast {ticker} {forecast_metric} using {forecast_method}\n"
                        error_context += f"**Issue:** ML forecast generation failed or returned no results.\n"
                        error_context += f"**Possible causes:**\n"
                        error_context += f"  - ML forecasting dependencies missing (TensorFlow for LSTM, PyTorch for Transformer)\n"
                        error_context += f"  - Insufficient historical data (need at least 5-10 periods)\n"
                        error_context += f"  - Model training/forecasting errors\n"
                        error_context += f"**Recommendation:** Try using a different method (ARIMA, Prophet, ETS) or ensure data is available.\n"
                        error_context += f"{'='*80}\n"
                        context_parts.insert(0, error_context)
                        LOGGER.info(f"Added error context for failed forecast generation")
                        
                        # CRITICAL: For forecasting queries, skip adding historical ticker context
                        # The forecast context (even if it's an error) is sufficient - historical data would confuse the LLM
                        # Skip the rest of the ticker context building for forecasting queries
                        LOGGER.info(f"Skipping historical ticker context for forecasting query - using ML forecast error context only")
                        continue  # Skip to next ticker or end of loop
                
                context_parts.append(ticker_context)
                
                # Add comprehensive historical trend and growth analysis
                try:
                    growth_data = analytics_engine.compute_growth_metrics(ticker, latest_records)
                    if growth_data:
                        trend_context = "📈 **Growth & Trend Analysis**:\n"
                        
                        # Revenue trends
                        revenue_items = []
                        if growth_data.get("revenue_growth_yoy") is not None:
                            revenue_items.append(f"Revenue Growth (YoY): {format_percent(growth_data['revenue_growth_yoy'])}")
                        if growth_data.get("revenue_cagr_3y") is not None:
                            revenue_items.append(f"Revenue CAGR (3Y): {format_percent(growth_data['revenue_cagr_3y'])}")
                        if growth_data.get("revenue_cagr_5y") is not None:
                            revenue_items.append(f"Revenue CAGR (5Y): {format_percent(growth_data['revenue_cagr_5y'])}")
                        
                        if revenue_items:
                            trend_context += "  Revenue Trends:\n    - " + "\n    - ".join(revenue_items) + "\n"
                        
                        # Earnings trends
                        earnings_items = []
                        if growth_data.get("eps_growth_yoy") is not None:
                            earnings_items.append(f"EPS Growth (YoY): {format_percent(growth_data['eps_growth_yoy'])}")
                        if growth_data.get("eps_cagr_3y") is not None:
                            earnings_items.append(f"EPS CAGR (3Y): {format_percent(growth_data['eps_cagr_3y'])}")
                        if growth_data.get("net_income_growth_yoy") is not None:
                            earnings_items.append(f"Net Income Growth (YoY): {format_percent(growth_data['net_income_growth_yoy'])}")
                        
                        if earnings_items:
                            trend_context += "  Earnings Trends:\n    - " + "\n    - ".join(earnings_items) + "\n"
                        
                        # Margin trends
                        margin_items = []
                        if growth_data.get("margin_change_yoy") is not None:
                            direction = "expansion" if growth_data["margin_change_yoy"] > 0 else "compression"
                            margin_items.append(f"EBITDA Margin Change (YoY): {growth_data['margin_change_yoy']:+.0f} bps ({direction})")
                        if growth_data.get("gross_margin_change_yoy") is not None:
                            margin_items.append(f"Gross Margin Change (YoY): {growth_data['gross_margin_change_yoy']:+.0f} bps")
                        
                        if margin_items:
                            trend_context += "  Profitability Trends:\n    - " + "\n    - ".join(margin_items) + "\n"
                        
                        # Cash flow trends
                        cf_items = []
                        if growth_data.get("fcf_growth_yoy") is not None:
                            cf_items.append(f"Free Cash Flow Growth (YoY): {format_percent(growth_data['fcf_growth_yoy'])}")
                        if growth_data.get("fcf_margin_change") is not None:
                            cf_items.append(f"FCF Margin Change: {growth_data['fcf_margin_change']:+.0f} bps")
                        
                        if cf_items:
                            trend_context += "  Cash Flow Trends:\n    - " + "\n    - ".join(cf_items) + "\n"
                        
                        trend_context += "\n"
                        context_parts.append(trend_context)
                        
                except Exception as e:
                    LOGGER.debug(f"Could not fetch growth data for {ticker}: {e}")
                
                # Add key financial ratios and efficiency metrics
                try:
                    ratios_context = "📊 **Key Financial Ratios & Efficiency**:\n"
                    ratio_items = []
                    
                    # Liquidity ratios
                    if latest_records.get("current_ratio"):
                        ratio_items.append(f"Current Ratio: {latest_records['current_ratio'].value:.2f}x (measures short-term liquidity)")
                    if latest_records.get("quick_ratio"):
                        ratio_items.append(f"Quick Ratio: {latest_records['quick_ratio'].value:.2f}x")
                    
                    # Leverage ratios
                    if latest_records.get("debt_equity"):
                        ratio_items.append(f"Debt-to-Equity: {latest_records['debt_equity'].value:.2f}x (measures financial leverage)")
                    if latest_records.get("debt_ebitda"):
                        ratio_items.append(f"Net Debt/EBITDA: {latest_records['debt_ebitda'].value:.2f}x (debt payback period)")
                    if latest_records.get("interest_coverage"):
                        ratio_items.append(f"Interest Coverage: {latest_records['interest_coverage'].value:.1f}x (ability to pay interest)")
                    
                    # Asset efficiency
                    if latest_records.get("asset_turnover"):
                        ratio_items.append(f"Asset Turnover: {latest_records['asset_turnover'].value:.2f}x (asset utilization efficiency)")
                    if latest_records.get("inventory_turnover"):
                        ratio_items.append(f"Inventory Turnover: {latest_records['inventory_turnover'].value:.1f}x")
                    
                    if ratio_items:
                        ratios_context += "\n".join(f"  • {item}" for item in ratio_items) + "\n\n"
                        context_parts.append(ratios_context)
                        
                except Exception as e:
                    LOGGER.debug(f"Could not build ratios context for {ticker}: {e}")
                
                # Add valuation context with interpretation
                try:
                    if any(latest_records.get(m) for m in ["ev_ebitda", "pe", "pb", "peg"]):
                        valuation_context = "💰 **Valuation Analysis**:\n"
                        val_items = []
                        
                        if latest_records.get("ev_ebitda"):
                            ev_ebitda = latest_records["ev_ebitda"].value
                            val_items.append(f"EV/EBITDA: {ev_ebitda:.1f}x (typical range: 8-15x for mature companies)")
                        
                        if latest_records.get("pe"):
                            pe = latest_records["pe"].value
                            val_items.append(f"P/E Ratio: {pe:.1f}x (trailing earnings multiple)")
                        
                        if latest_records.get("pb"):
                            pb = latest_records["pb"].value
                            val_items.append(f"Price-to-Book: {pb:.1f}x (market value vs. book value)")
                        
                        if latest_records.get("peg"):
                            peg = latest_records["peg"].value
                            val_items.append(f"PEG Ratio: {peg:.2f} (P/E relative to growth; <1 may indicate undervaluation)")
                        
                        if latest_records.get("dividend_yield"):
                            div_yield = latest_records["dividend_yield"].value
                            val_items.append(f"Dividend Yield: {format_percent(div_yield)}")
                        
                        if val_items:
                            valuation_context += "\n".join(f"  • {item}" for item in val_items) + "\n\n"
                            context_parts.append(valuation_context)
                            
                except Exception as e:
                    LOGGER.debug(f"Could not build valuation context for {ticker}: {e}")
                
            except Exception as e:
                LOGGER.debug(f"Could not fetch metrics for {ticker}: {e}")
                continue
        
        if not context_parts:
            # CRITICAL: Return explicit "no data" message instead of empty string
            # Empty string causes LLM to hallucinate from training data
            return (
                "=" * 80 + "\n"
                "⚠️ NO FINANCIAL DATA AVAILABLE\n"
                "=" * 80 + "\n\n"
                f"**Query:** {query}\n\n"
                f"**Status:** No financial data found in database\n\n"
                "**Detected tickers:** " + (", ".join(tickers) if tickers else "None") + "\n\n"
                "**Reason:** Database is empty or ticker data hasn't been ingested yet.\n\n"
                "**🎯 INSTRUCTION TO LLM:**\n"
                "1. DO NOT make up financial data from your training data!\n"
                "2. DO NOT calculate percentages or growth rates!\n"
                "3. RESPOND WITH: 'I don't have current financial data for [Company] in my database.'\n"
                "4. SUGGEST: 'To get accurate data, please run: ingest [TICKER]'\n"
                "5. BE CLEAR that you're waiting for data, not providing estimates\n\n"
                "=" * 80 + "\n"
            )
        
        # Add multi-source data (Yahoo Finance, FRED, etc.) if available
        if MULTI_SOURCE_AVAILABLE and tickers:
            for ticker in tickers[:1]:  # Add for first ticker to avoid context overload
                try:
                    fred_api_key = os.getenv('FRED_API_KEY')
                    multi_source_context = get_multi_source_context(
                        ticker=ticker,
                        fred_api_key=fred_api_key,
                        include_yahoo=True,
                        include_fred=True,  # Always try to fetch FRED data (graceful degradation if no key)
                        include_imf=True  # Enable IMF macroeconomic data
                    )
                    if multi_source_context:
                        context_parts.append(multi_source_context)
                except Exception as e:
                    LOGGER.warning(f"Could not fetch multi-source data for {ticker}: {e}")
        
        # Add comprehensive context header with detailed instructions
        header = (
            "╔═══════════════════════════════════════════════════════════════════════════════╗\n"
            "║                    COMPREHENSIVE FINANCIAL DATA CONTEXT                      ║\n"
            "╚═══════════════════════════════════════════════════════════════════════════════╝\n\n"
            "📋 **DATA SOURCES**:\n"
            "SEC EDGAR filings (10-K, 10-Q), Yahoo Finance (real-time data, analyst ratings, news), "
            "FRED economic indicators (optional), and IMF macroeconomic data (optional). "
            "Each section includes source URLs formatted as markdown links [Source Name](URL).\n\n"
            "📖 **RESPONSE INSTRUCTIONS**:\n"
            "1. **Write like ChatGPT**: Natural, conversational, engaging - not robotic or formal\n"
            "2. **Use markdown formatting**: **bold** for emphasis, bullets, clear headers\n"
            "3. **Answer first**: Lead with the direct answer, then explain\n"
            "4. **Tell a story**: Connect metrics into a narrative, explain WHY things changed\n"
            "5. **Add perspective**: Industry context, analyst views, market sentiment, trends, outlook\n"
            "6. **🚨 MANDATORY: Cite ALL sources** - ALWAYS end your response with a '📊 Sources:' section containing:\n"
            "   - At least 5-10 clickable markdown links: [Source Name](URL)\n"
            "   - Include ALL SEC filing links provided in context\n"
            "   - Include ALL Yahoo Finance links provided in context\n"
            "   - Include FRED/IMF links when economic data is used\n"
            "   - NEVER use placeholder URLs - only real URLs from context\n"
            "   - Example: 📊 **Sources:**\n"
            "     - [10-K FY2024](https://www.sec.gov/...)\n"
            "     - [Yahoo Finance - Ticker](https://finance.yahoo.com/quote/TICKER)\n"
            "7. **NEVER show full URLs**: Always use markdown link format [text](url)\n"
            "8. **Incorporate diverse data**: Use SEC fundamentals, Yahoo metrics, analyst ratings, news, etc.\n\n"
            "**⚠️ CRITICAL REMINDER**: Every response MUST include a '📊 Sources:' section with clickable links. "
            "This is mandatory, not optional. If you don't include sources, your response is incomplete.\n\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
        )
        
        return header + "\n".join(context_parts)
        
    except Exception as e:
        LOGGER.error(f"Error building financial context: {e}")
        return ""


def build_company_universe_context(database_path: str) -> str:
    """
    Build company universe context for filter queries.
    
    Returns:
        Formatted company universe context with sector breakdowns
    """
    try:
        import json
        from pathlib import Path
        
        # Load company universe data
        universe_path = Path(__file__).resolve().parents[2] / "webui" / "data" / "company_universe.json"
        if not universe_path.exists():
            return ""
        
        with open(universe_path, 'r', encoding='utf-8') as f:
            companies = json.load(f)
        
        if not companies:
            return ""
        
        # Group by sector
        sectors: Dict[str, List[Dict[str, Any]]] = {}
        for company in companies:
            sector = company.get('sector', 'Uncategorised')
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(company)
        
        # Build context
        context_parts = [
            "╔═══════════════════════════════════════════════════════════════════════════════╗\n"
            "║                     COMPANY UNIVERSE FILTER CONTEXT                          ║\n"
            "╚═══════════════════════════════════════════════════════════════════════════════╝\n\n"
            "📊 **INSTRUCTIONS FOR FILTER QUERIES**:\n"
            "The user is asking to filter or list companies by specific criteria (sector, revenue, growth, etc.).\n"
            "Use the company universe data below to:\n"
            "1. Filter companies by the requested criteria\n"
            "2. Present results as a formatted list or table\n"
            "3. Include key metrics: ticker, company name, sector, revenue, market cap\n"
            "4. Sort by relevance (e.g., by revenue if revenue filter is specified)\n"
            "5. Limit to top 10-20 most relevant results\n"
            "6. Explain the filtering criteria used\n\n"
            f"📈 **DATABASE OVERVIEW**: {len(companies)} companies across {len(sectors)} sectors\n\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
        ]
        
        # Add sector breakdowns
        for sector, sector_companies in sorted(sectors.items(), key=lambda x: len(x[1]), reverse=True):
            context_parts.append(f"**{sector}** ({len(sector_companies)} companies):\n")
            
            # Sort by market cap (if available) and show top companies
            sorted_companies = sorted(
                sector_companies,
                key=lambda c: c.get('market_cap', 0) if c.get('market_cap') else 0,
                reverse=True
            )[:15]  # Top 15 companies per sector
            
            for company in sorted_companies:
                ticker = company.get('ticker', 'N/A')
                name = company.get('company', 'Unknown')
                market_cap_display = company.get('market_cap_display', 'N/A')
                
                context_parts.append(f"  • {ticker}: {name} (Market Cap: {market_cap_display})\n")
            
            if len(sector_companies) > 15:
                context_parts.append(f"  ... and {len(sector_companies) - 15} more\n")
            
            context_parts.append("\n")
        
        return "".join(context_parts)
        
    except Exception as e:
        LOGGER.debug(f"Could not build company universe context: {e}")
        return ""


def format_metrics_naturally(ticker: str, metrics: Dict[str, Any]) -> str:
    """Format metrics as natural language text."""
    if not metrics:
        return f"No data available for {ticker}."
    
    lines = [f"Financial snapshot for {ticker}:"]
    
    # Revenue
    if metrics.get("revenue"):
        lines.append(f"  Revenue: {format_currency(metrics['revenue'])}")
    
    # Profitability
    if metrics.get("ebitda_margin"):
        lines.append(f"  EBITDA Margin: {format_percent(metrics['ebitda_margin'])}")
    
    # Cash flow
    if metrics.get("free_cash_flow"):
        lines.append(f"  Free Cash Flow: {format_currency(metrics['free_cash_flow'])}")
    
    # Valuation
    if metrics.get("ev_ebitda"):
        lines.append(f"  EV/EBITDA: {format_multiple(metrics['ev_ebitda'])}")
    
    return "\n".join(lines)

