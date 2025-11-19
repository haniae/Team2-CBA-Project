# How to Make Your Chatbot Answer More Queries

## 🎯 Current Status

Your chatbot already handles **many query types**, but there are opportunities to expand coverage and improve understanding.

> **Important:** Every enhancement in this guide should be implemented as an additive improvement. Preserve the existing behaviour and regression-test core flows (single metric lookup, comparisons, dashboard triggers) after each change. The goal is to increase recall/precision of intent matching without breaking the current happy paths or legacy commands.

---

## 📊 **1. EXPAND INTENT PATTERNS** (High Impact, Easy)

### Current Intent Patterns
Your chatbot recognizes:
- `compare`, `vs`, `versus` → Comparison queries
- `trend`, `over time`, `history` → Trend queries  
- `which`, `highest`, `lowest`, `top`, `best` → Ranking queries
- `explain`, `define`, `tell me about` → Explanation queries

### Add More Patterns

**File:** `src/finanlyzeos_chatbot/parsing/parse.py`

```python
# Add these new intent patterns:

# 1. CAUSAL/REASONING QUERIES
INTENT_WHY_PATTERN = re.compile(
    r"\b(why|what caused|what led to|what's driving|what's behind|"
    r"reason for|explanation for|why did|why is|why are|"
    r"what's the reason|what caused|what factors|what drives)\b"
)

# 2. PREDICTIVE/WHAT-IF QUERIES  
INTENT_WHATIF_PATTERN = re.compile(
    r"\b(what if|what would|what happens if|if.*then|"
    r"scenario|assume|suppose|imagine|project|forecast|predict)\b"
)

# 3. RELATIONSHIP/CORRELATION QUERIES
INTENT_RELATIONSHIP_PATTERN = re.compile(
    r"\b(relationship|correlation|connection|link|"
    r"how.*relate|how.*connect|how.*link|"
    r"does.*affect|does.*impact|does.*influence)\b"
)

# 4. BENCHMARK/COMPARISON QUERIES
INTENT_BENCHMARK_PATTERN = re.compile(
    r"\b(benchmark|vs industry|vs sector|vs peers|"
    r"compared to|relative to|industry average|sector average|"
    r"peer group|how does.*compare|where does.*rank)\b"
)

# 5. TEMPORAL/WHEN QUERIES
INTENT_WHEN_PATTERN = re.compile(
    r"\b(when|what year|what quarter|in which|"
    r"first time|last time|since when|until when|"
    r"what period|which year|which quarter)\b"
)

# 6. CONDITIONAL/IF-THEN QUERIES
INTENT_CONDITIONAL_PATTERN = re.compile(
    r"\b(if.*then|if.*what|what.*if|"
    r"assuming|supposing|given that|"
    r"conditional|hypothetical)\b"
)

# 7. AGGREGATION/SUMMARY QUERIES
INTENT_SUMMARY_PATTERN = re.compile(
    r"\b(summary|overview|summary of|key points|"
    r"main highlights|top|bottom|total|aggregate|"
    r"sum of|average of|combined)\b"
)

# 8. CHANGE/DELTA QUERIES
INTENT_CHANGE_PATTERN = re.compile(
    r"\b(change|delta|difference|increase|decrease|"
    r"growth|decline|improvement|deterioration|"
    r"how much.*change|how much.*increase|how much.*decrease)\b"
)
```

**Update `classify_intent()` function:**

```python
def classify_intent(norm: str, ticker_matches: List, metric_matches: List, periods: List) -> str:
    """Enhanced intent classification with new patterns."""
    
    # Check new patterns first
    if INTENT_WHY_PATTERN.search(norm):
        return "causal_analysis"
    elif INTENT_WHATIF_PATTERN.search(norm):
        return "scenario_analysis"
    elif INTENT_RELATIONSHIP_PATTERN.search(norm):
        return "relationship_analysis"
    elif INTENT_BENCHMARK_PATTERN.search(norm):
        return "benchmark_analysis"
    elif INTENT_WHEN_PATTERN.search(norm):
        return "temporal_query"
    elif INTENT_CONDITIONAL_PATTERN.search(norm):
        return "conditional_analysis"
    elif INTENT_SUMMARY_PATTERN.search(norm):
        return "summary"
    elif INTENT_CHANGE_PATTERN.search(norm):
        return "change_analysis"
    
    # Existing patterns...
    elif INTENT_COMPARE_PATTERN.search(norm):
        return "compare"
    elif INTENT_TREND_PATTERN.search(norm):
        return "trend"
    # ... rest of existing logic
```

