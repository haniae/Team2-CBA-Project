"""
Custom KPI Calculation System

Allows users to define, save, and reuse custom financial metrics.
Supports formula parsing, calculation, and traceability.
"""

from __future__ import annotations

import ast
import json
import logging
import operator
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import database
from .analytics_workspace import DataDictionary, DataSourcePreferencesManager
from .kpi_lookup import KPIDefinitionLookup, KPIDefinitionResult

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
    bindings: List[Dict[str, Any]] = field(default_factory=list)
    parameter_schema: Dict[str, Any] = field(default_factory=dict)
    data_preferences_id: Optional[str] = None

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
        if self.bindings:
            meta["bindings"] = self.bindings
        if self.parameter_schema:
            meta["parameter_schema"] = self.parameter_schema
        if self.data_preferences_id:
            meta["data_preferences_id"] = self.data_preferences_id
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
            "bindings": self.metadata.get("bindings", []),
            "parameter_schema": self.metadata.get("parameter_schema", {}),
            "data_preferences_id": self.metadata.get("data_preferences_id"),
        }
        return base

    @property
    def bindings(self) -> List[Dict[str, Any]]:
        return list(self.metadata.get("bindings", []))

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return dict(self.metadata.get("parameter_schema", {}))

    @property
    def data_preferences_id(self) -> Optional[str]:
        return self.metadata.get("data_preferences_id")


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
        self._create_lookup_patterns = [
            re.compile(
                r"(?:create|define|set up)\s+(?:a\s+)?(?:custom\s+)?(?:kpi|metric)\s*(?:called|named)?\s*['\"]?([\w\s%-]+?)['\"]?\s*$",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:define|what\s+is|explain)\s+(?:the\s+)?(?:kpi|metric)\s*['\"]?([\w\s%-]+?)['\"]?\s*$",
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

        if "=" not in text:
            for pattern in self._create_lookup_patterns:
                match = pattern.search(text)
                if match:
                    name = match.group(1).strip()
                    if name:
                        return {
                            "action": "source_lookup",
                            "kpi_name": name,
                            "lookup_scope": ["internal_dictionary", "financial_glossary", "web"],
                            "raw_prompt": text,
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


class _FormulaValidator(ast.NodeVisitor):
    """Validate AST nodes and collect metric identifiers."""

    _ALLOWED_BIN_OPS: Tuple[type, ...] = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
    _ALLOWED_UNARY_OPS: Tuple[type, ...] = (ast.UAdd, ast.USub)

    def __init__(self, allowed_functions: Sequence[str]) -> None:
        self.allowed_functions = {func.lower() for func in allowed_functions}
        self.identifiers: Set[str] = set()

    # pylint: disable=invalid-name
    def visit_BinOp(self, node: ast.BinOp) -> None:  # pragma: no cover - exercised in parser tests
        if not isinstance(node.op, self._ALLOWED_BIN_OPS):
            raise ValueError(f"Operator '{ast.dump(node.op)}' is not allowed in KPI formulas.")
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:  # pragma: no cover
        if not isinstance(node.op, self._ALLOWED_UNARY_OPS):
            raise ValueError("Only +/- unary operators are allowed.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pragma: no cover
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are supported.")
        func_name = node.func.id.lower()
        if func_name not in self.allowed_functions:
            raise ValueError(f"Function '{node.func.id}' is not permitted in KPI formulas.")
        for keyword in node.keywords:
            raise ValueError("Keyword arguments are not supported in KPI formulas.")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # pragma: no cover
        token = node.id
        if token.lower() not in self.allowed_functions:
            self.identifiers.add(token)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # pragma: no cover
        raise ValueError("Attribute access is not allowed in KPI formulas.")

    def visit_Subscript(self, node: ast.Subscript) -> None:  # pragma: no cover
        raise ValueError("Subscript access is not allowed in KPI formulas.")

    def visit_List(self, node: ast.List) -> None:  # pragma: no cover
        raise ValueError("List literals are not supported in KPI formulas.")

    def visit_Dict(self, node: ast.Dict) -> None:  # pragma: no cover
        raise ValueError("Dictionary literals are not supported in KPI formulas.")

    def generic_visit(self, node: ast.AST) -> None:  # pragma: no cover
        super().generic_visit(node)


class _CanonicalNameTransformer(ast.NodeTransformer):
    """Rewrite AST name nodes to their canonical KPI identifiers."""

    def __init__(self, mapping: Dict[str, str]) -> None:
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:  # pragma: no cover
        canonical = (
            self.mapping.get(node.id)
            or self.mapping.get(node.id.lower())
            or self.mapping.get(node.id.upper())
        )
        if canonical:
            return ast.copy_location(ast.Name(id=canonical, ctx=node.ctx), node)
        return node


class _FormulaEvaluator(ast.NodeVisitor):
    """Safely evaluate KPI formulas using whitelisted operations."""

    _BINARY_OPERATORS: Dict[type, Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _UNARY_OPERATORS: Dict[type, Any] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def __init__(self, context: Dict[str, Any], allowed_functions: Sequence[str]) -> None:
        self.context = context
        self.allowed_functions = {name.lower() for name in allowed_functions}

    def visit_Expression(self, node: ast.Expression) -> Any:  # pragma: no cover - thin wrapper
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op_type = type(node.op)
        if op_type not in self._BINARY_OPERATORS:
            raise ValueError(f"Operator '{ast.dump(node.op)}' is not allowed.")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return self._BINARY_OPERATORS[op_type](left, right)
        except ZeroDivisionError as exc:  # pragma: no cover - depends on user input
            raise ValueError("Division by zero in KPI formula.") from exc

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op_type = type(node.op)
        if op_type not in self._UNARY_OPERATORS:
            raise ValueError("Only +/- unary operators are allowed.")
        operand = self.visit(node.operand)
        return self._UNARY_OPERATORS[op_type](operand)

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are supported in KPI formulas.")
        if node.keywords:
            raise ValueError("Keyword arguments are not supported in KPI formulas.")
        func_name = node.func.id
        lookup_key = func_name.lower()
        if lookup_key not in self.allowed_functions:
            raise ValueError(f"Function '{func_name}' is not permitted in KPI formulas.")
        func = self._resolve_identifier(func_name)
        args = [self.visit(arg) for arg in node.args]
        return func(*args)

    def visit_Name(self, node: ast.Name) -> Any:
        value = self._resolve_identifier(node.id)
        if value is None:
            raise ValueError(f"Unknown identifier '{node.id}' in KPI formula.")
        return value

    def visit_Constant(self, node: ast.Constant) -> Any:  # pragma: no cover - simple path
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed in KPI formulas.")

    def visit_Num(self, node: ast.Num) -> Any:  # pragma: no cover - Python <3.8 compatibility
        return node.n

    def visit_List(self, node: ast.List) -> Any:  # pragma: no cover - defensive
        raise ValueError("List literals are not supported in KPI formulas.")

    def visit_Dict(self, node: ast.Dict) -> Any:  # pragma: no cover - defensive
        raise ValueError("Dictionary literals are not supported in KPI formulas.")

    def visit_Subscript(self, node: ast.Subscript) -> Any:  # pragma: no cover - defensive
        raise ValueError("Subscript access is not allowed in KPI formulas.")

    def visit_Attribute(self, node: ast.Attribute) -> Any:  # pragma: no cover - defensive
        raise ValueError("Attribute access is not allowed in KPI formulas.")

    def _resolve_identifier(self, name: str) -> Any:
        for candidate in (name, name.lower(), name.upper()):
            if candidate in self.context:
                return self.context[candidate]
        return None


class FormulaParser:
    """Parses, validates, and canonicalises custom KPI formulas."""

    _ALLOWED_FUNCTIONS = ("sum", "avg", "max", "min", "abs", "round")

    def __init__(self, dictionary: DataDictionary):
        self.dictionary = dictionary

    def parse(
        self,
        formula: str,
    ) -> Tuple[str, List[str], List[Dict[str, Any]], str]:
        """
        Parse formula, enforce allowed syntax, and return canonical representation.

        Returns:
            Tuple of (canonical_formula, canonical_dependencies, binding_metadata, original_formula)
        """
        original_formula = formula.strip()
        if not original_formula:
            raise ValueError("Formula cannot be empty.")

        try:
            tree = ast.parse(original_formula, mode="eval")
        except SyntaxError as exc:  # pragma: no cover - error branches
            raise ValueError(f"Invalid formula syntax: {exc}") from exc

        validator = _FormulaValidator(self._ALLOWED_FUNCTIONS)
        validator.visit(tree)

        dependencies = sorted(validator.identifiers)
        bindings_map = self.dictionary.resolve(dependencies)

        name_mapping: Dict[str, str] = {}
        canonical_dependencies: List[str] = []
        binding_metadata: List[Dict[str, Any]] = []

        for token in dependencies:
            binding = bindings_map.get(token)
            if not binding:
                continue
            canonical_metric = binding.canonical_metric
            name_mapping[token] = canonical_metric
            name_mapping[token.lower()] = canonical_metric
            name_mapping[token.upper()] = canonical_metric
            canonical_dependencies.append(canonical_metric)
            binding_metadata.append(binding.to_metadata())

        canonical_dependencies = sorted(dict.fromkeys(canonical_dependencies))

        transformer = _CanonicalNameTransformer(name_mapping)
        canonical_tree = transformer.visit(tree)
        ast.fix_missing_locations(canonical_tree)

        try:
            canonical_formula = ast.unparse(canonical_tree)
        except AttributeError:  # pragma: no cover - Python < 3.9 safety
            canonical_formula = original_formula

        canonical_formula = canonical_formula.strip()

        return canonical_formula, canonical_dependencies, binding_metadata, original_formula

    def validate_formula(self, formula: str) -> Tuple[bool, Optional[str]]:
        try:
            self.parse(formula)
            return True, None
        except ValueError as exc:
            return False, str(exc)


class CustomKPICalculator:
    """Calculates custom KPIs from formulas."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.dictionary = DataDictionary(db_path)
        self.preferences_manager = DataSourcePreferencesManager(db_path)
        self.parser = FormulaParser(self.dictionary)
        self.intent_parser = KPIIntentParser()
        self.definition_lookup = KPIDefinitionLookup()

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
        parameter_schema: Optional[Dict[str, Any]] = None,
        data_preferences_id: Optional[str] = None,
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
            parameter_schema=parameter_schema or {},
            data_preferences_id=data_preferences_id,
        )
        return self.create_kpi_from_definition(user_id=user_id, definition=definition)

    def create_kpi_from_definition(
        self,
        user_id: str,
        definition: CustomKPIDefinition,
    ) -> CustomKPI:
        """Create a KPI from a structured definition."""
        try:
            canonical_formula, dependencies, binding_metadata, original_formula = self.parser.parse(definition.formula)
        except ValueError as exc:
            raise ValueError(f"Invalid formula: {exc}") from exc

        kpi_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        inputs = definition.inputs or dependencies
        source_tags = self._derive_source_tags(definition.source_tags, binding_metadata)

        definition.inputs = inputs
        definition.source_tags = source_tags
        definition.bindings = binding_metadata

        metadata_payload = definition.to_metadata()
        metadata_payload.setdefault("original_formula", original_formula)
        metadata_payload["canonical_formula"] = canonical_formula
        metadata_payload["canonical_inputs"] = dependencies
        metadata_payload["binding_count"] = len(binding_metadata)

        kpi = CustomKPI(
            kpi_id=kpi_id,
            user_id=user_id,
            name=definition.name.strip(),
            formula=canonical_formula,
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
            self._save_kpi_version(conn, kpi_id, canonical_formula, metadata_payload, user_id)

        return kpi

    @staticmethod
    def _derive_source_tags(
        explicit_tags: Optional[Sequence[str]],
        bindings: Sequence[Dict[str, Any]],
    ) -> List[str]:
        ordered: List[str] = []
        for tag in explicit_tags or []:
            if tag and tag not in ordered:
                ordered.append(tag)

        for binding in bindings:
            primary = binding.get("primary_tag")
            if primary and primary not in ordered:
                ordered.append(primary)
            for fallback in binding.get("fallback_tags", []):
                if fallback and fallback not in ordered:
                    ordered.append(fallback)

        return ordered

    def upsert_kpi(self, user_id: str, definition: CustomKPIDefinition) -> CustomKPI:
        """Create a KPI or update existing one by name."""
        existing = self.get_kpi_by_name(user_id, definition.name)
        if not existing:
            return self.create_kpi_from_definition(user_id, definition)

        try:
            canonical_formula, dependencies, binding_metadata, original_formula = self.parser.parse(definition.formula)
        except ValueError as exc:
            raise ValueError(f"Invalid formula: {exc}") from exc
        now = datetime.now(timezone.utc)
        inputs = definition.inputs or dependencies
        source_tags = self._derive_source_tags(definition.source_tags, binding_metadata)
        definition.inputs = inputs
        definition.source_tags = source_tags
        definition.bindings = binding_metadata
        metadata_payload = definition.to_metadata()
        metadata_payload.setdefault("original_formula", original_formula)
        metadata_payload["canonical_formula"] = canonical_formula
        metadata_payload["canonical_inputs"] = dependencies
        metadata_payload["binding_count"] = len(binding_metadata)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE custom_kpis
                SET formula = ?, description = ?, updated_at = ?, frequency = ?, unit = ?, inputs = ?, source_tags = ?, metadata = ?
                WHERE kpi_id = ? AND user_id = ?
                """,
                (
                    canonical_formula,
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

            self._save_kpi_version(conn, existing.kpi_id, canonical_formula, metadata_payload, user_id)
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
        fiscal_year: Optional[int] = None,
        source_preferences: Optional[Sequence[str]] = None,
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
        
        # Resolve source preferences
        effective_source_preferences = list(source_preferences or [])
        applied_preference_id: Optional[str] = None
        if not effective_source_preferences:
            preference_id = kpi.data_preferences_id or kpi.metadata.get("data_preferences_id")
            if preference_id:
                preference = self.preferences_manager.get(preference_id)
                if preference and preference.source_order:
                    effective_source_preferences = list(preference.source_order)
                    applied_preference_id = preference.preference_id
        
        # Get dependencies
        dependencies = self._get_dependencies(kpi_id) or kpi.inputs
        
        # Fetch metric values
        metric_values = self._fetch_metric_values(
            ticker,
            dependencies,
            period,
            fiscal_year,
            source_preferences=effective_source_preferences or None,
        )
        
        # Calculate formula
        calculation_steps = []
        sources = []
        
        try:
            value = self._evaluate_formula(kpi.formula, metric_values, calculation_steps, sources)
        except Exception as e:
            error_message = str(e)
            if "Missing value for metric" in error_message:
                missing_metric = error_message.split(":")[-1].strip()
                if fiscal_year:
                    period_label = f"FY{fiscal_year}"
                elif period:
                    period_label = period
                else:
                    period_label = "requested period"
                error_message = (
                    f"{period_label} data not ingested yet (missing {missing_metric}). "
                    "Run the ingestion scripts to fetch that fiscal period."
                )
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
            metadata=self._build_result_metadata(
                kpi.metadata,
                effective_source_preferences,
                applied_preference_id,
            ),
                error=error_message,
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
            metadata=self._build_result_metadata(
                kpi.metadata,
                effective_source_preferences,
                applied_preference_id,
            ),
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
        fiscal_year: Optional[int],
        *,
        source_preferences: Optional[Sequence[str]] = None,
    ) -> Dict[str, MetricValue]:
        """Fetch metric values from database."""
        values = {}

        normalized_preferences = [pref.lower() for pref in (source_preferences or [])]

        def _label_source(source: Optional[str]) -> str:
            if not source:
                return "unknown"
            lowered = source.lower()
            if "sec" in lowered or "edgar" in lowered or "us-gaap" in lowered:
                return "sec"
            if "xbrl" in lowered:
                return "sec"
            if "yahoo" in lowered:
                return "yahoo"
            if "stooq" in lowered:
                return "stooq"
            return lowered

        def _matches_preferences(source: Optional[str]) -> bool:
            if not normalized_preferences:
                return True
            label = _label_source(source)
            for pref in normalized_preferences:
                if pref in {"sec", "sec_xbrl", "primary", "edgar"} and label == "sec":
                    return True
                if pref == "secondary" and label != "sec":
                    return True
                if pref == label:
                    return True
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            for metric in metrics:
                metric_value: Optional[MetricValue] = None

                snapshot_query = """
                    SELECT value, period, source, start_year, end_year, updated_at
                    FROM metric_snapshots
                    WHERE ticker = ? AND metric = ?
                """
                snapshot_params: List[Any] = [ticker.upper(), metric.lower()]

                if fiscal_year is not None:
                    snapshot_query += " AND (end_year = ? OR start_year = ?)"
                    snapshot_params.extend([fiscal_year, fiscal_year])
                elif period:
                    snapshot_query += " AND period = ?"
                    snapshot_params.append(period)

                snapshot_query += " ORDER BY updated_at DESC LIMIT 1"
                row = conn.execute(snapshot_query, snapshot_params).fetchone()
                if row and _matches_preferences(row["source"]):
                    fiscal = row["end_year"] or row["start_year"]
                    metric_value = MetricValue(
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

                if metric_value is None:
                    fact_query = """
                        SELECT value, period, fiscal_year, source, source_filing, cik, ingested_at
                        FROM financial_facts
                        WHERE ticker = ? AND metric = ?
                    """
                    fact_params: List[Any] = [ticker.upper(), metric.lower()]
                    if fiscal_year is not None:
                        fact_query += " AND fiscal_year = ?"
                        fact_params.append(fiscal_year)
                    fact_query += " ORDER BY ingested_at DESC LIMIT 1"
                    fact_row = conn.execute(fact_query, fact_params).fetchone()
                    if fact_row and _matches_preferences(fact_row["source"]):
                        metric_value = MetricValue(
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

                if metric_value is None:
                    metric_value = MetricValue(
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

                values[metric] = metric_value

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
        context: Dict[str, Any] = {}
        numeric_snapshot: Dict[str, Optional[float]] = {}

        for metric, metric_value in metric_values.items():
            numeric_snapshot[metric] = metric_value.value
            sources.append(
                {
                    "metric": metric,
                    "value": metric_value.value,
                    "period": metric_value.period,
                    "fiscal_year": metric_value.fiscal_year,
                    "source": metric_value.source,
                    "source_ref": metric_value.source_ref,
                    "cik": metric_value.cik,
                    "filing_date": metric_value.filing_date,
                    "url": metric_value.url,
                }
            )

            if metric_value.value is None:
                raise ValueError(f"Missing value for metric: {metric}")

            value = metric_value.value
            context.setdefault(metric, value)
            context.setdefault(metric.lower(), value)
            context.setdefault(metric.upper(), value)

        # Track data fetch steps for auditing
        for metric, metric_value in metric_values.items():
            calculation_steps.append(
                {
                    "step": f"Fetch {metric}",
                    "value": metric_value.value,
                    "source": metric_value.source or "database",
                    "period": metric_value.period,
                }
            )

        # Inject allowed helper functions
        context["sum"] = lambda *args: sum(args)
        context["avg"] = lambda *args: sum(args) / len(args) if args else 0
        context["max"] = lambda *args: max(args) if args else 0
        context["min"] = lambda *args: min(args) if args else 0
        context["abs"] = abs
        context["round"] = round

        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid canonical formula '{formula}': {exc}") from exc

        evaluator = _FormulaEvaluator(context, FormulaParser._ALLOWED_FUNCTIONS)
        try:
            result = evaluator.visit(tree)
        except Exception as exc:
            raise ValueError(f"Formula evaluation error: {exc}") from exc

        calculation_steps.append(
            {
                "step": "Calculate formula",
                "formula": formula,
                "inputs": numeric_snapshot,
                "result": result,
            }
        )
        return float(result)
    
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

    @staticmethod
    def _definition_lookup_metadata(result: KPIDefinitionResult) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "definition_source": result.source,
            "lookup_confidence": result.confidence,
            "lookup_scope": list(result.scope),
            "lookup_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if result.description:
            payload["definition_description"] = result.description
        if result.raw_entry:
            payload["definition_entry"] = result.raw_entry
        return payload

    def lookup_definition(
        self,
        kpi_name: str,
        lookup_scope: Optional[Sequence[str]] = None,
    ) -> Optional[KPIDefinitionResult]:
        """Attempt to resolve a KPI definition from the lookup resources."""
        if not kpi_name:
            return None
        if lookup_scope:
            lookup = KPIDefinitionLookup(lookup_scope=lookup_scope)
            return lookup.lookup(kpi_name)
        return self.definition_lookup.lookup(kpi_name)

    def _definition_from_lookup_result(
        self,
        result: KPIDefinitionResult,
    ) -> CustomKPIDefinition:
        metadata = self._definition_lookup_metadata(result)
        inputs = [token for token in (result.inputs or []) if token]
        source_tags = [token for token in (result.source_tags or []) if token]
        return CustomKPIDefinition(
            name=result.name,
            formula=result.formula,
            description=result.description,
            unit=result.unit,
            inputs=inputs,
            source_tags=source_tags,
            metadata=metadata,
        )

    def ensure_kpi_from_lookup(
        self,
        user_id: str,
        kpi_name: str,
        lookup_scope: Optional[Sequence[str]] = None,
    ) -> Optional[CustomKPI]:
        """
        Ensure a KPI exists by looking up a canonical definition if missing.
        Returns the existing or newly created KPI, or None if lookup fails.
        """
        existing = self.get_kpi_by_name(user_id, kpi_name)
        if existing:
            return existing
        result = self.lookup_definition(kpi_name, lookup_scope)
        if not result:
            return None
        definition = self._definition_from_lookup_result(result)
        return self.upsert_kpi(user_id, definition)

    @staticmethod
    def _build_result_metadata(
        base_metadata: Dict[str, Any],
        source_preferences: Sequence[str],
        applied_preference_id: Optional[str],
    ) -> Dict[str, Any]:
        merged = dict(base_metadata or {})
        merged["source_preferences"] = list(source_preferences)
        if applied_preference_id:
            merged["applied_data_preferences_id"] = applied_preference_id
            merged.setdefault("data_preferences_id", applied_preference_id)
        return merged


