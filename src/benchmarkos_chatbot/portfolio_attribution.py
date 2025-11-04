"""Performance attribution analysis using Brinson methodology."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

LOGGER = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Brinson attribution analysis result."""

    total_active_return: float
    allocation_effect: Dict[str, float]  # sector -> contribution
    selection_effect: Dict[str, float]  # sector -> contribution
    interaction_effect: Dict[str, float]  # sector -> contribution
    top_contributors: List[Dict[str, Any]]
    top_detractors: List[Dict[str, Any]]


def brinson_attribution(
    portfolio_weights: Dict[str, float],
    portfolio_returns: Dict[str, float],
    benchmark_weights: Dict[str, float],
    benchmark_returns: Dict[str, float],
    sectors: Dict[str, str],  # ticker -> sector
) -> AttributionResult:
    """
    Perform Brinson attribution analysis.

    Decomposes active return into:
    - Allocation effect: (portfolio_sector_wt - benchmark_sector_wt) × benchmark_sector_return
    - Selection effect: benchmark_sector_wt × (portfolio_return - benchmark_return)
    - Interaction effect: (portfolio_wt - benchmark_wt) × (portfolio_return - benchmark_return)

    Returns AttributionResult with breakdowns by sector.
    """
    # Calculate portfolio and benchmark returns
    portfolio_return = sum(portfolio_weights[ticker] * portfolio_returns.get(ticker, 0.0) for ticker in portfolio_weights)
    benchmark_return = sum(benchmark_weights[ticker] * benchmark_returns.get(ticker, 0.0) for ticker in benchmark_weights)

    total_active_return = portfolio_return - benchmark_return

    # Group by sector
    portfolio_sector_weights = defaultdict(float)
    portfolio_sector_returns = defaultdict(float)
    benchmark_sector_weights = defaultdict(float)
    benchmark_sector_returns = defaultdict(float)

    for ticker, sector in sectors.items():
        if ticker in portfolio_weights:
            weight = portfolio_weights[ticker]
            ret = portfolio_returns.get(ticker, 0.0)
            portfolio_sector_weights[sector] += weight
            portfolio_sector_returns[sector] += weight * ret

        if ticker in benchmark_weights:
            weight = benchmark_weights[ticker]
            ret = benchmark_returns.get(ticker, 0.0)
            benchmark_sector_weights[sector] += weight
            benchmark_sector_returns[sector] += weight * ret

    # Normalize sector returns (weighted average within sector)
    for sector in portfolio_sector_returns:
        if portfolio_sector_weights[sector] > 0:
            portfolio_sector_returns[sector] /= portfolio_sector_weights[sector]
    for sector in benchmark_sector_returns:
        if benchmark_sector_weights[sector] > 0:
            benchmark_sector_returns[sector] /= benchmark_sector_weights[sector]

    # Calculate attribution effects
    allocation_effect = {}
    selection_effect = {}
    interaction_effect = {}

    all_sectors = set(portfolio_sector_weights.keys()) | set(benchmark_sector_weights.keys())

    for sector in all_sectors:
        port_wt = portfolio_sector_weights.get(sector, 0.0)
        bmk_wt = benchmark_sector_weights.get(sector, 0.0)
        port_ret = portfolio_sector_returns.get(sector, 0.0)
        bmk_ret = benchmark_sector_returns.get(sector, 0.0)

        # Allocation effect
        allocation_effect[sector] = (port_wt - bmk_wt) * bmk_ret

        # Selection effect (security-level, not sector-level)
        selection_contribution = 0.0
        for ticker, ticker_sector in sectors.items():
            if ticker_sector == sector:
                port_wt_ticker = portfolio_weights.get(ticker, 0.0)
                bmk_wt_ticker = benchmark_weights.get(ticker, 0.0)
                port_ret_ticker = portfolio_returns.get(ticker, 0.0)
                bmk_ret_ticker = benchmark_returns.get(ticker, 0.0)
                selection_contribution += bmk_wt_ticker * (port_ret_ticker - bmk_ret_ticker)

        selection_effect[sector] = selection_contribution

        # Interaction effect (security-level)
        interaction_contribution = 0.0
        for ticker, ticker_sector in sectors.items():
            if ticker_sector == sector:
                port_wt_ticker = portfolio_weights.get(ticker, 0.0)
                bmk_wt_ticker = benchmark_weights.get(ticker, 0.0)
                port_ret_ticker = portfolio_returns.get(ticker, 0.0)
                bmk_ret_ticker = benchmark_returns.get(ticker, 0.0)
                interaction_contribution += (port_wt_ticker - bmk_wt_ticker) * (port_ret_ticker - bmk_ret_ticker)

        interaction_effect[sector] = interaction_contribution

    # Calculate total effects
    total_allocation = sum(allocation_effect.values())
    total_selection = sum(selection_effect.values())
    total_interaction = sum(interaction_effect.values())

    # Top contributors and detractors
    ticker_contributions = []
    for ticker in set(portfolio_weights.keys()) | set(benchmark_weights.keys()):
        port_wt = portfolio_weights.get(ticker, 0.0)
        bmk_wt = benchmark_weights.get(ticker, 0.0)
        port_ret = portfolio_returns.get(ticker, 0.0)
        bmk_ret = benchmark_returns.get(ticker, 0.0)

        contribution = port_wt * port_ret - bmk_wt * bmk_ret
        ticker_contributions.append({"ticker": ticker, "contribution": contribution})

    top_contributors = sorted(ticker_contributions, key=lambda x: x["contribution"], reverse=True)[:5]
    top_detractors = sorted(ticker_contributions, key=lambda x: x["contribution"])[:5]

    LOGGER.info(
        f"Brinson attribution: Active return={total_active_return:.2%}, Allocation={total_allocation:.2%}, "
        f"Selection={total_selection:.2%}, Interaction={total_interaction:.2%}"
    )

    return AttributionResult(
        total_active_return=total_active_return,
        allocation_effect=allocation_effect,
        selection_effect=selection_effect,
        interaction_effect=interaction_effect,
        top_contributors=top_contributors,
        top_detractors=top_detractors,
    )


