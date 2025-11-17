"""Batch ingest a ticker universe via the live data pipeline."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from finanlyzeos_chatbot import AnalyticsEngine, load_settings
from finanlyzeos_chatbot.data_ingestion import ingest_live_tickers
from finanlyzeos_chatbot.data_sources import EdgarClient
from finanlyzeos_chatbot.ticker_universe import load_ticker_universe


RATE_LIMIT_SECONDS = 1.0
MAX_RETRIES = 3
YEARS_BACK = 6

# Some S&P constituents have recently rebranded or delisted. Provide explicit aliases
# so ingestion keeps rolling instead of aborting on missing CIK lookups.
TICKER_ALIASES: dict[str, str] = {
    "CDAY": "DAY",   # Workday rebrand
    "FISV": "FI",    # Fiserv rebrand
    "PXD": "XOM",    # Acquired by Exxon Mobil
    "ANSS": "ANSS",  # Placeholder so we can track resolution status
    "DFS": "DFS",
    "MRO": "MRO",
}


class _NoopYahooClient:
    """Stub Yahoo client to bypass quote fetching during large backfills."""

    @staticmethod
    def fetch_quotes(tickers: Sequence[str]) -> list:
        return []


def _load_tickers(universe: str, *, settings) -> tuple[list[str], list[str]]:
    """Return (ingestable_tickers, skipped_tickers) for the requested universe."""
    tickers = load_ticker_universe(universe)

    edgar = EdgarClient(
        base_url=settings.edgar_base_url,
        user_agent=settings.sec_api_user_agent,
        cache_dir=settings.cache_dir,
        timeout=settings.http_request_timeout,
        min_interval=0.2,
    )
    mapping = edgar.ticker_map()

    ingestable: list[str] = []
    skipped: list[str] = []
    for raw in tickers:
        if raw in mapping:
            ingestable.append(raw)
            continue
        alias = TICKER_ALIASES.get(raw)
        if alias and alias in mapping:
            ingestable.append(alias)
            continue
        skipped.append(raw)

    return ingestable, skipped


def _chunk(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch-ingest a ticker universe.")
    parser.add_argument(
        "--universe",
        default="sp500",
        help="Ticker universe key defined in ticker_universe.py (default: sp500).",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=5,
        help="Number of tickers to ingest per API call (default: 5, keep low to avoid timeouts).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=YEARS_BACK,
        help="How many fiscal years of facts to request (default: 6).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=RATE_LIMIT_SECONDS,
        help="Seconds to pause between batches (default: 1.0).",
    )
    args = parser.parse_args()

    settings = load_settings()
    tickers, skipped = _load_tickers(args.universe, settings=settings)

    print(f"Batch ingestion started at {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")
    print(f"Universe {args.universe}: {len(tickers)} tickers to ingest, {len(skipped)} skipped.")
    if skipped:
        print("Skipped tickers (missing CIK or deprecated):", ", ".join(sorted(skipped)))

    failures: dict[str, str] = {}
    successes: dict[str, int] = {}

    yahoo_stub = _NoopYahooClient()

    for batch in _chunk(tickers, max(1, args.batch)):
        time.sleep(max(args.sleep, 0.0))
        tickers_str = ", ".join(batch)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                report = ingest_live_tickers(
                    settings,
                    batch,
                    years=args.years,
                    yahoo_client=yahoo_stub,
                )
            except Exception as exc:  # pragma: no cover - network or SEC failure
                for ticker in batch:
                    failures[ticker] = str(exc)
                print(f"[FAIL] {tickers_str} attempt {attempt}: {exc}")
                if attempt == MAX_RETRIES:
                    break
                time.sleep(max(args.sleep * 2, 0.5))
                continue
            else:
                loaded = report.records_loaded
                print(f"[OK]   {tickers_str}: loaded {loaded} records")
                for ticker in report.companies:
                    successes[ticker] = loaded
                    failures.pop(ticker, None)
                break

    print("Refreshing derived metrics …")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("Metrics refreshed.")

    summary = {
        "ingested": sorted(successes.keys()),
        "skipped": skipped,
        "failures": failures,
    }
    Path("batch_ingest_summary.json").write_text(json.dumps(summary, indent=2))

    if failures:
        print("\nFailures:")
        for ticker, message in failures.items():
            print(f"- {ticker}: {message}")
    else:
        print("\nAll batches completed without fatal errors.")


if __name__ == "__main__":  # pragma: no cover - script entry point
    main()
