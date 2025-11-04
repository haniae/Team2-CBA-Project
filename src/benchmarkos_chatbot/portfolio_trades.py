"""
Order management and trade list generation for portfolios.

This module provides:
- Trade list generation from optimization results
- Trade file export (CSV, FIX, OMS format)
- Trade cost estimation
- Trade execution simulation
- What-if trade analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import io

import numpy as np
import pandas as pd

from . import database, portfolio
from .portfolio import OptimizationResult

LOGGER = logging.getLogger(__name__)


# ============================================================================
# Trade Data Structures
# ============================================================================

@dataclass
class Trade:
    """Represents a single trade."""
    
    ticker: str
    action: str  # "BUY", "SELL", "HOLD"
    quantity: float
    current_weight: float
    target_weight: float
    current_shares: float
    target_shares: float
    price: Optional[float] = None
    estimated_cost: Optional[float] = None
    trade_value: Optional[float] = None


@dataclass
class TradeList:
    """Represents a list of trades."""
    
    portfolio_id: str
    trades: List[Trade]
    total_trade_value: float
    total_estimated_cost: float
    generated_at: datetime
    optimization_id: Optional[str] = None


@dataclass
class TradeImpactResult:
    """Result of trade impact analysis."""
    
    portfolio_id: str
    proposed_trades: List[Trade]
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    impact_analysis: Dict[str, Any]
    policy_violations: List[str]
    risk_changes: Dict[str, float]


@dataclass
class PortfolioState:
    """Represents portfolio state after trade execution."""
    
    portfolio_id: str
    holdings: Dict[str, float]  # ticker -> weight
    metrics: Dict[str, float]
    timestamp: datetime


# ============================================================================
# Trade List Generation
# ============================================================================

def generate_trade_list(
    database_path: Path,
    portfolio_id: str,
    optimization_result: OptimizationResult,
    current_holdings: Optional[List[Dict[str, Any]]] = None,
    portfolio_value: Optional[float] = None
) -> TradeList:
    """
    Generate trade list from optimization results.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        optimization_result: Result from portfolio optimization
        current_holdings: Current portfolio holdings (if None, fetched from DB)
        portfolio_value: Total portfolio value (if None, calculated from holdings)
        
    Returns:
        TradeList with all required trades
    """
    # Get current holdings if not provided
    if current_holdings is None:
        current_holdings = portfolio.get_portfolio_holdings(database_path, portfolio_id)
    
    # Calculate portfolio value if not provided
    if portfolio_value is None:
        portfolio_value = sum(
            h.get('market_value', 0) or 0
            for h in current_holdings
        )
        if portfolio_value == 0:
            portfolio_value = 1_000_000.0  # Default $1M
    
    # Build current holdings dictionary
    current_weights = {}
    current_shares = {}
    current_prices = {}
    
    for holding in current_holdings:
        ticker = holding['ticker']
        weight = holding.get('weight', 0) or 0
        shares = holding.get('shares', 0) or 0
        market_value = holding.get('market_value', 0) or 0
        
        current_weights[ticker] = weight / 100.0  # Convert to decimal
        current_shares[ticker] = shares
        
        if shares > 0:
            current_prices[ticker] = market_value / shares
        else:
            # Try to get current price from database
            try:
                from .database import fetch_latest_price
                price_data = fetch_latest_price(database_path, ticker)
                if price_data:
                    current_prices[ticker] = price_data[1]
                else:
                    current_prices[ticker] = 100.0  # Default price
            except Exception:
                current_prices[ticker] = 100.0
    
    # Generate trades
    trades = []
    all_tickers = set(list(current_weights.keys()) + list(optimization_result.optimized_weights.keys()))
    
    for ticker in all_tickers:
        current_weight = current_weights.get(ticker, 0.0)
        target_weight = optimization_result.optimized_weights.get(ticker, 0.0)
        
        # Skip if no change
        if abs(current_weight - target_weight) < 0.001:  # 0.1% threshold
            continue
        
        # Determine action
        if target_weight > current_weight:
            action = "BUY"
        elif target_weight < current_weight:
            action = "SELL"
        else:
            action = "HOLD"
        
        # Calculate target shares
        target_value = target_weight * portfolio_value
        current_price = current_prices.get(ticker, 100.0)
        target_shares = target_value / current_price if current_price > 0 else 0
        
        # Calculate quantity change
        current_shares_ticker = current_shares.get(ticker, 0.0)
        quantity = target_shares - current_shares_ticker
        
        # Estimate trade cost
        trade_value = abs(quantity * current_price)
        estimated_cost = estimate_single_trade_cost(trade_value, action)
        
        trades.append(Trade(
            ticker=ticker,
            action=action,
            quantity=abs(quantity),
            current_weight=current_weight,
            target_weight=target_weight,
            current_shares=current_shares_ticker,
            target_shares=target_shares,
            price=current_price,
            estimated_cost=estimated_cost,
            trade_value=trade_value
        ))
    
    # Sort trades by trade value (largest first)
    trades.sort(key=lambda t: t.trade_value or 0, reverse=True)
    
    # Calculate totals
    total_trade_value = sum(t.trade_value or 0 for t in trades)
    total_estimated_cost = sum(t.estimated_cost or 0 for t in trades)
    
    return TradeList(
        portfolio_id=portfolio_id,
        trades=trades,
        total_trade_value=total_trade_value,
        total_estimated_cost=total_estimated_cost,
        generated_at=datetime.now(timezone.utc),
        optimization_id=None
    )


def export_trade_list(
    trade_list: TradeList,
    format: str = "csv"
) -> bytes:
    """
    Export trade list to specified format.
    
    Args:
        trade_list: TradeList to export
        format: Export format ("csv", "fix", "json")
        
    Returns:
        Bytes of exported trade list
    """
    if format.lower() == "csv":
        return _export_trade_list_csv(trade_list)
    elif format.lower() == "fix":
        return _export_trade_list_fix(trade_list)
    elif format.lower() == "json":
        return _export_trade_list_json(trade_list)
    else:
        raise ValueError(f"Unsupported export format: {format}")


def _export_trade_list_csv(trade_list: TradeList) -> bytes:
    """Export trade list as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Ticker", "Action", "Quantity", "Current Weight (%)",
        "Target Weight (%)", "Current Shares", "Target Shares",
        "Price", "Trade Value", "Estimated Cost"
    ])
    
    # Trades
    for trade in trade_list.trades:
        writer.writerow([
            trade.ticker,
            trade.action,
            f"{trade.quantity:.2f}",
            f"{trade.current_weight * 100:.2f}",
            f"{trade.target_weight * 100:.2f}",
            f"{trade.current_shares:.2f}",
            f"{trade.target_shares:.2f}",
            f"{trade.price:.2f}" if trade.price else "",
            f"{trade.trade_value:.2f}" if trade.trade_value else "",
            f"{trade.estimated_cost:.2f}" if trade.estimated_cost else ""
        ])
    
    # Summary
    writer.writerow([])
    writer.writerow(["Total Trade Value", f"{trade_list.total_trade_value:.2f}"])
    writer.writerow(["Total Estimated Cost", f"{trade_list.total_estimated_cost:.2f}"])
    
    return output.getvalue().encode('utf-8')


