# How to Verify Your Chatbot Handles All Queries

## ✅ Quick Verification (No Database Required)

### Step 1: Test Parsing & Extraction
```bash
python test_queries.py
```
This tests:
- ✅ Ticker extraction (including typos)
- ✅ Metric detection
- ✅ Question type classification
- ✅ Partial information extraction
- ✅ Multi-line query handling

**Expected:** All tests pass, typos are corrected, metrics/concepts detected

---

### Step 2: Test Edge Cases
```bash
python test_any_prompt.py
```
This tests:
- ✅ Unrelated queries get context
- ✅ Gibberish doesn't crash
- ✅ Empty strings handled
- ✅ Edge cases processed

**Expected:** All queries get context (even unrelated ones)

---

## 🧪 Full Chatbot Testing (Requires Database & API)

### Option A: Quick Test (5 queries)
```bash
python test_chatbot_queries.py --quick
```
Tests 5 key queries in 1-2 minutes.

### Option B: Comprehensive Test (30+ queries)
```bash
python test_chatbot_queries.py
```
Tests all categories, provides detailed report.

### Option C: Interactive Testing
```bash
python test_chatbot_interactive.py
```
Type queries interactively, see responses in real-time.

---

## ✅ What to Verify

### 1. Parsing Works (test_queries.py)
- ✅ Typos corrected: "microsft" → MSFT
- ✅ Metrics detected: "revenue", "margins"
- ✅ Concepts extracted: "growth", "profitability"
- ✅ Question types identified: causal, comparison, etc.

### 2. Edge Cases Handled (test_any_prompt.py)
- ✅ Unrelated queries get context
- ✅ No crashes on gibberish
- ✅ Empty strings handled

### 3. Full Responses (test_chatbot_queries.py)
- ✅ Responses are helpful (50+ chars)
- ✅ No "I don't understand" messages
- ✅ Typos are corrected in responses
- ✅ Complex queries addressed

---

## 📋 Verification Checklist

### Implementation Checks (No Database Needed):
- [ ] Run `python test_queries.py` - All parsing tests pass
- [ ] Run `python test_any_prompt.py` - Edge cases handled
- [ ] Check `src/finanlyzeos_chatbot/chatbot.py` - System prompt has universal understanding section
- [ ] Check `src/finanlyzeos_chatbot/context_builder.py` - Has `_extract_partial_info_from_query()` function
- [ ] Check `src/finanlyzeos_chatbot/parsing/parse.py` - `normalize()` handles multi-line queries
- [ ] Check `src/finanlyzeos_chatbot/parsing/alias_builder.py` - Has fuzzy matching for typos

### Full Chatbot Checks (Requires Database):
- [ ] Run `python test_chatbot_queries.py --quick` - Basic queries work
- [ ] Test typo: "microsft revenu" - Should correct and answer
- [ ] Test conversational: "how's apple doing" - Should respond naturally
- [ ] Test unrelated: "what's the weather" - Should handle gracefully
- [ ] Test complex: "compare apple microsoft and google on revenue growth" - Should address all parts

---

## 🎯 Quick Verification Steps

1. **Test parsing (fast, no database):**
   ```bash
   python test_queries.py
   ```
   Should show: ✅ All tests completed

2. **Test edge cases (fast, no database):**
   ```bash
   python test_any_prompt.py
   ```
   Should show: ✅ OK: System can handle this query (for all queries)

3. **If you have database/API set up, test full chatbot:**
   ```bash
   python test_chatbot_interactive.py
   ```
   Then type: `test` (runs predefined queries)

---

## 🔍 Manual Code Verification

Check these files have the enhancements:

### 1. `src/finanlyzeos_chatbot/chatbot.py`
- Line ~707: Should have "## Universal Natural Language Understanding" section
- Line ~4358: Should have fallback context creation

### 2. `src/finanlyzeos_chatbot/context_builder.py`
- Line ~3291: Should have `_extract_partial_info_from_query()` function
- Line ~3529: Should have general context fallback for unrelated queries

### 3. `src/finanlyzeos_chatbot/parsing/parse.py`
- Line ~34: `normalize()` should handle multi-line queries
- Should preserve list structure

### 4. `src/finanlyzeos_chatbot/parsing/alias_builder.py`
- Should have fuzzy matching for ticker typos
- Should return warnings for corrections

---

## ✅ Success Indicators

### Parsing Tests (test_queries.py):
- ✅ Ticker extraction works (including typos)
- ✅ Metrics/concepts detected
- ✅ Question types classified
- ✅ Multi-line queries normalized

### Edge Case Tests (test_any_prompt.py):
- ✅ All queries get context
- ✅ No crashes
- ✅ Helpful context provided

### Full Chatbot Tests (test_chatbot_queries.py):
- ✅ 90%+ queries get helpful responses
- ✅ No error messages
- ✅ Responses are meaningful (50+ chars)

---

## 🚀 Recommended Testing Flow

1. **Start with parsing tests (no setup needed):**
   ```bash
   python test_queries.py
   python test_any_prompt.py
   ```
   If these pass → Implementation is correct ✅

2. **Then test full chatbot (requires database/API):**
   ```bash
   python test_chatbot_interactive.py
   ```
   Test a few queries manually

3. **If all pass → Your chatbot is ready! 🎉**

---

**The parsing tests verify the implementation is correct. Full chatbot tests verify end-to-end behavior.**

