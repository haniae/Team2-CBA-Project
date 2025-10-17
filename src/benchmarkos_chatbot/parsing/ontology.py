"""Shared ontology helpers for natural-language parsing."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict

METRIC_SYNONYMS: Dict[str, str] = {
    # Revenue / sales
    "revenue": "revenue",
    "sales": "revenue",
    "top line": "revenue",
    "topline": "revenue",
    "rev": "revenue",
    # Profitability
    "net income": "net_income",
    "net profit": "net_income",
    "profit": "net_income",
    "earnings": "net_income",
    "bottom line": "net_income",
    "earnings per share": "eps_diluted",
    "eps": "eps_diluted",
    "diluted eps": "eps_diluted",
    # Operating metrics
    "ebitda": "ebitda",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "ebit": "operating_income",
    "gross profit": "gross_profit",
    "gross margin": "gross_profit",
    "operating margin": "operating_margin",
    "net margin": "net_margin",
    "profit margin": "profit_margin",
    # Cash flow & returns
    "free cash flow": "free_cash_flow",
    "fcf": "free_cash_flow",
    "cash conversion": "cash_conversion",
    "return on equity": "return_on_equity",
    "roe": "return_on_equity",
    "return on assets": "return_on_assets",
    "roa": "return_on_assets",
    "return on invested capital": "return_on_invested_capital",
    "roic": "return_on_invested_capital",
    # Valuation
    "pe": "pe_ratio",
    "p/e": "pe_ratio",
    "price to earnings": "pe_ratio",
    "pe ratio": "pe_ratio",
    "price earnings": "pe_ratio",
    "ev/ebitda": "ev_ebitda",
    "enterprise value to ebitda": "ev_ebitda",
    "pb": "pb_ratio",
    "p/b": "pb_ratio",
    "price to book": "pb_ratio",
    "peg": "peg_ratio",
    "peg ratio": "peg_ratio",
    # Shareholder returns
    "dividend yield": "dividend_yield",
    "tsr": "tsr",
    "total shareholder return": "tsr",
    "buyback": "share_buyback_intensity",
    "repurchase": "share_buyback_intensity",
    "share repurchase": "share_buyback_intensity",
}


def _normalize_alias(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _simplify_company_name(name: str) -> str:
    simplified = re.sub(
        r"\b(the|incorporated|inc|corporation|corp|company|co|plc|ltd|limited|group|holding|holdings)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )
    simplified = re.sub(r"\s+", " ", simplified).strip()
    return simplified


@lru_cache(maxsize=1)
def load_ticker_aliases() -> Dict[str, str]:
    """Load company name aliases from documentation."""
    base_path = Path(__file__).resolve().parents[3]
    mapping: Dict[str, str] = {}
    source = base_path / "docs" / "ticker_names.md"
    if not source.exists():
        return mapping

    line_pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z.-]+)\)")
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        match = line_pattern.match(raw_line.strip())
        if not match:
            continue
        name = match.group("name")
        ticker = match.group("ticker").upper()

        aliases = {
            _normalize_alias(name),
            _normalize_alias(_simplify_company_name(name)),
            _normalize_alias(ticker),
        }

        words = _simplify_company_name(name).split()
        if words:
            aliases.add(_normalize_alias(words[0]))

        for alias in aliases:
            if not alias:
                continue
            mapping.setdefault(alias, ticker)

    return mapping


TICKER_ALIASES: Dict[str, str] = load_ticker_aliases()

for canonical in list({v for v in METRIC_SYNONYMS.values()}):
    METRIC_SYNONYMS.setdefault(canonical, canonical)
