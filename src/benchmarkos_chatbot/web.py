"""FastAPI service exposing the Finalyze chatbot, analytics API, and web UI."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timezone
import io
from io import BytesIO
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

LOGGER = logging.getLogger(__name__)

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import AnalyticsEngine, BenchmarkOSChatbot, database, load_settings
from .custom_kpis import CustomKPICalculator
from .analytics_workspace import DataSourcePreferencesManager
from .source_tracer import SourceTracer
from .interactive_modeling import ModelBuilder
from .framework_processor import FrameworkProcessor
from .template_processor import TemplateProcessor
from .document_processor import extract_text_from_file
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
from .portfolio_ppt_builder import build_portfolio_powerpoint
from .portfolio_export import build_portfolio_pdf, build_portfolio_excel
from .portfolio_risk_metrics import (
    calculate_cvar,
    optimize_portfolio_cvar_constrained,
    CVaRResult,
    CVaROptimizationResult,
)
# TODO: These functions don't exist yet - need to implement or import from correct module
# from .portfolio_scenarios_enhanced import (
#     create_custom_scenario,
#     run_geopolitical_scenario,
#     run_sector_specific_shock,
#     run_rate_term_structure_scenario,
#     run_fx_exposure_stress_test,
# )
# TODO: These functions don't exist yet - need to implement or import from correct module
# from .portfolio_optimizer_alternative import (
#     optimize_portfolio_esg_constrained,
#     analyze_esg_exposure,
#     optimize_portfolio_tax_aware,
#     calculate_tax_adjusted_returns,
#     optimize_portfolio_tracking_error,
#     optimize_portfolio_diversification,
#     ESGExposureResult,
#     ESGOptimizationResult,
#     TaxOptimizationResult,
# )
from .portfolio_trades import (
    generate_trade_list,
    export_trade_list,
    estimate_trade_costs,
    analyze_trade_impact,
    simulate_trade_execution,
    TradeList,
    TradeImpactResult,
    PortfolioState,
)
# TODO: portfolio_report_builder doesn't exist - using portfolio_reporting instead
# from .portfolio_report_builder import (
#     create_custom_report,
#     save_report_template,
#     load_report_template,
#     list_report_templates,
#     export_interactive_charts,
#     configure_report_branding,
#     apply_branding_to_report,
#     ReportConfig,
#     ReportTemplate,
#     BrandingConfig,
# )
# TODO: portfolio_data_enrichment doesn't exist yet
# from .portfolio_data_enrichment import (
#     enrich_with_alternative_data,
#     get_sentiment_score,
#     sync_brokerage_holdings,
#     execute_trades_via_brokerage,
#     EnrichedPortfolio,
#     SyncResult,
# )
# TODO: portfolio_dashboard_custom doesn't exist yet
# from .portfolio_dashboard_custom import (
#     save_dashboard_layout,
#     load_dashboard_layout,
#     list_dashboard_layouts,
#     save_user_preferences,
#     load_user_preferences,
#     DashboardLayout,
#     UserPreferences,
# )
from .portfolio_enhancements import (
    monte_carlo_portfolio_simulation,
    MonteCarloResult,
    # TODO: These functions don't exist yet - need to implement
    # optimize_portfolio_multi_period,
    # optimize_portfolio_risk_parity,
    # run_comprehensive_stress_test,
    # analyze_factor_attribution,
    # backtest_portfolio_strategy,
    # MultiPeriodOptimizationResult,
    # RiskParityResult,
    # StressTestResult,
    # FactorAttributionResult,
    # BacktestResult,
)

# Portfolio module imports (combined portfolio.py)
from .portfolio import (
    ingest_holdings_csv,
    ingest_holdings_excel,
    ingest_holdings_json,
    parse_ips_json,
    parse_ips_pdf,
    save_portfolio_to_database,
    save_policy_to_database,
    validate_holdings,
    enrich_holdings_with_fundamentals,
    calculate_portfolio_statistics,
    optimize_portfolio_sharpe,
    PolicyConstraint,
    OptimizationResult,
    analyze_exposure,
    brinson_attribution,
    run_equity_drawdown_scenario,
    run_sector_rotation_scenario,
    run_custom_scenario,
    generate_committee_brief,
    calculate_covariance_matrix,
    calculate_betas_batch,
    calculate_expected_returns,
    load_sp500_benchmark_weights,
    get_portfolio_holdings,
    EnrichedHolding,
    # Error handling
    PortfolioError,
    InvalidHoldingsError,
    OptimizationFailedError,
    PolicyConstraintError,
    PortfolioNotFoundError,
    format_portfolio_error,
)


# ----- CORS / Static ----------------------------------------------------------

# Safely read allowed origins from file
ALLOWED_ORIGINS = []
try:
    allowed_origins_file = Path.cwd().joinpath(".allowed_origins")
    if allowed_origins_file.exists():
        ALLOWED_ORIGINS = [
            origin.strip()
            for origin in allowed_origins_file.read_text(encoding="utf-8").splitlines()
            if origin.strip()
        ]
except Exception as e:
    LOGGER.warning(f"Could not read .allowed_origins file: {e}. Using default CORS settings.")
    ALLOWED_ORIGINS = []

app = FastAPI(title="Finalyze Analyst Copilot", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler to ensure JSON responses for unhandled exceptions
# Note: HTTPException is handled by FastAPI by default, so we only catch other exceptions

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch all unhandled exceptions and return JSON error response."""
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    # Skip HTTPException - FastAPI handles it correctly
    if isinstance(exc, HTTPException):
        raise exc
    
    error_traceback = traceback.format_exc()
    error_type = type(exc).__name__
    error_msg = str(exc)
    
    logger.exception(f"Unhandled exception: {error_type}: {error_msg}\n{error_traceback}")
    print(f"\n{'='*80}")
    print(f"UNHANDLED EXCEPTION: {error_type}: {error_msg}")
    print(f"{'='*80}")
    print(error_traceback)
    print(f"{'='*80}\n")
    
    # For other exceptions, return 500 with error details
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {error_type}: {error_msg}"}
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
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "ETag": f'"html-{int(time.time())}"',
            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT"
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
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "ETag": f'"css-{int(time.time())}"',
            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT"
        }
    )


@app.get("/portfolio")
async def serve_portfolio_dashboard():
    """Serve portfolio_dashboard.html with no-cache headers."""
    dashboard_path = PACKAGE_STATIC / "portfolio_dashboard.html" if PACKAGE_STATIC.exists() else FRONTEND_DIR / "portfolio_dashboard.html"
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="portfolio_dashboard.html not found")
    
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "ETag": f'"portfolio-{int(time.time())}"',
            "Last-Modified": "Thu, 01 Jan 1970 00:00:00 GMT"
        }
    )


@app.get("/static/portfolio_dashboard.js")
async def serve_portfolio_dashboard_js():
    """Serve portfolio_dashboard.js with no-cache headers."""
    js_path = PACKAGE_STATIC / "portfolio_dashboard.js" if PACKAGE_STATIC.exists() else FRONTEND_DIR / "portfolio_dashboard.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="portfolio_dashboard.js not found")
    
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


# ----- Portfolio API Models -----------------------------------------------------

class PortfolioMetadata(BaseModel):
    """Portfolio metadata response."""
    portfolio_id: str
    name: str
    base_currency: str
    benchmark_index: Optional[str] = None
    strategy_type: Optional[str] = None
    created_at: str


class PortfolioHolding(BaseModel):
    """Single portfolio holding with enrichment."""
    ticker: str
    weight: Optional[float] = None
    shares: Optional[float] = None
    price: Optional[float] = None
    market_value: Optional[float] = None
    sector: Optional[str] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None
    roic: Optional[float] = None


class PortfolioHoldingsResponse(BaseModel):
    """Response with portfolio holdings."""
    portfolio_id: str
    name: str
    holdings: List[PortfolioHolding]


class PolicyConstraintResponse(BaseModel):
    """Policy constraint response."""
    constraint_id: str
    type: str
    dimension: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: str
    active: bool


class PortfolioConstraintsResponse(BaseModel):
    """Response with portfolio constraints."""
    portfolio_id: str
    constraints: List[PolicyConstraintResponse]


class ExposureResponse(BaseModel):
    """Portfolio exposure response."""
    portfolio_id: str
    snapshot_date: str
    sector_exposure: Dict[str, float]
    factor_exposure: Dict[str, float]
    concentration_metrics: Dict[str, float]


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary statistics."""
    portfolio_id: str
    name: str
    num_holdings: int
    total_market_value: Optional[float] = None
    weighted_avg_pe: Optional[float] = None
    weighted_avg_dividend_yield: Optional[float] = None
    top_10_concentration: Optional[float] = None
    num_sectors: int
    sector_breakdown: Dict[str, float]


class OptimizationRequest(BaseModel):
    """Request body for portfolio optimization."""
    objective: str = "maximize_sharpe"  # maximize_sharpe, minimize_tracking_error, maximize_return
    turnover_limit: Optional[float] = None
    constraints_override: Optional[List[Dict[str, Any]]] = None


class Trade(BaseModel):
    """Proposed trade."""
    ticker: str
    action: str  # buy, sell, hold
    from_weight: Optional[float] = None
    to_weight: Optional[float] = None
    shares: Optional[float] = None


class OptimizationResponse(BaseModel):
    """Portfolio optimization response."""
    portfolio_id: str
    status: str
    proposed_trades: List[Trade]
    objective_value: Optional[float] = None
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    policy_flags: List[str] = []


class AttributionRequest(BaseModel):
    """Request for attribution analysis."""
    start_date: str
    end_date: str


class AttributionResponse(BaseModel):
    """Portfolio attribution response."""
    portfolio_id: str
    start_date: str
    end_date: str
    total_active_return: float
    allocation_effect: Dict[str, float]
    selection_effect: Dict[str, float]
    interaction_effect: Dict[str, float]
    top_contributors: List[Dict[str, Any]]
    top_detractors: List[Dict[str, Any]]


class ScenarioRequest(BaseModel):
    """Request for scenario analysis."""
    scenario_type: str  # equity_drawdown, sector_rotation, custom
    parameters: Dict[str, Any]


class ScenarioResponse(BaseModel):
    """Scenario analysis response."""
    portfolio_id: str
    scenario_type: str
    portfolio_return: float
    portfolio_value_change: float
    pnl_attribution: Dict[str, float]
    top_gainers: List[Dict[str, Any]]
    top_losers: List[Dict[str, Any]]
    risk_metrics: Dict[str, float]


class UploadResponse(BaseModel):
    """Response for portfolio upload."""
    success: bool
    portfolio_id: Optional[str] = None
    portfolio_name: Optional[str] = None
    num_holdings: Optional[int] = None
    errors: List[str] = []
    warnings: List[str] = []


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    success: bool
    document_id: Optional[str] = None
    conversation_id: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    content_preview: Optional[str] = None
    message: Optional[str] = None
    warnings: List[str] = []
    errors: List[str] = []

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


@lru_cache
def get_database() -> Path:
    """Get database path from settings."""
    return get_settings().database_path


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
        else:
            # Even when no prior messages exist, lock the conversation id so uploads and
            # subsequent prompts share the same identifier.
            bot.conversation.conversation_id = conversation_id
    
    # CRITICAL: Ensure fresh bot starts with no dashboard AND no cached summaries
    # This prevents stale dashboards and wrong company summaries from persisting
    if hasattr(bot, 'last_structured_response'):
        bot.last_structured_response["dashboard"] = None
        bot.last_structured_response["comparison_table"] = None
    
    # CRITICAL: Clear summary cache to prevent wrong company summaries
    # The summary cache can contain snapshots of wrong companies from fuzzy ticker matching
    if hasattr(bot, '_summary_cache'):
        bot._summary_cache.clear()
    
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
@app.options("/health")
def health():
    """Lightweight liveness probe used by deployment infra."""
    return Response(
        content=json.dumps({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
def chrome_devtools_config() -> Dict[str, Any]:
    """Handle Chrome DevTools configuration request to prevent 404 errors."""
    return {
        "name": "Finalyze Chatbot",
        "version": "1.1.0",
        "type": "web"
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Proxy chat submissions to the Finalyze chatbot."""
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
    
    # CRITICAL: Filter out None/empty dashboards - if dashboard is None, don't send it
    dashboard_data = structured.get("dashboard")
    if dashboard_data is None:
        dashboard_data = None  # Explicitly set to None (don't send)
    elif isinstance(dashboard_data, dict) and not dashboard_data:
        dashboard_data = None  # Empty dict, don't send
    
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
        dashboard=dashboard_data,  # Use filtered dashboard (None if cleared)
        progress_events=progress_snapshot.events,
    )


