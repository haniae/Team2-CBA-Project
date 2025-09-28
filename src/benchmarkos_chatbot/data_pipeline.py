"""Orchestration layer that connects data sources and analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Sequence

from . import analytics
from .data_sources import SecEdgarClient, YahooFinanceClient


DEFAULT_COMPANIES: Dict[str, analytics.CompanyProfile] = {
    "AAPL": analytics.CompanyProfile(
        ticker="AAPL", name="Apple Inc.", cik="0000320193"
    ),
    "MSFT": analytics.CompanyProfile(
        ticker="MSFT", name="Microsoft Corporation", cik="0000789019"
    ),
    "GOOGL": analytics.CompanyProfile(
        ticker="GOOGL", name="Alphabet Inc.", cik="0001652044"
    ),
    "AMZN": analytics.CompanyProfile(
        ticker="AMZN", name="Amazon.com, Inc.", cik="0001018724"
    ),
}


@dataclass
class CompanyRegistry:
    companies: Dict[str, analytics.CompanyProfile] = field(
        default_factory=lambda: DEFAULT_COMPANIES.copy()
    )

    def lookup(self, ticker: str) -> analytics.CompanyProfile:
        key = ticker.upper()
        if key not in self.companies:
            raise KeyError(
                f"Ticker {ticker!r} is not in the BenchmarkOS registry. "
                "Extend CompanyRegistry.companies to add it."
            )
        return self.companies[key]


@dataclass
class BenchmarkOSDataPipeline:
    sec_client: SecEdgarClient
    market_client: YahooFinanceClient
    registry: CompanyRegistry = field(default_factory=CompanyRegistry)

    @classmethod
    def create_default(cls) -> "BenchmarkOSDataPipeline":
        return cls(sec_client=SecEdgarClient(), market_client=YahooFinanceClient())

    def build_financial_report(self, ticker: str) -> str:
        profile = self.registry.lookup(ticker)

        facts = self.sec_client.company_facts(profile.cik)
        financial_metrics = analytics.compute_financial_metrics(facts)

        price_history = self.market_client.price_history(profile.ticker)
        price_metrics = analytics.compute_price_metrics(price_history)

        filings: Sequence[Mapping[str, str]] = [
            filing.__dict__ for filing in self.sec_client.recent_filings(profile.cik)
        ]

        return analytics.render_summary(
            profile=profile,
            financial_metrics=financial_metrics,
            price_metrics=price_metrics,
            filings=filings,
        )

