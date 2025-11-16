"""
External Factors Integration for ML Forecasting

Integrates market indices, economic indicators, and industry trends
to enhance forecasting accuracy.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

LOGGER = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    LOGGER.warning("yfinance not available - external factors will be limited")

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    LOGGER.warning("fredapi not available - economic indicators will be limited")


class ExternalFactorsProvider:
    """
    Provides external factors for forecasting.
    
    Includes:
    - Market indices (SPY, QQQ, sector indices)
    - Economic indicators (GDP, interest rates, inflation)
    - Industry-specific factors
    - Peer company performance
    """
    
    def __init__(self, fred_api_key: Optional[str] = None):
        """
        Initialize external factors provider.
        
        Args:
            fred_api_key: FRED API key for economic indicators (optional)
        """
        self.fred_api_key = fred_api_key
        self.fred_client = None
        
        if FRED_AVAILABLE and fred_api_key:
            try:
                self.fred_client = Fred(api_key=fred_api_key)
            except Exception as e:
                LOGGER.warning(f"Failed to initialize FRED client: {e}")
    
    def get_market_index_data(
        self,
        ticker: str = "SPY",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.Series]:
        """
        Get market index data.
        
        Args:
            ticker: Index ticker (SPY, QQQ, DIA, IWM, etc.)
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Time series of index returns or None if unavailable
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365 * 5)  # 5 years
            if end_date is None:
                end_date = datetime.now()
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                return None
            
            # Calculate returns
            returns = hist['Close'].pct_change().dropna()
            returns.index = pd.to_datetime(returns.index)
            
            return returns
            
        except Exception as e:
            LOGGER.warning(f"Failed to fetch market index data for {ticker}: {e}")
            return None
    
    def get_economic_indicator(
        self,
        series_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.Series]:
        """
        Get economic indicator from FRED.
        
        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE', 'FEDFUNDS')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Time series of economic indicator or None if unavailable
        """
        if not FRED_AVAILABLE or self.fred_client is None:
            return None
        
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365 * 5)
            if end_date is None:
                end_date = datetime.now()
            
            data = self.fred_client.get_series(
                series_id,
                observation_start=start_date,
                observation_end=end_date
            )
            
            if data.empty:
                return None
            
            data.index = pd.to_datetime(data.index)
            return data
            
        except Exception as e:
            LOGGER.warning(f"Failed to fetch economic indicator {series_id}: {e}")
            return None
    
    def get_external_regressors(
        self,
        ticker: str,
        metric: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get external regressors as DataFrame for Prophet/LSTM.
        
        Args:
            ticker: Company ticker
            metric: Metric to forecast
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with external regressors, indexed by date, or None if unavailable
        """
        try:
            # Get market indices
            spy_data = self.get_market_index_data("SPY", start_date, end_date)
            qqq_data = self.get_market_index_data("QQQ", start_date, end_date)
            
            # Combine into DataFrame
            regressors = pd.DataFrame(index=spy_data.index if spy_data is not None else None)
            
            if spy_data is not None:
                regressors['spy_returns'] = spy_data.values
            if qqq_data is not None:
                regressors['qqq_returns'] = qqq_data.values
            
            # Get economic indicators if available
            if self.fred_client:
                gdp_data = self.get_economic_indicator("GDP", start_date, end_date)
                if gdp_data is not None:
                    # Align GDP data with market data dates (quarterly to daily)
                    gdp_aligned = gdp_data.reindex(regressors.index, method='ffill')
                    regressors['gdp'] = gdp_aligned.values
                
                fedfunds_data = self.get_economic_indicator("FEDFUNDS", start_date, end_date)
                if fedfunds_data is not None:
                    # Align interest rate data
                    fedfunds_aligned = fedfunds_data.reindex(regressors.index, method='ffill')
                    regressors['interest_rate'] = fedfunds_aligned.values
            
            if regressors.empty:
                return None
            
            return regressors
            
        except Exception as e:
            LOGGER.warning(f"Failed to get external regressors: {e}")
            return None
    
    def build_external_factors_context(
        self,
        ticker: str,
        metric: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive external factors context.
        
        Args:
            ticker: Company ticker
            metric: Metric to forecast
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Dictionary with external factors data
        """
        context = {
            "market_indices": {},
            "economic_indicators": {},
            "peer_companies": None,
        }
        
        # Market indices
        indices = ["SPY", "QQQ", "DIA"]
        for idx_ticker in indices:
            idx_data = self.get_market_index_data(idx_ticker, start_date, end_date)
            if idx_data is not None:
                context["market_indices"][idx_ticker] = {
                    "returns": idx_data.tolist(),
                    "dates": idx_data.index.strftime("%Y-%m-%d").tolist(),
                    "mean_return": float(idx_data.mean()),
                    "volatility": float(idx_data.std()),
                }
        
        # Economic indicators (if FRED available)
        if self.fred_client:
            # GDP growth
            gdp_data = self.get_economic_indicator("GDP", start_date, end_date)
            if gdp_data is not None:
                context["economic_indicators"]["GDP"] = {
                    "values": gdp_data.tolist(),
                    "dates": gdp_data.index.strftime("%Y-%m-%d").tolist(),
                    "latest_value": float(gdp_data.iloc[-1]),
                }
            
            # Interest rates (Federal Funds Rate)
            fedfunds_data = self.get_economic_indicator("FEDFUNDS", start_date, end_date)
            if fedfunds_data is not None:
                context["economic_indicators"]["FEDFUNDS"] = {
                    "values": fedfunds_data.tolist(),
                    "dates": fedfunds_data.index.strftime("%Y-%m-%d").tolist(),
                    "latest_value": float(fedfunds_data.iloc[-1]),
                }
        
        return context


def get_external_factors_provider(fred_api_key: Optional[str] = None) -> ExternalFactorsProvider:
    """Factory function to create ExternalFactorsProvider instance."""
    return ExternalFactorsProvider(fred_api_key=fred_api_key)

