"""Portfolio exposure analysis by sector, factor, issuer, and geography."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yfinance as yf

from .portfolio_enrichment import EnrichedHolding, calculate_sector_active_weights
from .portfolio_calculations import calculate_betas_batch

LOGGER = logging.getLogger(__name__)


@dataclass
class ExposureAnalysis:
    """Multi-dimensional portfolio exposure analysis."""

    sector_exposure: Dict[str, float]  # sector -> weight
    factor_exposure: Dict[str, float]  # factor -> exposure
    issuer_exposure: Dict[str, float]  # ticker -> weight
    geographic_exposure: Dict[str, float]  # country -> weight
    concentration_metrics: Dict[str, float]  # HHI, top_n_concentration, etc.


def calculate_sector_exposure(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate sector exposure by GICS sector.

    Returns dict of sector -> portfolio weight.
    """
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    return dict(sector_weights)


def calculate_factor_exposure(
    enriched_holdings: List[EnrichedHolding],
    database_path: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Calculate factor exposures using simplified factor model.

    Factors: beta, value, momentum, size, quality, volatility
    Returns dict of factor -> exposure.
    
    Args:
        enriched_holdings: List of enriched holdings
        database_path: Optional database path for beta calculation (if None, uses fallback)
    """
    factor_exposures = defaultdict(float)
    total_weight = sum(h.weight or 0 for h in enriched_holdings)

    if total_weight == 0:
        return {}

    # Calculate betas from database if available
    betas = {}
    if database_path:
        try:
            ticker_list = [h.ticker for h in enriched_holdings if h.ticker]
            betas = calculate_betas_batch(
                database_path,
                ticker_list,
                benchmark="SPY",
                lookback_days=252,
            )
        except Exception as e:
            LOGGER.debug(f"Could not calculate betas from database: {e}")

    for holding in enriched_holdings:
        weight = holding.weight or 0.0

        # Beta (use database calculation if available, fallback to yfinance)
        if holding.ticker:
            beta = None
            if database_path and holding.ticker in betas:
                beta = betas[holding.ticker]
            else:
                # Fallback to yfinance if database unavailable
                try:
                    ticker_data = yf.Ticker(holding.ticker)
                    hist = ticker_data.history(period="1y")
                    if not hist.empty:
                        sp500 = yf.Ticker("^GSPC").history(period="1y")
                        if not sp500.empty:
                            stock_returns = hist["Close"].pct_change().dropna()
                            market_returns = sp500["Close"].pct_change().dropna()
                            if len(stock_returns) > 10 and len(market_returns) > 10:
                                common_dates = stock_returns.index.intersection(market_returns.index)
                                if len(common_dates) > 10:
                                    stock_ret = stock_returns.loc[common_dates]
                                    mkt_ret = market_returns.loc[common_dates]
                                    beta = stock_ret.cov(mkt_ret) / mkt_ret.var() if mkt_ret.var() > 0 else 1.0
                except Exception as e:
                    LOGGER.debug(f"Could not calculate beta for {holding.ticker}: {e}")
            
            if beta is not None:
                factor_exposures["beta"] += weight * beta

        # Value (inverse of P/E)
        if holding.pe_ratio and holding.pe_ratio > 0:
            value_score = 1.0 / holding.pe_ratio
            factor_exposures["value"] += weight * value_score

        # Momentum (revenue growth proxy)
        if holding.revenue_growth:
            momentum_score = max(0, min(1, holding.revenue_growth / 20))  # Normalize to 0-1
            factor_exposures["momentum"] += weight * momentum_score

        # Quality (ROE proxy)
        if holding.roe:
            quality_score = max(0, min(1, holding.roe / 30))  # Normalize to 0-1
            factor_exposures["quality"] += weight * quality_score

    return dict(factor_exposures)


def calculate_issuer_exposure(enriched_holdings: List[EnrichedHolding], top_n: int = 10) -> Dict[str, float]:
    """
    Calculate issuer concentration.

    Returns dict of ticker -> weight for top N holdings.
    """
    sorted_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)
    issuer_weights = {holding.ticker: holding.weight for holding in sorted_holdings[:top_n] if holding.weight}

    return issuer_weights


def calculate_concentration_metrics(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate concentration metrics: HHI, top 5/10/20 concentration.

    HHI (Herfindahl-Hirschman Index) measures concentration (0-1, higher = more concentrated).
    """
    weights = [h.weight or 0.0 for h in enriched_holdings if h.weight]
    total_weight = sum(weights)

    if total_weight == 0:
        return {}

    # Normalize weights to sum to 1
    normalized_weights = [w / total_weight for w in weights]

    # HHI
    hhi = sum(w**2 for w in normalized_weights)

    # Top N concentration
    sorted_weights = sorted(normalized_weights, reverse=True)
    top_5_concentration = sum(sorted_weights[:5])
    top_10_concentration = sum(sorted_weights[:10])
    top_20_concentration = sum(sorted_weights[:20])

    return {
        "hhi": hhi,
        "top_5_concentration": top_5_concentration,
        "top_10_concentration": top_10_concentration,
        "top_20_concentration": top_20_concentration,
        "effective_num_positions": 1.0 / hhi if hhi > 0 else 0,
    }


def calculate_geographic_exposure(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate geographic exposure by company headquarters country.

    This is a simplified implementation. A full version would use country mapping data.
    """
    # Simplified mapping for major US stocks
    us_tickers = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "V", "MA", "JPM"}
    geography_weights = defaultdict(float)

    for holding in enriched_holdings:
        if holding.weight:
            if holding.ticker in us_tickers:
                geography_weights["United States"] += holding.weight
            else:
                geography_weights["Other"] += holding.weight

    return dict(geography_weights)


def analyze_exposure(
    enriched_holdings: List[EnrichedHolding],
    database_path: Optional[Path] = None,
) -> ExposureAnalysis:
    """
    Perform comprehensive exposure analysis across all dimensions.

    Returns ExposureAnalysis with sector, factor, issuer, and geographic exposures.
    """
    sector_exp = calculate_sector_exposure(enriched_holdings)
    factor_exp = calculate_factor_exposure(enriched_holdings, database_path=database_path)
    issuer_exp = calculate_issuer_exposure(enriched_holdings, top_n=10)
    geographic_exp = calculate_geographic_exposure(enriched_holdings)
    concentration = calculate_concentration_metrics(enriched_holdings)

    analysis = ExposureAnalysis(
        sector_exposure=sector_exp,
        factor_exposure=factor_exp,
        issuer_exposure=issuer_exp,
        geographic_exposure=geographic_exp,
        concentration_metrics=concentration,
    )

    LOGGER.info(f"Exposure analysis completed: {len(sector_exp)} sectors, HHI={concentration.get('hhi', 0):.3f}")
    return analysis


def compare_exposures_vs_benchmark(
    portfolio_holdings: List[EnrichedHolding], benchmark_holdings: List[EnrichedHolding]
) -> Dict[str, Any]:
    """
    Compare portfolio exposures vs benchmark holdings.

    Returns comparison breakdowns by sector, factor, and issuer.
    """
    portfolio_analysis = analyze_exposure(portfolio_holdings)
    benchmark_analysis = analyze_exposure(benchmark_holdings)

    comparison = {
        "sector_tilts": {},
        "factor_tilts": {},
        "issuer_tilts": {},
        "concentration_difference": {},
    }

    # Sector tilts (active weights)
    all_sectors = set(portfolio_analysis.sector_exposure.keys()) | set(benchmark_analysis.sector_exposure.keys())
    for sector in all_sectors:
        port_wt = portfolio_analysis.sector_exposure.get(sector, 0.0)
        bmk_wt = benchmark_analysis.sector_exposure.get(sector, 0.0)
        comparison["sector_tilts"][sector] = port_wt - bmk_wt

    # Factor tilts
    all_factors = set(portfolio_analysis.factor_exposure.keys()) | set(benchmark_analysis.factor_exposure.keys())
    for factor in all_factors:
        port_exp = portfolio_analysis.factor_exposure.get(factor, 0.0)
        bmk_exp = benchmark_analysis.factor_exposure.get(factor, 0.0)
        comparison["factor_tilts"][factor] = port_exp - bmk_exp

    # Issuer tilts
    all_issuers = set(portfolio_analysis.issuer_exposure.keys()) | set(benchmark_analysis.issuer_exposure.keys())
    for issuer in all_issuers:
        port_wt = portfolio_analysis.issuer_exposure.get(issuer, 0.0)
        bmk_wt = benchmark_analysis.issuer_exposure.get(issuer, 0.0)
        comparison["issuer_tilts"][issuer] = port_wt - bmk_wt

    # Concentration differences
    if portfolio_analysis.concentration_metrics and benchmark_analysis.concentration_metrics:
        comparison["concentration_difference"] = {
            "hhi_spread": portfolio_analysis.concentration_metrics.get("hhi", 0)
            - benchmark_analysis.concentration_metrics.get("hhi", 0),
            "top_10_spread": portfolio_analysis.concentration_metrics.get("top_10_concentration", 0)
            - benchmark_analysis.concentration_metrics.get("top_10_concentration", 0),
        }

    return comparison


def format_exposure_table(exposure_dict: Dict[str, float], title: str = "Exposure") -> str:
    """
    Format exposure dictionary as a formatted table string.

    Useful for chatbot/CLI output.
    """
    if not exposure_dict:
        return f"{title}: No data"

    lines = [f"\n{title}:", "=" * 50]
    sorted_items = sorted(exposure_dict.items(), key=lambda x: x[1], reverse=True)

    for key, value in sorted_items:
        lines.append(f"  {key:30s}: {value:7.2%}")

    return "\n".join(lines)


def check_policy_compliance(
    exposure_analysis: ExposureAnalysis, policy_constraints: List[Any]  # PolicyConstraint type
) -> List[Dict[str, Any]]:
    """
    Check if portfolio exposures comply with policy constraints.

    Returns list of violations with details.
    """
    violations = []

    for constraint in policy_constraints:
        if constraint.constraint_type == "allocation_cap":
            if constraint.dimension == "*":  # Universal cap
                for ticker, weight in exposure_analysis.issuer_exposure.items():
                    if constraint.max_value and weight > constraint.max_value:
                        violations.append(
                            {
                                "constraint_type": "allocation_cap",
                                "dimension": ticker,
                                "current_value": weight,
                                "limit": constraint.max_value,
                                "violation": weight - constraint.max_value,
                            }
                        )

        elif constraint.constraint_type == "sector_limit":
            sector = constraint.dimension
            current_wt = exposure_analysis.sector_exposure.get(sector, 0.0)
            if constraint.min_value and current_wt < constraint.min_value:
                violations.append(
                    {
                        "constraint_type": "sector_limit",
                        "dimension": sector,
                        "current_value": current_wt,
                        "limit": constraint.min_value,
                        "violation": current_wt - constraint.min_value,
                    }
                )
            if constraint.max_value and current_wt > constraint.max_value:
                violations.append(
                    {
                        "constraint_type": "sector_limit",
                        "dimension": sector,
                        "current_value": current_wt,
                        "limit": constraint.max_value,
                        "violation": current_wt - constraint.max_value,
                    }
                )

    if violations:
        LOGGER.warning(f"Policy violations detected: {len(violations)}")
    else:
        LOGGER.info("All policy constraints satisfied")

    return violations


def compare_exposures_before_after_rebalance(
    before_holdings: List[EnrichedHolding], after_holdings: List[EnrichedHolding]
) -> Dict[str, Any]:
    """
    Show exposure changes from proposed rebalance.

    Returns comparison showing sector and factor changes.
    """
    before_analysis = analyze_exposure(before_holdings)
    after_analysis = analyze_exposure(after_holdings)

    changes = {
        "sector_changes": {},
        "factor_changes": {},
        "concentration_changes": {},
    }

    # Sector changes
    all_sectors = set(before_analysis.sector_exposure.keys()) | set(after_analysis.sector_exposure.keys())
    for sector in all_sectors:
        before_wt = before_analysis.sector_exposure.get(sector, 0.0)
        after_wt = after_analysis.sector_exposure.get(sector, 0.0)
        if abs(after_wt - before_wt) > 0.001:  # Only show non-trivial changes
            changes["sector_changes"][sector] = {"before": before_wt, "after": after_wt, "change": after_wt - before_wt}

    # Factor changes
    all_factors = set(before_analysis.factor_exposure.keys()) | set(after_analysis.factor_exposure.keys())
    for factor in all_factors:
        before_exp = before_analysis.factor_exposure.get(factor, 0.0)
        after_exp = after_analysis.factor_exposure.get(factor, 0.0)
        if abs(after_exp - before_exp) > 0.001:
            changes["factor_changes"][factor] = {"before": before_exp, "after": after_exp, "change": after_exp - before_exp}

    # Concentration changes
    if before_analysis.concentration_metrics and after_analysis.concentration_metrics:
        changes["concentration_changes"] = {
            "hhi_change": after_analysis.concentration_metrics.get("hhi", 0) - before_analysis.concentration_metrics.get("hhi", 0),
            "top_10_change": after_analysis.concentration_metrics.get("top_10_concentration", 0)
            - before_analysis.concentration_metrics.get("top_10_concentration", 0),
        }

    return changes


