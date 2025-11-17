"""Tests for the document upload API accepting arbitrary file types."""

from __future__ import annotations

import json
from io import BytesIO
from types import SimpleNamespace
from pathlib import Path

import pytest
import sqlite3
from starlette.datastructures import UploadFile

from finanlyzeos_chatbot import database
from finanlyzeos_chatbot import web as web_module


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_document_upload_accepts_binary_file(tmp_path: Path, monkeypatch) -> None:
    """Binary/image uploads should succeed, store metadata, and surface a warning."""
    db_path = tmp_path / "chat.sqlite3"
    database.initialise(db_path)

    dummy_settings = SimpleNamespace(database_path=str(db_path))
    web_module.get_settings.cache_clear()
    monkeypatch.setattr(web_module, "load_settings", lambda: dummy_settings)

    binary_content = b"\x00\x00\x00\x00\x00"
    upload = UploadFile(
        filename="example.png",
        file=BytesIO(binary_content),
    )

    response = await web_module.document_upload(upload, conversation_id=None)

    assert response.success is True
    assert response.document_id
    assert response.conversation_id
    assert response.filename == "example.png"
    assert response.warnings, "Expected a warning when no text can be extracted"
    assert any("text" in warning.lower() for warning in response.warnings)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT filename, file_type, content, metadata FROM uploaded_documents"
        ).fetchone()

    assert row is not None
    assert row["filename"] == "example.png"
    assert row["content"] == ""  # stored even when no text extracted

    metadata = json.loads(row["metadata"])
    assert metadata["original_filename"] == "example.png"
    assert metadata.get("warnings"), "Metadata should record extraction warnings"

