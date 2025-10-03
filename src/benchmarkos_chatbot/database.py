"""Utility functions for persisting chatbot conversations and market data in SQLite.

Key guarantees:
- ALL tickers normalized to uppercase on write.
- ALL timestamps written as UTC ISO-8601 strings (+00:00).
- No SQLite datetime(...) usage; string ordering/compare is used consistently.
- Safe datetime parsing on read (graceful with NULL/empty legacy values).
- UNIQUE/NULL behavior consistent (e.g., source_filing is NOT NULL DEFAULT '').
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .data_sources import AuditEvent, FilingRecord, FinancialFact, MarketQuote


# -----------------------------
# Dataclasses
# -----------------------------

@dataclass(frozen=True)
class Message:
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class MetricRecord:
    ticker: str
    metric: str
    period: str
    value: Optional[float]
    source: str
    updated_at: datetime
    start_year: Optional[int]
    end_year: Optional[int]


@dataclass(frozen=True)
class FinancialFactRecord:
    ticker: str
    metric: str
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]
    period: str
    value: Optional[float]
    unit: Optional[str]
    source: str
    source_filing: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    adjusted: bool
    adjustment_note: Optional[str]
    ingested_at: Optional[datetime]


@dataclass(frozen=True)
class ScenarioResultRecord:
    ticker: str
    scenario_name: str
    metrics: Dict[str, Optional[float]]
    narrative: str
    created_at: datetime


@dataclass(frozen=True)
class AuditEventRecord:
    ticker: str
    event_type: str
    entity_id: Optional[str]
    details: Dict[str, Any]
    created_at: datetime
    created_by: str


# -----------------------------
# Helpers
# -----------------------------

def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    """UTC ISO-8601 with explicit offset (+00:00)."""
    return _ensure_utc(value).isoformat()


def _json_default(value: Any) -> str:
    """JSON serializer for datetime/date objects."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serialisable")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=_json_default, separators=(",", ":"))


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.fromisoformat(s)


def _normalize_ticker(t: Optional[str]) -> str:
    return (t or "").upper()


