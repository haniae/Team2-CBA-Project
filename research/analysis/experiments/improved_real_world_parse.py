"""Improved Real-World Usage Intent Classification."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot.parsing.alias_builder import resolve_tickers_freeform
from benchmarkos_chatbot.parsing.ontology import METRIC_SYNONYMS
from benchmarkos_chatbot.parsing.time_grammar import parse_periods

_METRIC_ITEMS = sorted(METRIC_SYNONYMS.items(), key=lambda item: -len(item[0]))

# Improved Real-World Usage Intent Patterns
INTENT_COMPARE_PATTERN = re.compile(
    r"\b(compare|vs|versus|compared to|relative to|against|how does.*compare|which is better)\b"
)

INTENT_RANK_PATTERN = re.compile(
    r"\b(which|highest|lowest|top|best|worst|most|least|fastest|slowest|"
    r"best performing|worst performing|most profitable|least profitable|"
    r"fastest growing|slowest growing|top performing|bottom performing|"
    r"which.*has.*best|which.*has.*highest|which.*has.*most|"
    r"which.*has.*fastest|which.*stock.*best|which.*company.*best|"
    r"which.*company.*has.*best|which.*tech.*company.*best)\b"
)

INTENT_EXPLAIN_PATTERN = re.compile(
    r"\b(define|how (?:do|does|is|to).*(?:compute|calculated|measure)|"
    r"explain.*meaning|explain.*definition|"
    r"how do you.*calculate|how do you.*measure|how do you.*determine|"
    r"what does.*mean|what is.*definition)\b"
)

INTENT_TREND_PATTERN = re.compile(
    r"\b(over time|over the last|history|trend|past \d+\s+(?:years?|quarters?)|"
    r"growth|increase|decline|decrease|change|progression|evolution|"
    r"performance over|results over|data over|development over|"
    r"improvement|deterioration|fluctuation|variation|"
    r"how has.*changed|how has.*evolved|how has.*performed|"
    r"how did.*change|how did.*evolve|how did.*perform|lately|recently)\b"
)

INTENT_LAST_PATTERN = re.compile(r"\blast\s+\d+\s+(quarters?|years?)\b")

INTENT_QUESTION_PATTERN = re.compile(r"^(what|how|which|why|when|where)")
INTENT_IMPERATIVE_PATTERN = re.compile(r"^(show|display|get|find|list|give me|provide)")

# IMPROVED REAL-WORLD USAGE PATTERNS
REAL_WORLD_LOOKUP_PATTERNS = [
    # High priority lookup patterns (should override explain)
    r"what's.*\w+.*revenue",
    r"what's.*\w+.*earnings", 
    r"what's.*\w+.*profit",
    r"what's.*\w+.*margin",
    r"what's.*\w+.*ratio",
    r"what's.*\w+.*bottom line",
    r"what's.*\w+.*arr",
    r"what's.*\w+.*cash",
    r"what's.*\w+.*debt",
    r"what's.*\w+.*equity",
    r"what's.*\w+.*valuation",
    r"what's.*\w+.*pe.*ratio",
    r"what's.*\w+.*p/e.*ratio",
    r"what's.*\w+.*p\.e.*ratio",
    r"what's.*\w+.*ev/sales",
    r"what's.*\w+.*dcf",
    r"what's.*\w+.*doing",
    r"what's.*\w+.*happening",
    r"what's.*\w+.*deal",
    r"how is.*\w+.*doing",
    r"how is.*\w+.*performing",
    r"how is.*\w+.*profitable",
    r"tell me about.*\w+",
    r"show me.*\w+.*numbers",
    r"show me.*\w+.*data",
    r"show me.*\w+.*dough",
    r"show me.*\w+.*cash",
    r"get me.*\w+.*earnings",
    r"get me.*\w+.*revenue",
    r"get me.*\w+.*data",
    r"get me.*\w+.*valuation",
    r"is.*\w+.*profitable",
    r"does.*\w+.*make money",
    r"are.*\w+.*margins.*good",
    r"are.*\w+.*margins.*bad",
    r"how much.*cash.*does.*\w+.*have",
    r"how much.*money.*does.*\w+.*make",
    # EXCEPTION: Performance without time context should be lookup
    r"what's.*\w+.*performance$",
    r"what's.*\w+.*performance\?"
]

REAL_WORLD_TREND_PATTERNS = [
    # Trend patterns with improved coverage
    r"performance.*lately",
    r"performance.*recently", 
    r"performance.*over time",
    r"performance.*trend",
    r"performance.*growth",
    r"performance.*change",
    r"performance.*evolution",
    r"performance.*progression",
    r"how has.*\w+.*performed",
    r"how has.*\w+.*changed",
    r"how has.*\w+.*evolved",
    r"how did.*\w+.*perform",
    r"how did.*\w+.*change",
    r"how did.*\w+.*evolve",
    r"what's.*\w+.*performance.*lately",
    r"what's.*\w+.*performance.*recently",
    r"what's.*\w+.*performance.*trend",
    r"what's.*\w+.*performance.*growth"
]

REAL_WORLD_RANK_PATTERNS = [
    # Rank patterns with improved coverage
    r"which.*stock.*best",
    r"which.*company.*fastest",
    r"which.*has.*best.*performance",
    r"which.*has.*fastest.*growth",
    r"which.*company.*has.*best.*pe.*ratio",
    r"which.*stock.*has.*best.*pe.*ratio",
    r"which.*company.*has.*best.*debt.*equity",
    r"which.*company.*has.*best.*roe",
    r"which.*stock.*has.*highest.*dividend",
    r"which.*tech.*company.*best.*margins",
    r"which.*company.*has.*best.*current.*ratio",
    r"which.*company.*has.*best.*gross.*margin",
    r"which.*company.*has.*best.*pe.*ratio",
    r"which.*company.*has.*best.*debt.*equity.*ratio",
    r"which.*company.*has.*best.*roe",
    r"which.*company.*has.*best.*current.*ratio",
    r"which.*company.*has.*best.*gross.*margin",
    r"which.*company.*has.*best.*pe.*ratio\?",
    r"which.*company.*has.*best.*pe.*ratio",
    r"which.*company.*has.*best.*p/e.*ratio",
    r"which.*company.*has.*best.*p\.e.*ratio",
    r"which.*company.*has.*best.*p/e.*ratio\?",
    r"which.*company.*has.*best.*p\.e.*ratio\?"
]

REAL_WORLD_EXPLAIN_PATTERNS = [
    # Explain patterns (lower priority)
    r"how do you.*calculate",
    r"how do you.*measure",
    r"how do you.*determine",
    r"explain.*and.*show.*trend",
    r"explain.*industry.*trends",
    r"what does.*mean",
    r"what is.*definition",
    r"define.*\w+"
]

# Trend keyword priority patterns
TREND_KEYWORDS = ["trend", "growth", "increase", "decline", "change", "progression", "evolution", "over time", "history", "lately", "recently"]

def normalize(text: str) -> str:
    """Return a lower-cased, whitespace-collapsed representation."""
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def parse_to_structured(text: str) -> Dict[str, Any]:
    """Parse text to structured format with improved real-world usage intent classification."""
    norm = normalize(text)
    lowered_full = unicodedata.normalize("NFKC", text).lower()

    ticker_matches, ticker_warnings = resolve_tickers_freeform(text)
    metric_matches = resolve_metrics(text, lowered_full)
    periods = parse_periods(norm, prefer_fiscal=False)  # Use calendar default

    intent = classify_intent_improved_real_world(norm, ticker_matches, metric_matches, periods)

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
        "vmetrics": [{"input": entry["input"], "metric_id": entry["metric_id"]} for entry in metric_matches],
        "periods": periods,
        "computed": infer_computed(metric_matches),
        "filters": {"currency": "USD", "unit_preference": "auto"},
        "free_text": text,
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


def classify_intent_improved_real_world(
    norm_text: str,
    tickers: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    periods: Dict[str, Any],
) -> str:
    """Improved real-world usage intent classification with better pattern matching."""

    unique_tickers = {entry["ticker"] for entry in tickers}
    period_type = periods.get("type")

    # Priority 1: Real-World Usage Lookup Patterns (highest priority)
    for pattern in REAL_WORLD_LOOKUP_PATTERNS:
        if re.search(pattern, norm_text):
            return "lookup"

    # Priority 2: Real-World Usage Trend Patterns
    for pattern in REAL_WORLD_TREND_PATTERNS:
        if re.search(pattern, norm_text):
            return "trend"

    # Priority 3: Real-World Usage Rank Patterns
    for pattern in REAL_WORLD_RANK_PATTERNS:
        if re.search(pattern, norm_text):
            return "rank"

    # Priority 4: Real-World Usage Explain Patterns (lower priority)
    for pattern in REAL_WORLD_EXPLAIN_PATTERNS:
        if re.search(pattern, norm_text):
            return "explain_metric"

    # Priority 5: Standard Intent Detection
    # Trend Intent Detection (comprehensive)
    if is_trend_intent_improved_real_world(norm_text, periods):
        return "trend"

    # Compare Intent Detection (but not for complex lookup phrases)
    if len(unique_tickers) >= 2 or INTENT_COMPARE_PATTERN.search(norm_text):
        return "compare"

    # Rank Intent Detection
    if INTENT_RANK_PATTERN.search(norm_text):
        return "rank"

    # Explain Intent Detection (but not if trend keywords present)
    if INTENT_EXPLAIN_PATTERN.search(norm_text) and not has_trend_keywords(norm_text):
        return "explain_metric"

    # Lookup Intent Detection (for specific phrases)
    if INTENT_IMPERATIVE_PATTERN.search(norm_text):
        return "lookup"

    # Context-Aware Classification
    intent = classify_intent_with_improved_real_world_context(norm_text, tickers, metrics, periods)
    if intent != "lookup":
        return intent

    return "lookup"


def is_trend_intent_improved_real_world(norm_text: str, periods: Dict[str, Any]) -> bool:
    """Improved real-world usage trend intent detection with comprehensive coverage."""
    
    # Check for trend keywords
    if has_trend_keywords(norm_text):
        return True
    
    # Check for quarter range patterns in text (most comprehensive)
    if re.search(r"Q\d+-Q\d+", norm_text):
        return True
    
    # Check for quarter range patterns with year
    if re.search(r"Q\d+-Q\d+\s+\d{4}", norm_text):
        return True
    
    # Check for year range patterns
    if re.search(r"\d{4}-\d{4}", norm_text):
        return True
    
    # Check for period type
    period_type = periods.get("type")
    if period_type in {"range", "multi", "relative"}:
        return True
    
    # Check for quarter range in periods items (most comprehensive)
    if periods and "items" in periods:
        for item in periods["items"]:
            if isinstance(item, dict):
                # Check for quarter range in period field
                if "period" in item and re.search(r"Q\d+-Q\d+", str(item["period"])):
                    return True
                # Check for quarter range in fq field (like Q1-Q4)
                if "fq" in item and item["fq"] and str(item["fq"]).count("-") > 0:
                    return True
    
    # Manual quarter range detection for specific patterns (case insensitive)
    quarter_range_patterns = [
        "q1-q4", "q2-q4", "q3-q4", "q1-q3", "q1-q2", "q2-q3"
    ]
    
    for pattern in quarter_range_patterns:
        if pattern in norm_text:
            return True
    
    return False


def has_trend_keywords(norm_text: str) -> bool:
    """Check if text contains trend keywords."""
    return any(keyword in norm_text for keyword in TREND_KEYWORDS)


def classify_intent_with_improved_real_world_context(
    norm_text: str,
    tickers: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    periods: Dict[str, Any],
) -> str:
    """Improved real-world usage context-aware intent classification for edge cases."""

    # Question pattern analysis with trend priority
    if INTENT_QUESTION_PATTERN.search(norm_text):
        if has_trend_keywords(norm_text):
            return "trend"
        elif any(word in norm_text for word in ["mean", "is", "definition", "define"]):
            return "explain_metric"
        elif any(word in norm_text for word in ["best", "highest", "lowest", "worst", "most", "least"]):
            return "rank"

    # Imperative pattern analysis
    if INTENT_IMPERATIVE_PATTERN.search(norm_text):
        return "lookup"

    # Complex phrase analysis with trend priority
    if any(phrase in norm_text for phrase in [
        "Can you show", "Please show", "Could you show"
    ]):
        if has_trend_keywords(norm_text):
            return "trend"
        return "lookup"

    # Multi-metric analysis
    if len(metrics) > 1:
        return "compare"

    # Ambiguous cases default to lookup
    return "lookup"


def classify_intent_confidence(
    norm_text: str,
    tickers: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    periods: Dict[str, Any],
) -> tuple[str, float]:
    """Classify intent with confidence scoring."""

    intent_scores = {
        "lookup": 0.0,
        "compare": 0.0,
        "rank": 0.0,
        "explain_metric": 0.0,
        "trend": 0.0
    }

    unique_tickers = {entry["ticker"] for entry in tickers}
    period_type = periods.get("type")

    # Real-world usage lookup scoring (highest priority)
    for pattern in REAL_WORLD_LOOKUP_PATTERNS:
        if re.search(pattern, norm_text):
            intent_scores["lookup"] += 1.0

    # Real-world usage trend scoring
    for pattern in REAL_WORLD_TREND_PATTERNS:
        if re.search(pattern, norm_text):
            intent_scores["trend"] += 0.9

    # Real-world usage rank scoring
    for pattern in REAL_WORLD_RANK_PATTERNS:
        if re.search(pattern, norm_text):
            intent_scores["rank"] += 0.9

    # Real-world usage explain scoring (lower priority)
    for pattern in REAL_WORLD_EXPLAIN_PATTERNS:
        if re.search(pattern, norm_text):
            intent_scores["explain_metric"] += 0.8

    # Standard intent scoring
    if is_trend_intent_improved_real_world(norm_text, periods):
        intent_scores["trend"] += 0.9
    if has_trend_keywords(norm_text):
        intent_scores["trend"] += 0.8
    if INTENT_TREND_PATTERN.search(norm_text):
        intent_scores["trend"] += 0.7
    if INTENT_LAST_PATTERN.search(norm_text):
        intent_scores["trend"] += 0.6

    # Compare intent scoring
    if len(unique_tickers) >= 2:
        intent_scores["compare"] += 0.9
    if INTENT_COMPARE_PATTERN.search(norm_text):
        intent_scores["compare"] += 0.8

    # Rank intent scoring
    if INTENT_RANK_PATTERN.search(norm_text):
        intent_scores["rank"] += 0.8

    # Explain intent scoring (but not if trend keywords present)
    if INTENT_EXPLAIN_PATTERN.search(norm_text) and not has_trend_keywords(norm_text):
        intent_scores["explain_metric"] += 0.8

    # Lookup intent scoring
    if INTENT_IMPERATIVE_PATTERN.search(norm_text):
        intent_scores["lookup"] += 0.7

    # Context scoring
    if INTENT_QUESTION_PATTERN.search(norm_text):
        if has_trend_keywords(norm_text):
            intent_scores["trend"] += 0.3
        elif any(word in norm_text for word in ["mean", "is", "definition"]):
            intent_scores["explain_metric"] += 0.3
        elif any(word in norm_text for word in ["best", "highest", "lowest"]):
            intent_scores["rank"] += 0.3

    # Default lookup scoring
    if max(intent_scores.values()) == 0.0:
        intent_scores["lookup"] = 1.0

    # Return intent with highest score
    best_intent = max(intent_scores.items(), key=lambda x: x[1])
    return best_intent[0], best_intent[1]


def infer_computed(metrics: List[Dict[str, Any]]) -> List[str]:
    """Placeholder for future computed metrics inference."""
    return []


# Backward compatibility
def classify_intent(
    norm_text: str,
    tickers: List[Dict[str, Any]],
    metrics: List[Dict[str, Any]],
    periods: Dict[str, Any],
) -> str:
    """Backward compatibility wrapper for original classify_intent function."""
    return classify_intent_improved_real_world(norm_text, tickers, metrics, periods)


__all__ = ["parse_to_structured", "normalize", "resolve_metrics", "classify_intent_improved_real_world", "classify_intent_confidence"]