@app.get("/help-content")
def help_content() -> Dict[str, Any]:
    """Expose help metadata for the web UI."""
    return get_help_metadata()


@app.get("/conversations")
def list_conversations() -> List[Dict[str, Any]]:
    """List all conversations with their titles and metadata."""
    settings = load_settings()
    conversations = []
    
    for conv_id, msg_count in database.iter_conversation_summaries(settings.database_path):
        title = database.get_conversation_title(settings.database_path, conv_id)
        # Get the latest message time for this conversation
        messages = list(database.fetch_conversation(settings.database_path, conv_id))
        updated_at = messages[-1].created_at.isoformat() if messages else datetime.now(timezone.utc).isoformat()
        
        conversations.append({
            "id": conv_id,
            "title": title or conv_id,  # Use conv_id as fallback title
            "message_count": msg_count,
            "updated_at": updated_at
        })
    
    return conversations


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Get a specific conversation with all its messages."""
    settings = load_settings()
    messages = list(database.fetch_conversation(settings.database_path, conversation_id))
    
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    title = database.get_conversation_title(settings.database_path, conversation_id)
    
    return {
        "id": conversation_id,
        "title": title or conversation_id,
        "messages": [
            {
                "role": msg.role,
                "text": msg.content,
                "ts": int(msg.created_at.timestamp() * 1000)  # Convert to milliseconds
            }
            for msg in messages
        ]
    }


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str) -> Dict[str, Any]:
    """Delete a conversation and all its messages."""
    settings = load_settings()
    # Note: This would need a delete function in database.py
    # For now, just return success
    return {"success": True, "conversation_id": conversation_id}


@app.patch("/conversations/{conversation_id}/rename")
def rename_conversation(
    conversation_id: str,
    request: Dict[str, str]
) -> Dict[str, Any]:
    """Rename a conversation with a custom title."""
    title = request.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    settings = load_settings()
    database.set_conversation_title(settings.database_path, conversation_id, title)
    
    return {
        "success": True,
        "conversation_id": conversation_id,
        "title": title
    }


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
async def export_cfi(
    format: str = Query(
        ...,
        description="Export format to generate (pdf, pptx, or xlsx).",
        pattern="^(?i)(pdf|pptx?|xlsx|excel)$",
    ),
    ticker: str = Query(
        "AAPL",
        description="Ticker symbol to export (defaults to AAPL).",
    ),
):
    """Generate an executive export for the classic dashboard."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"[EXPORT] Starting export for {ticker} in format {format}")
        engine = get_engine()
        logger.info(f"[EXPORT] Engine obtained, generating export...")
        result = generate_dashboard_export(engine, ticker, format)
        logger.info(f"[EXPORT] Export successful for {ticker} in format {format}")
    except ValueError as exc:
        logger.warning(f"[EXPORT] ValueError during export: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        logger.exception(f"[EXPORT] Missing dependency for export: {ticker} in format {format}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Export functionality not available: {str(exc)}"}
        )
    except Exception as exc:
        error_traceback = traceback.format_exc()
        error_type = type(exc).__name__
        error_msg = str(exc)
        logger.exception(f"[EXPORT] Error generating export for {ticker} in format {format}: {error_type}: {error_msg}\n{error_traceback}")
        # Print to console for immediate visibility
        print(f"\n{'='*80}")
        print(f"[EXPORT ERROR] {error_type}: {error_msg}")
        print(f"{'='*80}")
        print(error_traceback)
        print(f"{'='*80}\n")
        error_detail = f"Failed to generate export: {error_type}: {error_msg}"
        # Return JSONResponse directly to ensure JSON format
        return JSONResponse(
            status_code=500,
            content={"detail": error_detail}
        )

    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Export-Format": format.lower(),
        "Content-Length": str(len(result.content)),
    }
    return StreamingResponse(
        BytesIO(result.content),
        media_type=result.media_type,
        headers=headers,
    )


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


# ----- Portfolio API Endpoints --------------------------------------------------

