from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

from . import database

LOGGER = logging.getLogger(__name__)


def _tokenize(text: str, stopwords: Set[str]) -> List[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if token and token not in stopwords
    ]


def build_uploaded_document_context(
    user_input: str,
    conversation_id: Optional[str],
    database_path: Path,
    *,
    max_documents: int = 3,
    max_chars: int = 6000,
    max_snippet_per_doc: int = 2000,
    chunk_overlap: int = 200,
) -> Optional[str]:
    if not conversation_id:
        return None

    try:
        documents = database.fetch_uploaded_documents(
            database_path,
            conversation_id,
            limit=max_documents,
            include_unscoped=False,
        )
    except Exception:
        return None

    if not documents:
        return None

    banner = "=" * 80
    sections: List[str] = []
    remaining_chars = max(max_chars, 0)

    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "with",
        "for",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "this",
        "that",
        "these",
        "those",
        "about",
        "into",
        "from",
        "at",
        "as",
        "their",
        "its",
    }

    query_tokens = set(_tokenize(user_input, stopwords))
    if not query_tokens:
        query_tokens = set(re.findall(r"[a-z0-9]+", (user_input or "").lower()))

    def iter_chunks(text: str) -> Iterable[str]:
        snippet_limit = max(200, min(max_snippet_per_doc, 5000))
        overlap = max(0, min(chunk_overlap, snippet_limit - 50))
        normalized = (text or "").strip()
        if not normalized:
            return
        if len(normalized) <= snippet_limit:
            yield normalized
            return
        step = max(1, snippet_limit - overlap)
        start = 0
        text_length = len(normalized)
        while start < text_length:
            end = min(text_length, start + snippet_limit)
            chunk = normalized[start:end]
            boundary = chunk.rfind("\n\n")
            if boundary > snippet_limit * 0.4:
                chunk = chunk[:boundary]
                end = start + boundary
            yield chunk.strip()
            if end >= text_length:
                break
            start += step

    def focus_chunk(chunk: str, terms: Set[str]) -> str:
        if not chunk or not terms:
            return chunk
        lowered = chunk.lower()
        spans: List[Tuple[int, int]] = []
        for term in terms:
            term_lower = term.lower()
            idx = lowered.find(term_lower)
            if idx != -1:
                spans.append((idx, idx + len(term_lower)))
        if not spans:
            return chunk
        start_idx = min(span[0] for span in spans)
        end_idx = max(span[1] for span in spans)
        window_before = 150
        window_after = 250
        start = max(0, start_idx - window_before)
        end = min(len(chunk), end_idx + window_after)
        snippet = chunk[start:end].strip()
        prefix = "… " if start > 0 else ""
        suffix = " …" if end < len(chunk) else ""
        return f"{prefix}{snippet}{suffix}".strip()

    for record in documents:
        metadata = record.metadata or {}
        text = (record.content or "").strip()

        fallback_snippet = text[:max_snippet_per_doc].strip()
        best_chunk = ""
        best_score = -1.0
        matched_terms: Set[str] = set()

        for chunk in iter_chunks(text):
            if not chunk:
                continue
            chunk_tokens = set(_tokenize(chunk, stopwords))
            if not chunk_tokens:
                continue
            overlap = query_tokens & chunk_tokens
            overlap_count = len(overlap)
            coverage = overlap_count / max(len(query_tokens), 1)
            density = overlap_count / max(len(chunk_tokens), 1)
            score = overlap_count + 0.7 * coverage + 0.5 * density
            if score > best_score:
                best_score = score
                best_chunk = chunk
                matched_terms = overlap

        if not best_chunk:
            best_chunk = fallback_snippet or text[:200].strip()
            matched_terms = set()

        if matched_terms:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            selected: List[str] = []
            for sentence in sentences:
                lowered_sentence = sentence.lower()
                if any(term in lowered_sentence for term in matched_terms):
                    cleaned = sentence.strip()
                    if cleaned and cleaned not in selected:
                        selected.append(cleaned)
            if selected:
                best_chunk = " ".join(selected)
            else:
                best_chunk = focus_chunk(best_chunk, matched_terms)
        else:
            best_chunk = focus_chunk(best_chunk, matched_terms)

        snippet_len = len(best_chunk)
        if remaining_chars and snippet_len:
            if snippet_len > remaining_chars:
                best_chunk = best_chunk[:remaining_chars].rstrip() + "\n[…]"
                snippet_len = len(best_chunk)
            remaining_chars = max(remaining_chars - snippet_len, 0)

        section_lines = [
            f"Filename: {record.filename}",
            f"Type: {record.file_type or 'unknown'}",
        ]

        uploaded_at = None
        try:
            if record.uploaded_at:
                uploaded_at = record.uploaded_at.isoformat()
        except Exception:
            uploaded_at = None
        if uploaded_at:
            section_lines.append(f"Uploaded: {uploaded_at}")

        file_size = metadata.get("file_size")
        if file_size:
            section_lines.append(f"Size: {file_size} bytes")

        if matched_terms:
            section_lines.append(f"Matched Terms: {', '.join(sorted(matched_terms))}")
        elif best_score > 0:
            section_lines.append(f"Match Score: {best_score:.2f}")

        warning_entries = metadata.get("warnings")
        if warning_entries:
            if isinstance(warning_entries, str):
                warning_text = warning_entries
            else:
                warning_text = " ".join(str(item) for item in warning_entries if item)
            if warning_text:
                section_lines.append(f"Warnings: {warning_text}")

        section_lines.append("Content Preview:")
        section_lines.append(best_chunk.strip() or "[No readable text extracted]")

        sections.append("\n".join(section_lines))

        if remaining_chars == 0:
            break

    if not sections:
        return None

    header = [
        banner,
        "UPLOADED FINANCIAL DOCUMENTS",
        "Use these excerpts when answering the user's question. Cite filenames in your response.",
        banner,
    ]
    body = f"\n\n{banner}\n".join(sections)
    return "\n".join(header) + "\n\n" + body
