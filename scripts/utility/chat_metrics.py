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
    """Optionally ingest fresh data so summaries reflect recent filings.

    Args:
        tickers: Iterable of ticker symbols the user asked to refresh.
        years: Number of fiscal years of history to request.
    """

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
    """Construct the chatbot and analytics engine backing the CLI session.

    Returns:
        Tuple ``(chatbot, engine)`` primed with refreshed metrics.
    """
    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    return bot, engine


def run_chatbot(tickers: Sequence[str], years: int) -> None:
    """Run the interactive BenchmarkOS chat loop.

    Args:
        tickers: Optional tickers to ingest before conversation begins.
        years: Number of fiscal years to fetch during ingestion.
    """
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
    """Route a user prompt to metrics, ingestion, scenario, or LLM handlers.

    Args:
        prompt: Raw user text from stdin.
        bot: Chatbot instance for free-form questions.
        engine: Analytics engine for metrics-oriented commands.
    Returns:
        Response text ready to print.
    """

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
    """Parse a `metrics` command and extract ticker symbols.

    Args:
        text: Raw user command string.
    Returns:
        List of ticker tokens or ``None`` if the command does not match.
    """
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
    """Render a comparison table string for the provided tickers.

    Args:
        engine: Analytics engine used to fetch metric snapshots.
        tickers: Ordered tickers to include in the comparison.
    Returns:
        Table formatted as plain text.
    """
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
    """Format a metric value with appropriate precision and suffix.

    Args:
        metric_name: Metric identifier to look up.
        metrics: Mapping of metric names to records for a ticker.
    Returns:
        Human readable string or ``"n/a"`` when missing.
    """
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
    """Render headers and rows into a markdown-style table.

    Args:
        headers: Column headings for the table.
        rows: Body rows of value strings.
    Returns:
        String ready for console output.
    """
    if not rows:
        return "No metrics available."

    alignments = ["left"] + ["right"] * (len(headers) - 1)
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(values: Sequence[str]) -> str:
        """Format a table row applying stored column widths/alignments."""
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
    """Process an `ingest` command and refresh requested tickers.

    Args:
        prompt: Full user command containing tickers/years.
        engine: Analytics engine to refresh after ingestion.
    Returns:
        Status message describing the ingestion outcome.
    """
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
    """Execute a scenario command and return the generated narrative.

    Args:
        prompt: Scenario command with ticker and adjustments.
        engine: Analytics engine used to calculate the scenario.
    Returns:
        Narrative string or an error message.
    """
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
    """Convert a percentage token such as '+5%' into a decimal float.

    Args:
        token: Percentage token to parse.
    Returns:
        Parsed decimal (e.g. 0.05).
    """
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
