"""Financial analytics utilities built on top of the BenchmarkOS datastore."""

from __future__ import annotations

# Loads raw financial facts, computes derived metrics, and exposes helpers used by the
# chatbot and web API for comparisons, scenarios, and quote refreshes.

import logging
import math
import re
import sqlite3
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from . import database
from .config import Settings
from .data_sources import YahooFinanceClient
from .secdb import SecPostgresStore
from .ticker_universe import load_ticker_universe

LOGGER = logging.getLogger(__name__)

BENCHMARK_LABEL = "S&P 500 Avg"

@dataclass(frozen=True)
class ScenarioSummary:
    """Lightweight summary of a stored scenario result returned to clients."""
    ticker: str
    scenario_name: str
    metrics: Dict[str, Optional[float]]
    narrative: str
    created_at: datetime


@dataclass(frozen=True)
class MetricDefinition:
    """Metadata describing a single metric and how it should be presented."""

    name: str
    description: str


BASE_METRICS = {
    "revenue",
    "net_income",
    "operating_income",
    "gross_profit",
    "total_assets",
    "total_liabilities",
    "shareholders_equity",
    "cash_from_operations",
    "cash_from_financing",
    "free_cash_flow",
    "eps_diluted",
    "eps_basic",
    "current_assets",
    "current_liabilities",
    "cash_and_cash_equivalents",
    "capital_expenditures",
    "depreciation_and_amortization",
    "ebit",
    "income_tax_expense",
    "long_term_debt",
    "long_term_debt_current",
    "short_term_debt",
    "shares_outstanding",
    "weighted_avg_diluted_shares",
    "dividends_per_share",
    "dividends_paid",
    "share_repurchases",
    "interest_expense",
}


METRIC_NAME_ALIASES = {
    "operating_cash_flow": "cash_from_operations",
    "operating_cashflow": "cash_from_operations",
    "capital_expenditure": "capital_expenditures",
    "cash": "cash_and_cash_equivalents",
    "share_buybacks": "share_repurchases",
    "total_equity": "shareholders_equity",
    "clean_operating_income": "operating_income",
    "normalised_free_cash_flow": "free_cash_flow",
}

SUPPLEMENTAL_METRICS = {
    "enterprise_value",
    "market_cap",
    "price",
    "total_debt",
    "working_capital",
    "adjusted_ebitda",
}

QUERY_METRICS = frozenset(BASE_METRICS | set(METRIC_NAME_ALIASES.keys()) | SUPPLEMENTAL_METRICS)

DERIVED_METRICS = {
    "profit_margin",
    "net_margin",
    "operating_margin",
    "return_on_assets",
    "roa",
    "return_on_equity",
    "roe",
    "return_on_invested_capital",
    "roic",
    "debt_to_equity",
    "free_cash_flow_margin",
    "cash_conversion",
    "working_capital",
    "ebitda",
    "ebitda_margin",
    "free_cash_flow",
}

AGGREGATE_METRICS = {
    "revenue_cagr",
    "eps_cagr",
    "ebitda_growth",
    "working_capital_change",
    "pe_ratio",
    "ev_ebitda",
    "pb_ratio",
    "peg_ratio",
    "dividend_yield",
    "tsr",
    "share_buyback_intensity",
}

DEFAULT_TAX_RATE = 0.21

METRIC_DEFINITIONS: List[MetricDefinition] = [
    MetricDefinition("revenue", "Revenue"),
    MetricDefinition("net_income", "Net income"),
    MetricDefinition("operating_income", "Operating income"),
    MetricDefinition("gross_profit", "Gross profit"),
    MetricDefinition("cash_from_operations", "Cash from operations"),
    MetricDefinition("free_cash_flow", "Free cash flow"),
    MetricDefinition("total_assets", "Total assets"),
    MetricDefinition("total_liabilities", "Total liabilities"),
    MetricDefinition("shareholders_equity", "Shareholders' equity"),
    MetricDefinition("revenue_cagr", "Revenue CAGR"),
    MetricDefinition("eps_cagr", "EPS CAGR"),
    MetricDefinition("ebitda_growth", "EBITDA growth"),
    MetricDefinition("ebitda_margin", "EBITDA margin"),
    MetricDefinition("profit_margin", "Profit margin"),
    MetricDefinition("operating_margin", "Operating margin"),
    MetricDefinition("net_margin", "Net margin"),
    MetricDefinition("return_on_assets", "Return on assets"),
    MetricDefinition("return_on_equity", "Return on equity"),
    MetricDefinition("return_on_invested_capital", "Return on invested capital"),
    MetricDefinition("free_cash_flow_margin", "Free cash flow margin"),
    MetricDefinition("cash_conversion", "Cash conversion"),
    MetricDefinition("debt_to_equity", "Debt to equity"),
    MetricDefinition("pe_ratio", "P/E ratio"),
    MetricDefinition("ev_ebitda", "EV/EBITDA"),
    MetricDefinition("pb_ratio", "P/B ratio"),
    MetricDefinition("peg_ratio", "PEG ratio"),
    MetricDefinition("dividend_yield", "Dividend yield"),
    MetricDefinition("tsr", "Total shareholder return"),
    MetricDefinition("share_buyback_intensity", "Share buyback intensity"),
]

