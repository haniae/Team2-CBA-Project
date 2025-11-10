"""
Analyst workspace persistence utilities.

This module provides helper classes for managing analyst-defined artefacts:

- Metric/data dictionary bindings (alias → canonical metric, source mapping)
- Data source preference profiles
- Analysis templates (collections of KPIs with parameter schemas)
- Analyst profiles and saved workspace sessions

All entities are persisted in SQLite with JSON metadata for traceability.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .data_sources import METRIC_ALIASES
from .parsing.ontology import METRIC_SYNONYMS

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=str, separators=(",", ":"))


def _json_loads(payload: Optional[str]) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


def _normalise_alias(value: str) -> str:
    normalised = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalised).strip()


def _normalize_metric_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _camel_to_snake(value: str) -> str:
    if not value:
        return value
    step_one = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    step_two = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", step_one)
    return step_two.replace("__", "_")


_LOOKUP_SYNONYMS: Dict[str, str] = {}
for raw_alias, canonical in METRIC_SYNONYMS.items():
    key = _normalise_alias(raw_alias)
    if key:
        _LOOKUP_SYNONYMS[key] = _normalize_metric_token(canonical)


_CANONICAL_TAGS: Dict[str, List[str]] = {}
for tag, canonical in METRIC_ALIASES.items():
    canonical_token = _normalize_metric_token(canonical)
    _CANONICAL_TAGS.setdefault(canonical_token, [])
    if tag not in _CANONICAL_TAGS[canonical_token]:
        _CANONICAL_TAGS[canonical_token].append(tag)


@dataclass(frozen=True)
class MetricBinding:
    alias: str
    canonical_metric: str
    source_system: str
    primary_tag: Optional[str]
    fallback_tags: List[str]
    description: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    raw_alias: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "raw_alias": self.raw_alias or self.alias,
            "canonical_metric": self.canonical_metric,
            "source_system": self.source_system,
            "primary_tag": self.primary_tag,
            "fallback_tags": list(self.fallback_tags),
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }


@dataclass(frozen=True)
class DataSourcePreference:
    preference_id: str
    user_id: str
    name: str
    source_order: List[str]
    fallback_rules: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preference_id": self.preference_id,
            "user_id": self.user_id,
            "name": self.name,
            "source_order": self.source_order,
            "fallback_rules": self.fallback_rules,
            "description": self.description,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class AnalysisTemplate:
    template_id: str
    user_id: str
    name: str
    kpi_ids: List[str]
    description: Optional[str]
    layout_config: Dict[str, Any]
    parameter_schema: Dict[str, Any]
    data_preferences_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "kpi_ids": self.kpi_ids,
            "layout_config": self.layout_config,
            "parameter_schema": self.parameter_schema,
            "data_preferences_id": self.data_preferences_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class AnalyticsProfile:
    profile_id: str
    user_id: str
    name: str
    description: Optional[str]
    kpi_library: List[str]
    template_ids: List[str]
    data_preferences_id: Optional[str]
    output_preferences: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "kpi_library": self.kpi_library,
            "template_ids": self.template_ids,
            "data_preferences_id": self.data_preferences_id,
            "output_preferences": self.output_preferences,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class SavedSession:
    session_id: str
    profile_id: str
    user_id: str
    name: Optional[str]
    workspace_state: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "user_id": self.user_id,
            "name": self.name,
            "workspace_state": self.workspace_state,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class DataDictionary:
    """Manage alias → canonical metric bindings with source metadata."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_dictionary (
                    alias TEXT PRIMARY KEY,
                    raw_alias TEXT,
                    canonical_metric TEXT NOT NULL,
                    source_system TEXT NOT NULL DEFAULT 'sec_xbrl',
                    primary_tag TEXT,
                    fallback_tags TEXT NOT NULL DEFAULT '[]',
                    description TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by TEXT NOT NULL DEFAULT 'system',
                    updated_by TEXT NOT NULL DEFAULT 'system'
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_metric_dictionary_canonical
                ON metric_dictionary (canonical_metric)
                """
            )
            conn.commit()

    def _row_to_binding(self, row: sqlite3.Row) -> MetricBinding:
        return MetricBinding(
            alias=row["alias"],
            raw_alias=row["raw_alias"],
            canonical_metric=row["canonical_metric"],
            source_system=row["source_system"],
            primary_tag=row["primary_tag"],
            fallback_tags=json.loads(row["fallback_tags"] or "[]"),
            description=row["description"],
            metadata=_json_loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )

    def resolve(self, aliases: Iterable[str], create_missing: bool = True) -> Dict[str, MetricBinding]:
        """Resolve a batch of aliases to MetricBinding objects."""
        alias_list = list(aliases)
        if not alias_list:
            return {}

        normalised = {_normalise_alias(alias): alias for alias in alias_list}
        bindings: Dict[str, MetricBinding] = {}

        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT alias, raw_alias, canonical_metric, source_system,
                       primary_tag, fallback_tags, description, metadata,
                       created_at, updated_at, created_by, updated_by
                FROM metric_dictionary
                WHERE alias IN ({",".join(["?"] * len(normalised))})
                """,
                list(normalised.keys()),
            ).fetchall()
            for row in rows:
                binding = self._row_to_binding(row)
                bindings[normalised[binding.alias]] = binding

            missing_keys = [alias for alias in normalised if alias not in bindings]
            if not create_missing or not missing_keys:
                return bindings

            for alias in missing_keys:
                raw_alias = normalised[alias]
                binding = self._auto_create_binding(conn, alias, raw_alias)
                bindings[raw_alias] = binding

            conn.commit()

        return bindings

    def _auto_create_binding(self, conn: sqlite3.Connection, alias: str, raw_alias: str) -> MetricBinding:
        canonical_metric = self._canonical_from_alias(raw_alias or alias)
        tags = _CANONICAL_TAGS.get(canonical_metric, [])
        primary_tag = tags[0] if tags else None
        fallback_tags = tags[1:] if len(tags) > 1 else []
        created_at = _now().isoformat()
        metadata = {
            "autogenerated": True,
            "source": "ontology",
        }
        conn.execute(
            """
            INSERT INTO metric_dictionary (
                alias,
                raw_alias,
                canonical_metric,
                source_system,
                primary_tag,
                fallback_tags,
                description,
                metadata,
                created_at,
                updated_at,
                created_by,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alias,
                raw_alias,
                canonical_metric,
                "sec_xbrl" if primary_tag else "unknown",
                primary_tag,
                _json_dumps(fallback_tags),
                None,
                _json_dumps(metadata),
                created_at,
                created_at,
                "system",
                "system",
            ),
        )
        row = conn.execute(
            """
            SELECT alias, raw_alias, canonical_metric, source_system, primary_tag,
                   fallback_tags, description, metadata, created_at, updated_at, created_by, updated_by
            FROM metric_dictionary
            WHERE alias = ?
            """,
            (alias,),
        ).fetchone()
        assert row is not None  # safety guard
        return self._row_to_binding(row)

    def _canonical_from_alias(self, alias: str) -> str:
        token = _normalize_metric_token(alias)
        if token in _CANONICAL_TAGS:
            return token

        camel_token = _normalize_metric_token(_camel_to_snake(alias))
        if camel_token and camel_token in _CANONICAL_TAGS:
            return camel_token

        lookup_key = _normalise_alias(alias)
        canonical = _LOOKUP_SYNONYMS.get(lookup_key)
        if canonical:
            return canonical

        if camel_token and camel_token != token:
            camel_lookup = _normalise_alias(_camel_to_snake(alias))
            canonical = _LOOKUP_SYNONYMS.get(camel_lookup)
            if canonical:
                return canonical

        # Fallback to normalized token when we cannot resolve.
        return token


class DataSourcePreferencesManager:
    """CRUD helpers for persisted data source preference profiles."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_source_preferences (
                    preference_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    source_order TEXT NOT NULL DEFAULT '[]',
                    fallback_rules TEXT NOT NULL DEFAULT '{}',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_data_source_preferences_user
                ON data_source_preferences (user_id, created_at DESC)
                """
            )
            conn.commit()

    def _row_to_preference(self, row: sqlite3.Row) -> DataSourcePreference:
        return DataSourcePreference(
            preference_id=row["preference_id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            source_order=json.loads(row["source_order"] or "[]"),
            fallback_rules=_json_loads(row["fallback_rules"]),
            metadata=_json_loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(
        self,
        user_id: str,
        name: str,
        *,
        source_order: Sequence[str],
        fallback_rules: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DataSourcePreference:
        preference_id = str(uuid.uuid4())
        now = _now().isoformat()
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO data_source_preferences (
                    preference_id,
                    user_id,
                    name,
                    description,
                    source_order,
                    fallback_rules,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preference_id,
                    user_id,
                    name,
                    description,
                    _json_dumps(list(source_order)),
                    _json_dumps(fallback_rules or {}),
                    _json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
            conn.commit()

        return self.get(preference_id)

    def update(
        self,
        preference_id: str,
        *,
        name: Optional[str] = None,
        source_order: Optional[Sequence[str]] = None,
        fallback_rules: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DataSourcePreference]:
        with sqlite3.connect(self.database_path) as conn:
            existing = conn.execute(
                "SELECT COUNT(*) FROM data_source_preferences WHERE preference_id = ?",
                (preference_id,),
            ).fetchone()[0]
            if not existing:
                return None

            current = self.get(preference_id)
            assert current is not None
            conn.execute(
                """
                UPDATE data_source_preferences
                SET name = ?,
                    description = ?,
                    source_order = ?,
                    fallback_rules = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE preference_id = ?
                """,
                (
                    name or current.name,
                    description if description is not None else current.description,
                    _json_dumps(list(source_order) if source_order is not None else current.source_order),
                    _json_dumps(fallback_rules if fallback_rules is not None else current.fallback_rules),
                    _json_dumps(metadata if metadata is not None else current.metadata),
                    _now().isoformat(),
                    preference_id,
                ),
            )
            conn.commit()

        return self.get(preference_id)

    def get(self, preference_id: str) -> Optional[DataSourcePreference]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT preference_id, user_id, name, description,
                       source_order, fallback_rules, metadata,
                       created_at, updated_at
                FROM data_source_preferences
                WHERE preference_id = ?
                """,
                (preference_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_preference(row)

    def list(self, user_id: str) -> List[DataSourcePreference]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT preference_id, user_id, name, description,
                       source_order, fallback_rules, metadata,
                       created_at, updated_at
                FROM data_source_preferences
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_preference(row) for row in rows]


class AnalysisTemplateRegistry:
    """Manage KPI analysis templates and their version history."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_templates (
                    template_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    kpi_ids TEXT NOT NULL DEFAULT '[]',
                    layout_config TEXT NOT NULL DEFAULT '{}',
                    parameter_schema TEXT NOT NULL DEFAULT '{}',
                    data_preferences_id TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_template_versions (
                    version_id TEXT PRIMARY KEY,
                    template_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    change_summary TEXT,
                    FOREIGN KEY (template_id) REFERENCES analysis_templates(template_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analysis_templates_user
                ON analysis_templates (user_id, updated_at DESC)
                """
            )
            conn.commit()

    def _row_to_template(self, row: sqlite3.Row) -> AnalysisTemplate:
        return AnalysisTemplate(
            template_id=row["template_id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            kpi_ids=json.loads(row["kpi_ids"] or "[]"),
            layout_config=_json_loads(row["layout_config"]),
            parameter_schema=_json_loads(row["parameter_schema"]),
            data_preferences_id=row["data_preferences_id"],
            metadata=_json_loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(
        self,
        user_id: str,
        name: str,
        *,
        kpi_ids: Sequence[str],
        description: Optional[str] = None,
        layout_config: Optional[Dict[str, Any]] = None,
        parameter_schema: Optional[Dict[str, Any]] = None,
        data_preferences_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: str = "system",
    ) -> AnalysisTemplate:
        template_id = str(uuid.uuid4())
        now = _now().isoformat()
        snapshot = {
            "template_id": template_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "kpi_ids": list(kpi_ids),
            "layout_config": layout_config or {},
            "parameter_schema": parameter_schema or {},
            "data_preferences_id": data_preferences_id,
            "metadata": metadata or {},
        }
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO analysis_templates (
                    template_id,
                    user_id,
                    name,
                    description,
                    kpi_ids,
                    layout_config,
                    parameter_schema,
                    data_preferences_id,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    user_id,
                    name,
                    description,
                    _json_dumps(list(kpi_ids)),
                    _json_dumps(layout_config or {}),
                    _json_dumps(parameter_schema or {}),
                    data_preferences_id,
                    _json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
            self._record_version(conn, template_id, snapshot, created_by)
            conn.commit()

        return self.get(template_id)

    def update(
        self,
        template_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        kpi_ids: Optional[Sequence[str]] = None,
        layout_config: Optional[Dict[str, Any]] = None,
        parameter_schema: Optional[Dict[str, Any]] = None,
        data_preferences_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        updated_by: str = "system",
    ) -> Optional[AnalysisTemplate]:
        current = self.get(template_id)
        if not current:
            return None

        new_snapshot = {
            "template_id": template_id,
            "user_id": current.user_id,
            "name": name or current.name,
            "description": description if description is not None else current.description,
            "kpi_ids": list(kpi_ids) if kpi_ids is not None else current.kpi_ids,
            "layout_config": layout_config if layout_config is not None else current.layout_config,
            "parameter_schema": parameter_schema if parameter_schema is not None else current.parameter_schema,
            "data_preferences_id": data_preferences_id if data_preferences_id is not None else current.data_preferences_id,
            "metadata": metadata if metadata is not None else current.metadata,
        }

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE analysis_templates
                SET name = ?,
                    description = ?,
                    kpi_ids = ?,
                    layout_config = ?,
                    parameter_schema = ?,
                    data_preferences_id = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE template_id = ?
                """,
                (
                    new_snapshot["name"],
                    new_snapshot["description"],
                    _json_dumps(new_snapshot["kpi_ids"]),
                    _json_dumps(new_snapshot["layout_config"]),
                    _json_dumps(new_snapshot["parameter_schema"]),
                    new_snapshot["data_preferences_id"],
                    _json_dumps(new_snapshot["metadata"]),
                    _now().isoformat(),
                    template_id,
                ),
            )
            self._record_version(conn, template_id, new_snapshot, updated_by)
            conn.commit()

        return self.get(template_id)

    def delete(self, template_id: str) -> bool:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute("DELETE FROM analysis_templates WHERE template_id = ?", (template_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get(self, template_id: str) -> Optional[AnalysisTemplate]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT template_id, user_id, name, description, kpi_ids,
                       layout_config, parameter_schema, data_preferences_id,
                       metadata, created_at, updated_at
                FROM analysis_templates
                WHERE template_id = ?
                """,
                (template_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_template(row)

    def list(self, user_id: str) -> List[AnalysisTemplate]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT template_id, user_id, name, description, kpi_ids,
                       layout_config, parameter_schema, data_preferences_id,
                       metadata, created_at, updated_at
                FROM analysis_templates
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_template(row) for row in rows]

    def list_versions(self, template_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT version_number, snapshot, created_at, created_by, change_summary
                FROM analysis_template_versions
                WHERE template_id = ?
                ORDER BY version_number DESC
                LIMIT ?
                """,
                (template_id, limit),
            ).fetchall()
        history: List[Dict[str, Any]] = []
        for row in rows:
            history.append(
                {
                    "version_number": row["version_number"],
                    "snapshot": _json_loads(row["snapshot"]),
                    "created_at": row["created_at"],
                    "created_by": row["created_by"],
                    "change_summary": row["change_summary"],
                }
            )
        return history

    def _record_version(
        self,
        conn: sqlite3.Connection,
        template_id: str,
        snapshot: Dict[str, Any],
        created_by: str,
        change_summary: Optional[str] = None,
    ) -> None:
        next_version = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM analysis_template_versions WHERE template_id = ?",
            (template_id,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT INTO analysis_template_versions (
                version_id,
                template_id,
                version_number,
                snapshot,
                created_at,
                created_by,
                change_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                template_id,
                next_version,
                _json_dumps(snapshot),
                _now().isoformat(),
                created_by,
                change_summary,
            ),
        )


class AnalyticsProfileManager:
    """Manage analyst profiles grouping KPIs, templates, and preferences."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_profiles (
                    profile_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    kpi_library TEXT NOT NULL DEFAULT '[]',
                    template_ids TEXT NOT NULL DEFAULT '[]',
                    data_preferences_id TEXT,
                    output_preferences TEXT NOT NULL DEFAULT '{}',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analytics_profiles_user
                ON analytics_profiles (user_id, updated_at DESC)
                """
            )
            conn.commit()

    def _row_to_profile(self, row: sqlite3.Row) -> AnalyticsProfile:
        return AnalyticsProfile(
            profile_id=row["profile_id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            kpi_library=json.loads(row["kpi_library"] or "[]"),
            template_ids=json.loads(row["template_ids"] or "[]"),
            data_preferences_id=row["data_preferences_id"],
            output_preferences=_json_loads(row["output_preferences"]),
            metadata=_json_loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create(
        self,
        user_id: str,
        name: str,
        *,
        kpi_library: Optional[Sequence[str]] = None,
        template_ids: Optional[Sequence[str]] = None,
        data_preferences_id: Optional[str] = None,
        output_preferences: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnalyticsProfile:
        profile_id = str(uuid.uuid4())
        now = _now().isoformat()
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO analytics_profiles (
                    profile_id,
                    user_id,
                    name,
                    description,
                    kpi_library,
                    template_ids,
                    data_preferences_id,
                    output_preferences,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    user_id,
                    name,
                    description,
                    _json_dumps(list(kpi_library or [])),
                    _json_dumps(list(template_ids or [])),
                    data_preferences_id,
                    _json_dumps(output_preferences or {}),
                    _json_dumps(metadata or {}),
                    now,
                    now,
                ),
            )
            conn.commit()

        return self.get(profile_id)

    def update(
        self,
        profile_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        kpi_library: Optional[Sequence[str]] = None,
        template_ids: Optional[Sequence[str]] = None,
        data_preferences_id: Optional[str] = None,
        output_preferences: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AnalyticsProfile]:
        current = self.get(profile_id)
        if not current:
            return None

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE analytics_profiles
                SET name = ?,
                    description = ?,
                    kpi_library = ?,
                    template_ids = ?,
                    data_preferences_id = ?,
                    output_preferences = ?,
                    metadata = ?,
                    updated_at = ?
                WHERE profile_id = ?
                """,
                (
                    name or current.name,
                    description if description is not None else current.description,
                    _json_dumps(list(kpi_library) if kpi_library is not None else current.kpi_library),
                    _json_dumps(list(template_ids) if template_ids is not None else current.template_ids),
                    data_preferences_id if data_preferences_id is not None else current.data_preferences_id,
                    _json_dumps(output_preferences if output_preferences is not None else current.output_preferences),
                    _json_dumps(metadata if metadata is not None else current.metadata),
                    _now().isoformat(),
                    profile_id,
                ),
            )
            conn.commit()

        return self.get(profile_id)

    def delete(self, profile_id: str) -> bool:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute("DELETE FROM analytics_profiles WHERE profile_id = ?", (profile_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get(self, profile_id: str) -> Optional[AnalyticsProfile]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT profile_id, user_id, name, description,
                       kpi_library, template_ids, data_preferences_id,
                       output_preferences, metadata, created_at, updated_at
                FROM analytics_profiles
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_profile(row)

    def list(self, user_id: str) -> List[AnalyticsProfile]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT profile_id, user_id, name, description,
                       kpi_library, template_ids, data_preferences_id,
                       output_preferences, metadata, created_at, updated_at
                FROM analytics_profiles
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [self._row_to_profile(row) for row in rows]


class SessionStore:
    """Persisted saved workspace sessions."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_sessions (
                    session_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    name TEXT,
                    workspace_state TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    FOREIGN KEY (profile_id) REFERENCES analytics_profiles(profile_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_saved_sessions_profile
                ON saved_sessions (profile_id, updated_at DESC)
                """
            )
            conn.commit()

    def _row_to_session(self, row: sqlite3.Row) -> SavedSession:
        return SavedSession(
            session_id=row["session_id"],
            profile_id=row["profile_id"],
            user_id=row["user_id"],
            name=row["name"],
            workspace_state=_json_loads(row["workspace_state"]),
            metadata=_json_loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )

    def save(
        self,
        profile_id: str,
        user_id: str,
        *,
        workspace_state: Dict[str, Any],
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> SavedSession:
        session_id = str(uuid.uuid4())
        now = _now().isoformat()
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO saved_sessions (
                    session_id,
                    profile_id,
                    user_id,
                    name,
                    workspace_state,
                    metadata,
                    created_at,
                    updated_at,
                    expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    profile_id,
                    user_id,
                    name,
                    _json_dumps(workspace_state),
                    _json_dumps(metadata or {}),
                    now,
                    now,
                    expires_at.isoformat() if expires_at else None,
                ),
            )
            conn.commit()

        return self.get(session_id)

    def update(
        self,
        session_id: str,
        *,
        workspace_state: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[SavedSession]:
        current = self.get(session_id)
        if not current:
            return None

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE saved_sessions
                SET name = ?,
                    workspace_state = ?,
                    metadata = ?,
                    updated_at = ?,
                    expires_at = ?
                WHERE session_id = ?
                """,
                (
                    name if name is not None else current.name,
                    _json_dumps(workspace_state if workspace_state is not None else current.workspace_state),
                    _json_dumps(metadata if metadata is not None else current.metadata),
                    _now().isoformat(),
                    expires_at.isoformat() if expires_at else (current.expires_at.isoformat() if current.expires_at else None),
                    session_id,
                ),
            )
            conn.commit()

        return self.get(session_id)

    def delete(self, session_id: str) -> bool:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute("DELETE FROM saved_sessions WHERE session_id = ?", (session_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get(self, session_id: str) -> Optional[SavedSession]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT session_id, profile_id, user_id, name,
                       workspace_state, metadata, created_at, updated_at, expires_at
                FROM saved_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return self._row_to_session(row)

    def list_for_profile(self, profile_id: str, limit: int = 50) -> List[SavedSession]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT session_id, profile_id, user_id, name,
                       workspace_state, metadata, created_at, updated_at, expires_at
                FROM saved_sessions
                WHERE profile_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (profile_id, limit),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]


