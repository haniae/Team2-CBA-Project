"""SQLite persistence layer for the BenchmarkOS chatbot platform.

The database module stores:

* Conversational transcripts used to maintain chatbot context.
* Normalised financial data, computed metrics, and scenario outputs that the
  analytics engine relies on to answer business questions.
* Audit artefacts (adjustments, alerts, governance trails) that help satisfy
  institutional compliance requirements.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Message:
    """A single conversational exchange."""

    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class FinancialFact:
    """A single normalised financial data point."""

    ticker: str
    company_name: str
    fiscal_year: int
    metric: str
    value: float
    source: str
    adjusted: bool
    adjustment_note: Optional[str]
    ingested_at: datetime


@dataclass(frozen=True)
class MetricRecord:
    """Computed KPI ready for consumption by the analytics layer."""

    ticker: str
    metric: str
    period: str
    value: Optional[float]
    phase: str
    methodology: str
    calculated_at: datetime


@dataclass(frozen=True)
class AuditEvent:
    """An audit trail entry capturing data lineage information."""

    event_type: str
    entity_id: Optional[str]
    details: str
    created_at: datetime
    created_by: str = "system"


@dataclass(frozen=True)
class ScenarioResult:
    """Materialised output from a what-if scenario."""

    ticker: str
    scenario_name: str
    assumptions: dict[str, float]
    metric: str
    value: float
    created_at: datetime
    scenario_id: Optional[int] = None


@dataclass(frozen=True)
class Alert:
    """Real-time notification raised by the analytics workflow."""

    ticker: str
    metric: str
    severity: str
    message: str
    created_at: datetime
    is_read: bool = False
    alert_id: Optional[int] = None


def initialise(database_path: Path) -> None:
    """Ensure the SQLite database exists and contains the required tables."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
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
            CREATE TABLE IF NOT EXISTS financial_facts (
                ticker TEXT NOT NULL,
                company_name TEXT NOT NULL,
                fiscal_year INTEGER NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                source TEXT NOT NULL,
                adjusted INTEGER NOT NULL DEFAULT 0,
                adjustment_note TEXT,
                ingested_at TEXT NOT NULL,
                PRIMARY KEY (ticker, fiscal_year, metric)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_results (
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                period TEXT NOT NULL,
                value REAL,
                phase TEXT NOT NULL,
                methodology TEXT NOT NULL,
                calculated_at TEXT NOT NULL,
                PRIMARY KEY (ticker, metric, period, phase)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                assumptions TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                metric TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.commit()


def log_message(
    database_path: Path,
    conversation_id: str,
    role: str,
    content: str,
    created_at: Optional[datetime] = None,
) -> None:
    """Persist a single message to the database."""

    created_at = created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO conversations (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, created_at.isoformat()),
        )
        connection.commit()


def fetch_conversation(
    database_path: Path, conversation_id: str
) -> Iterable[Message]:
    """Load the full transcript for a conversation."""

    with sqlite3.connect(database_path) as connection:
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
                created_at=datetime.fromisoformat(created_at),
            )