METRIC_LABELS: Dict[str, str] = {definition.name: definition.description for definition in METRIC_DEFINITIONS}

CURRENCY_METRICS = {
    "revenue",
    "net_income",
    "operating_income",
    "gross_profit",
    "cash_from_operations",
    "cash_from_financing",
    "free_cash_flow",
    "total_assets",
    "total_liabilities",
    "shareholders_equity",
    "working_capital",
    "enterprise_value",
    "market_cap",
}

PERCENTAGE_METRICS = {
    "revenue_cagr",
    "eps_cagr",
    "ebitda_growth",
    "ebitda_margin",
    "profit_margin",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
    "return_on_invested_capital",
    "free_cash_flow_margin",
    "cash_conversion",
    "dividend_yield",
    "tsr",
    "share_buyback_intensity",
}

MULTIPLE_METRICS = {
    "debt_to_equity",
    "pe_ratio",
    "ev_ebitda",
    "pb_ratio",
    "peg_ratio",
}

SUMMARY_SECTIONS: List[Tuple[str, Sequence[str]]] = [
    (
        "Phase1 KPIs",
        (
            "revenue",
            "net_income",
            "operating_income",
            "gross_profit",
            "cash_from_operations",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "shareholders_equity",
        ),
    ),
    (
        "Phase 2 KPIs",
        (
            "revenue_cagr",
            "eps_cagr",
            "ebitda_growth",
            "ebitda_margin",
            "profit_margin",
            "operating_margin",
            "net_margin",
            "return_on_assets",
            "return_on_equity",
            "return_on_invested_capital",
            "free_cash_flow_margin",
            "cash_conversion",
            "debt_to_equity",
            "pe_ratio",
            "ev_ebitda",
            "pb_ratio",
            "peg_ratio",
            "dividend_yield",
            "tsr",
            "share_buyback_intensity",
        ),
    ),
]


def _now() -> datetime:
    """Return the current UTC timestamp; extracted for easier testing."""
    return datetime.now(timezone.utc)