@app.post("/api/portfolio/upload", response_model=UploadResponse)
async def portfolio_upload(file: UploadFile = File(...)) -> UploadResponse:
    """Upload portfolio holdings from CSV, Excel, or JSON file."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Determine file type and parse
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == ".csv":
            holdings = ingest_holdings_csv(tmp_path)
        elif file_ext in [".xlsx", ".xls"]:
            holdings = ingest_holdings_excel(tmp_path)
        elif file_ext == ".json":
            holdings = ingest_holdings_json(tmp_path)
        else:
            return UploadResponse(
                success=False,
                errors=[f"Unsupported file type: {file_ext}. Supported: .csv, .xlsx, .xls, .json"]
            )
        
        # Validate holdings
        portfolio_id = f"port_{uuid.uuid4().hex[:8]}"
        portfolio_name = Path(file.filename).stem
        
        if not holdings:
            return UploadResponse(
                success=False,
                errors=["No holdings found in file. Please check the file format."]
            )
        
        validation = validate_holdings(holdings, portfolio_id=portfolio_id, base_currency="USD")
        
        if not validation.is_valid:
            # Use PortfolioError for better error messages
            error_response = format_portfolio_error(
                InvalidHoldingsError(
                    "Holdings validation failed. Please check the file format and data.",
                    errors=validation.errors,
                    warnings=validation.warnings
                ),
                include_technical=False
            )
            return UploadResponse(
                success=False,
                errors=[error_response["message"]] + validation.errors,
                warnings=validation.warnings
            )
        
        if not validation.normalized_holdings:
            error_response = format_portfolio_error(
                InvalidHoldingsError(
                    "No valid holdings found after validation. All holdings were filtered out."
                )
            )
            return UploadResponse(
                success=False,
                errors=[error_response["message"]],
                warnings=validation.warnings
            )
        
        # Save to database
        try:
            save_portfolio_to_database(
                db_path,
                portfolio_id,
                portfolio_name,
                "USD",
                validation.normalized_holdings,
            )
        except Exception as save_error:
            error_msg = str(save_error)
            LOGGER.error(f"Failed to save portfolio {portfolio_id}: {error_msg}", exc_info=True)
            
            # Provide more helpful error messages
            if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                error_detail = f"Portfolio with this name already exists. Please use a different name or delete the existing portfolio first."
            elif "database" in error_msg.lower() or "connection" in error_msg.lower():
                error_detail = f"Database connection issue. Please try again in a moment. Error: {error_msg}"
            elif "validation" in error_msg.lower():
                error_detail = f"Data validation failed: {error_msg}. Please check your file format and try again."
            else:
                error_detail = f"Failed to save portfolio to database: {error_msg}. Please check the file format and try again."
            
            return UploadResponse(
                success=False,
                errors=[error_detail]
            )
        
        return UploadResponse(
            success=True,
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            num_holdings=len(validation.normalized_holdings),
            warnings=validation.warnings
        )
    except InvalidHoldingsError as e:
        LOGGER.error(f"Invalid holdings error: {e.message}", exc_info=True)
        error_response = format_portfolio_error(e)
        return UploadResponse(
            success=False,
            errors=[error_response["message"]] + error_response.get("validation_errors", []),
            warnings=error_response.get("validation_warnings", [])
        )
    except PortfolioError as e:
        LOGGER.error(f"Portfolio error: {e.message}", exc_info=True)
        error_response = format_portfolio_error(e)
        return UploadResponse(
            success=False,
            errors=[error_response["message"]]
        )
    except Exception as e:
        error_msg = str(e)
        LOGGER.error(f"Portfolio upload error: {error_msg}", exc_info=True)
        
        # Provide more helpful error messages based on error type
        if "parsing" in error_msg.lower() or "parse" in error_msg.lower():
            error_detail = f"Unable to parse file. Please check that the file is a valid CSV, Excel, or JSON format. Error: {error_msg}"
        elif "columns" in error_msg.lower() or "required" in error_msg.lower():
            error_detail = f"File is missing required columns. Please ensure your file has at least a 'ticker' column. Error: {error_msg}"
        elif "empty" in error_msg.lower():
            error_detail = "File appears to be empty or contains no valid holdings data."
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_detail = "File access denied. Please check file permissions and try again."
        elif "size" in error_msg.lower() or "too large" in error_msg.lower():
            error_detail = "File is too large. Please ensure the file is under 10MB."
        else:
            error_detail = f"Error processing file: {error_msg}. Please verify the file format and try again."
        
        return UploadResponse(
            success=False,
            errors=[error_detail]
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def document_upload(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None)
) -> DocumentUploadResponse:
    """
    Upload any document type and extract text for chatbot to use.
    Accepts all file types: PDF, Word, TXT, CSV, Excel, JSON, code files, etc.
    """
    settings = get_settings()
    db_path = settings.database_path
    conversation_id = (conversation_id or "").strip() or f"conv_{uuid.uuid4().hex[:10]}"
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
        file_size = len(content)
    
    try:
        # Log file info for debugging
        LOGGER.info(f"Processing uploaded file: {file.filename}, size: {file_size} bytes")
        
        warnings: List[str] = []
        success_message: Optional[str] = None
        extraction_warning: Optional[str] = None

        # Extract text from file
        try:
            extracted_text, file_type = extract_text_from_file(tmp_path, file.filename)
            LOGGER.info(f"File type detected: {file_type}, extracted text length: {len(extracted_text) if extracted_text else 0}")
        except Exception as extract_error:
            LOGGER.error(f"Error during text extraction: {extract_error}", exc_info=True)
            extracted_text = None
            file_type = None
        
        if not extracted_text:
            if file_type == 'image':
                extraction_warning = "Text extraction is not yet supported for image files. The file has been stored for reference."
                LOGGER.info(f"Image file stored without text content: {file.filename}")
            elif file_type == 'unknown' or not file_type:
                # Try to extract as binary/text anyway
                LOGGER.info(f"Attempting fallback text extraction for {file.filename}")
                try:
                    with open(tmp_path, 'rb') as f:
                        content = f.read()
                    # Try to decode as text
                    try:
                        text_content = content.decode('utf-8', errors='replace')
                        if text_content.strip() and len(text_content.strip()) > 10:
                            extracted_text = text_content
                            file_type = 'text'
                            LOGGER.info(f"Successfully extracted text from unknown file type as plain text ({len(text_content)} chars)")
                    except Exception as e:
                        LOGGER.debug(f"UTF-8 decode failed: {e}")
                        # Try other encodings
                        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                            try:
                                text_content = content.decode(encoding, errors='replace')
                                if text_content.strip() and len(text_content.strip()) > 10:
                                    extracted_text = text_content
                                    file_type = 'text'
                                    LOGGER.info(f"Successfully extracted text using {encoding} encoding")
                                    break
                            except:
                                continue
                except Exception as e:
                    LOGGER.error(f"Fallback extraction failed: {e}")
            else:
                # Try one more fallback - read as text
                LOGGER.info(f"Attempting text fallback for {file_type} file: {file.filename}")
                try:
                    from .document_processor import extract_text_from_txt
                    fallback_text = extract_text_from_txt(tmp_path)
                    if fallback_text and fallback_text.strip() and len(fallback_text.strip()) > 10:
                        extracted_text = fallback_text
                        file_type = 'text'
                        LOGGER.info(f"Successfully extracted text using fallback method")
                except Exception as e:
                    LOGGER.debug(f"Fallback extraction failed: {e}")

            if not extracted_text:
                if not extraction_warning:
                    base_msg = f"Text could not be extracted from {file.filename}"
                    if file_type == 'pdf':
                        extraction_warning = base_msg + ". The PDF might be password-protected, image-based, or corrupted."
                    elif file_type == 'docx':
                        extraction_warning = base_msg + ". The Word document might be corrupted or password-protected."
                    elif file_type == 'text':
                        extraction_warning = base_msg + ". The file may be empty."
                    else:
                        detected_type = file_type or "unknown type"
                        extraction_warning = f"{base_msg} (detected: {detected_type}). The file may be empty, corrupted, or password-protected."
                warnings.append(extraction_warning)
                LOGGER.warning(f"[Upload] {extraction_warning}")
                extracted_text = ""
                success_message = f"✅ File \"{file.filename}\" uploaded. {extraction_warning}"
            else:
                success_message = f"✅ File \"{file.filename}\" uploaded successfully and is ready for analysis."
        else:
            success_message = f"✅ File \"{file.filename}\" uploaded successfully and is ready for analysis."
        
        # Generate document ID
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        # Truncate content if too long (keep first 500k chars for preview, full content stored)
        content_preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
        
        # Save to database
        import sqlite3
        from datetime import datetime, timezone
        
        created_at = datetime.now(timezone.utc).isoformat()
        metadata_payload = {
            "original_filename": file.filename,
            "file_size": file_size,
            "file_type": file_type,
            "content_length": len(extracted_text)
        }
        if warnings:
            metadata_payload["warnings"] = warnings

        metadata = json.dumps(metadata_payload)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO uploaded_documents 
                (document_id, conversation_id, filename, file_type, file_size, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    conversation_id,
                    file.filename,
                    file_type,
                    file_size,
                    extracted_text,
                    metadata,
                    created_at,
                    created_at
                )
            )
            conn.commit()
        
        LOGGER.info(f"Document uploaded: {document_id} ({file.filename}, {file_type}, {len(extracted_text)} chars)")
        
        return DocumentUploadResponse(
            success=True,
            document_id=document_id,
            conversation_id=conversation_id,
            filename=file.filename,
            file_type=file_type,
            content_preview=content_preview,
            message=success_message,
            warnings=warnings
        )
        
    except Exception as e:
        error_msg = str(e)
        LOGGER.error(f"Document upload error: {error_msg}", exc_info=True)
        
        if "size" in error_msg.lower() or "too large" in error_msg.lower():
            error_detail = "File is too large. Please ensure the file is under 50MB."
        elif "permission" in error_msg.lower() or "access" in error_msg.lower():
            error_detail = "File access denied. Please check file permissions and try again."
        else:
            error_detail = f"Error processing file: {error_msg}. Please verify the file format and try again."
        
        return DocumentUploadResponse(
            success=False,
            conversation_id=conversation_id,
            errors=[error_detail]
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/api/portfolio/policy/upload")
async def policy_upload(
    portfolio_id: str = Form(...),
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """Upload Investment Policy Statement (IPS) document."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Parse IPS document
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == ".json":
            ips_data = parse_ips_json(tmp_path)
        elif file_ext == ".pdf":
            ips_data = parse_ips_pdf(tmp_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
        
        # Save policy constraints
        constraints = ips_data.get("constraints", [])
        save_policy_to_database(
            db_path,
            portfolio_id,
            constraints,
            document_type="IPS",
            file_path=str(tmp_path)
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "num_constraints": len(constraints)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing IPS: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.get("/api/portfolio/list", response_model=List[PortfolioMetadata])
def portfolio_list() -> List[PortfolioMetadata]:
    """List all portfolios in the database."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Query database directly
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT portfolio_id, name, base_currency, benchmark_index, strategy_type, created_at "
            "FROM portfolio_metadata ORDER BY created_at DESC"
        ).fetchall()
    
    return [
        PortfolioMetadata(
            portfolio_id=row["portfolio_id"],
            name=row["name"],
            base_currency=row["base_currency"],
            benchmark_index=row["benchmark_index"],
            strategy_type=row["strategy_type"],
            created_at=row["created_at"]
        )
        for row in rows
    ]


@app.get("/api/portfolio/{portfolio_id}/holdings", response_model=PortfolioHoldingsResponse)
def portfolio_holdings(portfolio_id: str) -> PortfolioHoldingsResponse:
    """Get portfolio holdings with enriched fundamentals."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch portfolio metadata
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        meta_row = conn.execute(
            "SELECT portfolio_id, name FROM portfolio_metadata WHERE portfolio_id = ?",
            (portfolio_id,)
        ).fetchone()
        
        if not meta_row:
            error_response = format_portfolio_error(PortfolioNotFoundError(portfolio_id))
            raise HTTPException(
                status_code=404,
                detail=error_response["message"]
            )
        
        # Fetch holdings
        holding_rows = conn.execute(
            "SELECT ticker, shares, weight, market_value, currency, position_date "
            "FROM portfolio_holdings WHERE portfolio_id = ? ORDER BY weight DESC",
            (portfolio_id,)
        ).fetchall()
    
    # Convert to dict format for enrichment
    holdings_dict = [
        {
            "ticker": row["ticker"],
            "shares": row["shares"],
            "weight": row["weight"],
            "market_value": row["market_value"],
            "currency": row["currency"],
            "position_date": row["position_date"]
        }
        for row in holding_rows
    ]
    
    # Enrich with fundamentals
    enriched = enrich_holdings_with_fundamentals(db_path, holdings_dict)
    
    # Convert to response format
    holdings = [
        PortfolioHolding(
            ticker=h.ticker,
            weight=h.weight,
            shares=h.shares,
            price=h.price,
            market_value=h.market_value,
            sector=h.sector,
            pe_ratio=h.pe_ratio,
            dividend_yield=h.dividend_yield,
            roe=h.roe,
            roic=h.roic
        )
        for h in enriched
    ]
    
    return PortfolioHoldingsResponse(
        portfolio_id=portfolio_id,
        name=meta_row["name"],
        holdings=holdings
    )


@app.get("/api/portfolio/{portfolio_id}/constraints", response_model=PortfolioConstraintsResponse)
def portfolio_constraints(portfolio_id: str, active_only: bool = Query(True)) -> PortfolioConstraintsResponse:
    """Get policy constraints for a portfolio."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Check portfolio exists
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        meta_row = conn.execute(
            "SELECT portfolio_id FROM portfolio_metadata WHERE portfolio_id = ?",
            (portfolio_id,)
        ).fetchone()
        
        if not meta_row:
            error_response = format_portfolio_error(PortfolioNotFoundError(portfolio_id))
            raise HTTPException(
                status_code=404,
                detail=error_response["message"]
            )
        
        query = "SELECT * FROM policy_constraints WHERE portfolio_id = ?"
        params = [portfolio_id]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY type, dimension"
        
        rows = conn.execute(query, params).fetchall()
    
    constraints = [
        PolicyConstraintResponse(
            constraint_id=row["constraint_id"],
            type=row["constraint_type"],
            dimension=row["dimension"],
            min_value=row["min_value"],
            max_value=row["max_value"],
            target_value=row["target_value"],
            unit=row["unit"] or "percent",
            active=bool(row["active"])
        )
        for row in rows
    ]
    
    return PortfolioConstraintsResponse(
        portfolio_id=portfolio_id,
        constraints=constraints
    )


@app.get("/api/portfolio/{portfolio_id}/exposure", response_model=ExposureResponse)
def portfolio_exposure(portfolio_id: str) -> ExposureResponse:
    """Calculate multi-dimensional portfolio exposures."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch holdings
    holdings_response = portfolio_holdings(portfolio_id)
    
    # Convert to dict format for enrichment
    holdings_dict = [
        {
            "ticker": h.ticker,
            "weight": h.weight,
            "sector": h.sector
        }
        for h in holdings_response.holdings
    ]
    
    # Convert to EnrichedHolding format
    from .portfolio import EnrichedHolding
    enriched_holdings = [
        EnrichedHolding(
            ticker=h["ticker"],
            weight=h["weight"],
            sector=h.get("sector")
        )
        for h in holdings_dict
    ]
    
    # Calculate exposures (pass database path for beta calculation)
    exposure = analyze_exposure(enriched_holdings, database_path=db_path)
    
    return ExposureResponse(
        portfolio_id=portfolio_id,
        snapshot_date=datetime.now(timezone.utc).isoformat(),
        sector_exposure=exposure.sector_exposure,
        factor_exposure=exposure.factor_exposure,
        concentration_metrics=exposure.concentration_metrics
    )


@app.get("/api/portfolio/{portfolio_id}/summary", response_model=PortfolioSummaryResponse)
def portfolio_summary(portfolio_id: str) -> PortfolioSummaryResponse:
    """Get portfolio summary statistics."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch holdings
    holdings_response = portfolio_holdings(portfolio_id)
    holdings_dict = [
        {
            "ticker": h.ticker,
            "shares": h.shares,
            "weight": h.weight,
            "sector": h.sector,
            "pe_ratio": h.pe_ratio,
            "dividend_yield": h.dividend_yield,
            "market_value": h.market_value
        }
        for h in holdings_response.holdings
    ]
    
    # Calculate statistics
    stats = calculate_portfolio_statistics(
        enrich_holdings_with_fundamentals(db_path, holdings_dict)
    )
    
    return PortfolioSummaryResponse(
        portfolio_id=portfolio_id,
        name=holdings_response.name,
        num_holdings=stats.num_holdings,
        total_market_value=stats.total_market_value,
        weighted_avg_pe=stats.weighted_avg_pe,
        weighted_avg_dividend_yield=stats.weighted_avg_dividend_yield,
        top_10_concentration=stats.top_10_weight,
        num_sectors=stats.num_sectors,
        sector_breakdown=stats.sector_concentration
    )


@app.post("/api/portfolio/{portfolio_id}/optimize", response_model=OptimizationResponse)
def portfolio_optimize(portfolio_id: str, request: OptimizationRequest) -> OptimizationResponse:
    """Run portfolio optimization with policy constraints."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch holdings
    holdings_response = portfolio_holdings(portfolio_id)
    current_holdings = {h.ticker: h.weight or 0.0 for h in holdings_response.holdings if h.weight is not None}
    
    # Fetch constraints
    constraints_response = portfolio_constraints(portfolio_id, active_only=True)
    policy_constraints = [
        PolicyConstraint(
            constraint_type=c.type,
            dimension=c.dimension or "*",
            min_value=c.min_value,
            max_value=c.max_value
        )
        for c in constraints_response.constraints
    ]
    
    # Build expected returns and covariance matrix from historical data
    ticker_list = list(current_holdings.keys())
    
    # Calculate expected returns using historical method
    expected_returns = calculate_expected_returns(
        db_path,
        ticker_list,
        method="historical",
        lookback_days=252,
    )
    
    # Fallback to placeholder if no historical data available
    if not expected_returns:
        expected_returns = {ticker: 0.08 for ticker in ticker_list}  # Default: 8% return
    
    # Ensure all tickers have expected returns
    for ticker in ticker_list:
        if ticker not in expected_returns:
            expected_returns[ticker] = 0.08  # Default: 8% return
    
    # Calculate covariance matrix from historical prices
    import numpy as np
    try:
        covariance_matrix, valid_tickers = calculate_covariance_matrix(
            db_path,
            ticker_list,
            lookback_days=252,
        )
        
        # If some tickers were excluded, need to align
        if len(valid_tickers) != len(ticker_list):
            if len(valid_tickers) < 2:
                raise OptimizationFailedError(
                    f"Optimization requires at least 2 holdings with sufficient historical data. Only {len(valid_tickers)} ticker(s) have enough data."
                )
            # Reorder ticker_list to match valid_tickers
            ticker_list = valid_tickers
            # Filter current_holdings and expected_returns
            current_holdings = {t: current_holdings.get(t, 0.0) for t in ticker_list}
            expected_returns = {t: expected_returns.get(t, 0.08) for t in ticker_list}
            
            # Renormalize weights after filtering
            total_weight = sum(current_holdings.values())
            if total_weight > 0:
                current_holdings = {t: w / total_weight for t, w in current_holdings.items()}
            elif len(current_holdings) > 0:
                # If all weights were zero, assign equal weights
                equal_weight = 1.0 / len(current_holdings)
                current_holdings = {t: equal_weight for t in ticker_list}
    except Exception as e:
        # Fallback to placeholder if calculation fails
        LOGGER.warning(f"Failed to calculate covariance matrix: {e}, using placeholder")
        n = len(ticker_list)
        if n < 2:
            raise OptimizationFailedError(
                f"Optimization requires at least 2 holdings. Current portfolio has {n}."
            )
        # Create a reasonable placeholder covariance matrix
        # Use correlation of 0.3 between assets as default
        base_var = 0.04  # 4% variance per asset
        covariance_matrix = np.eye(n) * base_var
        correlation = 0.3
        for i in range(n):
            for j in range(i + 1, n):
                cov_value = correlation * base_var
                covariance_matrix[i, j] = cov_value
                covariance_matrix[j, i] = cov_value
    
    # Validate inputs before optimization
    if len(ticker_list) < 2:
        raise OptimizationFailedError(
            f"Optimization requires at least 2 holdings. Current portfolio has {len(ticker_list)}."
        )
    
    # Ensure weights are normalized
    total_weight = sum(current_holdings.values())
    if total_weight > 1.01 or (total_weight > 0 and total_weight < 0.99):
        # Normalize weights if they don't sum to 1.0
        if total_weight > 0:
            current_holdings = {t: w / total_weight for t, w in current_holdings.items()}
        else:
            # If all weights are zero, assign equal weights
            equal_weight = 1.0 / len(ticker_list)
            current_holdings = {t: equal_weight for t in ticker_list}
    
    # Run optimization
    try:
        result = optimize_portfolio_sharpe(
            current_holdings=current_holdings,
            expected_returns=expected_returns,
            covariance_matrix=covariance_matrix,
            ticker_list=ticker_list,
            constraints=policy_constraints,
            turnover_limit=request.turnover_limit,
            objective=request.objective
        )
        
        # Convert trades to response format
        trades = [
            Trade(
                ticker=trade.get("ticker", ""),
                action=trade.get("action", "hold"),
                from_weight=trade.get("from_weight"),
                to_weight=trade.get("to_weight"),
                shares=trade.get("shares")
            )
            for trade in result.proposed_trades
        ]
        
        return OptimizationResponse(
            portfolio_id=portfolio_id,
            status=result.status,
            proposed_trades=trades,
            objective_value=result.objective_value,
            metrics_before=result.metrics_before,
            metrics_after=result.metrics_after,
            policy_flags=result.policy_flags or []
        )
    except (OptimizationFailedError, ValueError, Exception) as e:
        error_msg = str(e) if isinstance(e, Exception) else getattr(e, 'message', str(e))
        LOGGER.error(f"Optimization failed for portfolio {portfolio_id}: {error_msg}", exc_info=True)
        
        if isinstance(e, OptimizationFailedError):
            error_response = format_portfolio_error(e, include_technical=False)
        else:
            # Convert other exceptions to OptimizationFailedError for consistent response
            error_response = format_portfolio_error(
                OptimizationFailedError(f"Optimization solver failed: {error_msg}"),
                include_technical=False
            )
        
        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "title": error_response.get("title", "Optimization Failed"),
                "message": error_response["message"],
                "error_code": error_response["error_code"],
                "common_causes": error_response.get("common_causes", []),
                "solutions": error_response.get("solutions", error_response.get("suggestions", [])),
                "status": getattr(e, 'status', 'error')
            }
        )
    except Exception as e:
        error_msg = str(e)
        LOGGER.error(f"Optimization failed for portfolio {portfolio_id}: {error_msg}", exc_info=True)
        
        # Create OptimizationFailedError for consistent handling
        opt_error = OptimizationFailedError(
            f"Optimization failed: {error_msg}. Please check portfolio holdings and try again.",
            status="unknown_error"
        )
        error_response = format_portfolio_error(opt_error, include_technical=False)
        
        # Provide more helpful error messages
        if "infeasible" in error_msg.lower() or "constraint" in error_msg.lower():
            detail_msg = error_response.get("solutions", [])[0] if error_response.get("solutions") else "Try relaxing policy constraints or increasing turnover limit."
        elif "covariance" in error_msg.lower() or "matrix" in error_msg.lower():
            detail_msg = "Unable to calculate portfolio risk metrics. Some holdings may lack sufficient historical data."
        elif "solver" in error_msg.lower():
            detail_msg = f"Optimization solver failed. This may indicate an invalid problem formulation. Error: {error_msg}"
        else:
            detail_msg = error_response["message"]
        
        raise HTTPException(
            status_code=422,
            detail={
                "message": detail_msg,
                "error_code": error_response["error_code"],
                "suggestions": error_response["suggestions"]
            }
        )


