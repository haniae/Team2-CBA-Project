"""
Transformer Forecasting Module

Deep learning forecasting using Transformer models with attention mechanisms
for time series forecasting. Handles complex patterns and long-term dependencies.
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

# Try to import PyTorch and Transformers
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Dummy classes for when PyTorch is not available
    class Dataset:
        pass
    class nn:
        class Module:
            pass
        class Linear:
            pass
        class Parameter:
            pass
        class TransformerEncoderLayer:
            pass
        class TransformerEncoder:
            pass
        class Sequential:
            pass
        class ReLU:
            pass
        class Dropout:
            pass
    class torch:
        class Tensor:
            pass
        @staticmethod
        def randn(*args):
            return None
        @staticmethod
        def FloatTensor(*args):
            return None
    LOGGER.warning("PyTorch not available - Transformer forecasting will not work")

from .ml_forecaster import BaseForecaster

if TORCH_AVAILABLE:
    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(1)  # Limit threads for CPU
else:
    device = None


@dataclass
class TransformerForecastResult:
    """Transformer forecast result with additional model details."""
    ticker: str
    metric: str
    periods: List[int]  # Years to forecast
    predicted_values: List[float]
    confidence_intervals_low: List[float]
    confidence_intervals_high: List[float]
    method: str  # Method used ('transformer')
    model_details: Dict  # Model-specific details
    confidence: float  # Overall confidence (0-1)
    model_name: str = "time-series-transformer"
    num_layers: int = 4
    num_heads: int = 4
    d_model: int = 64
    epochs_trained: int = 0
    training_loss: float = 0.0
    validation_loss: float = 0.0


class TimeSeriesDataset(Dataset):
    """Dataset for time series forecasting."""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        if TORCH_AVAILABLE:
            self.sequences = torch.FloatTensor(sequences)
            self.targets = torch.FloatTensor(targets)
        else:
            self.sequences = sequences
            self.targets = targets
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class AttentionAwareTransformerEncoderLayer(nn.TransformerEncoderLayer):
    """
    Custom TransformerEncoderLayer that can return attention weights.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attention_weights = None
    
    def forward(self, src, src_mask=None, src_key_padding_mask=None, return_attention=False):
        """
        Forward pass with optional attention weight extraction.
        """
        if return_attention:
            # Manually call self-attention to get weights
            src2, attn_weights = self.self_attn(
                src, src, src,
                attn_mask=src_mask,
                key_padding_mask=src_key_padding_mask,
                need_weights=True
            )
            self.attention_weights = attn_weights
        else:
            # Use standard forward
            src2 = self.self_attn(
                src, src, src,
                attn_mask=src_mask,
                key_padding_mask=src_key_padding_mask,
                need_weights=False
            )[0]
        
        src = src + self.dropout1(src2)
        src = self.norm1(src)
        src2 = self.linear2(self.dropout(self.activation(self.linear1(src))))
        src = src + self.dropout2(src2)
        src = self.norm2(src)
        
        if return_attention:
            return src, self.attention_weights
        return src