---

## 🔍 **2. IMPROVE QUESTION DETECTION** (High Impact, Medium Effort)

### Current Issue
Some questions aren't detected, causing full KPI dumps instead of focused answers.

**File:** `src/finanlyzeos_chatbot/chatbot.py` or `context_builder.py`

```python
# Expand question detection patterns
QUESTION_PATTERNS = [
    # Existing patterns...
    r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would|did|does)\b',
    r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would)\b',
    
    # ADD THESE:
    r'\bwhat\s+(?:happened|changed|improved|declined|increased|decreased)\b',
    r'\bhow\s+(?:has|have|did|does|will|can|should|would)\s+\w+\s+(?:changed|grown|improved|declined)\b',
    r'\bwhen\s+(?:is|are|was|were|did|will|can|should)\b',
    r'\bwhere\s+(?:is|are|can|do|does|did)\b',
    r'\bwho\s+(?:is|are|was|were|has|have|will|can)\b',
    r'\bis\s+\w+\s+(?:more|less|better|worse|higher|lower|greater|smaller)\b',
    r'\bdoes\s+\w+\s+(?:have|own|possess|exceed|surpass)\b',
    r'\bcan\s+(?:you|i|we|they)\b',
    r'\bshould\s+(?:i|we|they|you)\b',
    r'\bwould\s+(?:it|that|this|they)\b',
    r'\bcould\s+(?:you|i|we|they)\b',
    r'\btell\s+me\s+(?:about|why|how|what|when|where)\b',
    r'\bshow\s+me\s+(?:how|what|why|when|where)\b',
    r'\bexplain\s+(?:to\s+me|why|how|what|when|where)\b',
]
```

---

## 🎯 **3. ADD NEW QUERY HANDLERS** (High Impact, Medium Effort)

### Handler Structure

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
def _handle_causal_analysis(self, structured: Dict[str, Any]) -> Optional[str]:
    """Handle 'why' questions - explain causes and drivers."""
    # Example: "Why is Apple's margin declining?"
    ticker = structured.get('tickers', [None])[0]
    metric = structured.get('vmetrics', [None])[0]
    
    if not ticker or not metric:
        return None
    
    # Get historical data
    # Identify drivers (revenue, costs, etc.)
    # Build causal explanation
    return causal_analysis_response

def _handle_benchmark_analysis(self, structured: Dict[str, Any]) -> Optional[str]:
    """Handle benchmark comparisons - vs industry/sector/peers."""
    # Example: "How does Apple's margin compare to industry?"
    ticker = structured.get('tickers', [None])[0]
    metric = structured.get('vmetrics', [None])[0]
    
    if not ticker or not metric:
        return None
    
    # Get sector/industry data
    # Calculate peer averages
    # Build benchmark comparison
    return benchmark_response

def _handle_temporal_query(self, structured: Dict[str, Any]) -> Optional[str]:
    """Handle 'when' questions - find specific time periods."""
    # Example: "When did Tesla first become profitable?"
    ticker = structured.get('tickers', [None])[0]
    metric = structured.get('vmetrics', [None])[0]
    
    if not ticker or not metric:
        return None
    
    # Search historical data
    # Find first/last occurrence
    # Return temporal answer
    return temporal_response

def _handle_change_analysis(self, structured: Dict[str, Any]) -> Optional[str]:
    """Handle change/delta questions - quantify changes."""
    # Example: "How much did Apple's revenue change from 2020 to 2024?"
    tickers = structured.get('tickers', [])
    metrics = structured.get('vmetrics', [])
    periods = structured.get('periods', [])
    
    # Calculate deltas
    # Quantify changes
    # Build change explanation
    return change_analysis_response
