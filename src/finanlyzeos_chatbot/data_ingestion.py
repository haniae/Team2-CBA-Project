
"""Orchestrates sourcing and normalising market and filing data."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

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

DEFAULT_CONCURRENCY = 8
_FACT_CACHE: Dict[str, Tuple[List[FilingRecord], List[FinancialFact]]] = {}
SECTOR_CODES = {
    "Information Technology": 45.0,
    "Consumer Staples": 30.0,
    "Industrials": 20.0,
    "Health Care": 35.0,
    "Energy": 40.0,
    "Financials": 55.0,
    "Consumer Discretionary": 25.0,
    "Communication Services": 50.0,
}


async def _fetch_ticker_data(
    ticker: str,
    years: int,
    edgar: EdgarClient,
    edgar_forms: Optional[Sequence[str]],
    concepts: Sequence[str],
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Fetch filings and facts for a single ticker with bounded concurrency."""
    if ticker in _FACT_CACHE:
        cached_filings, cached_facts = _FACT_CACHE[ticker]
        return {
            "ticker": ticker,
            "filings": list(cached_filings),
            "facts": list(cached_facts),
            "fetch_ms": 0,
            "error": None,
        }

    async with semaphore:
        start = time.perf_counter()
        try:
            filings, facts = await asyncio.to_thread(
                _blocking_fetch_edgar,
                edgar,
                ticker,
                years,
                edgar_forms,
                concepts,
            )
        except Exception as exc:  # pragma: no cover - network dependent
            fetch_ms = int((time.perf_counter() - start) * 1000)
            return {
                "ticker": ticker,
                "filings": [],
                "facts": [],
                "fetch_ms": fetch_ms,
                "error": str(exc),
            }
        fetch_ms = int((time.perf_counter() - start) * 1000)

    _FACT_CACHE[ticker] = (list(filings), list(facts))
    return {
        "ticker": ticker,
        "filings": list(filings),
        "facts": list(facts),
        "fetch_ms": fetch_ms,
        "error": None,
    }


