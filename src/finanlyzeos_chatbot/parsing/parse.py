"""Natural-language parsing utilities for the FinanlyzeOS chatbot."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from .alias_builder import resolve_tickers_freeform
from .ontology import METRIC_SYNONYMS
from .time_grammar import parse_periods

_METRIC_ITEMS = sorted(METRIC_SYNONYMS.items(), key=lambda item: -len(item[0]))

INTENT_COMPARE_PATTERN = re.compile(
    r"\b(compare|vs|versus|v\.?s\.?|compared\s+to|compared\s+with|"
    r"comparison|contrast|difference\s+between|similarity\s+between|"
    r"versus|against|relative\s+to|in\s+comparison|"
    r"better\s+than|worse\s+than|higher\s+than|lower\s+than|"
    r"more\s+than|less\s+than|stronger\s+than|weaker\s+than|"
    r"times\s+more|times\s+less|X\s+times|twice|double|triple|"
    r"X%|percent|percentage\s+higher|percent\s+lower|"
    r"relative\s+performance|side\s+by\s+side|head\s+to\s+head)\b",
    re.IGNORECASE
)
INTENT_TREND_PATTERN = re.compile(
    r"(over\s+time|over\s+the\s+last|over\s+the\s+past|history|historical|"
    r"trend|trends|trending|trajectory|direction|path|course|"
    r"past\s+\d+\s+(?:years?|quarters?|months?)|"
    r"last\s+\d+\s+(?:years?|quarters?|months?)|"
    r"recent|recently|evolution|development|progression|"
    r"how\s+has|how\s+have|how\s+did|how\s+does|"
    r"changed\s+over|improved\s+over|declined\s+over|"
    r"grown\s+over|shrunk\s+over|evolved\s+over|"
    r"time\s+series|time\s+frame|period\s+over|"
    r"year\s+over\s+year|yoy|quarter\s+over\s+quarter|qoq)\b"
)
INTENT_LAST_PATTERN = re.compile(
    r"\b(last|past|previous|recent|recently|lately)\s+\d+\s+(quarters?|years?|months?|periods?)\b"
)
INTENT_RANK_PATTERN = re.compile(
    r"\b(which|who|what|highest|lowest|top|bottom|best|worst|most|least|"
    r"fastest|slowest|strongest|weakest|largest|smallest|"
    r"rank|ranking|ranked|ranks|"
    r"best\s+performing|worst\s+performing|top\s+performing|"
    r"which.*has.*best|which.*has.*worst|which.*has.*highest|which.*has.*lowest|"
    r"which.*company.*has|which.*stock.*has|which.*firm.*has|"
    r"which.*is.*best|which.*is.*worst|which.*is.*highest|which.*is.*lowest|"
    r"top\s+\d+|bottom\s+\d+|best\s+\d+|worst\s+\d+|"
    r"leading|trailing|ahead|behind|outperforming|underperforming|"
    r"number\s+one|#1|first\s+place|last\s+place)\b"
)
INTENT_EXPLAIN_PATTERN = re.compile(
    r"\b(define|explain|tell\s+me\s+about|describe|break\s+down|"
    r"clarify|elaborate|detail|expand|"
    r"how\s+(?:do|does|is|to|can|should|would).*(?:compute|calculate|calculated|work|mean|function|operate)|"
    r"what\s+does.*mean|what.*mean|explain.*mean|"
    r"definition\s+of|meaning\s+of|explanation\s+of|"
    r"what\s+is|what\s+are|what\s+was|what\s+were|"
    r"tell\s+me\s+what|help\s+me\s+understand|"
    r"can\s+you\s+explain|could\s+you\s+explain|"
    r"i\s+don\'t\s+understand|i\s+need\s+to\s+understand|"
    r"walk\s+me\s+through|break\s+it\s+down|"
    r"in\s+simple\s+terms|in\s+layman\'s\s+terms)\b"
)

# New intent patterns for expanded query types
INTENT_WHY_PATTERN = re.compile(
    r"\b(why|what\s+caused|what\s+led\s+to|what\'s\s+driving|what\'s\s+behind|"
    r"reason\s+for|explanation\s+for|why\s+did|why\s+is|why\s+are|why\s+was|why\s+were|"
    r"what\'s\s+the\s+reason|what\s+caused|what\s+factors|what\s+drives|"
    r"what\s+led|what\s+triggered|what\s+contributed\s+to|"
    r"how\s+come|why\s+so|why\s+does|why\s+do)\b"
)

INTENT_WHATIF_PATTERN = re.compile(
    r"\b(what\s+if|what\s+would|what\s+happens\s+if|if.*then|"
    r"scenario|assume|suppose|imagine|project|forecast|predict|"
    r"what\s+would\s+happen|what\s+might\s+happen|"
    r"hypothetical|projection|outlook|what\s+about|"
    r"supposing|assuming|given\s+that|if.*what)\b"
)

INTENT_RELATIONSHIP_PATTERN = re.compile(
    r"\b(relationship|correlation|connection|link|"
    r"how.*relate|how.*connect|how.*link|"
    r"does.*affect|does.*impact|does.*influence|"
    r"related\s+to|connected\s+to|linked\s+to|"
    r"how\s+does.*affect|how\s+does.*impact|how\s+does.*influence|"
    r"what\'s\s+the\s+relationship|what\'s\s+the\s+connection|"
    r"correlate|covariance|dependence)\b"
)

INTENT_BENCHMARK_PATTERN = re.compile(
    r"\b(benchmark|vs\s+industry|vs\s+sector|vs\s+peers|"
    r"compared\s+to\s+industry|compared\s+to\s+sector|compared\s+to\s+peers|"
    r"relative\s+to\s+industry|relative\s+to\s+sector|relative\s+to\s+peers|"
    r"industry\s+average|sector\s+average|peer\s+group|peer\s+average|"
    r"how\s+does.*compare\s+to\s+industry|how\s+does.*compare\s+to\s+sector|"
    r"where\s+does.*rank\s+in|rank\s+among|compared\s+to\s+market)\b"
)

INTENT_WHEN_PATTERN = re.compile(
    r"\b(when|what\s+year|what\s+quarter|in\s+which|"
    r"first\s+time|last\s+time|since\s+when|until\s+when|"
    r"what\s+period|which\s+year|which\s+quarter|"
    r"when\s+did|when\s+was|when\s+were|when\s+is|when\s+are|"
    r"at\s+what\s+time|during\s+what|what\s+date)\b"
)

INTENT_CONDITIONAL_PATTERN = re.compile(
    r"\b(if.*then|if.*what|what.*if|"
    r"assuming|supposing|given\s+that|"
    r"conditional|hypothetical|"
    r"in\s+case|should\s+.*\s+happen|would\s+.*\s+if)\b"
)

INTENT_SUMMARY_PATTERN = re.compile(
    r"\b(summary|overview|summary\s+of|key\s+points|"
    r"main\s+highlights|top|bottom|total|aggregate|"
    r"sum\s+of|average\s+of|combined|"
    r"give\s+me\s+a\s+summary|provide\s+a\s+summary|"
    r"what\'s\s+the\s+summary|overall|in\s+summary)\b"
)

INTENT_CHANGE_PATTERN = re.compile(
    r"\b(change|delta|difference|increase|decrease|"
    r"growth|decline|improvement|deterioration|"
    r"how\s+much.*change|how\s+much.*increase|how\s+much.*decrease|"
    r"what\'s\s+the\s+change|what\'s\s+the\s+difference|"
    r"change\s+from|change\s+to|changed\s+by|"
    r"improved|worsened|gained|lost|shift)\b"
)

INTENT_AGGREGATION_PATTERN = re.compile(
    r"\b(sum|total|aggregate|combined|collective|cumulative|grand\s+total|"
    r"sum\s+of|total\s+of|aggregate\s+of|combined\s+of|collective\s+of|cumulative\s+of|"
    r"calculate\s+the\s+sum|calculate\s+the\s+total|compute\s+the\s+sum|compute\s+the\s+total|"
    r"what\'s\s+the\s+sum|what\'s\s+the\s+total|what\'s\s+the\s+aggregate|what\'s\s+the\s+combined|"
    r"how\s+much\s+in\s+total|how\s+much\s+altogether|how\s+much\s+combined|"
    r"add\s+up|sum\s+up|total\s+up|combine|aggregate|"
    r"all\s+together|everything\s+combined|altogether|"
    r"sum\s+all|total\s+all|add\s+all|aggregate\s+all|combined\s+value|combined\s+amount)\b"
)

# NEW: Recommendation/Advice intent patterns
INTENT_RECOMMENDATION_PATTERN = re.compile(
    r"\b(should\s+i|should\s+we|should\s+you|should\s+they|"
    r"would\s+you\s+recommend|do\s+you\s+recommend|can\s+you\s+recommend|"
    r"what\s+do\s+you\s+recommend|what\s+would\s+you\s+recommend|"
    r"should\s+i\s+buy|should\s+i\s+sell|should\s+i\s+invest|should\s+i\s+hold|"
    r"is\s+it\s+a\s+good\s+investment|is\s+it\s+worth\s+investing|"
    r"would\s+you\s+advise|do\s+you\s+advise|what\s+is\s+your\s+advice|"
    r"what\s+is\s+your\s+recommendation|what\s+is\s+your\s+suggestion|"
    r"should\s+i\s+be\s+concerned|should\s+i\s+worry|"
    r"is\s+this\s+a\s+buy|is\s+this\s+a\s+sell|is\s+this\s+a\s+hold|"
    r"what\'s\s+your\s+take|what\'s\s+your\s+opinion|what\'s\s+your\s+view)\b"
)

# NEW: Risk analysis intent patterns
INTENT_RISK_PATTERN = re.compile(
    r"\b(risk|risks|risky|risk\s+analysis|risk\s+assessment|risk\s+profile|"
    r"what\s+are\s+the\s+risks|what\s+is\s+the\s+risk|how\s+risky|"
    r"volatility|volatile|volatility\s+analysis|"
    r"downside\s+risk|upside\s+potential|risk\s+reward|"
    r"how\s+safe|how\s+secure|is\s+it\s+safe|is\s+it\s+risky|"
    r"what\s+could\s+go\s+wrong|what\s+are\s+the\s+dangers|"  # More specific than forecast "what could"
    r"exposure|risk\s+exposure|risk\s+factors|risk\s+drivers|"
    r"beta|correlation\s+risk|concentration\s+risk|"
    r"credit\s+risk|market\s+risk|liquidity\s+risk|operational\s+risk)\b"
)

# NEW: Optimization intent patterns
INTENT_OPTIMIZATION_PATTERN = re.compile(
    r"\b(optimize|optimization|optimal|best\s+way|best\s+approach|"
    r"how\s+to\s+optimize|how\s+to\s+improve|how\s+to\s+maximize|how\s+to\s+minimize|"
    r"maximize|minimize|improve\s+performance|enhance|"
    r"what\'s\s+the\s+best\s+strategy|what\'s\s+the\s+optimal|"
    r"how\s+can\s+i\s+improve|how\s+can\s+we\s+improve|"
    r"efficiency|efficient|inefficient|"
    r"rebalance|rebalancing|portfolio\s+optimization|"
    r"asset\s+allocation|optimal\s+allocation|best\s+allocation)\b"
)

# NEW: Valuation intent patterns
INTENT_VALUATION_PATTERN = re.compile(
    r"\b(valuation|value|valued|worth|pricing|price|"
    r"is\s+it\s+overvalued|is\s+it\s+undervalued|is\s+it\s+fairly\s+valued|"
    r"is\s+\w+\s+overvalued|is\s+\w+\s+undervalued|is\s+\w+\s+fairly\s+valued|"  # "is apple overvalued"
    r"what\'s\s+it\s+worth|what\'s\s+the\s+value|how\s+much\s+is\s+it\s+worth|"
    r"fair\s+value|intrinsic\s+value|book\s+value|market\s+value|"
    r"P\s*[/\-]\s*E|P\s*[/\-]\s*E\s+ratio|P\s*[/\-]\s*E\s+of|P\s*[/\-]\s*E\s+of\s+\w+|"  # More flexible P/E matching - CHECK FIRST
    r"P/E|P\/E|P\/E\s+ratio|P\/E\s+of|P\/E\s+of\s+\w+|price\s+to\s+earnings|P/B|P\/B|P\/B\s+ratio|price\s+to\s+book|"  # Allow P/E and P/B with ratio and "of"
    r"EV/EBITDA|EV\/EBITDA|enterprise\s+value|"
    r"expensive|cheap|reasonably\s+priced|"
    r"valuation\s+metrics|valuation\s+analysis|DCF|DCF\s+analysis|discounted\s+cash\s+flow)\b",
    re.IGNORECASE
)

# NEW: Performance attribution intent patterns
INTENT_ATTRIBUTION_PATTERN = re.compile(
    r"\b(attribution|performance\s+attribution|what\s+drove|what\s+contributed|"
    r"what\s+led\s+to|what\s+caused\s+the|what\s+explains|"
    r"breakdown\s+of|decomposition|factor\s+analysis|"
    r"drivers|driving\s+factors|contributing\s+factors|"
    r"why\s+did\s+it\s+perform|why\s+did\s+it\s+underperform|why\s+did\s+it\s+outperform|"
    r"what\s+factors|which\s+factors|key\s+drivers|main\s+drivers)\b"
)

# NEW: Forecasting/Prediction intent patterns (more comprehensive)
INTENT_FORECAST_PATTERN = re.compile(
    r"\b(forecast|forecasting|predict|prediction|predicting|"
    r"project|projection|projecting|projected|estimate|estimation|estimating|"  # Added "projected"
    r"outlook|future|forward\s+looking|forward\s+projection|"
    r"what\s+will|what\s+would|what\s+might|what\s+could\s+(?:happen|be|occur|change)|"  # More specific to avoid matching "what could go wrong"
    r"how\s+will|how\s+would|how\s+might|how\s+could|"
    r"expected|expectation|expectations|"
    r"guidance|guidance\s+for|guidance\s+on|"
    r"next\s+year|next\s+quarter|upcoming|coming\s+year|coming\s+quarter|"
    r"future\s+performance|future\s+growth|future\s+earnings|"
    r"scenario\s+analysis|sensitivity\s+analysis|"
    r"what\s+if\s+analysis|model|modeling)\b"
)

# NEW: Efficiency/Productivity intent patterns
INTENT_EFFICIENCY_PATTERN = re.compile(
    r"\b(efficiency|efficient|inefficient|productivity|productive|"
    r"how\s+efficient|how\s+productive|"
    r"what\'s\s+the\s+ROE\b|what\'s\s+the\s+ROA\b|what\'s\s+the\s+ROIC\b|whats\s+the\s+ROE\b|whats\s+the\s+ROA\b|whats\s+the\s+ROIC\b|"  # "what's the ROE" (with and without apostrophe)
    r"ROE|ROE\s+analysis|return\s+on\s+equity|"  # Added "ROE analysis"
    r"ROA|ROA\s+analysis|return\s+on\s+assets|ROIC|ROIC\s+analysis|return\s+on\s+invested\s+capital|"  # Added "ROA analysis" and "ROIC analysis"
    r"asset\s+turnover|capital\s+efficiency|operational\s+efficiency|"
    r"utilization|utilization\s+rate|capacity\s+utilization|"
    r"productivity\s+metrics|efficiency\s+metrics|efficiency\s+ratio)\b",
    re.IGNORECASE
)


def normalize(text: str) -> str:
    """Return a lower-cased, whitespace-collapsed representation.
    
    For multi-line queries, intelligently preserves structure:
    - Joins lines with spaces (removes excessive newlines)
    - Preserves list markers (bullets, numbers) as context
    - Collapses multiple spaces but keeps query structure
    """
    if not text:
        return ""
    
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    
    # Handle multi-line queries intelligently
    # Split into lines and process each
    lines = normalized.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Preserve list markers (bullets, numbers) as context
        # This helps with structured queries like:
        # "Analyze:
        #  - Apple's revenue
        #  - Microsoft's margins"
        if re.match(r'^[\-\*\+]\s+', line) or re.match(r'^\d+[\.\)]\s+', line):
            # It's a list item - keep it as is (will be joined with space)
            processed_lines.append(line)
        else:
            # Regular line - collapse internal whitespace
            line = re.sub(r'\s+', ' ', line)
            processed_lines.append(line)
    
    # Join lines with single space (removes newlines but preserves structure)
    normalized = ' '.join(processed_lines)
    
    # Final cleanup: collapse any remaining excessive whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def parse_to_structured(text: str) -> Dict[str, Any]:
    norm = normalize(text)
    lowered_full = unicodedata.normalize("NFKC", text).lower()

    # Check for forecasting keywords BEFORE ticker resolution to prevent false positives
    # Forecasting queries need special handling - don't use default ticker fallback
    forecasting_keywords = [
        r'\bforecast\b', r'\bpredict\b', r'\bestimate\b', r'\bprojection\b',
        r'\bproject\b', r'\boutlook\b', r'\bfuture\b',
        r'\bnext\s+\d+\s+years?\b', r'\bupcoming\s+years?\b',
    ]
    is_forecasting_query = any(re.search(pattern, lowered_full, re.IGNORECASE) for pattern in forecasting_keywords)
    
    # Check for portfolio keywords BEFORE ticker resolution to prevent false positives
    # Portfolio keywords take priority over ticker resolution
    # This prevents false positives like "What's my portfolio risk?" -> CPB, VRSK
    portfolio_keywords = [
        # Basic portfolio keywords
        r'\bportfolio\b', r'\bmy portfolio\b', r'\bthe portfolio\b', r'\bthis portfolio\b',
        r'\bholdings\b', r'\bexposure\b', r'\bport_\w+\b',
        # Portfolio + attribute combinations (catch these even if words are separated)
        r'\bportfolio\s+\w+\s+risk\b', r'\bportfolio\s+risk\b', r'\bmy\s+portfolio\s+risk\b',
        r'\bportfolio\s+\w+\s+cvar\b', r'\bportfolio\s+cvar\b', r'\bmy\s+portfolio\s+cvar\b',
        r'\bportfolio\s+\w+\s+volatility\b', r'\bportfolio\s+volatility\b',
        r'\bportfolio\s+\w+\s+diversification\b', r'\bportfolio\s+diversification\b',
        r'\bportfolio\s+\w+\s+exposure\b', r'\bportfolio\s+exposure\b',
        r'\bportfolio\s+\w+\s+performance\b', r'\bportfolio\s+performance\b',
        r'\bportfolio\s+\w+\s+allocation\b', r'\bportfolio\s+allocation\b',
        r'\bportfolio\s+\w+\s+optimization\b', r'\bportfolio\s+optimization\b',
        r'\bportfolio\s+\w+\s+attribution\b', r'\bportfolio\s+attribution\b',
        r'\bportfolio\s+rebalancing\b', r'\bportfolio\s+rebalance\b',
        # Question patterns with portfolio (catch "what's my portfolio", "show my portfolio", etc.)
        # CRITICAL: Catch question words BEFORE individual word resolution
        r'\b(?:what\'?s?|what\s+is|what\'s|whats|show|analyze|calculate|get|display|tell\s+me)\s+(?:my\s+)?portfolio\b',
        r'\b(?:what\'?s?|what\s+is|what\'s|whats|show|analyze|calculate|get|display)\s+(?:my\s+)?(?:portfolio\s+)?(?:risk|cvar|cva?r|volatility|exposure|performance|allocation|diversification|sharpe|sortino|alpha|beta|tracking\s+error)\b',
        # Risk/other attributes with portfolio context (catch "CVAR for this portfolio", "CVaR of portfolio", etc.)
        r'\b(?:my\s+)?portfolio\s+(?:risk|cvar|cva?r|volatility|exposure|performance|allocation|diversification|optimization|attribution|sharpe|sortino|alpha|beta|tracking\s+error)\b',
        r'\b(?:risk|cvar|cva?r|volatility|exposure|performance|allocation|diversification|sharpe|sortino|alpha|beta|tracking\s+error)\s+(?:of|for|in)\s+(?:my\s+|the\s+|this\s+)?portfolio\b',
        # Catch "CVAR" or "CVaR" when portfolio context is present (prevents false match to AES)
        r'\b(?:what\s+is|what\'?s?|what\'s|whats|calculate|show|get)\s+(?:the\s+)?(?:cvar|cva?r)\s+(?:for|of|in)\s+(?:my\s+|the\s+|this\s+)?portfolio\b',
        r'\b(?:cvar|cva?r)\s+(?:for|of|in)\s+(?:my\s+|the\s+|this\s+)?portfolio\b',
        # Catch question words followed by portfolio keywords (e.g., "What's my portfolio Sharpe ratio?")
        r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+(?:my\s+)?portfolio\s+(?:sharpe|sortino|alpha|beta|tracking\s+error|ratio)\b',
        r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+(?:the\s+)?(?:sharpe|sortino|alpha|beta|tracking\s+error|ratio)\s+(?:for|of|in)\s+(?:my\s+|the\s+|this\s+)?portfolio\b',
    ]
    
    is_portfolio_query = any(re.search(pattern, lowered_full, re.IGNORECASE) for pattern in portfolio_keywords)
    
    # Skip ticker resolution if portfolio keywords are detected to prevent false positives
    # (e.g., "portfolio risk" shouldn't match VRSK, "portfolio CVaR" shouldn't match CPB)
    if is_portfolio_query:
        ticker_matches = []
        ticker_warnings = []
    else:
        ticker_matches, ticker_warnings = resolve_tickers_freeform(text)
    
    # For forecasting queries, don't use default ticker fallback (AAPL)
    # Let specialized extraction in context_builder handle forecasting queries
    if is_forecasting_query and not ticker_matches:
        # Don't add default ticker - let forecasting context builder handle extraction
        # This prevents false matches and allows specialized forecasting extraction
        pass
    
    metric_matches = resolve_metrics(text, lowered_full)
    periods = parse_periods(norm, prefer_fiscal=False)

    # Ensure ticker_matches and metric_matches are lists (not None)
    if ticker_matches is None:
        ticker_matches = []
    if metric_matches is None:
        metric_matches = []
    if periods is None:
        periods = {}
    
    # Ensure they're lists of dicts
    if not isinstance(ticker_matches, list):
        ticker_matches = []
    if not isinstance(metric_matches, list):
        metric_matches = []

    intent = classify_intent(norm, ticker_matches, metric_matches, periods)

    warnings = list(periods.get("warnings", [])) + ticker_warnings
    suggestion_ticker = None
    suggestion_source = None
    for warn in ticker_warnings:
        if warn.startswith("suggested_ticker:"):
            parts = warn.split(":", 2)
            if len(parts) >= 2:
                suggestion_ticker = parts[1]
                if len(parts) == 3:
                    suggestion_source = parts[2]
            break
    if not ticker_matches:
        if suggestion_ticker:
            ticker_matches = [
                {"input": suggestion_source or suggestion_ticker, "ticker": suggestion_ticker}
            ]
            warnings.append(f"autocorrect_ticker:{suggestion_source or suggestion_ticker}->{suggestion_ticker}")
        else:
            warnings.append("missing_ticker")
            # For forecasting queries, don't use default ticker fallback
            # Let specialized extraction in context_builder handle it
            if not is_forecasting_query:
                ticker_matches = [{"input": "AAPL", "ticker": "AAPL"}]
                warnings.append("default_ticker:AAPL")
    if not metric_matches:
        warnings.append("missing_metric")

    # Safely build tickers list - filter out None entries
    tickers_list = []
    for entry in ticker_matches:
        if entry is None:
            continue
        if not isinstance(entry, dict):
            continue
        input_val = entry.get("input")
        ticker_val = entry.get("ticker")
        if input_val is not None and ticker_val is not None:
            tickers_list.append({"input": input_val, "ticker": ticker_val})
    
    # Safely build metrics list - filter out None entries
    metrics_list = []
    for entry in metric_matches:
        if entry is None:
            continue
        if not isinstance(entry, dict):
            continue
        input_val = entry.get("input")
        metric_id = entry.get("metric_id")
        if input_val is not None and metric_id is not None:
            metrics_list.append({"input": input_val, "key": metric_id})
    
    structured = {
        "intent": intent,
        "tickers": tickers_list,
        "vmetrics": metrics_list,
        "periods": periods or {},
        "computed": infer_computed(metric_matches) if metric_matches else [],
        "filters": {"currency": "USD", "unit_preference": "auto"},
        "free_text": text,
        "norm_text": norm,  # Fix: Add norm_text field
        "warnings": warnings or [],
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

    # Safely extract unique tickers
    unique_tickers = set()
    if tickers and isinstance(tickers, list):
        for entry in tickers:
            if entry is None:
                continue
            if not isinstance(entry, dict):
                continue
            ticker = entry.get("ticker")
            if ticker and isinstance(ticker, str):
                unique_tickers.add(ticker)
    
    period_type = None
    if periods and isinstance(periods, dict):
        period_type = periods.get("type")

    # Priority order: forecast > what-if > recommendation > risk > valuation > attribution > 
    #                 why > when > relationship > benchmark > optimization > efficiency > 
    #                 summary > conditional > rank > explain > trend > compare > change > lookup
    
    # Check for forecast/prediction intent (highest priority - very specific)
    if INTENT_FORECAST_PATTERN.search(norm_text):
        return "forecast"
    
    # Check for what-if/scenario intent (very high priority - very specific)
    if INTENT_WHATIF_PATTERN.search(norm_text):
        return "scenario_analysis"
    
    # Check for recommendation/advice intent (high priority - actionable queries)
    if INTENT_RECOMMENDATION_PATTERN.search(norm_text):
        return "recommendation"
    
    # Check for risk analysis intent (high priority - specific risk queries)
    if INTENT_RISK_PATTERN.search(norm_text):
        return "risk_analysis"
    
    # Check for valuation intent (high priority - specific valuation queries)
    if INTENT_VALUATION_PATTERN.search(norm_text):
        return "valuation"
    
    # Check for performance attribution intent (high priority - specific attribution queries)
    if INTENT_ATTRIBUTION_PATTERN.search(norm_text):
        return "attribution"

    # Check for why/causal intent (high priority - specific reasoning queries)
    if INTENT_WHY_PATTERN.search(norm_text):
        return "causal_analysis"

    # Check for when/temporal intent (high priority - specific time queries)
    if INTENT_WHEN_PATTERN.search(norm_text):
        return "temporal_query"

    # Check for relationship/correlation intent (medium-high priority)
    if INTENT_RELATIONSHIP_PATTERN.search(norm_text):
        return "relationship_analysis"

    # Check for benchmark intent (medium priority - similar to compare but more specific)
    if INTENT_BENCHMARK_PATTERN.search(norm_text):
        return "benchmark_analysis"
    
    # Check for efficiency intent (medium priority - efficiency queries)
    # Check BEFORE optimization and rank since "how efficient" might match optimization
    # and "what's the ROE" might match rank
    if INTENT_EFFICIENCY_PATTERN.search(norm_text):
        return "efficiency"
    
    # Check for optimization intent (medium priority - optimization queries)
    if INTENT_OPTIMIZATION_PATTERN.search(norm_text):
        return "optimization"

    # Check for aggregation intent FIRST (higher priority than summary - more specific)
    # This must come before summary since "sum", "total", "combined" might match summary pattern
    if INTENT_AGGREGATION_PATTERN.search(norm_text):
        return "aggregation"

    # Check for summary intent (medium priority)
    if INTENT_SUMMARY_PATTERN.search(norm_text):
        return "summary"

    # Check for conditional intent (medium priority)
    if INTENT_CONDITIONAL_PATTERN.search(norm_text):
        return "conditional_analysis"

    # Check for rank intent (medium priority for ranking questions)
    # Check AFTER efficiency to avoid matching "what's the ROE" as rank
    if INTENT_RANK_PATTERN.search(norm_text):
        # Skip rank if it's actually an efficiency query (e.g., "what's the ROE")
        if re.search(r"what['\s]s\s+the\s+(ROE|ROA|ROIC)\b", norm_text, re.IGNORECASE):
            return "efficiency"
        # For ranking queries, only parse tickers if explicitly mentioned
        if tickers and isinstance(tickers, list) and unique_tickers:
            norm_upper = norm_text.upper()
            if not any(ticker in norm_upper for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]):
                # Likely over-parsing, return rank without ticker dependency
                pass
        return "rank"

    # Check for explain intent (medium priority)
    if INTENT_EXPLAIN_PATTERN.search(norm_text):
        # For explain queries, only parse tickers if explicitly mentioned
        if tickers and isinstance(tickers, list) and unique_tickers:
            norm_upper = norm_text.upper()
            if not any(ticker in norm_upper for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]):
                # Likely over-parsing, return explain without ticker dependency
                pass
        return "explain_metric"

    # Check for trend intent (medium-low priority)
    if (
        INTENT_TREND_PATTERN.search(norm_text)
        or INTENT_LAST_PATTERN.search(norm_text)
        or period_type in {"range", "multi", "relative"}
        or re.search(r"Q\d+-Q\d+", norm_text)  # Quarter range pattern
    ):
        return "trend"

    # Check for compare intent (medium-low priority)
    # Only classify as compare if explicitly compare keywords OR multiple tickers with clear compare context
    if (INTENT_COMPARE_PATTERN.search(norm_text) or 
        (unique_tickers and len(unique_tickers) >= 2 and ("compare" in norm_text or "vs" in norm_text or "versus" in norm_text))):
        return "compare"

    # Check for change/delta intent (low priority - could overlap with trend, so check after)
    if INTENT_CHANGE_PATTERN.search(norm_text):
        return "change_analysis"

    # Default to lookup intent
    return "lookup"


def infer_computed(metrics: List[Dict[str, Any]]) -> List[str]:
    """Placeholder for future computed metrics inference."""
    return []


__all__ = ["parse_to_structured", "normalize", "resolve_metrics"]
