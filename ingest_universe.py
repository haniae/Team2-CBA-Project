"""Utility to ingest large ticker universes via the BenchmarkOS pipeline."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Iterable, List

from benchmarkos_chatbot import AnalyticsEngine, load_settings
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers
from benchmarkos_chatbot.ticker_universe import load_ticker_universe, available_universes

DEFAULT_PROGRESS_FILE = Path.cwd() / ".ingestion_progress.json"


def chunked(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    """Yield ``size`` sized chunks from *iterable*."""

    chunk: List[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def load_progress(progress_file: Path) -> set[str]:
    """Read the ingest progress checkpoint file if present."""
    if not progress_file.exists():
        return set()
    try:
        data = json.loads(progress_file.read_text())
        return set(data.get("completed", []))
    except json.JSONDecodeError:
        return set()


def save_progress(progress_file: Path, completed: set[str]) -> None:
    """Persist the current ingest checkpoint state."""
    progress_file.write_text(json.dumps({"completed": sorted(completed)}, indent=2))


def ingest_universe(
    *,
    universe: str,
    years: int,
    chunk_size: int,
    sleep_seconds: float,
    progress_file: Path,
    resume: bool,
) -> None:
    """Iterate through a universe of tickers, ingesting each."""
    settings = load_settings()
    tickers = load_ticker_universe(universe)
    completed = load_progress(progress_file) if resume else set()

    todo = [ticker for ticker in tickers if ticker not in completed]
    total = len(tickers)

    print(f"Loaded universe '{universe}' with {total} tickers.")
    if completed:
        print(f"Resuming ingestion; {len(completed)} tickers already ingested.")
    if not todo:
        print("Nothing to do.")
        return

    failures: List[tuple[str, str]] = []
    total_chunks = math.ceil(len(todo) / chunk_size)

    for chunk_index, chunk in enumerate(chunked(todo, chunk_size), start=1):
        print(f"[{chunk_index}/{total_chunks}] Ingesting {len(chunk)} tickers: {chunk}")
        try:
            report = ingest_live_tickers(settings, chunk, years=years)
        except Exception as exc:  # noqa: BLE001 - keep the run going
            print(f"  ! Failed chunk {chunk}: {exc}")
            for ticker in chunk:
                failures.append((ticker, str(exc)))
            continue

        for ticker in report.companies:
            completed.add(ticker)
        save_progress(progress_file, completed)
        print(
            "  - Loaded {count} facts covering {tickers}".format(
                count=report.records_loaded,
                tickers=", ".join(report.companies),
            )
        )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    if failures:
        print("\nSome tickers failed to ingest:")
        for ticker, reason in failures:
            print(f"  - {ticker}: {reason}")
    else:
        print("\nAll tickers ingested successfully.")

    print("Refreshing cached metrics ...")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("Done.")
    engine.refresh_metrics(force=True)
    print("Done.")


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments for universe ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest a predefined ticker universe into the BenchmarkOS datastore.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--universe",
        default="sp500",
        choices=available_universes(),
        help="Ticker universe to ingest.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of fiscal years to pull when ingesting.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25,
        help="Number of tickers to ingest per batch call.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds to sleep between chunks to respect rate limits.",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=DEFAULT_PROGRESS_FILE,
        help="Location to store ingestion progress for resuming.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing progress file instead of starting fresh.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    """CLI entry point for large-scale universe ingestion runs."""
    args = parse_args(argv or sys.argv[1:])
    ingest_universe(
        universe=args.universe,
        years=args.years,
        chunk_size=args.chunk_size,
        sleep_seconds=args.sleep,
        progress_file=args.progress_file,
        resume=args.resume,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
