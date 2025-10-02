
"""Command-line entry point for the BenchmarkOS chatbot."""

from __future__ import annotations

import string
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from benchmarkos_chatbot import AnalyticsEngine, BenchmarkOSChatbot, load_settings
from benchmarkos_chatbot.analytics_engine import AGGREGATE_METRICS, BASE_METRICS, DERIVED_METRICS

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
    "pb": "pb_ratio",
    "p/b": "pb_ratio",
    "peg": "peg_ratio",
    "divyield": "dividend_yield",
    "dividendyield": "dividend_yield",
    "buyback": "share_buyback_intensity",
    "buybacks": "share_buyback_intensity",
    "cfo": "cash_from_operations",
    "cff": "cash_from_financing",
    "cash": "cash_and_cash_equivalents",
}

FILLER_WORDS = {"and", "vs", "versus", "between", "against", "with", "on", "for", "the"}

_ALL_METRICS_SET = set(BASE_METRICS) | set(DERIVED_METRICS) | set(AGGREGATE_METRICS)


def _build_metric_order() -> List[str]:
    order: List[str] = []
    for metric in PDS_METRICS:
        if metric in _ALL_METRICS_SET and metric not in order:
            order.append(metric)
    for metric in [
        "revenue",
        "net_income",
        "operating_income",
        "gross_profit",
        "cash_from_operations",
        "free_cash_flow",
        "cash_from_financing",
        "shares_outstanding",
        "total_assets",
        "total_liabilities",
        "shareholders_equity",
    ]:
        if metric in _ALL_METRICS_SET and metric not in order:
            order.append(metric)
    for metric in sorted(_ALL_METRICS_SET):
        if metric not in order:
            order.append(metric)
    return order

ALL_METRICS_ORDER = _build_metric_order()
ALL_METRICS_SET = set(ALL_METRICS_ORDER)


def _metric_label(metric: str) -> str:
    return METRIC_ABBREVIATIONS.get(metric, metric.replace("_", " ").title())


def _chunked(seq: Sequence[str], size: int) -> Iterable[List[str]]:
    for idx in range(0, len(seq), size):
        yield list(seq[idx : idx + size])


def _clean_token(token: str) -> str:
    return token.strip(string.punctuation)


def _extract_tickers(tokens: Sequence[str]) -> List[str]:
    tickers: List[str] = []
    for token in tokens:
        cleaned = _clean_token(token)
        if not cleaned:
            continue
        if cleaned.lower() in FILLER_WORDS:
            continue
        tickers.append(cleaned.upper())
    return tickers


def _canonical_metric(token: str) -> str:
    key = token.lower()
    normalised = key.replace("/", "").replace("-", "")
    if normalised in METRIC_SYNONYMS:
        return METRIC_SYNONYMS[normalised]
    if key in METRIC_SYNONYMS:
        return METRIC_SYNONYMS[key]
    return key


def _expand_metrics(raw_metrics: Sequence[str]) -> List[str]:
    if not raw_metrics:
        return ALL_METRICS_ORDER.copy()

    expanded: List[str] = []
    seen: set[str] = set()
    for raw in raw_metrics:
        token = _clean_token(raw)
        if not token:
            continue
        key = token.lower()
        if key == "all":
            return ALL_METRICS_ORDER.copy()
        canonical = _canonical_metric(token)
        if canonical in ALL_METRICS_SET and canonical not in seen:
            expanded.append(canonical)
            seen.add(canonical)
    if not expanded:
        return ALL_METRICS_ORDER.copy()
    return expanded


def _format_value(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value:,.2f}"


def _select_latest(records, metric: str) -> Optional[Tuple[str, Optional[float]]]:
    best: Optional[Tuple[str, Optional[float], int]] = None
    for record in records:
        if record.metric != metric:
            continue
        year = record.end_year or record.start_year or 0
        if best is None or year > best[2]:
            best = (record.period, record.value, year)
    if best is None:
        return None
    period, value, _ = best
    return period, value


def _build_table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def _render_line(parts: Sequence[str]) -> str:
        return " | ".join(part.ljust(widths[idx]) for idx, part in enumerate(parts))

    divider = "-+-".join("-" * width for width in widths)
    output = [_render_line(headers), divider]
    output.extend(_render_line(row) for row in rows)
    return "\n".join(output)


def _parse_year_filters(tokens: List[str]) -> Tuple[List[str], Optional[Sequence[Tuple[int, int]]], Optional[str]]:
    period_filters: Optional[List[Tuple[int, int]]] = None
    layout: Optional[str] = None
    filtered_tokens: List[str] = []
    for token in tokens:
        lower = token.lower()
        if lower.startswith("year="):
            value = lower.split("=", 1)[1]
            period_filters = [(int(value), int(value))]
        elif lower.startswith("years=") and "-" in token:
            value = lower.split("=", 1)[1]
            start_str, end_str = value.split("-", 1)
            start_year = int(start_str)
            end_year = int(end_str)
            if start_year > end_year:
                start_year, end_year = end_year, start_year
            period_filters = [(start_year, end_year)]
        elif lower.startswith("layout="):
            layout = lower.split("=", 1)[1]
        else:
            filtered_tokens.append(token)
    return filtered_tokens, period_filters, layout


def _resolve_metrics_and_tickers(
    command: str,
    tokens: List[str],
    period_filters: Optional[Sequence[Tuple[int, int]]],
    layout: Optional[str],
) -> Tuple[List[str], List[str], Optional[Sequence[Tuple[int, int]]], str]:
    layout_mode = (layout or "").lower()
    lowered = [token.lower() for token in tokens]

    if command == "table":
        if "metrics" not in lowered:
            raise ValueError("Usage: table <tickers...> metrics <metrics...> [year=YYYY | years=YYYY-YYYY]")
        split_index = lowered.index("metrics")
        tickers = _extract_tickers(tokens[:split_index])
        raw_metrics = tokens[split_index + 1 :]
        if not tickers or not raw_metrics:
            raise ValueError("Usage: table <tickers...> metrics <metrics...> [year=YYYY | years=YYYY-YYYY]")
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

    if anchor_index is None:
        raw_metrics = ["all"]

    metrics = _expand_metrics(raw_metrics)
    return tickers, metrics, period_filters, layout_mode


def _try_table_command(user_input: str, engine: AnalyticsEngine) -> Optional[str]:
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
                if latest is None:
                    row.append("-")
                else:
                    period, value = latest
                    row.append(f"{_format_value(value)} ({period})")
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
                if latest is None:
                    row.append("-")
                else:
                    period, value = latest
                    row.append(f"{_format_value(value)} ({period})")
            rows.append(row)

        table = _build_table(headers, rows)
        if total_chunks > 1:
            metric_label = ", ".join(metric.replace("_", " ") for metric in metric_subset)
            title = f"Metrics {index}/{total_chunks}: {metric_label}"
            table = title + "\n" + table
        tables.append(table)

    return "\n\n".join(tables)


def main() -> None:
    settings = load_settings()
    chatbot = BenchmarkOSChatbot.create(settings)
    analytics = AnalyticsEngine(settings)

    print("BenchmarkOS Chatbot (type 'exit' to quit)")
    print()

    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Exiting...")
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        table_output = _try_table_command(user_input, analytics)
        if table_output is not None:
            print()
            print(table_output)
            print()
            continue

        response = chatbot.ask(user_input)
        print(f"Bot: {response}")
        print()

    db_path = Path(settings.database_path)
    if db_path.exists():
        print(f"Conversation saved to {db_path}")


if __name__ == "__main__":  # pragma: no cover - CLI not unit tested
    main()
