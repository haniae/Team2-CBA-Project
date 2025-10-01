"""Data ingestion pipeline for financial statements and market metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd

from . import database
from .config import Settings
from .data_sources import SECFetcher, YahooFinanceFetcher, build_financial_dataset

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "sample_financials.csv"
)
DATA_SOURCE_NAME = "benchmarkos_sample_v1"

SECTOR_CODE_MAP = {
    "Information Technology": 10.0,
    "Consumer Staples": 20.0,
    "Industrials": 30.0,
    "Health Care": 35.0,
    "Energy": 40.0,
    "Consumer Discretionary": 45.0,
    "Communication Services": 50.0,
    "Financials": 55.0,
}
SECTOR_LABEL_MAP = {code: sector for sector, code in SECTOR_CODE_MAP.items()}

REQUIRED_COLUMNS = {
    "ticker",
    "company_name",
    "sector",
    "fiscal_year",
    "revenue",
    "ebitda",
    "net_income",
    "operating_income",
    "total_equity",
    "total_assets",
    "shares_outstanding",
    "dividends_paid",
    "free_cash_flow",
    "operating_cash_flow",
    "capital_expenditure",
    "cash",
    "total_debt",
    "enterprise_value",
    "market_cap",
    "price",
    "working_capital",
    "share_buybacks",
    "non_recurring_expense",
    "stock_compensation",
}

ADJUSTED_METRICS = {
    "adjusted_ebitda": "Added back disclosed non-recurring expenses to EBITDA to enable comparability.",
    "adjusted_net_income": "Normalised net income by removing non-recurring charges and 50% of stock-based compensation.",
    "clean_operating_income": "Operating income adjusted for one-off restructuring charges.",
    "normalised_free_cash_flow": "Free cash flow adjusted for capitalised transformation costs (30% of stock compensation).",
}


@dataclass(frozen=True)
class IngestionReport:
    """Summary output from a single ingestion run."""

    companies: List[str]
    records_loaded: int
    adjustments_applied: List[str]
    source_path: Path


def load_financial_data(data_path: Path | None = None) -> pd.DataFrame:
    """Load the canonical CSV dataset bundled with the repository."""

    path = data_path or DEFAULT_DATA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Financial data file not found at {path}.")

    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(
            "Dataset is missing required columns: " + ", ".join(sorted(missing))
        )
    return df


def _apply_accounting_adjustments(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Apply normalisation logic and return the adjusted frame plus audit notes."""

    adjusted = df.copy()
    notes: List[str] = []

    adjusted["adjusted_ebitda"] = adjusted["ebitda"] + adjusted["non_recurring_expense"]
    notes.append("Added back disclosed non-recurring expenses to EBITDA across all issuers.")

    adjusted["adjusted_net_income"] = (
        adjusted["net_income"]
        + adjusted["non_recurring_expense"]
        + 0.5 * adjusted["stock_compensation"]
    )
    notes.append(
        "Adjusted net income to exclude one-off charges and amortise 50% of stock-based compensation."
    )

    adjusted["clean_operating_income"] = (
        adjusted["operating_income"] + adjusted["non_recurring_expense"]
    )
    notes.append("Normalised operating income by removing restructuring charges flagged in 10-K footnotes.")

    adjusted["normalised_free_cash_flow"] = (
        adjusted["free_cash_flow"] + 0.3 * adjusted["stock_compensation"]
    )
    notes.append("Capitalised a share of transformation costs to derive normalised free cash flow.")

    return adjusted, notes


def _iter_metric_rows(row: pd.Series) -> Iterable[Tuple[str, float, bool]]:
    """Yield metric tuples (name, value, adjusted_flag)."""

    metrics = {
        "revenue": float(row["revenue"]),
        "ebitda": float(row["ebitda"]),
        "adjusted_ebitda": float(row["adjusted_ebitda"]),
        "net_income": float(row["net_income"]),
        "adjusted_net_income": float(row["adjusted_net_income"]),
        "operating_income": float(row["operating_income"]),
        "clean_operating_income": float(row["clean_operating_income"]),
        "total_equity": float(row["total_equity"]),
        "total_assets": float(row["total_assets"]),
        "shares_outstanding": float(row["shares_outstanding"]),
        "dividends_paid": float(row["dividends_paid"]),
        "free_cash_flow": float(row["free_cash_flow"]),
        "normalised_free_cash_flow": float(row["normalised_free_cash_flow"]),
        "operating_cash_flow": float(row["operating_cash_flow"]),
        "capital_expenditure": float(row["capital_expenditure"]),
        "cash": float(row["cash"]),
        "total_debt": float(row["total_debt"]),
        "enterprise_value": float(row["enterprise_value"]),
        "market_cap": float(row["market_cap"]),
        "price": float(row["price"]),
        "working_capital": float(row["working_capital"]),
        "share_buybacks": float(row["share_buybacks"]),
        "non_recurring_expense": float(row["non_recurring_expense"]),
        "stock_compensation": float(row["stock_compensation"]),
        "sector_code": float(SECTOR_CODE_MAP[row["sector"]]),
    }

    for metric, value in metrics.items():
        yield metric, value, metric in ADJUSTED_METRICS


