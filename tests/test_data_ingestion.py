"""Tests for the data ingestion workflow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from benchmarkos_chatbot import ingest_financial_data
from benchmarkos_chatbot.config import Settings
from benchmarkos_chatbot import database


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )


def test_ingest_financial_data_persists_records(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    database.initialise(settings.database_path)

    report = ingest_financial_data(settings)

    assert len(report.companies) == 8
    assert report.records_loaded > 0

    facts = database.fetch_financial_facts(settings.database_path)
    assert facts, "Financial facts should be stored after ingestion."
    assert any(f.metric == "adjusted_net_income" for f in facts)

    # Governance trail should capture ingestion notes.
    audit_events = database.fetch_recent_audit_events(settings.database_path, limit=5)
    assert any(event.event_type == "ingestion" for event in audit_events)


def test_sector_codes_round_trip(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    database.initialise(settings.database_path)
    ingest_financial_data(settings)

    facts = database.fetch_financial_facts(settings.database_path, ticker="EVO")
    sector_codes = {fact.metric: fact.value for fact in facts if fact.metric == "sector_code"}
    assert sector_codes, "Sector code fact should be stored for each company."
    assert sector_codes["sector_code"] == 40.0


def test_ingestion_adjustments_match_source(tmp_path: Path) -> None:
    settings = _make_settings(tmp_path)
    database.initialise(settings.database_path)
    ingest_financial_data(settings)

    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_financials.csv"
    df = pd.read_csv(data_path)
    alp_2023 = df[(df["ticker"] == "ALP") & (df["fiscal_year"] == 2023)].iloc[0]
    expected_adjusted_net_income = alp_2023["net_income"] + alp_2023["non_recurring_expense"] + 0.5 * alp_2023["stock_compensation"]

    facts = database.fetch_financial_facts(settings.database_path, ticker="ALP")
    values = {fact.metric: fact.value for fact in facts if fact.fiscal_year == 2023}
    assert values["adjusted_net_income"] == expected_adjusted_net_income

