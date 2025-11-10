"""
Framework Upload and Processing System

Extracts KPI definitions, methodology, and structure from uploaded frameworks
and uses them to guide chatbot responses.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import database
from .document_processor import extract_text_from_file

LOGGER = logging.getLogger(__name__)


@dataclass
class Framework:
    """Represents an uploaded framework."""
    framework_id: str
    user_id: str
    name: str
    file_type: str
    file_path: str
    extracted_content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "framework_id": self.framework_id,
            "user_id": self.user_id,
            "name": self.name,
            "file_type": self.file_type,
            "file_path": self.file_path,
            "extracted_content": self.extracted_content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FrameworkKPI:
    """Represents a KPI extracted from a framework."""
    framework_id: str
    kpi_name: str
    kpi_definition: Optional[str]
    extracted_from: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "framework_id": self.framework_id,
            "kpi_name": self.kpi_name,
            "kpi_definition": self.kpi_definition,
            "extracted_from": self.extracted_from,
        }


@dataclass
class FrameworkMethodology:
    """Represents methodology extracted from a framework."""
    framework_id: str
    section: str
    content: str
    applies_to: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "framework_id": self.framework_id,
            "section": self.section,
            "content": self.content,
            "applies_to": self.applies_to,
        }


class FrameworkExtractor:
    """Extracts structure and content from uploaded frameworks."""
    
    def __init__(self):
        self.kpi_patterns = [
            r'(?:KPI|Metric|Indicator)\s*[:\-]?\s*([A-Za-z\s]+?)\s*[=:]\s*(.+?)(?:\n|$)',
            r'([A-Za-z\s]+?)\s*=\s*([^=\n]+?)(?:\n|$)',
            r'(?:Define|Calculate|Measure)\s+([A-Za-z\s]+?)\s+as\s+(.+?)(?:\n|$)',
        ]
    
    def extract_kpis(self, text: str) -> List[Dict[str, str]]:
        """Extract KPI definitions from text."""
        kpis = []
        
        for pattern in self.kpi_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                kpi_name = match.group(1).strip()
                kpi_definition = match.group(2).strip()
                
                # Filter out false positives
                if len(kpi_name) > 3 and len(kpi_definition) > 5:
                    kpis.append({
                        "name": kpi_name,
                        "definition": kpi_definition,
                    })
        
        return kpis
    
    def extract_methodology(self, text: str) -> List[Dict[str, str]]:
        """Extract methodology sections from text."""
        methodology = []
        
        # Look for section headers
        section_pattern = r'(?:^|\n)(?:#{1,3}|##|###)\s*(.+?)(?:\n|$)'
        sections = re.finditer(section_pattern, text, re.MULTILINE)
        
        for section_match in sections:
            section_title = section_match.group(1).strip()
            
            # Find content until next section
            start_pos = section_match.end()
            next_section = re.search(section_pattern, text[start_pos:], re.MULTILINE)
            end_pos = next_section.start() if next_section else len(text)
            
            content = text[start_pos:start_pos + end_pos].strip()
            
            if content and len(content) > 20:
                methodology.append({
                    "section": section_title,
                    "content": content,
                })
        
        return methodology
    
    def extract_structure(self, text: str) -> Dict[str, Any]:
        """Extract document structure."""
        structure = {
            "headings": [],
            "tables": [],
            "lists": [],
        }
        
        # Extract headings
        heading_pattern = r'^(?:#{1,6}|##|###|####)\s*(.+?)$'
        headings = re.findall(heading_pattern, text, re.MULTILINE)
        structure["headings"] = headings
        
        # Extract tables (markdown format)
        table_pattern = r'\|.+\|'
        tables = re.findall(table_pattern, text, re.MULTILINE)
        structure["tables"] = tables[:10]  # Limit to first 10 tables
        
        return structure


class FrameworkProcessor:
    """Processes and manages uploaded frameworks."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.extractor = FrameworkExtractor()
    
    def upload_framework(
        self,
        user_id: str,
        name: str,
        file_path: Path,
        file_type: str
    ) -> Framework:
        """Upload and process a framework."""
        # Extract text from file
        text, detected_type = extract_text_from_file(file_path)
        if not text:
            raise ValueError(f"Could not extract text from {file_path}")
        
        file_type = file_type or detected_type or "unknown"
        
        # Extract content
        kpis = self.extractor.extract_kpis(text)
        methodology = self.extractor.extract_methodology(text)
        structure = self.extractor.extract_structure(text)
        
        extracted_content = {
            "text": text[:10000],  # Limit text length
            "kpis": kpis,
            "methodology": methodology,
            "structure": structure,
        }
        
        metadata = {
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "text_length": len(text),
            "kpi_count": len(kpis),
            "methodology_sections": len(methodology),
        }
        
        framework_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        framework = Framework(
            framework_id=framework_id,
            user_id=user_id,
            name=name,
            file_type=file_type,
            file_path=str(file_path),
            extracted_content=extracted_content,
            metadata=metadata,
            created_at=now,
        )
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO frameworks (framework_id, user_id, name, file_type, file_path, extracted_content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    framework.framework_id,
                    framework.user_id,
                    framework.name,
                    framework.file_type,
                    framework.file_path,
                    json.dumps(framework.extracted_content),
                    json.dumps(framework.metadata),
                    framework.created_at.isoformat(),
                ),
            )
            
            # Save KPIs
            for kpi in kpis:
                conn.execute(
                    """
                    INSERT INTO framework_kpis (framework_id, kpi_name, kpi_definition, extracted_from)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        framework_id,
                        kpi["name"],
                        kpi.get("definition"),
                        "text",
                    ),
                )
            
            # Save methodology
            for method in methodology:
                conn.execute(
                    """
                    INSERT INTO framework_methodology (framework_id, section, content, applies_to)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        framework_id,
                        method["section"],
                        method["content"],
                        None,
                    ),
                )
            
            conn.commit()
        
        return framework
    
    def get_framework(self, framework_id: str) -> Optional[Framework]:
        """Get a framework by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT framework_id, user_id, name, file_type, file_path, extracted_content, metadata, created_at
                FROM frameworks
                WHERE framework_id = ?
                """,
                (framework_id,),
            ).fetchone()
            
            if not row:
                return None
            
            return Framework(
                framework_id=row["framework_id"],
                user_id=row["user_id"],
                name=row["name"],
                file_type=row["file_type"],
                file_path=row["file_path"],
                extracted_content=json.loads(row["extracted_content"]) if row["extracted_content"] else {},
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
            )
    
    def list_frameworks(self, user_id: str) -> List[Framework]:
        """List all frameworks for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT framework_id, user_id, name, file_type, file_path, extracted_content, metadata, created_at
                FROM frameworks
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            
            return [
                Framework(
                    framework_id=row["framework_id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    file_type=row["file_type"],
                    file_path=row["file_path"],
                    extracted_content=json.loads(row["extracted_content"]) if row["extracted_content"] else {},
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]
    
    def get_framework_kpis(self, framework_id: str) -> List[FrameworkKPI]:
        """Get all KPIs extracted from a framework."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT framework_id, kpi_name, kpi_definition, extracted_from
                FROM framework_kpis
                WHERE framework_id = ?
                """,
                (framework_id,),
            ).fetchall()
            
            return [
                FrameworkKPI(
                    framework_id=row["framework_id"],
                    kpi_name=row["kpi_name"],
                    kpi_definition=row["kpi_definition"],
                    extracted_from=row["extracted_from"],
                )
                for row in rows
            ]
    
    def get_framework_methodology(self, framework_id: str) -> List[FrameworkMethodology]:
        """Get all methodology sections from a framework."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT framework_id, section, content, applies_to
                FROM framework_methodology
                WHERE framework_id = ?
                """,
                (framework_id,),
            ).fetchall()
            
            return [
                FrameworkMethodology(
                    framework_id=row["framework_id"],
                    section=row["section"],
                    content=row["content"],
                    applies_to=row["applies_to"],
                )
                for row in rows
            ]
    
    def build_framework_context(self, framework_id: str) -> str:
        """Build context string from framework for LLM."""
        framework = self.get_framework(framework_id)
        if not framework:
            return ""
        
        context_parts = [f"Framework: {framework.name}\n"]
        
        # Add KPIs
        kpis = self.get_framework_kpis(framework_id)
        if kpis:
            context_parts.append("\n## KPIs:\n")
            for kpi in kpis:
                context_parts.append(f"- {kpi.kpi_name}: {kpi.kpi_definition or 'N/A'}\n")
        
        # Add methodology
        methodology = self.get_framework_methodology(framework_id)
        if methodology:
            context_parts.append("\n## Methodology:\n")
            for method in methodology[:5]:  # Limit to first 5 sections
                context_parts.append(f"### {method.section}\n{method.content[:500]}\n")
        
        return "\n".join(context_parts)



