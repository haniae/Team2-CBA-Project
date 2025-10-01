"""Core chatbot orchestration logic with analytics-aware intents."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import database
from .analytics_engine import AnalyticsEngine, METRIC_DEFINITIONS
from .config import Settings
from .data_ingestion import IngestionReport, ingest_financial_data, ingest_live_tickers
from .llm_client import LLMClient, build_llm_client

# Metric formatting categories mirrored from analytics_engine.generate_summary
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

_METRICS_PATTERN = re.compile(r"^metrics(?:(?:\s+for)?\s+)(.+)$", re.IGNORECASE)


@dataclass
class Conversation:
    """Tracks a single chat session."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Mapping[str, str]] = field(default_factory=list)

    def as_llm_messages(self) -> List[Mapping[str, str]]:
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self.messages]


SYSTEM_PROMPT = (
    "You are BenchmarkOS, an institutional-grade finance analyst.\n"
    "You deliver precise, compliant insights grounded in the latest SEC filings,"
    " market data, and risk controls. Provide actionable intelligence in clear "
    "professional language. If you are unsure, request clarification or state "
    "explicitly that more data is required."
)


@dataclass
class BenchmarkOSChatbot:
    """High-level interface wrapping the entire chatbot pipeline."""

    settings: Settings
    llm_client: LLMClient
    analytics_engine: AnalyticsEngine
    ingestion_report: Optional[IngestionReport] = None
    conversation: Conversation = field(default_factory=Conversation)

    @classmethod
    def create(cls, settings: Settings) -> "BenchmarkOSChatbot":
        llm_client = build_llm_client(
            settings.llm_provider,
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

        database.initialise(settings.database_path)

        ingestion_report: Optional[IngestionReport] = None
        try:
            ingestion_report = ingest_financial_data(settings)
        except Exception as exc:  # pragma: no cover - defensive guard
            database.record_audit_event(
                settings.database_path,
                database.AuditEvent(
                    event_type="ingestion_error",
                    entity_id="startup",
                    details=f"Bootstrap ingestion failed: {exc}",
                    created_at=datetime.utcnow(),
                    created_by="chatbot",
                ),
            )

        analytics_engine = AnalyticsEngine(settings)
        analytics_engine.refresh_metrics(force=True)

        return cls(
            settings=settings,
            llm_client=llm_client,
            analytics_engine=analytics_engine,
            ingestion_report=ingestion_report,
        )

    def ask(self, user_input: str) -> str:
        """Generate a reply and persist both sides of the exchange."""

        timestamp = datetime.utcnow()
        database.log_message(
            self.settings.database_path,
            self.conversation.conversation_id,
            role="user",
            content=user_input,
            created_at=timestamp,
        )
        self.conversation.messages.append({"role": "user", "content": user_input})

        reply = self._handle_financial_intent(user_input)
        if reply is None:
            reply = self.llm_client.generate_reply(self.conversation.as_llm_messages())

        database.log_message(
            self.settings.database_path,
            self.conversation.conversation_id,
            role="assistant",
            content=reply,
            created_at=datetime.utcnow(),
        )
        self.conversation.messages.append({"role": "assistant", "content": reply})
        return reply

    def history(self) -> Iterable[database.Message]:
        """Return the stored conversation from the database."""

        return database.fetch_conversation(
            self.settings.database_path, self.conversation.conversation_id
        )

    def reset(self) -> None:
        """Start a fresh conversation while keeping the same configuration."""

        self.conversation = Conversation()

    # ------------------------------------------------------------------
    # Intent handling helpers
    # ------------------------------------------------------------------

    def _handle_financial_intent(self, text: str) -> Optional[str]:
        metrics_request = self._parse_metrics_request(text)
        if metrics_request is not None:
            if not metrics_request.tickers:
                return "Provide at least one ticker for metrics."
            resolution = self._resolve_tickers(metrics_request.tickers)
            if resolution.missing:
                return self._format_missing_message(metrics_request.tickers, resolution.available)
            return self._dispatch_metrics_request(
                resolution.available, metrics_request.period_filters
            )

        lowered = text.strip().lower()
        if lowered == "help":
            help_text = "\n".join(
                [
                    "Commands:",
                    "  metrics <TICKER> [YYYY | YYYY-YYYY] [vs <OTHER>...] - KPI summary or comparison table",
                    "  compare <TICKER_A> <TICKER_B> [MORE] [YYYY]        - metric comparison",
                    "  fact <TICKER> <YEAR> [metric]                     - show raw financial facts",
                    "  audit <TICKER> [YEAR]                             - recent audit trail entries",
                    "  ingest <TICKER> [years]                           - fetch SEC/Yahoo data and refresh",
                    "  scenario <T> <NAME> rev=+5% margin=+1% mult=+0.5% - run what-if",
                    "  anything else                                    - answered via the language model",
                ]
            )
            return help_text
        if lowered.startswith("compare "):
            tokens = text.split()[1:]
            return self._handle_metrics_comparison(tokens)

        if lowered.startswith("fact "):
            return self._handle_fact_command(text)

        if lowered.startswith("audit "):
            return self._handle_audit_command(text)

        if lowered.startswith("ingest "):
            return self._handle_ingest_command(text)

        if lowered.startswith("scenario "):
            return self._handle_scenario_command(text)

        return None
    def _handle_metrics_comparison(self, tokens: Sequence[str]) -> str:
        cleaned_tokens: List[str] = []
        for token in tokens:
            stripped = token.strip()
            if not stripped:
                continue
            upper = stripped.upper().rstrip(',')
            if upper in {"VS", "AND", "FOR"}:
                continue
            cleaned_tokens.append(stripped)

        tickers, period_filters = self._split_tickers_and_periods(cleaned_tokens)
        if len(tickers) < 2:
            return "Usage: compare <TICKER_A> <TICKER_B> [MORE] [YEAR]"
        resolution = self._resolve_tickers(tickers)
        if resolution.missing:
            return self._format_missing_message(tickers, resolution.available)
        return self._format_metrics_table(
            resolution.available, period_filters=period_filters
        )

    def _dispatch_metrics_request(
        self,
        tickers: Sequence[str],
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
    ) -> str:
        if not tickers:
            return "Provide at least one ticker for metrics."
        if len(tickers) == 1 and not period_filters:
            return self.analytics_engine.generate_summary(tickers[0])
        return self._format_metrics_table(
            tickers,
            period_filters=period_filters,
        )


    def _handle_ingest_command(self, text: str) -> str:
        parts = text.split()
        if len(parts) < 2:
            return "Usage: ingest <TICKER> [years]"
        ticker = parts[1].upper()
        years = 5
        if len(parts) >= 3:
            try:
                years = int(parts[2])
            except ValueError:
                return "Years must be an integer (e.g. ingest TSLA 5)."

        report = ingest_live_tickers(self.settings, [ticker], years=years)
        self.analytics_engine.refresh_metrics(force=True)
        companies = ", ".join(report.companies)
        return (
            f"Live ingestion complete for {companies or ticker}. "
            f"Loaded {report.records_loaded} facts; metrics refreshed."
        )

    def _handle_scenario_command(self, text: str) -> str:
        parts = text.split()
        if len(parts) < 3:
            return "Usage: scenario <TICKER> <NAME> [rev=+5% margin=+1% mult=+0.5%]"

        ticker = parts[1].upper()
        name = parts[2]
        deltas = {
            "revenue_growth_delta": 0.0,
            "ebitda_margin_delta": 0.0,
            "multiple_delta": 0.0,
        }
        for token in parts[3:]:
            token_lower = token.lower()
            if token_lower.startswith("rev="):
                deltas["revenue_growth_delta"] = self._parse_percent(token_lower[4:])
            elif token_lower.startswith("margin="):
                deltas["ebitda_margin_delta"] = self._parse_percent(token_lower[7:])
            elif token_lower.startswith("mult="):
                deltas["multiple_delta"] = self._parse_percent(token_lower[5:])

        summary = self.analytics_engine.run_scenario(
            ticker,
            scenario_name=name,
            **deltas,
        )
        return summary.narrative

    # Fact and audit helpers
    # ------------------------------------------------------------------
    def _handle_fact_command(self, text: str) -> str:
        match = re.match(r"fact\s+([A-Za-z0-9.-]+)\s+(?:FY)?(\d{4})(?:\s+([A-Za-z0-9_]+))?", text, re.IGNORECASE)
        if not match:
            return "Usage: fact <TICKER> <YEAR> [metric]"
        raw_ticker = match.group(1).upper()
        fiscal_year = int(match.group(2))
        metric = match.group(3)
        metric_key = metric.lower() if metric else None

        resolution = self._resolve_tickers([raw_ticker])
        if resolution.missing and not resolution.available:
            return self._format_missing_message([raw_ticker], [])
        ticker = resolution.available[0] if resolution.available else raw_ticker

        facts = self.analytics_engine.financial_facts(
            ticker,
            fiscal_year=fiscal_year,
            metric=metric_key,
            limit=20,
        )
        if not facts:
            if metric_key:
                return (
                    f"No {metric_key} facts stored for {ticker} in FY{fiscal_year}."
                )
            return f"No financial facts stored for {ticker} in FY{fiscal_year}."

        title_metric = metric_key.replace('_', ' ') if metric_key else 'financial facts'
        lines_out = [f"{title_metric.title()} for {ticker} FY{fiscal_year}:"]
        for fact in facts:
            label = fact.metric.replace('_', ' ')
            value_text = self._format_fact_value(fact.value)
            parts = [f"source={fact.source}"]
            if fact.adjusted:
                parts.append("adjusted")
            if fact.adjustment_note:
                parts.append(f"note: {fact.adjustment_note}")
            detail = ", ".join(parts)
            lines_out.append(f"- {label}: {value_text} ({detail})")
        return "\n".join(lines_out)

    def _handle_audit_command(self, text: str) -> str:
        match = re.match(r"audit\s+([A-Za-z0-9.-]+)(?:\s+(?:FY)?(\d{4}))?", text, re.IGNORECASE)
        if not match:
            return "Usage: audit <TICKER> [YEAR]"
        raw_ticker = match.group(1).upper()
        year_token = match.group(2)
        fiscal_year = int(year_token) if year_token else None

        resolution = self._resolve_tickers([raw_ticker])
        if resolution.missing and not resolution.available:
            return self._format_missing_message([raw_ticker], [])
        ticker = resolution.available[0] if resolution.available else raw_ticker

        events = self.analytics_engine.audit_events(
            ticker,
            fiscal_year=fiscal_year,
            limit=10,
        )
        if not events:
            suffix = f" in FY{fiscal_year}" if fiscal_year else ""
            return f"No audit events recorded for {ticker}{suffix}."

        header = f"Audit trail for {ticker}"
        if fiscal_year:
            header += f" FY{fiscal_year}"
        lines_out = [header + ":"]
        for event in events:
            timestamp = event.created_at.strftime("%Y-%m-%d %H:%M")
            entity = f" [{event.entity_id}]" if event.entity_id else ""
            lines_out.append(
                f"- {timestamp}{entity} ({event.event_type}) {event.details} [by {event.created_by}]"
            )
        return "\n".join(lines_out)

    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_percent(value: str) -> float:
        value = value.strip().rstrip("%")
        try:
            return float(value) / 100.0
        except ValueError:
            return 0.0

    def _parse_metrics_request(self, text: str) -> Optional["BenchmarkOSChatbot._MetricsRequest"]:
        match = _METRICS_PATTERN.match(text.strip())
        if not match:
            return None
        remainder = match.group(1)
        remainder = remainder.replace(",", " ")
        remainder = remainder.replace(" vs ", " ")
        remainder = remainder.replace(" and ", " ")
        tokens = [token for token in remainder.split() if token]
        tickers, period_filters = self._split_tickers_and_periods(tokens)
        return BenchmarkOSChatbot._MetricsRequest(
            tickers=tickers,
            period_filters=period_filters,
        )
    # ------------------------------------------------------------------
    def _split_tickers_and_periods(
        self, tokens: Sequence[str]
    ) -> tuple[List[str], Optional[List[tuple[int, int]]]]:
        period_filters: List[tuple[int, int]] = []
        tickers: List[str] = []
        for token in tokens:
            parsed = self._parse_period_token(token)
            if parsed:
                period_filters.append(parsed)
                continue
            cleaned = token.strip().upper().rstrip(',')
            if not cleaned or cleaned in {"VS", "AND", "FOR"}:
                continue
            tickers.append(cleaned)
        return tickers, (period_filters or None)

    @staticmethod
    def _parse_period_token(token: str) -> Optional[tuple[int, int]]:
        cleaned = token.strip().upper().rstrip(',')
        if cleaned.startswith('FY'):
            cleaned = cleaned[2:]
        cleaned = cleaned.strip()
        if not cleaned:
            return None
        match = re.fullmatch(r"(\d{4})(?:\s*[-/]\s*(\d{4}))?", cleaned)
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        if end < start:
            start, end = end, start
        return (start, end)
    # Metrics formatting helpers
    # ------------------------------------------------------------------

    @dataclass
    class _MetricsRequest:
        tickers: List[str]
        period_filters: Optional[List[tuple[int, int]]]

    @dataclass
    class _TickerResolution:
        available: List[str]
        missing: List[str]

    def _resolve_tickers(self, subjects: Sequence[str]) -> "BenchmarkOSChatbot._TickerResolution":
        available: List[str] = []
        missing: List[str] = []
        for subject in subjects:
            resolved = self.analytics_engine.lookup_ticker(subject, allow_partial=True)
            if resolved:
                if resolved not in available:
                    available.append(resolved)
            else:
                missing.append(subject)
        return BenchmarkOSChatbot._TickerResolution(available=available, missing=missing)

    def _format_missing_message(
        self, requested: Sequence[str], available: Sequence[str]
    ) -> str:
        missing = [ticker for ticker in requested if ticker.upper() not in available]
        hint = ", ".join(sorted(set(available))) if available else None
        if hint:
            return (
                "Unable to resolve one or more tickers. Try specifying: "
                f"{hint}."
            )
        missing_list = ", ".join(missing)
        return (
            f"Unable to resolve: {missing_list}. Ingest the data first using "
            "'ingest <ticker>'."
        )

    def _format_metrics_table(
        self,
        tickers: Sequence[str],
        *,
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
    ) -> str:
        metrics_per_ticker: Dict[str, Dict[str, database.MetricRecord]] = {}
        missing: List[str] = []
        latest_spans: Dict[str, tuple[int, int]] = {}
        for ticker in tickers:
            records = self.analytics_engine.get_metrics(
                ticker,
                period_filters=period_filters,
            )
            if not records:
                missing.append(ticker)
                continue
            selected = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            metrics_per_ticker[ticker] = selected
            if selected:
                span = max(
                    (
                        self.analytics_engine._period_span(record.period)
                        for record in selected.values()
                    ),
                    key=lambda value: value[1],
                )
                latest_spans[ticker] = span

        if not metrics_per_ticker:
            if period_filters:
                desc = self._describe_period_filters(period_filters)
                return f"No metrics available for {', '.join(tickers)} in {desc}."
            return "No metrics available for the requested tickers."

        ordered_tickers = [ticker for ticker in tickers if ticker in metrics_per_ticker]
        headers = ["Metric"] + ordered_tickers
        rows: List[List[str]] = []
        for definition in METRIC_DEFINITIONS:
            label = definition.description
            row = [label]
            for ticker in ordered_tickers:
                row.append(
                    self._format_metric_value(
                        definition.name, metrics_per_ticker[ticker]
                    )
                )
            rows.append(row)

        descriptor_filters: List[tuple[int, int]]
        if period_filters:
            descriptor_filters = list(period_filters)
        else:
            descriptor_filters = list(latest_spans.values())
        descriptor = (
            self._describe_period_filters(descriptor_filters)
            if descriptor_filters
            else "latest available"
        )

        highlights = self._compose_benchmark_summary(metrics_per_ticker)

        output_lines: List[str] = []
        if highlights:
            bullet_points = "\n".join(f"- {line}" for line in highlights)
            output_lines.append(
                f"Benchmark summary for {', '.join(ordered_tickers)} ({descriptor}):\n{bullet_points}\n"
            )
        else:
            output_lines.append(
                f"Benchmark results for {', '.join(ordered_tickers)} ({descriptor})."
            )

        output_lines.append(self._render_table(headers, rows))
        if missing:
            context = (
                self._describe_period_filters(period_filters)
                if period_filters
                else "the requested periods"
            )
            output_lines.append(
                f"No metrics for {', '.join(missing)} in {context}."
            )
        return "\n".join(output_lines)

    def _describe_period_filters(
        self, period_filters: Sequence[tuple[int, int]]
    ) -> str:
        labels = []
        for start, end in period_filters:
            if start == 0 and end == 0:
                continue
            if start == end:
                labels.append(f"FY{start}")
            else:
                labels.append(f"FY{start}-FY{end}")
        return ", ".join(labels) if labels else "the requested periods"

    def _select_latest_records(
        self,
        records: Iterable[database.MetricRecord],
        *,
        span_fn,
    ) -> Dict[str, database.MetricRecord]:
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

    def _compose_benchmark_summary(
        self, metrics_per_ticker: Dict[str, Dict[str, database.MetricRecord]]
    ) -> List[str]:
        if not metrics_per_ticker:
            return []
        key_metrics = {
            "adjusted_ebitda_margin": "Adjusted EBITDA margin",
            "net_margin": "Adjusted net margin",
            "return_on_equity": "Return on equity",
            "pe_ratio": "P/E ratio",
        }
        highlights: List[str] = []
        for metric, label in key_metrics.items():
            best_ticker: Optional[str] = None
            best_value: Optional[float] = None
            for ticker, records in metrics_per_ticker.items():
                record = records.get(metric)
                if not record or record.value is None:
                    continue
                if best_value is None or record.value > best_value:
                    best_value = record.value
                    best_ticker = ticker
            if best_ticker is None or best_value is None:
                continue
            display = self._format_metric_value(metric, metrics_per_ticker[best_ticker])
            highlights.append(f"{label}: {best_ticker} {display}")
        return highlights

    @staticmethod
    def _format_metric_value(
        metric_name: str, metrics: Dict[str, database.MetricRecord]
    ) -> str:
        record = metrics.get(metric_name)
        if not record or record.value is None:
            return "n/a"
        value = record.value
        if metric_name in PERCENT_METRICS:
            return f"{value:.1%}"
        if metric_name in MULTIPLE_METRICS:
            return f"{value:.2f}"
        return f"{value:,.0f}"

    @staticmethod
    def _format_fact_value(value: float) -> str:
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"{value/1_000_000:,.2f}M"
        if absolute >= 1_000:
            return f"{value:,.0f}"
        if absolute >= 10:
            return f"{value:,.2f}"
        return f"{value:.4f}"

    @staticmethod
    def _render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
        if not rows:
            return "No data available."

        alignments = ["left"] + ["right"] * (len(headers) - 1)
        widths = [len(header) for header in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))

        def format_row(values: Sequence[str]) -> str:
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
