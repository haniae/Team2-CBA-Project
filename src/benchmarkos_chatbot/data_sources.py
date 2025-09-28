"""Data acquisition helpers that rely only on the Python standard library."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = (
    "BenchmarkOSChatbot/0.1 (+https://benchmarkos.example; contact@example.com)"
)


@dataclass(frozen=True)
class FilingMetadata:
    form: str
    filing_date: Optional[str]
    report_date: Optional[str]
    accession_number: Optional[str]


@dataclass(frozen=True)
class PriceBar:
    timestamp: datetime
    close: float


class SecEdgarClient:
    """Lightweight wrapper around the SEC's public XBRL APIs."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.user_agent = user_agent

    @staticmethod
    def _normalise_cik(cik: str | int) -> str:
        value = str(cik).strip()
        if not value.isdigit():
            raise ValueError("CIK values must be numeric strings")
        return f"{int(value):010d}"

    def _get_json(self, url: str) -> Dict:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - trusted host
            data = response.read()
        return json.loads(data.decode("utf-8"))

    def company_facts(self, cik: str | int) -> Dict:
        normalised = self._normalise_cik(cik)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{normalised}.json"
        return self._get_json(url)

    def submissions(self, cik: str | int) -> Dict:
        normalised = self._normalise_cik(cik)
        url = f"https://data.sec.gov/submissions/CIK{normalised}.json"
        return self._get_json(url)

    def recent_filings(
        self, cik: str | int, form_types: Iterable[str] = ("10-K", "10-Q")
    ) -> List[FilingMetadata]:
        data = self.submissions(cik)
        forms = data.get("filings", {}).get("recent", {})
        form_list = forms.get("form", [])
        filing_dates = forms.get("filingDate", [])
        report_dates = forms.get("reportDate", [])
        accession_numbers = forms.get("accessionNumber", [])

        result: List[FilingMetadata] = []
        for idx, form in enumerate(form_list):
            if form not in form_types:
                continue
            filing_date = filing_dates[idx] if idx < len(filing_dates) else None
            report_date = report_dates[idx] if idx < len(report_dates) else None
            accession_number = (
                accession_numbers[idx] if idx < len(accession_numbers) else None
            )
            result.append(
                FilingMetadata(
                    form=form,
                    filing_date=filing_date,
                    report_date=report_date,
                    accession_number=accession_number,
                )
            )
        return result


class YahooFinanceClient:
    """Fetch daily adjusted close prices from the Yahoo Finance chart API."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.user_agent = user_agent

    def price_history(
        self,
        ticker: str,
        years: int = 5,
        interval: str = "1d",
    ) -> List[PriceBar]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=365 * years)
        params = urlencode(
            {
                "period1": int(start.timestamp()),
                "period2": int(end.timestamp()),
                "interval": interval,
                "includePrePost": "false",
            }
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{params}"
        request = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - trusted host
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover - network error path
            raise RuntimeError(f"Yahoo Finance request failed: {exc}") from exc

        result = payload.get("chart", {}).get("result") or []
        if not result:
            raise ValueError(f"No market data returned for {ticker!r}")

        series = result[0]
        timestamps = series.get("timestamp", [])
        adj_close = (
            series.get("indicators", {})
            .get("adjclose", [{}])[0]
            .get("adjclose", [])
        )

        price_bars: List[PriceBar] = []
        for ts, close in zip(timestamps, adj_close):
            if close is None:
                continue
            price_bars.append(
                PriceBar(timestamp=datetime.fromtimestamp(ts, tz=timezone.utc), close=float(close))
            )

        if not price_bars:
            raise ValueError(f"No usable market data returned for {ticker!r}")

        return price_bars

