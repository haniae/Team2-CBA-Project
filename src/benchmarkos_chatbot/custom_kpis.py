"""
Custom KPI Calculation System

Allows users to define, save, and reuse custom financial metrics.
Supports formula parsing, calculation, and traceability.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Iterable

from . import database

LOGGER = logging.getLogger(__name__)


def _json_dumps(payload: Any) -> str:
    """Serialise payloads with deterministic separators."""
    return json.dumps(payload, separators=(",", ":"), default=str)


def _json_loads(payload: Optional[str]) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        LOGGER.warning("Failed to decode JSON payload; returning fallback dict", exc_info=True)
        return {}


@dataclass
class CustomKPIDefinition:
    """Structured representation of a KPI definition extracted from natural language."""

    name: str
    formula: str
    description: Optional[str] = None
    frequency: Optional[str] = None
    unit: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    source_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalised_name(self) -> str:
        return re.sub(r"\s+", "", self.name or "", flags=re.UNICODE)

    def to_metadata(self) -> Dict[str, Any]:
        meta = {
            "name": self.name,
            "formula": self.formula,
            "description": self.description,
            "inputs": sorted(set(self.inputs)),
            "frequency": self.frequency,
            "unit": self.unit,
            "source_tags": sorted(set(self.source_tags)),
        }
        if self.metadata:
            meta.update(self.metadata)
        return meta


@dataclass
class CustomKPI:
    """Represents a user-defined custom KPI."""

    kpi_id: str
    user_id: str
    name: str
    formula: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    frequency: Optional[str] = None
    unit: Optional[str] = None
    inputs: List[str] = field(default_factory=list)
    source_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        base = {
            "kpi_id": self.kpi_id,
            "user_id": self.user_id,
            "name": self.name,
            "formula": self.formula,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "frequency": self.frequency,
            "unit": self.unit,
            "inputs": self.inputs,
            "source_tags": self.source_tags,
            "metadata": self.metadata or {},
        }
        return base


@dataclass
class KPICalculationResult:
    """Result of calculating a custom KPI."""
    kpi_id: str
    kpi_name: str
    ticker: str
    period: str
    value: Optional[float]
    formatted_value: Optional[str]
    calculation_steps: List[Dict[str, Any]]
    dependencies: List[str]
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "kpi_id": self.kpi_id,
            "kpi_name": self.kpi_name,
            "ticker": self.ticker,
            "period": self.period,
            "value": self.value,
            "formatted_value": self.formatted_value,
            "calculation_steps": self.calculation_steps,
            "dependencies": self.dependencies,
            "sources": self.sources,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass(frozen=True)
class MetricValue:
    """Metric value with provenance."""

    metric: str
    value: Optional[float]
    period: Optional[str]
    fiscal_year: Optional[int]
    source: Optional[str]
    source_ref: Optional[str]
    cik: Optional[str]
    filing_date: Optional[str]
    url: Optional[str]


class KPIIntentParser:
    """Parse natural language instructions about custom KPIs."""

    _FREQUENCY_KEYWORDS = {
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "quarter": "quarterly",
        "quarterly": "quarterly",
        "annual": "annual",
        "annually": "annual",
        "yearly": "annual",
        "fy": "annual",
    }

    _UNIT_KEYWORDS = {
        "%": "pct",
        "percent": "pct",
        "percentage": "pct",
        "bps": "bps",
        "basis point": "bps",
        "usd": "usd",
        "dollar": "usd",
        "million": "usd_millions",
        "billions": "usd_billions",
    }

    def __init__(self) -> None:
        self._create_patterns = [
            re.compile(
                r"(?:create|define|set up)\s+(?:a\s+)?(?:custom\s+)?(?:kpi|metric)\s*(?:called|named)?\s*['\"]?([\w\s%-]+?)['\"]?\s*(?:=|as)\s*(.+)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:new\s+)?kpi\s+(?:called|named)\s*['\"]?([\w\s%-]+?)['\"]?\s*(?:=|as)\s*(.+)",
                re.IGNORECASE,
            ),
        ]
        self._calc_patterns = [
            re.compile(
                r"(?:calculate|compute|show|what\s+is)\s+(?:the\s+)?(?:custom\s+)?(?:kpi|metric)\s*['\"]?([\w\s%-]+?)['\"]?\s+(?:for|of)\s+([A-Za-z0-9.\-]+)",
                re.IGNORECASE,
            )
        ]
        self._list_pattern = re.compile(r"\b(list|show)\s+(?:my\s+)?(?:custom\s+)?(?:kpis?|metrics?)\b", re.IGNORECASE)

    def detect(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect KPI intent from free-form text."""
        if not text:
            return None

        for pattern in self._create_patterns:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                formula = match.group(2).strip()
                definition = self._definition_from_text(text, name, formula)
                return {
                    "action": "create",
                    "definition": definition,
                    "raw_name": name,
                    "raw_formula": formula,
                }

        for pattern in self._calc_patterns:
            match = pattern.search(text)
            if match:
                return {
                    "action": "calculate",
                    "kpi_name": match.group(1).strip(),
                    "ticker": match.group(2).strip().upper(),
                }

        if self._list_pattern.search(text):
            return {"action": "list"}

        return None

    def _definition_from_text(self, text: str, name: str, formula: str) -> CustomKPIDefinition:
        """Build structured KPI definition from natural language."""
        frequency = self._extract_frequency(text)
        unit = self._extract_unit(text, formula)
        inputs = self._extract_inputs(formula)
        source_tags = self._extract_source_tags(text, inputs)
        description = self._extract_description(text, name)

        metadata = {
            "prompt": text.strip(),
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }

        return CustomKPIDefinition(
            name=name.strip(),
            formula=formula.strip(),
            description=description,
            frequency=frequency,
            unit=unit,
            inputs=inputs,
            source_tags=source_tags,
            metadata=metadata,
        )

    def _extract_frequency(self, text: str) -> Optional[str]:
        lowered = text.lower()
        for keyword, canonical in self._FREQUENCY_KEYWORDS.items():
            if keyword in lowered:
                return canonical
        return None

    def _extract_unit(self, text: str, formula: str) -> Optional[str]:
        combined = f"{text} {formula}".lower()
        for keyword, canonical in self._UNIT_KEYWORDS.items():
            if keyword in combined:
                return canonical
        return None

    @staticmethod
    def _extract_inputs(formula: str) -> List[str]:
        """Use the formula parser style regex to collect potential metric inputs."""
        tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formula))
        cleaned: Set[str] = set()
        for token in tokens:
            if token.lower() in {"sum", "avg", "max", "min", "abs", "round"}:
                continue
            try:
                float(token)
                continue
            except ValueError:
                cleaned.add(token)
        return sorted(cleaned)

    def _extract_source_tags(self, text: str, inputs: Iterable[str]) -> List[str]:
        tags = set()
        for token in inputs:
            tags.add(token)
        for match in re.findall(r"\b([A-Z][A-Za-z0-9_]+)\b", text):
            tags.add(match)
        return sorted(tags)

    @staticmethod
    def _extract_description(text: str, name: str) -> Optional[str]:
        lowered = text.lower()
        if "description" in lowered or "note" in lowered:
            return text
        # Provide a lightweight default description
        return f"Custom KPI '{name.strip()}' defined via chat instruction"


