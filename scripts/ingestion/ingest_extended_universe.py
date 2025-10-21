#!/usr/bin/env python
"""Ingest a custom universe with extended history."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List

from benchmarkos_chatbot import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers
from benchmarkos_chatbot.ticker_universe import load_ticker_file, load_ticker_universe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest an extended ticker universe into the BenchmarkOS datastore.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--universe", help="Predefined universe key (e.g. sp500).")
    group.add_argument(
        "--universe-file",
        type=Path,
        help="Path to a newline-delimited ticker list.",
    )
    parser.add_argument("--years", type=int, default=20, help="Number of fiscal years to load.")
    parser.add_argument("--chunk-size", type=int, default=25, help="Tickers per ingestion batch.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between batches.")
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=Path(".ingestion_progress_extended.json"),
        help="Checkpoint file path.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoint instead of starting fresh.",
    )
    return parser.parse_args()


def load_tickers(args: argparse.Namespace) -> tuple[str, List[str]]:
    if args.universe_file:
        tickers = load_ticker_file(args.universe_file)
        label = args.universe_file.stem
    else:
        universe_key = args.universe or "sp500"
        tickers = load_ticker_universe(universe_key)
        label = universe_key
    return label, sorted(set(tickers))


def main() -> None:
    args = parse_args()
    label, tickers = load_tickers(args)
    progress_file = args.progress_file

    completed = set()
    if args.resume and progress_file.exists():
        completed.update(t for t in progress_file.read_text().splitlines() if t)

    todo = [ticker for ticker in tickers if ticker not in completed]
    print(f"Loaded '{label}' with {len(tickers)} tickers; {len(todo)} remaining.")
    if not todo:
        print("Nothing to ingest – all tickers already processed.")
        return

    settings = load_settings()
    total_batches = (len(todo) + args.chunk_size - 1) // args.chunk_size
    failures: list[tuple[str, str]] = []

    for batch_index in range(total_batches):
        start = batch_index * args.chunk_size
        chunk = todo[start : start + args.chunk_size]
        print(f"[{batch_index + 1}/{total_batches}] ingesting {len(chunk)} tickers: {chunk}")
        try:
            report = ingest_live_tickers(settings, chunk, years=args.years)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! batch failed: {exc}")
            failures.extend((ticker, str(exc)) for ticker in chunk)
            continue

        for ticker in report.companies:
            completed.add(ticker)

        progress_file.write_text("\n".join(sorted(completed)))
        print(
            "  - loaded {count} records for {tickers}".format(
                count=report.records_loaded,
                tickers=", ".join(report.companies),
            )
        )

        if args.sleep:
            time.sleep(args.sleep)

    if failures:
        print("\nTickers that failed to ingest:")
        for ticker, reason in failures:
            print(f"  {ticker}: {reason}")
    else:
        print("\nAll batches ingested successfully.")

    print("Refreshing derived metrics …")
    AnalyticsEngine(settings).refresh_metrics(force=True)
    print("Done.")


if __name__ == "__main__":
    main()
