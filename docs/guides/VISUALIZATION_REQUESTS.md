# 📊 Visualization Requests Guide

## Overview

FinalyzeOS now supports **direct visualization requests** in natural language! Users can request specific charts and graphs without breaking the chatbot flow.

## ✅ What's Supported

### Chart Types

You can request the following chart types:

1. **Line Charts** - For trends over time
   - "Show me a line chart of Apple's revenue"
   - "Create a trend graph for Tesla's profit"
   - "Plot Microsoft's revenue over time"

2. **Bar Charts** - For comparisons
   - "Show me a bar chart comparing Apple and Microsoft's revenue"
   - "Create a bar graph of tech company profits"
   - "Compare Tesla vs Ford using a bar chart"

3. **Pie Charts** - For distributions
   - "Show me a pie chart of revenue by company"
   - "Create a pie graph showing market share"

4. **Scatter Charts** - For correlations (coming soon)
   - "Show me a scatter plot of revenue vs profit"

5. **Heatmaps** - For correlation matrices (coming soon)
   - "Create a heatmap of sector correlations"

## 🎯 How to Use

### Basic Syntax

Simply ask for a visualization in natural language:

```
"Show me a chart of Apple's revenue"
"Create a bar graph comparing AAPL and MSFT"
"Plot Tesla's profit margin over time"
"Visualize Microsoft's revenue trend"
```

### Examples

**Single Company Trend:**
```
User: "Show me a line chart of Apple's revenue over the last 5 years"
Bot: [Generates and displays line chart]
```

**Comparison:**
```
User: "Create a bar chart comparing Apple, Microsoft, and Google's revenue"
Bot: [Generates and displays bar chart with all three companies]
```

**Pie Chart:**
```
User: "Show me a pie chart of revenue distribution for tech companies"
Bot: [Generates and displays pie chart]
```

## 🔍 How It Works

1. **Intent Detection**: The system detects visualization keywords in your query
   - Keywords: "chart", "graph", "plot", "visualize", "show me a chart", etc.

2. **Chart Type Detection**: Automatically determines chart type
   - Line charts for trends/time series
   - Bar charts for comparisons
   - Pie charts for distributions

3. **Data Extraction**: Extracts tickers and metrics from your query
   - Tickers: Automatically detected (AAPL, MSFT, TSLA, etc.)
   - Metrics: Detected from keywords (revenue, profit, margin, etc.)

4. **Chart Generation**: Creates the visualization using matplotlib
   - High-quality PNG images
   - Professional styling
   - Embedded in chatbot response

## 🛡️ Error Handling

The system gracefully handles errors without breaking the chatbot:

- **No Tickers Found**: 
  - Response: "I couldn't identify which companies to visualize. Please specify ticker symbols."

- **No Data Available**: 
  - Response: "I couldn't find data for the requested visualization."

- **Chart Generation Failed**: 
  - Response: "I encountered an issue generating the visualization. Please try rephrasing."

## 💡 Tips

1. **Be Specific**: Include ticker symbols for best results
   - ✅ "Show me a chart for AAPL revenue"
   - ❌ "Show me a chart" (too vague)

2. **Specify Chart Type**: Mention the type you want
   - ✅ "Create a bar chart comparing..."
   - ✅ "Show me a line graph of..."

3. **Include Metrics**: Mention the metric you want to visualize
   - ✅ "Chart of Apple's revenue"
   - ❌ "Chart of Apple" (which metric?)

## 🔧 Technical Details

### Implementation

- **Module**: `src/finanlyzeos_chatbot/visualization_handler.py`
- **Integration**: Automatically integrated into chatbot's `ask()` method
- **Priority**: Checked before other intents (high priority)
- **Error Handling**: All errors caught and returned as user-friendly messages

### Chart Generation

- **Library**: matplotlib (non-interactive backend)
- **Format**: PNG images (150 DPI)
- **Storage**: Temporary files (cleaned up automatically)
- **Styling**: Professional, publication-ready charts

### Data Sources

1. **Analytics Engine**: Primary source for metric data
2. **Database**: Fallback for historical data queries
3. **Error Handling**: Graceful degradation if data unavailable

## 🚀 Future Enhancements

Planned improvements:

- [ ] Interactive Plotly charts
- [ ] More chart types (waterfall, candlestick, etc.)
- [ ] Custom styling options
- [ ] Chart export (PDF, PNG, SVG)
- [ ] Multi-metric charts
- [ ] Time period selection
- [ ] Chart templates

## 📝 Examples in Action

### Example 1: Simple Line Chart
```
User: "Show me a chart of Tesla's revenue"
Bot: I've created a line chart showing revenue for TSLA.

[Chart displayed]
```

### Example 2: Comparison Bar Chart
```
User: "Create a bar chart comparing Apple and Microsoft's profit"
Bot: I've created a bar chart showing profit for AAPL, MSFT.

[Bar chart displayed with both companies]
```

### Example 3: Error Handling
```
User: "Show me a chart for XYZ123"
Bot: I couldn't identify which companies to visualize. 
     Please specify ticker symbols (e.g., 'Show me a chart for AAPL').
```

## 🎓 Best Practices

1. **Always specify tickers**: Include company ticker symbols
2. **Mention the metric**: Specify which metric to visualize
3. **Choose chart type**: Mention line, bar, or pie for best results
4. **Be patient**: Chart generation takes 1-2 seconds

---

**Note**: This feature is designed to be non-intrusive. If a visualization request fails, the chatbot continues normally and provides a helpful error message.