def _export_trade_list_fix(trade_list: TradeList) -> bytes:
    """Export trade list as FIX message format (simplified)."""
    # FIX format: Tag=Value|Tag=Value|...
    lines = []
    
    for i, trade in enumerate(trade_list.trades, start=1):
        # FIX message structure (simplified)
        fix_msg = (
            f"35=D|"  # Message type: New Order Single
            f"11={trade_list.portfolio_id}_{i}|"  # ClOrdID
            f"55={trade.ticker}|"  # Symbol
            f"54={1 if trade.action == 'BUY' else 2}|"  # Side (1=Buy, 2=Sell)
            f"38={trade.quantity:.2f}|"  # OrderQty
            f"44={trade.price:.2f}|"  # Price
            f"59=0|"  # TimeInForce (0=Day)
        )
        lines.append(fix_msg)
    
    return "\n".join(lines).encode('utf-8')


def _export_trade_list_json(trade_list: TradeList) -> bytes:
    """Export trade list as JSON."""
    import json
    
    data = {
        "portfolio_id": trade_list.portfolio_id,
        "generated_at": trade_list.generated_at.isoformat(),
        "total_trade_value": trade_list.total_trade_value,
        "total_estimated_cost": trade_list.total_estimated_cost,
        "trades": [
            {
                "ticker": trade.ticker,
                "action": trade.action,
                "quantity": trade.quantity,
                "current_weight": trade.current_weight,
                "target_weight": trade.target_weight,
                "current_shares": trade.current_shares,
                "target_shares": trade.target_shares,
                "price": trade.price,
                "trade_value": trade.trade_value,
                "estimated_cost": trade.estimated_cost
            }
            for trade in trade_list.trades
        ]
    }
    
    return json.dumps(data, indent=2).encode('utf-8')


# ============================================================================
# Trade Cost Estimation
# ============================================================================

