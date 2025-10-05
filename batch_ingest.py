"""Batch ingest a curated list of tickers via the live data pipeline."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable
import time

from benchmarkos_chatbot import AnalyticsEngine, load_settings
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers

RATE_LIMIT_SECONDS = 2.0
MAX_RETRIES = 3
TICKERS: Iterable[str] = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "GOOG",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "BRK-B",
    "UNH",
    "JNJ",
    "V",
    "PG",
    "XOM",
    "JPM",
    "MA",
    "HD",
    "MRK",
    "BAC",
    "LLY",
    "ABBV",
    "PFE",
    "PEP",
    "KO",
    "AVGO",
    "COST",
    "DIS",
    "CSCO",
    "TMO",
    "ACN",
    "CRM",
    "CVX",
    "ABT",
    "NKE",
    "DHR",
    "MCD",
    "LIN",
    "WMT",
    "TXN",
    "INTC",
    "PM",
    "NEE",
    "HON",
    "AMD",
    "AMGN",
    "QCOM",
    "UPS",
    "RTX",
    "MS",
    "IBM",
    "SBUX",
    "CAT",
    "GS",
    "NOW",
    "LOW",
    "ADP",
    "BKNG",
    "BLK",
    "INTU",
    "GE",
    "BA",
    "USB",
    "TJX",
    "MDT",
    "SO",
    "MO",
    "CI",
    "LMT",
    "ISRG",
    "BDX",
    "CB",
    "T",
    "SYK",
    "ADI",
    "DE",
    "GILD",
    "MMC",
    "SCHW",
    "PLD",
    "EL",
    "FIS",
    "C",
    "SPGI",
    "ZTS",
    "REGN",
    "AXP",
    "ICE",
    "GM",
    "VRTX",
    "CSX",
    "PGR",
    "APD",
    "ETN",
    "EOG",
    "MU",
    "CL",
    "ORLY",
    "PAYX",
    "FDX",
    "LRCX",
    "MMM",
    "DUK"

]
YEARS_BACK = 5


def main() -> None:
    """Kick off the batch ingest loop for predefined tickers.

    The function walks through the `TICKERS` list, runs live ingestion with
    backoff/retry logic, and prints a summary of successes/failures before
    exiting.
    """
    settings = load_settings()

    print(f"Batch ingestion started at {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")
    failures: dict[str, str] = {}

    for ticker in TICKERS:
        time.sleep(RATE_LIMIT_SECONDS)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                report = ingest_live_tickers(settings, [ticker], years=YEARS_BACK)
            except Exception as exc:  # pragma: no cover - network failure path
                failures[ticker] = str(exc)
                print(f"[FAIL] {ticker} attempt {attempt}: {exc}")
                if attempt == MAX_RETRIES:
                    break
                time.sleep(RATE_LIMIT_SECONDS * 2)
                continue
            else:
                print(f"[OK]   {ticker}: loaded {report.records_loaded} facts")
                failures.pop(ticker, None)
                break

    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("Metrics refreshed.")

    if failures:
        print("\nFailures:")
        for ticker, message in failures.items():
            print(f"- {ticker}: {message}")
    else:
        print("\nAll tickers ingested successfully.")


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