@app.post("/api/portfolio/{portfolio_id}/attribution", response_model=AttributionResponse)
def portfolio_attribution(portfolio_id: str, request: AttributionRequest) -> AttributionResponse:
    """Run performance attribution analysis."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch holdings
    holdings_response = portfolio_holdings(portfolio_id)
    portfolio_weights = {h.ticker: h.weight or 0.0 for h in holdings_response.holdings if h.weight is not None}
    
    # Get sectors
    sectors = {h.ticker: h.sector or "Unknown" for h in holdings_response.holdings}
    
    # Placeholder returns (would need historical data integration)
    portfolio_returns = {ticker: 0.05 for ticker in portfolio_weights.keys()}
    benchmark_weights = {ticker: 1.0 / len(portfolio_weights) for ticker in portfolio_weights.keys()}
    benchmark_returns = {ticker: 0.04 for ticker in portfolio_weights.keys()}
    
    # Run attribution
    try:
        attribution = brinson_attribution(
            portfolio_weights=portfolio_weights,
            portfolio_returns=portfolio_returns,
            benchmark_weights=benchmark_weights,
            benchmark_returns=benchmark_returns,
            sectors=sectors
        )
        
        return AttributionResponse(
            portfolio_id=portfolio_id,
            start_date=request.start_date,
            end_date=request.end_date,
            total_active_return=attribution.total_active_return,
            allocation_effect=attribution.allocation_effect,
            selection_effect=attribution.selection_effect,
            interaction_effect=attribution.interaction_effect,
            top_contributors=attribution.top_contributors,
            top_detractors=attribution.top_detractors
        )
    except Exception as e:
        error_msg = str(e)
        LOGGER.error(f"Attribution failed for portfolio {portfolio_id}: {error_msg}", exc_info=True)
        
        # Provide more helpful error messages
        if "returns" in error_msg.lower() or "data" in error_msg.lower():
            detail = f"Unable to calculate attribution: insufficient return data for the specified period. Please check date range and ensure portfolio has holdings during this period."
        elif "weights" in error_msg.lower():
            detail = f"Invalid portfolio or benchmark weights. Please ensure weights sum to approximately 1.0. Error: {error_msg}"
        else:
            detail = f"Attribution calculation failed: {error_msg}. Please verify portfolio holdings and try again."
        
        raise HTTPException(status_code=500, detail=detail)


@app.post("/api/portfolio/{portfolio_id}/scenario", response_model=ScenarioResponse)
def portfolio_scenario(portfolio_id: str, request: ScenarioRequest) -> ScenarioResponse:
    """Run stress test scenario."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch holdings
    holdings_response = portfolio_holdings(portfolio_id)
    holdings = {h.ticker: h.weight or 0.0 for h in holdings_response.holdings if h.weight is not None}
    
    # Calculate real betas from historical data
    try:
        betas = calculate_betas_batch(
            db_path,
            list(holdings.keys()),
            benchmark="SPY",
            lookback_days=252,
        )
        # Fallback to default beta = 1.0 for tickers without historical data
        for ticker in holdings.keys():
            if ticker not in betas:
                betas[ticker] = 1.0
    except Exception as e:
        # Fallback to placeholder if calculation fails
        LOGGER.warning(f"Failed to calculate betas: {e}, using placeholder")
        betas = {ticker: 1.0 for ticker in holdings.keys()}


@app.delete("/api/portfolio/{portfolio_id}")
def delete_portfolio(portfolio_id: str) -> Dict[str, Any]:
    """Delete a portfolio and all its holdings."""
    settings = get_settings()
    db_path = settings.database_path  # Can be str or Path
    
    # Import delete function
    from .database import delete_portfolio as db_delete_portfolio
    
    try:
        deleted = db_delete_portfolio(db_path, portfolio_id)
        if deleted:
            LOGGER.info(f"Successfully deleted portfolio {portfolio_id}")
            return {"success": True, "message": f"Portfolio {portfolio_id} deleted successfully"}
        else:
            LOGGER.warning(f"Portfolio {portfolio_id} not found for deletion")
            error_response = format_portfolio_error(PortfolioNotFoundError(portfolio_id))
            raise HTTPException(
                status_code=404,
                detail=error_response["message"]
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown error"
        LOGGER.error(f"Failed to delete portfolio {portfolio_id}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete portfolio: {error_msg}")


@app.get("/api/portfolio/{portfolio_id}/export/pptx")
def portfolio_export_pptx(portfolio_id: str) -> StreamingResponse:
    """Export portfolio as PowerPoint presentation."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    try:
        settings = get_settings()
        db_path = settings.database_path
        
        # Build PowerPoint
        ppt_bytes = build_portfolio_powerpoint(
            database_path=Path(db_path),
            portfolio_id=portfolio_id,
            optimization_result=None,  # Optional - can be fetched if needed
            attribution_result=None,  # Optional - can be fetched if needed
            exposure_result=None,  # Optional - can be fetched if needed
            scenario_results=None,  # Optional - can be fetched if needed
        )
        
        # Return as streaming response
        filename = f"portfolio_{portfolio_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pptx"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Format": "pptx",
            "Content-Length": str(len(ppt_bytes)),
        }
        return StreamingResponse(
            BytesIO(ppt_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers=headers,
        )
    except ImportError as exc:
        logger.exception(f"Missing dependency for portfolio PPT export: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"PowerPoint export not available: {str(exc)}. Install python-pptx with: pip install python-pptx"
        ) from exc
    except ValueError as exc:
        logger.warning(f"Portfolio not found for PPT export: {exc}")
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        error_traceback = traceback.format_exc()
        error_type = type(exc).__name__
        error_msg = str(exc)
        logger.exception(f"Error generating portfolio PPT export for {portfolio_id}: {error_type}: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PowerPoint export: {error_type}: {error_msg}"
        ) from exc


@app.get("/api/portfolio/{portfolio_id}/export/pdf")
def portfolio_export_pdf(portfolio_id: str) -> StreamingResponse:
    """Export portfolio as PDF executive summary."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch all portfolio data
    holdings_response = portfolio_holdings(portfolio_id)
    summary_response = portfolio_summary(portfolio_id)
    exposure_response = portfolio_exposure(portfolio_id)
    
    # Convert to format expected by PDF builder
    holdings = [
        {
            "ticker": h.ticker,
            "weight": h.weight or 0.0,
            "shares": h.shares,
            "price": h.price,
            "roe": h.roe,
            "roic": h.roic,
            "sector": h.sector,
            "pe_ratio": h.pe_ratio,
            "dividend_yield": h.dividend_yield,
            "market_value": h.market_value,
            "roe": h.roe,
            "roic": h.roic,
        }
        for h in holdings_response.holdings
    ]
    
    summary = {
        "num_holdings": summary_response.num_holdings,
        "total_market_value": summary_response.total_market_value,
        "weighted_avg_pe": summary_response.weighted_avg_pe,
        "weighted_avg_dividend_yield": summary_response.weighted_avg_dividend_yield,
        "top_10_concentration": summary_response.top_10_concentration,
        "num_sectors": summary_response.num_sectors,
        "sector_breakdown": summary_response.sector_breakdown,
    }
    
    exposure = {
        "sector_exposure": exposure_response.sector_exposure,
        "factor_exposure": exposure_response.factor_exposure,
        "concentration_metrics": exposure_response.concentration_metrics,
    }
    
    # Build PDF
    pdf_bytes = build_portfolio_pdf(
        portfolio_id=portfolio_id,
        portfolio_name=holdings_response.name,
        holdings=holdings,
        summary=summary,
        exposure=exposure,
        attribution=None,  # Optional - can be fetched if needed
        optimization=None,  # Optional - can be fetched if needed
    )
    
    # Return as streaming response
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    filename = f"portfolio_{portfolio_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Export-Format": "pdf",
    }
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers=headers
    )


@app.get("/api/portfolio/{portfolio_id}/export/xlsx")
def portfolio_export_xlsx(portfolio_id: str) -> StreamingResponse:
    """Export portfolio as Excel workbook."""
    settings = get_settings()
    db_path = settings.database_path
    
    # Fetch all portfolio data
    holdings_response = portfolio_holdings(portfolio_id)
    summary_response = portfolio_summary(portfolio_id)
    exposure_response = portfolio_exposure(portfolio_id)
    
    # Convert to format expected by Excel builder
    holdings = [
        {
            "ticker": h.ticker,
            "weight": h.weight or 0.0,
            "shares": h.shares,
            "price": h.price,
            "sector": h.sector,
            "pe_ratio": h.pe_ratio,
            "dividend_yield": h.dividend_yield,
            "market_value": h.market_value,
            "roe": h.roe,
            "roic": h.roic,
        }
        for h in holdings_response.holdings
    ]
    
    summary = {
        "num_holdings": summary_response.num_holdings,
        "total_market_value": summary_response.total_market_value,
        "weighted_avg_pe": summary_response.weighted_avg_pe,
        "weighted_avg_dividend_yield": summary_response.weighted_avg_dividend_yield,
        "top_10_concentration": summary_response.top_10_concentration,
        "num_sectors": summary_response.num_sectors,
        "sector_breakdown": summary_response.sector_breakdown,
    }
    
    exposure = {
        "sector_exposure": exposure_response.sector_exposure,
        "factor_exposure": exposure_response.factor_exposure,
        "concentration_metrics": exposure_response.concentration_metrics,
    }
    
    # Build Excel
    excel_bytes = build_portfolio_excel(
        portfolio_id=portfolio_id,
        portfolio_name=holdings_response.name,
        holdings=holdings,
        summary=summary,
        exposure=exposure,
        attribution=None,  # Optional - can be fetched if needed
        optimization=None,  # Optional - can be fetched if needed
        scenarios=None,  # Optional - can be fetched if needed
    )
    
    # Return as streaming response
    buffer = BytesIO(excel_bytes)
    buffer.seek(0)
    filename = f"portfolio_{portfolio_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Export-Format": "xlsx",
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


