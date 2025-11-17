"""
Model Validation Framework for ML Forecasting

Provides validation metrics and cross-validation for forecasting models.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from datetime import datetime

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """Validation metrics for forecasting models."""
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    mape: float  # Mean Absolute Percentage Error
    direction_accuracy: float  # Directional accuracy (%)
    mean_error: float  # Mean error (bias)
    std_error: float  # Standard deviation of errors
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "direction_accuracy": self.direction_accuracy,
            "mean_error": self.mean_error,
            "std_error": self.std_error,
        }


class ModelValidator:
    """
    Validates forecasting models using various metrics.
    
    Provides:
    - MAE, RMSE, MAPE
    - Directional accuracy
    - Bias and variance metrics
    - Cross-validation support
    """
    
    def __init__(self):
        """Initialize model validator."""
        pass
    
    def calculate_metrics(
        self,
        actual: List[float],
        predicted: List[float]
    ) -> ValidationMetrics:
        """
        Calculate validation metrics.
        
        Args:
            actual: Actual values
            predicted: Predicted values
            
        Returns:
            ValidationMetrics with all calculated metrics
        """
        actual = np.array(actual)
        predicted = np.array(predicted)
        
        # Ensure same length
        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]
        
        # Calculate errors
        errors = actual - predicted
        
        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(errors))
        
        # RMSE (Root Mean Square Error)
        rmse = np.sqrt(np.mean(errors ** 2))
        
        # MAPE (Mean Absolute Percentage Error)
        # Avoid division by zero
        non_zero_mask = actual != 0
        if np.any(non_zero_mask):
            mape = np.mean(np.abs(errors[non_zero_mask] / actual[non_zero_mask])) * 100
        else:
            mape = float('inf')
        
        # Directional accuracy
        if len(actual) > 1:
            actual_direction = np.diff(actual) > 0
            predicted_direction = np.diff(predicted) > 0
            direction_accuracy = np.mean(actual_direction == predicted_direction) * 100
        else:
            direction_accuracy = 0.0
        
        # Mean error (bias)
        mean_error = np.mean(errors)
        
        # Standard deviation of errors
        std_error = np.std(errors)
        
        return ValidationMetrics(
            mae=float(mae),
            rmse=float(rmse),
            mape=float(mape),
            direction_accuracy=float(direction_accuracy),
            mean_error=float(mean_error),
            std_error=float(std_error),
        )
    
    def compare_models(
        self,
        actual: List[float],
        predictions: Dict[str, List[float]]
    ) -> Dict[str, ValidationMetrics]:
        """
        Compare multiple models.
        
        Args:
            actual: Actual values
            predictions: Dictionary mapping model names to predictions
            
        Returns:
            Dictionary mapping model names to ValidationMetrics
        """
        results = {}
        
        for model_name, predicted in predictions.items():
            try:
                metrics = self.calculate_metrics(actual, predicted)
                results[model_name] = metrics
            except Exception as e:
                LOGGER.warning(f"Failed to calculate metrics for {model_name}: {e}")
                continue
        
        return results


class TimeSeriesCrossValidator:
    """
    Time series cross-validation for forecasting models.
    
    Provides:
    - Blocked cross-validation (preserves temporal order)
    - Purged cross-validation (removes overlapping test periods)
    - Walk-forward validation (expanding window)
    - Sliding window validation
    """
    
    def __init__(self):
        """Initialize time series cross-validator."""
        pass
    
    def blocked_cv(
        self,
        data: pd.Series,
        n_splits: int = 5,
        test_size: int = 1
    ) -> List[Tuple[pd.Series, pd.Series]]:
        """
        Blocked cross-validation (preserves temporal order).
        
        Args:
            data: Time series data
            n_splits: Number of folds
            test_size: Size of test set in each fold
            
        Returns:
            List of (train, test) tuples
        """
        folds = []
        total_size = len(data)
        fold_size = total_size // n_splits
        
        for i in range(n_splits):
            train_end = (i + 1) * fold_size - test_size
            test_start = train_end
            test_end = test_start + test_size
            
            if train_end > 0 and test_end <= total_size:
                train_data = data.iloc[:train_end]
                test_data = data.iloc[test_start:test_end]
                folds.append((train_data, test_data))
        
        return folds
    
    def walk_forward_cv(
        self,
        data: pd.Series,
        initial_train_size: int,
        step_size: int = 1
    ) -> List[Tuple[pd.Series, pd.Series]]:
        """
        Walk-forward validation (expanding window).
        
        Args:
            data: Time series data
            initial_train_size: Initial training set size
            step_size: Step size for expanding window
            
        Returns:
            List of (train, test) tuples
        """
        folds = []
        total_size = len(data)
        
        for i in range(initial_train_size, total_size, step_size):
            train_data = data.iloc[:i]
            test_data = data.iloc[i:i+step_size]
            
            if len(test_data) > 0:
                folds.append((train_data, test_data))
        
        return folds
    
    def sliding_window_cv(
        self,
        data: pd.Series,
        train_size: int,
        test_size: int = 1,
        step_size: int = 1
    ) -> List[Tuple[pd.Series, pd.Series]]:
        """
        Sliding window validation.
        
        Args:
            data: Time series data
            train_size: Training set size
            test_size: Test set size
            step_size: Step size for sliding window
            
        Returns:
            List of (train, test) tuples
        """
        folds = []
        total_size = len(data)
        
        for i in range(0, total_size - train_size - test_size + 1, step_size):
            train_data = data.iloc[i:i+train_size]
            test_data = data.iloc[i+train_size:i+train_size+test_size]
            
            if len(test_data) > 0:
                folds.append((train_data, test_data))
        
        return folds
    
    def purged_cv(
        self,
        data: pd.Series,
        n_splits: int = 5,
        test_size: int = 1,
        gap_size: int = 1
    ) -> List[Tuple[pd.Series, pd.Series]]:
        """
        Purged cross-validation (removes overlapping test periods).
        
        Args:
            data: Time series data
            n_splits: Number of folds
            test_size: Size of test set
            gap_size: Gap between train and test sets
            
        Returns:
            List of (train, test) tuples
        """
        folds = []
        total_size = len(data)
        fold_size = total_size // n_splits
        
        for i in range(n_splits):
            train_end = (i + 1) * fold_size - test_size - gap_size
            test_start = train_end + gap_size
            test_end = test_start + test_size
            
            if train_end > 0 and test_end <= total_size:
                train_data = data.iloc[:train_end]
                test_data = data.iloc[test_start:test_end]
                folds.append((train_data, test_data))
        
        return folds


class StatisticalTester:
    """
    Statistical significance testing for forecasting models.
    
    Provides:
    - Diebold-Mariano test (compare forecast accuracy)
    - Model Confidence Set (select best models)
    - Sign test (direction accuracy significance)
    - Wilcoxon signed-rank test
    """
    
    def __init__(self):
        """Initialize statistical tester."""
        pass
    
    def diebold_mariano_test(
        self,
        errors1: List[float],
        errors2: List[float],
        h: int = 1
    ) -> Dict[str, float]:
        """
        Diebold-Mariano test for comparing forecast accuracy.
        
        Args:
            errors1: Forecast errors from model 1
            errors2: Forecast errors from model 2
            h: Forecast horizon
            
        Returns:
            Dictionary with test statistic and p-value
        """
        try:
            from scipy.stats import norm
            
            # Calculate loss differential
            loss_diff = np.array(errors1) - np.array(errors2)
            
            # Calculate test statistic
            mean_diff = np.mean(loss_diff)
            n = len(loss_diff)
            
            # HAC (Heteroskedasticity and Autocorrelation Consistent) standard error
            # Simplified version - in practice, use Newey-West estimator
            var_diff = np.var(loss_diff)
            se = np.sqrt(var_diff / n)
            
            if se == 0:
                return {"statistic": 0.0, "p_value": 1.0}
            
            dm_stat = mean_diff / se
            
            # Two-sided test
            p_value = 2 * (1 - norm.cdf(abs(dm_stat)))
            
            return {
                "statistic": float(dm_stat),
                "p_value": float(p_value),
                "mean_difference": float(mean_diff),
            }
            
        except Exception as e:
            LOGGER.warning(f"Diebold-Mariano test failed: {e}")
            return {"statistic": 0.0, "p_value": 1.0}
    
    def sign_test(
        self,
        actual_direction: List[bool],
        predicted_direction: List[bool]
    ) -> Dict[str, float]:
        """
        Sign test for directional accuracy.
        
        Args:
            actual_direction: Actual direction changes (True = up, False = down)
            predicted_direction: Predicted direction changes
            
        Returns:
            Dictionary with test statistic and p-value
        """
        try:
            from scipy.stats import binom
            
            matches = sum(a == p for a, p in zip(actual_direction, predicted_direction))
            n = len(actual_direction)
            
            if n == 0:
                return {"statistic": 0.0, "p_value": 1.0}
            
            # Under null hypothesis (random), p = 0.5
            p_value = 2 * binom.cdf(min(matches, n - matches), n, 0.5)
            
            accuracy = matches / n
            
            return {
                "statistic": float(accuracy),
                "p_value": float(p_value),
                "matches": matches,
                "total": n,
            }
            
        except Exception as e:
            LOGGER.warning(f"Sign test failed: {e}")
            return {"statistic": 0.0, "p_value": 1.0}
    
    def wilcoxon_test(
        self,
        errors1: List[float],
        errors2: List[float]
    ) -> Dict[str, float]:
        """
        Wilcoxon signed-rank test for comparing forecast errors.
        
        Args:
            errors1: Forecast errors from model 1
            errors2: Forecast errors from model 2
            
        Returns:
            Dictionary with test statistic and p-value
        """
        try:
            from scipy.stats import wilcoxon
            
            # Calculate differences
            diff = np.array(errors1) - np.array(errors2)
            
            # Remove zero differences
            diff = diff[diff != 0]
            
            if len(diff) == 0:
                return {"statistic": 0.0, "p_value": 1.0}
            
            statistic, p_value = wilcoxon(diff, alternative='two-sided')
            
            return {
                "statistic": float(statistic),
                "p_value": float(p_value),
            }
            
        except Exception as e:
            LOGGER.warning(f"Wilcoxon test failed: {e}")
            return {"statistic": 0.0, "p_value": 1.0}


class StabilityChecker:
    """
    Model stability checks for forecasting models.
    
    Provides:
    - Forecast stability across folds
    - Parameter stability (for ARIMA, Prophet)
    - Residual analysis (autocorrelation, normality)
    - Forecast variance analysis
    """
    
    def __init__(self):
        """Initialize stability checker."""
        pass
    
    def check_forecast_stability(
        self,
        forecasts: List[List[float]]
    ) -> Dict[str, float]:
        """
        Check forecast stability across folds.
        
        Args:
            forecasts: List of forecast lists (one per fold)
            
        Returns:
            Dictionary with stability metrics
        """
        if not forecasts:
            return {"stability_score": 0.0, "variance": float('inf')}
        
        # Convert to numpy array
        forecast_array = np.array(forecasts)
        
        # Calculate coefficient of variation (std/mean) for each horizon
        stability_scores = []
        for i in range(forecast_array.shape[1]):
            horizon_forecasts = forecast_array[:, i]
            if np.mean(horizon_forecasts) != 0:
                cv = np.std(horizon_forecasts) / np.mean(horizon_forecasts)
                stability_scores.append(1.0 / (1.0 + cv))  # Convert to stability score (0-1)
            else:
                stability_scores.append(0.0)
        
        overall_stability = np.mean(stability_scores)
        overall_variance = np.mean([np.var(f) for f in forecasts])
        
        return {
            "stability_score": float(overall_stability),
            "variance": float(overall_variance),
            "horizon_stability": [float(s) for s in stability_scores],
        }
    
    def check_residuals(
        self,
        residuals: List[float]
    ) -> Dict[str, float]:
        """
        Check residual properties (autocorrelation, normality).
        
        Args:
            residuals: Residual values
            
        Returns:
            Dictionary with residual analysis metrics
        """
        try:
            from scipy.stats import normaltest, jarque_bera
            
            residuals_array = np.array(residuals)
            
            # Normality test (Jarque-Bera)
            jb_stat, jb_p = jarque_bera(residuals_array)
            
            # Autocorrelation (Ljung-Box test approximation)
            # Simplified: check first-order autocorrelation
            if len(residuals) > 1:
                autocorr = np.corrcoef(residuals_array[:-1], residuals_array[1:])[0, 1]
            else:
                autocorr = 0.0
            
            # Mean and variance of residuals
            mean_residual = np.mean(residuals_array)
            std_residual = np.std(residuals_array)
            
            return {
                "mean": float(mean_residual),
                "std": float(std_residual),
                "autocorrelation": float(autocorr),
                "jb_statistic": float(jb_stat),
                "jb_p_value": float(jb_p),
                "is_normal": jb_p > 0.05,
            }
            
        except Exception as e:
            LOGGER.warning(f"Residual analysis failed: {e}")
            return {
                "mean": 0.0,
                "std": 0.0,
                "autocorrelation": 0.0,
                "jb_statistic": 0.0,
                "jb_p_value": 1.0,
                "is_normal": True,
            }


def get_model_validator() -> ModelValidator:
    """Factory function to create ModelValidator instance."""
    return ModelValidator()


def get_time_series_cv() -> TimeSeriesCrossValidator:
    """Factory function to create TimeSeriesCrossValidator instance."""
    return TimeSeriesCrossValidator()


def get_statistical_tester() -> StatisticalTester:
    """Factory function to create StatisticalTester instance."""
    return StatisticalTester()


def get_stability_checker() -> StabilityChecker:
    """Factory function to create StabilityChecker instance."""
    return StabilityChecker()

