"""Alias generation and runtime resolution for ticker detection."""

from __future__ import annotations

import difflib
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

LOGGER = logging.getLogger(__name__)

_ALIASES_PATH = Path(__file__).resolve().with_name("aliases.json")
_UNIVERSE_PATH = Path(__file__).resolve().parents[3] / "data" / "tickers" / "universe_sp500.txt"
_TICKER_NAMES_PATH = Path(__file__).resolve().parents[3] / "docs" / "ticker_names.md"

_CORPORATE_SUFFIXES = {
    "inc",
    "incorporated",
    "inc.",
    "corporation",
    "corp",
    "corp.",
    "company",
    "co",
    "co.",
    "ltd",
    "ltd.",
    "plc",
    "llc",
    "n.a.",
    "n.a",
}

_OPTIONAL_TRAILING_WORDS = {
    "group",
    "holdings",
}

_MANUAL_OVERRIDES: Dict[str, str] = {
    "alphabet": "GOOGL",
    "alphabet inc": "GOOGL",
    "alphabet class a": "GOOGL",
    "alphabet class c": "GOOG",
    "google": "GOOGL",
    "googl": "GOOGL",
    "goog": "GOOG",
    "meta": "META",
    "facebook": "META",
    "unitedhealth": "UNH",
    "united health": "UNH",
    "jp morgan": "JPM",
    "jpmorgan": "JPM",
    "j.p. morgan": "JPM",
    "att": "T",
    "at t": "T",
    "berkshire hathaway": "BRK.B",
    "berkshire class b": "BRK.B",
    "berkshire class a": "BRK.A",
    "berkshire b": "BRK.B",
    "berkshire a": "BRK.A",
}

_TICKER_PATTERN = re.compile(r"\b([A-Za-z]{1,5})(?:\.[A-Za-z]{1,2})?\b")

_ALIAS_CACHE: Optional[Dict[str, Set[str]]] = None
_ALIAS_LOOKUP: Optional[Dict[str, List[str]]] = None
_TICKER_SET: Optional[Set[str]] = None


def _base_tokens(text: str) -> List[str]:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return []
    return normalized.split(" ")


def _strip_leading_the(tokens: Sequence[str]) -> List[str]:
    result = list(tokens)
    while result and result[0] == "the":
        result.pop(0)
    return result


def _strip_suffixes(tokens: Sequence[str]) -> List[str]:
    result = list(tokens)
    while result and result[-1] in _CORPORATE_SUFFIXES:
        result.pop()
    return result


def _strip_optional_trailing(tokens: Sequence[str]) -> List[str]:
    result = list(tokens)
    while result and result[-1] in _OPTIONAL_TRAILING_WORDS:
        result.pop()
    return result


def normalize_alias(text: str) -> str:
    """Canonical normalisation for alias comparisons."""
    tokens = _base_tokens(text)
    if not tokens:
        return ""
    tokens = _strip_leading_the(tokens)
    tokens = _strip_suffixes(tokens)
    tokens = _strip_optional_trailing(tokens)
    return " ".join(tokens).strip()


def _alias_variants(tokens: Sequence[str]) -> Set[str]:
    """Produce a set of alias variants for the supplied token list."""
    variants: Set[str] = set()

    def _add_variant(candidate: Sequence[str]) -> None:
        joined = " ".join(candidate).strip()
        if joined:
            variants.add(normalize_alias(joined))
            compact = "".join(candidate).strip()
            if compact:
                variants.add(normalize_alias(compact))

    bases: List[List[str]] = []
    base = [token for token in tokens if token]
    if base:
        bases.append(base)
        bases.append(_strip_leading_the(base))

    for candidate in bases:
        if not candidate:
            continue
        _add_variant(candidate)
        stripped = _strip_suffixes(candidate)
        _add_variant(stripped)
        stripped_optional = _strip_optional_trailing(stripped)
        _add_variant(stripped_optional)
        if candidate and len(candidate[0]) > 2:
            _add_variant(candidate[:1])

    return {alias for alias in variants if alias}


def _load_universe() -> List[str]:
    if not _UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"S&P 500 universe file missing: {_UNIVERSE_PATH}")
    tickers: List[str] = []
    for line in _UNIVERSE_PATH.read_text(encoding="utf-8").splitlines():
        token = line.strip().upper()
        if not token or token.startswith("#"):
            continue
        tickers.append(token)
    return tickers


