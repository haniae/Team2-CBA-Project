"""Portfolio holdings enrichment with fundamentals and sector mapping."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import database
from .sector_analytics import SECTOR_MAP

LOGGER = logging.getLogger(__name__)


@dataclass
class EnrichedHolding:
    """Enriched holding with fundamentals and sector classification."""

    ticker: str
    weight: Optional[float]
    shares: Optional[float]
    price: Optional[float]
    market_value: Optional[float]
    sector: Optional[str]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    revenue_growth: Optional[float]
    roe: Optional[float]
    roic: Optional[float]


@dataclass
class PortfolioStatistics:
    """Aggregate portfolio statistics."""

    total_market_value: float
    num_holdings: int
    weighted_avg_pe: Optional[float]
    weighted_avg_dividend_yield: Optional[float]
    sector_concentration: Dict[str, float]  # sector -> weight
    top_10_weight: float
    num_sectors: int


def map_sector_classification(ticker: str) -> Optional[str]:
    """Map ticker to GICS sector using sector_analytics mapping."""
    return SECTOR_MAP.get(ticker.upper())


def enrich_holdings_with_fundamentals(
    database_path: database.Path,
    holdings: List[Dict[str, Any]],
    enrich_metrics: Optional[List[str]] = None,
) -> List[EnrichedHolding]:
    """
    Join portfolio holdings with fundamentals from metric_snapshots.

    Args:
        database_path: Path to database
        holdings: List of holding dicts with ticker, weight, shares, etc.
        enrich_metrics: Optional list of metrics to fetch (default: common metrics)

    Returns:
        List of enriched holdings with fundamentals
    """
    if enrich_metrics is None:
        enrich_metrics = ["pe_ratio", "dividend_yield", "revenue_cagr_3y", "roe", "roic"]

    enriched = []

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row

        for holding in holdings:
            ticker = holding.get("ticker", "").upper()

            enriched_holding = EnrichedHolding(
                ticker=ticker,
                weight=holding.get("weight"),
                shares=holding.get("shares"),
                price=holding.get("price"),
                market_value=holding.get("market_value"),
                sector=map_sector_classification(ticker),
                market_cap=None,
                pe_ratio=None,
                dividend_yield=None,
                revenue_growth=None,
                roe=None,
                roic=None,
            )

            # Fetch fundamentals for each metric
            for metric in enrich_metrics:
                try:
                    row = conn.execute(
                        """
                        SELECT value
                        FROM metric_snapshots
                        WHERE ticker = ? AND metric = ?
                        ORDER BY start_year DESC, end_year DESC
                        LIMIT 1
                        """,
                        (ticker, metric),
                    ).fetchone()

                    if row and row["value"] is not None:
                        setattr(enriched_holding, metric, row["value"])

                except Exception as e:
                    LOGGER.debug(f"Could not fetch {metric} for {ticker}: {e}")

            # Fetch market cap if not provided
            if enriched_holding.market_cap is None:
                try:
                    row = conn.execute(
                        """
                        SELECT value
                        FROM metric_snapshots
                        WHERE ticker = ? AND metric = 'market_cap'
                        ORDER BY start_year DESC
                        LIMIT 1
                        """,
                        (ticker,),
                    ).fetchone()
                    if row and row["value"]:
                        enriched_holding.market_cap = row["value"]
                except Exception as e:
                    LOGGER.debug(f"Could not fetch market_cap for {ticker}: {e}")

            enriched.append(enriched_holding)

    LOGGER.info(f"Enriched {len(enriched)} holdings with fundamentals")
    return enriched


def fetch_missing_fundamentals(database_path: database.Path, tickers: List[str]) -> List[str]:
    """
    Identify tickers in portfolio but not in database.

    Returns list of tickers missing from metric_snapshots.
    """
    missing = []

    with sqlite3.connect(database_path) as conn:
        for ticker in tickers:
            row = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM metric_snapshots
                WHERE ticker = ?
                """,
                (ticker.upper(),),
            ).fetchone()

            if row and row["count"] == 0:
                missing.append(ticker.upper())

    LOGGER.info(f"Found {len(missing)} tickers missing fundamentals: {missing}")
    return missing


def calculate_portfolio_statistics(enriched_holdings: List[EnrichedHolding]) -> PortfolioStatistics:
    """
    Calculate aggregate portfolio statistics from enriched holdings.

    Returns portfolio statistics including weighted averages, sector concentration, etc.
    """
    # Total market value
    total_mv = sum(h.market_value or 0 for h in enriched_holdings if h.market_value)

    # Sector concentration
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    # Sort holdings by weight (descending) for top 10 calculation
    sorted_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)
    top_10_weight = sum((h.weight or 0) for h in sorted_holdings[:10])

    # Weighted average calculations
    weighted_pe_sum = 0.0
    weighted_pe_denom = 0.0
    weighted_div_sum = 0.0
    weighted_div_denom = 0.0

    for holding in enriched_holdings:
        if holding.weight:
            if holding.pe_ratio is not None and holding.pe_ratio > 0:
                weighted_pe_sum += holding.weight * holding.pe_ratio
                weighted_pe_denom += holding.weight
            if holding.dividend_yield is not None and holding.dividend_yield > 0:
                weighted_div_sum += holding.weight * holding.dividend_yield
                weighted_div_denom += holding.weight

    weighted_avg_pe = weighted_pe_sum / weighted_pe_denom if weighted_pe_denom > 0 else None
    weighted_avg_div = weighted_div_sum / weighted_div_denom if weighted_div_denom > 0 else None

    stats = PortfolioStatistics(
        total_market_value=total_mv,
        num_holdings=len(enriched_holdings),
        weighted_avg_pe=weighted_avg_pe,
        weighted_avg_dividend_yield=weighted_avg_div,
        sector_concentration=dict(sector_weights),
        top_10_weight=top_10_weight,
        num_sectors=len(sector_weights),
    )

    LOGGER.info(f"Calculated portfolio statistics: {stats.num_holdings} holdings, {stats.num_sectors} sectors")
    return stats


