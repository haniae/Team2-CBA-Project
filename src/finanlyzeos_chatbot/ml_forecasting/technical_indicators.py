"""
Technical Indicators Module for ML Forecasting

Provides technical indicators (moving averages, momentum, volatility, trend)
as features for forecasting models.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available - technical indicators will be limited")

LOGGER = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Generate technical indicators for time series data.
    
    Provides:
    - Moving averages (SMA, EMA, WMA)
    - Momentum indicators (RSI, MACD, Stochastic)
    - Volatility indicators (Bollinger Bands, ATR)
    - Trend indicators (ADX, Parabolic SAR)
    """
    
    def __init__(self):
        """Initialize technical indicators generator."""
        pass
    
    def generate_indicators(
        self,
        data: pd.Series,
        include_all: bool = False
    ) -> pd.DataFrame:
        """
        Generate all technical indicators for a time series.
        
        Args:
            data: Time series data (price/values)
            include_all: Whether to include all indicators (default: False, only essential)
            
        Returns:
            DataFrame with technical indicators as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        # Moving averages
        df = self._add_moving_averages(df, data)
        
        # Momentum indicators
        df = self._add_momentum_indicators(df, data)
        
        # Volatility indicators
        df = self._add_volatility_indicators(df, data)
        
        if include_all:
            # Trend indicators
            df = self._add_trend_indicators(df, data)
        
        return df
    
    def _add_moving_averages(
        self,
        df: pd.DataFrame,
        data: pd.Series
    ) -> pd.DataFrame:
        """Add moving average indicators."""
        # Simple Moving Averages
        df['sma_5'] = data.rolling(window=5).mean()
        df['sma_10'] = data.rolling(window=10).mean()
        df['sma_20'] = data.rolling(window=20).mean()
        
        # Exponential Moving Averages
        df['ema_5'] = data.ewm(span=5, adjust=False).mean()
        df['ema_10'] = data.ewm(span=10, adjust=False).mean()
        df['ema_20'] = data.ewm(span=20, adjust=False).mean()
        
        # Weighted Moving Average
        weights = np.arange(1, 21)
        df['wma_20'] = data.rolling(window=20).apply(
            lambda x: np.sum(weights * x) / np.sum(weights), raw=True
        )
        
        return df
    
    def _add_momentum_indicators(
        self,
        df: pd.DataFrame,
        data: pd.Series
    ) -> pd.DataFrame:
        """Add momentum indicators."""
        # RSI (Relative Strength Index)
        if PANDAS_TA_AVAILABLE:
            try:
                rsi = ta.rsi(data, length=14)
                df['rsi'] = rsi
            except Exception:
                df['rsi'] = self._calculate_rsi(data)
        else:
            df['rsi'] = self._calculate_rsi(data)
        
        # MACD (Moving Average Convergence Divergence)
        if PANDAS_TA_AVAILABLE:
            try:
                macd = ta.macd(data, fast=12, slow=26, signal=9)
                if isinstance(macd, pd.DataFrame):
                    df['macd'] = macd.iloc[:, 0]  # MACD line
                    df['macd_signal'] = macd.iloc[:, 1]  # Signal line
                    df['macd_hist'] = macd.iloc[:, 2]  # Histogram
                else:
                    df['macd'] = macd
            except Exception:
                df['macd'] = self._calculate_macd(data)
                df['macd_signal'] = None
                df['macd_hist'] = None
        else:
            df['macd'] = self._calculate_macd(data)
            df['macd_signal'] = None
            df['macd_hist'] = None
        
        # Stochastic Oscillator
        if PANDAS_TA_AVAILABLE:
            try:
                stoch = ta.stoch(data, data, data, k=14, d=3)
                if isinstance(stoch, pd.DataFrame):
                    df['stoch_k'] = stoch.iloc[:, 0]
                    df['stoch_d'] = stoch.iloc[:, 1]
                else:
                    df['stoch_k'] = stoch
            except Exception:
                df['stoch_k'] = None
                df['stoch_d'] = None
        else:
            df['stoch_k'] = None
            df['stoch_d'] = None
        
        # Rate of Change
        df['roc_5'] = data.pct_change(periods=5)
        df['roc_10'] = data.pct_change(periods=10)
        
        return df
    
    def _add_volatility_indicators(
        self,
        df: pd.DataFrame,
        data: pd.Series
    ) -> pd.DataFrame:
        """Add volatility indicators."""
        # Bollinger Bands
        sma_20 = data.rolling(window=20).mean()
        std_20 = data.rolling(window=20).std()
        df['bb_upper'] = sma_20 + (std_20 * 2)
        df['bb_middle'] = sma_20
        df['bb_lower'] = sma_20 - (std_20 * 2)
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (data - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Average True Range (ATR) - simplified without high/low
        df['atr'] = data.rolling(window=14).apply(lambda x: np.std(x), raw=True)
        
        # Volatility (standard deviation)
        df['volatility_5'] = data.rolling(window=5).std()
        df['volatility_10'] = data.rolling(window=10).std()
        df['volatility_20'] = data.rolling(window=20).std()
        
        return df
    
    def _add_trend_indicators(
        self,
        df: pd.DataFrame,
        data: pd.Series
    ) -> pd.DataFrame:
        """Add trend indicators."""
        # ADX (Average Directional Index) - simplified
        # Full ADX requires high/low data, so we use a simplified version
        df['adx'] = None  # Would need high/low data
        
        # Simple trend (slope of moving average)
        df['trend_5'] = df['sma_5'].diff()
        df['trend_10'] = df['sma_10'].diff()
        df['trend_20'] = df['sma_20'].diff()
        
        return df
    
    def _calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI manually."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(
        self,
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.Series:
        """Calculate MACD manually."""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        
        return macd
    
    def get_indicator_names(self) -> List[str]:
        """Get list of all indicator column names."""
        return [
            'sma_5', 'sma_10', 'sma_20',
            'ema_5', 'ema_10', 'ema_20',
            'wma_20',
            'rsi',
            'macd', 'macd_signal', 'macd_hist',
            'stoch_k', 'stoch_d',
            'roc_5', 'roc_10',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'atr',
            'volatility_5', 'volatility_10', 'volatility_20',
            'trend_5', 'trend_10', 'trend_20',
        ]


def get_technical_indicators() -> TechnicalIndicators:
    """Factory function to create TechnicalIndicators instance."""
    return TechnicalIndicators()