@contextmanager
def temporary_connection(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Provide a context-managed SQLite connection.

    Useful when you need to execute multiple statements as part of a single
    transaction.
    """

    connection = sqlite3.connect(database_path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def most_recent_conversation_id(database_path: Path) -> Optional[str]:
    """Return the most recently used conversation identifier, if any."""

    with sqlite3.connect(database_path) as connection:
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
    """Yield (conversation_id, message_count) pairs for quick inspection."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT conversation_id, COUNT(*) AS message_count
            FROM conversations
            GROUP BY conversation_id
            ORDER BY MAX(created_at) DESC
            """
        )
        yield from rows


def upsert_financial_fact(database_path: Path, fact: FinancialFact) -> None:
    """Insert or update a normalised financial data point."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO financial_facts (
                ticker, company_name, fiscal_year, metric, value, source,
                adjusted, adjustment_note, ingested_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, fiscal_year, metric) DO UPDATE SET
                company_name = excluded.company_name,
                value = excluded.value,
                source = excluded.source,
                adjusted = excluded.adjusted,
                adjustment_note = excluded.adjustment_note,
                ingested_at = excluded.ingested_at
            """,
            (
                fact.ticker,
                fact.company_name,
                fact.fiscal_year,
                fact.metric,
                fact.value,
                fact.source,
                int(fact.adjusted),
                fact.adjustment_note,
                fact.ingested_at.isoformat(),
            ),
        )
        connection.commit()


def fetch_financial_facts(
    database_path: Path,
    ticker: Optional[str] = None,
    *,
    metric: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    limit: Optional[int] = None,
) -> list[FinancialFact]:
    """Return normalised financial facts with optional filtering."""

    query = (
        "SELECT ticker, company_name, fiscal_year, metric, value, source, "
        "adjusted, adjustment_note, ingested_at "
        "FROM financial_facts"
    )
    conditions: list[str] = []
    params: list[object] = []
    if ticker:
        conditions.append("ticker = ?")
        params.append(ticker)
    if metric:
        conditions.append("metric = ?")
        params.append(metric)
    if fiscal_year is not None:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ticker, fiscal_year, metric"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query, params)
        return [
            FinancialFact(
                ticker=row[0],
                company_name=row[1],
                fiscal_year=row[2],
                metric=row[3],
                value=float(row[4]),
                source=row[5],
                adjusted=bool(row[6]),
                adjustment_note=row[7],
                ingested_at=datetime.fromisoformat(row[8]),
            )
            for row in rows
        ]


def list_companies(database_path: Path) -> list[tuple[str, str]]:
    """Return the distinct (ticker, company_name) pairs in the store."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT ticker, company_name
            FROM financial_facts
            ORDER BY ticker ASC
            """
        )
        return [(row[0], row[1]) for row in rows]


def record_metric_result(database_path: Path, record: MetricRecord) -> None:
    """Persist a computed KPI."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO metric_results (
                ticker, metric, period, value, phase, methodology, calculated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, metric, period, phase) DO UPDATE SET
                value = excluded.value,
                methodology = excluded.methodology,
                calculated_at = excluded.calculated_at
            """,
            (
                record.ticker,
                record.metric,
                record.period,
                record.value,
                record.phase,
                record.methodology,
                record.calculated_at.isoformat(),
            ),
        )
        connection.commit()


def fetch_metric_results(
    database_path: Path,
    ticker: str,
    *,
    phase: Optional[str] = None,
    metrics: Optional[Sequence[str]] = None,
) -> list[MetricRecord]:
    """Retrieve computed KPIs for a ticker."""

    query = (
        "SELECT ticker, metric, period, value, phase, methodology, calculated_at "
        "FROM metric_results WHERE ticker = ?"
    )
    params: list[object] = [ticker]
    if phase:
        query += " AND phase = ?"
        params.append(phase)
    if metrics:
        placeholders = ",".join("?" for _ in metrics)
        query += f" AND metric IN ({placeholders})"
        params.extend(metrics)
    query += " ORDER BY period DESC"

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query, params)
        return [
            MetricRecord(
                ticker=row[0],
                metric=row[1],
                period=row[2],
                value=float(row[3]) if row[3] is not None else None,
                phase=row[4],
                methodology=row[5],
                calculated_at=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]


def record_audit_event(database_path: Path, event: AuditEvent) -> None:
    """Store an audit trail event."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_type, entity_id, details, created_at, created_by
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_type,
                event.entity_id,
                event.details,
                event.created_at.isoformat(),
                event.created_by,
            ),
        )
        connection.commit()


