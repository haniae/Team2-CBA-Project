"""Interactive runner that exposes BenchmarkOS metrics and SEC ingestion."""

from __future__ import annotations

import argparse
import re
from typing import Dict, List, Sequence

from benchmarkos_chatbot import BenchmarkOSChatbot, AnalyticsEngine, load_settings
from benchmarkos_chatbot.analytics_engine import METRIC_DEFINITIONS
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers
from benchmarkos_chatbot.database import MetricRecord

# Metric formatting categories reused from the analytics summary.
PERCENT_METRICS = {
    "revenue_cagr_3y",
    "eps_cagr_3y",
    "adjusted_ebitda_margin",
    "return_on_equity",
    "fcf_margin",
    "return_on_assets",
    "operating_margin",
    "net_margin",
    "cash_conversion_ratio",
    "tsr_3y",
    "dividend_yield",
}

MULTIPLE_METRICS = {
    "net_debt_to_ebitda",
    "ev_to_adjusted_ebitda",
    "peg_ratio",
    "working_capital_turnover",
    "buyback_intensity",
    "pe_ratio",
    "pb_ratio",
}


def ingest_if_requested(tickers: Sequence[str], years: int) -> None:
    """Optionally run live ingestion before entering the chat."""

    if not tickers:
        return

    tickers = [ticker.upper() for ticker in tickers]
    settings = load_settings()
    report = ingest_live_tickers(settings, tickers, years=years)

    AnalyticsEngine(settings).refresh_metrics(force=True)
    companies = ", ".join(report.companies)
    print(
        f"Ingested {report.records_loaded} normalised facts covering: {companies}."
    )


def build_chatbot() -> tuple[BenchmarkOSChatbot, AnalyticsEngine]:
    """Initialise a chatbot and analytics engine ready for interactive use."""
    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    return bot, engine


def run_chatbot(tickers: Sequence[str], years: int) -> None:
    """Launch the REPL-style chat experience, optionally ingesting data first."""
    ingest_if_requested(tickers, years)
    bot, engine = build_chatbot()

    print("BenchmarkOS Finance Chat (type 'help' for commands, 'exit' to quit)\n")
    while True:
        try:
            prompt = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break

        if prompt.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        response = dispatch_prompt(prompt, bot, engine)
        print(f"Bot: {response}\n")


def dispatch_prompt(prompt: str, bot: BenchmarkOSChatbot, engine: AnalyticsEngine) -> str:
    """Route the user request to the right handler."""

    metrics_request = parse_metrics_request(prompt)
    if metrics_request is not None:
        if not metrics_request:
            return "Provide at least one ticker for 'metrics'."
        tickers = [ticker.upper() for ticker in metrics_request]
        if len(tickers) == 1:
            return engine.generate_summary(tickers[0])
        return format_metrics_table(engine, tickers)

    lowered = prompt.strip().lower()
    if lowered == "help":
        return (
            "Commands:\n"
            "  metrics <TICKER>[ vs <OTHER>…] – KPI summary or comparison table\n"
            "  compare <TICKER> <OTHER> [MORE] – comparison table shorthand\n"
            "  ingest <TICKER> [years]        – fetch SEC/Yahoo data and refresh\n"
            "  scenario <T> <NAME> rev=+5% margin=+1% mult=+0.5% – run what-if\n"
            "  anything else                  – forwarded to the LLM"
        )

    if lowered.startswith("compare "):
        tickers = [token.upper() for token in prompt.split()[1:]]
        if len(tickers) < 2:
            return "Usage: compare <TICKER_A> <TICKER_B> [MORE]"
        return format_metrics_table(engine, tickers)

    if lowered.startswith("ingest "):
        return handle_ingest(prompt, engine)

    if lowered.startswith("scenario "):
        return handle_scenario(prompt, engine)

    return bot.ask(prompt)


_METRICS_PATTERN = re.compile(r"^metrics(?:(?:\s+for)?\s+)(.+)$", re.IGNORECASE)


def parse_metrics_request(text: str) -> list[str] | None:
    """Parse 'metrics' commands into a list of tickers."""
    match = _METRICS_PATTERN.match(text.strip())
    if not match:
        return None

    remainder = match.group(1)
    remainder = remainder.replace(",", " ")
    remainder = remainder.replace(" vs ", " ")
    remainder = remainder.replace(" and ", " ")
    tokens = [token for token in remainder.split() if token]
    return tokens


