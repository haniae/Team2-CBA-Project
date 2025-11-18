# Quick Verification Guide - Test Your Chatbot

## ✅ Fast Verification (No Database/API Needed)

### Step 1: Test Parsing & Extraction (30 seconds)
```bash
python test_queries.py
```

**What it tests:**
- ✅ Ticker extraction (including typos: "microsft" → MSFT)
- ✅ Metric detection ("revenue", "margins")
- ✅ Question type classification (causal, comparison, etc.)
- ✅ Complex query handling (50-300+ word queries)

**Expected output:**
```
✅ All tests completed!
```

---

### Step 2: Test Edge Cases (30 seconds)
```bash
python test_any_prompt.py
```

**What it tests:**
- ✅ Unrelated queries ("what's the weather")
- ✅ Gibberish ("asdfghjkl")
- ✅ Empty strings
- ✅ All get context (never empty)

**Expected output:**
```
✅ OK: System can handle this query
```
(for all queries)

---

## 🧪 Full Chatbot Testing (Requires Database & API)

### Option 1: Interactive Testing (Recommended)
```bash
python test_chatbot_interactive.py
```

**Then type:**
- `test` - Run predefined test queries
- `apple revenue` - Test your own query
- `microsft revenu` - Test typo correction
- `what's the weather` - Test unrelated query
- `quit` - Exit

**What to check:**
- ✅ Gets a response (not empty)
- ✅ Response is helpful (50+ characters)
- ✅ No "I don't understand" messages
- ✅ Typos are corrected

---

### Option 2: Automated Test Suite
```bash
# Quick test (5 queries, 1-2 minutes)
python test_chatbot_queries.py --quick

# Full test (30+ queries, 5-10 minutes)
python test_chatbot_queries.py
```

**What to check:**
- ✅ Success rate: 90%+
- ✅ No crashes
- ✅ All categories tested

---

## 📊 Verification Checklist

### ✅ Parsing & Extraction (test_queries.py)
- [ ] Typos corrected: "microsft" → MSFT, "nvida" → NVDA
- [ ] Metrics detected: "revenue", "margins", "cash flow"
- [ ] Concepts extracted: "growth", "profitability"
- [ ] Question types: causal, comparison, trend
- [ ] Complex queries: 50-300+ words handled

### ✅ Edge Cases (test_any_prompt.py)
- [ ] Unrelated queries get context
- [ ] Gibberish doesn't crash
- [ ] Empty strings handled
- [ ] All queries processed

### ✅ Full Chatbot (test_chatbot_queries.py)
- [ ] Simple queries work
- [ ] Typos corrected in responses
- [ ] Conversational queries work
- [ ] Complex queries addressed
- [ ] Unrelated queries handled gracefully

---

## 🎯 Quick Test Sequence

```bash
# 1. Test parsing (fast, no setup)
python test_queries.py

# 2. Test edge cases (fast, no setup)
python test_any_prompt.py

# 3. If both pass → Implementation is correct! ✅

# 4. Optional: Test full chatbot (requires database/API)
python test_chatbot_interactive.py
```

---

## ✅ Success Criteria

### Parsing Tests:
- ✅ All ticker extractions work
- ✅ Typos are corrected
- ✅ Metrics/concepts detected
- ✅ Complex queries parsed

### Edge Case Tests:
- ✅ All queries get context
- ✅ No crashes
- ✅ Helpful context provided

### Full Chatbot Tests:
- ✅ 90%+ success rate
- ✅ Responses are helpful (50+ chars)
- ✅ No error messages
- ✅ Typos corrected in responses

---

## 🔍 What Each Test Verifies

### `test_queries.py`
- **Purpose:** Verify parsing/extraction logic
- **Speed:** Fast (30 seconds)
- **Requires:** Nothing (no database/API)
- **Tests:** Ticker extraction, metric detection, question classification

### `test_any_prompt.py`
- **Purpose:** Verify edge case handling
- **Speed:** Fast (30 seconds)
- **Requires:** Nothing (no database/API)
- **Tests:** Unrelated queries, gibberish, empty strings

### `test_chatbot_queries.py`
- **Purpose:** Verify end-to-end chatbot responses
- **Speed:** Medium (1-10 minutes)
- **Requires:** Database + API keys
- **Tests:** Actual chatbot responses, quality checks

### `test_chatbot_interactive.py`
- **Purpose:** Manual testing and exploration
- **Speed:** Interactive (as long as you want)
- **Requires:** Database + API keys
- **Tests:** Your own queries, see responses

---

## 💡 Recommended Approach

1. **Start with parsing tests** (no setup needed):
   ```bash
   python test_queries.py
   python test_any_prompt.py
   ```
   If these pass → Your implementation is correct! ✅

2. **Then test full chatbot** (if you have database/API):
   ```bash
   python test_chatbot_interactive.py
   ```
   Test a few queries to verify responses

3. **If all pass → Your chatbot handles all queries! 🎉**

---

## 🚨 Troubleshooting

### If parsing tests fail:
- Check file paths are correct
- Verify imports work
- Check code changes are saved

### If edge case tests fail:
- Verify `_extract_partial_info_from_query()` exists
- Check fallback context creation in `context_builder.py`
- Verify `chatbot.py` has universal fallback

### If full chatbot tests fail:
- Check database path in settings
- Verify database exists
- Check LLM API keys are set
- Verify API is accessible

---

**The parsing tests are the fastest way to verify your implementation is correct!**

