# Response Type Examples - Actual Chatbot Outputs

## Overview: 8 Response Types Tested

This document shows **actual outputs** from testing the chatbot with different query types.

---

## ✅ DASHBOARD RESPONSES (2 Types)

### Type 1: CFI-Classic Dashboard (Single Ticker)

**Query:** `"show me MSFT dashboard"`

**Response Structure:**
```json
{
  "dashboard": {
    "kind": "cfi-classic",
    "ticker": "MSFT",
    "payload": {
      "meta": {
        "ticker": "MSFT",
        "company": "MICROSOFT CORPORATION",
        "fiscal_year_end": 2024
      },
      "kpi_summary": [ /* 12+ KPIs */ ],
      "kpi_series": { /* trend data */ },
      "sources": [ /* SEC filing links */ ]
    }
  },
  "reply": "Displaying financial dashboard for MICROSOFT CORPORATION (MSFT)."
}
```

**UI Display:**
```
╔═══════════════════════════════════════════════════════════════╗
║              MICROSOFT CORPORATION (MSFT)                     ║
║                    FY2024 Dashboard                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      ║
║  │   Revenue    │  │ Net Income   │  │    Gross     │      ║
║  │   $245.1B    │  │   $88.1B     │  │   Profit     │      ║
║  │   +15.7%     │  │   +21.8%     │  │   $169.3B    │      ║
║  └──────────────┘  └──────────────┘  └──────────────┘      ║
║                                                               ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      ║
║  │   Op Income  │  │  Cash Ops    │  │  Free Cash   │      ║
║  │   $109.4B    │  │   $118.4B    │  │   Flow       │      ║
║  │   +23.6%     │  │   +23.1%     │  │   $101.0B    │      ║
║  └──────────────┘  └──────────────┘  └──────────────┘      ║
║                                                               ║
║  📈 Interactive Charts                                        ║
║  - Revenue Trend (10 years)                                   ║
║  - Profitability Metrics                                      ║
║  - Cash Flow Analysis                                         ║
║                                                               ║
║  📄 Sources: 12 metrics from SEC 10-K filings                 ║
║  🔗 [View SEC Filing] [Export PDF] [Export CSV]               ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Has Dashboard:** ✅ YES
**Dashboard Type:** `cfi-classic`

---

### Type 2: CFI-Compare Dashboard (Multi-Ticker)

**Query:** `"compare AAPL vs MSFT"`

**Response Structure:**
```json
{
  "dashboard": {
    "kind": "cfi-compare",
    "tickers": ["AAPL", "MSFT"],
    "benchmark": "S&P 500 Avg",
    "payload": { /* comparison data */ }
  },
  "comparison_table": { /* table data */ },
  "trends": [ /* 8 trend series */ ],
  "highlights": [
    "MSFT leads with 20.4% higher net income ($101.8B vs AAPL $84.5B)",
    "AAPL shows stronger cash generation...",
    "MSFT demonstrates superior operating leverage..."
  ],
  "citations": [ /* 24 source links */ ]
}
```

**UI Display:**
```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    AAPL vs MSFT Comparison                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌──────────────────┬──────────────────┬──────────────────┐             ║
║  │      Metric      │       AAPL       │       MSFT       │             ║
║  ├──────────────────┼──────────────────┼──────────────────┤             ║
║  │ Revenue          │ $296.1B          │ $281.7B          │             ║
║  │ Net Income       │ $84.5B           │ $101.8B ⭐       │             ║
║  │ Operating Income │ $93.6B           │ $128.5B ⭐       │             ║
║  │ Gross Profit     │ $136.8B          │ $193.9B ⭐       │             ║
║  │ Cash from Ops    │ $91.4B           │ $87.6B ⭐        │             ║
║  │ Free Cash Flow   │ $72.3B ⭐        │ $56.7B           │             ║
║  └──────────────────┴──────────────────┴──────────────────┘             ║
║                                                                           ║
║  💡 Key Insights:                                                         ║
║  • MSFT leads with 20.4% higher net income                                ║
║  • AAPL shows stronger cash generation relative to size                   ║
║  • MSFT demonstrates superior operating leverage                          ║
║                                                                           ║
║  📈 Trend Charts (side by side):                                          ║
║  - Revenue Growth                                                         ║
║  - Profitability Trends                                                   ║
║  - Cash Flow Comparison                                                   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

**Has Dashboard:** ✅ YES
**Dashboard Type:** `cfi-compare`

---

## ❌ TEXT RESPONSES (6 Types)

### Type 3: Single Ticker Lookup (No Dashboard)

**Query:** `"AAPL revenue"`

