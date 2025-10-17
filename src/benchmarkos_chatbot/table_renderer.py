"""Shared helpers for rendering analytics tables from text commands."""

from __future__ import annotations

import re
import string
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .analytics_engine import (
    AGGREGATE_METRICS,
    AnalyticsEngine,
    BASE_METRICS,
    DERIVED_METRICS,
    METRIC_DEFINITIONS,
    MetricDefinition,
)

MAX_METRIC_COLUMNS = 6

PDS_METRICS: List[str] = [
    "revenue",
    "net_income",
    "operating_income",
    "gross_profit",
    "revenue_cagr",
    "eps_cagr",
    "ebitda_growth",
    "ebitda",
    "ebitda_margin",
    "profit_margin",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
    "return_on_invested_capital",
    "free_cash_flow",
    "free_cash_flow_margin",
    "cash_conversion",
    "working_capital",
    "working_capital_change",
    "debt_to_equity",
    "pe_ratio",
    "ev_ebitda",
    "pb_ratio",
    "peg_ratio",
    "dividend_yield",
    "tsr",
    "share_buyback_intensity",
]

METRIC_ABBREVIATIONS: Dict[str, str] = {
    "revenue": "Rev",
    "net_income": "NetInc",
    "operating_income": "OpInc",
    "gross_profit": "GrossPf",
    "cash_from_operations": "CFO",
    "cash_from_financing": "CFF",
    "cash_and_cash_equivalents": "Cash",
    "cash_conversion": "CashConv",
    "capital_expenditures": "CapEx",
    "current_assets": "CurrAst",
    "current_liabilities": "CurrLiab",
    "depreciation_and_amortization": "D&A",
    "dividend_yield": "DivYld",
    "dividends_paid": "DivPaid",
    "dividends_per_share": "DPS",
    "ebit": "EBIT",
    "ebitda": "EBITDA",
    "ebitda_growth": "EBITDA G",
    "ebitda_margin": "EBITDA %",
    "eps_basic": "EPS B",
    "eps_diluted": "EPS D",
    "eps_cagr": "EPS CAGR",
    "ev_ebitda": "EV/EBITDA",
    "free_cash_flow": "FCF",
    "free_cash_flow_margin": "FCF %",
    "income_tax_expense": "Tax",
    "interest_expense": "IntExp",
    "long_term_debt": "LT Debt",
    "long_term_debt_current": "LT Debt Cur",
    "net_margin": "Net %",
    "operating_margin": "Op %",
    "profit_margin": "Profit %",
    "pb_ratio": "P/B",
    "pe_ratio": "P/E",
    "peg_ratio": "PEG",
    "return_on_assets": "ROA",
    "return_on_equity": "ROE",
    "return_on_invested_capital": "ROIC",
    "revenue_cagr": "Rev CAGR",
    "share_buyback_intensity": "Buyback",
    "share_repurchases": "Repurch",
    "shares_outstanding": "Shares",
    "short_term_debt": "ST Debt",
    "tsr": "TSR",
    "total_assets": "TotAst",
    "total_liabilities": "TotLiab",
    "shareholders_equity": "Equity",
    "weighted_avg_diluted_shares": "WAvg Shr",
    "working_capital": "WC",
    "working_capital_change": "WC Chg",
}

METRIC_SYNONYMS: Dict[str, str] = {
    "rev": "revenue",
    "sales": "revenue",
    "netincome": "net_income",
    "net": "net_income",
    "netprofit": "net_income",
    "eps": "eps_diluted",
    "epsgrowth": "eps_cagr",
    "revcagr": "revenue_cagr",
    "ebitdagrowth": "ebitda_growth",
    "ebitdamargin": "ebitda_margin",
    "profitmargin": "profit_margin",
    "operatingmargin": "operating_margin",
    "opmargin": "operating_margin",
    "grossmargin": "gross_profit",
    "roe": "return_on_equity",
    "roa": "return_on_assets",
    "roic": "return_on_invested_capital",
    "fcf": "free_cash_flow",
    "fcfmargin": "free_cash_flow_margin",
    "cashconversion": "cash_conversion",
    "workingcapital": "working_capital",
    "workingcapitalchange": "working_capital_change",
    "wcchange": "working_capital_change",
    "debttoequity": "debt_to_equity",
    "d/e": "debt_to_equity",
    "pe": "pe_ratio",
    "p/e": "pe_ratio",
    "evebitda": "ev_ebitda",
    "ev/ebitda": "ev_ebitda",
}


