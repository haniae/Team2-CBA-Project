"""FastAPI service exposing the BenchmarkOS chatbot, analytics API, and web UI."""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import AnalyticsEngine, BenchmarkOSChatbot, database, load_settings
from .help_content import HELP_TEXT, get_help_metadata


# ----- CORS / Static ----------------------------------------------------------

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (
        Path.cwd().joinpath(".allowed_origins").read_text().splitlines()
        if Path.cwd().joinpath(".allowed_origins").exists()
        else []
    )
    if origin.strip()
]

app = FastAPI(title="BenchmarkOS Analyst Copilot", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = (BASE_DIR.parent / "webui").resolve()
PACKAGE_STATIC = (BASE_DIR / "static").resolve()

# prefer project-level /webui build; fall back to packaged static
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
elif PACKAGE_STATIC.exists():
    app.mount("/static", StaticFiles(directory=PACKAGE_STATIC), name="static")


# ----- Schemas ----------------------------------------------------------------

class ProgressEvent(BaseModel):
    """Single progress update emitted while building a chatbot response."""

    sequence: int
    stage: str
    label: str
    detail: str
    timestamp: str


class ProgressStatus(BaseModel):
    """Snapshot of progress emitted for an in-flight chat request."""

    request_id: str
    conversation_id: Optional[str] = None
    events: List[ProgressEvent] = []
    complete: bool = False
    error: Optional[str] = None


class ChatRequest(BaseModel):
    """Payload expected by the /chat endpoint when posting a prompt."""

    prompt: str
    conversation_id: Optional[str] = None
    request_id: Optional[str] = None


class TrendPoint(BaseModel):
    """Single datapoint for a trend visualisation."""
    period: str
    value: Optional[float]
    formatted_value: Optional[str] = None


class TrendSeries(BaseModel):
    """Series describing a ticker/metric trend."""
    ticker: str
    metric: str
    label: str
    points: List[TrendPoint]


class ComparisonTable(BaseModel):
    """Structured representation of the benchmark comparison table."""
    headers: List[str]
    rows: List[List[str]]
    descriptor: Optional[str] = None
    tickers: List[str] = []
    title: Optional[str] = None
    render: Optional[bool] = True
    render_hint: Optional[str] = None


class Citation(BaseModel):
    """Source metadata for numerical outputs shown to the user."""
    ticker: str
    metric: str
    label: str
    period: Optional[str] = None
    value: Optional[float] = None
    formatted_value: Optional[str] = None
    source: Optional[str] = None
    filing: Optional[str] = None
    unit: Optional[str] = None
    urls: Optional[Dict[str, Optional[str]]] = None
    filed_at: Optional[str] = None
    form: Optional[str] = None


class ExportPayload(BaseModel):
    """Client-side export descriptor (CSV/PDF)."""
    type: str
    label: str
    filename: Optional[str] = None
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    descriptor: Optional[str] = None
    highlights: Optional[List[str]] = None
    title: Optional[str] = None


class ChatResponse(BaseModel):
    """Response returned after processing a chat prompt."""
    conversation_id: str
    reply: str
    request_id: Optional[str] = None
    highlights: List[str] = []
    trends: List[TrendSeries] = []
    comparison_table: Optional[ComparisonTable] = None
    citations: List[Citation] = []
    exports: List[ExportPayload] = []
    progress_events: List[ProgressEvent] = []


class MetricsResponse(BaseModel):
    """Shape of the metrics payload returned to the UI/API."""
    ticker: str
    metrics: Dict[str, Optional[float]]
    period: str


class FactsResponse(BaseModel):
    """Response schema for detailed financial fact lookups."""
    ticker: str
    fiscal_year: int
    items: List[Dict]


class AuditEventResponse(BaseModel):
    """Response structure describing recorded audit trail entries."""
    ticker: str
    events: List[Dict]


class FilingFact(BaseModel):
    """Detailed view of a fact with source metadata."""
    ticker: str
    metric: str
    value: Optional[float]
    unit: Optional[str]
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]
    period: str
    source: str
    source_filing: Optional[str]
    accession: Optional[str]
    form: Optional[str]
    filed_at: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    adjusted: bool
    adjustment_note: Optional[str]
    sec_url: Optional[str]
    archive_url: Optional[str]
    search_url: Optional[str]


