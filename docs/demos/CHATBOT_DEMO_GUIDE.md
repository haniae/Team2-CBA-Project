# 🎯 Chatbot Demo Guide

A comprehensive guide for demonstrating the BenchmarkOS chatbot functionalities.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Demo Methods](#demo-methods)
3. [Demo Scenarios](#demo-scenarios)
4. [Example Queries by Category](#example-queries-by-category)
5. [Key Features to Highlight](#key-features-to-highlight)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

1. **Ensure database is populated** (if not already):
   ```bash
   # Quick 3-year data ingestion (recommended for demos)
   python scripts/ingestion/fill_data_gaps.py --target-years "2022,2023,2024" --years-back 3 --batch-size 10
   ```

2. **Verify environment is set up**:
   ```bash
   # Activate virtual environment
   .\.venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   
   # Check dependencies
   pip list | findstr fastapi uvicorn  # Windows
   # pip list | grep fastapi uvicorn  # macOS/Linux
   ```

---

## 🎬 Demo Methods

### Method 1: Web Interface (Recommended for Demos)

**Best for:** Live presentations, interactive demos, showing dashboard features

#### Start the Web Server:
```bash
python serve_chatbot.py --port 8000
```

#### Access the Interface:
- **Main Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

#### Features to Demonstrate:
- ✅ Interactive chat interface
- ✅ Real-time dashboard generation
- ✅ Export capabilities (PDF, PowerPoint, Excel)
- ✅ Multi-ticker comparisons
- ✅ Visual charts and graphs
- ✅ Source citations

#### Demo Flow:
1. Open browser to http://localhost:8000
2. Type a question in the chat box
3. Show the dashboard that appears
4. Demonstrate export functionality
5. Show multi-ticker comparisons

---

### Method 2: CLI/Terminal Interface

**Best for:** Technical demos, command-line workflows, testing

#### Start the CLI:
```bash
python run_chatbot.py
# OR
python chat_terminal.py
```

#### Available Commands:
```
help                    - Show available commands
metrics <TICKER>        - Show metrics for a ticker
compare <TICKER1> <TICKER2> - Compare two companies
table <TICKER> <METRIC> - Show tabular data
fact <TICKER> <YEAR> <METRIC> - Inspect raw financial fact
scenario <TICKER> <TYPE> - Run scenario analysis
ingest <TICKER> <YEARS> - Trigger data ingestion
quit / exit             - Exit the chatbot
```

#### Example Session:
```
💬 You: metrics AAPL
🤖 BenchmarkOS: [Shows Apple's metrics]

💬 You: compare AAPL MSFT
🤖 BenchmarkOS: [Shows comparison table]

💬 You: table AAPL revenue net_income
🤖 BenchmarkOS: [Shows ASCII table]
```

---

### Method 3: REST API

**Best for:** Integration demos, programmatic access, API testing

#### Start the Server:
```bash
python serve_chatbot.py --port 8000
```

#### API Endpoints:

**1. Chat Endpoint**
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Apple revenue?"}'
```

**2. Metrics Endpoint**
```bash
curl "http://localhost:8000/api/metrics?ticker=AAPL&start_year=2022&end_year=2024"
```

**3. Export Endpoint**
```bash
# PowerPoint export
curl -o AAPL_deck.pptx "http://localhost:8000/api/export/cfi?format=pptx&ticker=AAPL"

# PDF export
curl -o MSFT_report.pdf "http://localhost:8000/api/export/cfi?format=pdf&ticker=MSFT"
```

#### Interactive API Testing:
Visit http://localhost:8000/docs for interactive Swagger UI

---

## 🎭 Demo Scenarios

### Scenario 1: Executive Overview (5 minutes)

**Goal:** Show quick insights for decision-making

**Queries:**
1. "What's Apple's revenue in 2023?"
2. "Compare Apple and Microsoft profitability"
3. "Show me the Magnificent 7 performance"
4. "Which tech companies have the best margins?"

**Key Points:**
- ✅ Natural language understanding
- ✅ Quick comparisons
- ✅ Company groups support
- ✅ Dashboard generation

---

### Scenario 2: Financial Analysis (10 minutes)

**Goal:** Demonstrate deep financial analysis capabilities

**Queries:**
1. "Analyze Apple's financial performance over the last 5 years"
2. "Compare Tesla and Ford revenue growth YoY"
3. "Show me companies with ROE above 20%"
4. "What are the valuation multiples for big tech?"

**Key Points:**
- ✅ Historical trend analysis
- ✅ Advanced metrics (ROE, ROIC, P/E ratios)
- ✅ Growth rate calculations
- ✅ Multi-dimensional comparisons

---

### Scenario 3: Portfolio Analysis (10 minutes)

**Goal:** Show portfolio management features

**Queries:**
1. "Show me FAANG stocks dashboard"
2. "Compare revenue growth for tech sector companies"
3. "Which companies have the highest free cash flow?"
4. "Show undervalued companies with low P/E ratios"

**Key Points:**
- ✅ Multi-ticker dashboards
- ✅ Sector analysis
- ✅ Valuation screening
- ✅ Export capabilities

---

### Scenario 4: Research & Reporting (10 minutes)

**Goal:** Demonstrate research and export features

**Queries:**
1. "Generate a comprehensive analysis of Microsoft"
2. "Compare Apple, Microsoft, and Google across all metrics"
3. "Export Apple analysis as PowerPoint"
4. "Show me the data sources for Apple's revenue"

**Key Points:**
- ✅ Comprehensive analysis
- ✅ Multi-company comparisons
- ✅ Export functionality (PDF, PPTX, Excel)
- ✅ Source citations and audit trails

---

## 📊 Example Queries by Category

### Basic Questions

```
✅ "What's Apple's revenue?"
✅ "How's Microsoft doing?"
✅ "Show me Tesla's profit margins"
✅ "Tell me about Amazon's performance"
```

### Comparisons

```
✅ "Apple vs Microsoft revenue"
✅ "Which has better margins?"
✅ "Compare Tesla and Ford"
✅ "Who's the most profitable?"
✅ "Compare Magnificent 7 companies"
```

### Trends & Growth

```
✅ "Show me Apple's revenue growth over 5 years"
✅ "Which companies have growing revenue?"
✅ "Compare YoY growth for tech companies"
✅ "Show declining margins in retail sector"
```

### Advanced Metrics

```
✅ "What's Apple's ROE and ROIC?"
✅ "Show me P/E ratios for tech stocks"
✅ "Compare free cash flow margins"
✅ "Which companies have the best operating leverage?"
```

### Company Groups

```
✅ "FAANG stocks performance"
✅ "Magnificent 7 revenue comparison"
✅ "Big Tech profitability analysis"
✅ "Show me cloud providers comparison"
```

### Time Periods

```
✅ "Revenue last quarter"
✅ "YoY growth 2023 vs 2022"
✅ "Performance during the pandemic"
✅ "Data between 2020 and 2023"
```

### Filters & Conditions

```
✅ "Show me tech companies with revenue > $1B"
✅ "Companies with profit margin above 20%"
✅ "Undervalued companies with low P/E"
✅ "High-quality stocks with strong cash flow"
```

### Natural Language

```
✅ "I'm curious about Apple's financial health"
✅ "Can you tell me which company is doing better?"
✅ "What would you recommend for tech investments?"
✅ "Help me understand Microsoft's valuation"
```

---

## 🎯 Key Features to Highlight

### 1. Natural Language Understanding
- ✅ Handles misspellings and typos
- ✅ Understands abbreviations (YoY, P/E, EBITDA)
- ✅ Recognizes company groups (FAANG, Magnificent 7)
- ✅ Context-aware follow-up questions

**Demo Query:**
```
"What's Appel's reveneu?" → Correctly resolves to Apple's revenue
```

### 2. Intelligent Parsing
- ✅ Company name resolution (handles typos, aliases)
- ✅ Time period parsing (FY'24, Q4 2023, last 5 years)
- ✅ Metric inference from context
- ✅ Multi-intent queries

**Demo Query:**
```
"Compare Apple and Microsoft revenue growth during the pandemic"
→ Parses: companies (AAPL, MSFT), metric (revenue), time (2020-2021)
```

### 3. Dashboard Generation
- ✅ Automatic dashboard creation for company queries
- ✅ Multi-ticker comparison dashboards
- ✅ Interactive charts and visualizations
- ✅ Export to PDF, PowerPoint, Excel

**Demo Query:**
```
"Show me Apple's dashboard"
→ Generates comprehensive dashboard with charts
```

### 4. Advanced Analytics
- ✅ Sector benchmarking
- ✅ Anomaly detection
- ✅ Predictive analytics
- ✅ Scenario analysis

**Demo Query:**
```
"Show me sector benchmarks for Apple"
→ Compares Apple to Technology sector averages
```

### 5. Export Capabilities
- ✅ PDF reports
- ✅ PowerPoint presentations (12-slide CFI style)
- ✅ Excel workbooks
- ✅ CSV exports

**Demo Query:**
```
"Export Apple analysis as PowerPoint"
→ Generates professional 12-slide presentation
```

### 6. Source Citations
- ✅ Full audit trail
- ✅ SEC EDGAR links
- ✅ Data source transparency
- ✅ Lineage tracking

**Demo Query:**
```
"Show me data sources for Apple's revenue"
→ Lists all SEC filings used
```

---

## 🔧 Troubleshooting

### Issue: "No data showing up"

**Solution:**
```bash
# Refresh metrics after data ingestion
python -c "from finanlyzeos_chatbot.config import load_settings; from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine; AnalyticsEngine(load_settings()).refresh_metrics(force=True)"
```

### Issue: "Server won't start"

**Solution:**
```bash
# Check if port is already in use
netstat -ano | findstr :8000  # Windows
# lsof -i :8000  # macOS/Linux

# Use a different port
python serve_chatbot.py --port 8001
```

### Issue: "Module not found"

**Solution:**
```bash
# Install package in editable mode
pip install -e .

# Or set PYTHONPATH
$env:PYTHONPATH = (Resolve-Path .\src).Path  # Windows PowerShell
export PYTHONPATH=./src  # macOS/Linux
```

### Issue: "Database not found"

**Solution:**
```bash
# Check database path in .env file
DATABASE_PATH=./data/sqlite/finanlyzeos_chatbot.sqlite3

# Or run data ingestion
python scripts/ingestion/fill_data_gaps.py --target-years "2022,2023,2024" --years-back 3
```

---

## 📝 Demo Checklist

Before starting your demo:

- [ ] Database is populated with data
- [ ] Server starts successfully
- [ ] Test a few queries to ensure everything works
- [ ] Have example queries ready
- [ ] Know which features to highlight
- [ ] Prepare answers for common questions
- [ ] Have backup queries ready if something fails

---

## 🎓 Best Practices

### For Live Demos:

1. **Start Simple**: Begin with basic queries before showing advanced features
2. **Show Progress**: Let audience see the real-time processing
3. **Handle Errors Gracefully**: Have backup queries if something fails
4. **Explain Features**: Don't just show queries, explain what's happening
5. **Demonstrate Export**: Show the export functionality (it's impressive!)
6. **Show Multi-Ticker**: Demonstrate comparison capabilities
7. **Highlight Sources**: Show the audit trail and source citations

### For Technical Demos:

1. **Show Architecture**: Explain the system components
2. **Demonstrate Parsing**: Show how natural language is parsed
3. **Show Database**: Briefly show the data structure
4. **Explain Analytics**: Walk through the analytics engine
5. **Show API**: Demonstrate REST API capabilities

---

## 📚 Additional Resources

- **User Guide**: `docs/NLU_USER_GUIDE.md` - Comprehensive NLU features
- **Quick Reference**: `docs/QUICK_REFERENCE.md` - Quick query examples
- **Technical Guide**: `docs/NLU_TECHNICAL_GUIDE.md` - Developer documentation
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md` - Setup instructions
- **System Overview**: `docs/chatbot_system_overview_en.md` - Architecture details

---

## 🎉 Ready to Demo!

You're all set! Choose a demo method, select a scenario, and start showcasing the chatbot's capabilities.

**Remember:** The chatbot is designed to be conversational and forgiving. Don't worry about perfect syntax - just ask naturally!

---

**Version**: 1.0  
**Last Updated**: January 2025  
**For**: Team 2 CBA Project - BenchmarkOS Chatbot

