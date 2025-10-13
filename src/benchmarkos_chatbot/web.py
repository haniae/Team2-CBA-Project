"""FastAPI service exposing the BenchmarkOS chatbot, analytics API, and web UI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query
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

class ChatRequest(BaseModel):
    """Payload expected by the /chat endpoint when posting a prompt."""
    prompt: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response returned after processing a chat prompt."""
    conversation_id: str
    reply: str


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


# ----- Routes -----------------------------------------------------------------

@app.get("/")
def root() -> FileResponse:
    """Serve the static index file, preferring the local webui build when present."""
    if FRONTEND_DIR.exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    if PACKAGE_STATIC.exists():
        return FileResponse(PACKAGE_STATIC / "index.html")
    raise HTTPException(status_code=404, detail="Frontend assets are not available.")


@app.get("/health")
def health() -> Dict[str, str]:
    """Lightweight liveness probe used by deployment infra."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Proxy chat submissions to the BenchmarkOS chatbot."""
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    prompt = request.prompt.strip()
    lowered = prompt.lower()
    if lowered == "help":
        settings = get_settings()
        conversation_id = request.conversation_id or str(uuid.uuid4())
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
        return ChatResponse(
            conversation_id=conversation_id,
            reply=HELP_TEXT,
        )

    bot = build_bot(request.conversation_id)
    reply = bot.ask(request.prompt)
    return ChatResponse(
        conversation_id=bot.conversation.conversation_id,
        reply=reply,
    )


@app.get("/help-content")
def help_content() -> Dict[str, Any]:
    """Expose help metadata for the web UI."""
    return get_help_metadata()


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


def _build_filing_urls(accession: Optional[str], cik: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Generate viewer and archive URLs for a filing accession."""
    if not accession:
        return None, None
    ix_url = f"https://www.sec.gov/ixviewer/doc?action=fetch&accn={accession}"
    archive_url = None
    if cik:
        clean_cik = cik.lstrip("0") or cik
        acc_no_dash = accession.replace("-", "")
        archive_url = (
            f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{acc_no_dash}/{acc_no_dash}-index.html"
        )
    return ix_url, archive_url


@app.get("/metrics", response_model=List[MetricsResponse])
def metrics(
    tickers: str = Query(..., description="Comma separated list of tickers"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
) -> List[MetricsResponse]:
    """Return latest metric snapshots for one or more tickers."""
    ticker_list = [ticker.strip().upper() for ticker in tickers.split(",") if ticker]
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
                status_code=404, detail=f"No metrics available for ticker {ticker}.",
            )
        chosen = _select_latest_records(records, span_fn=engine._period_span)
        descriptor = _summarise_period(
            engine._period_span(record.period) for record in chosen.values()
        )
        responses.append(
            MetricsResponse(
                ticker=ticker,
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
    # normalize
    tickers = [t.strip().upper() for t in tickers if t and t.strip()]
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
            detail={"error": "Missing metrics for some tickers", "missing": missing},
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
            result.setdefault(m, {}).setdefault(p, {})[t] = v

    # sorted keys for stable UI rendering
    result = {m: dict(sorted(pmap.items())) for m, pmap in sorted(result.items())}

    return {"tickers": display_tickers, "comparison": result}


@app.get("/facts", response_model=FactsResponse)
def facts(
    ticker: str = Query(...),
    fiscal_year: int = Query(...),
    metric: Optional[str] = Query(None),
) -> FactsResponse:
    """Expose detailed financial fact rows from the analytics store."""
    engine = get_engine()
    facts = engine.financial_facts(
        ticker=ticker.upper(),
        fiscal_year=fiscal_year,
        metric=metric.lower() if metric else None,
        limit=100,
    )
    if not facts:
        raise HTTPException(
            status_code=404,
            detail=f"No financial facts for {ticker.upper()} in FY{fiscal_year}.",
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
    return FactsResponse(ticker=ticker.upper(), fiscal_year=fiscal_year, items=items)


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
    ticker_clean = ticker.strip().upper()
    if not ticker_clean:
        raise HTTPException(status_code=400, detail="Ticker is required.")

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
    metric_key = None
    if metric:
        metric_key = metric.strip().lower().replace(" ", "_")

    collected: List[database.FinancialFactRecord] = []
    for year in years_to_fetch:
        try:
            collected.extend(
                engine.financial_facts(
                    ticker=ticker_clean,
                    fiscal_year=year,
                    metric=metric_key,
                    limit=(limit if year is None else None),
                )
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not collected:
        raise HTTPException(
            status_code=404,
            detail=f"No filings found for {ticker_clean}.",
        )

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
        sec_url, archive_url = _build_filing_urls(accession, getattr(fact, "cik", None))
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
            )
        )

    summary = FilingFactsSummary(
        count=len(items),
        fiscal_years=sorted(
            {item.fiscal_year for item in items if item.fiscal_year is not None}, reverse=True
        ),
        metrics=sorted({item.metric for item in items if item.metric}),
    )

    return FilingFactsResponse(ticker=ticker_clean, items=items, summary=summary)


@app.get("/audit", response_model=AuditEventResponse)
def audit(
    ticker: str = Query(...),
    fiscal_year: Optional[int] = Query(None),
) -> AuditEventResponse:
    """Return recorded audit trail events for a ticker."""
    engine = get_engine()
    events = engine.audit_events(ticker.upper(), fiscal_year=fiscal_year, limit=20)
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit events recorded for {ticker.upper()}.",
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
    return AuditEventResponse(ticker=ticker.upper(), events=payload)