```

---

## 💬 **4. IMPROVE ERROR HANDLING & SUGGESTIONS** (High Impact, Easy)

### When Query Fails, Suggest Alternatives

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
def _generate_query_suggestions(self, failed_query: str, error_type: str) -> List[str]:
    """Generate helpful suggestions when query fails."""
    suggestions = []
    
    # Extract what we could understand
    tickers = self._extract_tickers(failed_query)
    metrics = self._extract_metrics(failed_query)
    
    if error_type == "TICKER_NOT_FOUND":
        suggestions = [
            f"Did you mean one of these companies? {', '.join(self._suggest_tickers(tickers[0]))}",
            "Try using the company's ticker symbol (e.g., 'AAPL' for Apple)",
            "Use 'help' to see available companies"
        ]
    elif error_type == "METRIC_NOT_AVAILABLE":
        suggestions = [
            f"Similar metrics available: {', '.join(self._suggest_metrics(metrics[0]))}",
            f"Try asking about: revenue, net_income, gross_margin, etc.",
            "Use 'help' to see all available metrics"
        ]
    elif error_type == "PARSING_ERROR":
        suggestions = [
            "Try rephrasing your question",
            "Example: 'What is Apple's revenue?'",
            "Example: 'Compare Apple vs Microsoft'",
            "Type 'help' for more examples"
        ]
    elif error_type == "NO_DATA":
        suggestions = [
            f"Data might not be available for {tickers[0]}",
            "Try a different time period",
            "Try a different metric"
        ]
    
    return suggestions

def _handle_unknown_query(self, user_input: str) -> str:
    """Handle queries we don't understand with helpful suggestions."""
    # Try to extract partial information
    tickers = self._extract_tickers(user_input)
    metrics = self._extract_metrics(user_input)
    
    response = "I'm not sure how to answer that question yet.\n\n"
    
    if tickers:
        response += f"I found {', '.join(tickers)} in your question. "
        response += f"Try asking:\n"
        response += f"- 'What is {tickers[0]}'s revenue?'\n"
        response += f"- 'Show me {tickers[0]}'s financials'\n"
    
    if metrics:
        response += f"I found '{metrics[0]}' in your question. "
        response += f"Try asking:\n"
        response += f"- 'What is {tickers[0] if tickers else 'Apple'}'s {metrics[0]}?'\n"
    
    response += "\nType 'help' for more examples."
    
    return response
```

---

## 🔄 **5. IMPROVE MULTI-TURN CONVERSATIONS** (Medium Impact, Medium Effort)

### Better Context Handling

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
def _enhance_query_with_context(self, user_input: str, conversation_history: List[Dict]) -> str:
    """Enhance query with context from previous messages."""
    
    # Check for follow-up questions
    follow_up_patterns = [
        r'\b(what about|how about|and|also|plus|'
        r'what.*competitors|what.*peers|what.*industry)\b',
        r'\b(why|how|when|where)\s+(?:is|are|was|were|did|does)\s+that\b',
        r'\b(compare|versus|vs)\s+(?:it|them|that|those)\b',
        r'\b(more|less|further|additional|extra)\s+(?:info|information|details|data)\b',
    ]
    
    is_follow_up = any(re.search(pattern, user_input.lower()) for pattern in follow_up_patterns)
    
    if is_follow_up and conversation_history:
        # Extract context from last message
        last_message = conversation_history[-1]
        last_tickers = self._extract_tickers_from_response(last_message.get('content', ''))
        last_metrics = self._extract_metrics_from_response(last_message.get('content', ''))
        
        # Enhance current query
        if not self._has_tickers(user_input) and last_tickers:
            user_input = f"{user_input} for {', '.join(last_tickers)}"
        
        if not self._has_metrics(user_input) and last_metrics:
            user_input = f"{user_input} about {', '.join(last_metrics)}"
    
    return user_input
