"""
Multi-Variate Forecasting Module

Provides multi-variate forecasting capabilities for forecasting multiple
related metrics simultaneously (e.g., revenue and net income together).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

try:
    from statsmodels.tsa.vector_ar.var_model import VAR
    VAR_AVAILABLE = True
except ImportError:
    VAR_AVAILABLE = False
    logging.warning("statsmodels VAR not available - multi-variate forecasting will be limited")

LOGGER = logging.getLogger(__name__)


@dataclass
class MultivariateForecast:
    """Multi-variate forecast result."""
    ticker: str
    metrics: List[str]  # List of metrics forecasted
    periods: List[int]  # Years to forecast
    predicted_values: Dict[str, List[float]]  # Dict mapping metric to predictions
    confidence_intervals_low: Dict[str, List[float]]
    confidence_intervals_high: Dict[str, List[float]]
    correlations: Dict[str, float]  # Correlations between metrics
    method: str  # Method used ('var', 'multivariate_lstm', 'multivariate_transformer')
    model_details: Dict
    confidence: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "metrics": self.metrics,
            "periods": self.periods,
            "predicted_values": self.predicted_values,
            "confidence_intervals": {
                "low": self.confidence_intervals_low,
                "high": self.confidence_intervals_high,
            },
            "correlations": self.correlations,
            "method": self.method,
            "model_details": self.model_details,
            "confidence": self.confidence,
        }


class MultivariateForecaster:
    """
    Multi-variate forecasting for financial metrics.
    
    Supports:
    - Vector ARIMA (VARIMA/VAR) for statistical models
    - Multi-variate LSTM/GRU for deep learning
    - Multi-variate Transformer
    """
    
    def __init__(self, database_path: str):
        """
        Initialize multi-variate forecaster.
        
        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
    
    def forecast_var(
        self,
        ticker: str,
        metrics: List[str],
        periods: int = 3,
        maxlags: int = 4
    ) -> Optional[MultivariateForecast]:
        """
        Forecast using Vector ARIMA (VAR).
        
        Args:
            ticker: Company ticker
            metrics: List of metrics to forecast together
            periods: Number of periods to forecast
            maxlags: Maximum lag order
            
        Returns:
            MultivariateForecast or None if fails
        """
        if not VAR_AVAILABLE:
            LOGGER.warning("VAR not available for multi-variate forecasting")
            return None
        
        try:
            # Fetch data for all metrics
            from .ml_forecaster import BaseForecaster
            
            # Use BaseForecaster to fetch data
            class TempForecaster(BaseForecaster):
                def forecast(self, ticker, metric, periods, **kwargs):
                    pass
            
            temp_forecaster = TempForecaster(self.database_path)
            
            # Get historical data for all metrics
            data_dict = {}
            for metric in metrics:
                records = temp_forecaster._fetch_metric_records(ticker, metric)
                if not records:
                    LOGGER.warning(f"No data for {ticker} {metric}")
                    return None
                
                df = pd.DataFrame(records)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                else:
                    df['date'] = pd.to_datetime(df['period'], errors='coerce')
                
                df = df.dropna(subset=['date'])
                df = df.sort_values('date')
                
                data_dict[metric] = pd.Series(
                    data=df['value'].values,
                    index=df['date'],
                    name=f"{ticker}_{metric}"
                )
            
            # Align all series to common index
            common_index = None
            for metric, series in data_dict.items():
                if common_index is None:
                    common_index = series.index
                else:
                    common_index = common_index.intersection(series.index)
            
            if len(common_index) < maxlags + 2:
                LOGGER.warning(f"Insufficient common data for VAR: {len(common_index)} points")
                return None
            
            # Create aligned DataFrame
            aligned_data = pd.DataFrame(index=common_index)
            for metric in metrics:
                aligned_data[metric] = data_dict[metric].loc[common_index]
            
            # Remove NaN values
            aligned_data = aligned_data.dropna()
            
            if len(aligned_data) < maxlags + 2:
                LOGGER.warning(f"Insufficient data after alignment: {len(aligned_data)} points")
                return None
            
            # Fit VAR model
            model = VAR(aligned_data)
            var_result = model.fit(maxlags=maxlags, ic='aic')
            
            # Forecast
            forecast = var_result.forecast(aligned_data.values[-var_result.k_ar:], steps=periods)
            
            # Calculate confidence intervals (simplified)
            forecast_std = np.std(aligned_data.values, axis=0)
            
            # Prepare results
            predicted_values = {}
            confidence_intervals_low = {}
            confidence_intervals_high = {}
            
            for i, metric in enumerate(metrics):
                predicted_values[metric] = forecast[:, i].tolist()
                confidence_intervals_low[metric] = (forecast[:, i] - 1.96 * forecast_std[i]).tolist()
                confidence_intervals_high[metric] = (forecast[:, i] + 1.96 * forecast_std[i]).tolist()
            
            # Calculate correlations
            correlations = {}
            for i, metric1 in enumerate(metrics):
                for j, metric2 in enumerate(metrics):
                    if i < j:
                        corr = np.corrcoef(aligned_data[metric1], aligned_data[metric2])[0, 1]
                        correlations[f"{metric1}_{metric2}"] = float(corr)
            
            # Model details
            model_details = {
                "lag_order": var_result.k_ar,
                "aic": float(var_result.aic),
                "bic": float(var_result.bic),
                "fpe": float(var_result.fpe),
            }
            
            return MultivariateForecast(
                ticker=ticker,
                metrics=metrics,
                periods=list(range(1, periods + 1)),
                predicted_values=predicted_values,
                confidence_intervals_low=confidence_intervals_low,
                confidence_intervals_high=confidence_intervals_high,
                correlations=correlations,
                method="var",
                model_details=model_details,
                confidence=0.8,  # Default confidence
            )
            
        except Exception as e:
            LOGGER.warning(f"VAR forecasting failed: {e}")
            return None
    
    def forecast_multivariate_lstm(
        self,
        ticker: str,
        metrics: List[str],
        periods: int = 3,
        **kwargs
    ) -> Optional[MultivariateForecast]:
        """
        Forecast using multi-variate LSTM.
        
        Args:
            ticker: Company ticker
            metrics: List of metrics to forecast together
            periods: Number of periods to forecast
            **kwargs: Additional arguments for LSTM
            
        Returns:
            MultivariateForecast or None if fails
        """
        try:
            import tensorflow as tf
            from tensorflow import keras
            from sklearn.preprocessing import MinMaxScaler
            
            # Fetch and prepare data (similar to VAR)
            from .ml_forecaster import BaseForecaster
            
            class TempForecaster(BaseForecaster):
                def forecast(self, ticker, metric, periods, **kwargs):
                    pass
            
            temp_forecaster = TempForecaster(self.database_path)
            
            # Get historical data for all metrics
            data_dict = {}
            for metric in metrics:
                records = temp_forecaster._fetch_metric_records(ticker, metric)
                if not records:
                    return None
                
                df = pd.DataFrame(records)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                else:
                    df['date'] = pd.to_datetime(df['period'], errors='coerce')
                
                df = df.dropna(subset=['date'])
                df = df.sort_values('date')
                
                data_dict[metric] = pd.Series(
                    data=df['value'].values,
                    index=df['date'],
                    name=f"{ticker}_{metric}"
                )
            
            # Align all series
            common_index = None
            for series in data_dict.values():
                if common_index is None:
                    common_index = series.index
                else:
                    common_index = common_index.intersection(series.index)
            
            aligned_data = pd.DataFrame(index=common_index)
            for metric in metrics:
                aligned_data[metric] = data_dict[metric].loc[common_index]
            
            aligned_data = aligned_data.dropna()
            
            if len(aligned_data) < 20:
                LOGGER.warning(f"Insufficient data for multi-variate LSTM: {len(aligned_data)} points")
                return None
            
            # Scale data
            scaler = MinMaxScaler()
            scaled_data = scaler.fit_transform(aligned_data.values)
            
            # Prepare sequences
            lookback = kwargs.get('lookback', 12)
            X, y = [], []
            for i in range(lookback, len(scaled_data)):
                X.append(scaled_data[i-lookback:i])
                y.append(scaled_data[i])
            
            X, y = np.array(X), np.array(y)
            
            if len(X) < 10:
                LOGGER.warning("Insufficient sequences for LSTM training")
                return None
            
            # Build model
            model = keras.Sequential([
                keras.layers.LSTM(50, return_sequences=True, input_shape=(lookback, len(metrics))),
                keras.layers.Dropout(0.2),
                keras.layers.LSTM(50, return_sequences=False),
                keras.layers.Dropout(0.2),
                keras.layers.Dense(len(metrics))
            ])
            
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            
            # Train
            model.fit(X, y, epochs=50, batch_size=32, verbose=0, validation_split=0.2)
            
            # Forecast
            last_sequence = scaled_data[-lookback:].reshape(1, lookback, len(metrics))
            forecast = []
            
            for _ in range(periods):
                pred = model.predict(last_sequence, verbose=0)
                forecast.append(pred[0])
                # Update sequence
                last_sequence = np.append(last_sequence[:, 1:, :], pred.reshape(1, 1, len(metrics)), axis=1)
            
            # Inverse transform
            forecast_array = np.array(forecast)
            forecast_unscaled = scaler.inverse_transform(forecast_array)
            
            # Prepare results
            predicted_values = {}
            confidence_intervals_low = {}
            confidence_intervals_high = {}
            
            forecast_std = np.std(aligned_data.values, axis=0)
            
            for i, metric in enumerate(metrics):
                predicted_values[metric] = forecast_unscaled[:, i].tolist()
                confidence_intervals_low[metric] = (forecast_unscaled[:, i] - 1.96 * forecast_std[i]).tolist()
                confidence_intervals_high[metric] = (forecast_unscaled[:, i] + 1.96 * forecast_std[i]).tolist()
            
            # Calculate correlations
            correlations = {}
            for i, metric1 in enumerate(metrics):
                for j, metric2 in enumerate(metrics):
                    if i < j:
                        corr = np.corrcoef(aligned_data[metric1], aligned_data[metric2])[0, 1]
                        correlations[f"{metric1}_{metric2}"] = float(corr)
            
            model_details = {
                "lookback": lookback,
                "units": 50,
                "layers": 2,
            }
            
            return MultivariateForecast(
                ticker=ticker,
                metrics=metrics,
                periods=list(range(1, periods + 1)),
                predicted_values=predicted_values,
                confidence_intervals_low=confidence_intervals_low,
                confidence_intervals_high=confidence_intervals_high,
                correlations=correlations,
                method="multivariate_lstm",
                model_details=model_details,
                confidence=0.75,
            )
            
        except Exception as e:
            LOGGER.warning(f"Multi-variate LSTM forecasting failed: {e}")
            return None


def get_multivariate_forecaster(database_path: str) -> MultivariateForecaster:
    """Factory function to create MultivariateForecaster instance."""
    return MultivariateForecaster(database_path)

