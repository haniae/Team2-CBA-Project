# 🚀 ML Forecasting Prompts - Quick Reference

## ✅ What Works Now

### **Trigger Keywords**
These keywords automatically trigger ML forecasting:
- `forecast`, `predict`, `estimate`, `projection`, `project`, `outlook`, `future`, `next X years`, `upcoming years`

---

## 📋 Working Prompt Examples

### **1. Basic Forecasts**
```
✅ "Forecast Apple's revenue"
✅ "Predict Tesla's earnings"
✅ "What's the revenue forecast for Microsoft?"
✅ "Estimate Amazon's cash flow"
```

### **2. Method-Specific Forecasts**
```
✅ "Forecast Apple's revenue using ARIMA"
✅ "Predict Tesla's earnings with LSTM"
✅ "Forecast Microsoft's revenue using Prophet"
✅ "Estimate Google's revenue using Transformer"
✅ "Forecast NVIDIA's revenue using ensemble"
✅ "Predict Apple's revenue using auto"  (automatically selects best model)
```

### **3. Multi-Year Forecasts**
```
✅ "Forecast Apple's revenue for the next 3 years"
✅ "Predict Tesla's earnings for the next 5 years"
✅ "What's the revenue outlook for Microsoft over the next 2 years?"
```

### **4. Combined Queries**
```
✅ "Forecast Apple's revenue using LSTM for the next 3 years"
✅ "Predict Tesla's earnings with Prophet for the next 5 years"
✅ "Estimate Microsoft's free cash flow using ensemble for the next 2 years"
```

### **5. Metric-Specific**
```
✅ "Forecast Apple's revenue"
✅ "Predict Tesla's net income"
✅ "Estimate Microsoft's free cash flow"
✅ "Project Google's EBITDA"
✅ "Forecast NVIDIA's earnings"
```

---

## 🤖 Available ML Models

| Model | Use Case | Example Prompt |
|-------|----------|----------------|
| **ARIMA** | Statistical time series | "Forecast using ARIMA" |
| **Prophet** | Seasonal patterns | "Forecast using Prophet" |
| **ETS** | Exponential smoothing | "Forecast using ETS" |
| **LSTM** | Deep learning, complex patterns | "Forecast using LSTM" |
| **GRU** | Faster than LSTM, similar accuracy | "Forecast using GRU" |
| **Transformer** | Attention-based, long-term dependencies | "Forecast using Transformer" |
| **Ensemble** | Best accuracy (combines multiple models) | "Forecast using ensemble" |
| **Auto** | Automatically selects best model | "Forecast using auto" |

---

## 📊 What You Get

Every forecast includes:

1. ✅ **Forecast Values** - Actual predicted numbers for each year
2. ✅ **Confidence Intervals** - 95% confidence ranges
3. ✅ **Model Explanation** - How the ML model works
4. ✅ **Regime Detection** - Market regime (bull/bear/volatile/stable)
5. ✅ **Model Explainability** - Feature importance and attention weights
6. ✅ **Historical Context** - Comparison to past trends
7. ✅ **Academic Sources** - References to research papers

---

## 🎯 Quick Start Examples

**Try these prompts:**

1. **Simple:** `"Forecast Apple's revenue"`
2. **Method-specific:** `"Forecast Tesla's earnings using LSTM"`
3. **Multi-year:** `"Predict Microsoft's revenue for the next 5 years"`
4. **Best model:** `"Forecast Google's revenue using ensemble"`
5. **Auto-select:** `"Predict NVIDIA's revenue using auto"`

---

## ⚠️ Important Notes

- ✅ Forecasts are **not cached** - always fresh
- ✅ Requires **5+ years** of historical data
- ✅ **Regime detection and explainability are automatic** - no special prompts needed
- ✅ **Ensemble method** generally provides the most reliable forecasts
- ✅ If you don't specify a method, it uses "auto" to select the best model

---

## 🔍 Troubleshooting

**If forecast doesn't work:**
1. ✅ Make sure you include a forecasting keyword (`forecast`, `predict`, etc.)
2. ✅ Specify a ticker (e.g., AAPL, MSFT, TSLA)
3. ✅ Specify a metric (e.g., revenue, earnings)
4. ✅ Check that company has enough historical data (5+ years)

**Common issues:**
- "No forecast generated" → Company may not have enough historical data
- "Method not available" → Try a different model or use "auto"
- "Generic snapshot instead of forecast" → Make sure you use forecasting keywords

---

## 📚 Full Documentation

For detailed information, see: [`ML_FORECASTING_PROMPTS.md`](./ML_FORECASTING_PROMPTS.md)

