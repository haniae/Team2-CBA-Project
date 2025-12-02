# Visualization Capabilities

## ✅ Chart Types Supported

### Fully Implemented

1. **Line Charts** ✅
   - **Use case**: Trends over time
   - **Multiple companies**: Up to 5 companies
   - **Example**: "plot AAPL, MSFT, GOOGL revenue over time"
   - **Features**: Multiple lines with different colors, legends, grid

2. **Bar Charts** ✅
   - **Use case**: Comparisons between companies
   - **Multiple companies**: Up to 10 companies
   - **Example**: "bar chart comparing AAPL, MSFT, GOOGL, AMZN revenue"
   - **Features**: Color-coded bars, value labels, rotated x-axis labels

3. **Pie Charts** ✅
   - **Use case**: Distribution/breakdown of values
   - **Multiple companies**: Up to 10 companies
   - **Example**: "pie chart of AAPL, MSFT, GOOGL, AMZN revenue"
   - **Features**: Percentage labels, color-coded segments

### Detected but Fallback

4. **Scatter Charts** ⚠️
   - **Status**: Detected but falls back to line chart
   - **Example**: "scatter chart of AAPL vs MSFT revenue"
   - **Future**: Will be fully implemented

5. **Heatmaps** ⚠️
   - **Status**: Detected but falls back to bar chart
   - **Example**: "heatmap of correlation between tech companies"
   - **Future**: Will be fully implemented

6. **Area Charts** ⚠️
   - **Status**: Detected but not yet implemented
   - **Future**: Will be implemented

7. **Histograms** ⚠️
   - **Status**: Detected but not yet implemented
   - **Future**: Will be implemented

8. **Box Plots** ⚠️
   - **Status**: Detected but not yet implemented
   - **Future**: Will be implemented

9. **Candlestick Charts** ⚠️
   - **Status**: Detected but not yet implemented
   - **Future**: Will be implemented

---

## ✅ Multiple Companies Support

### Yes, Multiple Companies Are Fully Supported!

**Line Charts:**
- **Limit**: Up to 5 companies
- **Example**: "line chart of AAPL, MSFT, GOOGL, AMZN, META revenue over time"
- **Features**: Each company gets its own line with different color and label

**Bar Charts:**
- **Limit**: Up to 10 companies
- **Example**: "bar chart comparing AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA revenue"
- **Features**: Side-by-side bars for easy comparison

**Pie Charts:**
- **Limit**: Up to 10 companies
- **Example**: "pie chart of AAPL, MSFT, GOOGL, AMZN, META revenue"
- **Features**: Each company gets a slice proportional to its value

### Examples That Work

✅ **Multiple companies with line chart:**
- "plot AAPL, MSFT, GOOGL revenue over time"
- "line chart showing revenue trends for Apple, Microsoft, and Google"
- "show me a trend chart of AAPL, MSFT, AMZN revenue"

✅ **Multiple companies with bar chart:**
- "bar chart comparing AAPL, MSFT, GOOGL, AMZN revenue"
- "compare revenue for Apple, Microsoft, Google, and Amazon using a bar chart"
- "bar chart of tech company revenue" (auto-infers 6 tech companies)

✅ **Multiple companies with pie chart:**
- "pie chart of AAPL, MSFT, GOOGL, AMZN, META revenue"
- "show me a pie chart comparing revenue for Apple, Microsoft, Google, Amazon, and Meta"
- "pie chart of tech company revenue" (auto-infers 6 tech companies)

✅ **Mixed formats:**
- "bar chart of AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, NFLX, INTC, ORCL revenue" (10 companies)
- "compare AAPL vs MSFT vs GOOGL revenue" (3 companies)

---

## 📊 Chart Type Detection

The system automatically detects chart types from keywords:

| Chart Type | Detection Keywords |
|------------|-------------------|
| Line | "line", "trend", "time series", "over time", "historical" |
| Bar | "bar", "column", "compare", "comparison", "versus", "vs" |
| Pie | "pie", "donut", "circle", "breakdown", "distribution" |
| Scatter | "scatter", "correlation" |
| Heatmap | "heatmap", "correlation matrix" |
| Area | "area", "stacked" |

**Default behavior:**
- Single company → Line chart
- Multiple companies → Bar chart
- No chart type specified → Line chart

---

## 🎯 Supported Metrics

The system recognizes these metrics (and more):
- `revenue`, `net_income`, `operating_income`, `gross_profit`
- `total_assets`, `total_liabilities`, `shareholders_equity`
- `cash_from_operations`, `free_cash_flow`
- `eps_diluted`, `eps_basic`
- And many more...

**Default**: If no metric is specified, defaults to "revenue"

---

## 🌐 Company Support

✅ **All S&P 1500+ companies supported:**
- Ticker symbols: Any 1-5 letter ticker (AAPL, MSFT, ZION, AAN, etc.)
- Company names: Resolved via SEC index and ticker resolver
- Sector keywords: "tech company", "financial company", etc.

---

## 📝 Summary

| Feature | Status | Details |
|---------|--------|---------|
| **Line Charts** | ✅ Full | Up to 5 companies |
| **Bar Charts** | ✅ Full | Up to 10 companies |
| **Pie Charts** | ✅ Full | Up to 10 companies |
| **Scatter Charts** | ⚠️ Partial | Detected, falls back to line |
| **Heatmaps** | ⚠️ Partial | Detected, falls back to bar |
| **Multiple Companies** | ✅ Full | 5-10 depending on chart type |
| **S&P 1500+ Support** | ✅ Full | All tickers recognized |
| **Company Names** | ✅ Full | Resolved via ticker resolver |
| **Sector Keywords** | ✅ Full | Auto-infers companies |

---

## 🚀 Future Enhancements

Planned implementations:
- Full scatter chart support
- Full heatmap support
- Area charts
- Histograms
- Box plots
- Candlestick charts
- Support for more than 10 companies in bar/pie charts