def estimate_trade_costs(
    trades: List[Trade],
    cost_model: str = "linear"
) -> float:
    """
    Estimate execution costs for trades.
    
    Args:
        trades: List of trades
        cost_model: Cost model ("linear", "quadratic", "fixed")
        
    Returns:
        Total estimated cost
    """
    total_cost = 0.0
    
    for trade in trades:
        if trade.trade_value:
            cost = estimate_single_trade_cost(trade.trade_value, trade.action, cost_model)
            total_cost += cost
    
    return total_cost


def estimate_single_trade_cost(
    trade_value: float,
    action: str,
    cost_model: str = "linear"
) -> float:
    """
    Estimate cost for a single trade.
    
    Args:
        trade_value: Dollar value of trade
        action: "BUY" or "SELL"
        cost_model: Cost model ("linear", "quadratic", "fixed")
        
    Returns:
        Estimated cost in dollars
    """
    if cost_model == "linear":
        # Linear cost model: cost = 0.1% of trade value
        cost = trade_value * 0.001
    elif cost_model == "quadratic":
        # Quadratic cost model: cost increases with trade size
        cost = trade_value * 0.0005 + (trade_value / 1000000) ** 2 * 100
    elif cost_model == "fixed":
        # Fixed cost per trade: $10 per trade
        cost = 10.0
    else:
        # Default: linear
        cost = trade_value * 0.001
    
    # Add spread cost (bid-ask spread)
    spread_cost = trade_value * 0.0002  # 2 bps spread
    total_cost = cost + spread_cost
    
    return total_cost


# ============================================================================
# What-If Trade Analysis
# ============================================================================

def analyze_trade_impact(
    database_path: Path,
    portfolio_id: str,
    proposed_trades: List[Trade],
    portfolio_value: Optional[float] = None
) -> TradeImpactResult:
    """
    Analyze impact of proposed trades on portfolio.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        proposed_trades: List of proposed trades
        portfolio_value: Total portfolio value
        
    Returns:
        TradeImpactResult with before/after metrics
    """
    # Get current holdings
    current_holdings = portfolio.get_portfolio_holdings(database_path, portfolio_id)
    
    # Calculate portfolio value if not provided
    if portfolio_value is None:
        portfolio_value = sum(
            h.get('market_value', 0) or 0
            for h in current_holdings
        )
        if portfolio_value == 0:
            portfolio_value = 1_000_000.0
    
    # Build current holdings dictionary
    current_weights = {}
    for holding in current_holdings:
        ticker = holding['ticker']
        weight = holding.get('weight', 0) or 0
        current_weights[ticker] = weight / 100.0
    
    # Calculate "after" weights from trades
    after_weights = current_weights.copy()
    
    for trade in proposed_trades:
        if trade.action == "BUY":
            after_weights[trade.ticker] = trade.target_weight
        elif trade.action == "SELL":
            after_weights[trade.ticker] = trade.target_weight
        # Update weights for all holdings (normalize)
        total_weight = sum(after_weights.values())
        if total_weight > 0:
            after_weights = {k: v / total_weight for k, v in after_weights.items()}
    
    # Calculate before metrics
    ticker_list = list(current_weights.keys())
    expected_returns = portfolio.calculate_expected_returns(
        database_path,
        ticker_list,
        method="historical"
    )
    
    covariance_matrix, ticker_list_ordered = portfolio.calculate_covariance_matrix(
        database_path,
        ticker_list
    )
    
    before_return = portfolio.calculate_portfolio_return(current_weights, expected_returns)
    
    # Calculate portfolio variance manually
    weights_array = np.array([current_weights.get(ticker, 0.0) for ticker in ticker_list_ordered])
    before_variance = float(weights_array @ covariance_matrix @ weights_array)
    before_volatility = np.sqrt(before_variance) if before_variance > 0 else 0.0
    before_sharpe = (before_return - 0.02) / before_volatility if before_volatility > 0 else 0.0
    
    # Calculate after metrics
    after_return = portfolio.calculate_portfolio_return(after_weights, expected_returns)
    
    # Calculate portfolio variance manually
    weights_array_after = np.array([after_weights.get(ticker, 0.0) for ticker in ticker_list_ordered])
    after_variance = float(weights_array_after @ covariance_matrix @ weights_array_after)
    after_volatility = np.sqrt(after_variance) if after_variance > 0 else 0.0
    after_sharpe = (after_return - 0.02) / after_volatility if after_volatility > 0 else 0.0
    
    # Check policy compliance
    policy_violations = []
    try:
        constraints = database.fetch_policy_constraints(database_path, portfolio_id, active_only=True)
        
        for constraint in constraints:
            if constraint.constraint_type == "allocation_cap":
                if constraint.dimension == "*":
                    # Check max weight for all holdings
                    max_weight = max(after_weights.values())
                    if max_weight > constraint.max_value:
                        policy_violations.append(
                            f"Maximum weight constraint violated: {max_weight:.2%} > {constraint.max_value:.2%}"
                        )
                else:
                    if constraint.dimension in after_weights:
                        if after_weights[constraint.dimension] > constraint.max_value:
                            policy_violations.append(
                                f"{constraint.dimension} weight exceeds limit: {after_weights[constraint.dimension]:.2%} > {constraint.max_value:.2%}"
                            )
    except Exception as e:
        LOGGER.debug(f"Could not check policy compliance: {e}")
    
    # Calculate risk changes
    risk_changes = {
        "return_change": after_return - before_return,
        "volatility_change": after_volatility - before_volatility,
        "sharpe_change": after_sharpe - before_sharpe,
        "variance_change": after_variance - before_variance
    }
    
    # Impact analysis
    impact_analysis = {
        "expected_portfolio_value_change": (after_return - before_return) * portfolio_value,
        "risk_adjustment": after_volatility - before_volatility,
        "cost_impact": sum(t.estimated_cost or 0 for t in proposed_trades),
        "net_benefit": (after_return - before_return) * portfolio_value - sum(t.estimated_cost or 0 for t in proposed_trades)
    }
    
    return TradeImpactResult(
        portfolio_id=portfolio_id,
        proposed_trades=proposed_trades,
        before_metrics={
            "expected_return": before_return,
            "volatility": before_volatility,
            "sharpe_ratio": before_sharpe,
            "variance": before_variance
        },
        after_metrics={
            "expected_return": after_return,
            "volatility": after_volatility,
            "sharpe_ratio": after_sharpe,
            "variance": after_variance
        },
        impact_analysis=impact_analysis,
        policy_violations=policy_violations,
        risk_changes=risk_changes
    )


