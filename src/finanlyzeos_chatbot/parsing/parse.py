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

# NEW: Sector/Industry Analysis intent patterns
INTENT_SECTOR_ANALYSIS_PATTERN = re.compile(
    r"\b(sector\s+analysis|industry\s+analysis|sector\s+performance|industry\s+performance|"
    r"sector\s+outlook|industry\s+outlook|sector\s+trends|industry\s+trends|"
    r"sector\s+comparison|industry\s+comparison|sector\s+benchmark|industry\s+benchmark|"
    r"how\s+is\s+the\s+(?:tech|financial|healthcare|energy|consumer|industrial|real\s+estate)\s+(?:sector|industry)|"
    r"what\'s\s+happening\s+in\s+the\s+(?:tech|financial|healthcare|energy|consumer|industrial|real\s+estate)\s+(?:sector|industry)|"
    r"sector\s+overview|industry\s+overview|sector\s+health|industry\s+health|"
    r"peer\s+group|peer\s+analysis|sector\s+peers|industry\s+peers)\b",
    re.IGNORECASE
)

# NEW: Market Analysis intent patterns
INTENT_MARKET_ANALYSIS_PATTERN = re.compile(
    r"\b(market\s+analysis|market\s+outlook|market\s+trends|market\s+performance|"
    r"market\s+conditions|market\s+environment|market\s+dynamics|"
    r"market\s+share|market\s+position|market\s+leadership|market\s+dominance|"
    r"competitive\s+position|competitive\s+landscape|competitive\s+analysis|"
    r"market\s+opportunity|market\s+potential|addressable\s+market|TAM|SAM|"
    r"market\s+growth|market\s+expansion|market\s+penetration|"
    r"how\s+is\s+the\s+market|what\'s\s+the\s+market|market\s+overview)\b",
    re.IGNORECASE
)

# NEW: M&A and Corporate Actions intent patterns
INTENT_MERGER_ACQUISITION_PATTERN = re.compile(
    r"\b(merger|acquisition|M&A|M\s*&\s*A|mergers\s+and\s+acquisitions|"
    r"takeover|buyout|acquisition\s+target|merger\s+target|"
    r"deal|deal\s+analysis|transaction|transaction\s+analysis|"
    r"spin\s+off|spin\s+off|divestiture|divestment|"
    r"corporate\s+action|corporate\s+restructuring|"
    r"has\s+\w+\s+(?:acquired|bought|merged|taken\s+over)|"
    r"did\s+\w+\s+(?:acquire|buy|merge|take\s+over)|"
    r"is\s+\w+\s+(?:acquiring|buying|merging|being\s+acquired|being\s+bought))\b",
    re.IGNORECASE
)

# NEW: IPO and Public Offering intent patterns
INTENT_IPO_PATTERN = re.compile(
    r"\b(IPO|initial\s+public\s+offering|going\s+public|public\s+offering|"
    r"listing|stock\s+listing|equity\s+offering|secondary\s+offering|"
    r"when\s+did\s+\w+\s+go\s+public|when\s+was\s+\w+\s+IPO|"
    r"IPO\s+date|IPO\s+price|IPO\s+valuation|"
    r"is\s+\w+\s+going\s+public|will\s+\w+\s+go\s+public|"
    r"public\s+company|private\s+company)\b",
    re.IGNORECASE
)

# NEW: ESG and Sustainability intent patterns
INTENT_ESG_PATTERN = re.compile(
    r"\b(ESG|environmental|social|governance|sustainability|"
    r"ESG\s+score|ESG\s+rating|ESG\s+performance|ESG\s+metrics|"
    r"carbon\s+footprint|emissions|greenhouse\s+gas|GHG|"
    r"diversity|inclusion|corporate\s+responsibility|CSR|"
    r"ethical|ethics|compliance|regulatory\s+compliance|"
    r"ESG\s+report|sustainability\s+report|impact|social\s+impact)\b",
    re.IGNORECASE
)

# NEW: Credit and Debt Analysis intent patterns
INTENT_CREDIT_ANALYSIS_PATTERN = re.compile(
    r"\b(credit\s+analysis|credit\s+rating|credit\s+risk|credit\s+quality|"
    r"debt\s+analysis|debt\s+structure|debt\s+profile|leverage\s+analysis|"
    r"credit\s+default|default\s+risk|bankruptcy\s+risk|solvency|"
    r"debt\s+to\s+equity|debt\s+ratio|leverage\s+ratio|"
    r"interest\s+coverage|debt\s+service|debt\s+capacity|"
    r"bond\s+rating|credit\s+spread|yield|"
    r"how\s+leveraged|how\s+much\s+debt|debt\s+level|debt\s+burden)\b",
    re.IGNORECASE
)