# ============================================================================
# Advanced Portfolio Features API Endpoints
# ============================================================================

@app.post("/api/portfolio/{portfolio_id}/optimize/multi-period", response_model=Dict[str, Any])
def optimize_portfolio_multi_period_endpoint(
    portfolio_id: str,
    periods: int = Query(4, ge=1, le=12, description="Number of periods to optimize"),
    rebalance_frequency: str = Query("quarterly", pattern="^(quarterly|monthly|weekly)$", description="Rebalance frequency"),
    objective: str = Query("sharpe", pattern="^(sharpe|tracking_error|return)$", description="Optimization objective"),
) -> Dict[str, Any]:
    """Optimize portfolio over multiple periods with rebalancing."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_multi_period
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Multi-period optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=422, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Multi-period optimization failed: {e}", exc_info=True)
        error_response = format_portfolio_error(
            OptimizationFailedError(f"Multi-period optimization failed: {str(e)}"),
            include_technical=False
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/portfolio/{portfolio_id}/optimize/risk-parity", response_model=Dict[str, Any])
def optimize_portfolio_risk_parity_endpoint(
    portfolio_id: str,
    target_risk_contribution: Optional[float] = Query(None, ge=0.0, le=1.0, description="Target risk contribution per asset"),
) -> Dict[str, Any]:
    """Optimize portfolio using risk parity approach."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_risk_parity
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Risk parity optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=422, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Risk parity optimization failed: {e}", exc_info=True)
        error_response = format_portfolio_error(
            OptimizationFailedError(f"Risk parity optimization failed: {str(e)}"),
            include_technical=False
        )
        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/portfolio/{portfolio_id}/stress-test", response_model=Dict[str, Any])
def comprehensive_stress_test_endpoint(
    portfolio_id: str,
    scenarios: List[Dict[str, Any]] = Body(..., description="List of scenario definitions"),
) -> Dict[str, Any]:
    """Run comprehensive stress test with multiple scenarios."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement run_comprehensive_stress_test
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Comprehensive stress test not yet implemented",
                "error": "This feature is under development"
            }
        )
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Stress test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Stress test failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/factor-attribution", response_model=Dict[str, Any])
def factor_attribution_endpoint(
    portfolio_id: str,
    benchmark_id: str = Query("sp500", description="Benchmark identifier"),
    factors: Optional[List[str]] = Query(None, description="List of factors to analyze"),
) -> Dict[str, Any]:
    """Decompose portfolio returns into factor exposures."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement analyze_factor_attribution
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Factor attribution analysis not yet implemented",
                "error": "This feature is under development"
            }
        )
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Factor attribution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Factor attribution failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/monte-carlo", response_model=Dict[str, Any])
def monte_carlo_simulation_endpoint(
    portfolio_id: str,
    num_simulations: int = Query(10000, ge=1000, le=100000, description="Number of simulations"),
    time_horizon: int = Query(252, ge=10, le=1000, description="Time horizon in trading days"),
) -> Dict[str, Any]:
    """Run Monte Carlo simulation for portfolio returns."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        result = monte_carlo_portfolio_simulation(
            db_path,
            portfolio_id,
            num_simulations=num_simulations,
            time_horizon=time_horizon
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "mean_return": result.mean_return,
            "std_return": result.std_return,
            "percentile_5": result.percentile_5,
            "percentile_95": result.percentile_95,
            "var_95": result.var_95,
            "cvar_95": result.cvar_95,
            "simulations_count": len(result.simulations)
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Monte Carlo simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Monte Carlo simulation failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/backtest", response_model=Dict[str, Any])
def backtest_portfolio_endpoint(
    portfolio_id: str,
    start_date: str = Query(..., description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format: YYYY-MM-DD)"),
    rebalance_frequency: str = Query("quarterly", pattern="^(quarterly|monthly|weekly)$", description="Rebalance frequency"),
) -> Dict[str, Any]:
    """Backtest portfolio strategy over historical period."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement backtest_portfolio_strategy
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Portfolio backtesting not yet implemented",
                "error": "This feature is under development"
            }
        )
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Backtest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Backtest failed: {str(e)}"})


# ============================================================================
# Priority 1: Advanced Risk Management Endpoints
# ============================================================================

