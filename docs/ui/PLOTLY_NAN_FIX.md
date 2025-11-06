# Plotly NaN Error Fix

## Issue
The dashboard was showing the following error repeatedly in the browser console:
```
Error: <text> attribute transform: Expected number, "translate(NaN,314)scale(0)".
```

## Root Cause
The error occurred when Plotly.js received `NaN` (Not a Number) or `Infinity` values in chart data. When Plotly tried to calculate SVG transform positions for chart elements, these invalid numeric values caused the transform calculations to fail, resulting in malformed SVG attributes like `translate(NaN,314)`.

## Solution
Implemented comprehensive data sanitization across all chart rendering functions to ensure only valid finite numbers are passed to Plotly.

### Changes Made

#### 1. Enhanced `buildNumericSeries` Function (Line 202-224)
- Added strict validation using `Number.isFinite()` to filter out `NaN` and `Infinity` values
- Added new helper function `sanitizeNumericArray()` to clean arrays of numeric values

```javascript
function buildNumericSeries(categories = [], values = [], labelPrefix = "") {
  // ... existing code ...
  const numeric = toNumericValue(values[idx], label);
  // Strict validation: must be a finite number (not NaN, not Infinity)
  if (numeric === null || !Number.isFinite(numeric)) continue;
  safe.push({ x: categories[idx], y: numeric });
}

function sanitizeNumericArray(arr) {
  if (!Array.isArray(arr)) return [];
  return arr.map(val => {
    if (val === null || val === undefined) return null;
    const num = Number(val);
    return Number.isFinite(num) ? num : null;
  });
}
```

#### 2. Updated Chart Rendering Functions

**plotRevenueChart (Line 928-1007)**
- Added validation to filter out non-finite values from y-axis data
- Added early return if no valid data exists
- Added `connectgaps: false` to prevent connecting across null values in line charts

**plotEbitdaChart (Line 1009-1087)**
- Same improvements as plotRevenueChart
- Validates both bar chart data and multiples line data

**plotForecastChart (Line 1089-1154)**
- Uses `sanitizeNumericArray()` to clean forecast data
- Counts valid data points before rendering
- Added `connectgaps: false` for all traces

**plotValuationBar (Line 1156-1270)**
- Enhanced existing sanitization logic
- Added validation for reference lines (Current Price, Average)
- Only adds reference lines if values are valid finite numbers

**renderTrendChart (Line 762-831)**
- Sanitizes series values before processing
- Enhanced growth calculation to check for finite numbers
- Validates calculated growth rates

**openKpiDrilldown Chart (Line 675-714)**
- Added `Number.isFinite()` validation for all data points
- Added `connectgaps: false` to trend charts

### Key Improvements

1. **Strict Validation**: All numeric values are validated using `Number.isFinite()` which returns `false` for:
   - `NaN`
   - `Infinity`
   - `-Infinity`
   - Non-numeric values

2. **Graceful Degradation**: Charts gracefully handle missing or invalid data by:
   - Skipping invalid points rather than crashing
   - Showing helpful error messages when no valid data exists
   - Using `connectgaps: false` to avoid connecting across missing data

3. **Comprehensive Coverage**: All chart types are protected:
   - Bar charts (Revenue, EBITDA, Valuation)
   - Line charts (Forecast, Trends, KPI drilldowns)
   - Combination charts (dual-axis charts)
   - Reference lines (Current Price, Average)

## Testing
After applying these fixes:
1. Open the dashboard in your browser
2. Check the browser console (F12 → Console tab)
3. The NaN transform errors should be eliminated
4. Charts should render correctly with valid data
5. Invalid data points will be gracefully skipped

## Prevention
To prevent similar issues in the future:
- Always validate numeric data before passing to chart libraries
- Use `Number.isFinite()` for strict numeric validation
- Add early returns when no valid data exists
- Consider adding data validation at the data source level

## Files Modified
- `webui/cfi_dashboard.js` - All chart rendering functions updated with NaN protection

