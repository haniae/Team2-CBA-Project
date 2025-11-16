"""Refresh the local ticker alias catalog from the SEC company list."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import requests

from finanlyzeos_chatbot import database, load_settings

SEC_TICKER_LIST = "https://www.sec.gov/files/company_tickers.json"


def _iter_sec_entries(url: str, user_agent: str, timeout: float = 60.0) -> Iterable[dict]:
    response = requests.get(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        return payload.values()
    return payload


def refresh_aliases(url: str, *, user_agent: str, database_path: Path) -> int:
    timestamp = datetime.now(timezone.utc)
    records: List[database.TickerAliasRecord] = []
    for entry in _iter_sec_entries(url, user_agent):
        ticker = str(entry.get("ticker") or "").strip().upper()
        cik = str(entry.get("cik_str") or "").strip()
        name = str(entry.get("title") or entry.get("name") or "").strip()
        if not ticker or not cik:
            continue
        records.append(
            database.TickerAliasRecord(
                ticker=ticker,
                cik=cik.zfill(10),
                company_name=name,
                updated_at=timestamp,
            )
        )
    if not records:
        return 0
    return database.upsert_ticker_aliases(database_path, records)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Refresh ticker aliases from SEC data")
    parser.add_argument(
        "--url",
        default=SEC_TICKER_LIST,
        help="Source JSON URL (default: SEC company_tickers list)",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    updated = refresh_aliases(
        args.url,
        user_agent=settings.sec_api_user_agent,
        database_path=settings.database_path,
    )
    print(f"Updated {updated} ticker aliases at {settings.database_path}")


if __name__ == "__main__":
    main()
