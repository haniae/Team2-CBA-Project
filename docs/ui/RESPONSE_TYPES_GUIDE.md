# Response Types & Dashboard Display Guide

## Summary: When Are Dashboards Built?

Based on testing the chatbot with different query types, here's when dashboards are displayed vs. text responses:

---

## 📊 Dashboard Response Types (2 Types)

### 1. **Single-Ticker Dashboard** (`cfi-classic`)

**When Built:**
- User explicitly asks for a dashboard with keywords like:
  - "show me [TICKER] dashboard"
  - "display [TICKER] dashboard"
  - "[TICKER] comprehensive dashboard"

**Example Queries:**
- ✅ "show me MSFT dashboard" → **Dashboard Built**
- ✅ "display AAPL dashboard" → **Dashboard Built**
- ❌ "AAPL revenue" → **Text Only** (no dashboard keyword)
- ❌ "dashboard AAPL" → **Text Only** (treated as ticker summary)

**Response Structure:**
```json
{
  "dashboard": {
    "kind": "cfi-classic",
    "ticker": "MSFT",
    "payload": { /* full dashboard data */ }
  },
  "reply": "Displaying financial dashboard for MICROSOFT CORPORATION (MSFT)."
}
```

**UI Display:** Full interactive dashboard with KPIs, charts, and drill-downs

---

### 2. **Multi-Ticker Comparison Dashboard** (`cfi-compare`)

**When Built:**
- Comparing 2 or more tickers
- Multi-ticker KPI requests

**Example Queries:**
- ✅ "compare AAPL vs MSFT" → **Compare Dashboard**
- ✅ "compare AAPL, MSFT, and GOOGL" → **Compare Dashboard**
- ✅ "show AAPL, MSFT, GOOGL KPIs" → **Compare Dashboard**

**Response Structure:**
```json
{
  "dashboard": {
    "kind": "cfi-compare",
    "tickers": ["AAPL", "MSFT", "GOOGL"],
    "benchmark": "S&P 500 Avg",
    "payload": { /* comparison data */ }
  },
  "comparison_table": { /* table data */ },
  "trends": [ /* trend series */ ],
  "highlights": [ /* key insights */ ],
  "citations": [ /* source links */ ]
}
```

**UI Display:** Side-by-side comparison dashboard with benchmark

---

## 📝 Text-Only Response Types (6 Types)

### 3. **Single Ticker Lookup** (NO Dashboard)

**Example Queries:**
- "AAPL revenue"
- "What is MSFT net income?"

**Response:** Text summary with KPI snapshot

---

### 4. **Trend Analysis** (NO Dashboard)

**Example Queries:**
- "show AAPL revenue trend over last 5 years"
- "MSFT growth trends"

**Response:** Text summary (trends series available but not used)

---

### 5. **Ranking Query** (NO Dashboard)

**Example Queries:**
- "which tech companies have the highest revenue?"
- "top 10 companies by market cap"

**Response:** Natural language response with rankings

---

### 6. **Explanation Query** (NO Dashboard)

**Example Queries:**
- "what is EBITDA?"
- "explain free cash flow"

**Response:** Natural language explanation

---

### 7. **Single Metric Query** (NO Dashboard)

**Example Queries:**
- "AAPL P/E ratio"
- "Tesla revenue FY2024"

**Response:** Direct metric value with context

---

### 8. **Period-Specific Query** (NO Dashboard)

**Example Queries:**
- "AAPL revenue in Q3 2024"
- "MSFT earnings last quarter"

**Response:** Text table with period data

---

## 🎨 UX/UI Adjustment Summary

For your UI work, you need to handle **these distinct display formats:**

| Response Type | Dashboard? | Display Format | UI Adjustments Needed |
|---------------|-----------|----------------|----------------------|
| **Single-Ticker Dashboard** | ✅ Yes (`cfi-classic`) | Full dashboard | Apply dashboard styling |
| **Multi-Ticker Compare** | ✅ Yes (`cfi-compare`) | Comparison dashboard | Apply comparison styling |
| **Single Ticker Lookup** | ❌ No | Text + KPI cards | Apply card/text styling |
| **Trend Analysis** | ❌ No | Text + charts (optional) | Apply chart styling |
| **Ranking Query** | ❌ No | Text list | Apply list styling |
| **Explanation Query** | ❌ No | Text prose | Apply prose styling |
| **Single Metric** | ❌ No | Text value | Apply inline styling |
| **Period-Specific** | ❌ No | Text table | Apply table styling |

---

## 🔍 Key Findings

### Dashboards ARE Built (2 scenarios):
1. **Explicit single-ticker dashboard request** with "dashboard" in query
   - Returns: `cfi-classic` dashboard
   
2. **Multi-ticker comparison** (2+ tickers)
   - Returns: `cfi-compare` dashboard with table, trends, highlights

### Dashboards are NOT Built (6 scenarios):
3. Single ticker **without** "dashboard" keyword → Text summary
4. Trend queries → Text response
5. Ranking queries → Natural language response
6. Explanation queries → Natural language response
7. Single metric queries → Direct value response
8. Period-specific queries → Text table response

---

## 💡 Implications for Your UX/UI Work

1. **Dashboard Layouts (2 types):**
   - `cfi-classic`: Single company full dashboard
   - `cfi-compare`: Multi-company comparison view

2. **Text Layouts (6 types):**
   - Each needs appropriate styling:
     - Cards for KPI summaries
     - Tables for comparisons
     - Charts for trends
     - Lists for rankings
     - Prose for explanations
     - Inline for single values

3. **Detection Logic:**
   Check `response.dashboard.kind` to determine which UI template to use:
   ```javascript
   if (response.dashboard) {
     if (response.dashboard.kind === 'cfi-classic') {
       // Render single-ticker dashboard
     } else if (response.dashboard.kind === 'cfi-compare') {
       // Render comparison dashboard
     }
   } else {
     // Render text-based response with appropriate styling
   }
   ```

---

## 📸 Test Results Summary

Tested 8 different query types:

| # | Query Type | Query Example | Dashboard Built? | Dashboard Type |
|---|-----------|---------------|-----------------|----------------|
| 1 | Single ticker (no keyword) | "AAPL revenue" | ❌ NO | N/A |
| 2 | Single ticker (with "dashboard") | "dashboard AAPL" | ❌ NO | N/A |
| 3 | Explicit dashboard request | "show me MSFT dashboard" | ✅ YES | `cfi-classic` |
| 4 | Compare two tickers | "compare AAPL vs MSFT" | ✅ YES | `cfi-compare` |
| 5 | Compare multiple tickers | "compare AAPL, MSFT, GOOGL" | ✅ YES | `cfi-compare` |
| 6 | Multi-ticker KPIs | "show AAPL, MSFT, GOOGL KPIs" | ✅ YES | `cfi-compare` |
| 7 | Trend query | "show AAPL revenue trend" | ❌ NO | N/A |
| 8 | Ranking query | "which tech companies..." | ❌ NO | N/A |

**Total Dashboard Types: 2**
- `cfi-classic` (single ticker)
- `cfi-compare` (multi-ticker)

**Total Text Response Types: 6+**
- Single ticker lookup
- Trend analysis
- Ranking queries
- Explanation queries
- Single metric queries
- Period-specific queries

---

## Next Steps for UI Implementation

1. **Identify which response type** you're rendering
2. **Apply appropriate styling** for that type:
   - Dashboard types get full dashboard UI
   - Text types get context-appropriate formatting
3. **Don't mix styles** - each response type should have its own clear visual treatment
4. **Test each type** independently to ensure clean, non-messy displays