@app.get("/api/portfolio/{portfolio_id}/risk/cvar", response_model=Dict[str, Any])
def portfolio_cvar_endpoint(
    portfolio_id: str,
    confidence_level: float = Query(0.95, ge=0.90, le=0.99, description="Confidence level (e.g., 0.95 for 95%)"),
    lookback_days: int = Query(252, ge=20, le=1000, description="Lookback period in days"),
) -> Dict[str, Any]:
    """Calculate Conditional Value at Risk (CVaR) for portfolio."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        result = calculate_cvar(
            db_path,
            portfolio_id,
            confidence_level=confidence_level,
            lookback_days=lookback_days
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "cvar": result.cvar,
            "var": result.var,
            "confidence_level": result.confidence_level,
            "portfolio_value": result.portfolio_value,
            "expected_loss": result.expected_loss,
            "position_cvar": result.position_cvar
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"CVaR calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"CVaR calculation failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/optimize/cvar-constrained", response_model=Dict[str, Any])
def optimize_portfolio_cvar_constrained_endpoint(
    portfolio_id: str,
    max_cvar: float = Body(..., description="Maximum allowed CVaR (as decimal, e.g., -0.05 for -5%)"),
    confidence_level: float = Body(0.95, description="Confidence level for CVaR"),
    objective: str = Body("sharpe", pattern="^(sharpe|return|minimize_variance)$", description="Optimization objective"),
) -> Dict[str, Any]:
    """Optimize portfolio with CVaR constraint."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        result = optimize_portfolio_cvar_constrained(
            db_path,
            portfolio_id,
            max_cvar=max_cvar,
            confidence_level=confidence_level,
            objective=objective,
            constraints=None  # Can be extended to accept constraints
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "holdings": result.holdings,
            "expected_return": result.expected_return,
            "portfolio_variance": result.portfolio_variance,
            "sharpe_ratio": result.sharpe_ratio,
            "cvar": result.cvar,
            "var": result.var,
            "optimization_status": result.optimization_status
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=400, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"CVaR-constrained optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Optimization failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/scenario/custom", response_model=Dict[str, Any])
def custom_scenario_endpoint(
    portfolio_id: str,
    shocks: Dict[str, Any] = Body(..., description="Custom scenario shocks definition"),
) -> Dict[str, Any]:
    """Create custom stress test scenario with user-defined shocks."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement create_custom_scenario
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Custom scenario not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Custom scenario failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/scenario/geopolitical", response_model=Dict[str, Any])
def geopolitical_scenario_endpoint(
    portfolio_id: str,
    event_type: str = Body(..., pattern="^(trade_war|sanctions|conflict|pandemic)$", description="Type of geopolitical event"),
    severity: float = Body(0.5, ge=0.0, le=1.0, description="Severity level (0.0 to 1.0)"),
) -> Dict[str, Any]:
    """Run geopolitical stress test scenario."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement run_geopolitical_scenario
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Geopolitical scenario not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Geopolitical scenario failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/scenario/sector-shock", response_model=Dict[str, Any])
def sector_shock_scenario_endpoint(
    portfolio_id: str,
    sector: str = Body(..., description="Sector name (e.g., 'Technology', 'Financials')"),
    shock_pct: float = Body(..., description="Shock percentage (e.g., -0.15 for 15% decline)"),
) -> Dict[str, Any]:
    """Run sector-specific shock scenario."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement run_sector_specific_shock
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Sector shock scenario not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Sector shock scenario failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/scenario/rate-structure", response_model=Dict[str, Any])
def rate_structure_scenario_endpoint(
    portfolio_id: str,
    short_rate_change: float = Body(..., description="Short-term rate change in basis points"),
    long_rate_change: float = Body(..., description="Long-term rate change in basis points"),
    curve_steepening: bool = Body(False, description="Whether yield curve steepens"),
) -> Dict[str, Any]:
    """Run interest rate term structure scenario."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement run_rate_term_structure_scenario
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Rate term structure scenario not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Rate structure scenario failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/scenario/fx-exposure", response_model=Dict[str, Any])
def fx_exposure_scenario_endpoint(
    portfolio_id: str,
    currency_shocks: Dict[str, float] = Body(..., description="Currency shocks (e.g., {'EUR': -0.10, 'GBP': -0.15})"),
) -> Dict[str, Any]:
    """Run FX exposure stress test."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement run_fx_exposure_stress_test
        raise HTTPException(
            status_code=501,
            detail={
                "message": "FX exposure stress test not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"FX exposure scenario failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario failed: {str(e)}"})


# ============================================================================
# Priority 2: Alternative Optimization Objectives Endpoints
# ============================================================================

@app.get("/api/portfolio/{portfolio_id}/exposure/esg", response_model=Dict[str, Any])
def portfolio_esg_exposure_endpoint(
    portfolio_id: str,
) -> Dict[str, Any]:
    """Analyze portfolio ESG exposure."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement analyze_esg_exposure
        raise HTTPException(
            status_code=501,
            detail={
                "message": "ESG exposure analysis not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"ESG exposure analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Analysis failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/optimize/esg-constrained", response_model=Dict[str, Any])
def optimize_portfolio_esg_constrained_endpoint(
    portfolio_id: str,
    min_esg_score: float = Body(6.0, ge=0.0, le=10.0, description="Minimum portfolio ESG score"),
    objective: str = Body("sharpe", pattern="^(sharpe|return|minimize_variance)$", description="Optimization objective"),
) -> Dict[str, Any]:
    """Optimize portfolio with ESG constraints."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_esg_constrained
        raise HTTPException(
            status_code=501,
            detail={
                "message": "ESG-constrained optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=400, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"ESG-constrained optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Optimization failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/optimize/tax-aware", response_model=Dict[str, Any])
def optimize_portfolio_tax_aware_endpoint(
    portfolio_id: str,
    tax_rate_short: float = Body(0.37, ge=0.0, le=1.0, description="Short-term capital gains tax rate"),
    tax_rate_long: float = Body(0.20, ge=0.0, le=1.0, description="Long-term capital gains tax rate"),
    harvest_losses: bool = Body(True, description="Identify tax-loss harvesting opportunities"),
    objective: str = Body("sharpe", pattern="^(sharpe|return|minimize_variance)$", description="Optimization objective"),
) -> Dict[str, Any]:
    """Optimize portfolio with tax considerations."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_tax_aware
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Tax-aware optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=400, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Tax-aware optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Optimization failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/tax-analysis", response_model=Dict[str, Any])
def portfolio_tax_analysis_endpoint(
    portfolio_id: str,
    tax_rate_short: float = Query(0.37, ge=0.0, le=1.0, description="Short-term capital gains tax rate"),
    tax_rate_long: float = Query(0.20, ge=0.0, le=1.0, description="Long-term capital gains tax rate"),
) -> Dict[str, Any]:
    """Calculate tax-adjusted returns for portfolio holdings."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # Get holdings with estimated holding periods
        holdings = get_portfolio_holdings(db_path, portfolio_id)
        holding_periods = {h['ticker']: 180 for h in holdings}  # Assume 6 months average
        
        # TODO: Implement calculate_tax_adjusted_returns
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Tax-adjusted returns calculation not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Tax analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Analysis failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/optimize/tracking-error", response_model=Dict[str, Any])
def optimize_portfolio_tracking_error_endpoint(
    portfolio_id: str,
    benchmark_id: str = Body("sp500", description="Benchmark identifier"),
    max_tracking_error: float = Body(0.025, ge=0.0, le=0.5, description="Maximum allowed tracking error"),
    objective: str = Body("minimize_tracking_error", pattern="^(minimize_tracking_error|sharpe|return)$", description="Optimization objective"),
) -> Dict[str, Any]:
    """Optimize portfolio to minimize tracking error."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_tracking_error
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Tracking error optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=400, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Tracking error optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Optimization failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/optimize/diversification", response_model=Dict[str, Any])
def optimize_portfolio_diversification_endpoint(
    portfolio_id: str,
) -> Dict[str, Any]:
    """Optimize portfolio to maximize diversification ratio."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement optimize_portfolio_diversification
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Diversification optimization not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except OptimizationFailedError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=400, detail=error_response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Diversification optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Optimization failed: {str(e)}"})


# ============================================================================
# Priority 4: Order Management Integration Endpoints
# ============================================================================

@app.post("/api/portfolio/{portfolio_id}/trades/generate", response_model=Dict[str, Any])
def generate_trade_list_endpoint(
    portfolio_id: str,
    optimization_result: Dict[str, Any] = Body(..., description="Optimization result from previous optimization"),
) -> Dict[str, Any]:
    """Generate trade list from optimization results."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # Convert optimization result to OptimizationResult object
        from .portfolio import OptimizationResult
        opt_result = OptimizationResult(
            holdings=optimization_result.get('holdings', {}),
            expected_return=optimization_result.get('expected_return', 0.0),
            portfolio_variance=optimization_result.get('portfolio_variance', 0.0),
            sharpe_ratio=optimization_result.get('sharpe_ratio', 0.0),
            optimization_status=optimization_result.get('optimization_status', 'optimal')
        )
        
        trade_list = generate_trade_list(
            db_path,
            portfolio_id,
            opt_result
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "trades": [
                {
                    "ticker": t.ticker,
                    "action": t.action,
                    "quantity": t.quantity,
                    "current_weight": t.current_weight,
                    "target_weight": t.target_weight,
                    "price": t.price,
                    "trade_value": t.trade_value,
                    "estimated_cost": t.estimated_cost
                }
                for t in trade_list.trades
            ],
            "total_trade_value": trade_list.total_trade_value,
            "total_estimated_cost": trade_list.total_estimated_cost,
            "generated_at": trade_list.generated_at.isoformat()
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Trade list generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Trade list generation failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/trades/export/{format}")
def export_trade_list_endpoint(
    portfolio_id: str,
    format: str,
    optimization_result: Dict[str, Any] = Body(..., description="Optimization result"),
) -> StreamingResponse:
    """Export trade list in specified format."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        from .portfolio import OptimizationResult
        opt_result = OptimizationResult(
            holdings=optimization_result.get('holdings', {}),
            expected_return=optimization_result.get('expected_return', 0.0),
            portfolio_variance=optimization_result.get('portfolio_variance', 0.0),
            sharpe_ratio=optimization_result.get('sharpe_ratio', 0.0),
            optimization_status=optimization_result.get('optimization_status', 'optimal')
        )
        
        trade_list = generate_trade_list(db_path, portfolio_id, opt_result)
        trade_bytes = export_trade_list(trade_list, format=format)
        
        content_type_map = {
            "csv": "text/csv",
            "fix": "text/plain",
            "json": "application/json"
        }
        
        return StreamingResponse(
            BytesIO(trade_bytes),
            media_type=content_type_map.get(format, "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="trades_{portfolio_id}.{format}"'
            }
        )
    except Exception as e:
        LOGGER.error(f"Trade list export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Export failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/trades/analyze", response_model=Dict[str, Any])
def analyze_trade_impact_endpoint(
    portfolio_id: str,
    proposed_trades: List[Dict[str, Any]] = Body(..., description="List of proposed trades"),
) -> Dict[str, Any]:
    """Analyze impact of proposed trades on portfolio."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        from .portfolio_trades import Trade
        trades = [
            Trade(
                ticker=t['ticker'],
                action=t['action'],
                quantity=t.get('quantity', 0),
                current_weight=t.get('current_weight', 0),
                target_weight=t.get('target_weight', 0),
                current_shares=t.get('current_shares', 0),
                target_shares=t.get('target_shares', 0),
                price=t.get('price'),
            )
            for t in proposed_trades
        ]
        
        result = analyze_trade_impact(db_path, portfolio_id, trades)
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "before_metrics": result.before_metrics,
            "after_metrics": result.after_metrics,
            "impact_analysis": result.impact_analysis,
            "policy_violations": result.policy_violations,
            "risk_changes": result.risk_changes
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Trade impact analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Analysis failed: {str(e)}"})


@app.post("/api/portfolio/{portfolio_id}/trades/simulate", response_model=Dict[str, Any])
def simulate_trade_execution_endpoint(
    portfolio_id: str,
    trades: List[Dict[str, Any]] = Body(..., description="List of trades to simulate"),
) -> Dict[str, Any]:
    """Simulate portfolio state after trade execution."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        from .portfolio_trades import Trade
        trade_objects = [
            Trade(
                ticker=t['ticker'],
                action=t['action'],
                quantity=t.get('quantity', 0),
                current_weight=t.get('current_weight', 0),
                target_weight=t.get('target_weight', 0),
                current_shares=t.get('current_shares', 0),
                target_shares=t.get('target_shares', 0),
            )
            for t in trades
        ]
        
        result = simulate_trade_execution(db_path, portfolio_id, trade_objects)
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "holdings": result.holdings,
            "metrics": result.metrics,
            "timestamp": result.timestamp.isoformat()
        }
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Trade simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Simulation failed: {str(e)}"})


# ============================================================================
# Priority 5: Enhanced Reporting & Customization Endpoints
# ============================================================================

@app.post("/api/portfolio/{portfolio_id}/reports/custom")
def create_custom_report_endpoint(
    portfolio_id: str,
    report_config: Dict[str, Any] = Body(..., description="Report configuration"),
) -> StreamingResponse:
    """Generate custom report from configuration."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        from .portfolio_report_builder import ReportConfig, ReportSection  # type: ignore
        sections = [
            ReportSection(**s) for s in report_config.get('sections', [])
        ]
        config = ReportConfig(
            portfolio_id=portfolio_id,
            report_name=report_config.get('report_name', 'Custom Report'),
            sections=sections,
            format=report_config.get('format', 'pdf'),
            branding=report_config.get('branding'),
            include_charts=report_config.get('include_charts', True),
            chart_types=report_config.get('chart_types')
        )
        
        # TODO: Implement create_custom_report
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Custom report generation not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Custom report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Report generation failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/charts/export")
def export_interactive_charts_endpoint(
    portfolio_id: str,
    chart_types: Optional[List[str]] = Query(None, description="List of chart types to export"),
) -> Response:
    """Export portfolio charts as interactive HTML."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement export_interactive_charts
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Interactive chart export not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Chart export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Chart export failed: {str(e)}"})


# ============================================================================
# Template Management API Endpoints
# ============================================================================

@app.post("/api/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    user_id: Optional[str] = Form("default")
) -> Dict[str, Any]:
    """Upload a report template."""
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        # Determine file type
        file_ext = (Path(file.filename).suffix or "").lower()
        file_type = file_ext.lstrip(".")
        
        # Process template
        template = processor.upload_template(
            user_id=user_id or "default",
            name=name or file.filename or "Untitled Template",
            file_path=tmp_path,
            file_type=file_type
        )
        
        # Clean up temp file
        try:
            tmp_path.unlink()
        except:
            pass
        
        return {
            "success": True,
            "template": template.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Template upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template upload failed: {str(e)}"})


@app.get("/api/templates")
def list_templates(
    user_id: Optional[str] = Query("default", description="User ID to filter templates")
) -> Dict[str, Any]:
    """List all templates for a user."""
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        templates = processor.list_templates(user_id or "default")
        return {
            "success": True,
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }
    except Exception as e:
        LOGGER.error(f"Template listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template listing failed: {str(e)}"})


@app.post("/api/templates/{template_id}/generate")
async def generate_from_template(
    template_id: str,
    ticker: str = Body(..., embed=True),
    user_id: Optional[str] = Body("default", embed=True)
) -> Dict[str, Any]:
    """Generate a report from a template with new data."""
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        
        # Create output file
        import tempfile
        output_path = Path(tempfile.mktemp(suffix=".pptx"))  # Default to PPTX
        
        render_result = processor.generate_from_template(
            template_id=template_id,
            ticker=ticker,
            output_path=output_path,
            context={
                "user_id": user_id or "default",
            }
        )
        
        if not render_result.success:
            raise HTTPException(status_code=500, detail={"message": "Failed to generate report from template"})
        
        # Return file
        headers = {}
        if render_result.job_id:
            headers["X-Template-Render-Job"] = render_result.job_id
        if render_result.warnings:
            headers["X-Template-Warnings"] = "; ".join(render_result.warnings)
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"report_{ticker}.pptx",
            headers=headers
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Template generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template generation failed: {str(e)}"})


@app.get("/api/reports/templates")
def list_report_templates_endpoint() -> List[Dict[str, Any]]:
    """List all available report templates (legacy endpoint)."""
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        templates = processor.list_templates("default")
        return [t.to_dict() for t in templates]
    except Exception as e:
        LOGGER.error(f"Template list failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template list failed: {str(e)}"})


@app.get("/api/templates/{template_id}/renders")
def list_template_renders(
    template_id: str,
    limit: int = Query(20, ge=1, le=200)
) -> Dict[str, Any]:
    """List render history for a template."""
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        jobs = processor.list_render_jobs(template_id, limit=limit)
        return {
            "success": True,
            "template_id": template_id,
            "jobs": jobs,
            "count": len(jobs),
        }
    except Exception as e:
        LOGGER.error(f"Template render history failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template render history failed: {str(e)}"})


# ============================================================================
# Priority 6: Data Integration & External Services Endpoints
# ============================================================================

@app.get("/api/portfolio/{portfolio_id}/enrichment")
def enrich_portfolio_endpoint(
    portfolio_id: str,
    data_sources: Optional[List[str]] = Query(None, description="List of data sources to use"),
) -> Dict[str, Any]:
    """Enrich portfolio with alternative data sources."""
    settings = get_settings()
    db_path = settings.database_path
    
    try:
        # TODO: Implement enrich_with_alternative_data
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Portfolio enrichment not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except PortfolioNotFoundError as e:
        error_response = format_portfolio_error(e, include_technical=False)
        raise HTTPException(status_code=404, detail=error_response)
    except Exception as e:
        LOGGER.error(f"Portfolio enrichment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Enrichment failed: {str(e)}"})


@app.get("/api/portfolio/{portfolio_id}/sentiment/{ticker}")
def get_sentiment_score_endpoint(
    portfolio_id: str,
    ticker: str,
    source: str = Query("news", pattern="^(news|analyst|social)$", description="Sentiment source"),
) -> Dict[str, Any]:
    """Get sentiment score for ticker."""
    try:
        # TODO: Implement get_sentiment_score
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Sentiment score retrieval not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Sentiment score fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Sentiment fetch failed: {str(e)}"})


# ============================================================================
# Custom KPIs API Endpoints
# ============================================================================

class CreateKPIRequest(BaseModel):
    """Request to create a custom KPI."""
    name: str
    formula: str
    description: Optional[str] = None
    frequency: Optional[str] = None
    unit: Optional[str] = None
    inputs: Optional[List[str]] = None
    source_tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "default"
    parameter_schema: Optional[Dict[str, Any]] = None
    data_preferences_id: Optional[str] = None
    group: Optional[str] = None


class KPICalculationRequest(BaseModel):
    """Request to calculate a custom KPI."""
    ticker: str
    period: Optional[str] = None
    fiscal_year: Optional[int] = None
    user_id: Optional[str] = "default"
    data_preferences_id: Optional[str] = None
    source_order: Optional[List[str]] = None


class CreateDataPreferenceRequest(BaseModel):
    """Request payload for creating data source preferences."""

    name: str
    source_order: List[str]
    fallback_rules: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "default"


class UpdateDataPreferenceRequest(BaseModel):
    """Request payload for updating data source preferences."""

    name: Optional[str] = None
    source_order: Optional[List[str]] = None
    fallback_rules: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CreateAnalysisTemplateRequest(BaseModel):
    """Request payload for creating analysis templates."""

    name: str
    kpi_ids: List[str]
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    data_preferences_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "default"


class UpdateAnalysisTemplateRequest(BaseModel):
    """Request payload for updating analysis templates."""

    name: Optional[str] = None
    kpi_ids: Optional[List[str]] = None
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    data_preferences_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class RenderAnalysisTemplateRequest(BaseModel):
    """Request payload for rendering templates."""

    tickers: List[str]
    parameters: Optional[Dict[str, Any]] = None
    data_preferences_id: Optional[str] = None
    source_order: Optional[List[str]] = None
    user_id: Optional[str] = "default"


class CreateProfileRequest(BaseModel):
    """Request payload for creating analyst profiles."""

    name: str
    kpi_library: Optional[List[str]] = None
    template_ids: Optional[List[str]] = None
    data_preferences_id: Optional[str] = None
    output_preferences: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "default"


class UpdateProfileRequest(BaseModel):
    """Request payload for updating analyst profiles."""

    name: Optional[str] = None
    kpi_library: Optional[List[str]] = None
    template_ids: Optional[List[str]] = None
    data_preferences_id: Optional[str] = None
    output_preferences: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class SaveSessionRequest(BaseModel):
    """Request payload for saving sessions."""

    profile_id: str
    workspace_state: Dict[str, Any]
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = "default"


class UpdateSessionRequest(BaseModel):
    """Request payload for updating sessions."""

    workspace_state: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


@app.post("/api/kpis/custom")
def create_custom_kpi(request: CreateKPIRequest) -> Dict[str, Any]:
    """Create a new custom KPI."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        kpi = calculator.create_kpi(
            user_id=request.user_id or "default",
            name=request.name,
            formula=request.formula,
            description=request.description,
            metadata=request.metadata,
            frequency=request.frequency,
            unit=request.unit,
            inputs=request.inputs,
            source_tags=request.source_tags,
            parameter_schema=request.parameter_schema,
            data_preferences_id=request.data_preferences_id,
            group=request.group,
        )
        return {
            "success": True,
            "kpi": kpi.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Custom KPI creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI creation failed: {str(e)}"})


@app.get("/api/kpis/custom")
def list_custom_kpis(
    user_id: Optional[str] = Query("default", description="User ID to filter KPIs")
) -> Dict[str, Any]:
    """List all custom KPIs for a user."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        kpis = calculator.list_kpis(user_id or "default")
        return {
            "success": True,
            "kpis": [kpi.to_dict() for kpi in kpis],
            "count": len(kpis)
        }
    except Exception as e:
        LOGGER.error(f"Custom KPI listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI listing failed: {str(e)}"})


@app.post("/api/kpis/custom/{kpi_id}/calculate")
def calculate_custom_kpi(
    kpi_id: str,
    request: KPICalculationRequest
) -> Dict[str, Any]:
    """Calculate a custom KPI for a specific ticker and period."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        source_preferences = list(request.source_order or [])

        if request.data_preferences_id:
            pref_manager = DataSourcePreferencesManager(settings.database_path)
            preference = pref_manager.get(request.data_preferences_id)
            if preference is None:
                LOGGER.warning("Data source preference %s not found", request.data_preferences_id)
            elif request.user_id and preference.user_id != request.user_id:
                LOGGER.warning(
                    "User %s attempted to access data preference %s owned by %s",
                    request.user_id,
                    request.data_preferences_id,
                    preference.user_id,
                )
            elif not source_preferences:
                source_preferences = preference.source_order

        result = calculator.calculate_kpi(
            kpi_id=kpi_id,
            ticker=request.ticker,
            period=request.period,
            fiscal_year=request.fiscal_year,
            source_preferences=source_preferences or None,
        )
        return {
            "success": result.error is None,
            "result": result.to_dict()
        }
    except Exception as e:
        LOGGER.error(f"Custom KPI calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI calculation failed: {str(e)}"})


@app.delete("/api/kpis/custom/{kpi_id}")
def delete_custom_kpi(
    kpi_id: str,
    user_id: Optional[str] = Query("default", description="User ID")
) -> Dict[str, Any]:
    """Delete a custom KPI."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        deleted = calculator.delete_kpi(kpi_id, user_id or "default")
        if not deleted:
            raise HTTPException(status_code=404, detail={"message": f"KPI {kpi_id} not found"})
        return {
            "success": True,
            "message": f"KPI {kpi_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Custom KPI deletion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI deletion failed: {str(e)}"})


@app.get("/api/kpis/custom/{kpi_id}/versions")
def get_custom_kpi_versions(
    kpi_id: str,
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """Get version history for a custom KPI."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        versions = calculator.list_kpi_versions(kpi_id, limit=limit)
        return {
            "success": True,
            "kpi_id": kpi_id,
            "versions": versions,
            "count": len(versions),
        }
    except Exception as e:
        LOGGER.error(f"KPI version retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI version retrieval failed: {str(e)}"})


@app.get("/api/kpis/custom/{kpi_id}/usage")
def get_custom_kpi_usage(
    kpi_id: str,
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """Get recent usage records for a custom KPI."""
    try:
        settings = get_settings()
        calculator = CustomKPICalculator(settings.database_path)
        usage = calculator.get_kpi_usage(kpi_id, limit=limit)
        return {
            "success": True,
            "kpi_id": kpi_id,
            "usage": usage,
            "count": len(usage),
        }
    except Exception as e:
        LOGGER.error(f"KPI usage retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"KPI usage retrieval failed: {str(e)}"})


# ============================================================================
# Analyst Workspace API Endpoints
# ============================================================================


@app.post("/api/analytics/data-preferences")
def create_data_preference(request: CreateDataPreferenceRequest) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        preference = processor.create_data_preferences(
            user_id=request.user_id or "default",
            name=request.name,
            source_order=request.source_order,
            fallback_rules=request.fallback_rules,
            description=request.description,
            metadata=request.metadata,
        )
        return {"success": True, "preference": preference}
    except Exception as exc:
        LOGGER.error("Data preference creation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Data preference creation failed: {str(exc)}"})


@app.put("/api/analytics/data-preferences/{preference_id}")
def update_data_preference(
    preference_id: str,
    request: UpdateDataPreferenceRequest,
) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        updated = processor.update_data_preferences(
            preference_id,
            name=request.name,
            source_order=request.source_order,
            fallback_rules=request.fallback_rules,
            description=request.description,
            metadata=request.metadata,
        )
        if not updated:
            raise HTTPException(status_code=404, detail={"message": f"Preference {preference_id} not found"})
        return {"success": True, "preference": updated}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Data preference update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Data preference update failed: {str(exc)}"})


@app.get("/api/analytics/data-preferences")
def list_data_preferences(user_id: str = Query("default")) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        preferences = processor.list_data_preferences(user_id or "default")
        return {"success": True, "preferences": preferences, "count": len(preferences)}
    except Exception as exc:
        LOGGER.error("Listing data preferences failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Listing data preferences failed: {str(exc)}"})


@app.get("/api/analytics/data-preferences/{preference_id}")
def get_data_preference(preference_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        preference = processor.get_data_preference(preference_id)
        if not preference:
            raise HTTPException(status_code=404, detail={"message": f"Preference {preference_id} not found"})
        return {"success": True, "preference": preference}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Fetching data preference failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Fetching data preference failed: {str(exc)}"})


@app.post("/api/analytics/templates")
def create_analysis_template(request: CreateAnalysisTemplateRequest) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        template = processor.create_analysis_template(
            user_id=request.user_id or "default",
            name=request.name,
            kpi_ids=request.kpi_ids,
            description=request.description,
            layout_config=request.layout_config,
            parameter_schema=request.parameter_schema,
            data_preferences_id=request.data_preferences_id,
            metadata=request.metadata,
            created_by=request.user_id or "system",
        )
        return {"success": True, "template": template}
    except Exception as exc:
        LOGGER.error("Analysis template creation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template creation failed: {str(exc)}"})


@app.put("/api/analytics/templates/{template_id}")
def update_analysis_template(
    template_id: str,
    request: UpdateAnalysisTemplateRequest,
) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        updated = processor.update_analysis_template(
            template_id,
            name=request.name,
            description=request.description,
            kpi_ids=request.kpi_ids,
            layout_config=request.layout_config,
            parameter_schema=request.parameter_schema,
            data_preferences_id=request.data_preferences_id,
            metadata=request.metadata,
            updated_by=request.user_id or "system",
        )
        if not updated:
            raise HTTPException(status_code=404, detail={"message": f"Template {template_id} not found"})
        return {"success": True, "template": updated}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Analysis template update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template update failed: {str(exc)}"})


@app.get("/api/analytics/templates")
def list_analysis_templates(user_id: str = Query("default")) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        templates = processor.list_analysis_templates(user_id or "default")
        return {"success": True, "templates": templates, "count": len(templates)}
    except Exception as exc:
        LOGGER.error("Template listing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template listing failed: {str(exc)}"})


