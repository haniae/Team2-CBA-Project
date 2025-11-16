#!/usr/bin/env python3
"""Batch backfill helper that cascades SEC → Yahoo/Stooq → IMF for every ticker."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from finanlyzeos_chatbot.config import Settings
from finanlyzeos_chatbot.database import Database
from finanlyzeos_chatbot.kpi_backfill import fill_missing_kpis


def _load_tickers(database_path: Path, user_tickers: Sequence[str]) -> List[str]:
    if user_tickers:
        return sorted({ticker.upper() for ticker in user_tickers})
    query_candidates = (
        "SELECT DISTINCT ticker FROM metric_snapshots",
        "SELECT DISTINCT ticker FROM financial_facts",
    )
    with sqlite3.connect(database_path) as conn:
        for query in query_candidates:
            rows = [row[0] for row in conn.execute(query)]
            if rows:
                return sorted({ticker.upper() for ticker in rows})
    raise RuntimeError("No tickers found in the local database; ingest data first.")


def _iter_years(years: Sequence[int] | None, default_year: int) -> Iterable[int]:
    if years:
        return sorted({int(year) for year in years})
    return [default_year]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill KPIs for every ticker with robust fallbacks.")
    parser.add_argument("--year", type=int, action="append", dest="years", help="Fiscal year to process (repeatable)")
    parser.add_argument("--ticker", type=str, action="append", dest="tickers", help="Restrict to specific ticker(s)")
    parser.add_argument("--allow-external", action="store_true", default=False, help="Permit external price lookups (Yahoo/Stooq)")
    parser.add_argument("--database", type=Path, default=None, help="Optional override for the SQLite database path")
    args = parser.parse_args(argv)

    settings = Settings()
    database_path = args.database or Path(settings.database_path)
    db = Database(database_path)

    tickers = _load_tickers(database_path, args.tickers or [])
    if not tickers:
        print("[warn] No tickers discovered – nothing to do.")
        return 0

    latest_year = datetime.now().year - 1
    years = list(_iter_years(args.years, latest_year))

    processed = 0
    for year in years:
        print(f"[info] Filling KPIs for FY{year} ({len(tickers)} tickers)")
        for ticker in tickers:
            added = fill_missing_kpis(db, ticker, year, allow_external=args.allow_external)
            if added:
                print(f"  [ok] {ticker}: added {added} metrics")
            processed += added
    print(f"[info] Completed. {processed} KPI values refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
