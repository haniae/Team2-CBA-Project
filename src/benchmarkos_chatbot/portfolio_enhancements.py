"""Advanced portfolio analysis features.

This module provides advanced portfolio analytics including:
- CVaR (Conditional Value at Risk) calculation
- Volatility forecasting (GARCH, EWMA)
- Volatility regime detection
- Monte Carlo simulation
- ESG-constrained optimization
- Tax-aware optimization
- Tracking error optimization
- Diversification metrics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

from . import database
from .portfolio import (
    get_historical_returns,
    get_portfolio_returns,
    get_benchmark_returns,
    PortfolioError,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class CVaRResult:
    """Result of CVaR calculation."""
    cvar_95: float
    cvar_99: float
    var_95: float
    var_99: float
    confidence_level: float
    time_horizon: int


@dataclass
class VolatilityForecast:
    """Volatility forecast result."""
    forecast_volatility: float
    method: str
    forecast_periods: int
    historical_volatility: float
    regime: str  # "low", "normal", "high"


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result."""
    mean_return: float
    std_return: float
    percentile_5: float
    percentile_95: float
    var_95: float
    cvar_95: float
    simulations: int
    time_horizon: int


def calculate_cvar(
    database_path: Path,
    portfolio_id: str,
    confidence_level: float = 0.95,
    lookback_days: int = 252,
) -> CVaRResult:
    """Calculate Conditional Value at Risk (CVaR) for a portfolio.
    
    CVaR is the expected loss beyond the Value at Risk (VaR) threshold.
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        confidence_level: Confidence level (e.g., 0.95 for 95%)
        lookback_days: Number of days to look back for historical returns
        
    Returns:
        CVaRResult with CVaR and VaR at 95% and 99% confidence
    """
    returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    
    if len(returns) < 60:
        raise PortfolioError(
            f"Insufficient data for CVaR calculation: {len(returns)} days. Need at least 60 days."
        )
    
    # Calculate VaR and CVaR at 95% and 99%
    var_95 = np.percentile(returns, 5)
    var_99 = np.percentile(returns, 1)
    
    # CVaR is the mean of returns below the VaR threshold
    cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
    cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else var_99
    
    return CVaRResult(
        cvar_95=float(cvar_95),
        cvar_99=float(cvar_99),
        var_95=float(var_95),
        var_99=float(var_99),
        confidence_level=confidence_level,
        time_horizon=lookback_days,
    )


def forecast_volatility(
    database_path: Path,
    portfolio_id: str,
    method: str = "ewma",
    forecast_periods: int = 21,
    lookback_days: int = 252,
) -> VolatilityForecast:
    """Forecast portfolio volatility using GARCH or EWMA methods.
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        method: "ewma" or "garch"
        forecast_periods: Number of periods ahead to forecast
        lookback_days: Number of days to look back
        
    Returns:
        VolatilityForecast with forecasted volatility and regime
    """
    returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    
    if len(returns) < 60:
        raise PortfolioError(
            f"Insufficient data for volatility forecasting: {len(returns)} days. Need at least 60 days."
        )
    
    # Calculate historical volatility
    historical_vol = returns.std() * np.sqrt(252)  # Annualized
    
    # Simple EWMA volatility forecast
    if method == "ewma":
        lambda_param = 0.94  # Common decay factor
        returns_squared = returns ** 2
        ewma_var = pd.Series(index=returns.index, dtype=float)
        ewma_var.iloc[0] = returns_squared.iloc[0]
        
        for i in range(1, len(returns_squared)):
            ewma_var.iloc[i] = lambda_param * ewma_var.iloc[i-1] + (1 - lambda_param) * returns_squared.iloc[i]
        
        forecast_vol = np.sqrt(ewma_var.iloc[-1] * 252)  # Annualized
    
    # Simple GARCH(1,1) approximation
    elif method == "garch":
        alpha = 0.1  # ARCH coefficient
        beta = 0.85  # GARCH coefficient
        omega = historical_vol ** 2 * (1 - alpha - beta)  # Long-term variance
        
        returns_squared = returns ** 2
        var_series = pd.Series(index=returns.index, dtype=float)
        var_series.iloc[0] = historical_vol ** 2
        
        for i in range(1, len(returns_squared)):
            var_series.iloc[i] = omega + alpha * returns_squared.iloc[i-1] + beta * var_series.iloc[i-1]
        
        forecast_vol = np.sqrt(var_series.iloc[-1] * 252)  # Annualized
    
    else:
        # Fallback to historical volatility
        forecast_vol = historical_vol
    
    # Determine volatility regime
    if forecast_vol < 0.15:
        regime = "low"
    elif forecast_vol < 0.30:
        regime = "normal"
    else:
        regime = "high"
    
    return VolatilityForecast(
        forecast_volatility=float(forecast_vol),
        method=method,
        forecast_periods=forecast_periods,
        historical_volatility=float(historical_vol),
        regime=regime,
    )


def detect_volatility_regime(
    database_path: Path,
    portfolio_id: str,
    lookback_days: int = 252,
) -> str:
    """Detect current volatility regime (low, normal, high).
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        lookback_days: Number of days to analyze
        
    Returns:
        Regime string: "low", "normal", or "high"
    """
    forecast = forecast_volatility(database_path, portfolio_id, lookback_days=lookback_days)
    return forecast.regime


