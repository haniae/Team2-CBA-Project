"""
ML Forecasting Module

Advanced machine learning forecasting capabilities for financial metrics.
Implements time series models (ARIMA, Prophet, ETS) and deep learning models.
"""

from __future__ import annotations

from .ml_forecaster import MLForecaster, get_ml_forecaster
from .user_plugins import ForecastingPluginManager

# Try to import forecasters (may not be available if dependencies missing)
try:
    from .arima_forecaster import ARIMAForecaster, get_arima_forecaster
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    ARIMAForecaster = None
    get_arima_forecaster = None

try:
    from .prophet_forecaster import ProphetForecaster, get_prophet_forecaster
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    ProphetForecaster = None
    get_prophet_forecaster = None

try:
    from .ets_forecaster import ETSForecaster, get_ets_forecaster
    ETS_AVAILABLE = True
except ImportError:
    ETS_AVAILABLE = False
    ETSForecaster = None
    get_ets_forecaster = None

try:
    from .lstm_forecaster import LSTMForecaster, get_lstm_forecaster
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    LSTMForecaster = None
    get_lstm_forecaster = None

try:
    from .transformer_forecaster import TransformerForecaster, get_transformer_forecaster
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    TransformerForecaster = None
    get_transformer_forecaster = None

__all__ = [
    "MLForecaster",
    "get_ml_forecaster",
    "ForecastingPluginManager",
]

# Add individual forecasters if available
if ARIMA_AVAILABLE:
    __all__.extend(["ARIMAForecaster", "get_arima_forecaster"])
if PROPHET_AVAILABLE:
    __all__.extend(["ProphetForecaster", "get_prophet_forecaster"])
if ETS_AVAILABLE:
    __all__.extend(["ETSForecaster", "get_ets_forecaster"])
if LSTM_AVAILABLE:
    __all__.extend(["LSTMForecaster", "get_lstm_forecaster"])
if TRANSFORMER_AVAILABLE:
    __all__.extend(["TransformerForecaster", "get_transformer_forecaster"])