def calculate_portfolio_return(weights: Dict[str, float], returns: Dict[str, float]) -> float:
    """Calculate portfolio return from weights and returns."""
    return sum(weights.get(ticker, 0.0) * returns.get(ticker, 0.0) for ticker in weights)


def format_attribution_table(attribution: AttributionResult) -> str:
    """Format attribution result as readable table."""
    lines = ["\nPerformance Attribution Analysis", "=" * 60]

    lines.append(f"\nTotal Active Return: {attribution.total_active_return:.2%}")
    lines.append("\nBy Sector:")

    all_sectors = set(attribution.allocation_effect.keys()) | set(attribution.selection_effect.keys())

    lines.append(f"{'Sector':30s} {'Allocation':>12s} {'Selection':>12s} {'Interaction':>12s}")
    lines.append("-" * 66)

    for sector in sorted(all_sectors):
        alloc = attribution.allocation_effect.get(sector, 0.0)
        select = attribution.selection_effect.get(sector, 0.0)
        interact = attribution.interaction_effect.get(sector, 0.0)
        lines.append(f"{sector:30s} {alloc:12.2%} {select:12.2%} {interact:12.2%}")

    # Totals
    total_alloc = sum(attribution.allocation_effect.values())
    total_select = sum(attribution.selection_effect.values())
    total_interact = sum(attribution.interaction_effect.values())
    lines.append("-" * 66)
    lines.append(f"{'TOTAL':30s} {total_alloc:12.2%} {total_select:12.2%} {total_interact:12.2%}")

    # Top contributors/detractors
    lines.append("\nTop Contributors:")
    for i, item in enumerate(attribution.top_contributors[:5], 1):
        lines.append(f"  {i}. {item['ticker']:10s}: {item['contribution']:+.2%}")

    lines.append("\nTop Detractors:")
    for i, item in enumerate(attribution.top_detractors[:5], 1):
        lines.append(f"  {i}. {item['ticker']:10s}: {item['contribution']:+.2%}")

    return "\n".join(lines)