@app.get("/api/analytics/templates/{template_id}")
def get_analysis_template_endpoint(template_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        template = processor.get_analysis_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail={"message": f"Template {template_id} not found"})
        return {"success": True, "template": template}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Template fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template fetch failed: {str(exc)}"})


@app.delete("/api/analytics/templates/{template_id}")
def delete_analysis_template(template_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        deleted = processor.delete_analysis_template(template_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"message": f"Template {template_id} not found"})
        return {"success": True, "message": f"Template {template_id} deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Template deletion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template deletion failed: {str(exc)}"})


@app.get("/api/analytics/templates/{template_id}/versions")
def list_analysis_template_versions(template_id: str, limit: int = Query(20, ge=1, le=100)) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        history = processor.list_analysis_template_versions(template_id, limit=limit)
        return {"success": True, "template_id": template_id, "versions": history, "count": len(history)}
    except Exception as exc:
        LOGGER.error("Template version listing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template version listing failed: {str(exc)}"})


@app.post("/api/analytics/templates/{template_id}/render")
def render_analysis_template(
    template_id: str,
    request: RenderAnalysisTemplateRequest,
) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        payload = processor.render_analysis_template(
            template_id=template_id,
            tickers=request.tickers,
            parameters=request.parameters,
            data_preferences_id=request.data_preferences_id,
            source_order=request.source_order,
            user_id=request.user_id or "default",
        )
        return {"success": True, "render": payload}
    except Exception as exc:
        LOGGER.error("Template render failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Template render failed: {str(exc)}"})


@app.post("/api/analytics/profiles")
def create_profile(request: CreateProfileRequest) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        profile = processor.create_profile(
            user_id=request.user_id or "default",
            name=request.name,
            kpi_library=request.kpi_library,
            template_ids=request.template_ids,
            data_preferences_id=request.data_preferences_id,
            output_preferences=request.output_preferences,
            description=request.description,
            metadata=request.metadata,
        )
        return {"success": True, "profile": profile}
    except Exception as exc:
        LOGGER.error("Profile creation failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Profile creation failed: {str(exc)}"})


@app.put("/api/analytics/profiles/{profile_id}")
def update_profile(
    profile_id: str,
    request: UpdateProfileRequest,
) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        profile = processor.update_profile(
            profile_id,
            name=request.name,
            description=request.description,
            kpi_library=request.kpi_library,
            template_ids=request.template_ids,
            data_preferences_id=request.data_preferences_id,
            output_preferences=request.output_preferences,
            metadata=request.metadata,
        )
        if not profile:
            raise HTTPException(status_code=404, detail={"message": f"Profile {profile_id} not found"})
        return {"success": True, "profile": profile}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Profile update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Profile update failed: {str(exc)}"})


@app.get("/api/analytics/profiles")
def list_profiles(user_id: str = Query("default")) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        profiles = processor.list_profiles(user_id or "default")
        return {"success": True, "profiles": profiles, "count": len(profiles)}
    except Exception as exc:
        LOGGER.error("Profile listing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Profile listing failed: {str(exc)}"})


@app.get("/api/analytics/profiles/{profile_id}")
def get_profile(profile_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        profile = processor.get_profile(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail={"message": f"Profile {profile_id} not found"})
        return {"success": True, "profile": profile}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Profile retrieval failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Profile retrieval failed: {str(exc)}"})


@app.delete("/api/analytics/profiles/{profile_id}")
def delete_profile(profile_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        deleted = processor.delete_profile(profile_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"message": f"Profile {profile_id} not found"})
        return {"success": True, "message": f"Profile {profile_id} deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Profile deletion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Profile deletion failed: {str(exc)}"})


@app.post("/api/analytics/sessions")
def save_session(request: SaveSessionRequest) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        session = processor.save_session(
            profile_id=request.profile_id,
            user_id=request.user_id or "default",
            workspace_state=request.workspace_state,
            name=request.name,
            metadata=request.metadata,
            expires_at=request.expires_at,
        )
        return {"success": True, "session": session}
    except Exception as exc:
        LOGGER.error("Session save failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Session save failed: {str(exc)}"})


@app.put("/api/analytics/sessions/{session_id}")
def update_session(session_id: str, request: UpdateSessionRequest) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        session = processor.update_session(
            session_id,
            workspace_state=request.workspace_state,
            name=request.name,
            metadata=request.metadata,
            expires_at=request.expires_at,
        )
        if not session:
            raise HTTPException(status_code=404, detail={"message": f"Session {session_id} not found"})
        return {"success": True, "session": session}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Session update failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Session update failed: {str(exc)}"})


@app.get("/api/analytics/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        session = processor.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail={"message": f"Session {session_id} not found"})
        return {"success": True, "session": session}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Session fetch failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Session fetch failed: {str(exc)}"})


@app.get("/api/analytics/profiles/{profile_id}/sessions")
def list_sessions_for_profile(profile_id: str, limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        sessions = processor.list_sessions_for_profile(profile_id, limit=limit)
        return {"success": True, "sessions": sessions, "count": len(sessions)}
    except Exception as exc:
        LOGGER.error("Session listing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Session listing failed: {str(exc)}"})


@app.delete("/api/analytics/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, Any]:
    try:
        settings = get_settings()
        processor = TemplateProcessor(settings.database_path)
        deleted = processor.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"message": f"Session {session_id} not found"})
        return {"success": True, "message": f"Session {session_id} deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Session deletion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Session deletion failed: {str(exc)}"})