def _connect(database_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _table_has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in rows)


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _table_has_column(connection, table, column):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _apply_migrations(connection: sqlite3.Connection) -> None:
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    # financial_facts
    if "financial_facts" in tables:
        _ensure_column(connection, "financial_facts", "period", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "financial_facts", "unit", "TEXT")
        _ensure_column(connection, "financial_facts", "source", "TEXT NOT NULL DEFAULT 'edgar'")
        _ensure_column(connection, "financial_facts", "source_filing", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "financial_facts", "raw", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(connection, "financial_facts", "period_start", "TEXT")
        _ensure_column(connection, "financial_facts", "period_end", "TEXT")
        _ensure_column(connection, "financial_facts", "adjusted", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(connection, "financial_facts", "adjustment_note", "TEXT")
        _ensure_column(connection, "financial_facts", "ingested_at", "TEXT")

        # Normalize legacy values
        connection.execute("""
            UPDATE financial_facts
            SET period_start = NULLIF(period_start, ''),
                period_end   = NULLIF(period_end, ''),
                ingested_at  = NULLIF(ingested_at, '')
        """)
        connection.execute("""
            UPDATE financial_facts
            SET source_filing = ''
            WHERE source_filing IS NULL
        """)

    # metric_snapshots
    if "metric_snapshots" in tables:
        _ensure_column(connection, "metric_snapshots", "start_year", "INTEGER")
        _ensure_column(connection, "metric_snapshots", "end_year", "INTEGER")
        _ensure_column(connection, "metric_snapshots", "source", "TEXT NOT NULL DEFAULT 'edgar'")
        _ensure_column(connection, "metric_snapshots", "updated_at", "TEXT")
        connection.execute("""
            UPDATE metric_snapshots
            SET updated_at = NULLIF(updated_at, '')
        """)

    # market_quotes
    if "market_quotes" in tables:
        _ensure_column(connection, "market_quotes", "data", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(connection, "market_quotes", "source", "TEXT NOT NULL DEFAULT 'yahoo'")

    # audit_events
    if "audit_events" in tables:
        _ensure_column(connection, "audit_events", "ticker", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(connection, "audit_events", "details", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(connection, "audit_events", "created_by", "TEXT NOT NULL DEFAULT 'system'")

    # company_filings
    if "company_filings" in tables:
        _ensure_column(connection, "company_filings", "data", "TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(connection, "company_filings", "source", "TEXT NOT NULL DEFAULT 'edgar'")


# -----------------------------
# Schema init
# -----------------------------

def initialise(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                metrics TEXT NOT NULL,
                narrative TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS company_filings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cik TEXT NOT NULL,
                ticker TEXT NOT NULL,
                accession_number TEXT NOT NULL,
                form_type TEXT NOT NULL,
                filed_at TEXT NOT NULL,
                period_of_report TEXT,
                acceptance_datetime TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'edgar',
                UNIQUE(cik, accession_number)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cik TEXT NOT NULL,
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                fiscal_year INTEGER,
                fiscal_period TEXT,
                period TEXT NOT NULL DEFAULT '',
                value REAL,
                unit TEXT,
                source_filing TEXT NOT NULL DEFAULT '',
                raw TEXT NOT NULL DEFAULT '{}',
                period_start TEXT,
                period_end TEXT,
                adjusted INTEGER NOT NULL DEFAULT 0,
                adjustment_note TEXT,
                source TEXT NOT NULL DEFAULT 'edgar',
                ingested_at TEXT,
                UNIQUE(ticker, metric, period, source, source_filing)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS market_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT,
                volume REAL,
                quote_time TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'yahoo',
                UNIQUE(ticker, quote_time, source)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL DEFAULT '',
                event_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'system'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                period TEXT NOT NULL,
                start_year INTEGER,
                end_year INTEGER,
                value REAL,
                source TEXT NOT NULL DEFAULT 'edgar',
                updated_at TEXT,
                UNIQUE(ticker, metric, period, source)
            )
            """
        )

        _apply_migrations(connection)

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_financial_facts_key
            ON financial_facts (ticker, metric, period, source)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_market_quotes_ticker_time
            ON market_quotes (ticker, quote_time DESC)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_metric_snapshots_ticker
            ON metric_snapshots (ticker, metric)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scenario_results_ticker
            ON scenario_results (ticker, scenario_name, created_at DESC)
            """
        )
        connection.commit()


# -----------------------------
# Conversations
# -----------------------------

def log_message(
    database_path: Path,
    conversation_id: str,
    role: str,
    content: str,
    created_at: Optional[datetime] = None,
) -> None:
    created_at = _ensure_utc(created_at or datetime.now(timezone.utc))
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO conversations (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, _iso_utc(created_at)),
        )
        connection.commit()


def fetch_conversation(
    database_path: Path, conversation_id: str
) -> Iterable[Message]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT role, content, created_at
            FROM conversations
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        )
        for role, content, created_at in rows:
            yield Message(
                role=role,
                content=content,
                created_at=_parse_dt(created_at) or datetime(1970, 1, 1, tzinfo=timezone.utc),
            )


@contextmanager
def temporary_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = _connect(database_path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def most_recent_conversation_id(database_path: Path) -> Optional[str]:
    with _connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT conversation_id
            FROM conversations
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return row[0] if row else None


def iter_conversation_summaries(database_path: Path) -> Iterator[Tuple[str, int]]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT conversation_id, COUNT(*) AS message_count
            FROM conversations
            GROUP BY conversation_id
            ORDER BY MAX(created_at) DESC
            """
        )
        yield from rows


# -----------------------------
# Company Filings
# -----------------------------

def bulk_upsert_company_filings(
    database_path: Path, filings: Sequence["FilingRecord"]
) -> int:
    if not filings:
        return 0

    payload = [
        (
            filing.cik,
            _normalize_ticker(filing.ticker),
            filing.accession_number,
            filing.form_type,
            _iso_utc(filing.filed_at),
            filing.period_of_report.isoformat() if filing.period_of_report else None,
            filing.acceptance_datetime.isoformat() if filing.acceptance_datetime else None,
            _json_dumps(filing.data),
            filing.source,
        )
        for filing in filings
    ]

    with _connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT OR IGNORE INTO company_filings (
                cik, ticker, accession_number, form_type, filed_at,
                period_of_report, acceptance_datetime, data, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        connection.commit()
        return cursor.rowcount


# -----------------------------
# Financial Facts
# -----------------------------

def bulk_upsert_financial_facts(
    database_path: Path, facts: Sequence["FinancialFact"]
) -> int:
    if not facts:
        return 0

    payload = [
        (
            fact.cik,
            _normalize_ticker(fact.ticker),
            fact.metric.lower(),
            fact.fiscal_year,
            fact.fiscal_period,
            fact.period,
            fact.value,
            fact.unit,
            (fact.source_filing or ""),
            _json_dumps(fact.raw),
            fact.period_start.isoformat() if fact.period_start else None,
            fact.period_end.isoformat() if fact.period_end else None,
            1 if fact.adjusted else 0,
            fact.adjustment_note,
            fact.source,
            _iso_utc(fact.ingested_at) if fact.ingested_at else None,
        )
        for fact in facts
    ]

    with _connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT INTO financial_facts (
                cik, ticker, metric, fiscal_year, fiscal_period, period, value,
                unit, source_filing, raw, period_start, period_end, adjusted,
                adjustment_note, source, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, metric, period, source, source_filing) DO UPDATE SET
                value = excluded.value,
                unit = excluded.unit,
                raw = excluded.raw,
                period_start = excluded.period_start,
                period_end = excluded.period_end,
                adjusted = excluded.adjusted,
                adjustment_note = excluded.adjustment_note,
                ingested_at = excluded.ingested_at
            """,
            payload,
        )
        connection.commit()
        return cursor.rowcount


def fetch_financial_facts(
    database_path: Path,
    ticker: str,
    *,
    fiscal_year: Optional[int] = None,
    metric: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[FinancialFactRecord]:
    sql = [
        "SELECT metric, fiscal_year, fiscal_period, period, value, unit, source,",
        "       source_filing, period_start, period_end, adjusted, adjustment_note, ingested_at",
        "FROM financial_facts",
        "WHERE ticker = ?",
    ]
    params: List[Any] = [_normalize_ticker(ticker)]

    if fiscal_year is not None:
        sql.append("AND fiscal_year = ?")
        params.append(fiscal_year)
    if metric is not None:
        sql.append("AND metric = ?")
        params.append(metric.lower())

    sql.append("ORDER BY (fiscal_year IS NULL) ASC, fiscal_year DESC, period DESC, metric ASC")
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(limit)

    query = "\n".join(sql)
    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    records: List[FinancialFactRecord] = []
    for row in rows:
        records.append(
            FinancialFactRecord(
                ticker=_normalize_ticker(ticker),
                metric=row["metric"],
                fiscal_year=row["fiscal_year"],
                fiscal_period=row["fiscal_period"],
                period=row["period"],
                value=row["value"],
                unit=row["unit"],
                source=row["source"],
                source_filing=row["source_filing"] or None,
                period_start=_parse_dt(row["period_start"]),
                period_end=_parse_dt(row["period_end"]),
                adjusted=bool(row["adjusted"]),
                adjustment_note=row["adjustment_note"],
                ingested_at=_parse_dt(row["ingested_at"]),
            )
        )
    return records


# -----------------------------
# Market Quotes
# -----------------------------

def bulk_insert_market_quotes(
    database_path: Path, quotes: Sequence["MarketQuote"]
) -> int:
    if not quotes:
        return 0

    payload = [
        (
            _normalize_ticker(quote.ticker),
            quote.price,
            quote.currency,
            quote.volume,
            _iso_utc(quote.timestamp),
            _json_dumps(quote.raw),
            quote.source,
        )
        for quote in quotes
    ]

    with _connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT OR IGNORE INTO market_quotes (
                ticker, price, currency, volume, quote_time, data, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        connection.commit()
        return cursor.rowcount


def fetch_latest_quote(database_path: Path, ticker: str) -> Optional[Dict[str, Any]]:
    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT price, currency, volume, quote_time, data, source
            FROM market_quotes
            WHERE ticker = ?
            ORDER BY quote_time DESC
            LIMIT 1
            """,
            (_normalize_ticker(ticker),),
        ).fetchone()

    if row is None:
        return None

    return {
        "price": row["price"],
        "currency": row["currency"],
        "volume": row["volume"],
        "timestamp": _parse_dt(row["quote_time"]),
        "source": row["source"],
        "raw": json.loads(row["data"]) if row["data"] else {},
    }


def fetch_quote_on_or_before(
    database_path: Path, ticker: str, *, before: datetime
) -> Optional[Dict[str, Any]]:
    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT price, currency, volume, quote_time, data, source
            FROM market_quotes
            WHERE ticker = ? AND quote_time <= ?
            ORDER BY quote_time DESC
            LIMIT 1
            """,
            (_normalize_ticker(ticker), _iso_utc(before)),
        ).fetchone()

    if row is None:
        return None

    return {
        "price": row["price"],
        "currency": row["currency"],
        "volume": row["volume"],
        "timestamp": _parse_dt(row["quote_time"]),
        "source": row["source"],
        "raw": json.loads(row["data"]) if row["data"] else {},
    }


# -----------------------------
# Audit Events
# -----------------------------

def bulk_insert_audit_events(
    database_path: Path,
    events: Sequence["AuditEvent"],
) -> int:
    """Persist audit trail events for later inspection."""
    if not events:
        return 0

    payload = [
        (
            _normalize_ticker(event.ticker),
            event.event_type,
            event.entity_id,
            _json_dumps(event.details),
            _iso_utc(event.created_at),
            event.created_by,
        )
        for event in events
    ]

    with _connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT INTO audit_events (
                ticker, event_type, entity_id, details, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        connection.commit()
        return cursor.rowcount


def fetch_audit_events(
    database_path: Path,
    ticker: str,
    *,
    fiscal_year: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[AuditEventRecord]:
    sql = [
        "SELECT event_type, entity_id, details, created_at, created_by",
        "FROM audit_events",
        "WHERE ticker = ?",
    ]
    params: List[Any] = [_normalize_ticker(ticker)]

    if fiscal_year is not None:
        sql.append("AND entity_id LIKE ?")
        params.append(f"%FY{fiscal_year}%")

    sql.append("ORDER BY created_at DESC")
    if limit is not None:
        sql.append("LIMIT ?")
        params.append(limit)

    query = "\n".join(sql)
    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    events: List[AuditEventRecord] = []
    for row in rows:
        events.append(
            AuditEventRecord(
                ticker=_normalize_ticker(ticker),
                event_type=row["event_type"],
                entity_id=row["entity_id"],
                details=json.loads(row["details"]) if row["details"] else {},
                created_at=_parse_dt(row["created_at"]) or datetime(1970, 1, 1, tzinfo=timezone.utc),
                created_by=row["created_by"],
            )
        )
    return events


# -----------------------------
# Metric Snapshots
# -----------------------------

def replace_metric_snapshots(
    database_path: Path,
    records: Sequence[MetricRecord],
) -> int:
    """Replace metric snapshots with the supplied values."""
    if not records:
        return 0

    payload = [
        (
            _normalize_ticker(record.ticker),
            record.metric,
            record.period,
            record.start_year,
            record.end_year,
            record.value,
            record.source,
            _iso_utc(record.updated_at),
        )
        for record in records
    ]

    with _connect(database_path) as connection:
        cursor = connection.executemany(
            """
            INSERT INTO metric_snapshots (
                ticker, metric, period, start_year, end_year, value, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, metric, period, source) DO UPDATE SET
                start_year = excluded.start_year,
                end_year   = excluded.end_year,
                value      = excluded.value,
                updated_at = excluded.updated_at
            """,
            payload,
        )
        connection.commit()
        return cursor.rowcount


def fetch_metric_snapshots(
    database_path: Path,
    ticker: str,
    *,
    period_filters: Optional[Sequence[Tuple[int, int]]] = None,
) -> List[MetricRecord]:
    """Return metric snapshots for `ticker` optionally filtered by years."""
    sql = [
        "SELECT ticker, metric, period, value, source, updated_at, start_year, end_year",
        "FROM metric_snapshots",
        "WHERE ticker = ?",
    ]
    params: List[Any] = [_normalize_ticker(ticker)]

    if period_filters:
        clauses = []
        for start_year, end_year in period_filters:
            # overlap: NOT (end < start OR start > end)
            clauses.append(
                "(start_year IS NOT NULL AND end_year IS NOT NULL "
                "AND NOT (end_year < ? OR start_year > ?))"
            )
            params.extend([start_year, end_year])
        sql.append("AND (" + " OR ".join(clauses) + ")")

    sql.append("ORDER BY metric ASC, (end_year IS NULL) ASC, end_year DESC, updated_at DESC")
    query = "\n".join(sql)

    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    results: List[MetricRecord] = []
    for row in rows:
        results.append(
            MetricRecord(
                ticker=row["ticker"],
                metric=row["metric"],
                period=row["period"],
                value=row["value"],
                source=row["source"],
                updated_at=_parse_dt(row["updated_at"]) or datetime(1970, 1, 1, tzinfo=timezone.utc),
                start_year=row["start_year"],
                end_year=row["end_year"],
            )
        )
    return results

# -----------------------------
# Scenario results
# -----------------------------


def store_scenario_result(database_path: Path, record: ScenarioResultRecord) -> None:
    payload = _json_dumps(record.metrics)
    created_at = _ensure_utc(record.created_at).isoformat()
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO scenario_results (ticker, scenario_name, metrics, narrative, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _normalize_ticker(record.ticker),
                record.scenario_name,
                payload,
                record.narrative,
                created_at,
            ),
        )
        connection.commit()


def fetch_scenario_results(
    database_path: Path,
    *,
    ticker: str,
    scenario_name: Optional[str] = None,
    limit: int = 10,
) -> List[ScenarioResultRecord]:
    query = [
        "SELECT ticker, scenario_name, metrics, narrative, created_at",
        "FROM scenario_results",
        "WHERE ticker = ?",
    ]
    params: List[Any] = [_normalize_ticker(ticker)]
    if scenario_name:
        query.append("AND scenario_name = ?")
        params.append(scenario_name)
    query.append("ORDER BY created_at DESC")
    if limit:
        query.append("LIMIT ?")
        params.append(limit)

    with _connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        query_str = "\n".join(query)
        rows = connection.execute(query_str, params).fetchall()

    results: List[ScenarioResultRecord] = []
    for row in rows:
        metrics_raw = json.loads(row["metrics"] or "{}")
        metrics: Dict[str, Optional[float]] = {}
        for key, value in metrics_raw.items():
            if isinstance(value, (int, float)):
                metrics[key] = float(value)
            else:
                metrics[key] = None
        created_at = _parse_dt(row["created_at"]) or datetime.now(timezone.utc)
        results.append(
            ScenarioResultRecord(
                ticker=_normalize_ticker(row["ticker"]),
                scenario_name=row["scenario_name"],
                metrics=metrics,
                narrative=row["narrative"],
                created_at=created_at,
            )
        )
    return results