"""External data source clients for BenchmarkOS ingestion."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import requests
import random

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilingRecord:
    """Normalised representation of an SEC filing."""

    cik: str
    ticker: str
    accession_number: str
    form_type: str
    filed_at: datetime
    period_of_report: Optional[date]
    acceptance_datetime: Optional[datetime]
    data: Mapping[str, Any]
    source: str = "edgar"


@dataclass(frozen=True)
class FinancialFact:
    """Normalised numeric data point extracted from regulatory filings."""

    cik: str
    ticker: str
    metric: str
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]
    period: str
    value: Optional[float]
    unit: Optional[str]
    source: str
    source_filing: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    adjusted: bool
    adjustment_note: Optional[str]
    ingested_at: datetime
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class MarketQuote:
    """Normalised real-time quote."""

    ticker: str
    price: float
    currency: Optional[str]
    volume: Optional[float]
    timestamp: datetime
    source: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class AuditEvent:
    """Simple audit trail record for ingestion actions."""

    ticker: str
    event_type: str
    entity_id: Optional[str]
    details: Mapping[str, Any]
    created_at: datetime
    created_by: str


DEFAULT_FACT_CONCEPTS: Sequence[str] = (
    "us-gaap:Revenues",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:NetSales",
    "us-gaap:SalesRevenueNet",
    "us-gaap:SalesRevenueGoodsNet",
    "us-gaap:NetIncomeLoss",
    "us-gaap:ProfitLoss",
    "us-gaap:OperatingIncomeLoss",
    "us-gaap:GrossProfit",
    "us-gaap:Assets",
    "us-gaap:AssetsCurrent",
    "us-gaap:Liabilities",
    "us-gaap:LiabilitiesCurrent",
    "us-gaap:StockholdersEquity",
    "us-gaap:CashAndCashEquivalentsAtCarryingValue",
    "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "us-gaap:NetCashProvidedByUsedInFinancingActivities",
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    "us-gaap:DepreciationAndAmortization",
    "us-gaap:EarningsBeforeInterestAndTaxes",
    "us-gaap:IncomeTaxExpenseBenefit",
    "us-gaap:LongTermDebtNoncurrent",
    "us-gaap:LongTermDebtCurrent",
    "us-gaap:ShortTermBorrowings",
    "us-gaap:CommonStockSharesOutstanding",
    "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
    "us-gaap:DividendsDeclaredPerCommonShare",
    "us-gaap:DividendsPerShareDeclared",
    "us-gaap:PaymentsOfDividendsCommonStock",
    "us-gaap:PaymentsForRepurchaseOfCommonStock",
    "us-gaap:PaymentsForRepurchaseOfCommonStockAndPreferredStock",
    "us-gaap:FreeCashFlow",
    "us-gaap:EarningsPerShareDiluted",
    "us-gaap:EarningsPerShareBasic",
    "us-gaap:InterestExpense",
)

METRIC_ALIASES = {
    "us-gaap:Revenues": "revenue",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "us-gaap:NetSales": "revenue",
    "us-gaap:SalesRevenueNet": "revenue",
    "us-gaap:SalesRevenueGoodsNet": "revenue",
    "us-gaap:NetIncomeLoss": "net_income",
    "us-gaap:ProfitLoss": "net_income",
    "us-gaap:OperatingIncomeLoss": "operating_income",
    "us-gaap:GrossProfit": "gross_profit",
    "us-gaap:Assets": "total_assets",
    "us-gaap:AssetsCurrent": "current_assets",
    "us-gaap:Liabilities": "total_liabilities",
    "us-gaap:LiabilitiesCurrent": "current_liabilities",
    "us-gaap:StockholdersEquity": "shareholders_equity",
    "us-gaap:CashAndCashEquivalentsAtCarryingValue": "cash_and_cash_equivalents",
    "us-gaap:NetCashProvidedByUsedInOperatingActivities": "cash_from_operations",
    "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations": "cash_from_operations",
    "us-gaap:NetCashProvidedByUsedInOperatingActivitiesDiscontinuedOperations": "cash_from_operations",
    "us-gaap:NetCashProvidedByUsedInFinancingActivities": "cash_from_financing",
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditures",
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipmentContinuingOperations": "capital_expenditures",
    "us-gaap:PaymentsToAcquireProductiveAssets": "capital_expenditures",
    "us-gaap:DepreciationAndAmortization": "depreciation_and_amortization",
    "us-gaap:EarningsBeforeInterestAndTaxes": "ebit",
    "us-gaap:IncomeTaxExpenseBenefit": "income_tax_expense",
    "us-gaap:LongTermDebtNoncurrent": "long_term_debt",
    "us-gaap:LongTermDebtCurrent": "long_term_debt_current",
    "us-gaap:ShortTermBorrowings": "short_term_debt",
    "us-gaap:CommonStockSharesOutstanding": "shares_outstanding",
    "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding": "weighted_avg_diluted_shares",
    "us-gaap:DividendsDeclaredPerCommonShare": "dividends_per_share",
    "us-gaap:DividendsPerShareDeclared": "dividends_per_share",
    "us-gaap:PaymentsOfDividendsCommonStock": "dividends_paid",
    "us-gaap:PaymentsForRepurchaseOfCommonStock": "share_repurchases",
    "us-gaap:PaymentsForRepurchaseOfCommonStockAndPreferredStock": "share_repurchases",
    "us-gaap:FreeCashFlow": "free_cash_flow",
    "us-gaap:EarningsPerShareDiluted": "eps_diluted",
    "us-gaap:EarningsPerShareBasic": "eps_basic",
    "us-gaap:InterestExpense": "interest_expense",
}


FORM_PRIORITY = {
    "10-K/A": 6,
    "10-K": 5,
    "20-F/A": 5,
    "20-F": 5,
    "40-F/A": 5,
    "40-F": 5,
    "10-Q/A": 4,
    "10-Q": 4,
    "8-K": 2,
}

UNIT_MULTIPLIERS: Dict[str, float] = {
    "USD": 1.0,
    "USD$": 1.0,
    "USDm": 1_000_000.0,
    "USDmm": 1_000_000.0,
    "USDth": 1_000.0,
    "USDThousands": 1_000.0,
    "shares": 1.0,
    "sharesBasic": 1.0,
    "sharesDiluted": 1.0,
}

UNIT_PRIORITY: Dict[str, int] = {
    "USD": 5,
    "USD$": 5,
    "USDm": 4,
    "USDmm": 4,
    "USDth": 3,
    "USDThousands": 3,
    "shares": 5,
    "sharesBasic": 4,
    "sharesDiluted": 4,
}

ALLOWED_FORMS = {
    "10-K",
    "10-K/A",
    "10-Q",
    "10-Q/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
}

ALLOWED_PERIODS = {"FY", "CY", "FYTD", "Q4", "Q4YTD"}


def _pad_cik(cik: str | int) -> str:
    """Left-pad CIK identifiers to the expected SEC format."""
    return f"{int(cik):010d}"


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse date strings returned by APIs into date objects."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            LOGGER.debug("Unable to parse date %s", value)
            return None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse timestamp strings into timezone-aware datetime objects."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            LOGGER.debug("Unable to parse datetime %s", value)
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_bloomberg_field_payload(field_data, fields: Sequence[str]) -> Dict[str, Any]:
    """Normalise Bloomberg quote payloads to a flat dict."""
    payload: Dict[str, Any] = {}
    for field_name in fields:
        try:
            if not field_data.hasElement(field_name):
                payload[field_name] = None
                continue
            element = field_data.getElement(field_name)
            try:
                value = element.getValue()
            except Exception:  # pragma: no cover - defensive
                try:
                    value = element.toString()
                except Exception:
                    value = None
        except Exception:
            payload[field_name] = None
            continue
        if hasattr(value, "toPython"):
            try:
                value = value.toPython()
            except Exception:  # pragma: no cover - fallback
                value = str(value)
        payload[field_name] = value
    return payload


def _canonical_metric(concept: str) -> str:
    """Map incoming metric aliases onto canonical metric names."""
    return METRIC_ALIASES.get(concept, concept.lower())


class EdgarClient:
    """Lightweight wrapper around the SEC EDGAR data endpoints."""

    TICKER_LIST_PATH = "/files/company_tickers.json"

    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        cache_dir: Path,
        timeout: float = 30.0,
        min_interval: float = 0.12,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialise the client with credentials, endpoints, and limits."""
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.min_interval = min_interval
        self.cache_dir = cache_dir
        self.session = session or requests.Session()
        self._last_request = 0.0
        self._ticker_cache: Optional[Dict[str, str]] = None

    def _headers(self) -> Dict[str, str]:
        """Return HTTP headers required for external data requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def _maybe_throttle(self) -> None:
        """Sleep when necessary to respect upstream rate limits."""
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _request(self, path: str, *, params: Optional[Mapping[str, Any]] = None) -> Any:
        """Perform an HTTP request and bubble up meaningful errors."""
        self._maybe_throttle()
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._last_request = time.monotonic()
            return response.json()
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404 and self.base_url.rstrip('/') != "https://www.sec.gov":
                fallback_url = f"https://www.sec.gov{path}"
                fallback = self.session.get(
                    fallback_url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                fallback.raise_for_status()
                self._last_request = time.monotonic()
                self.base_url = "https://www.sec.gov"
                return fallback.json()
            raise
        except requests.HTTPError as exc:
            if response.status_code == 404 and path == self.TICKER_LIST_PATH:
                fallback_url = f"https://www.sec.gov{path}"
                fallback_response = self.session.get(
                    fallback_url,
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                fallback_response.raise_for_status()
                self._last_request = time.monotonic()
                self.base_url = "https://www.sec.gov"
                return fallback_response.json()
            raise


    def ticker_map(self, *, force_refresh: bool = False) -> Dict[str, str]:
        """Return a mapping of tickers to CIK identifiers."""
        if self._ticker_cache is not None and not force_refresh:
            return self._ticker_cache
        cache_file = self.cache_dir / "edgar_tickers.json"
        if cache_file.exists() and not force_refresh:
            try:
                cached = json.loads(cache_file.read_text())
                if isinstance(cached, dict):
                    mapping = {str(ticker).upper(): _pad_cik(cik) for ticker, cik in cached.items()}
                else:
                    mapping = {entry["ticker"].upper(): _pad_cik(entry["cik_str"]) for entry in cached}
                self._ticker_cache = mapping
                return mapping
            except Exception:  # pragma: no cover - cache corruption fallback
                LOGGER.warning("Failed to load cached ticker map; refreshing.")
        payload = self._request(self.TICKER_LIST_PATH)
        if isinstance(payload, dict):
            entries = payload.values()
        else:
            entries = payload
        mapping = {
            str(entry["ticker"]).upper(): _pad_cik(entry["cik_str"])
            for entry in entries
            if entry.get("ticker") and entry.get("cik_str")
        }
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(mapping, indent=2))
        self._ticker_cache = mapping
        return mapping

    def cik_for_ticker(self, ticker: str) -> str:
        """Lookup the CIK for a supplied ticker symbol."""
        mapping = self.ticker_map()
        try:
            return mapping[ticker.upper()]
        except KeyError as exc:
            raise KeyError(f"Ticker {ticker} not recognised by EDGAR") from exc

    def company_submissions(self, cik: str) -> Mapping[str, Any]:
        """Fetch the list of recent SEC submissions for a company."""
        cik = _pad_cik(cik)
        return self._request(f"/submissions/CIK{cik}.json")

    def company_facts(self, cik: str) -> Mapping[str, Any]:
        """Retrieve detailed company facts from the SEC API."""
        cik = _pad_cik(cik)
        return self._request(f"/api/xbrl/companyfacts/CIK{cik}.json")

    def fetch_filings(
        self,
        ticker: str,
        *,
        forms: Optional[Sequence[str]] = None,
        limit: int = 50,
    ) -> List[FilingRecord]:
        """Yield filing metadata for tickers over a time range."""
        cik = self.cik_for_ticker(ticker)
        data = self.company_submissions(cik)
        recent = data.get("filings", {}).get("recent", {})
        filings: List[FilingRecord] = []
        for index, accession in enumerate(recent.get("accessionNumber", [])[:limit]):
            form = recent.get("form", [None])[index]
            if forms and form not in forms:
                continue
            filed = recent.get("filingDate", [None])[index]
            reported = recent.get("reportDate", [None])[index]
            accepted = recent.get("acceptanceDateTime", [None])[index]
            filings.append(
                FilingRecord(
                    cik=cik,
                    ticker=ticker.upper(),
                    accession_number=str(accession),
                    form_type=str(form),
                    filed_at=_parse_datetime(filed) or datetime.now(timezone.utc),
                    period_of_report=_parse_date(reported),
                    acceptance_datetime=_parse_datetime(accepted),
                    data={
                        "company": data.get("name"),
                        "form": form,
                        "fileNumber": recent.get("fileNumber", [None])[index],
                        "items": recent.get("primaryDocDescription", [None])[index],
                    },
                )
            )
        return filings

    def fetch_facts(
        self,
        ticker: str,
        *,
        concepts: Sequence[str] = DEFAULT_FACT_CONCEPTS,
        years: int = 10,
    ) -> List[FinancialFact]:
        """Yield raw fact entries for a company and metric set."""
        cik = self.cik_for_ticker(ticker)
        payload = self.company_facts(cik)
        taxonomy_map = payload.get("facts", {})
        cutoff_year = datetime.now(timezone.utc).year - years + 1
        concept_filter = set(concepts) if concepts else None
        best: Dict[Tuple[str, Optional[int], Optional[str]], Tuple[Tuple, FinancialFact]] = {}

        def _multiplier_for(unit: str) -> Optional[float]:
            """Determine conversion multipliers for incoming fact units."""
            if unit in UNIT_MULTIPLIERS:
                return UNIT_MULTIPLIERS[unit]
            return None

        def _score_entry(entry: Mapping[str, Any], unit: str) -> Tuple:
            """Compute a ranking score that favours recent, high-quality filings."""
            segment_score = 1 if not entry.get("segment") else 0
            form = (entry.get("form") or "").upper()
            form_score = FORM_PRIORITY.get(form, 1 if form else 0)
            filed = entry.get("filed") or ""
            period_end = entry.get("end") or ""
            unit_score = UNIT_PRIORITY.get(unit, 0)
            return (segment_score, form_score, filed, period_end, unit_score)

        for taxonomy, concepts_map in taxonomy_map.items():
            if not isinstance(concepts_map, Mapping):
                continue
            for tag, data in concepts_map.items():
                if not isinstance(data, Mapping):
                    continue
                concept_key = f"{taxonomy}:{tag}"
                if concept_filter and concept_key not in concept_filter:
                    # allow implicit aliases even if not explicitly requested
                    if concept_key not in METRIC_ALIASES:
                        continue
                metric_name = _canonical_metric(concept_key)
                units = data.get("units", {})
                if not isinstance(units, Mapping):
                    continue
                for unit, entries in units.items():
                    multiplier = _multiplier_for(unit)
                    if multiplier is None:
                        continue
                    for entry in entries or []:
                        if not isinstance(entry, Mapping):
                            continue
                        if entry.get("segment"):
                            continue
                        form = (entry.get("form") or "").upper()
                        if form and form not in ALLOWED_FORMS:
                            continue
                        fiscal_year = entry.get("fy")
                        if fiscal_year is not None and fiscal_year < cutoff_year:
                            continue
                        fiscal_period = entry.get("fp")
                        period_code = fiscal_period.upper() if isinstance(fiscal_period, str) else None
                        if period_code and period_code not in ALLOWED_PERIODS:
                            continue
                        value_raw = entry.get("val")
                        try:
                            numeric_value = (
                                float(value_raw) * multiplier if value_raw is not None else None
                            )
                        except (TypeError, ValueError):
                            continue
                        period_label = _derive_period_label(fiscal_year, fiscal_period)
                        score = _score_entry(entry, unit)
                        key = (metric_name, fiscal_year, fiscal_period)
                        existing = best.get(key)
                        if existing and existing[0] >= score:
                            continue
                        best[key] = (
                            score,
                            FinancialFact(
                                cik=cik,
                                ticker=ticker.upper(),
                                metric=metric_name,
                                fiscal_year=fiscal_year,
                                fiscal_period=fiscal_period,
                                period=period_label,
                                value=numeric_value,
                                unit=unit,
                                source="edgar",
                                source_filing=entry.get("accn"),
                                period_start=_parse_datetime(entry.get("start")),
                                period_end=_parse_datetime(entry.get("end")),
                                adjusted=form.endswith("/A"),
                                adjustment_note=entry.get("form"),
                                ingested_at=datetime.now(timezone.utc),
                                raw=entry,
                            ),
                        )

        return [fact for _, fact in best.values()]


def _derive_period_label(fy: Optional[int], fiscal_period: Optional[str]) -> str:
    """Generate a human-readable period label for quote history."""
    if fy is None:
        return fiscal_period or "unknown"
    if fiscal_period and fiscal_period.upper() not in {"FY", "CY"}:
        return f"FY{fy}{fiscal_period.upper()}"
    return f"FY{fy}"


class YahooFinanceClient:
    """Client for Yahoo Finance real-time quote API."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        batch_size: int = 50,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialise the client with credentials, endpoints, and limits."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = max(1, batch_size)
        self.session = session or requests.Session()

    def fetch_quotes(self, tickers: Sequence[str]) -> List[MarketQuote]:
        """Fetch batch quotes from the configured market data provider."""
        if not tickers:
            return []
        results: List[MarketQuote] = []
        # Perform resilient HTTP fetches with retries/backoff to handle 429s or transient 5xx
        max_attempts = 4
        base_backoff = 1.0
        for idx in range(0, len(tickers), self.batch_size):
            chunk = [ticker.upper() for ticker in tickers[idx : idx + self.batch_size]]
            params = {"symbols": ",".join(chunk)}
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                try:
                    response = self.session.get(
                        self.base_url,
                        params=params,
                        timeout=self.timeout,
                        headers={"Accept": "application/json"},
                    )
                    # If we get 429 or 5xx, raise and handle below
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
                    response.raise_for_status()
                    data = response.json()
                    for item in data.get("quoteResponse", {}).get("result", []):
                        price = item.get("regularMarketPrice")
                        if price is None:
                            continue
                        timestamp = item.get("regularMarketTime") or item.get("postMarketTime")
                        if timestamp:
                            quote_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                        else:
                            quote_time = datetime.now(timezone.utc)
                        results.append(
                            MarketQuote(
                                ticker=item.get("symbol", "").upper(),
                                price=float(price),
                                currency=item.get("currency"),
                                volume=float(item.get("regularMarketVolume")) if item.get("regularMarketVolume") is not None else None,
                                timestamp=quote_time,
                                source="yahoo",
                                raw=item,
                            )
                        )
                    # success, break out of retry loop
                    break
                except requests.HTTPError as exc:
                    status = None
                    try:
                        status = exc.response.status_code  # type: ignore[attr-defined]
                    except Exception:
                        status = None
                    # For rate limiting or server errors, backoff and retry
                    if status == 429 or (status and 500 <= status < 600):
                        sleep_for = base_backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                        LOGGER.warning(
                            "Yahoo fetch batch %s attempt %d/%d got status %s, sleeping %.2fs",
                            ",".join(chunk[:3]) + ("..." if len(chunk) > 3 else ""),
                            attempt,
                            max_attempts,
                            status,
                            sleep_for,
                        )
                        time.sleep(sleep_for)
                        continue
                    # For other HTTP errors, don't retry
                    LOGGER.exception("Yahoo fetch failed: %s", exc)
                    break
                except Exception as exc:  # network/connect/json errors
                    sleep_for = base_backoff * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    LOGGER.warning(
                        "Yahoo fetch batch %s attempt %d/%d error: %s; sleeping %.2fs",
                        ",".join(chunk[:3]) + ("..." if len(chunk) > 3 else ""),
                        attempt,
                        max_attempts,
                        exc,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    continue
        return results


class BloombergClient:
    """Thin wrapper for Bloomberg REF data. Optional dependency."""

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialise the client with credentials, endpoints, and limits."""
        self.timeout = timeout
        try:
            import blpapi  # type: ignore
        except ImportError as exc:  # pragma: no cover - requires Bloomberg environment
            raise RuntimeError(
                "blpapi package is not available. Install Bloomberg's Python SDK and set ENABLE_BLOOMBERG=1."
            ) from exc
        self._blpapi = blpapi
        session_options = blpapi.SessionOptions()
        if host:
            session_options.setServerHost(host)
        if port:
            session_options.setServerPort(port)
        self._session = blpapi.Session(session_options)
        if not self._session.start():
            raise RuntimeError("Failed to start Bloomberg API session")
        if not self._session.openService("//blp/refdata"):
            raise RuntimeError("Failed to open Bloomberg refdata service")
        self._service = self._session.getService("//blp/refdata")

    def fetch_quotes(self, tickers: Sequence[str], fields: Optional[Sequence[str]] = None) -> List[MarketQuote]:
        """Fetch batch quotes from the configured market data provider."""
        if not tickers:
            return []
        fields = list(fields or ("PX_LAST", "VOLUME", "CRNCY", "LAST_UPDATE"))
        request = self._service.createRequest("ReferenceDataRequest")
        for ticker in tickers:
            request.append("securities", ticker)
        for field in fields:
            request.append("fields", field)
        self._session.sendRequest(request)

        quotes: List[MarketQuote] = []
        done = False
        while not done:
            ev = self._session.nextEvent(int(self.timeout * 1000))
            if ev.eventType() in (self._blpapi.Event.RESPONSE, self._blpapi.Event.PARTIAL_RESPONSE):
                for msg in ev:
                    security_data_array = msg.getElement("securityData")
                    for security_idx in range(security_data_array.numValues()):
                        security_data = security_data_array.getValue(security_idx)
                        ticker = security_data.getElementAsString("security")
                        field_data = security_data.getElement("fieldData")
                        price = field_data.getElementAsFloat("PX_LAST") if field_data.hasElement("PX_LAST") else None
                        if price is None:
                            continue
                        volume = field_data.getElementAsFloat("VOLUME") if field_data.hasElement("VOLUME") else None
                        currency = field_data.getElementAsString("CRNCY") if field_data.hasElement("CRNCY") else None
                        if field_data.hasElement("LAST_UPDATE"):
                            last_update = field_data.getElementAsDatetime("LAST_UPDATE").toPython()
                            if last_update.tzinfo is None:
                                last_update = last_update.replace(tzinfo=timezone.utc)
                            timestamp = last_update.astimezone(timezone.utc)
                        else:
                            timestamp = datetime.now(timezone.utc)
                        quotes.append(
                            MarketQuote(
                                ticker=ticker.upper(),
                                price=float(price),
                                currency=currency,
                                volume=float(volume) if volume is not None else None,
                                timestamp=timestamp,
                                source="bloomberg",
                                raw=_extract_bloomberg_field_payload(field_data, fields),
                            )
                        )
            if ev.eventType() == self._blpapi.Event.RESPONSE:
                done = True
        return quotes

    def close(self) -> None:
        """Close any open HTTP session resources."""
        try:
            self._session.stop()
        except Exception:
            LOGGER.debug("Error stopping Bloomberg session", exc_info=True)
