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
_UNIVERSE_SP1500_PATH = Path(__file__).resolve().parents[3] / "data" / "tickers" / "universe_sp1500.txt"
_TICKER_NAMES_PATH = Path(__file__).resolve().parents[3] / "docs" / "guides" / "ticker_names.md"

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
    # Common failing company names
    "enact": "ACT",
    "enact holdings": "ACT",
    "adtran": "ADTN",
    "adtran holdings": "ADTN",
    "aspen insurance": "AHL",
    "aspen": "AHL",
    "alpha metallurgical": "AMR",
    "amentum": "AMTM",
    "alpha omega semiconductor": "AOSL",
    "bread financial": "BFH",
    "bread": "BFH",
    "bill": "BILL",
    "bj wholesale": "BJ",
    "bj's wholesale": "BJ",
    "booking": "BKNG",
    "booking holdings": "BKNG",
    "bookng": "BKNG",  # Common misspelling
    "bookng holdings": "BKNG",
    "bookng holdings inc": "BKNG",  # With suffix
    "bookng holdings incorporated": "BKNG",
    "crown": "CCK",
    "crown holdings": "CCK",
    "celsius": "CELH",
    "celsius holdings": "CELH",
    "cf industries": "CF",
    "cinemark": "CNK",
    "concentra": "CON",
    "cooper standard": "CPS",
    "cooper-standard": "CPS",
    "csc collective": "CSC",
    "lionheart": "CUB",
    "digital ocean": "DOCN",
    "digitalocean": "DOCN",
    "double verify": "DV",
    "doubleverify": "DV",
    "energizer": "ENR",
    "equitable": "EQH",
    "exl service": "EXLS",
    "exlservice": "EXLS",
    "national vision": "EYE",
    "first cash": "FCFS",
    "firstcash": "FCFS",
    "floor decor": "FND",
    "floor & decor": "FND",
    "fortrea": "FTRE",
    "grid dynamics": "GDYN",
    "generac": "GNRC",
    "acushnet": "GOLF",
    "hayward": "HAYW",
    "hilton worldwide": "HLT",
    "hilton": "HLT",
    "harmony biosciences": "HRMY",
    "hilltop": "HTH",
    "hertz": "HTZ",
    "hertz global": "HTZ",
    "james river": "JRVR",
    "kyndryl": "KD",
    "kinetik": "KNTK",
    "knight swift": "KNX",
    "kennedy wilson": "KW",
    "leidos": "LDOS",
    "labcorp": "LH",
    "lantheus": "LNTH",
    "el pollo loco": "LOCO",
    "lamb weston": "LW",
    "mara": "MARA",
    "mativ": "MATV",
    "medpace": "MEDP",
    "marketaxess": "MKTX",
    "norwegian cruise line": "NCLH",
    "norwegian cruise": "NCLH",
    "neptune insurance": "NP",
    "neptune": "NP",
    "envista": "NVST",
    "organogenesis": "ORGO",
    "paymentus": "PAY",
    "performance food": "PFGC",
    "palomar": "PLMR",
    "prog": "PRG",
    "paypal": "PYPL",
    "liveramp": "RAMP",
    "live ramp": "RAMP",
    "remax": "RMAX",
    "re max": "RMAX",
    "ryan specialty": "RYAN",
    "ryan": "RYAN",
    "sally beauty": "SBH",
    "sally": "SBH",
    "sun country": "SNCY",
    "sun": "SNCY",
    "spok": "SPOK",
    "seagate": "STX",
    "seagate technology": "STX",
    "southwest gas": "SWX",
    "thryv": "THRY",
    "tko": "TKO",
    "tko group": "TKO",
    "ttec": "TTEC",
    "united airlines": "UAL",
    "united": "UAL",
    "universal insurance": "UVE",
    "universal": "UVE",
    "veritex": "VBTX",
    "victory capital": "VCTR",
    "victory": "VCTR",
    "willscot": "WSC",
    "will scot": "WSC",
    "xerox": "XRX",
    "zimmer biomet": "ZBH",
    "zimmer": "ZBH",
    # Common misspellings
    "tesla": "TSLA",
    "tesl": "TSLA",  # Common misspelling
    "nvida": "NVDA",  # Common misspelling
    "nvidia": "NVDA",
    "appel": "AAPL",  # Common misspelling (Apple)
    "appl": "AAPL",  # Another common misspelling
}