class FilingFactsSummary(BaseModel):
    """Aggregate stats describing the filing facts payload."""
    count: int
    fiscal_years: List[int]
    metrics: List[str]


class FilingFactsResponse(BaseModel):
    """Response shape for the filing source viewer."""
    ticker: str
    items: List[FilingFact]
    summary: FilingFactsSummary

# ----- Dependencies / Singletons ---------------------------------------------

@lru_cache
def get_settings():
    """Load application settings once per process."""
    return load_settings()


@lru_cache
def get_engine() -> AnalyticsEngine:
    """Initialise and prime the analytics engine (cached for reuse)."""
    engine = AnalyticsEngine(get_settings())
    engine.refresh_metrics()
    return engine


def build_bot(conversation_id: Optional[str] = None) -> BenchmarkOSChatbot:
    """Create a chatbot instance and hydrate it with stored history when provided."""
    settings = get_settings()
    bot = BenchmarkOSChatbot.create(settings)
    if conversation_id:
        history = list(
            database.fetch_conversation(settings.database_path, conversation_id)
        )
        if history:
            bot.conversation.conversation_id = conversation_id
            bot.conversation.messages = [
                {"role": msg.role, "content": msg.content} for msg in history
            ]
    return bot


_PROGRESS_LOCK = threading.Lock()
_PROGRESS_STATE: Dict[str, Dict[str, Any]] = {}
_PROGRESS_RETENTION_SECONDS = 120.0
_PROGRESS_MAX_EVENTS = 200
_PROGRESS_STAGE_LABELS: Dict[str, str] = {
    "start": "Startup",
    "message_logged": "Conversation",
    "cache_lookup": "Cache",
    "cache_hit": "Cache",
    "cache_miss": "Cache",
    "cache_skip": "Cache",
    "cache_store": "Cache",
    "help_lookup": "Help",
    "help_complete": "Help",
    "intent_normalised": "Intent",
    "intent_analysis_start": "Intent",
    "intent_analysis_complete": "Intent",
    "intent_routed_structured": "Intent",
    "intent_routed_natural": "Intent",
    "intent_metrics_detected": "Intent",
    "intent_metrics_missing": "Intent",
    "intent_attempt": "Intent",
    "intent_complete": "Intent",
    "summary_cache_hit": "Summary",
    "summary_build_start": "Summary",
    "summary_build_complete": "Summary",
    "summary_unavailable": "Summary",
    "summary_attempt": "Summary",
    "summary_complete": "Summary",
    "ticker_resolution_start": "Context",
    "ticker_resolution_complete": "Context",
    "metrics_dispatch": "Context",
    "metrics_fetch_start": "Context",
    "metrics_fetch_progress": "Context",
    "metrics_fetch_complete": "Context",
    "metrics_fetch_notice": "Context",
    "metrics_fetch_missing": "Context",
    "context_sources_scan": "Context",
    "context_cache_hit": "Context",
    "context_build_start": "Context",
    "context_build_ready": "Context",
    "context_sources_ready": "Context",
    "context_sources_empty": "Context",
    "llm_query_start": "LLM",
    "llm_query_complete": "LLM",
    "fallback": "Fallback",
    "finalize": "Finalising",
    "complete": "Done",
    "error": "Error",
}