# Coordinates metric refresh, quote hydration, and accessors so higher layers stay declarative.
class AnalyticsEngine:
    """Provides computed metrics and fact retrieval for the web/API layer."""

    BENCHMARK_LABEL = BENCHMARK_LABEL

    def __init__(self, settings: Settings) -> None:
        """Store runtime settings and bootstrap optional SEC store connections."""
        self.settings = settings
        self._sec_store: Optional[SecPostgresStore] = None
        if settings.database_type == "postgresql":
            self._sec_store = SecPostgresStore(settings)

    def benchmark_label(self) -> str:
        """Return the human-readable label for benchmark columns."""
        return self.BENCHMARK_LABEL

    def compute_benchmark_metrics(
        self,
        metrics: Sequence[str],
        *,
        period_filters: Optional[Sequence[Tuple[int, int]]] = None,
        universe: str = "sp500",
    ) -> Dict[str, database.MetricRecord]:
        """
        Aggregate the latest metric snapshots across a ticker universe.

        Parameters
        ----------
        metrics:
            Metric identifiers to aggregate (case-insensitive).
        period_filters:
            Optional fiscal year ranges to constrain which snapshots contribute to the
            benchmark. When omitted the most recent observation per ticker is used.
        universe:
            Named ticker universe defined in :mod:`ticker_universe`.
        """

        if not metrics:
            return {}

        tickers = load_ticker_universe(universe)
        if not tickers:
            return {}

        normalized_metrics = sorted({metric.lower() for metric in metrics})
        metric_placeholders = ",".join("?" for _ in normalized_metrics)
        ticker_placeholders = ",".join("?" for _ in tickers)

        where_clauses = [
            f"metric IN ({metric_placeholders})",
            f"ticker IN ({ticker_placeholders})",
            "value IS NOT NULL",
        ]

        params: List[Any] = list(normalized_metrics) + tickers
        if period_filters:
            range_clauses: List[str] = []
            for start, end in period_filters:
                if start is None or end is None:
                    continue
                if end < start:
                    start, end = end, start
                range_clauses.append(
                    "(COALESCE(start_year, end_year) >= ? AND COALESCE(end_year, start_year) <= ?)"
                )
                params.extend([start, end])
            if range_clauses:
                where_clauses.append("(" + " OR ".join(range_clauses) + ")")

        where_sql = " AND ".join(where_clauses)
        query = f"""
            WITH ranked AS (
                SELECT
                    ticker,
                    metric,
                    period,
                    value,
                    start_year,
                    end_year,
                    updated_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY ticker, metric
                        ORDER BY
                            COALESCE(end_year, -9999) DESC,
                            COALESCE(start_year, -9999) DESC,
                            COALESCE(updated_at, '') DESC
                    ) AS rn
                FROM metric_snapshots
                WHERE {where_sql}
            )
            SELECT metric, period, value, start_year, end_year
            FROM ranked
            WHERE rn = 1
        """

        grouped: Dict[str, List[sqlite3.Row]] = defaultdict(list)
        with sqlite3.connect(self.settings.database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(query, params).fetchall()
            for row in rows:
                metric_name = (row["metric"] or "").lower()
                value = _to_float(row["value"])
                if value is None:
                    continue
                grouped[metric_name].append(row)

        if not grouped:
            return {}

        benchmark_records: Dict[str, database.MetricRecord] = {}
        timestamp = _now()
        for metric_name, rows in grouped.items():
            values = [_to_float(row["value"]) for row in rows]
            numeric_values = [value for value in values if value is not None]
            if not numeric_values:
                continue

            average_value = sum(numeric_values) / len(numeric_values)
            period_label = _most_common([row["period"] for row in rows])
            start_year = _most_common([row["start_year"] for row in rows])
            end_year = _most_common([row["end_year"] for row in rows])

            benchmark_records[metric_name] = database.MetricRecord(
                ticker=self.BENCHMARK_LABEL,
                metric=metric_name,
                period=str(period_label) if period_label else self.BENCHMARK_LABEL,
                value=average_value,
                source="benchmark",
                updated_at=timestamp,
                start_year=int(start_year) if isinstance(start_year, int) else None,
                end_year=int(end_year) if isinstance(end_year, int) else None,
            )

        return benchmark_records

    def refresh_metrics(self, *, force: bool = False) -> None:
        """Compute or refresh metric snapshots using the latest financial facts."""

        database.initialise(self.settings.database_path)
        rows = self._fetch_base_fact_rows()

        per_year: Dict[Tuple[str, int], Dict[str, Tuple[Optional[float], datetime]]] = {}
        for row in rows:
            ticker = str(row.get("ticker") or "").upper()
            fiscal_year = row.get("fiscal_year")
            if fiscal_year is None:
                continue
            if not ticker:
                continue
            metric_raw = (row.get("metric") or "").lower()
            if not metric_raw:
                continue
            metric = METRIC_NAME_ALIASES.get(metric_raw, metric_raw)
            key = (ticker, fiscal_year)
            bucket = per_year.setdefault(key, {})
            ingested_raw = row.get("ingested_at")
            ingested_at: datetime
            if isinstance(ingested_raw, datetime):
                ingested_at = ingested_raw
            elif isinstance(ingested_raw, str):
                try:
                    ingested_at = datetime.fromisoformat(ingested_raw)
                except ValueError:
                    ingested_at = _now()
            else:
                ingested_at = _now()
            if ingested_at.tzinfo is None:
                ingested_at = ingested_at.replace(tzinfo=timezone.utc)
            else:
                ingested_at = ingested_at.astimezone(timezone.utc)
            current = bucket.get(metric)
            if current is None or ingested_at > current[1]:
                bucket[metric] = (row.get("value"), ingested_at)

        if not per_year:
            LOGGER.info("No financial facts available to compute metrics.")
            return

        tickers = sorted({ticker for ticker, _ in per_year})
        self._ensure_quotes(tickers)

        metric_records: List[database.MetricRecord] = []
        derived_records: List[database.MetricRecord] = []
        ticker_year_map: Dict[str, Dict[int, Dict[str, Tuple[Optional[float], datetime]]]] = defaultdict(dict)

        for (ticker, fiscal_year), metrics in per_year.items():
            ticker_year_map[ticker][fiscal_year] = metrics
            updated_at = _latest_timestamp(metrics)

            for metric_name, (value, recorded_at) in metrics.items():
                numeric_value = _to_float(value)
                if numeric_value is None:
                    continue
                metric_records.append(
                    database.MetricRecord(
                        ticker=ticker,
                        metric=metric_name,
                        period=f"FY{fiscal_year}",
                        value=numeric_value,
                        source="edgar",
                        updated_at=recorded_at,
                        start_year=fiscal_year,
                        end_year=fiscal_year,
                    )
                )

            derived_values = _compute_derived_metrics(metrics)
            for metric_name, value in derived_values.items():
                numeric_value = _to_float(value)
                if numeric_value is None:
                    continue
                derived_records.append(
                    database.MetricRecord(
                        ticker=ticker,
                        metric=metric_name,
                        period=f"FY{fiscal_year}",
                        value=numeric_value,
                        source="derived",
                        updated_at=updated_at,
                        start_year=fiscal_year,
                        end_year=fiscal_year,
                    )
                )
                metrics[metric_name] = (numeric_value, updated_at)

        aggregate_records: List[database.MetricRecord] = []
        for ticker, year_metrics in ticker_year_map.items():
            years = sorted(year_metrics)
            if not years:
                continue
            last_year = years[-1]
            last_metrics = year_metrics[last_year]
            last_updated = _latest_timestamp(last_metrics)
            values_by_year = {
                year: {name: _to_float(pair[0]) for name, pair in metrics.items()}
                for year, metrics in year_metrics.items()
            }
            last_values = values_by_year.get(last_year, {})

            def _add_metric(name: str, value: Optional[float], *, start: Optional[int] = None, end: Optional[int] = None) -> None:
                """Append a derived metric snapshot when a usable numeric value is available."""
                numeric_value = _to_float(value)
                if numeric_value is None:
                    return
                aggregate_records.append(
                    database.MetricRecord(
                        ticker=ticker,
                        metric=name,
                        period=f"FY{last_year}",
                        value=numeric_value,
                        source="derived",
                        updated_at=last_updated,
                        start_year=start if start is not None else last_year,
                        end_year=end if end is not None else last_year,
                    )
                )
                last_metrics[name] = (numeric_value, last_updated)

            def _eps_from(values: Dict[str, Optional[float]]) -> Optional[float]:
                """Derive earnings per share from the best available fact values."""
                eps_value = _first_non_none(values, "eps_diluted", "eps_basic")
                if eps_value is not None:
                    return eps_value
                net_income_val = _first_non_none(values, "net_income")
                shares_val = _first_non_none(values, "weighted_avg_diluted_shares", "shares_outstanding")
                return _safe_div(net_income_val, shares_val)

            if len(years) >= 2:
                periods = len(years) - 1
                revenue_cagr = _calc_cagr(
                    _first_non_none(values_by_year[years[0]], "revenue"),
                    _first_non_none(last_values, "revenue"),
                    periods,
                )
                _add_metric("revenue_cagr", revenue_cagr, start=years[0], end=last_year)

                eps_start = _eps_from(values_by_year[years[0]])
                eps_end = _eps_from(last_values)
                eps_cagr = _calc_cagr(eps_start, eps_end, periods)
                _add_metric("eps_cagr", eps_cagr, start=years[0], end=last_year)

                prev_year = years[-2]
                ebitda_growth = _calc_growth(
                    _first_non_none(values_by_year[prev_year], "ebitda", "adjusted_ebitda"),
                    _first_non_none(last_values, "ebitda", "adjusted_ebitda"),
                )
                _add_metric("ebitda_growth", ebitda_growth, start=prev_year, end=last_year)

                working_cap_change = _calc_growth(
                    _first_non_none(values_by_year[prev_year], "working_capital"),
                    _first_non_none(last_values, "working_capital"),
                )
                _add_metric("working_capital_change", working_cap_change, start=prev_year, end=last_year)

            quote = database.fetch_latest_quote(self.settings.database_path, ticker)
            price = _to_float(quote.get("price") if quote else None)
            if price is None:
                price = _to_float(_first_non_none(last_values, "price"))

            shares = _to_float(
                _first_non_none(last_values, "shares_outstanding", "weighted_avg_diluted_shares")
            )

            market_cap = _to_float(quote.get("raw", {}).get("marketCap") if quote else None)
            if market_cap is None:
                market_cap = _to_float(_first_non_none(last_values, "market_cap"))
            if market_cap is None and price is not None and shares is not None:
                market_cap = price * shares

            book_value = _to_float(_first_non_none(last_values, "shareholders_equity", "total_equity"))
            eps_latest = _eps_from(last_values)

            pe_ratio_value = None
            if price is not None and eps_latest not in (None, 0):
                pe_ratio = _safe_div(price, eps_latest)
                _add_metric("pe_ratio", pe_ratio)
                pe_ratio_value = pe_ratio

            if market_cap is not None and book_value not in (None, 0):
                pb_ratio = _safe_div(market_cap, book_value)
                _add_metric("pb_ratio", pb_ratio)

            total_debt_components = [
                _first_non_none(last_values, "long_term_debt"),
                _first_non_none(last_values, "long_term_debt_current"),
                _first_non_none(last_values, "short_term_debt"),
            ]
            debt_parts = [
                value
                for value in (_to_float(item) for item in total_debt_components)
                if value is not None
            ]
            total_debt = sum(debt_parts) if debt_parts else None
            if total_debt is None:
                total_debt = _to_float(_first_non_none(last_values, "total_debt"))

            cash = _to_float(_first_non_none(last_values, "cash_and_cash_equivalents", "cash"))
            enterprise_value = _to_float(quote.get("raw", {}).get("enterpriseValue") if quote else None)
            if enterprise_value is None:
                enterprise_value = _to_float(_first_non_none(last_values, "enterprise_value"))
            if enterprise_value is None and market_cap is not None:
                enterprise_value = market_cap + (total_debt or 0.0) - (cash or 0.0)

            ebitda_latest = _to_float(_first_non_none(last_values, "ebitda", "adjusted_ebitda"))
            if enterprise_value is not None and ebitda_latest not in (None, 0):
                ev_ebitda = _safe_div(enterprise_value, ebitda_latest)
                _add_metric("ev_ebitda", ev_ebitda)

            eps_cagr_value = last_metrics.get("eps_cagr")[0] if last_metrics.get("eps_cagr") else None
            pe_metric = pe_ratio_value if pe_ratio_value is not None else (
                last_metrics.get("pe_ratio")[0] if last_metrics.get("pe_ratio") else None
            )
            if pe_metric is not None and eps_cagr_value not in (None, 0):
                peg_ratio = _safe_div(pe_metric, eps_cagr_value * 100)
                _add_metric("peg_ratio", peg_ratio)

            dividends_per_share = _to_float(_first_non_none(last_values, "dividends_per_share"))
            if dividends_per_share is None and shares not in (None, 0):
                dividends_paid = _to_float(_first_non_none(last_values, "dividends_paid"))
                if dividends_paid is not None:
                    dividends_per_share = abs(dividends_paid) / shares
            if price is not None and dividends_per_share is not None:
                dividend_yield = _safe_div(dividends_per_share, price)
                _add_metric("dividend_yield", dividend_yield)

            if quote and price is not None:
                one_year_ago = _now() - timedelta(days=365)
                previous_quote = database.fetch_quote_on_or_before(
                    self.settings.database_path, ticker, before=one_year_ago
                )
                prev_price = _to_float(previous_quote.get("price") if previous_quote else None)
                if prev_price not in (None, 0):
                    dividends = dividends_per_share or 0.0
                    tsr = ((price - prev_price) + dividends) / prev_price
                    start_year = max(last_year - 1, years[0])
                    _add_metric("tsr", tsr, start=start_year, end=last_year)

            share_repurchases = _to_float(_first_non_none(last_values, "share_repurchases", "share_buybacks"))
            if share_repurchases is not None and market_cap not in (None, 0):
                intensity = abs(share_repurchases) / market_cap
                _add_metric("share_buyback_intensity", intensity)

        derived_records.extend(aggregate_records)
        all_records = metric_records + derived_records
        if not all_records:
            LOGGER.info("No financial facts available to compute metrics.")
            return
        database.replace_metric_snapshots(self.settings.database_path, all_records)
        LOGGER.info(
            "Updated %d metric snapshots (%d base, %d derived)",
            len(all_records),
            len(metric_records),
            len(derived_records),
        )

    def get_metrics(
        self,
        ticker: str,
        *,
        period_filters: Optional[Sequence[Tuple[int, int]]] = None,
    ) -> List[database.MetricRecord]:
        """Return cached metric snapshots for ``ticker`` with optional period filters."""
        return database.fetch_metric_snapshots(
            self.settings.database_path,
            ticker.upper(),
            period_filters=period_filters,
        )

    def generate_summary(self, ticker: str) -> str:
        """Return a narrative summary of key metrics for ``ticker``."""
        ticker_upper = ticker.upper()
        records = database.fetch_metric_snapshots(self.settings.database_path, ticker_upper)
        if not records:
            return (
                f"No cached metrics for {ticker_upper}. "
                f"Run 'ingest {ticker_upper}' to pull the latest filings."
            )

        latest = self._select_latest_records(records, span_fn=self._period_span)
        if not latest:
            return (
                f"No cached metrics for {ticker_upper}. "
                f"Run 'ingest {ticker_upper}' to pull the latest filings."
            )

        company_name: Optional[str] = None
        try:
            with database.temporary_connection(self.settings.database_path) as connection:
                row = connection.execute(
                    """
                    SELECT company_name
                    FROM financial_facts
                    WHERE ticker = ? AND company_name <> ''
                    ORDER BY ingested_at DESC
                    LIMIT 1
                    """,
                    (ticker_upper,),
                ).fetchone()
                if row and row[0]:
                    company_name = str(row[0])
        except sqlite3.Error:
            LOGGER.debug("Unable to fetch company name for %s", ticker_upper, exc_info=True)

        updated_at = max(
            (record.updated_at for record in latest.values() if record.updated_at),
            default=None,
        )
        header_title = (
            f"{company_name} ({ticker_upper}) snapshot"
            if company_name and company_name.upper() != ticker_upper
            else f"{ticker_upper} snapshot"
        )
        header_lines = [header_title]
        if updated_at:
            header_lines.append(f"Last updated {updated_at.strftime('%Y-%m-%d')}")
        header_lines.append("")

        section_blocks: List[str] = []
        for section_title, metric_names in SUMMARY_SECTIONS:
            lines: List[str] = []
            for metric_name in metric_names:
                label = METRIC_LABELS.get(metric_name, metric_name.replace("_", " ").title())
                record = latest.get(metric_name)
                value_repr = _format_metric_value(metric_name, record)
                period_repr = _format_metric_period(record)
                if period_repr:
                    lines.append(f"- {label}: {value_repr} ({period_repr})")
                else:
                    lines.append(f"- {label}: {value_repr}")
            section_blocks.append("\n".join([section_title, *lines]))

        body = "\n\n".join(section_blocks)
        return "\n".join(header_lines) + body

    def lookup_ticker(self, query: str, *, allow_partial: bool = False) -> Optional[str]:
        """Map a natural-language company reference to a ticker if possible."""
        return database.lookup_ticker(
            self.settings.database_path,
            query,
            allow_partial=allow_partial,
        )


    def run_scenario(
        self,
        ticker: str,
        *,
        scenario_name: str,
        revenue_growth_delta: float = 0.0,
        ebitda_margin_delta: float = 0.0,
        multiple_delta: float = 0.0,
    ) -> ScenarioSummary:
        """Generate an illustrative scenario by tweaking a few core inputs."""
        ticker_upper = ticker.upper()
        records = database.fetch_metric_snapshots(
            self.settings.database_path, ticker_upper
        )
        latest = self._select_latest_records(
            records, span_fn=self._period_span
        )

        def metric_value(name: str) -> Optional[float]:
            """Resolve a metric record from the latest snapshot dictionary."""
            record = latest.get(name)
            return record.value if record else None

        baseline_revenue = metric_value("revenue")
        baseline_ebitda = metric_value("ebitda")
        baseline_margin = metric_value("ebitda_margin")
        if baseline_margin is None and baseline_revenue and baseline_ebitda is not None:
            if baseline_revenue != 0:
                baseline_margin = baseline_ebitda / baseline_revenue

        projected_revenue = (
            None if baseline_revenue is None else baseline_revenue * (1 + revenue_growth_delta)
        )

        projected_margin = None
        if baseline_margin is not None:
            projected_margin = baseline_margin + ebitda_margin_delta

        projected_ebitda = None
        if projected_revenue is not None and projected_margin is not None:
            projected_ebitda = projected_revenue * projected_margin

        baseline_multiple = metric_value("ev_to_adjusted_ebitda")
        if baseline_multiple is None:
            baseline_multiple = metric_value("ev_ebitda")
        if baseline_multiple is None:
            baseline_multiple = metric_value("pe_ratio")

        projected_multiple = (
            None if baseline_multiple is None else baseline_multiple + multiple_delta
        )

        projected_enterprise_value = None
        if projected_multiple is not None and projected_ebitda is not None:
            projected_enterprise_value = projected_multiple * projected_ebitda

        scenario_metrics: Dict[str, Optional[float]] = {
            "baseline_revenue": baseline_revenue,
            "projected_revenue": projected_revenue,
            "baseline_ebitda_margin": baseline_margin,
            "projected_ebitda_margin": projected_margin,
            "projected_ebitda": projected_ebitda,
            "baseline_multiple": baseline_multiple,
            "projected_multiple": projected_multiple,
            "projected_enterprise_value": projected_enterprise_value,
        }

        parts = [f"Scenario '{scenario_name}' for {ticker_upper}:"]
        if baseline_revenue is not None and projected_revenue is not None:
            parts.append(
                f"revenue grows from {baseline_revenue:,.0f} to {projected_revenue:,.0f} ({revenue_growth_delta:+.1%})."
            )
        if baseline_margin is not None and projected_margin is not None:
            parts.append(
                f"EBITDA margin shifts from {baseline_margin:.1%} to {projected_margin:.1%}."
            )
        if projected_enterprise_value is not None:
            parts.append(
                f"Implied enterprise value: {projected_enterprise_value:,.0f}."
            )
        if len(parts) == 1:
            parts.append(
                "Insufficient baseline data to model this scenario - adjust deltas or ingest more facts."
            )
        narrative = " ".join(parts)

        created_at = datetime.utcnow()
        database.store_scenario_result(
            self.settings.database_path,
            database.ScenarioResultRecord(
                ticker=ticker_upper,
                scenario_name=scenario_name,
                metrics={
                    key: (float(value) if isinstance(value, (int, float)) and value is not None else None)
                    for key, value in scenario_metrics.items()
                },
                narrative=narrative,
                created_at=created_at,
            ),
        )

        return ScenarioSummary(
            ticker=ticker_upper,
            scenario_name=scenario_name,
            metrics=scenario_metrics,
            narrative=narrative,
            created_at=created_at,
        )

    def financial_facts(
        self,
        *,
        ticker: str,
        fiscal_year: Optional[int] = None,
        metric: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[database.FinancialFactRecord]:
        """Fetch raw SEC facts for a ticker/year, falling back to SQLite copies."""
        if self._sec_store:
            return self._sec_store.fetch_financial_facts(
                ticker.upper(),
                fiscal_year=fiscal_year,
                metric=metric.lower() if metric else None,
                limit=limit,
            )
        return database.fetch_financial_facts(
            self.settings.database_path,
            ticker.upper(),
            fiscal_year=fiscal_year,
            metric=metric.lower() if metric else None,
            limit=limit,
        )

    def audit_events(
        self,
        ticker: str,
        *,
        fiscal_year: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[database.AuditEventRecord]:
        """Return the most recent audit events persisted for ``ticker``."""
        return database.fetch_audit_events(
            self.settings.database_path,
            ticker.upper(),
            fiscal_year=fiscal_year,
            limit=limit,
        )

    def _fetch_base_fact_rows(self) -> List[Dict[str, Any]]:
        """Yield raw fact rows from the configured backing store (Postgres or SQLite)."""
        if self._sec_store:
            return self._sec_store.fetch_base_facts(sorted(QUERY_METRICS))

        with sqlite3.connect(self.settings.database_path) as connection:
            connection.row_factory = sqlite3.Row
            placeholders = ",".join(["?"] * len(QUERY_METRICS))
            rows = connection.execute(
                f"""
                SELECT ticker, metric, fiscal_year, period, value, source, ingested_at
                FROM financial_facts
                WHERE metric IN ({placeholders})
                  AND fiscal_year IS NOT NULL
                ORDER BY ticker, fiscal_year, metric, ingested_at DESC
                """,
                tuple(QUERY_METRICS),
            ).fetchall()
        return [dict(row) for row in rows]

    def _ensure_quotes(self, tickers: Sequence[str]) -> None:
        """Ensure supplemental market quotes exist for each ticker before deriving ratios."""
        if not tickers:
            return
        if getattr(self.settings, "disable_quote_refresh", False):
            LOGGER.debug("Quote refresh disabled via settings; skipping Yahoo fetch for %d tickers", len(tickers))
            return
        missing: List[str] = []
        for ticker in tickers:
            quote = database.fetch_latest_quote(self.settings.database_path, ticker)
            if not quote:
                missing.append(ticker)
        if not missing:
            return

        client = YahooFinanceClient(
            base_url=self.settings.yahoo_quote_url,
            timeout=self.settings.http_request_timeout,
            batch_size=self.settings.yahoo_quote_batch_size,
        )
        try:
            quotes = client.fetch_quotes(missing)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("Failed to refresh quotes for %s: %s", ", ".join(missing), exc)
            return
        if not quotes:
            return
        database.bulk_insert_market_quotes(self.settings.database_path, quotes)

    def _select_latest_records(
        self,
        records: Sequence[database.MetricRecord],
        *,
        span_fn,
    ) -> Dict[str, database.MetricRecord]:
        """Pick the freshest metric snapshot for each metric name encountered."""
        selected: Dict[str, database.MetricRecord] = {}
        for record in records:
            existing = selected.get(record.metric)
            if existing is None:
                selected[record.metric] = record
                continue
            if record.value is not None and existing.value is None:
                selected[record.metric] = record
                continue
            if record.value is None and existing.value is not None:
                continue
            new_span = span_fn(record.period)
            old_span = span_fn(existing.period)
            if new_span[1] > old_span[1] or (
                new_span[1] == old_span[1] and new_span[0] > old_span[0]
            ):
                selected[record.metric] = record
        return selected

    @staticmethod
    def _period_span(period: str) -> Tuple[int, int]:
        """Parse period strings like 'FY2022' or ranges into integer year spans."""
        years = [int(match) for match in re.findall(r"\d{4}", period)]
        if not years:
            return (0, 0)
        return (min(years), max(years))

def _latest_timestamp(metrics: Dict[str, Tuple[Optional[float], datetime]]) -> datetime:
    """Return the newest ingestion timestamp among the metric entries."""
    return max(pair[1] for pair in metrics.values()) if metrics else _now()


def _first_non_none(mapping: Mapping[str, Optional[float]], *keys: str) -> Optional[float]:
    """Return the first non-None value that matches any of the provided keys."""
    for key in keys:
        if key not in mapping:
            continue
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _to_float(value: Optional[float]) -> Optional[float]:
    """Coerce numeric-like inputs to floats while filtering NaNs or infinities."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Divide numerator by denominator while guarding against missing or zero values."""
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return None


def _calc_cagr(start: Optional[float], end: Optional[float], periods: int) -> Optional[float]:
    """Compute a compound annual growth rate across the supplied periods."""
    start_value = _to_float(start)
    end_value = _to_float(end)
    if start_value in (None, 0) or end_value is None or periods <= 0:
        return None
    if start_value <= 0 or end_value <= 0:
        return None
    try:
        return math.pow(end_value / start_value, 1 / periods) - 1
    except (ValueError, ZeroDivisionError):
        return None


def _calc_growth(previous: Optional[float], current: Optional[float]) -> Optional[float]:
    """Compute the single-period growth relative to the previous value."""
    prev_val = _to_float(previous)
    curr_val = _to_float(current)
    if prev_val in (None, 0) or curr_val is None:
        return None
    return (curr_val - prev_val) / abs(prev_val)


def _most_common(values: Sequence[Any]) -> Optional[Any]:
    """Return the most frequent non-null entry in ``values``."""
    filtered = [value for value in values if value not in (None, "")]
    if not filtered:
        return None
    counter = Counter(filtered)
    return counter.most_common(1)[0][0]

def _format_currency(value: float) -> str:
    """Return a compact currency string with magnitude suffixes."""
    abs_value = abs(value)
    suffix = ""
    scaled = value
    if abs_value >= 1_000_000_000:
        scaled = value / 1_000_000_000
        suffix = "B"
    elif abs_value >= 1_000_000:
        scaled = value / 1_000_000
        suffix = "M"
    elif abs_value >= 1_000:
        scaled = value / 1_000
        suffix = "K"
    sign = "-" if scaled < 0 else ""
    return f"{sign}${abs(scaled):,.1f}{suffix}"


def _format_metric_period(record: Optional[database.MetricRecord]) -> str:
    """Render the coverage period for a metric snapshot."""
    if record is None:
        return ""
    start = record.start_year
    end = record.end_year
    if start and end:
        if start == end:
            return f"FY{start}"
        return f"FY{start}-FY{end}"
    if record.period:
        return record.period
    if end:
        return f"FY{end}"
    if start:
        return f"FY{start}"
    return ""


def _format_metric_value(metric: str, record: Optional[database.MetricRecord]) -> str:
    """Return a display string for a metric based on its unit semantics."""
    if record is None or record.value is None:
        return "–"
    value = record.value
    if metric in PERCENTAGE_METRICS:
        return f"{value * 100:.1f}%"
    if metric in MULTIPLE_METRICS:
        return f"{value:.1f}x"
    if metric in CURRENCY_METRICS:
        return _format_currency(value)
    return f"{value:,.1f}"


def _compute_derived_metrics(
    metrics: Dict[str, Tuple[Optional[float], datetime]]
) -> Dict[str, Optional[float]]:
    """Derive additional ratios and margins from base metric values."""
    value_map = {name: _to_float(pair[0]) for name, pair in metrics.items()}
    derived: Dict[str, Optional[float]] = {}

    revenue = _first_non_none(value_map, "revenue")
    net_income = _first_non_none(value_map, "net_income")
    operating_income = _first_non_none(value_map, "operating_income", "clean_operating_income")
    total_assets = _first_non_none(value_map, "total_assets")
    shareholders_equity = _first_non_none(value_map, "shareholders_equity", "total_equity")
    total_liabilities = _first_non_none(value_map, "total_liabilities", "total_debt")
    cash_from_operations = _first_non_none(value_map, "cash_from_operations", "operating_cash_flow")
    capital_expenditures = _first_non_none(value_map, "capital_expenditures", "capital_expenditure")
    cash = _first_non_none(value_map, "cash_and_cash_equivalents", "cash")
    current_assets = _first_non_none(value_map, "current_assets")
    current_liabilities = _first_non_none(value_map, "current_liabilities")
    ebit = _first_non_none(value_map, "ebit", "operating_income", "clean_operating_income")
    depreciation = _first_non_none(value_map, "depreciation_and_amortization")

    ebitda = _first_non_none(value_map, "ebitda", "adjusted_ebitda")
    if ebitda is None and operating_income is not None:
        ebitda = operating_income + (depreciation or 0.0)

    free_cash_flow = _first_non_none(value_map, "free_cash_flow", "normalised_free_cash_flow")
    if free_cash_flow is None and cash_from_operations is not None and capital_expenditures is not None:
        free_cash_flow = cash_from_operations + capital_expenditures

    working_capital = _first_non_none(value_map, "working_capital")
    if working_capital is None and current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    derived["profit_margin"] = _safe_div(net_income, revenue)
    derived["net_margin"] = derived["profit_margin"]
    derived["operating_margin"] = _safe_div(operating_income, revenue)
    derived["return_on_assets"] = _safe_div(net_income, total_assets)
    derived["roa"] = derived["return_on_assets"]
    derived["return_on_equity"] = _safe_div(net_income, shareholders_equity)
    derived["roe"] = derived["return_on_equity"]
    derived["debt_to_equity"] = _safe_div(total_liabilities, shareholders_equity)
    derived["free_cash_flow_margin"] = _safe_div(free_cash_flow, revenue)
    derived["cash_conversion"] = _safe_div(cash_from_operations, net_income)
    derived["working_capital"] = working_capital
    derived["ebitda"] = ebitda
    derived["ebitda_margin"] = _safe_div(ebitda, revenue)

    invested_capital = None
    if total_assets is not None:
        invested_capital = total_assets
        if cash is not None:
            invested_capital -= cash
        if current_liabilities is not None:
            invested_capital -= current_liabilities
    nopat = None
    if ebit is not None:
        nopat = ebit * (1 - DEFAULT_TAX_RATE)
    derived["return_on_invested_capital"] = _safe_div(nopat, invested_capital)
    derived["roic"] = derived["return_on_invested_capital"]

    if free_cash_flow is not None and "free_cash_flow" not in metrics:
        derived["free_cash_flow"] = free_cash_flow

    return {name: value for name, value in derived.items() if name in DERIVED_METRICS}