_TICKER_PATTERN = re.compile(r"\b([A-Za-z]{1,5})(?:\.[A-Za-z]{1,2})?\b")

_ALIAS_CACHE: Optional[Dict[str, Set[str]]] = None
_ALIAS_LOOKUP: Optional[Dict[str, List[str]]] = None
_TICKER_SET: Optional[Set[str]] = None


def _base_tokens(text: str) -> List[str]:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.lower()
    # Handle possessive forms - convert "company's" to "company" before removing punctuation
    # This helps with queries like "Microsft's revenue" -> "microsft revenue"
    normalized = re.sub(r"'s\b", " ", normalized)  # Remove possessive 's
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
    """Load ticker universe - prefers S&P 1500 if available, falls back to S&P 500."""
    # Try S&P 1500 first (if file exists)
    if _UNIVERSE_SP1500_PATH.exists():
        tickers: List[str] = []
        for line in _UNIVERSE_SP1500_PATH.read_text(encoding="utf-8").splitlines():
            token = line.strip().upper()
            if not token or token.startswith("#"):
                continue
            tickers.append(token)
        return tickers
    
    # Fall back to S&P 500
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
    lowered_text = (text or "").lower()
    original_text = text or ""  # Keep original for case checking
    
    # Forecasting keyword detection - extract company names from forecasting query structures
    # Patterns like "Forecast Apple revenue", "Predict Microsoft revenue using LSTM"
    forecasting_keywords = [
        r'\bforecast\b', r'\bpredict\b', r'\bestimate\b', r'\bprojection\b',
        r'\bproject\b', r'\boutlook\b', r'\bfuture\b',
    ]
    is_forecasting_query = any(re.search(pattern, lowered_text, re.IGNORECASE) for pattern in forecasting_keywords)
    
    # If forecasting query, try to extract company name from forecasting patterns
    if is_forecasting_query:
        # Patterns for forecasting queries: "Forecast [Company] revenue", "[Company]'s revenue forecast"
        forecasting_patterns = [
            r'\b(?:forecast|predict|estimate|project)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income)',
            r'\b(?:forecast|predict|estimate|project)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income)\s+(?:forecast|prediction|estimate)',
            r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income)\s+(?:forecast|prediction|estimate)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income)\s+(?:forecast|prediction|estimate)',
        ]
        
        for pattern in forecasting_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                # Try to resolve the extracted company name using alias lookup directly
                # Avoid recursion by using internal lookup functions
                try:
                    alias_map, lookup, ticker_set = _ensure_lookup_loaded()
                    # Try direct lookup first
                    company_lower = company_name.lower()
                    if company_lower in lookup:
                        for ticker in lookup[company_lower]:
                            return [{"input": company_name, "ticker": ticker}], []
                    # Try fuzzy matching
                    normalized_company = normalize_alias(company_lower)
                    if normalized_company in lookup:
                        for ticker in lookup[normalized_company]:
                            return [{"input": company_name, "ticker": ticker}], []
                    # Try partial matching
                    for alias, tickers in lookup.items():
                        if company_lower in alias or alias in company_lower:
                            for ticker in tickers:
                                return [{"input": company_name, "ticker": ticker}], []
                except Exception:
                    # If resolution fails, continue to normal flow below
                    pass
    
    # Portfolio keyword blacklist - skip ticker resolution if portfolio keywords detected
    # This prevents false positives like "portfolio risk" -> VRSK, "portfolio CVaR" -> CPB
    # "What's my portfolio" -> CPB, "risk?" -> VRSK
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
        r'\bportfolio\s+scenario\b', r'\bportfolio\s+stress\b', r'\bportfolio\s+esg\b',
        r'\bportfolio\s+tax\b', r'\bportfolio\s+tracking\b', r'\bportfolio\s+sentiment\b',
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
    
    # Check if this is a portfolio query - if so, skip ticker resolution
    is_portfolio_query = any(re.search(pattern, lowered_text, re.IGNORECASE) for pattern in portfolio_keywords)
    if is_portfolio_query:
        return [], []
    
    normalized_text = normalize_alias(lowered_text)
    padded_text = f" {normalized_text} "
    matches: List[Tuple[int, str, str]] = []
    seen: Set[str] = set()
    warnings: List[str] = []
    
    # CRITICAL: Question stopwords to prevent false ticker matches
    # Don't resolve question words as tickers
    # Expanded to include more variations and ensure they're checked BEFORE ticker matching
    QUESTION_STOPWORDS = {
        "what", "whats", "what's", "whats'", "how", "hows", "how's", "why", "when", "where", "who", "which",
        "is", "are", "was", "were", "does", "did", "do", "can", "could", "would", "should", "will",
        "has", "have", "had", "to", "from", "in", "on", "by", "at", "the", "a", "an", "of", "for", "with",
        "tell", "help", "explain", "understand", "know", "think", "see", "look", "find",
        "trading", "growing", "performing", "profitable", "sales", "revenue", "profit", "margin",
        "figures", "metrics", "data", "information", "about", "their", "its", "them",
        # Additional stopwords to prevent false matches
        "ratio", "risk", "sharpe", "sortino", "alpha", "beta", "cvar", "cva", "volatility",
        "portfolio", "holdings", "exposure", "allocation", "diversification",
    }

    for match in _TICKER_PATTERN.finditer(lowered_text):
        raw_token = match.group(0)
        token = raw_token.upper()
        token_lower = raw_token.lower().rstrip('?.,!;:')
        
        # Check if token is a valid ticker FIRST - if it is, don't filter it out
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
            continue
        
        # Only filter out stopwords if they're NOT valid tickers
        # This prevents false matches like "What's" -> CPB, "risk?" -> VRSK
        # But allows legitimate tickers like AN, DO, ON
        if token_lower in QUESTION_STOPWORDS:
            continue
        
        if len(token) <= 2 and not raw_token.isupper():
            continue

    for alias, tickers in lookup.items():
        # Try multiple matching strategies for each alias
        # Strategy 1: Exact phrase match
        marker = f" {alias} "
        position = padded_text.find(marker)
        
        # Strategy 2: Word boundary match (for single words that might be part of phrases)
        if position == -1 and len(alias.split()) == 1:
            # Try finding the word with word boundaries
            word_pattern = re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE)
            match = word_pattern.search(normalized_text)
            if match:
                position = match.start()
        
        if position == -1:
            continue
        
        # Allow short aliases if they're valid tickers (e.g., AN, DO, ON)
        # Only skip very short aliases that aren't in ticker_set
        if len(alias) <= 2:
            # Check if any of the tickers for this alias are valid
            has_valid_ticker = any(t in ticker_set for t in tickers)
            if not has_valid_ticker:
                continue
        # For longer aliases that are stopwords, still allow if they're valid tickers
        # This handles cases like "booking", "enact", "bread" which are stopwords but also company names
        elif alias in QUESTION_STOPWORDS:
            has_valid_ticker = any(t in ticker_set for t in tickers)
            if not has_valid_ticker:
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
        
        # First try lookup
        tickers_to_try = lookup.get(alias_key, [])
        
        # If not in lookup, check manual overrides directly (in case aliases.json wasn't regenerated)
        if not tickers_to_try and alias_key in _MANUAL_OVERRIDES:
            override_ticker = _MANUAL_OVERRIDES[alias_key]
            if override_ticker in ticker_set:
                tickers_to_try = [override_ticker]
        
        # Also try normalized version in manual overrides
        if not tickers_to_try:
            normalized_key = normalize_alias(alias_key)
            if normalized_key and normalized_key != alias_key and normalized_key in _MANUAL_OVERRIDES:
                override_ticker = _MANUAL_OVERRIDES[normalized_key]
                if override_ticker in ticker_set:
                    tickers_to_try = [override_ticker]
        
        for ticker in tickers_to_try:
            if ticker in seen:
                continue
            resolved.append({"input": source_value, "ticker": ticker})
            seen.add(ticker)
            if mark_warning:
                warnings.append("fuzzy_match")
            return True
        return False

    tokens = [token for token in _base_tokens(lowered_text) if token]
    
    # FIRST: Try single-word tokens for misspellings (e.g., "tesl", "bookng", "nvida")
    # This is important for company names that are single words
    for token in tokens:
        if len(token) < 3:
            continue
        token_normalized = normalize_alias(token)
        # Use original token if normalization returns empty (e.g., "holdings" -> "")
        if not token_normalized:
            token_normalized = token.lower().strip()
        
        # Check if token is a valid ticker FIRST (try both normalized and original)
        is_valid_ticker = any(t in ticker_set for t in lookup.get(token_normalized, []))
        if not is_valid_ticker and token != token_normalized:
            # Also try original token
            is_valid_ticker = any(t in ticker_set for t in lookup.get(token.lower().strip(), []))
        
        # Skip if it's a stopword and not a valid ticker
        if token_normalized in QUESTION_STOPWORDS and not is_valid_ticker:
            # Try with original token if normalized is stopword
            if token.lower().strip() not in QUESTION_STOPWORDS:
                token_normalized = token.lower().strip()
                is_valid_ticker = any(t in ticker_set for t in lookup.get(token_normalized, []))
            if token_normalized in QUESTION_STOPWORDS and not is_valid_ticker:
                continue
        
        # Check manual overrides FIRST (before exact match, in case aliases.json wasn't regenerated)
        if token_normalized in _MANUAL_OVERRIDES:
            override_ticker = _MANUAL_OVERRIDES[token_normalized]
            if override_ticker in ticker_set:
                if _try_add_alias(token_normalized, token):
                    continue
        # Also check original token
        if token.lower().strip() != token_normalized and token.lower().strip() in _MANUAL_OVERRIDES:
            override_ticker = _MANUAL_OVERRIDES[token.lower().strip()]
            if override_ticker in ticker_set:
                if _try_add_alias(token.lower().strip(), token):
                    continue
        
        # Try exact match first (with normalized)
        if _try_add_alias(token_normalized, token):
            continue
        # Also try with original token if different
        if token.lower().strip() != token_normalized and _try_add_alias(token.lower().strip(), token):
            continue
        
        # If exact match fails, try fuzzy matching for misspellings
        # Check if this looks like a company name (4+ chars or capitalized in original)
        original_token_pos = lowered_text.find(token)
        original_token = original_text[original_token_pos:original_token_pos+len(token)] if original_token_pos >= 0 else ""
        looks_like_company = len(token) >= 4 or (original_token and original_token[0].isupper())
        
        if looks_like_company and not is_valid_ticker:
            # Try fuzzy matching with progressive cutoffs for single-word misspellings
            best_match = None
            best_score = 0.0
            best_cutoff = 0.0
            
            for cutoff in [0.85, 0.80, 0.75, 0.70, 0.65]:
                close_matches = difflib.get_close_matches(token_normalized, alias_candidates, n=20, cutoff=cutoff)
                if close_matches:
                    for alias_candidate in close_matches:
                        # Skip if alias is a stopword and not a valid ticker
                        if alias_candidate in QUESTION_STOPWORDS:
                            if not any(t in ticker_set for t in lookup.get(alias_candidate, [])):
                                continue
                        
                        score = difflib.SequenceMatcher(None, token_normalized, alias_candidate).ratio()
                        # Use adaptive threshold - be more lenient for misspellings
                        # Prioritize matches that are longer and more similar
                        threshold = 0.85 if cutoff >= 0.75 else 0.80 if cutoff >= 0.70 else 0.75
                        
                        # Boost score for longer matches and similar length
                        if len(alias_candidate) >= 4:
                            # Prefer matches with similar length (within 1-2 chars)
                            length_diff = abs(len(token_normalized) - len(alias_candidate))
                            if length_diff <= 2:
                                score_boost = 0.05
                            elif length_diff <= 3:
                                score_boost = 0.02
                            else:
                                score_boost = 0.0
                            adjusted_score = min(1.0, score + score_boost)
                        else:
                            adjusted_score = score
                        
                        if adjusted_score >= threshold:
                            candidate_tickers = lookup.get(alias_candidate, [])
                            if candidate_tickers:
                                # Track the best match across all cutoffs
                                if adjusted_score > best_score:
                                    best_match = alias_candidate
                                    best_score = adjusted_score
                                    best_cutoff = cutoff
                                # If we have a very good match, use it immediately
                                if adjusted_score >= 0.90:
                                    if _try_add_alias(alias_candidate, token):
                                        break
            
            # Use the best match if we found one
            if best_match and best_score >= 0.80:
                if _try_add_alias(best_match, token):
                    continue
    
    # THEN: Try multi-word phrases
    max_window = min(5, len(tokens))  # Increased from 4 to 5 for longer company names
    for window in range(max_window, 2, -1):  # Start with longer phrases (5 words, then 4, then 3)
        for start_idx in range(len(tokens) - window + 1):
            phrase_tokens = tokens[start_idx : start_idx + window]
            candidate_phrase = " ".join(phrase_tokens)
            if not candidate_phrase:
                continue
            normalised_phrase = normalize_alias(candidate_phrase)
            
            # CRITICAL: Check if phrase matches a valid ticker FIRST (including manual overrides)
            # This allows common words that are also company names (e.g., "booking", "enact")
            is_valid_ticker = any(t in ticker_set for t in lookup.get(normalised_phrase, []))
            # Also check manual overrides before filtering
            if not is_valid_ticker:
                if normalised_phrase in _MANUAL_OVERRIDES:
                    override_ticker = _MANUAL_OVERRIDES[normalised_phrase]
                    if override_ticker in ticker_set:
                        is_valid_ticker = True
                elif candidate_phrase.lower().strip() in _MANUAL_OVERRIDES:
                    override_ticker = _MANUAL_OVERRIDES[candidate_phrase.lower().strip()]
                    if override_ticker in ticker_set:
                        is_valid_ticker = True
            
            # Only filter out stopwords if they're NOT valid tickers (including manual overrides)
            if normalised_phrase in QUESTION_STOPWORDS and not is_valid_ticker:
                continue
            
            # Try exact match first (including manual overrides)
            # If normalization returns empty, try with original phrase
            if not normalised_phrase:
                normalised_phrase = candidate_phrase.lower().strip()
            
            # Check manual overrides FIRST (before lookup, in case aliases.json wasn't regenerated)
            if normalised_phrase in _MANUAL_OVERRIDES:
                override_ticker = _MANUAL_OVERRIDES[normalised_phrase]
                if override_ticker in ticker_set:
                    if _try_add_alias(normalised_phrase, candidate_phrase):
                        continue
            # Also check original phrase
            if candidate_phrase.lower().strip() in _MANUAL_OVERRIDES:
                override_ticker = _MANUAL_OVERRIDES[candidate_phrase.lower().strip()]
                if override_ticker in ticker_set:
                    if _try_add_alias(candidate_phrase.lower().strip(), candidate_phrase):
                        continue
            
            if normalised_phrase:
                if _try_add_alias(normalised_phrase, candidate_phrase):
                    continue
                # Also try with original phrase if different
                if candidate_phrase.lower().strip() != normalised_phrase:
                    if _try_add_alias(candidate_phrase.lower().strip(), candidate_phrase):
                        continue
            
            # For multi-word phrases, try progressively shorter versions
            if len(phrase_tokens) > 1:
                # Strategy 1: Try without last word if it's a common suffix
                if phrase_tokens[-1] in ["holdings", "inc", "incorporated", "corp", "corporation", "ltd", "company", "co", "group", "parent", "ltd"]:
                    shorter_phrase = " ".join(phrase_tokens[:-1])
                    shorter_normalized = normalize_alias(shorter_phrase)
                    # If normalization returns empty, use original
                    if not shorter_normalized:
                        shorter_normalized = shorter_phrase.lower().strip()
                    
                    if shorter_normalized:
                        # Try exact match with normalized
                        if _try_add_alias(shorter_normalized, shorter_phrase):
                            continue
                        # Also try with original if different
                        if shorter_phrase.lower().strip() != shorter_normalized:
                            if _try_add_alias(shorter_phrase.lower().strip(), shorter_phrase):
                                continue
                
                # Strategy 2: Try first word (important for company names like "Booking Holdings")
                if len(phrase_tokens) >= 2:
                    first_word = phrase_tokens[0]
                    first_normalized = normalize_alias(first_word)
                    # Use original word if normalization returns empty
                    if not first_normalized:
                        first_normalized = first_word.lower().strip()
                    
                    if first_normalized:
                        # Always try first word if it's a valid ticker alias (even if it's a stopword)
                        is_first_word_ticker = any(t in ticker_set for t in lookup.get(first_normalized, []))
                        if not is_first_word_ticker:
                            # Also check manual overrides
                            if first_normalized in _MANUAL_OVERRIDES:
                                override_ticker = _MANUAL_OVERRIDES[first_normalized]
                                if override_ticker in ticker_set:
                                    is_first_word_ticker = True
                                    if _try_add_alias(first_normalized, first_word):
                                        continue
                            if first_word.lower().strip() in _MANUAL_OVERRIDES:
                                override_ticker = _MANUAL_OVERRIDES[first_word.lower().strip()]
                                if override_ticker in ticker_set:
                                    is_first_word_ticker = True
                                    if _try_add_alias(first_word.lower().strip(), first_word):
                                        continue
                        
                        if is_first_word_ticker:
                            if _try_add_alias(first_normalized, first_word):
                                continue
                        # Also try if it's not a stopword
                        elif first_normalized not in QUESTION_STOPWORDS:
                            if _try_add_alias(first_normalized, first_word):
                                continue
                
                # Strategy 3: Try all individual words in the phrase (for cases like "Enact Holdings" -> try "enact")
                for word in phrase_tokens:
                    word_normalized = normalize_alias(word)
                    # Use original word if normalization returns empty
                    if not word_normalized:
                        word_normalized = word.lower().strip()
                    
                    if word_normalized and len(word_normalized) >= 3:  # Only try words with 3+ chars
                        is_word_ticker = any(t in ticker_set for t in lookup.get(word_normalized, []))
                        if not is_word_ticker and word != word_normalized:
                            # Also try original word
                            is_word_ticker = any(t in ticker_set for t in lookup.get(word.lower().strip(), []))
                        
                        # Also check manual overrides
                        if not is_word_ticker:
                            if word_normalized in _MANUAL_OVERRIDES:
                                override_ticker = _MANUAL_OVERRIDES[word_normalized]
                                if override_ticker in ticker_set:
                                    is_word_ticker = True
                            if not is_word_ticker and word.lower().strip() in _MANUAL_OVERRIDES:
                                override_ticker = _MANUAL_OVERRIDES[word.lower().strip()]
                                if override_ticker in ticker_set:
                                    is_word_ticker = True
                        
                        if is_word_ticker:
                            # Try with normalized first
                            if word_normalized and _try_add_alias(word_normalized, word):
                                continue
                            # Also try with original if different
                            if word.lower().strip() != word_normalized and _try_add_alias(word.lower().strip(), word):
                                continue
                
                # Strategy 4: Try without multiple suffix words (e.g., "group holdings parent" -> just base)
                if len(phrase_tokens) >= 3:
                    # Try first N-2 words (removing last 2 if they're suffixes)
                    if phrase_tokens[-1] in ["holdings", "inc", "incorporated", "corp", "corporation", "ltd", "company", "co", "group", "parent"] and \
                       phrase_tokens[-2] in ["holdings", "inc", "incorporated", "corp", "corporation", "ltd", "company", "co", "group", "parent"]:
                        base_phrase = " ".join(phrase_tokens[:-2])
                        base_normalized = normalize_alias(base_phrase)
                        if base_normalized and _try_add_alias(base_normalized, base_phrase):
                            continue
            
            # Allow short phrases if they're valid tickers
            if len(normalised_phrase) <= 2:
                # Check if it's a valid ticker before skipping
                if not any(t in ticker_set for t in lookup.get(normalised_phrase, [])):
                    continue
            
            # OPTIMIZATION: Pre-filter candidates before expensive fuzzy matching
            # Only consider aliases with similar characteristics
            phrase_len = len(normalised_phrase)
            first_char = normalised_phrase[0] if normalised_phrase else ''
            
            # Pre-filter: only check aliases with similar length and same first letter
            # But be more lenient for spelling mistakes - allow slightly different first letters
            filtered_candidates = [
                alias for alias in alias_candidates
                if alias and
                alias[0] == first_char and  # Same first letter
                abs(len(alias) - phrase_len) <= 6  # Similar length (±6 chars, increased from 5 for spelling mistakes)
            ]
            
            # If no candidates after filtering, try without first letter requirement for longer phrases
            # Also try similar first letters for common misspellings (e.g., "Appel" vs "Apple")
            if not filtered_candidates and phrase_len >= 4:
                # First try without first letter requirement
                filtered_candidates = [
                    alias for alias in alias_candidates
                    if alias and abs(len(alias) - phrase_len) <= 6
                ]
                
                # If still no matches, try similar first letters (common typos)
                if not filtered_candidates and phrase_len >= 3:
                    # Common first letter typos: a/e, e/a, i/e, o/u, etc.
                    similar_first_chars = []
                    if first_char in 'aeiou':
                        # Vowel substitutions
                        for v in 'aeiou':
                            if v != first_char:
                                similar_first_chars.append(v)
                    else:
                        # Consonant substitutions (common typos)
                        char_map = {
                            'b': 'p', 'p': 'b',
                            'c': 'k', 'k': 'c',
                            'd': 't', 't': 'd',
                            'g': 'j', 'j': 'g',
                            'm': 'n', 'n': 'm',
                            'v': 'w', 'w': 'v',
                        }
                        if first_char in char_map:
                            similar_first_chars.append(char_map[first_char])
                    
                    for similar_char in similar_first_chars:
                        filtered_candidates = [
                            alias for alias in alias_candidates
                            if alias and alias[0] == similar_char and abs(len(alias) - phrase_len) <= 6
                        ]
                        if filtered_candidates:
                            break
            
            # If still no candidates, skip fuzzy matching
            if not filtered_candidates:
                continue
            
            # Limit to top 100 candidates max (increased from 50 for better coverage)
            if len(filtered_candidates) > 100:
                filtered_candidates = filtered_candidates[:100]
            
            best_alias = None
            best_score = 0.0
            for alias in filtered_candidates:
                score = difflib.SequenceMatcher(None, normalised_phrase, alias).ratio()
                if score > best_score:
                    best_alias = alias
                    best_score = score
                # Early exit if we find a very good match
                if score >= 0.98:
                    break
            
            # Lower threshold to 0.82 for better matching of company names and spelling mistakes
            # Balance between catching misspellings and avoiding false positives
            # This handles misspellings like "Microsft", "Appel", "Tesl" while maintaining accuracy
            if best_alias and best_score >= 0.82:
                if _try_add_alias(best_alias, candidate_phrase, mark_warning=True):
                    continue

    # If nothing resolved yet, attempt a softer suggestion with spelling mistake tolerance
    if not resolved:
        suggestion_alias: Optional[str] = None
        suggestion_score: float = 0.0
        suggestion_source: Optional[str] = None
        
        # Try individual tokens first (also check original tokens that might not have been normalized)
        unique_tokens = []
        for token in tokens:
            token_norm = normalize_alias(token)
            if token_norm and token_norm not in unique_tokens:
                unique_tokens.append(token_norm)
            # Also add original token if different and not empty
            if token.lower().strip() and token.lower().strip() != token_norm and token.lower().strip() not in unique_tokens:
                unique_tokens.append(token.lower().strip())
        
        for token_norm in unique_tokens:
            if len(token_norm) < 3:
                continue
            # Check manual overrides FIRST (before any other checks)
            if token_norm in _MANUAL_OVERRIDES:
                override_ticker = _MANUAL_OVERRIDES[token_norm]
                if override_ticker in ticker_set:
                    # Direct match found in manual overrides
                    suggestion_score = 1.0  # Perfect match for manual override
                    suggestion_alias = token_norm
                    suggestion_source = token_norm
                    break  # Exit early for manual override match
            # Skip question words that are not valid tickers (but check manual overrides first)
            if token_norm in QUESTION_STOPWORDS:
                # Only skip if it's not a valid ticker alias and not in manual overrides
                if not any(t in ticker_set for t in lookup.get(token_norm, [])):
                    continue
            # Lower cutoff to 0.60 for better spelling mistake tolerance
            # Try even more aggressive matching for common misspellings
            for cutoff in [0.75, 0.70, 0.65, 0.60]:
                close_matches = difflib.get_close_matches(token_norm, alias_candidates, n=10, cutoff=cutoff)
                if close_matches:
                    for alias_candidate in close_matches:
                        # Skip if alias is a stopword and not a valid ticker
                        if alias_candidate in QUESTION_STOPWORDS:
                            if not any(t in ticker_set for t in lookup.get(alias_candidate, [])):
                                continue
                        score = difflib.SequenceMatcher(None, token_norm, alias_candidate).ratio()
                        # Use adaptive threshold based on cutoff
                        threshold = 0.85 if cutoff >= 0.70 else 0.75
                        if score >= threshold and score > suggestion_score:
                            suggestion_score = score
                            suggestion_alias = alias_candidate
                            suggestion_source = token_norm
                            if score >= 0.85:  # Early exit for good matches
                                break
                    if suggestion_score >= 0.85:
                        break
            if suggestion_score >= 0.85:
                break
        
        # Also try multi-word phrases with spelling mistakes
        if suggestion_score < 0.85:
            for window in range(min(3, len(tokens)), 0, -1):
                for start_idx in range(len(tokens) - window + 1):
                    phrase_tokens = tokens[start_idx : start_idx + window]
                    candidate_phrase = " ".join(phrase_tokens)
                    if not candidate_phrase:
                        continue
                    normalised_phrase = normalize_alias(candidate_phrase)
                    if len(normalised_phrase) < 4:
                        continue
                    # Check manual overrides FIRST (before fuzzy matching)
                    if normalised_phrase in _MANUAL_OVERRIDES:
                        override_ticker = _MANUAL_OVERRIDES[normalised_phrase]
                        if override_ticker in ticker_set:
                            # Direct match found in manual overrides
                            suggestion_score = 1.0  # Perfect match for manual override
                            suggestion_alias = normalised_phrase
                            suggestion_source = candidate_phrase
                            break  # Exit early for manual override match
                    # Also check original phrase
                    if candidate_phrase.lower().strip() in _MANUAL_OVERRIDES:
                        override_ticker = _MANUAL_OVERRIDES[candidate_phrase.lower().strip()]
                        if override_ticker in ticker_set:
                            # Direct match found in manual overrides
                            suggestion_score = 1.0  # Perfect match for manual override
                            suggestion_alias = candidate_phrase.lower().strip()
                            suggestion_source = candidate_phrase
                            break  # Exit early for manual override match
                    # Try fuzzy matching with progressive cutoffs for spelling mistakes
                    for cutoff in [0.75, 0.70, 0.65, 0.60]:
                        close_matches = difflib.get_close_matches(normalised_phrase, alias_candidates, n=10, cutoff=cutoff)
                        if close_matches:
                            for alias_candidate in close_matches:
                                score = difflib.SequenceMatcher(None, normalised_phrase, alias_candidate).ratio()
                                # Use adaptive threshold based on cutoff
                                threshold = 0.85 if cutoff >= 0.70 else 0.75
                                if score >= threshold and score > suggestion_score:
                                    suggestion_score = score
                                    suggestion_alias = alias_candidate
                                    suggestion_source = candidate_phrase
                                    if score >= 0.85:  # Early exit for good matches
                                        break
                            if suggestion_score >= 0.85:
                                break
                    if suggestion_score >= 0.85:
                        break
                if suggestion_score >= 0.90:
                    break
        
        if suggestion_alias and suggestion_score >= 0.78:  # Balanced threshold for spelling mistakes
            # First check manual overrides
            if suggestion_alias in _MANUAL_OVERRIDES:
                override_ticker = _MANUAL_OVERRIDES[suggestion_alias]
                if override_ticker in ticker_set:
                    resolved.append({"input": suggestion_source or suggestion_alias, "ticker": override_ticker})
                    warnings.append(f"suggested_ticker:{override_ticker}:{suggestion_source or suggestion_alias}")
            else:
                # Otherwise, use lookup
                tickers = lookup.get(suggestion_alias, [])
                if tickers:
                    ticker = tickers[0]
                    resolved.append({"input": suggestion_source or suggestion_alias, "ticker": ticker})
                    warnings.append(f"suggested_ticker:{ticker}:{suggestion_source or suggestion_alias}")

    return resolved, warnings


__all__ = [
    "build_alias_map",
    "load_aliases",
    "normalize_alias",
    "resolve_tickers_freeform",
]
