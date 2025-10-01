"""Live data acquisition helpers for SEC and Yahoo Finance."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class YahooQuote:
    ticker: str
    company_name: str
    sector: str
    price: Optional[float]
    market_cap: Optional[float]
    enterprise_value: Optional[float]
    shares_outstanding: Optional[float]


class YahooFinanceFetcher:
    """Fetch structured financial data using Yahoo Finance."""

    def __init__(self) -> None:
        self._cache: Dict[str, yf.Ticker] = {}

    def _get_ticker(self, ticker: str) -> yf.Ticker:
        if ticker not in self._cache:
            self._cache[ticker] = yf.Ticker(ticker)
        return self._cache[ticker]

    def fetch_quote(self, ticker: str) -> YahooQuote:
        ticker_obj = self._get_ticker(ticker)
        info = ticker_obj.info or {}
        fast_info = getattr(ticker_obj, "fast_info", {}) or {}

        def _safe_get(mapping, key):
            value = mapping.get(key)
            if value is None:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        price = _safe_get(fast_info, "last_price") or _safe_get(info, "regularMarketPrice")
        market_cap = _safe_get(info, "marketCap")
        enterprise_value = _safe_get(info, "enterpriseValue")
        shares_outstanding = _safe_get(fast_info, "shares_outstanding") or _safe_get(
            info, "sharesOutstanding"
        )

        return YahooQuote(
            ticker=ticker.upper(),
            company_name=info.get("longName") or info.get("shortName") or ticker.upper(),
            sector=info.get("sector") or "Unknown",
            price=price,
            market_cap=market_cap,
            enterprise_value=enterprise_value,
            shares_outstanding=shares_outstanding,
        )

    def fetch_financial_frames(self, ticker: str) -> Dict[str, pd.DataFrame]:
        ticker_obj = self._get_ticker(ticker)
        frames = {
            "income": ticker_obj.financials.transpose(),
            "balance": ticker_obj.balance_sheet.transpose(),
            "cashflow": ticker_obj.cashflow.transpose(),
        }
        cleaned: Dict[str, pd.DataFrame] = {}
        for name, frame in frames.items():
            if frame is None or frame.empty:
                cleaned[name] = pd.DataFrame()
            else:
                frame.index = pd.to_datetime(frame.index)
                cleaned[name] = frame
        return cleaned


class SECFetcher:
    """Fetch company facts from the SEC XBRL API."""

    def __init__(self, user_agent: str | None = None) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent
                or "BenchmarkOSChatbot/0.1 (+https://github.com/BenchmarkOS/chatbot)",
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def get_company_facts(self, ticker: str, *, cik: str | None = None) -> dict | None:
        cik_code = cik or self._infer_cik_from_yahoo(ticker)
        if cik_code is None:
            return None
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_code}.json"
        response = self._session.get(url, timeout=30)
        if response.status_code != 200:
            logger.warning("SEC companyfacts request failed for %s: %s", ticker, response.status_code)
            return None
        try:
            return response.json()
        except ValueError:
            logger.exception("Failed to decode JSON for ticker %s", ticker)
            return None

    def _infer_cik_from_yahoo(self, ticker: str) -> Optional[str]:
        try:
            info = yf.Ticker(ticker).info
        except Exception:  # pragma: no cover - network failures
            logger.exception("Unable to fetch Yahoo info for %s", ticker)
            return None
        cik_val = info.get("cik")
        if cik_val is None:
            return None
        try:
            return str(int(cik_val)).zfill(10)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def extract_fact(series: dict | None, concept: str, unit: str = "USD") -> Dict[int, float]:
        if not series:
            return {}
        concept_data = series.get("facts", {}).get("us-gaap", {}).get(concept)
        if not concept_data:
            return {}
        unit_data = concept_data.get("units", {}).get(unit, [])
        results: Dict[int, float] = {}
        for item in unit_data:
            try:
                end_date = datetime.fromisoformat(item["end"])
                year = end_date.year
                value = float(item["val"])
            except (KeyError, ValueError, TypeError):
                continue
            results[year] = value
        return results


def build_financial_dataset(
    ticker: str,
    *,
    years: int = 5,
    sec_fetcher: Optional[SECFetcher] = None,
    yahoo_fetcher: Optional[YahooFinanceFetcher] = None,
) -> pd.DataFrame:
    """Construct a normalised multi-year dataset for a ticker."""

    yahoo_fetcher = yahoo_fetcher or YahooFinanceFetcher()
    quote = yahoo_fetcher.fetch_quote(ticker)
    frames = yahoo_fetcher.fetch_financial_frames(ticker)

    periods: List[pd.Timestamp] = sorted(
        set(frames["income"].index)
        | set(frames["balance"].index)
        | set(frames["cashflow"].index)
    )
    if years:
        periods = periods[-years:]

    if not periods:
        raise ValueError(f"No financial periods available for ticker {ticker}.")

    def get_value(frame_name: str, period: pd.Timestamp, keys: Iterable[str], default: float = 0.0) -> float:
        frame = frames[frame_name]
        if frame.empty:
            return default
        for key in keys:
            if key in frame.columns:
                try:
                    value = frame.loc[period, key]
                except KeyError:
                    continue
                if pd.notna(value):
                    return float(value)
        return default

    working_capital_cache: Dict[pd.Timestamp, Optional[float]] = {}

    rows: List[Dict[str, float | str | int]] = []
    for period in periods:
        fiscal_year = period.year
        revenue = get_value("income", period, ["Total Revenue", "Operating Revenue", "Revenues"])
        ebitda = get_value("income", period, ["Ebitda", "EBITDA"])
        net_income = get_value("income", period, ["Net Income", "Net Income Applicable To Common Shares", "NetIncome"])
        operating_income = get_value("income", period, ["Operating Income", "OperatingIncomeLoss"])
        total_equity = get_value("balance", period, ["Total Stockholder Equity", "Total Equity Gross Minority Interest"])
        total_assets = get_value("balance", period, ["Total Assets"])
        dividends_paid = abs(get_value("cashflow", period, ["Dividends Paid", "Cash Dividends Paid"], 0.0))
        free_cash_flow = get_value("cashflow", period, ["Free Cash Flow"]) or (
            get_value("cashflow", period, ["Total Cash From Operating Activities"]) + get_value("cashflow", period, ["Capital Expenditures"])
        )
        operating_cash_flow = get_value("cashflow", period, ["Total Cash From Operating Activities", "Cash Provided By Operating Activities"])
        capital_expenditure = abs(get_value("cashflow", period, ["Capital Expenditures", "Purchases Of Property Plant And Equipment"]))
        cash = get_value("balance", period, ["Cash", "Cash And Cash Equivalents", "Cash And Short Term Investments"])
        total_debt = get_value("balance", period, ["Total Debt", "Short Long Term Debt Total", "Long Term Debt"])
        share_buybacks = abs(get_value("cashflow", period, ["Common Stock Repurchased", "Common Stock Issued"], 0.0))
        stock_compensation = get_value("cashflow", period, ["Stock Based Compensation", "Share Based Compensation"], 0.0)

        if period not in working_capital_cache:
            current_assets = get_value("balance", period, ["Total Current Assets"], 0.0)
            current_liabilities = get_value("balance", period, ["Total Current Liabilities"], 0.0)
            working_capital_cache[period] = current_assets - current_liabilities
        working_capital = working_capital_cache[period] or 0.0

        rows.append(
            {
                "ticker": quote.ticker,
                "company_name": quote.company_name,
                "sector": quote.sector,
                "fiscal_year": fiscal_year,
                "revenue": revenue,
                "ebitda": ebitda,
                "net_income": net_income,
                "operating_income": operating_income,
                "total_equity": total_equity,
                "total_assets": total_assets,
                "shares_outstanding": quote.shares_outstanding or 0.0,
                "dividends_paid": dividends_paid,
                "free_cash_flow": free_cash_flow,
                "operating_cash_flow": operating_cash_flow,
                "capital_expenditure": capital_expenditure,
                "cash": cash,
                "total_debt": total_debt,
                "enterprise_value": quote.enterprise_value or 0.0,
                "market_cap": quote.market_cap or 0.0,
                "price": quote.price or 0.0,
                "working_capital": working_capital,
                "share_buybacks": share_buybacks,
                "non_recurring_expense": 0.0,
                "stock_compensation": stock_compensation,
            }
        )

    df = pd.DataFrame(rows)

    if sec_fetcher is not None:
        facts = sec_fetcher.get_company_facts(ticker)
        if facts:
            adjustments = SECFetcher.extract_fact(facts, "RestructuringCosts")
            for idx, row in df.iterrows():
                if row["fiscal_year"] in adjustments:
                    df.at[idx, "non_recurring_expense"] = adjustments[row["fiscal_year"]]

    return df
