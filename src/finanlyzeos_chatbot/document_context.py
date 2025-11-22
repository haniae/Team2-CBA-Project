from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Iterable, List, Optional, Set, Tuple

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
    file_ids: Optional[List[str]] = None,  # Explicit file IDs to include
    max_documents: int = 3,
    max_chars: int = 100000,  # ChatGPT-style: ~110k tokens = ~440k chars, but we use 100k for safety
    max_snippet_per_doc: int = 50000,  # ChatGPT-style: Include substantial chunks directly
    chunk_overlap: int = 200,
    use_semantic_search: bool = True,
) -> Optional[str]:
    """
    Build context from uploaded documents using ChatGPT-style hybrid approach:
    1. Direct injection: First ~100k chars directly in prompt (like ChatGPT's 110k tokens)
    2. Vector search: For remaining content, retrieve relevant chunks dynamically
    
    Args:
        file_ids: Explicit list of document IDs to include. If provided, only these documents will be used.
        use_semantic_search: If True, use vector search when available; 
                            falls back to token overlap if vector store unavailable.
    """
    if not conversation_id and not file_ids:
        return None

    # If explicit file_ids provided, fetch those documents directly
    if file_ids:
        LOGGER.info("\n" + "="*80)
        LOGGER.info("BUILDING DOCUMENT CONTEXT FROM EXPLICIT FILE IDs")
        LOGGER.info("="*80)
        LOGGER.info(f"📎 Requested file_ids: {file_ids}")
        LOGGER.info(f"📁 Database path: {database_path}")
        
        try:
            documents = database.fetch_uploaded_documents_by_ids(
                database_path,
                file_ids,
            )
            
            LOGGER.info(f"🔍 Database query returned {len(documents) if documents else 0} documents")
            
            if not documents:
                LOGGER.warning(f"❌ No documents found for file_ids: {file_ids}")
                LOGGER.warning(f"💡 Possible issues:")
                LOGGER.warning(f"   - Document IDs don't exist in database")
                LOGGER.warning(f"   - Document IDs format mismatch")
                LOGGER.warning(f"   - Database connection issue")
                LOGGER.warning("="*80)
                return None
            
            LOGGER.info(f"✅ Found {len(documents)} documents:")
            for i, doc in enumerate(documents, 1):
                content_len = len(doc.content) if doc.content else 0
                LOGGER.info(f"   {i}. {doc.filename} (ID: {doc.document_id}, Content: {content_len} chars)")
            # ChatGPT-style direct injection: Include first ~100k chars directly
            # This matches ChatGPT's approach of injecting first 110k tokens directly
            banner = "=" * 80
            sections: List[str] = []
            remaining_chars = max(max_chars, 0)
            
            # Calculate chars per document (ChatGPT distributes 110k tokens across multiple docs)
            if len(documents) > 1:
                chars_per_doc = max(remaining_chars // len(documents), 10000)  # At least 10k per doc
            else:
                chars_per_doc = remaining_chars
            
            for record in documents:
                metadata = record.metadata or {}
                text = (record.content or "").strip()
                
                if not text:
                    continue
                
                # ChatGPT-style: Include first N chars directly (like 110k tokens)
                # For multiple files, distribute the budget
                doc_budget = min(chars_per_doc, remaining_chars) if remaining_chars > 0 else chars_per_doc
                snippet_len = min(len(text), doc_budget)
                file_snippet = text[:snippet_len]
                
                # If there's more content, note it (ChatGPT uses vector search for the rest)
                if len(text) > snippet_len:
                    remaining_content_len = len(text) - snippet_len
                    file_snippet += f"\n\n[... {remaining_content_len:,} more characters available via search if needed ...]"
                
                if snippet_len:
                    remaining_chars = max(remaining_chars - snippet_len, 0) if remaining_chars > 0 else 0
                
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
                
                section_lines.append("Content:")
                section_lines.append(file_snippet.strip() or "[No readable text extracted]")
                
                sections.append("\n".join(section_lines))
                
                if remaining_chars == 0:
                    break
            
            if not sections:
                return None
            
            header = [
                banner,
                "UPLOADED FILES (Explicitly Selected)",
                "",
                "⚠️ IMPORTANT: The user has uploaded these files and is asking you to analyze them.",
                "You MUST use the content from these files to answer the user's question.",
                "DO NOT say 'I don't have access to external documents' - you have the file content below.",
                "Reference specific parts of the files (page numbers, sections, data points) in your response.",
                "",
                banner,
            ]
            body = f"\n\n{banner}\n".join(sections)
            result = "\n".join(header) + "\n\n" + body
            
            LOGGER.info(f"✅ Built document context from {len(sections)} files, total length: {len(result)} chars")
            LOGGER.info(f"📝 Final context preview (first 300 chars):\n{result[:300]}")
            LOGGER.info("="*80)
            return result
            
        except Exception as e:
            LOGGER.error(f"❌ Error fetching documents by IDs: {e}", exc_info=True)
            LOGGER.error(f"   Database path: {database_path}")
            LOGGER.error(f"   Database exists: {database_path.exists()}")
            LOGGER.error(f"   File IDs requested: {file_ids}")
            return None
    else:
        # No explicit file_ids provided - automatically fetch all files from conversation
        # ChatGPT-style hybrid approach: Direct injection + Vector search
        LOGGER.info("\n" + "="*80)
        LOGGER.info("AUTO-FETCHING DOCUMENTS FROM CONVERSATION (ChatGPT-style)")
        LOGGER.info("="*80)
        LOGGER.info(f"📎 No explicit file_ids - using all files from conversation_id: {conversation_id}")
        LOGGER.info(f"📁 Database path: {database_path}")
        
        # ChatGPT-style Step 1: Direct injection - fetch all documents and inject first ~100k chars
        # This matches ChatGPT's approach: first 110k tokens directly injected
        try:
            LOGGER.info(f"🔍 Step 1: Fetching documents for direct injection (conversation_id: {conversation_id})")
            documents = database.fetch_uploaded_documents(
                database_path,
                conversation_id,
                limit=max_documents * 2,  # Get more documents for direct injection
                include_unscoped=False,
            )
            
            if documents:
                LOGGER.info(f"✅ Found {len(documents)} documents for direct injection")
                for i, doc in enumerate(documents, 1):
                    content_len = len(doc.content) if doc.content else 0
                    LOGGER.info(f"   {i}. {doc.filename} (ID: {doc.document_id}, Content: {content_len} chars)")
                
                # ChatGPT-style: Build context with direct injection
                banner = "=" * 80
                sections: List[str] = []
                remaining_chars = max(max_chars, 0)
                
                # Calculate chars per document (ChatGPT distributes 110k tokens across multiple docs)
                if len(documents) > 1:
                    chars_per_doc = max(remaining_chars // len(documents), 20000)  # At least 20k per doc
                else:
                    chars_per_doc = remaining_chars
                
                for record in documents:
                    metadata = record.metadata or {}
                    text = (record.content or "").strip()
                    
                    if not text:
                        continue
                    
                    # ChatGPT-style: Include first N chars directly (like 110k tokens)
                    doc_budget = min(chars_per_doc, remaining_chars) if remaining_chars > 0 else chars_per_doc
                    snippet_len = min(len(text), doc_budget)
                    file_snippet = text[:snippet_len]
                    
                    # If there's more content, note it (ChatGPT uses vector search for the rest)
                    if len(text) > snippet_len:
                        remaining_content_len = len(text) - snippet_len
                        file_snippet += f"\n\n[... {remaining_content_len:,} more characters in this document ...]"
                    
                    if snippet_len:
                        remaining_chars = max(remaining_chars - snippet_len, 0) if remaining_chars > 0 else 0
                    
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
                    
                    section_lines.append("Content:")
                    section_lines.append(file_snippet.strip() or "[No readable text extracted]")
                    
                    sections.append("\n".join(section_lines))
                    
                    if remaining_chars == 0:
                        break
                
                if sections:
                    header = [
                        banner,
                        "UPLOADED FILES (Available in this conversation)",
                        "",
                        "⚠️ IMPORTANT: The user has uploaded these files and is asking you to analyze them.",
                        "You MUST use the content from these files to answer the user's question.",
                        "DO NOT say 'I don't have access to external documents' - you have the file content below.",
                        "Reference specific parts of the files (filenames, sections, data points) in your response.",
                        "",
                        banner,
                    ]
                    body = f"\n\n{banner}\n".join(sections)
                    result = "\n".join(header) + "\n\n" + body
                    
                    LOGGER.info(f"✅ Built document context using ChatGPT-style direct injection: {len(result)} chars from {len(sections)} files")
                    LOGGER.info(f"📝 Final context preview (first 300 chars):\n{result[:300]}")
                    LOGGER.info("="*80)
                    return result
            else:
                LOGGER.warning(f"⚠️ No documents found in conversation {conversation_id}")
                # Debug: Check database directly
                import sqlite3
                try:
                    with sqlite3.connect(database_path) as conn:
                        cursor = conn.execute(
                            "SELECT document_id, filename, conversation_id, LENGTH(content) as content_len FROM uploaded_documents WHERE conversation_id = ? LIMIT 10",
                            (conversation_id,)
                        )
                        rows = cursor.fetchall()
                        if rows:
                            LOGGER.warning(f"   ⚠️ Found {len(rows)} documents with matching conversation_id in database:")
                            for row in rows:
                                LOGGER.warning(f"      - ID: {row[0]}, Filename: {row[1]}, Conv: {row[2]}, Content: {row[3]} chars")
                        else:
                            LOGGER.warning(f"   ❌ No documents found with conversation_id: {conversation_id}")
                except Exception as db_e:
                    LOGGER.error(f"   Error checking database directly: {db_e}")
        except Exception as e:
            LOGGER.error(f"❌ Error fetching documents from conversation: {e}", exc_info=True)
        
        # Step 2: Fallback to vector search if direct injection didn't work
        if use_semantic_search:
            try:
                from .rag_retriever import VectorStore
                
                vector_store = VectorStore(database_path)
                if vector_store._available:
                    LOGGER.info(f"🔍 Step 2: Trying vector search as fallback")
                    filter_metadata = {}
                    if conversation_id:
                        filter_metadata["conversation_id"] = conversation_id
                    
                    results = vector_store.search_uploaded_docs(
                        query=user_input,
                        n_results=max_documents,
                        filter_metadata=filter_metadata if filter_metadata else None,
                    )
                    
                    if results:
                        LOGGER.info(f"✅ Vector search found {len(results)} relevant chunks")
                        return _format_semantic_search_results(results, max_chars)
            except (ImportError, Exception) as e:
                LOGGER.debug(f"Vector search unavailable: {e}")
        
        # No documents found
        return None


def _format_semantic_search_results(
    results: List[Any],  # List[RetrievedDocument]
    max_chars: int = 6000,
) -> str:
    """Format semantic search results from vector store."""
    banner = "=" * 80
    sections: List[str] = []
    remaining_chars = max(max_chars, 0)
    
    for result in results:
        if remaining_chars <= 0:
            break
            
        metadata = result.metadata or {}
        text = result.text or ""
        
        # Truncate if needed
        if len(text) > remaining_chars:
            text = text[:remaining_chars].rstrip() + "\n[…]"
            remaining_chars = 0
        else:
            remaining_chars -= len(text)
        
        section_lines = [
            f"Filename: {metadata.get('filename', 'unknown')}",
            f"Type: {metadata.get('file_type', 'unknown')}",
        ]
        
        if result.score is not None:
            # Convert distance to similarity (ChromaDB returns distance, lower = more similar)
            similarity = 1.0 - result.score if result.score <= 1.0 else 1.0 / (1.0 + result.score)
            section_lines.append(f"Relevance Score: {similarity:.2f}")
        
        uploaded_at = metadata.get("uploaded_at")
        if uploaded_at:
            section_lines.append(f"Uploaded: {uploaded_at}")
        
        section_lines.append("Content Preview:")
        section_lines.append(text.strip() or "[No readable text extracted]")
        
        sections.append("\n".join(section_lines))
    
    if not sections:
        return None
    
    header = [
        banner,
        "UPLOADED FINANCIAL DOCUMENTS (Semantic Search)",
        "",
        "⚠️ IMPORTANT: The user has uploaded these documents and is asking you to analyze them.",
        "You MUST use the content from these documents to answer the user's question.",
        "DO NOT say 'I don't have access to external documents' - you have the document content below.",
        "Reference specific parts of the documents (filenames, sections, data points) in your response.",
        "",
        banner,
    ]
    body = f"\n\n{banner}\n".join(sections)
    return "\n".join(header) + "\n\n" + body