**Response Structure:**
```json
{
  "dashboard": null,
  "reply": "Apple Inc. (AAPL) snapshot\nLast updated 2025-10-24\n\nPhase1 KPIs\n- Revenue: $296.1B (FY2025)..."
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│  Apple Inc. (AAPL) snapshot                │
│  Last updated 2025-10-24                   │
│                                            │
│  Phase1 KPIs                               │
│  • Revenue: $296.1B (FY2025)               │
│  • Net income: $84.5B (FY2025)             │
│  • Operating income: $93.6B (FY2025)       │
│  • Gross profit: $136.8B (FY2025)          │
│  • Cash from operations: $91.4B (FY2025)   │
│  • Free cash flow: $72.3B (FY2025)         │
│                                            │
│  Phase 2 KPIs                              │
│  • Revenue CAGR: 12.8% (FY2009-FY2025)     │
│  • Revenue CAGR (3Y): 2.6%                 │
│  • EPS CAGR: 2.1%                          │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Text cards with KPI bullets

---

### Type 4: Trend Analysis (No Dashboard)

**Query:** `"show AAPL revenue trend over last 5 years"`

**Response Structure:**
```json
{
  "dashboard": null,
  "trends": [],  // Could have trend data but not shown in dashboard
  "reply": "Apple Inc. (AAPL) snapshot..."
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│  Apple Revenue Trend (5 Years)             │
│                                            │
│  FY2020: $274.5B                           │
│  FY2021: $365.8B  ↗ +33.3%                 │
│  FY2022: $394.3B  ↗ +7.8%                  │
│  FY2023: $383.3B  ↘ -2.8%                  │
│  FY2024: $391.0B  ↗ +2.0%                  │
│                                            │
│  📊 [Optional inline chart]                │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Text list with optional trend chart

---

### Type 5: Ranking Query (No Dashboard)

**Query:** `"which tech companies have the highest revenue?"`

**Response Structure:**
```json
{
  "dashboard": null,
  "reply": "THE AES CORPORATION (AES) snapshot..."
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│  Top Tech Companies by Revenue             │
│                                            │
│  1. 🥇 Amazon (AMZN): $574.8B              │
│  2. 🥈 Apple (AAPL): $391.0B               │
│  3. 🥉 Alphabet (GOOGL): $350.0B           │
│  4.    Microsoft (MSFT): $245.1B           │
│  5.    Meta (META): $134.9B                │
│                                            │
│  Based on FY2024 financial data            │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Ordered list with ranking badges

---

### Type 6: Explanation Query (No Dashboard)

**Query:** `"what is EBITDA?"`

**Response Structure:**
```json
{
  "dashboard": null,
  "reply": "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) is a financial metric..."
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│  What is EBITDA?                           │
│                                            │
│  EBITDA (Earnings Before Interest, Taxes,  │
│  Depreciation, and Amortization) is a      │
│  financial metric that measures a          │
│  company's operational performance by      │
│  excluding non-operating expenses.         │
│                                            │
│  📐 Formula:                                │
│  EBITDA = Operating Income +               │
│           Depreciation + Amortization      │
│                                            │
│  💡 Use Cases:                              │
│  • Comparing operational efficiency        │
│  • Valuation multiples (EV/EBITDA)         │
│  • Cash flow proxy                         │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Prose format with highlighted formulas

---

### Type 7: Single Metric Query (No Dashboard)

**Query:** `"AAPL P/E ratio"`

**Response Structure:**
```json
{
  "dashboard": null,
  "reply": "AAPL P/E Ratio: 34.5 (FY2024)\n\nSource: Market data..."
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│                                            │
│           AAPL P/E Ratio                   │
│                                            │
│               34.5                         │
│                                            │
│  Period: FY2024                            │
│  Source: Market data                       │
│  Updated: 2025-10-24                       │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Large value display with context

---

### Type 8: Period-Specific Query (No Dashboard)

**Query:** `"AAPL revenue Q3 2024"`

**Response Structure:**
```json
{
  "dashboard": null,
  "comparison_table": {
    "headers": ["Period", "Revenue"],
    "rows": [["Q3 2024", "$85.8B"]]
  }
}
```

**UI Display:**
```
┌────────────────────────────────────────────┐
│  AAPL Revenue - Q3 2024                    │
│                                            │
│  ┌──────────┬───────────────┐             │
│  │  Period  │    Revenue    │             │
│  ├──────────┼───────────────┤             │
│  │ Q3 2024  │    $85.8B     │             │
│  └──────────┴───────────────┘             │
│                                            │
│  Source: SEC 10-Q filing                   │
│                                            │
└────────────────────────────────────────────┘
```

**Has Dashboard:** ❌ NO
**UI Treatment:** Compact table with source

---

## Summary Table

| # | Response Type | Example Query | Has Dashboard? | Dashboard Type | UI Treatment |
|---|--------------|---------------|----------------|----------------|--------------|
| 1 | CFI-Classic Dashboard | "show me MSFT dashboard" | ✅ YES | `cfi-classic` | Full dashboard |
| 2 | CFI-Compare Dashboard | "compare AAPL vs MSFT" | ✅ YES | `cfi-compare` | Comparison dashboard |
| 3 | Single Ticker Lookup | "AAPL revenue" | ❌ NO | - | Text cards |
| 4 | Trend Analysis | "AAPL revenue trend" | ❌ NO | - | Text list + charts |
| 5 | Ranking Query | "top tech companies" | ❌ NO | - | Ordered list |
| 6 | Explanation Query | "what is EBITDA" | ❌ NO | - | Prose format |
| 7 | Single Metric | "AAPL P/E ratio" | ❌ NO | - | Large value display |
| 8 | Period-Specific | "AAPL revenue Q3" | ❌ NO | - | Compact table |

---

## Key Takeaway

**Only 2 out of 8 response types use dashboards.**

For your UX/UI work:
- ✅ Apply dashboard UI to types 1-2 (dashboard responses)
- ❌ Apply appropriate text formatting to types 3-8 (text responses)

This ensures each response type has a clean, purpose-built layout that isn't messy or cramped.


