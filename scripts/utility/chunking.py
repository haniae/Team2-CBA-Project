"""
Shared chunking utility for document indexing.
"""

from typing import List, Dict, Any


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
    max_chunks: int = 1000
) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        max_chunks: Maximum number of chunks to generate
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    if len(text) <= chunk_size:
        return [text.strip()]
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length and len(chunks) < max_chunks:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < text_length:
            sentence_end = max(
                chunk.rfind('. '),
                chunk.rfind('.\n'),
                chunk.rfind('? '),
                chunk.rfind('! '),
            )
            if sentence_end > chunk_size * 0.7:
                chunk = chunk[:sentence_end + 1]
                end = start + sentence_end + 1
        
        chunk_stripped = chunk.strip()
        if chunk_stripped:
            chunks.append(chunk_stripped)
        
        start = end - chunk_overlap
        if start >= text_length or start < 0:
            break
    
    return chunks


def create_document_chunks(
    text: str,
    metadata: Dict[str, Any],
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
    max_chunks: int = 1000
) -> List[Dict[str, Any]]:
    """
    Create document chunks with metadata.
    
    Args:
        text: Text to chunk
        metadata: Base metadata for all chunks
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        max_chunks: Maximum number of chunks
        
    Returns:
        List of document dicts with 'text' and 'metadata' keys
    """
    chunks = chunk_text(text, chunk_size, chunk_overlap, max_chunks)
    
    documents = []
    for chunk_idx, chunk_content in enumerate(chunks):
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_index"] = chunk_idx
        chunk_metadata["total_chunks"] = len(chunks)
        
        documents.append({
            "text": chunk_content,
            "metadata": chunk_metadata
        })
    
    return documents