def format_metrics_table(engine: AnalyticsEngine, tickers: Sequence[str]) -> str:
    """Render metrics for the supplied tickers as a comparison table."""
    metrics_per_ticker: Dict[str, Dict[str, MetricRecord]] = {}
    for ticker in tickers:
        records = engine.get_metrics(ticker)
        metrics_per_ticker[ticker] = {record.metric: record for record in records}

    headers = ["Metric"] + list(tickers)
    rows: List[List[str]] = []
    for definition in METRIC_DEFINITIONS:
        label = definition.description
        row = [label]
        for ticker in tickers:
            row.append(format_metric_value(definition.name, metrics_per_ticker[ticker]))
        rows.append(row)

    return render_table(headers, rows)


def format_metric_value(metric_name: str, metrics: Dict[str, MetricRecord]) -> str:
    """Format a metric value with the right precision and suffix."""
    record = metrics.get(metric_name)
    if not record or record.value is None:
        return "n/a"

    value = record.value
    if metric_name in PERCENT_METRICS:
        return f"{value:.1%}"
    if metric_name in MULTIPLE_METRICS:
        return f"{value:.2f}"
    return f"{value:,.0f}"


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render rows and headers into a markdown-style table."""
    if not rows:
        return "No metrics available."

    alignments = ["left"] + ["right"] * (len(headers) - 1)
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(values: Sequence[str]) -> str:
        """Format a MetricRecord into printable table cells."""
        formatted = []
        for idx, value in enumerate(values):
            if alignments[idx] == "left":
                formatted.append(value.ljust(widths[idx]))
            else:
                formatted.append(value.rjust(widths[idx]))
        return " | ".join(formatted)

    header_line = format_row(headers)
    separator = "-+-".join("-" * width for width in widths)
    body = "\n".join(format_row(row) for row in rows)
    return "\n".join([header_line, separator, body])


def handle_ingest(text: str, engine: AnalyticsEngine) -> str:
    """Run on-demand data ingestion triggered from the chat UI."""
    parts = text.split()
    if len(parts) < 2:
        return "Usage: ingest <TICKER> [years]"

    ticker = parts[1].upper()
    years = int(parts[2]) if len(parts) >= 3 else 5
    settings = load_settings()
    report = ingest_live_tickers(settings, [ticker], years=years)
    engine.refresh_metrics(force=True)
    return (
        f"Live ingestion complete for {ticker}. "
        f"Loaded {report.records_loaded} facts; metrics refreshed."
    )


def handle_scenario(text: str, engine: AnalyticsEngine) -> str:
    """Execute a simple scenario model and return the narrative."""
    parts = text.split()
    if len(parts) < 3:
        return "Usage: scenario <TICKER> <NAME> [rev=+5% margin=+1% mult=+0.5%]"

    ticker = parts[1].upper()
    name = parts[2]

    kwargs = {
        "revenue_growth_delta": 0.0,
        "ebitda_margin_delta": 0.0,
        "multiple_delta": 0.0,
    }

    for token in parts[3:]:
        token_lower = token.lower()
        if token_lower.startswith("rev="):
            kwargs["revenue_growth_delta"] = parse_percent(token_lower.split("=", 1)[1])
        elif token_lower.startswith("margin="):
            kwargs["ebitda_margin_delta"] = parse_percent(token_lower.split("=", 1)[1])
        elif token_lower.startswith("mult="):
            kwargs["multiple_delta"] = parse_percent(token_lower.split("=", 1)[1])

    summary = engine.run_scenario(ticker, scenario_name=name, **kwargs)
    return summary.narrative


def parse_percent(value: str) -> float:
    """Convert percentage tokens (e.g. '+5%') into floats."""
    value = value.strip().rstrip("%")
    try:
        return float(value) / 100.0
    except ValueError:
        return 0.0


def main() -> None:
    """CLI entry point that launches the interactive metrics chat tool."""
    parser = argparse.ArgumentParser(
        description="BenchmarkOS finance chatbot runner with analytics shortcuts"
    )
    parser.add_argument(
        "--ingest",
        nargs="*",
        default=[],
        help="Tickers to ingest from SEC/Yahoo before starting the chat",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of fiscal years to pull when ingesting (default: 5)",
    )
    args = parser.parse_args()
    run_chatbot(args.ingest or [], args.years)


if __name__ == "__main__":
    main()
