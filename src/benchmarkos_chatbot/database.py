"""Utility functions for persisting chatbot conversations in SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Message:
    """A single conversational exchange."""

    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class Deliverable:
    """Represents a single workstream item for the programme."""

    position: int
    title: str
    owner: Optional[str] = None
    due_window: Optional[str] = None
    status: str = "Not Started"
    category: Optional[str] = None


DEFAULT_DELIVERABLES: Tuple[Deliverable, ...] = (
    Deliverable(
        position=1,
        title="Select Financial Datasets (SEC EDGAR, Yahoo Finance, Kaggle, etc.)",
        owner="Hania Abdel",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=2,
        title="Build SEC EDGAR data fetcher for 10-K filings",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=3,
        title="Build market data connector (Yahoo Finance API)",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=4,
        title="Set up data environment (PostgreSQL, Python, Git)",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=5,
        title="AI Assisted Benchmarking for 10-K filings",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=6,
        title="8-10 Standardized KPIs with Audit Trails",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=7,
        title="Create basic filing storage structure (company/year/filing_type)",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=8,
        title="Implement text extraction pipeline for financial statements",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=9,
        title="Automate metric list with Drill Down Capabilities",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=10,
        title="Automated Report Generation",
        due_window="Sep 21-28",
    ),
    Deliverable(
        position=11,
        title="Click Through Lineage to Source Documents",
        due_window="Sep 21-28",
    ),
)


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
            CREATE TABLE IF NOT EXISTS deliverables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                owner TEXT,
                due_window TEXT,
                status TEXT NOT NULL,
                category TEXT
            )
            """
        )
        connection.commit()

    seed_deliverables(database_path)


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


def seed_deliverables(
    database_path: Path, deliverables: Sequence[Deliverable] = DEFAULT_DELIVERABLES
) -> None:
    """Populate the deliverables table with default items if it is empty."""

    with sqlite3.connect(database_path) as connection:
        existing = connection.execute(
            "SELECT COUNT(*) FROM deliverables"
        ).fetchone()[0]
        if existing:
            return

        connection.executemany(
            """
            INSERT INTO deliverables (position, title, owner, due_window, status, category)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.position,
                    item.title,
                    item.owner,
                    item.due_window,
                    item.status,
                    item.category,
                )
                for item in deliverables
            ],
        )
        connection.commit()


def list_deliverables(database_path: Path) -> List[Deliverable]:
    """Return the deliverables ordered by their planned sequence."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT position, title, owner, due_window, status, category
            FROM deliverables
            ORDER BY position ASC
            """
        ).fetchall()

    return [
        Deliverable(
            position=row[0],
            title=row[1],
            owner=row[2],
            due_window=row[3],
            status=row[4],
            category=row[5],
        )
        for row in rows
    ]


def update_deliverable_status(
    database_path: Path, position: int, status: str
) -> Deliverable:
    """Update a deliverable's status and return the refreshed record."""

    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE deliverables
            SET status = ?
            WHERE position = ?
            """,
            (status, position),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"No deliverable found at position {position}")
        connection.commit()

    deliverables = list_deliverables(database_path)
    for item in deliverables:
        if item.position == position:
            return item

    raise ValueError(f"Deliverable at position {position} could not be reloaded")
