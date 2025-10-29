# Sources Panel Visibility Fix - Complete

## The Problem

The sources panel was being **rendered in JavaScript** (console showed 57 sources successfully created), but was **hidden by CSS**. The dashboard CSS had a rule that prevented the panel from being visible:

```css
/* Hide Sources Section */
.cfi-panel[data-area="sources"] {
  display: none !important;
}
```

This CSS rule with `!important` was overriding all JavaScript attempts to show the panel.

## The Solution

### 1. Removed the Hiding CSS Rule

**File**: `webui/cfi_dashboard.css` (lines 245-248)

**Removed**:
```css
/* Hide Sources Section */
.cfi-panel[data-area="sources"] {
  display: none !important;
}
```

This CSS block was completely deleted, allowing the JavaScript to control the panel's visibility.

### 2. Updated Cache-Busting

**File**: `webui/cfi_dashboard.html` (line 9)

**Changed**: `?v=20241027h` → `?v=20241027M`

```html
<link rel="stylesheet" href="cfi_dashboard.css?v=20241027M"/>
```

This forces the browser to reload the new CSS without caching issues.

### 3. Copied Files to Static Directory

```bash
copy webui\cfi_dashboard.css src\benchmarkos_chatbot\static\cfi_dashboard.css
copy webui\cfi_dashboard.html src\benchmarkos_chatbot\static\cfi_dashboard.html
```

### 4. Restarted Server

- **Old PID**: 33148 (terminated)
- **New PID**: 4752 (now running with updated CSS)

## What You'll See Now

### ✅ Sources Panel is Visible

The **Sources and References** section will now appear at the bottom of every dashboard, showing:

- **57 data sources** for Apple (for example)
- **20 clickable links** to SEC EDGAR filings
- All source details (Ticker, Metric, Fiscal Year, Value)

### ✅ Expanded by Default

The sources panel now starts **expanded** (not collapsed), so you can immediately see all the sources without clicking a toggle button.

### ✅ Visualizations Should Work

With the CSS fix, the entire dashboard rendering should now work correctly, including:
- Charts and graphs
- KPI scorecards
- Key financials table
- Valuation charts
- **Sources and references section**

## Next Steps

### 1. Hard Refresh Your Browser

**CRITICAL**: You must hard refresh to load the new CSS:

- **Windows**: `Ctrl + Shift + R` or `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`

### 2. Test with Any Dashboard

```
dashboard apple
dashboard tesla
dashboard apple microsoft amazon
```

### 3. Check Console

The console should show:
```
✅ Forced sources panel visibility
✅ Sources rendered successfully
Created 57 source items and 20 links
```

But now you should **actually see** the sources section on the page, not just in the console!

## Technical Details

### Why It Was Hidden

The CSS file had two conflicting rules:

1. **Lines 231-233** (GOOD): Set grid area for sources panel
2. **Lines 246-248** (BAD): Hid the panel entirely with `display: none !important`

The `!important` flag meant the JavaScript couldn't override it, even though it was trying to:

```javascript
sourcesPanel.style.display = 'flex';  // ❌ Overridden by CSS !important
sourcesPanel.style.visibility = 'visible';  // ❌ Overridden by CSS !important
```

### The Fix

By **removing the CSS hiding rule**, the JavaScript can now control visibility:

```javascript
// Start with sources expanded by default
let isCollapsed = false;
sourcesBody.classList.remove('collapsed');
toggleBtn.classList.remove('collapsed');
```

The panel now renders **visible and expanded** from the start.

## Status

✅ **CSS hiding rule removed** - Panel no longer hidden by CSS  
✅ **Cache-busting updated** - Browser will reload fresh CSS (`?v=20241027M`)  
✅ **Files copied** to static directory  
✅ **Server restarted** - PID 4752 now serving updated CSS  
🔒 **NOT pushed to GitHub** (as requested)

**The sources panel should now be fully visible!** 📚✨

