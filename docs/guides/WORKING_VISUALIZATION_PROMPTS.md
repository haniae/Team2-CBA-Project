# Working Visualization Prompts

This document lists all the visualization prompts that are currently working in the FinalyzeOS chatbot.

## ✅ All Tests Passing (6/6)

### Chart Types Supported

The system supports the following chart types:
- **Line charts** - For trends over time
- **Bar charts** - For comparisons
- **Pie charts** - For distributions/breakdowns
- **Area charts** - For stacked data
- **Scatter plots** - For correlations (detected but not fully implemented)
- **Heatmaps** - For correlation matrices (detected but not fully implemented)

---

## Working Prompts by Category

### 1. Pie Chart Prompts

#### With Explicit Tickers
```
✅ "show me a pie chart of AAPL, MSFT, GOOGL revenue"
✅ "create a pie chart showing revenue for AAPL, MSFT, and GOOGL"
✅ "pie chart of AAPL, MSFT, GOOGL revenue"
✅ "show me a pie chart of tech company revenue"
```

#### With Sector Keywords
```
✅ "show me a pie chart of tech company revenue"
✅ "pie chart of financial company revenue"
✅ "pie chart of healthcare company revenue"
```

**Note:** When using sector keywords, the system automatically infers default companies:
- **Tech companies**: AAPL, MSFT, GOOGL, AMZN, META, NVDA
- **Financial companies**: JPM, BAC, WFC, C, GS
- **Healthcare companies**: JNJ, PFE, UNH, ABT, TMO

---

### 2. Bar Chart Prompts

#### Simple Comparisons
```
✅ "create a bar chart comparing AAPL and MSFT revenue"
✅ "bar chart of AAPL, MSFT, AMZN, META revenue"
✅ "show me a bar chart comparing revenue for Apple and Microsoft"
✅ "bar chart comparing AAPL vs MSFT revenue"
```

#### Multiple Companies
```
✅ "bar chart of AAPL, MSFT, AMZN, META revenue"
✅ "create a bar chart showing revenue for AAPL, MSFT, GOOGL, AMZN"
```

---

### 3. Line Chart Prompts

#### Single Company Trends
```
✅ "plot Apple's revenue over time"
✅ "show me a line chart of Tesla revenue"
✅ "create a line chart showing AAPL revenue over time"
✅ "plot revenue for Apple"
```

#### Multiple Companies
```
✅ "line chart of AAPL, MSFT, GOOGL revenue over time"
✅ "plot revenue trends for Apple and Microsoft"
```

---

### 4. Generic Chart Requests

#### Simple Requests
```
✅ "show me a chart of Tesla revenue"
✅ "create a chart showing Apple revenue"
✅ "visualize AAPL revenue"
✅ "plot MSFT revenue"
```

**Note:** Generic chart requests default to **line charts** for single companies and **bar charts** for multiple companies.

---

## Supported Metrics

The system recognizes these metrics (and more):
- `revenue`
- `net_income`
- `operating_income`
- `gross_profit`
- `total_assets`
- `total_liabilities`
- `shareholders_equity`
- `cash_from_operations`
- `free_cash_flow`
- `eps_diluted`
- `eps_basic`
- And many more...

---

## Ticker Recognition

### Explicit Tickers
The system recognizes standard ticker symbols:
- **Tech**: AAPL, MSFT, GOOGL, GOOG, AMZN, META, FB, NVDA, NFLX, TSLA
- **Financial**: JPM, BAC, WFC, C, GS, MS
- **Healthcare**: JNJ, PFE, UNH, ABT, TMO
- And many more...

### Company Name Recognition
The system can also recognize company names:
- "Apple" → AAPL
- "Microsoft" → MSFT
- "Google" → GOOGL
- "Amazon" → AMZN
- "Tesla" → TSLA
- "Meta" or "Facebook" → META
- And more...

---

## Prompt Patterns That Work

### Pattern 1: Direct Request
```
"[chart type] of [tickers] [metric]"
Example: "pie chart of AAPL, MSFT, GOOGL revenue"
```

### Pattern 2: Action Verb
```
"[action] a [chart type] [tickers] [metric]"
Example: "show me a bar chart comparing AAPL and MSFT revenue"
```

### Pattern 3: Company Name
```
"[action] [company name]'s [metric] [over time/chart]"
Example: "plot Apple's revenue over time"
```

### Pattern 4: Sector-Based
```
"[chart type] of [sector] company [metric]"
Example: "show me a pie chart of tech company revenue"
```

### Pattern 5: Comparison
```
"[chart type] comparing [tickers] [metric]"
Example: "bar chart comparing AAPL and MSFT revenue"
```

---

## Important Notes

### Data Availability
- If no real data is available in the database, the system will generate **sample/demonstration data** so you can see how the visualization works
- To use real data, ingest company data first: `"ingest AAPL"` or `"ingest MSFT"`

### Chart Generation
- Charts are generated as PNG images
- Charts are saved to temporary files and referenced in the response
- The response includes markdown image syntax: `![chart type](file_path)`

### Error Handling
- If tickers can't be identified, you'll get a helpful error message
- If metrics can't be identified, the system defaults to "revenue"
- If chart type can't be identified, the system defaults to "line" for single companies or "bar" for multiple companies

---

## Example Responses

### Successful Response
```
I've created a pie chart showing revenue for AAPL, MSFT, GOOGL.

![pie chart](C:\Users\...\temp_file.png)

*Chart generated successfully. The image is available in the response.*
```

### Response with Sample Data
```
I've created a bar chart showing revenue for AAPL, MSFT.

![bar chart](C:\Users\...\temp_file.png)

*Note: No financial data found in database for AAPL, MSFT. 
Chart shows sample/demonstration data. To see real data, 
ingest company data first: 'ingest AAPL' or 'ingest MSFT'.*
```

---

## Testing

All prompts have been tested and verified working. You can run the test suite:

```bash
python quick_test_viz.py
```

Expected output: `Results: 6/6 passed`

---

## Future Enhancements

The following chart types are detected but not yet fully implemented:
- Scatter plots
- Heatmaps
- Area charts (partially implemented)
- Histograms
- Box plots
- Candlestick charts
- Waterfall charts

These will be added in future updates.

