"""
Regime Detection Module for ML Forecasting

Detects market regimes (bull, bear, volatile, stable) and structural breaks
in time series data to adjust forecasts accordingly.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime

try:
    from statsmodels.tsa.regime_switching import MarkovRegression
    MARKOV_AVAILABLE = True
except ImportError:
    MARKOV_AVAILABLE = False
    logging.warning("statsmodels Markov switching not available - regime detection will be limited")

try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False
    logging.warning("ruptures not available - change point detection will be limited")

LOGGER = logging.getLogger(__name__)


@dataclass
class RegimeInfo:
    """Information about detected regime."""
    regime_type: str  # 'bull', 'bear', 'volatile', 'stable'
    confidence: float  # Confidence in regime classification (0-1)
    change_points: List[datetime]  # Detected change points
    regime_periods: List[Dict[str, Any]]  # List of regime periods with start/end dates
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "regime_type": self.regime_type,
            "confidence": self.confidence,
            "change_points": [cp.isoformat() if isinstance(cp, datetime) else str(cp) for cp in self.change_points],
            "regime_periods": self.regime_periods,
        }


class RegimeDetector:
    """
    Detect market regimes and structural breaks in time series.
    
    Methods:
    - Markov Switching Models
    - Structural break detection (Chow test, CUSUM)
    - Change point detection (PELT algorithm)
    """
    
    def __init__(self):
        """Initialize regime detector."""
        pass
    
    def detect_markov_switching(
        self,
        data: pd.Series,
        k_regimes: int = 2
    ) -> Optional[RegimeInfo]:
        """
        Detect regimes using Markov Switching Model.
        
        Args:
            data: Time series data
            k_regimes: Number of regimes (default: 2 for bull/bear)
            
        Returns:
            RegimeInfo or None if fails
        """
        if not MARKOV_AVAILABLE:
            LOGGER.warning("Markov switching models not available")
            return None
        
        try:
            # Fit Markov switching model
            model = MarkovRegression(data.values, k_regimes=k_regimes, trend='c')
            result = model.fit()
            
            # Get regime probabilities
            regime_probs = result.smoothed_marginal_probabilities
            
            # Classify each period into regime
            regimes = np.argmax(regime_probs, axis=1)
            
            # Determine regime characteristics
            regime_means = []
            for i in range(k_regimes):
                regime_data = data.values[regimes == i]
                if len(regime_data) > 0:
                    regime_means.append(np.mean(regime_data))
                else:
                    regime_means.append(0)
            
            # Classify regimes as bull/bear based on mean
            if k_regimes == 2:
                if regime_means[0] > regime_means[1]:
                    regime_names = ['bull', 'bear']
                else:
                    regime_names = ['bear', 'bull']
            else:
                # Sort by mean and classify
                sorted_indices = np.argsort(regime_means)
                regime_names = ['stable', 'volatile', 'bull', 'bear'][:k_regimes]
            
            # Get current regime
            current_regime_idx = regimes[-1]
            current_regime = regime_names[current_regime_idx]
            confidence = float(regime_probs[-1, current_regime_idx])
            
            # Find change points (where regime changes)
            change_points = []
            for i in range(1, len(regimes)):
                if regimes[i] != regimes[i-1]:
                    change_points.append(data.index[i])
            
            # Create regime periods
            regime_periods = []
            start_idx = 0
            current_regime = regimes[0]
            
            for i in range(1, len(regimes)):
                if regimes[i] != current_regime:
                    regime_periods.append({
                        "regime": regime_names[current_regime],
                        "start": data.index[start_idx],
                        "end": data.index[i-1],
                    })
                    start_idx = i
                    current_regime = regimes[i]
            
            # Add last period
            if start_idx < len(regimes):
                regime_periods.append({
                    "regime": regime_names[current_regime],
                    "start": data.index[start_idx],
                    "end": data.index[-1],
                })
            
            return RegimeInfo(
                regime_type=current_regime,
                confidence=confidence,
                change_points=change_points,
                regime_periods=regime_periods,
            )
            
        except Exception as e:
            LOGGER.warning(f"Markov switching regime detection failed: {e}")
            return None
    
    def detect_change_points(
        self,
        data: pd.Series,
        method: str = "pelt",
        min_size: int = 2
    ) -> Optional[RegimeInfo]:
        """
        Detect change points using PELT algorithm.
        
        Args:
            data: Time series data
            method: Detection method ('pelt', 'binseg', 'window')
            min_size: Minimum segment size
            
        Returns:
            RegimeInfo with change points
        """
        if not RUPTURES_AVAILABLE:
            LOGGER.warning("ruptures not available for change point detection")
            return None
        
        try:
            # Convert to numpy array
            signal = data.values.reshape(-1, 1)
            
            # Detect change points
            if method == "pelt":
                algo = rpt.Pelt(model="rbf", min_size=min_size).fit(signal)
                change_point_indices = algo.predict(pen=10)
            elif method == "binseg":
                algo = rpt.Binseg(model="rbf", min_size=min_size).fit(signal)
                change_point_indices = algo.predict(n_bkps=3)
            elif method == "window":
                algo = rpt.Window(width=40, model="rbf", min_size=min_size).fit(signal)
                change_point_indices = algo.predict(n_bkps=3)
            else:
                LOGGER.warning(f"Unknown change point method: {method}")
                return None
            
            # Convert indices to dates
            change_points = [data.index[idx] for idx in change_point_indices[:-1]]  # Last is always end
            
            # Classify current regime based on recent trend
            if len(data) > 10:
                recent_data = data.iloc[-10:]
                trend = np.polyfit(range(len(recent_data)), recent_data.values, 1)[0]
                volatility = recent_data.std()
                
                if trend > 0 and volatility < data.std():
                    regime_type = "bull"
                elif trend < 0 and volatility < data.std():
                    regime_type = "bear"
                elif volatility > data.std() * 1.5:
                    regime_type = "volatile"
                else:
                    regime_type = "stable"
            else:
                regime_type = "stable"
            
            # Create regime periods from change points
            regime_periods = []
            start_idx = 0
            
            for cp_idx in change_point_indices[:-1]:
                regime_periods.append({
                    "regime": "unknown",
                    "start": data.index[start_idx],
                    "end": data.index[cp_idx - 1],
                })
                start_idx = cp_idx
            
            # Add last period
            if start_idx < len(data):
                regime_periods.append({
                    "regime": regime_type,
                    "start": data.index[start_idx],
                    "end": data.index[-1],
                })
            
            confidence = 0.7  # Default confidence for change point detection
            
            return RegimeInfo(
                regime_type=regime_type,
                confidence=confidence,
                change_points=change_points,
                regime_periods=regime_periods,
            )
            
        except Exception as e:
            LOGGER.warning(f"Change point detection failed: {e}")
            return None
    
    def detect_regime_simple(
        self,
        data: pd.Series,
        window: int = 20
    ) -> RegimeInfo:
        """
        Simple regime detection based on trend and volatility.
        
        Args:
            data: Time series data
            window: Window size for trend/volatility calculation
            
        Returns:
            RegimeInfo with detected regime
        """
        if len(data) < window:
            return RegimeInfo(
                regime_type="stable",
                confidence=0.5,
                change_points=[],
                regime_periods=[],
            )
        
        # Calculate rolling trend and volatility
        rolling_mean = data.rolling(window=window).mean()
        rolling_std = data.rolling(window=window).std()
        
        # Recent values
        recent_mean = rolling_mean.iloc[-1]
        recent_std = rolling_std.iloc[-1]
        overall_mean = data.mean()
        overall_std = data.std()
        
        # Calculate trend
        trend_values = rolling_mean.diff()
        recent_trend = trend_values.iloc[-window:].mean()
        
        # Classify regime
        if recent_trend > 0 and recent_std < overall_std * 1.2:
            regime_type = "bull"
            confidence = 0.75
        elif recent_trend < 0 and recent_std < overall_std * 1.2:
            regime_type = "bear"
            confidence = 0.75
        elif recent_std > overall_std * 1.5:
            regime_type = "volatile"
            confidence = 0.7
        else:
            regime_type = "stable"
            confidence = 0.6
        
        return RegimeInfo(
            regime_type=regime_type,
            confidence=confidence,
            change_points=[],
            regime_periods=[{
                "regime": regime_type,
                "start": data.index[0],
                "end": data.index[-1],
            }],
        )


def get_regime_detector() -> RegimeDetector:
    """Factory function to create RegimeDetector instance."""
    return RegimeDetector()