```

---

## 📚 **6. EXPAND METRIC SYNONYMS** (High Impact, Easy)

### Add More Metric Variations

**File:** `src/finanlyzeos_chatbot/parsing/ontology.py`

```python
METRIC_SYNONYMS = {
    # Existing...
    'revenue': ['revenue', 'sales', 'top line', 'total revenue', 'net sales'],
    
    # ADD THESE:
    'revenue': [
        'revenue', 'sales', 'top line', 'total revenue', 'net sales',
        'revenues', 'sales revenue', 'total sales', 'gross sales',
        'income', 'turnover', 'business income'
    ],
    'net_income': [
        'net income', 'profit', 'earnings', 'bottom line', 'net profit',
        'net earnings', 'income', 'profit after tax', 'PAT',
        'net', 'earnings after tax', 'EAT'
    ],
    'gross_margin': [
        'gross margin', 'gross profit margin', 'gross margin %',
        'gross profit %', 'gross margin percentage', 'GM %',
        'gross profitability', 'gross margin ratio'
    ],
    'operating_margin': [
        'operating margin', 'operating profit margin', 'OPM',
        'operating margin %', 'operating profitability',
        'EBIT margin', 'operating income margin'
    ],
    'free_cash_flow': [
        'free cash flow', 'FCF', 'free cash', 'operating cash flow',
        'cash from operations', 'CFO', 'operating cash',
        'cash generated', 'cash flow from operations'
    ],
    # Add 20-30 more common variations...
}
```

---

## 🧹 **7. HANDLE SPELLING MISTAKES & TYPOS** (High Impact, Medium Effort)

Users frequently misspell tickers (“Microsft”), company names (“Nividia”), or metrics (“profability”). Harden the parser so these keep working instead of falling back to “ticker not found.”

### a. Normalize and sanitize input earlier

**File:** `src/finanlyzeos_chatbot/parsing/parse.py`

```python
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'")
    text = re.sub(r"[^a-zA-Z0-9\-\s\.&']", " ", text)  # strip emojis / odd glyphs
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()
```

### b. Boost ticker fuzzy matching

**File:** `src/finanlyzeos_chatbot/parsing/alias_builder.py`

```python
from difflib import get_close_matches
# Optional: pip install rapidfuzz for better speed/accuracy
from rapidfuzz import process as fuzz_process

def resolve_tickers_freeform(text: str):
    exact_matches = _direct_lookup(text)
    if exact_matches:
        return exact_matches, []

    lowered = text.lower()
    close_names = get_close_matches(lowered, COMPANY_NAME_INDEX.keys(), n=5, cutoff=0.78)
    if not close_names and fuzz_process:
        candidate, score = fuzz_process.extractOne(lowered, COMPANY_NAME_INDEX.keys())
        if score >= 80:
            close_names = [candidate]

    for name in close_names:
        ticker = COMPANY_NAME_INDEX[name]
        matches.append({"ticker": ticker, "confidence": score / 100})

    return matches, (["Did you mean: {}".format(", ".join({m['ticker']} for m in matches))] if matches else [])
```

### c. Auto-suggest corrections

Hook into error handling (Section 4) so `TICKER_NOT_FOUND` errors surface “Did you mean MSFT?” suggestions and automatically retry once with the top candidate.

```python
def _attempt_autocorrect(self, query: str):
    candidates = self.alias_builder.suggest_close_tickers(query)
    if candidates:
        corrected_query = query.replace(misspelled, candidates[0])
        return corrected_query
    return None

def _handle_user_query(...):
    result = self._process(query)
    if result.error == ErrorCategory.TICKER_NOT_FOUND:
        corrected = self._attempt_autocorrect(query)
        if corrected:
            return self._process(corrected, note="Auto-corrected '{}' → '{}'".format(query, corrected))
```

### d. Metric spelling corrections

Extend `METRIC_SYNONYMS` to include misspelled variants and/or run a `difflib.get_close_matches` check before rejecting a metric outright.

---

## 🎨 **8. ADD QUERY TEMPLATES** (Medium Impact, Easy)

### Pre-built Query Templates

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
QUERY_TEMPLATES = {
    'company_overview': [
        "Tell me about {ticker}",
        "What should I know about {ticker}?",
        "Give me an overview of {ticker}",
        "Analyze {ticker}",
    ],
    'financial_health': [
        "Is {ticker} financially healthy?",
        "What's {ticker}'s financial position?",
        "How strong is {ticker}'s balance sheet?",
        "What's {ticker}'s debt situation?",
    ],
    'growth_analysis': [
        "How fast is {ticker} growing?",
        "What's {ticker}'s growth rate?",
        "Is {ticker} growing?",
        "Show me {ticker}'s growth trends",
    ],
    'profitability': [
        "How profitable is {ticker}?",
        "What's {ticker}'s profit margin?",
        "Is {ticker} making money?",
        "Show me {ticker}'s profitability",
    ],
    'valuation': [
        "How is {ticker} valued?",
        "Is {ticker} overvalued?",
        "What's {ticker}'s P/E ratio?",
        "Show me {ticker}'s valuation metrics",
    ],
}

def _suggest_query_templates(self, ticker: str) -> List[str]:
    """Suggest query templates based on context."""
    suggestions = []
    for category, templates in QUERY_TEMPLATES.items():
        suggestions.append(templates[0].format(ticker=ticker))
    return suggestions
```

