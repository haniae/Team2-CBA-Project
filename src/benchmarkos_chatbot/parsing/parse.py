"""Natural-language parsing utilities for the BenchmarkOS chatbot."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from .alias_builder import resolve_tickers_freeform
from .ontology import METRIC_SYNONYMS
from .time_grammar import parse_periods

_METRIC_ITEMS = sorted(METRIC_SYNONYMS.items(), key=lambda item: -len(item[0]))

INTENT_COMPARE_PATTERN = re.compile(r"\b(compare|vs|versus)\b")
INTENT_TREND_PATTERN = re.compile(
    r"(over time|over the last|history|trend|past \d+\s+(?:years?|quarters?))"
)
INTENT_LAST_PATTERN = re.compile(r"\blast\s+\d+\s+(quarters?|years?)\b")
INTENT_RANK_PATTERN = re.compile(
    r"\b(which|highest|lowest|top|best|worst|most|least|fastest|slowest|"
    r"rank|ranking|ranked|best performing|worst performing|"
    r"which.*has.*best|which.*has.*worst|which.*has.*highest|which.*has.*lowest|"
    r"which.*company.*has|which.*stock.*has|which.*firm.*has)\b"
)
INTENT_EXPLAIN_PATTERN = re.compile(
    r"\b(define|explain|tell me about|describe|break down|"
    r"how (?:do|does|is|to).*(?:compute|calculate|calculated|work|mean)|"
    r"what does.*mean|what.*mean|explain.*mean|"
    r"definition of|meaning of|explanation of)\b"
)


def normalize(text: str) -> str:
    """Return a lower-cased, whitespace-collapsed representation."""
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def parse_to_structured(text: str) -> Dict[str, Any]:
    norm = normalize(text)
    lowered_full = unicodedata.normalize("NFKC", text).lower()

    ticker_matches, ticker_warnings = resolve_tickers_freeform(text)
    metric_matches = resolve_metrics(text, lowered_full)
    periods = parse_periods(norm, prefer_fiscal=False)

    intent = classify_intent(norm, ticker_matches, metric_matches, periods)

    warnings = list(periods.get("warnings", [])) + ticker_warnings
    if not ticker_matches:
        warnings.append("missing_ticker")
        ticker_matches = [{"input": "AAPL", "ticker": "AAPL"}]
        warnings.append("default_ticker:AAPL")
    if not metric_matches:
        warnings.append("missing_metric")

    structured = {
        "intent": intent,
        "tickers": [{"input": entry["input"], "ticker": entry["ticker"]} for entry in ticker_matches],
        "vmetrics": [{"input": entry["input"], "key": entry["metric_id"]} for entry in metric_matches],
        "periods": periods,
        "computed": infer_computed(metric_matches),
        "filters": {"currency": "USD", "unit_preference": "auto"},
        "free_text": text,
        "norm_text": norm,  # Fix: Add norm_text field
        "warnings": warnings,
    }
    return structured


def resolve_metrics(text: str, lowered_full: str) -> List[Dict[str, Any]]:
    """Detect requested metrics from synonyms and canonical names."""
    matches: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for alias, metric_id in _METRIC_ITEMS:
        if not alias:
            continue
        escaped = re.escape(alias).replace(r"\ ", r"\s+")
        pattern = re.compile(r"\b" + escaped + r"\b")
        found = pattern.search(lowered_full)
        if not found:
            continue
        if metric_id in seen:
            continue
        original_fragment = text[found.start():found.end()]
        matches.append(
            {
                "input": original_fragment,
                "metric_id": metric_id,
                "position": found.start(),
            }
        )
        seen.add(metric_id)

    matches.sort(key=lambda item: item["position"])
    return [{"input": item["input"], "metric_id": item["metric_id"]} for item in matches]


def classify_intent(
    norm_text: str,
    tickers: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    periods: Dict[str, Any],
) -> str:
    """Infer the user's intent from tokens, tickers, metrics, and period metadata."""

    unique_tickers = {entry["ticker"] for entry in tickers}
    period_type = periods.get("type")

    # Priority order: rank > explain > trend > compare > lookup
    
    # Check for rank intent first (highest priority for ranking questions)
    if INTENT_RANK_PATTERN.search(norm_text):
        # For ranking queries, only parse tickers if explicitly mentioned
        if tickers and not any(ticker in norm_text.upper() for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]):
            # Likely over-parsing, return rank without ticker dependency
            pass
        return "rank"

    # Check for explain intent (second priority)
    if INTENT_EXPLAIN_PATTERN.search(norm_text):
        # For explain queries, only parse tickers if explicitly mentioned
        if tickers and not any(ticker in norm_text.upper() for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]):
            # Likely over-parsing, return explain without ticker dependency
            pass
        return "explain_metric"

    # Check for trend intent (third priority)
    if (
        INTENT_TREND_PATTERN.search(norm_text)
        or INTENT_LAST_PATTERN.search(norm_text)
        or period_type in {"range", "multi", "relative"}
        or re.search(r"Q\d+-Q\d+", norm_text)  # Quarter range pattern
    ):
        return "trend"

    # Check for compare intent (fourth priority)
    # Only classify as compare if explicitly compare keywords OR multiple tickers with clear compare context
    if (INTENT_COMPARE_PATTERN.search(norm_text) or 
        (len(unique_tickers) >= 2 and ("compare" in norm_text or "vs" in norm_text or "versus" in norm_text))):
        return "compare"

    # Default to lookup intent
    return "lookup"


def infer_computed(metrics: List[Dict[str, Any]]) -> List[str]:
    """Placeholder for future computed metrics inference."""
    return []


__all__ = ["parse_to_structured", "normalize", "resolve_metrics"]