def _load_name_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not _TICKER_NAMES_PATH.exists():
        return mapping
    line_pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z0-9.-]+)\)")
    for raw in _TICKER_NAMES_PATH.read_text(encoding="utf-8").splitlines():
        match = line_pattern.match(raw.strip())
        if not match:
            continue
        mapping[match.group("ticker").upper()] = match.group("name").strip()
    return mapping


def normalise_compact(alias: str) -> str:
    """Return a compacted variant of an alias (without whitespace)."""
    compact = alias.replace(" ", "")
    return normalize_alias(compact) if compact else ""


def _apply_manual_overrides(alias_map: Dict[str, Set[str]]) -> None:
    owned_aliases: List[Tuple[str, Optional[str], str]] = []
    for raw_alias, ticker in _MANUAL_OVERRIDES.items():
        if ticker not in alias_map:
            continue
        normalised = normalize_alias(raw_alias)
        if not normalised:
            continue
        compact = normalise_compact(normalised) or None
        alias_map[ticker].add(normalised)
        if compact:
            alias_map[ticker].add(compact)
        owned_aliases.append((normalised, compact, ticker))

    for canonical, compact, owner in owned_aliases:
        for ticker, aliases in alias_map.items():
            if ticker == owner:
                continue
            aliases.discard(canonical)
            if compact:
                aliases.discard(compact)


def build_alias_map(max_aliases: int = 40) -> Dict[str, List[str]]:
    """Construct the alias map from canonical data sources."""
    universe = _load_universe()
    names = _load_name_map()
    alias_map: Dict[str, Set[str]] = {ticker: set() for ticker in universe}

    for ticker in universe:
        canonical_name = names.get(ticker, ticker)
        tokens = _base_tokens(canonical_name) or _base_tokens(ticker)
        variants = _alias_variants(tokens)
        if not variants:
            variants.add(normalize_alias(ticker))
        alias_map[ticker].update(variants)
        alias_map[ticker].add(normalize_alias(ticker))
        alias_map[ticker].add(normalize_alias(ticker.replace(".", " ")))
        alias_map[ticker].add(normalize_alias(ticker.replace(".", "")))
        alias_map[ticker].add(normalise_compact(" ".join(tokens)))

    _apply_manual_overrides(alias_map)

    final_map: Dict[str, List[str]] = {}
    for ticker, aliases in alias_map.items():
        cleaned = []
        for alias in sorted({normalize_alias(entry) for entry in aliases if entry}, key=lambda val: (len(val), val)):
            if not alias:
                continue
            if len(alias) == 1 and alias.upper() != ticker:
                continue
            if alias not in cleaned:
                cleaned.append(alias)
            if len(cleaned) >= max_aliases:
                break
        if not cleaned:
            cleaned = [normalize_alias(ticker)]
        final_map[ticker] = cleaned
    return final_map


def _write_aliases_json(alias_map: Dict[str, List[str]]) -> None:
    _ALIASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ALIASES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(alias_map, handle, indent=2, sort_keys=True)


def _build_lookup(alias_map: Dict[str, Set[str]]) -> Dict[str, List[str]]:
    lookup: Dict[str, List[str]] = {}
    for ticker, aliases in alias_map.items():
        for alias in aliases:
            bucket = lookup.setdefault(alias, [])
            if ticker not in bucket:
                bucket.append(ticker)

    preferences: Dict[str, str] = {}
    for raw_alias, target in _MANUAL_OVERRIDES.items():
        canonical = normalize_alias(raw_alias)
        if canonical:
            preferences[canonical] = target
            compact = normalise_compact(canonical)
            if compact:
                preferences[compact] = target

    for alias, preferred in preferences.items():
        tickers = lookup.get(alias)
        if not tickers or preferred not in tickers:
            continue
        tickers.remove(preferred)
        tickers.insert(0, preferred)

    return lookup


