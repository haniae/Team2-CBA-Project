# Accuracy Improvement Plan - Roadmap to 98%+

## Current Status

### What We Achieved
- ✅ **97.8%** average confidence (521 companies, base metrics)
- ✅ **85.7%** average confidence (2,000 tests, all 68 KPIs)
- ✅ **86.6%** achieve perfect 100% confidence
- ✅ **98.8%** meet 85% quality threshold

### Accuracy by Category
```
Base Metrics (revenue, income):     91.9% ✅ Excellent
Supplemental (market cap, price):   95.0% ✅ Excellent
Aggregate (P/E, growth):             84.5% ✅ Good
Derived (margins, ROE):              78.8% ⚠️ Needs Improvement
Complex Multi-Source Queries:        10%   ❌ Needs Major Fix
```

## Improvement Roadmap

### Phase 1: Quick Wins (Impact: +5-10%)

**Problem 1: FRED Data Confusion (10% → 95%)**
- Issue: LLM confuses company revenue ($245B) with GDP growth
- Fix Applied: FRED formatting with warnings ✅
- Still Needed: Stronger context separation
- Expected Impact: Complex queries from 10% → 95%

**Problem 2: Ticker Resolution Edge Cases**
- Issue: Some companies at 65% confidence (ticker not resolved)
- Fix: Improve global ticker extraction for edge cases
- Expected Impact: +2-3% overall

**Problem 3: Derived Metrics Underperforming (78.8% → 90%)**
- Issue: ROE, margins, ratios have lower accuracy
- Fix: Better unit conversion for decimal percentages
- Expected Impact: Derived metrics from 78.8% → 90%

### Phase 2: Major Improvements (Impact: +10-15%)

**Problem 4: Mandatory Data Blocks Not Fully Integrated**
- Issue: Added to code but LLM may still ignore
- Fix: Make data blocks MORE prominent with stronger language
- Expected Impact: +5-8% overall

**Problem 5: Period Matching**
- Issue: LLM uses FY2024 training data when DB has FY2025
- Fix: Explicit period enforcement in context
- Expected Impact: +3-5% overall

**Problem 6: Metric Identification**
- Issue: 41.8% verification rate (should be 80%+)
- Fix: Better metric keyword matching, context awareness
- Expected Impact: Verification rate from 41.8% → 75%+

### Phase 3: Advanced Optimizations (Impact: +5%)

**Problem 7: Auto-Correction Not Always Triggered**
- Fix: Strengthen auto-correction logic
- Expected Impact: +2-3%

**Problem 8: Cross-Validation Not Fully Utilized**
- Fix: Use Yahoo Finance for validation
- Expected Impact: +1-2%

**Problem 9: Response Regeneration**
- Fix: If confidence <85%, regenerate with explicit instructions
- Expected Impact: +2-3%

## Specific Improvements

### Improvement 1: Strengthen Mandatory Data Blocks

**Current (Partial):**
```
🚨 USE THESE EXACT VALUES FOR {TICKER} 🚨
Revenue: $281.7B (FY2025)
```

**Improved (Stronger):**
```
╔═══════════════════════════════════════════════════════╗
║  🚨 MANDATORY: USE ONLY THESE VALUES - NO EXCEPTIONS  ║
╚═══════════════════════════════════════════════════════╝

COMPANY: Microsoft (MSFT)
PERIOD: FY2025 (DO NOT use FY2024 training data!)

✅ APPROVED VALUES (Use these EXACTLY):
  • Revenue: $281.7B (FY2025)
  • Net Income: $84.5B (FY2025)
  • Gross Margin: 46.2% (FY2025)

❌ PROHIBITED:
  • DO NOT use $245.1B (that's FY2024 training data)
  • DO NOT use FY2024 values
  • DO NOT confuse with economic indicators

⚠️ YOUR RESPONSE WILL BE VERIFIED:
  • Every number will be checked against database
  • Period must match (FY2025)
  • Using wrong values will result in failed verification
```