def _progress_timestamp() -> str:
    """Return an ISO8601 timestamp with explicit UTC marker."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _cleanup_progress_locked(current_time: float) -> None:
    """Remove completed trackers that have exceeded the retention window."""
    stale_keys = [
        key
        for key, state in _PROGRESS_STATE.items()
        if state.get("expires_at") is not None and state["expires_at"] <= current_time
    ]
    for key in stale_keys:
        _PROGRESS_STATE.pop(key, None)


def _start_progress_tracking(request_id: str, conversation_id: Optional[str]) -> None:
    """Initialise a progress tracker for a new chat request."""
    now = time.monotonic()
    with _PROGRESS_LOCK:
        _cleanup_progress_locked(now)
        _PROGRESS_STATE[request_id] = {
            "conversation_id": conversation_id,
            "events": [],
            "complete": False,
            "error": None,
            "next_sequence": 1,
            "expires_at": None,
        }


def _label_for_stage(stage: str) -> str:
    """Return a user-friendly label for the given stage."""
    return _PROGRESS_STAGE_LABELS.get(stage, stage.replace("_", " ").title())


def _record_progress_event(request_id: str, stage: str, detail: str) -> None:
    """Append a progress event for downstream polling."""
    timestamp = _progress_timestamp()
    with _PROGRESS_LOCK:
        state = _PROGRESS_STATE.get(request_id)
        if state is None:
            state = {
                "conversation_id": None,
                "events": [],
                "complete": False,
                "error": None,
                "next_sequence": 1,
                "expires_at": None,
            }
            _PROGRESS_STATE[request_id] = state
        sequence = state["next_sequence"]
        state["next_sequence"] += 1
        state["events"].append(
            {
                "sequence": sequence,
                "stage": stage,
                "label": _label_for_stage(stage),
                "detail": detail,
                "timestamp": timestamp,
            }
        )
        if len(state["events"]) > _PROGRESS_MAX_EVENTS:
            state["events"] = state["events"][-_PROGRESS_MAX_EVENTS :]


def _complete_progress_tracking(request_id: str, *, error: Optional[str] = None) -> None:
    """Mark a progress tracker as complete and schedule cleanup."""
    now = time.monotonic()
    with _PROGRESS_LOCK:
        state = _PROGRESS_STATE.get(request_id)
        if state is None:
            return
        if error:
            state["error"] = error
            sequence = state["next_sequence"]
            state["next_sequence"] += 1
            state["events"].append(
                {
                    "sequence": sequence,
                    "stage": "error",
                    "label": _label_for_stage("error"),
                    "detail": error,
                    "timestamp": _progress_timestamp(),
                }
            )
        state["complete"] = True
        state["expires_at"] = now + _PROGRESS_RETENTION_SECONDS


def _progress_snapshot(request_id: str, since: Optional[int] = None) -> ProgressStatus:
    """Return the current progress state for a request."""
    now = time.monotonic()
    with _PROGRESS_LOCK:
        _cleanup_progress_locked(now)
        state = _PROGRESS_STATE.get(request_id)
        if state is None:
            return ProgressStatus(
                request_id=request_id,
                conversation_id=None,
                events=[],
                complete=False,
                error=None,
            )
        events = state["events"]
        if since is not None:
            events = [event for event in events if event["sequence"] > since]
        return ProgressStatus(
            request_id=request_id,
            conversation_id=state.get("conversation_id"),
            events=[ProgressEvent(**event) for event in events],
            complete=bool(state.get("complete")),
            error=state.get("error"),
        )


def _normalise_ticker_symbol(value: str) -> str:
    """Return canonical ticker form used by the datastore (share classes -> dash)."""
    symbol = (value or "").strip().upper()
    return symbol.replace(".", "-")


def _ticker_variants(value: str) -> List[str]:
    """Return canonical ticker plus fallbacks for legacy dot-form symbols."""
    original = (value or "").strip().upper()
    primary = _normalise_ticker_symbol(value)
    dotted = primary.replace("-", ".")
    variants: List[str] = []
    for candidate in (primary, original, dotted):
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


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


def _lookup_company_name(ticker: str) -> Optional[str]:
    """Fetch a human-readable company name for the supplied ticker."""
    settings = get_settings()
    try:
        with database.temporary_connection(settings.database_path) as connection:
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


def _format_number(value: Optional[float], decimals: int = 1) -> Optional[str]:
    """Format a float with trimmed trailing zeroes."""
    if value is None:
        return None
    formatted = f"{value:.{decimals}f}"
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


# ----- Routes -----------------------------------------------------------------

@app.get("/")
def root() -> FileResponse:
    """Serve the static index file, preferring the local webui build when present."""
    if FRONTEND_DIR.exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    if PACKAGE_STATIC.exists():
        return FileResponse(PACKAGE_STATIC / "index.html")
    raise HTTPException(status_code=404, detail="Frontend assets are not available.")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Serve a favicon; prefer project webui asset, fall back to packaged static.

    Browsers request /favicon.ico by default; we serve our SVG for simplicity.
    """
    candidates = []
    if FRONTEND_DIR.exists():
        candidates.append(FRONTEND_DIR / "favicon.svg")
    if PACKAGE_STATIC.exists():
        candidates.append(PACKAGE_STATIC / "favicon.svg")
    for path in candidates:
        if path.exists():
            return FileResponse(path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/health")
def health() -> Dict[str, str]:
    """Lightweight liveness probe used by deployment infra."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Proxy chat submissions to the BenchmarkOS chatbot."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    request_id = request.request_id or str(uuid.uuid4())
    prompt = request.prompt.strip()
    lowered = prompt.lower()
    if lowered == "help":
        settings = get_settings()
        conversation_id = request.conversation_id or str(uuid.uuid4())
        _start_progress_tracking(request_id, conversation_id)
        _record_progress_event(request_id, "start", "Processing your request")
        _record_progress_event(request_id, "help_lookup", "Loading help content")
        timestamp = datetime.utcnow()
        database.log_message(
            settings.database_path,
            conversation_id,
            role="user",
            content=prompt,
            created_at=timestamp,
        )
        database.log_message(
            settings.database_path,
            conversation_id,
            role="assistant",
            content=HELP_TEXT,
            created_at=datetime.utcnow(),
        )
        _record_progress_event(request_id, "help_complete", "Help content ready")
        _record_progress_event(request_id, "complete", "Response ready")
        _complete_progress_tracking(request_id)
        progress_snapshot = _progress_snapshot(request_id)
        return ChatResponse(
            conversation_id=conversation_id,
            reply=HELP_TEXT,
            request_id=request_id,
            progress_events=progress_snapshot.events,
        )

    bot = build_bot(request.conversation_id)
    conversation_id = bot.conversation.conversation_id
    _start_progress_tracking(request_id, conversation_id)

    def _progress_hook(stage: str, detail: str) -> None:
        _record_progress_event(request_id, stage, detail)

    try:
        reply = bot.ask(request.prompt, progress_callback=_progress_hook)
    except Exception as exc:  # pragma: no cover - defensive relay
        _complete_progress_tracking(request_id, error=str(exc))
        _progress_snapshot(request_id)  # ensure cleanup scheduling
        raise
    else:
        _complete_progress_tracking(request_id)

    progress_snapshot = _progress_snapshot(request_id)
    structured = getattr(bot, "last_structured_response", {}) or {}
    trends = [
        TrendSeries(**series) for series in structured.get("trends") or []
    ]
    comparison_table = (
        ComparisonTable(**structured["comparison_table"])
        if structured.get("comparison_table")
        else None
    )
    citations = [
        Citation(**citation) for citation in structured.get("citations") or []
    ]
    exports = [
        ExportPayload(**payload) for payload in structured.get("exports") or []
    ]
    return ChatResponse(
        conversation_id=bot.conversation.conversation_id,
        reply=reply,
        request_id=request_id,
        highlights=structured.get("highlights") or [],
        trends=trends,
        comparison_table=comparison_table,
        citations=citations,
        exports=exports,
        progress_events=progress_snapshot.events,
    )


@app.get("/help-content")
def help_content() -> Dict[str, Any]:
    """Expose help metadata for the web UI."""
    return get_help_metadata()


@app.get("/progress/{request_id}", response_model=ProgressStatus)
def progress_status(
    request_id: str,
    since: Optional[int] = Query(
        None,
        description="Only return events whose sequence exceeds this value.",
    ),
) -> ProgressStatus:
    """Allow the UI to poll for in-flight chatbot progress updates."""
    return _progress_snapshot(request_id, since)


def _select_latest_records(
    records: Iterable[database.MetricRecord],
    span_fn,
) -> Dict[str, database.MetricRecord]:
    """Pick the most recent record per metric, honouring period spans."""
    selected: Dict[str, database.MetricRecord] = {}
    for record in records:
        existing = selected.get(record.metric)
        if existing is None:
            selected[record.metric] = record
            continue
        if record.value is not None and (existing.value is None or not isinstance(existing.value, float)):
            selected[record.metric] = record
            continue
        if record.value is None and existing.value is not None:
            continue
        new_span = span_fn(record.period)
        old_span = span_fn(existing.period)
        if new_span[1] > old_span[1] or (new_span[1] == old_span[1] and new_span[0] > old_span[0]):
            selected[record.metric] = record
    return selected


def _summarise_period(spans: Iterable[Tuple[int, int]]) -> str:
    """Render a human-friendly period label for the supplied spans."""
    spans = [(start, end) for start, end in spans if start or end]
    if not spans:
        return "latest"
    start = min(span[0] for span in spans if span[0])
    end = max(span[1] for span in spans if span[1])
    return f"FY{start}" if start == end else f"FY{start}-FY{end}"


def _build_filing_urls(
    accession: Optional[str], cik: Optional[str]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Generate interactive, detail, and fallback search URLs for a filing accession."""
    if not accession:
        return None, None, None

    search_url = None
    interactive_url = None
    detail_url = None

    if cik:
        clean_cik = cik.lstrip("0") or cik
        acc_no_dash = accession.replace("-", "")
        interactive_url = (
            "https://www.sec.gov/cgi-bin/viewer"
            f"?action=view&cik={clean_cik}&accession_number={accession}&xbrl_type=v"
        )
        detail_url = (
            f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{acc_no_dash}/{accession}-index.html"
        )
        search_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={clean_cik}"
        )
    else:
        # Fall back to accession-based browse search
        base = accession.split("-")[0]
        if base:
            search_url = (
                f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={base}"
            )

    return interactive_url, detail_url, search_url


