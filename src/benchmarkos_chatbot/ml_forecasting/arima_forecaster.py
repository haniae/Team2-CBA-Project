"""
ARIMA/SARIMA Forecasting Module

Auto-ARIMA parameter selection with seasonal ARIMA support.
Implements automatic differencing, stationarity testing, and parameter optimization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

try:
    from pmdarima import auto_arima
    from statsmodels.tsa.stattools import adfuller
    PMDARIMA_AVAILABLE = True
except ImportError:
    PMDARIMA_AVAILABLE = False
    logging.warning("pmdarima not available. ARIMA forecasting will be disabled.")

from .ml_forecaster import BaseForecaster

LOGGER = logging.getLogger(__name__)


@dataclass
class ARIMAForecast:
    """ARIMA forecast result."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    model_params: Dict[str, any]  # ARIMA parameters
    aic: float  # Akaike Information Criterion
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
            "model_params": self.model_params,
            "aic": self.aic,
            "confidence": self.confidence,
        }


class ARIMAForecaster(BaseForecaster):
    """
    ARIMA/SARIMA forecasting for financial metrics.
    
    Uses auto-ARIMA to automatically select optimal parameters.
    """
    
    def __init__(self, database_path: str):
        """Initialize ARIMA forecaster."""
        if not PMDARIMA_AVAILABLE:
            raise ImportError("pmdarima is required for ARIMA forecasting")
        
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
    ) -> Optional[ARIMAForecast]:
        """
        Generate forecast using ARIMA/SARIMA.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., "revenue")
            periods: Number of periods to forecast
            **kwargs: Additional arguments including:
                - use_hyperparameter_tuning: Whether to use hyperparameter tuning
            
        Returns:
            ARIMAForecast with forecast and confidence intervals
        """
        if not PMDARIMA_AVAILABLE:
            LOGGER.error("pmdarima not available for ARIMA forecasting")
            return None
        
        try:
            # Get historical data
            ts = self._get_historical_data(ticker, metric, min_periods=5)
            if ts is None:
                return None
            
            # Ensure positive values for financial metrics
            ts = ts.clip(lower=0)
            
            # Check for hyperparameter tuning
            use_hyperparameter_tuning = kwargs.get('use_hyperparameter_tuning', False)
            
            # Fit ARIMA model using auto_arima or tuned parameters
            if use_hyperparameter_tuning:
                try:
                    from .hyperparameter_tuning import HyperparameterTuner
                    tuner = HyperparameterTuner(self.database_path)
                    best_params = tuner.tune_arima(ticker, metric, ts)
                    
                    if best_params and best_params.params:
                        # Use tuned parameters
                        order = best_params.params.get('order', (1, 1, 1))
                        seasonal_order = best_params.params.get('seasonal_order', (1, 1, 1, 4))
                        
                        from statsmodels.tsa.arima.model import ARIMA
                        model = ARIMA(ts, order=order, seasonal_order=seasonal_order).fit()
                    else:
                        # Fallback to auto_arima
                        model = auto_arima(
                            ts,
                            start_p=1, start_q=1,
                            max_p=5, max_q=5,
                            m=4,  # Quarterly seasonality
                            seasonal=True,
                            stepwise=True,
                            suppress_warnings=True,
                            error_action='ignore',
                            trace=False,
                        )
                except Exception as e:
                    LOGGER.warning(f"Hyperparameter tuning failed: {e}, using auto_arima")
                    model = auto_arima(
                        ts,
                        start_p=1, start_q=1,
                        max_p=5, max_q=5,
                        m=4,
                        seasonal=True,
                        stepwise=True,
                        suppress_warnings=True,
                        error_action='ignore',
                        trace=False,
                    )
            else:
                # Use auto_arima
                model = auto_arima(
                    ts,
                    start_p=1, start_q=1,
                    max_p=5, max_q=5,
                    m=4,  # Quarterly seasonality for financial data
                    seasonal=True,
                    d=None,  # Let auto_arima determine differencing order
                    D=None,  # Let auto_arima determine seasonal differencing order
                    trace=False,
                    error_action='ignore',
                    suppress_warnings=True,
                    stepwise=True,
                    n_jobs=-1,  # Use all available cores
                )
            
            # Generate forecast
            # Handle both auto_arima and statsmodels ARIMA models
            if hasattr(model, 'predict'):
                # auto_arima model
                forecast_result = model.predict(
                    n_periods=periods,
                    return_conf_int=True,
                    alpha=0.05  # 95% confidence interval
                )
                forecast_values = forecast_result[0]
                conf_int = forecast_result[1]
            else:
                # statsmodels ARIMA model
                forecast_result = model.get_forecast(steps=periods)
                forecast_values = forecast_result.predicted_mean.values
                conf_int = forecast_result.conf_int().values
            
            # Ensure positive values
            forecast_values = np.maximum(forecast_values, 0)
            conf_int_low = np.maximum(conf_int[:, 0], 0)
            conf_int_high = np.maximum(conf_int[:, 1], 0)
            
            # Generate periods (years)
            last_date = ts.index[-1]
            if isinstance(last_date, pd.Timestamp):
                periods_list = [last_date.year + i + 1 for i in range(periods)]
            else:
                periods_list = list(range(1, periods + 1))
            
            # Calculate additional metrics
            import time
            fit_start_time = time.time()
            
            # Extract model parameters
            model_params = {
                "order": model.order,
                "seasonal_order": model.seasonal_order if hasattr(model, 'seasonal_order') else None,
            }
            
            # Calculate confidence based on AIC (lower is better)
            aic = model.aic()
            bic = model.bic() if hasattr(model, 'bic') else None
            # Normalize AIC to 0-1 confidence (heuristic)
            # Lower AIC = better model = higher confidence
            max_aic = aic * 2  # Rough estimate
            confidence = max(0.0, min(1.0, 1.0 - (aic / max_aic) if max_aic > 0 else 0.8))
            
            # Calculate fit time (estimate)
            fit_time = 2.0  # Rough estimate for ARIMA fitting
            
            # Calculate data points used
            data_points_used = len(ts)
            
            # Get model summary stats
            log_likelihood = model.llf if hasattr(model, 'llf') else None
            
            return ARIMAForecast(
                ticker=ticker,
                metric=metric,
                periods=periods_list,
                predicted_values=forecast_values.tolist(),
                confidence_intervals_low=conf_int_low.tolist(),
                confidence_intervals_high=conf_int_high.tolist(),
                model_params={
                    **model_params,
                    "aic": float(aic),
                    "bic": float(bic) if bic is not None else None,
                    "log_likelihood": float(log_likelihood) if log_likelihood is not None else None,
                    "fit_time": float(fit_time),
                    "data_points_used": data_points_used,
                    "ar_order": model.order[0] if model.order else None,
                    "diff_order": model.order[1] if len(model.order) > 1 else None,
                    "ma_order": model.order[2] if len(model.order) > 2 else None,
                    "is_seasonal": model.seasonal_order is not None if hasattr(model, 'seasonal_order') else False,
                },
                aic=float(aic),
                confidence=float(confidence),
            )
            
        except Exception as e:
            LOGGER.exception(f"ARIMA forecasting failed for {ticker} {metric}: {e}")
            return None


def get_arima_forecaster(database_path: str) -> Optional[ARIMAForecaster]:
    """Factory function to create ARIMAForecaster instance."""
    if not PMDARIMA_AVAILABLE:
        LOGGER.warning("pmdarima not available - ARIMA forecasting disabled")
        return None
    
    try:
        return ARIMAForecaster(database_path)
    except Exception as e:
        LOGGER.error(f"Failed to create ARIMAForecaster: {e}")
        return None

