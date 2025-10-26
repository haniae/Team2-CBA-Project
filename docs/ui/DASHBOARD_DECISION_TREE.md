# Dashboard Decision Tree - When to Display Dashboard vs Text

```
User Query
    |
    ├─── Contains "show/display [TICKER] dashboard"?
    |    └─── YES → ✅ BUILD CFI-CLASSIC DASHBOARD (Single Ticker)
    |         Example: "show me MSFT dashboard"
    |         Response: Full interactive dashboard with KPIs
    |
    ├─── Multiple Tickers (2+) with compare/KPI keywords?
    |    └─── YES → ✅ BUILD CFI-COMPARE DASHBOARD (Multi-Ticker)
    |         Examples: 
    |           - "compare AAPL vs MSFT"
    |           - "show AAPL, MSFT, GOOGL KPIs"
    |         Response: Side-by-side comparison dashboard
    |
    └─── ALL OTHER QUERIES
         └─── ❌ NO DASHBOARD - TEXT RESPONSE
              Examples:
                - "AAPL revenue" → Text KPI summary
                - "AAPL revenue trend" → Text with charts
                - "which tech companies..." → Natural language list
                - "what is EBITDA?" → Natural language explanation
```

---

## Visual Response Type Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│                     RESPONSE TYPE CLASSIFICATION                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Dashboard Responses (2 types)                                       │
│  ================================                                     │
│                                                                       │
│  1. CFI-CLASSIC DASHBOARD                                           │
│     ┌─────────────────────────────────────────────┐                │
│     │ Full Single-Company Dashboard                │                │
│     │ • Company header with name & ticker         │                │
│     │ • KPI summary cards (12+ metrics)           │                │
│     │ • Interactive charts & trends                │                │
│     │ • Source citations with SEC links            │                │
│     │ • Export options (CSV, PDF)                  │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "show [TICKER] dashboard"                               │
│                                                                       │
│  2. CFI-COMPARE DASHBOARD                                           │
│     ┌─────────────────────────────────────────────┐                │
│     │ Multi-Company Comparison View                │                │
│     │ • Side-by-side ticker cards                  │                │
│     │ • Comparison table with benchmark            │                │
│     │ • Trend charts for each ticker               │                │
│     │ • Highlight insights (3+ items)              │                │
│     │ • Citation links (per ticker)                │                │
│     └─────────────────────────────────────────────┘                │
│     Triggers:                                                        │
│       - "compare X vs Y"                                             │
│       - "show X, Y, Z KPIs"                                          │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Text Responses (6+ types)                                           │
│  ===========================                                          │
│                                                                       │
│  3. SINGLE TICKER LOOKUP                                            │
│     ┌─────────────────────────────────────────────┐                │
│     │ Apple Inc. (AAPL) snapshot                   │                │
│     │ Last updated 2025-10-24                      │                │
│     │                                               │                │
│     │ Phase1 KPIs                                   │                │
│     │ - Revenue: $296.1B (FY2025)                  │                │
│     │ - Net income: $84.5B (FY2025)                │                │
│     │ - Operating income: $93.6B (FY2025)          │                │
│     │ ...                                           │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "AAPL revenue" (no dashboard keyword)                  │
│                                                                       │
│  4. TREND ANALYSIS                                                  │
│     ┌─────────────────────────────────────────────┐                │
│     │ Revenue Trend for AAPL                       │                │
│     │                                               │                │
│     │ FY2020: $274.5B                              │                │
│     │ FY2021: $365.8B (+33.3%)                     │                │
│     │ FY2022: $394.3B (+7.8%)                      │                │
│     │ FY2023: $383.3B (-2.8%)                      │                │
│     │ FY2024: $391.0B (+2.0%)                      │                │
│     │                                               │                │
│     │ [Optional: Inline chart visualization]       │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "AAPL revenue trend over 5 years"                      │
│                                                                       │
│  5. RANKING QUERY                                                   │
│     ┌─────────────────────────────────────────────┐                │
│     │ Top Tech Companies by Revenue:               │                │
│     │                                               │                │
│     │ 1. Apple (AAPL): $391.0B                     │                │
│     │ 2. Microsoft (MSFT): $245.1B                 │                │
│     │ 3. Alphabet (GOOGL): $350.0B                 │                │
│     │ 4. Amazon (AMZN): $574.8B                    │                │
│     │ ...                                           │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "which tech companies have highest revenue?"           │
│                                                                       │
│  6. EXPLANATION QUERY                                               │
│     ┌─────────────────────────────────────────────┐                │
│     │ EBITDA (Earnings Before Interest, Taxes,    │                │
│     │ Depreciation, and Amortization) is a         │                │
│     │ financial metric that measures a company's   │                │
│     │ operational performance...                    │                │
│     │                                               │                │
│     │ Formula: EBITDA = Operating Income +         │                │
│     │          Depreciation + Amortization         │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "what is EBITDA?"                                      │
│                                                                       │
│  7. SINGLE METRIC QUERY                                             │
│     ┌─────────────────────────────────────────────┐                │
│     │ AAPL P/E Ratio: 34.5 (FY2024)               │                │
│     │                                               │                │
│     │ Source: Market data, updated 2025-10-24      │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "AAPL P/E ratio"                                       │
│                                                                       │
│  8. PERIOD-SPECIFIC QUERY                                           │
│     ┌─────────────────────────────────────────────┐                │
│     │ AAPL Revenue Q3 2024                         │                │
│     │                                               │                │
│     │ Quarter | Revenue                            │                │
│     │ --------+---------                           │                │
│     │ Q3 2024 | $85.8B                             │                │
│     └─────────────────────────────────────────────┘                │
│     Trigger: "AAPL revenue Q3 2024"                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Code Detection Logic

