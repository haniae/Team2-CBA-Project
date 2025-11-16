"""Portfolio reporting and narrative generation for IVPA."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .portfolio_attribution import AttributionResult
from .portfolio_optimizer import OptimizationResult
from .portfolio_scenarios import ScenarioResult

LOGGER = logging.getLogger(__name__)


@dataclass
class CommitteeBrief:
    """Auto-generated committee brief for meeting agendas."""

    insights: List[str]
    key_metrics: Dict[str, Any]
    recommendations: List[str]


def generate_committee_brief(
    portfolio_name: str,
    attribution_result: Optional[AttributionResult] = None,
    optimization_result: Optional[OptimizationResult] = None,
    scenario_results: Optional[Dict[str, ScenarioResult]] = None,
    policy_violations: Optional[List[Dict[str, Any]]] = None,
) -> CommitteeBrief:
    """
    Generate 3-5 key insights for investment committee meeting agenda.

    Creates natural language summaries from attribution, optimization, and scenario analysis.
    """
    insights = []
    key_metrics = {}
    recommendations = []

    # Attribution insights
    if attribution_result:
        active_return = attribution_result.total_active_return
        if active_return > 0.005:  # >0.5%
            insights.append(f"Portfolio outperformed benchmark by {active_return*100:.1f} bps this period.")

            # Identify main driver
            total_allocation = sum(attribution_result.allocation_effect.values())
            total_selection = sum(attribution_result.selection_effect.values())

            if abs(total_allocation) > abs(total_selection):
                insights.append(f"Outperformance driven primarily by allocation effect (+{total_allocation*100:.1f} bps).")
            else:
                insights.append(f"Outperformance driven primarily by security selection (+{total_selection*100:.1f} bps).")

            # Top contributor
            if attribution_result.top_contributors:
                top_contrib = attribution_result.top_contributors[0]
                insights.append(
                    f"Top contributor: {top_contrib['ticker']} added {abs(top_contrib['contribution'])*100:.1f} bps to returns."
                )

        elif active_return < -0.005:  # Underperformance
            insights.append(f"Portfolio underperformed benchmark by {abs(active_return)*100:.1f} bps this period.")

        # Key metrics
        key_metrics["active_return"] = active_return
        key_metrics["allocation_effect"] = sum(attribution_result.allocation_effect.values())
        key_metrics["selection_effect"] = sum(attribution_result.selection_effect.values())

    # Optimization insights
    if optimization_result:
        num_trades = len(optimization_result.proposed_trades)
        if num_trades > 0:
            insights.append(f"Proposed rebalance: {num_trades} trades recommended to optimize portfolio efficiency.")

            # Expected improvement
            if optimization_result.metrics_before and optimization_result.metrics_after:
                before_ret = optimization_result.metrics_before.get("expected_return", 0)
                after_ret = optimization_result.metrics_after.get("expected_return", 0)
                if after_ret > before_ret:
                    improvement = (after_ret - before_ret) * 100
                    recommendations.append(f"Expected return improvement of {improvement:.1f} bps from optimization.")

            # Policy flags
            if optimization_result.policy_flags:
                recommendations.append(f"All proposed trades respect policy constraints: {len(optimization_result.policy_flags)} limits applied.")

    # Policy violations
    if policy_violations:
        num_violations = len(policy_violations)
        insights.append(f"⚠️ Policy violations detected: {num_violations} constraints breached requiring immediate action.")
        recommendations.append("Review and rebalance portfolio to restore policy compliance.")

    # Scenario analysis
    if scenario_results:
        bear_result = scenario_results.get("Bear")
        if bear_result:
            bear_return = bear_result.portfolio_return
            if bear_return < -0.10:  # -10% or worse
                insights.append(f"Stress test: portfolio would decline {abs(bear_return)*100:.0f}% in bear market scenario.")

    # Default if no insights
    if not insights:
        insights.append(f"Portfolio performance in-line with benchmark.")
        insights.append("No policy violations or required actions.")

    LOGGER.info(f"Generated committee brief with {len(insights)} insights for {portfolio_name}")

    return CommitteeBrief(insights=insights, key_metrics=key_metrics, recommendations=recommendations)


def generate_optimization_summary(optimization_result: OptimizationResult) -> str:
    """
    Generate narrative explaining proposed optimization trades.

    Returns natural language summary for user review.
    """
    lines = []

    num_trades = len(optimization_result.proposed_trades)
    if num_trades == 0:
        return "No trades recommended. Current portfolio is already optimal within constraints."

    lines.append(f"Proposed Optimization Summary ({optimization_result.status}):")
    lines.append(f"\n{num_trades} trades recommended to improve portfolio efficiency.")

    # Key changes
    buy_trades = [t for t in optimization_result.proposed_trades if t["action"] == "buy"]
    sell_trades = [t for t in optimization_result.proposed_trades if t["action"] == "sell"]

    if buy_trades:
        top_buy = sorted(buy_trades, key=lambda t: t["to_weight"], reverse=True)[0]
        lines.append(f"Largest addition: {top_buy['ticker']} +{top_buy['to_weight']*100:.1f}% weight")
    if sell_trades:
        top_sell = sorted(sell_trades, key=lambda t: t["from_weight"], reverse=True)[0]
        lines.append(f"Largest reduction: {top_sell['ticker']} -{top_sell['from_weight']*100:.1f}% weight")

    # Expected impact
    if optimization_result.metrics_before and optimization_result.metrics_after:
        before_ret = optimization_result.metrics_before.get("expected_return", 0)
        after_ret = optimization_result.metrics_after.get("expected_return", 0)
        before_var = optimization_result.metrics_before.get("portfolio_variance", 0)
        after_var = optimization_result.metrics_after.get("portfolio_variance", 0)

        lines.append(f"\nExpected Impact:")
        lines.append(f"  Return: {before_ret:.2%} → {after_ret:.2%} ({'+' if after_ret >= before_ret else ''}{(after_ret-before_ret)*100:.2f} bps)")

        if before_var > 0 and after_var > 0:
            risk_change = ((after_var**0.5 / before_var**0.5) - 1) * 100
            lines.append(f"  Risk: {before_var**0.5:.2%} → {after_var**0.5:.2%} ({'+' if risk_change >= 0 else ''}{risk_change:.1f}%)")

    # Constraints respected
    if optimization_result.policy_flags:
        lines.append(f"\nConstraints Applied:")
        for flag in optimization_result.policy_flags:
            lines.append(f"  • {flag}")

    return "\n".join(lines)


def generate_attribution_narrative(attribution: AttributionResult, period: str = "Q4 2024") -> str:
    """
    Generate natural language explanation of attribution results.

    Returns narrative describing allocation, selection, and interaction effects.
    """
    lines = []

    lines.append(f"Performance Attribution for {period}:")
    lines.append(f"\nTotal Active Return: {attribution.total_active_return:+.2%}")

    # Decompose by effect
    total_alloc = sum(attribution.allocation_effect.values())
    total_select = sum(attribution.selection_effect.values())
    total_interact = sum(attribution.interaction_effect.values())

    lines.append("\nDecomposition:")
    if abs(total_alloc) > 0.0001:
        lines.append(f"  • Allocation effect: {total_alloc:+.2%} (sector over/underweights)")
    if abs(total_select) > 0.0001:
        lines.append(f"  • Selection effect: {total_select:+.2%} (security selection within sectors)")
    if abs(total_interact) > 0.0001:
        lines.append(f"  • Interaction effect: {total_interact:+.2%} (combined effect)")

    # Top contributors/detractors
    if attribution.top_contributors:
        lines.append("\nTop Contributors:")
        for i, item in enumerate(attribution.top_contributors[:3], 1):
            lines.append(f"  {i}. {item['ticker']}: {item['contribution']:+.2%}")

    if attribution.top_detractors:
        lines.append("\nTop Detractors:")
        for i, item in enumerate(attribution.top_detractors[:3], 1):
            if item['contribution'] < -0.0001:
                lines.append(f"  {i}. {item['ticker']}: {item['contribution']:+.2%}")

    return "\n".join(lines)


def format_committee_brief(brief: CommitteeBrief) -> str:
    """Format committee brief as markdown-ready text."""
    lines = ["## Investment Committee Brief", ""]

    lines.append("### Key Insights")
    for i, insight in enumerate(brief.insights, 1):
        lines.append(f"{i}. {insight}")

    if brief.key_metrics:
        lines.append("\n### Performance Metrics")
        for key, value in brief.key_metrics.items():
            if isinstance(value, float):
                lines.append(f"- {key.replace('_', ' ').title()}: {value:+.2%}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    if brief.recommendations:
        lines.append("\n### Recommendations")
        for i, rec in enumerate(brief.recommendations, 1):
            lines.append(f"{i}. {rec}")

    return "\n".join(lines)


def generate_portfolio_summary(
    portfolio_name: str,
    num_holdings: int,
    total_value: float,
    sector_exposure: Dict[str, float],
    top_holdings: List[Dict[str, Any]],
) -> str:
    """Generate executive summary of portfolio composition."""
    lines = [f"## {portfolio_name} - Portfolio Summary"]

    lines.append(f"\nPortfolio value: ${total_value:,.0f}")
    lines.append(f"Number of holdings: {num_holdings}")
    lines.append(f"Sectors: {len(sector_exposure)}")

    # Top sectors
    lines.append("\nTop Sectors:")
    sorted_sectors = sorted(sector_exposure.items(), key=lambda x: x[1], reverse=True)
    for sector, weight in sorted_sectors[:5]:
        lines.append(f"  • {sector}: {weight*100:.1f}%")

    # Top holdings
    if top_holdings:
        lines.append("\nTop Holdings:")
        for i, holding in enumerate(top_holdings[:10], 1):
            ticker = holding.get("ticker", "?")
            weight = holding.get("weight", 0)
            lines.append(f"  {i:2d}. {ticker:10s}: {weight*100:5.1f}%")

    return "\n".join(lines)


