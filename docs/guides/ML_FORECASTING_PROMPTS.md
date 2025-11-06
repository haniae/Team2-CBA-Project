# ML Forecasting Prompts Guide

## 🎯 Overview

Your chatbot now supports **machine learning forecasting** using multiple models:
- **ARIMA** - Statistical time series forecasting
- **Prophet** - Facebook's forecasting tool for seasonal data
- **ETS** - Exponential Smoothing State Space
- **LSTM** - Long Short-Term Memory neural networks
- **GRU** - Gated Recurrent Unit neural networks
- **Transformer** - Attention-based neural networks
- **Ensemble** - Combines multiple models for best accuracy
- **Auto** - Automatically selects the best model

---

## ✅ Working Prompt Patterns

### 1. **Basic Forecasting Queries**

These keywords trigger forecasting:
- `forecast`
- `predict`
- `estimate`
- `projection`
- `project`
- `outlook`
- `future`
- `next X years`
- `upcoming years`

**Examples:**
- "Forecast Apple's revenue"
- "Predict Microsoft's revenue for the next 3 years"
- "What's the revenue forecast for Tesla?"
- "Estimate Amazon's earnings"
- "Project Google's free cash flow"
- "What's the outlook for NVIDIA's revenue?"

---

### 2. **Method-Specific Queries**

You can specify which ML model to use:

**ARIMA:**
- "Forecast Apple's revenue using ARIMA"
- "Predict Tesla's earnings with ARIMA"
- "ARIMA forecast for Microsoft's revenue"

**Prophet:**
- "Forecast Apple's revenue using Prophet"
- "Predict Tesla's earnings with Prophet"
- "Prophet forecast for Microsoft's revenue"

**LSTM:**
- "Forecast Apple's revenue using LSTM"
- "Predict Tesla's earnings with LSTM"
- "LSTM forecast for Microsoft's revenue"

**GRU:**
- "Forecast Apple's revenue using GRU"
- "Predict Tesla's earnings with GRU"
- "GRU forecast for Microsoft's revenue"

**Transformer:**
- "Forecast Apple's revenue using Transformer"
- "Predict Tesla's earnings with Transformer"
- "Transformer forecast for Microsoft's revenue"

**Ensemble:**
- "Forecast Apple's revenue using ensemble"
- "Predict Tesla's earnings with ensemble"
- "Ensemble forecast for Microsoft's revenue"

**Auto (Best Model):**
- "Forecast Apple's revenue using auto"
- "Predict Tesla's earnings with best model"
- "ML forecast for Microsoft's revenue"

---

### 3. **Metric-Specific Queries**

Supported metrics:
- `revenue` / `sales`
- `net income` / `earnings` / `income`
- `cash flow` / `free cash flow`
- `ebitda`
- `profit`
- `margin`
- `eps`
- `assets`
- `liabilities`

**Examples:**
- "Forecast Apple's revenue"
- "Predict Tesla's net income"
- "Estimate Microsoft's free cash flow"
- "Project Google's EBITDA"
- "What's the earnings forecast for Amazon?"
- "Forecast NVIDIA's cash flow"

---

### 4. **Time Period Queries**

You can specify forecast periods:
- "Forecast Apple's revenue for the next 3 years"
- "Predict Tesla's earnings for the next 5 years"
- "What's the revenue outlook for Microsoft over the next 2 years?"
- "Estimate Amazon's revenue for upcoming years"

---

### 5. **Combined Queries**

Combine method, metric, and time period:

**Examples:**
- "Forecast Apple's revenue using LSTM for the next 3 years"
- "Predict Tesla's earnings with Prophet for the next 5 years"
- "Estimate Microsoft's free cash flow using ensemble for the next 2 years"
- "What's the ARIMA forecast for Google's revenue over the next 3 years?"

---

### 6. **Question Format Queries**

Natural language questions also work:
- "What's the revenue forecast for Apple?"
- "What's Apple's revenue prediction?"
- "What's the revenue estimate for Apple?"
- "What's the revenue projection for Apple?"
- "What's the revenue outlook for Apple?"
- "What will Apple's revenue be in the future?"

---

