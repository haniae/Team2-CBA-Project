"""Shared helpers for rendering analytics tables from text commands."""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .analytics_engine import AGGREGATE_METRICS, AnalyticsEngine, BASE_METRICS, DERIVED_METRICS

MAX_METRIC_COLUMNS = 6

@dataclass(frozen=True)
class MetricDefinition:
    name: str
    description: str

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

METRIC_DEFINITIONS: List[MetricDefinition] = [
    MetricDefinition("revenue", "Revenue"),
    MetricDefinition("net_income", "Net income"),
    MetricDefinition("operating_income", "Operating income"),
    MetricDefinition("gross_profit", "Gross profit"),
    MetricDefinition("ebitda", "EBITDA"),
    MetricDefinition("free_cash_flow", "Free cash flow"),
    MetricDefinition("revenue_cagr", "Revenue CAGR"),
    MetricDefinition("eps_cagr", "EPS CAGR"),
    MetricDefinition("ebitda_growth", "EBITDA growth"),
    MetricDefinition("working_capital", "Working capital"),
    MetricDefinition("working_capital_change", "Working capital change"),
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
        remaining, period_filters, layout = _parse_year_filters(tokens)
    except ValueError:
        return "Invalid year filter. Use year=YYYY or years=YYYY-YYYY."

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

    if layout_mode in {"metrics", "metric", "rows", "matrix", "pivot"}:
        headers = ["Metric"] + tickers
        rows: List[List[str]] = []
        for metric in metrics:
            label = _metric_label(metric)
            row = [label]
            for ticker in tickers:
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
        for ticker in tickers:
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


def _parse_year_filters(tokens: Sequence[str]) -> Tuple[List[str], Optional[List[Tuple[int, int]]], Optional[str]]:
    period_filters: List[Tuple[int, int]] = []
    layout: Optional[str] = None
    remaining: List[str] = []

    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("year="):
            year = _coerce_int(cleaned.split("=", 1)[1])
            if year is None:
                raise ValueError
            period_filters.append((year, year))
            continue
        if cleaned.lower().startswith("years="):
            bounds = cleaned.split("=", 1)[1].split("-", 1)
            if len(bounds) != 2:
                raise ValueError
            start = _coerce_int(bounds[0])
            end = _coerce_int(bounds[1])
            if start is None or end is None:
                raise ValueError
            if end < start:
                start, end = end, start
            period_filters.append((start, end))
            continue
        if cleaned.lower().startswith("layout="):
            layout = cleaned.split("=", 1)[1].lower()
            continue
        remaining.append(cleaned)

    return remaining, (period_filters or None), layout


# Additional helpers (_resolve_metrics_and_tickers, _split_tickers_and_periods, etc.) will follow.


def _resolve_metrics_and_tickers(
    command: str,
    tokens: Sequence[str],
    period_filters: Optional[List[Tuple[int, int]]],
    layout: Optional[str],
) -> Tuple[List[str], List[str], Optional[List[Tuple[int, int]]], str]:
    layout_mode = (layout or "").lower()
    lowered = [token.lower() for token in tokens]

    if command == "table":
        if "metrics" not in lowered:
            raise ValueError(
                "Usage: table <tickers...> metrics <metrics...> [year=YYYY | years=YYYY-YYYY]"
            )
        split_index = lowered.index("metrics")
        tickers = _extract_tickers(tokens[:split_index])
        raw_metrics = tokens[split_index + 1 :]
        if not tickers or not raw_metrics:
            raise ValueError(
                "Usage: table <tickers...> metrics <metrics...> [year=YYYY | years=YYYY-YYYY]"
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


def _parse_year_filters(tokens: Sequence[str]) -> Tuple[List[str], Optional[List[Tuple[int, int]]], Optional[str]]:
    remaining: List[str] = []
    period_filters: List[Tuple[int, int]] = []
    layout: Optional[str] = None

    for token in tokens:
        cleaned = token.strip()
        lower = cleaned.lower()
        if lower.startswith("year="):
            year = _coerce_int(lower.split("=", 1)[1])
            if year is None:
                raise ValueError
            period_filters.append((year, year))
            continue
        if lower.startswith("years=") and "-" in lower:
            bounds = lower.split("=", 1)[1].split("-", 1)
            if len(bounds) != 2:
                raise ValueError
            start = _coerce_int(bounds[0])
            end = _coerce_int(bounds[1])
            if start is None or end is None:
                raise ValueError
            if end < start:
                start, end = end, start
            period_filters.append((start, end))
            continue
        if lower.startswith("layout="):
            layout = lower.split("=", 1)[1]
            continue
        remaining.append(cleaned)

    return remaining, (period_filters or None), layout


def _parse_period_token(token: str) -> Optional[Tuple[int, int]]:
    cleaned = token.strip().lower()
    if cleaned.startswith("fy") and cleaned[2:].isdigit():
        year = int(cleaned[2:])
        return (year, year)
    if cleaned.isdigit() and len(cleaned) == 4:
        year = int(cleaned)
        if 1900 <= year <= 2100:
            return (year, year)
    if "-" in cleaned:
        left, right = cleaned.split("-", 1)
        if left.isdigit() and right.isdigit():
            start = int(left)
            end = int(right)
            if end < start:
                start, end = end, start
            return (start, end)
    return None


def _select_latest(records: Iterable, metric: str) -> Optional[Tuple[str, Optional[float]]]:
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
    if latest is None:
        return "-"
    period, value = latest
    if value is None:
        return f"- ({period})"
    return f"{_format_value(value)} ({period})"


def _format_value(value: Optional[float]) -> str:
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
    for definition in METRIC_DEFINITIONS:
        if definition.name == metric:
            return definition.description
    abbreviation = METRIC_ABBREVIATIONS.get(metric)
    if abbreviation:
        return abbreviation
    return metric.replace("_", " ").title()


def _build_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return "No data available."

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(values: Sequence[str]) -> str:
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
    for index in range(0, len(sequence), size):
        yield sequence[index : index + size]


def _coerce_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None


def _clean_token(token: str) -> str:
    return token.strip(string.punctuation)
