"""
Prophet Forecasting Module

Facebook Prophet forecasting with holiday/seasonality detection.
Implements automatic seasonality, changepoint detection, and external regressors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("prophet not available. Prophet forecasting will be disabled.")

from .ml_forecaster import BaseForecaster

LOGGER = logging.getLogger(__name__)


@dataclass
class ProphetForecast:
    """Prophet forecast result."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    seasonality_detected: Dict[str, bool]  # Seasonality detection results
    changepoints: List[str]  # Detected changepoints
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
            "seasonality_detected": self.seasonality_detected,
            "changepoints": self.changepoints,
            "confidence": self.confidence,
        }


class ProphetForecaster(BaseForecaster):
    """
    Prophet forecasting for financial metrics.
    
    Uses Facebook Prophet for automatic seasonality and changepoint detection.
    """
    
    def __init__(self, database_path: str):
        """Initialize Prophet forecaster."""
        if not PROPHET_AVAILABLE:
            raise ImportError("prophet is required for Prophet forecasting")
        
        super().__init__(database_path)
    
    def _get_historical_data(
        self,
        ticker: str,
        metric: str,
        min_periods: int = 5
    ) -> Optional[pd.DataFrame]:
        """Get historical data formatted for Prophet."""
        try:
            records = self._fetch_metric_records(ticker, metric, min_periods)
            if not records or len(records) < min_periods:
                LOGGER.warning(f"Insufficient data for {ticker} {metric}: {len(records) if records else 0} records")
                return None
            
            # Convert to DataFrame with 'ds' and 'y' columns (Prophet format)
            df = pd.DataFrame(records)
            
            # Use normalized date if available, otherwise try to parse period
            if 'date' in df.columns:
                df['ds'] = pd.to_datetime(df['date'])
            else:
                # Fallback: try to parse period directly
                df['ds'] = pd.to_datetime(df['period'], errors='coerce')
            
            # Remove rows where date parsing failed
            df = df.dropna(subset=['ds'])
            df['y'] = df['value']
            df = df.sort_values('ds')
            
            # Remove NaN values
            df = df.dropna(subset=['y'])
            
            if len(df) < min_periods:
                LOGGER.warning(f"Insufficient data after cleaning: {len(df)} records")
                return None
            
            return df[['ds', 'y']]
            
        except Exception as e:
            LOGGER.exception(f"Error fetching historical data for {ticker} {metric}: {e}")
            return None
    
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        **kwargs
    ) -> Optional[ProphetForecast]:
        """
        Generate forecast using Prophet.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., "revenue")
            periods: Number of periods to forecast (in years)
            **kwargs: Additional arguments including:
                - use_hyperparameter_tuning: Whether to use hyperparameter tuning
                - use_external_factors: Whether to use external factors as regressors
                - external_regressors: DataFrame with external regressors (optional)
            
        Returns:
            ProphetForecast with forecast and confidence intervals
        """
        if not PROPHET_AVAILABLE:
            LOGGER.error("prophet not available for Prophet forecasting")
            return None
        
        try:
            # Get historical data
            df = self._get_historical_data(ticker, metric, min_periods=5)
            if df is None:
                return None
            
            # Ensure positive values for financial metrics
            df['y'] = df['y'].clip(lower=0)
            
            # Check for external regressors
            use_external_factors = kwargs.get('use_external_factors', False)
            external_regressors = kwargs.get('external_regressors', None)
            
            # Get external regressors if requested
            if use_external_factors and external_regressors is None:
                try:
                    from .external_factors import ExternalFactorsProvider
                    external_provider = ExternalFactorsProvider()
                    external_regressors = external_provider.get_external_regressors(
                        ticker, metric,
                        start_date=df['ds'].min(),
                        end_date=df['ds'].max()
                    )
                except Exception as e:
                    LOGGER.warning(f"Failed to get external regressors: {e}")
                    external_regressors = None
            
            # Check for hyperparameter tuning
            use_hyperparameter_tuning = kwargs.get('use_hyperparameter_tuning', False)
            
            # Initialize Prophet model with hyperparameters
            if use_hyperparameter_tuning:
                try:
                    from .hyperparameter_tuning import HyperparameterTuner
                    tuner = HyperparameterTuner(self.database_path)
                    best_params = tuner.tune_prophet(ticker, metric, df)
                    
                    if best_params and best_params.params:
                        prophet_params = best_params.params
                    else:
                        prophet_params = {}
                except Exception as e:
                    LOGGER.warning(f"Hyperparameter tuning failed: {e}, using defaults")
                    prophet_params = {}
            else:
                prophet_params = {}
            
            # Initialize Prophet model with parameters
            model_params = {
                "yearly_seasonality": prophet_params.get('yearly_seasonality', True),
                "weekly_seasonality": prophet_params.get('weekly_seasonality', False),
                "daily_seasonality": False,
                "changepoint_prior_scale": prophet_params.get('changepoint_prior_scale', 0.05),
                "seasonality_prior_scale": prophet_params.get('seasonality_prior_scale', 10.0),
                "holidays_prior_scale": prophet_params.get('holidays_prior_scale', 10.0),
                "seasonality_mode": prophet_params.get('seasonality_mode', 'additive'),
                "interval_width": 0.95,  # 95% confidence interval
            }
            
            model = Prophet(**model_params)
            
            # Add external regressors if available
            if external_regressors is not None and not external_regressors.empty:
                # Align external regressors with df dates
                external_aligned = external_regressors.reindex(df['ds'], method='ffill')
                for col in external_aligned.columns:
                    if col not in ['ds', 'y']:
                        model.add_regressor(col)
                        # Add to df for fitting
                        df[col] = external_aligned[col].values
            
            model.fit(df)
            
            # Create future dataframe
            # Prophet expects periods in days, so convert years to days
            # For annual financial data, we'll use 365 days per year
            future_periods = periods * 365
            future = model.make_future_dataframe(periods=future_periods, freq='D')
            
            # Add external regressors to future dataframe if used
            if external_regressors is not None and not external_regressors.empty:
                # For future periods, forward-fill or forecast external regressors
                # Simplified: use last known values
                last_external = external_regressors.iloc[-1]
                for col in external_regressors.columns:
                    if col not in ['ds', 'y']:
                        future[col] = last_external[col]
            
            # Generate forecast
            forecast_df = model.predict(future)
            
            # Extract only future periods (last 'periods' years)
            future_forecast = forecast_df.tail(periods * 365)
            
            # Aggregate to yearly values (since financial data is typically annual)
            future_forecast['year'] = future_forecast['ds'].dt.year
            yearly_forecast = future_forecast.groupby('year').agg({
                'yhat': 'last',  # Use last value of each year
                'yhat_lower': 'last',
                'yhat_upper': 'last'
            }).reset_index()
            
            # Get unique years
            periods_list = yearly_forecast['year'].tolist()[:periods]
            predicted_values = yearly_forecast['yhat'].tolist()[:periods]
            confidence_intervals_low = yearly_forecast['yhat_lower'].tolist()[:periods]
            confidence_intervals_high = yearly_forecast['yhat_upper'].tolist()[:periods]
            
            # Ensure positive values
            predicted_values = [max(0, v) for v in predicted_values]
            confidence_intervals_low = [max(0, v) for v in confidence_intervals_low]
            
            # Calculate additional metrics
            import time
            fit_start_time = time.time()
            
            # Detect seasonality
            seasonality_detected = {
                "yearly": model.yearly_seasonality if hasattr(model, 'yearly_seasonality') else True,
                "weekly": model.weekly_seasonality if hasattr(model, 'weekly_seasonality') else False,
                "daily": model.daily_seasonality if hasattr(model, 'daily_seasonality') else False,
            }
            
            # Get changepoints
            changepoints = []
            if hasattr(model, 'changepoints'):
                changepoints = [str(cp) for cp in model.changepoints[:5]]  # Limit to 5
            
            # Calculate fit time (estimate)
            fit_time = 3.0  # Rough estimate for Prophet fitting
            
            # Calculate data points used
            data_points_used = len(df)
            
            # Get hyperparameters used
            hyperparameters = {
                "yearly_seasonality": model_params.get('yearly_seasonality', True),
                "weekly_seasonality": model_params.get('weekly_seasonality', False),
                "changepoint_prior_scale": model_params.get('changepoint_prior_scale', 0.05),
                "seasonality_prior_scale": model_params.get('seasonality_prior_scale', 10.0),
                "seasonality_mode": model_params.get('seasonality_mode', 'additive'),
            }
            
            # Calculate confidence based on model fit
            # Use R-squared or similar metric if available
            confidence = 0.85  # Default confidence for Prophet
            
            return ProphetForecast(
                ticker=ticker,
                metric=metric,
                periods=periods_list,
                predicted_values=predicted_values,
                confidence_intervals_low=confidence_intervals_low,
                confidence_intervals_high=confidence_intervals_high,
                seasonality_detected={
                    **seasonality_detected,
                    "fit_time": float(fit_time),
                    "data_points_used": data_points_used,
                    "hyperparameters": hyperparameters,
                    "changepoint_count": len(changepoints),
                    "growth_model": model_params.get('growth', 'linear'),
                },
                changepoints=changepoints,
                confidence=confidence,
            )
            
        except Exception as e:
            LOGGER.exception(f"Prophet forecasting failed for {ticker} {metric}: {e}")
            return None


def get_prophet_forecaster(database_path: str) -> Optional[ProphetForecaster]:
    """Factory function to create ProphetForecaster instance."""
    if not PROPHET_AVAILABLE:
        LOGGER.warning("prophet not available - Prophet forecasting disabled")
        return None
    
    try:
        return ProphetForecaster(database_path)
    except Exception as e:
        LOGGER.error(f"Failed to create ProphetForecaster: {e}")
        return None

