"""KPI backfill pipeline orchestrating SEC facts, derived metrics, and external data."""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # Optional dependency for dividend and price history helpers
    import pandas as pd  # type: ignore[import]
except ImportError:  # pragma: no cover - lightweight environments
    pd = None  # type: ignore[assignment]

from . import imf_proxy
from .backfill_policy import POLICY, Rule, register_rules
from .database import (
    Database,
    FinancialFactRecord,
    KpiValueRecord,
    MetricRecord,
    replace_metric_snapshots,
)
from .external_data import stooq_last_close, yahoo_snapshot

LOGGER = logging.getLogger(__name__)

ComputationResult = Tuple[Optional[float], str, str, str, Optional[str]]

_SNAPSHOT_CACHE: Dict[str, Dict[str, Any]] = {}

PERCENT_METRICS = {
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

PRICE_BASED_METRICS = {
    "pe_ratio",
    "ev_ebitda",
    "pb_ratio",
    "peg_ratio",
    "dividend_yield",
    "tsr",
    "share_buyback_intensity",
}


def reset_external_snapshot_cache() -> None:
    """Clear memoised external snapshot cache (per refresh invocation)."""
    _SNAPSHOT_CACHE.clear()


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Protect division operations from zero or missing values."""
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return None


def _calc_cagr(start: Optional[float], end: Optional[float], periods: int) -> Optional[float]:
    """Return the compound annual growth rate given two endpoints."""
    if start is None or end is None or periods <= 0:
        return None
    if start <= 0:
        return None
    try:
        result = (end / start) ** (1 / periods) - 1
    except (ZeroDivisionError, ValueError):
        return None
    if isinstance(result, complex):
        return None
    if not math.isfinite(result):
        return None
    return float(result)


def _infer_year_from_period(period: Optional[str]) -> Optional[int]:
    """Extract the fiscal year from strings like 'FY2023'."""
    if not period:
        return None
    period = period.strip().upper()
    if period.startswith("FY") and period[2:].isdigit():
        return int(period[2:])
    if len(period) == 4 and period.isdigit():
        return int(period)
    return None


def _record_year(record: MetricRecord) -> Optional[int]:
    """Resolve the most appropriate fiscal year for a metric snapshot."""
    return record.end_year or record.start_year or _infer_year_from_period(record.period)


def _join_sources(*sources: str) -> str:
    """Combine multiple source labels into a canonical string."""
    labels = [label for label in sources if label]
    if not labels:
        return ""
    unique: List[str] = []
    for label in labels:
        if label not in unique:
            unique.append(label)
    return "/".join(unique)


class Context:
    """Execution context supplied to backfill compute rules."""

    def __init__(
        self,
        db: Database,
        ticker: str,
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None,
        *,
        allow_external: bool = True,
    ) -> None:
        self.db = db
        self.ticker = ticker.upper()
        self.fiscal_year = fiscal_year
        self.fiscal_quarter = fiscal_quarter
        self.allow_external = allow_external
        self._now = datetime.now(timezone.utc)

        self._metric_records: Dict[str, List[MetricRecord]] = defaultdict(list)
        for record in db.fetch_metric_snapshots(self.ticker):
            self._metric_records[record.metric].append(record)
        for records in self._metric_records.values():
            records.sort(
                key=lambda rec: (
                    rec.updated_at or datetime(1970, 1, 1, tzinfo=timezone.utc),
                    _record_year(rec) or 0,
                ),
                reverse=True,
            )

        existing = db.fetch_kpi_values(
            self.ticker,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
        )
        self._kpi_existing: Dict[str, KpiValueRecord] = {row.metric_id: row for row in existing}
        self._computed_values: Dict[str, float] = {}
        self._computed_records: Dict[str, Dict[str, Any]] = {}
        self._warnings: Dict[str, List[str]] = defaultdict(list)

        self._fact_cache: Dict[str, List[FinancialFactRecord]] = {}
        self._external_snapshot: Optional[Dict[str, Any]] = None
        self._quote_cache: Optional[Dict[str, Any]] = None
        self._imf_sector: Optional[str] = None

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------
    def metric(
        self,
        name: str,
        year: Optional[int] = None,
        *,
        include_kpi: bool = True,
    ) -> Optional[float]:
        """Return the best metric snapshot for ``name`` and fiscal year."""
        target_year = year if year is not None else self.fiscal_year
        if name in self._computed_values:
            return self._computed_values[name]
        if include_kpi:
            record = self._kpi_existing.get(name)
            if record and record.value is not None and record.fiscal_year == target_year:
                return float(record.value)

        records = self._metric_records.get(name, [])
        for record in records:
            rec_year = _record_year(record)
            if rec_year == target_year and record.value is not None:
                return float(record.value)
        # fallback to window overlap (e.g., CAGR spanning multiple years)
        for record in records:
            if record.value is None:
                continue
            start = record.start_year
            end = record.end_year or _infer_year_from_period(record.period)
            if start is not None and end is not None and start <= target_year <= end:
                return float(record.value)
        return None

    def metric_series(
        self,
        name: str,
        *,
        upto: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[int, float]]:
        """Return a sorted list of (year, value) pairs for the metric."""
        upto = upto if upto is not None else self.fiscal_year
        records = self._metric_records.get(name, [])
        latest_per_year: Dict[int, Tuple[float, datetime]] = {}
        for record in records:
            year = _record_year(record)
            if year is None or year > upto or record.value is None:
                continue
            stamp = record.updated_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
            existing = latest_per_year.get(year)
            if existing is None or stamp > existing[1]:
                latest_per_year[year] = (float(record.value), stamp)
        series = sorted((year, value_stamp[0]) for year, value_stamp in latest_per_year.items())
        if limit:
            series = series[-limit:]
        return series

    def _get_fact_records(self, metric: str) -> List[FinancialFactRecord]:
        if metric not in self._fact_cache:
            self._fact_cache[metric] = self.db.fetch_financial_facts(self.ticker, metric=metric)
        return self._fact_cache[metric]

    def fact(
        self,
        metric: str,
        year: Optional[int] = None,
        *,
        fiscal_period: Optional[str] = None,
    ) -> Optional[float]:
        """Return the latest SEC fact for the requested metric/year."""
        target_year = year if year is not None else self.fiscal_year
        records = self._get_fact_records(metric)
        best_value: Optional[float] = None
        best_stamp: Optional[datetime] = None
        for record in records:
            if target_year is not None and record.fiscal_year != target_year:
                continue
            if fiscal_period and (record.fiscal_period or "").upper() != fiscal_period.upper():
                continue
            if record.value is None:
                continue
            stamp = record.period_end or record.ingested_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
            if best_stamp is None or stamp > best_stamp:
                best_stamp = stamp
                best_value = float(record.value)
        if best_value is not None:
            return best_value
        # If fiscal period unspecified, fall back to any available record for the year
        if fiscal_period is None:
            for record in records:
                if target_year is not None and record.fiscal_year != target_year:
                    continue
                if record.value is None:
                    continue
                return float(record.value)
        return None

    def sum_quarterly(self, metric: str, year: int) -> Optional[float]:
        """Sum quarterly SEC facts when annual data is unavailable."""
        records = self._get_fact_records(metric)
        quarters = {"Q1", "Q2", "Q3", "Q4"}
        values: List[float] = []
        for record in records:
            if record.fiscal_year != year:
                continue
            if (record.fiscal_period or "").upper() not in quarters:
                continue
            if record.value is None:
                continue
            values.append(float(record.value))
        if not values:
            return None
        return float(sum(values))

    def value_with_fallback(
        self,
        metric: str,
        year: Optional[int],
        *,
        aliases: Optional[Sequence[str]] = None,
        allow_quarterly: bool = False,
        warn_metric: Optional[str] = None,
        return_year: bool = False,
        fallback_to_prior: bool = True,
        max_lookback: int = 5,
    ) -> Tuple[Optional[float], str] | Tuple[Optional[float], str, Optional[int]]:
        """Return value with fallback lookups and provenance tag."""
        names = [metric]
        if aliases:
            names.extend(aliases)
        target_year = year if year is not None else self.fiscal_year
        candidate_years: List[Optional[int]] = [target_year]
        if fallback_to_prior and target_year is not None:
            for offset in range(1, max_lookback + 1):
                candidate = target_year - offset
                if candidate < 1900:
                    break
                candidate_years.append(candidate)

        def _result(
            value: Optional[float],
            ref: str,
            year_used: Optional[int],
            fell_back: bool,
        ) -> Tuple[Optional[float], str] | Tuple[Optional[float], str, Optional[int]]:
            if value is None:
                if return_year:
                    return None, "", None
                return None, ""
            if fell_back and warn_metric and year_used is not None and target_year is not None:
                self.add_warning(
                    warn_metric,
                    f"Using FY{year_used} data for requested FY{target_year}",
                )
            if return_year:
                return value, ref, year_used
            return value, ref

        for candidate_year in candidate_years:
            fell_back = candidate_year is not None and target_year is not None and candidate_year != target_year
            for name in names:
                value = self.metric(name, candidate_year, include_kpi=False)
                if value is not None:
                    return _result(value, f"{name}.metric", candidate_year, fell_back)
            for name in names:
                value = self.fact(name, candidate_year, fiscal_period="FY")
                if value is not None:
                    return _result(value, f"{name}.fact", candidate_year, fell_back)
            if allow_quarterly and candidate_year is not None:
                aggregated = self.sum_quarterly(metric, candidate_year)
                if aggregated is not None:
                    metric_id = warn_metric or metric
                    self.add_warning(metric_id, f"Summed quarterly {metric} for FY{candidate_year}")
                    return _result(aggregated, f"{metric}.quarterly", candidate_year, fell_back)
        if return_year:
            return None, "", None
        return None, ""

    def imf_sector(self) -> str:
        """Return the sector associated with the current ticker (falls back to GLOBAL)."""
        if self._imf_sector is None:
            self._imf_sector = imf_proxy.sector_for_ticker(self.ticker) or "GLOBAL"
        return self._imf_sector

    def _imf_fallback(self, metric_id: str) -> Optional[Tuple[float, str]]:
        """Return an IMF-derived proxy for the requested metric, if available."""
        value = imf_proxy.metric_for(self.ticker, metric_id)
        if value is None:
            return None
        sector = self.imf_sector()
        self.add_warning(metric_id, f"Used IMF sector proxy ({sector})")
        try:
            return float(value), sector
        except (TypeError, ValueError):
            LOGGER.debug("IMF proxy for %s/%s is not numeric (%s)", self.ticker, metric_id, value)
            return None

    def _imf_result(self, metric_id: str) -> Optional[ComputationResult]:
        fallback = self._imf_fallback(metric_id)
        if fallback is None:
            return None
        value, sector = fallback
        warning = self._pop_warning(metric_id)
        return (
            value,
            "proxy",
            "IMF",
            f"imf_sector::{sector}",
            warning,
        )

    # ------------------------------------------------------------------
    # Warning management & computed results
    # ------------------------------------------------------------------
    def add_warning(self, metric_id: str, message: str) -> None:
        """Record a warning message to surface alongside KPI values."""
        if not message:
            return
        self._warnings[metric_id].append(message)

    def _pop_warning(self, metric_id: str) -> Optional[str]:
        entries = self._warnings.pop(metric_id, [])
        if not entries:
            return None
        # De-duplicate while preserving order
        seen: List[str] = []
        for entry in entries:
            if entry not in seen:
                seen.append(entry)
        return "; ".join(seen)

    def register_result(
        self,
        metric_id: str,
        value: float,
        *,
        method: str,
        source: str,
        source_ref: str,
        warning: Optional[str],
    ) -> None:
        """Register a computed KPI so downstream rules can reuse it."""
        self._computed_values[metric_id] = float(value)
        self._computed_records[metric_id] = {
            "value": float(value),
            "method": method,
            "source": source,
            "source_ref": source_ref,
            "warning": warning,
        }

    def kpi_record(self, metric_id: str) -> Optional[KpiValueRecord]:
        """Return an existing persisted KPI value if available."""
        if metric_id in self._computed_records:
            payload = self._computed_records[metric_id]
            return KpiValueRecord(
                ticker=self.ticker,
                fiscal_year=self.fiscal_year,
                fiscal_quarter=self.fiscal_quarter,
                metric_id=metric_id,
                value=payload["value"],
                unit=None,
                method=payload["method"],
                source=payload["source"],
                source_ref=payload["source_ref"],
                warning=payload["warning"],
                updated_at=self._now,
            )
        return self._kpi_existing.get(metric_id)

    def get_kpi(self, metric_id: str) -> Optional[float]:
        record = self.kpi_record(metric_id)
        if record and record.value is not None:
            return float(record.value)
        return None

    # ------------------------------------------------------------------
    # External data access
    # ------------------------------------------------------------------
    def latest_quote(self) -> Optional[Dict[str, Any]]:
        if self._quote_cache is None:
            self._quote_cache = self.db.fetch_latest_quote(self.ticker) or {}
        return self._quote_cache or None

    def get_ext_snapshot(self) -> Dict[str, Any]:
        if self._external_snapshot is not None:
            return self._external_snapshot
        cached = _SNAPSHOT_CACHE.get(self.ticker)
        if cached is not None:
            self._external_snapshot = cached
            return cached
        if not self.allow_external:
            snapshot = {"price": None, "price_source": "", "stooq_price": None}
            self._external_snapshot = snapshot
            return snapshot
        snapshot: Dict[str, Any] = {}
        try:
            snapshot = yahoo_snapshot(self.ticker) or {}
        except Exception:  # pragma: no cover - network dependent
            LOGGER.exception("Yahoo snapshot failed for %s", self.ticker)
            snapshot = {}
        price_source = ""
        price = snapshot.get("price")
        if isinstance(price, (int, float)):
            price = float(price)
            price_source = "Yahoo"
        else:
            price = None
        stooq_price = None
        if price is None:
            try:
                stooq_price = stooq_last_close(self.ticker, self._now)
            except Exception:  # pragma: no cover - network dependent
                LOGGER.exception("Stooq fetch failed for %s", self.ticker)
            if stooq_price is not None:
                price = stooq_price
                price_source = "Stooq"
        snapshot["price"] = price
        snapshot["price_source"] = price_source
        snapshot["stooq_price"] = stooq_price
        _SNAPSHOT_CACHE[self.ticker] = snapshot
        self._external_snapshot = snapshot
        return snapshot

    # ------------------------------------------------------------------
    # Derived fact helpers
    # ------------------------------------------------------------------
    def latest_price(self) -> Optional[float]:
        quote = self.latest_quote()
        if quote:
            price = quote.get("price")
            if isinstance(price, (int, float)):
                return float(price)
        price_metric = self.metric("price", self.fiscal_year)
        if price_metric is not None:
            return price_metric
        snapshot = self.get_ext_snapshot()
        price = snapshot.get("price")
        if isinstance(price, (int, float)):
            return float(price)
        return None

    def shares_outstanding(self, year: Optional[int] = None) -> Tuple[Optional[float], str]:
        return self.value_with_fallback(
            "shares_outstanding",
            year,
            aliases=["weighted_avg_diluted_shares"],
            allow_quarterly=False,
            warn_metric=None,
        )

    def market_cap(self, year: Optional[int] = None) -> Tuple[Optional[float], str]:
        value = self.metric("market_cap", year)
        if value is not None:
            return value, "market_cap.metric"
        quote = self.latest_quote()
        if quote:
            raw = quote.get("raw") or {}
            market_cap = raw.get("marketCap")
            if isinstance(market_cap, (int, float)):
                return float(market_cap), "market_cap.quote"
        snapshot = self.get_ext_snapshot()
        mc = snapshot.get("market_cap")
        if isinstance(mc, (int, float)):
            return float(mc), "market_cap.yahoo"
        price = self.latest_price()
        shares, shares_ref = self.shares_outstanding(year)
        if price is not None and shares is not None:
            return price * shares, f"price*shares[{shares_ref}]"
        return None, ""

    def enterprise_value(self, year: Optional[int] = None) -> Tuple[Optional[float], str]:
        quote = self.latest_quote()
        if quote:
            raw = quote.get("raw") or {}
            ev = raw.get("enterpriseValue")
            if isinstance(ev, (int, float)):
                return float(ev), "enterprise_value.quote"
        snapshot = self.get_ext_snapshot()
        ev = snapshot.get("ev")
        if isinstance(ev, (int, float)):
            return float(ev), "enterprise_value.yahoo"
        market_cap, mc_ref = self.market_cap(year)
        total_debt, debt_ref = self.total_debt(year)
        cash, cash_ref = self.cash_balance(year)
        if market_cap is None:
            return None, ""
        debt = total_debt or 0.0
        cash = cash or 0.0
        ref = "+".join(filter(None, [mc_ref, debt_ref, cash_ref]))
        return market_cap + debt - cash, f"market_cap+debt-cash[{ref}]"

    def total_debt(self, year: Optional[int]) -> Tuple[Optional[float], str]:
        targets = [
            ("long_term_debt", False),
            ("long_term_debt_current", False),
            ("short_term_debt", False),
        ]
        parts: List[str] = []
        values: List[float] = []
        for metric, allow_quarterly in targets:
            value, ref = self.value_with_fallback(
                metric,
                year,
                allow_quarterly=allow_quarterly,
                warn_metric="debt_to_equity",
            )
            if value is not None:
                parts.append(ref)
                values.append(value)
        if values:
            return float(sum(values)), "+".join(parts)
        fallback, ref = self.value_with_fallback("total_debt", year)
        if fallback is not None:
            return fallback, ref
        liabilities, ref = self.value_with_fallback("total_liabilities", year)
        if liabilities is not None:
            self.add_warning("debt_to_equity", "Using total liabilities as proxy for debt")
            return liabilities, ref
        return None, ""

    def cash_balance(self, year: Optional[int]) -> Tuple[Optional[float], str]:
        return self.value_with_fallback(
            "cash_and_cash_equivalents",
            year,
            aliases=["cash"],
            allow_quarterly=False,
        )

    def dividends_per_share(self, year: Optional[int]) -> Tuple[Optional[float], str]:
        value, ref = self.value_with_fallback(
            "dividends_per_share",
            year,
            allow_quarterly=False,
            warn_metric="dividend_yield",
        )
        if value is not None:
            return value, ref
        total_dividends, div_ref = self.value_with_fallback(
            "dividends_paid",
            year,
            allow_quarterly=False,
            warn_metric="dividend_yield",
        )
        shares, shares_ref = self.shares_outstanding(year)
        if total_dividends is not None and shares not in (None, 0):
            self.add_warning("dividend_yield", "Derived DPS from dividends paid and share count")
            return abs(total_dividends) / shares, f"dividends_paid[{div_ref}]/shares[{shares_ref}]"
        snapshot = self.get_ext_snapshot()
        dividends = snapshot.get("dividends")
        if pd is not None and isinstance(dividends, pd.Series) and not dividends.empty:
            trailing = dividends.tail(4).sum()
            if float(trailing) != 0.0:
                self.add_warning("dividend_yield", "Used Yahoo dividend history for trailing DPS")
                return float(trailing), "dividends.yahoo"
        return None, ""

    def eps_value(
        self,
        year: Optional[int],
        *,
        warn_metric: str,
        return_year: bool = False,
    ) -> Tuple[Optional[float], str] | Tuple[Optional[float], str, Optional[int]]:
        eps_value = self.value_with_fallback(
            "eps_diluted",
            year,
            aliases=["eps_basic"],
            allow_quarterly=False,
            warn_metric=warn_metric,
            return_year=True,
        )
        eps, ref, eps_year = eps_value
        if eps is not None:
            if return_year:
                return eps, ref, eps_year
            return eps, ref
        net_income_value = self.value_with_fallback(
            "net_income",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
            return_year=True,
        )
        net_income, ni_ref, ni_year = net_income_value
        shares, shares_ref = self.shares_outstanding(year)
        if net_income is not None and shares not in (None, 0):
            actual_year = ni_year if ni_year is not None else year
            self.add_warning(
                warn_metric,
                f"Derived EPS from net income and shares for FY{actual_year}",
            )
            value = net_income / shares
            if return_year:
                return value, f"net_income[{ni_ref}]/shares[{shares_ref}]", actual_year
            return value, f"net_income[{ni_ref}]/shares[{shares_ref}]"
        snapshot = self.get_ext_snapshot()
        raw_info = snapshot.get("raw") or {}
        trailing_eps = raw_info.get("trailingEps")
        if isinstance(trailing_eps, (int, float)) and year == self.fiscal_year:
            self.add_warning(warn_metric, "Used Yahoo trailing EPS as fallback")
            if return_year:
                return float(trailing_eps), "eps.yahoo.trailing", year
            return float(trailing_eps), "eps.yahoo.trailing"
        if return_year:
            return None, "", None
        return None, ""

    def ebitda_value(
        self,
        year: Optional[int],
        warn_metric: str,
        *,
        return_year: bool = False,
        fallback_to_prior: bool = True,
    ) -> Tuple[Optional[float], str] | Tuple[Optional[float], str, Optional[int]]:
        ebitda_result = self.value_with_fallback(
            "ebitda",
            year,
            aliases=["adjusted_ebitda"],
            allow_quarterly=False,
            warn_metric=warn_metric,
            return_year=True,
            fallback_to_prior=fallback_to_prior,
        )
        ebitda, ref, e_year = ebitda_result
        if ebitda is not None:
            if return_year:
                return ebitda, ref, e_year
            return ebitda, ref
        operating_income_result = self.value_with_fallback(
            "operating_income",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
            return_year=True,
            fallback_to_prior=fallback_to_prior,
        )
        operating_income, op_ref, op_year = operating_income_result
        depreciation_result = self.value_with_fallback(
            "depreciation_and_amortization",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
            return_year=True,
            fallback_to_prior=fallback_to_prior,
        )
        depreciation, dep_ref, dep_year = depreciation_result
        if operating_income is not None:
            depreciation = depreciation or 0.0
            actual_year = op_year if op_year is not None else year
            self.add_warning(warn_metric, "Approximated EBITDA via operating income + D&A")
            value = operating_income + depreciation
            if return_year:
                return value, f"operating_income[{op_ref}]+depr[{dep_ref}]", actual_year
            return value, f"operating_income[{op_ref}]+depr[{dep_ref}]"
        profit_loss_result = self.value_with_fallback(
            "profit_loss",
            year,
            return_year=True,
            fallback_to_prior=fallback_to_prior,
        )
        profit_loss, pl_ref, pl_year = profit_loss_result
        if profit_loss is not None and depreciation is not None:
            actual_year = pl_year if pl_year is not None else year
            self.add_warning(warn_metric, "Used profit loss + D&A for EBITDA approximation")
            value = profit_loss + depreciation
            if return_year:
                return value, f"profit_loss[{pl_ref}]+depr[{dep_ref}]", actual_year
            return value, f"profit_loss[{pl_ref}]+depr[{dep_ref}]"
        if return_year:
            return None, "", None
        return None, ""

    def free_cash_flow(self, year: Optional[int], warn_metric: str) -> Tuple[Optional[float], str]:
        value, ref = self.value_with_fallback(
            "free_cash_flow",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        if value is not None:
            return value, ref
        cfo, cfo_ref = self.value_with_fallback(
            "cash_from_operations",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        capex, capex_ref = self.value_with_fallback(
            "capital_expenditures",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        if cfo is not None and capex is not None:
            self.add_warning(warn_metric, "Computed FCF as CFO - CapEx")
            return cfo - capex, f"CFO[{cfo_ref}] - CapEx[{capex_ref}]"
        return None, ""

    def average_balance(self, metric: str, year: int, warn_metric: str) -> Tuple[Optional[float], str]:
        current, current_ref = self.value_with_fallback(
            metric,
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        previous, prev_ref = self.value_with_fallback(
            metric,
            year - 1,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        if current is None or previous is None:
            return None, ""
        ref = f"{metric}[{current_ref}|{prev_ref}]"
        return (current + previous) / 2, ref

    def effective_tax_rate(self, year: int, warn_metric: str) -> Tuple[Optional[float], str]:
        tax_expense, tax_ref = self.value_with_fallback(
            "income_tax_expense",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        if tax_expense is None:
            return None, ""
        net_income, ni_ref = self.value_with_fallback(
            "net_income",
            year,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        pre_tax_income = None
        if net_income is not None:
            pre_tax_income = net_income + tax_expense
        if pre_tax_income in (None, 0):
            default_rate = 0.21
            self.add_warning(warn_metric, "Applied default 21% tax rate")
            return default_rate, "default_rate"
        return tax_expense / pre_tax_income, f"tax[{tax_ref}]/pretax[{ni_ref}]"

    # ------------------------------------------------------------------
    # Metric computations
    # ------------------------------------------------------------------
    def compute_revenue_cagr(self) -> ComputationResult:
        end_year_request = self.fiscal_year
        end_result = self.value_with_fallback(
            "revenue",
            end_year_request,
            allow_quarterly=True,
            warn_metric="revenue_cagr",
            return_year=True,
        )
        end_value, end_ref, end_year_actual = end_result
        if end_value is None:
            warning = self._pop_warning("revenue_cagr") or "Missing revenue for latest fiscal year"
            return (None, "n/a", "", "", warning)

        anchor_year = end_year_actual if end_year_actual is not None else end_year_request

        start_value: Optional[float] = None
        start_ref = ""
        start_year: Optional[int] = None
        if anchor_year is not None:
            for lookback in range(1, 6):
                candidate_year = anchor_year - lookback
                if candidate_year < 1900:
                    break
                value, ref, value_year = self.value_with_fallback(
                    "revenue",
                    candidate_year,
                    allow_quarterly=True,
                    warn_metric="revenue_cagr",
                    return_year=True,
                    fallback_to_prior=False,
                )
                if value is not None:
                    start_year = value_year if value_year is not None else candidate_year
                    start_value = value
                    start_ref = ref
                    break

        if (start_year is None or start_value is None) and anchor_year is not None:
            series = self.metric_series("revenue", upto=anchor_year, limit=2)
            if len(series) >= 2:
                earlier_year, earlier_value = series[-2]
                start_year = earlier_year
                start_value = earlier_value
                start_ref = "revenue.series"
                self.add_warning("revenue_cagr", "Used historical revenue series fallback")

        if start_year is None or start_value is None or anchor_year is None:
            imf_result = self._imf_result("revenue_cagr")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("revenue_cagr") or "Insufficient revenue history for CAGR"
            return (None, "n/a", "", "", warning)

        periods = anchor_year - start_year
        if periods <= 0:
            warning = self._pop_warning("revenue_cagr") or "Unable to compute revenue CAGR"
            return (None, "n/a", "", "", warning)

        value = _calc_cagr(start_value, end_value, periods)
        if value is None:
            imf_result = self._imf_result("revenue_cagr")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("revenue_cagr") or "Unable to compute revenue CAGR"
            return (None, "n/a", "", "", warning)

        source_ref = f"revenue[{start_year}:{start_ref}->{anchor_year}:{end_ref}]"
        warning = self._pop_warning("revenue_cagr")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_eps_cagr(self) -> ComputationResult:
        end_year_request = self.fiscal_year
        end_tuple = self.eps_value(end_year_request, warn_metric="eps_cagr", return_year=True)
        end_value, end_ref, end_year_actual = end_tuple

        start_value: Optional[float] = None
        start_ref = ""
        start_year: Optional[int] = None
        anchor_year = end_year_actual if end_year_actual is not None else end_year_request
        if anchor_year is not None:
            for lookback in range(1, 6):
                candidate_year = anchor_year - lookback
                if candidate_year < 1900:
                    break
                value, ref, value_year = self.eps_value(
                    candidate_year,
                    warn_metric="eps_cagr",
                    return_year=True,
                )
                if value is not None:
                    start_year = value_year if value_year is not None else candidate_year
                    start_value = value
                    start_ref = ref
                    break

        periods: Optional[int] = None
        if start_year is None or start_value is None or end_value is None:
            snapshot = self.get_ext_snapshot()
            raw_info = snapshot.get("raw") or {}
            trailing = raw_info.get("trailingEps")
            forward = raw_info.get("forwardEps")
            if isinstance(trailing, (int, float)) and isinstance(forward, (int, float)):
                base_year = anchor_year if anchor_year is not None else end_year_request
                if base_year is None:
                    warning = self._pop_warning("eps_cagr") or "Insufficient EPS history for CAGR"
                    return (None, "n/a", "", "", warning)
                start_year = base_year - 1
                start_value = float(trailing)
                end_value = float(forward)
                start_ref = "eps.yahoo.trailing"
                end_ref = "eps.yahoo.forward"
                periods = 1
                self.add_warning("eps_cagr", "Used Yahoo analyst EPS for CAGR fallback")
            else:
                warning = self._pop_warning("eps_cagr") or "Insufficient EPS history for CAGR"
                return (None, "n/a", "", "", warning)

        if periods is None:
            if anchor_year is None or start_year is None:
                imf_result = self._imf_result("eps_cagr")
                if imf_result is not None:
                    return imf_result
                warning = self._pop_warning("eps_cagr") or "Unable to compute EPS CAGR"
                return (None, "n/a", "", "", warning)
            periods = anchor_year - start_year

        if periods <= 0 or start_value is None or end_value is None:
            imf_result = self._imf_result("eps_cagr")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("eps_cagr") or "Unable to compute EPS CAGR"
            return (None, "n/a", "", "", warning)

        value = _calc_cagr(start_value, end_value, periods)
        if value is None:
            imf_result = self._imf_result("eps_cagr")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("eps_cagr") or "Unable to compute EPS CAGR"
            return (None, "n/a", "", "", warning)

        end_year_for_ref = anchor_year if anchor_year is not None else end_year_request
        source_ref = f"eps[{start_year}:{start_ref}->{end_year_for_ref}:{end_ref}]"
        warning = self._pop_warning("eps_cagr")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_ebitda_growth(self) -> ComputationResult:
        current_year_request = self.fiscal_year
        current_tuple = self.ebitda_value(
            current_year_request,
            warn_metric="ebitda_growth",
            return_year=True,
        )
        current_value, current_ref, current_year_actual = current_tuple
        if current_value is None:
            imf_result = self._imf_result("ebitda_growth")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("ebitda_growth") or "Missing EBITDA history"
            return (None, "n/a", "", "", warning)

        anchor_year = current_year_actual if current_year_actual is not None else current_year_request
        previous_value: Optional[float] = None
        previous_ref = ""
        previous_year_actual: Optional[int] = None
        if anchor_year is not None:
            for lookback in range(1, 6):
                candidate_year = anchor_year - lookback
                if candidate_year < 1900:
                    break
                prev_tuple = self.ebitda_value(
                    candidate_year,
                    warn_metric="ebitda_growth",
                    return_year=True,
                    fallback_to_prior=False,
                )
                prev_value, prev_ref, prev_year = prev_tuple
                if prev_value is not None:
                    previous_value = prev_value
                    previous_ref = prev_ref
                    previous_year_actual = prev_year if prev_year is not None else candidate_year
                    break

        if previous_value in (None, 0) or previous_year_actual is None or anchor_year is None:
            imf_result = self._imf_result("ebitda_growth")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("ebitda_growth") or "Missing EBITDA history"
            return (None, "n/a", "", "", warning)

        growth = _safe_div(current_value - previous_value, abs(previous_value))
        if growth is None:
            imf_result = self._imf_result("ebitda_growth")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("ebitda_growth") or "Unable to compute EBITDA growth"
            return (None, "n/a", "", "", warning)
        source_ref = f"ebitda[{previous_year_actual}:{previous_ref}->{anchor_year}:{current_ref}]"
        warning = self._pop_warning("ebitda_growth")
        return (growth, "derived", "SEC", source_ref, warning)

    def _margin(
        self,
        numerator_metric: str,
        denominator_metric: str,
        *,
        warn_metric: str,
        numerator_aliases: Optional[Sequence[str]] = None,
        denominator_aliases: Optional[Sequence[str]] = None,
        numerator_custom: Optional[Tuple[Optional[float], str]] = None,
    ) -> Tuple[Optional[float], str, str]:
        year = self.fiscal_year
        if numerator_custom is not None:
            numerator, num_ref = numerator_custom
        else:
            numerator, num_ref = self.value_with_fallback(
                numerator_metric,
                year,
                aliases=numerator_aliases,
                allow_quarterly=False,
                warn_metric=warn_metric,
            )
        denominator, den_ref = self.value_with_fallback(
            denominator_metric,
            year,
            aliases=denominator_aliases,
            allow_quarterly=False,
            warn_metric=warn_metric,
        )
        if numerator is None or denominator in (None, 0):
            return None, "", ""
        value = _safe_div(numerator, denominator)
        if value is None:
            return None, "", ""
        return value, num_ref, den_ref

    def compute_ebitda_margin(self) -> ComputationResult:
        value, num_ref, den_ref = self._margin(
            "ebitda",
            "revenue",
            warn_metric="ebitda_margin",
            numerator_aliases=["adjusted_ebitda"],
        )
        if value is None:
            imf_result = self._imf_result("ebitda_margin")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("ebitda_margin") or "Unable to compute EBITDA margin"
            return (None, "n/a", "", "", warning)
        source_ref = f"ebitda[{num_ref}]/revenue[{den_ref}]"
        warning = self._pop_warning("ebitda_margin")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_operating_margin(self) -> ComputationResult:
        value, num_ref, den_ref = self._margin(
            "operating_income",
            "revenue",
            warn_metric="operating_margin",
        )
        if value is None:
            imf_result = self._imf_result("operating_margin")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("operating_margin") or "Unable to compute operating margin"
            return (None, "n/a", "", "", warning)
        source_ref = f"operating_income[{num_ref}]/revenue[{den_ref}]"
        warning = self._pop_warning("operating_margin")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_net_margin(self) -> ComputationResult:
        value, num_ref, den_ref = self._margin(
            "net_income",
            "revenue",
            warn_metric="net_margin",
        )
        if value is None:
            imf_result = self._imf_result("net_margin")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("net_margin") or "Unable to compute net margin"
            return (None, "n/a", "", "", warning)
        source_ref = f"net_income[{num_ref}]/revenue[{den_ref}]"
        warning = self._pop_warning("net_margin")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_profit_margin(self) -> ComputationResult:
        result = self.compute_net_margin()
        if result[0] is not None:
            # Mirror metadata for clarity
            return (result[0], result[1], result[2], result[3].replace("net_income", "net_income"), result[4])
        return result

    def compute_return_on_assets(self) -> ComputationResult:
        net_income, ni_ref = self.value_with_fallback(
            "net_income",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="return_on_assets",
        )
        average_assets, asset_ref = self.average_balance("total_assets", self.fiscal_year, "return_on_assets")
        if net_income is None or average_assets in (None, 0):
            imf_result = self._imf_result("return_on_assets")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_assets") or "Unable to compute ROA"
            return (None, "n/a", "", "", warning)
        value = _safe_div(net_income, average_assets)
        if value is None:
            imf_result = self._imf_result("return_on_assets")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_assets") or "Unable to compute ROA"
            return (None, "n/a", "", "", warning)
        source_ref = f"net_income[{ni_ref}]/avg_assets[{asset_ref}]"
        warning = self._pop_warning("return_on_assets")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_return_on_equity(self) -> ComputationResult:
        net_income, ni_ref = self.value_with_fallback(
            "net_income",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="return_on_equity",
        )
        average_equity, eq_ref = self.average_balance(
            "shareholders_equity",
            self.fiscal_year,
            "return_on_equity",
        )
        if net_income is None or average_equity in (None, 0):
            imf_result = self._imf_result("return_on_equity")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_equity") or "Unable to compute ROE"
            return (None, "n/a", "", "", warning)
        value = _safe_div(net_income, average_equity)
        if value is None:
            imf_result = self._imf_result("return_on_equity")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_equity") or "Unable to compute ROE"
            return (None, "n/a", "", "", warning)
        source_ref = f"net_income[{ni_ref}]/avg_equity[{eq_ref}]"
        warning = self._pop_warning("return_on_equity")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_return_on_invested_capital(self) -> ComputationResult:
        operating_income, op_ref = self.value_with_fallback(
            "operating_income",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="return_on_invested_capital",
        )
        tax_rate, tax_ref = self.effective_tax_rate(self.fiscal_year, "return_on_invested_capital")
        total_debt, debt_ref = self.total_debt(self.fiscal_year)
        equity, equity_ref = self.value_with_fallback(
            "shareholders_equity",
            self.fiscal_year,
            aliases=["total_equity"],
            allow_quarterly=False,
            warn_metric="return_on_invested_capital",
        )
        cash, cash_ref = self.cash_balance(self.fiscal_year)

        if operating_income is None:
            warning = self._pop_warning("return_on_invested_capital") or "Missing operating income"
            return (None, "n/a", "", "", warning)
        if tax_rate is None:
            self.add_warning("return_on_invested_capital", "Using default tax rate for NOPAT calculation")
            tax_rate = 0.21

        nopat = operating_income * (1 - tax_rate)

        if total_debt is None or equity is None:
            imf_result = self._imf_result("return_on_invested_capital")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_invested_capital") or "Unable to compute invested capital"
            return (None, "n/a", "", "", warning)
        invested_capital = total_debt + equity - (cash or 0.0)
        if invested_capital in (None, 0):
            imf_result = self._imf_result("return_on_invested_capital")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_invested_capital") or "Invested capital unavailable"
            return (None, "n/a", "", "", warning)

        value = _safe_div(nopat, invested_capital)
        if value is None:
            imf_result = self._imf_result("return_on_invested_capital")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("return_on_invested_capital") or "Unable to compute ROIC"
            return (None, "n/a", "", "", warning)

        source_ref = f"NOPAT[{op_ref}|{tax_ref}]/invested_capital[{debt_ref}+{equity_ref}-{cash_ref}]"
        warning = self._pop_warning("return_on_invested_capital")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_free_cash_flow_margin(self) -> ComputationResult:
        fcf, fcf_ref = self.free_cash_flow(self.fiscal_year, "free_cash_flow_margin")
        revenue, rev_ref = self.value_with_fallback(
            "revenue",
            self.fiscal_year,
            allow_quarterly=True,
            warn_metric="free_cash_flow_margin",
        )
        if fcf is None or revenue in (None, 0):
            imf_result = self._imf_result("free_cash_flow_margin")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("free_cash_flow_margin") or "Unable to compute FCF margin"
            return (None, "n/a", "", "", warning)
        value = _safe_div(fcf, revenue)
        source_ref = f"fcf[{fcf_ref}]/revenue[{rev_ref}]"
        warning = self._pop_warning("free_cash_flow_margin")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_cash_conversion(self) -> ComputationResult:
        cfo, cfo_ref = self.value_with_fallback(
            "cash_from_operations",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="cash_conversion",
        )
        net_income, ni_ref = self.value_with_fallback(
            "net_income",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="cash_conversion",
        )
        if cfo is None or net_income in (None, 0):
            imf_result = self._imf_result("cash_conversion")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("cash_conversion") or "Unable to compute cash conversion"
            return (None, "n/a", "", "", warning)
        value = _safe_div(cfo, net_income)
        source_ref = f"CFO[{cfo_ref}]/net_income[{ni_ref}]"
        warning = self._pop_warning("cash_conversion")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_debt_to_equity(self) -> ComputationResult:
        total_debt, debt_ref = self.total_debt(self.fiscal_year)
        equity, equity_ref = self.value_with_fallback(
            "shareholders_equity",
            self.fiscal_year,
            aliases=["total_equity"],
            allow_quarterly=False,
            warn_metric="debt_to_equity",
        )
        if total_debt is None or equity in (None, 0):
            imf_result = self._imf_result("debt_to_equity")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("debt_to_equity") or "Unable to compute debt to equity"
            return (None, "n/a", "", "", warning)
        value = _safe_div(total_debt, equity)
        source_ref = f"debt[{debt_ref}]/equity[{equity_ref}]"
        warning = self._pop_warning("debt_to_equity")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_dividend_yield(self) -> ComputationResult:
        price = self.latest_price()
        dps, dps_ref = self.dividends_per_share(self.fiscal_year)
        if price in (None, 0) or dps is None:
            imf_result = self._imf_result("dividend_yield")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("dividend_yield")
            return (None, "n/a", "", "", warning or "Dividend yield requires price and DPS")
        value = _safe_div(dps, price)
        source = "derived"
        source_ref = f"DPS[{dps_ref}]/price"
        warning = self._pop_warning("dividend_yield")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_tsr(self) -> ComputationResult:
        price = self.latest_price()
        if price is None:
            imf_result = self._imf_result("tsr")
            if imf_result is not None:
                return imf_result
            return (None, "n/a", "", "", "Latest price unavailable")
        one_year_ago = self._now - timedelta(days=365)
        previous_quote = self.db.fetch_quote_on_or_before(self.ticker, before=one_year_ago)
        prev_price = previous_quote.get("price") if previous_quote else None
        if prev_price in (None, 0):
            imf_result = self._imf_result("tsr")
            if imf_result is not None:
                return imf_result
            return (None, "n/a", "", "", "Historical price unavailable for TSR")
        dps, dps_ref = self.dividends_per_share(self.fiscal_year)
        dividends = dps or 0.0
        tsr = ((price - prev_price) + dividends) / prev_price
        source_ref = f"price_change+dividends[{dps_ref}]"
        warning = self._pop_warning("tsr")
        return (tsr, "derived", "SEC", source_ref, warning)

    def compute_share_buyback_intensity(self) -> ComputationResult:
        repurchases, rep_ref = self.value_with_fallback(
            "share_repurchases",
            self.fiscal_year,
            allow_quarterly=False,
            warn_metric="share_buyback_intensity",
        )
        market_cap, mc_ref = self.market_cap(self.fiscal_year)
        if repurchases is None or market_cap in (None, 0):
            imf_result = self._imf_result("share_buyback_intensity")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("share_buyback_intensity") or "Missing data for buyback intensity"
            return (None, "n/a", "", "", warning)
        intensity = abs(repurchases) / market_cap
        source_ref = f"share_repurchases[{rep_ref}]/market_cap[{mc_ref}]"
        warning = self._pop_warning("share_buyback_intensity")
        return (intensity, "derived", "SEC", source_ref, warning)

    def compute_pe_ratio(self) -> ComputationResult:
        price = self.latest_price()
        eps, eps_ref = self.eps_value(self.fiscal_year, warn_metric="pe_ratio")
        if price in (None, 0) or eps in (None, 0):
            warning = self._pop_warning("pe_ratio")
            return (None, "n/a", "", "", warning or "Cannot compute P/E without price and EPS")
        value = _safe_div(price, eps)
        source = "derived"
        source_ref = f"price/eps[{eps_ref}]"
        warning = self._pop_warning("pe_ratio")
        return (value, source, "SEC", source_ref, warning)

    def compute_ev_ebitda(self) -> ComputationResult:
        ev, ev_ref = self.enterprise_value(self.fiscal_year)
        ebitda, e_ref = self.ebitda_value(self.fiscal_year, warn_metric="ev_ebitda")
        if ev in (None, 0) or ebitda in (None, 0):
            warning = self._pop_warning("ev_ebitda")
            return (None, "n/a", "", "", warning or "Cannot compute EV/EBITDA")
        value = _safe_div(ev, ebitda)
        source_ref = f"enterprise_value[{ev_ref}]/ebitda[{e_ref}]"
        warning = self._pop_warning("ev_ebitda")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_pb_ratio(self) -> ComputationResult:
        price = self.latest_price()
        equity, eq_ref = self.value_with_fallback(
            "shareholders_equity",
            self.fiscal_year,
            aliases=["total_equity"],
            allow_quarterly=False,
            warn_metric="pb_ratio",
        )
        shares, shares_ref = self.shares_outstanding(self.fiscal_year)
        if price in (None, 0) or equity is None or shares in (None, 0):
            warning = self._pop_warning("pb_ratio")
            return (None, "n/a", "", "", warning or "Cannot compute P/B ratio")
        book_per_share = equity / shares
        if book_per_share in (None, 0):
            warning = self._pop_warning("pb_ratio") or "Book value per share unavailable"
            return (None, "n/a", "", "", warning)
        value = _safe_div(price, book_per_share)
        source_ref = f"price/(equity[{eq_ref}]/shares[{shares_ref}])"
        warning = self._pop_warning("pb_ratio")
        return (value, "derived", "SEC", source_ref, warning)

    def compute_peg_ratio(self) -> ComputationResult:
        pe_value = self.get_kpi("pe_ratio") or self.metric("pe_ratio", self.fiscal_year)
        if pe_value is None:
            computed = self.compute_pe_ratio()
            pe_value = computed[0]
            if computed[4]:
                self.add_warning("peg_ratio", computed[4])
        if pe_value in (None, 0):
            imf_result = self._imf_result("peg_ratio")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("peg_ratio") or "P/E ratio unavailable for PEG"
            return (None, "n/a", "", "", warning)
        eps_growth = self.get_kpi("eps_cagr") or self.metric("eps_cagr", self.fiscal_year)
        if eps_growth in (None, 0):
            self.add_warning("peg_ratio", "EPS growth unavailable for PEG")
            imf_result = self._imf_result("peg_ratio")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("peg_ratio") or "EPS growth unavailable for PEG"
            return (None, "n/a", "", "", warning)
        if abs(eps_growth) < 1e-6:
            self.add_warning("peg_ratio", "EPS growth near zero; PEG undefined")
            imf_result = self._imf_result("peg_ratio")
            if imf_result is not None:
                return imf_result
            warning = self._pop_warning("peg_ratio")
            return (None, "n/a", "", "", warning or "EPS growth near zero; PEG undefined")
        value = pe_value / (eps_growth * 100)
        warning = self._pop_warning("peg_ratio")
        return (value, "derived", "SEC", "pe_ratio/eps_cagr", warning)


def compute_price_based(metric_id: str, ctx: Context, snapshot: Dict[str, Any]) -> ComputationResult:
    """Compute metrics that depend on external price data."""
    price = snapshot.get("price")
    price_source = snapshot.get("price_source") or ""
    external_source = price_source if price_source else ""
    if not isinstance(price, (int, float)):
        price = ctx.latest_price()
        if price is not None and not external_source:
            external_source = "quote"

    if metric_id == "pe_ratio":
        eps, eps_ref = ctx.eps_value(ctx.fiscal_year, warn_metric="pe_ratio")
        if price in (None, 0) or eps in (None, 0):
            warning = ctx._pop_warning("pe_ratio")
            return (None, "n/a", "", "", warning or "Missing price or EPS for P/E")
        value = _safe_div(price, eps)
        source = _join_sources(external_source, "SEC")
        source_ref = f"price[{external_source or 'quote'}]/eps[{eps_ref}]"
        warning = ctx._pop_warning("pe_ratio")
        return (value, "external", source or "Yahoo", source_ref, warning)

    if metric_id == "ev_ebitda":
        ev = snapshot.get("ev")
        ev_source = "Yahoo" if isinstance(ev, (int, float)) else ""
        if not isinstance(ev, (int, float)):
            market_cap_raw = snapshot.get("market_cap")
            market_cap_source = "Yahoo" if isinstance(market_cap_raw, (int, float)) else ""
            mc_ref = "market_cap.yahoo" if market_cap_source else ""
            if not isinstance(market_cap_raw, (int, float)):
                market_cap_raw, mc_ref = ctx.market_cap(ctx.fiscal_year)
                market_cap_source = "SEC"
            total_debt, debt_ref = ctx.total_debt(ctx.fiscal_year)
            cash, cash_ref = ctx.cash_balance(ctx.fiscal_year)
            if market_cap_raw is None:
                return (None, "n/a", "", "", ctx._pop_warning("ev_ebitda") or "Market cap unavailable")
            ev = market_cap_raw + (total_debt or 0.0) - (cash or 0.0)
            ev_source = _join_sources(market_cap_source, "SEC")
        ebitda, e_ref = ctx.ebitda_value(ctx.fiscal_year, warn_metric="ev_ebitda")
        if ev in (None, 0) or ebitda in (None, 0):
            warning = ctx._pop_warning("ev_ebitda") or "Missing EV or EBITDA"
            return (None, "n/a", "", "", warning)
        value = _safe_div(ev, ebitda)
        source = _join_sources(ev_source, "SEC")
        source_ref = f"enterprise_value[{ev_source}]/ebitda[{e_ref}]"
        warning = ctx._pop_warning("ev_ebitda")
        return (value, "external", source or "Yahoo", source_ref, warning)

    if metric_id == "pb_ratio":
        equity, eq_ref = ctx.value_with_fallback(
            "shareholders_equity",
            ctx.fiscal_year,
            aliases=["total_equity"],
            allow_quarterly=False,
            warn_metric="pb_ratio",
        )
        shares, shares_ref = ctx.shares_outstanding(ctx.fiscal_year)
        if price in (None, 0) or equity is None or shares in (None, 0):
            warning = ctx._pop_warning("pb_ratio") or "Cannot compute P/B ratio"
            return (None, "n/a", "", "", warning)
        book = equity / shares
        if book in (None, 0):
            warning = ctx._pop_warning("pb_ratio") or "Book value per share unavailable"
            return (None, "n/a", "", "", warning)
        value = _safe_div(price, book)
        source = _join_sources(external_source, "SEC")
        source_ref = f"price[{external_source or 'quote'}]/(equity[{eq_ref}]/shares[{shares_ref}])"
        warning = ctx._pop_warning("pb_ratio")
        return (value, "external", source or "Yahoo", source_ref, warning)

    if metric_id == "peg_ratio":
        # Prefer previously computed values
        eps_growth = ctx.get_kpi("eps_cagr") or ctx.metric("eps_cagr", ctx.fiscal_year)
        if eps_growth in (None, 0):
            warning = "EPS growth unavailable for PEG"
            return (None, "n/a", "", "", warning)
        pe_value = ctx.get_kpi("pe_ratio") or ctx.metric("pe_ratio", ctx.fiscal_year)
        if pe_value is None:
            pe_result = compute_price_based("pe_ratio", ctx, snapshot)
            pe_value = pe_result[0]
        if pe_value is None:
            warning = "Unable to compute P/E for PEG"
            return (None, "n/a", "", "", warning)
        if abs(eps_growth) < 1e-6:
            warning = "EPS growth near zero; PEG undefined"
            return (None, "n/a", "", "", warning)
        value = pe_value / (eps_growth * 100)
        warning = ctx._pop_warning("peg_ratio")
        return (value, "external", "Yahoo", "pe_ratio/eps_cagr", warning)

    if metric_id == "dividend_yield":
        dps, dps_ref = ctx.dividends_per_share(ctx.fiscal_year)
        if price in (None, 0) or dps is None:
            warning = ctx._pop_warning("dividend_yield") or "Missing price or DPS"
            return (None, "n/a", "", "", warning)
        value = _safe_div(dps, price)
        source = _join_sources(external_source, "SEC")
        source_ref = f"DPS[{dps_ref}]/price[{external_source or 'quote'}]"
        warning = ctx._pop_warning("dividend_yield")
        return (value, "external", source or "Yahoo", source_ref, warning)

    if metric_id == "tsr":
        history = snapshot.get("history")
        if pd is None or not isinstance(history, pd.DataFrame) or history.empty or "Close" not in history:
            return (None, "n/a", "", "", "Price history unavailable for TSR")
        history = history.dropna(subset=["Close"]).sort_index()
        if history.empty:
            return (None, "n/a", "", "", "Price history unavailable for TSR")
        end_price = float(history["Close"].iloc[-1])
        start_idx = max(0, len(history) - 252)
        start_price = float(history["Close"].iloc[start_idx])
        dividends = 0.0
        if "Dividends" in history:
            dividends = float(history["Dividends"].iloc[start_idx:].fillna(0).sum())
        if start_price in (None, 0):
            return (None, "n/a", "", "", "Insufficient price history for TSR")
        value = ((end_price - start_price) + dividends) / start_price
        source_ref = "Yahoo history (1y)"
        return (value, "external", "Yahoo", source_ref, None)

    if metric_id == "share_buyback_intensity":
        repurchases, rep_ref = ctx.value_with_fallback(
            "share_repurchases",
            ctx.fiscal_year,
            allow_quarterly=False,
            warn_metric="share_buyback_intensity",
        )
        market_cap = snapshot.get("market_cap")
        mc_source = "Yahoo" if isinstance(market_cap, (int, float)) else ""
        if not isinstance(market_cap, (int, float)):
            market_cap, mc_ref = ctx.market_cap(ctx.fiscal_year)
            mc_source = "SEC"
        else:
            mc_ref = "market_cap.yahoo"
        if repurchases is None or market_cap in (None, 0):
            warning = ctx._pop_warning("share_buyback_intensity") or "Missing data for buyback intensity"
            return (None, "n/a", "", "", warning)
        value = abs(repurchases) / market_cap
        source = _join_sources(mc_source, "SEC")
        source_ref = f"share_repurchases[{rep_ref}]/market_cap[{mc_ref}]"
        warning = ctx._pop_warning("share_buyback_intensity")
        return (value, "external", source or "Yahoo", source_ref, warning)

    return (None, "n/a", "", "", None)


def fill_missing_kpis(
    db: Database,
    ticker: str,
    fy: int,
    fq: Optional[int] = None,
    *,
    allow_external: bool = True,
) -> int:
    """Evaluate registered backfill rules and persist any successful computations."""
    register_rules()
    ctx = Context(db, ticker, fy, fq, allow_external=allow_external)
    filled = 0
    for metric_id, rule in POLICY.items():
        # Skip metrics already present from the primary pipeline
        if ctx.metric(metric_id, fy) is not None:
            continue
        if ctx.get_kpi(metric_id) is not None:
            continue
        try:
            value, method, source, source_ref, warning = rule.compute(ctx)
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Backfill rule %s failed for %s FY%s", metric_id, ticker, fy)
            continue
        if metric_id in PRICE_BASED_METRICS:
            if value is None or method != "external":
                snapshot = ctx.get_ext_snapshot()
                ext_value, ext_method, ext_source, ext_source_ref, ext_warning = compute_price_based(
                    metric_id, ctx, snapshot
                )
                if ext_value is not None:
                    value = ext_value
                    method = ext_method
                    source = ext_source
                    source_ref = ext_source_ref
                    warning = ext_warning
            if value is None:
                imf_result = ctx._imf_result(metric_id)
                if imf_result is not None:
                    value, method, source, source_ref, warning = imf_result
        if value is None:
            continue
        if metric_id in PERCENT_METRICS:
            unit = "percent"
        elif metric_id in MULTIPLE_METRICS:
            unit = "multiple"
        else:
            unit = "ratio"
        db.upsert_kpi(
            ticker,
            fy,
            fq,
            metric_id,
            float(value),
            unit,
            method,
            source or "",
            source_ref or "",
            warning,
        )
        ctx.register_result(
            metric_id,
            float(value),
            method=method,
            source=source or "",
            source_ref=source_ref or "",
            warning=warning,
        )
        period = f"FY{fy}" if fq is None else f"FY{fy}Q{fq}"
        record = MetricRecord(
            ticker=ticker.upper(),
            metric=metric_id,
            period=period,
            value=float(value),
            source=source or method or "proxy",
            updated_at=ctx._now,
            start_year=fy,
            end_year=fy,
        )
        replace_metric_snapshots(db.path, [record])
        filled += 1
    return filled
