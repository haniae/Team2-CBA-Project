"""
Lookup utilities for canonical KPI definitions.

Provides a lightweight resolver that searches the local KPI library JSON
and applies synonym matching so the assistant can auto-fill formulas when
users omit them.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .parsing.ontology import METRIC_SYNONYMS

LOGGER = logging.getLogger(__name__)

_DEFAULT_LOOKUP_SCOPE = ["internal_dictionary", "financial_glossary", "web"]


def _normalise_token(value: str) -> str:
    """
    Normalise KPI names for lookup.

    Strips punctuation/spacing and lowercases so "Gross Margin" and "gross-margin"
    collapse to "grossmargin".
    """
    if not value:
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", value.lower())
    return cleaned


def _unit_to_metadata(unit: Optional[str]) -> Optional[str]:
    """Map descriptive unit labels to internal metadata codes."""
    if not unit:
        return None
    lowered = unit.lower()
    if lowered in {"percent", "percentage", "%"}:
        return "pct"
    if lowered in {"basis points", "bps"}:
        return "bps"
    if lowered in {"usd", "dollars", "currency"}:
        return "usd"
    if lowered in {"usd millions", "millions"}:
        return "usd_millions"
    if lowered in {"usd billions", "billions"}:
        return "usd_billions"
    return None


@dataclass(frozen=True)
class KPIDefinitionResult:
    """Resolved KPI definition with provenance metadata."""

    name: str
    formula: str
    description: Optional[str]
    source: Dict[str, Any]
    confidence: float
    scope: Sequence[str]
    unit: Optional[str] = None
    inputs: Sequence[str] = ()
    source_tags: Sequence[str] = ()
    raw_entry: Optional[Dict[str, Any]] = None


class KPIDefinitionLookup:
    """Resolve KPI definitions from local resources."""

    def __init__(
        self,
        *,
        library_path: Optional[Path] = None,
        lookup_scope: Optional[Sequence[str]] = None,
    ) -> None:
        self.library_path = library_path or Path(__file__).resolve().parent / "static" / "data" / "kpi_library.json"
        self.lookup_scope: Sequence[str] = tuple(lookup_scope or _DEFAULT_LOOKUP_SCOPE)
        self._library_index: Dict[str, Dict[str, Any]] = {}
        self._library_by_id: Dict[str, Dict[str, Any]] = {}
        self._synonym_map: Dict[str, str] = {}
        self._loaded = False

    def lookup(self, kpi_name: str) -> Optional[KPIDefinitionResult]:
        """Attempt to locate a KPI definition."""
        if not kpi_name:
            return None

        self._ensure_loaded()

        normalised = _normalise_token(kpi_name)
        if not normalised:
            return None

        entry = self._library_index.get(normalised)
        source_hint = "internal_dictionary"

        if not entry:
            canonical_id = self._synonym_map.get(normalised)
            if canonical_id:
                entry = self._library_by_id.get(canonical_id)

        if not entry:
            return None

        formula = (entry.get("formula_text") or "").strip()
        if not formula:
            return None

        description = entry.get("definition_short") or entry.get("interpretation")
        unit = _unit_to_metadata(entry.get("units"))
        inputs = self._extract_inputs(entry)
        source_tags = self._extract_source_tags(entry, inputs)

        return KPIDefinitionResult(
            name=entry.get("display_name") or kpi_name,
            formula=formula,
            description=description,
            source={
                "type": source_hint,
                "name": "BenchmarkOS KPI Library",
                "kpi_id": entry.get("kpi_id"),
                "last_updated": entry.get("last_updated"),
            },
            confidence=0.9,
            scope=self.lookup_scope,
            unit=unit,
            inputs=inputs,
            source_tags=source_tags,
            raw_entry=entry,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            data = json.loads(self.library_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            LOGGER.warning("KPI library not found at %s", self.library_path)
            self._loaded = True
            return
        except Exception as exc:
            LOGGER.error("Failed to load KPI library from %s: %s", self.library_path, exc)
            self._loaded = True
            return

        kpis = data.get("kpis") or []
        for entry in kpis:
            display_name = entry.get("display_name") or entry.get("kpi_id")
            if not display_name:
                continue
            norm = _normalise_token(display_name)
            if norm:
                self._library_index.setdefault(norm, entry)

            kpi_id = entry.get("kpi_id")
            if kpi_id:
                self._library_by_id.setdefault(kpi_id, entry)
                self._library_index.setdefault(_normalise_token(kpi_id), entry)

        # Build synonym map (alias -> kpi_id)
        for alias, canonical in METRIC_SYNONYMS.items():
            norm_alias = _normalise_token(alias)
            if not norm_alias:
                continue
            canonical_norm = _normalise_token(canonical)
            if canonical_norm in self._library_index:
                mapped = self._library_index[canonical_norm]
                kpi_id = mapped.get("kpi_id") or canonical_norm
                self._synonym_map[norm_alias] = kpi_id
            elif canonical in self._library_by_id:
                self._synonym_map[norm_alias] = canonical

        self._loaded = True

    @staticmethod
    def _extract_inputs(entry: Dict[str, Any]) -> List[str]:
        tokens: List[str] = []
        for spec in entry.get("inputs", []) or []:
            tag = spec.get("tag") or spec.get("name")
            if not tag:
                continue
            tokens.append(_normalise_token(tag))
            for component in spec.get("components", []) or []:
                tokens.append(_normalise_token(component))
        filtered = [token for token in tokens if token]
        return filtered

    @staticmethod
    def _extract_source_tags(entry: Dict[str, Any], inputs: Iterable[str]) -> List[str]:
        tags: List[str] = []
        seen = set()

        for token in inputs:
            if token and token not in seen:
                tags.append(token)
                seen.add(token)

        for spec in entry.get("inputs", []) or []:
            tag = spec.get("tag")
            if tag:
                norm = _normalise_token(tag)
                if norm and norm not in seen:
                    tags.append(norm)
                    seen.add(norm)

        return tags


__all__ = ["KPIDefinitionLookup", "KPIDefinitionResult"]

