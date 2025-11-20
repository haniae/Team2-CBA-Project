"""
SEC Filing Parser for RAG Pipeline

Extracts narrative sections from SEC filings for vectorization:
- Management's Discussion and Analysis (MD&A)
- Risk Factors
- Business Overview
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional

LOGGER = logging.getLogger(__name__)


def extract_sections_from_filing(
    filing_text: str,
    ticker: str,
    filing_type: str,
    fiscal_year: int,
    source_url: str,
    filing_date: Optional[str] = None,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Extract narrative sections from SEC filing text and chunk them for vectorization.
    
    Returns list of dicts with 'text' and 'metadata' for each section/chunk.
    """
    if not filing_text or not filing_text.strip():
        return []
    
    sections = []
    
    # Clean HTML tags if present
    filing_text = re.sub(r'<[^>]+>', ' ', filing_text)
    filing_text = re.sub(r'\s+', ' ', filing_text)
    filing_text = filing_text.strip()
    
    # Define section patterns for 10-K filings
    section_patterns = {
        "MD&A": [
            r"ITEM\s+7[\.\s]+MANAGEMENT['\s]S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"ITEM\s+7A[\.\s]+QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES",
            r"MANAGEMENT['\s]S\s+DISCUSSION\s+AND\s+ANALYSIS",
        ],
        "Risk Factors": [
            r"ITEM\s+1A[\.\s]+RISK\s+FACTORS",
            r"RISK\s+FACTORS",
        ],
        "Business Overview": [
            r"ITEM\s+1[\.\s]+BUSINESS",
            r"BUSINESS\s+OVERVIEW",
            r"DESCRIPTION\s+OF\s+BUSINESS",
        ],
    }
    
    # For 10-Q filings, adjust patterns
    if filing_type == "10-Q":
        section_patterns["MD&A"] = [
            r"ITEM\s+2[\.\s]+MANAGEMENT['\s]S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"MANAGEMENT['\s]S\s+DISCUSSION\s+AND\s+ANALYSIS",
        ]
    
    extracted_sections = {}
    
    for section_name, patterns in section_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, filing_text, re.IGNORECASE)
            if match:
                start_idx = match.start()
                
                # Find end of section
                next_item_match = re.search(
                    r"ITEM\s+\d+[A-Z]?[\.\s]+",
                    filing_text[start_idx + 100:],
                    re.IGNORECASE,
                )
                if next_item_match:
                    end_idx = start_idx + 100 + next_item_match.start()
                else:
                    end_match = re.search(
                        r"(SIGNATURES|CERTIFICATION|EXHIBIT)",
                        filing_text[start_idx + 100:],
                        re.IGNORECASE,
                    )
                    if end_match:
                        end_idx = start_idx + 100 + end_match.start()
                    else:
                        end_idx = len(filing_text)
                
                section_text = filing_text[start_idx:end_idx].strip()
                
                if len(section_text) > 500:
                    extracted_sections[section_name] = section_text
                    break
    
    # Chunk each section
    for section_name, section_text in extracted_sections.items():
        chunks = _chunk_text(section_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        
        for chunk_idx, chunk_text in enumerate(chunks):
            sections.append({
                "text": chunk_text,
                "metadata": {
                    "ticker": ticker.upper(),
                    "filing_type": filing_type,
                    "fiscal_year": fiscal_year,
                    "section": section_name,
                    "source_url": source_url,
                    "filing_date": filing_date,
                    "chunk_index": chunk_idx,
                    "total_chunks": len(chunks),
                }
            })
    
    return sections


def _chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
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
        
        chunks.append(chunk.strip())
        start = end - chunk_overlap
        if start >= text_length:
            break
    
    return chunks
