"""External market data helpers used by the KPI backfill pipeline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

LOGGER = logging.getLogger(__name__)


def _stooq_symbol(ticker: str) -> str:
    """Return the Stooq symbol for a US-listed ticker."""
    normalized = ticker.strip().lower()
    if not normalized:
        return ""
    # Stooq maps BRK/B style tickers by replacing '-' with ''
    normalized = normalized.replace(".", "").replace("-", "")
    return f"{normalized}.us"


def stooq_last_close(ticker: str, asof: datetime) -> Optional[float]:
    """
    Return the latest closing price from Stooq on or before ``asof``.

    Parameters
    ----------
    ticker:
        Exchange ticker symbol (e.g., ``AAPL``).
    asof:
        Anchor date for the lookup.
    """
    symbol = _stooq_symbol(ticker)
    if not symbol:
        return None
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    try:
        df = pd.read_csv(url)
    except Exception as exc:  # pragma: no cover - network dependent
        LOGGER.debug("Stooq price fetch failed for %s (%s)", ticker, exc)
        return None
    if df.empty or "Date" not in df or "Close" not in df:
        return None
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    asof_ts = pd.Timestamp(asof)
    if asof_ts.tzinfo is not None:
        asof_ts = asof_ts.tz_convert("UTC").tz_localize(None)
    if getattr(df["Date"].dt, "tz", None) is not None:
        df["Date"] = df["Date"].dt.tz_localize(None)
    df = df[df["Date"] <= asof_ts].sort_values("Date")
    if df.empty:
        return None
    try:
        return float(df["Close"].iloc[-1])
    except (TypeError, ValueError):
        return None


def yahoo_snapshot(ticker: str) -> Dict[str, Any]:
    """
    Return a combined snapshot of price, market cap, shares, EV, and 1Y history.

    The function relies on :mod:`yfinance` (no API key required) and attempts to
    provide sensible fallbacks when certain fields are unavailable.
    """
    ticker_obj = yf.Ticker(ticker)
    info: Dict[str, Any] = {}
    fast_info = getattr(ticker_obj, "fast_info", None)
    if isinstance(fast_info, dict):
        info.update(fast_info)
    elif fast_info is not None:
        info.update(getattr(fast_info, "__dict__", {}))

    static_info = getattr(ticker_obj, "info", {})
    if isinstance(static_info, dict):
        info.setdefault("last_price", static_info.get("regularMarketPrice"))
        info.setdefault("market_cap", static_info.get("marketCap"))
        info.setdefault("shares", static_info.get("sharesOutstanding"))
        info.setdefault("enterprise_value", static_info.get("enterpriseValue"))

    try:
        history = ticker_obj.history(period="1y", actions=True, auto_adjust=True)
    except Exception as exc:  # pragma: no cover - network dependent
        LOGGER.debug("Yahoo history fetch failed for %s (%s)", ticker, exc)
        history = pd.DataFrame()

    price_candidates = [
        info.get("lastPrice"),
        info.get("last_price"),
        info.get("regular_market_price"),
        info.get("regularMarketPrice"),
    ]
    if not history.empty and "Close" in history:
        price_candidates.append(history["Close"].dropna().iloc[-1])

    price = next((float(p) for p in price_candidates if isinstance(p, (int, float))), None)
    market_cap = info.get("market_cap")
    if not isinstance(market_cap, (int, float)):
        market_cap = None
    shares = info.get("shares")
    if not isinstance(shares, (int, float)):
        shares = None
    enterprise_value = info.get("enterprise_value")
    if not isinstance(enterprise_value, (int, float)):
        enterprise_value = static_info.get("enterpriseValue") if isinstance(static_info, dict) else None
    if not isinstance(enterprise_value, (int, float)):
        enterprise_value = None

    dividends = None
    if not history.empty and "Dividends" in history:
        dividends = history["Dividends"].copy()

    return {
        "price": price,
        "market_cap": float(market_cap) if market_cap is not None else None,
        "shares": float(shares) if shares is not None else None,
        "ev": float(enterprise_value) if enterprise_value is not None else None,
        "dividends": dividends,
        "history": history,
        "fetched_at": datetime.now(timezone.utc),
        "raw": info,
    }