class FormulaParser:
    """Parses and validates custom KPI formulas."""
    
    # Supported operators
    OPERATORS = ['+', '-', '*', '/', '(', ')']
    
    # Supported functions
    FUNCTIONS = ['SUM', 'AVG', 'MAX', 'MIN', 'ABS', 'ROUND']
    
    def __init__(self):
        self.metric_pattern = re.compile(r'\b([a-z_][a-z0-9_]*)\b', re.IGNORECASE)
    
    def parse_formula(self, formula: str) -> Tuple[str, List[str]]:
        """
        Parse formula and extract metric dependencies.
        
        Returns:
            Tuple of (normalized_formula, list_of_dependencies)
        """
        # Normalize whitespace
        formula = re.sub(r'\s+', ' ', formula.strip())
        
        # Extract potential metric names
        potential_metrics = set()
        for match in self.metric_pattern.finditer(formula):
            word = match.group(1).lower()
            # Skip if it's a function name
            if word.upper() in self.FUNCTIONS:
                continue
            # Skip if it's a number
            try:
                float(word)
                continue
            except ValueError:
                pass
            potential_metrics.add(word)
        
        return formula, sorted(list(potential_metrics))
    
    def validate_formula(self, formula: str) -> Tuple[bool, Optional[str]]:
        """
        Validate formula syntax.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for balanced parentheses
            if formula.count('(') != formula.count(')'):
                return False, "Unbalanced parentheses"
            
            # Check for valid characters
            valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_+-*/()[]., ')
            if not all(c in valid_chars for c in formula):
                return False, "Invalid characters in formula"
            
            # Basic syntax check - try to create a safe evaluation context
            test_context = {func.lower(): lambda *args: 0 for func in self.FUNCTIONS}
            test_context.update({f'metric_{i}': 1.0 for i in range(10)})
            
            # Replace metric names with test values
            test_formula = formula
            for i, metric in enumerate(self.parse_formula(formula)[1]):
                test_formula = re.sub(
                    rf'\b{re.escape(metric)}\b',
                    f'metric_{i}',
                    test_formula,
                    flags=re.IGNORECASE
                )
            
            # Try to compile (but don't execute)
            compile(test_formula, '<string>', 'eval')
            
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class CustomKPICalculator:
    """Calculates custom KPIs from formulas."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.parser = FormulaParser()
        self.intent_parser = KPIIntentParser()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    
    def create_kpi(
        self,
        user_id: str,
        name: str,
        formula: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        frequency: Optional[str] = None,
        unit: Optional[str] = None,
        inputs: Optional[List[str]] = None,
        source_tags: Optional[List[str]] = None,
    ) -> CustomKPI:
        """Create a new custom KPI."""
        definition = CustomKPIDefinition(
            name=name,
            formula=formula,
            description=description,
            frequency=frequency,
            unit=unit,
            inputs=inputs or [],
            source_tags=source_tags or [],
            metadata=metadata or {},
        )
        return self.create_kpi_from_definition(user_id=user_id, definition=definition)

    def create_kpi_from_definition(
        self,
        user_id: str,
        definition: CustomKPIDefinition,
    ) -> CustomKPI:
        """Create a KPI from a structured definition."""
        # Validate formula
        is_valid, error = self.parser.validate_formula(definition.formula)
        if not is_valid:
            raise ValueError(f"Invalid formula: {error}")
        
        # Parse formula to get dependencies
        normalized_formula, dependencies = self.parser.parse_formula(definition.formula)
        
        kpi_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        inputs = definition.inputs or dependencies
        source_tags = definition.source_tags or inputs
        metadata_payload = definition.to_metadata()

        kpi = CustomKPI(
            kpi_id=kpi_id,
            user_id=user_id,
            name=definition.name.strip(),
            formula=normalized_formula,
            description=definition.description,
            created_at=now,
            updated_at=now,
            frequency=definition.frequency,
            unit=definition.unit,
            inputs=inputs,
            source_tags=source_tags,
            metadata=metadata_payload,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO custom_kpis (
                    kpi_id,
                    user_id,
                    name,
                    formula,
                    description,
                    created_at,
                    updated_at,
                    frequency,
                    unit,
                    inputs,
                    source_tags,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kpi.kpi_id,
                    kpi.user_id,
                    kpi.name,
                    kpi.formula,
                    kpi.description,
                    kpi.created_at.isoformat(),
                    kpi.updated_at.isoformat(),
                    kpi.frequency,
                    kpi.unit,
                    _json_dumps(kpi.inputs),
                    _json_dumps(kpi.source_tags),
                    _json_dumps(metadata_payload),
                ),
            )
            
            # Save dependencies
            for metric_name in dependencies:
                conn.execute(
                    """
                    INSERT INTO kpi_dependencies (kpi_id, metric_name, dependency_type)
                    VALUES (?, ?, 'metric')
                    """,
                    (kpi_id, metric_name),
                )
            
            conn.commit()
            self._save_kpi_version(conn, kpi_id, normalized_formula, metadata_payload, user_id)
        
        return kpi

    def upsert_kpi(self, user_id: str, definition: CustomKPIDefinition) -> CustomKPI:
        """Create a KPI or update existing one by name."""
        existing = self.get_kpi_by_name(user_id, definition.name)
        if not existing:
            return self.create_kpi_from_definition(user_id, definition)

        is_valid, error = self.parser.validate_formula(definition.formula)
        if not is_valid:
            raise ValueError(f"Invalid formula: {error}")

        normalized_formula, dependencies = self.parser.parse_formula(definition.formula)
        now = datetime.now(timezone.utc)
        inputs = definition.inputs or dependencies
        source_tags = definition.source_tags or inputs
        metadata_payload = definition.to_metadata()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE custom_kpis
                SET formula = ?, description = ?, updated_at = ?, frequency = ?, unit = ?, inputs = ?, source_tags = ?, metadata = ?
                WHERE kpi_id = ? AND user_id = ?
                """,
                (
                    normalized_formula,
                    definition.description,
                    now.isoformat(),
                    definition.frequency,
                    definition.unit,
                    _json_dumps(inputs),
                    _json_dumps(source_tags),
                    _json_dumps(metadata_payload),
                    existing.kpi_id,
                    user_id,
                ),
            )

            conn.execute("DELETE FROM kpi_dependencies WHERE kpi_id = ?", (existing.kpi_id,))
            for metric_name in dependencies:
                conn.execute(
                    """
                    INSERT INTO kpi_dependencies (kpi_id, metric_name, dependency_type)
                    VALUES (?, ?, 'metric')
                    """,
                    (existing.kpi_id, metric_name),
                )

            self._save_kpi_version(conn, existing.kpi_id, normalized_formula, metadata_payload, user_id)
            conn.commit()

        return self.get_kpi(existing.kpi_id)  # type: ignore[return-value]
    
    def get_kpi(self, kpi_id: str) -> Optional[CustomKPI]:
        """Get a custom KPI by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT kpi_id, user_id, name, formula, description, created_at, updated_at, frequency, unit, inputs, source_tags, metadata
                FROM custom_kpis
                WHERE kpi_id = ?
                """,
                (kpi_id,),
            ).fetchone()
            
            if not row:
                return None
            
            return CustomKPI(
                kpi_id=row["kpi_id"],
                user_id=row["user_id"],
                name=row["name"],
                formula=row["formula"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                frequency=row["frequency"],
                unit=row["unit"],
                inputs=json.loads(row["inputs"]) if row["inputs"] else [],
                source_tags=json.loads(row["source_tags"]) if row["source_tags"] else [],
                metadata=_json_loads(row["metadata"]),
            )
    
    def get_kpi_by_name(self, user_id: str, name: str) -> Optional[CustomKPI]:
        """Retrieve KPI by case-insensitive name."""
        normalized = name.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT kpi_id, user_id, name, formula, description, created_at, updated_at, frequency, unit, inputs, source_tags, metadata
                FROM custom_kpis
                WHERE user_id = ? AND lower(name) = ?
                """,
                (user_id, normalized),
            ).fetchone()

            if not row:
                return None

            return CustomKPI(
                kpi_id=row["kpi_id"],
                user_id=row["user_id"],
                name=row["name"],
                formula=row["formula"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                frequency=row["frequency"],
                unit=row["unit"],
                inputs=json.loads(row["inputs"]) if row["inputs"] else [],
                source_tags=json.loads(row["source_tags"]) if row["source_tags"] else [],
                metadata=_json_loads(row["metadata"]),
            )

    def list_kpis(self, user_id: str) -> List[CustomKPI]:
        """List all custom KPIs for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT kpi_id, user_id, name, formula, description, created_at, updated_at, frequency, unit, inputs, source_tags, metadata
                FROM custom_kpis
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            
            return [
                CustomKPI(
                    kpi_id=row["kpi_id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    formula=row["formula"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    frequency=row["frequency"],
                    unit=row["unit"],
                    inputs=json.loads(row["inputs"]) if row["inputs"] else [],
                    source_tags=json.loads(row["source_tags"]) if row["source_tags"] else [],
                    metadata=_json_loads(row["metadata"]),
                )
                for row in rows
            ]

    def list_kpi_versions(self, kpi_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List version history for a KPI."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT version_number, formula, metadata, created_at, created_by
                FROM custom_kpi_versions
                WHERE kpi_id = ?
                ORDER BY version_number DESC
                LIMIT ?
                """,
                (kpi_id, limit),
            ).fetchall()

            history: List[Dict[str, Any]] = []
            for row in rows:
                history.append(
                    {
                        "version_number": row["version_number"],
                        "formula": row["formula"],
                        "metadata": _json_loads(row["metadata"]),
                        "created_at": row["created_at"],
                        "created_by": row["created_by"],
                    }
                )
            return history

    def get_kpi_usage(self, kpi_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent usage records for a KPI."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT ticker, period, value, calculated_at
                FROM custom_kpi_usage
                WHERE kpi_id = ?
                ORDER BY calculated_at DESC
                LIMIT ?
                """,
                (kpi_id, limit),
            ).fetchall()

            return [
                {
                    "ticker": row["ticker"],
                    "period": row["period"],
                    "value": row["value"],
                    "calculated_at": row["calculated_at"],
                }
                for row in rows
            ]
    
    def delete_kpi(self, kpi_id: str, user_id: str) -> bool:
        """Delete a custom KPI."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM custom_kpis
                WHERE kpi_id = ? AND user_id = ?
                """,
                (kpi_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def calculate_kpi(
        self,
        kpi_id: str,
        ticker: str,
        period: Optional[str] = None,
        fiscal_year: Optional[int] = None
    ) -> KPICalculationResult:
        """Calculate a custom KPI for a specific ticker and period."""
        kpi = self.get_kpi(kpi_id)
        if not kpi:
            return KPICalculationResult(
                kpi_id=kpi_id,
                kpi_name="Unknown",
                ticker=ticker,
                period=period or "unknown",
                value=None,
                calculation_steps=[],
                dependencies=[],
                sources=[],
                formatted_value=None,
                metadata={},
                error=f"KPI {kpi_id} not found",
            )
        
        # Get dependencies
        dependencies = self._get_dependencies(kpi_id) or kpi.inputs
        
        # Fetch metric values
        metric_values = self._fetch_metric_values(ticker, dependencies, period, fiscal_year)
        
        # Calculate formula
        calculation_steps = []
        sources = []
        
        try:
            value = self._evaluate_formula(kpi.formula, metric_values, calculation_steps, sources)
        except Exception as e:
            return KPICalculationResult(
                kpi_id=kpi_id,
                kpi_name=kpi.name,
                ticker=ticker,
                period=period or "unknown",
                value=None,
                calculation_steps=calculation_steps,
                dependencies=dependencies,
                sources=sources,
                formatted_value=None,
                metadata=kpi.metadata,
                error=str(e),
            )
        
        # Save usage
        self._save_usage(kpi_id, ticker, period or "latest", value)
        
        return KPICalculationResult(
            kpi_id=kpi_id,
            kpi_name=kpi.name,
            ticker=ticker,
            period=period or "latest",
            value=value,
            formatted_value=self._format_value(value, kpi.unit),
            calculation_steps=calculation_steps,
            dependencies=dependencies,
            sources=sources,
            metadata=kpi.metadata,
        )
    
    def _get_dependencies(self, kpi_id: str) -> List[str]:
        """Get list of metric dependencies for a KPI."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT metric_name
                FROM kpi_dependencies
                WHERE kpi_id = ?
                """,
                (kpi_id,),
            ).fetchall()
            return [row[0] for row in rows]
    
    def _fetch_metric_values(
        self,
        ticker: str,
        metrics: List[str],
        period: Optional[str],
        fiscal_year: Optional[int]
    ) -> Dict[str, MetricValue]:
        """Fetch metric values from database."""
        values = {}
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            for metric in metrics:
                # Try to find metric in metric_snapshots
                query = """
                    SELECT value, period, source, start_year, end_year, updated_at
                    FROM metric_snapshots
                    WHERE ticker = ? AND metric = ?
                """
                params = [ticker.upper(), metric.lower()]
                
                if fiscal_year:
                    query += " AND (end_year = ? OR start_year = ?)"
                    params.extend([fiscal_year, fiscal_year])
                elif period:
                    query += " AND period = ?"
                    params.append(period)
                
                query += " ORDER BY updated_at DESC LIMIT 1"
                
                row = conn.execute(query, params).fetchone()
                if row:
                    fiscal = row["end_year"] or row["start_year"]
                    values[metric] = MetricValue(
                        metric=metric,
                        value=row["value"],
                        period=row["period"],
                        fiscal_year=fiscal,
                        source=row["source"],
                        source_ref=None,
                        cik=None,
                        filing_date=row["updated_at"],
                        url=None,
                    )
                else:
                    # Try financial_facts as fallback
                    fact_query = """
                        SELECT value, period, fiscal_year, source, source_filing, cik, ingested_at
                        FROM financial_facts
                        WHERE ticker = ? AND metric = ?
                    """
                    fact_params = [ticker.upper(), metric.lower()]
                    
                    if fiscal_year:
                        fact_query += " AND fiscal_year = ?"
                        fact_params.append(fiscal_year)
                    
                    fact_query += " ORDER BY ingested_at DESC LIMIT 1"
                    
                    fact_row = conn.execute(fact_query, fact_params).fetchone()
                    if fact_row:
                        values[metric] = MetricValue(
                            metric=metric,
                            value=fact_row["value"],
                            period=fact_row["period"],
                            fiscal_year=fact_row["fiscal_year"],
                            source=fact_row["source"],
                            source_ref=fact_row["source_filing"],
                            cik=fact_row["cik"],
                            filing_date=fact_row["ingested_at"],
                            url=None,
                        )
                    else:
                        values[metric] = MetricValue(
                            metric=metric,
                            value=None,
                            period=None,
                            fiscal_year=fiscal_year,
                            source=None,
                            source_ref=None,
                            cik=None,
                            filing_date=None,
                            url=None,
                        )
        
        return values
    
    def _evaluate_formula(
        self,
        formula: str,
        metric_values: Dict[str, MetricValue],
        calculation_steps: List[Dict[str, Any]],
        sources: List[Dict[str, Any]]
    ) -> float:
        """Evaluate formula with metric values."""
        # Create evaluation context
        context = {}
        
        # Add metric values
        for metric, metric_value in metric_values.items():
            if metric_value.value is None:
                raise ValueError(f"Missing value for metric: {metric}")
            value = metric_value.value
            # Normalize metric name for formula matching
            context[metric.lower()] = value
            context[metric] = value
            context[metric.upper()] = value
            sources.append({
                "metric": metric,
                "value": value,
                "period": metric_value.period,
                "fiscal_year": metric_value.fiscal_year,
                "source": metric_value.source,
                "source_ref": metric_value.source_ref,
                "cik": metric_value.cik,
                "filing_date": metric_value.filing_date,
                "url": metric_value.url,
            })
        
        # Add functions
        context['sum'] = lambda *args: sum(args)
        context['avg'] = lambda *args: sum(args) / len(args) if args else 0
        context['max'] = lambda *args: max(args) if args else 0
        context['min'] = lambda *args: min(args) if args else 0
        context['abs'] = abs
        context['round'] = round
        
        # Track calculation steps
        for metric, metric_value in metric_values.items():
            calculation_steps.append({
                "step": f"Fetch {metric}",
                "value": metric_value.value,
                "source": metric_value.source or "database",
                "period": metric_value.period,
            })
        
        # Replace metric names in formula with their values
        eval_formula = formula
        for metric, metric_value in metric_values.items():
            # Replace all variations of the metric name
            for variant in [metric, metric.lower(), metric.upper()]:
                if variant in eval_formula:
                    eval_formula = re.sub(
                        rf'\b{re.escape(variant)}\b',
                        str(metric_value.value),
                        eval_formula,
                        flags=re.IGNORECASE
                    )
        
        # Evaluate
        try:
            result = eval(eval_formula, {"__builtins__": {}}, context)
            calculation_steps.append({
                "step": "Calculate formula",
                "formula": eval_formula,
                "result": result
            })
            return float(result)
        except Exception as e:
            raise ValueError(f"Formula evaluation error: {str(e)}")
    
    @staticmethod
    def _format_value(value: Optional[float], unit: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if unit == "pct":
            return f"{value * 100:.2f}%"
        if unit == "bps":
            return f"{value * 10000:.0f} bps"
        if unit and unit.startswith("usd"):
            return f"${value:,.2f}"
        return f"{value:,.2f}"

    def _save_usage(
        self,
        kpi_id: str,
        ticker: str,
        period: str,
        value: Optional[float]
    ) -> None:
        """Save KPI usage record."""
        usage_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO custom_kpi_usage (usage_id, kpi_id, ticker, period, value, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (usage_id, kpi_id, ticker.upper(), period, value, now.isoformat()),
            )
            conn.commit()

    def _save_kpi_version(
        self,
        conn: sqlite3.Connection,
        kpi_id: str,
        formula: str,
        metadata: Dict[str, Any],
        user_id: str,
    ) -> None:
        """Persist a version snapshot for auditability."""
        next_version = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM custom_kpi_versions WHERE kpi_id = ?",
            (kpi_id,),
        ).fetchone()[0]

        conn.execute(
            """
            INSERT INTO custom_kpi_versions (
                version_id,
                kpi_id,
                version_number,
                formula,
                metadata,
                created_at,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                kpi_id,
                next_version,
                formula,
                _json_dumps(metadata),
                datetime.now(timezone.utc).isoformat(),
                user_id,
            ),
        )


