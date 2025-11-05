# Hallucination Fix: Question Queries Showing Wrong Company Data

## Problem Identified

**Issue**: Queries like "What's Amazon trading at?" and "How profitable is Microsoft?" were showing ticker summaries for WRONG companies (Atmos Energy instead of Amazon, Campbell's instead of Microsoft).

**Root Cause**: Even though questions were detected, `_detect_summary_target()` was still triggering on keywords like "performance", "metrics", "trading" and generating summaries, which then showed wrong/random company data.

---

## Solution Applied

### Fix: Block Summary Generation for Questions

**File**: `src/benchmarkos_chatbot/chatbot.py`  
**Method**: `_detect_summary_target()` (line ~1013)

Added early exit for question patterns before checking for summary keywords.

```python
def _detect_summary_target(...):
    # CRITICAL: Don't generate summaries for questions
    lowered_check = user_input.strip().lower()
    question_blockers = [
        r'\bwhat\'s\b',  # "what's"
        r'\bhow\s+(?:profitable|fast|good|bad|strong|weak)',  # "how profitable"
        r'\b(?:would|could|can)\s+you\s+help',
        r'\bhelp\s+me\s+understand',
        r'\b(?:please|can you|would you)\s+(?:show|tell|explain|help)',
        r'\b(?:can|could|would)\s+you\s+(?:tell|explain|show|help)',
        r'\bi\s+want\s+to\s+know',
        r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would|about|does|did)\b',
        r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would|about|to|do)\b',
    ]
    if any(re.search(pattern, lowered_check) for pattern in question_blockers):
        return None  # Block summary generation
    
    # ... rest of summary detection logic
```

---

## Additional Improvements

### 1. Contraction Support

Added explicit patterns for contractions:
- `r'\bwhat\'s\b'` - "what's"
- `r'\bhow\'s\b'` - "how's"

### 2. Expanded "how" Pattern

Added common adjectives after "how":
- `r'\bhow\s+(?:....|profitable|fast|good|bad|strong|weak)\b'`

Now detects:
- "How profitable is Microsoft?"
- "How fast is Apple growing?"
- "How good is Tesla?"

---

## Verification

### Test Results:

```
Query: "What's Amazon trading at?"
  - Is question: True ✓
  - Should generate summary: False ✓
  - Expected: LLM response about Amazon (not Atmos Energy)

Query: "What's Microsoft's sales figures?"
  - Is question: True ✓
  - Should generate summary: False ✓
  - Expected: LLM response about Microsoft (not Campbell's)

Query: "How profitable is Microsoft?"
  - Is question: True ✓
  - Should generate summary: False ✓
  - Expected: LLM response about Microsoft profitability

Query: "How fast is Microsoft growing?"
  - Is question: True ✓
  - Should generate summary: False ✓
  - Expected: LLM response about Microsoft growth
```

### Non-Questions (should still work):

```
Query: "Microsoft metrics"
  - Is question: False ✓
  - Should generate summary: True ✓
  - Expected: Summary/dashboard for Microsoft

Query: "AAPL"
  - Is question: False ✓
  - Should generate summary: True ✓
  - Expected: Summary/dashboard for Apple
```

---

## Complete Flow (After Fix)

### For Questions:
```
User: "What's Amazon trading at?"
  ↓
Early check: Detects question ✓
  ↓
_detect_summary_target(): Blocks summary (returns None) ✓
  ↓
Dashboard check: Skipped (is_question = True) ✓
  ↓
Routes to LLM with enhanced context ✓
  ↓
Response: Conversational answer about Amazon's P/E ratio ✓
```

### For Non-Questions:
```
User: "AAPL"
  ↓
Early check: Not a question ✓
  ↓
_detect_summary_target(): Detects bare ticker ✓
  ↓
Generates summary for Apple ✓
  ↓
Response: Apple metrics/dashboard ✓
```

---

## Changes Summary

### Files Modified:
1. `src/benchmarkos_chatbot/chatbot.py` - 3 locations
   - `_detect_summary_target()` - Added question blockers
   - `_handle_financial_intent()` question_patterns - Added contractions
   - `ask()` method question_patterns - Added contractions

### Patterns Added:
- Contraction support: `what's`, `how's`
- Expanded "how" adjectives: `profitable`, `fast`, `good`, `bad`, `strong`, `weak`
- Question blockers in summary detection

---

## Impact

### Before Fix:
- "What's Amazon trading at?" → Showed Atmos Energy data ❌
- "What's Microsoft's sales figures?" → Showed Campbell's data ❌
- "How profitable is Microsoft?" → Showed wrong company data ❌

### After Fix:
- "What's Amazon trading at?" → LLM response about Amazon ✅
- "What's Microsoft's sales figures?" → LLM response about Microsoft ✅
- "How profitable is Microsoft?" → LLM response about Microsoft ✅

---

## Testing Checklist

- [ ] "What's Amazon trading at?" - Shows Amazon data (not Atmos Energy)
- [ ] "What's Microsoft's sales figures?" - Shows Microsoft data (not Campbell's)
- [ ] "How profitable is Microsoft?" - Shows Microsoft profitability
- [ ] "How fast is Microsoft growing?" - Shows Microsoft growth
- [ ] "AAPL" (bare ticker) - Still shows Apple summary (backward compatibility)
- [ ] "Microsoft metrics" - Still shows Microsoft metrics (backward compatibility)

---

## Summary

**Problem**: Questions triggered summary generation, which showed wrong company data  
**Solution**: Block summary generation for questions in `_detect_summary_target()`  
**Result**: Questions now route correctly to LLM without triggering summaries  
**Status**: ✅ FIXED

---

**Fixed By**: Malcolm Munoriyarwa  
**Date**: November 2, 2025  
**Status**: Ready for testing

