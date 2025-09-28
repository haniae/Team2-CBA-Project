"""Integration tests for the BenchmarkOS data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from benchmarkos_chatbot import analytics
from benchmarkos_chatbot.data_pipeline import BenchmarkOSDataPipeline, CompanyRegistry
from benchmarkos_chatbot.data_sources import FilingMetadata, PriceBar


def sample_facts() -> dict:
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 100},
                            {"fy": 2021, "form": "10-K", "val": 120},
                            {"fy": 2022, "form": "10-K", "val": 140},
                            {"fy": 2023, "form": "10-K", "val": 180},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 20},
                            {"fy": 2021, "form": "10-K", "val": 24},
                            {"fy": 2022, "form": "10-K", "val": 28},
                            {"fy": 2023, "form": "10-K", "val": 36},
                        ]
                    }
                },
                "OperatingIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2020, "form": "10-K", "val": 30},
                            {"fy": 2021, "form": "10-K", "val": 32},
                            {"fy": 2022, "form": "10-K", "val": 40},
                            {"fy": 2023, "form": "10-K", "val": 50},
                        ]
                    }
                },
            }
        }
    }


@dataclass
class FakeSecClient:
    facts: dict
    filings: list[FilingMetadata]

    def company_facts(self, cik: str) -> dict:  # pragma: no cover - simple proxy
        assert cik == "0000320193"
        return self.facts

    def recent_filings(self, cik: str):
        assert cik == "0000320193"
        return self.filings


@dataclass
class FakeMarketClient:
    prices: list[PriceBar]

    def price_history(self, ticker: str, *_, **__):
        assert ticker == "AAPL"
        return self.prices


def test_build_financial_report():
    sec_client = FakeSecClient(
        facts=sample_facts(),
        filings=[
            FilingMetadata(
                form="10-K",
                filing_date="2023-10-31",
                report_date="2023-09-30",
                accession_number="0000320193-23-000010",
            )
        ],
    )
    base = datetime(2019, 1, 1, tzinfo=timezone.utc)
    market_client = FakeMarketClient(
        prices=[
            PriceBar(timestamp=base, close=100.0),
            PriceBar(timestamp=base.replace(year=2020), close=110.0),
            PriceBar(timestamp=base.replace(year=2021), close=120.0),
            PriceBar(timestamp=base.replace(year=2022), close=130.0),
            PriceBar(timestamp=base.replace(year=2023), close=150.0),
        ]
    )

    registry = CompanyRegistry(
        companies={
            "AAPL": analytics.CompanyProfile(
                ticker="AAPL", name="Apple Inc.", cik="0000320193"
            )
        }
    )

    pipeline = BenchmarkOSDataPipeline(
        sec_client=sec_client,
        market_client=market_client,
        registry=registry,
    )

    report = pipeline.build_financial_report("AAPL")
    assert "Apple Inc." in report
    assert "Revenue CAGR" in report
    assert "Recent SEC Filings" in report


def test_unknown_ticker_raises():
    pipeline = BenchmarkOSDataPipeline(
        sec_client=FakeSecClient(sample_facts(), []),
        market_client=FakeMarketClient(
            prices=[
                PriceBar(
                    timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc), close=100.0
                ),
                PriceBar(
                    timestamp=datetime(2020, 1, 2, tzinfo=timezone.utc), close=101.0
                ),
            ]
        ),
    )

    try:
        pipeline.build_financial_report("TSLA")
    except KeyError as exc:
        assert "TSLA" in str(exc)
    else:  # pragma: no cover - ensure the exception is raised
        raise AssertionError("Expected KeyError for unknown ticker")
