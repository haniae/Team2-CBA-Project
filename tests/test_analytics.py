"""Unit tests for the analytics helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from benchmarkos_chatbot import analytics
from benchmarkos_chatbot.data_sources import PriceBar


def build_facts() -> dict:
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 200},
                            {"fy": 2021, "form": "10-K", "val": 220},
                            {"fy": 2022, "form": "10-K", "val": 250},
                            {"fy": 2023, "form": "10-K", "val": 300},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 40},
                            {"fy": 2021, "form": "10-K", "val": 44},
                            {"fy": 2022, "form": "10-K", "val": 50},
                            {"fy": 2023, "form": "10-K", "val": 60},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 60},
                            {"fy": 2021, "form": "10-K", "val": 70},
                            {"fy": 2022, "form": "10-K", "val": 75},
                            {"fy": 2023, "form": "10-K", "val": 90},
                        ]
                    }
                },
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {"fy": 2022, "form": "10-K", "val": 3.5},
                            {"fy": 2023, "form": "10-K", "val": 4.2},
                        ]
                    }
                },
            }
        }
    }


def sample_prices() -> list[PriceBar]:
    base = datetime(2019, 1, 1, tzinfo=timezone.utc)
    return [
        PriceBar(timestamp=base, close=100.0),
        PriceBar(timestamp=base.replace(year=2020), close=110.0),
        PriceBar(timestamp=base.replace(year=2021), close=120.0),
        PriceBar(timestamp=base.replace(year=2022), close=130.0),
        PriceBar(timestamp=base.replace(year=2023), close=150.0),
    ]


def test_compute_financial_metrics():
    metrics = analytics.compute_financial_metrics(build_facts())
    assert metrics["revenue_series"][-1].value == 300
    expected_cagr = ((300 / 200) ** (1 / 3)) - 1
    assert round(metrics["revenue_cagr_3y"], 4) == round(expected_cagr, 4)
    assert round(metrics["net_margin"], 4) == round(60 / 300, 4)
    assert round(metrics["operating_margin"], 4) == round(90 / 300, 4)


def test_compute_price_metrics():
    metrics = analytics.compute_price_metrics(sample_prices())
    assert metrics["total_return"] > 0
    assert metrics["annualised_volatility"] is not None
    assert metrics["cagr"] is not None
    assert metrics["max_drawdown"] <= 0


def test_render_summary_includes_filings():
    metrics = analytics.compute_financial_metrics(build_facts())
    price_metrics = analytics.compute_price_metrics(sample_prices())

    profile = analytics.CompanyProfile(
        ticker="AAPL", name="Apple Inc.", cik="0000320193"
    )
    report = analytics.render_summary(
        profile,
        metrics,
        price_metrics,
        [
            {
                "form": "10-K",
                "filing_date": "2023-10-01",
                "report_date": "2023-09-30",
                "accession_number": "0000320193-23-000010",
            }
        ],
    )

    assert "Recent SEC Filings" in report
    assert "Revenue CAGR" in report
    assert "Apple Inc." in report