def load_aliases() -> Dict[str, Set[str]]:
    """Load (or build) the alias map for runtime resolution."""
    global _ALIAS_CACHE, _ALIAS_LOOKUP, _TICKER_SET
    if _ALIAS_CACHE is not None:
        return _ALIAS_CACHE

    if _ALIASES_PATH.exists():
        raw: Dict[str, Iterable[str]] = json.loads(_ALIASES_PATH.read_text(encoding="utf-8"))
    else:
        LOGGER.info("Alias file missing. Regenerating %s", _ALIASES_PATH)
        raw = build_alias_map()
        _write_aliases_json(raw)

    alias_cache: Dict[str, Set[str]] = {}
    for ticker, values in raw.items():
        bucket = {normalize_alias(value) for value in values if value}
        if not bucket:
            bucket.add(normalize_alias(ticker))
        alias_cache[ticker.upper()] = bucket

    _ALIAS_CACHE = alias_cache
    _ALIAS_LOOKUP = _build_lookup(alias_cache)
    _TICKER_SET = set(alias_cache.keys())
    return alias_cache


def _ensure_lookup_loaded() -> Tuple[Dict[str, Set[str]], Dict[str, List[str]], Set[str]]:
    alias_map = load_aliases()
    assert _ALIAS_LOOKUP is not None
    assert _TICKER_SET is not None
    return alias_map, _ALIAS_LOOKUP, _TICKER_SET


def resolve_tickers_freeform(text: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """Resolve tickers from free-form text using aliases and fuzzy fallback."""
    alias_map, lookup, ticker_set = _ensure_lookup_loaded()
    lowered_text = text or ""
    normalized_text = normalize_alias(lowered_text)
    padded_text = f" {normalized_text} "
    matches: List[Tuple[int, str, str]] = []
    seen: Set[str] = set()
    warnings: List[str] = []

    for match in _TICKER_PATTERN.finditer(lowered_text):
        raw_token = match.group(0)
        token = raw_token.upper()
        if len(token) <= 2 and not raw_token.isupper():
            continue
        candidate = token
        if candidate in ticker_set:
            if candidate not in seen:
                matches.append((match.start(), token, candidate))
                seen.add(candidate)
            continue
        if candidate.replace(".", "") in ticker_set:
            normalized_candidate = candidate.replace(".", "")
            if normalized_candidate not in seen:
                matches.append((match.start(), token, normalized_candidate))
                seen.add(normalized_candidate)

    for alias, tickers in lookup.items():
        marker = f" {alias} "
        position = padded_text.find(marker)
        if position == -1:
            continue
        if len(alias) <= 2:
            continue
        for target in tickers:
            if target in seen:
                continue
            matches.append((position, alias, target))
            seen.add(target)
            break

    matches.sort(key=lambda item: item[0])
    resolved = [{"input": match[1], "ticker": match[2]} for match in matches]

    alias_candidates = list(lookup.keys())

    def _try_add_alias(alias_key: str, source_value: str, mark_warning: bool = False) -> bool:
        if not alias_key:
            return False
        for ticker in lookup.get(alias_key, []):
            if ticker in seen:
                continue
            resolved.append({"input": source_value, "ticker": ticker})
            seen.add(ticker)
            if mark_warning:
                warnings.append("fuzzy_match")
            return True
        return False

    tokens = [token for token in _base_tokens(lowered_text) if token]
    max_window = min(4, len(tokens))
    for window in range(max_window, 0, -1):
        for start_idx in range(len(tokens) - window + 1):
            phrase_tokens = tokens[start_idx : start_idx + window]
            candidate_phrase = " ".join(phrase_tokens)
            if not candidate_phrase:
                continue
            normalised_phrase = normalize_alias(candidate_phrase)
            if normalised_phrase and _try_add_alias(normalised_phrase, candidate_phrase):
                continue
            if len(normalised_phrase) <= 2:
                continue
            best_alias = None
            best_score = 0.0
            for alias in alias_candidates:
                score = difflib.SequenceMatcher(None, normalised_phrase, alias).ratio()
                if score > best_score:
                    best_alias = alias
                    best_score = score
            if best_alias and best_score >= 0.95:
                if _try_add_alias(best_alias, candidate_phrase, mark_warning=True):
                    continue

    return resolved, warnings


__all__ = [
    "build_alias_map",
    "load_aliases",
    "normalize_alias",
    "resolve_tickers_freeform",
]