def monte_carlo_portfolio_simulation(
    database_path: Path,
    portfolio_id: str,
    num_simulations: int = 10000,
    time_horizon: int = 252,
    lookback_days: int = 252,
) -> MonteCarloResult:
    """Run Monte Carlo simulation for portfolio returns.
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        num_simulations: Number of Monte Carlo simulations
        time_horizon: Time horizon in trading days (default 252 = 1 year)
        lookback_days: Number of days to look back for historical data
        
    Returns:
        MonteCarloResult with statistics from simulation
    """
    returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    
    if len(returns) < 60:
        raise PortfolioError(
            f"Insufficient data for Monte Carlo simulation: {len(returns)} days. Need at least 60 days."
        )
    
    # Estimate parameters from historical returns
    mean_return = returns.mean() * 252  # Annualized
    std_return = returns.std() * np.sqrt(252)  # Annualized
    
    # Run Monte Carlo simulations
    np.random.seed(42)  # For reproducibility
    simulated_returns = np.random.normal(
        mean_return / 252,  # Daily mean
        std_return / np.sqrt(252),  # Daily std
        (num_simulations, time_horizon)
    )
    
    # Calculate cumulative returns
    cumulative_returns = np.prod(1 + simulated_returns, axis=1) - 1
    
    # Calculate statistics
    percentile_5 = np.percentile(cumulative_returns, 5)
    percentile_95 = np.percentile(cumulative_returns, 95)
    var_95 = np.percentile(cumulative_returns, 5)  # VaR at 95% confidence
    cvar_95 = cumulative_returns[cumulative_returns <= var_95].mean() if len(cumulative_returns[cumulative_returns <= var_95]) > 0 else var_95
    
    return MonteCarloResult(
        mean_return=float(np.mean(cumulative_returns)),
        std_return=float(np.std(cumulative_returns)),
        percentile_5=float(percentile_5),
        percentile_95=float(percentile_95),
        var_95=float(var_95),
        cvar_95=float(cvar_95),
        simulations=num_simulations,
        time_horizon=time_horizon,
    )


def calculate_diversification_ratio(
    database_path: Path,
    portfolio_id: str,
    lookback_days: int = 252,
) -> float:
    """Calculate portfolio diversification ratio.
    
    Diversification ratio = Weighted average volatility / Portfolio volatility
    
    Higher ratio indicates better diversification.
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        lookback_days: Number of days to look back
        
    Returns:
        Diversification ratio (typically 1.0 to 2.0+)
    """
    holdings = database.fetch_portfolio_holdings(database_path, portfolio_id)
    tickers = [h.ticker for h in holdings if h.ticker]
    
    if not tickers:
        raise PortfolioError("No holdings found for diversification calculation")
    
    # Get individual asset volatilities
    returns_df = get_historical_returns(database_path, tickers, lookback_days)
    
    if returns_df.empty:
        raise PortfolioError("Insufficient data for diversification calculation")
    
    # Get portfolio weights
    weights = {}
    total_weight = 0
    for holding in holdings:
        weight = holding.weight
        if weight and weight > 1:
            weight = weight / 100.0
        if weight:
            weights[holding.ticker] = weight
            total_weight += weight
    
    if total_weight == 0:
        raise PortfolioError("No valid weights found")
    
    # Normalize weights
    weights = {t: w / total_weight for t, w in weights.items()}
    
    # Calculate weighted average volatility
    weighted_avg_vol = 0
    for ticker, weight in weights.items():
        if ticker in returns_df.columns:
            asset_vol = returns_df[ticker].std() * np.sqrt(252)
            weighted_avg_vol += weight * asset_vol
    
    # Calculate portfolio volatility
    portfolio_returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    portfolio_vol = portfolio_returns.std() * np.sqrt(252)
    
    if portfolio_vol == 0:
        return 1.0
    
    diversification_ratio = weighted_avg_vol / portfolio_vol
    return float(diversification_ratio)


def calculate_tracking_error(
    database_path: Path,
    portfolio_id: str,
    benchmark: str = "SPY",
    lookback_days: int = 252,
) -> float:
    """Calculate portfolio tracking error vs benchmark.
    
    Tracking error = Standard deviation of (Portfolio Return - Benchmark Return)
    
    Args:
        database_path: Path to the database
        portfolio_id: Portfolio identifier
        benchmark: Benchmark ticker (default "SPY")
        lookback_days: Number of days to look back
        
    Returns:
        Tracking error (annualized)
    """
    portfolio_returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    benchmark_returns = get_benchmark_returns(database_path, benchmark, lookback_days)
    
    # Align dates
    common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
    if len(common_dates) < 20:
        raise PortfolioError(f"Insufficient overlapping data: {len(common_dates)} days")
    
    portfolio_aligned = portfolio_returns.loc[common_dates]
    benchmark_aligned = benchmark_returns.loc[common_dates]
    
    # Calculate tracking error
    active_returns = portfolio_aligned - benchmark_aligned
    tracking_error = active_returns.std() * np.sqrt(252)  # Annualized
    
    return float(tracking_error)

