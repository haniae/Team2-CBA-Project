"""Shared helpers for building CFI dashboard payloads and formatting."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import database
from .analytics_engine import METRIC_LABELS, MULTIPLE_METRICS, PERCENTAGE_METRICS

DASHBOARD_KPI_ORDER: Tuple[str, ...] = (
    "revenue_cagr",
    "eps_cagr",
    "ebitda_growth",
    "ebitda_margin",
    "operating_margin",
    "net_margin",
    "profit_margin",
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
)


def _normalise_ticker_symbol(value: str) -> str:
    """Return canonical ticker form used by the datastore (share classes -> dash)."""
    symbol = (value or "").strip().upper()
    return symbol.replace(".", "-")


def _display_ticker_symbol(symbol: str) -> str:
    """Convert canonical datastore ticker to a UI-friendly representation."""
    if "-" in symbol:
        return symbol.replace("-", ".")
    return symbol


def _metric_year(record: Optional[database.MetricRecord]) -> Optional[int]:
    """Extract a fiscal year from a metric snapshot."""
    if record is None:
        return None
    if record.end_year:
        return int(record.end_year)
    if record.start_year:
        return int(record.start_year)
    if record.period:
        matches = re.findall(r"\d{4}", record.period)
        if matches:
            try:
                return int(matches[-1])
            except ValueError:
                return None
    return None


def _format_billions(value: Optional[float]) -> Optional[float]:
    """Scale raw currency values to billions with compact precision."""
    if value is None:
        return None
    scaled = value / 1_000_000_000
    magnitude = abs(scaled)
    if magnitude >= 100:
        return round(scaled)
    if magnitude >= 10:
        return round(scaled, 1)
    return round(scaled, 2)


def _format_percent(value: Optional[float]) -> Optional[float]:
    """Convert fractional metrics into percentage values."""
    if value is None:
        return None
    return round(value * 100, 1)


def _format_number(value: Optional[float], decimals: int = 1) -> Optional[str]:
    """Format a float with trimmed trailing zeroes."""
    if value is None:
        return None
    formatted = f"{value:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".")


def _lookup_company_name(database_path: Path, ticker: str) -> Optional[str]:
    """Fetch a human-readable company name for the supplied ticker."""
    try:
        with database.temporary_connection(database_path) as connection:
            row = connection.execute(
                """
                SELECT company_name
                FROM ticker_aliases
                WHERE ticker = ? AND company_name <> ''
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()
            if row and row[0]:
                return str(row[0])
            row = connection.execute(
                """
                SELECT company_name
                FROM financial_facts
                WHERE ticker = ? AND company_name <> ''
                ORDER BY ingested_at DESC
                LIMIT 1
                """,
                (ticker,),
            ).fetchone()
            if row and row[0]:
                return str(row[0])
    except Exception:  # pragma: no cover - best-effort lookup
        return None
    return None


def _latest_metric_value(
    latest: Dict[str, database.MetricRecord],
    *names: str,
) -> Optional[float]:
    """Return the newest available metric value matching any of the supplied aliases."""
    for name in names:
        record = latest.get(name)
        if record and record.value is not None:
            try:
                return float(record.value)
            except (TypeError, ValueError):
                continue
    return None


def _round_two(value: Optional[float]) -> Optional[float]:
    """Round a float to two decimal places when present."""
    if value is None:
        return None
    return round(value, 2)


def _build_kpi_summary(
    latest: Dict[str, database.MetricRecord],
) -> List[Dict[str, Any]]:
    """Assemble the ordered KPI list used by the dashboard scorecard."""
    summary: List[Dict[str, Any]] = []
    for metric_id in DASHBOARD_KPI_ORDER:
        record = latest.get(metric_id)
        value = _latest_metric_value(latest, metric_id)
        entry: Dict[str, Any] = {
            "id": metric_id,
            "label": METRIC_LABELS.get(metric_id, metric_id.replace("_", " ").title()),
            "value": value,
            "type": "percent"
            if metric_id in PERCENTAGE_METRICS
            else "multiple"
            if metric_id in MULTIPLE_METRICS
            else "number",
        }
        if record:
            period_label = record.period
            if not period_label:
                period = _metric_year(record)
                period_label = f"FY{period}" if period else None
            if period_label:
                entry["period"] = period_label
            if getattr(record, "source", None):
                entry["source"] = record.source
            if getattr(record, "updated_at", None):
                entry["updated_at"] = record.updated_at.isoformat()
        summary.append(entry)
    return summary


