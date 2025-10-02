"""Basic coverage for the SQLite helper module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlite3

from benchmarkos_chatbot import database
from benchmarkos_chatbot.data_sources import AuditEvent, FinancialFact, FilingRecord, MarketQuote


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "chat.sqlite3"
    database.initialise(db_path)
    return db_path


def test_log_and_fetch_round_trip(temp_db: Path) -> None:
    conversation_id = "test-123"
    database.log_message(temp_db, conversation_id, "user", "Hello", datetime(2024, 1, 1))
    database.log_message(temp_db, conversation_id, "assistant", "Hi", datetime(2024, 1, 1, 0, 0, 10))

    messages = list(database.fetch_conversation(temp_db, conversation_id))
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "Hello"
    assert messages[1].content == "Hi"


def test_iter_conversation_summaries(temp_db: Path) -> None:
    database.log_message(temp_db, "conv-a", "user", "One")
    database.log_message(temp_db, "conv-a", "assistant", "Two")
    database.log_message(temp_db, "conv-b", "user", "Only")

    summaries = list(database.iter_conversation_summaries(temp_db))
    assert summaries == [("conv-b", 1), ("conv-a", 2)]


def test_most_recent_conversation_id(temp_db: Path) -> None:
    assert database.most_recent_conversation_id(temp_db) is None

    database.log_message(temp_db, "conv-a", "user", "Hi")
    database.log_message(temp_db, "conv-b", "user", "Hello")

    assert database.most_recent_conversation_id(temp_db) == "conv-b"


def _dt(year=2024, month=1, day=1, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def test_bulk_upsert_company_filings(temp_db: Path) -> None:
    filing = FilingRecord(
        cik="0000000123",
        ticker="TEST",
        accession_number="000123-23-000001",
        form_type="10-K",
        filed_at=_dt(),
        period_of_report=_dt().date(),
        acceptance_datetime=_dt(hour=12),
        data={"example": True},
    )
    inserted = database.bulk_upsert_company_filings(temp_db, [filing])
    assert inserted == 1
    assert database.bulk_upsert_company_filings(temp_db, [filing]) == 0


def test_bulk_upsert_financial_facts_roundtrip(temp_db: Path) -> None:
    fact = FinancialFact(
        cik="0000000123",
        ticker="TEST",
        metric="revenue",
        fiscal_year=2024,
        fiscal_period="FY",
        period="FY2024",
        value=123.45,
        unit="USD",
        source="edgar",
        source_filing="000123-23-000001",
        period_start=_dt(2023, 1, 1),
        period_end=_dt(2023, 12, 31),
        adjusted=False,
        adjustment_note=None,
        ingested_at=_dt(2024, 2, 1),
        raw={"val": 123.45},
    )
    database.bulk_upsert_financial_facts(temp_db, [fact])
    fetched = database.fetch_financial_facts(temp_db, "TEST", fiscal_year=2024)
    assert len(fetched) == 1
    assert fetched[0].value == pytest.approx(123.45)
    assert fetched[0].period == "FY2024"


def test_market_quotes_and_metrics(temp_db: Path) -> None:
    quote = MarketQuote(
        ticker="TEST",
        price=200.5,
        currency="USD",
        volume=1_500_000,
        timestamp=_dt(),
        source="yahoo",
        raw={"source": "test"},
    )
    assert database.bulk_insert_market_quotes(temp_db, [quote]) == 1
    assert database.bulk_insert_market_quotes(temp_db, [quote]) == 0

    metric = database.MetricRecord(
        ticker="TEST",
        metric="revenue",
        period="FY2024",
        value=123.45,
        source="edgar",
        updated_at=_dt(2024, 2, 1),
        start_year=2024,
        end_year=2024,
    )
    database.replace_metric_snapshots(temp_db, [metric])
    records = database.fetch_metric_snapshots(temp_db, "TEST")
    assert len(records) == 1
    assert records[0].metric == "revenue"


def test_audit_events_roundtrip(temp_db: Path) -> None:
    event = AuditEvent(
        ticker="TEST",
        event_type="ingestion.completed",
        entity_id="TEST-FY2024",
        details={"status": "ok"},
        created_at=_dt(),
        created_by="unit-test",
    )
    database.bulk_insert_audit_events(temp_db, [event])
    events = database.fetch_audit_events(temp_db, "TEST")
    assert len(events) == 1
    assert events[0].event_type == "ingestion.completed"


def test_initialise_upgrades_existing_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE financial_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cik TEXT NOT NULL,
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                fiscal_year INTEGER,
                value REAL
            )
            """
        )
        connection.commit()
    # Should migrate missing columns without raising
    database.initialise(db_path)
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(financial_facts)")}
    for expected in {"period", "source", "raw", "ingested_at"}:
        assert expected in columns
