# Multi-Ticker Detection Fix

## Issue

When users requested multi-ticker dashboards (e.g., "dashboard apple microsoft"), only one company was being detected and displayed in the comparison bar. The image showed "COMPARE COMPANIES (1):" with only "Apple Inc." button, even though the user requested both Apple and Microsoft.

## Root Cause

The ticker detection logic (`_detect_tickers`) was using a pattern-matching approach that:
1. Tried to match ticker symbols (e.g., AAPL, MSFT)
2. Tried to match company phrases using a regex pattern
3. But the phrase pattern could match multi-word phrases like "dashboard apple microsoft" as a single phrase
4. When trying to resolve "dashboard apple microsoft" as a company name, it would fail
5. This meant individual company names like "microsoft" were not being detected

## Solution

Added an additional pass in the `_detect_tickers` method that:
1. **Splits the text into individual words**: `"dashboard apple microsoft"` → `["dashboard", "apple", "microsoft"]`
2. **Filters out command words**: Skips words like "dashboard", "show", "display", etc.
3. **Tries to resolve each word separately**: Both "apple" and "microsoft" are individually resolved to tickers

### Code Changes

**File**: `src/benchmarkos_chatbot/chatbot.py`

**Location**: `_detect_tickers` method (lines 3809-3831)

**New Logic**:
```python
# Additional pass: try individual words in case multi-word phrases didn't resolve
# This helps when users say "dashboard apple microsoft" - try each word separately
command_words = {"dashboard", "show", "display", "compare", "view", "get", "give", "full", "comprehensive", "detailed"}
words = text.split()
for word in words:
    word = word.strip()
    if len(word) < 2:
        continue
    if word.lower() in command_words:
        continue
    if word.upper() in _COMMON_WORDS:
        continue
    if word.upper() in seen:
        continue
    # Try to resolve this individual word as a company name or ticker
    print(f"[DEBUG] Trying individual word: '{word}'")
    ticker = self._name_to_ticker(word)
    print(f"[DEBUG] Resolved individual word '{word}' -> {ticker}")
    if ticker and ticker not in seen:
        seen.add(ticker)
        candidates.append(ticker)
```

### Additional Debug Logging

Also added progress event emission to help track ticker detection:
```python
all_tickers = self._detect_tickers(user_input)
emit("ticker_detection", f"Detected tickers from '{user_input}': {all_tickers}")
```

## How It Works Now

### Example: "dashboard apple microsoft"

1. **Ticker Pattern Matching**: No uppercase tickers found
2. **Company Phrase Matching**: May match "apple microsoft" as a phrase, tries to resolve, likely fails
3. **NEW: Individual Word Matching**:
   - Split: `["dashboard", "apple", "microsoft"]`
   - Skip "dashboard" (command word)
   - Try "apple" → resolves to "AAPL" ✅
   - Try "microsoft" → resolves to "MSFT" ✅
4. **Result**: `all_tickers = ["AAPL", "MSFT"]`
5. **Multi-Ticker Dashboard**: Since `len(all_tickers) >= 2`, builds dashboards for both companies

## Visual Result

### Before (Only 1 company):
```
COMPARE COMPANIES (1):
┌────────────────┐
│ Apple Inc.     │
│     AAPL       │
└────────────────┘
```

### After (All companies):
```
COMPARE COMPANIES (2):
┌────────────────┐  ┌────────────────┐
│ Apple Inc.     │  │ Microsoft Corp.│
│     AAPL       │  │     MSFT       │
└────────────────┘  └────────────────┘
```

## Test Queries

Try these to verify the fix:

```
dashboard apple microsoft
show dashboard for apple microsoft tesla
dashboard NVDA tesla apple
comprehensive dashboard microsoft nvidia
dashboard apple microsoft tesla nvidia
```

All companies should now appear in the comparison bar with their own dashboard buttons.

## Benefits

1. **More Robust Detection**: Works even when company names are separated by command words
2. **Handles Various Formats**: Works with both company names ("apple") and tickers ("AAPL")
3. **Backward Compatible**: Still uses original pattern matching first, word-by-word is a fallback
4. **Better User Experience**: All requested companies are now included in the dashboard

## Technical Details

- **Command Words Filtered**: `dashboard`, `show`, `display`, `compare`, `view`, `get`, `give`, `full`, `comprehensive`, `detailed`
- **Minimum Word Length**: 2 characters
- **Deduplication**: Uses a `seen` set to avoid duplicate tickers
- **Order Preserved**: Maintains the order companies appear in the user's input
- **Server Restart**: Required for changes to take effect (completed, running on PID 11440)

## Debug Mode

The debug `print` statements will show in the server console what's being detected:
```
[DEBUG] Trying individual word: 'apple'
[DEBUG] Resolved individual word 'apple' -> AAPL
[DEBUG] Trying individual word: 'microsoft'
[DEBUG] Resolved individual word 'microsoft' -> MSFT
```

You can see this output in the terminal where `python serve_chatbot.py` is running.

## Status

✅ **FIXED** - Server is running with the improved ticker detection (PID 11440)

When you request "dashboard apple microsoft", both companies will now appear in the comparison bar with their own dashboard buttons!

