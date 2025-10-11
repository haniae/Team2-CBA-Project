
"""Orchestrates sourcing and normalising market and filing data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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
    StooqQuoteClient,
    YahooFinanceClient,
    DEFAULT_FACT_CONCEPTS,
)
from .sec_bulk import CompanyFactsBulkCache

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
    errors: List[str] = field(default_factory=list)
    stooq_quotes_loaded: int = 0


class IngestionError(Exception):
    """Raised when ingestion cannot proceed."""


def ingest_financial_data(settings: Settings) -> Optional[IngestionReport]:
    """Bootstrap ingestion hook used by the CLI."""

    LOGGER.info("Bootstrap ingestion skipped (no packaged sample data).")
    return None


def _now() -> datetime:
    """Return the current UTC timestamp; extracted for easier testing."""
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

    database.initialise(settings.database_path)

    unique_tickers = sorted({ticker.upper() for ticker in tickers})
    LOGGER.info("Starting ingestion for %d tickers", len(unique_tickers))

    bulk_cache: Optional[CompanyFactsBulkCache] = None
    if getattr(settings, "use_companyfacts_bulk", False):
        try:
            bulk_cache = CompanyFactsBulkCache(
                settings.cache_dir / "companyfacts_bulk",
                url=settings.companyfacts_bulk_url,
                refresh_hours=settings.companyfacts_bulk_refresh_hours,
                user_agent=settings.sec_api_user_agent,
            )
        except Exception:
            LOGGER.warning("Failed to initialise SEC companyfacts bulk cache; continuing without it.", exc_info=True)
            bulk_cache = None

    stooq_client: Optional[StooqQuoteClient] = None
    if getattr(settings, "use_stooq_fallback", False):
        try:
            stooq_client = StooqQuoteClient(
                base_url=settings.stooq_quote_url,
                symbol_suffix=settings.stooq_symbol_suffix,
                timeout=settings.stooq_timeout,
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to initialise Stooq fallback client: %s", exc)
            stooq_client = None

    created_bloomberg = False
    edgar = edgar_client or EdgarClient(
        base_url=settings.edgar_base_url,
        user_agent=settings.sec_api_user_agent,
        cache_dir=settings.cache_dir,
        timeout=settings.http_request_timeout,
        min_interval=0.2,
        bulk_cache=bulk_cache,
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
    alias_records: List[database.TickerAliasRecord] = []

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
        if new_facts:
            alias_records.append(
                database.TickerAliasRecord(
                    ticker=ticker.upper(),
                    cik=new_facts[0].cik,
                    company_name=new_facts[0].company_name,
                    updated_at=_now(),
                )
            )
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
    if alias_records:
        database.upsert_ticker_aliases(settings.database_path, alias_records)

    quotes_loaded = 0
    stooq_quotes_loaded = 0
    missing_tickers: List[str] = []

    if getattr(settings, "disable_quote_refresh", False):
        LOGGER.debug("Quote refresh disabled via settings; skipping market data fetch")
    else:
        try:
            quotes = yahoo.fetch_quotes(unique_tickers)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("Yahoo quote ingestion failed: %s", exc)
            quotes = []
            missing_tickers = list(unique_tickers)
        else:
            quotes_loaded = database.bulk_insert_market_quotes(settings.database_path, quotes)
            fetched = {quote.ticker.upper() for quote in quotes}
            missing_tickers = [ticker for ticker in unique_tickers if ticker.upper() not in fetched]

    if missing_tickers and stooq_client is not None:
        try:
            stooq_quotes = stooq_client.fetch_quotes(missing_tickers)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("Stooq fallback ingestion failed: %s", exc)
        else:
            if stooq_quotes:
                stooq_quotes_loaded = database.bulk_insert_market_quotes(
                    settings.database_path, stooq_quotes
                )
                recovered = {quote.ticker.upper() for quote in stooq_quotes}
                missing_tickers = [ticker for ticker in missing_tickers if ticker.upper() not in recovered]

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

    records_loaded = (
        filings_loaded
        + facts_loaded
        + quotes_loaded
        + bloomberg_quotes_loaded
        + stooq_quotes_loaded
    )

    return IngestionReport(
        companies=unique_tickers,
        records_loaded=records_loaded,
        filings_loaded=filings_loaded,
        facts_loaded=facts_loaded,
        quotes_loaded=quotes_loaded,
        bloomberg_quotes_loaded=bloomberg_quotes_loaded,
        stooq_quotes_loaded=stooq_quotes_loaded,
        errors=errors,
    )
