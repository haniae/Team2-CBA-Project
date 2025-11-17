# Multi-Ticker Dashboard Guide

## 🎯 Overview

The multi-ticker dashboard allows you to compare multiple companies side-by-side with individual full dashboards for each company and easy switching between them.

## ✅ Recent Updates (October 27, 2024)

### Fix 1: Resolved Crash
**Issue Resolved**: Fixed `AttributeError: '_handle_compare_multi' does not exist` crash

The multi-ticker dashboard feature was crashing due to a missing method. This has been fixed by implementing proper dashboard building logic that creates individual dashboards for each ticker and packages them together. See `MULTI_TICKER_DASHBOARD_FIX.md` for technical details.

### Fix 2: Removed Complex Toolbar
**Enhancement**: The complex dashboard toolbar (view switcher, search, density controls, currency selector, etc.) is now automatically hidden for multi-ticker dashboards, leaving only the clean company switcher buttons. Single-ticker dashboards still show the full toolbar. See `MULTI_TICKER_TOOLBAR_REMOVAL.md` for details.

### Fix 3: Improved Ticker Detection
**Issue Resolved**: Fixed ticker detection to correctly identify all companies when requested (e.g., "dashboard apple microsoft" now detects both Apple and Microsoft)

When users requested multi-ticker dashboards, only the first company was being detected. This was fixed by adding an additional word-by-word detection pass that splits the input and tries to resolve each word individually. See `MULTI_TICKER_DETECTION_FIX.md` for technical details.

## 🚀 How to Use

### 1. Request a Multi-Ticker Dashboard

In the chatbot, use any of these formats:

```
Dashboard NVIDIA Tesla Apple
Show dashboard for NVDA TSLA AAPL MSFT
Dashboard comparison NVIDIA Apple Microsoft  
Full dashboard NVDA TSLA
```

**Key Points:**
- Must use the word "dashboard" (triggers dashboard mode)
- Include 2 or more company names or tickers
- Separate companies by spaces
- System will limit to 3 companies for performance

### 2. What You'll See

When the dashboard loads, you'll see:

```
Compare Companies (3):
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ NVIDIA Corp.   │  │ Tesla, Inc.    │  │ Apple Inc.     │
│     NVDA       │  │     TSLA       │  │     AAPL       │
└────────────────┘  └────────────────┘  └────────────────┘

[Full CFI Dashboard for selected company shown below]
```

### 3. Switch Between Companies

- Click any company button to instantly switch to that company's dashboard
- The active button will be highlighted in blue with white text
- Inactive buttons have white background with blue border
- No page reload needed - instant switching

## 📊 What Each Dashboard Includes

Each company dashboard contains:

### Top Section
- **Company Overview**: Price, target, key stats
- **Market Data**: Shares O/S, market cap, dividend
- **Valuation**: Market, DCF, Comps

### Middle Section  
- **Key Financials Table**: Multi-year financial metrics
- **KPI Scorecard**: 20+ financial ratios and metrics

### Charts Section
- **Share Price Chart**: Historical & forecast
- **Revenue vs EV/Revenue**: Trend analysis
- **EBITDA vs EV/EBITDA**: Profitability metrics
- **Trend Explorer**: Interactive metric analysis

### Features
- Export buttons (PPT, PDF, Excel) available
- All charts are interactive (Plotly)
- Sources section at bottom (currently hidden)

## 🎨 Button Design

**Inactive Button:**
- White background
- Blue border
- Company name + ticker
- Hover: Lifts up with shadow

**Active Button:**
- Blue gradient background
- White text
- Company name + ticker in white
- Slightly elevated

## 🔍 Technical Details

### Backend (`src/finanlyzeos_chatbot/chatbot.py`)

When processing a query:
1. Detects "dashboard" keyword
2. Extracts 2+ tickers
3. Builds individual dashboard payload for each ticker (limited to 3)
4. Returns `dashboard_descriptor` with:
   ```python
   {
       "kind": "multi-classic",
       "dashboards": [
           {"ticker": "NVDA", "payload": {...}},
           {"ticker": "TSLA", "payload": {...}},
           {"ticker": "AAPL", "payload": {...}}
       ]
   }
   ```

