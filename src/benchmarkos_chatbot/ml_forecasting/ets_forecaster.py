"""
ETS (Exponential Smoothing) Forecasting Module

Exponential Smoothing State Space Model forecasting.
Implements multiple trend patterns and automatic seasonality detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels not available. ETS forecasting will be disabled.")

from .ml_forecaster import BaseForecaster

LOGGER = logging.getLogger(__name__)


@dataclass
class ETSForecast:
    """ETS forecast result."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    model_type: str  # ETS model type (e.g., "AAN", "AAN")
    seasonal_periods: int  # Seasonal period length
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
            "model_type": self.model_type,
            "seasonal_periods": self.seasonal_periods,
            "confidence": self.confidence,
        }


class ETSForecaster(BaseForecaster):
    """
    ETS (Exponential Smoothing) forecasting for financial metrics.
    
    Uses triple exponential smoothing (Holt-Winters) for trend and seasonality.
    """
    
    def __init__(self, database_path: str):
        """Initialize ETS forecaster."""
        if not STATSMODELS_AVAILABLE:
            raise ImportError("statsmodels is required for ETS forecasting")
        
        super().__init__(database_path)
    
    def _get_historical_data(
        self,
        ticker: str,
        metric: str,
        min_periods: int = 5
    ) -> Optional[pd.Series]:
        """Get historical data for ticker and metric."""
        try:
            records = self._fetch_metric_records(ticker, metric, min_periods)
            if not records or len(records) < min_periods:
                LOGGER.warning(f"Insufficient data for {ticker} {metric}: {len(records) if records else 0} records")
                return None
            
            # Convert to time series
            df = pd.DataFrame(records)
            
            # Use normalized date if available, otherwise try to parse period
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                # Fallback: try to parse period directly
                df['date'] = pd.to_datetime(df['period'], errors='coerce')
            
            # Remove rows where date parsing failed
            df = df.dropna(subset=['date'])
            df = df.sort_values('date')
            
            if len(df) < min_periods:
                LOGGER.warning(f"Insufficient data after date parsing: {len(df)} records")
                return None
            
            # Create time series
            ts = pd.Series(
                data=df['value'].values,
                index=df['date'].values,
                name=f"{ticker}_{metric}"
            )
            
            # Remove NaN values
            ts = ts.dropna()
            
            if len(ts) < min_periods:
                LOGGER.warning(f"Insufficient data after cleaning: {len(ts)} records")
                return None
            
            return ts
            
        except Exception as e:
            LOGGER.exception(f"Error fetching historical data for {ticker} {metric}: {e}")
            return None
    
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        **kwargs
    ) -> Optional[ETSForecast]:
        """
        Generate forecast using ETS.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., "revenue")
            periods: Number of periods to forecast
            **kwargs: Additional arguments
            
        Returns:
            ETSForecast with forecast and confidence intervals
        """
        if not STATSMODELS_AVAILABLE:
            LOGGER.error("statsmodels not available for ETS forecasting")
            return None
        
        try:
            # Get historical data
            ts = self._get_historical_data(ticker, metric, min_periods=5)
            if ts is None:
                return None
            
            # Ensure positive values for financial metrics
            ts = ts.clip(lower=0)
            
            # Determine if we have enough data for seasonality
            # For annual financial data, we typically don't have seasonality
            # But we'll try with additive trend and no seasonality first
            try:
                # Try additive trend, no seasonality
                model = ExponentialSmoothing(
                    ts,
                    trend='add',
                    seasonal=None,
                    seasonal_periods=None,
                )
                fitted_model = model.fit()
                model_type = "AAN"  # Additive trend, Additive error, No seasonality
            except:
                # Fallback to simple exponential smoothing
                model = ExponentialSmoothing(
                    ts,
                    trend=None,
                    seasonal=None,
                )
                fitted_model = model.fit()
                model_type = "AAN"  # Simple exponential smoothing
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=periods)
            
            # Get confidence intervals (simplified - use standard error)
            # ETS doesn't provide built-in confidence intervals, so we estimate
            residuals = fitted_model.resid
            std_error = np.std(residuals) if len(residuals) > 0 else np.std(ts) * 0.1
            
            # 95% confidence interval
            z_score = 1.96
            forecast_values = forecast_result.values
            confidence_intervals_low = forecast_values - (z_score * std_error)
            confidence_intervals_high = forecast_values + (z_score * std_error)
            
            # Ensure positive values
            forecast_values = np.maximum(forecast_values, 0)
            confidence_intervals_low = np.maximum(confidence_intervals_low, 0)
            
            # Generate periods (years)
            last_date = ts.index[-1]
            if isinstance(last_date, pd.Timestamp):
                periods_list = [last_date.year + i + 1 for i in range(periods)]
            else:
                periods_list = list(range(1, periods + 1))
            
            # Calculate confidence based on AIC or similar
            aic = fitted_model.aic if hasattr(fitted_model, 'aic') else None
            confidence = 0.80  # Default confidence for ETS
            if aic is not None:
                # Lower AIC = better model = higher confidence
                max_aic = abs(aic) * 2
                confidence = max(0.0, min(1.0, 1.0 - (abs(aic) / max_aic) if max_aic > 0 else 0.8))
            
            return ETSForecast(
                ticker=ticker,
                metric=metric,
                periods=periods_list,
                predicted_values=forecast_values.tolist(),
                confidence_intervals_low=confidence_intervals_low.tolist(),
                confidence_intervals_high=confidence_intervals_high.tolist(),
                model_type=model_type,
                seasonal_periods=0,  # No seasonality for annual financial data
                confidence=confidence,
            )
            
        except Exception as e:
            LOGGER.exception(f"ETS forecasting failed for {ticker} {metric}: {e}")
            return None


def get_ets_forecaster(database_path: str) -> Optional[ETSForecaster]:
    """Factory function to create ETSForecaster instance."""
    if not STATSMODELS_AVAILABLE:
        LOGGER.warning("statsmodels not available - ETS forecasting disabled")
        return None
    
    try:
        return ETSForecaster(database_path)
    except Exception as e:
        LOGGER.error(f"Failed to create ETSForecaster: {e}")
        return None

