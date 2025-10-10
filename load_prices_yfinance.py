"""
Populate latest market prices using yfinance so price-based ratios populate. Optional Postgres support kicks in when PG* environment variables are supplied.
"""

from __future__ import annotations

import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import yfinance as yf

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:  # pragma: no cover
    psycopg2 = None  # type: ignore

from benchmarkos_chatbot import database
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.data_sources import MarketQuote

DEFAULT_TICKERS = "MSFT,GE,AAPL,AMZN"
MAX_RETRIES = 3
RETRY_DELAY = 5.0


class PostgresWriter:
    def __init__(self) -> None:
        self.enabled = False
        if psycopg2 is None:
            return
        host = os.getenv("PGHOST")
        if not host:
            return
        port = int(os.getenv("PGPORT", "5432"))
        dbname = os.getenv("PGDATABASE", "secdb")
        user = os.getenv("PGUSER", "postgres")
        password = os.getenv("PGPASSWORD", "")
        self._dsn = dict(host=host, port=port, dbname=dbname, user=user, password=password)
        self.enabled = True

    def __enter__(self) -> "PostgresWriter":
        if not self.enabled:
            return self
        self._conn = psycopg2.connect(**self._dsn)  # type: ignore[arg-type]
        self._conn.autocommit = True
        self._ensure_table()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self.enabled:
            return
        self._conn.close()  # type: ignore[attr-defined]

    def _ensure_table(self) -> None:
        if not self.enabled:
            return
        with self._conn.cursor() as cur:  # type: ignore[attr-defined]
            cur.execute("CREATE SCHEMA IF NOT EXISTS sec")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sec.prices_daily (
                    ticker TEXT NOT NULL,
                    date DATE NOT NULL,
                    close DOUBLE PRECISION,
                    adj_close DOUBLE PRECISION,
                    volume BIGINT,
                    PRIMARY KEY (ticker, date)
                )
                """
            )

    def upsert(self, rows: Sequence[Tuple[str, str, Optional[float], Optional[float], Optional[int]]]) -> None:
        if not self.enabled or not rows:
            return
        with self._conn.cursor() as cur:  # type: ignore[attr-defined]
            execute_batch(
                cur,
                """
                INSERT INTO sec.prices_daily (ticker, date, close, adj_close, volume)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (ticker, date) DO UPDATE
                SET close = EXCLUDED.close,
                    adj_close = EXCLUDED.adj_close,
                    volume = EXCLUDED.volume
                """,
                rows,
                page_size=200,
            )


def fetch_price(ticker: str) -> Optional[Tuple[float, Optional[float], datetime]]:
    y_ticker = yf.Ticker(ticker)
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            history = y_ticker.history(period="1mo", interval="1d", auto_adjust=False)
        except Exception as exc:
            last_error = exc
            time.sleep(RETRY_DELAY * attempt)
            continue
        if history.empty:
            last_error = ValueError("Empty price history")
            time.sleep(RETRY_DELAY * attempt)
            continue
        row = history.iloc[-1]
        close = row.get("Close")
        if close is None or (isinstance(close, float) and math.isnan(close)):
            last_error = ValueError("Missing close price")
            time.sleep(RETRY_DELAY * attempt)
            continue
        timestamp = row.name.to_pydatetime()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        volume_val = row.get("Volume")
        if volume_val is not None and isinstance(volume_val, float) and math.isnan(volume_val):
            volume_val = None
        return float(close), (float(volume_val) if volume_val is not None else None), timestamp
    if last_error:
        print(f"[WARN] Failed {ticker}: {last_error}")
    else:
        print(f"[WARN] Failed {ticker}: unknown error")
    return None


def main() -> None:
    settings = load_settings()
    tickers_env = os.getenv("SEC_TICKERS", DEFAULT_TICKERS)
    tickers = sorted({t.strip().upper() for t in tickers_env.split(',') if t.strip()})
    if not tickers:
        raise SystemExit("SEC_TICKERS does not contain any tickers.")

    quotes: List[MarketQuote] = []
    rows: List[Tuple[str, str, Optional[float], Optional[float], Optional[int]]] = []

    print(f"[INFO] Fetching latest prices for {len(tickers)} tickers via yfinance")
    for ticker in tickers:
        captured = fetch_price(ticker)
        if not captured:
            continue
        price, volume, timestamp = captured
        quotes.append(
            MarketQuote(
                ticker=ticker,
                price=price,
                currency="USD",
                volume=volume,
                timestamp=timestamp,
                source="yfinance",
                raw={
                    "price": price,
                    "volume": volume,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
        rows.append((ticker, timestamp.date().isoformat(), price, price, int(volume) if volume else None))
        time.sleep(0.2)

    inserted = database.bulk_insert_market_quotes(settings.database_path, quotes)
    print(f"[INFO] Upserted {inserted} quotes into {Path(settings.database_path).name}")

    with PostgresWriter() as pg:
        if pg.enabled:
            pg.upsert(rows)
            print(f"[INFO] Upserted {len(rows)} rows into sec.prices_daily")
        else:
            print("[INFO] Postgres connection not supplied; skipped sec.prices_daily upsert.")

    print("[INFO] Done.")


if __name__ == "__main__":
    main()
