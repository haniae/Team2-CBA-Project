from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from finanlyzeos_chatbot.custom_kpis import CustomKPICalculator
from finanlyzeos_chatbot.template_processor import TemplateProcessor
from finanlyzeos_chatbot.database import initialise


def _seed_metric(db_path: Path, ticker: str, metric: str, value: float, year: int) -> None:
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


def test_analysis_template_render_with_data_preferences(tmp_path):
    db_path = tmp_path / "workspace.db"
    initialise(Path(db_path))

    calculator = CustomKPICalculator(Path(db_path))
    processor = TemplateProcessor(Path(db_path))

    kpi = calculator.create_kpi(
        user_id="default",
        name="Return On Sales",
        formula="NetIncome / Revenue",
    )

    preference = processor.create_data_preferences(
        user_id="default",
        name="SEC only",
        source_order=["sec"],
    )

    template = processor.create_analysis_template(
        user_id="default",
        name="Profitability Template",
        kpi_ids=[kpi.kpi_id],
        data_preferences_id=preference["preference_id"],
        parameter_schema={"defaults": {"fiscal_year": 2023}},
    )

    _seed_metric(Path(db_path), "MSFT", "revenue", 200.0, 2023)
    _seed_metric(Path(db_path), "MSFT", "net_income", 40.0, 2023)

    render = processor.render_analysis_template(
        template_id=template["template_id"],
        tickers=["MSFT"],
        parameters={"fiscal_year": 2023},
    )

    assert render["template"]["template_id"] == template["template_id"]
    assert render["data_preferences"]["source_order"] == ["sec"]
    msft_results = render["results"]["MSFT"]
    assert len(msft_results) == 1
    assert msft_results[0]["kpi_id"] == kpi.kpi_id
    assert msft_results[0]["fiscal_year"] == 2023
    assert pytest.approx(msft_results[0]["value"], rel=1e-6) == 0.2