# ============================================================================
# Source Tracing API Endpoints
# ============================================================================

@app.get("/api/sources/trace/{ticker}/{metric}")
def trace_metric_source(
    ticker: str,
    metric: str,
    period: Optional[str] = Query(None, description="Period (e.g., '2023-FY')"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year")
) -> Dict[str, Any]:
    """Get full source trace for a metric."""
    try:
        settings = get_settings()
        tracer = SourceTracer(settings.database_path)
        trace = tracer.trace_metric(ticker, metric, period, fiscal_year)
        return {
            "success": True,
            "trace": trace.to_dict()
        }
    except Exception as e:
        LOGGER.error(f"Source trace failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Source trace failed: {str(e)}"})


@app.get("/api/sources/drilldown/{fact_id}")
def get_fact_drilldown(fact_id: int) -> Dict[str, Any]:
    """Get detailed drill-down information for a specific fact."""
    try:
        settings = get_settings()
        tracer = SourceTracer(settings.database_path)
        fact_detail = tracer.get_fact_drilldown(fact_id)
        
        if not fact_detail:
            raise HTTPException(status_code=404, detail={"message": f"Fact {fact_id} not found"})
        
        return {
            "success": True,
            "fact": fact_detail.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Fact drilldown failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Fact drilldown failed: {str(e)}"})


@app.get("/api/sources/lineage/{ticker}/{metric}")
def get_metric_lineage(
    ticker: str,
    metric: str,
    period: Optional[str] = Query(None, description="Period (e.g., '2023-FY')")
) -> Dict[str, Any]:
    """Get complete data lineage for a metric."""
    try:
        settings = get_settings()
        tracer = SourceTracer(settings.database_path)
        lineage = tracer.get_metric_lineage(ticker, metric, period)
        return {
            "success": True,
            "lineage": lineage
        }
    except Exception as e:
        LOGGER.error(f"Lineage retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Lineage retrieval failed: {str(e)}"})


# ============================================================================
# Custom Modeling API Endpoints
# ============================================================================

class CreateModelRequest(BaseModel):
    """Request to create a custom model."""
    name: str
    model_type: str  # "arima", "prophet", "lstm", "linear_regression", "growth_rate"
    parameters: Optional[Dict[str, Any]] = None
    metrics: Optional[List[str]] = None
    description: Optional[str] = None
    target_metric: Optional[str] = None
    frequency: Optional[str] = None
    forecast_horizon: Optional[int] = None
    regressors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "default"


class ForecastRequest(BaseModel):
    """Request to run a forecast."""
    ticker: str
    metric: str
    forecast_years: int = 3


class ScenarioRequest(BaseModel):
    """Request to run a scenario analysis."""
    ticker: str
    metric: str
    scenario_name: str
    assumptions: Dict[str, float]
    forecast_years: int = 3


@app.post("/api/models/create")
def create_custom_model(request: CreateModelRequest) -> Dict[str, Any]:
    """Create a new custom forecasting model."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        model = builder.create_model(
            user_id=request.user_id or "default",
            name=request.name,
            model_type=request.model_type,
            parameters=request.parameters,
            metrics=request.metrics,
            description=request.description,
            target_metric=request.target_metric,
            frequency=request.frequency,
            forecast_horizon=request.forecast_horizon,
            regressors=request.regressors,
            metadata=request.metadata,
        )
        return {
            "success": True,
            "model": model.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Model creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Model creation failed: {str(e)}"})


@app.get("/api/models")
def list_custom_models(
    user_id: Optional[str] = Query("default", description="User ID to filter models")
) -> Dict[str, Any]:
    """List all custom models for a user."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        models = builder.list_models(user_id or "default")
        return {
            "success": True,
            "models": [model.to_dict() for model in models],
            "count": len(models)
        }
    except Exception as e:
        LOGGER.error(f"Model listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Model listing failed: {str(e)}"})


@app.get("/api/models/backends")
def list_model_backends() -> Dict[str, Any]:
    """List available forecasting backends."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        return {"success": True, "backends": builder.available_backends()}
    except Exception as e:
        LOGGER.error(f"Backend listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Backend listing failed: {str(e)}"})


@app.get("/api/models/{model_id}/runs")
def list_model_runs_endpoint(
    model_id: str,
    limit: int = Query(20, ge=1, le=200)
) -> Dict[str, Any]:
    """List recent runs for a model."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        runs = builder.list_runs(model_id, limit=limit)
        return {"success": True, "runs": runs, "count": len(runs)}
    except Exception as e:
        LOGGER.error(f"Model run listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Model run listing failed: {str(e)}"})


@app.post("/api/models/{model_id}/forecast")
def run_forecast(
    model_id: str,
    request: ForecastRequest
) -> Dict[str, Any]:
    """Run a forecast using a custom model."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        model_run = builder.run_forecast(
            model_id=model_id,
            ticker=request.ticker,
            metric=request.metric,
            forecast_years=request.forecast_years
        )
        return {
            "success": True,
            "run": model_run.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Forecast failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Forecast failed: {str(e)}"})


@app.post("/api/models/{model_id}/scenario")
def run_scenario(
    model_id: str,
    request: ScenarioRequest
) -> Dict[str, Any]:
    """Run a scenario analysis with custom assumptions."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        model_run = builder.run_scenario(
            model_id=model_id,
            ticker=request.ticker,
            metric=request.metric,
            scenario_name=request.scenario_name,
            assumptions=request.assumptions,
            forecast_years=request.forecast_years
        )
        return {
            "success": True,
            "run": model_run.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Scenario analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Scenario analysis failed: {str(e)}"})


@app.get("/api/models/{model_id}/explain")
def explain_model(model_id: str) -> Dict[str, Any]:
    """Get explanation of model assumptions and methodology."""
    try:
        settings = get_settings()
        builder = ModelBuilder(settings.database_path)
        explanation = builder.explain_model(model_id)
        return {
            "success": True,
            "explanation": explanation
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Model explanation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Model explanation failed: {str(e)}"})


# ============================================================================
# Framework Upload API Endpoints
# ============================================================================

@app.post("/api/frameworks/upload")
async def upload_framework(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    user_id: Optional[str] = Form("default")
) -> Dict[str, Any]:
    """Upload a framework document."""
    try:
        settings = get_settings()
        processor = FrameworkProcessor(settings.database_path)
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        # Determine file type
        file_ext = (Path(file.filename).suffix or "").lower()
        file_type = file_ext.lstrip(".")
        
        # Process framework
        framework = processor.upload_framework(
            user_id=user_id or "default",
            name=name or file.filename or "Untitled Framework",
            file_path=tmp_path,
            file_type=file_type
        )
        
        # Clean up temp file
        try:
            tmp_path.unlink()
        except:
            pass
        
        return {
            "success": True,
            "framework": framework.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Framework upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Framework upload failed: {str(e)}"})


@app.get("/api/frameworks")
def list_frameworks(
    user_id: Optional[str] = Query("default", description="User ID to filter frameworks")
) -> Dict[str, Any]:
    """List all frameworks for a user."""
    try:
        settings = get_settings()
        processor = FrameworkProcessor(settings.database_path)
        frameworks = processor.list_frameworks(user_id or "default")
        return {
            "success": True,
            "frameworks": [f.to_dict() for f in frameworks],
            "count": len(frameworks)
        }
    except Exception as e:
        LOGGER.error(f"Framework listing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Framework listing failed: {str(e)}"})


@app.get("/api/frameworks/{framework_id}/extracted")
def get_framework_extracted(framework_id: str) -> Dict[str, Any]:
    """Get extracted content from a framework."""
    try:
        settings = get_settings()
        processor = FrameworkProcessor(settings.database_path)
        framework = processor.get_framework(framework_id)
        
        if not framework:
            raise HTTPException(status_code=404, detail={"message": f"Framework {framework_id} not found"})
        
        kpis = processor.get_framework_kpis(framework_id)
        methodology = processor.get_framework_methodology(framework_id)
        
        return {
            "success": True,
            "framework": framework.to_dict(),
            "kpis": [kpi.to_dict() for kpi in kpis],
            "methodology": [method.to_dict() for method in methodology],
        }
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Framework extraction retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Framework extraction retrieval failed: {str(e)}"})


@app.post("/api/frameworks/{framework_id}/activate")
def activate_framework(
    framework_id: str,
    conversation_id: Optional[str] = Body(None)
) -> Dict[str, Any]:
    """Activate a framework for a conversation session."""
    try:
        settings = get_settings()
        processor = FrameworkProcessor(settings.database_path)
        framework = processor.get_framework(framework_id)
        
        if not framework:
            raise HTTPException(status_code=404, detail={"message": f"Framework {framework_id} not found"})
        
        # Build context from framework
        context = processor.build_framework_context(framework_id)
        
        # TODO: Store active framework in conversation metadata
        # For now, just return the context
        
        return {
            "success": True,
            "framework_id": framework_id,
            "framework_name": framework.name,
            "context": context,
            "message": f"Framework '{framework.name}' activated. Responses will be guided by this framework."
        }
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Framework activation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Framework activation failed: {str(e)}"})


# ============================================================================
# Priority 7: User Experience & Accessibility Endpoints
# ============================================================================

@app.post("/api/dashboard/layouts")
def save_dashboard_layout_endpoint(
    layout_data: Dict[str, Any] = Body(..., description="Dashboard layout data"),
) -> Dict[str, Any]:
    """Save dashboard layout."""
    try:
        from .portfolio_dashboard_custom import DashboardLayout, DashboardWidget  # type: ignore
        widgets = [
            DashboardWidget(**w) for w in layout_data.get('widgets', [])
        ]
        layout = DashboardLayout(
            layout_id=layout_data.get('layout_id', f"layout_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"),
            layout_name=layout_data['layout_name'],
            user_id=layout_data.get('user_id'),
            portfolio_id=layout_data.get('portfolio_id'),
            widgets=widgets
        )
        
        # TODO: Implement save_dashboard_layout
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Dashboard layout saving not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Layout save failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Layout save failed: {str(e)}"})


@app.get("/api/dashboard/layouts/{layout_id}")
def load_dashboard_layout_endpoint(
    layout_id: str,
) -> Dict[str, Any]:
    """Load dashboard layout by ID."""
    try:
        # TODO: Implement load_dashboard_layout
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Dashboard layout loading not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"message": str(e)})
    except Exception as e:
        LOGGER.error(f"Layout load failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Layout load failed: {str(e)}"})


@app.get("/api/dashboard/layouts")
def list_dashboard_layouts_endpoint(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    portfolio_id: Optional[str] = Query(None, description="Filter by portfolio ID"),
) -> List[Dict[str, Any]]:
    """List available dashboard layouts."""
    try:
        # TODO: Implement list_dashboard_layouts
        raise HTTPException(
            status_code=501,
            detail={
                "message": "Dashboard layout listing not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Layout list failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Layout list failed: {str(e)}"})


@app.post("/api/user/preferences")
def save_user_preferences_endpoint(
    preferences_data: Dict[str, Any] = Body(..., description="User preferences data"),
) -> Dict[str, Any]:
    """Save user preferences."""
    try:
        from .portfolio_dashboard_custom import UserPreferences  # type: ignore
        preferences = UserPreferences(
            user_id=preferences_data['user_id'],
            theme=preferences_data.get('theme', 'light'),
            font_size=preferences_data.get('font_size', 'medium'),
            color_scheme=preferences_data.get('color_scheme'),
            accessibility_options=preferences_data.get('accessibility_options'),
            dashboard_layout_id=preferences_data.get('dashboard_layout_id')
        )
        
        # TODO: Implement save_user_preferences
        raise HTTPException(
            status_code=501,
            detail={
                "message": "User preferences saving not yet implemented",
                "error": "This feature is under development"
            }
        )
        # TODO: Function implementation code removed
    except Exception as e:
        LOGGER.error(f"Preferences save failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Preferences save failed: {str(e)}"})


@app.get("/api/user/{user_id}/preferences")
def load_user_preferences_endpoint(
    user_id: str,
) -> Dict[str, Any]:
    """Load user preferences by user ID."""
    try:
        # TODO: Implement load_user_preferences
        raise HTTPException(
            status_code=501,
            detail={
                "message": "User preferences loading not yet implemented",
                "error": "This feature is under development"
            }
        )
    except Exception as e:
        LOGGER.error(f"Preferences load failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": f"Preferences load failed: {str(e)}"})

