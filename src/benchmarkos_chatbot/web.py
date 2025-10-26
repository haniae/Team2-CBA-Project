"""FastAPI service exposing the BenchmarkOS chatbot, analytics API, and web UI."""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from io import BytesIO
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import AnalyticsEngine, BenchmarkOSChatbot, database, load_settings
from .help_content import HELP_TEXT, get_help_metadata
from .dashboard_utils import (
    _collect_series as _collect_series_util,
    _display_ticker_symbol as _display_ticker_symbol_util,
    _format_billions as _format_billions_util,
    _format_number as _format_number_util,
    _format_percent as _format_percent_util,
    _latest_metric_value as _latest_metric_value_util,
    _lookup_company_name as _lookup_company_name_util,
    _metric_year as _metric_year_util,
    _normalise_ticker_symbol as _normalise_ticker_symbol_util,
    _round_two as _round_two_util,
    _valuation_per_share as _valuation_per_share_util,
    build_cfi_dashboard_payload,
    build_cfi_compare_payload,
)
from .export_pipeline import generate_dashboard_export


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


# Custom handlers with no-cache headers to prevent stale JavaScript
# IMPORTANT: These MUST be defined BEFORE app.mount() to take precedence

@app.get("/")
async def serve_index():
    """Serve index.html with no-cache headers to ensure fresh JavaScript."""
    index_path = PACKAGE_STATIC / "index.html" if PACKAGE_STATIC.exists() else FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/static/app.js")
async def serve_app_js():
    """Serve app.js with no-cache headers."""
    js_path = PACKAGE_STATIC / "app.js" if PACKAGE_STATIC.exists() else FRONTEND_DIR / "app.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="app.js not found")
    
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/static/styles.css")
async def serve_styles_css():
    """Serve styles.css with no-cache headers."""
    css_path = PACKAGE_STATIC / "styles.css" if PACKAGE_STATIC.exists() else FRONTEND_DIR / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found")
    
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# Mount static files for other assets (images, fonts, etc.)
# The specific routes above will take precedence for app.js, styles.css, and index.html
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
    sources: Optional[List[Dict[str, str]]] = None


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
    dashboard: Optional[Dict[str, Any]] = None
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
    """Wrapper to normalise ticker symbols using shared dashboard helpers."""
    return _normalise_ticker_symbol_util(value)


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
    return _display_ticker_symbol_util(symbol)


def _metric_year(record: Optional[database.MetricRecord]) -> Optional[int]:
    """Extract a fiscal year from a metric snapshot."""
    return _metric_year_util(record)


def _format_billions(value: Optional[float]) -> Optional[float]:
    """Scale raw currency values to billions with compact precision."""
    return _format_billions_util(value)


def _format_percent(value: Optional[float]) -> Optional[float]:
    """Convert fractional metrics into percentage values."""
    return _format_percent_util(value)


def _lookup_company_name(ticker: str) -> Optional[str]:
    """Fetch a human-readable company name for the supplied ticker."""
    settings = get_settings()
    return _lookup_company_name_util(Path(settings.database_path), ticker)


def _latest_metric_value(
    latest: Dict[str, database.MetricRecord],
    *names: str,
) -> Optional[float]:
    """Return the newest available metric value matching any of the supplied aliases."""
    return _latest_metric_value_util(latest, *names)


def _round_two(value: Optional[float]) -> Optional[float]:
    """Round a float to two decimal places when present."""
    return _round_two_util(value)


def _valuation_per_share(
    latest: Dict[str, database.MetricRecord],
) -> Optional[Dict[str, Optional[float]]]:
    """Derive simple valuation scenarios (per share) from available metrics."""
    return _valuation_per_share_util(latest)


def _collect_series(
    records: Iterable[database.MetricRecord],
    metric: str,
    *,
    scale_billions: bool = False,
) -> Dict[int, float]:
    """Return a year -> value mapping for a metric."""
    return _collect_series_util(records, metric, scale_billions=scale_billions)


def _format_number(value: Optional[float], decimals: int = 1) -> Optional[str]:
    """Format a float with trimmed trailing zeroes."""
    return _format_number_util(value, decimals)


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
        dashboard=structured.get("dashboard"),
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
    try:
        payload = build_cfi_compare_payload(
            engine,
            requested,
            benchmark_label=benchmark,
            strict=True,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "No metric snapshots" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    if not payload:
        raise HTTPException(status_code=404, detail="Unable to construct comparison dashboard.")
    return payload

@app.get("/api/dashboard/cfi")
def cfi_dashboard(
    ticker: str = Query(
        "AAPL",
        description="Ticker symbol to render in the classic CFI dashboard (defaults to AAPL).",
    )
) -> Dict[str, Any]:
    """Return the single-company payload required by the classic CFI dashboard."""
    engine = get_engine()
    payload = build_cfi_dashboard_payload(engine, ticker)
    if not payload:
        display = _display_ticker_symbol(_normalise_ticker_symbol(ticker))
        raise HTTPException(status_code=404, detail=f"No dashboard data available for {display}.")
    return payload


@app.get("/api/export/cfi")
def export_cfi(
    format: str = Query(
        ...,
        description="Export format to generate (pdf, pptx, or xlsx).",
        regex="^(?i)(pdf|pptx?|xlsx|excel)$",
    ),
    ticker: str = Query(
        "AAPL",
        description="Ticker symbol to export (defaults to AAPL).",
    ),
) -> StreamingResponse:
    """Generate an executive export for the classic dashboard."""
    engine = get_engine()
    try:
        result = generate_dashboard_export(engine, ticker, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    buffer = BytesIO(result.content)
    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Export-Format": format.lower(),
    }
    return StreamingResponse(buffer, media_type=result.media_type, headers=headers)


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

