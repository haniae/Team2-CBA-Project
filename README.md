<div align="center">

# 📊 BenchmarkOS Chatbot Platform

### Institutional-Grade Finance Copilot with Explainable AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**BenchmarkOS** is an institutional-grade copilot for finance teams. It pairs deterministic market analytics with a conversational interface so analysts can ask natural-language questions, inspect lineage, and keep data pipelines auditable.

[Quick Start](#quick-start) • [Documentation](docs/) • [Features](#core-capabilities) • [Contributing](CONTRIBUTING.md)

---

</div>

## 🎓 Practicum Context

This repository underpins our Fall 2025 DNSC 6317 practicum at The George Washington University, where we are building and governing an explainable finance copilot that can support regulated teams. Our objectives include stress-testing BenchmarkOS against real analyst workflows, documenting orchestration strategies for enterprise rollouts, and demonstrating responsible AI guardrails around data access, lineage, and scenario planning.

### 👥 Team

- **Hania A.** 
- **Van Nhi Vuong** 
- **Malcolm Muoriyarwa**
- **Devarsh Patel** 
- **Professor Patrick Hall** - Supervising Faculty (The George Washington University)

### 🎯 Project Focus

- 🔧 **Production-Grade Analytics** - Translate classroom techniques into a production-grade analytics assistant that blends deterministic KPI calculations with auditable LLM experiences
- 🛡️ **Resilient Pipelines** - Stand up KPI coverage pipelines that stay resilient when market data lags or filing assumptions drift
- 📚 **Practitioner-Ready Documentation** - Deliver deployment runbooks and testing strategies so stakeholders can re-create the practicum outcomes after the semester concludes

## 💼 User Story and Pain Points

| Main group | Sub-group | Role / examples | Goals when using chatbot | Current pain points | Key needs from chatbot |
|------------|-----------|----------------|-------------------------|-------------------|----------------------|
| Financial industry (professional users) | CFO / FP&A / IR | CFOs, finance directors, investor relations leads | Generate peer comparisons in minutes; ensure KPI standardisation and source traceability | Data collection and reconciliation takes 3–5 days; KPI definitions drift; no audit trail for the board | Peer packets in under five minutes; standardised KPI dictionary with lineage; export-ready reports |
| Corporate development / M&A teams | Corporate development, strategy, M&A analysts | Benchmark targets quickly for acquisitions; compare competitors by segment and geography | Manual benchmarking is slow; limited ability to expand peer sets | Dynamic peer set management; audit trail per KPI; override controls for peers, KPIs, and timeframes |
| Consulting and advisory | Consulting analysts, advisory teams | Deliver rapid, credible benchmarks; produce slide-ready, verifiable outputs | Data gathering and normalisation are time-consuming; clients question credibility without lineage | KPI metrics with click-through lineage; segment normalisation; multi-dimensional benchmarking |
| Non-financial users (non-professional) | Business decision makers | CEOs, COOs, heads of strategy | See competitor and market context without deep finance expertise; decide quickly | Financial data feels complex; no time to compute KPIs; reports lack actionable insights | Strategic summaries tied to KPIs; clear visuals; action-oriented insights |
| Students and learners | Students, researchers, MBA learners | Learn to read 10-K/10-Q filings; understand KPI calculations | Unsure how to compute KPIs; do not know reliable data sources | Step-by-step KPI explanations; guided drill-down from KPI to tables to source filings |
| Semi-professional users | Investors and analysts | Buy-side and sell-side analysts, individual investors | Make faster investment calls with peer benchmarks | Hard to compare multiple companies quickly; limited reliable data sources | Dynamic peer comparisons by ticker; exportable reports; transparent source traceability |

## 📑 Table of Contents

- [🎓 Practicum Context](#-practicum-context)
- [📖 Overview](#-overview)
- [📊 Current Data Coverage](#-current-data-coverage)
- [⚡ Core Capabilities](#-core-capabilities)
- [🚀 Advanced Analytics (Phase 1)](#-advanced-analytics-phase-1---new)
- [🏗️ Architecture Map](#-architecture-map)
- [🧠 Retrieval & ML Internals](#-retrieval--ml-internals)
- [🚀 Quick Start](#-quick-start)
- [💬 Running the Chatbot](#-running-the-chatbot)
- [📥 Data Ingestion Guide](#-data-ingestion-guide)
- [⚙️ Configuration Reference](#-configuration-reference)
- [🗄️ Database Schema](#-database-schema)
- [📁 Project Layout](#-project-layout)
- [📝 File Reference](#-file-reference)
- [✅ Quality and Testing](#-quality-and-testing)
- [🔧 Troubleshooting](#-troubleshooting)
- [📚 Further Reading](#-further-reading)

## 📖 Overview

BenchmarkOS ships as a **batteries-included template** for building finance copilots. Out of the box you gain:

- 🗄️ **Durable Storage** - SQLite by default, PostgreSQL optional for conversations, facts, metrics, audit trails, and scenarios
- 📊 **Analytics Engines** - Normalise SEC filings, hydrate them with market quotes, and expose tabular as well as scenario-ready metrics
- 🤖 **Flexible LLM Integration** - Deterministic echo model for testing or OpenAI for production deployments
- 🖥️ **Multi-Channel Experiences** - CLI REPL, FastAPI REST service, single-page web UI so you can prototype quickly and scale later
- 📚 **Rich Documentation** - Complete guides for scaling "any company" requests and replicating workflows in production

## 📊 Current Data Coverage

The database currently contains **390,966 total rows** of financial data across 475 S&P 500 companies:

| Table | Rows | Description |
|-------|------|-------------|
| metric_snapshots | 319,891 | Pre-calculated analytics and KPIs |
| financial_facts | 33,684 | Raw SEC filing data (revenue, expenses, etc.) |
| company_filings | 23,743 | SEC filing metadata (10-K, 10-Q forms) |
| kpi_values | 9,980 | KPI backfill and override values |
| audit_events | 3,015 | Data ingestion and processing logs |
| ticker_aliases | 475 | Company ticker mappings (S&P 500) |
| conversations | 132 | Chat history and user interactions |
| market_quotes | 46 | Latest market prices and quotes |
| scenario_results | 0 | Saved scenario analysis results |

### 📈 Data Characteristics

- 📅 **Year Range:** 2019-2027 (9 years of coverage)
- 🏢 **Companies:** 475 unique S&P 500 tickers
- 📡 **Data Sources:** SEC EDGAR (10-K, 10-Q filings), Yahoo Finance (market quotes)
- 🔄 **Update Frequency:** On-demand ingestion with smart gap detection
- 🔍 **Audit Trail:** Full lineage tracking for every data point
- 💾 **Database Size:** ~150-200 MB (SQLite file)

### ⚡ Quick Start: First-Time Data Ingestion

If you're setting up BenchmarkOS for the first time, start with a focused ingestion to get familiar with the process:

```bash
# Step 1: Activate your virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # macOS/Linux

# Step 2: Run a quick 3-year ingestion (recommended for first-time users)
python scripts/ingestion/fill_data_gaps.py --target-years "2022,2023,2024" --years-back 3 --batch-size 10

# Expected: ~5-7 minutes, loads ~5,000-8,000 records for 475 companies
```

After this completes, you can:
1. Start the chatbot: `python run_chatbot.py`
2. Try queries like: "Show me Apple's metrics" or "Compare Microsoft and Google"
3. Launch the web UI: `python serve_chatbot.py --port 8000`

## ⚡ Core Capabilities

- 💬 **Multi-Channel Chat** – CLI REPL, REST API endpoints, and browser client with live status indicators
- 📊 **Deterministic Analytics** – Calculate primary/secondary metrics, growth rates, valuation multiples, and derived KPIs from the latest filings and quotes
- 📥 **Incremental Ingestion** – Pull SEC EDGAR facts, Yahoo quotes, and optional Bloomberg feeds with retry/backoff
- 🔒 **Audit-Ready Storage** – Complete metric snapshots, raw financial facts, audit events, and full chat history for compliance reviews
- 🤖 **Extensible LLM Layer** – Toggle between local echo model and OpenAI, or extend for other vendors
- 🔄 **Task Orchestration** – Queue abstraction for ingestion and long-running commands

## 🚀 Advanced Analytics (Phase 1 - NEW)

Four sophisticated analytics modules deliver institutional-grade capabilities:

### 1️⃣ Sector Benchmarking (`sector_analytics.py`)
- 🏭 Compare companies within 11 GICS sectors (Technology, Financials, Healthcare, etc.)
- 📊 Calculate sector-wide averages/medians for all key metrics
- 🏆 Identify top performers and percentile rankings
- 💡 **Example:** "Apple ranks 100th percentile for revenue in Technology with $391B vs sector avg $49B"

### 2️⃣ Anomaly Detection (`anomaly_detection.py`)
- 🔍 Statistical detection using Z-score analysis with configurable thresholds
- ⚠️ Identifies outliers in revenue growth, margins, cash flow, balance sheet ratios
- 🚨 Severity classification (low/medium/high/critical) with confidence scores
- 💡 **Example:** "Revenue growth spike: 51.2% vs historical avg 23.5% (3.2 std devs, high severity)"

### 3️⃣ Predictive Analytics (`predictive_analytics.py`)
- 🔮 Forecast metrics using linear regression and CAGR projections
- 📈 Confidence intervals and trend classification (increasing/decreasing/stable/volatile)
- 🎯 Scenario analysis (optimistic/base/pessimistic)
- 💡 **Example:** "MSFT revenue forecast 2026: $280.9B (CAGR: 13.78%, increasing trend, 66% confidence)"

### 4️⃣ Advanced KPI Calculator (`advanced_kpis.py`)
- 💰 30+ sophisticated ratios: ROE, ROA, ROIC, ROCE, debt-to-equity, interest coverage, FCF metrics
- 📋 Categorized outputs: profitability, liquidity, leverage, efficiency, cash flow
- 💡 **Example:** "Apple: ROE 164.59%, ROIC 49.60%, FCF-to-Revenue 32.66%, Debt-to-Equity 5.41"

**Documentation:** See `docs/PHASE1_ANALYTICS_FEATURES.md` for complete API reference and integration examples.  
**Test Suite:** Run `python test_new_analytics.py` to see live demonstrations with real S&P 500 data.

These modules transform BenchmarkOS into a professional analytics platform comparable to Bloomberg Terminal and FactSet.

## 📊 Portfolio Management 

BenchmarkOS includes comprehensive **portfolio management capabilities** that enable institutional-grade portfolio analysis, optimization, and risk management. The portfolio system supports multiple portfolios, automatic detection from user queries, and sophisticated analytics.

### 🎯 Core Portfolio Features

#### 1. **Portfolio Detection & Management**
- **Automatic Detection**: System automatically detects portfolio-related queries and extracts portfolio identifiers
- **Multiple Portfolios**: Support for managing multiple portfolios simultaneously (e.g., `port_abc123`, `port_xyz789`)
- **Portfolio Upload**: Upload portfolios via CSV files with ticker, weight, or shares+price columns
- **Portfolio Storage**: Persistent storage of portfolio holdings, metadata, and analysis results

#### 2. **Portfolio Holdings Analysis**
- **Holdings Display**: View all tickers, weights, shares, current prices, and market values
- **Fundamental Enrichment**: Automatic enrichment with P/E ratios, dividend yields, ROE, ROIC, and sector classifications
- **Sector Breakdown**: GICS sector classification for all holdings
- **Concentration Metrics**: HHI (Herfindahl-Hirschman Index), top 10 concentration, max weights

**Example Queries:**
```
✅ "Show my portfolio holdings"
✅ "What are the holdings for port_abc123?"
✅ "Show holdings for port_abc123"
✅ "Use portfolio port_abc123"
```

#### 3. **Portfolio Exposure Analysis**
- **Sector Exposure**: Weight breakdown across 11 GICS sectors (Technology, Financials, Healthcare, etc.)
- **Factor Exposure**: Beta, momentum, value, size, and quality factor exposures
- **Concentration Analysis**: HHI, top 10 concentration ratio, maximum position weights
- **Geographic Exposure**: Regional allocation (if available in data)

**Example Queries:**
```
✅ "What's my portfolio exposure?"
✅ "Show portfolio sector exposure"
✅ "Analyze exposure for port_abc123"
✅ "What's my factor exposure?"
```

#### 4. **Portfolio Optimization**
- **Mean-Variance Optimization**: Optimize for maximum Sharpe ratio, minimum variance, or target return
- **Constraint Support**: Sector limits, position limits, turnover constraints
- **Rebalancing Recommendations**: Specific buy/sell recommendations with expected impact
- **Performance Projections**: Expected return, variance, and Sharpe ratio for optimized portfolio

**Example Queries:**
```
✅ "Optimize my portfolio"
✅ "Rebalance portfolio port_abc123"
✅ "Optimize for maximum Sharpe ratio"
```

#### 5. **Performance Attribution (Brinson-Fachler)**
- **Active Return Decomposition**: Total active return broken down into allocation, selection, and interaction effects
- **Top Contributors**: Best performing positions and their contribution to portfolio returns
- **Top Detractors**: Worst performing positions and their impact
- **Sector-Level Analysis**: Which sectors drove portfolio performance

**Example Queries:**
```
✅ "Show portfolio attribution"
✅ "What's driving my portfolio performance?"
✅ "Attribution analysis for port_abc123"
```

#### 6. **Risk Metrics & Stress Testing**
- **CVaR (Conditional Value at Risk)**: Expected shortfall at 95% confidence level
- **VaR (Value at Risk)**: Maximum expected loss at specified confidence level
- **Volatility**: Portfolio volatility and individual position contributions
- **Sharpe Ratio**: Risk-adjusted return metric
- **Sortino Ratio**: Downside risk-adjusted return
- **Tracking Error**: Active risk vs. benchmark (S&P 500)
- **Beta**: Portfolio beta vs. market

**Example Queries:**
```
✅ "What's my portfolio CVaR?"
✅ "Calculate CVaR for port_abc123"
✅ "Portfolio expected shortfall"
✅ "What's my portfolio tracking error?"
```

#### 7. **Scenario Analysis & Stress Testing**
- **Equity Drawdown Scenarios**: Test portfolio performance under market crashes (e.g., -20%, -30%)
- **Sector Rotation Scenarios**: Analyze impact of sector-specific shocks (e.g., tech sector -30%)
- **Custom Scenarios**: Define custom market scenarios with position-specific impacts
- **Monte Carlo Simulation**: Probabilistic scenario analysis with thousands of simulations

**Example Queries:**
```
✅ "What if the market crashes 20%?"
✅ "Stress test my portfolio"
✅ "What happens if tech sector drops 30%?"
✅ "Monte Carlo simulation for port_abc123"
```

#### 8. **ESG & Sustainability Analysis**
- **ESG Scores**: Overall portfolio ESG score and component scores (Environmental, Social, Governance)
- **Holding-Level ESG**: ESG scores for individual positions
- **Sector ESG**: Average ESG scores by sector
- **Controversy Detection**: Portfolio controversy level and flagging of controversial holdings

**Example Queries:**
```
✅ "What's my portfolio ESG score?"
✅ "Show ESG exposure for port_abc123"
✅ "Analyze portfolio ESG"
```

#### 9. **Tax Analysis**
- **Tax Liability Estimation**: Estimated taxes if positions were sold
- **Tax-Adjusted Returns**: Returns after accounting for tax implications
- **Gain/Loss Breakdown**: Unrealized gains and losses by position
- **Holding Period Classification**: Short-term vs. long-term capital gains
- **Wash Sale Detection**: Identification of potential wash sale issues

**Example Queries:**
```
✅ "Tax analysis for my portfolio"
✅ "What's my tax-adjusted return?"
✅ "Tax-aware analysis for port_abc123"
```

#### 10. **Diversification Analysis**
- **Diversification Ratio**: Measure of diversification benefit
- **Effective Number of Holdings**: Equivalent number of equal-weighted positions
- **Risk Contribution Analysis**: Which positions drive portfolio risk
- **Diversification Recommendations**: Specific suggestions to improve diversification

**Example Queries:**
```
✅ "How diversified is my portfolio?"
✅ "Diversification score for port_abc123"
✅ "Show portfolio concentration"
```

#### 11. **Portfolio Export & Reporting**
- **PowerPoint Export**: 12-slide professional presentation with portfolio summary, holdings, exposure charts, performance attribution, risk metrics, and recommendations
- **PDF Export**: Multi-page PDF report with executive summary, holdings table, charts, and risk analysis
- **Excel Export**: Multi-tab workbook with holdings sheet, exposure breakdowns, performance attribution table, and risk metrics

**Example Queries:**
```
✅ "Export portfolio as PowerPoint"
✅ "Generate PDF report for port_abc123"
✅ "Export to Excel"
```

### 📋 Portfolio Data Structure

Portfolios are stored with the following structure:
- **Portfolio ID**: Unique identifier (e.g., `port_abc123`)
- **Holdings**: List of tickers with weights, shares, prices, and market values
- **Metadata**: Creation date, last updated, portfolio name, description
- **Statistics**: Pre-calculated portfolio statistics (P/E, dividend yield, concentration, etc.)
- **Risk Metrics**: Pre-calculated risk metrics (CVaR, VaR, volatility, Sharpe ratio, etc.)
- **Exposure**: Sector and factor exposure breakdowns

### 🔧 Technical Implementation

**Key Files:**
- `src/benchmarkos_chatbot/portfolio.py` - Main portfolio management module
- `src/benchmarkos_chatbot/portfolio_optimizer.py` - Portfolio optimization algorithms
- `src/benchmarkos_chatbot/portfolio_risk_metrics.py` - Risk metric calculations
- `src/benchmarkos_chatbot/portfolio_attribution.py` - Performance attribution (Brinson-Fachler)
- `src/benchmarkos_chatbot/portfolio_scenarios.py` - Scenario analysis and stress testing
- `src/benchmarkos_chatbot/portfolio_export.py` - Export functionality (PowerPoint, PDF, Excel)

**Documentation:** See `docs/guides/PORTFOLIO_QUESTIONS_GUIDE.md` for complete portfolio query examples and response formats.

## 🤖 Machine Learning Forecasting (NEW)

BenchmarkOS includes **sophisticated machine learning forecasting capabilities** that provide institutional-grade financial predictions using multiple ML models. The forecasting system integrates seamlessly with the RAG layer to provide detailed, technically accurate forecasts.

### 🎯 ML Forecasting Models

BenchmarkOS supports **7 different ML forecasting models**, each optimized for different use cases:

#### 1. **ARIMA (AutoRegressive Integrated Moving Average)**
- **Best For**: Short-term forecasts, trend-following patterns
- **Method**: Statistical time series model with auto-regression and moving averages
- **Hyperparameters**: Automatically optimized using AIC/BIC criteria
- **Features**: Handles seasonality, trend decomposition, confidence intervals

#### 2. **Prophet (Facebook's Time Series Forecasting)**
- **Best For**: Seasonal patterns, holidays, long-term trends
- **Method**: Additive time series model with seasonality components
- **Hyperparameters**: Automatically tuned for yearly, weekly, daily seasonality
- **Features**: Handles missing data, outliers, changepoints

#### 3. **ETS (Exponential Smoothing State Space Model)**
- **Best For**: Smooth trends, exponential growth/decay patterns
- **Method**: State space model with error, trend, and seasonality components
- **Hyperparameters**: Automatically selected from 30 possible model configurations
- **Features**: Handles additive/multiplicative trends and seasonality

#### 4. **LSTM (Long Short-Term Memory Neural Network)**
- **Best For**: Complex patterns, non-linear relationships, long-term dependencies
- **Method**: Deep learning recurrent neural network
- **Architecture**: Multi-layer LSTM with dropout, batch normalization
- **Training**: Optimized with Adam optimizer, early stopping, learning rate scheduling
- **Features**: Handles complex patterns, learns from historical data

#### 5. **GRU (Gated Recurrent Unit)**
- **Best For**: Similar to LSTM but faster training, similar accuracy
- **Method**: Simplified RNN architecture with gating mechanisms
- **Architecture**: Multi-layer GRU with dropout and batch normalization
- **Training**: Optimized with Adam optimizer, early stopping
- **Features**: Faster than LSTM, good for real-time forecasting

#### 6. **Transformer (Attention-Based Architecture)**
- **Best For**: Long-term dependencies, complex patterns, attention to important periods
- **Method**: Attention-based neural network architecture
- **Architecture**: Multi-head attention, positional encoding, feed-forward layers
- **Training**: Optimized with Adam optimizer, learning rate scheduling
- **Features**: State-of-the-art for time series with long dependencies

#### 7. **Ensemble (Combines Multiple Models)**
- **Best For**: Maximum accuracy, robust predictions
- **Method**: Weighted combination of ARIMA, Prophet, ETS, LSTM, GRU, and Transformer
- **Weighting**: Optimized based on historical performance
- **Features**: Best accuracy, reduces model-specific errors

#### 8. **Auto (Automatic Model Selection)**
- **Best For**: Ease of use, automatic best model selection
- **Method**: Automatically selects best-performing model based on historical data
- **Selection Criteria**: Cross-validation performance, AIC/BIC, forecast accuracy
- **Features**: No need to specify model - system picks the best one

### 📊 Forecasting Capabilities

#### **Supported Metrics:**
- **Revenue/Sales**: Revenue forecasts with growth rates
- **Net Income/Earnings**: Earnings forecasts with margin analysis
- **Free Cash Flow**: Cash flow forecasts with FCF margin
- **EBITDA**: EBITDA forecasts with margin trends
- **Other Metrics**: Profit, margin, EPS, assets, liabilities, and more

#### **Forecast Horizons:**
- **Short-term**: 1-2 years (recommended for ARIMA, Prophet)
- **Medium-term**: 3-5 years (recommended for LSTM, GRU, Transformer)
- **Long-term**: 5+ years (recommended for Ensemble, Auto)

#### **Forecast Outputs:**
- **Point Forecasts**: Predicted values for each period
- **Confidence Intervals**: 95% confidence intervals (upper and lower bounds)
- **Growth Rates**: Year-over-year growth rates and multi-year CAGR
- **Trend Classification**: Increasing, decreasing, stable, or volatile trends
- **Model Confidence**: Confidence score (0-1) indicating forecast reliability
- **Technical Details**: Complete model architecture, hyperparameters, training details

### 🔍 Enhanced RAG Integration

The ML forecasting system is **deeply integrated with the RAG layer** to provide comprehensive, technically detailed forecasts:

#### **1. Explicit Data Dump Section**
- **Purpose**: Ensures LLM receives ALL technical details in structured format
- **Content**: Model architecture, hyperparameters, training details, computational details, model-specific parameters
- **Format**: Key-value pairs for easy extraction and inclusion in responses
- **Mandate**: LLM is explicitly instructed to include EVERY value from this section

#### **2. Enhanced Context Building**
The `context_builder.py` module builds comprehensive ML forecast context including:
- **Forecast Values**: All predicted values with confidence intervals
- **Model Details**: Complete technical specifications (layers, units, epochs, loss, learning rate, batch size, etc.)
- **Training Process**: Training loss, validation loss, early stopping, learning rate schedule
- **Data Preprocessing**: Scaling methods, outlier handling, missing data treatment
- **Feature Engineering**: Features created for the model
- **Model Selection**: Why this model was chosen, alternative models considered
- **Performance Metrics**: Training metrics, validation metrics, forecast accuracy
- **Forecast Analysis**: Year-over-year growth, CAGR, confidence interval uncertainty
- **Sector Comparison**: How forecast compares to sector averages and peers
- **Scenario Analysis**: Bull/base/bear scenarios based on confidence intervals
- **Risk Analysis**: Model confidence, downside risks, upside opportunities

#### **3. Response Verification**
The `ml_response_verifier.py` module ensures responses include all required technical details:
- **Strict Mode**: When "EXPLICIT DATA DUMP" is present, verifies exact value matches
- **Required Checks**: Verifies presence of model architecture, hyperparameters, training details, computational details
- **Enhancement**: Automatically appends missing technical details if LLM response is incomplete
- **Categorization**: Groups missing details by category (architecture, training, hyperparameters, etc.)

#### **4. System Prompt Enhancements**
The chatbot system prompt includes explicit instructions for ML forecasts:
- **Mandatory Inclusion**: Instructions to include EVERY value from "EXPLICIT DATA DUMP"
- **No Summarization**: Explicit prohibition against summarizing technical details
- **Exact Values**: Instructions to use exact numerical values (e.g., "training loss is 0.001234" not "training loss is low")
- **Technical Depth**: Minimum 500-1000 words for forecast responses
- **Professional Formatting**: Markdown formatting guidelines for professional presentation

### 📋 Example Forecast Queries

#### **Basic Forecasts:**
```
✅ "Forecast Apple's revenue"
✅ "Predict Microsoft's revenue for the next 3 years"
✅ "What's the revenue forecast for Tesla?"
✅ "Estimate Amazon's earnings"
✅ "Project Google's free cash flow"
```

#### **Method-Specific:**
```
✅ "Forecast Apple's revenue using ARIMA"
✅ "Predict Tesla's earnings with Prophet"
✅ "LSTM forecast for Microsoft's revenue"
✅ "Transformer forecast for Google's revenue"
✅ "Ensemble forecast for NVIDIA's earnings"
✅ "Auto forecast for Amazon's revenue"
```

#### **Metric-Specific:**
```
✅ "Forecast Apple's revenue"
✅ "Predict Tesla's net income"
✅ "Estimate Microsoft's free cash flow"
✅ "Project Google's EBITDA"
✅ "Forecast NVIDIA's earnings"
```

#### **Time Period-Specific:**
```
✅ "Forecast Apple's revenue for the next 2 years"
✅ "Predict Tesla's earnings for the next 3 years"
✅ "What's the revenue outlook for Microsoft over the next 5 years?"
✅ "Estimate Amazon's revenue for upcoming years"
```

#### **Combined Queries:**
```
✅ "Forecast Apple's revenue using ARIMA for the next 3 years"
✅ "Predict Tesla's earnings with Prophet for the next 5 years"
✅ "What's the LSTM forecast for Google's revenue over the next 3 years?"
✅ "Estimate Microsoft's free cash flow using Transformer for the next 2 years"
```

### 📚 Documentation

- **Complete Prompt Guide**: See `docs/guides/ALL_ML_FORECASTING_PROMPTS.md` for all working forecast prompts
- **Quick Reference**: See `docs/guides/ML_FORECASTING_QUICK_REFERENCE.md` for quick reference guide
- **Technical Details**: See `src/benchmarkos_chatbot/ml_forecasting/` for implementation details

## 🏗️ Architecture Map

See [`docs/architecture.md`](docs/architecture.md) for the complete component diagram. The latest revision includes the structured parsing pipeline (alias_builder.py, parse.py, time_grammar.py) and the retrieval layer that feeds grounded artefacts into the LLM alongside the existing CLI, FastAPI, analytics, and ingestion components.

## 🧠 Retrieval & ML Internals

BenchmarkOS combines **deterministic data prep** with **retrieval-augmented generation (RAG)** so every answer traces back to persisted facts. The RAG layer has been significantly enhanced to support portfolio management and machine learning forecasting with comprehensive technical details.

### 🔤 Natural-Language Parsing (Deterministic)

- src/benchmarkos_chatbot/parsing/alias_builder.py loads a generated aliases.json covering the S&P 500. It normalises free-text mentions, resolves ticker aliases, applies manual overrides (Alphabet, Berkshire share classes, JP Morgan, AT&T), and when needed performs a fuzzy fallback and emits warnings.
- parse_to_structured in parsing/parse.py orchestrates alias resolution, metric synonym detection, and the flexible time grammar (time_grammar.py). It returns a strict JSON intent schema that downstream planners consume and store (conversation.last_structured_response["parser"]).
- **Portfolio Detection**: The parser automatically detects portfolio-related queries and extracts portfolio identifiers (e.g., `port_abc123`) from user queries.
- **ML Forecast Detection**: The parser detects forecast-related keywords (`forecast`, `predict`, `estimate`, `projection`, etc.) and routes queries to the ML forecasting system.

### 🔍 Retrieval Layer (RAG)

- 📊 Structured intents route directly into AnalyticsEngine, reading metric snapshots, KPI overrides, and fact tables from SQLite/Postgres
- 🔐 Retrieved artefacts (tables, benchmark comparisons, audit trails) become RAG "system" messages that condition the LLM, ensuring no fabricated values slip through
- **Portfolio Context**: When portfolio queries are detected, the system retrieves portfolio holdings, exposure data, risk metrics, and attribution results from the portfolio database
- **ML Forecast Context**: When forecast queries are detected, the system retrieves historical time series data, runs ML forecasting models, and builds comprehensive technical context including model architecture, hyperparameters, training details, and forecast results
- **Multi-Source Aggregation**: The RAG layer aggregates data from multiple sources (SEC EDGAR, Yahoo Finance, FRED, IMF) to provide comprehensive context for financial queries

### 🎯 Generation / Machine Learning

- 🤖 `llm_client.py` abstracts provider selection (local echo vs. OpenAI). The model verbalises retrieved metrics, summarises trends, and surfaces parser warnings
- 📈 Scenario and benchmarking flows blend deterministic calculations (growth rates, spreads) with LLM narration, preserving numeric accuracy while keeping explanations natural
- **Enhanced ML Forecast Responses**: The system prompt includes explicit instructions for ML forecasts, mandating inclusion of ALL technical details from the "EXPLICIT DATA DUMP" section. The `ml_response_verifier.py` module post-processes responses to ensure all required technical details are present.
- **Portfolio Response Enhancement**: The system prompt includes explicit instructions for portfolio analysis, mandating use of actual portfolio data (tickers, weights, metrics) and prohibiting hallucination of portfolio details.
- **Response Verification**: The `ml_response_verifier.py` module verifies ML forecast responses include all required technical details (model architecture, hyperparameters, training details, computational details) and automatically enhances responses if details are missing.

### 🔧 RAG Enhancements for ML Forecasting

The RAG layer has been significantly enhanced to support detailed ML forecasting:

#### **1. Explicit Data Dump Section**
- **Purpose**: Ensures LLM receives ALL technical details in structured format
- **Content**: Model architecture (layers, units, activation functions), hyperparameters (learning rate, batch size, epochs), training details (loss values, validation metrics), computational details (training time, memory usage), model-specific parameters (ARIMA orders, Prophet seasonality, LSTM/GRU/Transformer architecture)
- **Format**: Key-value pairs for easy extraction and inclusion in responses
- **Mandate**: LLM is explicitly instructed to include EVERY value from this section without summarization

#### **2. Enhanced Context Building**
The `context_builder.py` module builds comprehensive ML forecast context including:
- **Forecast Values**: All predicted values with 95% confidence intervals (upper and lower bounds)
- **Model Details**: Complete technical specifications (layers, units, epochs, loss, learning rate, batch size, optimizer, activation functions, dropout rates, etc.)
- **Training Process**: Training loss, validation loss, early stopping criteria, learning rate schedule, convergence metrics
- **Data Preprocessing**: Scaling methods (standardization, normalization), outlier handling, missing data treatment, feature engineering
- **Model Selection**: Why this model was chosen, alternative models considered, model comparison metrics
- **Performance Metrics**: Training metrics (loss, accuracy), validation metrics, forecast accuracy (MAE, RMSE, MAPE), cross-validation scores
- **Forecast Analysis**: Year-over-year growth rates, multi-year CAGR, confidence interval uncertainty analysis
- **Sector Comparison**: How forecast compares to sector averages and peers, percentile rankings
- **Scenario Analysis**: Bull/base/bear scenarios based on confidence intervals, upside potential, downside risk
- **Risk Analysis**: Model confidence scores, downside risks, upside opportunities, data quality warnings

#### **3. Response Verification & Enhancement**
The `ml_response_verifier.py` module ensures responses include all required technical details:
- **Strict Mode**: When "EXPLICIT DATA DUMP" is present, verifies exact value matches (not just keyword mentions)
- **Required Checks**: Verifies presence of model architecture, hyperparameters, training details, computational details, model-specific parameters
- **Enhancement**: Automatically appends missing technical details if LLM response is incomplete, grouped by category (architecture, training, hyperparameters, computational, other)
- **Categorization**: Groups missing details by category for better readability when appending to response

#### **4. System Prompt Enhancements**
The chatbot system prompt includes explicit instructions for ML forecasts:
- **Mandatory Inclusion**: Instructions to include EVERY value from "EXPLICIT DATA DUMP" without summarization
- **No Summarization**: Explicit prohibition against summarizing technical details (e.g., "training loss is low" is prohibited - must say "training loss is 0.001234")
- **Exact Values**: Instructions to use exact numerical values from the context (e.g., "training loss is {X.XXXXXX}" not "training loss is low")
- **Technical Depth**: Minimum 500-1000 words for forecast responses, suitable for institutional analysts
- **Professional Formatting**: Markdown formatting guidelines for professional presentation (headers, bold text, lists, tables, blockquotes)

### 🔧 RAG Enhancements for Portfolio Management

The RAG layer has been enhanced to support comprehensive portfolio analysis:

#### **1. Portfolio Context Building**
The `context_builder.py` module builds comprehensive portfolio context including:
- **Holdings Data**: All tickers, weights, shares, prices, market values, sectors, fundamental metrics
- **Exposure Analysis**: Sector exposure, factor exposure (beta, momentum, value, size, quality), concentration metrics (HHI, top 10 concentration)
- **Portfolio Statistics**: Weighted average P/E, dividend yield, ROE, ROIC, concentration ratios, diversification metrics
- **Risk Metrics**: Pre-calculated CVaR, VaR, volatility, Sharpe ratio, Sortino ratio, tracking error, beta
- **Performance Attribution**: Brinson-Fachler attribution with allocation, selection, and interaction effects
- **Scenario Results**: Stress test results, scenario analysis outcomes, Monte Carlo simulation results

#### **2. Portfolio Response Instructions**
The system prompt includes explicit instructions for portfolio analysis:
- **Use Actual Data**: Mandates use of actual portfolio data (tickers, weights, metrics) from the portfolio context
- **No Hallucination**: Explicit prohibition against making up portfolio data - must use data from context
- **Quote Exact Numbers**: Instructions to reference exact tickers, weights, and metrics (e.g., "AAPL is 15.2% of the portfolio")
- **Specific Recommendations**: Instructions to provide specific rebalancing actions based on actual portfolio composition
- **Risk Metric Usage**: Instructions to use pre-calculated risk metrics from portfolio context, not estimate them

#### **3. Multi-Source Portfolio Context**
The RAG layer aggregates portfolio data from multiple sources:
- **SEC Filings**: 10-K, 10-Q filings for top holdings
- **Yahoo Finance**: Real-time prices, analyst ratings, market data
- **Portfolio Database**: Holdings, weights, historical performance, risk metrics
- **Sector Analytics**: Sector benchmarks, peer comparisons, percentile rankings

### 🛠️ Tooling & Coverage

Regenerate the alias universe with:
```bash
export PYTHONPATH=./src
python scripts/generate_aliases.py
```

The script reads data/tickers/universe_sp500.txt, applies the same normalisation rules as runtime, and rewrites aliases.json with coverage stats.

Guardrails live in tests/test_alias_resolution.py, tests/test_time_grammar.py, and tests/test_nl_parser.py, ensuring alias coverage, period parsing, and structured intents stay within spec.

## 🚀 Quick Start

These steps assume Python 3.10+ and Git are installed.

### 1️⃣ Clone and Set Up Virtual Environment

```bash
git clone https://github.com/haniae/Team2-CBA-Project.git
cd Team2-CBA-Project
python -m venv .venv
# PowerShell
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env   # PowerShell
# cp .env.example .env        # macOS/Linux
```

### 📊 PowerPoint Export & Analyst Documentation

The PowerPoint export generates a comprehensive **12-slide CFI-style presentation** suitable for client presentations, investment committee meetings, and academic deliverables. Each deck is automatically generated from live dashboard data with **zero manual formatting required**.

**Slide Structure (12 pages):**
1. **Cover Page** – Company name, ticker, date, Team 2 branding with diagonal accent
2. **Executive Summary** – 3-5 data-driven analyst bullets + 8-KPI panel (Revenue, EBITDA, FCF, EPS, EV/EBITDA, P/E, Net Debt, ROIC)
3. **Revenue & EBITDA Growth** – Column chart for revenue + commentary with YoY growth and CAGR calculations
4. **Valuation Multiples vs Time** – Line chart for EV/EBITDA and P/E trends vs 5-year average
5. **Share Price Performance** – Price chart with 50/200-DMA and 52-week high/low analysis
6. **Cash Flow & Leverage** – Free cash flow chart + leverage metrics table (Net Debt/EBITDA, Coverage)
7. **Forecast vs Actuals** – Earnings surprise analysis (EPS & Revenue vs consensus estimates)
8. **Segment / Geographic Mix** – Business unit breakdown with revenue contribution analysis
9. **DCF & Scenario Analysis** – Bull/Base/Bear valuation scenarios with WACC and terminal growth assumptions
10. **Peer Comparison** – Scatter plot of EV/EBITDA vs EBITDA Margin with focal company highlighted
11. **Risk Considerations** – 3-5 automated risk bullets derived from leverage, margin trends, and valuation signals
12. **Data Sources & Appendix** – Clickable hyperlinks to SEC EDGAR, Yahoo Finance, and internal database

**Visual Standards (CFI Style):**
- **Color Palette:** Deep navy `#0B214A`, mid blue `#1E5AA8`, slate grey for gridlines and text
- **Typography:** Titles 20-24pt semibold, body 11-14pt, small-caps labels, clean margins
- **Layout:** Navy title bar with company + date; footer with page numbers and "Prepared by Team 2"
- **Charts:** Thin gridlines, transparent backgrounds, compact numeric labels ($2.1B / 13.4%)

**Analytics Auto-Generated:**
- **Growth Metrics:** YoY and CAGR (3y/5y) for Revenue, EBITDA, FCF with momentum tagging
- **Profitability:** EBITDA margin trend with ±150 bps change flags
- **Valuation:** EV/EBITDA and P/E vs 5-year average with rich/cheap/in-line interpretation
- **Cash Quality:** FCF trend analysis with leverage ratio warnings (Net Debt/EBITDA > 3.5x)
- **Risk Signals:** Automated bullets for margin compression, negative FCF, elevated leverage

**Data Sources (Embedded as Hyperlinks):**
- [SEC EDGAR Company Filings](https://www.sec.gov/edgar/searchedgar/companysearch.html)
- [SEC Financial Statement & Notes Datasets](https://www.sec.gov/dera/data/financial-statement-and-notes-data-sets.html)
- [Yahoo Finance Market Data](https://finance.yahoo.com)
- [BenchmarkOS GitHub Repository](https://github.com/haniae/Team2-CBA-Project)

**Usage Examples:**

*Via API (Direct Download):*
```bash
# Generate PowerPoint for Apple
curl -o AAPL_deck.pptx "http://localhost:8000/api/export/cfi?format=pptx&ticker=AAPL"

# Generate PDF report for Microsoft
curl -o MSFT_report.pdf "http://localhost:8000/api/export/cfi?format=pdf&ticker=MSFT"

# Generate Excel workbook for Tesla
curl -o TSLA_data.xlsx "http://localhost:8000/api/export/cfi?format=xlsx&ticker=TSLA"
```

*Via Dashboard (UI):*
1. Navigate to `http://localhost:8000`
2. Ask: "Show me [Company Name]'s financial performance"
3. Scroll to bottom of dashboard
4. Click **"Export PowerPoint"** button
5. File downloads automatically: `benchmarkos-{ticker}-{date}.pptx`

*Programmatic (Python SDK):*
```python
from benchmarkos_chatbot import AnalyticsEngine, load_settings
from benchmarkos_chatbot.export_pipeline import generate_dashboard_export

# Initialize engine
settings = load_settings()
engine = AnalyticsEngine(settings)

# Generate PowerPoint
result = generate_dashboard_export(engine, "AAPL", "pptx")

# Save to file
with open("AAPL_analysis.pptx", "wb") as f:
    f.write(result.content)
```

**Quality Assurance Checklist:**
- [ ] Company name and ticker are correct on cover slide
- [ ] As-of date reflects latest data refresh
- [ ] Charts render correctly (no placeholders) for Revenue, EBITDA, Valuation
- [ ] KPI values are reasonable (no `NaN`, `Infinity`, negative multiples)
- [ ] Commentary bullets are grammatically correct and data-driven
- [ ] Footer page numbers are sequential (Page 1 of 12, 2 of 12, ...)
- [ ] Color palette matches CFI standard (Navy #0B214A, Blue #1E5AA8)
- [ ] File size < 10 MB for email distribution

**Target Audience:**
- **Financial Analysts** – Equity research, investment banking, corporate finance
- **Investment Committees** – Board presentations, portfolio reviews
- **Academic Use** – MBA case studies, finance courses, professor deliverables
- **Client Presentations** – Pitch decks, quarterly business reviews

---

### 2️⃣ Configure Environment Defaults

Open `.env` and update database paths, API keys, and provider toggles. Prefer not to store an OpenAI key in the repo? Put it in `~/.config/benchmarkos-chatbot/openai_api_key` and the loader will pick it up automatically.

### 3️⃣ (Optional) Warm the Datastore

SQLite tables are created lazily, but you can preload metrics with:

```bash
python scripts/ingestion/ingest_universe.py --years 5 --chunk-size 25 --sleep 2 --resume
```

This pulls the sample watch list, respects SEC rate limits, and writes audit events.

## 💬 Running the Chatbot

### 🖥️ CLI REPL

```bash
python run_chatbot.py
```

Inside the prompt, type help to see available commands. Common examples:

| Command | Example | What it does |
|---------|---------|--------------|
| metrics | metrics AAPL 2022-2024 | Latest and historical KPI block for one ticker. |
| compare | compare MSFT NVDA 2023 | Side-by-side metrics table. |
| table | table TSLA metrics revenue net_income | Renders a low-level ASCII table (useful in tests). |
| fact | fact AMZN 2023 revenue | Inspect a normalised financial fact. |
| scenario | scenario GOOGL bull rev=+8% mult=+0.5 | Run a what-if scenario with metric deltas. |
| ingest | ingest SHOP 5 | Trigger live ingestion (SEC, Yahoo, optional Bloomberg). |

Comparison responses append an "S&P 500 Avg" column highlighting how each ticker stacks up on margins, ROE, and valuation multiples.

### 🌐 FastAPI + SPA

```bash
python serve_chatbot.py --port 8000
# or run the ASGI app directly
uvicorn benchmarkos_chatbot.web:app --reload --port 8000
```

Navigate to `http://localhost:8000`. The SPA exposes:

- ⏱️ **Real-time Request Timeline** - Intent, cache, context, compose with slow-step hints
- 📤 **Export Shortcuts** - CSV, PDF and in-line benchmarks
- ⚙️ **Settings Panel** - Toggle data sources, timeline detail, and export defaults

### 🔌 REST Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| POST | /chat | Submit a prompt. Returns reply, conversation_id, structured artefacts, and progress events. |
| GET | /metrics | Retrieve numeric metrics for one or more tickers (start_year / end_year filters supported). |
| GET | /facts | Fetch normalised financial facts backing the numbers. |
| GET | /audit | View the latest ingestion/audit events for a ticker. |
| GET | /health | Basic readiness/liveness check for load balancers. |

The /chat response includes structured extras (highlights, trends, comparison_table, citations, exports, conclusion) so downstream integrations can reuse the analytics without re-parsing text.

## 📥 Data Ingestion Guide

BenchmarkOS provides **multiple ingestion strategies** to fit different use cases. This section explains how to populate your database with financial data.

### ⭐ Recommended: Smart Gap Filling Script

The `fill_data_gaps.py` script is the **easiest and most powerful** way to ingest data. It automatically:
- Detects which companies are missing data for specified years
- Fetches data from SEC EDGAR with intelligent rate limiting
- Handles retries and failures gracefully
- Provides real-time progress tracking
- Generates comprehensive completion reports

#### Basic Usage Examples

```bash
# 1. Quick Start: Get last 3 years of data (recommended for first-time users)
python scripts/ingestion/fill_data_gaps.py --target-years "2022,2023,2024" --years-back 3 --batch-size 10
# Time: ~5-7 minutes | Records: ~5,000-8,000 | Companies: 475

# 2. Recent History: Last 5 years for analysis
python scripts/ingestion/fill_data_gaps.py --target-years "2020,2021,2022,2023,2024" --years-back 5 --batch-size 10
# Time: ~8-12 minutes | Records: ~12,000-15,000 | Companies: 475

# 3. Full Historical Data: 20 years for long-term trends
python scripts/ingestion/fill_data_gaps.py \
  --target-years "2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025" \
  --years-back 20 \
  --batch-size 10
# Time: ~25-35 minutes | Records: ~50,000-80,000 | Companies: 475

# 4. Fill Specific Gap Years Only
python scripts/ingestion/fill_data_gaps.py --target-years "2019,2020" --years-back 7 --batch-size 10
# Time: ~3-5 minutes | Fills only missing 2019 and 2020 data
```

#### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--target-years` | "2019,2020,2025" | Comma-separated years to check and fill |
| `--years-back` | 7 | How many years of data to fetch from SEC API |
| `--batch-size` | 10 | Number of companies to process per batch |
| `--max-tickers` | None | Limit ingestion to first N companies (for testing) |
| `--dry-run` | False | Show what would be ingested without actually doing it |

#### Windows PowerShell Shortcut

```powershell
# One-command 20-year ingestion
.\run_data_ingestion.ps1

# This runs the full historical ingestion automatically
```

#### Understanding the Output

While running, you'll see:
```
================================================================================
FILLING DATA GAPS - MAKING ALL YEARS SOLID
================================================================================
Target years: 2022, 2023, 2024
Years to fetch from SEC: 3
Batch size: 10
Started at: 2025-10-23 15:30:00 UTC

📊 Loading existing tickers from database...
   Found 475 tickers in database
🔍 Checking coverage for years: 2022, 2023, 2024...
   156 companies missing data for these years
🚀 Starting ingestion of 475 tickers...
   This will take approximately 1.2 minutes

[1/48 - 2.1%] Processing: AAPL, ABBV, ABNB, ABT, ACGL, ACN, ADBE, ADI, ADM, ADP
   ✅ Loaded 335 records (Total: 335)
[2/48 - 4.2%] Processing: ADSK, AEP, AES, AFL, AIG, AIZ, AJG, AKAM, ALB, ALGN
   ✅ Loaded 318 records (Total: 653)
...
📊 Progress Report:
   Batches processed: 10/48
   Total records loaded: 3,249
   Successes: 100
   Failures: 0
...
🔄 Refreshing derived metrics...
   ✅ Metrics refreshed
📄 Summary saved to: fill_gaps_summary.json
================================================================================
INGESTION COMPLETE
================================================================================
✅ Successfully ingested: 475 companies
📊 Total records loaded: 15,889
🎉 All companies ingested successfully!
```

#### After Ingestion Completes

Check your data:
```bash
# View row counts per table
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/benchmarkos_chatbot.sqlite3'); cursor = conn.cursor(); tables = ['financial_facts', 'company_filings', 'metric_snapshots', 'kpi_values']; [print(f'{t}: {cursor.execute(f\"SELECT COUNT(*) FROM {t}\").fetchone()[0]:,}') for t in tables]; conn.close()"

# Check year coverage
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/benchmarkos_chatbot.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT ticker) FROM financial_facts'); print('Years: %s-%s | Companies: %s' % cursor.fetchone()); conn.close()"
```

### Alternative: Legacy Batch Scripts

These scripts are available for specific use cases but `fill_data_gaps.py` is generally easier:

| Script | When to use it | Example |
|--------|---------------|---------|
| `scripts/ingestion/ingest_universe.py` | Refresh a watch list with resume support and polite rate limiting. | `python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2 --resume` |
| `scripts/ingestion/batch_ingest.py` | Pull the built-in mega-cap list through ingest_live_tickers with retry/backoff. | `python scripts/ingestion/batch_ingest.py` |
| `scripts/ingestion/load_prices_yfinance.py` | Refresh market quotes from Yahoo Finance. | `python scripts/ingestion/load_prices_yfinance.py` |

### On-Demand Ingestion

AnalyticsEngine.get_metrics calls ingest_live_tickers when it detects missing coverage. You can route this through tasks.TaskManager to queue and monitor ingestion jobs—see inline docstrings for patterns.

All scripts honour the configuration from load_settings() and write audit events so the chatbot can justify sourcing decisions.

### Price-refresh workflow

Use this to keep price-driven ratios current without re-ingesting everything:

```bash
pip install yfinance  # one-time
$env:SEC_TICKERS = (Get-Content data/tickers/universe_sp500.txt) -join ','
# Optional Postgres target
$env:PGHOST='127.0.0.1'; $env:PGPORT='5432'
$env:PGDATABASE='secdb'; $env:PGUSER='postgres'; $env:PGPASSWORD='your_password_here'
python scripts/ingestion/load_prices_yfinance.py

$env:PYTHONPATH = (Resolve-Path .\src).Path
python - <<'PY'
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
AnalyticsEngine(load_settings()).refresh_metrics(force=True)
PY
```

Restart serve_chatbot.py afterwards so the SPA sees the refreshed metrics.

## 📊 Ingest and Quote Loading (Quick Guide)

### ✅ Prerequisites

- Python 3.10+
- Create/activate venv and install deps:
  ```bash
python -m venv .venv
  source .venv/bin/activate  # PowerShell: .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
pip install -e .
  ```
- Optional but recommended for SEC: set a descriptive User-Agent (not a token):
  ```bash
  export SEC_API_USER_AGENT="BenchmarkOSBot/1.0 (you@example.com)"
  ```

### Ingest the S&P 500 into SQLite

SQLite path defaults to data/sqlite/benchmarkos_chatbot.sqlite3 (configurable via DATABASE_PATH).

Pick one of the following forms (both equivalent if you ran pip install -e .).

Module form:
```bash
python -m scripts.ingestion.ingest_universe --universe sp500 --years 10 --chunk-size 25 --sleep 2
```

Script path form:
```bash
python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2
```

Notes:

- --years 10 pulls the most recent 10 fiscal years (cutoff = current_year - years + 1).
- The job uses a progress file .ingestion_progress.json so re-runs can --resume where they left off.
- If you see "Nothing to do" but the DB is empty, delete the progress file and re-run:
  ```bash
  rm -f .ingestion_progress.json
  ```

Verify counts:

```python
python - <<'PY'
import sqlite3, json
p='data/sqlite/benchmarkos_chatbot.sqlite3'
con=sqlite3.connect(p)
print(json.dumps({t: con.execute('select count(*) from '+t).fetchone()[0] for t in [
  'financial_facts','company_filings','market_quotes','metric_snapshots','audit_events','ticker_aliases'
]}, indent=2))
PY
```

### Load market quotes (so price-based ratios populate)

Load via Yahoo Finance in batches to avoid rate limits. Example: load all tickers already present in the DB, 50 per batch:

```python
python - <<'PY'
import os, time, sqlite3, subprocess
db='data/sqlite/benchmarkos_chatbot.sqlite3'
con=sqlite3.connect(db)
tickers=[r[0] for r in con.execute("SELECT DISTINCT ticker FROM financial_facts ORDER BY ticker")]
BATCH=50
for i in range(0,len(tickers),BATCH):
    os.environ['SEC_TICKERS']=",".join(tickers[i:i+BATCH])
    subprocess.run(['python','-m','scripts.ingestion.load_prices_yfinance'], check=False)
    time.sleep(1)
print('Done.')
PY
```

Then refresh analytics snapshots to recalculate P/E, EV/EBITDA, dividend yield, TSR, etc. with the latest prices:

```python
python - <<'PY'
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
AnalyticsEngine(load_settings()).refresh_metrics(force=True)
print('Refreshed metric_snapshots.')
PY
```

Check the latest quote timestamp:

```python
python - <<'PY'
import sqlite3
con=sqlite3.connect('data/sqlite/benchmarkos_chatbot.sqlite3')
print('quotes=',con.execute('select count(*) from market_quotes').fetchone()[0])
print('latest=',con.execute('select max(quote_time) from market_quotes').fetchone()[0])
PY
```

### Windows notes (PowerShell)

- Activate:  .\\.venv\\Scripts\\Activate.ps1
- Use the script path variant if python -m complains about imports:
  ```bash
  python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2
  ```
- If you see ModuleNotFoundError: benchmarkos_chatbot, ensure you ran pip install -e . or set:
  ```bash
  $env:PYTHONPATH = (Resolve-Path .\src).Path
  ```

### Common issues

- "Nothing to do" with --resume: delete .ingestion_progress.json and re-run.
- Yahoo 429: reduce batch size (env YAHOO_QUOTE_BATCH_SIZE) and add small sleeps; retry.
- DB path: override with DATABASE_PATH if you don't want the default under data/sqlite/.

### Coverage universe

docs/ticker_names.md lists every tracked company (482 tickers at generation time). Regenerate it—and keep the parser aligned—whenever the universe changes:

```bash
$env:SEC_TICKERS = (Get-Content data/tickers/universe_sp500.txt) -join ','
python - <<'PY'
import os
from pathlib import Path
import yfinance as yf
root = Path(__file__).resolve().parent
tickers = [
    line.strip()
    for line in (root / "data" / "tickers" / "universe_sp500.txt").read_text().splitlines()
    if line.strip()
]
pairs = []
for ticker in tickers:
    name = None
    try:
        info = yf.Ticker(ticker).info
        name = info.get("longName") or info.get("shortName")
    except Exception:
        name = None
    if not name:
        name = ticker
    pairs.append((ticker, name))
out = root / "docs" / "ticker_names.md"
out.write_text("## Coverage Universe\n\n" + "\n".join(f"- {name} ({ticker})" for ticker, name in pairs), encoding="utf-8")
print(f"Updated {out}")
PY
```

To refresh aliases at the same time:

```bash
export PYTHONPATH=./src
python scripts/generate_aliases.py
```

## ⚙️ Configuration Reference

`load_settings()` reads environment variables (or `.env`) and provides sensible defaults.

| Variable | Default | Notes |
|----------|---------|-------|
| DATABASE_TYPE | sqlite | Switch to postgresql for shared deployments. |
| DATABASE_PATH | ./data/sqlite/benchmarkos_chatbot.sqlite3 | SQLite file location; created automatically. |
| POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD | unset | Required when DATABASE_TYPE=postgresql; POSTGRES_SCHEMA overrides the default sec. |
| LLM_PROVIDER | local | local uses the deterministic echo model; set to openai for real completions. |
| OPENAI_MODEL | gpt-4o-mini | Passed verbatim to the OpenAI Chat Completions API. |
| SEC_API_USER_AGENT | BenchmarkOSBot/1.0 (support@benchmarkos.com) | Mandatory for SEC EDGAR requests. Customize it for your org. |
| EDGAR_BASE_URL | https://data.sec.gov | Override if you proxy or mirror EDGAR. |
| YAHOO_QUOTE_URL | https://query1.finance.yahoo.com/v7/finance/quote | Used to refresh quotes. |
| YAHOO_QUOTE_BATCH_SIZE | 50 | Maximum tickers per Yahoo batch. |
| HTTP_REQUEST_TIMEOUT | 30 | Seconds before HTTP clients give up. |
| INGESTION_MAX_WORKERS | 8 | Thread pool size for ingestion routines. |
| DATA_CACHE_DIR | ./cache | Stores downloaded filings, facts, and progress markers. |
| ENABLE_BLOOMBERG | false | Toggle Bloomberg ingestion; requires host/port/timeout values. |
| BLOOMBERG_HOST, BLOOMBERG_PORT, BLOOMBERG_TIMEOUT | unset | Only used if Bloomberg is enabled. |
| OPENAI_API_KEY | unset | Looked up in env, then keyring, then ~/.config/benchmarkos-chatbot/openai_api_key. |

Secrets belong in your local .env. Windows developers can rely on keyring so API keys live outside the repo.

## 🗄️ Database Schema

BenchmarkOS intentionally supports **two storage backends**, but your deployment uses only one at a time—by default it's SQLite:

- **SQLite (default / implied in this repo)** – shipping the database as a file keeps setup frictionless for development, tests, and CI. All conversations, metrics, and audit events live in the path defined by DATABASE_PATH. For this reason, the stock .env (and most tests such as test_ingestion_perf.py) run purely on SQLite. It was chosen because it "just works": no external server to provision, a trivial backup story, and fast enough for single-user workflows. PRAGMAs (WAL, synchronous=NORMAL, temp_store=MEMORY, cache_size=-16000) are applied automatically so sustained writes remain smooth.
- **PostgreSQL (optional)** – the same helper module can target Postgres when you set DATABASE_TYPE=postgresql and supply the POSTGRES_* DSN variables. Teams switch to Postgres when chat sessions are shared across analysts, when concurrency or replication matters, or when governance requires managed backups. If you haven't changed those settings, Postgres is unused.

In other words, you are currently using a single database—SQLite—because it was selected for simplicity and portability. The PostgreSQL path is documented for teams that choose to run BenchmarkOS in a multi-user/shared environment later.

Regardless of backend, both share the same schema:

### Key tables:

| Table | Purpose | Notable columns |
|-------|---------|-----------------|
| conversations | Stores chat turns for resumable threads. | conversation_id, role, content, created_at |
| cached_prompts | Deduplicates prompts so identical requests reuse cached replies. | prompt_hash, payload, created_at, reply |
| metric_snapshots | Persisted analytics snapshot consumed by the chatbot/UI. | ticker, metric, period, value, start_year, end_year, updated_at, source |
| company_filings | Metadata for SEC filings pulled during ingestion. | ticker, accession_number, form_type, filed_at, data |
| financial_facts | Normalised SEC fact rows (revenues, margins, etc.). | ticker, metric, fiscal_year, period, value, unit, source_filing, raw |
| market_quotes | Latest quotes from Yahoo/Bloomberg/Stooq loaders. | ticker, price, currency, timestamp, source |
| kpi_values | KPI backfill overrides that smooth derived metrics. | ticker, fiscal_year, fiscal_quarter, metric_id, value, method, warning |
| audit_events | Traceability for ingestion and scenario runs. | ticker, event_type, entity_id, details, created_at |
| ticker_aliases | Maps tickers to CIK/company names to speed ingestion. | ticker, cik, company_name, updated_at |

On startup database.initialise() applies schema migrations idempotently. When running in SQLite mode the PRAGMAs mentioned above are applied automatically; switching to Postgres only requires setting the DSN variables—the rest of the code paths remain identical.

## 📁 Project Layout

```
Project/
├── README.md                          # Main project documentation
├── pyproject.toml                     # Project metadata and dependencies
├── requirements.txt                   # Python dependencies
├── env.example                        # Environment configuration template
├── run_chatbot.py                     # CLI chatbot entry point
├── serve_chatbot.py                   # Web server entry point
├── run_data_ingestion.ps1             # Windows ingestion script
├── run_data_ingestion.sh              # Unix ingestion script
├── fill_gaps_summary.json             # Ingestion progress tracking
│
├── scripts/
│   ├── generate_aliases.py            # Regenerate ticker alias universe
│   ├── ingestion/
│   │   ├── fill_data_gaps.py          # ⭐ Recommended: Smart gap-filling script
│   │   ├── ingest_20years_sp500.py    # Full historical ingestion
│   │   ├── batch_ingest.py
│   │   ├── ingest_companyfacts.py
│   │   ├── ingest_companyfacts_batch.py
│   │   ├── ingest_frames.py
│   │   ├── ingest_from_file.py
│   │   ├── ingest_universe.py
│   │   ├── load_prices_stooq.py
│   │   ├── load_prices_yfinance.py
│   │   └── load_ticker_cik.py
│   └── utility/
│       ├── check_database_simple.py   # Database verification
│       ├── check_ingestion_status.py  # Ingestion status checker
│       ├── check_kpi_values.py        # KPI validation
│       ├── monitor_progress.py        # Progress monitoring
│       ├── quick_status.py            # Quick status check
│       ├── show_complete_attribution.py
│       ├── plotly_demo.py             # Plotly chart examples
│       ├── chat_metrics.py
│       ├── data_sources_backup.py
│       └── main.py
│
├── src/
│   └── benchmarkos_chatbot/
│       ├── analytics_engine.py        # Core analytics engine
│       ├── chatbot.py                 # Chatbot orchestration
│       ├── config.py                  # Configuration management
│       ├── data_ingestion.py          # Data ingestion pipeline
│       ├── data_sources.py            # Data source integrations
│       ├── database.py                # Database abstraction layer
│       ├── cfi_ppt_builder.py         # PowerPoint export builder
│       ├── parsing/
│       │   ├── alias_builder.py       # Ticker alias resolution
│       │   ├── aliases.json           # Generated ticker aliases
│       │   ├── ontology.py            # Metric ontology
│       │   ├── parse.py               # Natural language parser
│       │   └── time_grammar.py        # Time period parser
│       ├── llm_client.py              # LLM provider abstraction
│       ├── table_renderer.py          # ASCII table rendering
│       ├── tasks.py                   # Task queue management
│       └── web.py                     # FastAPI web server
│
├── docs/
│   ├── README.md                      # Documentation index
│   ├── architecture.md                # System architecture
│   ├── orchestration_playbook.md      # Deployment guide
│   ├── product_design_spec.md         # Product specifications
│   ├── TEAM_SETUP_GUIDE.md            # Team onboarding
│   ├── INSTALLATION_GUIDE.md          # Installation instructions
│   ├── SETUP_GUIDE.md                 # Setup guide
│   ├── README_SETUP.md                # Setup README
│   ├── README_SP500_INGESTION.md      # S&P 500 ingestion guide
│   ├── EXPAND_DATA_GUIDE.md           # Data expansion guide
│   ├── DATA_INGESTION_PLAN.md         # Ingestion planning
│   ├── PLOTLY_INTEGRATION.md          # Plotly integration docs
│   ├── PHASE1_ANALYTICS_FEATURES.md   # Phase 1 features
│   ├── PHASE1_COMPLETION_SUMMARY.md   # Phase 1 summary
│   ├── ticker_names.md                # Ticker coverage list
│   ├── ui_design_philosophy.md        # UI design principles
│   ├── dashboard_interactions.md      # Dashboard UX patterns
│   ├── chatbot_system_overview_en.md  # System overview
│   ├── DASHBOARD_SOURCES_INSTRUCTIONS.md
│   ├── DASHBOARD_IMPROVEMENTS_COMPLETE.md
│   ├── DASHBOARD_SOURCES_DISPLAY_FIX.md
│   ├── SOURCES_LOCATION_GUIDE.md
│   ├── SOURCES_TROUBLESHOOTING.md
│   ├── SOURCES_DISPLAY_FIXED.md
│   ├── SOURCES_100_PERCENT_COMPLETE_SUMMARY.md
│   ├── 100_PERCENT_SOURCE_COMPLETENESS.md
│   ├── SEC_URLS_FIX_SUMMARY.md
│   ├── SP500_INGESTION_SYSTEM_COMPLETE.md
│   ├── duplicate_files_report.md      # Cleanup report
│   ├── export_pipeline_scope.md
│   ├── prompt_processing_analysis.md
│   ├── command_routing_analysis_report.md
│   ├── DATABASE_DATA_SUMMARY.md
│   ├── EXTENDED_INGESTION_INFO.md
│   ├── RAW_SEC_PARSER_IMPLEMENTATION_GUIDE.md
│   ├── reports/                       # Generated reports
│   │   └── (various analysis and improvement reports)
│   └── analysis/                      # Analysis documentation
│       └── (consolidated analysis reports and documentation)
│
├── data/
│   ├── sample_financials.csv          # Sample data
│   ├── external/
│   │   └── imf_sector_kpis.json       # IMF sector benchmarks
│   ├── sqlite/
│   │   └── benchmarkos_chatbot.sqlite3 (created on demand)
│   └── tickers/
│       ├── universe_sp500.txt         # S&P 500 ticker list
│       ├── sec_top100.txt             # Top 100 companies
│       └── sample_watchlist.txt       # Sample watchlist
│
├── cache/                             # Generated at runtime
│   └── edgar_tickers.json             # Cached EDGAR ticker data
│
├── analysis/
│   ├── experiments/                   # Experimental code
│   │   ├── enhanced_ticker_resolver.py
│   │   ├── fixed_ticker_resolver.py
│   │   └── (other experiments)
│   └── scripts/                       # Analysis scripts
│       └── (analysis and validation scripts)
│
├── tools/
│   └── refresh_ticker_catalog.py     # Ticker catalog management
│
├── webui/
│   ├── index.html                     # Web UI entry point
│   ├── app.js                         # Frontend application logic
│   ├── styles.css                     # UI styling
│   └── static/                        # Static assets
│
└── tests/
    ├── README.md                      # Testing documentation
    ├── test_alias_resolution.py
    ├── test_analytics.py
    ├── test_analytics_engine.py
    ├── test_cli_tables.py
    ├── test_data_ingestion.py
    ├── test_database.py
    ├── test_dashboard_flow.py
    ├── test_new_analytics.py
    ├── test_nl_parser.py
    ├── test_time_grammar.py
    ├── regression/                    # Regression tests
    │   ├── test_ticker_resolution.py
    │   ├── final_comparison_test.py
    │   └── system_integration_test.py
    └── (additional test files)
```

## 📝 File Reference

### 🔧 Root Scripts & Helpers

| File | Description |
|------|-------------|
| scripts/utility/main.py | Rich CLI wrapper exposing metrics/table commands, abbreviations, and scenario helpers. |
| run_chatbot.py | Lightweight REPL entry point that calls BenchmarkOSChatbot.create(). |
| serve_chatbot.py | Convenience launcher for the FastAPI app (src/benchmarkos_chatbot/web.py). |
| scripts/ingestion/batch_ingest.py | Loads the curated watch list with retry/backoff. |
| scripts/ingestion/ingest_universe.py | Batch ingester with resume support; refreshes metrics after each chunk. |
| scripts/ingestion/ingest_frames.py | Downloads SEC data frames into Postgres for benchmarking. |
| scripts/ingestion/load_prices_stooq.py | Imports Stooq prices as a fallback when Yahoo throttles. |
| scripts/generate_aliases.py | Regenerates the S&P 500 alias universe (aliases.json). |
| requirements.txt | Runtime dependency lockfile. |
| pyproject.toml | Project metadata, dependencies, and pytest configuration (adds src/ to PYTHONPATH). |

### 🔤 Parsing & Retrieval Components

| File | Description |
|------|-------------|
| parsing/alias_builder.py | Normalises company mentions, loads alias sets, applies overrides, and resolves tickers with fuzzy fallbacks. |
| parsing/aliases.json | Generated alias universe consumed at runtime. |
| parsing/parse.py | Converts prompts into structured intents (tickers, metrics, periods, warnings). |
| parsing/time_grammar.py | Flexible period parser covering fiscal/calendar ranges, lists, quarters, and relative windows. |

### 🧪 Parser-Focused Tests

| File | Description |
|------|-------------|
| tests/test_alias_resolution.py | Validates alias coverage, manual overrides, fuzzy warnings, and ordering. |
| tests/test_time_grammar.py | Ensures the time grammar handles ranges, lists, quarter formats, and two-digit years. |
| tests/test_nl_parser.py | End-to-end structured intent checks for compare/trend prompts and parser warnings. |

### 🌐 Web Assets

| Path | Description |
|------|-------------|
| webui/app.js | SPA logic, progress timeline updates, settings panel, and chat interactions. |
| webui/styles.css | Styling for the SPA (dark/light friendly, timeline badges, typography). |
| webui/static/data/*.json | Precompiled KPI library and company universe metadata. |

## ✅ Quality and Testing

- Run the suite: `pytest`
- Parser & alias focus: `pytest tests/test_alias_resolution.py tests/test_time_grammar.py tests/test_nl_parser.py`
- Target a single test: `pytest tests/test_cli_tables.py::test_table_command_formats_rows`
- Manual sanity: point LLM_PROVIDER=local to avoid burning API credits during smoke tests.
- Database reset: delete benchmarkos_chatbot.sqlite3 and rerun ingestion—migrations run automatically on startup.

CI isn't configured by default, but pytest -ra (preconfigured in pyproject.toml) surfaces skipped/xfail tests neatly. Consider adding ruff or black once your team standardises formatting.

## 🔧 Troubleshooting

### ⚠️ General Issues

- **"OpenAI API key not found"** – set OPENAI_API_KEY, store it via keyring, or create ~/.config/benchmarkos-chatbot/openai_api_key.
- **WinError 10048 when starting the server** – another process is on the port. Run `Get-NetTCPConnection -LocalPort 8000` and terminate it, or start with `--port 8001`.
- **PostgreSQL auth failures** – confirm SSL/network settings, then double-check POSTGRES_* vars; the DSN is logged at debug level when DATABASE_TYPE=postgresql is active.
- **Pytest cannot locate modules** – run from the repo root so the pythonpath = ["src", "."] entry in pyproject.toml kicks in.

### 📥 Data Ingestion Issues

#### ❌ "No data showing up in chatbot after ingestion"
**Cause:** Metrics need to be refreshed after data ingestion.
**Solution:**
```bash
python -c "from benchmarkos_chatbot.config import load_settings; from benchmarkos_chatbot.analytics_engine import AnalyticsEngine; AnalyticsEngine(load_settings()).refresh_metrics(force=True)"
```
The `fill_data_gaps.py` script does this automatically, but manual ingestion scripts may not.

#### "Yahoo Finance 429 errors during ingestion"
**Cause:** Yahoo Finance rate limits (too many requests too quickly).
**Solution:**
- The script automatically retries with exponential backoff (1s → 2s → 4s → 8s)
- These are warnings, not errors - the process continues
- If persistent, lower `YAHOO_QUOTE_BATCH_SIZE` in your `.env` file:
  ```bash
  YAHOO_QUOTE_BATCH_SIZE=25  # Default is 50
  ```
- Alternative: Use `scripts/ingestion/load_prices_stooq.py` for market data

#### "SEC API returns 403 Forbidden"
**Cause:** Missing or invalid User-Agent header (SEC requires identification).
**Solution:** Set a descriptive User-Agent in your `.env`:
```bash
SEC_API_USER_AGENT="YourCompany/1.0 (your.email@example.com)"
```

#### "Some companies show 'Failed to ingest' messages"
**Cause:** Some tickers may not have SEC filings (delisted, private, or ticker changed).
**Examples from logs:** ALP, BRV, CTL, FIN (these are known issues)
**Solution:** This is expected behavior - the script handles failures gracefully and continues. Check the summary report in `fill_gaps_summary.json` for details.

#### "Ingestion seems slow or stuck"
**Cause:** SEC API rate limiting (10 requests/second limit enforced by script).
**What's normal:**
- 3-year ingestion: 5-7 minutes
- 5-year ingestion: 8-12 minutes
- 20-year ingestion: 25-35 minutes

**Progress indicators to watch:**
```
[10/48 - 20.8%] Processing: CMCSA, CME, CMG, CMI, CMS, CNC, CNP, COF, COO, COP
   ✅ Loaded 331 records (Total: 3,254)
```
If you see new batches completing, the script is working correctly.

#### "Database file not found"
**Cause:** Default database path may differ from your configuration.
**Solution:** Check your `.env` file for `DATABASE_PATH`:
```bash
DATABASE_PATH=./data/sqlite/benchmarkos_chatbot.sqlite3
```
Or use the full path:
```bash
DATABASE_PATH=C:/Users/YOUR_USERNAME/Documents/GitHub/Project/benchmarkos_chatbot.sqlite3
```

#### "ModuleNotFoundError: benchmarkos_chatbot"
**Cause:** Package not installed in editable mode.
**Solution:**
```bash
pip install -e .
# Or set PYTHONPATH manually:
$env:PYTHONPATH = (Resolve-Path .\src).Path  # PowerShell
export PYTHONPATH=./src  # Bash
```

### Verifying Ingestion Success

After ingestion completes, verify your data:

```bash
# 1. Check total row counts
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/benchmarkos_chatbot.sqlite3'); cursor = conn.cursor(); print(f'financial_facts: {cursor.execute(\"SELECT COUNT(*) FROM financial_facts\").fetchone()[0]:,}'); print(f'metric_snapshots: {cursor.execute(\"SELECT COUNT(*) FROM metric_snapshots\").fetchone()[0]:,}'); conn.close()"

# 2. Check year coverage
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/benchmarkos_chatbot.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT ticker) FROM financial_facts'); print('Years: %s-%s | Companies: %s' % cursor.fetchone()); conn.close()"

# 3. Test a specific company
python run_chatbot.py
# Then type: metrics AAPL
```

**Expected results after successful 3-year ingestion:**
- financial_facts: ~30,000-35,000 rows
- metric_snapshots: ~250,000-350,000 rows
- Companies: 475 tickers
- Years: 2022-2024

**Expected results after successful 20-year ingestion:**
- financial_facts: ~80,000-120,000 rows
- metric_snapshots: ~500,000-700,000 rows
- Companies: 475 tickers
- Years: 2005-2025 (varies by company IPO date)

## 📚 Further Reading

- 📖 [`docs/orchestration_playbook.md`](docs/orchestration_playbook.md) – Three ingestion/orchestration patterns (local queue, serverless fetchers, batch jobs) and how to wire them into BenchmarkOSChatbot
- 💻 **Inline Module Documentation** - Comprehensive docs across `src/benchmarkos_chatbot/` describe invariants, data contracts, and extension hooks
- 🔧 **Versioning Best Practices** - Consider versioning your `.env` templates and deployment runbooks alongside these docs as the project evolves

## 🎓 System Overview (Professor Summary)

### Core Components
| Layer | Function | Key files |
|-------|----------|-----------|
| Experiences | Web dashboard, CLI, REST API | webui/, 
un_chatbot.py, serve_chatbot.py |
| Parsing | Ticker/period normalisation | src/benchmarkos_chatbot/parsing/alias_builder.py, 	ime_grammar.py |
| Retrieval & Analytics | KPI calculations, scenarios | src/benchmarkos_chatbot/analytics_engine.py, database.py, data_ingestion.py |
| RAG Orchestration | Prompt assembly, LLM calls | src/benchmarkos_chatbot/chatbot.py, llm_client.py |
| Data Acquisition | SEC ingests, quotes, macro baselines | scripts/ingestion/*.py, xternal_data.py |

### Processing Workflow
| Step | Example module | Responsibilities |
|------|----------------|------------------|
| 1. Normalise Input | lias_builder.resolve_tickers_freeform | Clean ticker names, fuzzy match alerts |
| 2. Parse Periods | 	ime_grammar.parse_periods | Interpret FY-24, calender 2020, ranges |
| 3. Retrieve Facts | nalytics_engine.fetch_metrics | Read metric_snapshots, recompute derived KPIs |
| 4. Assemble Prompt | chatbot.build_prompt | Comparison tables, highlights, trend snippets |
| 5. Generate Response | llm_client | Provide natural-language answer, citations |
| 6. Display & Export | webui/, /api/export/cfi | Dashboard, PDF/PPTX/Excel exports |

### Database (SQLite default)
| Table | Purpose |
|-------|---------|
| inancial_facts | Raw SEC CompanyFacts metrics |
| company_filings | Filing metadata (CIK, accession, period) |
| metric_snapshots | Precomputed KPIs, scenarios |
| market_quotes | Price/share-count snapshots |
| udit_events | Ingestion lineage (source system, timestamps) |
| kpi_values | Optional macro baselines |
| 	icker_aliases | Alias dictionary for parsing |

### Key Features
- Deterministic analytics + explainable responses
- Full citation trail (filings, quote timestamps)
- Dashboard + export parity (chat answers = PDF/PPTX)
- Optional macro context (IMF baselines)
- Modular ingestion scripts (resume-safe)
- Deployment: local FastAPI/Plotly; Postgres supported

### Maintenance Toolkit
| Script | Frequency | Notes |
|--------|-----------|-------|
| ingest_extended_universe.py | Monthly/quarterly | Deep SEC ingest, custom universes |
| ackfill_metrics.py | After ingests | Recompute KPIs, refresh scenarios |
| 
efresh_quotes.py | Daily | Price/ratio refresh |
| etch_imf_sector_kpis.py | As needed | Macro baselines |


---

<div align="center">

## 🎉 Happy Building!

**BenchmarkOS** - Institutional-grade analytics tooling for finance teams

*Conversational interface • Reproducible metrics • Transparent data lineage*

</div>

---

## 📌 About

**Institutional-grade analytics tooling** for finance teams who need a conversational interface, reproducible metrics, and transparent data lineage. 

The codebase includes:
- 💬 CLI copilot
- 🌐 FastAPI service
- 🖥️ Single-page web client
- 📥 Ingestion utilities that keep SEC filings and market data in sync

### Resources
- [Readme](#readme)
- [Activity](#activity)
- Stars: 0 stars
- Watchers: 0 watching
- Forks: 0 forks
- Releases: 1
  - DB snapshot 2025-10-18
  - Latest: 5 days ago

### Packages
No packages published
Publish your first package

### Contributors
2
- @haniae
- haniae Hania Abdelrahman
- @nhivuong390-code
- nhivuong390-code

### Languages
- Python: 61.2%
- JavaScript: 23.8%
- CSS: 11.2%
- HTML: 3.8%

### Suggested workflows
Based on your tech stack
- Pylint logo: Pylint - Lint a Python application with pylint.
- Node.js logo: Node.js - Build and test a Node.js project with npm.
- SLSA Generic generator logo: SLSA Generic generator - Generate SLSA3 provenance for your existing release workflows
- More workflows

Footer
© 2025 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community