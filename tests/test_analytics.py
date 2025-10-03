"""Tests for the analytics engine."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchmarkos_chatbot import AnalyticsEngine, BenchmarkOSChatbot
from benchmarkos_chatbot import tasks as task_module
from benchmarkos_chatbot.config import Settings
from benchmarkos_chatbot.data_ingestion import ingest_financial_data
from benchmarkos_chatbot import database


@pytest.fixture()
def prepared_engine(tmp_path: Path) -> AnalyticsEngine:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    database.initialise(settings.database_path)
    ingest_financial_data(settings)
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    return engine


def test_phase_one_metrics_match_expected(prepared_engine: AnalyticsEngine) -> None:
    records = prepared_engine.get_metrics("ALP", phase="phase1")
    assert records, "Phase 1 metrics should be available for ALP."
    metrics = {record.metric: record for record in records}

    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_financials.csv"
    df = pd.read_csv(data_path)
    alp = df[df["ticker"] == "ALP"].sort_values("fiscal_year")

    revenue_cagr = ((alp.iloc[-1]["revenue"] / alp.iloc[-4]["revenue"]) ** (1 / 3)) - 1
    assert metrics["revenue_cagr_3y"].value == pytest.approx(revenue_cagr, rel=1e-4)

    adjusted_ebitda = alp.iloc[-1]["ebitda"] + alp.iloc[-1]["non_recurring_expense"]
    ebitda_margin = adjusted_ebitda / alp.iloc[-1]["revenue"]
    assert metrics["adjusted_ebitda_margin"].value == pytest.approx(ebitda_margin, rel=1e-6)

    adjusted_net_income = (
        alp.iloc[-1]["net_income"]
        + alp.iloc[-1]["non_recurring_expense"]
        + 0.5 * alp.iloc[-1]["stock_compensation"]
    )
    roe = adjusted_net_income / alp.iloc[-1]["total_equity"]
    assert metrics["return_on_equity"].value == pytest.approx(roe, rel=1e-6)


def test_lookup_ticker_accepts_company_names(prepared_engine: AnalyticsEngine) -> None:
    assert prepared_engine.lookup_ticker("Alpha Technologies") == "ALP"
    assert prepared_engine.lookup_ticker("Alpha") == "ALP"
    assert prepared_engine.lookup_ticker("Bravo Retail") == "BRV"


def test_chatbot_metrics_accepts_company_name(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    task_module._default_manager = None
    bot = BenchmarkOSChatbot.create(settings)
    try:
        reply = bot.ask("metrics for Alpha Technologies phase 1")
    finally:
        task_module._default_manager = None
    assert "Alpha Technologies" in reply
    assert "Phase1 KPIs" in reply



def test_chatbot_compare_accepts_company_names(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    task_module._default_manager = None
    bot = BenchmarkOSChatbot.create(settings)
    try:
        reply = bot.ask("compare Alpha Technologies vs Bravo Retail phase 2")
    finally:
        task_module._default_manager = None
    assert "Benchmarking ALP, BRV" in reply
    assert "Phase 2 KPIs" in reply


def test_scenario_generation_records_results(prepared_engine: AnalyticsEngine) -> None:
    summary = prepared_engine.run_scenario(
        "ALP",
        scenario_name="stress",
        revenue_growth_delta=0.05,
        ebitda_margin_delta=0.02,
        multiple_delta=0.1,
    )

    assert "stress" in summary.scenario_name
    assert summary.metrics["projected_revenue"] > 0

    # Scenario results should be persisted.
    stored = database.fetch_scenario_results(
        prepared_engine.settings.database_path, ticker="ALP", scenario_name=summary.scenario_name
    )
    assert stored, "Scenario results should be stored in the database."


def test_generate_summary_returns_structured_text(prepared_engine: AnalyticsEngine) -> None:
    summary = prepared_engine.generate_summary("BRV")
    assert "BRV" in summary
    assert "Revenue CAGR" in summary


def test_chatbot_metrics_suggests_candidates(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    task_module._default_manager = None
    bot = BenchmarkOSChatbot.create(settings)
    try:
        reply = bot.ask("metrics for Alpha Technologes")
    finally:
        task_module._default_manager = None
    assert "Try one of" in reply
    assert "Alpha Technologies" in reply


def test_chatbot_compare_suggests_when_unresolved(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    task_module._default_manager = None
    bot = BenchmarkOSChatbot.create(settings)
    try:
        reply = bot.ask("compare Alphaa vs Bravo Retail phase 2")
    finally:
        task_module._default_manager = None
    assert "Try one of these tickers" in reply
    assert "Alpha Technologies" in reply


def test_chatbot_scenario_suggests_candidates(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "chat.sqlite3",
        llm_provider="local",
        openai_model="local",
        sec_api_user_agent=None,
    )
    task_module._default_manager = None
    bot = BenchmarkOSChatbot.create(settings)
    try:
        reply = bot.ask("scenario Alphaa revenue +5% margin +1%")
    finally:
        task_module._default_manager = None
    assert "Try one of" in reply
    assert "Alpha" in reply


