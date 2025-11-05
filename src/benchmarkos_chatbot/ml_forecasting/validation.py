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


def get_model_validator() -> ModelValidator:
    """Factory function to create ModelValidator instance."""
    return ModelValidator()