## 📊 What You Get

When you ask for a forecast, the chatbot provides:

1. **Forecast Values** - Actual predicted numbers for each year
2. **Confidence Intervals** - 95% confidence ranges (e.g., $395B-$425B)
3. **Model Explanation** - How the ML model works
4. **Model Suitability** - Why this model is good for this type of data
5. **Historical Context** - Brief comparison to past trends
6. **Model Performance** - Training/validation metrics if available
7. **Academic Sources** - References to research papers and documentation

**Example Response Structure:**
```
Based on LSTM forecasting, Apple's revenue is projected to be $410.50B in 2025, 
$425.30B in 2026, and $440.80B in 2027.

[Model explanation paragraph]

[Confidence intervals and interpretation]

[Brief historical comparison]

📊 Sources:
- [Model documentation links]
- [SEC filing links]
```

---

## 🚀 Quick Start Examples

Try these prompts:

1. **Simple Forecast:**
   - "Forecast Apple's revenue"

2. **Method-Specific:**
   - "Forecast Tesla's earnings using LSTM"

3. **Multi-Year:**
   - "Predict Microsoft's revenue for the next 5 years"

4. **Combined:**
   - "Forecast Google's free cash flow using ensemble for the next 3 years"

5. **Question Format:**
   - "What's the revenue forecast for Amazon?"

---

## ⚙️ Technical Details

### Detection
The system detects forecasting queries using keyword matching:
- Keywords: `forecast`, `predict`, `estimate`, `projection`, `project`, `outlook`, `future`, `next X years`

### Method Selection
- If you specify a method (ARIMA, LSTM, etc.), it uses that model
- If you don't specify, it uses "auto" mode to select the best model
- "Ensemble" combines multiple models for improved accuracy

### Metric Mapping
- `revenue` / `sales` → revenue
- `net income` / `earnings` / `income` → net_income
- `cash flow` → cash_from_operations
- `free cash flow` → free_cash_flow
- Default: revenue (if no metric specified)

### Period Default
- Default: 3 years ahead
- Can specify: "next 3 years", "next 5 years", etc.

---

## 🔍 Troubleshooting

**If a forecast doesn't work:**
1. Make sure you include a forecasting keyword (`forecast`, `predict`, etc.)
2. Specify a ticker (e.g., AAPL, MSFT, TSLA)
3. Specify a metric (e.g., revenue, earnings)
4. Check that the company has historical data in the database

**Common Issues:**
- "No forecast generated" → Company may not have enough historical data
- "Method not available" → Try a different model or use "auto"
- "Generic snapshot instead of forecast" → Make sure you use forecasting keywords

---

## 📊 Advanced Features

### 7. **Regime Detection** (Automatic)

When you request a forecast, the system automatically detects market regimes:

- **Bull Market**: Strong upward trends
- **Bear Market**: Declining trends
- **Volatile**: High volatility periods
- **Stable**: Consistent patterns

**Example Output:**
```
📊 MARKET REGIME DETECTION:
- Current Regime: BULL
- Confidence: 85.2%
- Recent Change Points: 2 detected
```

**Note:** Regime detection is automatically included in forecast responses - no special prompt needed.

---

### 8. **Model Explainability** (Automatic)

Forecasts automatically include explainability analysis:

- **Feature Importance**: Which historical periods matter most
- **Attention Weights**: For Transformer models, shows which years the model focuses on
- **Forecast Decomposition**: Breaks down forecast into components (trend, seasonality, etc.)
- **SHAP Values**: Shows contribution of each feature to the forecast

**Example Output:**
```
🔍 MODEL EXPLAINABILITY:
- Feature Importance: 
  * 2020-2021 growth: 35% contribution
  * 2022-2023 trend: 28% contribution
  * Historical average: 22% contribution
```

**Note:** Explainability is automatically included in forecast responses - no special prompt needed.

---

## 📝 Notes

- Forecasts are generated fresh each time (not cached)
- Requires sufficient historical data (typically 5+ years)
- Different models work better for different types of data
- Ensemble method generally provides the most reliable forecasts
- **Regime detection and explainability are automatically included** - they enhance every forecast response

