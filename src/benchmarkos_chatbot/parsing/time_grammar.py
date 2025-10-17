"""Flexible time-period grammar for financial queries."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

_YEAR_TOKEN = r"([12]\d{3}|\d{2})"
FY_PATTERN = re.compile(rf"(?i)\bFY\s*{_YEAR_TOKEN}\b")
CY_PATTERN = re.compile(rf"(?i)\bCY\s*{_YEAR_TOKEN}\b|\bcalendar\s+([12]\d{{3}})\b")
YEAR_PATTERN = re.compile(r"(?<!\d)([12]\d{3})(?!\d)")
RANGE_JOINER = r"(?:-|–|—|to|\.\.)"
RANGE_PATTERN = re.compile(
    rf"(?i)\b(?:(FY|CY)\s*)?{_YEAR_TOKEN}\s*{RANGE_JOINER}\s*(?:(FY|CY)\s*)?{_YEAR_TOKEN}\b"
)
RELATIVE_PATTERN = re.compile(r"(?i)\blast\s+(\d{1,2})\s+(quarters?|years?)\b")
QUARTER_COMBOS: Sequence[Tuple[re.Pattern, Tuple[int, int]]] = [
    (re.compile(rf"(?i)\bQ([1-4])\s*FY\s*{_YEAR_TOKEN}\b"), (1, 2)),
    (re.compile(rf"(?i)\bFY\s*{_YEAR_TOKEN}\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*(?:CY|calendar)\s*{_YEAR_TOKEN}\b"), (1, 2)),
    (re.compile(rf"(?i)\b(?:CY|calendar)\s*{_YEAR_TOKEN}\s*Q([1-4])\b"), (2, 1)),
    (re.compile(rf"(?i)\bQ([1-4])\s*{_YEAR_TOKEN}\b"), (1, 2)),
    (re.compile(rf"(?i)\b{_YEAR_TOKEN}\s*Q([1-4])\b"), (2, 1)),
    (re.compile(r"(?i)\bQ([1-4])\s*'([0-9]{2})\b"), (1, 2)),
    (re.compile(r"(?i)\b'([0-9]{2})\s*Q([1-4])\b"), (2, 1)),
]


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _convert_two_digit_year(value: str) -> int:
    number = int(value)
    if number <= 30:
        return 2000 + number
    return 1900 + number


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
    fiscal_token_present = bool(FY_PATTERN.search(lower_text))

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
            quarter_num = int(quarter_token)
            if len(year_token) == 2:
                year = _convert_two_digit_year(year_token)
            else:
                year = int(year_token)
            calendar_hint = "calendar" in match.group(0).lower() or "cy" in match.group(0).lower()
            if calendar_hint:
                calendar_override = True
            if re.search(r"(?i)\bFY\b", match.group(0)):
                fiscal_token_present = True
            _add_spec(specs, seen_specs, year, year, f"Q{quarter_num}")
            consumed_spans.append((start, end))

    for match in RANGE_PATTERN.finditer(original):
        start_span = match.span()
        if _span_overlaps(start_span, consumed_spans):
            continue
        prefix1, year1, prefix2, year2 = match.groups()
        y1 = _convert_two_digit_year(year1) if len(year1) == 2 else int(year1)
        y2 = _convert_two_digit_year(year2) if len(year2) == 2 else int(year2)
        if y2 < y1:
            y1, y2 = y2, y1
        if (prefix1 and prefix1.upper() == "CY") or (prefix2 and prefix2.upper() == "CY"):
            calendar_override = True
        if (prefix1 and prefix1.upper() == "FY") or (prefix2 and prefix2.upper() == "FY"):
            fiscal_token_present = True
        _add_spec(specs, seen_specs, y1, y2, None)
        consumed_spans.append(start_span)

    for match in FY_PATTERN.finditer(original):
        span = match.span()
        if _span_overlaps(span, consumed_spans):
            continue
        raw_year = match.group(1)
        year = _convert_two_digit_year(raw_year) if len(raw_year) == 2 else int(raw_year)
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
        year = _convert_two_digit_year(raw_year) if len(raw_year) == 2 else int(raw_year)
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
