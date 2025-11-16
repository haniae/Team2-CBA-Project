"""Portfolio calculations using real historical data: covariance matrix, beta, etc."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from . import database
import sqlite3 as _sqlite3

LOGGER = logging.getLogger(__name__)


def fetch_historical_prices(
    database_path: database.Path,
    ticker: str,
    start_date: datetime,
    end_date: datetime,
) -> List[Tuple[datetime, float]]:
    """
    Fetch historical prices for a ticker from the database.
    
    Returns list of (date, price) tuples sorted by date.
    """
    with database._connect(database_path) as conn:
        conn.row_factory = _sqlite3.Row
        rows = conn.execute(
            """
            SELECT quote_time, price
            FROM market_quotes
            WHERE ticker = ? AND quote_time >= ? AND quote_time <= ?
            ORDER BY quote_time ASC
            """,
            (
                database._normalize_ticker(ticker),
                database._iso_utc(start_date),
                database._iso_utc(end_date),
            ),
        ).fetchall()
    
    prices = []
    for row in rows:
        quote_time = database._parse_dt(row["quote_time"])
        if quote_time:
            prices.append((quote_time, row["price"]))
    
    return prices


def calculate_returns(prices: List[Tuple[datetime, float]]) -> np.ndarray:
    """
    Calculate daily returns from price series.
    
    Returns numpy array of daily returns (pct_change).
    """
    if len(prices) < 2:
        return np.array([])
    
    price_values = np.array([p[1] for p in prices])
    returns = np.diff(price_values) / price_values[:-1]
    return returns


def calculate_covariance_matrix(
    database_path: database.Path,
    ticker_list: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 252,
) -> Tuple[np.ndarray, List[str]]:
    """
    Calculate covariance matrix from historical price data.
    
    Args:
        database_path: Path to database
        ticker_list: List of tickers to include
        start_date: Start date (defaults to lookback_days ago)
        end_date: End date (defaults to today)
        lookback_days: Number of trading days to look back (default 252 = 1 year)
    
    Returns:
        Tuple of (covariance_matrix, valid_ticker_list)
        Only includes tickers with sufficient historical data.
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=lookback_days * 2)  # Extra buffer for weekends
    
    # Fetch historical prices for all tickers
    ticker_returns: Dict[str, np.ndarray] = {}
    valid_tickers = []
    
    for ticker in ticker_list:
        prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
        
        if len(prices) < 2:
            LOGGER.warning(f"Insufficient price data for {ticker}: {len(prices)} observations")
            continue
        
        returns = calculate_returns(prices)
        
        if len(returns) < 20:  # Need at least 20 observations
            LOGGER.warning(f"Insufficient returns for {ticker}: {len(returns)} observations")
            continue
        
        ticker_returns[ticker] = returns
        valid_tickers.append(ticker)
    
    if not valid_tickers:
        LOGGER.warning("No valid tickers with sufficient historical data")
        # Return identity matrix as fallback
        n = len(ticker_list)
        return np.eye(n) * 0.04, ticker_list
    
    # Align returns by date (if we had date info, but we'll use length matching for now)
    # For simplicity, we'll use the minimum length across all tickers
    min_length = min(len(returns) for returns in ticker_returns.values())
    
    # Truncate all returns to same length (take most recent)
    aligned_returns = np.array([
        ticker_returns[ticker][-min_length:] for ticker in valid_tickers
    ])
    
    # Calculate covariance matrix
    # Shape: (n_tickers, n_days) -> (n_tickers, n_tickers)
    covariance_matrix = np.cov(aligned_returns) * 252  # Annualize (252 trading days)
    
    # Ensure positive semi-definite
    covariance_matrix = (covariance_matrix + covariance_matrix.T) / 2
    
    # Add small regularization term if needed
    eigenvals = np.linalg.eigvals(covariance_matrix)
    if np.any(eigenvals < 0):
        LOGGER.warning("Covariance matrix not positive semi-definite, adding regularization")
        regularization = np.abs(np.min(eigenvals)) + 0.01
        covariance_matrix += np.eye(len(valid_tickers)) * regularization
    
    return covariance_matrix, valid_tickers


