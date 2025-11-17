"""Tests for building uploaded document context snippets."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from finanlyzeos_chatbot import database
from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.document_context import build_uploaded_document_context


@pytest.fixture
def chatbot(tmp_path: Path) -> tuple[FinanlyzeOSChatbot, Path]:
    """Provide a chatbot instance backed by a temporary database."""
    db_path = tmp_path / "chat.sqlite3"
    database.initialise(db_path)

    settings = SimpleNamespace(
        database_path=str(db_path),
        verification_enabled=False,
        cross_validation_enabled=False,
    )
    llm_client = SimpleNamespace(generate_reply=lambda *args, **kwargs: "ok")
    analytics_engine = SimpleNamespace()

    bot = FinanlyzeOSChatbot(
        settings=settings,
        llm_client=llm_client,
        analytics_engine=analytics_engine,
    )
    bot.conversation.conversation_id = "conv-test"

    return bot, db_path


def _insert_document(
    db_path: Path,
    *,
    document_id: str,
    conversation_id: str,
    filename: str,
    file_type: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Insert a document into the uploaded_documents table for testing."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO uploaded_documents (
                document_id,
                conversation_id,
                filename,
                file_type,
                file_size,
                content,
                metadata,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                conversation_id,
                filename,
                file_type,
                len(content.encode("utf-8")),
                content,
                json.dumps(metadata or {}),
                now,
                now,
            ),
        )


def test_uploaded_document_context_includes_snippet(chatbot):
    bot, db_path = chatbot

    _insert_document(
        db_path,
        document_id="doc-1",
        conversation_id="conv-test",
        filename="sample_financials.pdf",
        file_type="pdf",
        content="Key findings:\nRevenue grew 12% YoY.\nMargins improved by 150 bps.",
        metadata={"file_size": 1280},
    )

    context = build_uploaded_document_context(
        "summarize the uploaded financial document",
        bot.conversation.conversation_id,
        Path(bot.settings.database_path),
    )

    assert context is not None
    assert "sample_financials.pdf" in context
    assert "Revenue grew 12% YoY." in context
    assert "Margins improved by 150 bps." in context
    assert "UPLOADED FINANCIAL DOCUMENTS" in context


def test_uploaded_document_context_handles_empty_text(chatbot):
    bot, db_path = chatbot

    _insert_document(
        db_path,
        document_id="doc-2",
        conversation_id="conv-test",
        filename="scanned_statement.png",
        file_type="image",
        content="",
        metadata={"warnings": ["Text extraction not available"]},
    )

    context = build_uploaded_document_context(
        "explain the uploaded statement",
        bot.conversation.conversation_id,
        Path(bot.settings.database_path),
    )

    assert context is not None
    assert "scanned_statement.png" in context
    assert "[No readable text extracted]" in context
    assert "Text extraction not available" in context


def test_uploaded_document_context_prioritises_query_snippet(chatbot):
    bot, db_path = chatbot

    content = (
        "Apples are nutritious and popular across many diets.\n\n"
        "Oranges deliver high vitamin C levels and support immune health."
    )

    _insert_document(
        db_path,
        document_id="doc-3",
        conversation_id="conv-test",
        filename="fruits.txt",
        file_type="text",
        content=content,
    )

    context = build_uploaded_document_context(
        "Tell me about oranges",
        bot.conversation.conversation_id,
        Path(bot.settings.database_path),
    )

    assert context is not None
    assert "fruits.txt" in context
    assert "Oranges deliver high vitamin C levels" in context
    orange_idx = context.find("Oranges deliver")
    apple_idx = context.find("Apples are nutritious")
    assert orange_idx != -1
    if apple_idx != -1:
        assert orange_idx < apple_idx