def get_holdings_by_sector(enriched_holdings: List[EnrichedHolding]) -> Dict[str, List[EnrichedHolding]]:
    """Group holdings by GICS sector."""
    by_sector = defaultdict(list)

    for holding in enriched_holdings:
        sector = holding.sector or "Unknown"
        by_sector[sector].append(holding)

    return dict(by_sector)


def calculate_active_weights(
    portfolio_weights: Dict[str, float], benchmark_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate active weights (over/underweights vs benchmark).

    Args:
        portfolio_weights: Dict of ticker -> weight for portfolio
        benchmark_weights: Dict of ticker -> weight for benchmark

    Returns:
        Dict of ticker -> active weight (portfolio - benchmark)
    """
    all_tickers = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
    active_weights = {}

    for ticker in all_tickers:
        port_wt = portfolio_weights.get(ticker, 0.0)
        bmk_wt = benchmark_weights.get(ticker, 0.0)
        active_weights[ticker] = port_wt - bmk_wt

    return active_weights


def calculate_sector_active_weights(
    enriched_holdings: List[EnrichedHolding], benchmark_sector_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate active weights by sector.

    Args:
        enriched_holdings: Enriched portfolio holdings
        benchmark_sector_weights: Benchmark sector weights (sector -> weight)

    Returns:
        Dict of sector -> active weight
    """
    portfolio_sectors = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            portfolio_sectors[holding.sector] += holding.weight

    active_weights = {}
    all_sectors = set(portfolio_sectors.keys()) | set(benchmark_sector_weights.keys())

    for sector in all_sectors:
        port_wt = portfolio_sectors.get(sector, 0.0)
        bmk_wt = benchmark_sector_weights.get(sector, 0.0)
        active_weights[sector] = port_wt - bmk_wt

    return active_weights


def compare_with_benchmark_stats(
    portfolio_stats: PortfolioStatistics, benchmark_stats: PortfolioStatistics
) -> Dict[str, Any]:
    """
    Compare portfolio statistics vs benchmark.

    Returns comparison metrics including active returns, sector tilts, etc.
    """
    comparison = {
        "num_holdings": portfolio_stats.num_holdings - benchmark_stats.num_holdings,
        "num_sectors": portfolio_stats.num_sectors - benchmark_stats.num_sectors,
        "top_10_concentration": portfolio_stats.top_10_weight - benchmark_stats.top_10_weight,
        "weighted_pe_spread": None,
        "weighted_dividend_spread": None,
        "sector_tilts": {},
    }

    # PE and dividend yield spreads
    if portfolio_stats.weighted_avg_pe and benchmark_stats.weighted_avg_pe:
        comparison["weighted_pe_spread"] = portfolio_stats.weighted_avg_pe - benchmark_stats.weighted_avg_pe

    if portfolio_stats.weighted_avg_dividend_yield and benchmark_stats.weighted_avg_dividend_yield:
        comparison["weighted_dividend_spread"] = (
            portfolio_stats.weighted_avg_dividend_yield - benchmark_stats.weighted_avg_dividend_yield
        )

    # Sector tilts (active weights)
    all_sectors = set(portfolio_stats.sector_concentration.keys()) | set(benchmark_stats.sector_concentration.keys())
    for sector in all_sectors:
        port_wt = portfolio_stats.sector_concentration.get(sector, 0.0)
        bmk_wt = benchmark_stats.sector_concentration.get(sector, 0.0)
        comparison["sector_tilts"][sector] = port_wt - bmk_wt

    return comparison


def save_enriched_holdings_to_exposure_snapshots(
    database_path: database.Path,
    portfolio_id: str,
    enriched_holdings: List[EnrichedHolding],
    snapshot_date: Optional[datetime] = None,
) -> None:
    """
    Save enriched holdings as exposure snapshot for historical tracking.

    Creates exposure snapshots for sector and individual holding exposures.
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc)

    snapshots = []

    # Sector exposures
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    for sector, weight in sector_weights.items():
        snapshot_id = f"{portfolio_id}_{snapshot_date.isoformat()}_{sector}_sector"
        snapshots.append(
            database.ExposureSnapshotRecord(
                snapshot_id=snapshot_id,
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date,
                exposure_type="sector",
                dimension=sector,
                value=None,
                weight=weight,
            )
        )

    # Individual holding exposures
    for holding in enriched_holdings:
        if holding.weight:
            snapshot_id = f"{portfolio_id}_{snapshot_date.isoformat()}_{holding.ticker}_holding"
            snapshots.append(
                database.ExposureSnapshotRecord(
                    snapshot_id=snapshot_id,
                    portfolio_id=portfolio_id,
                    snapshot_date=snapshot_date,
                    exposure_type="issuer",
                    dimension=holding.ticker,
                    value=holding.market_value,
                    weight=holding.weight,
                )
            )

    database.bulk_insert_exposure_snapshots(database_path, snapshots)
    LOGGER.info(f"Saved {len(snapshots)} exposure snapshots for portfolio {portfolio_id}")


