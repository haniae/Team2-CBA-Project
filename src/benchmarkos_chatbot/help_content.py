"""Shared help content utilities with optional user customisation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Sequence

DEFAULT_PROMPTS: List[str] = [
    "Show Apple KPIs for 2022–2024",
    "Compare Microsoft and Amazon in FY2023",
    "What was Tesla’s 2022 revenue?",
]

DEFAULT_SECTIONS: List[Dict[str, Any]] = [
    {
        "icon": "📊",
        "title": "KPI & Comparisons",
        "command": "Metrics TICKER [YEAR | YEAR–YEAR] [+ peers]",
        "purpose": "Summarise a company’s finance snapshot or line up peers on one table.",
        "example": "Metrics AAPL 2023 vs MSFT",
        "delivers": "Revenue, profitability, free cash flow, ROE, valuation ratios.",
    },
    {
        "icon": "🧾",
        "title": "Facts from SEC Filings",
        "command": "Fact TICKER YEAR [metric]",
        "purpose": "Retrieve exactly what was reported in 10-K/10-Q filings.",
        "example": "Fact TSLA 2022 revenue",
        "delivers": "Original value, adjustment notes, and source reference.",
    },
    {
        "icon": "🧮",
        "title": "Scenario Modelling",
        "command": "Scenario TICKER NAME rev=+X% margin=+Y% mult=+Z",
        "purpose": "Run what-if cases for growth, margin shifts, or valuation moves.",
        "example": "Scenario NVDA Bull rev=+8% margin=+1.5% mult=+0.5",
        "delivers": "Projected revenue, margins, EPS/FCF change, implied valuation.",
    },
    {
        "icon": "⚙️",
        "title": "Data Management",
        "command": [
            "Ingest TICKER [years]",
            "Ingest status TICKER",
            "Audit TICKER [year]",
        ],
        "purpose": "Refresh data, track ingestion progress, or review the audit log.",
        "examples": [
            "Ingest META 5 — refreshes five fiscal years of filings and quotes.",
            "Audit META 2023 — lists the latest import activity and KPI updates.",
        ],
    },
]

def _parse_user_tips(raw: str) -> List[str]:
    """Interpret user-supplied HELP_TIPS content from the environment."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    tips: Iterable[str]
    if isinstance(parsed, list):
        tips = [str(entry) for entry in parsed]
    elif isinstance(parsed, str):
        tips = [parsed]
    else:
        # Fallback: split on pipes or newlines
        separators = "|" if "|" in raw else "\n"
        tips = raw.split(separators) if separators in raw else [raw]

    cleaned = [tip.strip() for tip in tips if str(tip).strip()]
    return cleaned


def load_user_tips() -> List[str] | None:
    """Return user-defined tips sourced from the HELP_TIPS environment variable."""
    raw = os.getenv("HELP_TIPS")
    if not raw:
        return None
    custom = _parse_user_tips(raw)
    return custom or None


HELP_TIPS: List[str] = load_user_tips() or []


def build_help_text(tips: Sequence[str] | None = None) -> str:
    """Compose the multiline help text used by the chatbot and CLI."""

    tips = list(tips or HELP_TIPS)
    lines: List[str] = [
        "📘 BenchmarkOS Copilot — Quick Reference",
        "",
        "How to ask:",
    ]

    lines.extend(f"• {prompt}" for prompt in DEFAULT_PROMPTS)
    lines.append("")
    lines.append("──────────────────────────────────────")

    for idx, section in enumerate(DEFAULT_SECTIONS):
        lines.append(f"{section['icon']} {section['title'].upper()}")

        command = section["command"]
        if isinstance(command, (list, tuple)):
            for i, entry in enumerate(command):
                prefix = "Command:" if i == 0 else "         "
                lines.append(f"{prefix} {entry}")
        else:
            lines.append(f"Command: {command}")

        if purpose := section.get("purpose"):
            lines.append(f"Purpose: {purpose}")
        if example := section.get("example"):
            lines.append(f"Example: {example}")
        if delivers := section.get("delivers"):
            lines.append(f"Delivers: {delivers}")

        if examples := section.get("examples"):
            lines.append("Examples:")
            lines.extend(f"• {item}" for item in examples)

        lines.append("")
        if idx != len(DEFAULT_SECTIONS) - 1:
            lines.append("──────────────────────────────────────")

    if tips:
        lines.append("──────────────────────────────────────")
        lines.append("💡 TIPS")
        for tip in tips:
            lines.append(f"• {tip}")

    return "\n".join(lines)


def get_help_metadata() -> Dict[str, Any]:
    """Return structured help data for the web UI."""
    return {
        "prompts": DEFAULT_PROMPTS,
        "sections": DEFAULT_SECTIONS,
        "tips": HELP_TIPS,
    }


HELP_TEXT = build_help_text()
