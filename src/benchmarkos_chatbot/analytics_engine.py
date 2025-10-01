"""Analytical engine for BenchmarkOS financial intelligence chatbot."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
import re
import difflib

from . import database
from .config import Settings
from .data_ingestion import SECTOR_LABEL_MAP
from .tasks import get_task_manager


_CORPORATE_SUFFIXES = (
    " INCORPORATED",
    " INC",
    " CORPORATION",
    " CORP",
    " COMPANY",
    " CO",
    " LTD",
    " LIMITED",
    " PLC",
    " HOLDINGS",
    " HOLDING",
    " GROUP",
    " LLC",
    " LP",
    " SA",
    " NV",
)


@dataclass(frozen=True)
class MetricComputation:
    """Container for a computed KPI."""

    value: Optional[float]
    period: str
    methodology: str


@dataclass(frozen=True)
class MetricDefinition:
    """Definition for an institutional KPI."""

    name: str
    phase: str
    description: str
    calculator: Callable[[pd.DataFrame], MetricComputation]


@dataclass(frozen=True)
class ScenarioSummary:
    """Aggregated output from a what-if scenario."""

    ticker: str
    scenario_name: str
    metrics: Dict[str, float]
    assumptions: Dict[str, float]
    narrative: str


def _sort_financials(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("fiscal_year")


def _latest_year(df: pd.DataFrame) -> int:
    return int(df["fiscal_year"].max())


def _safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    value = numerator / denominator
    if np.isfinite(value):
        return float(value)
    return None


def _cagr(df: pd.DataFrame, column: str, periods: int) -> Optional[float]:
    df_sorted = _sort_financials(df)
    if df_sorted.shape[0] < periods + 1:
        return None
    window = df_sorted.iloc[-(periods + 1) :]
    start_value = float(window.iloc[0][column])
    end_value = float(window.iloc[-1][column])
    if start_value <= 0 or end_value <= 0:
        return None
    growth = (end_value / start_value) ** (1 / periods) - 1
    return float(growth)


def _eps_series(df: pd.DataFrame) -> pd.Series:
    shares = df["shares_outstanding"].replace(0, np.nan)
    eps = df["adjusted_net_income"] / shares
    return eps.replace([np.inf, -np.inf], np.nan)


def _compute_revenue_cagr(df: pd.DataFrame) -> MetricComputation:
    df_sorted = _sort_financials(df)
    value = _cagr(df_sorted, "revenue", periods=3)
    if value is None:
        return MetricComputation(None, "insufficient-history", "Requires at least 4 usable revenue periods.")
    end_year = _latest_year(df_sorted)
    return MetricComputation(value, f"{end_year-3}-{end_year}", "3-year CAGR on reported revenue.")


def _compute_eps_cagr(df: pd.DataFrame) -> MetricComputation:
    df_sorted = _sort_financials(df)
    eps = _eps_series(df_sorted).dropna()
    if eps.shape[0] < 4:
        return MetricComputation(None, "insufficient-history", "Requires 4 EPS observations post normalisation.")
    start_eps = float(eps.iloc[-4])
    end_eps = float(eps.iloc[-1])
    if start_eps <= 0 or end_eps <= 0:
        return MetricComputation(None, "non-positive-eps", "EPS must be positive for CAGR calculation.")
    value = (end_eps / start_eps) ** (1 / 3) - 1
    end_year = _latest_year(df_sorted)
    return MetricComputation(value, f"{end_year-3}-{end_year}", "3-year CAGR on adjusted EPS.")


def _compute_margin(df: pd.DataFrame, numerator: str, denominator: str, label: str) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    value = _safe_ratio(float(latest[numerator]), float(latest[denominator]))
    methodology = f"Latest fiscal year {label}."
    return MetricComputation(value, str(int(latest["fiscal_year"])), methodology)


def _compute_return_on_equity(df: pd.DataFrame) -> MetricComputation:
    return _compute_margin(df, "adjusted_net_income", "total_equity", "adjusted net income over average equity proxy")


def _compute_return_on_assets(df: pd.DataFrame) -> MetricComputation:
    return _compute_margin(df, "adjusted_net_income", "total_assets", "adjusted net income over total assets")


def _compute_free_cash_flow_margin(df: pd.DataFrame) -> MetricComputation:
    return _compute_margin(df, "normalised_free_cash_flow", "revenue", "normalised FCF divided by revenue")


def _compute_cash_conversion(df: pd.DataFrame) -> MetricComputation:
    return _compute_margin(df, "operating_cash_flow", "revenue", "operating cash flow divided by revenue")


def _compute_working_capital_turnover(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    value = _safe_ratio(float(latest["revenue"]), float(latest["working_capital"]))
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Revenue divided by working capital.")


def _compute_buyback_intensity(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    value = _safe_ratio(float(latest["share_buybacks"]), float(latest["market_cap"]))
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Share repurchases divided by market capitalisation.")


def _compute_total_shareholder_return(df: pd.DataFrame) -> MetricComputation:
    df_sorted = _sort_financials(df)
    if df_sorted.shape[0] < 4:
        return MetricComputation(None, "insufficient-history", "Requires 4 price observations for 3-year TSR.")
    subset = df_sorted.iloc[-4:]
    start_price = float(subset.iloc[0]["price"])
    end_price = float(subset.iloc[-1]["price"])
    if start_price <= 0:
        return MetricComputation(None, "invalid-price", "Starting price must be positive.")
    dividends = (subset["dividends_paid"] / subset["shares_outstanding"].replace(0, np.nan)).fillna(0)
    total_return = (end_price + dividends.iloc[1:].sum() - start_price) / start_price
    end_year = int(subset.iloc[-1]["fiscal_year"])
    return MetricComputation(float(total_return), f"{end_year-3}-{end_year}", "Price appreciation plus dividends over 3 years.")


def _compute_dividend_yield(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    dividends_per_share = _safe_ratio(float(latest["dividends_paid"]), float(latest["shares_outstanding"]))
    value = None if dividends_per_share is None else _safe_ratio(dividends_per_share, float(latest["price"]))
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Total dividends over price in most recent year.")


def _compute_pe_ratio(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    eps = _safe_ratio(float(latest["adjusted_net_income"]), float(latest["shares_outstanding"]))
    value = None if eps in (None, 0) else _safe_ratio(float(latest["price"]), eps)
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Price divided by adjusted EPS.")


def _compute_pb_ratio(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    book_value_per_share = _safe_ratio(float(latest["total_equity"]), float(latest["shares_outstanding"]))
    value = None if book_value_per_share in (None, 0) else _safe_ratio(float(latest["price"]), book_value_per_share)
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Price divided by book value per share.")


def _compute_ev_to_ebitda(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    value = _safe_ratio(float(latest["enterprise_value"]), float(latest["adjusted_ebitda"]))
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Enterprise value divided by adjusted EBITDA.")


def _compute_peg_ratio(df: pd.DataFrame) -> MetricComputation:
    pe = _compute_pe_ratio(df).value
    eps_cagr = _compute_eps_cagr(df).value
    if pe is None or eps_cagr in (None, 0):
        return MetricComputation(None, "requires-pe-and-growth", "Needs positive PE and EPS CAGR.")
    peg = pe / (eps_cagr * 100)
    latest_year = _latest_year(_sort_financials(df))
    return MetricComputation(peg, str(latest_year), "PE divided by EPS growth (growth expressed as %).")


def _compute_net_debt_to_ebitda(df: pd.DataFrame) -> MetricComputation:
    latest = _sort_financials(df).iloc[-1]
    net_debt = float(latest["total_debt"]) - float(latest["cash"])
    value = _safe_ratio(net_debt, float(latest["adjusted_ebitda"]))
    return MetricComputation(value, str(int(latest["fiscal_year"])), "Net debt divided by adjusted EBITDA.")


METRIC_DEFINITIONS: List[MetricDefinition] = [
    MetricDefinition("revenue_cagr_3y", "phase1", "Three-year revenue CAGR", _compute_revenue_cagr),
    MetricDefinition("eps_cagr_3y", "phase1", "Three-year adjusted EPS CAGR", _compute_eps_cagr),
    MetricDefinition("adjusted_ebitda_margin", "phase1", "Adjusted EBITDA margin", lambda df: _compute_margin(df, "adjusted_ebitda", "revenue", "adjusted EBITDA over revenue")),
    MetricDefinition("return_on_equity", "phase1", "Return on equity", _compute_return_on_equity),
    MetricDefinition("fcf_margin", "phase1", "Normalised free cash flow margin", _compute_free_cash_flow_margin),
    MetricDefinition("return_on_assets", "phase2", "Return on assets", _compute_return_on_assets),
    MetricDefinition("operating_margin", "phase2", "Clean operating margin", lambda df: _compute_margin(df, "clean_operating_income", "revenue", "clean operating income over revenue")),
    MetricDefinition("net_margin", "phase2", "Adjusted net margin", lambda df: _compute_margin(df, "adjusted_net_income", "revenue", "adjusted net income over revenue")),
    MetricDefinition("cash_conversion_ratio", "phase2", "Cash conversion ratio", _compute_cash_conversion),
    MetricDefinition("tsr_3y", "phase2", "Three-year total shareholder return", _compute_total_shareholder_return),
    MetricDefinition("dividend_yield", "phase2", "Dividend yield", _compute_dividend_yield),
    MetricDefinition("pe_ratio", "phase2", "Price-to-earnings ratio", _compute_pe_ratio),
    MetricDefinition("pb_ratio", "phase3", "Price-to-book ratio", _compute_pb_ratio),
    MetricDefinition("ev_to_adjusted_ebitda", "phase3", "EV / adjusted EBITDA", _compute_ev_to_ebitda),
    MetricDefinition("peg_ratio", "phase3", "PEG ratio", _compute_peg_ratio),
    MetricDefinition("net_debt_to_ebitda", "phase3", "Net debt to adjusted EBITDA", _compute_net_debt_to_ebitda),
    MetricDefinition("working_capital_turnover", "phase3", "Working capital turnover", _compute_working_capital_turnover),
    MetricDefinition("buyback_intensity", "phase3", "Share buyback intensity", _compute_buyback_intensity),
]

METRIC_DEFINITIONS_BY_NAME: Dict[str, MetricDefinition] = {definition.name: definition for definition in METRIC_DEFINITIONS}
METRIC_DEFINITIONS_BY_PHASE: Dict[str, List[MetricDefinition]] = {}
for definition in METRIC_DEFINITIONS:
    METRIC_DEFINITIONS_BY_PHASE.setdefault(definition.phase, []).append(definition)

class AnalyticsEngine:
    """Core analytics workflow powering BenchmarkOS responses."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._financials_cache: Optional[pd.DataFrame] = None
        self._alias_index: Dict[str, Set[str]] = {}
        self._alias_keys: List[str] = []

    def _load_live_financials(self, ticker: str, *, years: int = 5) -> None:
        """Attempt to fetch live data for a ticker missing from the cache."""

        manager = get_task_manager(self.settings)
        future = manager.submit_ingest(ticker, years=years)
        try:
            future.result(timeout=60)
        except Exception as exc:  # pragma: no cover - network/timeout failures
            raise RuntimeError(
                f"Unable to ingest live data for {ticker}: {exc}"
            ) from exc
        self._financials_cache = None

    @property
    def settings(self) -> Settings:
        return self._settings

    def _load_financials(self) -> pd.DataFrame:
        facts = database.fetch_financial_facts(self.settings.database_path)
        if not facts:
            return pd.DataFrame()
        records = [
            {
                "ticker": fact.ticker,
                "company_name": fact.company_name,
                "fiscal_year": fact.fiscal_year,
                "metric": fact.metric,
                "value": fact.value,
            }
            for fact in facts
        ]
        df = pd.DataFrame(records)
        pivot = (
            df.pivot_table(
                index=["ticker", "company_name", "fiscal_year"],
                columns="metric",
                values="value",
                aggfunc="last",
            )
            .reset_index()
            .sort_values(["ticker", "fiscal_year"])
        )
        pivot.columns = [col if isinstance(col, str) else col[1] for col in pivot.columns]
        return pivot

    def _ensure_financials(self, force: bool = False) -> pd.DataFrame:
        if force or self._financials_cache is None:
            financials = self._load_financials()
            self._financials_cache = financials
            self._rebuild_alias_index(financials)
        return self._financials_cache


    @staticmethod
    def _normalise_alias(value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", value.upper()).strip()

    @staticmethod
    def _strip_suffixes(name: str) -> str:
        candidate = name.upper()
        stripped = candidate
        changed = True
        while changed:
            changed = False
            for suffix in _CORPORATE_SUFFIXES:
                if stripped.endswith(suffix):
                    stripped = stripped[: -len(suffix)]
                    stripped = stripped.rstrip(" ,.")
                    changed = True
        return stripped.strip(" ,.")

    @staticmethod
    def _add_alias(alias_index: Dict[str, Set[str]], alias: str, ticker: str) -> None:
        normalised = AnalyticsEngine._normalise_alias(alias)
        if not normalised:
            return
        alias_index[normalised].add(ticker)

    def _rebuild_alias_index(self, financials: pd.DataFrame) -> None:
        alias_index: Dict[str, Set[str]] = defaultdict(set)
        if financials.empty:
            self._alias_index = {}
            return
        unique_rows = (
            financials[["ticker", "company_name"]]
            .drop_duplicates(subset="ticker")
            .itertuples(index=False)
        )
        for ticker, company_name in unique_rows:
            canonical_ticker = str(ticker).upper()
            display_name = str(company_name)
            self._add_alias(alias_index, canonical_ticker, canonical_ticker)
            self._add_alias(alias_index, display_name, canonical_ticker)
            stripped = self._strip_suffixes(display_name)
            if stripped and stripped != display_name.upper():
                self._add_alias(alias_index, stripped, canonical_ticker)
            tokens = re.split(r"[\s&,.:/-]+", display_name)
            for token in tokens:
                if len(token) < 3:
                    continue
                self._add_alias(alias_index, token, canonical_ticker)
        self._alias_index = {alias: set(values) for alias, values in alias_index.items()}
        self._alias_keys = sorted(self._alias_index.keys())

    def match_ticker(
        self,
        query: str,
        *,
        allow_partial: bool = True,
        max_suggestions: int = 5,
    ) -> tuple[Optional[str], list[str]]:
        """Return a resolved ticker or candidate suggestions."""

        if not query:
            return None, []

        self._ensure_financials()
        normalised = self._normalise_alias(query)
        candidates = self._alias_index.get(normalised)

        stripped = self._strip_suffixes(query)
        if not candidates and stripped:
            stripped_norm = self._normalise_alias(stripped)
            if stripped_norm and stripped_norm != normalised:
                candidates = self._alias_index.get(stripped_norm)
                normalised = stripped_norm if candidates else normalised

        if candidates:
            if len(candidates) == 1:
                return next(iter(candidates)), []
            return None, sorted(candidates)

        suggestions: set[str] = set()
        if allow_partial and " " in query:
            tokens = re.split(r"[\s&,.:/-]+", query)
            for token in tokens:
                if len(token) < 3:
                    continue
                token_candidates = self._alias_index.get(self._normalise_alias(token))
                if token_candidates:
                    if len(token_candidates) == 1:
                        return next(iter(token_candidates)), []
                    suggestions.update(token_candidates)

        alias_keys = self._alias_keys
        if alias_keys:
            close_aliases = difflib.get_close_matches(
                normalised,
                alias_keys,
                n=max_suggestions,
                cutoff=0.65,
            )
            for alias in close_aliases:
                suggestions.update(self._alias_index[alias])

        if not suggestions and stripped and alias_keys:
            stripped_norm = self._normalise_alias(stripped)
            close_aliases = difflib.get_close_matches(
                stripped_norm,
                alias_keys,
                n=max_suggestions,
                cutoff=0.65,
            )
            for alias in close_aliases:
                suggestions.update(self._alias_index[alias])

        return None, sorted(suggestions)[:max_suggestions]

    def lookup_ticker(self, query: str, *, allow_partial: bool = True) -> Optional[str]:
        ticker, _ = self.match_ticker(query, allow_partial=allow_partial)
        return ticker


    def _record_yearly_ratios(
        self,
        ticker: str,
        company_frame: pd.DataFrame,
        timestamp: datetime,
    ) -> None:
        yearly_metrics = self._compute_yearly_ratios(company_frame)
        for year, metrics in yearly_metrics.items():
            for metric_name, value in metrics.items():
                definition = METRIC_DEFINITIONS_BY_NAME.get(metric_name)
                if not definition:
                    continue
                methodology = (
                    f"Fiscal year {year} {definition.description.lower()}."
                )
                database.record_metric_result(
                    self.settings.database_path,
                    database.MetricRecord(
                        ticker=ticker,
                        metric=metric_name,
                        period=str(year),
                        value=value,
                        phase=definition.phase,
                        methodology=methodology,
                        calculated_at=timestamp,
                    ),
                )

    def _compute_yearly_ratios(
        self, company_frame: pd.DataFrame
    ) -> Dict[int, Dict[str, Optional[float]]]:
        yearly: Dict[int, Dict[str, Optional[float]]] = {}
        for _, row in company_frame.iterrows():
            year = int(row["fiscal_year"])
            revenue = float(row.get("revenue", 0))
            adjusted_ebitda = float(row.get("adjusted_ebitda", 0))
            adjusted_net_income = float(row.get("adjusted_net_income", 0))
            normalised_fcf = float(row.get("normalised_free_cash_flow", 0))
            clean_operating_income = float(row.get("clean_operating_income", 0))
            operating_cash_flow = float(row.get("operating_cash_flow", 0))
            total_equity = float(row.get("total_equity", 0))
            total_assets = float(row.get("total_assets", 0))
            shares = float(row.get("shares_outstanding", 0))
            dividends_paid = float(row.get("dividends_paid", 0))
            enterprise_value = float(row.get("enterprise_value", 0))
            market_cap = float(row.get("market_cap", 0))
            price = float(row.get("price", 0))
            total_debt = float(row.get("total_debt", 0))
            cash = float(row.get("cash", 0))
            working_capital = float(row.get("working_capital", 0))
            share_buybacks = float(row.get("share_buybacks", 0))

            def ratio(numerator: float, denominator: float) -> Optional[float]:
                return _safe_ratio(numerator, denominator)

            eps = ratio(adjusted_net_income, shares)
            book_value_per_share = ratio(total_equity, shares)
            dividends_per_share = ratio(dividends_paid, shares)
            net_debt = total_debt - cash

            yearly[year] = {
                "adjusted_ebitda_margin": ratio(adjusted_ebitda, revenue),
                "return_on_equity": ratio(adjusted_net_income, total_equity),
                "fcf_margin": ratio(normalised_fcf, revenue),
                "return_on_assets": ratio(adjusted_net_income, total_assets),
                "operating_margin": ratio(clean_operating_income, revenue),
                "net_margin": ratio(adjusted_net_income, revenue),
                "cash_conversion_ratio": ratio(operating_cash_flow, revenue),
                "dividend_yield": None
                if dividends_per_share is None
                else ratio(dividends_per_share, price),
                "pe_ratio": None if eps in (None, 0) else ratio(price, eps),
                "pb_ratio": None
                if book_value_per_share in (None, 0)
                else ratio(price, book_value_per_share),
                "ev_to_adjusted_ebitda": ratio(enterprise_value, adjusted_ebitda),
                "net_debt_to_ebitda": ratio(net_debt, adjusted_ebitda),
                "working_capital_turnover": ratio(revenue, working_capital),
                "buyback_intensity": ratio(share_buybacks, market_cap),
            }
        return yearly
    def refresh_metrics(self, *, force: bool = False) -> None:
        financials = self._ensure_financials(force=force)
        if financials.empty:
            return

        now = datetime.now(timezone.utc)
        existing_alert_keys = {
            (alert.ticker, alert.metric, alert.message)
            for alert in database.fetch_active_alerts(self.settings.database_path)
        }

        for ticker, company_frame in financials.groupby("ticker"):
            metrics_store: Dict[str, MetricComputation] = {}
            for definition in METRIC_DEFINITIONS:
                computation = definition.calculator(company_frame)
                metrics_store[definition.name] = computation
                database.record_metric_result(
                    self.settings.database_path,
                    database.MetricRecord(
                        ticker=ticker,
                        metric=definition.name,
                        period=computation.period,
                        value=computation.value,
                        phase=definition.phase,
                        methodology=computation.methodology,
                        calculated_at=now,
                    ),
                )
            self._emit_alerts(ticker, company_frame, metrics_store, now, existing_alert_keys)
            self._record_yearly_ratios(ticker, company_frame, now)

    def _emit_alerts(
        self,
        ticker: str,
        company_frame: pd.DataFrame,
        metrics_store: Dict[str, MetricComputation],
        timestamp: datetime,
        existing_alert_keys: set[tuple[str, str, str]],
    ) -> None:
        alerts: List[database.Alert] = []

        revenue_cagr = metrics_store.get("revenue_cagr_3y")
        if revenue_cagr and revenue_cagr.value is not None and revenue_cagr.value < 0:
            severity = "high" if revenue_cagr.value < -0.05 else "medium"
            message = f"Revenue CAGR over 3 years is {revenue_cagr.value:.1%}."
            key = (ticker, "revenue_cagr_3y", message)
            if key not in existing_alert_keys:
                alerts.append(
                    database.Alert(
                        ticker=ticker,
                        metric="revenue_cagr_3y",
                        severity=severity,
                        message=message,
                        created_at=timestamp,
                    )
                )
                existing_alert_keys.add(key)

        roe = metrics_store.get("return_on_equity")
        if roe and roe.value is not None and roe.value < 0.08:
            message = f"Return on equity has fallen to {roe.value:.1%}."
            key = (ticker, "return_on_equity", message)
            if key not in existing_alert_keys:
                alerts.append(
                    database.Alert(
                        ticker=ticker,
                        metric="return_on_equity",
                        severity="medium",
                        message=message,
                        created_at=timestamp,
                    )
                )
                existing_alert_keys.add(key)

        leverage = metrics_store.get("net_debt_to_ebitda")
        if leverage and leverage.value is not None and leverage.value > 3:
            message = f"Net debt / EBITDA is elevated at {leverage.value:.2f}x."
            key = (ticker, "net_debt_to_ebitda", message)
            if key not in existing_alert_keys:
                alerts.append(
                    database.Alert(
                        ticker=ticker,
                        metric="net_debt_to_ebitda",
                        severity="high",
                        message=message,
                        created_at=timestamp,
                    )
                )
                existing_alert_keys.add(key)

        tsr = metrics_store.get("tsr_3y")
        if tsr and tsr.value is not None and tsr.value < 0:
            message = f"Three-year TSR is negative at {tsr.value:.1%}."
            key = (ticker, "tsr_3y", message)
            if key not in existing_alert_keys:
                alerts.append(
                    database.Alert(
                        ticker=ticker,
                        metric="tsr_3y",
                        severity="medium",
                        message=message,
                        created_at=timestamp,
                    )
                )
                existing_alert_keys.add(key)

        for alert in alerts:
            database.record_alert(self.settings.database_path, alert)

    def compare_metrics(
        self,
        tickers: Sequence[str],
        *,
        phase: Optional[str] = None,
        metrics: Optional[Sequence[str]] = None,
    ) -> tuple[List[MetricDefinition], Dict[str, Dict[str, database.MetricRecord]]]:
        """Return metric definitions and records for benchmarking."""

        tickers = [ticker.upper() for ticker in tickers]
        if metrics:
            definitions: List[MetricDefinition] = []
            for name in metrics:
                definition = METRIC_DEFINITIONS_BY_NAME.get(name)
                if not definition:
                    raise ValueError(f"Unknown metric: {name}")
                definitions.append(definition)
        elif phase:
            phase_key = phase.lower()
            definitions = METRIC_DEFINITIONS_BY_PHASE.get(phase_key)
            if definitions is None:
                raise ValueError(f"Unknown phase: {phase}")
        else:
            definitions = METRIC_DEFINITIONS

        results: Dict[str, Dict[str, database.MetricRecord]] = {}
        for ticker in tickers:
            records = self.get_metrics(ticker, phase=phase)
            results[ticker] = {record.metric: record for record in records}
        return definitions, results

    def get_metrics(
        self,
        ticker: str,
        *,
        phase: Optional[str] = None,
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
    ) -> List[database.MetricRecord]:
        results = database.fetch_metric_results(
            self.settings.database_path,
            ticker,
            phase=phase,
        )
        if not results:
            self.refresh_metrics()
            results = database.fetch_metric_results(
                self.settings.database_path,
                ticker,
                phase=phase,
            )
        if not results:
            self._load_live_financials(ticker)
            self.refresh_metrics(force=True)
            results = database.fetch_metric_results(
                self.settings.database_path,
                ticker,
                phase=phase,
            )

        if period_filters:
            results = [
                record
                for record in results
                if self._record_matches_period_filters(record, period_filters)
            ]
        return results


    @staticmethod
    def _period_span(period: str) -> tuple[int, int]:
        if not period:
            return (0, 0)
        cleaned = period.upper().replace("FY", "")
        parts = [p for p in cleaned.split("-") if p]
        try:
            start = int(parts[0])
        except (IndexError, ValueError):
            return (0, 0)
        if len(parts) == 1:
            return (start, start)
        try:
            end = int(parts[1])
        except ValueError:
            end = start
        if end < start:
            start, end = end, start
        return (start, end)

    def _record_matches_period_filters(
        self,
        record: database.MetricRecord,
        period_filters: Sequence[tuple[int, int]],
    ) -> bool:
        start, end = self._period_span(record.period)
        if start == 0 and end == 0:
            return True
        for filter_start, filter_end in period_filters:
            if filter_end >= start and filter_start <= end:
                return True
        return False


    def financial_facts(
        self,
        ticker: str,
        *,
        fiscal_year: Optional[int] = None,
        metric: Optional[str] = None,
        limit: int = 25,
    ) -> List[database.FinancialFact]:
        return database.fetch_financial_facts(
            self.settings.database_path,
            ticker=ticker,
            metric=metric,
            fiscal_year=fiscal_year,
            limit=limit,
        )

    def audit_events(
        self,
        ticker: str,
        *,
        fiscal_year: Optional[int] = None,
        limit: int = 20,
    ) -> List[database.AuditEvent]:
        return database.fetch_audit_events_for_ticker(
            self.settings.database_path,
            ticker=ticker,
            fiscal_year=fiscal_year,
            limit=limit,
        )

    def company_profile(self, ticker: str) -> Optional[Dict[str, object]]:
        financials = self._ensure_financials()
        company_rows = financials[financials["ticker"] == ticker]
        if company_rows.empty:
            self._load_live_financials(ticker)
            financials = self._ensure_financials(force=True)
            company_rows = financials[financials["ticker"] == ticker]
            if company_rows.empty:
                return None
        latest = company_rows.iloc[-1]
        sector_code = latest.get("sector_code")
        sector = SECTOR_LABEL_MAP.get(sector_code, "Unknown") if sector_code is not None else "Unknown"
        return {
            "ticker": ticker,
            "company_name": latest["company_name"],
            "sector": sector,
            "years": (int(company_rows["fiscal_year"].min()), int(company_rows["fiscal_year"].max())),
        }

    def generate_summary(self, ticker: str) -> str:
        profile = self.company_profile(ticker)
        if not profile:
            try:
                self._load_live_financials(ticker)
            except RuntimeError as exc:
                return str(exc)
            profile = self.company_profile(ticker)
            if not profile:
                return f"No financial data available for {ticker}."

        metrics = {record.metric: record for record in self.get_metrics(ticker)}

        def fmt(metric_name: str, default: str = "n/a") -> str:
            record = metrics.get(metric_name)
            if not record or record.value is None:
                return default
            if metric_name in {"revenue_cagr_3y", "eps_cagr_3y", "adjusted_ebitda_margin", "return_on_equity", "fcf_margin", "return_on_assets", "operating_margin", "net_margin", "cash_conversion_ratio", "tsr_3y", "dividend_yield"}:
                return f"{record.value:.1%}"
            if metric_name in {"net_debt_to_ebitda", "ev_to_adjusted_ebitda", "peg_ratio", "working_capital_turnover", "buyback_intensity", "pe_ratio", "pb_ratio"}:
                return f"{record.value:.2f}"
            return f"{record.value:,.0f}"

        lines = [
            f"{profile['ticker']} | {profile['company_name']} ({profile['sector']})",
            f"Coverage: FY{profile['years'][0]}–FY{profile['years'][1]}",
            f"Revenue CAGR (3y): {fmt('revenue_cagr_3y')}  |  EPS CAGR (3y): {fmt('eps_cagr_3y')}",
            f"Adj. EBITDA Margin: {fmt('adjusted_ebitda_margin')}  |  ROE: {fmt('return_on_equity')}  |  FCF Margin: {fmt('fcf_margin')}",
            f"TSR (3y): {fmt('tsr_3y')}  |  Dividend Yield: {fmt('dividend_yield')}  |  P/E: {fmt('pe_ratio')}",
            f"Net Debt / EBITDA: {fmt('net_debt_to_ebitda')}  |  EV/EBITDA: {fmt('ev_to_adjusted_ebitda')}  |  PEG: {fmt('peg_ratio')}",
        ]
        return "\n".join(lines)

    def run_scenario(
        self,
        ticker: str,
        *,
        scenario_name: str,
        revenue_growth_delta: float = 0.0,
        ebitda_margin_delta: float = 0.0,
        multiple_delta: float = 0.0,
    ) -> ScenarioSummary:
        financials = self._ensure_financials()
        company_rows = financials[financials["ticker"] == ticker]
        if company_rows.empty:
            raise ValueError(f"No financial data available for ticker {ticker}.")
        latest = company_rows.iloc[-1]

        base_revenue = float(latest["revenue"])
        projected_revenue = base_revenue * (1 + revenue_growth_delta)

        base_margin = _safe_ratio(float(latest["adjusted_ebitda"]), base_revenue) or 0.0
        projected_margin = max(base_margin + ebitda_margin_delta, 0.0)
        projected_ebitda = projected_revenue * projected_margin

        base_net_margin = _safe_ratio(float(latest["adjusted_net_income"]), base_revenue) or 0.0
        projected_net_income = projected_revenue * max(base_net_margin + 0.4 * ebitda_margin_delta, 0.0)

        shares = float(latest["shares_outstanding"]) or 1.0
        projected_eps = projected_net_income / shares

        base_eps = _safe_ratio(float(latest["adjusted_net_income"]), shares)
        base_price = float(latest["price"])
        base_pe = _safe_ratio(base_price, base_eps) if base_eps else None
        projected_pe = base_pe * (1 + multiple_delta) if base_pe is not None else None
        target_price = projected_eps * projected_pe if projected_pe is not None else base_price

        dividends_per_share = _safe_ratio(float(latest["dividends_paid"]), shares) or 0.0
        implied_total_return = _safe_ratio(target_price + dividends_per_share - base_price, base_price) or 0.0

        assumptions = {
            "revenue_growth_delta": revenue_growth_delta,
            "ebitda_margin_delta": ebitda_margin_delta,
            "multiple_delta": multiple_delta,
        }
        metrics = {
            "projected_revenue": projected_revenue,
            "projected_adjusted_ebitda": projected_ebitda,
            "projected_net_income": projected_net_income,
            "projected_eps": projected_eps,
            "target_price": target_price,
            "implied_total_return": implied_total_return,
        }

        timestamp = datetime.now(timezone.utc)
        for metric_name, value in metrics.items():
            database.record_scenario_result(
                self.settings.database_path,
                database.ScenarioResult(
                    ticker=ticker,
                    scenario_name=scenario_name,
                    assumptions=assumptions,
                    metric=metric_name,
                    value=float(value),
                    created_at=timestamp,
                ),
            )

        database.record_audit_event(
            self.settings.database_path,
            database.AuditEvent(
                event_type="scenario",
                entity_id=f"{ticker}:{scenario_name}",
                details=(
                    f"Scenario '{scenario_name}' with revenue delta {revenue_growth_delta:.1%}, "
                    f"margin delta {ebitda_margin_delta:.1%}, multiple delta {multiple_delta:.1%}."
                ),
                created_at=timestamp,
                created_by="analytics-engine",
            ),
        )

        base_margin_display = f"{base_margin:.1%}" if base_margin else "n/a"
        projected_margin_display = f"{projected_margin:.1%}"
        narrative = (
            f"Applying the '{scenario_name}' case, revenue shifts to {projected_revenue:,.0f} "
            f"({revenue_growth_delta:+.1%} vs. base). Adjusted EBITDA margin moves from "
            f"{base_margin_display} to {projected_margin_display}, driving EBITDA to "
            f"{projected_ebitda:,.0f}. Normalised net income steps to {projected_net_income:,.0f}, "
            f"implying EPS of {projected_eps:.2f}. With valuation multiples adjusted by "
            f"{multiple_delta:+.1%}, the implied price target is {target_price:.2f} and total "
            f"return (incl. dividends) {implied_total_return:.1%}."
        )

        return ScenarioSummary(
            ticker=ticker,
            scenario_name=scenario_name,
            metrics=metrics,
            assumptions=assumptions,
            narrative=narrative,
        )

    def active_alerts(self) -> List[database.Alert]:
        return database.fetch_active_alerts(self.settings.database_path)

    def recent_audit_events(self, limit: int = 20) -> List[database.AuditEvent]:
        return database.fetch_recent_audit_events(self.settings.database_path, limit=limit)

    def list_companies(self) -> List[str]:
        financials = self._ensure_financials()
        if financials.empty:
            return []
        return sorted(financials["ticker"].unique().tolist())