```javascript
// In your frontend (webui/app.js)
function renderResponse(response) {
  // Check if dashboard payload exists
  if (response.dashboard) {
    const dashboardType = response.dashboard.kind;
    
    if (dashboardType === 'cfi-classic') {
      // ✅ Render single-ticker dashboard
      renderCfiClassicDashboard(response.dashboard.payload);
    } 
    else if (dashboardType === 'cfi-compare') {
      // ✅ Render comparison dashboard
      renderCfiCompareDashboard(response.dashboard.payload);
    }
  } 
  else {
    // ❌ No dashboard - render text response with appropriate styling
    renderTextResponse(response);
    
    // Optionally render additional artifacts
    if (response.comparison_table) {
      renderComparisonTable(response.comparison_table);
    }
    if (response.trends && response.trends.length > 0) {
      renderTrendCharts(response.trends);
    }
    if (response.highlights && response.highlights.length > 0) {
      renderHighlights(response.highlights);
    }
  }
}
```

---

## UI Styling Recommendations

### For Dashboard Responses (2 types)

**CFI-Classic Dashboard:**
- Full-width layout
- Card-based KPI grid (3-4 columns)
- Interactive chart sections
- Prominent source citations
- Action buttons (Export, Share)

**CFI-Compare Dashboard:**
- Split layout (2-3 columns for tickers)
- Aligned metrics for easy comparison
- Benchmark column (S&P 500)
- Color-coded performance indicators
- Synchronized chart interactions

### For Text Responses (6 types)

**Single Ticker Lookup:**
- Compact card layout
- Clear metric hierarchy
- Subtle dividers between sections
- Last updated timestamp

**Trend Analysis:**
- Timeline/list format
- Growth indicators (arrows, colors)
- Optional inline charts
- Period labels

**Ranking Query:**
- Numbered list
- Aligned values
- Ranking badges (1st, 2nd, 3rd)
- Hover effects for details

**Explanation Query:**
- Prose format
- Highlighted formulas
- Example calculations
- Related links

**Single Metric:**
- Large value display
- Metric label
- Source attribution
- Period context

**Period-Specific:**
- Compact table
- Column headers
- Alternating row colors
- Summary footer

---

## Testing Matrix

| Query Type | Expected Result | UI Treatment |
|-----------|----------------|--------------|
| "show MSFT dashboard" | `cfi-classic` dashboard | Full dashboard layout |
| "compare AAPL vs MSFT" | `cfi-compare` dashboard | Comparison layout |
| "AAPL revenue" | Text summary | Card layout |
| "AAPL revenue trend" | Text + trends | List + optional charts |
| "top tech companies" | Natural language | Formatted list |
| "what is EBITDA" | Natural language | Prose format |
| "AAPL P/E" | Single value | Prominent value display |
| "AAPL revenue Q3" | Table | Compact table |


