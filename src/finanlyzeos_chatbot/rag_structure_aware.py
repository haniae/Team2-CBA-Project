"""
Structure-Aware & Table-Aware RAG

Handles structured content in financial documents:
- Parses tables from SEC filings
- Identifies document sections (MD&A, Risk Factors, etc.)
- Returns specific table rows/columns instead of dumping whole text
- Routes table queries to table-specific retrieval
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class DocumentSection:
    """Represents a section in a document."""
    name: str  # e.g., "MD&A", "Risk Factors"
    text: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]


@dataclass
class TableRow:
    """Represents a row in a table."""
    headers: List[str]
    values: List[str]
    metadata: Dict[str, Any]


@dataclass
class DocumentTable:
    """Represents a table in a document."""
    title: Optional[str]
    headers: List[str]
    rows: List[TableRow]
    metadata: Dict[str, Any]


class StructureAwareParser:
    """
    Parses document structure (sections, tables) from text.
    
    Identifies:
    - Section headers (MD&A, Risk Factors, Segment Info, etc.)
    - Tables (revenue by segment, geography, etc.)
    - Footnotes
    """
    
    # Common SEC filing section patterns
    SECTION_PATTERNS = [
        r'(?:^|\n)\s*(?:Item\s+\d+[.:]?\s*)?(?:Management[’\']?s?\s+Discussion\s+and\s+Analysis|MD&A)',
        r'(?:^|\n)\s*(?:Item\s+\d+[.:]?\s*)?(?:Risk\s+Factors)',
        r'(?:^|\n)\s*(?:Item\s+\d+[.:]?\s*)?(?:Segment\s+Information|Segment\s+Results)',
        r'(?:^|\n)\s*(?:Item\s+\d+[.:]?\s*)?(?:Financial\s+Statements)',
        r'(?:^|\n)\s*(?:Item\s+\d+[.:]?\s*)?(?:Notes\s+to\s+Financial\s+Statements)',
    ]
    
    def parse_sections(self, text: str) -> List[DocumentSection]:
        """
        Parse document sections from text.
        
        Args:
            text: Document text
        
        Returns:
            List of DocumentSection
        """
        sections = []
        
        for pattern in self.SECTION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_name = match.group(0).strip()
                start_pos = match.start()
                
                # Find end of section (next section or end of document)
                next_match = None
                for next_pattern in self.SECTION_PATTERNS:
                    next_matches = list(re.finditer(next_pattern, text[start_pos + 100:], re.IGNORECASE | re.MULTILINE))
                    if next_matches:
                        if next_match is None or next_matches[0].start() < next_match.start():
                            next_match = next_matches[0]
                
                if next_match:
                    end_pos = start_pos + 100 + next_match.start()
                else:
                    end_pos = len(text)
                
                section_text = text[start_pos:end_pos]
                
                sections.append(DocumentSection(
                    name=section_name,
                    text=section_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    metadata={"pattern": pattern},
                ))
        
        LOGGER.debug(f"Parsed {len(sections)} sections from document")
        return sections
    
    def parse_tables(self, text: str) -> List[DocumentTable]:
        """
        Parse tables from text.
        
        Args:
            text: Document text
        
        Returns:
            List of DocumentTable
        """
        tables = []
        
        # Simple table detection: look for pipe-separated or tab-separated rows
        # More sophisticated parsing would use HTML/XML parsing for XBRL
        
        # Pattern 1: Markdown-style tables (| col1 | col2 |)
        markdown_table_pattern = r'\|[^\n]+\|\n(?:\|[^\n]+\|\n)*'
        markdown_matches = re.finditer(markdown_table_pattern, text, re.MULTILINE)
        
        for match in markdown_matches:
            table_text = match.group(0)
            lines = [line.strip() for line in table_text.split('\n') if line.strip()]
            
            if len(lines) < 2:
                continue
            
            # First line is usually headers
            headers = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
            
            # Skip separator line (|---|---|)
            data_lines = lines[1:]
            rows = []
            for line in data_lines:
                if re.match(r'^[\|\s\-:]+$', line):  # Separator line
                    continue
                values = [cell.strip() for cell in line.split('|') if cell.strip()]
                if len(values) == len(headers):
                    rows.append(TableRow(
                        headers=headers,
                        values=values,
                        metadata={},
                    ))
            
            if rows:
                tables.append(DocumentTable(
                    title=None,
                    headers=headers,
                    rows=rows,
                    metadata={"format": "markdown"},
                ))
        
        LOGGER.debug(f"Parsed {len(tables)} tables from document")
        return tables
    
    def serialize_table(self, table: DocumentTable, ticker: str, period: str) -> str:
        """
        Serialize table as text for retrieval.
        
        Args:
            table: DocumentTable
            ticker: Ticker symbol
            period: Period (e.g., "FY2023")
        
        Returns:
            Serialized table text
        """
        lines = []
        if table.title:
            lines.append(f"Table: {table.title}")
        
        lines.append(f"Table: {', '.join(table.headers)} | Ticker={ticker} | Period={period}")
        
        for row in table.rows:
            row_text = " | ".join(f"{h}={v}" for h, v in zip(row.headers, row.values))
            lines.append(f"  - {row_text}")
        
        return "\n".join(lines)


class TableAwareRetriever:
    """
    Table-aware retriever that routes table queries to table-specific retrieval.
    """
    
    def __init__(self, structure_parser: Optional[StructureAwareParser] = None):
        """
        Initialize table-aware retriever.
        
        Args:
            structure_parser: StructureAwareParser instance
        """
        self.structure_parser = structure_parser or StructureAwareParser()
        self.table_index: Dict[str, List[DocumentTable]] = {}  # doc_id -> tables
    
    def is_table_query(self, query: str) -> bool:
        """
        Check if query is asking for table data.
        
        Args:
            query: User query
        
        Returns:
            True if query is table-related
        """
        query_lower = query.lower()
        table_keywords = [
            "by segment", "by region", "by geography", "by product",
            "breakdown", "table", "segment revenue", "geographic revenue",
            "revenue breakdown", "by division", "by business unit",
        ]
        return any(keyword in query_lower for keyword in table_keywords)
    
    def index_tables(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        """
        Index tables from a document.
        
        Args:
            doc_id: Document ID
            text: Document text
            metadata: Document metadata
        """
        tables = self.structure_parser.parse_tables(text)
        if tables:
            self.table_index[doc_id] = tables
            LOGGER.debug(f"Indexed {len(tables)} tables for document {doc_id}")
    
    def retrieve_tables(
        self,
        query: str,
        ticker: Optional[str] = None,
        period: Optional[str] = None,
    ) -> List[str]:
        """
        Retrieve relevant table data for query.
        
        Args:
            query: User query
            ticker: Optional ticker filter
            period: Optional period filter
        
        Returns:
            List of serialized table texts
        """
        if not self.is_table_query(query):
            return []
        
        results = []
        for doc_id, tables in self.table_index.items():
            for table in tables:
                # Simple relevance check: keyword matching
                table_text = " ".join(table.headers)
                query_keywords = set(re.findall(r'\b\w+\b', query.lower()))
                table_keywords = set(re.findall(r'\b\w+\b', table_text.lower()))
                
                overlap = query_keywords & table_keywords
                if len(overlap) > 0:
                    # Serialize table
                    serialized = self.structure_parser.serialize_table(
                        table, ticker or "UNKNOWN", period or "UNKNOWN"
                    )
                    results.append(serialized)
        
        LOGGER.debug(f"Retrieved {len(results)} tables for query '{query[:50]}...'")
        return results

