# Button Event Handler Fix

## Problem
When testing the multi-company dashboard with 4 tickers (NVIDIA, Tesla, Apple, Microsoft), the buttons to switch between companies weren't working. The buttons were rendering correctly but clicking them had no effect.

## Root Cause
The event handler setup code was trying to query for buttons in the DOM before they were fully appended to their parent container. The buttons were being created in a loop but the event handlers were being attached too early in the rendering process.

## Solution

### 1. Changed Button Creation Pattern
**Before:**
```javascript
const companyButtons = descriptor.dashboards.map((dashboardItem, index) => {
  // Create button
  buttonGroup.appendChild(button);
  return button;  // Collected in array
});
```

**After:**
```javascript
descriptor.dashboards.forEach((dashboardItem, index) => {
  // Create button
  buttonGroup.appendChild(button);
  // No array collection needed
});
```

### 2. Added Timing Fix for Event Handler Attachment
**Before:**
```javascript
const companyButtons = selectorWrapper.querySelectorAll(".message-dashboard__company-btn");
companyButtons.forEach((button) => {
  button.addEventListener("click", () => {
    // handler
  });
});
```

**After:**
```javascript
setTimeout(() => {
  const companyButtons = selectorWrapper.querySelectorAll(".message-dashboard__company-btn");
  companyButtons.forEach((button) => {
    button.addEventListener("click", () => {
      // handler
    });
  });
}, 0);
```

The `setTimeout(..., 0)` ensures the event handler setup happens after the current call stack completes and the buttons are fully rendered in the DOM.

### 3. Added Initial Selection for Dropdown
For the dropdown mode (>10 companies), explicitly set the initial selection:
```javascript
selectElement.selectedIndex = 0;
```

## Testing Checklist

- [x] 4 companies (NVIDIA, Tesla, Apple, Microsoft) - Should show buttons
- [x] Buttons are rendered correctly
- [x] Button click events fire properly
- [x] Dashboard switches when button is clicked
- [x] Active state updates correctly
- [x] First dashboard is shown by default
- [x] Lazy loading works (dashboards render on first view)

## Files Modified
1. `webui/app.js` (lines 2974-3004, 3115-3128)
2. `src/benchmarkos_chatbot/static/app.js` (lines 2974-3004, 3115-3128)

## Technical Details

### Why setTimeout(..., 0)?
This is a common JavaScript pattern that defers execution until after the current call stack completes. It ensures:
1. All DOM manipulations finish
2. The browser has updated the DOM tree
3. Elements are queryable and ready for event attachment

### Why Change from .map() to .forEach()?
The original code used `.map()` to collect button elements in an array, but then tried to query them again from the DOM. This created a race condition. The new approach:
- Uses `.forEach()` to create and append buttons
- Queries buttons after they're in the DOM
- Avoids maintaining a separate array

## Performance Impact
Minimal - the `setTimeout(..., 0)` adds negligible delay (< 1ms) and only affects initial render, not switching performance.

## Backward Compatibility
✅ Fully compatible - the fix preserves all existing functionality and only corrects the timing of event handler attachment.

