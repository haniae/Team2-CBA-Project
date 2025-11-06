
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from benchmarkos_chatbot import database
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.config import Settings
from benchmarkos_chatbot.data_sources import FinancialFact, MarketQuote


def _fact(ticker: str, metric: str, year: int, value: float) -> FinancialFact:
    return FinancialFact(
        cik="0000000001",
        ticker=ticker,
        company_name=f"{ticker} Inc",
        metric=metric,
        fiscal_year=year,
        fiscal_period="FY",
        period=f"FY{year}",
        value=value,
        unit="USDm",
        source="edgar",
        source_filing="0001-23-000001",
        period_start=datetime(year - 1, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(year, 12, 31, tzinfo=timezone.utc),
        adjusted=False,
        adjustment_note=None,
        ingested_at=datetime.now(timezone.utc),
        raw={},
    )


def _settings(db_path, cache_dir) -> Settings:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        database_type="sqlite",
        database_path=db_path,
        postgres_host=None,
        postgres_port=None,
        postgres_database=None,
        postgres_user=None,
        postgres_password=None,
        postgres_schema="sec",
        llm_provider="local",
        openai_model="gpt-4o-mini",
        sec_api_user_agent="unit-test/1.0",
        edgar_base_url="https://example.com",
        yahoo_quote_url="https://example.com",
        yahoo_quote_batch_size=25,
        http_request_timeout=30.0,
        max_ingestion_workers=4,
        cache_dir=cache_dir,
        enable_bloomberg=False,
        bloomberg_host=None,
        bloomberg_port=None,
        bloomberg_timeout=30.0,
    )


def test_refresh_metrics_computes_growth_and_valuation(tmp_path):
    db_path = tmp_path / "db.sqlite3"
    database.initialise(db_path)

    facts = [
        # FY2023
        _fact("TEST", "revenue", 2023, 1000.0),
        _fact("TEST", "net_income", 2023, 100.0),
        _fact("TEST", "operating_income", 2023, 150.0),
        _fact("TEST", "gross_profit", 2023, 400.0),
        _fact("TEST", "total_assets", 2023, 2000.0),
        _fact("TEST", "total_liabilities", 2023, 900.0),
        _fact("TEST", "shareholders_equity", 2023, 1100.0),
        _fact("TEST", "cash_from_operations", 2023, 130.0),
        _fact("TEST", "capital_expenditures", 2023, -30.0),
        _fact("TEST", "depreciation_and_amortization", 2023, 20.0),
        _fact("TEST", "current_assets", 2023, 500.0),
        _fact("TEST", "current_liabilities", 2023, 300.0),
        _fact("TEST", "cash_and_cash_equivalents", 2023, 200.0),
        _fact("TEST", "eps_diluted", 2023, 5.0),
        _fact("TEST", "eps_basic", 2023, 5.0),
        _fact("TEST", "shares_outstanding", 2023, 100.0),
        # FY2024
        _fact("TEST", "revenue", 2024, 1100.0),
        _fact("TEST", "net_income", 2024, 120.0),
        _fact("TEST", "operating_income", 2024, 160.0),
        _fact("TEST", "gross_profit", 2024, 440.0),
        _fact("TEST", "total_assets", 2024, 2200.0),
        _fact("TEST", "total_liabilities", 2024, 950.0),
        _fact("TEST", "shareholders_equity", 2024, 1250.0),
        _fact("TEST", "cash_from_operations", 2024, 140.0),
        _fact("TEST", "capital_expenditures", 2024, -35.0),
        _fact("TEST", "depreciation_and_amortization", 2024, 22.0),
        _fact("TEST", "current_assets", 2024, 520.0),
        _fact("TEST", "current_liabilities", 2024, 310.0),
        _fact("TEST", "cash_and_cash_equivalents", 2024, 210.0),
        _fact("TEST", "eps_diluted", 2024, 5.5),
        _fact("TEST", "eps_basic", 2024, 5.5),
        _fact("TEST", "shares_outstanding", 2024, 98.0),
        _fact("TEST", "dividends_per_share", 2024, 1.2),
        _fact("TEST", "dividends_paid", 2024, -118.0),
        _fact("TEST", "share_repurchases", 2024, -400.0),
        _fact("TEST", "long_term_debt", 2024, 420.0),
        _fact("TEST", "long_term_debt_current", 2024, 60.0),
        _fact("TEST", "short_term_debt", 2024, 30.0),
    ]

    database.bulk_upsert_financial_facts(db_path, facts)

    now = datetime.now(timezone.utc)
    database.bulk_insert_market_quotes(
        db_path,
        [
            MarketQuote(
                ticker="TEST",
                price=50.0,
                currency="USD",
                volume=1_000_000,
                timestamp=now,
                source="yahoo",
                raw={"marketCap": 5000.0, "enterpriseValue": 5300.0},
            ),
            MarketQuote(
                ticker="TEST",
                price=45.0,
                currency="USD",
                volume=1_000_000,
                timestamp=now - timedelta(days=370),
                source="yahoo",
                raw={"marketCap": 4500.0, "enterpriseValue": 4800.0},
            ),
        ],
    )

    settings = _settings(db_path, tmp_path / "cache")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)

    records = engine.get_metrics("TEST")
    latest = {record.metric: record.value for record in records if record.period == "FY2024"}

    assert pytest.approx(latest["revenue_cagr"], rel=1e-6) == 0.10
    assert pytest.approx(latest["eps_cagr"], rel=1e-6) == 0.10
    assert pytest.approx(latest["ebitda"], rel=1e-6) == 182.0
    assert pytest.approx(latest["ebitda_growth"], rel=1e-6) == pytest.approx((182.0 - 170.0) / 170.0, rel=1e-6)
    assert pytest.approx(latest["working_capital"], rel=1e-6) == 210.0
    assert pytest.approx(latest["working_capital_change"], rel=1e-6) == 0.05
    assert pytest.approx(latest["pe_ratio"], rel=1e-6) == pytest.approx(50.0 / 5.5, rel=1e-6)
    assert pytest.approx(latest["pb_ratio"], rel=1e-6) == pytest.approx(5000.0 / 1250.0, rel=1e-6)
    assert pytest.approx(latest["dividend_yield"], rel=1e-6) == pytest.approx(1.2 / 50.0, rel=1e-6)
    assert pytest.approx(latest["share_buyback_intensity"], rel=1e-6) == pytest.approx(400.0 / 5000.0, rel=1e-6)
    assert pytest.approx(latest["cash_conversion"], rel=1e-6) == pytest.approx(140.0 / 120.0, rel=1e-6)
    assert pytest.approx(latest["free_cash_flow"], rel=1e-6) == 105.0
    assert pytest.approx(latest["tsr"], rel=1e-6) == pytest.approx(((50.0 - 45.0) + 1.2) / 45.0, rel=1e-6)
    assert "roic" in latest and latest["roic"] is not None