class TableCommandError(Exception):
    """Raised when a table command cannot be fulfilled."""


def render_table_command(user_input: str, engine: AnalyticsEngine) -> Optional[str]:
    """Render metrics into a table for the CLI command output."""
    if not user_input.strip():
        return None

    raw_tokens = user_input.strip().split()
    if not raw_tokens:
        return None

    command = _clean_token(raw_tokens[0]).lower()
    if command.endswith(":"):
        command = command[:-1]

    if command not in {"table", "compare"}:
        return None

    tokens = raw_tokens[1:]

    try:
        remaining, period_filters, layout, period_specs = _parse_year_filters(tokens)
    except ValueError:
        return "Invalid period filter. Use 2024, 2024Q1, year=YYYY, or years=YYYY-YYYY."

    try:
        tickers, metrics, period_filters, layout_mode = _resolve_metrics_and_tickers(
            command, remaining, period_filters, layout
        )
    except ValueError as exc:
        return str(exc)

    records_by_ticker = {
        ticker: engine.get_metrics(ticker, period_filters=period_filters)
        for ticker in tickers
    }

    benchmark_label: Optional[str] = None
    compute_benchmark = getattr(engine, "compute_benchmark_metrics", None)
    if command == "compare" and callable(compute_benchmark):
        try:
            aggregated = compute_benchmark(metrics, period_filters=period_filters)
        except Exception:
            aggregated = {}
        if aggregated:
            label_getter = getattr(engine, "benchmark_label", None)
            if callable(label_getter):
                benchmark_label = label_getter()
            else:
                benchmark_label = getattr(engine, "BENCHMARK_LABEL", "Benchmark")
            records_by_ticker[benchmark_label] = list(aggregated.values())

    if period_specs:
        for ticker, records in list(records_by_ticker.items()):
            records_by_ticker[ticker] = _filter_records_by_period(records, period_specs)

    display_tickers = list(tickers)
    if benchmark_label:
        display_tickers.append(benchmark_label)

    if layout_mode in {"metrics", "metric", "rows", "matrix", "pivot"}:
        headers = ["Metric"] + display_tickers
        rows: List[List[str]] = []
        for metric in metrics:
            label = _metric_label(metric)
            row = [label]
            for ticker in display_tickers:
                records = records_by_ticker[ticker]
                latest = _select_latest(records, metric)
                row.append(_format_value_display(latest))
            rows.append(row)
        return _build_table(headers, rows)

    metric_chunks = list(_chunked(metrics, MAX_METRIC_COLUMNS)) or [[]]
    tables: List[str] = []
    total_chunks = len(metric_chunks)

    for index, metric_subset in enumerate(metric_chunks, start=1):
        headers = ["Ticker"] + [metric.title().replace("_", " ") for metric in metric_subset]
        rows: List[List[str]] = []
        for ticker in display_tickers:
            records = records_by_ticker[ticker]
            row = [ticker]
            for metric in metric_subset:
                latest = _select_latest(records, metric)
                row.append(_format_value_display(latest))
            rows.append(row)

        table = _build_table(headers, rows)
        if total_chunks > 1:
            metric_label = ", ".join(metric.replace("_", " ") for metric in metric_subset)
            title = f"Metrics {index}/{total_chunks}: {metric_label}"
            table = f"{title}\n{table}"
        tables.append(table)

    return "\n\n".join(tables)


# -- Helper functions -----------------------------------------------------


def _parse_year_filters(
    tokens: Sequence[str],
) -> Tuple[List[str], Optional[List[Tuple[int, int]]], Optional[str], List[Dict[str, Any]]]:
    """Parse tokens describing fiscal year/quarter ranges or lists."""
    remaining: List[str] = []
    layout: Optional[str] = None
    specs: List[Dict[str, Any]] = []
    seen_specs: set[Tuple[int, int, Optional[str]]] = set()

    for token in tokens:
        cleaned = token.strip().rstrip(",")
        if not cleaned:
            continue
        lower = cleaned.lower()
        if lower.startswith("layout="):
            layout = lower.split("=", 1)[1]
            continue
        if lower.startswith("year="):
            year = _coerce_int(lower.split("=", 1)[1])
            if year is None:
                raise ValueError
            spec = {"start": year, "end": year, "quarter": None}
        elif lower.startswith("years=") and "-" in lower:
            bounds = lower.split("=", 1)[1].split("-", 1)
            if len(bounds) != 2:
                raise ValueError
            start = _coerce_int(bounds[0])
            end = _coerce_int(bounds[1])
            if start is None or end is None:
                raise ValueError
            if end < start:
                start, end = end, start
            spec = {"start": start, "end": end, "quarter": None}
        else:
            parsed = _parse_period_token(cleaned)
            if parsed is None:
                remaining.append(cleaned)
                continue
            spec = parsed

        key = (spec["start"], spec["end"], spec.get("quarter"))
        if key not in seen_specs:
            seen_specs.add(key)
            specs.append(spec)

    sorted_specs = sorted(seen_specs, key=lambda item: (item[0], item[1], item[2] or ""))
    period_filters = [(start, end) for (start, end, _quarter) in sorted_specs]
    return remaining, (period_filters or None), layout, specs