def simulate_trade_execution(
    database_path: Path,
    portfolio_id: str,
    trades: List[Trade],
    portfolio_value: Optional[float] = None
) -> PortfolioState:
    """
    Simulate portfolio state after trade execution.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        trades: List of trades to execute
        portfolio_value: Total portfolio value
        
    Returns:
        PortfolioState after trade execution
    """
    # Get current holdings
    current_holdings = portfolio.get_portfolio_holdings(database_path, portfolio_id)
    
    # Calculate portfolio value if not provided
    if portfolio_value is None:
        portfolio_value = sum(
            h.get('market_value', 0) or 0
            for h in current_holdings
        )
        if portfolio_value == 0:
            portfolio_value = 1_000_000.0
    
    # Build current weights
    current_weights = {}
    for holding in current_holdings:
        ticker = holding['ticker']
        weight = holding.get('weight', 0) or 0
        current_weights[ticker] = weight / 100.0
    
    # Apply trades
    after_weights = current_weights.copy()
    
    for trade in trades:
        if trade.action == "BUY" or trade.action == "SELL":
            after_weights[trade.ticker] = trade.target_weight
    
    # Normalize weights
    total_weight = sum(after_weights.values())
    if total_weight > 0:
        after_weights = {k: v / total_weight for k, v in after_weights.items()}
    
    # Calculate metrics
    ticker_list = list(after_weights.keys())
    expected_returns = portfolio.calculate_expected_returns(
        database_path,
        ticker_list,
        method="historical"
    )
    
    covariance_matrix, ticker_list_ordered = portfolio.calculate_covariance_matrix(
        database_path,
        ticker_list
    )
    
    expected_return = portfolio.calculate_portfolio_return(after_weights, expected_returns)
    
    # Calculate portfolio variance manually
    weights_array = np.array([after_weights.get(ticker, 0.0) for ticker in ticker_list_ordered])
    portfolio_variance = float(weights_array @ covariance_matrix @ weights_array)
    portfolio_volatility = np.sqrt(portfolio_variance) if portfolio_variance > 0 else 0.0
    sharpe_ratio = (expected_return - 0.02) / portfolio_volatility if portfolio_volatility > 0 else 0.0
    
    metrics = {
        "expected_return": expected_return,
        "volatility": portfolio_volatility,
        "sharpe_ratio": sharpe_ratio,
        "variance": portfolio_variance
    }
    
    return PortfolioState(
        portfolio_id=portfolio_id,
        holdings=after_weights,
        metrics=metrics,
        timestamp=datetime.now(timezone.utc)
    )


