"""
Unified ML Forecasting Interface

Main interface for all ML forecasting models. Automatically selects
the best model based on data characteristics or allows manual selection.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

LOGGER = logging.getLogger(__name__)

# Import new modules (with error handling)
try:
    from .hyperparameter_tuning import HyperparameterTuner
    HYPERPARAMETER_TUNING_AVAILABLE = True
except ImportError:
    HYPERPARAMETER_TUNING_AVAILABLE = False
    HyperparameterTuner = None

try:
    from .technical_indicators import TechnicalIndicators
    TECHNICAL_INDICATORS_AVAILABLE = True
except ImportError:
    TECHNICAL_INDICATORS_AVAILABLE = False
    TechnicalIndicators = None

try:
    from .feature_engineering import FeatureEngineering
    FEATURE_ENGINEERING_AVAILABLE = True
except ImportError:
    FEATURE_ENGINEERING_AVAILABLE = False
    FeatureEngineering = None

try:
    from .preprocessing import OutlierDetector, MissingDataImputer, DataScaler, TrendDecomposer
    PREPROCESSING_AVAILABLE = True
except ImportError:
    PREPROCESSING_AVAILABLE = False
    OutlierDetector = None
    MissingDataImputer = None
    DataScaler = None
    TrendDecomposer = None

try:
    from .external_factors import ExternalFactorsProvider
    EXTERNAL_FACTORS_AVAILABLE = True
except ImportError:
    EXTERNAL_FACTORS_AVAILABLE = False
    ExternalFactorsProvider = None

try:
    from .regime_detection import RegimeDetector
    REGIME_DETECTION_AVAILABLE = True
except ImportError:
    REGIME_DETECTION_AVAILABLE = False
    RegimeDetector = None

try:
    from .explainability import ModelExplainer
    EXPLAINABILITY_AVAILABLE = True
except ImportError:
    EXPLAINABILITY_AVAILABLE = False
    ModelExplainer = None

try:
    from .uncertainty import UncertaintyQuantifier
    UNCERTAINTY_AVAILABLE = True
except ImportError:
    UNCERTAINTY_AVAILABLE = False
    UncertaintyQuantifier = None


@dataclass
class MLForecast:
    """Unified ML forecast result."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    method: str  # Method used ('arima', 'prophet', 'ets', 'lstm', 'transformer', 'ensemble')
    model_details: Dict  # Model-specific details
    confidence: float  # Overall confidence (0-1)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "periods": self.periods,
            "predicted_values": self.predicted_values,
            "confidence_intervals": {
                "low": self.confidence_intervals_low,
                "high": self.confidence_intervals_high,
            },
            "method": self.method,
            "model_details": self.model_details,
            "confidence": self.confidence,
        }