# Additional helpers (_resolve_metrics_and_tickers, _split_tickers_and_periods, etc.) will follow.


def _resolve_metrics_and_tickers(
    command: str,
    tokens: Sequence[str],
    period_filters: Optional[List[Tuple[int, int]]],
    layout: Optional[str],
) -> Tuple[List[str], List[str], Optional[List[Tuple[int, int]]], str]:
    """Resolve requested metric names and tickers simultaneously."""
    layout_mode = (layout or "").lower()
    lowered = [token.lower() for token in tokens]

    if command == "table":
        if "metrics" not in lowered:
            raise ValueError(
                "Usage: table <tickers...> metrics <metrics...> [2024 | 2024Q1 | year=YYYY | years=YYYY-YYYY]"
            )
        split_index = lowered.index("metrics")
        tickers = _extract_tickers(tokens[:split_index])
        raw_metrics = tokens[split_index + 1 :]
        if not tickers or not raw_metrics:
            raise ValueError(
                "Usage: table <tickers...> metrics <metrics...> [2024 | 2024Q1 | year=YYYY | years=YYYY-YYYY]"
            )
        metrics = _expand_metrics(raw_metrics)
        return tickers, metrics, period_filters, layout_mode

    layout_mode = layout_mode or "metrics"
    anchor_index = None
    for keyword in ("metrics", "on", "with", "using", "for"):
        if keyword in lowered:
            anchor_index = lowered.index(keyword)
            break

    if anchor_index is not None:
        tickers_part = tokens[:anchor_index]
        raw_metrics = tokens[anchor_index + 1 :]
    else:
        tickers_part = tokens
        raw_metrics = ["all"]

    tickers = _extract_tickers(tickers_part)
    if not tickers:
        raise ValueError("Please specify at least one ticker to compare.")

    metrics = _expand_metrics(raw_metrics)
    return tickers, metrics, period_filters, layout_mode


def _extract_tickers(tokens: Sequence[str]) -> List[str]:
    """Extract ticker symbols from free-form tokens."""
    tickers: List[str] = []
    for token in tokens:
        cleaned = token.strip().upper().rstrip(",")
        if not cleaned or cleaned in {"VS", "AND", "FOR", "ON", "METRICS"}:
            continue
        if _parse_period_token(cleaned):
            continue
        tickers.append(cleaned)
    return tickers


def _expand_metrics(raw_metrics: Sequence[str]) -> List[str]:
    """Expand metric aliases or groups into specific metric names."""
    metrics: List[str] = []
    for token in raw_metrics:
        cleaned = token.strip().lower().strip(string.punctuation)
        if cleaned in {"all", "*"}:
            metrics.extend(sorted({
                *BASE_METRICS,
                *DERIVED_METRICS,
                *AGGREGATE_METRICS,
            }))
            continue
        if cleaned == "pds":
            metrics.extend(PDS_METRICS)
            continue
        metric = METRIC_SYNONYMS.get(cleaned, cleaned)
        metrics.append(metric)
    seen = set()
    ordered: List[str] = []
    for metric in metrics:
        if metric in seen:
            continue
        seen.add(metric)
        ordered.append(metric)
    return ordered


_QUARTER_PATTERN = re.compile(r"^(?:fy)?(?P<year>\d{4})(?:q(?P<quarter>[1-4]))?$")