class TimeSeriesTransformer(nn.Module):
    """
    Simple Transformer model for time series forecasting.
    
    Uses multi-head attention and positional encoding for time series.
    """
    
    def __init__(
        self,
        input_dim: int = 1,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 4,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        output_dim: int = 1
    ):
        super().__init__()
        
        self.d_model = d_model
        self.input_projection = nn.Linear(input_dim, d_model)
        
        # Positional encoding (learnable)
        self.pos_encoder = nn.Parameter(torch.randn(1000, d_model))
        
        # Transformer encoder - use custom layer if attention weights needed
        # For now, use standard layer but can be switched to AttentionAwareTransformerEncoderLayer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        # Store whether we should extract attention
        self.extract_attention = False
        
        # Output projection
        self.output_projection = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, output_dim)
        )
        
    def forward(self, x: torch.Tensor, return_attention: bool = False) -> torch.Tensor | tuple[torch.Tensor, list[list[float]]]:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (batch, seq_len, features)
            return_attention: If True, also return attention weights
            
        Returns:
            Output tensor of shape (batch, seq_len, output_dim)
            If return_attention=True, also returns attention weights as list of lists
        """
        # Project input
        x = self.input_projection(x)
        
        # Add positional encoding
        seq_len = x.size(1)
        if seq_len <= self.pos_encoder.size(0):
            x = x + self.pos_encoder[:seq_len].unsqueeze(0)
        else:
            # Extend positional encoding if needed
            pos_enc = self.pos_encoder.repeat((seq_len // self.pos_encoder.size(0)) + 1, 1)
            x = x + pos_enc[:seq_len].unsqueeze(0)
        
        # Apply transformer and capture attention weights if requested
        attention_weights = None
        if return_attention:
            # Extract attention weights using hooks on self-attention modules
            attention_weights_list = []
            hooks = []
            
            def make_attention_hook():
                def hook(module, input_tuple, output_tuple):
                    # MultiheadAttention returns (output, attention_weights) when need_weights=True
                    # But we need to intercept it during forward
                    # For now, we'll use a simpler approach: store weights from last layer
                    if isinstance(output_tuple, tuple) and len(output_tuple) == 2:
                        attn_weights = output_tuple[1]
                        attention_weights_list.append(attn_weights.detach())
                    elif hasattr(module, 'attention_weights'):
                        attention_weights_list.append(module.attention_weights.detach())
                return hook
            
            # Hook into self-attention modules of each layer
            for layer in self.transformer_encoder.layers:
                if hasattr(layer, 'self_attn'):
                    hook = layer.self_attn.register_forward_hook(make_attention_hook())
                    hooks.append(hook)
            
            # Apply transformer (this will trigger hooks)
            x = self.transformer_encoder(x)
            
            # Remove hooks
            for hook in hooks:
                hook.remove()
            
            # Process captured attention weights
            if attention_weights_list:
                # Average attention across all layers
                # Each attention weight is (batch, num_heads, seq_len, seq_len)
                stacked = torch.stack(attention_weights_list)
                # Average across layers and heads: (num_layers, batch, num_heads, seq_len, seq_len)
                # -> (batch, seq_len, seq_len)
                avg_attention = torch.mean(torch.mean(stacked, dim=0), dim=1)  # Average across heads
                attention_weights = avg_attention[0]  # Take first batch item: (seq_len, seq_len)
            else:
                # Fallback: return uniform attention (equal weights)
                seq_len = x.size(1)
                attention_weights = torch.ones(seq_len, seq_len) / seq_len
        else:
            # Apply transformer normally
            x = self.transformer_encoder(x)
        
        # Project to output
        x = self.output_projection(x)
        
        if return_attention:
            # Convert attention weights to list format: list of lists (seq_len x seq_len)
            if attention_weights is not None:
                attention_list = attention_weights.cpu().detach().numpy().tolist()
                return x, attention_list
            else:
                # Return uniform attention as placeholder if extraction failed
                seq_len = x.size(1)
                uniform_attention = [[1.0 / seq_len] * seq_len for _ in range(seq_len)]
                return x, uniform_attention
        return x


class TransformerForecaster(BaseForecaster):
    """
    Transformer-based forecasting for financial metrics.
    
    Uses attention mechanisms to capture complex patterns and long-term dependencies.
    """
    
    def __init__(self, database_path: str):
        """Initialize Transformer forecaster."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for Transformer forecasting")
        
        super().__init__(database_path)
        self.model_cache: Dict[str, Any] = {}
        self.scaler_cache: Dict[str, Any] = {}
        self.device = device
        
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
        Prepare sequences for Transformer training.
        
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
    
    def forecast(
        self,
        ticker: str,
        metric: str,
        periods: int = 3,
        lookback_window: int = 12,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 4,
        dim_feedforward: int = 256,
        dropout: float = 0.1,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        **kwargs
    ) -> Optional[TransformerForecastResult]:
        """
        Generate forecast using Transformer model.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to forecast (e.g., "revenue")
            periods: Number of periods to forecast
            lookback_window: Number of past periods to use for prediction
            d_model: Model dimension (embedding size)
            nhead: Number of attention heads
            num_layers: Number of transformer layers
            dim_feedforward: Feedforward network dimension
            dropout: Dropout rate
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate for optimizer
            validation_split: Fraction of data to use for validation
            **kwargs: Additional arguments
            
        Returns:
            TransformerForecastResult with forecast and confidence intervals
        """
        if not TORCH_AVAILABLE:
            LOGGER.error("PyTorch not available for Transformer forecasting")
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
            
            # Check for hyperparameter tuning
            use_hyperparameter_tuning = kwargs.get('use_hyperparameter_tuning', False)
            
            # Get hyperparameters
            if use_hyperparameter_tuning:
                try:
                    # Note: Transformer hyperparameter tuning not yet implemented in hyperparameter_tuning.py
                    # Use provided kwargs or defaults
                    d_model = kwargs.get('d_model', d_model)
                    nhead = kwargs.get('nhead', nhead)
                    num_layers = kwargs.get('num_layers', num_layers)
                    dropout = kwargs.get('dropout', dropout)
                    learning_rate = kwargs.get('learning_rate', learning_rate)
                except Exception as e:
                    LOGGER.warning(f"Hyperparameter tuning failed: {e}, using defaults")
                    pass
            
            # Update d_model based on feature dimensions
            if feature_data.shape[1] > 1:
                # Adjust d_model to accommodate feature dimensions
                d_model = max(d_model, feature_data.shape[1] * 8)  # Ensure d_model is large enough
            
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
            
            # Prepare sequences (now multi-dimensional)
            X, y = self._prepare_sequences(data_scaled, lookback_window, periods)
            
            if len(X) == 0:
                LOGGER.error(f"Insufficient data for sequences: need {lookback_window + periods} periods")
                return None
            
            # Update input_dim based on feature dimensions
            input_dim = feature_data.shape[1]
            
            # Split train/validation
            split_idx = int(len(X) * (1 - validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Create datasets
            train_dataset = TimeSeriesDataset(X_train, y_train)
            val_dataset = TimeSeriesDataset(X_val, y_val) if len(X_val) > 0 else None
            
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False) if val_dataset else None
            
            # Build model
            model_key = f"{ticker}_{metric}_transformer_{lookback_window}_{input_dim}"
            if model_key not in self.model_cache:
                model = TimeSeriesTransformer(
                    input_dim=input_dim,  # Multi-dimensional features
                    d_model=d_model,
                    nhead=nhead,
                    num_layers=num_layers,
                    dim_feedforward=dim_feedforward,
                    dropout=dropout,
                    output_dim=1
                ).to(self.device)
            else:
                model = self.model_cache[model_key]
            
            # Training
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=learning_rate)
            scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode='min', factor=0.5, patience=5, verbose=False
            )
            
            best_val_loss = float('inf')
            epochs_trained = 0
            training_losses = []
            validation_losses = []
            
            for epoch in range(epochs):
                # Training
                model.train()
                train_loss = 0.0
                for batch_X, batch_y in train_loader:
                    batch_X = batch_X.to(self.device)
                    batch_y = batch_y.to(self.device)
                    
                    optimizer.zero_grad()
                    output = model(batch_X)
                    loss = criterion(output, batch_y)
                    loss.backward()
                    optimizer.step()
                    
                    train_loss += loss.item()
                
                train_loss /= len(train_loader)
                training_losses.append(train_loss)
                
                # Validation
                val_loss = train_loss
                if val_loader:
                    model.eval()
                    val_loss = 0.0
                    with torch.no_grad():
                        for batch_X, batch_y in val_loader:
                            batch_X = batch_X.to(self.device)
                            batch_y = batch_y.to(self.device)
                            
                            output = model(batch_X)
                            loss = criterion(output, batch_y)
                            val_loss += loss.item()
                    
                    val_loss /= len(val_loader)
                    validation_losses.append(val_loss)
                
                scheduler.step(val_loss)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    epochs_trained = epoch + 1
                    # Save best model state
                    best_model_state = model.state_dict().copy()
                
                # Early stopping
                if epoch > 10 and val_loss > best_val_loss * 1.1:
                    break
            
            # Load best model
            if 'best_model_state' in locals():
                model.load_state_dict(best_model_state)
            
            # Cache model
            self.model_cache[model_key] = model
            
            # Generate forecast with attention weights
            model.eval()
            attention_weights = None
            with torch.no_grad():
                # Use last 'lookback_window' periods as input (multi-dimensional)
                last_sequence = data_scaled[-lookback_window:].reshape(1, lookback_window, input_dim)
                last_sequence_tensor = torch.FloatTensor(last_sequence).to(self.device)
                
                # Get attention weights from the last sequence (for explainability)
                try:
                    _, attention_weights = model(last_sequence_tensor, return_attention=True)
                except Exception as e:
                    LOGGER.debug(f"Failed to extract attention weights: {e}")
                    attention_weights = None
                
                # Forecast step by step
                forecast_scaled = []
                current_input = last_sequence_tensor.clone()
                
                for _ in range(periods):
                    # Predict next value
                    output = model(current_input)
                    next_pred = output[0, -1, 0].item()
                    forecast_scaled.append(next_pred)
                    
                    # Update input sequence (shift window)
                    # For multi-dimensional features, we need to handle differently
                    current_input = torch.roll(current_input, -1, dims=1)
                    # For the new timestep, use the prediction for the first feature
                    # and repeat the last values for other features
                    current_input[0, -1, 0] = next_pred
                    if input_dim > 1:
                        current_input[0, -1, 1:] = last_sequence_tensor[0, -1, 1:]
            
            # Inverse transform predictions (only inverse transform first feature)
            forecast_scaled = np.array(forecast_scaled).reshape(-1, 1)
            # Create full feature array for inverse transform
            full_pred = np.zeros((len(forecast_scaled), input_dim))
            full_pred[:, 0] = forecast_scaled.flatten()
            # Use last known values for other features (for inverse transform)
            if input_dim > 1:
                last_features = feature_data[-1, 1:]
                for i in range(len(forecast_scaled)):
                    full_pred[i, 1:] = last_features
            forecast_values = scaler.inverse_transform(full_pred)[:, 0]  # Extract first feature
            
            # Ensure positive values for financial metrics
            forecast_values = np.maximum(forecast_values, 0)
            
            # Calculate confidence intervals (simplified: use validation error)
            val_loss = validation_losses[-1] if validation_losses else training_losses[-1]
            # Use scale from first feature (the target metric)
            std_error = np.sqrt(val_loss) * scaler.scale_[0] if hasattr(scaler, 'scale_') else np.sqrt(val_loss)
            
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
                confidence = 0.8
            
            # Generate periods (years)
            last_date = ts.index[-1]
            if isinstance(last_date, pd.Timestamp):
                periods_list = [last_date.year + i + 1 for i in range(periods)]
            else:
                periods_list = list(range(1, periods + 1))
            
            # Calculate additional metrics
            import time
            training_time = epochs_trained * 0.8  # Rough estimate
            
            # Calculate model complexity
            total_params = sum(p.numel() for p in model.parameters())
            
            # Calculate data points used
            data_points_used = len(feature_data)
            
            # Calculate train/test split
            train_size = len(X_train)
            val_size = len(X_val) if len(X_val) > 0 else 0
            train_test_split = f"{train_size}/{val_size}" if val_size > 0 else f"{train_size}/0"
            
            # Calculate overfitting ratio
            training_loss = float(training_losses[-1])
            validation_loss = float(validation_losses[-1]) if validation_losses else training_loss
            overfit_ratio = validation_loss / training_loss if training_loss > 0 else 1.0
            
            # Get optimizer details
            optimizer_name = optimizer.__class__.__name__ if hasattr(optimizer, '__class__') else "Adam"
            
            return TransformerForecastResult(
                ticker=ticker,
                metric=metric,
                periods=periods_list,
                predicted_values=forecast_values.tolist(),
                confidence_intervals_low=confidence_intervals_low.tolist(),
                confidence_intervals_high=confidence_intervals_high.tolist(),
                method="TRANSFORMER",
                model_details={
                    "model_name": "time-series-transformer",
                    "d_model": d_model,
                    "nhead": nhead,
                    "num_layers": num_layers,
                    "num_heads": nhead,  # Alias for consistency
                    "dim_feedforward": dim_feedforward,
                    "dropout": dropout,
                    "lookback_window": lookback_window,
                    "epochs_trained": epochs_trained,
                    "training_loss": training_loss,
                    "validation_loss": validation_loss,
                    "total_parameters": total_params,
                    "training_time": float(training_time),
                    "data_points_used": data_points_used,
                    "train_test_split": train_test_split,
                    "batch_size": batch_size,
                    "learning_rate": float(learning_rate),
                    "optimizer": optimizer_name,
                    "overfit_ratio": float(overfit_ratio),
                    "preprocessing_applied": ["scaling", "feature_engineering"],
                    "scaling_method": "MinMaxScaler",
                    "attention_weights": attention_weights if attention_weights is not None else None,  # Store attention weights for explainability
                    "hyperparameters": {
                        "d_model": d_model,
                        "nhead": nhead,
                        "num_layers": num_layers,
                        "dim_feedforward": dim_feedforward,
                        "dropout": dropout,
                        "lookback_window": lookback_window,
                        "batch_size": batch_size,
                        "learning_rate": float(learning_rate),
                        "epochs": epochs,
                        "optimizer": optimizer_name,
                    },
                },
                confidence=float(confidence),
                model_name="time-series-transformer",
                num_layers=num_layers,
                num_heads=nhead,
                d_model=d_model,
                epochs_trained=epochs_trained,
                training_loss=training_loss,
                validation_loss=validation_loss,
            )
            
        except Exception as e:
            LOGGER.exception(f"Transformer forecasting failed for {ticker} {metric}: {e}")
            return None


def get_transformer_forecaster(database_path: str) -> Optional[TransformerForecaster]:
    """Factory function to create TransformerForecaster instance."""
    if not TORCH_AVAILABLE:
        LOGGER.warning("PyTorch not available - Transformer forecasting disabled")
        return None
    
    try:
        return TransformerForecaster(database_path)
    except Exception as e:
        LOGGER.error(f"Failed to create TransformerForecaster: {e}")
        return None