def ingest_financial_data(
    settings: Settings, *, data_path: Path | None = None
) -> IngestionReport:
    """Load, normalise, and persist financial data into SQLite."""

    df_raw = load_financial_data(data_path)
    df_adjusted, adjustment_notes = _apply_accounting_adjustments(df_raw)
    timestamp = datetime.now(timezone.utc)

    records_loaded = 0
    for _, row in df_adjusted.iterrows():
        fiscal_year = int(row["fiscal_year"])
        ticker = str(row["ticker"])
        company_name = str(row["company_name"])

        for metric, value, is_adjusted in _iter_metric_rows(row):
            adjustment_note = ADJUSTED_METRICS.get(metric)
            fact = database.FinancialFact(
                ticker=ticker,
                company_name=company_name,
                fiscal_year=fiscal_year,
                metric=metric,
                value=value,
                source=DATA_SOURCE_NAME,
                adjusted=is_adjusted,
                adjustment_note=adjustment_note,
                ingested_at=timestamp,
            )
            database.upsert_financial_fact(settings.database_path, fact)
            records_loaded += 1

        for note in adjustment_notes:
            database.record_audit_event(
                settings.database_path,
                database.AuditEvent(
                    event_type="accounting_adjustment",
                    entity_id=f"{ticker}-{fiscal_year}",
                    details=note,
                    created_at=timestamp,
                    created_by="ingestion-pipeline",
                ),
            )

    completion_timestamp = datetime.now(timezone.utc)
    database.record_audit_event(
        settings.database_path,
        database.AuditEvent(
            event_type="ingestion",
            entity_id=DATA_SOURCE_NAME,
            details=(
                f"Ingested {records_loaded} normalised facts across "
                f"{df_adjusted['ticker'].nunique()} tickers."
            ),
            created_at=completion_timestamp,
            created_by="ingestion-pipeline",
        ),
    )

    return IngestionReport(
        companies=sorted(df_adjusted["ticker"].unique()),
        records_loaded=records_loaded,
        adjustments_applied=adjustment_notes,
        source_path=data_path or DEFAULT_DATA_PATH,
    )

def _sector_code(sector: str) -> float:
    if sector in SECTOR_CODE_MAP:
        return SECTOR_CODE_MAP[sector]
    dynamic_code = 90.0 + len(SECTOR_CODE_MAP)
    SECTOR_CODE_MAP.setdefault(sector, dynamic_code)
    SECTOR_LABEL_MAP[dynamic_code] = sector
    return dynamic_code


def ingest_live_tickers(
    settings: Settings,
    tickers: Iterable[str],
    *,
    years: int = 5,
    sec_user_agent: str | None = None,
) -> IngestionReport:
    """Fetch and ingest live fundamentals for the supplied tickers."""

    tickers = [t.upper() for t in tickers]
    if not tickers:
        raise ValueError("No tickers supplied for live ingestion.")

    yf_fetcher = YahooFinanceFetcher()
    sec_fetcher = SECFetcher(user_agent=sec_user_agent or settings.sec_api_user_agent)

    frames = []
    for ticker in tickers:
        dataset = build_financial_dataset(
            ticker,
            years=years,
            sec_fetcher=sec_fetcher,
            yahoo_fetcher=yf_fetcher,
        )
        dataset["sector_code"] = dataset["sector"].map(_sector_code)
        frames.append(dataset)

    combined = pd.concat(frames, ignore_index=True)
    adjusted, adjustment_notes = _apply_accounting_adjustments(combined)
    timestamp = datetime.now(timezone.utc)
    records_loaded = 0

    for _, row in adjusted.iterrows():
        fiscal_year = int(row["fiscal_year"])
        ticker = str(row["ticker"]).upper()
        company_name = str(row["company_name"])

        for metric, value, is_adjusted in _iter_metric_rows(row):
            fact = database.FinancialFact(
                ticker=ticker,
                company_name=company_name,
                fiscal_year=fiscal_year,
                metric=metric,
                value=float(value),
                source="live_yahoo_sec_v1",
                adjusted=is_adjusted,
                adjustment_note=ADJUSTED_METRICS.get(metric),
                ingested_at=timestamp,
            )
            database.upsert_financial_fact(settings.database_path, fact)
            records_loaded += 1

        for note in adjustment_notes:
            database.record_audit_event(
                settings.database_path,
                database.AuditEvent(
                    event_type="accounting_adjustment",
                    entity_id=f"{ticker}-{fiscal_year}",
                    details=note,
                    created_at=timestamp,
                    created_by="live-ingestion",
                ),
            )

    completion_timestamp = datetime.now(timezone.utc)
    database.record_audit_event(
        settings.database_path,
        database.AuditEvent(
            event_type="ingestion",
            entity_id="live_yahoo_sec_v1",
            details=(
                f"Ingested {records_loaded} normalised facts across "
                f"{adjusted['ticker'].nunique()} tickers."
            ),
            created_at=completion_timestamp,
            created_by="live-ingestion",
        ),
    )

    return IngestionReport(
        companies=sorted(adjusted["ticker"].unique()),
        records_loaded=records_loaded,
        adjustments_applied=adjustment_notes,
        source_path=Path("live") / "yahoo-sec",
    )