### Frontend (`webui/app.js`)

When rendering:
1. Detects `kind === "multi-classic"`
2. Creates company switcher buttons
3. Renders first dashboard
4. Hides other dashboards
5. Click handler switches visible dashboard

### Styling (`webui/styles.css`)

Button classes:
- `.message-dashboard__company-btn` - Base button style
- `.message-dashboard__company-btn.active` - Active state
- `.company-btn-name` - Company name text
- `.company-btn-ticker` - Ticker badge

## ⚠️ Limitations

- Maximum 3 companies per dashboard (performance)
- Must explicitly use "dashboard" keyword
- Cannot mix dashboard with specific metric queries
- Each company gets full dashboard (data-intensive)

## 🐛 Troubleshooting

### Buttons Not Showing

1. **Hard refresh browser**: `Ctrl + Shift + R`
2. **Clear cache**: 
   - Open DevTools (`F12`)
   - Right-click refresh button
   - Select "Empty Cache and Hard Reload"
3. **Check query format**: Must include "dashboard" keyword
4. **Check company count**: Need 2+ companies

### Dashboard Not Loading

1. Check browser console for errors (`F12` → Console)
2. Verify companies have data in database
3. Check server logs for errors
4. Try with well-known tickers (AAPL, MSFT, GOOGL)

### Button Clicks Not Working

1. Hard refresh to load latest JavaScript
2. Check console for JavaScript errors
3. Verify `app.js` version is latest (`?v=20241027i`)

## 📝 Example Queries

### ✅ Will Generate Multi-Ticker Dashboard

- `Dashboard NVIDIA Tesla Apple`
- `Show dashboard for AAPL MSFT GOOGL`
- `Full dashboard comparison NVDA TSLA`
- `Dashboard AMD INTC NVDA`

### ❌ Will NOT Generate Multi-Ticker Dashboard

- `Compare NVIDIA Tesla Apple` (no "dashboard" keyword)
- `Show revenue for NVDA TSLA AAPL` (specific metric query)
- `Dashboard AAPL` (only one company)
- `NVIDIA Tesla financials` (no "dashboard" keyword)

## 🎯 Testing Checklist

- [ ] Query with 2+ companies and "dashboard" keyword
- [ ] See company switcher buttons at top
- [ ] First company's dashboard loads automatically
- [ ] Click second company button
- [ ] Dashboard switches to second company
- [ ] Click third company button
- [ ] Dashboard switches to third company
- [ ] Active button is highlighted in blue
- [ ] All charts render without errors
- [ ] Export buttons are available

---

## 🔗 Related Files

- **Backend**: `src/finanlyzeos_chatbot/chatbot.py` (lines 3026-3047)
- **Frontend**: `webui/app.js` (lines 2900-3130)
- **Styling**: `webui/styles.css` (lines 4264-4354)
- **Dashboard Payload**: `src/finanlyzeos_chatbot/dashboard_utils.py`

---

## ✅ Current Status

**Implementation**: ✅ **FIXED AND COMPLETE**
**Testing**: ✅ Ready for user verification
**Documentation**: ✅ Complete

### 🔧 **Recent Fix (October 27, 2024)**

**Issue**: Multi-ticker dashboard requests were not being detected correctly. When typing "Dashboard NVIDIA Tesla Apple", the system would only build a dashboard for the first ticker.

**Root Cause**: The dashboard detection logic was using `_detect_summary_target()` which only returns a single ticker.

**Solution**: Modified `src/finanlyzeos_chatbot/chatbot.py` (lines 1751-1795) to:
1. Check for "dashboard" keyword FIRST
2. If found, detect ALL tickers in the input
3. If 2+ tickers → route to multi-ticker path → generate company switcher buttons
4. If 1 ticker → single-ticker dashboard
5. If 0 tickers → no dashboard

**Status**: ✅ Server restarted with fix. Multi-ticker dashboards will now generate correctly with company switching buttons.

