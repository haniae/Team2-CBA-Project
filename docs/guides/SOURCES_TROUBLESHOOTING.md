# 🔧 Sources Section Troubleshooting Guide

## ✅ What Was Fixed

1. **Button Styling** - Changed to clean white button with blue text
2. **Section Visibility** - Added `!important` flags to force display
3. **Debug Logging** - Extensive console logs to identify issues
4. **Forced Display** - JavaScript explicitly shows the panel

## 🎯 Where to Look

The sources section is at the **BOTTOM** of the dashboard:

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard Content                     │
│                    (charts, KPIs, etc.)                 │
│                                                          │
│                    ↓ Scroll Down ↓                      │
│                                                          │
╞═════════════════════════════════════════════════════════╡
║  Data Sources & References         [Hide ▼]            ║  ← BRIGHT BLUE HEADER
╞═════════════════════════════════════════════════════════╡
║  ┌─────────┐  ┌─────────┐  ┌─────────┐               ║
║  │ Revenue │  │ EBITDA  │  │ ROE     │               ║
║  │ $391.0B │  │ Formula │  │ Formula │               ║
║  │ 📄 SEC  │  │ EBIT+D&A│  │ NI/Eqty │               ║
║  └─────────┘  └─────────┘  └─────────┘               ║
║  ... 57 sources total ...                             ║
╚═════════════════════════════════════════════════════════╝
```

## 🔍 Debugging Steps

### Step 1: Check Console Logs

Open browser console (F12) and look for:

```
✅ GOOD:
[CFI] Checking sources... {sourcesCount: 57, hasEnhancements: true}
[renderDataSources] ✅ Container found, rendering 57 sources
[setupSourcesToggle] ✅ Toggle button initialized and sources VISIBLE

❌ BAD:
[CFI] ⚠️ No sources in payload
[renderDataSources] ❌ Container #cfi-sources-grid NOT FOUND!
```

### Step 2: Check HTML Elements

In browser console, run:
```javascript
document.querySelector('[data-area="sources"]')
document.getElementById('cfi-sources-grid')
document.getElementById('toggle-sources-btn')
```

All three should return HTML elements, not `null`.

### Step 3: Visual Check

The sources section should have:
- **Bright blue gradient background** on the header
- **3px blue border** around the entire panel
- **White "Hide" button** with a chevron icon
- **Grid of cards** below (57 total for AAPL)

### Step 4: Check Payload

Run in console:
```javascript
window.__cfiDashboardLastPayload?.sources?.length
```

Should return `57` (or similar number for other companies).

## 🚨 Common Issues

### Issue 1: "I don't see the blue section at all"

**Solutions:**
1. **Clear cache** - Ctrl+Shift+Del (Windows) or Cmd+Shift+Del (Mac)
2. **Hard refresh** - Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
3. **Check you scrolled all the way down**
4. **Regenerate dashboard** - Ask chatbot again: `show dashboard for AAPL`

### Issue 2: "Button looks wrong or is missing"

**Check:**
- Look for console errors
- Verify `toggle-sources-btn` exists in DOM
- Try clicking where the button should be

### Issue 3: "Blue header exists but no sources below"

**Check console for:**
```
[renderDataSources] ✅ Container found, rendering X sources
```

If you see "rendering 0 sources", the payload is empty.

### Issue 4: "Everything is there but still looks bad"

The button styling was just improved to:
- White background (not transparent)
- Blue text (matches theme)
- Better shadow and hover effects
- Larger, clearer text

## 📝 Test Files

Two test files were created to help:

1. **`test_sources_visibility.html`** - Open in browser to check if payload has sources
2. **`SOURCES_TROUBLESHOOTING.md`** (this file) - Complete troubleshooting guide

## 🆘 If Nothing Works

1. **Take screenshots of:**
   - The entire dashboard (with scroll position shown)
   - Browser console logs
   - Result of running Step 2 commands above

2. **Share this info:**
   - Browser name and version
   - Console error messages
   - Screenshot of the dashboard

3. **Try opening `webui/cfi_dashboard.html` directly:**
   ```
   file:///C:/Users/YourName/Desktop/Team2-CBA-Project/webui/cfi_dashboard.html
   ```
   See if the HTML structure exists.

## ✨ Current Status

**All code changes pushed to GitHub:**
- ✅ Sources section forced visible with `!important`
- ✅ Button styled with white background
- ✅ Extensive debug logging added
- ✅ Panel explicitly shown via JavaScript

**Expected behavior:**
- Sources section appears at bottom of dashboard
- Bright blue header stands out
- 57 sources displayed in grid
- Toggle button allows hiding/showing

---

**Last Updated:** Just now  
**Commit:** `cc51ab6` - "fix: Improve sources section visibility and button styling"