# NEW: Liquidity Analysis intent patterns
INTENT_LIQUIDITY_PATTERN = re.compile(
    r"\b(liquidity|liquid|liquidity\s+analysis|liquidity\s+ratio|"
    r"current\s+ratio|quick\s+ratio|acid\s+test|working\s+capital|"
    r"cash\s+position|cash\s+reserves|cash\s+on\s+hand|"
    r"cash\s+equivalents|short\s+term\s+liquidity|"
    r"can\s+they\s+pay|ability\s+to\s+pay|payment\s+ability|"
    r"liquidity\s+crisis|liquidity\s+risk|illiquid)\b",
    re.IGNORECASE
)

# NEW: Capital Structure intent patterns
INTENT_CAPITAL_STRUCTURE_PATTERN = re.compile(
    r"\b(capital\s+structure|capital\s+allocation|capital\s+management|"
    r"equity\s+structure|debt\s+structure|financing\s+structure|"
    r"share\s+capital|authorized\s+shares|outstanding\s+shares|"
    r"share\s+buyback|stock\s+buyback|repurchase|share\s+repurchase|"
    r"dividend\s+policy|dividend\s+strategy|payout\s+policy|"
    r"capital\s+expenditure|CAPEX|capital\s+spending|"
    r"how\s+is\s+capital\s+allocated|capital\s+allocation\s+strategy)\b",
    re.IGNORECASE
)

# NEW: Economic Indicators intent patterns
INTENT_ECONOMIC_INDICATORS_PATTERN = re.compile(
    r"\b(economic\s+indicators|economic\s+data|macro\s+economic|macroeconomic|"
    r"GDP|gross\s+domestic\s+product|inflation|deflation|CPI|consumer\s+price\s+index|"
    r"unemployment|employment|job\s+market|interest\s+rates|fed\s+rate|federal\s+funds\s+rate|"
    r"yield\s+curve|bond\s+yield|treasury|economic\s+growth|economic\s+outlook|"
    r"recession|economic\s+downturn|economic\s+cycle|business\s+cycle|"
    r"how\s+does\s+the\s+economy|economic\s+impact|macro\s+environment)\b",
    re.IGNORECASE
)