class BaseForecaster(ABC):
    """Base class for all forecasters."""
    
    def __init__(self, database_path: str):
        """Initialize forecaster with database path."""
        self.database_path = database_path
    
    def _normalize_period_to_date(self, period: str, fiscal_year: Optional[int] = None) -> Optional[str]:
        """
        Normalize financial period format to a date string.
        
        Handles formats like:
        - "2023-FY" → "2023-12-31"
        - "2023-Q1" → "2023-03-31"
        - "2023-Q2" → "2023-06-30"
        - "2023-Q3" → "2023-09-30"
        - "2023-Q4" → "2023-12-31"
        - "2023" → "2023-12-31"
        - ISO date strings → returned as-is
        
        Args:
            period: Period string from database (e.g., "2023-FY", "2023-Q3")
            fiscal_year: Optional fiscal year if period doesn't contain year
            
        Returns:
            Date string in YYYY-MM-DD format, or None if cannot parse
        """
        if not period:
            # Try fiscal_year if available
            if fiscal_year:
                return f"{fiscal_year}-12-31"
            return None
        
        period_str = str(period).strip()
        
        # Already a date format (YYYY-MM-DD or similar)
        if re.match(r'^\d{4}-\d{2}-\d{2}', period_str):
            return period_str
        
        # Handle "2023-FY" format
        if '-FY' in period_str:
            year = period_str.split('-FY')[0]
            try:
                year_int = int(year)
                return f"{year_int}-12-31"
            except ValueError:
                pass
        
        # Handle "2023-Q1", "2023-Q2", etc.
        if '-Q' in period_str:
            parts = period_str.split('-Q')
            if len(parts) == 2:
                try:
                    year = int(parts[0])
                    quarter = int(parts[1])
                    # Map quarters to end dates
                    quarter_end_dates = {
                        1: (3, 31),  # Q1 ends March 31
                        2: (6, 30),  # Q2 ends June 30
                        3: (9, 30),  # Q3 ends September 30
                        4: (12, 31), # Q4 ends December 31
                    }
                    if quarter in quarter_end_dates:
                        month, day = quarter_end_dates[quarter]
                        return f"{year}-{month:02d}-{day:02d}"
                except ValueError:
                    pass
        
        # Handle year-only format "2023"
        if re.match(r'^\d{4}$', period_str):
            try:
                year_int = int(period_str)
                return f"{year_int}-12-31"
            except ValueError:
                pass
        
        # Try fiscal_year if provided
        if fiscal_year:
            return f"{fiscal_year}-12-31"
        
        # Try to parse as date (fallback)
        try:
            from datetime import datetime
            parsed = pd.to_datetime(period_str)
            return parsed.strftime('%Y-%m-%d')
        except:
            pass
        
        return None
    
    def _fetch_metric_records(
        self,
        ticker: str,
        metric: str,
        min_periods: int = 2
    ) -> List[Dict[str, any]]:
        """
        Fetch historical metric records from database.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric name (e.g., 'revenue', 'net_income')
            min_periods: Minimum number of periods required
            
        Returns:
            List of records with 'period' and 'value' keys
        """
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query metric_snapshots table (which stores metric values)
                # Try metric_snapshots first, fallback to financial_facts
                cursor.execute("""
                    SELECT period, value, updated_at, fiscal_year
                    FROM metric_snapshots
                    WHERE ticker = ? AND metric = ?
                    ORDER BY period ASC
                """, (ticker.upper(), metric))
                
                rows = cursor.fetchall()
                
                # If no data in metric_snapshots, try financial_facts
                if len(rows) == 0:
                    cursor.execute("""
                        SELECT period, value, period_end as updated_at, fiscal_year
                        FROM financial_facts
                        WHERE ticker = ? AND metric = ?
                        ORDER BY period ASC
                    """, (ticker.upper(), metric))
                    rows = cursor.fetchall()
                
                if len(rows) < min_periods:
                    LOGGER.warning(f"Insufficient data for {ticker} {metric}: {len(rows)} records")
                    return []
                
                records = []
                for row in rows:
                    period_str = row['period'] if row['period'] else f"{row.get('fiscal_year', '')}-FY"
                    fiscal_year = row.get('fiscal_year')
                    
                    # Normalize period to date format
                    normalized_date = self._normalize_period_to_date(period_str, fiscal_year)
                    if normalized_date is None:
                        # Skip records we can't parse
                        LOGGER.warning(f"Could not parse period format: {period_str}")
                        continue
                    
                    records.append({
                        'period': period_str,  # Keep original for reference
                        'date': normalized_date,  # Normalized date for time series
                        'value': row['value'],
                        'updated_at': row['updated_at'] if row['updated_at'] else None,
                        'fiscal_year': fiscal_year
                    })
                
                return records
                
        except Exception as e:
            LOGGER.exception(f"Error fetching metric records for {ticker} {metric}: {e}")
            return []
    
    @abstractmethod
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        **kwargs
    ) -> Optional[MLForecast]:
        """
        Generate forecast.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast
            periods: Number of periods to forecast
            **kwargs: Additional arguments for specific forecasters
            
        Returns:
            MLForecast or None if forecast fails
        """
        pass


# Import forecasters (with error handling)
try:
    from .arima_forecaster import ARIMAForecaster, ARIMAForecast
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    ARIMAForecaster = None
    ARIMAForecast = None

try:
    from .prophet_forecaster import ProphetForecaster, ProphetForecast
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    ProphetForecaster = None
    ProphetForecast = None

try:
    from .ets_forecaster import ETSForecaster, ETSForecast
    ETS_AVAILABLE = True
except ImportError:
    ETS_AVAILABLE = False
    ETSForecaster = None
    ETSForecast = None

try:
    from .lstm_forecaster import LSTMForecaster, LSTMForecastResult
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    LSTMForecaster = None
    LSTMForecastResult = None

try:
    from .transformer_forecaster import TransformerForecaster, TransformerForecastResult
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    TransformerForecaster = None
    TransformerForecastResult = None