def test_refresh_metrics_handles_alias_metrics_without_quotes(tmp_path, monkeypatch):
    db_path = tmp_path / "db.sqlite3"
    database.initialise(db_path)

    facts = [
        # FY2023 alias-heavy inputs
        _fact("ALIAS", "revenue", 2023, 1000.0),
        _fact("ALIAS", "net_income", 2023, 100.0),
        _fact("ALIAS", "clean_operating_income", 2023, 150.0),
        _fact("ALIAS", "total_assets", 2023, 2000.0),
        _fact("ALIAS", "total_equity", 2023, 1150.0),
        _fact("ALIAS", "operating_cash_flow", 2023, 120.0),
        _fact("ALIAS", "capital_expenditure", 2023, -30.0),
        _fact("ALIAS", "cash", 2023, 170.0),
        _fact("ALIAS", "shares_outstanding", 2023, 100.0),
        _fact("ALIAS", "working_capital", 2023, 200.0),
        _fact("ALIAS", "total_debt", 2023, 480.0),
        _fact("ALIAS", "price", 2023, 40.0),
        _fact("ALIAS", "market_cap", 2023, 4000.0),
        _fact("ALIAS", "enterprise_value", 2023, 4300.0),
        _fact("ALIAS", "share_buybacks", 2023, -200.0),
        _fact("ALIAS", "dividends_paid", 2023, -80.0),
        _fact("ALIAS", "adjusted_ebitda", 2023, 170.0),
        _fact("ALIAS", "normalised_free_cash_flow", 2023, 90.0),
        # FY2024 alias-heavy inputs
        _fact("ALIAS", "revenue", 2024, 1100.0),
        _fact("ALIAS", "net_income", 2024, 120.0),
        _fact("ALIAS", "clean_operating_income", 2024, 165.0),
        _fact("ALIAS", "total_assets", 2024, 2200.0),
        _fact("ALIAS", "total_equity", 2024, 1300.0),
        _fact("ALIAS", "operating_cash_flow", 2024, 140.0),
        _fact("ALIAS", "capital_expenditure", 2024, -35.0),
        _fact("ALIAS", "cash", 2024, 180.0),
        _fact("ALIAS", "shares_outstanding", 2024, 95.0),
        _fact("ALIAS", "working_capital", 2024, 220.0),
        _fact("ALIAS", "total_debt", 2024, 520.0),
        _fact("ALIAS", "price", 2024, 44.0),
        _fact("ALIAS", "market_cap", 2024, 4400.0),
        _fact("ALIAS", "enterprise_value", 2024, 4700.0),
        _fact("ALIAS", "share_buybacks", 2024, -220.0),
        _fact("ALIAS", "dividends_paid", 2024, -90.0),
        _fact("ALIAS", "adjusted_ebitda", 2024, 190.0),
        _fact("ALIAS", "normalised_free_cash_flow", 2024, 105.0),
    ]

    database.bulk_upsert_financial_facts(db_path, facts)

    monkeypatch.setattr(
        "benchmarkos_chatbot.analytics_engine.YahooFinanceClient.fetch_quotes",
        lambda self, tickers: [],
    )

    settings = _settings(db_path, tmp_path / "cache_alias")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)

    records = engine.get_metrics("ALIAS")
    latest_derived = {
        record.metric: record.value
        for record in records
        if record.period == "FY2024" and record.source == "derived"
    }
    latest_base = {
        record.metric: record.value
        for record in records
        if record.period == "FY2024" and record.source == "edgar"
    }

    for metric in ("cash_from_operations", "capital_expenditures", "cash_and_cash_equivalents", "share_repurchases"):
        assert metric in latest_base

    assert pytest.approx(latest_base["cash_from_operations"], rel=1e-6) == 140.0
    assert pytest.approx(latest_base["capital_expenditures"], rel=1e-6) == -35.0
    assert pytest.approx(latest_base["cash_and_cash_equivalents"], rel=1e-6) == 180.0
    assert pytest.approx(latest_base["share_repurchases"], rel=1e-6) == -220.0

    expected_eps_end = 120.0 / 95.0
    expected_eps_start = 100.0 / 100.0
    expected_eps_cagr = (expected_eps_end / expected_eps_start) - 1.0
    expected_revenue_cagr = (1100.0 / 1000.0) - 1.0
    expected_ebitda_growth = (190.0 - 170.0) / 170.0
    expected_pe_ratio = 44.0 / expected_eps_end
    expected_pb_ratio = 4400.0 / 1300.0
    expected_ev_ebitda = 4700.0 / 190.0
    expected_dividend_yield = (abs(-90.0) / 95.0) / 44.0
    expected_buyback_intensity = abs(-220.0) / 4400.0
    expected_cash_conversion = 140.0 / 120.0
    expected_free_cash_flow_margin = 105.0 / 1100.0
    expected_debt_to_equity = 520.0 / 1300.0

    assert pytest.approx(latest_derived["eps_cagr"], rel=1e-6) == expected_eps_cagr
    assert pytest.approx(latest_derived["revenue_cagr"], rel=1e-6) == expected_revenue_cagr
    assert pytest.approx(latest_derived["ebitda"], rel=1e-6) == 190.0
    assert pytest.approx(latest_derived["ebitda_growth"], rel=1e-6) == expected_ebitda_growth
    assert pytest.approx(latest_derived["working_capital"], rel=1e-6) == 220.0
    assert pytest.approx(latest_derived["working_capital_change"], rel=1e-6) == 0.1
    assert pytest.approx(latest_derived["pe_ratio"], rel=1e-6) == expected_pe_ratio
    assert pytest.approx(latest_derived["pb_ratio"], rel=1e-6) == expected_pb_ratio
    assert pytest.approx(latest_derived["ev_ebitda"], rel=1e-6) == expected_ev_ebitda
    assert pytest.approx(latest_derived["dividend_yield"], rel=1e-6) == expected_dividend_yield
    assert pytest.approx(latest_derived["share_buyback_intensity"], rel=1e-6) == expected_buyback_intensity
    assert pytest.approx(latest_derived["cash_conversion"], rel=1e-6) == expected_cash_conversion
    assert pytest.approx(latest_derived["free_cash_flow_margin"], rel=1e-6) == expected_free_cash_flow_margin
    assert pytest.approx(latest_derived["debt_to_equity"], rel=1e-6) == expected_debt_to_equity