---

## 🚀 **9. IMPROVE LLM FALLBACK** (High Impact, Medium Effort)

### When Structured Parsing Fails, Use LLM Intelligently

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
def _handle_llm_fallback(self, user_input: str, structured: Dict[str, Any]) -> str:
    """Enhanced LLM fallback with better context."""
    
    # Build rich context even for unstructured queries
    context_parts = []
    
    # Extract what we could understand
    tickers = structured.get('tickers', [])
    metrics = structured.get('vmetrics', [])
    
    if tickers:
        # Get basic data for tickers
        for ticker in tickers[:3]:  # Limit to 3 tickers
            basic_data = self.analytics_engine.get_ticker_summary(ticker)
            context_parts.append(f"{ticker}: {basic_data}")
    
    # Build context
    context = "\n\n".join(context_parts) if context_parts else ""
    
    # Enhanced prompt
    prompt = f"""You are a financial analyst assistant. Answer the user's question about financial data.

Available context:
{context}

User question: {user_input}

Provide a helpful, data-driven answer. If you don't have specific data, explain what information would be needed.
"""
    
    return self.llm_client.generate(prompt)
```

---

## 📈 **10. ADD QUERY ANALYTICS** (Low Impact, High Value)

### Track What Queries Fail

**File:** `src/finanlyzeos_chatbot/chatbot.py`

```python
def _log_failed_query(self, query: str, error_type: str, structured: Dict[str, Any]):
    """Log failed queries for analysis."""
    failed_query_record = {
        'query': query,
        'error_type': error_type,
        'tickers_found': structured.get('tickers', []),
        'metrics_found': structured.get('vmetrics', []),
        'timestamp': datetime.now().isoformat(),
    }
    
    # Store in database or log file
    database.log_failed_query(self.settings.database_path, failed_query_record)
```

**Then analyze failed queries to:**
- Identify common patterns that fail
- Add new intent patterns
- Expand metric synonyms
- Improve error messages

---

## 🎯 **11. QUICK WINS - Implement These First**

### Priority Order:

1. **Expand Question Patterns** (1-2 hours)
   - Add missing question forms (how has, what happened, etc.)
   - File: `parsing/parse.py` or `chatbot.py`

2. **Add Query Suggestions** (2-3 hours)
   - When query fails, suggest alternatives
   - File: `chatbot.py`

3. **Expand Metric Synonyms** (1 hour)
   - Add common variations
   - File: `parsing/ontology.py`

4. **Improve Error Messages** (1-2 hours)
   - More helpful error responses
   - File: `chatbot.py`

5. **Add New Intent Patterns** (3-4 hours)
   - Causal, benchmark, temporal queries
   - File: `parsing/parse.py`

---

## 📊 **Expected Impact**

After implementing these improvements:

- **+30-40% more queries answered** (from better pattern matching)
- **+20-30% better error handling** (from suggestions)
- **+15-25% better context** (from multi-turn improvements)
- **Overall: 50-70% improvement** in query coverage

---

## 🧪 **Testing Strategy**

1. **Collect real user queries** (from logs or test cases)
2. **Categorize by type** (working vs. failing)
3. **Implement fixes** for failing categories
4. **Test with same queries** to measure improvement
5. **Iterate** on remaining failures

---

## 📝 **Next Steps**

1. Start with **Quick Wins** (#11 above)
2. Add **new intent patterns** for common query types
3. Improve **error handling** with suggestions
4. Expand **metric synonyms** based on failed queries
5. Monitor **failed queries** and iterate

Would you like me to implement any of these improvements? I'd recommend starting with **expanding question patterns** and **adding query suggestions** as they provide the biggest immediate impact.