### Improvement 2: Fix FRED Data Completely

**Add clear labeling:**
```
╔═══════════════════════════════════════════════════════╗
║  📊 ECONOMIC INDICATORS (NOT COMPANY METRICS!)        ║
╚═══════════════════════════════════════════════════════╝

These are MACRO indicators (percentages), NOT company financials:

  ✅ GDP Growth Rate: 2.5% (economic growth)
     ❌ NOT $245B (that's Microsoft's revenue!)
  
  ✅ Federal Funds Rate: 4.5% (interest rate)
     ❌ NOT $281B (that's Microsoft's assets!)
  
  ✅ CPI Inflation: 3.2% (inflation rate)
     ❌ NOT $30B (that's a company metric!)

⚠️ CRITICAL: These are all PERCENTAGES, never dollar amounts!
```

### Improvement 3: Enhanced Verification

**Add response regeneration:**
```python
# In chatbot.py ask() method, after verification:
if conf.score < 0.85 and not strict_mode:
    # Try to regenerate with explicit correction
    correction_prompt = f"""
    Previous response had accuracy issues.
    Regenerate using ONLY the mandatory data block values.
    Period: {period}
    Do NOT use training data.
    """
    # Regenerate response
    reply = self._regenerate_with_correction(correction_prompt)
```

### Improvement 4: Better Metric Identification

**Improve context windows:**
```python
# Expand context window for derived metrics
context_start = max(0, match.start() - 100)  # Was: 50
context_end = min(len(response), match.end() + 100)  # Was: 50
```

**Add metric-specific patterns:**
```python
# ROE patterns
if any(word in context for word in ['return on equity', 'roe', 'return on shareholders']):
    return 'roe'

# Margin patterns
if any(word in context for word in ['gross margin', 'gross profit margin']):
    return 'gross_margin'
```

## Expected Improvements

### Target Accuracy After Fixes

| Metric Type | Current | Target | Improvement |
|-------------|---------|--------|-------------|
| **Base Metrics** | 91.9% | 98%+ | +6.1% |
| **Derived Metrics** | 78.8% | 90%+ | +11.2% |
| **Aggregate Metrics** | 84.5% | 92%+ | +7.5% |
| **Complex Queries** | 10% | 95%+ | +85% |
| **Overall Average** | 85.7% | **95%+** | **+9.3%** |

### Implementation Priorities

**CRITICAL (Week 1):**
1. Strengthen mandatory data blocks (visual borders, explicit prohibitions)
2. Complete FRED formatting fix (clear labeling)
3. Add response regeneration for <85% confidence
4. **Expected: Complex queries from 10% → 95%**

**HIGH (Week 2):**
5. Improve derived metric identification (expand context, better patterns)
6. Period enforcement (prevent FY2024 when FY2025 available)
7. **Expected: Derived metrics from 78.8% → 90%**

**MEDIUM (Week 3):**
8. Enhanced ticker resolution
9. Cross-validation with Yahoo Finance
10. **Expected: Overall from 85.7% → 95%+**

## Questions for You

To create the most effective improvement plan, I need to understand your priorities:

1. **Timeline:** When does Mizuho Bank need to see the improvements?
   - a) This week (focus on critical fixes only)
   - b) Next 2-3 weeks (comprehensive improvements)
   - c) Ongoing (gradual optimization)

2. **Priority:** What matters most for the judge?
   - a) Fix complex queries (10% → 95%) - most dramatic improvement
   - b) Improve overall average (85.7% → 95%) - best headline number
   - c) Both equally important

3. **Scope:** Which queries are most important for Mizuho Bank?
   - a) Simple financial queries ("What is X's revenue?") - already at 97.8%
   - b) Complex forecasts ("Forecast revenue using LSTM") - currently 10%
   - c) Comparisons and analysis - currently 85-90%

Based on your answers, I'll prioritize the specific improvements to implement.


