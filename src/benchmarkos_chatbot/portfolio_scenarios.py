"""Portfolio scenario analysis and stress testing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

LOGGER = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of portfolio scenario analysis."""

    portfolio_value_change: float  # absolute change
    portfolio_return: float  # percentage return
    pnl_attribution: Dict[str, float]  # component -> contribution
    top_gainers: List[Dict[str, Any]]
    top_losers: List[Dict[str, Any]]
    risk_metrics: Dict[str, float]  # VaR, CVaR, max drawdown, etc.


def run_equity_drawdown_scenario(
    holdings: Dict[str, float],  # ticker -> weight
    betas: Dict[str, float],
    drawdown_pct: float,  # e.g., -0.20 for 20% market decline
) -> ScenarioResult:
    """
    Run equity drawdown scenario.

    Applies beta-adjusted returns to portfolio holdings.
    """
    if drawdown_pct >= 0:
        LOGGER.warning("Drawdown should be negative (e.g., -0.20 for 20% decline)")

    ticker_returns = {}
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        beta = betas.get(ticker, 1.0)  # Default beta = 1.0
        ticker_return = drawdown_pct * beta  # Beta-adjusted return
        ticker_returns[ticker] = ticker_return
        ticker_pnl[ticker] = weight * ticker_return

    # Calculate portfolio impact
    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return  # Weighted by portfolio value

    # Attribution by rate/equity component
    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    # Top gainers/losers
    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    # Risk metrics
    risk_metrics = {
        "portfolio_drawdown": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    LOGGER.info(f"Equity drawdown scenario: portfolio return={portfolio_return:.2%}")

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_sector_rotation_scenario(
    holdings: Dict[str, float],
    ticker_sectors: Dict[str, str],
    sector_shifts: Dict[str, float],  # sector -> return %
) -> ScenarioResult:
    """
    Run sector rotation scenario.

    Applies sector-specific return shocks to portfolio.
    """
    ticker_returns = {}
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        sector = ticker_sectors.get(ticker, "Unknown")
        sector_return = sector_shifts.get(sector, 0.0)
        ticker_returns[ticker] = sector_return
        ticker_pnl[ticker] = weight * sector_return

    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return

    # Attribution
    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    risk_metrics = {
        "portfolio_return": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    LOGGER.info(f"Sector rotation scenario: portfolio return={portfolio_return:.2%}")

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_custom_scenario(
    holdings: Dict[str, float],
    custom_returns: Dict[str, float],  # ticker -> return %
) -> ScenarioResult:
    """
    Run custom scenario with user-provided return assumptions.

    Returns scenario result with portfolio impact.
    """
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        return_pct = custom_returns.get(ticker, 0.0)
        ticker_pnl[ticker] = weight * return_pct

    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return

    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    risk_metrics = {
        "portfolio_return": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_multiple_scenarios(
    holdings: Dict[str, float],
    scenarios: Dict[str, Any],  # scenario_name -> parameters
    ticker_betas: Optional[Dict[str, float]] = None,
    ticker_sectors: Optional[Dict[str, str]] = None,
) -> Dict[str, ScenarioResult]:
    """
    Run multiple scenarios and compare results.

    Returns dict of scenario_name -> ScenarioResult.
    """
    results = {}

    for scenario_name, params in scenarios.items():
        scenario_type = params.get("type")
        parameters = params.get("parameters", {})

        if scenario_type == "equity_drawdown":
            betas = ticker_betas or {}
            drawdown = parameters.get("drawdown_pct", -0.20)
            results[scenario_name] = run_equity_drawdown_scenario(holdings, betas, drawdown)

        elif scenario_type == "sector_rotation":
            sectors = ticker_sectors or {}
            shifts = parameters.get("sector_shifts", {})
            results[scenario_name] = run_sector_rotation_scenario(holdings, sectors, shifts)

        elif scenario_type == "custom":
            custom_returns = parameters.get("returns", {})
            results[scenario_name] = run_custom_scenario(holdings, custom_returns)

        else:
            LOGGER.warning(f"Unknown scenario type: {scenario_type}")

    LOGGER.info(f"Ran {len(results)} scenarios")
    return results


def format_scenario_results(scenario_results: Dict[str, ScenarioResult]) -> str:
    """Format multiple scenario results as table."""
    lines = ["\nScenario Analysis Results", "=" * 70]
    lines.append(f"{'Scenario':30s} {'Portfolio Return':>15s} {'Value Impact':>15s}")
    lines.append("-" * 60)

    for name, result in scenario_results.items():
        lines.append(f"{name:30s} {result.portfolio_return:15.2%} {result.portfolio_value_change:15.2%}")

    return "\n".join(lines)