def fetch_recent_audit_events(
    database_path: Path, limit: int = 25
) -> list[AuditEvent]:
    """Fetch the most recent audit trail entries."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT event_type, entity_id, details, created_at, created_by
            FROM audit_events
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            AuditEvent(
                event_type=row[0],
                entity_id=row[1],
                details=row[2],
                created_at=datetime.fromisoformat(row[3]),
                created_by=row[4],
            )
            for row in rows
        ]




def fetch_audit_events_for_ticker(
    database_path: Path,
    ticker: str,
    *,
    fiscal_year: Optional[int] = None,
    limit: int = 25,
) -> list[AuditEvent]:
    """Fetch audit events that relate to a specific ticker/year."""

    conditions = []
    params: list[object] = []

    if fiscal_year is not None:
        conditions.append("entity_id = ?")
        params.append(f"{ticker}-{fiscal_year}")
        conditions.append("details LIKE ?")
        params.append(f"%{ticker}%")
    else:
        conditions.extend(["entity_id LIKE ?", "entity_id LIKE ?", "details LIKE ?"])
        params.extend([f"{ticker}-%", f"{ticker}:%", f"%{ticker}%"])

    where_clause = " OR ".join(conditions) if conditions else "1=1"
    query = (
        "SELECT event_type, entity_id, details, created_at, created_by "
        "FROM audit_events "
        f"WHERE {where_clause} "
        "ORDER BY datetime(created_at) DESC "
        "LIMIT ?"
    )
    params.append(limit)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query, params)
        return [
            AuditEvent(
                event_type=row[0],
                entity_id=row[1],
                details=row[2],
                created_at=datetime.fromisoformat(row[3]),
                created_by=row[4],
            )
            for row in rows
        ]
def record_scenario_result(database_path: Path, result: ScenarioResult) -> None:
    """Persist the output of a what-if scenario run."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO scenario_results (
                ticker, scenario_name, assumptions, metric, value, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.ticker,
                result.scenario_name,
                json.dumps(result.assumptions, sort_keys=True),
                result.metric,
                result.value,
                result.created_at.isoformat(),
            ),
        )
        connection.commit()


def fetch_scenario_results(
    database_path: Path,
    ticker: str,
    scenario_name: Optional[str] = None,
) -> list[ScenarioResult]:
    """Retrieve previously calculated scenario outputs."""

    query = (
        "SELECT id, ticker, scenario_name, assumptions, metric, value, created_at "
        "FROM scenario_results WHERE ticker = ?"
    )
    params: list[object] = [ticker]
    if scenario_name:
        query += " AND scenario_name = ?"
        params.append(scenario_name)
    query += " ORDER BY datetime(created_at) DESC"

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(query, params)
        return [
            ScenarioResult(
                ticker=row[1],
                scenario_name=row[2],
                assumptions=json.loads(row[3]),
                metric=row[4],
                value=float(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                scenario_id=row[0],
            )
            for row in rows
        ]


def record_alert(database_path: Path, alert: Alert) -> None:
    """Store an alert raised by the analytics workflow."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO alerts (
                ticker, metric, severity, message, created_at, is_read
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alert.ticker,
                alert.metric,
                alert.severity,
                alert.message,
                alert.created_at.isoformat(),
                int(alert.is_read),
            ),
        )
        connection.commit()


def fetch_active_alerts(database_path: Path) -> list[Alert]:
    """Return unread alerts."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, ticker, metric, severity, message, created_at, is_read
            FROM alerts
            WHERE is_read = 0
            ORDER BY datetime(created_at) DESC
            """
        )
        return [
            Alert(
                ticker=row[1],
                metric=row[2],
                severity=row[3],
                message=row[4],
                created_at=datetime.fromisoformat(row[5]),
                is_read=bool(row[6]),
                alert_id=row[0],
            )
            for row in rows
        ]


def mark_alert_read(database_path: Path, alert_id: int) -> None:
    """Mark an alert as acknowledged."""

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE alerts SET is_read = 1 WHERE id = ?",
            (alert_id,),
        )
        connection.commit()
