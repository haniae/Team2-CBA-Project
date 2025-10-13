"""Core chatbot orchestration logic with analytics-aware intents."""

from __future__ import annotations

# High-level conversation orchestrator: parses intents, calls the analytics engine, handles
# ingestion commands, and falls back to the configured language model. Used by CLI and web UI.

import re
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import requests

from . import database, tasks
from .analytics_engine import AnalyticsEngine
from .config import Settings
from .data_ingestion import IngestionReport, ingest_financial_data
from .help_content import HELP_TEXT
from .llm_client import LLMClient, build_llm_client
from .table_renderer import METRIC_DEFINITIONS, render_table_command

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Company name → ticker resolver built from SEC company_tickers.json + local aliases
# --------------------------------------------------------------------------------------
class _CompanyNameIndex:
    _SUFFIXES = (
        "inc", "inc.", "corporation", "corp", "corp.", "co", "co.",
        "company", "ltd", "ltd.", "plc", "llc", "lp", "s.a.", "sa",
        "holdings", "holding", "group"
    )

    @staticmethod
    def _normalize(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9 &\-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        parts = [p for p in s.split(" ") if p]
        while parts and parts[-1] in _CompanyNameIndex._SUFFIXES:
            parts.pop()
        return " ".join(parts)

    def __init__(self) -> None:
        self.by_exact: Dict[str, str] = {}        # normalized name -> ticker
        self.rows: List[tuple[str, str]] = []     # (normalized name, ticker)
        self._add_builtin_aliases()

    def _add_builtin_aliases(self) -> None:
        """Seed the index with a handful of high-usage aliases."""
        extras = {
            # Mega-cap technology
            "apple": "AAPL",
            "apple inc": "AAPL",
            "apple incorporated": "AAPL",
            "apple computer": "AAPL",
            "microsoft": "MSFT",
            "microsoft corp": "MSFT",
            "microsoft corporation": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "alphabet inc": "GOOGL",
            "amazon": "AMZN",
            "amazon.com": "AMZN",
            "meta": "META",
            "facebook": "META",
            "tesla": "TSLA",
            "tesla motors": "TSLA",
            "nvidia": "NVDA",
            "nvidia corporation": "NVDA",
            # Financial heavyweights
            "jpmorgan": "JPM",
            "jpmorgan chase": "JPM",
            "goldman sachs": "GS",
            "bank of america": "BAC",
            # Consumer staples
            "coca cola": "KO",
            "coca-cola": "KO",
            "pepsi": "PEP",
            "pepsico": "PEP",
            # Industrials / others
            "berkshire hathaway": "BRK-B",
            "berkshire": "BRK-B",
        }
        for name, ticker in extras.items():
            norm = self._normalize(name)
            if not norm or not ticker:
                continue
            ticker = ticker.upper()
            if norm not in self.by_exact:
                self.by_exact[norm] = ticker
                self.rows.append((norm, ticker))

    def build_from_sec(self, base_url: str, user_agent: str, timeout: float = 20.0) -> None:
        """Populate the index from the SEC company_tickers payload with graceful fallbacks."""
        candidate_urls = [
            f"{base_url.rstrip('/')}/files/company_tickers.json",
        ]
        if "sec.gov" not in base_url or base_url.rstrip("/").endswith("data.sec.gov"):
            candidate_urls.append("https://www.sec.gov/files/company_tickers.json")

        payload = None
        last_error: Optional[Exception] = None
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
        for url in candidate_urls:
            try:
                response = requests.get(url, timeout=timeout, headers=headers)
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:  # pragma: no cover - network dependent
                last_error = exc
                LOGGER.warning("Unable to fetch SEC company tickers from %s: %s", url, exc)

        if payload is None:
            if last_error:
                raise last_error
            raise RuntimeError("SEC company ticker payload could not be retrieved.")

        entries = payload.values() if isinstance(payload, dict) else payload

        for e in entries:
            title = str(e.get("title") or e.get("name") or "").strip()
            ticker = str(e.get("ticker") or "").upper().strip()
            if not title or not ticker:
                continue
            norm = self._normalize(title)
            if norm:
                if norm not in self.by_exact or "-" not in ticker:  # prefer common shares
                    self.by_exact[norm] = ticker
                self.rows.append((norm, ticker))

        # friendly short names (seed)
        extras = {
            "alphabet": "GOOGL",
            "google": "GOOGL",
            "meta": "META",
            "facebook": "META",
            "berkshire hathaway": "BRK-B",
            "berkshire": "BRK-B",
            "coca cola": "KO",
            "coca-cola": "KO",
        }
        for k, v in extras.items():
            self.by_exact.setdefault(self._normalize(k), v)

    def load_local_aliases(self, path: str | Path) -> None:
        try:
            p = Path(path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                added = 0
                for k, v in (data or {}).items():
                    norm = self._normalize(k)
                    if norm and v and norm not in self.by_exact:
                        self.by_exact[norm] = str(v).upper()
                        self.rows.append((norm, self.by_exact[norm]))
                        added += 1
                LOGGER.info("Loaded %d local name aliases from %s", added, p)
            else:
                LOGGER.warning("Local alias file not found: %s", p)
        except Exception:
            LOGGER.exception("Failed loading local alias file %s", path)

    def resolve(self, phrase: str) -> Optional[str]:
        if not phrase:
            return None
        q = self._normalize(phrase)
        if not q:
            return None

        # 1) exact normalized
        t = self.by_exact.get(q)
        if t:
            return t

        # 2) prefix (e.g., "apple" vs "apple computer")
        for name, tic in self.rows:
            if name.startswith(q):
                return tic

        # 3) contains (e.g., "bank of america" vs "bank of america corp")
        for name, tic in self.rows:
            if q in name:
                return tic

        # 4) light token-overlap score
        q_tokens = set(q.split())
        best, best_score = None, 0.0
        for name, tic in self.rows:
            n_tokens = set(name.split())
            inter = len(q_tokens & n_tokens)
            if not inter:
                continue
            score = inter / max(len(q_tokens), 1)
            if score > best_score:
                best, best_score = tic, score
        return best


# --------------------------------------------------------------------------------------
# Metric formatting categories mirrored from analytics_engine.generate_summary
# --------------------------------------------------------------------------------------
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

# Metrics highlighted in retrieval-augmented context for the language model.
CONTEXT_SUMMARY_METRICS: Sequence[str] = (
    "revenue",
    "net_income",
    "operating_margin",
    "net_margin",
    "return_on_equity",
    "free_cash_flow",
    "free_cash_flow_margin",
    "pe_ratio",
)

BENCHMARK_KEY_METRICS: Dict[str, str] = {
    "adjusted_ebitda_margin": "Adjusted EBITDA margin",
    "net_margin": "Adjusted net margin",
    "return_on_equity": "Return on equity",
    "pe_ratio": "P/E ratio",
}

_METRIC_LABEL_MAP: Dict[str, str] = {
    definition.name: definition.description for definition in METRIC_DEFINITIONS
}

_TICKER_TOKEN_PATTERN = re.compile(r"\b[A-Z]{1,5}(?:-[A-Z]{1,2})?\b")
_COMPANY_PHRASE_PATTERN = re.compile(
    r"\b(?:[A-Za-z][A-Za-z&.]+(?:\s+[A-Za-z][A-Za-z&.]+){0,3})\b"
)
_COMMON_WORDS = {
    "AND",
    "OR",
    "THE",
    "A",
    "AN",
    "OF",
    "FOR",
    "WITH",
    "VS",
    "VERSUS",
    "PLEASE",
    "SHOW",
    "TELL",
    "WHAT",
    "HOW",
    "WHY",
    "IS",
    "ARE",
    "ON",
    "IN",
    "TO",
    "HELP",
}

_METRICS_PATTERN = re.compile(r"^metrics(?:(?:\s+for)?\s+)(.+)$", re.IGNORECASE)


@dataclass
class Conversation:
    """Tracks a single chat session."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Mapping[str, str]] = field(default_factory=list)

    def as_llm_messages(self) -> List[Mapping[str, str]]:
        """Render the conversation history in chat-completions format."""
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self.messages]


SYSTEM_PROMPT = (
    "You are BenchmarkOS, an institutional-grade finance analyst.\n"
    "You deliver precise, compliant insights grounded in the latest SEC filings,"
    " market data, and risk controls. Provide actionable intelligence in clear "
    "professional language. If you are unsure, request clarification or state "
    "explicitly that more data is required."
)


@dataclass
# Wraps settings, analytics, ingestion hooks, and the LLM client into a stateful conversation
# object. Use `BenchmarkOSChatbot.create()` before calling `ask()`.
class BenchmarkOSChatbot:
    """High-level interface wrapping the entire chatbot pipeline."""

    settings: Settings
    llm_client: LLMClient
    analytics_engine: AnalyticsEngine
    ingestion_report: Optional[IngestionReport] = None
    conversation: Conversation = field(default_factory=Conversation)
    # new: SEC-backed index
    name_index: _CompanyNameIndex = field(default_factory=_CompanyNameIndex)

    @classmethod
    def create(cls, settings: Settings) -> "BenchmarkOSChatbot":
        """Factory that wires analytics, storage, and the LLM client together."""
        llm_client = build_llm_client(
            settings.llm_provider,
            model=settings.openai_model,
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

        # Build the SEC-backed name index once; always attempt local alias fallback
        index = _CompanyNameIndex()
        base = getattr(settings, "edgar_base_url", None) or "https://www.sec.gov"
        ua = getattr(settings, "sec_api_user_agent", None) or "BenchmarkOSBot/1.0 (support@benchmarkos.com)"
        try:
            index.build_from_sec(base, ua)
            LOGGER.info("SEC company index built with %d names", len(index.by_exact))
        except Exception as e:
            LOGGER.warning("SEC company index build failed: %s", e)

        # Always attempt local fallback (data/name_aliases.json)
        try:
            alias_path = Path(__file__).resolve().parent.parent / "data" / "name_aliases.json"
            index.load_local_aliases(alias_path)
        except Exception:
            LOGGER.exception("Failed while loading local aliases")

        LOGGER.info("Final name->ticker index size: %d", len(index.by_exact))

        return cls(
            settings=settings,
            llm_client=llm_client,
            analytics_engine=analytics_engine,
            ingestion_report=ingestion_report,
            name_index=index,
        )

    # ----------------------------------------------------------------------------------
    # NL → command normalization (accept natural company names)
    # ----------------------------------------------------------------------------------
    def _name_to_ticker(self, term: str) -> Optional[str]:
        """Resolve free-text company names to tickers using:
           1) engine.lookup_ticker (if provided)
           2) SEC-backed name index (exact/prefix/contains/token overlap)
           3) local alias fallback
        """
        if not term:
            return None
        t = term.strip()

        # engine's own mapping first
        lookup = getattr(self.analytics_engine, "lookup_ticker", None)
        if callable(lookup):
            try:
                tk = lookup(t, allow_partial=True)  # type: ignore[misc]
            except TypeError:
                tk = lookup(t)  # type: ignore[misc]
            except Exception:
                tk = None
            if tk:
                return tk.upper()

        # SEC/local name index
        tk = self.name_index.resolve(t)
        if tk:
            return tk.upper()

        return None

    def _normalize_nl_to_command(self, text: str) -> Optional[str]:
        """Turn flexible NL prompts into the strict CLI-style commands this class handles."""
        t = text.strip()

        def _canon_year_span(txt: str) -> Optional[str]:
            if not txt:
                return None
            m = re.search(r"(?:FY\s*)?(\d{4})\s*(?:[-/]\s*(?:FY\s*)?(\d{4}))?$", txt.strip(), re.IGNORECASE)
            if not m:
                return None
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else None
            if b and b < a:
                a, b = b, a
            return f"{a}-{b}" if b else f"{a}"

        def _split_entities(value: str) -> List[str]:
            s = value.strip().strip(",")
            if not s:
                return []
            quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', s)
            taken, out = set(), []
            for a, b in quoted:
                name = (a or b).strip()
                if name:
                    out.append(name); taken.add(name)
            s_clean = re.sub(r'"[^"]+"|\'[^\']+\'', "", s).strip()
            parts = [p for p in re.split(r"\s*,\s*", s_clean)] if "," in s_clean else \
                    [p for p in re.split(r"\s+and\s+", s_clean, flags=re.IGNORECASE)]
            for p in parts:
                p = p.strip()
                if p and p not in taken:
                    out.append(p)
            return out or [s]

        def _to_ticker(name_or_ticker: str) -> str:
            return (self._name_to_ticker(name_or_ticker) or name_or_ticker).upper()

        lower = t.lower()
        skip_prefixes = (
            "metrics",
            "metric ",
            "compare",
            "versus",
            "vs ",
            "vs.",
            "fact",
            "facts",
            "audit",
            "ingest",
            "fetch",
            "hydrate",
            "update",
            "scenario",
            "what-if",
            "what if",
            "table",
        )
        metric_terms = {
            "eps",
            "ebitda",
            "roe",
            "roa",
            "fcf",
            "peg",
            "pe",
            "p/e",
            "cagr",
        }

        if not any(lower.startswith(prefix) for prefix in skip_prefixes):
            detected_entities = self._detect_tickers(text)

            def _has_metrics(candidate: str) -> bool:
                try:
                    records = self.analytics_engine.get_metrics(candidate)
                except Exception:
                    return False
                return bool(records)

            ordered_subjects: List[str] = []
            seen_subjects: set[str] = set()
            ticker_pattern = re.compile(r"[A-Z]{1,5}(?:-[A-Z]{1,2})?")

            for raw in detected_entities:
                candidate = self._name_to_ticker(raw)
                if candidate:
                    resolved = candidate.upper()
                else:
                    upper_raw = raw.upper()
                    if not ticker_pattern.fullmatch(upper_raw):
                        continue
                    if not _has_metrics(upper_raw):
                        continue
                    resolved = upper_raw

                if resolved.lower() in metric_terms:
                    continue
                if resolved in seen_subjects:
                    continue
                seen_subjects.add(resolved)
                ordered_subjects.append(resolved)

            if ordered_subjects:
                span_match = re.search(
                    r"(?:fy\s*)?\d{4}(?:\s*[-/]\s*(?:fy\s*)?\d{4})?",
                    t,
                    re.IGNORECASE,
                )
                period_token = _canon_year_span(span_match.group(0)) if span_match else None

                compare_triggers = bool(
                    re.search(r"\b(compare|versus|vs\.?|against|between|relative)\b", lower)
                    or "better than" in lower
                    or "outperform" in lower
                    or "beats" in lower
                )
                if compare_triggers and len(ordered_subjects) >= 2:
                    parts = ["compare", *ordered_subjects]
                    if period_token:
                        parts.append(period_token)
                    return " ".join(parts)

                parts = ["metrics", *ordered_subjects]
                if period_token:
                    parts.append(period_token)
                return " ".join(parts)

        # METRICS
        m = re.match(
            r'^(?:show|give me|get|what (?:are|is) the|list)?\s*(?:kpis?|metrics?|financials?)\s+(?:for\s+)?(?P<ents>.+?)(?:\s+(?:in|for)\s+(?P<per>(?:fy)?\d{4}(?:\s*[-/]\s*(?:fy)?\d{4})?))?\s*$',
            t, re.IGNORECASE,
        )
        if m:
            tickers = [_to_ticker(e) for e in _split_entities(m.group("ents")) if e]
            per = _canon_year_span(m.group("per") or "")
            if tickers:
                return " ".join(["metrics", *tickers, *(per and [per] or [])])

        # COMPARE
        m = re.match(r"^(?:compare|versus|vs\.?|against)\s+(?P<body>.+)$", t, re.IGNORECASE)
        if m:
            body = m.group("body").strip()
            yr = None
            myr = re.search(r"(\d{4})\s*$", body)
            if myr:
                yr = myr.group(1); body = body[: myr.start()].strip()
            parts = re.split(r"\s*(?:,|&|/|\s+vs\.?\s+|\s+versus\s+|\s+against\s+|\s+and\s+)\s*", body, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2 and parts[0] and parts[1]:
                a, b = _to_ticker(parts[0]), _to_ticker(parts[1])
                return " ".join(filter(None, ["compare", a, b, yr]))

        # FACTS
        m = re.match(r'^(?:show|get|give me)?\s*(?:fact|facts?)\s+(?:for\s+)?(?P<e>.+?)\s+(?:fy)?(?P<y>\d{4})(?:\s+(?P<mtr>[A-Za-z0-9_]+))?\s*$', t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["fact", tk, m.group("y"), m.group("mtr")]))

        # AUDIT
        m = re.match(r'^(?:show|get|give me)?\s*(?:audit|audit trail|ingestion log)s?\s+(?:for\s+)?(?P<e>.+?)(?:\s+(?:fy)?(?P<y>\d{4}))?\s*$', t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["audit", tk, m.group("y")]))

        # INGEST
        m = re.match(r"^(?:ingest|fetch|hydrate|update)\s+(?P<e>.+?)(?:\s+(?P<yrs>\d{1,2}))?\s*$", t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["ingest", tk, m.group("yrs")]))

        # SCENARIO / WHAT-IF
        m = re.match(r"^(?:scenario|what[- ]?if)\s+(?P<e>.+?)\s+(?P<name>[A-Za-z0-9_\-]+)(?:\s+(?P<rest>.*))?$", t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            rest = (m.group("rest") or "")
            rest_norm = []
            for tok in re.split(r"\s+", rest.strip()):
                if not tok:
                    continue
                tl = tok.lower()
                if tl.startswith(("rev=", "revenue=")):
                    rest_norm.append("rev=" + tok.split("=", 1)[1])
                elif tl.startswith(("margin=", "ebitda=", "ebitda_margin=")):
                    rest_norm.append("margin=" + tok.split("=", 1)[1])
                elif tl.startswith(("mult=", "multiple=")):
                    rest_norm.append("mult=" + tok.split("=", 1)[1])
            return " ".join(["scenario", tk, m.group("name"), *rest_norm]).strip()

        return None

    # ----------------------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------------------
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

        if user_input.strip().lower() == "help":
            reply = HELP_TEXT
            database.log_message(
                self.settings.database_path,
                self.conversation.conversation_id,
                role="assistant",
                content=reply,
                created_at=datetime.utcnow(),
            )
            self.conversation.messages.append({"role": "assistant", "content": reply})
            return reply

        # Try to normalize natural text into a concrete command first
        normalized = self._normalize_nl_to_command(user_input)
        if normalized and normalized.strip().lower() != user_input.strip().lower():
            reply = self._handle_financial_intent(normalized)
            if reply is not None:
                database.log_message(
                    self.settings.database_path,
                    self.conversation.conversation_id,
                    role="assistant",
                    content=reply,
                    created_at=datetime.utcnow(),
                )
                self.conversation.messages.append({"role": "assistant", "content": reply})
                return reply

        reply = self._handle_financial_intent(user_input)
        if reply is None:
            context = self._build_rag_context(user_input)
            messages = self.conversation.as_llm_messages()
            if context:
                messages = [messages[0], {"role": "system", "content": context}, *messages[1:]]
            reply = self.llm_client.generate_reply(messages)

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

    # ----------------------------------------------------------------------------------
    # Intent handling helpers
    # ----------------------------------------------------------------------------------
    def _handle_financial_intent(self, text: str) -> Optional[str]:
        """Handle natural-language requests that map to metrics workflows."""
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
            return HELP_TEXT
        if lowered.startswith("compare "):
            tokens = text.split()[1:]
            return self._handle_metrics_comparison(tokens)

        if lowered.startswith("table "):
            table_output = render_table_command(text, self.analytics_engine)
            if table_output is None:
                return "Unable to generate a table for that request."
            return table_output

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
        """Render a comparison table for the resolved tickers/metrics."""
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
        """Fetch metrics and build a response message for the chat."""
        if not tickers:
            return "Provide at least one ticker for metrics."
        if len(tickers) == 1 and not period_filters:
            return self.analytics_engine.generate_summary(tickers[0])
        return self._format_metrics_table(
            tickers,
            period_filters=period_filters,
        )

    def _handle_ingest_command(self, text: str) -> str:
        """Execute ingestion commands issued by the user."""
        parts = text.split()
        if len(parts) < 2:
            return "Usage: ingest <TICKER> [years]"
        if parts[1].lower() == "status":
            if len(parts) < 3:
                return "Usage: ingest status <TICKER>"
            ticker = parts[2].upper()
            manager = tasks.get_task_manager(self.settings)
            status = manager.get_status(ticker)
            if not status:
                return f"No ingestion task found for {ticker}."
            return (
                f"Ingestion status for {ticker}: {status.summary()} "
                f"(submitted {status.submitted_at:%Y-%m-%d %H:%M:%S} UTC)"
            )

        ticker = parts[1].upper()
        years = 5
        if len(parts) >= 3:
            try:
                years = int(parts[2])
            except ValueError:
                return "Years must be an integer (e.g. ingest TSLA 5)."
        manager = tasks.get_task_manager(self.settings)
        manager.submit_ingest(ticker, years=years)
        current_status = manager.get_status(ticker)
        summary = current_status.summary() if current_status else "queued"
        return (
            f"Ingestion for {ticker} queued (status: {summary}). "
            f"Use 'ingest status {ticker}' to check progress."
        )

    def _handle_scenario_command(self, text: str) -> str:
        """Run scenario modelling commands and persist the results."""
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

        runner = getattr(self.analytics_engine, 'run_scenario', None)
        if not callable(runner):
            return 'Scenario analysis is not available in this configuration.'

        summary = runner(
            ticker,
            scenario_name=name,
            **deltas,
        )
        return getattr(summary, 'narrative', str(summary))

    # ----------------------------------------------------------------------------------
    # Fact and audit helpers
    # ----------------------------------------------------------------------------------
    def _handle_fact_command(self, text: str) -> str:
        """Return detailed fact rows for the requested ticker/year."""
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
            ticker=ticker,
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
        """Summarise audit events for a given ticker."""
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

    # ----------------------------------------------------------------------------------
    # Parsing helpers
    # ----------------------------------------------------------------------------------
    @staticmethod
    def _parse_percent(value: str) -> float:
        """Interpret percentage tokens and return them as floats."""
        value = value.strip().rstrip("%")
        try:
            return float(value) / 100.0
        except ValueError:
            return 0.0

    def _parse_metrics_request(self, text: str) -> Optional["BenchmarkOSChatbot._MetricsRequest"]:
        """Convert free-form text into a structured metrics request."""
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

    def _split_tickers_and_periods(
        self, tokens: Sequence[str]
    ) -> tuple[List[str], Optional[List[tuple[int, int]]]]:
        """Separate ticker symbols from potential period filters."""
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
        """Convert textual period filters into numeric start/end years."""
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

    # ----------------------------------------------------------------------------------
    # Metrics formatting helpers
    # ----------------------------------------------------------------------------------
    @dataclass
    class _MetricsRequest:
        """Structured representation of a parsed metrics request."""
        tickers: List[str]
        period_filters: Optional[List[tuple[int, int]]]

    @dataclass
    class _TickerResolution:
        """Tracks which tickers resolved successfully versus missing."""
        available: List[str]
        missing: List[str]

    def _resolve_tickers(self, subjects: Sequence[str]) -> "BenchmarkOSChatbot._TickerResolution":
        """Resolve tickers against the dataset, recording missing entries."""
        available: List[str] = []
        missing: List[str] = []
        lookup = getattr(self.analytics_engine, "lookup_ticker", None)
        for subject in subjects:
            resolved: Optional[str] = None
            if callable(lookup):
                try:
                    resolved = lookup(subject, allow_partial=True)  # type: ignore[misc]
                except TypeError:
                    try:
                        resolved = lookup(subject)  # type: ignore[misc]
                    except Exception:
                        resolved = None
                except Exception:
                    resolved = None
            if not resolved:
                resolved = self._name_to_ticker(subject)
            if resolved:
                resolved = resolved.upper()
                if resolved not in available:
                    available.append(resolved)
                continue

            candidate = subject.upper()
            try:
                records = self.analytics_engine.get_metrics(candidate)
            except Exception:
                records = []
            if records:
                if candidate not in available:
                    available.append(candidate)
                continue
            missing.append(subject)
        return BenchmarkOSChatbot._TickerResolution(available=available, missing=missing)

    def _format_missing_message(
        self, requested: Sequence[str], available: Sequence[str]
    ) -> str:
        """Build a friendly message for unresolved tickers."""
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
        """Render metrics output as a table suitable for chat."""
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

        benchmark_label: Optional[str] = None
        compute_benchmark = getattr(self.analytics_engine, "compute_benchmark_metrics", None)
        if callable(compute_benchmark):
            metrics_needed = {definition.name for definition in METRIC_DEFINITIONS}
            metrics_needed.update(BENCHMARK_KEY_METRICS.keys())
            try:
                benchmark_metrics = compute_benchmark(
                    sorted(metrics_needed),
                    period_filters=period_filters,
                )
            except Exception:
                benchmark_metrics = {}
            if benchmark_metrics:
                label_getter = getattr(self.analytics_engine, "benchmark_label", None)
                benchmark_label = (
                    label_getter()
                    if callable(label_getter)
                    else getattr(self.analytics_engine, "BENCHMARK_LABEL", "Benchmark")
                )
                metrics_per_ticker[benchmark_label] = benchmark_metrics

        ordered_tickers = [ticker for ticker in tickers if ticker in metrics_per_ticker]
        display_tickers = list(ordered_tickers)
        if benchmark_label:
            display_tickers.append(benchmark_label)
        headers = ["Metric"] + display_tickers
        rows: List[List[str]] = []
        for definition in METRIC_DEFINITIONS:
            label = definition.description
            row = [label]
            for ticker in display_tickers:
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

        highlights = self._compose_benchmark_summary(
            metrics_per_ticker,
            benchmark_label=benchmark_label,
        )

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
        """Render a human-readable summary of applied period filters."""
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
        """Choose latest metric snapshots for each metric name."""
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

    def _build_rag_context(self, user_input: str) -> Optional[str]:
        """Assemble finance facts to ground the LLM response."""
        tickers = self._detect_tickers(user_input)
        if not tickers:
            return None

        context_sections: List[str] = []
        for ticker in tickers:
            try:
                records = self.analytics_engine.get_metrics(ticker)
            except Exception:  # pragma: no cover - database path
                continue
            if not records:
                continue

            latest = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            if not latest:
                continue

            spans = [
                self.analytics_engine._period_span(record.period)
                for record in latest.values()
                if record.period
            ]
            descriptor = (
                self._describe_period_filters(spans) if spans else "latest available"
            )

            lines = [f"{ticker} ({descriptor})"]
            for metric_name in CONTEXT_SUMMARY_METRICS:
                formatted = self._format_metric_value(metric_name, latest)
                if formatted == "n/a":
                    continue
                label = _METRIC_LABEL_MAP.get(
                    metric_name, metric_name.replace("_", " ").title()
                )
                lines.append(f"- {label}: {formatted}")

            if len(lines) > 1:
                lines_text = "\n".join(lines)
                context_sections.append(lines_text)

        if not context_sections:
            return None
        combined = "\n".join(context_sections)
        return "Financial context:\n" + combined

    def _detect_tickers(self, text: str) -> List[str]:
        """Best-effort ticker extraction from user text (tickers + company names)."""
        candidates: List[str] = []
        seen = set()

        for token in _TICKER_TOKEN_PATTERN.findall(text.upper()):
            normalized = token.upper()
            if normalized in _COMMON_WORDS:
                continue
            if normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

        # Also resolve company phrases to tickers
        for match in _COMPANY_PHRASE_PATTERN.findall(text):
            phrase = match.strip()
            if not phrase:
                continue
            if phrase.upper() in _COMMON_WORDS:
                continue
            ticker = self._name_to_ticker(phrase)
            if ticker and ticker not in seen:
                seen.add(ticker)
                candidates.append(ticker)

        return candidates

    def _compose_benchmark_summary(
        self,
        metrics_per_ticker: Dict[str, Dict[str, database.MetricRecord]],
        *,
        benchmark_label: Optional[str] = None,
    ) -> List[str]:
        """Summarise how tickers stack up against an optional benchmark column."""
        if not metrics_per_ticker:
            return []

        contenders = {
            ticker: records
            for ticker, records in metrics_per_ticker.items()
            if ticker != benchmark_label
        }
        if not contenders:
            return []

        benchmark_metrics = (
            metrics_per_ticker.get(benchmark_label) if benchmark_label else None
        )

        highlights: List[str] = []
        for metric, label in BENCHMARK_KEY_METRICS.items():
            best_ticker: Optional[str] = None
            best_value: Optional[float] = None
            best_display: Optional[str] = None
            for ticker, records in contenders.items():
                record = records.get(metric)
                if not record or record.value is None:
                    continue
                if best_value is None or record.value > best_value:
                    best_value = record.value
                    best_ticker = ticker
                    best_display = self._format_metric_value(metric, records)
            if best_ticker is None or best_value is None or best_display is None:
                continue

            line = f"{label}: {best_ticker} {best_display}"

            benchmark_display: Optional[str] = None
            benchmark_value: Optional[float] = None
            if benchmark_metrics:
                benchmark_record = benchmark_metrics.get(metric)
                if benchmark_record and benchmark_record.value is not None:
                    benchmark_value = benchmark_record.value
                    benchmark_display = self._format_metric_value(metric, benchmark_metrics)

            if benchmark_display:
                benchmark_name = benchmark_label or "Benchmark"
                line += f" vs {benchmark_name} {benchmark_display}"
                delta_note = self._format_benchmark_delta(metric, best_value, benchmark_value)
                if delta_note is not None and benchmark_value is not None:
                    direction = "above" if (best_value - benchmark_value) >= 0 else "below"
                    line += f" ({delta_note} {direction})"

            highlights.append(line)
        return highlights

    def _format_benchmark_delta(
        self,
        metric_name: str,
        best_value: Optional[float],
        benchmark_value: Optional[float],
    ) -> Optional[str]:
        """Express the difference between the leader and benchmark in human terms."""
        if best_value is None or benchmark_value is None:
            return None
        delta = best_value - benchmark_value
        if abs(delta) < 1e-9:
            return None
        if metric_name in PERCENT_METRICS:
            return f"{delta * 100:+.1f} pts"
        if metric_name in MULTIPLE_METRICS:
            return f"{delta:+.2f}x"
        return f"{delta:+,.0f}"

    @staticmethod
    def _format_metric_value(
        metric_name: str, metrics: Dict[str, database.MetricRecord]
    ) -> str:
        """Format metric values with appropriate precision and units."""
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
        """Format fact values for display, preserving units where possible."""
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
        """Render rows and headers into a markdown-style table."""
        if not rows:
            return "No data available."

        alignments = ["left"] + ["right"] * (len(headers) - 1)
        widths = [len(header) for header in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))

        def format_row(values: Sequence[str]) -> str:
            """Format a single row tuple for display in tables."""
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
