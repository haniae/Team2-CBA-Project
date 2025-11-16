"""
Advanced Uncertainty Quantification Module

Provides advanced uncertainty quantification methods for forecasting models
including prediction intervals, conformal prediction, and ensemble uncertainty.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from scipy import stats

LOGGER = logging.getLogger(__name__)


@dataclass
class UncertaintyMetrics:
    """Uncertainty quantification metrics."""
    prediction_intervals: Dict[str, Dict[str, List[float]]]  # confidence_level -> {low, high}
    forecast_distribution: Dict[str, float]  # Distribution statistics (mean, std, etc.)
    coverage_probability: float  # Coverage probability of intervals
    uncertainty_score: float  # Overall uncertainty score (0-1)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "prediction_intervals": self.prediction_intervals,
            "forecast_distribution": self.forecast_distribution,
            "coverage_probability": self.coverage_probability,
            "uncertainty_score": self.uncertainty_score,
        }


class UncertaintyQuantifier:
    """
    Advanced uncertainty quantification for forecasts.
    
    Provides:
    - Prediction intervals at multiple confidence levels
    - Conformal prediction (distribution-free)
    - Ensemble-based uncertainty
    - Monte Carlo simulation for forecast distribution
    """
    
    def __init__(self):
        """Initialize uncertainty quantifier."""
        pass
    
    def calculate_prediction_intervals(
        self,
        predictions: List[float],
        residuals: Optional[List[float]] = None,
        confidence_levels: List[float] = [0.90, 0.95, 0.99]
    ) -> Dict[str, Dict[str, List[float]]]:
        """
        Calculate prediction intervals at multiple confidence levels.
        
        Args:
            predictions: Point forecasts
            residuals: Historical residuals (if available)
            confidence_levels: List of confidence levels (e.g., [0.90, 0.95, 0.99])
            
        Returns:
            Dictionary mapping confidence level to {low, high} intervals
        """
        intervals = {}
        
        if residuals is None or len(residuals) == 0:
            # Use simple heuristic: assume 10% uncertainty
            std_factor = 0.1
            for level in confidence_levels:
                alpha = 1 - level
                z_score = stats.norm.ppf(1 - alpha / 2)
                
                low = [p - z_score * std_factor * abs(p) for p in predictions]
                high = [p + z_score * std_factor * abs(p) for p in predictions]
                
                intervals[str(level)] = {
                    "low": low,
                    "high": high,
                }
        else:
            # Use empirical residuals
            residual_std = np.std(residuals)
            residual_mean = np.mean(residuals)
            
            for level in confidence_levels:
                alpha = 1 - level
                z_score = stats.norm.ppf(1 - alpha / 2)
                
                low = [p - z_score * residual_std - residual_mean for p in predictions]
                high = [p + z_score * residual_std - residual_mean for p in predictions]
                
                intervals[str(level)] = {
                    "low": low,
                    "high": high,
                }
        
        return intervals
    
    def conformal_prediction(
        self,
        predictions: List[float],
        calibration_errors: List[float],
        confidence_level: float = 0.95
    ) -> Dict[str, List[float]]:
        """
        Conformal prediction intervals (distribution-free).
        
        Args:
            predictions: Point forecasts
            calibration_errors: Errors on calibration set
            confidence_level: Confidence level (e.g., 0.95)
            
        Returns:
            Dictionary with {low, high} intervals
        """
        if len(calibration_errors) == 0:
            # Fallback to parametric intervals
            return self.calculate_prediction_intervals(predictions, confidence_levels=[confidence_level])[str(confidence_level)]
        
        # Calculate quantile of calibration errors
        quantile = (1 + confidence_level) / 2
        error_quantile = np.quantile(np.abs(calibration_errors), quantile)
        
        low = [p - error_quantile for p in predictions]
        high = [p + error_quantile for p in predictions]
        
        return {
            "low": low,
            "high": high,
        }
    
    def ensemble_uncertainty(
        self,
        ensemble_predictions: List[List[float]]
    ) -> Dict[str, Any]:
        """
        Calculate uncertainty from ensemble predictions.
        
        Args:
            ensemble_predictions: List of prediction lists (one per model)
            
        Returns:
            Dictionary with uncertainty metrics
        """
        if not ensemble_predictions:
            return {
                "mean": [],
                "std": [],
                "variance": [],
            }
        
        # Convert to numpy array
        predictions_array = np.array(ensemble_predictions)
        
        # Calculate statistics across ensemble
        mean_predictions = np.mean(predictions_array, axis=0).tolist()
        std_predictions = np.std(predictions_array, axis=0).tolist()
        variance_predictions = np.var(predictions_array, axis=0).tolist()
        
        # Calculate prediction intervals
        intervals_90 = {
            "low": [m - 1.645 * s for m, s in zip(mean_predictions, std_predictions)],
            "high": [m + 1.645 * s for m, s in zip(mean_predictions, std_predictions)],
        }
        
        intervals_95 = {
            "low": [m - 1.96 * s for m, s in zip(mean_predictions, std_predictions)],
            "high": [m + 1.96 * s for m, s in zip(mean_predictions, std_predictions)],
        }
        
        intervals_99 = {
            "low": [m - 2.576 * s for m, s in zip(mean_predictions, std_predictions)],
            "high": [m + 2.576 * s for m, s in zip(mean_predictions, std_predictions)],
        }
        
        return {
            "mean": mean_predictions,
            "std": std_predictions,
            "variance": variance_predictions,
            "prediction_intervals": {
                "0.90": intervals_90,
                "0.95": intervals_95,
                "0.99": intervals_99,
            },
        }
    
    def monte_carlo_uncertainty(
        self,
        model_predictions: List[float],
        prediction_std: List[float],
        n_simulations: int = 1000
    ) -> Dict[str, Any]:
        """
        Monte Carlo simulation for forecast distribution.
        
        Args:
            model_predictions: Point forecasts
            prediction_std: Standard deviation of predictions
            n_simulations: Number of Monte Carlo simulations
            
        Returns:
            Dictionary with distribution statistics
        """
        simulations = []
        
        for pred, std in zip(model_predictions, prediction_std):
            # Generate samples from normal distribution
            samples = np.random.normal(pred, std, n_simulations)
            simulations.append(samples)
        
        # Calculate distribution statistics
        distribution_stats = {}
        
        for i, sims in enumerate(simulations):
            distribution_stats[f"period_{i+1}"] = {
                "mean": float(np.mean(sims)),
                "std": float(np.std(sims)),
                "median": float(np.median(sims)),
                "q25": float(np.quantile(sims, 0.25)),
                "q75": float(np.quantile(sims, 0.75)),
                "q5": float(np.quantile(sims, 0.05)),
                "q95": float(np.quantile(sims, 0.95)),
            }
        
        return {
            "simulations": len(simulations),
            "distribution_stats": distribution_stats,
        }
    
    def calculate_uncertainty_metrics(
        self,
        predictions: List[float],
        residuals: Optional[List[float]] = None,
        ensemble_predictions: Optional[List[List[float]]] = None
    ) -> UncertaintyMetrics:
        """
        Calculate comprehensive uncertainty metrics.
        
        Args:
            predictions: Point forecasts
            residuals: Historical residuals
            ensemble_predictions: Ensemble predictions (if available)
            
        Returns:
            UncertaintyMetrics with all uncertainty information
        """
        # Calculate prediction intervals
        prediction_intervals = self.calculate_prediction_intervals(
            predictions,
            residuals,
            confidence_levels=[0.90, 0.95, 0.99]
        )
        
        # Calculate forecast distribution
        forecast_distribution = {
            "mean": float(np.mean(predictions)),
            "std": float(np.std(predictions)),
            "min": float(np.min(predictions)),
            "max": float(np.max(predictions)),
        }
        
        # Calculate coverage probability (if residuals available)
        coverage_probability = 0.95  # Default
        if residuals and len(residuals) > 0:
            # Calculate how many actual values fall within 95% interval
            # This is a simplified version - in practice, would use actual vs predicted
            residual_std = np.std(residuals)
            z_score = 1.96
            within_interval = np.sum(np.abs(residuals) < z_score * residual_std) / len(residuals)
            coverage_probability = float(within_interval)
        
        # Calculate uncertainty score (0-1, higher = more uncertain)
        if residuals and len(residuals) > 0:
            cv = np.std(residuals) / np.abs(np.mean(predictions)) if np.mean(predictions) != 0 else 1.0
            uncertainty_score = min(1.0, cv)
        else:
            # Use prediction interval width as proxy
            interval_width = prediction_intervals["0.95"]["high"][0] - prediction_intervals["0.95"]["low"][0]
            uncertainty_score = min(1.0, interval_width / abs(predictions[0]) if predictions[0] != 0 else 1.0)
        
        return UncertaintyMetrics(
            prediction_intervals=prediction_intervals,
            forecast_distribution=forecast_distribution,
            coverage_probability=coverage_probability,
            uncertainty_score=uncertainty_score,
        )


def get_uncertainty_quantifier() -> UncertaintyQuantifier:
    """Factory function to create UncertaintyQuantifier instance."""
    return UncertaintyQuantifier()