def _build_kpi_series(
    records: Iterable[database.MetricRecord],
) -> Dict[str, Dict[str, Any]]:
    """Collect KPI trend series for drill-down interactions."""
    series_by_metric: Dict[str, Dict[str, Any]] = {}
    for metric_id in DASHBOARD_KPI_ORDER:
        series = _collect_series(records, metric_id)
        if not series:
            continue
        years = sorted(series)
        series_by_metric[metric_id] = {
            "type": "percent" if metric_id in PERCENTAGE_METRICS else "multiple" if metric_id in MULTIPLE_METRICS else "number",
            "years": years,
            "values": [series[year] for year in years],
        }
    return series_by_metric


def _collect_sources(
    latest: Dict[str, database.MetricRecord],
) -> List[Dict[str, Any]]:
    """Summarise source provenance for dashboard metrics."""
    sources: List[Dict[str, Any]] = []
    for metric_id, record in latest.items():
        if not record or not getattr(record, "source", None):
            continue
        entry: Dict[str, Any] = {
            "metric": metric_id,
            "label": METRIC_LABELS.get(metric_id, metric_id.replace("_", " ").title()),
            "source": record.source,
            "value": record.value,
        }
        if record.period:
            entry["period"] = record.period
        else:
            year = _metric_year(record)
            if year:
                entry["period"] = f"FY{year}"
        if record.updated_at:
            entry["updated_at"] = record.updated_at.isoformat()
        sources.append(entry)
    sources.sort(key=lambda item: item.get("label") or item["metric"])
    return sources


