
"""Orchestrates sourcing and normalising market and filing data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from . import database
from .config import Settings
from .data_sources import (
    AuditEvent,
    BloombergClient,
    EdgarClient,
    FinancialFact,
    FilingRecord,
    YahooFinanceClient,
    DEFAULT_FACT_CONCEPTS,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionReport:
    """Summary outcome from an ingestion run."""

    companies: List[str]
    records_loaded: int
    filings_loaded: int
    facts_loaded: int
    quotes_loaded: int
    bloomberg_quotes_loaded: int
    errors: List[str]


class IngestionError(Exception):
    """Raised when ingestion cannot proceed."""


def ingest_financial_data(settings: Settings) -> Optional[IngestionReport]:
    """Bootstrap ingestion hook used by the CLI."""

    LOGGER.info("Bootstrap ingestion skipped (no packaged sample data).")
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ingest_live_tickers(
    settings: Settings,
    tickers: Sequence[str],
    *,
    years: int = 10,
    edgar_forms: Optional[Sequence[str]] = None,
    fact_concepts: Optional[Sequence[str]] = None,
    edgar_client: Optional[EdgarClient] = None,
    yahoo_client: Optional[YahooFinanceClient] = None,
    bloomberg_client: Optional[BloombergClient] = None,
) -> IngestionReport:
    """Ingest filings and market data for ``tickers`` into the datastore."""

    if not tickers:
        raise IngestionError("No tickers supplied for ingestion")

    unique_tickers = sorted({ticker.upper() for ticker in tickers})
    LOGGER.info("Starting ingestion for %d tickers", len(unique_tickers))

    created_bloomberg = False
    edgar = edgar_client or EdgarClient(
        base_url=settings.edgar_base_url,
        user_agent=settings.sec_api_user_agent,
        cache_dir=settings.cache_dir,
        timeout=settings.http_request_timeout,
        min_interval=0.2,
    )
    yahoo = yahoo_client or YahooFinanceClient(
        base_url=settings.yahoo_quote_url,
        timeout=settings.http_request_timeout,
        batch_size=settings.yahoo_quote_batch_size,
    )

    bloomberg: Optional[BloombergClient]
    if settings.enable_bloomberg:
        if bloomberg_client is not None:
            bloomberg = bloomberg_client
        else:
            bloomberg = BloombergClient(
                host=settings.bloomberg_host,
                port=settings.bloomberg_port,
                timeout=settings.bloomberg_timeout,
            )
            created_bloomberg = True
    else:
        bloomberg = bloomberg_client  # allow explicit override

    filings: List[FilingRecord] = []
    facts: List[FinancialFact] = []
    audit_events: List[AuditEvent] = []
    errors: List[str] = []

    concepts = tuple(fact_concepts or DEFAULT_FACT_CONCEPTS)

    for ticker in unique_tickers:
        try:
            new_filings = edgar.fetch_filings(ticker, forms=edgar_forms)
            new_facts = edgar.fetch_facts(ticker, concepts=concepts, years=years)
        except Exception as exc:  # pragma: no cover - exercised in live ingestion
            message = f"{ticker}: {exc}"
            LOGGER.error("Failed to ingest %s", ticker, exc_info=True)
            errors.append(message)
            audit_events.append(
                AuditEvent(
                    ticker=ticker,
                    event_type="ingestion.failed",
                    entity_id=None,
                    details={"error": str(exc)},
                    created_at=_now(),
                    created_by="data_ingestion",
                )
            )
            continue

        filings.extend(new_filings)
        facts.extend(new_facts)
        if new_facts and new_facts[0].fiscal_year is not None:
            entity_id = f"{ticker}-FY{new_facts[0].fiscal_year}"
        else:
            entity_id = ticker
        audit_events.append(
            AuditEvent(
                ticker=ticker,
                event_type="ingestion.completed",
                entity_id=entity_id,
                details={
                    "filings": len(new_filings),
                    "facts": len(new_facts),
                },
                created_at=_now(),
                created_by="data_ingestion",
            )
        )

    filings_loaded = database.bulk_upsert_company_filings(settings.database_path, filings)
    facts_loaded = database.bulk_upsert_financial_facts(settings.database_path, facts)
    database.bulk_insert_audit_events(settings.database_path, audit_events)

    quotes = yahoo.fetch_quotes(unique_tickers)
    quotes_loaded = database.bulk_insert_market_quotes(settings.database_path, quotes)

    bloomberg_quotes_loaded = 0
    if bloomberg:
        try:
            bloomberg_quotes = bloomberg.fetch_quotes(unique_tickers)
            bloomberg_quotes_loaded = database.bulk_insert_market_quotes(
                settings.database_path, bloomberg_quotes
            )
        except Exception as exc:  # pragma: no cover - depends on Bloomberg availability
            LOGGER.warning("Bloomberg quote ingestion failed: %s", exc)
        finally:
            if created_bloomberg:
                bloomberg.close()

    records_loaded = filings_loaded + facts_loaded + quotes_loaded + bloomberg_quotes_loaded

    return IngestionReport(
        companies=unique_tickers,
        records_loaded=records_loaded,
        filings_loaded=filings_loaded,
        facts_loaded=facts_loaded,
        quotes_loaded=quotes_loaded,
        bloomberg_quotes_loaded=bloomberg_quotes_loaded,
        errors=errors,
    )
