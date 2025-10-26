# Enhanced Routing System

**Status:** ✅ Implemented (Optional, Off by Default)

## Overview

The enhanced routing system provides **deterministic intent classification** on top of your existing parser, without changing any behavior by default.

## Key Features

- ✅ **Non-invasive** - Wraps existing parsing, doesn't replace it
- ✅ **Backward compatible** - Off by default, zero breaking changes
- ✅ **Confidence-based** - Low-confidence queries fall back to LLM
- ✅ **Dashboard control** - Explicit control over when dashboards are built
- ✅ **Preserves aesthetic** - Uses all existing formatting methods

## How It Works

### Without Enhanced Routing (Default)

```
User: "Show Apple KPIs"
  ↓
parse_to_structured() → intent="lookup"
  ↓
_handle_structured_metrics()
  ↓
Single ticker → build_cfi_dashboard_payload()
  ↓
Returns: "Displaying financial dashboard for Apple Inc. (AAPL)."
```

### With Enhanced Routing (Opt-in)

```
User: "Show Apple KPIs"
  ↓
parse_to_structured() → intent="lookup"
  ↓
enhance_structured_parse() → EnhancedIntent.METRICS_SINGLE
  ↓
(Same flow as above - no change to output)
  ↓
Returns: "Displaying financial dashboard for Apple Inc. (AAPL)."
```

## Enabling Enhanced Routing

### Option 1: Environment Variable

```bash
export ENABLE_ENHANCED_ROUTING=true
```

### Option 2: .env File

```bash
# Add to your .env file
ENABLE_ENHANCED_ROUTING=true
```

### Option 3: Programmatically

```python
from benchmarkos_chatbot.config import Settings

settings = Settings(
    enable_enhanced_routing=True,
    # ... other settings ...
)

chatbot = BenchmarkOSChatbot.create(settings=settings)
```

## Enhanced Intent Types

The router classifies queries into these intents:

| Intent | Example | Dashboard | Output |
|--------|---------|-----------|--------|
| `METRICS_SINGLE` | "Show Apple KPIs" | Auto (existing logic) | Dashboard or text |
| `METRICS_MULTI` | "Show Apple and Microsoft KPIs" | Never | Text table only |
| `COMPARE_TWO` | "Compare Apple vs Microsoft" | Never | Text table only |
| `COMPARE_MULTI` | "Compare Apple, Microsoft, Google" | Never | Text table only |
| `FACT_SINGLE` | "fact AAPL 2022" | Never | Legacy handler |
| `SCENARIO` | "scenario AAPL Bull" | Never | Legacy handler |
| `INGEST` | "ingest AAPL 5" | Never | Legacy handler |
| `AUDIT` | "audit AAPL 2022" | Never | Legacy handler |
| `DASHBOARD_EXPLICIT` | "Dashboard AAPL" | Always | Full dashboard |
| `LEGACY_COMMAND` | Any "fact/table/..." | Never | Pass through |
| `NATURAL_LANGUAGE` | Complex queries | Never | LLM fallback |

## Confidence Thresholds

The router assigns confidence scores:

- **1.0** - Perfect match (explicit patterns)
- **0.9** - Very confident (pattern with variations)
- **0.8** - Confident (structured parser agreement)
- **0.7** - Moderate confidence (threshold)
- **< 0.7** - Low confidence → Falls back to LLM

## Dashboard Control

The router provides explicit dashboard control:

### Force Dashboard
```python
# User: "Dashboard AAPL"
EnhancedRouting(
    intent=DASHBOARD_EXPLICIT,
    force_dashboard=True  # Always build dashboard
)
```

### Force Text Only
```python
# User: "Compare Apple vs Microsoft"
EnhancedRouting(
    intent=COMPARE_TWO,
    force_text_only=True  # Never build dashboard
)
```

### Respect Existing Logic
```python
# User: "Show Apple KPIs"
EnhancedRouting(
    intent=METRICS_SINGLE,
    force_dashboard=False,
    force_text_only=False
)
# Existing code decides: single ticker + no period filters = dashboard
```

## Testing Enhanced Routing

### Test Pattern Matching

```python
from benchmarkos_chatbot.routing import enhance_structured_parse
from benchmarkos_chatbot.parsing.parse import parse_to_structured

# Test input
text = "Show Apple KPIs for 2023"
structured = parse_to_structured(text)
routing = enhance_structured_parse(text, structured)

print(f"Intent: {routing.intent}")
print(f"Confidence: {routing.confidence}")
print(f"Force dashboard: {routing.force_dashboard}")
print(f"Force text only: {routing.force_text_only}")
```

### Test End-to-End

```python
from benchmarkos_chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import Settings

# Enable enhanced routing
settings = Settings(enable_enhanced_routing=True)
bot = BenchmarkOSChatbot.create(settings=settings)

# Test query
response = bot.ask("Show Apple KPIs")

# Check routing metadata
routing_info = bot.last_structured_response.get("enhanced_routing")
print(f"Routing: {routing_info}")
```

