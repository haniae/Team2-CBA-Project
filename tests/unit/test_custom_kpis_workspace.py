from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from finanlyzeos_chatbot import custom_kpis
from finanlyzeos_chatbot.analytics_workspace import DataSourcePreferencesManager
from finanlyzeos_chatbot.custom_kpis import CustomKPICalculator, KPIIntentParser
from finanlyzeos_chatbot.kpi_lookup import KPIDefinitionLookup
from finanlyzeos_chatbot.database import initialise


def _seed_metric_snapshots(db_path: Path, ticker: str, metric: str, value: float, year: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO metric_snapshots (
                ticker, metric, period, start_year, end_year, value, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker.upper(),
                metric,
                f"FY{year}",
                year,
                year,
                value,
                "edgar",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def test_custom_kpi_creation_canonicalises_formula(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Contribution Margin",
        formula="(Revenue - NetIncome) / Revenue",
        parameter_schema={"defaults": {"fiscal_year": 2024}},
        data_preferences_id="pref-sec",
    )

    assert "revenue" in kpi.formula
    assert "net_income" in kpi.formula
    assert kpi.metadata["original_formula"] == "(Revenue - NetIncome) / Revenue"
    assert kpi.metadata["canonical_formula"] == kpi.formula
    assert "canonical_inputs" in kpi.metadata
    bindings = kpi.metadata.get("bindings", [])
    assert any(binding["canonical_metric"] == "revenue" for binding in bindings)
    assert kpi.metadata.get("data_preferences_id") == "pref-sec"


def test_custom_kpi_calculation_respects_source_preferences(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Margin",
        formula="(Revenue - NetIncome) / Revenue",
    )

    _seed_metric_snapshots(Path(db_path), "AAPL", "revenue", 100.0, 2024)
    _seed_metric_snapshots(Path(db_path), "AAPL", "net_income", 20.0, 2024)

    sec_result = calculator.calculate_kpi(
        kpi.kpi_id,
        "AAPL",
        fiscal_year=2024,
        source_preferences=["sec"],
    )
    assert pytest.approx(sec_result.value, rel=1e-6) == 0.8
    assert sec_result.metadata["source_preferences"] == ["sec"]
    assert not sec_result.error

    secondary_result = calculator.calculate_kpi(
        kpi.kpi_id,
        "AAPL",
        fiscal_year=2024,
        source_preferences=["secondary"],
    )
    assert secondary_result.error is not None


def test_custom_kpi_calculation_applies_saved_preferences(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))
    prefs = DataSourcePreferencesManager(Path(db_path))

    preference = prefs.create(
        user_id="default",
        name="SEC only",
        source_order=["sec"],
    )

    kpi = calculator.create_kpi(
        user_id="default",
        name="Contribution Margin",
        formula="(Revenue - NetIncome) / Revenue",
        data_preferences_id=preference.preference_id,
    )

    _seed_metric_snapshots(Path(db_path), "AAPL", "revenue", 100.0, 2024)
    _seed_metric_snapshots(Path(db_path), "AAPL", "net_income", 20.0, 2024)

    result = calculator.calculate_kpi(
        kpi.kpi_id,
        "AAPL",
        fiscal_year=2024,
    )

    assert pytest.approx(result.value, rel=1e-6) == 0.8
    assert result.metadata["source_preferences"] == ["sec"]
    assert result.metadata["applied_data_preferences_id"] == preference.preference_id


def test_kpi_definition_lookup_returns_formula():
    lookup = KPIDefinitionLookup()
    result = lookup.lookup("EBITDA Margin")
    assert result is not None
    assert "revenue" in result.formula.lower()


def test_ensure_kpi_from_lookup_creates_definition(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.ensure_kpi_from_lookup("default", "EBITDA Margin")
    assert kpi is not None
    assert "ebitda margin" in kpi.name.lower()

    _seed_metric_snapshots(Path(db_path), "AAPL", "revenue", 100.0, 2024)
    _seed_metric_snapshots(Path(db_path), "AAPL", "ebitda", 25.0, 2024)

    result = calculator.calculate_kpi(kpi.kpi_id, "AAPL", fiscal_year=2024)
    assert result.value is not None
    assert pytest.approx(result.value, rel=1e-6) == 0.25
    assert result.metadata.get("definition_source")


def test_calculate_kpi_missing_period_message(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Margin",
        formula="(Revenue - NetIncome) / Revenue",
    )

    result = calculator.calculate_kpi(kpi.kpi_id, "TSLA", fiscal_year=2024)
    assert result.error is not None
    assert "FY2024 data not ingested yet" in result.error


def test_custom_kpi_rejects_unknown_metric(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    with pytest.raises(ValueError, match="Unknown metrics"):
        calculator.create_kpi(
            user_id="default",
            name="Invalid KPI",
            formula="Revenue + MadeUpMetric",
        )


def test_custom_kpi_rejects_self_reference(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    with pytest.raises(ValueError, match="cannot reference itself"):
        calculator.create_kpi(
            user_id="default",
            name="Recurring",
            formula="Recurring + 1",
        )


def test_custom_kpi_group_metadata(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Operating Spread",
        formula="Revenue - CostOfRevenue, unit percent, group Profitability",
    )

    assert kpi.metadata.get("group") == "Profitability"
    assert kpi.to_dict()["group"] == "Profitability"
    assert kpi.unit == "pct"


def test_kpi_intent_handles_define_metric():
    parser = KPIIntentParser()
    intent = parser.detect("define metric Custom Spread = Revenue - NetIncome")
    assert intent is not None
    assert intent.get("action") == "create"
    definition = intent.get("definition")
    assert definition is not None
    assert definition.formula == "Revenue - NetIncome"


def test_kpi_intent_handles_custom_margin_metric():
    parser = KPIIntentParser()
    intent = parser.detect("Define custom margin metric Gross Efficiency = GrossProfit / Revenue")
    assert intent is not None
    assert intent.get("action") == "create"
    definition = intent.get("definition")
    assert definition is not None
    assert definition.formula == "GrossProfit / Revenue"


def test_custom_kpi_alias_resolution(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Net Debt Coverage",
        formula="(CashAndCashEquivalents + ShortTermInvestments) / TotalDebt",
    )

    assert set(kpi.inputs) == {
        "CashAndCashEquivalents",
        "ShortTermInvestments",
        "TotalDebt",
    }
    assert "cash_and_cash_equivalents" in kpi.formula
    assert "short_term_investments" in kpi.formula
    assert "total_debt" in kpi.formula


@pytest.mark.skipif(custom_kpis._NUMEXPR is None, reason="numexpr not available")
def test_custom_kpi_uses_numexpr_when_available(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))
    calculator = CustomKPICalculator(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Simple Sum",
        formula="Revenue + NetIncome",
    )

    _seed_metric_snapshots(Path(db_path), "AAPL", "revenue", 80.0, 2024)
    _seed_metric_snapshots(Path(db_path), "AAPL", "net_income", 20.0, 2024)

    result = calculator.calculate_kpi(kpi.kpi_id, "AAPL", fiscal_year=2024)
    assert pytest.approx(result.value, rel=1e-6) == 100.0