def _parse_period_token(token: str) -> Optional[Dict[str, Any]]:
    """Interpret year/quarter tokens (e.g. 2020, FY2020Q1) for filtering."""
    cleaned = token.strip().lower()
    if not cleaned:
        return None
    if "-" in cleaned:
        left, right = cleaned.split("-", 1)
        if left and right:
            left = left.removeprefix("fy")
            right = right.removeprefix("fy")
            if left.isdigit() and right.isdigit():
                start = int(left)
                end = int(right)
                if end < start:
                    start, end = end, start
                if 1900 <= start <= 2100 and 1900 <= end <= 2100:
                    return {"start": start, "end": end, "quarter": None}
    match = _QUARTER_PATTERN.match(cleaned)
    if match:
        year = int(match.group("year"))
        if 1900 <= year <= 2100:
            quarter = match.group("quarter")
            quarter_label = f"Q{quarter}" if quarter else None
            return {"start": year, "end": year, "quarter": quarter_label}
    return None


def _filter_records_by_period(records: Sequence, specs: Sequence[Dict[str, Any]]) -> List:
    """Filter metric records to the requested period specifications."""
    records_list = list(records)
    if not records_list or not specs:
        return records_list
    matched: List = []
    seen: set[Tuple[str, str, Optional[str]]] = set()
    for spec in specs:
        for record in records_list:
            if _record_matches_spec(record, spec):
                key = (
                    getattr(record, "metric", ""),
                    getattr(record, "period", "") or "",
                    getattr(record, "source", None),
                )
                if key not in seen:
                    seen.add(key)
                    matched.append(record)
    return matched if matched else records_list


def _record_matches_spec(record: Any, spec: Dict[str, Any]) -> bool:
    """Return True when a metric record aligns with the requested period spec."""
    start = spec["start"]
    end = spec["end"]
    quarter = spec.get("quarter")
    year = getattr(record, "end_year", None) or getattr(record, "start_year", None)
    if year is None:
        year = _infer_year_from_period(getattr(record, "period", "") or "")
    if year is None or not (start <= year <= end):
        return False
    if quarter:
        period_label = (getattr(record, "period", "") or "").upper()
        if quarter not in period_label:
            return False
    return True


def _infer_year_from_period(period: str) -> Optional[int]:
    """Best-effort extraction of a fiscal year from a period label."""
    match = re.search(r"(19|20)\d{2}", period)
    if match:
        return int(match.group(0))
    return None


def _select_latest(records: Iterable, metric: str) -> Optional[Tuple[str, Optional[float]]]:
    """Return the most recent metric entries per ticker."""
    latest_period = None
    latest_value = None
    for record in records:
        if record.metric != metric:
            continue
        if latest_period is None or record.period > latest_period:
            latest_period = record.period
            latest_value = record.value
    if latest_period is None:
        return None
    return latest_period, latest_value


def _format_value_display(latest: Optional[Tuple[str, Optional[float]]]) -> str:
    """Format a metric value for display alongside units/notes."""
    if latest is None:
        return "-"
    period, value = latest
    if value is None:
        return f"- ({period})"
    return f"{_format_value(value)} ({period})"


def _format_value(value: Optional[float]) -> str:
    """Format numeric values with thousands separators and precision."""
    if value is None:
        return "-"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value/1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value/1_000:.1f}K"
    if abs_value >= 1:
        return f"{value:.2f}"
    return f"{value:.3f}"


def _metric_label(metric: str) -> str:
    """Return the human-readable label for a metric."""
    for definition in METRIC_DEFINITIONS:
        if definition.name == metric:
            return definition.description
    abbreviation = METRIC_ABBREVIATIONS.get(metric)
    if abbreviation:
        return abbreviation
    return metric.replace("_", " ").title()


def _build_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Construct a printable table structure from metric data."""
    if not rows:
        return "No data available."

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(values: Sequence[str]) -> str:
        """Format a row dictionary into a list of printable columns."""
        formatted = []
        for idx, value in enumerate(values):
            align = "<" if idx == 0 else ">"
            formatted.append(f"{value:{align}{widths[idx]}}")
        return " | ".join(formatted)

    header_line = format_row(headers)
    separator = "-+-".join("-" * width for width in widths)
    body = "\n".join(format_row(row) for row in rows)
    return "\n".join([header_line, separator, body])


def _chunked(sequence: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    """Yield items from an iterable in fixed-size chunks."""
    for index in range(0, len(sequence), size):
        yield sequence[index : index + size]


def _coerce_int(value: str) -> Optional[int]:
    """Convert strings to integers when possible, ignoring blanks."""
    try:
        return int(value)
    except ValueError:
        return None


def _clean_token(token: str) -> str:
    """Normalise raw tokens taken from user input."""
    return token.strip(string.punctuation)