def _build_interactions(
    kpi_series: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Create interaction metadata consumed by the web dashboard."""
    drilldowns: List[Dict[str, Any]] = []
    for metric_id in DASHBOARD_KPI_ORDER:
        if metric_id not in kpi_series:
            continue
        drilldowns.append(
            {
                "id": metric_id,
                "label": METRIC_LABELS.get(metric_id, metric_id.replace("_", " ").title()),
                "default_view": "trend",
                "data_refs": {
                    "series": f"kpi_series.{metric_id}",
                    "summary_id": metric_id,
                },
            }
        )

    interactions: Dict[str, Any] = {
        "kpis": {
            "drilldowns": drilldowns,
            "default_mode": "trend",
        },
        "charts": {
            "controls": {
                "modes": ["absolute", "growth"],
                "default": "absolute",
            }
        },
        "sources": {
            "enabled": True,
            "types": ["filing", "market_data", "derived"],
        },
    }
    return interactions


def _build_peer_config(
    engine: "AnalyticsEngine",
    ticker: str,
) -> Dict[str, Any]:
    """Return peer selector configuration for the dashboard."""
    benchmark_label = engine.benchmark_label()
    peer_config: Dict[str, Any] = {
        "focus_ticker": ticker,
        "default_peer_group": "benchmark",
        "max_peers": 5,
        "supports_custom": True,
        "benchmark_label": benchmark_label,
        "available_peer_groups": [
            {
                "id": "benchmark",
                "label": benchmark_label,
                "tickers": [],
            },
            {
                "id": "custom",
                "label": "Custom selection",
                "tickers": [],
            },
        ],
    }
    return peer_config


def _valuation_per_share(
    latest: Dict[str, database.MetricRecord],
) -> Optional[Dict[str, Optional[float]]]:
    """Derive simple valuation scenarios (per share) from available metrics."""
    shares = _latest_metric_value(latest, "shares_outstanding", "weighted_avg_diluted_shares")
    if not shares or shares <= 0:
        return None

    net_income = _latest_metric_value(latest, "net_income")
    pe_ratio = _latest_metric_value(latest, "pe_ratio")
    ebitda = _latest_metric_value(latest, "ebitda")
    free_cash_flow = _latest_metric_value(latest, "free_cash_flow")
    ev_ebitda = _latest_metric_value(latest, "ev_ebitda")
    cash = _latest_metric_value(latest, "cash_and_cash_equivalents", "cash")
    total_debt = _latest_metric_value(latest, "total_debt", "long_term_debt")

    eps = None
    if net_income is not None:
        eps = net_income / shares

    market_price = None
    if eps is not None and pe_ratio not in (None, 0):
        market_price = eps * pe_ratio

    fcf_per_share = None
    if free_cash_flow is not None:
        fcf_per_share = free_cash_flow / shares

    comps_price = None
    if ebitda is not None and ev_ebitda not in (None, 0):
        enterprise_value = ebitda * ev_ebitda
        net_debt = (total_debt or 0.0) - (cash or 0.0)
        equity_value = enterprise_value - net_debt
        comps_price = equity_value / shares if shares else None

    if market_price is None:
        market_price = comps_price

    if fcf_per_share is None and market_price is not None:
        # Back into a proxy FCF multiple when only market pricing exists
        fcf_per_share = market_price / 18.0

    if market_price is None and fcf_per_share is None:
        return None

    dcf_base = None
    if fcf_per_share is not None:
        dcf_base = fcf_per_share * 18.0

    if dcf_base is None:
        dcf_base = market_price

    if dcf_base is None:
        return None

    dcf_bull = dcf_base * 1.15
    dcf_bear = dcf_base * 0.85
    comps_value = comps_price or market_price

    return {
        "dcf_base": _round_two(dcf_base),
        "dcf_bull": _round_two(dcf_bull),
        "dcf_bear": _round_two(dcf_bear),
        "comps": _round_two(comps_value),
        "market": _round_two(market_price),
    }


def _collect_series(
    records: Iterable[database.MetricRecord],
    metric: str,
    *,
    scale_billions: bool = False,
) -> Dict[int, float]:
    """Return a year -> value mapping for a metric."""
    series: Dict[int, float] = {}
    for record in records:
        if record.metric != metric:
            continue
        year = _metric_year(record)
        if year is None or record.value is None:
            continue
        value = float(record.value)
        if scale_billions:
            value = value / 1_000_000_000
        series[year] = value
    return series


def build_cfi_dashboard_payload(
    engine: "AnalyticsEngine",
    ticker: str,
) -> Optional[Dict[str, Any]]:
    """Construct the payload expected by ``cfi_dashboard.js`` for a ticker."""
    from datetime import date as _date  # local import to avoid circular hints

    canonical = _normalise_ticker_symbol(ticker)
    records = engine.get_metrics(canonical)
    if not records:
        return None

    latest = engine._select_latest_records(records, span_fn=engine._period_span)
    if not latest:
        return None

    valuations = _valuation_per_share(latest) or {}
    database_path = Path(engine.settings.database_path)
    company_name = _lookup_company_name(database_path, canonical) or _display_ticker_symbol(canonical)
    display_ticker = _display_ticker_symbol(canonical)

    shares = _latest_metric_value(latest, "shares_outstanding", "weighted_avg_diluted_shares")
    market_cap = _latest_metric_value(latest, "market_cap")
    enterprise_value = _latest_metric_value(latest, "enterprise_value")
    total_debt = _latest_metric_value(latest, "total_debt", "long_term_debt")
    cash = _latest_metric_value(latest, "cash_and_cash_equivalents", "cash")
    net_debt = None
    if total_debt is not None or cash is not None:
        net_debt = (total_debt or 0.0) - (cash or 0.0)

    revenue_latest = latest.get("revenue")
    revenue_year = _metric_year(revenue_latest)

    price_current = valuations.get("market")
    price_target = valuations.get("dcf_base")
    upside_pct = None
    if price_current not in (None, 0) and price_target is not None:
        upside_pct = ((price_target / price_current) - 1.0) * 100.0

    recommendation = "Hold"
    if upside_pct is not None:
        if upside_pct >= 10:
            recommendation = "Buy"
        elif upside_pct <= -5:
            recommendation = "Sell"

    meta = {
        "brand": (company_name.split()[0] if company_name else display_ticker).lower(),
        "company": company_name,
        "ticker": display_ticker,
        "recommendation": recommendation,
        "target_price": price_target,
        "scenario": "Consensus",
        "report_tag": "BenchmarkOS Equity Research",
        "date": _date.today().isoformat(),
    }

    price_table = {
        "Ticker": display_ticker,
        "Current Price": price_current,
        "Target Price": price_target,
        "TP Upside %": upside_pct,
    }

    overview = {
        "Company": company_name,
        "Benchmark": engine.benchmark_label(),
        "Latest Revenue FY": f"FY{revenue_year}" if revenue_year else None,
    }

    net_margin = _latest_metric_value(latest, "net_margin")
    roe = _latest_metric_value(latest, "return_on_equity")
    fcf_margin = _latest_metric_value(latest, "free_cash_flow_margin")
    key_stats = {}
    if net_margin is not None:
        key_stats["Net margin"] = net_margin
    if roe is not None:
        key_stats["ROE"] = roe
    if fcf_margin is not None:
        key_stats["FCF margin"] = fcf_margin

    market_data = {}
    if shares is not None:
        market_data["Shares O/S (M)"] = shares / 1_000_000
    if market_cap is not None:
        market_data["Market Cap ($B)"] = market_cap / 1_000_000_000
    if net_debt is not None:
        market_data["Net Debt ($B)"] = net_debt / 1_000_000_000
    if enterprise_value is not None:
        market_data["Enterprise Value ($B)"] = enterprise_value / 1_000_000_000

    valuation_table = []
    if any(value is not None for value in (price_current, price_target, valuations.get("comps"))):
        valuation_table.append(
            {
                "Label": "Share Price",
                "Market": price_current,
                "DCF": price_target,
                "Comps": valuations.get("comps"),
            }
        )
    if enterprise_value is not None:
        valuation_table.append(
            {
                "Label": "Enterprise Value ($B)",
                "Market": enterprise_value / 1_000_000_000,
                "DCF": None,
                "Comps": None,
            }
        )

    revenue_series = _collect_series(records, "revenue")
    ebitda_series = _collect_series(records, "ebitda")
    net_income_series = _collect_series(records, "net_income")
    net_margin_series = _collect_series(records, "net_margin")
    fcf_series = _collect_series(records, "free_cash_flow")
    enterprise_series = _collect_series(records, "enterprise_value")

    years_set = set(revenue_series) | set(ebitda_series) | set(net_income_series) | set(fcf_series)
    if not years_set:
        years_set = {year for year in net_margin_series}
    years = sorted(years_set)
    if len(years) > 8:
        years = years[-8:]

    def _series_values(series: Dict[int, float], transform=None) -> List[Optional[float]]:
        values: List[Optional[float]] = []
        for year in years:
            value = series.get(year)
            if value is not None and transform:
                value = transform(value)
            values.append(value)
        return values

    def _safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator in (None, 0) or denominator in (None, 0):
            return None
        return numerator / denominator

    ev_revenue_series: Dict[int, float] = {}
    ev_ebitda_series: Dict[int, float] = {}
    for year in years:
        ev = enterprise_series.get(year)
        rev = revenue_series.get(year)
        ebitda = ebitda_series.get(year)
        ratio_rev = _safe_ratio(ev, rev)
        ratio_ebitda = _safe_ratio(ev, ebitda)
        if ratio_rev is not None:
            ev_revenue_series[year] = ratio_rev
        if ratio_ebitda is not None:
            ev_ebitda_series[year] = ratio_ebitda

    key_financials = {
        "columns": years,
        "rows": [
            {"label": "Revenue", "values": _series_values(revenue_series)},
            {"label": "EBITDA", "values": _series_values(ebitda_series)},
            {"label": "Net income", "values": _series_values(net_income_series)},
            {"label": "Net profit margin", "values": _series_values(net_margin_series), "type": "percent"},
            {"label": "Free cash flow", "values": _series_values(fcf_series)},
            {"label": "EV/Revenue (×)", "values": _series_values(ev_revenue_series), "type": "multiple"},
            {"label": "EV/EBITDA (×)", "values": _series_values(ev_ebitda_series), "type": "multiple"},
        ],
    }

    charts: Dict[str, Any] = {}
    if years:
        charts["revenue_ev"] = {
            "Year": years,
            "Revenue": [revenue_series.get(year) for year in years],
            "EV_Rev": [ev_revenue_series.get(year) for year in years],
        }
        charts["ebitda_ev"] = {
            "Year": years,
            "EBITDA": [ebitda_series.get(year) for year in years],
            "EV_EBITDA": [ev_ebitda_series.get(year) for year in years],
        }

    current_year = datetime.utcnow().year
    forecast_years = [current_year, current_year + 1, current_year + 2]
    if price_current is not None:
        bull = valuations.get("dcf_bull") or price_target or price_current
        base = price_target or price_current
        bear = valuations.get("dcf_bear") or price_target or price_current
        charts["forecast"] = {
            "Year": forecast_years,
            "Bull": [price_current, bull, bull * 1.05 if bull else None],
            "Base": [price_current, base, base * 1.03 if base else None],
            "Bear": [price_current, bear, bear * 0.97 if bear else None],
        }

    valuation_cases: List[str] = []
    valuation_values: List[Optional[float]] = []
    for label, key in (
        ("DCF - Bull", "dcf_bull"),
        ("DCF - Base", "dcf_base"),
        ("DCF - Bear", "dcf_bear"),
        ("Comps", "comps"),
        ("Market", "market"),
    ):
        value = valuations.get(key)
        if value is not None:
            valuation_cases.append(label)
            valuation_values.append(value)
    if valuation_cases:
        charts["valuation_bar"] = {"Case": valuation_cases, "Value": valuation_values}

    valuation_notes = []
    if price_target is not None:
        valuation_notes.append(f"DCF base case target ${price_target:,.2f}")
    if valuations.get("dcf_bull") is not None and valuations.get("dcf_bear") is not None:
        valuation_notes.append("Bull/Bear range reflects ±15% swing to base case.")
    if valuations.get("comps") is not None:
        valuation_notes.append("Comps derived from EV/EBITDA peer median.")

    current_price = price_current
    average_price = None
    if valuation_values:
        average_price = sum(v for v in valuation_values if v is not None) / len(valuation_values)

    valuation_data = {
        "current": current_price,
        "average": _round_two(average_price) if average_price is not None else None,
        "notes": valuation_notes,
    }

    kpi_summary = _build_kpi_summary(latest)
    kpi_series = _build_kpi_series(records)
    interactions = _build_interactions(kpi_series)
    peer_config = _build_peer_config(engine, display_ticker)
    sources = _collect_sources(latest)

    payload = {
        "meta": meta,
        "price": price_table,
        "overview": overview,
        "key_stats": key_stats,
        "market_data": market_data,
        "valuation_table": valuation_table,
        "key_financials": key_financials,
        "charts": charts,
        "valuation_data": valuation_data,
        "kpi_summary": kpi_summary,
        "kpi_series": kpi_series,
        "interactions": interactions,
        "peer_config": peer_config,
        "sources": sources,
    }
    return payload


def build_cfi_compare_payload(
    engine: "AnalyticsEngine",
    tickers: Sequence[str],
    benchmark_label: Optional[str] = None,
    *,
    strict: bool = True,
) -> Optional[Dict[str, Any]]:
    """Construct the payload expected by ``cfi_compare.js`` for up to three tickers."""
    if not tickers:
        if strict:
            raise ValueError("At least one ticker is required.")
        return None

    canonical: List[str] = []
    for ticker in tickers:
        if ticker and ticker.strip():
            symbol = _normalise_ticker_symbol(ticker)
            if symbol not in canonical:
                canonical.append(symbol)
        if len(canonical) >= 3:
            break

    if not canonical:
        if strict:
            raise ValueError("No valid tickers provided.")
        return None

    display_order = [_display_ticker_symbol(symbol) for symbol in canonical]

    records_by_ticker: Dict[str, List[database.MetricRecord]] = {}
    latest_by_ticker: Dict[str, Dict[str, database.MetricRecord]] = {}
    valuations_by_ticker: Dict[str, Optional[Dict[str, Optional[float]]]] = {}

    for symbol in canonical:
        records = engine.get_metrics(symbol)
        if not records:
            if strict:
                raise ValueError(f"No metric snapshots available for {_display_ticker_symbol(symbol)}.")
            return None
        records_by_ticker[symbol] = records
        latest = engine._select_latest_records(records, span_fn=engine._period_span)
        latest_by_ticker[symbol] = latest
        valuations_by_ticker[symbol] = _valuation_per_share(latest)

    benchmark_label = benchmark_label or engine.benchmark_label()
    metric_scope = {
        "revenue",
        "net_margin",
        "return_on_equity",
        "pe_ratio",
        "ebitda_margin",
        "ev_ebitda",
        "debt_to_equity",
        "ebitda",
        "free_cash_flow",
        "net_income",
        "shares_outstanding",
        "cash_and_cash_equivalents",
        "total_debt",
        "long_term_debt",
        "revenue_cagr",
        "eps_cagr",
        "ebitda_growth",
        "operating_margin",
        "return_on_assets",
        "return_on_invested_capital",
        "pb_ratio",
        "peg_ratio",
        "cash_conversion",
        "working_capital",
        "tsr",
        "dividend_yield",
        "share_buyback_intensity",
    }
    benchmark_metrics = engine.compute_benchmark_metrics(metric_scope)

    db_path = Path(engine.settings.database_path)
    company_names = {
        display: (_lookup_company_name(db_path, symbol) or display)
        for symbol, display in zip(canonical, display_order)
    }

    cards: Dict[str, Dict[str, str]] = {}
    for symbol, display in zip(canonical, display_order):
        latest = latest_by_ticker.get(symbol, {})
        valuation = valuations_by_ticker.get(symbol) or {}
        card: Dict[str, str] = {}
        if valuation.get("market") is not None:
            card["Price"] = f"${_format_number(valuation['market'], 2)}"
        revenue_record = latest.get("revenue")
        revenue_billions = _format_billions(
            revenue_record.value if revenue_record and revenue_record.value is not None else None
        )
        if revenue_billions is not None:
            year = _metric_year(revenue_record)
            if year:
                label = f"Revenue (FY{str(year)[-2:]} $B)"
            else:
                label = "Revenue ($B)"
            card[label] = _format_number(revenue_billions, 1)

        net_margin_pct = _format_percent(_latest_metric_value(latest, "net_margin"))
        if net_margin_pct is not None:
            card["Net margin"] = f"{_format_number(net_margin_pct, 1)}%"
        roe_pct = _format_percent(_latest_metric_value(latest, "return_on_equity", "roe"))
        if roe_pct is not None:
            card["ROE"] = f"{_format_number(roe_pct, 1)}%"
        pe_ratio = _latest_metric_value(latest, "pe_ratio")
        if pe_ratio is not None:
            card["P/E (ttm)"] = f"{_format_number(pe_ratio, 2)}×"
        cards[display] = card

    benchmark_card: Dict[str, str] = {}
    bench_revenue = benchmark_metrics.get("revenue")
    bench_revenue_b = _format_billions(bench_revenue.value if bench_revenue and bench_revenue.value is not None else None)
    if bench_revenue_b is not None:
        benchmark_card["Revenue (Avg $B)"] = _format_number(bench_revenue_b, 1)
    bench_net_margin = _format_percent(_latest_metric_value(benchmark_metrics, "net_margin"))
    if bench_net_margin is not None:
        benchmark_card["Net margin"] = f"{_format_number(bench_net_margin, 1)}%"
    bench_roe = _format_percent(_latest_metric_value(benchmark_metrics, "return_on_equity"))
    if bench_roe is not None:
        benchmark_card["ROE"] = f"{_format_number(bench_roe, 1)}%"
    bench_pe = _latest_metric_value(benchmark_metrics, "pe_ratio")
    if bench_pe is not None:
        benchmark_card["P/E (ttm)"] = f"{_format_number(bench_pe, 2)}×"
    cards["SP500"] = benchmark_card

    table_columns = ["Metric", *display_order, benchmark_label]
    table_rows: List[Dict[str, Any]] = []
    table_config = [
        {"metric": "revenue", "label": "Revenue", "type": "moneyB"},
        {"metric": "revenue_cagr", "label": "Revenue CAGR", "type": "pct"},
        {"metric": "eps_cagr", "label": "EPS CAGR", "type": "pct"},
        {"metric": "ebitda_growth", "label": "EBITDA Growth", "type": "pct"},
        {"metric": "ebitda_margin", "label": "EBITDA margin", "type": "pct"},
        {"metric": "operating_margin", "label": "Operating margin", "type": "pct"},
        {"metric": "net_margin", "label": "Net margin", "type": "pct"},
        {"metric": "return_on_assets", "label": "ROA", "type": "pct"},
        {"metric": "return_on_equity", "label": "ROE", "type": "pct"},
        {"metric": "return_on_invested_capital", "label": "ROIC", "type": "pct"},
        {"metric": "pe_ratio", "label": "P/E (ttm)", "type": "x"},
        {"metric": "ev_ebitda", "label": "EV/EBITDA (ttm)", "type": "x"},
        {"metric": "pb_ratio", "label": "P/B", "type": "x"},
        {"metric": "peg_ratio", "label": "PEG", "type": "x"},
        {"metric": "free_cash_flow", "label": "Free Cash Flow", "type": "moneyB"},
        {"metric": "cash_conversion", "label": "Cash Conversion", "type": "pct"},
        {"metric": "working_capital", "label": "Working Capital", "type": "moneyB"},
        {"metric": "tsr", "label": "TSR", "type": "pct"},
        {"metric": "dividend_yield", "label": "Dividend Yield", "type": "pct"},
        {"metric": "share_buyback_intensity", "label": "Share Buyback Intensity", "type": "pct"},
        {"metric": "debt_to_equity", "label": "Debt/Equity", "type": "x"},
    ]

    for config in table_config:
        metric_name = config["metric"]
        row: Dict[str, Any] = {"label": config["label"], "type": config["type"]}
        if metric_name == "revenue":
            revenue_years = [
                _metric_year(latest_by_ticker[symbol].get("revenue"))
                for symbol in canonical
                if latest_by_ticker[symbol].get("revenue")
            ]
            revenue_years = [year for year in revenue_years if year]
            if revenue_years:
                row["label"] = f"Revenue (FY{str(max(revenue_years))[-2:]} $B)"
        elif metric_name in {"free_cash_flow", "working_capital"}:
            row["label"] = f"{config['label']} ($B)"

        for symbol, display in zip(canonical, display_order):
            latest = latest_by_ticker[symbol]
            value: Optional[float]
            if config["type"] == "pct":
                value = _format_percent(_latest_metric_value(latest, metric_name))
            elif config["type"] == "moneyB":
                value = _format_billions(_latest_metric_value(latest, metric_name))
            else:
                value = _latest_metric_value(latest, metric_name)
                if value is not None:
                    value = round(float(value), 2)
            row[display] = value

        bench_metric = benchmark_metrics.get(metric_name)
        if config["type"] == "pct":
            bench_value = _format_percent(_latest_metric_value(benchmark_metrics, metric_name))
        elif config["type"] == "moneyB":
            bench_value = _format_billions(bench_metric.value if bench_metric else None)
        else:
            bench_value = _latest_metric_value(benchmark_metrics, metric_name)
            if bench_value is not None:
                bench_value = round(float(bench_value), 2)
        row[benchmark_label] = bench_value
        row["SPX"] = bench_value
        table_rows.append(row)

    table = {"columns": table_columns, "rows": table_rows}

    all_years: set[int] = set()
    revenue_series_map: Dict[str, Dict[int, float]] = {}
    ebitda_series_map: Dict[str, Dict[int, float]] = {}
    for symbol, display in zip(canonical, display_order):
        revenue_series = _collect_series(records_by_ticker[symbol], "revenue", scale_billions=True)
        ebitda_series = _collect_series(records_by_ticker[symbol], "ebitda", scale_billions=True)
        if revenue_series:
            all_years.update(revenue_series.keys())
        if ebitda_series:
            all_years.update(ebitda_series.keys())
        revenue_series_map[display] = revenue_series
        ebitda_series_map[display] = ebitda_series

    years = sorted(all_years)
    if len(years) > 8:
        years = years[-8:]

    revenue_series_payload: Dict[str, List[Optional[float]]] = {}
    ebitda_series_payload: Dict[str, List[Optional[float]]] = {}
    for display in display_order:
        revenue_data = revenue_series_map.get(display, {})
        ebitda_data = ebitda_series_map.get(display, {})
        revenue_series_payload[display] = [
            _round_two(revenue_data.get(year)) if revenue_data.get(year) is not None else None
            for year in years
        ]
        ebitda_series_payload[display] = [
            _round_two(ebitda_data.get(year)) if ebitda_data.get(year) is not None else None
            for year in years
        ]

    series = {
        "years": years,
        "revenue": revenue_series_payload,
        "ebitda": ebitda_series_payload,
    }

    scatter: List[Dict[str, Any]] = []
    for symbol, display in zip(canonical, display_order):
        latest = latest_by_ticker[symbol]
        net_margin_pct = _format_percent(_latest_metric_value(latest, "net_margin"))
        roe_pct = _format_percent(_latest_metric_value(latest, "return_on_equity", "roe"))
        revenue_billions = _format_billions(_latest_metric_value(latest, "revenue"))
        if net_margin_pct is None or roe_pct is None:
            continue
        scatter.append(
            {
                "ticker": display,
                "x": net_margin_pct,
                "y": roe_pct,
                "size": _round_two(revenue_billions) or 0.0,
            }
        )

    bench_scatter_margin = _format_percent(_latest_metric_value(benchmark_metrics, "net_margin"))
    bench_scatter_roe = _format_percent(_latest_metric_value(benchmark_metrics, "return_on_equity"))
    bench_scatter_revenue = _format_billions(
        benchmark_metrics.get("revenue").value if benchmark_metrics.get("revenue") else None
    )
    if bench_scatter_margin is not None and bench_scatter_roe is not None:
        scatter.append(
            {
                "ticker": benchmark_label,
                "x": bench_scatter_margin,
                "y": bench_scatter_roe,
                "size": _round_two(bench_scatter_revenue) or 0.0,
            }
        )

    football: List[Dict[str, Any]] = []
    val_summary_cases = ["DCF-Bull", "DCF-Base", "DCF-Bear", "Comps", "Market"]
    val_summary: Dict[str, Any] = {"case": val_summary_cases}

    for symbol, display in zip(canonical, display_order):
        valuation = valuations_by_ticker.get(symbol)
        if not valuation:
            continue
        ranges: List[Dict[str, Optional[float]]] = []
        if valuation.get("dcf_base") is not None:
            ranges.append(
                {
                    "name": "DCF",
                    "lo": valuation.get("dcf_bear"),
                    "hi": valuation.get("dcf_bull"),
                }
            )
        if valuation.get("comps") is not None:
            comps = valuation.get("comps")
            if comps is not None:
                ranges.append(
                    {
                        "name": "Comps",
                        "lo": _round_two(comps * 0.95),
                        "hi": _round_two(comps * 1.05),
                    }
                )
        if valuation.get("market") is not None:
            market_price = valuation.get("market")
            ranges.append(
                {
                    "name": "Market",
                    "lo": market_price,
                    "hi": market_price,
                }
            )
        if ranges:
            football.append({"ticker": display, "ranges": ranges})
        val_summary[display] = [
            valuation.get("dcf_bull"),
            valuation.get("dcf_base"),
            valuation.get("dcf_bear"),
            valuation.get("comps"),
            valuation.get("market"),
        ]

    meta = {
        "date": datetime.utcnow().date().isoformat(),
        "peerset": " vs ".join(
            [
                f"{company_names.get(display, display)} ({display})" if company_names.get(display) != display else display
                for display in display_order
            ]
            + ([benchmark_label] if benchmark_label else [])
        ),
        "tickers": display_order,
        "companies": company_names,
        "benchmark": benchmark_label,
    }

    payload = {
        "meta": meta,
        "cards": cards,
        "table": table,
        "football": football,
        "series": series,
        "scatter": scatter,
        "valSummary": val_summary,
    }
    return payload