class MLForecaster:
    """Unified ML forecaster for financial metrics."""
    
    def __init__(self, db_path: str):
        """
        Initialize ML forecaster.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        
        # Initialize forecasters (with error handling)
        self.arima_forecaster = None
        self.prophet_forecaster = None
        self.ets_forecaster = None
        self.lstm_forecaster = None
        self.transformer_forecaster = None
        
        # Initialize new modules (with error handling)
        self.hyperparameter_tuner = None
        self.technical_indicators = None
        self.feature_engineering = None
        self.outlier_detector = None
        self.missing_data_imputer = None
        self.data_scaler = None
        self.trend_decomposer = None
        self.external_factors_provider = None
        self.regime_detector = None
        self.model_explainer = None
        self.uncertainty_quantifier = None
        
        try:
            if ARIMA_AVAILABLE:
                self.arima_forecaster = ARIMAForecaster(db_path)
        except ImportError:
            LOGGER.warning("ARIMA forecaster not available (pmdarima not installed)")
        
        try:
            if PROPHET_AVAILABLE:
                self.prophet_forecaster = ProphetForecaster(db_path)
        except ImportError:
            LOGGER.warning("Prophet forecaster not available (prophet not installed)")
        
        try:
            if ETS_AVAILABLE:
                self.ets_forecaster = ETSForecaster(db_path)
        except ImportError:
            LOGGER.warning("ETS forecaster not available (statsmodels not installed)")
        
        try:
            if LSTM_AVAILABLE:
                self.lstm_forecaster = LSTMForecaster(db_path)
        except (ImportError, Exception) as e:
            LOGGER.warning(f"LSTM forecaster not available: {e}")
        
        try:
            if TRANSFORMER_AVAILABLE:
                self.transformer_forecaster = TransformerForecaster(db_path)
        except (ImportError, Exception) as e:
            LOGGER.warning(f"Transformer forecaster not available: {e}")
        
        # Initialize new modules
        try:
            if HYPERPARAMETER_TUNING_AVAILABLE:
                self.hyperparameter_tuner = HyperparameterTuner(db_path)
        except Exception as e:
            LOGGER.warning(f"Hyperparameter tuner not available: {e}")
        
        try:
            if TECHNICAL_INDICATORS_AVAILABLE:
                self.technical_indicators = TechnicalIndicators()
        except Exception as e:
            LOGGER.warning(f"Technical indicators not available: {e}")
        
        try:
            if FEATURE_ENGINEERING_AVAILABLE:
                self.feature_engineering = FeatureEngineering()
        except Exception as e:
            LOGGER.warning(f"Feature engineering not available: {e}")
        
        try:
            if PREPROCESSING_AVAILABLE:
                self.outlier_detector = OutlierDetector()
                self.missing_data_imputer = MissingDataImputer()
                self.data_scaler = DataScaler()
                self.trend_decomposer = TrendDecomposer()
        except Exception as e:
            LOGGER.warning(f"Preprocessing modules not available: {e}")
        
        try:
            if EXTERNAL_FACTORS_AVAILABLE:
                self.external_factors_provider = ExternalFactorsProvider()
        except Exception as e:
            LOGGER.warning(f"External factors provider not available: {e}")
        
        try:
            if REGIME_DETECTION_AVAILABLE:
                self.regime_detector = RegimeDetector()
        except Exception as e:
            LOGGER.warning(f"Regime detector not available: {e}")
        
        try:
            if EXPLAINABILITY_AVAILABLE:
                self.model_explainer = ModelExplainer()
        except Exception as e:
            LOGGER.warning(f"Model explainer not available: {e}")
        
        try:
            if UNCERTAINTY_AVAILABLE:
                self.uncertainty_quantifier = UncertaintyQuantifier()
        except Exception as e:
            LOGGER.warning(f"Uncertainty quantifier not available: {e}")
    
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        method: Literal["auto", "arima", "prophet", "ets", "lstm", "gru", "transformer", "ensemble"] = "auto",
        use_hyperparameter_tuning: bool = False,
        use_external_factors: bool = False,
        use_technical_indicators: bool = False,
        use_preprocessing: bool = True,
        **kwargs
    ) -> Optional[MLForecast]:
        """
        Forecast metric using ML models.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., 'revenue', 'net_income')
            periods: Number of years to forecast
            method: Forecasting method ('auto', 'arima', 'prophet', 'ets', 'lstm', 'gru', 'transformer', 'ensemble')
            use_hyperparameter_tuning: Whether to use hyperparameter tuning
            use_external_factors: Whether to use external factors (market indices, economic indicators)
            use_technical_indicators: Whether to use technical indicators
            use_preprocessing: Whether to apply preprocessing (outlier detection, missing data, scaling)
            **kwargs: Additional arguments for specific forecasters
            
        Returns:
            MLForecast with predictions and confidence intervals
        """
        # Auto-select best method if requested
        if method == "auto":
            method = self._select_best_method(ticker, metric)
        
        # Store preprocessing and feature engineering flags for use in forecasters
        kwargs['use_hyperparameter_tuning'] = use_hyperparameter_tuning
        kwargs['use_external_factors'] = use_external_factors
        kwargs['use_technical_indicators'] = use_technical_indicators
        kwargs['use_preprocessing'] = use_preprocessing
        
        # Generate forecast using selected method
        if method == "arima":
            return self._forecast_arima(ticker, metric, periods, **kwargs)
        elif method == "prophet":
            return self._forecast_prophet(ticker, metric, periods, **kwargs)
        elif method == "ets":
            return self._forecast_ets(ticker, metric, periods, **kwargs)
        elif method == "lstm" or method == "gru":
            if self.lstm_forecaster is None:
                LOGGER.warning(f"LSTM/GRU not available (TensorFlow missing), falling back to auto-select")
                # Fall back to auto-select best available method
                fallback_method = self._select_best_method(ticker, metric)
                if fallback_method == "arima":
                    return self._forecast_arima(ticker, metric, periods, **kwargs)
                elif fallback_method == "prophet":
                    return self._forecast_prophet(ticker, metric, periods, **kwargs)
                elif fallback_method == "ets":
                    return self._forecast_ets(ticker, metric, periods, **kwargs)
                else:
                    LOGGER.error(f"Fallback method {fallback_method} also not available")
                    return None
            return self._forecast_lstm(ticker, metric, periods, model_type=method, **kwargs)
        elif method == "transformer":
            if self.transformer_forecaster is None:
                LOGGER.warning(f"Transformer not available (PyTorch missing), falling back to auto-select")
                # Fall back to auto-select best available method
                fallback_method = self._select_best_method(ticker, metric)
                if fallback_method == "arima":
                    return self._forecast_arima(ticker, metric, periods, **kwargs)
                elif fallback_method == "prophet":
                    return self._forecast_prophet(ticker, metric, periods, **kwargs)
                elif fallback_method == "ets":
                    return self._forecast_ets(ticker, metric, periods, **kwargs)
                else:
                    LOGGER.error(f"Fallback method {fallback_method} also not available")
                    return None
            return self._forecast_transformer(ticker, metric, periods, **kwargs)
        elif method == "ensemble":
            return self._forecast_ensemble(ticker, metric, periods, **kwargs)
        else:
            LOGGER.error(f"Unknown forecasting method: {method}")
            return None
    
    def _forecast_arima(
        self, ticker: str, metric: str, periods: int, **kwargs
    ) -> Optional[MLForecast]:
        """Forecast using ARIMA."""
        if self.arima_forecaster is None:
            LOGGER.error("ARIMA forecaster not available")
            return None
        
        forecast = self.arima_forecaster.forecast(ticker, metric, periods, **kwargs)
        if forecast is None:
            return None
        
        return MLForecast(
            ticker=forecast.ticker,
            metric=forecast.metric,
            periods=forecast.periods,
            predicted_values=forecast.predicted_values,
            confidence_intervals_low=forecast.confidence_intervals_low,
            confidence_intervals_high=forecast.confidence_intervals_high,
            method="arima",
            model_details={
                "model_params": forecast.model_params,
                "aic": forecast.aic,
            },
            confidence=forecast.confidence,
        )
    
    def _forecast_prophet(
        self, ticker: str, metric: str, periods: int, **kwargs
    ) -> Optional[MLForecast]:
        """Forecast using Prophet."""
        if self.prophet_forecaster is None:
            LOGGER.error("Prophet forecaster not available")
            return None
        
        forecast = self.prophet_forecaster.forecast(ticker, metric, periods, **kwargs)
        if forecast is None:
            return None
        
        return MLForecast(
            ticker=forecast.ticker,
            metric=forecast.metric,
            periods=forecast.periods,
            predicted_values=forecast.predicted_values,
            confidence_intervals_low=forecast.confidence_intervals_low,
            confidence_intervals_high=forecast.confidence_intervals_high,
            method="prophet",
            model_details={
                "seasonality_detected": forecast.seasonality_detected,
                "changepoints": forecast.changepoints,
            },
            confidence=forecast.confidence,
        )
    
    def _forecast_ets(
        self, ticker: str, metric: str, periods: int, **kwargs
    ) -> Optional[MLForecast]:
        """Forecast using ETS."""
        if self.ets_forecaster is None:
            LOGGER.error("ETS forecaster not available")
            return None
        
        forecast = self.ets_forecaster.forecast(ticker, metric, periods, **kwargs)
        if forecast is None:
            return None
        
        return MLForecast(
            ticker=forecast.ticker,
            metric=forecast.metric,
            periods=forecast.periods,
            predicted_values=forecast.predicted_values,
            confidence_intervals_low=forecast.confidence_intervals_low,
            confidence_intervals_high=forecast.confidence_intervals_high,
            method="ets",
            model_details={
                "model_type": forecast.model_type,
                "seasonal_periods": forecast.seasonal_periods,
            },
            confidence=forecast.confidence,
        )
    
    def _forecast_lstm(
        self, ticker: str, metric: str, periods: int, model_type: str = "lstm", **kwargs
    ) -> Optional[MLForecast]:
        """Forecast using LSTM/GRU."""
        if self.lstm_forecaster is None:
            LOGGER.error("LSTM forecaster not available")
            return None
        
        forecast = self.lstm_forecaster.forecast(
            ticker, metric, periods, model_type=model_type, **kwargs
        )
        if forecast is None:
            return None
        
        return MLForecast(
            ticker=forecast.ticker,
            metric=forecast.metric,
            periods=forecast.periods,
            predicted_values=forecast.predicted_values,
            confidence_intervals_low=forecast.confidence_intervals_low,
            confidence_intervals_high=forecast.confidence_intervals_high,
            method=model_type.upper(),
            model_details={
                "model_type": forecast.model_type,
                "layers": forecast.layers,
                "epochs_trained": forecast.epochs_trained,
                "training_loss": forecast.training_loss,
                "validation_loss": forecast.validation_loss,
            },
            confidence=forecast.confidence,
        )
    
    def _forecast_transformer(
        self, ticker: str, metric: str, periods: int, **kwargs
    ) -> Optional[MLForecast]:
        """Forecast using Transformer."""
        if self.transformer_forecaster is None:
            LOGGER.error("Transformer forecaster not available")
            return None
        
        forecast = self.transformer_forecaster.forecast(ticker, metric, periods, **kwargs)
        if forecast is None:
            return None
        
        return MLForecast(
            ticker=forecast.ticker,
            metric=forecast.metric,
            periods=forecast.periods,
            predicted_values=forecast.predicted_values,
            confidence_intervals_low=forecast.confidence_intervals_low,
            confidence_intervals_high=forecast.confidence_intervals_high,
            method="TRANSFORMER",
            model_details={
                "model_name": forecast.model_name,
                "num_layers": forecast.num_layers,
                "num_heads": forecast.num_heads,
                "d_model": forecast.d_model,
                "epochs_trained": forecast.epochs_trained,
                "training_loss": forecast.training_loss,
                "validation_loss": forecast.validation_loss,
            },
            confidence=forecast.confidence,
        )
    
    def _forecast_ensemble(
        self, ticker: str, metric: str, periods: int, **kwargs
    ) -> Optional[MLForecast]:
        """
        Forecast using ensemble of multiple models.
        
        Supports multiple ensemble methods:
        - 'weighted': Weight by confidence scores (default)
        - 'performance': Weight by validation metrics (MAE/RMSE)
        - 'equal': Equal weights
        """
        ensemble_method = kwargs.get('ensemble_method', 'weighted')
        
        forecasts = []
        
        # Get forecasts from all available models
        if self.arima_forecaster:
            arima_forecast = self._forecast_arima(ticker, metric, periods, **kwargs)
            if arima_forecast:
                forecasts.append(arima_forecast)
        
        if self.prophet_forecaster:
            prophet_forecast = self._forecast_prophet(ticker, metric, periods, **kwargs)
            if prophet_forecast:
                forecasts.append(prophet_forecast)
        
        if self.ets_forecaster:
            ets_forecast = self._forecast_ets(ticker, metric, periods, **kwargs)
            if ets_forecast:
                forecasts.append(ets_forecast)
        
        if self.lstm_forecaster:
            lstm_forecast = self._forecast_lstm(ticker, metric, periods, model_type="lstm", **kwargs)
            if lstm_forecast:
                forecasts.append(lstm_forecast)
        
        if self.transformer_forecaster:
            transformer_forecast = self._forecast_transformer(ticker, metric, periods, **kwargs)
            if transformer_forecast:
                forecasts.append(transformer_forecast)
        
        if not forecasts:
            LOGGER.error("No forecasts available for ensemble")
            return None
        
        # If only one model, return it directly
        if len(forecasts) == 1:
            result = forecasts[0]
            result.method = "ensemble"
            return result
        
        # Calculate weights based on ensemble method
        if ensemble_method == "performance":
            weights = self._calculate_performance_weights(forecasts, ticker, metric)
        elif ensemble_method == "equal":
            weights = [1.0 / len(forecasts)] * len(forecasts)
        else:  # 'weighted' or default
            weights = self._calculate_confidence_weights(forecasts)
        
        # Combine predictions
        ensemble_values = []
        ensemble_low = []
        ensemble_high = []
        
        for i in range(periods):
            weighted_value = sum(f.predicted_values[i] * w for f, w in zip(forecasts, weights))
            weighted_low = sum(f.confidence_intervals_low[i] * w for f, w in zip(forecasts, weights))
            weighted_high = sum(f.confidence_intervals_high[i] * w for f, w in zip(forecasts, weights))
            
            ensemble_values.append(weighted_value)
            ensemble_low.append(weighted_low)
            ensemble_high.append(weighted_high)
        
        # Average confidence
        avg_confidence = sum(f.confidence * w for f, w in zip(forecasts, weights))
        
        # Combine model details
        model_details = {
            "models_used": [f.method for f in forecasts],
            "weights": dict(zip([f.method for f in forecasts], weights)),
            "ensemble_method": ensemble_method,
            "individual_forecasts": [f.to_dict() for f in forecasts],
        }
        
        return MLForecast(
            ticker=forecasts[0].ticker,
            metric=forecasts[0].metric,
            periods=forecasts[0].periods,  # All should have same periods
            predicted_values=ensemble_values,
            confidence_intervals_low=ensemble_low,
            confidence_intervals_high=ensemble_high,
            method="ensemble",
            model_details=model_details,
            confidence=avg_confidence,
        )
    
    def _calculate_confidence_weights(self, forecasts: List[MLForecast]) -> List[float]:
        """Calculate weights based on confidence scores."""
        weights = [f.confidence for f in forecasts]
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0 / len(forecasts)] * len(forecasts)
        else:
            weights = [w / total_weight for w in weights]
        return weights
    
    def _calculate_performance_weights(
        self,
        forecasts: List[MLForecast],
        ticker: str,
        metric: str
    ) -> List[float]:
        """
        Calculate weights based on validation performance (MAE/RMSE).
        
        Uses inverse of validation metrics - lower error = higher weight.
        """
        try:
            from .validation import ModelValidator
            from .backtesting import BacktestRunner
            
            # Run quick backtest to get validation metrics
            backtest_runner = BacktestRunner(self.db_path)
            backtest_results = backtest_runner.run_backtest(
                ticker=ticker,
                metric=metric,
                train_periods=5,
                test_periods=2,
                models=[f.method for f in forecasts]
            )
            
            # Calculate inverse RMSE weights (lower RMSE = higher weight)
            inverse_rmse = []
            for forecast in forecasts:
                model_name = forecast.method
                if model_name in backtest_results:
                    rmse = backtest_results[model_name].metrics.rmse
                    if rmse > 0:
                        inverse_rmse.append(1.0 / rmse)
                    else:
                        inverse_rmse.append(1.0)
                else:
                    # If no backtest result, use confidence as fallback
                    inverse_rmse.append(forecast.confidence)
            
            # Normalize weights
            total_weight = sum(inverse_rmse)
            if total_weight > 0:
                weights = [w / total_weight for w in inverse_rmse]
            else:
                weights = [1.0 / len(forecasts)] * len(forecasts)
            
            return weights
            
        except Exception as e:
            LOGGER.warning(f"Performance-based weighting failed: {e}, using confidence weights")
            return self._calculate_confidence_weights(forecasts)
    
    def _select_best_method(
        self, ticker: str, metric: str
    ) -> Literal["arima", "prophet", "ets", "lstm", "transformer"]:
        """
        Auto-select best forecasting method based on cross-validation.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast
            
        Returns:
            Best method name
        """
        try:
            from .validation import TimeSeriesCrossValidator, ModelValidator
            
            # Get historical data
            records = self._fetch_metric_records(ticker, metric)
            if not records or len(records) < 10:
                # Not enough data for cross-validation, use simple heuristic
                return self._select_best_method_simple()
            
            # Convert to time series
            df = pd.DataFrame(records)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                df['date'] = pd.to_datetime(df['period'], errors='coerce')
            
            df = df.dropna(subset=['date'])
            df = df.sort_values('date')
            
            ts = pd.Series(
                data=df['value'].values,
                index=df['date'].values,
                name=f"{ticker}_{metric}"
            )
            
            if len(ts) < 10:
                return self._select_best_method_simple()
            
            # Check available methods
            available_methods = []
            if self.prophet_forecaster:
                available_methods.append("prophet")
            if self.arima_forecaster:
                available_methods.append("arima")
            if self.ets_forecaster:
                available_methods.append("ets")
            if self.lstm_forecaster and len(ts) >= 20:
                available_methods.append("lstm")
            if self.transformer_forecaster and len(ts) >= 20:
                available_methods.append("transformer")
            
            if not available_methods:
                raise ValueError("No forecasting methods available")
            
            # Use walk-forward cross-validation to select best method
            cv = TimeSeriesCrossValidator()
            validator = ModelValidator()
            
            initial_train_size = max(5, len(ts) // 2)
            folds = cv.walk_forward_cv(ts, initial_train_size=initial_train_size, step_size=1)
            
            if len(folds) < 2:
                # Not enough folds, use simple heuristic
                return self._select_best_method_simple()
            
            # Test each method on folds
            method_scores = {}
            
            for method in available_methods:
                scores = []
                for train_data, test_data in folds[:3]:  # Use first 3 folds for speed
                    try:
                        # Generate forecast
                        forecast = self.forecast(
                            ticker=ticker,
                            metric=metric,
                            periods=len(test_data),
                            method=method
                        )
                        
                        if forecast and len(forecast.predicted_values) >= len(test_data):
                            # Calculate RMSE
                            predicted = forecast.predicted_values[:len(test_data)]
                            actual = test_data.values
                            
                            rmse = validator.calculate_metrics(actual.tolist(), predicted).rmse
                            scores.append(rmse)
                    except Exception:
                        continue
                
                if scores:
                    method_scores[method] = np.mean(scores)
            
            if not method_scores:
                # All methods failed, use simple heuristic
                return self._select_best_method_simple()
            
            # Select method with lowest RMSE
            best_method = min(method_scores, key=method_scores.get)
            LOGGER.info(f"Selected best method for {ticker} {metric}: {best_method} (RMSE: {method_scores[best_method]:.2f})")
            
            return best_method
            
        except Exception as e:
            LOGGER.warning(f"Cross-validation method selection failed: {e}, using simple heuristic")
            return self._select_best_method_simple()
    
    def _select_best_method_simple(
        self
    ) -> Literal["arima", "prophet", "ets", "lstm", "transformer"]:
        """
        Simple heuristic method selection (fallback).
        
        Returns:
            Best method name based on simple heuristics
        """
        # Check data availability
        available_methods = []
        if self.prophet_forecaster:
            available_methods.append("prophet")
        if self.arima_forecaster:
            available_methods.append("arima")
        if self.ets_forecaster:
            available_methods.append("ets")
        if self.lstm_forecaster:
            available_methods.append("lstm")
        if self.transformer_forecaster:
            available_methods.append("transformer")
        
        if not available_methods:
            raise ValueError("No forecasting methods available")
        
        # Default preference: Prophet > ARIMA > ETS > LSTM > Transformer
        if "prophet" in available_methods:
            return "prophet"
        elif "arima" in available_methods:
            return "arima"
        elif "ets" in available_methods:
            return "ets"
        elif "lstm" in available_methods:
            return "lstm"
        else:
            return "transformer"


def get_ml_forecaster(db_path: str) -> MLForecaster:
    """Factory function to create MLForecaster instance."""
    return MLForecaster(db_path)

