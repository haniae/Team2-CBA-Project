"""
Explainability Module for ML Forecasting

Provides feature importance and model explainability for forecasting models
using SHAP values, attention weights, and component analysis.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("shap not available - explainability will be limited")

LOGGER = logging.getLogger(__name__)


@dataclass
class ExplainabilityResult:
    """Explainability analysis result."""
    model_name: str
    feature_importance: Dict[str, float]  # Feature name -> importance score
    forecast_decomposition: Dict[str, float]  # Component -> contribution
    attention_weights: Optional[List[List[float]]] = None  # For Transformer models
    shap_values: Optional[np.ndarray] = None  # SHAP values if available
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = {
            "model_name": self.model_name,
            "feature_importance": self.feature_importance,
            "forecast_decomposition": self.forecast_decomposition,
        }
        
        if self.attention_weights:
            result["attention_weights"] = self.attention_weights
        
        if self.shap_values is not None:
            result["shap_values_available"] = True
        
        return result


class ModelExplainer:
    """
    Explain forecasting models using various methods.
    
    Provides:
    - SHAP values for feature importance
    - Attention weights from Transformer models
    - Component analysis for Prophet
    - Forecast decomposition
    """
    
    def __init__(self):
        """Initialize model explainer."""
        pass
    
    def explain_prophet(
        self,
        model: Any,
        forecast_df: pd.DataFrame
    ) -> ExplainabilityResult:
        """
        Explain Prophet model using component analysis.
        
        Args:
            model: Fitted Prophet model
            forecast_df: Forecast DataFrame from Prophet
            
        Returns:
            ExplainabilityResult with component contributions
        """
        try:
            # Prophet provides component breakdown
            components = {}
            
            if 'trend' in forecast_df.columns:
                components['trend'] = float(forecast_df['trend'].iloc[-1])
            if 'yearly' in forecast_df.columns:
                components['yearly_seasonality'] = float(forecast_df['yearly'].iloc[-1])
            if 'weekly' in forecast_df.columns:
                components['weekly_seasonality'] = float(forecast_df['weekly'].iloc[-1])
            if 'holidays' in forecast_df.columns:
                components['holidays'] = float(forecast_df['holidays'].iloc[-1])
            
            # Feature importance (if external regressors)
            feature_importance = {}
            if hasattr(model, 'extra_regressors'):
                for regressor_name in model.extra_regressors.keys():
                    if regressor_name in forecast_df.columns:
                        feature_importance[regressor_name] = float(forecast_df[regressor_name].iloc[-1])
            
            return ExplainabilityResult(
                model_name="prophet",
                feature_importance=feature_importance,
                forecast_decomposition=components,
            )
            
        except Exception as e:
            LOGGER.warning(f"Prophet explainability failed: {e}")
            return ExplainabilityResult(
                model_name="prophet",
                feature_importance={},
                forecast_decomposition={},
            )
    
    def explain_arima(
        self,
        model: Any,
        data: pd.Series
    ) -> ExplainabilityResult:
        """
        Explain ARIMA model using coefficient analysis.
        
        Args:
            model: Fitted ARIMA model
            data: Time series data
            
        Returns:
            ExplainabilityResult with ARIMA coefficients
        """
        try:
            # Extract ARIMA coefficients
            feature_importance = {}
            
            if hasattr(model, 'arparams'):
                for i, coef in enumerate(model.arparams):
                    feature_importance[f"AR_{i+1}"] = float(coef)
            
            if hasattr(model, 'maparams'):
                for i, coef in enumerate(model.maparams):
                    feature_importance[f"MA_{i+1}"] = float(coef)
            
            # Forecast decomposition (trend vs seasonal)
            forecast_decomposition = {
                "trend": 1.0,  # ARIMA captures trend
                "seasonal": 0.0,  # ARIMA doesn't explicitly model seasonality
            }
            
            return ExplainabilityResult(
                model_name="arima",
                feature_importance=feature_importance,
                forecast_decomposition=forecast_decomposition,
            )
            
        except Exception as e:
            LOGGER.warning(f"ARIMA explainability failed: {e}")
            return ExplainabilityResult(
                model_name="arima",
                feature_importance={},
                forecast_decomposition={},
            )
    
    def explain_lstm(
        self,
        model: Any,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> ExplainabilityResult:
        """
        Explain LSTM model using SHAP values.
        
        Args:
            model: Fitted LSTM model
            X: Input features (sequences)
            feature_names: Names of features
            
        Returns:
            ExplainabilityResult with feature importance
        """
        try:
            feature_importance = {}
            
            if SHAP_AVAILABLE and len(X) > 0:
                # Use SHAP for LSTM (if feasible)
                # Note: SHAP for LSTM can be computationally expensive
                try:
                    # Create SHAP explainer (using a subset for efficiency)
                    sample_size = min(100, len(X))
                    sample_indices = np.random.choice(len(X), sample_size, replace=False)
                    X_sample = X[sample_indices]
                    
                    # Use DeepExplainer for neural networks
                    explainer = shap.DeepExplainer(model, X_sample[:10])
                    shap_values = explainer.shap_values(X_sample)
                    
                    # Calculate feature importance as mean absolute SHAP value
                    if isinstance(shap_values, list):
                        shap_values = shap_values[0]  # For regression, take first output
                    
                    # Average across samples and time steps
                    mean_shap = np.abs(shap_values).mean(axis=(0, 1))
                    
                    if feature_names:
                        for i, name in enumerate(feature_names):
                            if i < len(mean_shap):
                                feature_importance[name] = float(mean_shap[i])
                    else:
                        for i, importance in enumerate(mean_shap):
                            feature_importance[f"feature_{i}"] = float(importance)
                    
                except Exception as e:
                    LOGGER.warning(f"SHAP for LSTM failed: {e}, using simple feature importance")
                    # Fallback: use gradient-based importance
                    feature_importance = self._calculate_gradient_importance(model, X)
            else:
                # Fallback: use gradient-based importance
                feature_importance = self._calculate_gradient_importance(model, X)
            
            forecast_decomposition = {
                "lstm_contribution": 1.0,
            }
            
            return ExplainabilityResult(
                model_name="lstm",
                feature_importance=feature_importance,
                forecast_decomposition=forecast_decomposition,
            )
            
        except Exception as e:
            LOGGER.warning(f"LSTM explainability failed: {e}")
            return ExplainabilityResult(
                model_name="lstm",
                feature_importance={},
                forecast_decomposition={},
            )
    
    def explain_transformer(
        self,
        model: Any,
        attention_weights: Optional[List[List[float]]] = None
    ) -> ExplainabilityResult:
        """
        Explain Transformer model using attention weights.
        
        Args:
            model: Fitted Transformer model
            attention_weights: Attention weights from model (if available)
            
        Returns:
            ExplainabilityResult with attention-based importance
        """
        try:
            feature_importance = {}
            
            if attention_weights:
                # Calculate feature importance from attention weights
                # Average attention across heads and layers
                attention_array = np.array(attention_weights)
                if len(attention_array.shape) > 2:
                    # Average across heads and layers
                    mean_attention = attention_array.mean(axis=(0, 1))
                else:
                    mean_attention = attention_array.mean(axis=0)
                
                for i, importance in enumerate(mean_attention):
                    feature_importance[f"time_step_{i}"] = float(importance)
            else:
                # Default: equal importance
                feature_importance = {"attention_unavailable": 1.0}
            
            forecast_decomposition = {
                "transformer_attention": 1.0,
            }
            
            return ExplainabilityResult(
                model_name="transformer",
                feature_importance=feature_importance,
                forecast_decomposition=forecast_decomposition,
                attention_weights=attention_weights,
            )
            
        except Exception as e:
            LOGGER.warning(f"Transformer explainability failed: {e}")
            return ExplainabilityResult(
                model_name="transformer",
                feature_importance={},
                forecast_decomposition={},
            )
    
    def _calculate_gradient_importance(
        self,
        model: Any,
        X: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate feature importance using gradients (fallback method).
        
        Args:
            model: Neural network model
            X: Input features
            
        Returns:
            Dictionary of feature importance
        """
        try:
            import tensorflow as tf
            
            # Calculate gradients w.r.t. input
            X_tensor = tf.constant(X[:10], dtype=tf.float32)  # Use sample
            
            with tf.GradientTape() as tape:
                tape.watch(X_tensor)
                predictions = model(X_tensor)
            
            gradients = tape.gradient(predictions, X_tensor)
            
            # Calculate importance as mean absolute gradient
            importance = np.abs(gradients.numpy()).mean(axis=(0, 1))
            
            feature_importance = {}
            for i, imp in enumerate(importance):
                feature_importance[f"feature_{i}"] = float(imp)
            
            return feature_importance
            
        except Exception as e:
            LOGGER.warning(f"Gradient-based importance calculation failed: {e}")
            return {}


def get_model_explainer() -> ModelExplainer:
    """Factory function to create ModelExplainer instance."""
    return ModelExplainer()