# NEW: Regulatory and Compliance intent patterns
INTENT_REGULATORY_PATTERN = re.compile(
    r"\b(regulatory|regulation|compliance|regulatory\s+compliance|"
    r"SEC|securities\s+and\s+exchange\s+commission|filing|10-K|10-Q|8-K|"
    r"regulatory\s+risk|compliance\s+risk|regulatory\s+environment|"
    r"audit|auditor|audit\s+opinion|internal\s+controls|"
    r"regulatory\s+action|enforcement|regulatory\s+scrutiny|"
    r"legal\s+issues|litigation|lawsuits|legal\s+risk)\b",
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
    """Detect requested metrics from synonyms and canonical names.
    
    Enhanced to handle:
    - Apostrophes and punctuation (e.g., "Apple's revenue")
    - Case variations
    - Compound words without spaces (e.g., "netincome" -> "net income")
    - Hyphenated variations (e.g., "price-to-earnings" -> "price to earnings")
    - Space-separated abbreviations (e.g., "p e" -> "pe")
    - Partial matches when exact matches fail
    - Word boundaries that work with punctuation
    """
    matches: List[Dict[str, Any]] = []
    seen: set[str] = set()
    
    # Normalize the text for better matching:
    # 1. Replace hyphens with spaces (e.g., "price-to-earnings" -> "price to earnings")
    # 2. Normalize multiple spaces to single space
    # 3. Handle compound words by trying to split common patterns
    normalized_text = lowered_full
    
    # Replace hyphens with spaces for better matching
    normalized_text = re.sub(r'[\-–—]', ' ', normalized_text)
    
    # Normalize multiple spaces
    normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()
    
    # Create a version with common compound word splits
    # This helps match "netincome" -> "net income", "marketcap" -> "market cap", etc.
    compound_splits = normalized_text
    # Try to split common compound patterns (camelCase-like but all lowercase)
    # Pattern: lowercase word followed by uppercase or another word boundary
    # For now, we'll handle this in the matching logic below

    for alias, metric_id in _METRIC_ITEMS:
        if not alias:
            continue
        
        # Try multiple matching strategies
        found = None
        original_fragment = None
        
        # Strategy 1: Exact match with flexible word boundaries
        # Handle apostrophes, hyphens, and other punctuation
        escaped = re.escape(alias).replace(r"\ ", r"\s+")
        # Allow word boundary OR apostrophe/hyphen before/after
        pattern1 = re.compile(r"(?<![a-zA-Z0-9])" + escaped + r"(?![a-zA-Z0-9])", re.IGNORECASE)
        found = pattern1.search(normalized_text)
        
        # Strategy 2: If exact match fails, try without strict word boundaries
        # (for phrases like "top line" that might be split)
        if not found:
            # Replace spaces with flexible whitespace matching
            flexible_alias = alias.replace(" ", r"\s+")
            pattern2 = re.compile(flexible_alias, re.IGNORECASE)
            found = pattern2.search(normalized_text)
        
        # Strategy 3: Handle compound words (e.g., "netincome" -> "net income")
        # Try matching alias without spaces against compound words
        if not found:
            alias_no_spaces = alias.replace(" ", "").replace("-", "").replace("_", "")
            if len(alias_no_spaces) > 2:  # Only for meaningful aliases
                # Try to find compound word that matches (e.g., "netincome" contains "net" and "income")
                # Create pattern that matches the compound word
                compound_pattern = re.compile(
                    r"(?<![a-zA-Z0-9])" + re.escape(alias_no_spaces) + r"(?![a-zA-Z0-9])",
                    re.IGNORECASE
                )
                found = compound_pattern.search(normalized_text)
                
                # Also try matching individual words from alias in compound
                if not found and " " in alias:
                    words = alias.split()
                    if len(words) == 2:
                        # Try to match compound like "netincome" for "net income"
                        first_word = words[0].lower()
                        second_word = words[1].lower()
                        # Pattern: first word immediately followed by second word (no space)
                        compound_word_pattern = re.compile(
                            r"(?<![a-zA-Z0-9])" + re.escape(first_word + second_word) + r"(?![a-zA-Z0-9])",
                            re.IGNORECASE
                        )
                        found = compound_word_pattern.search(normalized_text)
        
        # Strategy 4: Handle space-separated abbreviations (e.g., "p e" -> "pe")
        if not found:
            alias_no_spaces = alias.replace(" ", "").replace("-", "").replace("_", "")
            if len(alias_no_spaces) <= 5 and len(alias.split()) == 1:  # Short abbreviations
                # Try to match space-separated version (e.g., "p e" for "pe")
                if len(alias_no_spaces) >= 2:
                    # Create pattern like "p\s+e" for "pe"
                    spaced_pattern = r"\s+".join(list(alias_no_spaces))
                    spaced_regex = re.compile(
                        r"(?<![a-zA-Z0-9])" + spaced_pattern + r"(?![a-zA-Z0-9])",
                        re.IGNORECASE
                    )
                    found = spaced_regex.search(normalized_text)
        
        # Strategy 5: Try partial match (alias contained in text)
        if not found:
            if alias.lower() in normalized_text:
                # Find the position
                idx = normalized_text.find(alias.lower())
                if idx >= 0:
                    # Create a match-like object
                    class Match:
                        def __init__(self, start, end):
                            self.start = lambda: start
                            self.end = lambda: end
                    found = Match(idx, idx + len(alias))
        
        if not found:
            continue
        
        if metric_id in seen:
            continue
        
        # Extract original fragment preserving case
        # Map back to original text position if possible
        start_pos = found.start()
        end_pos = found.end()
        
        # Try to find the corresponding position in original text
        # by searching for the matched text in the original
        matched_text = normalized_text[start_pos:end_pos]
        # Find in original lowered_full (which preserves more structure)
        orig_idx = lowered_full.find(matched_text)
        if orig_idx >= 0:
            original_fragment = text[orig_idx:orig_idx + len(matched_text)]
            position = orig_idx
        else:
            # Fallback: use normalized position
            original_fragment = matched_text
            position = start_pos
        
        matches.append(
            {
                "input": original_fragment,
                "metric_id": metric_id,
                "position": position,
            }
        )
        seen.add(metric_id)

    # Always try fuzzy matching for spelling mistakes (even if we have some matches)
    # This helps catch misspelled metrics that weren't found by exact matching
    if True:  # Always try fuzzy matching
        import difflib
        normalized_lower = normalized_text.lower()
        metric_aliases = [alias for alias, _ in _METRIC_ITEMS]
        
        # Try fuzzy matching on individual words and phrases
        tokens = normalized_lower.split()
        
        # First, try to match individual words that might be misspelled metrics
        for token in tokens:
            if len(token) < 3:
                continue
            # Skip common words that aren't metrics
            skip_words = ["what", "is", "the", "show", "me", "get", "tell", "how", "when", "where", "why", "which", "who", 
                         "a", "an", "to", "of", "for", "with", "from", "by", "on", "at", "in", "as", "are", "was", "were"]
            if token in skip_words:
                continue
            
            # Try multiple cutoff levels for better spelling mistake tolerance (more aggressive)
            for cutoff in [0.85, 0.80, 0.75, 0.70, 0.65]:
                close_matches = difflib.get_close_matches(token, metric_aliases, n=10, cutoff=cutoff)
                if close_matches:
                    for alias_match in close_matches:
                        score = difflib.SequenceMatcher(None, token, alias_match).ratio()
                        # Use more lenient thresholds for spelling mistakes
                        threshold = 0.80 if cutoff >= 0.75 else 0.70
                        if score >= threshold:
                            metric_id = METRIC_SYNONYMS.get(alias_match)
                            if metric_id and metric_id not in seen:
                                pos = lowered_full.find(token)
                                if pos < 0:
                                    pos = 0
                                
                                matches.append({
                                    "input": token,
                                    "metric_id": metric_id,
                                    "position": pos,
                                })
                                seen.add(metric_id)
                                break
                    if any(METRIC_SYNONYMS.get(m) in seen for m in close_matches):
                        break
                if any(METRIC_SYNONYMS.get(m) in seen for m in close_matches if METRIC_SYNONYMS.get(m)):
                    break
        
        # Then try multi-word phrases (even if we already have some matches)
        if True:  # Always try phrases
            for window in range(min(4, len(tokens)), 0, -1):
                for start_idx in range(len(tokens) - window + 1):
                    phrase = " ".join(tokens[start_idx : start_idx + window])
                    if len(phrase) < 3:
                        continue
                    
                    # Find close matches with spelling mistake tolerance (try multiple cutoff levels, more aggressive)
                    for cutoff in [0.85, 0.80, 0.75, 0.70, 0.65]:
                        close_matches = difflib.get_close_matches(phrase, metric_aliases, n=10, cutoff=cutoff)
                        if close_matches:
                            for alias_match in close_matches:
                                score = difflib.SequenceMatcher(None, phrase, alias_match).ratio()
                                # Use more lenient thresholds for spelling mistakes
                                threshold = 0.80 if cutoff >= 0.75 else 0.70
                                if score >= threshold:
                                    metric_id = METRIC_SYNONYMS.get(alias_match)
                                    if metric_id and metric_id not in seen:
                                        # Find position in original text
                                        phrase_lower = phrase.lower()
                                        pos = lowered_full.find(phrase_lower)
                                        if pos < 0:
                                            pos = 0
                                        
                                        matches.append({
                                            "input": phrase,
                                            "metric_id": metric_id,
                                            "position": pos,
                                        })
                                        seen.add(metric_id)
                                        break  # Only one match per phrase
                            if any(METRIC_SYNONYMS.get(m) in seen for m in close_matches if METRIC_SYNONYMS.get(m)):
                                break
                        if any(METRIC_SYNONYMS.get(m) in seen for m in close_matches if METRIC_SYNONYMS.get(m)):
                            break
                    if matches:
                        break
                if matches:
                    break
    
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
    #                 sector > market > M&A > IPO > ESG > credit > liquidity > capital_structure >
    #                 economic > regulatory > why > when > relationship > benchmark > 
    #                 optimization > efficiency > summary > conditional > rank > explain > 
    #                 trend > compare > change > lookup
    
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
    
    # Check for sector/industry analysis intent (high priority - sector-specific queries)
    if INTENT_SECTOR_ANALYSIS_PATTERN.search(norm_text):
        return "sector_analysis"
    
    # Check for market analysis intent (high priority - market-specific queries)
    if INTENT_MARKET_ANALYSIS_PATTERN.search(norm_text):
        return "market_analysis"
    
    # Check for M&A intent (high priority - M&A-specific queries)
    if INTENT_MERGER_ACQUISITION_PATTERN.search(norm_text):
        return "merger_acquisition"
    
    # Check for IPO intent (high priority - IPO-specific queries)
    if INTENT_IPO_PATTERN.search(norm_text):
        return "ipo"
    
    # Check for ESG intent (high priority - ESG-specific queries)
    if INTENT_ESG_PATTERN.search(norm_text):
        return "esg"
    
    # Check for credit analysis intent (high priority - credit-specific queries)
    if INTENT_CREDIT_ANALYSIS_PATTERN.search(norm_text):
        return "credit_analysis"
    
    # Check for liquidity analysis intent (high priority - liquidity-specific queries)
    if INTENT_LIQUIDITY_PATTERN.search(norm_text):
        return "liquidity_analysis"
    
    # Check for capital structure intent (high priority - capital structure queries)
    if INTENT_CAPITAL_STRUCTURE_PATTERN.search(norm_text):
        return "capital_structure"
    
    # Check for economic indicators intent (high priority - macroeconomic queries)
    if INTENT_ECONOMIC_INDICATORS_PATTERN.search(norm_text):
        return "economic_indicators"
    
    # Check for regulatory intent (high priority - regulatory queries)
    if INTENT_REGULATORY_PATTERN.search(norm_text):
        return "regulatory"

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
