"""
Data Preprocessing Module for ML Forecasting

Provides outlier detection, missing data imputation, data scaling, and trend decomposition.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Literal, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from sklearn.ensemble import IsolationForest

try:
    from statsmodels.tsa.seasonal import seasonal_decompose, STL
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels not available - decomposition will be limited")

LOGGER = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """Result of preprocessing operations."""
    data: pd.Series
    outliers_removed: int
    outliers_capped: int
    missing_filled: int
    scaler_used: str
    decomposition_method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "outliers_removed": self.outliers_removed,
            "outliers_capped": self.outliers_capped,
            "missing_filled": self.missing_filled,
            "scaler_used": self.scaler_used,
            "decomposition_method": self.decomposition_method,
        }


class OutlierDetector:
    """Detect and handle outliers in time series data."""
    
    def __init__(self):
        """Initialize outlier detector."""
        pass
    
    def detect_iqr(
        self,
        data: pd.Series,
        multiplier: float = 1.5
    ) -> pd.Series:
        """
        Detect outliers using IQR method.
        
        Args:
            data: Time series data
            multiplier: IQR multiplier (default 1.5)
            
        Returns:
            Boolean series indicating outliers
        """
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR
        
        outliers = (data < lower_bound) | (data > upper_bound)
        return outliers
    
    def detect_zscore(
        self,
        data: pd.Series,
        threshold: float = 3.0
    ) -> pd.Series:
        """
        Detect outliers using Z-score method.
        
        Args:
            data: Time series data
            threshold: Z-score threshold (default 3.0)
            
        Returns:
            Boolean series indicating outliers
        """
        z_scores = np.abs(stats.zscore(data.dropna()))
        outliers = pd.Series(z_scores > threshold, index=data.index)
        return outliers
    
    def detect_isolation_forest(
        self,
        data: pd.Series,
        contamination: float = 0.1
    ) -> pd.Series:
        """
        Detect outliers using Isolation Forest.
        
        Args:
            data: Time series data
            contamination: Expected proportion of outliers
            
        Returns:
            Boolean series indicating outliers
        """
        try:
            # Reshape for Isolation Forest
            X = data.dropna().values.reshape(-1, 1)
            
            if len(X) < 10:
                # Too few points for Isolation Forest
                return pd.Series(False, index=data.index)
            
            clf = IsolationForest(contamination=contamination, random_state=42)
            outliers = clf.fit_predict(X) == -1
            
            # Map back to original index
            outlier_series = pd.Series(False, index=data.index)
            outlier_series.loc[data.dropna().index] = outliers
            
            return outlier_series
            
        except Exception as e:
            LOGGER.warning(f"Isolation Forest outlier detection failed: {e}")
            return pd.Series(False, index=data.index)
    
    def handle_outliers(
        self,
        data: pd.Series,
        method: str = "iqr",
        strategy: str = "cap",  # 'remove', 'cap', 'interpolate'
        **kwargs
    ) -> Tuple[pd.Series, int, int]:
        """
        Detect and handle outliers.
        
        Args:
            data: Time series data
            method: Detection method ('iqr', 'zscore', 'isolation_forest')
            strategy: Handling strategy ('remove', 'cap', 'interpolate')
            **kwargs: Additional arguments for detection method
            
        Returns:
            Tuple of (cleaned_data, num_removed, num_capped)
        """
        # Detect outliers
        if method == "iqr":
            outliers = self.detect_iqr(data, **kwargs)
        elif method == "zscore":
            outliers = self.detect_zscore(data, **kwargs)
        elif method == "isolation_forest":
            outliers = self.detect_isolation_forest(data, **kwargs)
        else:
            LOGGER.warning(f"Unknown outlier detection method: {method}")
            return data, 0, 0
        
        num_outliers = outliers.sum()
        
        if num_outliers == 0:
            return data, 0, 0
        
        cleaned_data = data.copy()
        num_removed = 0
        num_capped = 0
        
        if strategy == "remove":
            cleaned_data = cleaned_data[~outliers]
            num_removed = num_outliers
        elif strategy == "cap":
            # Cap outliers at IQR bounds
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            cleaned_data.loc[outliers & (cleaned_data < lower_bound)] = lower_bound
            cleaned_data.loc[outliers & (cleaned_data > upper_bound)] = upper_bound
            num_capped = num_outliers
        elif strategy == "interpolate":
            # Interpolate outliers
            cleaned_data.loc[outliers] = np.nan
            cleaned_data = cleaned_data.interpolate(method='linear')
            num_capped = num_outliers
        
        return cleaned_data, num_removed, num_capped


class MissingDataImputer:
    """Impute missing data in time series."""
    
    def __init__(self):
        """Initialize missing data imputer."""
        pass
    
    def forward_fill(
        self,
        data: pd.Series
    ) -> pd.Series:
        """Forward fill missing values."""
        return data.fillna(method='ffill')
    
    def backward_fill(
        self,
        data: pd.Series
    ) -> pd.Series:
        """Backward fill missing values."""
        return data.fillna(method='bfill')
    
    def interpolate_linear(
        self,
        data: pd.Series
    ) -> pd.Series:
        """Linear interpolation."""
        return data.interpolate(method='linear')
    
    def interpolate_spline(
        self,
        data: pd.Series
    ) -> pd.Series:
        """Spline interpolation."""
        return data.interpolate(method='spline', order=2)
    
    def seasonal_impute(
        self,
        data: pd.Series,
        period: int = 4  # Quarterly for financial data
    ) -> pd.Series:
        """
        Seasonal imputation (use same period from previous year).
        
        Args:
            data: Time series data
            period: Seasonal period (4 for quarterly, 12 for monthly)
            
        Returns:
            Series with imputed values
        """
        imputed = data.copy()
        
        for i in range(len(data)):
            if pd.isna(data.iloc[i]):
                # Try to use value from same position in previous period
                prev_idx = i - period
                if prev_idx >= 0 and not pd.isna(data.iloc[prev_idx]):
                    imputed.iloc[i] = data.iloc[prev_idx]
                else:
                    # Fall back to interpolation
                    imputed = imputed.interpolate(method='linear')
        
        return imputed
    
    def impute(
        self,
        data: pd.Series,
        method: str = "interpolate",
        **kwargs
    ) -> pd.Series:
        """
        Impute missing data using specified method.
        
        Args:
            data: Time series data
            method: Imputation method ('forward_fill', 'backward_fill', 'interpolate_linear', 'interpolate_spline', 'seasonal')
            **kwargs: Additional arguments for specific methods
            
        Returns:
            Series with imputed values
        """
        if method == "forward_fill":
            return self.forward_fill(data)
        elif method == "backward_fill":
            return self.backward_fill(data)
        elif method == "interpolate_linear" or method == "interpolate":
            return self.interpolate_linear(data)
        elif method == "interpolate_spline":
            return self.interpolate_spline(data)
        elif method == "seasonal":
            period = kwargs.get('period', 4)
            return self.seasonal_impute(data, period)
        else:
            LOGGER.warning(f"Unknown imputation method: {method}, using linear interpolation")
            return self.interpolate_linear(data)


class DataScaler:
    """Scale and normalize time series data."""
    
    def __init__(self):
        """Initialize data scaler."""
        self.scaler = None
        self.scaler_type = None
    
    def minmax_scale(
        self,
        data: pd.Series,
        feature_range: Tuple[float, float] = (0, 1)
    ) -> Tuple[pd.Series, Any]:
        """
        MinMax scaling (0-1 range).
        
        Args:
            data: Time series data
            feature_range: Min and max values for scaling
            
        Returns:
            Tuple of (scaled_data, scaler)
        """
        scaler = MinMaxScaler(feature_range=feature_range)
        scaled_values = scaler.fit_transform(data.values.reshape(-1, 1))
        scaled_data = pd.Series(scaled_values.flatten(), index=data.index)
        
        self.scaler = scaler
        self.scaler_type = "minmax"
        
        return scaled_data, scaler
    
    def standard_scale(
        self,
        data: pd.Series
    ) -> Tuple[pd.Series, Any]:
        """
        Standard scaling (mean=0, std=1).
        
        Args:
            data: Time series data
            
        Returns:
            Tuple of (scaled_data, scaler)
        """
        scaler = StandardScaler()
        scaled_values = scaler.fit_transform(data.values.reshape(-1, 1))
        scaled_data = pd.Series(scaled_values.flatten(), index=data.index)
        
        self.scaler = scaler
        self.scaler_type = "standard"
        
        return scaled_data, scaler
    
    def robust_scale(
        self,
        data: pd.Series
    ) -> Tuple[pd.Series, Any]:
        """
        Robust scaling (median-based, outlier-resistant).
        
        Args:
            data: Time series data
            
        Returns:
            Tuple of (scaled_data, scaler)
        """
        scaler = RobustScaler()
        scaled_values = scaler.fit_transform(data.values.reshape(-1, 1))
        scaled_data = pd.Series(scaled_values.flatten(), index=data.index)
        
        self.scaler = scaler
        self.scaler_type = "robust"
        
        return scaled_data, scaler
    
    def log_transform(
        self,
        data: pd.Series
    ) -> pd.Series:
        """
        Log transformation (for skewed data).
        
        Args:
            data: Time series data
            
        Returns:
            Log-transformed series
        """
        # Handle negative or zero values
        min_val = data.min()
        if min_val <= 0:
            offset = abs(min_val) + 1
            data = data + offset
        
        return np.log(data)
    
    def box_cox_transform(
        self,
        data: pd.Series
    ) -> Tuple[pd.Series, float]:
        """
        Box-Cox transformation.
        
        Args:
            data: Time series data (must be positive)
            
        Returns:
            Tuple of (transformed_data, lambda_parameter)
        """
        # Box-Cox requires positive values
        min_val = data.min()
        if min_val <= 0:
            data = data - min_val + 1
        
        try:
            from scipy.stats import boxcox
            transformed, lambda_param = boxcox(data.values)
            transformed_data = pd.Series(transformed, index=data.index)
            return transformed_data, lambda_param
        except Exception as e:
            LOGGER.warning(f"Box-Cox transformation failed: {e}, using log transform")
            return self.log_transform(data), None
    
    def scale(
        self,
        data: pd.Series,
        method: str = "standard",
        **kwargs
    ) -> Tuple[pd.Series, Any]:
        """
        Scale data using specified method.
        
        Args:
            data: Time series data
            method: Scaling method ('minmax', 'standard', 'robust', 'log', 'boxcox')
            **kwargs: Additional arguments for specific methods
            
        Returns:
            Tuple of (scaled_data, scaler)
        """
        if method == "minmax":
            return self.minmax_scale(data, **kwargs)
        elif method == "standard":
            return self.standard_scale(data)
        elif method == "robust":
            return self.robust_scale(data)
        elif method == "log":
            return self.log_transform(data), None
        elif method == "boxcox":
            return self.box_cox_transform(data)
        else:
            LOGGER.warning(f"Unknown scaling method: {method}, using standard scaling")
            return self.standard_scale(data)
    
    def inverse_transform(
        self,
        scaled_data: pd.Series,
        scaler: Any = None
    ) -> pd.Series:
        """
        Inverse transform scaled data.
        
        Args:
            scaled_data: Scaled time series data
            scaler: Scaler used for transformation
            
        Returns:
            Original scale data
        """
        if scaler is None:
            scaler = self.scaler
        
        if scaler is None:
            LOGGER.warning("No scaler provided for inverse transform")
            return scaled_data
        
        if self.scaler_type in ["minmax", "standard", "robust"]:
            original_values = scaler.inverse_transform(scaled_data.values.reshape(-1, 1))
            return pd.Series(original_values.flatten(), index=scaled_data.index)
        else:
            # Log and Box-Cox require manual inverse
            LOGGER.warning("Inverse transform not implemented for log/boxcox")
            return scaled_data


class TrendDecomposer:
    """Decompose time series into trend, seasonal, and residual components."""
    
    def __init__(self):
        """Initialize trend decomposer."""
        pass
    
    def seasonal_decompose(
        self,
        data: pd.Series,
        model: str = "additive",
        period: Optional[int] = None
    ) -> Dict[str, pd.Series]:
        """
        Seasonal decomposition.
        
        Args:
            data: Time series data
            model: Decomposition model ('additive' or 'multiplicative')
            period: Seasonal period (auto-detected if None)
            
        Returns:
            Dictionary with 'trend', 'seasonal', 'resid' components
        """
        if not STATSMODELS_AVAILABLE:
            LOGGER.warning("statsmodels not available for decomposition")
            return {
                "trend": data,
                "seasonal": pd.Series(0, index=data.index),
                "resid": pd.Series(0, index=data.index),
            }
        
        try:
            if period is None:
                # Auto-detect period (try quarterly for financial data)
                if len(data) >= 8:
                    period = 4
                else:
                    period = len(data) // 2
            
            decomposition = seasonal_decompose(
                data,
                model=model,
                period=period,
                extrapolate_trend='freq'
            )
            
            return {
                "trend": decomposition.trend,
                "seasonal": decomposition.seasonal,
                "resid": decomposition.resid,
            }
            
        except Exception as e:
            LOGGER.warning(f"Seasonal decomposition failed: {e}")
            return {
                "trend": data,
                "seasonal": pd.Series(0, index=data.index),
                "resid": pd.Series(0, index=data.index),
            }
    
    def stl_decompose(
        self,
        data: pd.Series,
        period: Optional[int] = None
    ) -> Dict[str, pd.Series]:
        """
        STL decomposition (Seasonal and Trend decomposition using Loess).
        
        Args:
            data: Time series data
            period: Seasonal period (auto-detected if None)
            
        Returns:
            Dictionary with 'trend', 'seasonal', 'resid' components
        """
        if not STATSMODELS_AVAILABLE:
            LOGGER.warning("statsmodels not available for STL decomposition")
            return self.seasonal_decompose(data)
        
        try:
            if period is None:
                if len(data) >= 8:
                    period = 4
                else:
                    period = len(data) // 2
            
            stl = STL(data, period=period, robust=True)
            result = stl.fit()
            
            return {
                "trend": result.trend,
                "seasonal": result.seasonal,
                "resid": result.resid,
            }
            
        except Exception as e:
            LOGGER.warning(f"STL decomposition failed: {e}, falling back to seasonal decomposition")
            return self.seasonal_decompose(data)


def get_outlier_detector() -> OutlierDetector:
    """Factory function to create OutlierDetector instance."""
    return OutlierDetector()


def get_missing_data_imputer() -> MissingDataImputer:
    """Factory function to create MissingDataImputer instance."""
    return MissingDataImputer()


def get_data_scaler() -> DataScaler:
    """Factory function to create DataScaler instance."""
    return DataScaler()


def get_trend_decomposer() -> TrendDecomposer:
    """Factory function to create TrendDecomposer instance."""
    return TrendDecomposer()