@app.get("/metrics", response_model=List[MetricsResponse])
def metrics(
    tickers: str = Query(..., description="Comma separated list of tickers"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
) -> List[MetricsResponse]:
    """Return latest metric snapshots for one or more tickers."""
    ticker_list = [
        _normalise_ticker_symbol(ticker)
        for ticker in tickers.split(",")
        if ticker and ticker.strip()
    ]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="At least one ticker required.")

    period_filters: Optional[List[tuple[int, int]]] = None
    if start_year is not None or end_year is not None:
        if start_year is None or end_year is None:
            raise HTTPException(
                status_code=400, detail="start_year and end_year must be provided together",
            )
        if end_year < start_year:
            start_year, end_year = end_year, start_year
        period_filters = [(start_year, end_year)]

    engine = get_engine()
    responses: List[MetricsResponse] = []
    for ticker in ticker_list:
        records = engine.get_metrics(ticker, period_filters=period_filters)
        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics available for ticker {_display_ticker_symbol(ticker)}.",
            )
        chosen = _select_latest_records(records, span_fn=engine._period_span)
        descriptor = _summarise_period(
            engine._period_span(record.period) for record in chosen.values()
        )
        responses.append(
            MetricsResponse(
                ticker=_display_ticker_symbol(ticker),
                metrics={metric: rec.value for metric, rec in chosen.items()},
                period=descriptor,
            )
        )
    return responses


