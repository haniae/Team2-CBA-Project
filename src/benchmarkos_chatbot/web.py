"""FastAPI service exposing the BenchmarkOS chatbot, analytics API, and web UI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import AnalyticsEngine, BenchmarkOSChatbot, database, load_settings

ALLOWED_ORIGINS = [origin.strip() for origin in (
    Path.cwd().joinpath(".allowed_origins").read_text().splitlines()
    if Path.cwd().joinpath(".allowed_origins").exists()
    else []
) if origin.strip()]

app = FastAPI(title="BenchmarkOS Analyst Copilot", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = (BASE_DIR.parent / "webui").resolve()
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class ChatRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


class MetricsResponse(BaseModel):
    ticker: str
    metrics: Dict[str, Optional[float]]
    period: str


class FactsResponse(BaseModel):
    ticker: str
    fiscal_year: int
    items: List[Dict]


class AuditEventResponse(BaseModel):
    ticker: str
    events: List[Dict]


@lru_cache
def get_settings():
    return load_settings()


@lru_cache
def get_engine() -> AnalyticsEngine:
    engine = AnalyticsEngine(get_settings())
    engine.refresh_metrics()
    return engine


def build_bot(conversation_id: Optional[str] = None) -> BenchmarkOSChatbot:
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


@app.get("/")
def root() -> FileResponse:
    if not FRONTEND_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend assets are not available.")
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    bot = build_bot(request.conversation_id)
    reply = bot.ask(request.prompt)
    return ChatResponse(
        conversation_id=bot.conversation.conversation_id,
        reply=reply,
    )


def _select_latest_records(
    records: Iterable[database.MetricRecord],
    span_fn,
) -> Dict[str, database.MetricRecord]:
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
    spans = [(start, end) for start, end in spans if start or end]
    if not spans:
        return "latest"
    start = min(span[0] for span in spans if span[0])
    end = max(span[1] for span in spans if span[1])
    return f"FY{start}" if start == end else f"FY{start}-FY{end}"


@app.get("/metrics", response_model=List[MetricsResponse])
def metrics(
    tickers: str = Query(..., description="Comma separated list of tickers"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
) -> List[MetricsResponse]:
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


@app.get("/facts", response_model=FactsResponse)
def facts(
    ticker: str = Query(...),
    fiscal_year: int = Query(...),
    metric: Optional[str] = Query(None),
) -> FactsResponse:
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


@app.get("/audit", response_model=AuditEventResponse)
def audit(
    ticker: str = Query(...),
    fiscal_year: Optional[int] = Query(None),
) -> AuditEventResponse:
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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