def _blocking_fetch_edgar(
    edgar: EdgarClient,
    ticker: str,
    years: int,
    edgar_forms: Optional[Sequence[str]],
    concepts: Sequence[str],
) -> Tuple[List[FilingRecord], List[FinancialFact]]:
    """Blocking helper executed inside a worker thread."""
    filings = edgar.fetch_filings(ticker, forms=edgar_forms)
    facts = edgar.fetch_facts(ticker, concepts=concepts, years=years)
    return filings, facts


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

    data_path = Path(__file__).resolve().parents[2] / "data" / "sample_financials.csv"
    if not data_path.exists():
        raise IngestionError(f"Sample financial dataset not found at {data_path}")

    frame = pd.read_csv(data_path)
    if frame.empty:
        raise IngestionError("Sample financial dataset is empty.")

    database.initialise(settings.database_path)
    if hasattr(settings, "disable_quote_refresh"):
        object.__setattr__(settings, "disable_quote_refresh", True)

    # Normalise tickers early so lookups stay consistent across the ingestion flow.
    frame["ticker"] = frame["ticker"].astype(str).str.upper()

    metric_map: Dict[str, Tuple[str, Optional[str]]] = {
        "revenue": ("revenue", "USD"),
        "ebitda": ("ebitda", "USD"),
        "net_income": ("net_income", "USD"),
        "operating_income": ("operating_income", "USD"),
        "total_equity": ("shareholders_equity", "USD"),
        "total_assets": ("total_assets", "USD"),
        "shares_outstanding": ("shares_outstanding", "shares"),
        "dividends_paid": ("dividends_paid", "USD"),
        "free_cash_flow": ("free_cash_flow", "USD"),
        "operating_cash_flow": ("cash_from_operations", "USD"),
        "capital_expenditure": ("capital_expenditures", "USD"),
        "cash": ("cash_and_cash_equivalents", "USD"),
        "total_debt": ("total_debt", "USD"),
        "enterprise_value": ("enterprise_value", "USD"),
        "market_cap": ("market_cap", "USD"),
        "price": ("price", "USD"),
        "working_capital": ("working_capital", "USD"),
        "share_buybacks": ("share_repurchases", "USD"),
        "non_recurring_expense": ("non_recurring_expense", "USD"),
        "stock_compensation": ("stock_compensation", "USD"),
    }

    tickers = sorted(frame["ticker"].unique())
    cik_map: Dict[str, str] = {
        ticker: f"{index + 1:010d}" for index, ticker in enumerate(tickers)
    }

    facts: List[FinancialFact] = []
    aliases: List[database.TickerAliasRecord] = []
    audit_events: List[AuditEvent] = []

    def _is_missing(value: Any) -> bool:
        return pd.isna(value)

    for ticker in tickers:
        company_rows = frame[frame["ticker"] == ticker].sort_values("fiscal_year")
        if company_rows.empty:
            continue

        first = company_rows.iloc[0]
        company_name = str(first.get("company_name", "") or "")
        sector = str(first.get("sector", "") or "")
        cik = cik_map[ticker]
        aliases.append(
            database.TickerAliasRecord(
                ticker=ticker,
                cik=cik,
                company_name=company_name,
                updated_at=_now(),
            )
        )

        sector_code = SECTOR_CODES.get(sector)
        if sector_code is not None:
            facts.append(
                FinancialFact(
                    cik=cik,
                    ticker=ticker,
                    company_name=company_name,
                    metric="sector_code",
                    fiscal_year=None,
                    fiscal_period=None,
                    period="FYSECTOR",
                    value=float(sector_code),
                    unit=None,
                    source="sample",
                    source_filing="sample-sector",
                    period_start=None,
                    period_end=None,
                    adjusted=False,
                    adjustment_note=None,
                    ingested_at=_now(),
                    raw={
                        "source": "sample_financials",
                        "sector": sector,
                    },
                )
            )

        for row in company_rows.to_dict("records"):
            fiscal_year_value = row.get("fiscal_year")
            if _is_missing(fiscal_year_value):
                continue
            fiscal_year = int(fiscal_year_value)
            period_label = f"FY{fiscal_year}"
            ingested_at = _now()
            source_filing = f"sample-{fiscal_year}"

            for column, (metric_name, unit) in metric_map.items():
                value = row.get(column)
                if _is_missing(value):
                    continue
                facts.append(
                    FinancialFact(
                        cik=cik,
                        ticker=ticker,
                        company_name=company_name,
                        metric=metric_name,
                        fiscal_year=fiscal_year,
                        fiscal_period="FY",
                        period=period_label,
                        value=float(value),
                        unit=unit,
                        source="sample",
                        source_filing=source_filing,
                        period_start=None,
                        period_end=None,
                        adjusted=False,
                        adjustment_note=None,
                        ingested_at=ingested_at,
                        raw={
                            "source": "sample_financials",
                            "original_metric": column,
                            "fiscal_year": fiscal_year,
                        },
                    )
                )

            total_assets = row.get("total_assets")
            total_equity = row.get("total_equity")
            if not _is_missing(total_assets) and not _is_missing(total_equity):
                total_liabilities = float(total_assets) - float(total_equity)
                facts.append(
                    FinancialFact(
                        cik=cik,
                        ticker=ticker,
                        company_name=company_name,
                        metric="total_liabilities",
                        fiscal_year=fiscal_year,
                        fiscal_period="FY",
                        period=period_label,
                        value=total_liabilities,
                        unit="USD",
                        source="sample",
                        source_filing=source_filing,
                        period_start=None,
                        period_end=None,
                        adjusted=False,
                        adjustment_note=None,
                        ingested_at=ingested_at,
                        raw={
                            "source": "sample_financials",
                            "calculation": "total_assets - total_equity",
                            "fiscal_year": fiscal_year,
                        },
                    )
                )

            revenue = row.get("revenue")
            ebitda = row.get("ebitda")
            non_recurring = row.get("non_recurring_expense", 0.0)
            stock_comp = row.get("stock_compensation", 0.0)
            net_income = row.get("net_income")

            adjusted_note = (
                "Adjusted for non-recurring expense and 50% of stock compensation."
            )

            if not _is_missing(ebitda) and not _is_missing(non_recurring):
                adjusted_ebitda_value = float(ebitda) + float(non_recurring)
                facts.append(
                    FinancialFact(
                        cik=cik,
                        ticker=ticker,
                        company_name=company_name,
                        metric="adjusted_ebitda",
                        fiscal_year=fiscal_year,
                        fiscal_period="FY",
                        period=period_label,
                        value=adjusted_ebitda_value,
                        unit="USD",
                        source="sample",
                        source_filing=source_filing,
                        period_start=None,
                        period_end=None,
                        adjusted=True,
                        adjustment_note="Adds back non-recurring expense to EBITDA.",
                        ingested_at=ingested_at,
                        raw={
                            "source": "sample_financials",
                            "fiscal_year": fiscal_year,
                            "formula": "ebitda + non_recurring_expense",
                        },
                    )
                )
                if not _is_missing(revenue) and float(revenue):
                    adjusted_margin = adjusted_ebitda_value / float(revenue)
                    facts.append(
                        FinancialFact(
                            cik=cik,
                            ticker=ticker,
                            company_name=company_name,
                            metric="adjusted_ebitda_margin",
                            fiscal_year=fiscal_year,
                            fiscal_period="FY",
                            period=period_label,
                            value=adjusted_margin,
                            unit=None,
                            source="sample",
                            source_filing=source_filing,
                            period_start=None,
                            period_end=None,
                            adjusted=True,
                            adjustment_note="Adjusted EBITDA margin uses adjusted EBITDA divided by revenue.",
                            ingested_at=ingested_at,
                            raw={
                                "source": "sample_financials",
                                "fiscal_year": fiscal_year,
                                "formula": "(ebitda + non_recurring_expense) / revenue",
                            },
                        )
                    )

            if not _is_missing(net_income):
                adjustments = 0.0
                if not _is_missing(non_recurring):
                    adjustments += float(non_recurring)
                if not _is_missing(stock_comp):
                    adjustments += 0.5 * float(stock_comp)
                adjusted_net_income = float(net_income) + adjustments
                facts.append(
                    FinancialFact(
                        cik=cik,
                        ticker=ticker,
                        company_name=company_name,
                        metric="adjusted_net_income",
                        fiscal_year=fiscal_year,
                        fiscal_period="FY",
                        period=period_label,
                        value=adjusted_net_income,
                        unit="USD",
                        source="sample",
                        source_filing=source_filing,
                        period_start=None,
                        period_end=None,
                        adjusted=True,
                        adjustment_note=adjusted_note,
                        ingested_at=ingested_at,
                        raw={
                            "source": "sample_financials",
                            "fiscal_year": fiscal_year,
                            "formula": "net_income + non_recurring_expense + 0.5 * stock_compensation",
                        },
                    )
                )

        audit_events.append(
            AuditEvent(
                ticker=ticker,
                event_type="ingestion",
                entity_id=f"{ticker}-sample",
                details={
                    "source": "sample_financials",
                    "company_name": company_name,
                    "rows": len(company_rows),
                    "years": sorted(set(company_rows["fiscal_year"].tolist())),
                },
                created_at=_now(),
                created_by="sample_ingestion",
            )
        )

    with database.temporary_connection(settings.database_path) as connection:
        facts_loaded = database.bulk_upsert_financial_facts(
            settings.database_path, facts, connection=connection
        )
        database.bulk_insert_audit_events(
            settings.database_path, audit_events, connection=connection
        )
        database.upsert_ticker_aliases(
            settings.database_path, aliases, connection=connection
        )

    return IngestionReport(
        companies=tickers,
        records_loaded=facts_loaded,
        filings_loaded=0,
        facts_loaded=facts_loaded,
        quotes_loaded=0,
        bloomberg_quotes_loaded=0,
        errors=[],
    )


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

    concepts = tuple(fact_concepts or DEFAULT_FACT_CONCEPTS)
    year_buffer = max(1, getattr(settings, "ingestion_year_buffer", 2))
    current_year = _now().year
    fetch_plans: List[Tuple[str, int]] = []
    for ticker in unique_tickers:
        existing_year = database.latest_fiscal_year(settings.database_path, ticker)
        years_to_fetch = years
        if existing_year is not None:
            delta_years = max(1, current_year - existing_year + year_buffer)
            years_to_fetch = max(year_buffer, min(years, delta_years))
        fetch_plans.append((ticker, years_to_fetch))

    async def _gather_fetches() -> List[Dict[str, Any]]:
        concurrency = max(1, getattr(settings, "ingestion_concurrency", DEFAULT_CONCURRENCY))
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            _fetch_ticker_data(plan_ticker, plan_years, edgar, edgar_forms, concepts, semaphore)
            for plan_ticker, plan_years in fetch_plans
        ]
        return await asyncio.gather(*tasks)

    fetch_results = asyncio.run(_gather_fetches())

    filings: List[FilingRecord] = []
    facts: List[FinancialFact] = []
    audit_events: List[AuditEvent] = []
    errors: List[str] = []
    alias_records: List[database.TickerAliasRecord] = []

    for result in fetch_results:
        ticker = result["ticker"]
        fetch_ms = result["fetch_ms"]
        normalize_start = time.perf_counter()
        if result["error"]:
            message = f"{ticker}: {result['error']}"
            LOGGER.error("Failed to ingest %s", ticker, exc_info=True)
            errors.append(message)
            audit_events.append(
                AuditEvent(
                    ticker=ticker,
                    event_type="ingestion.failed",
                    entity_id=None,
                    details={"error": result["error"]},
                    created_at=_now(),
                    created_by="data_ingestion",
                )
            )
            LOGGER.debug("ingest.timing %s fetch_ms=%d normalize_ms=%d", ticker, fetch_ms, 0)
            continue

        new_filings: List[FilingRecord] = result["filings"]
        new_facts: List[FinancialFact] = result["facts"]
        filings.extend(new_filings)
        facts.extend(new_facts)

        if new_facts:
            alias_timestamp = _now()
            alias_records.append(
                database.TickerAliasRecord(
                    ticker=ticker.upper(),
                    cik=new_facts[0].cik,
                    company_name=new_facts[0].company_name,
                    updated_at=alias_timestamp,
                )
            )
            entity_id = f"{ticker}-FY{new_facts[0].fiscal_year}" if new_facts[0].fiscal_year else ticker
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
        normalize_ms = int((time.perf_counter() - normalize_start) * 1000)
        LOGGER.debug("ingest.timing %s fetch_ms=%d normalize_ms=%d", ticker, fetch_ms, normalize_ms)

    write_start = time.perf_counter()
    filings_loaded = 0
    facts_loaded = 0
    with database.temporary_connection(settings.database_path) as connection:
        filings_loaded = database.bulk_upsert_company_filings(
            settings.database_path, filings, connection=connection
        )
        facts_loaded = database.bulk_upsert_financial_facts(
            settings.database_path, facts, connection=connection
        )
        database.bulk_insert_audit_events(
            settings.database_path, audit_events, connection=connection
        )
        if alias_records:
            database.upsert_ticker_aliases(
                settings.database_path, alias_records, connection=connection
            )
    write_ms = int((time.perf_counter() - write_start) * 1000)
    LOGGER.debug("ingest.write_ms=%d", write_ms)

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
            with database.temporary_connection(settings.database_path) as quote_connection:
                quotes_loaded = database.bulk_insert_market_quotes(
                    settings.database_path, quotes, connection=quote_connection
                )
            fetched = {quote.ticker.upper() for quote in quotes}
            missing_tickers = [ticker for ticker in unique_tickers if ticker.upper() not in fetched]

    if missing_tickers and stooq_client is not None:
        try:
            stooq_quotes = stooq_client.fetch_quotes(missing_tickers)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("Stooq fallback ingestion failed: %s", exc)
        else:
            if stooq_quotes:
                with database.temporary_connection(settings.database_path) as quote_connection:
                    stooq_quotes_loaded = database.bulk_insert_market_quotes(
                        settings.database_path, stooq_quotes, connection=quote_connection
                    )
                recovered = {quote.ticker.upper() for quote in stooq_quotes}
                missing_tickers = [
                    ticker for ticker in missing_tickers if ticker.upper() not in recovered
                ]

    bloomberg_quotes_loaded = 0
    if bloomberg:
        try:
            bloomberg_quotes = bloomberg.fetch_quotes(unique_tickers)
            with database.temporary_connection(settings.database_path) as quote_connection:
                bloomberg_quotes_loaded = database.bulk_insert_market_quotes(
                    settings.database_path, bloomberg_quotes, connection=quote_connection
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
