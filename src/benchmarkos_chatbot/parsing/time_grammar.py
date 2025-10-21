"""Flexible time-period grammar for financial queries."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

_YEAR_TOKEN = r"(?:[12]\d{3}|\d{2})"
FY_PATTERN = re.compile(rf"(?i)\bfy['’\-\s]*({_YEAR_TOKEN})(?=[^\d]|$)")
FISCAL_PATTERN = re.compile(
    rf"(?i)\b(?:fiscal|financial)\s+(?:year\s*)?({_YEAR_TOKEN})(?=[^\d]|$)"
)
CY_PATTERN = re.compile(
    rf"(?i)\bcy['’\-\s]*({_YEAR_TOKEN})(?=[^\d]|$)|\bcalendar\s+([12]\d{{3}})\b"
)
YEAR_PATTERN = re.compile(r"(?<!\d)([12]\d{3})(?!\d)")
RANGE_JOINER = r"(?:-|–|—|to|\.\.)"
RANGE_PATTERN = re.compile(
    rf"(?i)\b(?:(FY|CY|fiscal|financial)(?:\s+year\s*)?)?{_YEAR_TOKEN}\s*{RANGE_JOINER}\s*"
    rf"(?:(FY|CY|fiscal|financial)(?:\s+year\s*)?)?{_YEAR_TOKEN}\b"
)
QUARTER_RANGE_PATTERN = re.compile(
    rf"(?i)\bQ([1-4])\s*{RANGE_JOINER}\s*Q([1-4])(?:\s*({_YEAR_TOKEN}))?\b"
)
RELATIVE_PATTERN = re.compile(r"(?i)\blast\s+(\d{1,2})\s+(quarters?|years?)\b")
_NORMALIZATION_RULES: Sequence[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\bfisical\b"), "fiscal"),
    (re.compile(r"(?i)\bfiscaly\b"), "fiscal"),
    (re.compile(r"(?i)\bfinacial\b"), "financial"),
    (re.compile(r"(?i)\bcalender\b"), "calendar"),
    (re.compile(r"(?i)\bf\s*[\-']?\s*y\b"), "FY"),
    (re.compile(r"(?i)\bc\s*[\-']?\s*y\b"), "CY"),
]
QUARTER_COMBOS: Sequence[Tuple[re.Pattern, Tuple[int, int]]] = [
    (re.compile(rf"(?i)\bQ([1-4])\s*FY['’\-\s]*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\bFY['’\-\s]*({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*(?:CY|calendar)\s*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\b(?:CY|calendar)\s*({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*({_YEAR_TOKEN})\b"), (1, 2)),
    (re.compile(rf"(?i)\b({_YEAR_TOKEN})\s*Q([1-4])\b"), (2, 1)),
    (re.compile(r"(?i)\bQ([1-4])\s*'([0-9]{2})\b"), (1, 2)),
    (re.compile(r"(?i)\b'([0-9]{2})\s*Q([1-4])\b"), (2, 1)),
]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    for pattern, replacement in _NORMALIZATION_RULES:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _convert_two_digit_year(value: str) -> int:
    number = int(value)
    if number <= 30:
        return 2000 + number
    return 1900 + number


def _extract_year(value: str) -> int:
    cleaned = (value or "").upper()
    cleaned = re.sub(r"(?<=\d)[O](?=\d)", "0", cleaned)
    cleaned = re.sub(r"(?<=\d)[IL](?=\d)", "1", cleaned)
    cleaned = re.sub(r"[O](?=\d{2,})", "0", cleaned)
    digits = re.findall(r"\d+", cleaned)
    if not digits:
        raise ValueError(f"No year digits found in '{value}'")
    token = digits[-1]
    if len(token) == 2:
        return _convert_two_digit_year(token)
    if len(token) == 3:
        # Treat 3-digit tokens as the last two digits of a fiscal year (rare edge case)
        return _convert_two_digit_year(token[-2:])
    if len(token) > 4:
        token = token[-4:]
    return int(token)


def _clean_quarter(value: str) -> Optional[int]:
    digits = re.findall(r"\d", (value or "").upper())
    if not digits:
        return None
    quarter = int(digits[-1])
    if 1 <= quarter <= 4:
        return quarter
    return None


def _is_calendar_prefix(prefix: Optional[str]) -> bool:
    if not prefix:
        return False
    pref = prefix.lower()
    return pref.startswith("cy") or pref.startswith("cal")


def _is_fiscal_prefix(prefix: Optional[str]) -> bool:
    if not prefix:
        return False
    pref = prefix.lower()
    return pref.startswith("fy") or pref.startswith("fis") or pref.startswith("fin")


def _span_overlaps(span: Tuple[int, int], intervals: List[Tuple[int, int]]) -> bool:
    s1, e1 = span
    return any(not (e1 <= s2 or e2 <= s1) for s2, e2 in intervals)


def _add_spec(
    specs: List[Dict[str, Any]],
    seen: set,
    start: int,
    end: int,
    quarter: Optional[str],
) -> None:
    key = (start, end, quarter)
    if key in seen:
        return
    seen.add(key)
    specs.append({"start": start, "end": end, "quarter": quarter})


def parse_periods(text: str, prefer_fiscal: bool = True) -> Dict[str, Any]:
    """Parse flexible period expressions from text into structured metadata."""

    original = _normalize(text)
    lower_text = original.lower()
    warnings: List[str] = []

    relative_match = RELATIVE_PATTERN.search(lower_text)
    if relative_match:
        count = int(relative_match.group(1))
        unit = relative_match.group(2).lower()
        is_quarter = unit.startswith("quarter")
        normalize_to_fiscal = prefer_fiscal
        if is_quarter:
            granularity = "fiscal_quarter" if normalize_to_fiscal else "calendar_quarter"
        else:
            granularity = "fiscal_year" if normalize_to_fiscal else "calendar_year"
        warnings.append(f"relative_window: {count} {unit}")
        return {
            "type": "relative",
            "granularity": granularity,
            "items": [],
            "normalize_to_fiscal": normalize_to_fiscal,
            "warnings": warnings,
        }

    specs: List[Dict[str, Any]] = []
    seen_specs: set = set()
    consumed_spans: List[Tuple[int, int]] = []
    calendar_override = False
    fiscal_token_present = bool(FY_PATTERN.search(lower_text) or FISCAL_PATTERN.search(lower_text))

    # Handle quarter ranges first (e.g., Q1-Q4 2023) - before single quarters
    for match in QUARTER_RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        quarter1, quarter2, year_token = match.groups()
        year = _extract_year(year_token) if year_token else None
        if year is None:
            continue
        q1, q2 = int(quarter1), int(quarter2)
        if q2 < q1:
            q1, q2 = q2, q1
        # Add quarter range as multiple quarters
        for q in range(q1, q2 + 1):
            _add_spec(specs, seen_specs, year, year, f"Q{q}")
        consumed_spans.append(start_span)

    for pattern, order in QUARTER_COMBOS:
        for match in pattern.finditer(original):
            start, end = match.span()
            if _span_overlaps((start, end), consumed_spans):
                continue
            first_idx, second_idx = order
            quarter_token = match.group(first_idx)
            year_token = match.group(second_idx)
            if year_token is None:
                year_token = quarter_token
                quarter_token = match.group(2 if first_idx == 1 else 1)
            quarter_num = _clean_quarter(quarter_token)
            if quarter_num is None:
                continue
            year = _extract_year(year_token)
            calendar_hint = "calendar" in match.group(0).lower() or "cy" in match.group(0).lower()
            if calendar_hint:
                calendar_override = True
            if re.search(r"(?i)\bFY\b|\bfiscal\b|\bfinancial\b", match.group(0)):
                fiscal_token_present = True
            _add_spec(specs, seen_specs, year, year, f"Q{quarter_num}")
            consumed_spans.append((start, end))

    for match in RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        groups = match.groups()
        if len(groups) >= 4:
            prefix1, year1, prefix2, year2 = groups[:4]
        elif len(groups) == 3:
            # Handle case where one prefix is missing
            prefix1, year1, prefix2 = groups[:3]
            year2 = groups[2] if groups[2] else groups[1]
        elif len(groups) == 2:
            # Handle case where both prefixes are missing
            year1, year2 = groups[:2]
            prefix1, prefix2 = None, None
        else:
            # Skip this match if we don't have enough groups
            continue
        if year1 is None or year2 is None:
            continue
        y1 = _extract_year(year1)
        y2 = _extract_year(year2)
        if y2 < y1:
            y1, y2 = y2, y1
        if _is_calendar_prefix(prefix1) or _is_calendar_prefix(prefix2):
            calendar_override = True
        if _is_fiscal_prefix(prefix1) or _is_fiscal_prefix(prefix2):
            fiscal_token_present = True
        _add_spec(specs, seen_specs, y1, y2, None)
        consumed_spans.append(start_span)


    for match in FY_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        raw_year = match.group(1)
        year = _extract_year(raw_year)
        fiscal_token_present = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in FISCAL_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        raw_year = match.group(1)
        year = _extract_year(raw_year)
        fiscal_token_present = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in CY_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        year_groups = [g for g in match.groups() if g]
        if not year_groups:
            continue
        raw_year = year_groups[0]
        year = _extract_year(raw_year)
        calendar_override = True
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    for match in YEAR_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        year = int(match.group(1))
        _add_spec(specs, seen_specs, year, year, None)
        consumed_spans.append(span)

    explicit_calendar = bool(re.search(r"(?i)(\bCY\s*[12]\d{3}\b|\bcalendar\b)", original))
    if explicit_calendar:
        calendar_override = True

    normalize_to_fiscal = prefer_fiscal
    if calendar_override:
        normalize_to_fiscal = False
    elif fiscal_token_present:
        normalize_to_fiscal = True

    if not specs:
        granularity = "fiscal_year" if normalize_to_fiscal else "calendar_year"
        return {
            "type": "latest",
            "granularity": granularity,
            "items": [],
            "normalize_to_fiscal": normalize_to_fiscal,
            "warnings": warnings,
        }

    has_quarter = any(spec.get("quarter") for spec in specs)
    specs_sorted = sorted(specs, key=lambda spec: (spec["start"], spec.get("quarter") or ""))

    if calendar_override:
        granularity = "calendar_quarter" if has_quarter else "calendar_year"
    else:
        granularity = "fiscal_quarter" if has_quarter else "fiscal_year"

    range_spec = next((spec for spec in specs_sorted if spec["start"] != spec["end"]), None)

    if range_spec is None and len(specs_sorted) == 1:
        period_type = "single"
        items = [_spec_to_item(specs_sorted[0])]
    elif range_spec is not None:
        period_type = "range"
        items = [
            _spec_to_item({"start": range_spec["start"], "end": range_spec["start"], "quarter": range_spec.get("quarter")}),
            _spec_to_item({"start": range_spec["end"], "end": range_spec["end"], "quarter": range_spec.get("quarter")}),
        ]
    else:
        period_type = "multi"
        items = [_spec_to_item(spec) for spec in specs_sorted]

    return {
        "type": period_type,
        "granularity": granularity,
        "items": items,
        "normalize_to_fiscal": normalize_to_fiscal,
        "warnings": warnings,
    }


def _spec_to_item(spec: Dict[str, Any]) -> Dict[str, Optional[int]]:
    return {
        "fy": spec["start"],
        "fq": int(spec["quarter"][1]) if spec.get("quarter") else None,
    }


__all__ = ["parse_periods"]
