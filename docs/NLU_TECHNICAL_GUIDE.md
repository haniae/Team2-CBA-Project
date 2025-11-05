# 🔧 Natural Language Understanding - Technical Guide

## Overview

This document provides technical details for developers working with the BenchmarkOS Chatbot NLU system. It covers architecture, implementation details, extension points, and best practices.

---

## 📚 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [NLU Pipeline](#nlu-pipeline)
3. [Module Descriptions](#module-descriptions)
4. [Integration Points](#integration-points)
5. [Performance Characteristics](#performance-characteristics)
6. [Testing Strategy](#testing-strategy)
7. [Extending the System](#extending-the-system)
8. [Common Patterns](#common-patterns)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Query Input                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Spelling Correction Layer                       │
│  (correction_engine.py, company_corrector.py,               │
│   metric_corrector.py, fuzzy_matcher.py)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Core Parsing Pipeline                       │
│                    (parse.py)                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Intent Classification                            │  │
│  │  2. Entity Extraction (tickers, metrics, time)       │  │
│  │  3. NLU Feature Detection (parallel)                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              NLU Feature Detectors (Parallel)                │
│                                                              │
│  ├─ ComparativeAnalyzer       (comparative.py)              │
│  ├─ TrendAnalyzer              (trends.py)                  │
│  ├─ MetricInferenceEngine      (metric_inference.py)        │
│  ├─ NegationDetector           (negation.py)                │
│  ├─ MultiIntentDetector        (multi_intent.py)            │
│  ├─ FuzzyQuantityDetector      (fuzzy_quantities.py)        │
│  ├─ NaturalFilterDetector      (natural_filters.py)         │
│  ├─ TemporalRelationshipDetector (temporal_relationships.py)│
│  ├─ ConditionalDetector        (conditionals.py)            │
│  ├─ SentimentDetector          (sentiment.py)               │
│  ├─ CompanyGroupDetector       (company_groups.py)          │
│  ├─ AbbreviationDetector       (abbreviations.py)           │
│  └─ QuestionChainDetector      (question_chaining.py)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             Structured Output Generation                     │
│  (intent, entities, features, confidence scores)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 Chatbot Orchestration                        │
│                   (chatbot.py)                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Route based on intent                            │  │
│  │  2. Build context (RAG)                              │  │
│  │  3. Generate response (LLM/structured)               │  │
│  │  4. Update conversation context                      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Response to User                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Modularity**: Each NLU feature is a separate module with clear interface
2. **Singleton Pattern**: Feature detectors are instantiated once, reused across queries
3. **Parallel Processing**: Features are detected independently, enabling parallelization
4. **Confidence Scoring**: All features provide confidence scores for downstream decision-making
5. **Fail-Safe**: Missing or failed feature detection doesn't break the pipeline
6. **Performance-First**: Optimized for sub-100ms parsing on typical queries

---

## NLU Pipeline

### Phase 1: Preprocessing

**File**: `src/benchmarkos_chatbot/spelling/correction_engine.py`

```python
def correct_query(query: str) -> dict:
    """
    Entry point for spelling correction.
    
    Returns:
    {
        "corrected_text": str,
        "corrections": List[Dict],  # What was corrected
        "confidence": float          # Overall confidence
    }
    """
```

**Process**:
1. Tokenize query (handling possessives, punctuation)
2. Check each token against:
   - Known company names/tickers
   - Known metric names
   - Common financial terms
3. Apply fuzzy matching (Levenshtein, Soundex, Jaro-Winkler)
4. Calculate confidence scores
5. Apply corrections above confidence threshold

### Phase 2: Core Parsing

**File**: `src/benchmarkos_chatbot/parsing/parse.py`

```python
def parse_to_structured(query: str, conversation_history: List = None) -> dict:
    """
    Main parsing entry point.
    
    Returns structured representation of query including:
    - intent: str
    - tickers: List[str]
    - metrics: List[str]
    - time_periods: List[Dict]
    - comparison: Dict (if comparative)
    - trend: Dict (if trend-related)
    - negations: List[Dict]
    - multi_intent: Dict (if multiple intents)
    - ... and 10 more feature outputs
    """
```

**Process**:
1. **Intent Classification**: Determine primary intent (question, compare, lookup, etc.)
2. **Entity Extraction**:
   - Tickers: `_detect_tickers()`, `_detect_freeform_tickers()`
   - Metrics: Match against `METRIC_SYNONYMS` from `ontology.py`
   - Time: `parse_periods()` from `time_grammar.py`
3. **Feature Detection**: Call all 14 feature detectors in parallel
4. **Structured Assembly**: Combine all outputs into unified structure

### Phase 3: Feature Detection

Each feature detector follows this interface:

```python
class FeatureDetector:
    def detect(self, query: str, **context) -> Dict:
        """
        Detect feature in query.
        
        Args:
            query: User query string
            **context: Optional context (previous queries, etc.)
        
        Returns:
            {
                "detected": bool,
                "confidence": float,
                "data": Dict  # Feature-specific data
            }
        """
```

**All detectors are singletons** to avoid re-compilation of regex patterns:

```python
_COMPARATIVE_ANALYZER = ComparativeAnalyzer()
_TREND_ANALYZER = TrendAnalyzer()
# ... etc
```

### Phase 4: Response Generation

**File**: `src/benchmarkos_chatbot/chatbot.py`

**Process**:
1. **Routing Decision**:
   - If `intent == "question"` → LLM conversational response
   - If `intent == "compare"` → Structured comparison
   - If `intent == "lookup"` → Data retrieval
   - Etc.

2. **Context Building** (for LLM):
   - Retrieve relevant financial data
   - Format into context string
   - Include conversation history

3. **Response Generation**:
   - LLM: Call OpenAI API with context
   - Structured: Format data into table/chart

4. **Context Update**:
   - Store tickers, metrics, intent in `_conversation_context`
   - Enable follow-up question resolution

---

## Module Descriptions

### 1. Spelling Correction

**Location**: `src/benchmarkos_chatbot/spelling/`

#### `correction_engine.py`
- **Purpose**: Orchestrates spelling correction across all token types
- **Key Functions**:
  - `correct_query(query)`: Main entry point
  - `_tokenize(text)`: Smart tokenization (handles possessives)
  - `_calculate_context_boost()`: Boosts confidence based on surrounding words

#### `company_corrector.py`
- **Purpose**: Corrects company names and ticker symbols
- **Data Source**: Company alias map from `alias_builder.py`
- **Techniques**: Levenshtein (typos), Soundex (phonetic), Jaro-Winkler (prefix-weighted)

#### `metric_corrector.py`
- **Purpose**: Corrects financial metric names
- **Data Source**: `METRIC_SYNONYMS` from `ontology.py`
- **Special Handling**: Multi-word metrics (e.g., "profit margin")

#### `fuzzy_matcher.py`
- **Purpose**: Low-level fuzzy matching utilities
- **Algorithms**:
  - `levenshtein_ratio()`: Edit distance
  - `soundex()`: Phonetic encoding
  - `jaro_winkler()`: Prefix-weighted similarity

**Configuration**:
```python
# Minimum confidence to apply correction
MIN_CONFIDENCE = 0.75

# Levenshtein threshold
LEVENSHTEIN_THRESHOLD = 0.80

# Soundex threshold
SOUNDEX_THRESHOLD = 0.90
```

---

### 2. Comparative Language

**File**: `src/benchmarkos_chatbot/parsing/comparative.py`

**Class**: `ComparativeAnalyzer`

**Detection Patterns**:
- **COMPARATIVE_PATTERNS**: "vs", "versus", "compared to", "better than"
- **SUPERLATIVE_PATTERNS**: "best", "worst", "highest", "lowest"
- **RELATIVE_PATTERNS**: "twice as much", "3x larger"
- **DIRECTIONAL_PATTERNS**: "outperforming", "underperforming", "beating"
- **QUESTION_PATTERNS**: "which has higher", "does X have more than Y"

**Output Structure**:
```python
{
    "detected": True,
    "confidence": 0.92,
    "comparison_type": "QUESTION",  # or BASIC, SUPERLATIVE, etc.
    "dimensions": ["revenue", "profit"],
    "magnitude": "significant",      # if detected
    "direction": "positive"          # if directional
}
```

**Key Methods**:
- `detect_comparison(query)`: Main detection
- `_detect_comparison_type(query)`: Classify type
- `_extract_dimensions(query)`: Find what's being compared
- `_detect_magnitude(query)`: Find magnitude keywords

---

### 3. Trend Direction Language

**File**: `src/benchmarkos_chatbot/parsing/trends.py`

**Class**: `TrendAnalyzer`

**Detection Patterns**:
- **POSITIVE_PATTERNS**: "growing", "rising", "improving", "increasing"
- **NEGATIVE_PATTERNS**: "declining", "falling", "deteriorating", "decreasing"
- **STABLE_PATTERNS**: "steady", "flat", "consistent", "stable"
- **VOLATILE_PATTERNS**: "volatile", "erratic", "fluctuating"
- **VELOCITY_PATTERNS**: "accelerating", "decelerating", "rapidly", "slowly"
- **MAGNITUDE_PATTERNS**: "dramatically", "slightly", "significantly"

**Output Structure**:
```python
{
    "detected": True,
    "confidence": 0.88,
    "direction": "POSITIVE",      # POSITIVE, NEGATIVE, STABLE, VOLATILE
    "velocity": "accelerating",   # if detected
    "magnitude": "significant",   # if detected
    "timeframe": "recent",        # if detected
    "dimensions": ["revenue"]     # auto-detected
}
```

**Key Methods**:
- `detect_trend(query)`: Main detection
- `_detect_direction(query)`: Find trend direction
- `_detect_velocity(query)`: Find speed of change
- `_extract_dimension(query)`: Auto-detect metric

---

### 4. Contextual Metric Inference

**File**: `src/benchmarkos_chatbot/parsing/metric_inference.py`

**Class**: `MetricInferenceEngine`

**Detection Patterns**: 70+ patterns across 15 metric types

**Pattern Categories**:
1. **Value Patterns**: "$100M", "20%", "$50/share"
2. **Verb Patterns**: "earning", "trading at", "valued at"
3. **Context Patterns**: Financial terms near values

**Output Structure**:
```python
{
    "detected": True,
    "inferred_metrics": [
        {
            "metric_type": "revenue",
            "value": 100000000,
            "operator": ">",
            "confidence": 0.90,
            "matched_pattern": "over $100M"
        }
    ]
}
```

**Key Methods**:
- `infer_metrics(query)`: Main inference
- `_parse_numeric_value(text)`: Extract numbers
- `_calculate_confidence(...)`: Context-aware scoring

---

### 5. Negation Handling

**File**: `src/benchmarkos_chatbot/parsing/negation.py`

**Class**: `NegationDetector`

**Detection Patterns**: 50+ patterns across 3 types

**Pattern Types**:
1. **BASIC**: "not", "without", "no", "never"
2. **EXCLUSION**: "except", "excluding", "but", "other than"
3. **THRESHOLD**: "under", "below", "less than", "no more than"

**Output Structure**:
```python
{
    "detected": True,
    "negations": [
        {
            "type": "EXCLUSION",
            "scope": "tech sector",
            "pattern": "except",
            "confidence": 0.88
        }
    ]
}
```

**Key Methods**:
- `detect_negations(query)`: Main detection
- `_extract_scope(query, match)`: Find what's negated
- `_to_filter_transformation(...)`: Convert to filter logic

---

### 6. Multi-Intent Queries

**File**: `src/benchmarkos_chatbot/parsing/multi_intent.py`

**Class**: `MultiIntentDetector`

**Detection Patterns**: 30+ patterns across 5 types

**Conjunction Types** (Priority Order):
1. **THEN**: "then", "and then", "after that"
2. **ALSO**: "also", "additionally", "furthermore"
3. **AND**: "and", "as well as"
4. **OR**: "or", "versus", "either"
5. **COMMA**: ", "

**Output Structure**:
```python
{
    "detected": True,
    "sub_intents": [
        {
            "text": "show me Apple's revenue",
            "intent": "lookup",
            "confidence": 0.92
        },
        {
            "text": "compare it to Microsoft",
            "intent": "compare",
            "confidence": 0.88
        }
    ],
    "primary_conjunction": "THEN"
}
```

**Key Methods**:
- `detect_multi_intent(query)`: Main detection
- `_find_conjunctions(query)`: Locate split points
- `_classify_sub_intent(text)`: Classify each part

---

### 7. Fuzzy Quantities & Approximations

**File**: `src/benchmarkos_chatbot/parsing/fuzzy_quantities.py`

**Class**: `FuzzyQuantityDetector`

**Detection Patterns**:
1. **APPROXIMATION**: "around", "roughly", "about"
2. **UPPER_THRESHOLD**: "over", "above", "more than"
3. **LOWER_THRESHOLD**: "under", "below", "less than"
4. **RANGE**: "between X and Y", "X-Y"

**Output Structure**:
```python
{
    "detected": True,
    "quantities": [
        {
            "type": "approximation",
            "value": 1000000000,
            "tolerance": 0.10,  # ±10%
            "unit": "dollars",
            "confidence": 0.90
        }
    ]
}
```

**Key Methods**:
- `detect_fuzzy_quantities(query)`: Main detection
- `_parse_numeric_value(text)`: Extract numbers
- `_infer_tolerance(modifier)`: Calculate tolerance

---

### 8. Natural Filtering

**File**: `src/benchmarkos_chatbot/parsing/natural_filters.py`

**Class**: `NaturalFilterDetector`

**Filter Types**: 80+ patterns across 6 categories

**Categories**:
1. **SECTOR**: tech, healthcare, finance, energy, consumer, industrial, telecom, real estate, materials, media
2. **QUALITY**: high-quality, blue chip, investment-grade
3. **RISK**: low-risk, safe, volatile, high-risk
4. **SIZE**: large-cap, small-cap, mega-cap, mid-cap
5. **PERFORMANCE**: high-performing, top performers, underperforming
6. **VALUATION**: undervalued, overvalued, fairly valued

**Output Structure**:
```python
{
    "detected": True,
    "filters": [
        {
            "type": "SECTOR",
            "value": "technology",
            "confidence": 0.95
        },
        {
            "type": "SIZE",
            "value": "large-cap",
            "confidence": 0.88
        }
    ]
}
```

**Key Methods**:
- `detect_filters(query)`: Main detection
- `_deduplicate_filters(filters)`: Remove duplicates
- `to_structured_filters(filters)`: Convert to query filters

---

### 9. Temporal Relationships

**File**: `src/benchmarkos_chatbot/parsing/temporal_relationships.py`

**Class**: `TemporalRelationshipDetector`

**Relationship Types**:
1. **BEFORE**: "before", "prior to", "preceding"
2. **AFTER**: "after", "following", "since"
3. **DURING**: "during", "throughout", "within"
4. **WITHIN**: "within", "in", "over"
5. **SINCE**: "since", "from"
6. **UNTIL**: "until", "up to", "through"
7. **BETWEEN**: "between", "from X to Y"

**Event Detection**: Pandemic, Financial Crisis, Dot-Com Bubble, Recession, Crisis

**Output Structure**:
```python
{
    "detected": True,
    "relationships": [
        {
            "type": "DURING",
            "reference": "pandemic",
            "resolved_timeframe": {
                "start": "2020-Q1",
                "end": "2023-Q4"
            },
            "confidence": 0.92
        }
    ]
}
```

**Key Methods**:
- `detect_temporal_relationships(query)`: Main detection
- `_extract_time_reference(match)`: Get time reference
- `_resolve_event_timeframe(event)`: Map event to dates

---

### 10. Conditional Statements

**File**: `src/benchmarkos_chatbot/parsing/conditionals.py`

**Class**: `ConditionalDetector`

**Conditional Types**:
1. **IF_THEN**: "if X then Y", "if X, Y"
2. **WHEN_THEN**: "when X, Y"
3. **UNLESS**: "unless X", "X unless Y"
4. **WHENEVER**: "whenever X"

**Operator Detection**: 50+ operator variations (symbolic + natural language)

**Output Structure**:
```python
{
    "detected": True,
    "conditionals": [
        {
            "type": "IF_THEN",
            "condition": "revenue > $1B",
            "action": "show me",
            "operator": ">",
            "threshold": 1000000000,
            "confidence": 0.90
        }
    ]
}
```

**Key Methods**:
- `detect_conditionals(query)`: Main detection
- `_parse_operator(text)`: Extract comparison operator
- `_extract_condition(match)`: Get condition clause

---

### 11. Sentiment Detection

**File**: `src/benchmarkos_chatbot/parsing/sentiment.py`

**Class**: `SentimentDetector`

**Sentiment Categories**:
1. **POSITIVE**: Strong (outstanding, exceptional) vs Mild (good, decent)
2. **NEGATIVE**: Strong (terrible, disastrous) vs Mild (poor, weak)
3. **BULLISH/BEARISH**: Financial-specific sentiment
4. **NEUTRAL**: Balanced, objective terms

**Modifiers**:
- **Intensifiers**: "very", "extremely", "incredibly"
- **Diminishers**: "somewhat", "slightly", "a bit"

**Output Structure**:
```python
{
    "detected": True,
    "polarity": "POSITIVE",    # POSITIVE, NEGATIVE, NEUTRAL
    "intensity": "STRONG",     # STRONG, MODERATE, MILD
    "financial": "BULLISH",    # BULLISH, BEARISH, or None
    "confidence": 0.88
}
```

**Key Methods**:
- `detect_sentiment(query)`: Main detection
- `_detect_polarity(query)`: Find sentiment direction
- `_detect_intensity(query)`: Find strength

---

### 12. Company Groups

**File**: `src/benchmarkos_chatbot/parsing/company_groups.py`

**Class**: `CompanyGroupDetector`

**Group Types**:
1. **TECH_ACRONYM**: FAANG, MAMAA, Magnificent 7, MATANA, GRANOLAS
2. **INDUSTRY**: Big Tech, Cloud, Chip Makers, Big Auto, Big Oil, Big Pharma, Big Banks
3. **INDEX**: S&P 500 Leaders, Dow 30
4. **CATEGORY**: Dividend Aristocrats, Growth Stocks, Value Stocks, ESG Leaders

**Output Structure**:
```python
{
    "detected": True,
    "groups": [
        {
            "name": "FAANG",
            "type": "TECH_ACRONYM",
            "tickers": ["META", "AAPL", "AMZN", "NFLX", "GOOGL"],
            "confidence": 0.98
        }
    ]
}
```

**Key Methods**:
- `detect_groups(query)`: Main detection
- `_expand_group(group_name)`: Get constituent tickers

---

### 13. Abbreviations & Acronyms

**File**: `src/benchmarkos_chatbot/parsing/abbreviations.py`

**Class**: `AbbreviationDetector`

**Abbreviation Types**:
1. **TIME_PERIOD**: YoY, QoQ, MoM, YTD, QTD, MTD
2. **METRIC**: P/E, ROE, ROA, EBITDA, EPS, FCF, CAGR, ARR, MRR
3. **BUSINESS**: CEO, CFO, IPO, M&A, VC, PE, SaaS, B2B, B2C
4. **GENERAL**: NYSE, NASDAQ, ETF, GAAP, SEC

**Output Structure**:
```python
{
    "detected": True,
    "abbreviations": [
        {
            "abbrev": "YoY",
            "expansion": "Year-over-Year",
            "category": "time_period",
            "confidence": 0.95
        }
    ]
}
```

**Key Methods**:
- `detect_abbreviations(query)`: Main detection
- `_expand_abbreviation(abbrev)`: Get full form

---

### 14. Question Chaining

**File**: `src/benchmarkos_chatbot/parsing/question_chaining.py`

**Class**: `QuestionChainDetector`

**Chain Types**:
1. **SEQUENTIAL**: "next", "then", "after that"
2. **COMPARATIVE**: "how does that compare", "versus"
3. **EXPLORATORY**: "what about", "how about"
4. **CONTINUATION**: "and", "also", "plus"
5. **ELABORATION**: "tell me more", "expand on"

**Output Structure**:
```python
{
    "detected": True,
    "chain_type": "SEQUENTIAL",
    "requires_context": True,     # Does it need previous query?
    "context_requirements": {
        "tickers": True,
        "metrics": False,
        "intent": False
    },
    "confidence": 0.90
}
```

**Key Methods**:
- `detect_chain(query, conversation_history)`: Main detection
- `_determine_context_requirements(chain_type)`: What context needed

---

## Integration Points

### Adding a New NLU Feature

**Step 1: Create Feature Module**

Create `src/benchmarkos_chatbot/parsing/my_feature.py`:

```python
import re
from typing import Dict, List

class MyFeatureDetector:
    def __init__(self):
        # Compile patterns once (performance)
        self.PATTERNS = {
            "pattern1": re.compile(r'regex1', re.IGNORECASE),
            "pattern2": re.compile(r'regex2', re.IGNORECASE),
        }
    
    def detect_my_feature(self, query: str, **context) -> Dict:
        """
        Detect my feature in query.
        
        Args:
            query: User query string
            **context: Optional context
        
        Returns:
            {
                "detected": bool,
                "confidence": float,
                "data": Dict  # Feature-specific
            }
        """
        # Detection logic here
        detected = False
        confidence = 0.0
        data = {}
        
        for name, pattern in self.PATTERNS.items():
            if pattern.search(query):
                detected = True
                confidence = self._calculate_confidence(query, name)
                data[name] = True
        
        return {
            "detected": detected,
            "confidence": confidence,
            "data": data
        }
    
    def _calculate_confidence(self, query: str, pattern_name: str) -> float:
        """Calculate confidence score."""
        base_confidence = 0.85
        
        # Add boosters
        if "explicit_keyword" in query.lower():
            base_confidence += 0.10
        
        return min(base_confidence, 1.0)
```

**Step 2: Integrate into Parse Pipeline**

Edit `src/benchmarkos_chatbot/parsing/parse.py`:

```python
# At top of file
from benchmarkos_chatbot.parsing.my_feature import MyFeatureDetector

# Create singleton
_MY_FEATURE_DETECTOR = MyFeatureDetector()

# In parse_to_structured()
def parse_to_structured(query: str, conversation_history: List = None) -> dict:
    # ... existing code ...
    
    # Add feature detection
    my_feature_result = _MY_FEATURE_DETECTOR.detect_my_feature(
        query,
        tickers=tickers,
        metrics=metrics
    )
    
    # Add to structured output
    structured = {
        # ... existing fields ...
        "my_feature": my_feature_result,
    }
    
    return structured
```

**Step 3: Create Tests**

Create `tests/test_my_feature.py`:

```python
import pytest
from benchmarkos_chatbot.parsing.my_feature import MyFeatureDetector

@pytest.fixture
def detector():
    return MyFeatureDetector()

def test_basic_detection(detector):
    query = "test query with my feature"
    result = detector.detect_my_feature(query)
    
    assert result["detected"] is True
    assert result["confidence"] > 0.8
    assert "data" in result

def test_no_detection(detector):
    query = "query without the feature"
    result = detector.detect_my_feature(query)
    
    assert result["detected"] is False

def test_confidence_scoring(detector):
    query = "query with explicit_keyword"
    result = detector.detect_my_feature(query)
    
    assert result["confidence"] > 0.9  # Should be boosted
```

**Step 4: Integrate into Chatbot Logic** (if needed)

Edit `src/benchmarkos_chatbot/chatbot.py`:

```python
def ask(self, query: str) -> str:
    # ... existing code ...
    
    # Use feature in routing/response
    if parsed["my_feature"]["detected"]:
        # Special handling for my feature
        return self._handle_my_feature(parsed, query)
    
    # ... rest of logic ...
```

---

## Performance Characteristics

### Parsing Time Breakdown

**Measured on typical queries** (26-68ms total):

| Component | Time | % of Total |
|-----------|------|------------|
| Ticker Resolution | 8-25ms | 30-40% |
| Intent Classification | 2-5ms | 8-10% |
| Entity Extraction | 3-8ms | 12-15% |
| Feature Detection (all 14) | 8-20ms | 30-35% |
| Assembly | 1-3ms | 4-6% |
| Overhead | 2-7ms | 8-12% |

### Optimization Techniques Applied

1. **Singleton Pattern**: Regex patterns compiled once
2. **Pre-filtering**: Reduce fuzzy matching candidates by 95%
3. **Early Exit**: Stop at "good enough" matches
4. **Candidate Limiting**: Cap expensive operations
5. **Lazy Loading**: Only load data when needed

### Performance Targets

| Query Type | Target | Actual | Status |
|------------|--------|--------|--------|
| Simple | <50ms | 12ms | ✅ 4.2x better |
| Typical | <100ms | 26-68ms | ✅ 1.5-3.8x better |
| Complex | <200ms | 68-117ms | ✅ 1.7-2.9x better |
| Very Complex | <300ms | 117-167ms | ✅ 1.8-2.6x better |

### Memory Usage

- **Startup Memory**: ~150MB (including all NLU modules)
- **Per-Query Memory**: ~2-5MB (transient)
- **Pattern Storage**: ~10MB (compiled regexes)
- **Company/Metric Data**: ~50MB (alias maps, synonyms)

---

## Testing Strategy

### Test Structure

```
tests/
├── test_spelling_correction.py        # 45 tests
├── test_comparative_language.py       # 58 tests
├── test_trend_direction.py            # 57 tests
├── test_metric_inference.py           # 49 tests
├── test_negation_handling.py          # 46 tests
├── test_multi_intent.py               # 49 tests
├── test_fuzzy_quantities.py           # 53 tests
├── test_natural_filters.py            # 58 tests
├── test_temporal_relationships.py     # 54 tests
├── test_conditionals.py               # 53 tests
├── test_sentiment.py                  # 51 tests
├── test_company_groups.py             # 45 tests
├── test_abbreviations.py              # 56 tests
├── test_question_chaining.py          # 46 tests
├── test_integration_e2e.py            # 23 tests
└── test_performance_benchmarks.py     # 11 tests
```

**Total**: 790 tests, 100% passing

### Test Categories

1. **Unit Tests**: Test individual feature detectors
2. **Integration Tests**: Test feature interactions
3. **Performance Tests**: Measure parsing speed
4. **Regression Tests**: Prevent breaking changes

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific feature
pytest tests/test_comparative_language.py -v

# Performance tests
pytest tests/test_performance_benchmarks.py -v

# Integration tests
pytest tests/test_integration_e2e.py -v

# With coverage
pytest tests/ --cov=src/benchmarkos_chatbot --cov-report=html
```

### Test Pattern

```python
import pytest
from benchmarkos_chatbot.parsing.feature import FeatureDetector

@pytest.fixture
def detector():
    """Reusable detector instance."""
    return FeatureDetector()

class TestBasicDetection:
    """Group related tests."""
    
    def test_positive_case(self, detector):
        """Test when feature should be detected."""
        query = "query with feature"
        result = detector.detect(query)
        
        assert result["detected"] is True
        assert result["confidence"] > 0.8
        assert "data" in result
    
    def test_negative_case(self, detector):
        """Test when feature should NOT be detected."""
        query = "query without feature"
        result = detector.detect(query)
        
        assert result["detected"] is False

class TestEdgeCases:
    """Test boundary conditions."""
    
    def test_empty_query(self, detector):
        result = detector.detect("")
        assert result["detected"] is False
    
    def test_long_query(self, detector):
        query = "word " * 1000
        result = detector.detect(query)
        # Should handle gracefully
        assert isinstance(result, dict)
```

---

## Common Patterns

### Pattern 1: Regex-Based Detection

```python
import re

class Detector:
    def __init__(self):
        # Compile once for performance
        self.PATTERNS = {
            "basic": re.compile(r'\bkeyword\b', re.IGNORECASE),
            "advanced": re.compile(
                r'\b(option1|option2|option3)\s+(?:target)\b',
                re.IGNORECASE
            ),
        }
    
    def detect(self, query: str) -> Dict:
        for name, pattern in self.PATTERNS.items():
            match = pattern.search(query)
            if match:
                return self._process_match(match, name)
        return {"detected": False}
```

### Pattern 2: Confidence Scoring

```python
def _calculate_confidence(self, query: str, base: float = 0.85) -> float:
    """
    Context-aware confidence scoring.
    
    Base confidence: 0.85
    Boosters:
    - Explicit keywords: +0.05-0.10
    - Financial context: +0.05
    - Multiple signals: +0.05
    
    Penalties:
    - Ambiguous context: -0.10
    - False positive risk: -0.15
    """
    confidence = base
    
    # Boosters
    if self._has_explicit_keyword(query):
        confidence += 0.10
    if self._has_financial_context(query):
        confidence += 0.05
    if self._has_multiple_signals(query):
        confidence += 0.05
    
    # Penalties
    if self._is_ambiguous(query):
        confidence -= 0.10
    if self._is_false_positive_risk(query):
        confidence -= 0.15
    
    return max(0.0, min(confidence, 1.0))
```

### Pattern 3: False Positive Prevention

```python
class Detector:
    def __init__(self):
        self.FALSE_POSITIVE_PATTERNS = [
            re.compile(r'\bwhat\s+(?:is|are|does)\b', re.IGNORECASE),
            re.compile(r'\bdefine\b', re.IGNORECASE),
            re.compile(r'\bexplain\b', re.IGNORECASE),
        ]
    
    def detect(self, query: str) -> Dict:
        # Check false positives first
        if self._is_false_positive(query):
            return {"detected": False}
        
        # Then do actual detection
        return self._do_detection(query)
    
    def _is_false_positive(self, query: str) -> bool:
        """Check if query is a meta-question about the feature."""
        return any(
            pattern.search(query)
            for pattern in self.FALSE_POSITIVE_PATTERNS
        )
```

### Pattern 4: Deduplication

```python
def _deduplicate(self, items: List[Dict]) -> List[Dict]:
    """Remove duplicate detections."""
    seen = set()
    unique = []
    
    for item in items:
        # Create unique key
        key = (item["type"], item["value"].lower())
        
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    return unique
```

### Pattern 5: Priority Ordering

```python
def _prioritize_patterns(self, query: str) -> List[Dict]:
    """
    Apply patterns in priority order.
    Higher priority patterns can override lower ones.
    """
    # Define priority order
    PRIORITY_ORDER = [
        ("specific", self.SPECIFIC_PATTERNS),
        ("general", self.GENERAL_PATTERNS),
        ("fallback", self.FALLBACK_PATTERNS),
    ]
    
    results = []
    for priority_name, patterns in PRIORITY_ORDER:
        for name, pattern in patterns.items():
            match = pattern.search(query)
            if match:
                results.append({
                    "priority": priority_name,
                    "pattern": name,
                    "match": match
                })
    
    # Sort by priority, return highest
    results.sort(key=lambda x: PRIORITY_ORDER.index(
        next(p for p in PRIORITY_ORDER if p[0] == x["priority"])
    ))
    
    return results
```

---

## Troubleshooting

### Issue: Feature Not Detected

**Symptoms**: Query should trigger feature, but `detected` is `False`

**Debug Steps**:
1. Check pattern matches:
   ```python
   detector = MyFeatureDetector()
   query = "test query"
   
   # Print all patterns and matches
   for name, pattern in detector.PATTERNS.items():
       match = pattern.search(query)
       print(f"{name}: {match}")
   ```

2. Check false positive filters:
   ```python
   if detector._is_false_positive(query):
       print("Blocked by false positive filter")
   ```

3. Check confidence threshold:
   ```python
   confidence = detector._calculate_confidence(query, name)
   print(f"Confidence: {confidence}")
   # Is it above MIN_CONFIDENCE?
   ```

### Issue: Wrong Feature Detected

**Symptoms**: Feature detected when it shouldn't be

**Debug Steps**:
1. Review pattern specificity - too broad?
2. Add false positive filters
3. Increase confidence threshold
4. Add negative test cases

### Issue: Low Confidence Scores

**Symptoms**: Feature detected but confidence too low

**Debug Steps**:
1. Review confidence calculation logic
2. Add context boosters for your use case
3. Reduce penalties that don't apply
4. Ensure patterns are specific enough

### Issue: Slow Performance

**Symptoms**: Parsing takes >100ms on typical queries

**Debug Steps**:
1. Profile with cProfile:
   ```bash
   python -m cProfile -s cumtime -m pytest tests/test_my_feature.py
   ```

2. Check for:
   - Uncompiled regexes (compile in `__init__`)
   - Expensive operations in loops
   - Large data structure traversals
   - Unnecessary string operations

3. Apply optimizations:
   - Pre-filter candidates before expensive operations
   - Use sets/dicts instead of lists for lookups
   - Add early exit conditions
   - Cache repeated computations

### Issue: Test Failures After Changes

**Symptoms**: Tests pass locally but fail in CI, or vice versa

**Debug Steps**:
1. Check for:
   - Regex flags (IGNORECASE, MULTILINE)
   - Locale-dependent behavior
   - Timing-dependent logic
   - Randomness without seed

2. Run full test suite:
   ```bash
   pytest tests/ -v --tb=short
   ```

3. Check integration with other features:
   ```bash
   pytest tests/test_integration_e2e.py -v
   ```

---

## Best Practices

### 1. Pattern Design

✅ **Do**:
- Use word boundaries (`\b`) for precision
- Make patterns case-insensitive (`re.IGNORECASE`)
- Group related patterns by priority
- Test with real-world queries

❌ **Don't**:
- Make patterns too greedy (e.g., `.*`)
- Forget special character escaping
- Over-complicate with nested groups
- Hardcode values that should be configurable

### 2. Confidence Scoring

✅ **Do**:
- Start with conservative base (0.85)
- Add small, well-justified boosters (+0.05-0.10)
- Apply meaningful penalties (-0.10-0.15)
- Clamp to [0.0, 1.0] range

❌ **Don't**:
- Use arbitrary confidence values
- Make all detections high confidence (>0.95)
- Ignore context in scoring
- Skip validation against test cases

### 3. Testing

✅ **Do**:
- Test positive and negative cases
- Test edge cases (empty, long, special chars)
- Test integration with other features
- Include real-world query examples

❌ **Don't**:
- Only test happy path
- Hardcode expected values (use variables)
- Skip performance tests
- Ignore flaky tests

### 4. Performance

✅ **Do**:
- Compile regexes in `__init__`
- Use singletons for detector instances
- Pre-filter before expensive operations
- Profile before optimizing

❌ **Don't**:
- Re-compile patterns on every call
- Perform expensive ops unnecessarily
- Optimize prematurely without data
- Sacrifice correctness for speed

### 5. Documentation

✅ **Do**:
- Document pattern purposes
- Explain confidence scoring logic
- Provide usage examples
- Keep docs up to date

❌ **Don't**:
- Leave magic numbers unexplained
- Skip docstrings
- Use unclear variable names
- Forget to update after changes

---

## Version History

### v1.0 (November 2025)
- Initial release with 14 NLU features
- 790 comprehensive tests (100% passing)
- Performance optimization (12-167ms parsing)
- Full integration with chatbot system

---

**Maintained By**: BenchmarkOS Team  
**Last Updated**: November 2025  
**Next Review**: Quarterly or after major changes

