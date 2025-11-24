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
    
    # Clean HTML/XML tags if present (more aggressive cleaning)
    filing_text = re.sub(r'<[^>]+>', ' ', filing_text)
    # Remove XML entities
    filing_text = re.sub(r'&[a-z]+;', ' ', filing_text, flags=re.IGNORECASE)
    # Normalize whitespace but preserve some structure
    filing_text = re.sub(r'\s+', ' ', filing_text)
    # Remove excessive punctuation/formatting
    filing_text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\'\"]+', ' ', filing_text)
    filing_text = filing_text.strip()
    
    # Debug: Log if text seems too short or malformed
    if len(filing_text) < 1000:
        LOGGER.warning(f"Filing text seems very short ({len(filing_text)} chars) - may be malformed")
    
    # Define section patterns for 10-K filings (more flexible patterns)
    section_patterns = {
        "MD&A": [
            r"ITEM\s+7[\.\s]*MANAGEMENT['\s]*S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"ITEM\s+7A[\.\s]*QUANTITATIVE\s+AND\s+QUALITATIVE",
            r"MANAGEMENT['\s]*S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"MANAGEMENT['\s]*S\s+DISCUSSION",
            r"MD&A",
            r"MD\s*&\s*A",
        ],
        "Risk Factors": [
            r"ITEM\s+1A[\.\s]*RISK\s+FACTORS",
            r"ITEM\s+1[A-Z]?[\.\s]*RISK\s+FACTORS",
            r"RISK\s+FACTORS",
        ],
        "Business Overview": [
            r"ITEM\s+1[\.\s]*BUSINESS",
            r"ITEM\s+1[A-Z]?[\.\s]*BUSINESS",
            r"BUSINESS\s+OVERVIEW",
            r"DESCRIPTION\s+OF\s+BUSINESS",
            r"BUSINESS\s+DESCRIPTION",
        ],
    }
    
    # For 10-Q filings, adjust patterns
    if filing_type == "10-Q":
        section_patterns["MD&A"] = [
            r"ITEM\s+2[\.\s]*MANAGEMENT['\s]*S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"ITEM\s+2[A-Z]?[\.\s]*MANAGEMENT['\s]*S\s+DISCUSSION",
            r"MANAGEMENT['\s]*S\s+DISCUSSION\s+AND\s+ANALYSIS",
            r"MANAGEMENT['\s]*S\s+DISCUSSION",
            r"MD&A",
            r"MD\s*&\s*A",
        ]
    
    extracted_sections = {}
    
    # First, find all ITEM markers to help with section boundaries
    item_markers = []
    for match in re.finditer(r"ITEM\s+(\d+)([A-Z]?)[\.\s]+", filing_text, re.IGNORECASE):
        item_markers.append((match.start(), match.group(1), match.group(2)))
    
    # Try to extract each section type
    for section_name, patterns in section_patterns.items():
        # Skip if we already extracted this section
        if section_name in extracted_sections:
            continue
            
        for pattern in patterns:
            match = re.search(pattern, filing_text, re.IGNORECASE | re.MULTILINE)
            if match:
                start_idx = match.start()
                LOGGER.debug(f"Found {section_name} section at position {start_idx}")
                
                # Find end of section - look for next ITEM or section boundary
                # Search starting a bit after the match to avoid matching the same item
                search_start = start_idx + 200
                
                # Find the next ITEM marker after this position
                next_item_pos = None
                for item_pos, item_num, item_letter in item_markers:
                    if item_pos > search_start:
                        next_item_pos = item_pos
                        break
                
                if next_item_pos:
                    end_idx = next_item_pos
                else:
                    # Look for other section boundaries
                    end_match = re.search(
                        r"(SIGNATURES|CERTIFICATION|EXHIBIT|PART\s+II|PART\s+III|TABLE\s+OF\s+CONTENTS)",
                        filing_text[search_start:],
                        re.IGNORECASE,
                    )
                    if end_match:
                        end_idx = search_start + end_match.start()
                    else:
                        # Limit section size to prevent memory issues (max 50000 chars per section)
                        # But allow larger sections for very large filings
                        max_section_size = min(50000, len(filing_text) // 3)
                        end_idx = min(start_idx + max_section_size, len(filing_text))
                
                section_text = filing_text[start_idx:end_idx].strip()
                
                # More lenient minimum length
                if len(section_text) > 500:  # Increased from 300
                    extracted_sections[section_name] = section_text
                    LOGGER.debug(f"Extracted {section_name}: {len(section_text)} chars")
                    break
    
    # Fallback: If no sections found, try to extract multiple ITEM sections
    # This helps when standard patterns don't match but ITEM sections exist
    if not extracted_sections and len(filing_text) > 1000:
        LOGGER.debug(f"No standard sections found in {filing_type} filing, trying ITEM-based extraction")
        
        # Find all ITEM sections and extract them as separate sections
        item_sections = []
        for i, (item_pos, item_num, item_letter) in enumerate(item_markers):
            # Determine section name based on ITEM number
            section_name = None
            if filing_type == "10-K":
                if item_num == "1" and not item_letter:
                    section_name = "Business Overview"
                elif item_num == "1" and item_letter == "A":
                    section_name = "Risk Factors"
                elif item_num == "7":
                    section_name = "MD&A"
                elif item_num == "7" and item_letter == "A":
                    section_name = "Quantitative Disclosures"
            elif filing_type == "10-Q":
                if item_num == "1":
                    section_name = "Financial Statements"
                elif item_num == "2":
                    section_name = "MD&A"
                elif item_num == "3":
                    section_name = "Controls and Procedures"
                elif item_num == "4":
                    section_name = "Risk Factors"
            
            # If we don't have a specific name, use generic
            if not section_name:
                section_name = f"ITEM {item_num}{item_letter}" if item_letter else f"ITEM {item_num}"
            
            # Find end of this section (next ITEM or end of document)
            if i + 1 < len(item_markers):
                end_pos = item_markers[i + 1][0]
            else:
                # Last section - look for document end markers
                end_match = re.search(
                    r"(SIGNATURES|CERTIFICATION|EXHIBIT)",
                    filing_text[item_pos:],
                    re.IGNORECASE,
                )
                if end_match:
                    end_pos = item_pos + end_match.start()
                else:
                    end_pos = min(item_pos + 50000, len(filing_text))
            
            section_text = filing_text[item_pos:end_pos].strip()
            
            # Only extract if substantial content
            if len(section_text) > 1000:
                item_sections.append((section_name, section_text))
        
        # Add extracted ITEM sections (limit to top 5 to avoid too many)
        for section_name, section_text in item_sections[:5]:
            if section_name not in extracted_sections:
                extracted_sections[section_name] = section_text
                LOGGER.debug(f"Extracted {section_name} via ITEM fallback: {len(section_text)} chars")
    
    # Last resort: If still nothing, try keyword-based extraction
    if not extracted_sections and len(filing_text) > 1000:
        LOGGER.debug(f"Trying keyword-based fallback extraction")
        
        # Try to find sections by keywords
        keyword_patterns = [
            (r"MANAGEMENT['\s]*S?\s+DISCUSSION", "Management Discussion"),
            (r"RISK\s+FACTORS?", "Risk Factors"),
            (r"BUSINESS\s+(?:OVERVIEW|DESCRIPTION)", "Business Description"),
        ]
        
        for pattern, section_name in keyword_patterns:
            matches = list(re.finditer(pattern, filing_text, re.IGNORECASE))
            if matches:
                # Take the first substantial match
                for match in matches:
                    start_idx = max(0, match.start() - 500)
                    # Find next section or limit size
                    next_match = None
                    for other_pattern, _ in keyword_patterns:
                        if other_pattern != pattern:
                            next_m = re.search(other_pattern, filing_text[match.end():], re.IGNORECASE)
                            if next_m and (next_match is None or next_m.start() < next_match.start()):
                                next_match = next_m
                    
                    if next_match:
                        end_idx = match.end() + next_match.start()
                    else:
                        end_idx = min(start_idx + 30000, len(filing_text))
                    
                    section_text = filing_text[start_idx:end_idx].strip()
                    if len(section_text) > 1000 and section_name not in extracted_sections:
                        extracted_sections[section_name] = section_text
                        LOGGER.debug(f"Extracted {section_name} via keyword: {len(section_text)} chars")
                        break
    
    # Final fallback: Extract middle portion if nothing else worked
    if not extracted_sections and len(filing_text) > 2000:
        start_pct = len(filing_text) // 10
        end_pct = len(filing_text) - (len(filing_text) // 10)
        fallback_text = filing_text[start_pct:end_pct].strip()
        if len(fallback_text) > 1000:
            extracted_sections["Filing Content"] = fallback_text
            LOGGER.debug(f"Final fallback: {len(fallback_text)} chars")
    
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
    if not text or len(text.strip()) == 0:
        return []
    
    if len(text) <= chunk_size:
        return [text.strip()]
    
    chunks = []
    start = 0
    text_length = len(text)
    # Limit chunks per section to prevent memory issues
    # For very large sections, cap at reasonable number
    max_chunks_per_section = 1000  # Restored to 1000 as requested
    
    while start < text_length and len(chunks) < max_chunks_per_section:
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
        
        chunk_text = chunk.strip()
        if chunk_text:  # Only add non-empty chunks
            chunks.append(chunk_text)
        
        start = end - chunk_overlap
        if start >= text_length or start < 0:
            break
    
    if not chunks and text.strip():
        # If chunking failed but we have text, return the whole thing (truncated)
        return [text[:chunk_size * 10].strip()]  # Max 10 chunks worth
    
    return chunks
