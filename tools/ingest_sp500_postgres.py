"""Ingest the full S&P 500 universe into the Postgres SEC store."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import psycopg2

# Dynamically load the richer ingestion helpers that live under src/.
_MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "ingest_companyfacts.py"
if not _MODULE_PATH.exists():
    raise SystemExit(f"Ingestion helper not found: {_MODULE_PATH}")
spec = None
module = None
try:
    import importlib.util

    spec = importlib.util.spec_from_file_location("benchmarkos_ingest", _MODULE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load ingest_companyfacts module spec.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
except Exception as exc:  # pragma: no cover - defensive guard
    raise SystemExit(f"Failed to load ingestion helpers: {exc}") from exc

from benchmarkos_chatbot.ticker_universe import load_ticker_universe


def chunk(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    """Yield successive slices of *items* with length *size*."""
    for index in range(0, len(items), size):
        yield items[index : index + size]


def ingest_batch(
    tickers: Sequence[str],
    *,
    pg_settings,
    schema: str,
    user_agent: str,
    years: int,
    min_interval: float,
) -> Tuple[List[str], List[str]]:
    """Ingest a batch of tickers, returning (successes, failures)."""
    successes: List[str] = []
    failures: List[str] = []

    client = module.SecClient(user_agent=user_agent, min_interval=min_interval)
    with psycopg2.connect(pg_settings.dsn()) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT ticker, cik FROM {schema}.ticker_cik WHERE ticker = ANY(%s)",
                (list(tickers),),
            )
            rows = cur.fetchall()
        mapping = {row[0].upper(): str(row[1]).zfill(10) for row in rows}
        missing = [t for t in tickers if t.upper() not in mapping]
        if missing:
            module.populate_ticker_map(pg_settings, schema, client)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT ticker, cik FROM {schema}.ticker_cik WHERE ticker = ANY(%s)",
                    (list(tickers),),
                )
                rows = cur.fetchall()
            mapping = {row[0].upper(): str(row[1]).zfill(10) for row in rows}

        for ticker in tickers:
            key = ticker.upper()
            cik = mapping.get(key)
            if not cik:
                failures.append(f"{ticker}: missing CIK mapping")
                continue
            print(f"[INFO] Fetching {ticker} (CIK={cik})")
            try:
                payload = client.fetch_companyfacts(cik)
            except Exception as exc:  # pragma: no cover - network variability
                failures.append(f"{ticker}: fetch failed ({exc})")
                continue

            rows, index = module.process_companyfacts(cik, payload)
            if years > 0:
                cutoff = datetime.utcnow().year - years + 1
                rows = [row for row in rows if row.get("fy") is None or row["fy"] >= cutoff]
            module.derive_metrics(rows, index)
            print(f"[INFO]   Upserting {len(rows)} rows")
            try:
                module.upsert_rows(conn, rows, schema)
            except Exception as exc:  # pragma: no cover - database constraints
                failures.append(f"{ticker}: upsert failed ({exc})")
                continue
            successes.append(ticker)
            time.sleep(min_interval)

    return successes, failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Load SEC companyfacts into Postgres.")
    parser.add_argument(
        "--universe",
        default="sp500",
        help="Ticker universe name defined in ticker_universe.py (default: sp500).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=15,
        help="Number of fiscal years of history to retain (default: 15).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of tickers to ingest per batch (default: 5).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.4,
        help="Seconds to pause between SEC calls (default: 0.4).",
    )
    args = parser.parse_args()

    user_agent = os.getenv("SEC_API_USER_AGENT")
    if not user_agent:
        raise SystemExit("SEC_API_USER_AGENT must be set (e.g. 'Firstname Lastname email@example.com').")

    pg_settings = module.PostgresSettings()
    run_settings = module.RunSettings(tickers=[], min_interval=args.sleep)
    module.ensure_schema(pg_settings, run_settings.schema)

    universe = load_ticker_universe(args.universe)
    print(f"[INFO] Universe '{args.universe}' -> {len(universe)} tickers")

    total_success: List[str] = []
    total_failures: List[str] = []
    for batch in chunk(universe, max(1, args.batch_size)):
        successes, failures = ingest_batch(
            batch,
            pg_settings=pg_settings,
            schema=run_settings.schema,
            user_agent=user_agent,
            years=args.years,
            min_interval=args.sleep,
        )
        total_success.extend(successes)
        total_failures.extend(failures)
        print(
            f"[INFO] Batch complete: {len(successes)} succeeded, {len(failures)} failed "
            f"(progress {len(total_success)}/{len(universe)})"
        )

    summary = {
        "universe": args.universe,
        "years": args.years,
        "successes": total_success,
        "failures": total_failures,
    }
    Path("postgres_ingest_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"[INFO] Ingestion complete. Successes: {len(total_success)}, Failures: {len(total_failures)}")


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
