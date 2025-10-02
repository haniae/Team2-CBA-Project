"""Ingest tickers listed in a file via the BenchmarkOS pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmarkos_chatbot import load_settings
from benchmarkos_chatbot.data_ingestion import ingest_live_tickers
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest tickers from a file and refresh analytics cache."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a text file with one ticker per line (commas also supported).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of fiscal years to pull per ticker (default: 5)",
    )
    return parser.parse_args()


def load_tickers(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Ticker file not found: {path}")

    contents = path.read_text(encoding="utf-8")
    raw_tokens = contents.replace(",", "\n").splitlines()
    tickers = [token.strip().upper() for token in raw_tokens if token.strip()]
    if not tickers:
        raise ValueError("No tickers found in the supplied file.")
    return tickers


def main() -> None:
    args = parse_args()
    tickers = load_tickers(args.path)
    print(f"Ingesting {len(tickers)} tickers from {args.path}...")

    settings = load_settings()
    report = ingest_live_tickers(settings, tickers, years=args.years)
    AnalyticsEngine(settings).refresh_metrics(force=True)

    companies = ", ".join(report.companies)
    print(
        f"Ingested {report.records_loaded} normalised facts covering: {companies}."
    )
    print("Analytics cache refreshed. Metrics are now available via the chatbot.")


if __name__ == "__main__":
    main()
