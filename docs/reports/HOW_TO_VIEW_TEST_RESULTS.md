# How to View ML Prompt Test Results

## Quick Commands

### 1. **Check Progress** (Summary)
```bash
python check_test_progress.py
```
Shows:
- Total prompts tested
- Pass/fail counts and percentages
- Category breakdown
- Recent failures

### 2. **View Detailed Results** (Full Details)
```bash
python show_detailed_results.py
```
Shows:
- Detailed quality metrics for each prompt
- Response previews
- Specific issues for failures

### 3. **View Raw JSON** (Complete Data)
```bash
# Windows PowerShell
Get-Content ml_patterns_test_results.json | ConvertFrom-Json | Format-List

# Or open in a text editor
code ml_patterns_test_results.json
```

### 4. **View Test Output Log**
```bash
# Windows PowerShell
Get-Content ml_test_output.txt -Tail 100
```

## Current Test Status

**Progress:** 38/93 prompts tested (40.9% complete)

**Results:**
- ✅ **Passed:** 19 prompts (50.0%)
- ❌ **Failed:** 19 prompts (50.0%)

## Key Findings

### ✅ **Working Patterns** (100% Pass Rate)
- **Basic Forecast** (5/5) - "Forecast Apple's revenue"
- **Basic Predict** (4/4) - "Predict Microsoft's revenue"
- **Basic Show** (3/3) - "Show me Apple's revenue forecast"
- **Basic Whats** (4/4) - "What's Tesla's revenue forecast?"

### ❌ **Failing Patterns** (0-33% Pass Rate)
- **With Model GRU** (0/3) - "Model 'gru' not found"
- **With Model Transformer** (0/3) - "Model 'transformer' not found"
- **With Model ETS** (0/3) - "Model 'ets' not found"
- **With Model Ensemble** (0/3) - "Model 'ensemble' not found"
- **With Model LSTM** (1/4) - 25% pass rate
- **With Model ARIMA** (1/3) - 33% pass rate
- **With Model Prophet** (1/3) - 33% pass rate

## Root Cause

**Issue:** Model-specific prompts are being routed to the **custom model builder** instead of the **ML forecasting system**.

**Error Pattern:**
```
Model 'gru' not found. Use 'List my models' to see available models.
```

**Expected Behavior:**
- Should route to ML forecasting system
- Should use the specified ML model (GRU, Transformer, ETS, etc.)
- Should return ML forecast with values, CI, years

**Actual Behavior:**
- Routing to custom model builder
- Looking for user-defined custom models
- Returning error message instead of forecast

## Next Steps

1. **Fix Model Name Extraction**
   - Ensure "using GRU", "using Transformer", etc. are recognized as ML model requests
   - Not custom model builder requests

2. **Fix Routing Logic**
   - Prioritize ML forecasting for model-specific prompts
   - Only route to custom model builder if explicitly requested

3. **Test Model Name Variations**
   - "using GRU" vs "using gru" vs "using GRU model"
   - Ensure all variations work

## Files

- `ml_patterns_test_results.json` - Complete test results (JSON)
- `ml_test_output.txt` - Full test output log
- `check_test_progress.py` - Progress checker script
- `show_detailed_results.py` - Detailed results viewer

## Test Still Running

The test is still running in the background. Check progress anytime with:
```bash
python check_test_progress.py
```
