"""Portfolio optimization engine with policy-aware constraints."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Optional imports for optimization
try:
    import cvxpy as cp  # type: ignore
except ImportError:
    cp = None  # type: ignore

try:
    import scipy.optimize as sco  # type: ignore
except ImportError:
    sco = None  # type: ignore

from . import database

LOGGER = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    optimized_weights: Dict[str, float]
    proposed_trades: List[Dict[str, Any]]
    objective_value: Optional[float]
    iterations: int
    status: str
    policy_flags: List[str]
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]


@dataclass
class PolicyConstraint:
    """Portfolio policy constraint definition."""

    constraint_type: str  # allocation_cap, sector_limit, tracking_error, etc.
    dimension: Optional[str]  # ticker or sector name
    min_value: Optional[float]
    max_value: Optional[float]


def optimize_portfolio_sharpe(
    current_holdings: Dict[str, float],  # ticker -> weight
    expected_returns: Dict[str, float],
    covariance_matrix: np.ndarray,
    ticker_list: List[str],
    constraints: List[PolicyConstraint],
    turnover_limit: Optional[float] = None,
    objective: str = "maximize_sharpe",
) -> OptimizationResult:
    """
    Optimize portfolio to maximize Sharpe ratio subject to policy constraints.

    Args:
        current_holdings: Current portfolio weights
        expected_returns: Expected returns for each ticker
        covariance_matrix: Covariance matrix (symmetric, positive semi-definite)
        ticker_list: Ordered list of tickers matching covariance matrix
        constraints: List of policy constraints to enforce
        turnover_limit: Maximum portfolio turnover (0-1)
        objective: Optimization objective (maximize_sharpe, minimize_tracking_error, maximize_return)

    Returns:
        OptimizationResult with optimized weights and trades
    """
    n = len(ticker_list)
    if n == 0:
        raise ValueError("Empty ticker list")

    # Initialize optimization variables
    weights = cp.Variable(n)

    # Convert to numpy arrays
    returns_vec = np.array([expected_returns.get(ticker, 0.0) for ticker in ticker_list])
    current_weights_vec = np.array([current_holdings.get(ticker, 0.0) for ticker in ticker_list])

    # Portfolio expected return
    portfolio_return = returns_vec @ weights

    # Portfolio variance
    portfolio_var = cp.quad_form(weights, covariance_matrix)

    # Constraints list
    optimization_constraints = []

    # Constraint: weights sum to 1.0
    optimization_constraints.append(cp.sum(weights) == 1.0)

    # Constraint: no shorting
    optimization_constraints.append(weights >= 0.0)

    # Apply policy constraints
    policy_flags = []
    for constraint in constraints:
        if constraint.constraint_type == "allocation_cap":
            if constraint.dimension == "*":  # Universal cap on all positions
                if constraint.max_value is not None:
                    optimization_constraints.append(weights <= constraint.max_value)
                    policy_flags.append(f"Allocation cap: max {constraint.max_value*100:.1f}% per position")
            else:  # Specific ticker cap
                if constraint.dimension in ticker_list:
                    idx = ticker_list.index(constraint.dimension)
                    if constraint.max_value is not None:
                        optimization_constraints.append(weights[idx] <= constraint.max_value)

        elif constraint.constraint_type == "sector_limit":
            # For sector limits, we'd need sector mapping - simplified here
            if constraint.min_value is not None or constraint.max_value is not None:
                LOGGER.warning(f"Sector limit constraints require sector mapping (not implemented here)")

        elif constraint.constraint_type == "tracking_error":
            # Tracking error constraint would need benchmark weights
            LOGGER.warning(f"Tracking error constraint requires benchmark data")

    # Turnover limit
    if turnover_limit is not None:
        turnover = cp.sum(cp.abs(weights - current_weights_vec))
        optimization_constraints.append(turnover <= turnover_limit)
        policy_flags.append(f"Turnover limit: max {turnover_limit*100:.0f}%")

    # Objective function
    if objective == "maximize_sharpe":
        # Maximize Sharpe ratio = (return - risk_free_rate) / sqrt(variance)
        risk_free_rate = 0.0  # Can be parameterized
        objective_fn = cp.Maximize((portfolio_return - risk_free_rate) / cp.sqrt(portfolio_var))
        policy_flags.append("Objective: Maximize Sharpe ratio")
    elif objective == "minimize_tracking_error":
        # Would need benchmark weights
        objective_fn = cp.Minimize(portfolio_var)
        policy_flags.append("Objective: Minimize risk")
    elif objective == "maximize_return":
        objective_fn = cp.Maximize(portfolio_return)
        policy_flags.append("Objective: Maximize return")
    else:
        raise ValueError(f"Unknown objective: {objective}")

    # Solve optimization problem
    problem = cp.Problem(objective_fn, optimization_constraints)

    try:
        problem.solve(solver=cp.OSQP, verbose=False)
        status = problem.status
        iterations = 0  # OSQP doesn't expose iteration count directly

        if status not in ["optimal", "optimal_inaccurate"]:
            LOGGER.warning(f"Optimization status: {status}")
            return OptimizationResult(
                optimized_weights={},
                proposed_trades=[],
                objective_value=None,
                iterations=0,
                status=status,
                policy_flags=policy_flags,
                metrics_before={},
                metrics_after={},
            )

        # Extract optimized weights
        optimized_weights_dict = {ticker: float(w) for ticker, w in zip(ticker_list, weights.value) if w > 1e-6}
        optimized_weights_vec = weights.value if weights.value is not None else np.zeros(n)

        # Calculate metrics before/after
        metrics_before = {
            "expected_return": float(returns_vec @ current_weights_vec),
            "portfolio_variance": float(current_weights_vec @ covariance_matrix @ current_weights_vec),
            "num_positions": sum(1 for w in current_weights_vec if w > 1e-6),
        }

        metrics_after = {
            "expected_return": float(returns_vec @ optimized_weights_vec),
            "portfolio_variance": float(optimized_weights_vec @ covariance_matrix @ optimized_weights_vec),
            "num_positions": sum(1 for w in optimized_weights_vec if w > 1e-6),
        }

        # Calculate proposed trades
        proposed_trades = []
        for ticker in ticker_list:
            idx = ticker_list.index(ticker)
            current_wt = float(current_weights_vec[idx])
            new_wt = float(optimized_weights_vec[idx])

            if abs(new_wt - current_wt) > 1e-6:
                action = "buy" if new_wt > current_wt else "sell"
                proposed_trades.append(
                    {
                        "ticker": ticker,
                        "action": action,
                        "from_weight": current_wt,
                        "to_weight": new_wt,
                        "shares": None,  # Would need portfolio value to calculate
                    }
                )

        result = OptimizationResult(
            optimized_weights=optimized_weights_dict,
            proposed_trades=proposed_trades,
            objective_value=float(objective_fn.value) if objective_fn.value is not None else None,
            iterations=iterations,
            status=status,
            policy_flags=policy_flags,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
        )

        LOGGER.info(f"Optimization completed: {len(proposed_trades)} trades, status={status}")
        return result

    except Exception as e:
        LOGGER.error(f"Optimization failed: {e}")
        return OptimizationResult(
            optimized_weights={},
            proposed_trades=[],
            objective_value=None,
            iterations=0,
            status="error",
            policy_flags=policy_flags,
            metrics_before={},
            metrics_after={},
        )


def optimize_portfolio_simple(
    current_holdings: Dict[str, float],
    expected_returns: Dict[str, float],
    risk_free_rate: float = 0.02,
    max_position_size: float = 0.12,
    turnover_limit: Optional[float] = None,
) -> Dict[str, float]:
    """
    Simplified optimization using scipy (no external solver required).

    For demonstration purposes when cvxpy is not available or desired.
    """
    n = len(current_holdings)
    if n == 0:
        return {}

    ticker_list = list(current_holdings.keys())
    current_weights_vec = np.array([current_holdings[ticker] for ticker in ticker_list])
    returns_vec = np.array([expected_returns.get(ticker, risk_free_rate) for ticker in ticker_list])

    # Objective: maximize mean-variance utility
    def objective(weights):
        portfolio_return = np.dot(returns_vec, weights)
        # Simple risk measure (could use actual variance)
        portfolio_risk = np.std(weights)
        return -(portfolio_return - 0.5 * portfolio_risk)  # Maximize utility

    # Constraints
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]  # Weights sum to 1

    # Bounds: no shorting, max position size
    bounds = [(0.0, max_position_size) for _ in range(n)]

    # Initial guess: current weights
    initial_guess = current_weights_vec.copy()

    try:
        result = sco.minimize(
            objective, initial_guess, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000}
        )

        if result.success:
            optimized_weights = {ticker: float(w) for ticker, w in zip(ticker_list, result.x) if w > 1e-6}
            LOGGER.info(f"Simple optimization completed: {len(optimized_weights)} positions")
            return optimized_weights
        else:
            LOGGER.warning(f"Simple optimization failed: {result.message}")
            return {}

    except Exception as e:
        LOGGER.error(f"Simple optimization error: {e}")
        return {}


def save_optimization_trades_to_database(
    database_path: database.Path,
    portfolio_id: str,
    optimization_result: OptimizationResult,
    trade_date: Optional[datetime] = None,
) -> None:
    """
    Save proposed optimization trades to database as transaction records.

    Marks trades as "proposed" (not executed) until user approves.
    """
    if trade_date is None:
        trade_date = datetime.now(timezone.utc)

    for trade in optimization_result.proposed_trades:
        transaction_id = str(uuid.uuid4())
        transaction = database.PortfolioTransactionRecord(
            transaction_id=transaction_id,
            portfolio_id=portfolio_id,
            ticker=trade["ticker"],
            trade_date=trade_date,
            action=f"{trade['action']}_proposed",
            shares=trade.get("shares"),
            price=None,
            commission=None,
            notes=f"Optimization result - {optimization_result.status}",
        )
        database.insert_portfolio_transaction(database_path, transaction)

    LOGGER.info(f"Saved {len(optimization_result.proposed_trades)} proposed trades for portfolio {portfolio_id}")