def calculate_beta(
    database_path: database.Path,
    ticker: str,
    benchmark: str = "SPY",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 252,
) -> Optional[float]:
    """
    Calculate beta via regression of ticker returns vs benchmark returns.
    
    Args:
        database_path: Path to database
        ticker: Ticker to calculate beta for
        benchmark: Benchmark ticker (default: SPY for S&P 500)
        start_date: Start date (defaults to lookback_days ago)
        end_date: End date (defaults to today)
        lookback_days: Number of trading days to look back (default 252 = 1 year)
    
    Returns:
        Beta coefficient, or None if insufficient data
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=lookback_days * 2)
    
    # Fetch historical prices
    ticker_prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
    benchmark_prices = fetch_historical_prices(database_path, benchmark, start_date, end_date)
    
    if len(ticker_prices) < 20 or len(benchmark_prices) < 20:
        LOGGER.warning(f"Insufficient data for beta calculation: {ticker} ({len(ticker_prices)} obs), {benchmark} ({len(benchmark_prices)} obs)")
        return None
    
    # Calculate returns
    ticker_returns = calculate_returns(ticker_prices)
    benchmark_returns = calculate_returns(benchmark_prices)
    
    if len(ticker_returns) < 20 or len(benchmark_returns) < 20:
        return None
    
    # Align by length (take most recent overlapping period)
    min_length = min(len(ticker_returns), len(benchmark_returns))
    ticker_returns_aligned = ticker_returns[-min_length:]
    benchmark_returns_aligned = benchmark_returns[-min_length:]
    
    # Calculate beta via linear regression: y = alpha + beta * x + epsilon
    # Where y = ticker returns, x = benchmark returns
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        benchmark_returns_aligned, ticker_returns_aligned
    )
    
    LOGGER.debug(f"Beta for {ticker} vs {benchmark}: {slope:.3f} (R²={r_value**2:.3f}, p={p_value:.3f})")
    
    return float(slope)


def calculate_betas_batch(
    database_path: database.Path,
    ticker_list: List[str],
    benchmark: str = "SPY",
    lookback_days: int = 252,
) -> Dict[str, float]:
    """
    Calculate betas for multiple tickers in batch.
    
    Returns dict of ticker -> beta.
    Missing/invalid betas are not included in the result.
    """
    betas = {}
    for ticker in ticker_list:
        beta = calculate_beta(
            database_path,
            ticker,
            benchmark=benchmark,
            lookback_days=lookback_days,
        )
        if beta is not None:
            betas[ticker] = beta
    
    return betas


def calculate_expected_returns(
    database_path: database.Path,
    ticker_list: List[str],
    method: str = "historical",
    lookback_days: int = 252,
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """
    Calculate expected returns for tickers.
    
    Args:
        database_path: Path to database
        ticker_list: List of tickers
        method: "historical" (default) or "capm"
        lookback_days: Number of days for historical calculation
        risk_free_rate: Risk-free rate for CAPM (default 2% = 0.02)
    
    Returns:
        Dict of ticker -> expected return
    """
    if method == "historical":
        # Calculate mean historical return (annualized)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days * 2)
        
        returns_dict = {}
        for ticker in ticker_list:
            prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
            if len(prices) < 2:
                continue
            
            daily_returns = calculate_returns(prices)
            if len(daily_returns) > 0:
                mean_daily_return = np.mean(daily_returns)
                annualized_return = mean_daily_return * 252  # Annualize
                returns_dict[ticker] = annualized_return
        
        return returns_dict
    
    elif method == "capm":
        # CAPM: E[R] = Rf + Beta * (E[Rm] - Rf)
        # Assume market return is 8% (E[Rm] = 0.08)
        market_return = 0.08
        
        betas = calculate_betas_batch(database_path, ticker_list, lookback_days=lookback_days)
        
        returns_dict = {}
        for ticker in ticker_list:
            beta = betas.get(ticker, 1.0)  # Default beta = 1.0
            expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
            returns_dict[ticker] = expected_return
        
        return returns_dict
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'historical' or 'capm'")