# ---------- NEW: /compare (bypasses LLM; uses AnalyticsEngine directly) --------

@app.get("/compare")
def compare(
    tickers: List[str] = Query(..., min_items=2, description="Repeat ?tickers=AAPL&tickers=MSFT"),
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
):
    """
    Compare metrics across tickers using the AnalyticsEngine.
    Returns JSON: { tickers: [...], comparison: {metric -> {period -> {ticker -> value}}} }
    """
    tickers = [_normalise_ticker_symbol(t) for t in tickers if t and t.strip()]
    if len(tickers) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two tickers.")

    # optional period filter
    period_filters = None
    if (start_year is None) ^ (end_year is None):
        raise HTTPException(status_code=400, detail="Provide both start_year and end_year, or neither.")
    if start_year is not None:
        if end_year < start_year:
            start_year, end_year = end_year, start_year
        period_filters = [(start_year, end_year)]

    engine = get_engine()

    # fetch records per ticker
    by_ticker: Dict[str, list] = {}
    missing: list[str] = []
    for t in tickers:
        recs = engine.get_metrics(t, period_filters=period_filters)
        if not recs:
            missing.append(t)
        else:
            by_ticker[t] = recs

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing metrics for some tickers",
                "missing": [_display_ticker_symbol(t) for t in missing],
            },
        )

    display_tickers = list(tickers)
    benchmark_label: Optional[str] = None
    compute_benchmark = getattr(engine, "compute_benchmark_metrics", None)
    if callable(compute_benchmark):
        metric_names = sorted(
            {
                record.metric
                for records in by_ticker.values()
                for record in records
                if record.metric
            }
        )
        try:
            benchmark_metrics = compute_benchmark(
                metric_names,
                period_filters=period_filters,
            )
        except Exception:
            benchmark_metrics = {}
        if benchmark_metrics:
            label_getter = getattr(engine, "benchmark_label", None)
            benchmark_label = (
                label_getter()
                if callable(label_getter)
                else getattr(engine, "BENCHMARK_LABEL", "Benchmark")
            )
            by_ticker[benchmark_label] = list(benchmark_metrics.values())
            display_tickers.append(benchmark_label)

    # shape as {metric -> {period -> {ticker -> value}}}
    result: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for t, recs in by_ticker.items():
        for r in recs:
            m = r.metric
            p = str(r.period)
            v = r.value
            
            # Format percentage metrics for display
            if v is not None and isinstance(v, (int, float)):
                # Percentage metrics (multiply by 100)
                percentage_metrics = [
                    'revenue_cagr', 'eps_cagr', 'ebitda_growth', 'dividend_yield', 
                    'ebitda_margin', 'profit_margin', 'operating_margin', 'net_margin', 
                    'return_on_assets', 'return_on_equity', 'return_on_invested_capital', 
                    'free_cash_flow_margin', 'tsr'
                ]
                if m in percentage_metrics:
                    v = v * 100
            
            result.setdefault(m, {}).setdefault(p, {})[t] = v

    # sorted keys for stable UI rendering
    result = {m: dict(sorted(pmap.items())) for m, pmap in sorted(result.items())}

    display_map = {ticker: _display_ticker_symbol(ticker) for ticker in display_tickers}
    display_tickers = [display_map[ticker] for ticker in display_tickers]

    comparison: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for metric, period_map in result.items():
        remapped: Dict[str, Dict[str, Any]] = {}
        for period, values in period_map.items():
            remapped[period] = {
                display_map.get(ticker, ticker): value for ticker, value in values.items()
            }
        comparison[metric] = remapped

    return {"tickers": display_tickers, "comparison": comparison}


