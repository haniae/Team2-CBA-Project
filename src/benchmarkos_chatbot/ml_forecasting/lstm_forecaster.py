"""
LSTM/GRU Forecasting Module

Deep learning forecasting using LSTM (Long Short-Term Memory) and GRU (Gated Recurrent Unit)
networks for time series forecasting. Handles non-linear patterns and long-term dependencies.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

LOGGER = logging.getLogger(__name__)

# Try to import TensorFlow/Keras
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, Input
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    LOGGER.warning("TensorFlow not available - LSTM forecasting will not work")

from .ml_forecaster import BaseForecaster

if TENSORFLOW_AVAILABLE:
    # Set TensorFlow to use CPU by default (can be overridden)
    tf.config.set_visible_devices([], 'GPU')  # Disable GPU by default
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)


@dataclass
class LSTMForecastResult:
    """LSTM forecast result with additional model details."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    method: str  # Method used ('lstm' or 'gru')
    model_details: Dict  # Model-specific details
    confidence: float  # Overall confidence (0-1)
    model_type: str = "lstm"  # "lstm" or "gru"
    layers: List[int] = None
    epochs_trained: int = 0
    training_loss: float = 0.0
    validation_loss: float = 0.0


class LSTMForecaster(BaseForecaster):
    """
    LSTM/GRU-based forecasting for financial metrics.
    
    Uses deep learning to capture non-linear patterns and long-term dependencies
    in time series data.
    """
    
    def __init__(self, database_path: str):
        """Initialize LSTM forecaster."""
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM forecasting")
        
        super().__init__(database_path)
        self.model_cache: Dict[str, Any] = {}
        self.scaler_cache: Dict[str, Any] = {}
        
    def _get_historical_data(
        self,
        ticker: str,
        metric: str,
        min_periods: int = 20
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
    
    def _prepare_sequences(
        self,
        data: np.ndarray,
        lookback: int,
        forecast_steps: int
    ) -> tuple:
        """
        Prepare sequences for LSTM training.
        
        Args:
            data: Time series data (normalized)
            lookback: Number of past periods to use for prediction
            forecast_steps: Number of future periods to forecast
            
        Returns:
            X (input sequences), y (target sequences)
        """
        X, y = [], []
        
        for i in range(len(data) - lookback - forecast_steps + 1):
            # Input: past 'lookback' periods
            X.append(data[i:i + lookback])
            # Target: next 'forecast_steps' periods
            y.append(data[i + lookback:i + lookback + forecast_steps])
        
        return np.array(X), np.array(y)
    
    def _build_model(
        self,
        input_shape: tuple,
        layers: List[int],
        model_type: Literal["lstm", "gru"] = "lstm",
        dropout: float = 0.2,
        learning_rate: float = 0.001
    ) -> keras.Model:
        """
        Build LSTM/GRU model.
        
        Args:
            input_shape: Shape of input data (lookback, features)
            layers: List of layer sizes [64, 32] means two layers with 64 and 32 units
            model_type: "lstm" or "gru"
            dropout: Dropout rate for regularization
            learning_rate: Learning rate for optimizer
            
        Returns:
            Compiled Keras model
        """
        model = Sequential()
        
        # First layer (return sequences if multiple layers)
        first_layer = LSTM if model_type == "lstm" else GRU
        
        if len(layers) > 1:
            model.add(Input(shape=input_shape))
            model.add(first_layer(
                layers[0],
                return_sequences=True,
                activation='relu'
            ))
            model.add(Dropout(dropout))
        else:
            model.add(Input(shape=input_shape))
            model.add(first_layer(
                layers[0],
                return_sequences=False,
                activation='relu'
            ))
            model.add(Dropout(dropout))
        
        # Additional layers
        for layer_size in layers[1:-1]:
            layer_class = LSTM if model_type == "lstm" else GRU
            model.add(layer_class(
                layer_size,
                return_sequences=True,
                activation='relu'
            ))
            model.add(Dropout(dropout))
        
        # Final layer (no return sequences)
        if len(layers) > 1:
            final_layer = LSTM if model_type == "lstm" else GRU
            model.add(final_layer(
                layers[-1],
                return_sequences=False,
                activation='relu'
            ))
            model.add(Dropout(dropout))
        
        # Output layer
        model.add(Dense(1))  # Single output for each forecast step
        
        # Compile
        # Get hyperparameters from kwargs if available
        units = kwargs.get('units', layers[0] if layers else 50)
        dropout = kwargs.get('dropout', 0.2)
        learning_rate = kwargs.get('learning_rate', learning_rate)
        
        optimizer = Adam(learning_rate=learning_rate)
        model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        
        return model
    
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        model_type: Literal["lstm", "gru"] = "lstm",
        lookback_window: int = 10,
        layers: Optional[List[int]] = None,
        epochs: int = 100,
        batch_size: int = 32,
        validation_split: float = 0.2,
        **kwargs
    ) -> Optional[LSTMForecastResult]:
        """
        Generate forecast using LSTM/GRU.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., "revenue")
            periods: Number of periods to forecast
            model_type: "lstm" or "gru"
            lookback_window: Number of past periods to use for prediction
            layers: List of layer sizes (default: [64, 32] for 2 layers)
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
            **kwargs: Additional arguments
            
        Returns:
            LSTMForecastResult with forecast and confidence intervals
        """
        if not TENSORFLOW_AVAILABLE:
            LOGGER.error("TensorFlow not available for LSTM forecasting")
            return None
        
        try:
            # Get historical data
            ts = self._get_historical_data(ticker, metric, min_periods=lookback_window + periods + 5)
            if ts is None:
                return None
            
            # Check for feature engineering
            use_technical_indicators = kwargs.get('use_technical_indicators', False)
            use_external_factors = kwargs.get('use_external_factors', False)
            
            # Build feature matrix
            feature_data = ts.values.reshape(-1, 1)
            
            # Add technical indicators if requested
            if use_technical_indicators:
                try:
                    from .technical_indicators import TechnicalIndicators
                    tech_indicators = TechnicalIndicators()
                    tech_df = tech_indicators.generate_indicators(ts, include_all=False)
                    # Add technical indicator features (excluding 'value' column)
                    tech_features = tech_df.drop(columns=['value'], errors='ignore').values
                    if tech_features.shape[1] > 0:
                        feature_data = np.hstack([feature_data, tech_features])
                except Exception as e:
                    LOGGER.warning(f"Failed to add technical indicators: {e}")
            
            # Add external factors if requested
            if use_external_factors:
                try:
                    from .external_factors import ExternalFactorsProvider
                    external_provider = ExternalFactorsProvider()
                    external_regressors = external_provider.get_external_regressors(
                        ticker, metric,
                        start_date=ts.index.min(),
                        end_date=ts.index.max()
                    )
                    if external_regressors is not None and not external_regressors.empty:
                        # Align external regressors with ts dates
                        external_aligned = external_regressors.reindex(ts.index, method='ffill')
                        external_features = external_aligned.values
                        if external_features.shape[1] > 0:
                            feature_data = np.hstack([feature_data, external_features])
                except Exception as e:
                    LOGGER.warning(f"Failed to add external factors: {e}")
            
            # Normalize data (now multi-dimensional)
            from sklearn.preprocessing import MinMaxScaler
            
            scaler_key = f"{ticker}_{metric}"
            if scaler_key not in self.scaler_cache:
                scaler = MinMaxScaler(feature_range=(0, 1))
                self.scaler_cache[scaler_key] = scaler
            else:
                scaler = self.scaler_cache[scaler_key]
            
            # Scale all features
            data_scaled = scaler.fit_transform(feature_data)
            
            # Prepare sequences
            X, y = self._prepare_sequences(data_scaled, lookback_window, periods)
            
            if len(X) == 0:
                LOGGER.error(f"Insufficient data for sequences: need {lookback_window + periods} periods")
                return None
            
            # Update input shape for multi-dimensional features
            input_shape = (lookback_window, feature_data.shape[1])
            
            # Split train/validation
            split_idx = int(len(X) * (1 - validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Check for hyperparameter tuning
            use_hyperparameter_tuning = kwargs.get('use_hyperparameter_tuning', False)
            
            # Get hyperparameters
            if use_hyperparameter_tuning:
                try:
                    from .hyperparameter_tuning import HyperparameterTuner
                    tuner = HyperparameterTuner(self.database_path)
                    best_params = tuner.tune_lstm(ticker, metric, ts)
                    
                    if best_params and best_params.params:
                        units = best_params.params.get('units', 50)
                        layers_count = best_params.params.get('layers', 2)
                        dropout = best_params.params.get('dropout', 0.2)
                        learning_rate = best_params.params.get('learning_rate', 0.001)
                    else:
                        units = kwargs.get('units', 50)
                        layers_count = kwargs.get('layers', 2)
                        dropout = kwargs.get('dropout', 0.2)
                        learning_rate = kwargs.get('learning_rate', 0.001)
                except Exception as e:
                    LOGGER.warning(f"Hyperparameter tuning failed: {e}, using defaults")
                    units = kwargs.get('units', 50)
                    layers_count = kwargs.get('layers', 2)
                    dropout = kwargs.get('dropout', 0.2)
                    learning_rate = kwargs.get('learning_rate', 0.001)
            else:
                units = kwargs.get('units', 50)
                layers_count = kwargs.get('layers', 2)
                dropout = kwargs.get('dropout', 0.2)
                learning_rate = kwargs.get('learning_rate', 0.001)
            
            # Build layers list
            if layers is None:
                layers = [units] * layers_count
            
            # Build model with updated input shape
            model_key = f"{ticker}_{metric}_{model_type}_{lookback_window}_{input_shape[1]}"
            if model_key not in self.model_cache:
                model = self._build_model(
                    input_shape=input_shape,  # Multi-dimensional features
                    layers=layers,
                    model_type=model_type,
                    dropout=dropout,
                    learning_rate=learning_rate
                )
            else:
                model = self.model_cache[model_key]
            
            # Train model
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True,
                    verbose=0
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-6,
                    verbose=0
                )
            ]
            
            history = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val) if len(X_val) > 0 else None,
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=0
            )
            
            # Cache model
            self.model_cache[model_key] = model
            
            # Generate forecast
            # Use last 'lookback_window' periods as input (multi-dimensional)
            last_sequence = data_scaled[-lookback_window:].reshape(1, lookback_window, input_shape[1])
            
            # Forecast step by step
            forecast_scaled = []
            current_input = last_sequence.copy()
            
            for _ in range(periods):
                # Predict next value
                next_pred = model.predict(current_input, verbose=0)[0, 0]
                forecast_scaled.append(next_pred)
                
                # Update input sequence (shift window)
                # For multi-dimensional features, we need to handle differently
                current_input = np.roll(current_input, -1, axis=1)
                # For the new timestep, use the prediction for the first feature
                # and repeat the last values for other features
                current_input[0, -1, 0] = next_pred
                if input_shape[1] > 1:
                    current_input[0, -1, 1:] = last_sequence[0, -1, 1:]
            
            # Inverse transform predictions (only inverse transform first feature)
            forecast_scaled = np.array(forecast_scaled).reshape(-1, 1)
            # Create full feature array for inverse transform
            full_pred = np.zeros((len(forecast_scaled), input_shape[1]))
            full_pred[:, 0] = forecast_scaled.flatten()
            # Use last known values for other features (for inverse transform)
            if input_shape[1] > 1:
                last_features = feature_data[-1, 1:]
                for i in range(len(forecast_scaled)):
                    full_pred[i, 1:] = last_features
            forecast_values = scaler.inverse_transform(full_pred)[:, 0]  # Extract first feature
            
            # Ensure positive values for financial metrics
            forecast_values = np.maximum(forecast_values, 0)
            
            # Calculate confidence intervals (simplified: use validation error)
            val_loss = history.history.get('val_loss', [history.history['loss']])[-1]
            # Use scale from first feature (the target metric)
            std_error = np.sqrt(val_loss) * scaler.scale_[0] if hasattr(scaler, 'scale_') and len(scaler.scale_) > 0 else np.sqrt(val_loss)
            
            # 95% confidence interval (±1.96 * std_error)
            conf_interval = 1.96 * std_error
            
            confidence_intervals_low = forecast_values - conf_interval
            confidence_intervals_high = forecast_values + conf_interval
            
            # Ensure positive
            confidence_intervals_low = np.maximum(confidence_intervals_low, 0)
            
            # Calculate confidence score (inverse of validation loss, normalized)
            data_range = np.max(feature_data[:, 0]) - np.min(feature_data[:, 0])
            if data_range > 0:
                confidence = max(0.0, min(1.0, 1.0 - (val_loss / data_range)))
            else:
                confidence = 0.5
            
            # Generate periods (years)
            last_date = ts.index[-1]
            if isinstance(last_date, pd.Timestamp):
                periods_list = [last_date.year + i + 1 for i in range(periods)]
            else:
                periods_list = list(range(1, periods + 1))
            
            # Training info
            epochs_trained = len(history.history['loss'])
            training_loss = history.history['loss'][-1]
            validation_loss = history.history.get('val_loss', [training_loss])[-1]
            
            # Calculate additional metrics
            import time
            training_start_time = time.time()
            # Estimate training time (would be better to track actual time)
            training_time = epochs_trained * 0.5  # Rough estimate
            
            # Calculate model complexity
            total_params = model.count_params()
            
            # Calculate data points used
            data_points_used = len(feature_data)
            
            # Calculate train/test split
            train_size = len(X_train)
            val_size = len(X_val) if len(X_val) > 0 else 0
            total_size = train_size + val_size
            train_test_split = f"{train_size}/{val_size}" if val_size > 0 else f"{train_size}/0"
            
            # Calculate overfitting ratio
            overfit_ratio = validation_loss / training_loss if training_loss > 0 else 1.0
            
            # Get optimizer details
            optimizer_name = model.optimizer.__class__.__name__
            learning_rate = float(model.optimizer.learning_rate.numpy()) if hasattr(model.optimizer.learning_rate, 'numpy') else 0.001
            
            return LSTMForecastResult(
                ticker=ticker,
                metric=metric,
                periods=periods_list,
                predicted_values=forecast_values.tolist(),
                confidence_intervals_low=confidence_intervals_low.tolist(),
                confidence_intervals_high=confidence_intervals_high.tolist(),
                method=f"{model_type.upper()}",
                model_details={
                    "model_type": model_type,
                    "layers": layers,
                    "units": layers[0] if layers else 50,  # First layer units
                    "lookback_window": lookback_window,
                    "epochs_trained": epochs_trained,
                    "training_loss": float(training_loss),
                    "validation_loss": float(validation_loss),
                    "input_shape": (lookback_window, input_shape[1]),
                    "total_parameters": total_params,
                    "training_time": float(training_time),
                    "data_points_used": data_points_used,
                    "train_test_split": train_test_split,
                    "batch_size": batch_size,
                    "learning_rate": float(learning_rate),
                    "optimizer": optimizer_name,
                    "dropout": 0.2,  # Default dropout if used
                    "overfit_ratio": float(overfit_ratio),
                    "preprocessing_applied": ["scaling", "feature_engineering"],
                    "scaling_method": "MinMaxScaler",
                    "hyperparameters": {
                        "layers": layers,
                        "units_per_layer": layers[0] if layers else 50,
                        "lookback_window": lookback_window,
                        "batch_size": batch_size,
                        "learning_rate": float(learning_rate),
                        "epochs": epochs,
                        "dropout": 0.2,
                        "optimizer": optimizer_name,
                    },
                },
                confidence=float(confidence),
                model_type=model_type,
                layers=layers,
                epochs_trained=epochs_trained,
                training_loss=float(training_loss),
                validation_loss=float(validation_loss),
            )
            
        except Exception as e:
            LOGGER.exception(f"LSTM forecasting failed for {ticker} {metric}: {e}")
            return None


def get_lstm_forecaster(database_path: str) -> Optional[LSTMForecaster]:
    """Factory function to create LSTMForecaster instance."""
    if not TENSORFLOW_AVAILABLE:
        LOGGER.warning("TensorFlow not available - LSTM forecasting disabled")
        return None
    
    try:
        return LSTMForecaster(database_path)
    except Exception as e:
        LOGGER.error(f"Failed to create LSTMForecaster: {e}")
        return None

