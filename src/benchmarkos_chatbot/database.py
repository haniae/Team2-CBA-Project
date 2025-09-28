"""Utility functions for persisting chatbot conversations in SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional, Tuple


@dataclass(frozen=True)
class Message:
    """A single conversational exchange."""

    role: str
    content: str
    created_at: datetime


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
