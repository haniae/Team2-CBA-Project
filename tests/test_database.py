"""Basic coverage for the SQLite helper module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from benchmarkos_chatbot import database


@pytest.fixture()
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "chat.sqlite3"
    database.initialise(db_path)
    return db_path


def test_log_and_fetch_round_trip(temp_db: Path) -> None:
    conversation_id = "test-123"
    database.log_message(temp_db, conversation_id, "user", "Hello", datetime(2024, 1, 1))
    database.log_message(temp_db, conversation_id, "assistant", "Hi", datetime(2024, 1, 1, 0, 0, 10))

    messages = list(database.fetch_conversation(temp_db, conversation_id))
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "Hello"
    assert messages[1].content == "Hi"


def test_iter_conversation_summaries(temp_db: Path) -> None:
    database.log_message(temp_db, "conv-a", "user", "One")
    database.log_message(temp_db, "conv-a", "assistant", "Two")
    database.log_message(temp_db, "conv-b", "user", "Only")

    summaries = list(database.iter_conversation_summaries(temp_db))
    assert summaries == [("conv-b", 1), ("conv-a", 2)]


def test_most_recent_conversation_id(temp_db: Path) -> None:
    assert database.most_recent_conversation_id(temp_db) is None

    database.log_message(temp_db, "conv-a", "user", "Hi")
    database.log_message(temp_db, "conv-b", "user", "Hello")

    assert database.most_recent_conversation_id(temp_db) == "conv-b"
