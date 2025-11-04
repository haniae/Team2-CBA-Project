"""
Advanced risk metrics for portfolio analysis.

This module provides:
- Conditional Value at Risk (CVaR) calculation
- VaR vs CVaR comparison
- Portfolio-level and position-level CVaR
- CVaR-constrained optimization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import cvxpy as cp

from . import database, portfolio

LOGGER = logging.getLogger(__name__)


# ============================================================================
# CVaR (Conditional Value at Risk) Implementation
# ============================================================================

@dataclass
class CVaRResult:
    """Result of CVaR calculation."""
    
    cvar: float
    var: float
    confidence_level: float
    portfolio_value: float
    expected_loss: float
    position_cvar: Dict[str, float]


@dataclass
class CVaROptimizationResult:
    """Result of CVaR-constrained optimization."""
    
    holdings: Dict[str, float]
    expected_return: float
    portfolio_variance: float
    sharpe_ratio: float
    cvar: float
    var: float
    optimization_status: str


def calculate_cvar(
    database_path: Path,
    portfolio_id: str,
    confidence_level: float = 0.95,
    lookback_days: int = 252
) -> CVaRResult:
    """
    Calculate Conditional Value at Risk (CVaR) for portfolio.
    
    CVaR (Expected Shortfall) is the expected loss given that the loss
    exceeds the VaR threshold. It provides a more conservative risk measure
    than VaR, especially for tail risk.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        confidence_level: Confidence level (default: 0.95 = 95%)
        lookback_days: Number of days to look back for returns
        
    Returns:
        CVaRResult with CVaR, VaR, and position-level CVaR
    """
    # Get portfolio returns
    portfolio_returns = portfolio.get_portfolio_returns(
        database_path,
        portfolio_id,
        lookback_days=lookback_days
    )
    
    if len(portfolio_returns) < 20:
        raise ValueError("Insufficient historical data for CVaR calculation")
    
    # Calculate VaR (Value at Risk)
    var = float(np.percentile(portfolio_returns, (1 - confidence_level) * 100))
    
    # Calculate CVaR (Expected Shortfall)
    # CVaR is the mean of returns below the VaR threshold
    tail_returns = portfolio_returns[portfolio_returns <= var]
    if len(tail_returns) == 0:
        # If no returns below VaR, CVaR equals VaR
        cvar = var
    else:
        cvar = float(tail_returns.mean())
    
    # Get portfolio holdings for position-level CVaR
    holdings = portfolio.get_portfolio_holdings(database_path, portfolio_id)
    ticker_list = [h['ticker'] for h in holdings]
    weights = {h['ticker']: h['weight'] / 100.0 if h['weight'] else 0.0 for h in holdings}
    
    # Calculate position-level CVaR
    position_cvar = {}
    for ticker in ticker_list:
        if ticker in weights and weights[ticker] > 0:
            # Get individual asset returns
            ticker_returns = portfolio.get_historical_returns(
                database_path,
                [ticker],
                periods=lookback_days
            )
            
            if len(ticker_returns) > 0 and ticker in ticker_returns.columns:
                asset_returns = ticker_returns[ticker].dropna()
                if len(asset_returns) >= 20:
                    asset_var = float(np.percentile(asset_returns, (1 - confidence_level) * 100))
                    asset_tail = asset_returns[asset_returns <= asset_var]
                    asset_cvar = float(asset_tail.mean()) if len(asset_tail) > 0 else asset_var
                    position_cvar[ticker] = asset_cvar * weights[ticker]  # Contribution to portfolio CVaR
    
    # Calculate expected loss (negative of CVaR)
    expected_loss = -cvar
    
    # Get portfolio value (approximate)
    portfolio_value = sum(h.get('market_value', 0) or 0 for h in holdings)
    if portfolio_value == 0:
        # Fallback: assume $1M portfolio
        portfolio_value = 1_000_000.0
    
    return CVaRResult(
        cvar=cvar,
        var=var,
        confidence_level=confidence_level,
        portfolio_value=portfolio_value,
        expected_loss=expected_loss,
        position_cvar=position_cvar
    )


def optimize_portfolio_cvar_constrained(
    database_path: Path,
    portfolio_id: str,
    max_cvar: float,
    confidence_level: float = 0.95,
    objective: str = "sharpe",
    constraints: Optional[List[portfolio.PolicyConstraint]] = None
) -> CVaROptimizationResult:
    """
    Optimize portfolio with CVaR constraint.
    
    This is a more complex optimization problem that requires
    approximating CVaR using linear programming or scenario-based methods.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        max_cvar: Maximum allowed CVaR (as a decimal, e.g., -0.05 for -5%)
        confidence_level: Confidence level for CVaR
        objective: Optimization objective ("sharpe", "return", "minimize_variance")
        constraints: Additional policy constraints
        
    Returns:
        CVaROptimizationResult with optimized portfolio
    """
    # Get current holdings
    current_holdings = portfolio.get_portfolio_holdings(database_path, portfolio_id)
    ticker_list = [h['ticker'] for h in current_holdings]
    
    if len(ticker_list) < 2:
        raise ValueError("CVaR optimization requires at least 2 holdings")
    
    # Calculate expected returns and covariance
    expected_returns = portfolio.calculate_expected_returns(
        database_path,
        ticker_list,
        method="historical"
    )
    
    covariance_matrix, ticker_list_ordered = portfolio.calculate_covariance_matrix(
        database_path,
        ticker_list
    )
    
    # Get historical returns for scenario-based CVaR approximation
    returns_df = portfolio.get_historical_returns(
        database_path,
        ticker_list_ordered,
        periods=252
    )
    
    if len(returns_df) < 50:
        raise ValueError("Insufficient historical data for CVaR optimization")
    
    # Number of scenarios (use historical data)
    num_scenarios = len(returns_df)
    scenario_returns = returns_df.values  # Shape: (num_scenarios, num_assets)
    
    # Define optimization variables
    n = len(ticker_list_ordered)
    weights = cp.Variable(n)
    
    # Portfolio return for each scenario
    portfolio_returns_scenarios = scenario_returns @ weights
    
    # Calculate VaR (approximate using scenario returns)
    alpha = 1 - confidence_level
    var_threshold = cp.Variable()
    
    # CVaR constraint: E[loss | loss >= VaR] <= max_cvar
    # This is approximated using scenario-based approach
    # CVaR = (1/alpha) * E[max(0, VaR - portfolio_return)]
    cvar_expr = var_threshold - (1 / alpha) * cp.mean(
        cp.maximum(0, var_threshold - portfolio_returns_scenarios)
    )
    
    # Expected portfolio return
    portfolio_return = expected_returns @ weights
    
    # Portfolio variance
    portfolio_var = cp.quad_form(weights, covariance_matrix)
    
    # Objective
    if objective == "sharpe":
        # Maximize Sharpe ratio (approximate, since CVaR constraint makes it complex)
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        objective_func = cp.Maximize(
            (portfolio_return - risk_free_rate) / cp.sqrt(portfolio_var)
        )
    elif objective == "return":
        objective_func = cp.Maximize(portfolio_return)
    elif objective == "minimize_variance":
        objective_func = cp.Minimize(portfolio_var)
    else:
        raise ValueError(f"Unknown objective: {objective}")
    
    # Constraints
    constraint_list = [
        cp.sum(weights) == 1.0,
        weights >= 0.0,  # Long-only
        cvar_expr >= max_cvar  # CVaR constraint (max_cvar is negative, so >= means less negative)
    ]
    
    # Add policy constraints if provided
    if constraints:
        for constraint in constraints:
            if constraint.constraint_type == "allocation_cap":
                if constraint.ticker == "*":
                    # Max weight for all holdings
                    constraint_list.append(weights <= constraint.max_value)
                else:
                    # Max weight for specific ticker
                    if constraint.ticker in ticker_list_ordered:
                        idx = ticker_list_ordered.index(constraint.ticker)
                        constraint_list.append(weights[idx] <= constraint.max_value)
            elif constraint.constraint_type == "allocation_floor":
                if constraint.ticker in ticker_list_ordered:
                    idx = ticker_list_ordered.index(constraint.ticker)
                    constraint_list.append(weights[idx] >= constraint.min_value)
    
    # Solve
    problem = cp.Problem(objective_func, constraint_list)
    
    # Try multiple solvers
    solvers = [cp.OSQP, cp.ECOS, cp.SCS]
    solved = False
    
    for solver in solvers:
        try:
            problem.solve(solver=solver)
            if problem.status == 'optimal' or problem.status == 'optimal_inaccurate':
                solved = True
                break
        except Exception as e:
            LOGGER.debug(f"Solver {solver} failed: {e}")
            continue
    
    if not solved or problem.status not in ['optimal', 'optimal_inaccurate']:
        raise portfolio.OptimizationFailedError(
            f"CVaR-constrained optimization failed: {problem.status}"
        )
    
    # Format results
    optimized_weights = {
        ticker: float(weight)
        for ticker, weight in zip(ticker_list_ordered, weights.value)
    }
    
    # Normalize weights
    total_weight = sum(optimized_weights.values())
    if total_weight > 0:
        optimized_weights = {k: v / total_weight for k, v in optimized_weights.items()}
    
    # Calculate metrics
    expected_return = portfolio.calculate_portfolio_return(
        optimized_weights,
        expected_returns
    )
    portfolio_variance = float(portfolio_var.value)
    
    # Calculate realized CVaR
    optimized_returns = portfolio_returns_scenarios.value
    var_value = float(np.percentile(optimized_returns, (1 - confidence_level) * 100))
    tail_returns = optimized_returns[optimized_returns <= var_value]
    cvar_value = float(tail_returns.mean()) if len(tail_returns) > 0 else var_value
    
    # Sharpe ratio
    sharpe_ratio = (expected_return - 0.02) / np.sqrt(portfolio_variance) if portfolio_variance > 0 else 0.0
    
    return CVaROptimizationResult(
        holdings=optimized_weights,
        expected_return=expected_return,
        portfolio_variance=portfolio_variance,
        sharpe_ratio=sharpe_ratio,
        cvar=cvar_value,
        var=var_value,
        optimization_status=problem.status
    )


