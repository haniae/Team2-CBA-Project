"""
Backtesting Framework for ML Forecasting

Provides walk-forward backtesting and performance evaluation for forecasting models.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from .validation import ModelValidator, ValidationMetrics
from .ml_forecaster import MLForecaster

LOGGER = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    model_name: str
    ticker: str
    metric: str
    train_periods: int
    test_periods: int
    num_folds: int
    metrics: ValidationMetrics
    fold_metrics: List[ValidationMetrics]
    avg_metrics: ValidationMetrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_name": self.model_name,
            "ticker": self.ticker,
            "metric": self.metric,
            "train_periods": self.train_periods,
            "test_periods": self.test_periods,
            "num_folds": self.num_folds,
            "metrics": self.metrics.to_dict(),
            "avg_metrics": self.avg_metrics.to_dict(),
            "fold_metrics": [m.to_dict() for m in self.fold_metrics],
        }


class BacktestRunner:
    """
    Runs backtests on forecasting models.
    
    Provides:
    - Walk-forward validation
    - Model comparison
    - Performance metrics
    - Statistical significance testing
    """
    
    def __init__(self, database_path: str):
        """
        Initialize backtest runner.
        
        Args:
            database_path: Path to SQLite database
        """
        self.database_path = database_path
        self.validator = ModelValidator()
        self.ml_forecaster = MLForecaster(database_path)
    
    def run_backtest(
        self,
        ticker: str,
        metric: str,
        train_periods: int = 5,
        test_periods: int = 2,
        models: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, BacktestResult]:
        """
        Run backtest on forecasting models.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast
            train_periods: Number of periods for training
            test_periods: Number of periods for testing
            models: List of models to test (default: all available)
            metrics: List of metrics to calculate (default: all)
            **kwargs: Additional arguments for forecasters
            
        Returns:
            Dictionary mapping model names to BacktestResult
        """
        if models is None:
            models = ["arima", "prophet", "ets"]
            # Add deep learning models if available
            if self.ml_forecaster.lstm_forecaster:
                models.append("lstm")
            if self.ml_forecaster.transformer_forecaster:
                models.append("transformer")
        
        if metrics is None:
            metrics = ["mae", "rmse", "mape", "direction_accuracy"]
        
        # Fetch historical data
        records = self._fetch_metric_records(ticker, metric)
        if not records or len(records) < train_periods + test_periods:
            LOGGER.warning(f"Insufficient data for backtest: {len(records) if records else 0} records")
            return {}
        
        # Convert to time series
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['period'])
        df = df.sort_values('date')
        
        ts = pd.Series(
            data=df['value'].values,
            index=df['date'].values,
            name=f"{ticker}_{metric}"
        )
        
        results = {}
        
        # Test each model
        for model_name in models:
            try:
                result = self._backtest_model(
                    ticker=ticker,
                    metric=metric,
                    model_name=model_name,
                    train_periods=train_periods,
                    test_periods=test_periods,
                    ts=ts,
                    **kwargs
                )
                
                if result:
                    results[model_name] = result
                    
            except Exception as e:
                LOGGER.warning(f"Backtest failed for {model_name}: {e}")
                continue
        
        return results
    
    def _backtest_model(
        self,
        ticker: str,
        metric: str,
        model_name: str,
        train_periods: int,
        test_periods: int,
        ts: pd.Series,
        **kwargs
    ) -> Optional[BacktestResult]:
        """
        Backtest a single model.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast
            model_name: Name of model to test
            train_periods: Number of periods for training
            test_periods: Number of periods for testing
            ts: Time series data
            **kwargs: Additional arguments
            
        Returns:
            BacktestResult or None if failed
        """
        fold_metrics = []
        all_actual = []
        all_predicted = []
        
        # Walk-forward validation
        num_folds = 0
        for i in range(len(ts) - train_periods - test_periods + 1):
            train_data = ts.iloc[i:i + train_periods]
            test_data = ts.iloc[i + train_periods:i + train_periods + test_periods]
            
            try:
                # Generate forecast
                forecast = self.ml_forecaster.forecast(
                    ticker=ticker,
                    metric=metric,
                    periods=test_periods,
                    method=model_name,
                    **kwargs
                )
                
                if forecast is None:
                    continue
                
                # Extract predictions
                predicted = forecast.predicted_values[:test_periods]
                
                # Calculate metrics for this fold
                fold_metric = self.validator.calculate_metrics(
                    actual=test_data.tolist(),
                    predicted=predicted
                )
                
                fold_metrics.append(fold_metric)
                all_actual.extend(test_data.tolist())
                all_predicted.extend(predicted)
                num_folds += 1
                
            except Exception as e:
                LOGGER.warning(f"Backtest fold {i} failed for {model_name}: {e}")
                continue
        
        if not fold_metrics:
            return None
        
        # Calculate average metrics across folds
        avg_metrics = ValidationMetrics(
            mae=np.mean([m.mae for m in fold_metrics]),
            rmse=np.mean([m.rmse for m in fold_metrics]),
            mape=np.mean([m.mape for m in fold_metrics]),
            direction_accuracy=np.mean([m.direction_accuracy for m in fold_metrics]),
            mean_error=np.mean([m.mean_error for m in fold_metrics]),
            std_error=np.mean([m.std_error for m in fold_metrics]),
        )
        
        # Overall metrics
        overall_metrics = self.validator.calculate_metrics(all_actual, all_predicted)
        
        return BacktestResult(
            model_name=model_name,
            ticker=ticker,
            metric=metric,
            train_periods=train_periods,
            test_periods=test_periods,
            num_folds=num_folds,
            metrics=overall_metrics,
            fold_metrics=fold_metrics,
            avg_metrics=avg_metrics,
        )
    
    def _fetch_metric_records(
        self,
        ticker: str,
        metric: str
    ) -> List[Dict[str, Any]]:
        """Fetch metric records from database."""
        # Use the MLForecaster's method to fetch records
        try:
            # Access the underlying forecasters to fetch records
            if self.ml_forecaster.arima_forecaster:
                return self.ml_forecaster.arima_forecaster._fetch_metric_records(ticker, metric)
            elif self.ml_forecaster.prophet_forecaster:
                return self.ml_forecaster.prophet_forecaster._fetch_metric_records(ticker, metric)
            elif self.ml_forecaster.ets_forecaster:
                return self.ml_forecaster.ets_forecaster._fetch_metric_records(ticker, metric)
            else:
                LOGGER.warning(f"No forecasters available to fetch records for {ticker} {metric}")
                return []
        except Exception as e:
            LOGGER.warning(f"Failed to fetch metric records: {e}")
            return []


def get_backtest_runner(database_path: str) -> BacktestRunner:
    """Factory function to create BacktestRunner instance."""
    return BacktestRunner(database_path)