@app.get("/api/dashboard/cfi-compare")
def cfi_compare_dashboard(
    tickers: Optional[str] = Query(
        None,
        description="Comma separated list of up to three tickers (defaults to AAPL, MSFT, AMZN).",
    ),
    benchmark: Optional[str] = Query(
        None,
        description="Override the benchmark label (defaults to S&P 500 Avg).",
    ),
) -> Dict[str, Any]:
    """Return the structured payload required by the CFIX dashboard."""

    requested = [
        part.strip()
        for part in (tickers.split(",") if tickers else [])
        if part and part.strip()
    ]
    if not requested:
        requested = ["AAPL", "MSFT", "AMZN"]
    requested = requested[:3]
    if not requested:
        raise HTTPException(status_code=400, detail="At least one ticker is required.")

    engine = get_engine()

    canonical = [_normalise_ticker_symbol(ticker) for ticker in requested]
    display_order = [_display_ticker_symbol(ticker) for ticker in canonical]

    records_by_ticker: Dict[str, List[database.MetricRecord]] = {}
    latest_by_ticker: Dict[str, Dict[str, database.MetricRecord]] = {}
    valuations_by_ticker: Dict[str, Optional[Dict[str, Optional[float]]]] = {}
    for ticker in canonical:
        records = engine.get_metrics(ticker)
        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"No metric snapshots available for {_display_ticker_symbol(ticker)}.",
            )
        records_by_ticker[ticker] = records
        latest = engine._select_latest_records(records, span_fn=engine._period_span)
        latest_by_ticker[ticker] = latest
        valuations_by_ticker[ticker] = _valuation_per_share(latest)

    benchmark_label = benchmark or engine.benchmark_label()
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
    }
    benchmark_metrics = engine.compute_benchmark_metrics(metric_scope)

    company_names = {
        name: (_lookup_company_name(symbol) or name)
        for symbol, name in zip(canonical, display_order)
    }

    cards: Dict[str, Dict[str, str]] = {}
    for symbol, display in zip(canonical, display_order):
        latest = latest_by_ticker[symbol]
        valuation = valuations_by_ticker[symbol] or {}
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

    peerset_parts: List[str] = []
    for display in display_order:
        name = company_names.get(display)
        if name and name.strip() and name.upper() != display.upper():
            peerset_parts.append(f"{name} ({display})")
        else:
            peerset_parts.append(display)
    if benchmark_label:
        peerset_parts.append(benchmark_label)

    meta = {
        "date": datetime.utcnow().date().isoformat(),
        "peerset": " vs ".join(peerset_parts),
        "tickers": display_order,
        "companies": company_names,
        "benchmark": benchmark_label,
    }

    table_columns = ["Metric", *display_order, benchmark_label]
    table_rows: List[Dict[str, Any]] = []

    table_config = [
        {"metric": "revenue", "label": "Revenue", "type": "moneyB"},
        {"metric": "ebitda_margin", "label": "EBITDA margin", "type": "pct"},
        {"metric": "net_margin", "label": "Net margin", "type": "pct"},
        {"metric": "return_on_equity", "label": "ROE", "type": "pct"},
        {"metric": "pe_ratio", "label": "P/E (ttm)", "type": "x"},
        {"metric": "ev_ebitda", "label": "EV/EBITDA (ttm)", "type": "x"},
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
        bench_value: Optional[float]
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
        revenue_series = _collect_series(
            records_by_ticker[symbol],
            "revenue",
            scale_billions=True,
        )
        ebitda_series = _collect_series(
            records_by_ticker[symbol],
            "ebitda",
            scale_billions=True,
        )
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


@app.get("/facts", response_model=FactsResponse)
def facts(
    ticker: str = Query(...),
    fiscal_year: int = Query(...),
    metric: Optional[str] = Query(None),
) -> FactsResponse:
    """Expose detailed financial fact rows from the analytics store."""
    engine = get_engine()
    ticker_clean = _normalise_ticker_symbol(ticker)
    requested = (ticker or "").strip().upper() or ticker_clean
    facts = engine.financial_facts(
        ticker=ticker_clean,
        fiscal_year=fiscal_year,
        metric=metric.lower() if metric else None,
        limit=100,
    )
    if not facts:
        raise HTTPException(
            status_code=404,
            detail=f"No financial facts for {requested} in FY{fiscal_year}.",
        )
    items = [
        {
            "metric": fact.metric,
            "value": fact.value,
            "source": fact.source,
            "adjusted": fact.adjusted,
            "adjustment_note": fact.adjustment_note,
            "ingested_at": fact.ingested_at.isoformat(),
        }
        for fact in facts
    ]
    response_ticker = requested or _display_ticker_symbol(ticker_clean)
    return FactsResponse(ticker=response_ticker, fiscal_year=fiscal_year, items=items)


@app.get("/filings", response_model=FilingFactsResponse)
def filing_sources(
    ticker: str = Query(...),
    metric: Optional[str] = Query(None),
    fiscal_year: Optional[int] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    limit: int = Query(250, ge=1, le=1000),
) -> FilingFactsResponse:
    """Return fact rows with filing metadata for the filing source viewer."""
    if (start_year is not None or end_year is not None) and fiscal_year is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either fiscal_year or start_year/end_year, not both.",
        )

    if (start_year is None) ^ (end_year is None):
        raise HTTPException(
            status_code=400,
            detail="start_year and end_year must be provided together.",
        )

    years_to_fetch: List[Optional[int]] = []
    if fiscal_year is not None:
        years_to_fetch = [fiscal_year]
    elif start_year is not None and end_year is not None:
        if end_year < start_year:
            start_year, end_year = end_year, start_year
        years_to_fetch = list(range(start_year, end_year + 1))
    else:
        years_to_fetch = [None]

    engine = get_engine()
    variants = _ticker_variants(ticker)
    if not variants:
        raise HTTPException(status_code=400, detail="Ticker is required.")
    metric_key = None
    if metric:
        metric_key = metric.strip().lower().replace(" ", "_")

    collected: List[database.FinancialFactRecord] = []
    canonical_symbol: Optional[str] = None
    for symbol in variants:
        symbol_collected: List[database.FinancialFactRecord] = []
        for year in years_to_fetch:
            try:
                symbol_collected.extend(
                    engine.financial_facts(
                        ticker=symbol,
                        fiscal_year=year,
                        metric=metric_key,
                        limit=(limit if year is None else None),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                raise HTTPException(status_code=500, detail=str(exc)) from exc
        if symbol_collected:
            collected = symbol_collected
            canonical_symbol = symbol
            break

    if not collected:
        raise HTTPException(
            status_code=404,
            detail=f"No filings found for {_display_ticker_symbol(variants[0])}.",
        )
    ticker_clean = canonical_symbol or variants[0]

    def _sort_key(fact: database.FinancialFactRecord) -> Tuple[int, str, str]:
        year = fact.fiscal_year if fact.fiscal_year is not None else -1
        period = fact.period or ""
        metric_name = fact.metric or ""
        return (-year, period, metric_name)

    collected.sort(key=_sort_key)
    if limit:
        collected = collected[:limit]

    items: List[FilingFact] = []
    for fact in collected:
        raw_payload = getattr(fact, "raw", None) or {}
        if isinstance(raw_payload, str):
            try:
                raw_payload = json.loads(raw_payload)
            except Exception:
                raw_payload = {}
        accession = raw_payload.get("accn") or fact.source_filing or None
        form = raw_payload.get("form")
        filed_at = raw_payload.get("filed")
        period_start = fact.period_start.isoformat() if fact.period_start else None
        period_end = fact.period_end.isoformat() if fact.period_end else None
        sec_url, archive_url, search_url = _build_filing_urls(accession, getattr(fact, "cik", None))
        items.append(
            FilingFact(
                ticker=fact.ticker,
                metric=fact.metric,
                value=fact.value,
                unit=fact.unit,
                fiscal_year=fact.fiscal_year,
                fiscal_period=fact.fiscal_period,
                period=fact.period,
                source=fact.source,
                source_filing=fact.source_filing,
                accession=accession,
                form=form,
                filed_at=filed_at,
                period_start=period_start,
                period_end=period_end,
                adjusted=fact.adjusted,
                adjustment_note=fact.adjustment_note,
                sec_url=sec_url,
                archive_url=archive_url,
                search_url=search_url,
            )
        )

    summary = FilingFactsSummary(
        count=len(items),
        fiscal_years=sorted(
            {item.fiscal_year for item in items if item.fiscal_year is not None}, reverse=True
        ),
        metrics=sorted({item.metric for item in items if item.metric}),
    )

    display_symbol = _display_ticker_symbol(ticker_clean)
    return FilingFactsResponse(ticker=display_symbol, items=items, summary=summary)


@app.get("/audit", response_model=AuditEventResponse)
def audit(
    ticker: str = Query(...),
    fiscal_year: Optional[int] = Query(None),
) -> AuditEventResponse:
    """Return recorded audit trail events for a ticker."""
    engine = get_engine()
    requested = (ticker or "").strip().upper()
    events = None
    canonical = None
    for symbol in _ticker_variants(ticker):
        events = engine.audit_events(symbol, fiscal_year=fiscal_year, limit=20)
        if events:
            canonical = symbol
            break
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit events recorded for {requested or _display_ticker_symbol(_normalise_ticker_symbol(ticker))}.",
        )
    payload = [
        {
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "details": event.details,
            "created_at": event.created_at.isoformat(),
            "created_by": event.created_by,
        }
        for event in events
    ]
    display_symbol = requested or _display_ticker_symbol(canonical or _normalise_ticker_symbol(ticker))
    return AuditEventResponse(ticker=display_symbol, events=payload)