## Pattern Examples

### ✅ Deterministic Patterns (High Confidence)

```python
# METRICS_SINGLE
"Show Apple KPIs" → METRICS_SINGLE (0.9)
"Show Apple metrics" → METRICS_SINGLE (0.9)
"Show AAPL KPIs for 2023" → METRICS_SINGLE (0.9)

# METRICS_MULTI
"Show Apple and Microsoft KPIs" → METRICS_MULTI (0.9)
"Show Apple, Microsoft, and Google metrics" → METRICS_MULTI (0.9)

# COMPARE_TWO
"Compare Apple vs Microsoft" → COMPARE_TWO (1.0)
"Compare AAPL versus MSFT" → COMPARE_TWO (1.0)

# COMPARE_MULTI
"Compare Apple, Microsoft, and Google" → COMPARE_MULTI (1.0)

# DASHBOARD_EXPLICIT
"Dashboard AAPL" → DASHBOARD_EXPLICIT (1.0)
"Show me full dashboard for Apple" → DASHBOARD_EXPLICIT (1.0)

# LEGACY_COMMAND
"fact AAPL 2022" → LEGACY_COMMAND (1.0)
"scenario AAPL Bull rev=+8%" → LEGACY_COMMAND (1.0)
```

### ⚠️ Fallback to Existing Parser (Medium Confidence)

```python
# Relies on existing structured parser
"What are the metrics for Apple?" → Uses parse_to_structured (0.8)
"Apple performance last year" → Uses parse_to_structured (0.8)
```

### 🤖 LLM Fallback (Low Confidence)

```python
# Complex queries that need natural language understanding
"Tell me about Apple's competitive position" → LLM (0.5)
"How is Apple performing in the smartphone market?" → LLM (0.4)
"Explain the risks facing Apple" → LLM (0.4)
```

## Structured Response Format

When enhanced routing is enabled, the chatbot adds routing metadata to `last_structured_response`:

```python
{
    "parser": {...},  # Existing parse_to_structured output
    "enhanced_routing": {
        "intent": "metrics_single",
        "confidence": 0.9,
        "force_dashboard": false,
        "force_text_only": false
    },
    "dashboard": {...},  # Dashboard payload (if built)
    "highlights": [...],  # Existing highlights
    # ... other existing fields ...
}
```

## Benefits

### For Users
- ✅ More consistent responses
- ✅ Explicit dashboard control ("Dashboard AAPL")
- ✅ Predictable behavior for common queries

### For Developers
- ✅ Clear intent classification
- ✅ Easy to debug routing decisions
- ✅ Confidence scores for monitoring
- ✅ Non-breaking integration

### For System
- ✅ Reduces unnecessary dashboard builds
- ✅ Faster response times for text-only queries
- ✅ Better resource utilization

## Monitoring

Track routing decisions in your analytics:

```python
routing_info = bot.last_structured_response.get("enhanced_routing")

if routing_info:
    log_metric("intent", routing_info["intent"])
    log_metric("confidence", routing_info["confidence"])
    log_metric("dashboard_forced", routing_info["force_dashboard"])
```

## Rollback

To disable enhanced routing:

```bash
# Remove from environment
unset ENABLE_ENHANCED_ROUTING

# Or set to false
export ENABLE_ENHANCED_ROUTING=false
```

All behavior will revert to existing parsing with **zero changes**.

## Future Enhancements

Potential additions (not yet implemented):

- [ ] Time period pattern matching (FY:2023, FQ:2023Q3)
- [ ] Metric filtering patterns ("Show revenue and margin")
- [ ] Peer comparison patterns ("Compare Apple to sector")
- [ ] Custom intent handlers (SCENARIO, AUDIT improvements)
- [ ] Machine learning confidence tuning
- [ ] A/B testing framework

## Architecture

```
User Input
    ↓
┌─────────────────────────────────────┐
│  _handle_financial_intent()         │
│                                     │
│  1. Check legacy commands           │
│  2. Check complex NL queries        │
│  3. parse_to_structured()           │ ← Existing
│  4. enhance_structured_parse()      │ ← New (optional)
│  5. _handle_structured_metrics()    │ ← Existing
│  6. Fallback to LLM if needed       │ ← Existing
└─────────────────────────────────────┘
    ↓
Response (Same format as before)
```

## Summary

The enhanced routing system is a **non-invasive confidence layer** that:

1. ✅ Preserves all existing behavior by default
2. ✅ Adds deterministic pattern matching when enabled
3. ✅ Provides explicit dashboard control
4. ✅ Maintains backward compatibility
5. ✅ Enhances debuggability with confidence scores

**To enable:** Set `ENABLE_ENHANCED_ROUTING=true` in your environment.

---

*Last Updated: October 26, 2025*  
*Status: Production Ready*  
*Default: Disabled (No Impact)*

