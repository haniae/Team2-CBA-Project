"""
Feature Engineering Module for ML Forecasting

Provides rolling features, lag features, difference features, and transformations
for time series forecasting.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

LOGGER = logging.getLogger(__name__)


class FeatureEngineering:
    """
    Generate engineered features for time series forecasting.
    
    Provides:
    - Rolling statistics (mean, std, min, max)
    - Lag features (1-period, 2-period, etc.)
    - Difference features (first difference, second difference)
    - Percentage change features (YoY, QoQ)
    - Polynomial features (squared, cubed)
    """
    
    def __init__(self):
        """Initialize feature engineering generator."""
        pass
    
    def generate_rolling_features(
        self,
        data: pd.Series,
        windows: List[int] = [3, 5, 10, 20],
        stats: List[str] = ['mean', 'std', 'min', 'max']
    ) -> pd.DataFrame:
        """
        Generate rolling statistics features.
        
        Args:
            data: Time series data
            windows: List of window sizes for rolling calculations
            stats: List of statistics to calculate ('mean', 'std', 'min', 'max', 'median', 'skew', 'kurt')
            
        Returns:
            DataFrame with rolling features as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        for window in windows:
            rolling = data.rolling(window=window)
            
            if 'mean' in stats:
                df[f'rolling_mean_{window}'] = rolling.mean()
            if 'std' in stats:
                df[f'rolling_std_{window}'] = rolling.std()
            if 'min' in stats:
                df[f'rolling_min_{window}'] = rolling.min()
            if 'max' in stats:
                df[f'rolling_max_{window}'] = rolling.max()
            if 'median' in stats:
                df[f'rolling_median_{window}'] = rolling.median()
            if 'skew' in stats:
                df[f'rolling_skew_{window}'] = rolling.skew()
            if 'kurt' in stats or 'kurtosis' in stats:
                df[f'rolling_kurt_{window}'] = rolling.apply(lambda x: x.kurtosis())
        
        return df
    
    def generate_lag_features(
        self,
        data: pd.Series,
        lags: List[int] = [1, 2, 3, 4, 5, 10]
    ) -> pd.DataFrame:
        """
        Generate lag features.
        
        Args:
            data: Time series data
            lags: List of lag periods
            
        Returns:
            DataFrame with lag features as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        for lag in lags:
            df[f'lag_{lag}'] = data.shift(lag)
        
        return df
    
    def generate_difference_features(
        self,
        data: pd.Series,
        orders: List[int] = [1, 2]
    ) -> pd.DataFrame:
        """
        Generate difference features.
        
        Args:
            data: Time series data
            orders: List of difference orders (1 = first difference, 2 = second difference)
            
        Returns:
            DataFrame with difference features as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        for order in orders:
            df[f'diff_{order}'] = data.diff(periods=order)
            df[f'pct_change_{order}'] = data.pct_change(periods=order)
        
        return df
    
    def generate_periodic_features(
        self,
        data: pd.Series,
        periods: List[int] = [4, 12]  # Quarterly and yearly for financial data
    ) -> pd.DataFrame:
        """
        Generate periodic change features (YoY, QoQ).
        
        Args:
            data: Time series data
            periods: List of periods for percentage change (4 = quarterly, 12 = yearly)
            
        Returns:
            DataFrame with periodic change features as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        for period in periods:
            df[f'pct_change_{period}'] = data.pct_change(periods=period)
            df[f'change_{period}'] = data.diff(periods=period)
            
            # Calculate growth rate
            df[f'growth_rate_{period}'] = ((data / data.shift(periods=period)) - 1) * 100
        
        return df
    
    def generate_polynomial_features(
        self,
        data: pd.Series,
        degrees: List[int] = [2, 3]
    ) -> pd.DataFrame:
        """
        Generate polynomial features (squared, cubed, etc.).
        
        Args:
            data: Time series data
            degrees: List of polynomial degrees
            
        Returns:
            DataFrame with polynomial features as columns
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        for degree in degrees:
            df[f'value_pow_{degree}'] = data ** degree
        
        # Square root
        df['value_sqrt'] = np.sqrt(data.abs())
        
        # Logarithmic transformation (handle zeros/negatives)
        df['value_log'] = np.log(data + 1)
        
        return df
    
    def generate_all_features(
        self,
        data: pd.Series,
        include_rolling: bool = True,
        include_lags: bool = True,
        include_differences: bool = True,
        include_periodic: bool = True,
        include_polynomial: bool = True
    ) -> pd.DataFrame:
        """
        Generate all feature types.
        
        Args:
            data: Time series data
            include_rolling: Whether to include rolling features
            include_lags: Whether to include lag features
            include_differences: Whether to include difference features
            include_periodic: Whether to include periodic features
            include_polynomial: Whether to include polynomial features
            
        Returns:
            DataFrame with all engineered features
        """
        df = pd.DataFrame(index=data.index)
        df['value'] = data.values
        
        if include_rolling:
            rolling_df = self.generate_rolling_features(data)
            df = pd.concat([df, rolling_df.drop(columns=['value'])], axis=1)
        
        if include_lags:
            lag_df = self.generate_lag_features(data)
            df = pd.concat([df, lag_df.drop(columns=['value'])], axis=1)
        
        if include_differences:
            diff_df = self.generate_difference_features(data)
            df = pd.concat([df, diff_df.drop(columns=['value'])], axis=1)
        
        if include_periodic:
            periodic_df = self.generate_periodic_features(data)
            df = pd.concat([df, periodic_df.drop(columns=['value'])], axis=1)
        
        if include_polynomial:
            poly_df = self.generate_polynomial_features(data)
            df = pd.concat([df, poly_df.drop(columns=['value'])], axis=1)
        
        return df
    
    def get_feature_names(
        self,
        include_rolling: bool = True,
        include_lags: bool = True,
        include_differences: bool = True,
        include_periodic: bool = True,
        include_polynomial: bool = True
    ) -> List[str]:
        """Get list of all feature column names."""
        features = ['value']
        
        if include_rolling:
            windows = [3, 5, 10, 20]
            stats = ['mean', 'std', 'min', 'max']
            for window in windows:
                for stat in stats:
                    features.append(f'rolling_{stat}_{window}')
        
        if include_lags:
            lags = [1, 2, 3, 4, 5, 10]
            for lag in lags:
                features.append(f'lag_{lag}')
        
        if include_differences:
            orders = [1, 2]
            for order in orders:
                features.append(f'diff_{order}')
                features.append(f'pct_change_{order}')
        
        if include_periodic:
            periods = [4, 12]
            for period in periods:
                features.append(f'pct_change_{period}')
                features.append(f'change_{period}')
                features.append(f'growth_rate_{period}')
        
        if include_polynomial:
            degrees = [2, 3]
            for degree in degrees:
                features.append(f'value_pow_{degree}')
            features.extend(['value_sqrt', 'value_log'])
        
        return features


def get_feature_engineering() -> FeatureEngineering:
    """Factory function to create FeatureEngineering instance."""
    return FeatureEngineering()

