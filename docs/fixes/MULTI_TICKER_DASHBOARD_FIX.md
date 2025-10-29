# Multi-Ticker Dashboard Fix

## Issue

The chatbot was crashing with a `500 Internal Server Error` when users requested dashboards for multiple companies:

```
AttributeError: 'BenchmarkOSChatbot' object has no attribute '_handle_compare_multi'
```

## Root Cause

The code at line 1763 in `src/benchmarkos_chatbot/chatbot.py` was calling a non-existent method `self._handle_compare_multi()` when handling multi-ticker dashboard requests.

## Solution

Replaced the non-existent method call with code that:

1. **Builds Individual Dashboards**: Loops through each ticker and builds a complete CFI dashboard payload using `build_cfi_dashboard_payload()`

2. **Packages Multiple Dashboards**: Creates a special data structure with `"kind": "multi-cfi-classic"` that contains an array of individual dashboard objects

3. **Stores in Standard Response**: Places the multi-dashboard structure in the `last_structured_response["dashboard"]` field, maintaining compatibility with the existing API

## Code Changes

### Before (Line 1763):
```python
reply = self._handle_compare_multi(all_tickers, None, None)
```

### After (Lines 1763-1787):
```python
# Build individual dashboards for each ticker
dashboards = []
for ticker in all_tickers:
    dashboard_payload = build_cfi_dashboard_payload(self.analytics_engine, ticker)
    if dashboard_payload:
        display = _display_ticker_symbol(_normalise_ticker_symbol(ticker))
        dashboards.append({
            "kind": "cfi-classic",
            "ticker": display,
            "payload": dashboard_payload,
        })

if dashboards:
    # Store all dashboards for multi-ticker display
    # Use a special structure to indicate multiple dashboards
    self.last_structured_response["dashboard"] = {
        "kind": "multi-cfi-classic",
        "dashboards": dashboards,
    }
    company_names = [d["payload"].get("meta", {}).get("company", d["ticker"]) for d in dashboards]
    reply = f"Displaying financial dashboards for {', '.join(company_names)}."
    emit("summary_complete", f"Dashboards prepared for {len(dashboards)} companies")
else:
    reply = "Unable to build dashboards for the requested companies."
    emit("summary_unavailable", "Dashboard data unavailable")
```

## How It Works

1. **Detection**: When a user asks for a dashboard with multiple companies (e.g., "dashboard AAPL MSFT NVDA TSLA"), the code detects:
   - The "dashboard" keyword is present
   - Multiple tickers are mentioned (≥2)

2. **Dashboard Building**: For each ticker:
   - Fetches all financial data using the analytics engine
   - Builds a complete dashboard payload with KPIs, charts, tables, etc.
   - Adds the dashboard to the collection

3. **Response Structure**: Creates a special multi-dashboard object:
   ```json
   {
     "kind": "multi-cfi-classic",
     "dashboards": [
       {
         "kind": "cfi-classic",
         "ticker": "AAPL",
         "payload": { /* full dashboard data */ }
       },
       {
         "kind": "cfi-classic",
         "ticker": "MSFT",
         "payload": { /* full dashboard data */ }
       }
     ]
   }
   ```

4. **Frontend Display**: The web UI (already implemented in `webui/app.js`) recognizes the "multi-cfi-classic" kind and displays company switcher buttons, allowing users to view each dashboard individually.

## What Users Will See

When users request a multi-ticker dashboard:

1. **Request**: "dashboard NVDA TSLA AAPL MSFT"

2. **Response**: "Displaying financial dashboards for NVIDIA Corporation, Tesla Inc., Apple Inc., Microsoft Corporation."

3. **UI**: Company switcher buttons appear above the dashboard:
   ```
   [NVIDIA Corporation] [Tesla Inc.] [Apple Inc.] [Microsoft Corporation]
   ```
   - First company's dashboard is shown by default
   - Clicking any button instantly switches to that company's dashboard
   - Each dashboard is fully interactive with all KPIs, charts, exports, sources, etc.

## Test Queries

Try these to verify the fix:

- `dashboard AAPL MSFT` (2 companies)
- `dashboard NVDA TSLA AAPL` (3 companies)
- `show me dashboard for Apple Microsoft Tesla` (natural language)
- `comprehensive dashboard TSLA NVDA` (with adjective)

## Technical Details

- **File Modified**: `src/benchmarkos_chatbot/chatbot.py` (lines 1759-1787)
- **Method**: `ask()` in `BenchmarkOSChatbot` class
- **Dependencies**: Uses existing `build_cfi_dashboard_payload()` function
- **Backward Compatible**: Single-ticker dashboards still work exactly as before
- **Server Restart**: Required for changes to take effect (completed)

## Status

✅ **FIXED** - Server is now running with the corrected code on port 8000 (PID 36240)

The multi-ticker dashboard feature is now fully functional.
