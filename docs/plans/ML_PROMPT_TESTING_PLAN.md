# ML Prompt Testing Plan

## Current Status

✅ **Fixed Critical Bug**: `re` import scope issue fixed - chatbot now works for basic prompts

## Test Results So Far

### ✅ Working Patterns
- "Forecast Apple's revenue" - ✅ WORKING
  - Returns proper forecast with values, model name, confidence intervals
  - No snapshots
  - Proper format

### ⚠️ Needs Testing
- All other prompt patterns need comprehensive testing
- Some prompts may be returning error messages (71 chars suggests error)

## Comprehensive Testing Required

### Test Categories (93 prompts total)

1. **Basic Forecast** (5 prompts) - ⚠️ Need to test all
2. **Basic Predict** (4 prompts) - ⚠️ Need to test all
3. **Basic Whats** (4 prompts) - ⚠️ Need to test all
4. **Basic Show** (3 prompts) - ⚠️ Need to test all
5. **With Model Prophet** (3 prompts) - ⚠️ Need to test all
6. **With Model ARIMA** (3 prompts) - ⚠️ Need to test all
7. **With Model LSTM** (4 prompts) - ⚠️ One failed (71 chars)
8. **With Model GRU** (3 prompts) - ⚠️ Need to test all
9. **With Model Transformer** (3 prompts) - ⚠️ Need to test all
10. **With Model ETS** (3 prompts) - ⚠️ Need to test all
11. **With Model Ensemble** (4 prompts) - ⚠️ Need to test all
12. **With Model Best** (3 prompts) - ⚠️ Need to test all
13. **With Time Years** (3 prompts) - ⚠️ Need to test all
14. **With Time Period** (3 prompts) - ⚠️ Need to test all
15. **Different Metrics** (6 prompts) - ⚠️ Need to test all
16. **Different Metrics With Model** (4 prompts) - ⚠️ Need to test all
17. **Question Formats** (5 prompts) - ⚠️ Need to test all
18. **Imperative** (4 prompts) - ⚠️ Need to test all
19. **Variations Project** (3 prompts) - ⚠️ Need to test all
20. **Variations Estimate** (3 prompts) - ⚠️ Need to test all
21. **Variations Outlook** (3 prompts) - ⚠️ Need to test all
22. **Variations Forecast For** (3 prompts) - ⚠️ Need to test all
23. **Variations Predict For** (3 prompts) - ⚠️ Need to test all
24. **Complex Combinations** (5 prompts) - ⚠️ Need to test all
25. **Edge Cases** (6 prompts) - ⚠️ Need to test all

## Next Steps

1. **Run Comprehensive Test Suite**
   ```bash
   python test_all_ml_patterns_comprehensive.py
   ```
   This will test all 93 prompts and identify which patterns are failing.

2. **Analyze Failures**
   - Check which prompt patterns consistently fail
   - Identify common issues (e.g., model not found, metric not recognized)
   - Check if errors are due to:
     - Query detection issues
     - Model selection issues
     - Metric extraction issues
     - Context generation issues
     - LLM response issues

3. **Fix Issues**
   - Fix query detection for failing patterns
   - Fix model selection logic
   - Fix metric extraction
   - Improve context generation
   - Strengthen LLM instructions

4. **Re-test**
   - Run test suite again
   - Verify all patterns work
   - Target: 90%+ success rate

## Known Issues to Investigate

1. **LSTM prompts returning short responses (71 chars)**
   - May be error messages
   - Need to check what the actual response is

2. **Model-specific prompts may not be working**
   - Need to verify model selection logic
   - Check if model names are being extracted correctly

3. **Different metrics may not be recognized**
   - "earnings" vs "net income"
   - Need to verify metric mapping

4. **Time-based prompts may not work**
   - "for next 3 years"
   - "for 2025-2027"
   - Need to verify period extraction

## Quality Criteria

Each response must have:
- ✅ Forecast values ($X.XB format)
- ✅ Model name mentioned
- ✅ Confidence intervals (95% CI)
- ✅ Forecast years (2025-2028)
- ❌ NO Growth/Margin Snapshots
- ❌ NO error messages

## Test Scripts

- `test_all_ml_patterns_comprehensive.py` - Tests all 93 prompts
- `test_ml_debug.py` - Quick debug test
- `test_ml_batch.py` - Batch testing
- `test_ml_incremental.py` - Incremental with save/resume

