# Multi-Ticker Dashboard Toolbar Removal

## Changes Made

For multi-ticker dashboards, the complex dashboard toolbar (with view switcher, search, density controls, currency selector, refresh button, etc.) has been removed and replaced with just the company switcher buttons.

## What Was Changed

### 1. Backend (`src/benchmarkos_chatbot/chatbot.py`)
No changes needed - already returns `"kind": "multi-cfi-classic"` with multiple dashboard payloads.

### 2. Frontend JavaScript (`webui/app.js`)

#### A. Updated `renderDashboardArtifact()` function:
- Added support for `"multi-cfi-classic"` kind (in addition to existing `"multi-classic"`)
- Lines 2896, 2901, 2721, 2731: Added `|| kind === "multi-cfi-classic"` checks

#### B. Updated `showCfiDashboard()` function (line 7672):
- Extracts `isMultiTicker` flag from options
- Sets `data-multi-ticker="true"` attribute on the dashboard host container when `isMultiTicker` is true
- This flag is then used by the dashboard JavaScript to hide the toolbar

```javascript
// Mark host as multi-ticker if applicable
if (isMultiTicker) {
  host.dataset.multiTicker = "true";
}
```

#### C. Updated multi-ticker dashboard rendering (line 3048):
- Passes `isMultiTicker: true` flag when building dashboard options for each ticker

```javascript
const options = { 
  container: host,
  payload: dashboardItem.payload,
  ticker: dashboardItem.ticker,
  isMultiTicker: true  // Flag to indicate this is part of a multi-ticker dashboard
};
```

### 3. Dashboard JavaScript (`webui/cfi_dashboard.js`)

#### Updated `window.CFI.render()` function (line 1676):
- Added toolbar hiding logic at the start of the render function
- Checks if the dashboard container has `data-multi-ticker="true"` attribute
- If multi-ticker, hides the `.dashboard-toolbar` element using `display: none`

```javascript
// Check if this is a multi-ticker dashboard and hide toolbar if so
const scope = resolveScope();
const isMultiTicker = scope.dataset && scope.dataset.multiTicker === "true";
if (isMultiTicker) {
  const toolbar = scopedSelect(".dashboard-toolbar");
  if (toolbar) {
    toolbar.style.display = "none";
  }
}
```

## How It Works

### Single-Ticker Dashboard:
1. User asks: `"dashboard AAPL"`
2. Backend returns: `{"kind": "cfi-classic", ...}`
3. Frontend renders the full toolbar with all controls
4. Dashboard displays normally with toolbar

### Multi-Ticker Dashboard:
1. User asks: `"dashboard NVDA TSLA AAPL MSFT"`
2. Backend returns: `{"kind": "multi-cfi-classic", "dashboards": [...]}`
3. Frontend:
   - Creates company switcher buttons at the top
   - For each individual dashboard, sets `data-multi-ticker="true"`
   - When dashboard renders, detects the flag and hides the toolbar
4. Result: Clean company switcher buttons + dashboards without the complex toolbar

## Visual Result

### Before (What was removed):
```
┌────────────────────────────────────────────────────────────────────┐
│ [Single Company View ▼] [🔍 Search...]  [≡≡≡] [$€£] Updated 22h ago │
└────────────────────────────────────────────────────────────────────┘
```

### After (What you see now):
```
Compare Companies (4):
┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ NVIDIA Corp.   │  │ Tesla, Inc.    │  │ Apple Inc.     │  │ Microsoft Corp.│
│     NVDA       │  │     TSLA       │  │     AAPL       │  │     MSFT       │
└────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘

[Full CFI Dashboard displayed below - WITHOUT the complex toolbar]
```

## Benefits

1. **Cleaner Interface**: Removes visual clutter for multi-company comparisons
2. **Clear Focus**: The company switcher is the only control needed for multi-ticker mode
3. **Consistent Behavior**: Each company's dashboard is identical, just without the toolbar
4. **No Feature Loss**: All dashboard features (charts, tables, KPIs, exports) remain fully functional

## Test Queries

Try these to see the toolbar-free multi-ticker dashboards:

```
dashboard NVDA TSLA AAPL
show dashboard for Apple Microsoft Tesla
comprehensive dashboard MSFT AAPL
dashboard TSLA NVDA MSFT AAPL
```

## Technical Notes

- The toolbar HTML is still present in the DOM, just hidden with `display: none`
- Single-ticker dashboards (`dashboard AAPL`) still show the full toolbar
- The company switcher buttons are styled separately and are always visible for multi-ticker mode
- Server restart was required for changes to take effect (completed, running on PID 22116)

## Files Modified

1. `webui/app.js` - Added multi-cfi-classic support and isMultiTicker flag
2. `webui/cfi_dashboard.js` - Added toolbar hiding logic in render function

## Status

✅ **COMPLETE** - Server is running with all changes applied (PID 22116)

The multi-ticker dashboard toolbar has been successfully removed and replaced with just the company switcher.

