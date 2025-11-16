<div align="center">

# 📊 FinalyzeOS Chatbot Platform

### Institutional-Grade Finance Copilot with Explainable AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**FinalyzeOS** is an institutional-grade copilot for finance teams. It pairs deterministic market analytics with a conversational interface so analysts can ask natural-language questions, inspect lineage, and keep data pipelines auditable.

[Quick Start](#quick-start) • [Documentation](docs/) • [Features](#core-capabilities) • [Contributing](CONTRIBUTING.md)

---

</div>

## 🎓 Practicum Context

This repository underpins our Fall 2025 DNSC 6317 practicum at The George Washington University, where we are building and governing an explainable finance copilot that can support regulated teams. Our objectives include stress-testing FinalyzeOS against real analyst workflows, documenting orchestration strategies for enterprise rollouts, and demonstrating responsible AI guardrails around data access, lineage, and scenario planning.

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
- [🤖 Machine Learning Stack](#-machine-learning-stack)
- [📚 Retrieval-Augmented Generation](#-retrieval-augmented-generation)
- [🏗️ Architecture Map](#-architecture-map)
- [🧠 Retrieval & ML Internals](#-retrieval--ml-internals)
- [🚀 Quick Start](#-quick-start)
- [💬 Running FinalyzeOS](#-running-the-chatbot)
- [📥 Data Ingestion Guide](#-data-ingestion-guide)
- [⚙️ Configuration Reference](#-configuration-reference)
- [🗄️ Database Schema](#-database-schema)
- [📁 Project Layout](#-project-layout)
- [📝 File Reference](#-file-reference)
- [✅ Quality and Testing](#-quality-and-testing)
- [🔧 Troubleshooting](#-troubleshooting)
- [📚 Further Reading](#-further-reading)

## 📖 Overview

FinalyzeOS ships as a **batteries-included template** for building finance copilots. Out of the box you gain:

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

If you're setting up FinalyzeOS for the first time, start with a focused ingestion to get familiar with the process:

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

These modules transform FinalyzeOS into a professional analytics platform comparable to Bloomberg Terminal and FactSet.

## 🤖 Machine Learning Stack

FinalyzeOS blends deterministic analytics with a modular ML layer so finance teams can prototype forecasts without giving up auditability.

### Architecture Overview

- **Data Foundation:** `analytics_engine.AnalyticsEngine.refresh_metrics()` normalises SEC filings into `metric_snapshots`. Forecast pipelines consume the same curated metrics, keeping model inputs aligned with what the dashboard renders.
- **Model Registry:** Classical (Prophet, ARIMA/ETS) and ML estimators live under `src/finanlyzeos_chatbot/ml_forecasting/`. Shared base classes (`ml_forecasting.ml_forecaster`) expose a consistent interface so new models can be dropped in with minimal wiring.
- **Context Builder:** `context_builder.build_forecast_context()` assembles explicit data dumps (predictions, confidence bands, training diagnostics) that are injected verbatim into the LLM prompt. The bot cannot answer without citing these artefacts.

### Forecast Workflow

1. **Trigger:** The intent router flags a forecasting query (see `routing/enhanced_router.py`).  
2. **Dataset Assembly:** Historical metrics are pulled from SQLite or Postgres and preprocessed (`predictive_analytics.prepare_training_series`).  
3. **Model Selection:** The ensemble coordinator benchmarks candidates, caching scores so repeated queries stay performant.  
4. **Output Packaging:** Predictions, bull/base/bear scenarios, CAGR deltas, and sector benchmarks are serialised into the forecast context.  
5. **Conversation Delivery:** `FinalyzeOSChatbot.ask()` appends the forecast context to the conversational history before calling the LLM client.

### Guardrails & Verification

- `ml_response_verifier.verify_ml_forecast_response()` checks that every figure from the explicit data dump appears in the generated answer and back-fills omissions.
- `response_verifier.verify_response()` plus the `confidence_scorer` attach a confidence footer and can redact the reply if confidence falls below configurable thresholds.
- Structured fallbacks prevent snapshots or dashboards from leaking into forecast responses; missing numbers yield a polite apology instead of hallucinations.

### Developer Workflow

- **Enable/Disable:** Toggle forecasting via the runtime settings object (`config.get_settings().forecasting_enabled`) or by exporting the matching environment variable (see `config.py` for names).  
- **Refresh Data:** `python scripts/ingestion/fill_data_gaps.py --ticker AAPL --years-back 5` hydrates the metric store before training.  
- **Unit Tests:** `pytest tests/unit/test_analytics_engine.py tests/unit/test_analysis_templates.py` cover metric hydration, forecast assembly, and verification hooks.  
- **Interactive Checks:** In a Python shell run `from finanlyzeos_chatbot.predictive_analytics import build_forecast_payload` to assemble the forecast dictionary for a given ticker/metric before handing it to the chatbot.

- `src/finanlyzeos_chatbot/context_builder.py` – forecast context orchestration.  
- `src/finanlyzeos_chatbot/predictive_analytics.py` – training/evaluation utilities and scenario generation.  
- `src/finanlyzeos_chatbot/ml_forecasting/` – individual model implementations and preprocessing helpers.  
- `src/finanlyzeos_chatbot/ml_response_verifier.py` – forecast-specific guardrails.  
- `src/finanlyzeos_chatbot/response_verifier.py` & `confidence_scorer.py` – cross-cutting verification and confidence scoring.

## 📚 Retrieval-Augmented Generation

Natural-language answers are grounded in auditable data through a layered RAG stack that combines structured metrics, uploaded documents, and conversational memory.

### Document Lifecycle

1. **Upload:** The frontend posts to `/api/documents/upload`; FastAPI persists the binary, metadata, and extracted text alongside the active `conversation_id` (`web.py`, `database.store_uploaded_document`).  
2. **Extraction:** File-type specific parsers normalise text and capture warnings (e.g., OCR failures) that are surfaced back to the user and stored for context generation.  
3. **Indexing:** Documents remain in SQLite for deterministic recall; we avoid opaque vector stores so every snippet can be reviewed in audits.

### Prompt-Aware Retrieval

- `document_context.build_uploaded_document_context()` tokenises the user query, scores overlapping chunks, and stitches together sentence-level snippets so the LLM sees the most pertinent evidence first.
- Chunk overlap, snippet length, and stop-word lists are configurable, letting admins tighten or loosen recall depending on compliance needs.
- Matched terms, file metadata, and extraction warnings are embedded directly in the context so the model can cite sources verbatim.

### Context Fusion

- `FinalyzeOSChatbot.ask()` merges three layers in priority order: portfolio analytics, financial KPI context, and document snippets.  
- A document-follow-up heuristic (`_is_document_followup`) skips ticker summary heuristics when the user says “summarise it” immediately after an upload.  
- When heuristics cannot serve the request, the bot falls back to a plain conversational instruction set ensuring non-financial prompts still receive responses.

### Quality & Monitoring

- **Unit Tests:** `pytest tests/unit/test_document_upload.py tests/unit/test_uploaded_document_context.py` guard conversation linkage and snippet relevance.  
- **Telemetry:** Progress events (e.g., `context_sources_ready`, `upload_complete`) are emitted via Server-Sent Events so the UI can surface status breadcrumbs.  
- **Operational Runbooks:** Refer to `docs/guides/PORTFOLIO_QUESTIONS_GUIDE.md` (upload section) and inline module docstrings for end-to-end walkthroughs when onboarding analysts.

### Key Modules

- `src/finanlyzeos_chatbot/document_context.py` – prompt-aware chunking and snippet assembly.  
- `src/finanlyzeos_chatbot/chatbot.py` – document-aware intent routing and context fusion.  
- `src/finanlyzeos_chatbot/static/app.js` & `webui/app.js` – frontend upload orchestration with persistent `conversation_id`s.  
- `src/finanlyzeos_chatbot/web.py` – backend API endpoint, validation, and database persistence.

## 📊 Portfolio Management 

FinalyzeOS includes comprehensive **portfolio management capabilities** that enable institutional-grade portfolio analysis, optimization, and risk management. The portfolio system supports multiple portfolios, automatic detection from user queries, and sophisticated analytics.

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
- `src/finanlyzeos_chatbot/portfolio.py` - Main portfolio management module
- `src/finanlyzeos_chatbot/portfolio_optimizer.py` - Portfolio optimization algorithms
- `src/finanlyzeos_chatbot/portfolio_risk_metrics.py` - Risk metric calculations
- `src/finanlyzeos_chatbot/portfolio_attribution.py` - Performance attribution (Brinson-Fachler)
- `src/finanlyzeos_chatbot/portfolio_scenarios.py` - Scenario analysis and stress testing
- `src/finanlyzeos_chatbot/portfolio_export.py` - Export functionality (PowerPoint, PDF, Excel)

**Documentation:** See `docs/guides/PORTFOLIO_QUESTIONS_GUIDE.md` for complete portfolio query examples and response formats.

## 🤖 Machine Learning Forecasting (NEW)

FinalyzeOS includes **sophisticated machine learning forecasting capabilities** that provide institutional-grade financial predictions using multiple ML models. The forecasting system integrates seamlessly with the RAG layer to provide detailed, technically accurate forecasts.

### 🎯 ML Forecasting Models

FinalyzeOS supports **7 different ML forecasting models**, each optimized for different use cases:

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
- **Technical Details**: See `src/finanlyzeos_chatbot/ml_forecasting/` for implementation details

## 🏗️ Architecture Map

See [`docs/architecture.md`](docs/architecture.md) for the complete component diagram. The latest revision includes the structured parsing pipeline (alias_builder.py, parse.py, time_grammar.py) and the retrieval layer that feeds grounded artefacts into the LLM alongside the existing CLI, FastAPI, analytics, and ingestion components.

## 🧠 Retrieval & ML Internals

FinalyzeOS combines **deterministic data prep** with **retrieval-augmented generation (RAG)** so every answer traces back to persisted facts. The RAG layer has been significantly enhanced to support portfolio management and machine learning forecasting with comprehensive technical details.

### 🔤 Natural-Language Parsing (Deterministic)

- src/finanlyzeos_chatbot/parsing/alias_builder.py loads a generated aliases.json covering the S&P 500. It normalises free-text mentions, resolves ticker aliases, applies manual overrides (Alphabet, Berkshire share classes, JP Morgan, AT&T), and when needed performs a fuzzy fallback and emits warnings.
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
pip install -e .
Copy-Item .env.example .env   # PowerShell
# cp .env.example .env        # macOS/Linux
```

### 📦 Complete Package Installation Guide

#### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **pip** (Python package manager, usually comes with Python)
- **Git** (to clone the repository)

#### All Required Packages

The chatbot requires the following packages (all automatically installed via `requirements.txt`):

**Core Framework:**
- `fastapi>=0.111.0` - Web framework for API endpoints
- `uvicorn[standard]>=0.30.0` - ASGI server for FastAPI
- `python-dotenv>=1.0.1` - Environment variable management

**AI/ML:**
- `openai>=1.35.0` - OpenAI API client for LLM integration
- `transformers>=4.35.0` - Hugging Face transformers library
- `torch>=2.1.0` - PyTorch for deep learning models
- `sentence-transformers>=2.2.0` - Sentence embeddings
- `langchain>=0.1.0` - LLM application framework
- `openai-whisper>=20231117` - Speech recognition

**Database:**
- `SQLAlchemy>=2.0` - SQL toolkit and ORM
- `psycopg[binary]>=3.1` - PostgreSQL adapter (Python 3)
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter (legacy)

**HTTP & API:**
- `requests>=2.32.0` - HTTP library for API calls
- `httpx>=0.25.0` - Async HTTP client

**Financial Data Sources:**
- `yfinance>=0.2.40` - Yahoo Finance data
- `fredapi>=0.5.0` - Federal Reserve Economic Data API
- `pandas-datareader>=0.10.0` - Financial data readers

**Data Processing:**
- `pandas>=2.0.0` - Data manipulation and analysis
- `numpy>=1.26,<2.3` - Numerical computing
- `openpyxl>=3.1.5` - Excel file support

**Data Visualization:**
- `plotly>=5.17.0` - Interactive plotting
- `dash>=2.14.0` - Web dashboard framework
- `dash-bootstrap-components>=1.5.0` - Bootstrap components for Dash
- `matplotlib>=3.7.0` - Static plotting
- `seaborn>=0.12.0` - Statistical visualization
- `bokeh>=3.3.0` - Interactive visualization
- `altair>=5.0.0` - Declarative visualization

**Document Generation:**
- `fpdf2>=2.7.8` - PDF generation
- `python-pptx>=0.6.23` - PowerPoint generation

**Web & Frontend:**
- `jinja2>=3.1.0` - Template engine
- `aiofiles>=23.0.0` - Async file operations
- `streamlit>=1.28.0` - Streamlit web framework
- `gradio>=4.0.0` - Gradio UI framework
- `flask>=2.3.0` - Flask web framework
- `flask-cors>=4.0.0` - CORS support for Flask
- `flask-socketio>=5.3.0` - WebSocket support for Flask

**Real-time & WebSocket:**
- `websockets>=12.0` - WebSocket library
- `socketio>=5.10.0` - Socket.IO client/server
- `redis>=5.0.0` - Redis for caching/queues
- `celery>=5.3.0` - Distributed task queue

**ML Forecasting:**
- `pmdarima>=2.0.0` - ARIMA models
- `statsmodels>=0.14.0` - Statistical models
- `prophet>=1.1.0` - Facebook Prophet forecasting
- `tensorflow>=2.13.0` - TensorFlow for deep learning
- `keras>=2.13.0` - Keras neural network library
- `optuna>=3.0.0` - Hyperparameter optimization
- `scikit-learn>=1.3.0` - Machine learning utilities
- `pandas-ta>=0.3.14b0` - Technical analysis indicators
- `scipy>=1.11.0` - Scientific computing
- `shap>=0.42.0` - Model explainability
- `ruptures>=1.1.8` - Change point detection

**NLP & Text Processing:**
- `nltk>=3.8.0` - Natural Language Toolkit
- `spacy>=3.7.0` - Advanced NLP library
- `textblob>=0.17.0` - Text processing library
- `wordcloud>=1.9.0` - Word cloud generation

**Utilities:**
- `click>=8.1.0` - Command-line interface
- `tqdm>=4.65.0` - Progress bars
- `python-dateutil>=2.8.0` - Date utilities
- `pyyaml>=6.0.0` - YAML parser
- `pillow>=10.0.0` - Image processing

**Logging & Monitoring:**
- `structlog>=23.0.0` - Structured logging
- `rich>=13.0.0` - Rich text and formatting

**Security:**
- `cryptography>=41.0.0` - Cryptographic library
- `python-jose[cryptography]>=3.3.0` - JWT handling

**Testing:**
- `pytest>=8.2.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `pytest-cov>=4.0.0` - Coverage reporting

**Development Tools:**
- `black>=23.0.0` - Code formatter
- `flake8>=6.0.0` - Linter
- `mypy>=1.5.0` - Type checker

#### Installation Verification

After installation, verify everything works:

```bash
# Check Python version (should be 3.10+)
python --version

# Verify key packages are installed
python -c "import fastapi, openai, pandas, sqlalchemy; print('✅ Core packages installed')"

# Run a quick test
python -c "from finanlyzeos_chatbot.config import load_settings; print('✅ FinalyzeOS imports successfully')"
```

#### Troubleshooting Installation

**Issue: Package conflicts**
```bash
# Create a fresh virtual environment
deactivate  # Exit current venv
rm -rf .venv  # Remove old venv (or rmdir /s .venv on Windows)
python -m venv .venv  # Create new venv
source .venv/bin/activate  # Activate (or .\.venv\Scripts\activate on Windows)
pip install --upgrade pip  # Upgrade pip first
pip install -r requirements.txt  # Reinstall
```

**Issue: psycopg2 installation fails (Windows)**
```bash
# Install pre-compiled binary
pip install psycopg2-binary
```

**Issue: TensorFlow/GPU issues**
```bash
# For CPU-only installation (if GPU causes issues)
pip install tensorflow-cpu
```

**Issue: Memory errors during installation**
```bash
# Install packages in smaller batches
pip install fastapi uvicorn python-dotenv
pip install openai requests httpx
pip install pandas numpy
# ... continue with other packages from requirements.txt
```

**Issue: Permission errors (Linux/macOS)**
```bash
# Use --user flag or ensure virtual environment is activated
pip install --user -r requirements.txt
# OR ensure venv is activated:
source .venv/bin/activate
pip install -r requirements.txt
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
- [FinalyzeOS GitHub Repository](https://github.com/haniae/Team2-CBA-Project)

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
5. File downloads automatically: `finanlyzeos-{ticker}-{date}.pptx`

*Programmatic (Python SDK):*
```python
from finanlyzeos_chatbot import AnalyticsEngine, load_settings
from finanlyzeos_chatbot.export_pipeline import generate_dashboard_export

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

Open `.env` and update database paths, API keys, and provider toggles. Prefer not to store an OpenAI key in the repo? Put it in `~/.config/finanlyzeos-chatbot/openai_api_key` and the loader will pick it up automatically.

### 3️⃣ (Optional) Warm the Datastore

SQLite tables are created lazily, but you can preload metrics with:

```bash
python scripts/ingestion/ingest_universe.py --years 5 --chunk-size 25 --sleep 2 --resume
```

This pulls the sample watch list, respects SEC rate limits, and writes audit events.

## 💬 Running FinalyzeOS

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
uvicorn finanlyzeos_chatbot.web:app --reload --port 8000
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

FinalyzeOS provides **multiple ingestion strategies** to fit different use cases. This section explains how to populate your database with financial data.

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
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/finanlyzeos_chatbot.sqlite3'); cursor = conn.cursor(); tables = ['financial_facts', 'company_filings', 'metric_snapshots', 'kpi_values']; [print(f'{t}: {cursor.execute(f\"SELECT COUNT(*) FROM {t}\").fetchone()[0]:,}') for t in tables]; conn.close()"

# Check year coverage
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/finanlyzeos_chatbot.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT ticker) FROM financial_facts'); print('Years: %s-%s | Companies: %s' % cursor.fetchone()); conn.close()"
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
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
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
  export SEC_API_USER_AGENT="FinalyzeOSBot/1.0 (you@example.com)"
  ```

### Ingest the S&P 500 into SQLite

SQLite path defaults to data/sqlite/finanlyzeos_chatbot.sqlite3 (configurable via DATABASE_PATH).

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
p='data/sqlite/finanlyzeos_chatbot.sqlite3'
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
db='data/sqlite/finanlyzeos_chatbot.sqlite3'
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
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
AnalyticsEngine(load_settings()).refresh_metrics(force=True)
print('Refreshed metric_snapshots.')
PY
```

Check the latest quote timestamp:

```python
python - <<'PY'
import sqlite3
con=sqlite3.connect('data/sqlite/finanlyzeos_chatbot.sqlite3')
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
- If you see ModuleNotFoundError: finanlyzeos_chatbot, ensure you ran pip install -e . or set:
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
| DATABASE_PATH | ./data/sqlite/finanlyzeos_chatbot.sqlite3 | SQLite file location; created automatically. |
| POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE, POSTGRES_USER, POSTGRES_PASSWORD | unset | Required when DATABASE_TYPE=postgresql; POSTGRES_SCHEMA overrides the default sec. |
| LLM_PROVIDER | local | local uses the deterministic echo model; set to openai for real completions. |
| OPENAI_MODEL | gpt-4o-mini | Passed verbatim to the OpenAI Chat Completions API. |
| SEC_API_USER_AGENT | FinalyzeOSBot/1.0 (support@finanlyzeos.com) | Mandatory for SEC EDGAR requests. Customize it for your org. |
| EDGAR_BASE_URL | https://data.sec.gov | Override if you proxy or mirror EDGAR. |
| YAHOO_QUOTE_URL | https://query1.finance.yahoo.com/v7/finance/quote | Used to refresh quotes. |
| YAHOO_QUOTE_BATCH_SIZE | 50 | Maximum tickers per Yahoo batch. |
| HTTP_REQUEST_TIMEOUT | 30 | Seconds before HTTP clients give up. |
| INGESTION_MAX_WORKERS | 8 | Thread pool size for ingestion routines. |
| DATA_CACHE_DIR | ./cache | Stores downloaded filings, facts, and progress markers. |
| ENABLE_BLOOMBERG | false | Toggle Bloomberg ingestion; requires host/port/timeout values. |
| BLOOMBERG_HOST, BLOOMBERG_PORT, BLOOMBERG_TIMEOUT | unset | Only used if Bloomberg is enabled. |
| OPENAI_API_KEY | unset | Looked up in env, then keyring, then ~/.config/finanlyzeos-chatbot/openai_api_key. |

Secrets belong in your local .env. Windows developers can rely on keyring so API keys live outside the repo.

## 🗄️ Database Schema

FinalyzeOS intentionally supports **two storage backends**, but your deployment uses only one at a time—by default it's SQLite:

- **SQLite (default / implied in this repo)** – shipping the database as a file keeps setup frictionless for development, tests, and CI. All conversations, metrics, and audit events live in the path defined by DATABASE_PATH. For this reason, the stock .env (and most tests such as test_ingestion_perf.py) run purely on SQLite. It was chosen because it "just works": no external server to provision, a trivial backup story, and fast enough for single-user workflows. PRAGMAs (WAL, synchronous=NORMAL, temp_store=MEMORY, cache_size=-16000) are applied automatically so sustained writes remain smooth.
- **PostgreSQL (optional)** – the same helper module can target Postgres when you set DATABASE_TYPE=postgresql and supply the POSTGRES_* DSN variables. Teams switch to Postgres when chat sessions are shared across analysts, when concurrency or replication matters, or when governance requires managed backups. If you haven't changed those settings, Postgres is unused.

In other words, you are currently using a single database—SQLite—because it was selected for simplicity and portability. The PostgreSQL path is documented for teams that choose to run FinalyzeOS in a multi-user/shared environment later.

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
├── CHANGELOG.md                       # Project changelog
├── LICENSE                            # Project license (MIT)
├── SECURITY.md                        # Security policy
├── CODE_OF_CONDUCT.md                 # Code of conduct
├── CONTRIBUTING.md                    # Contribution guidelines
├── pyproject.toml                     # Project metadata, dependencies, pytest config
├── requirements.txt                   # Python dependencies lockfile
├── .env.example                       # Environment configuration template
├── run_chatbot.py                     # CLI chatbot entry point (REPL)
├── serve_chatbot.py                   # Web server entry point (FastAPI)
├── run_data_ingestion.ps1             # Windows PowerShell ingestion script
├── run_data_ingestion.sh              # Unix/Linux ingestion script
│
├── scripts/
│   ├── generate_aliases.py            # Regenerate ticker alias universe (S&P 500)
│   │
│   ├── ingestion/                      # Data ingestion scripts
│   │   ├── fill_data_gaps.py          # ⭐ Recommended: Smart gap-filling script
│   │   ├── ingest_20years_sp500.py    # Full 20-year historical ingestion
│   │   ├── batch_ingest.py            # Batch ingestion with retry/backoff
│   │   ├── ingest_companyfacts.py     # SEC CompanyFacts API ingestion
│   │   ├── ingest_companyfacts_batch.py # Batch CompanyFacts ingestion
│   │   ├── ingest_frames.py           # SEC data frames ingestion
│   │   ├── ingest_from_file.py        # Ingestion from file input
│   │   ├── ingest_universe.py         # Universe-based ingestion with resume support
│   │   ├── load_prices_stooq.py       # Stooq price loader (fallback)
│   │   ├── load_prices_yfinance.py   # Yahoo Finance price loader
│   │   └── load_ticker_cik.py         # Ticker to CIK mapping loader
│   │
│   └── utility/                        # Utility and helper scripts
│       ├── check_database_simple.py   # Database verification utility
│       ├── check_ingestion_status.py  # Ingestion status checker
│       ├── check_kpi_values.py        # KPI validation utility
│       ├── check_braces.py            # Syntax checking utility
│       ├── check_syntax.py            # Code syntax validation
│       ├── find_unclosed_brace.py     # Brace matching utility
│       ├── combine_portfolio_files.py # Portfolio file combiner
│       ├── chat_terminal.py           # Terminal chat interface
│       ├── monitor_progress.py        # Progress monitoring utility
│       ├── quick_status.py            # Quick status check
│       ├── show_complete_attribution.py # Attribution display utility
│       ├── plotly_demo.py             # Plotly chart examples
│       ├── chat_metrics.py            # Chat metrics utility
│       ├── data_sources_backup.py     # Data sources backup utility
│       ├── refresh_ticker_catalog.py  # Ticker catalog refresh utility
│       └── main.py                    # Main utility CLI wrapper
│
├── src/
│   └── finanlyzeos_chatbot/
│       │
│       ├── Core Components:
│       ├── analytics_engine.py        # Core analytics engine (KPI calculations)
│       ├── chatbot.py                 # Main chatbot orchestration (RAG, LLM integration)
│       ├── config.py                  # Configuration management (settings loader)
│       ├── database.py                # Database abstraction layer (SQLite/Postgres)
│       ├── llm_client.py              # LLM provider abstraction (OpenAI/local echo)
│       ├── web.py                     # FastAPI web server (REST API endpoints)
│       │
│       ├── Data & Ingestion:
│       ├── data_ingestion.py          # Data ingestion pipeline (SEC, Yahoo, Bloomberg)
│       ├── data_sources.py            # Data source integrations (SEC EDGAR, Yahoo Finance)
│       ├── external_data.py          # External data providers (FRED, IMF)
│       ├── macro_data.py              # Macroeconomic data provider
│       ├── multi_source_aggregator.py # Multi-source data aggregation
│       ├── sec_bulk.py                # SEC bulk data access
│       ├── secdb.py                   # SEC database utilities
│       │
│       ├── Context & RAG:
│       ├── context_builder.py         # Financial context builder for RAG (ML forecasts, portfolio)
│       ├── ml_response_verifier.py    # ML forecast response verification & enhancement
│       ├── followup_context.py       # Follow-up question context management
│       ├── intent_carryover.py       # Intent carryover between conversations
│       │
│       ├── Parsing & NLP:
│       ├── parsing/
│       │   ├── alias_builder.py       # Ticker alias resolution (S&P 500)
│       │   ├── aliases.json           # Generated ticker aliases (S&P 500 coverage)
│       │   ├── ontology.py           # Metric ontology (KPI definitions)
│       │   ├── parse.py               # Natural language parser (structured intents)
│       │   ├── time_grammar.py        # Time period parser (FY, quarters, ranges)
│       │   ├── abbreviations.py       # Abbreviation expansion
│       │   ├── company_groups.py      # Company group detection
│       │   ├── comparative.py         # Comparative language parsing
│       │   ├── conditionals.py        # Conditional statement parsing
│       │   ├── fuzzy_quantities.py    # Fuzzy quantity parsing
│       │   ├── metric_inference.py   # Metric inference from context
│       │   ├── multi_intent.py       # Multi-intent detection
│       │   ├── natural_filters.py    # Natural language filters
│       │   ├── negation.py            # Negation handling
│       │   ├── question_chaining.py   # Question chaining detection
│       │   ├── sentiment.py          # Sentiment analysis
│       │   ├── temporal_relationships.py # Temporal relationship parsing
│       │   └── trends.py              # Trend detection
│       │
│       ├── Spelling & Correction:
│       ├── spelling/
│       │   ├── company_corrector.py   # Company name spelling correction
│       │   ├── correction_engine.py  # Main spelling correction engine
│       │   ├── fuzzy_matcher.py      # Fuzzy string matching
│       │   └── metric_corrector.py    # Metric name spelling correction
│       │
│       ├── Routing:
│       ├── routing/
│       │   └── enhanced_router.py     # Enhanced intent routing (dashboard detection)
│       │
│       ├── Analytics Modules:
│       ├── sector_analytics.py        # Sector benchmarking (GICS sectors)
│       ├── anomaly_detection.py      # Anomaly detection (Z-score analysis)
│       ├── predictive_analytics.py   # Predictive analytics (regression, CAGR)
│       ├── advanced_kpis.py           # Advanced KPI calculator (30+ ratios)
│       │
│       ├── Portfolio Management:
│       ├── portfolio.py               # Main portfolio management module (combined)
│       ├── portfolio_optimizer.py    # Portfolio optimization (mean-variance)
│       ├── portfolio_risk_metrics.py # Risk metrics (CVaR, VaR, Sharpe, Sortino)
│       ├── portfolio_attribution.py  # Performance attribution (Brinson-Fachler)
│       ├── portfolio_scenarios.py    # Scenario analysis & stress testing
│       ├── portfolio_exposure.py     # Exposure analysis (sector, factor)
│       ├── portfolio_calculations.py # Portfolio calculation utilities
│       ├── portfolio_enrichment.py   # Portfolio enrichment with fundamentals
│       ├── portfolio_enhancements.py # Portfolio enhancement utilities
│       ├── portfolio_reporting.py    # Portfolio reporting utilities
│       ├── portfolio_trades.py       # Trade recommendation utilities
│       ├── portfolio_export.py       # Portfolio export (PowerPoint, PDF, Excel)
│       └── portfolio_ppt_builder.py   # Portfolio PowerPoint builder
│       │
│       ├── ML Forecasting:
│       ├── ml_forecasting/
│       │   ├── ml_forecaster.py       # Main ML forecaster (model selection)
│       │   ├── arima_forecaster.py    # ARIMA model (statistical time series)
│       │   ├── prophet_forecaster.py # Prophet model (seasonal patterns)
│       │   ├── ets_forecaster.py     # ETS model (exponential smoothing)
│       │   ├── lstm_forecaster.py    # LSTM model (deep learning RNN)
│       │   ├── transformer_forecaster.py # Transformer model (attention-based)
│       │   ├── preprocessing.py     # Data preprocessing (scaling, normalization)
│       │   ├── feature_engineering.py # Feature engineering utilities
│       │   ├── hyperparameter_tuning.py # Hyperparameter optimization (Optuna)
│       │   ├── backtesting.py        # Model backtesting utilities
│       │   ├── validation.py          # Model validation utilities
│       │   ├── explainability.py     # Model explainability (SHAP, attention)
│       │   ├── uncertainty.py         # Uncertainty quantification
│       │   ├── regime_detection.py  # Regime detection (market states)
│       │   ├── technical_indicators.py # Technical indicators for features
│       │   ├── external_factors.py   # External factor integration
│       │   └── multivariate_forecaster.py # Multivariate forecasting
│       │
│       ├── Export & Presentation:
│       ├── export_pipeline.py        # Export pipeline (PDF, PPTX, Excel)
│       ├── cfi_ppt_builder.py         # CFI-style PowerPoint builder (12 slides)
│       ├── table_renderer.py         # ASCII table rendering
│       │
│       ├── Utilities:
│       ├── tasks.py                   # Task queue management
│       ├── help_content.py           # Help content and documentation
│       ├── dashboard_utils.py        # Dashboard utility functions
│       ├── document_processor.py     # Document processing utilities
│       ├── imf_proxy.py              # IMF data proxy
│       ├── kpi_backfill.py           # KPI backfill utilities
│       ├── backfill_policy.py        # Backfill policy management
│       ├── ticker_universe.py        # Ticker universe management
│       │
│       └── Static Assets:
│       └── static/
│           ├── app.js                 # Frontend application logic (SPA)
│           ├── styles.css             # UI styling (markdown, progress indicator)
│           ├── index.html             # Web UI entry point
│           ├── favicon.svg            # Favicon
│           ├── cfi_dashboard.html     # CFI dashboard HTML
│           ├── cfi_dashboard.js       # CFI dashboard JavaScript
│           ├── cfi_dashboard.css      # CFI dashboard styling
│           ├── portfolio_dashboard.html # Portfolio dashboard HTML
│           ├── portfolio_dashboard.js  # Portfolio dashboard JavaScript
│           └── data/
│               ├── company_universe.json # Company universe metadata
│               └── kpi_library.json      # KPI library definitions
│
├── docs/
│   ├── README.md                      # Documentation index
│   │
│   ├── architecture/                    # Architecture documentation
│   │   ├── architecture.md            # System architecture diagram
│   │   ├── chatbot_system_overview_en.md # System overview
│   │   └── product_design_spec.md     # Product design specifications
│   │
│   ├── demos/                          # Demo and presentation docs
│   │   ├── CBA_POSTER_CONDENSED.md    # CBA poster (condensed)
│   │   ├── CBA_POSTER_CONTENT.md      # CBA poster content
│   │   ├── CHATBOT_DEMO_GUIDE.md      # Chatbot demo guide
│   │   └── CLIENT_DEMO_PROMPTS.md     # Client demo prompts
│   │
│   ├── guides/                         # User and technical guides
│   │   ├── ALL_ML_FORECASTING_PROMPTS.md # All ML forecasting prompts
│   │   ├── ML_FORECASTING_QUICK_REFERENCE.md # ML forecasting quick reference
│   │   ├── ML_FORECASTING_PROMPTS.md  # ML forecasting prompts guide
│   │   ├── PORTFOLIO_QUESTIONS_GUIDE.md # Portfolio questions guide
│   │   ├── FINANCIAL_PROMPTS_GUIDE.md # Financial prompts guide
│   │   ├── CHATBOT_PROMPT_GUIDE.md    # Chatbot prompt guide
│   │   ├── COMPREHENSIVE_DATA_SOURCES.md # Data sources guide
│   │   ├── DASHBOARD_SOURCES_INSTRUCTIONS.md # Dashboard sources guide
│   │   ├── DATA_INGESTION_PLAN.md     # Data ingestion planning
│   │   ├── ENABLE_FRED_GUIDE.md       # FRED integration guide
│   │   ├── EXPAND_DATA_GUIDE.md       # Data expansion guide
│   │   ├── EXTENDED_INGESTION_INFO.md # Extended ingestion info
│   │   ├── INSTALLATION_GUIDE.md      # Installation instructions
│   │   ├── SETUP_GUIDE.md             # Setup guide
│   │   ├── TEAM_SETUP_GUIDE.md        # Team onboarding guide
│   │   ├── PLOTLY_INTEGRATION.md      # Plotly integration docs
│   │   ├── MULTI_TICKER_DASHBOARD_GUIDE.md # Multi-ticker dashboard guide
│   │   ├── MULTI_TICKER_DASHBOARDS.md # Multi-ticker dashboards guide
│   │   ├── SOURCES_LOCATION_GUIDE.md  # Sources location guide
│   │   ├── SOURCES_TROUBLESHOOTING.md # Sources troubleshooting
│   │   ├── SYSTEM_PROMPT_SIMPLIFIED.md # System prompt guide
│   │   ├── ENHANCED_ROUTING.md        # Enhanced routing guide
│   │   ├── RAW_SEC_PARSER_IMPLEMENTATION_GUIDE.md # SEC parser guide
│   │   ├── export_pipeline_scope.md  # Export pipeline scope
│   │   ├── orchestration_playbook.md # Deployment orchestration guide
│   │   ├── ticker_names.md           # Ticker coverage list
│   │   └── (additional guides)
│   │
│   ├── organization/                   # Organization documentation
│   │   ├── REPOSITORY_ORGANIZATION_2024.md # Repository organization (2024)
│   │   ├── REPOSITORY_ORGANIZATION_COMPLETE.md # Repository organization (complete)
│   │   └── COMPLETE_ORGANIZATION_STATUS.md # Organization status
│   │
│   ├── enhancements/                  # Enhancement documentation
│   │   ├── FINANCIAL_PROMPTS_ENHANCEMENT_COMPLETE.md # Financial prompts enhancement
│   │   ├── MULTI_SOURCE_INTEGRATION.md # Multi-source integration
│   │   ├── MARKDOWN_FORMATTING_FIX.md # Markdown formatting fix
│   │   ├── MESSAGE_FORMATTING_IMPROVED.md # Message formatting improvements
│   │   ├── PDF_ENHANCEMENTS_COMPLETE.md # PDF enhancements
│   │   ├── PDF_EXPORT_IMPROVEMENTS.md # PDF export improvements
│   │   ├── PDF_LAYOUT_FIXES_COMPLETE.md # PDF layout fixes
│   │   ├── PROGRESS_INDICATOR_ENHANCEMENT.md # Progress indicator enhancement
│   │   ├── QUESTION_DETECTION_FIX.md  # Question detection fix
│   │   ├── SOURCES_AND_DEPTH_FIX.md  # Sources and depth fix
│   │   └── INVESTMENT_GRADE_PDF_COMPLETE.md # Investment-grade PDF
│   │
│   ├── fixes/                          # Fix documentation
│   │   ├── FINAL_NAN_FIX_COMPLETE.md  # NaN fix completion
│   │   ├── JAVASCRIPT_SYNTAX_ERROR_FIX.md # JavaScript syntax fix
│   │   ├── MULTI_TICKER_DASHBOARD_FIX.md # Multi-ticker dashboard fix
│   │   ├── MULTI_TICKER_DETECTION_FIX.md # Multi-ticker detection fix
│   │   ├── MULTI_TICKER_TOOLBAR_REMOVAL.md # Multi-ticker toolbar removal
│   │   ├── PDF_EXPORT_FIX.md          # PDF export fix
│   │   ├── PDF_UNICODE_FIX.md        # PDF unicode fix
│   │   ├── PLOTLY_NAN_ERRORS_FIX.md   # Plotly NaN errors fix
│   │   ├── SOURCES_PANEL_RESTORED.md  # Sources panel restoration
│   │   └── SOURCES_PANEL_VISIBILITY_FIX.md # Sources panel visibility fix
│   │
│   ├── ui/                             # UI documentation
│   │   ├── USER_GUIDE.md              # User guide
│   │   ├── ACCURATE_SOURCE_LINKS_UPDATE.md # Source links update
│   │   ├── BUTTON_EVENT_HANDLER_FIX.md # Button event handler fix
│   │   ├── COMPANY_SELECTOR_COMPARISON.md # Company selector comparison
│   │   ├── COMPANY_SELECTOR_SCALING_FIX.md # Company selector scaling fix
│   │   ├── COMPREHENSIVE_IMPROVEMENTS_SUMMARY.md # Comprehensive improvements
│   │   ├── DASHBOARD_IMPROVEMENTS.md  # Dashboard improvements
│   │   ├── DASHBOARD_LAYOUT_IMPROVEMENTS.md # Dashboard layout improvements
│   │   ├── DATA_SOURCES_FORMAT.md     # Data sources format
│   │   ├── FINAL_LAYOUT_SUMMARY.md    # Final layout summary
│   │   ├── IMPLEMENTATION_COMPLETE.md # Implementation completion
│   │   ├── LAYOUT_REORGANIZATION.md   # Layout reorganization
│   │   ├── LINKS_FIX_SUMMARY.md       # Links fix summary
│   │   └── PLOTLY_NAN_FIX.md          # Plotly NaN fix
│   │
│   ├── summaries/                      # Summary documentation
│   │   └── (28 summary files documenting various features and improvements)
│   │
│   ├── analysis/                       # Analysis documentation
│   │   ├── README.md                   # Analysis documentation index
│   │   └── (22 analysis reports and documentation files)
│   │
│   └── reports/                        # Generated reports
│       └── (various analysis and improvement reports)
│
├── data/
│   ├── sample_financials.csv          # Sample financial data
│   ├── external/
│   │   └── imf_sector_kpis.json       # IMF sector KPI benchmarks
│   ├── sqlite/
│   │   └── finanlyzeos_chatbot.sqlite3 # SQLite database (created on demand)
│   └── tickers/
│       ├── universe_sp500.txt         # S&P 500 ticker list (475 companies)
│       ├── sec_top100.txt             # Top 100 SEC companies
│       ├── universe_custom.txt        # Custom universe list
│       └── sample_watchlist.txt       # Sample watchlist
│
├── cache/                              # Generated at runtime (gitignored)
│   ├── edgar_tickers.json             # Cached EDGAR ticker data
│   └── progress/
│       └── fill_gaps_summary.json     # Ingestion progress tracking
│
├── analysis/                           # Experimental and analysis code
│   ├── experiments/                   # Experimental implementations
│   │   ├── enhanced_ticker_resolver.py # Enhanced ticker resolver experiment
│   │   ├── fixed_ticker_resolver.py   # Fixed ticker resolver experiment
│   │   ├── fixed_time_grammar.py      # Fixed time grammar experiment
│   │   ├── implement_metric_improvements.py # Metric improvements experiment
│   │   ├── improved_real_world_parse.py # Real-world parsing improvements
│   │   └── ultimate_failing_cases_fix.py # Failing cases fix experiment
│   └── scripts/                        # Analysis and validation scripts
│       └── (20 analysis and validation scripts)
│
├── archive/                            # Archived files
│   └── parsing_development/           # Parsing development archive
│       └── (15 archived files: 11 markdown, 4 Python)
│
├── webui/                              # Web UI files
│   ├── index.html                      # Web UI entry point
│   ├── app.js                          # Frontend application logic
│   ├── styles.css                      # UI styling (7432 lines)
│   ├── package.json                   # Node.js dependencies
│   ├── service-worker.js              # Service worker for PWA
│   ├── start_dashboard.js             # Dashboard startup script
│   ├── favicon.svg                    # Favicon
│   ├── cfi_dashboard.html             # CFI dashboard HTML
│   ├── cfi_dashboard.js                # CFI dashboard JavaScript
│   ├── cfi_dashboard.css              # CFI dashboard styling
│   ├── cfi_compare.html               # CFI compare view HTML
│   ├── cfi_compare.js                 # CFI compare view JavaScript
│   ├── cfi_compare.css                # CFI compare view styling
│   ├── cfi_dense.html                 # CFI dense view HTML
│   ├── cfi_dense.js                    # CFI dense view JavaScript
│   ├── cfi_dense.css                   # CFI dense view styling
│   ├── cfi_compare_demo.html          # CFI compare demo
│   ├── cfi_compare_standalone.html    # CFI compare standalone
│   ├── cfi_dashboard_backup_original.html # Backup files
│   ├── cfi_dashboard_improved.html    # Improved dashboard
│   ├── cfi_dashboard_old_backup.html  # Old backup
│   ├── cfi_dashboard_v2.html          # Dashboard v2
│   └── data/
│       └── (2 JSON data files)
│
└── tests/                              # Test files
    ├── README.md                       # Testing documentation
    │
    ├── unit/                           # Unit tests
    │   ├── test_analytics.py           # Analytics unit tests
    │   ├── test_analytics_engine.py    # Analytics engine unit tests
    │   ├── test_cli_tables.py          # CLI table rendering tests
    │   ├── test_database.py            # Database unit tests
    │   └── test_data_ingestion.py      # Data ingestion unit tests
    │
    ├── integration/                    # Integration tests
    │   ├── test_chatbot_sec_fix.py    # SEC integration tests
    │   ├── test_sec_api_fix.py        # SEC API integration tests
    │   ├── test_new_analytics.py      # New analytics integration tests
    │   ├── test_dashboard_flow.py     # Dashboard workflow integration tests
    │   ├── test_fixes.py              # General fixes integration tests
    │   └── test_enhanced_routing.py   # Enhanced routing integration tests
    │
    ├── e2e/                            # End-to-end tests
    │   ├── test_all_sp500_dashboards.py # Full S&P 500 dashboard test
    │   ├── test_sample_companies.py   # Sample companies test (10 companies)
    │   ├── test_single_company.py     # Single company test (Apple)
    │   ├── test_chatbot_stress_test.py # FinalyzeOS stress test
    │   ├── test_chatgpt_style.py      # ChatGPT-style test
    │   ├── test_comprehensive_sources.py # Comprehensive sources test
    │   ├── PORTFOLIO_STRESS_TEST_SUMMARY.md # Portfolio stress test summary
    │   └── test_ml_detailed_answers.py # ML detailed answers test
    │
    ├── verification/                   # Verification scripts
    │   ├── verify_metrics.py           # Metric verification
    │   ├── verify_new_data.py          # New data verification
    │   ├── verify_100_percent_complete.py # 100% completeness verification
    │   └── check_sources.py           # Source checking utility
    │
    ├── ui/                             # UI test files
    │   ├── test_dashboard_sources.html # Dashboard sources test
    │   ├── test_upload_button.html     # Upload button test
    │   └── VERIFY_MARKDOWN_WORKS.html  # Markdown verification test
    │
    ├── regression/                     # Regression tests
    │   ├── test_ticker_resolution.py   # Ticker resolution regression
    │   ├── test_time_fixes.py          # Time parsing fixes regression
    │   └── (additional regression tests)
    │
    ├── Parser & NLP Tests:
    ├── test_alias_resolution.py         # Alias resolution tests
    ├── test_time_grammar.py            # Time grammar tests
    ├── test_nl_parser.py               # Natural language parser tests
    ├── test_abbreviations.py           # Abbreviation tests
    ├── test_advanced_followups.py     # Advanced follow-up tests
    ├── test_company_groups.py          # Company group tests
    ├── test_comparative_language.py    # Comparative language tests
    ├── test_conditionals.py            # Conditional statement tests
    ├── test_enhanced_intents.py        # Enhanced intent tests
    ├── test_enhanced_metric_synonyms.py # Enhanced metric synonym tests
    ├── test_enhanced_question_patterns.py # Enhanced question pattern tests
    ├── test_followup_features_unit.py  # Follow-up feature unit tests
    ├── test_fuzzy_quantities.py        # Fuzzy quantity tests
    ├── test_metric_inference.py        # Metric inference tests
    ├── test_multi_intent.py            # Multi-intent tests
    ├── test_natural_filters.py         # Natural filter tests
    ├── test_negation_handling.py       # Negation handling tests
    ├── test_performance_benchmarks.py  # Performance benchmark tests
    ├── test_period_normalization.py   # Period normalization tests
    ├── test_pronoun_resolution.py      # Pronoun resolution tests
    ├── test_question_chaining.py      # Question chaining tests
    ├── test_sentiment.py               # Sentiment analysis tests
    ├── test_spelling_correction.py     # Spelling correction tests
    ├── test_temporal_relationships.py  # Temporal relationship tests
    ├── test_time_period_enhancement.py # Time period enhancement tests
    ├── test_trend_direction.py        # Trend direction tests
    │
    ├── Portfolio Tests:
    ├── test_portfolio_detection_working.py # Portfolio detection tests
    ├── test_portfolio_patterns.py      # Portfolio pattern tests
    ├── test_portfolio_questions.py     # Portfolio question tests
    ├── test_portfolio_stress_test.py   # Portfolio stress test
    │
    ├── ML Forecasting Tests:
    ├── test_all_forecast_prompts.py   # All forecast prompt tests
    ├── test_forecast_detection.py     # Forecast detection tests
    ├── test_forecast_prompts.py       # Forecast prompt tests
    ├── test_ml_context_debug.py       # ML context debug tests
    ├── test_ml_detailed_response.py   # ML detailed response tests
    │
    ├── Other Tests:
    ├── test_terminal_bot.py            # Terminal bot tests
    ├── test_working_prompts.py         # Working prompt tests
    ├── test_api_direct.sh             # API direct test script
    ├── test_dashboard_sources.html     # Dashboard sources HTML test
    ├── test_integration_e2e.py        # Integration E2E tests
    ├── test_source_completeness.py    # Source completeness tests
    ├── test_chatbot_stress_test.py    # FinalyzeOS stress test
    ├── test_chatgpt_style.py          # ChatGPT-style test
    ├── portfolio_stress_test_results.json # Portfolio stress test results
    │
    ├── cache/                          # Test cache (gitignored)
    ├── data/                           # Test data fixtures
    └── outputs/                        # Test outputs (gitignored)
```

## 📝 File Reference

### 🔧 Root Scripts & Helpers

| File | Description |
|------|-------------|
| run_chatbot.py | Lightweight REPL entry point that calls FinalyzeOSChatbot.create(). Provides interactive CLI for chatbot queries. |
| serve_chatbot.py | Convenience launcher for the FastAPI app (src/finanlyzeos_chatbot/web.py). Starts web server on specified port. |
| run_data_ingestion.ps1 | Windows PowerShell script for automated data ingestion. Wraps fill_data_gaps.py with Windows-specific settings. |
| run_data_ingestion.sh | Unix/Linux script for automated data ingestion. Wraps fill_data_gaps.py with Unix-specific settings. |
| pyproject.toml | Project metadata, dependencies, and pytest configuration. Adds src/ to PYTHONPATH for imports. |
| requirements.txt | Python dependencies lockfile. Lists all required packages with version constraints. |
| CHANGELOG.md | Project changelog documenting version history and changes. |
| LICENSE | Project license (MIT). |
| SECURITY.md | Security policy and vulnerability reporting guidelines. |
| CODE_OF_CONDUCT.md | Code of conduct for contributors. |
| CONTRIBUTING.md | Contribution guidelines and development workflow. |

### 📜 Scripts

#### Ingestion Scripts

| File | Description |
|------|-------------|
| scripts/ingestion/fill_data_gaps.py | ⭐ **Recommended**: Smart gap-filling script that detects missing data, fetches from SEC EDGAR with rate limiting, handles retries, and provides progress tracking. |
| scripts/ingestion/ingest_20years_sp500.py | Full 20-year historical ingestion for S&P 500 companies. Fetches comprehensive historical data. |
| scripts/ingestion/batch_ingest.py | Batch ingestion with retry/backoff. Loads curated watch list with intelligent error handling. |
| scripts/ingestion/ingest_companyfacts.py | SEC CompanyFacts API ingestion. Fetches company facts from SEC EDGAR CompanyFacts endpoint. |
| scripts/ingestion/ingest_companyfacts_batch.py | Batch CompanyFacts ingestion. Processes multiple companies with rate limiting. |
| scripts/ingestion/ingest_frames.py | SEC data frames ingestion. Downloads SEC data frames into Postgres for benchmarking. |
| scripts/ingestion/ingest_from_file.py | Ingestion from file input. Reads ticker list from file and ingests data. |
| scripts/ingestion/ingest_universe.py | Universe-based ingestion with resume support. Batch ingester that refreshes metrics after each chunk. |
| scripts/ingestion/load_prices_stooq.py | Stooq price loader (fallback). Imports Stooq prices as a fallback when Yahoo throttles. |
| scripts/ingestion/load_prices_yfinance.py | Yahoo Finance price loader. Fetches real-time and historical prices from Yahoo Finance. |
| scripts/ingestion/load_ticker_cik.py | Ticker to CIK mapping loader. Maps ticker symbols to SEC CIK numbers. |
| scripts/generate_aliases.py | Regenerates the S&P 500 alias universe (aliases.json). Updates ticker aliases for parser. |

#### Utility Scripts

| File | Description |
|------|-------------|
| scripts/utility/main.py | Rich CLI wrapper exposing metrics/table commands, abbreviations, and scenario helpers. |
| scripts/utility/check_database_simple.py | Database verification utility. Checks database integrity and connectivity. |
| scripts/utility/check_ingestion_status.py | Ingestion status checker. Monitors ingestion progress and completion. |
| scripts/utility/check_kpi_values.py | KPI validation utility. Validates KPI calculations and data quality. |
| scripts/utility/check_braces.py | Syntax checking utility. Validates Python brace matching. |
| scripts/utility/check_syntax.py | Code syntax validation. Checks Python syntax errors. |
| scripts/utility/find_unclosed_brace.py | Brace matching utility. Finds unclosed braces in code. |
| scripts/utility/combine_portfolio_files.py | Portfolio file combiner. Merges multiple portfolio files into one. |
| scripts/utility/chat_terminal.py | Terminal chat interface. Provides terminal-based chatbot interface. |
| scripts/utility/monitor_progress.py | Progress monitoring utility. Tracks and displays ingestion progress. |
| scripts/utility/quick_status.py | Quick status check. Provides fast status overview of system. |
| scripts/utility/show_complete_attribution.py | Attribution display utility. Shows complete performance attribution. |
| scripts/utility/plotly_demo.py | Plotly chart examples. Demonstrates Plotly chart generation. |
| scripts/utility/chat_metrics.py | Chat metrics utility. Analyzes chatbot usage metrics. |
| scripts/utility/data_sources_backup.py | Data sources backup utility. Backs up data source configurations. |
| scripts/utility/refresh_ticker_catalog.py | Ticker catalog refresh utility. Updates ticker catalog with latest data. |

### 🏗️ Core Components

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/analytics_engine.py | Core analytics engine performing KPI calculations, metric aggregations, and financial analysis. Central component for all financial calculations. |
| src/finanlyzeos_chatbot/chatbot.py | Main chatbot orchestration module. Integrates RAG layer, LLM client, context builder, and response verifier. Handles conversation flow and intent routing. |
| src/finanlyzeos_chatbot/config.py | Configuration management and settings loader. Reads environment variables, .env files, and provides default settings. |
| src/finanlyzeos_chatbot/database.py | Database abstraction layer supporting both SQLite and PostgreSQL. Handles schema migrations, connection pooling, and query execution. |
| src/finanlyzeos_chatbot/llm_client.py | LLM provider abstraction layer. Supports OpenAI API and local echo mode. Handles API calls, error handling, and response formatting. |
| src/finanlyzeos_chatbot/web.py | FastAPI web server providing REST API endpoints. Handles /chat, /metrics, /facts, /audit, and /health endpoints. Serves static files and web UI. |

### 📥 Data & Ingestion

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/data_ingestion.py | Data ingestion pipeline orchestrating SEC, Yahoo Finance, and Bloomberg data sources. Handles async ingestion, rate limiting, and error recovery. |
| src/finanlyzeos_chatbot/data_sources.py | Data source integrations for SEC EDGAR, Yahoo Finance, and Bloomberg. Provides client classes for each data source. |
| src/finanlyzeos_chatbot/external_data.py | External data providers for FRED (Federal Reserve Economic Data) and IMF (International Monetary Fund). Fetches macroeconomic indicators. |
| src/finanlyzeos_chatbot/macro_data.py | Macroeconomic data provider. Aggregates and normalizes macroeconomic indicators from multiple sources. |
| src/finanlyzeos_chatbot/multi_source_aggregator.py | Multi-source data aggregation. Combines data from multiple sources (SEC, Yahoo, FRED, IMF) into unified format. |
| src/finanlyzeos_chatbot/sec_bulk.py | SEC bulk data access. Provides caching and bulk access to SEC EDGAR data. |
| src/finanlyzeos_chatbot/secdb.py | SEC database utilities. Helper functions for SEC data access and normalization. |

### 🧠 Context & RAG

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/context_builder.py | Financial context builder for RAG layer. Assembles ML forecast details, portfolio data, financial metrics, SEC filings, and macroeconomic context. Includes "EXPLICIT DATA DUMP" section for technical details. |
| src/finanlyzeos_chatbot/ml_response_verifier.py | ML forecast response verification and enhancement. Verifies LLM responses include all required technical details (model architecture, hyperparameters, training details). Automatically enhances responses if details are missing. |
| src/finanlyzeos_chatbot/followup_context.py | Follow-up question context management. Maintains conversation context for follow-up questions and pronoun resolution. |
| src/finanlyzeos_chatbot/intent_carryover.py | Intent carryover between conversations. Preserves user intent across conversation turns for better context understanding. |

### 🔤 Parsing & NLP

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/parsing/alias_builder.py | Ticker alias resolution for S&P 500. Normalizes company mentions, loads alias sets, applies overrides, and resolves tickers with fuzzy fallbacks. |
| src/finanlyzeos_chatbot/parsing/aliases.json | Generated ticker aliases covering S&P 500 companies. Consumed at runtime by parser for ticker resolution. |
| src/finanlyzeos_chatbot/parsing/ontology.py | Metric ontology defining KPI definitions, synonyms, and relationships. Provides structured knowledge base for financial metrics. |
| src/finanlyzeos_chatbot/parsing/parse.py | Natural language parser converting prompts into structured intents. Extracts tickers, metrics, periods, and warnings from user queries. |
| src/finanlyzeos_chatbot/parsing/time_grammar.py | Time period parser handling fiscal/calendar ranges, lists, quarters, and relative windows. Flexible grammar for temporal expressions. |
| src/finanlyzeos_chatbot/parsing/abbreviations.py | Abbreviation expansion. Expands common financial abbreviations (e.g., "rev" → "revenue"). |
| src/finanlyzeos_chatbot/parsing/company_groups.py | Company group detection. Identifies and handles company groups (e.g., "FAANG", "tech companies"). |
| src/finanlyzeos_chatbot/parsing/comparative.py | Comparative language parsing. Handles comparative queries (e.g., "better than", "higher than", "compare"). |
| src/finanlyzeos_chatbot/parsing/conditionals.py | Conditional statement parsing. Handles conditional queries (e.g., "if revenue > 100B", "when P/E < 20"). |
| src/finanlyzeos_chatbot/parsing/fuzzy_quantities.py | Fuzzy quantity parsing. Handles approximate quantities (e.g., "around 100B", "roughly 50%"). |
| src/finanlyzeos_chatbot/parsing/metric_inference.py | Metric inference from context. Infers missing metrics from conversation context and query patterns. |
| src/finanlyzeos_chatbot/parsing/multi_intent.py | Multi-intent detection. Identifies and handles queries with multiple intents (e.g., "compare AAPL and MSFT revenue and earnings"). |
| src/finanlyzeos_chatbot/parsing/natural_filters.py | Natural language filters. Converts natural language filters into structured query filters. |
| src/finanlyzeos_chatbot/parsing/negation.py | Negation handling. Properly handles negated queries (e.g., "not revenue", "excluding tech"). |
| src/finanlyzeos_chatbot/parsing/question_chaining.py | Question chaining detection. Identifies related questions and maintains context across question chains. |
| src/finanlyzeos_chatbot/parsing/sentiment.py | Sentiment analysis. Analyzes sentiment in user queries and financial data. |
| src/finanlyzeos_chatbot/parsing/temporal_relationships.py | Temporal relationship parsing. Handles temporal relationships (e.g., "before 2020", "after Q3", "during 2021-2023"). |
| src/finanlyzeos_chatbot/parsing/trends.py | Trend detection. Identifies trend-related queries (e.g., "increasing", "declining", "stable"). |

### ✏️ Spelling & Correction

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/spelling/company_corrector.py | Company name spelling correction. Corrects misspelled company names using fuzzy matching. |
| src/finanlyzeos_chatbot/spelling/correction_engine.py | Main spelling correction engine. Orchestrates spelling correction for companies, metrics, and other entities. |
| src/finanlyzeos_chatbot/spelling/fuzzy_matcher.py | Fuzzy string matching. Provides fuzzy matching algorithms for entity resolution. |
| src/finanlyzeos_chatbot/spelling/metric_corrector.py | Metric name spelling correction. Corrects misspelled metric names using fuzzy matching. |

### 🧭 Routing

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/routing/enhanced_router.py | Enhanced intent routing with dashboard detection. Routes queries to appropriate handlers (dashboard, chatbot, export, etc.). |

### 📊 Analytics Modules

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/sector_analytics.py | Sector benchmarking using GICS sectors. Compares company metrics against sector averages and peers. |
| src/finanlyzeos_chatbot/anomaly_detection.py | Anomaly detection using Z-score analysis. Identifies outliers in financial metrics. |
| src/finanlyzeos_chatbot/predictive_analytics.py | Predictive analytics including regression and CAGR calculations. Provides forward-looking analysis. |
| src/finanlyzeos_chatbot/advanced_kpis.py | Advanced KPI calculator with 30+ financial ratios. Calculates complex metrics like EV/EBITDA, ROIC, FCF yield, etc. |

### 💼 Portfolio Management

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/portfolio.py | Main portfolio management module (combined). Provides portfolio validation, enrichment, statistics, exposure analysis, attribution, scenarios, and risk metrics. Central module for all portfolio operations. |
| src/finanlyzeos_chatbot/portfolio_optimizer.py | Portfolio optimization using mean-variance optimization. Optimizes portfolios for maximum Sharpe ratio, minimum variance, or target return. |
| src/finanlyzeos_chatbot/portfolio_risk_metrics.py | Risk metrics calculation including CVaR, VaR, Sharpe ratio, Sortino ratio, tracking error, and beta. Provides comprehensive risk analysis. |
| src/finanlyzeos_chatbot/portfolio_attribution.py | Performance attribution using Brinson-Fachler model. Decomposes active return into allocation, selection, and interaction effects. |
| src/finanlyzeos_chatbot/portfolio_scenarios.py | Scenario analysis and stress testing. Runs equity drawdown scenarios, sector rotation scenarios, and custom scenarios. |
| src/finanlyzeos_chatbot/portfolio_exposure.py | Exposure analysis for sector and factor exposure. Calculates sector allocation, factor exposures (beta, momentum, value, size, quality), and concentration metrics. |
| src/finanlyzeos_chatbot/portfolio_calculations.py | Portfolio calculation utilities. Helper functions for portfolio calculations (weights, returns, correlations, etc.). |
| src/finanlyzeos_chatbot/portfolio_enrichment.py | Portfolio enrichment with fundamentals. Enriches portfolio holdings with P/E ratios, dividend yields, ROE, ROIC, and sector classifications. |
| src/finanlyzeos_chatbot/portfolio_enhancements.py | Portfolio enhancement utilities. Additional utilities for portfolio enhancements and transformations. |
| src/finanlyzeos_chatbot/portfolio_reporting.py | Portfolio reporting utilities. Generates portfolio reports and summaries. |
| src/finanlyzeos_chatbot/portfolio_trades.py | Trade recommendation utilities. Generates buy/sell recommendations for portfolio rebalancing. |
| src/finanlyzeos_chatbot/portfolio_export.py | Portfolio export functionality for PowerPoint, PDF, and Excel. Generates professional portfolio reports. |
| src/finanlyzeos_chatbot/portfolio_ppt_builder.py | Portfolio PowerPoint builder. Creates 12-slide professional portfolio presentations. |

### 🤖 ML Forecasting

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/ml_forecasting/ml_forecaster.py | Main ML forecaster with model selection. Orchestrates all ML forecasting models and selects best model based on historical performance. |
| src/finanlyzeos_chatbot/ml_forecasting/arima_forecaster.py | ARIMA model for statistical time series forecasting. Best for short-term forecasts and trend-following patterns. Automatically optimizes hyperparameters using AIC/BIC. |
| src/finanlyzeos_chatbot/ml_forecasting/prophet_forecaster.py | Prophet model for seasonal pattern forecasting. Best for seasonal patterns, holidays, and long-term trends. Handles missing data and outliers. |
| src/finanlyzeos_chatbot/ml_forecasting/ets_forecaster.py | ETS model for exponential smoothing. Best for smooth trends and exponential growth/decay patterns. Automatically selects from 30 possible configurations. |
| src/finanlyzeos_chatbot/ml_forecasting/lstm_forecaster.py | LSTM model for deep learning RNN forecasting. Best for complex patterns, non-linear relationships, and long-term dependencies. Multi-layer architecture with dropout and batch normalization. |
| src/finanlyzeos_chatbot/ml_forecasting/transformer_forecaster.py | Transformer model for attention-based forecasting. Best for long-term dependencies and complex patterns. Multi-head attention architecture with positional encoding. |
| src/finanlyzeos_chatbot/ml_forecasting/preprocessing.py | Data preprocessing for scaling, normalization, outlier handling, and missing data treatment. Prepares time series data for ML models. |
| src/finanlyzeos_chatbot/ml_forecasting/feature_engineering.py | Feature engineering utilities. Creates technical indicators, lag features, and other engineered features for ML models. |
| src/finanlyzeos_chatbot/ml_forecasting/hyperparameter_tuning.py | Hyperparameter optimization using Optuna. Optimizes model hyperparameters using Bayesian optimization. |
| src/finanlyzeos_chatbot/ml_forecasting/backtesting.py | Model backtesting utilities. Tests model performance on historical data with walk-forward validation. |
| src/finanlyzeos_chatbot/ml_forecasting/validation.py | Model validation utilities. Validates model performance using cross-validation and holdout sets. |
| src/finanlyzeos_chatbot/ml_forecasting/explainability.py | Model explainability using SHAP values and attention weights. Provides insights into model predictions. |
| src/finanlyzeos_chatbot/ml_forecasting/uncertainty.py | Uncertainty quantification. Calculates prediction intervals and confidence bounds for forecasts. |
| src/finanlyzeos_chatbot/ml_forecasting/regime_detection.py | Regime detection for identifying market states. Detects different market regimes (bull, bear, volatile) in time series data. |
| src/finanlyzeos_chatbot/ml_forecasting/technical_indicators.py | Technical indicators for feature engineering. Calculates RSI, MACD, Bollinger Bands, and other technical indicators. |
| src/finanlyzeos_chatbot/ml_forecasting/external_factors.py | External factor integration. Incorporates external factors (macroeconomic indicators, market sentiment) into forecasts. |
| src/finanlyzeos_chatbot/ml_forecasting/multivariate_forecaster.py | Multivariate forecasting. Handles forecasting with multiple input variables and dependencies. |

### 📤 Export & Presentation

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/export_pipeline.py | Export pipeline for PDF, PPTX, and Excel generation. Orchestrates export generation for dashboards and reports. |
| src/finanlyzeos_chatbot/cfi_ppt_builder.py | CFI-style PowerPoint builder generating 12-slide professional presentations. Creates investment-grade presentations with charts and analysis. |
| src/finanlyzeos_chatbot/table_renderer.py | ASCII table rendering for CLI output. Formats financial data into readable tables. |

### 🛠️ Utilities

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/tasks.py | Task queue management. Handles background tasks, async operations, and task scheduling. |
| src/finanlyzeos_chatbot/help_content.py | Help content and documentation. Provides help text and documentation for chatbot features. |
| src/finanlyzeos_chatbot/dashboard_utils.py | Dashboard utility functions. Helper functions for dashboard generation and data formatting. |
| src/finanlyzeos_chatbot/document_processor.py | Document processing utilities. Extracts text from PDFs, Word documents, and other file formats. |
| src/finanlyzeos_chatbot/imf_proxy.py | IMF data proxy. Provides proxy access to IMF data sources. |
| src/finanlyzeos_chatbot/kpi_backfill.py | KPI backfill utilities. Backfills missing KPI values using interpolation and extrapolation. |
| src/finanlyzeos_chatbot/backfill_policy.py | Backfill policy management. Defines policies for data backfilling and gap filling. |
| src/finanlyzeos_chatbot/ticker_universe.py | Ticker universe management. Manages ticker universes (S&P 500, custom, etc.) and provides ticker lists. |

### 🌐 Web Assets

| Path | Description |
|------|-------------|
| webui/app.js | SPA logic, progress timeline updates, settings panel, and chat interactions. Handles real-time progress tracking and message rendering. |
| webui/styles.css | Styling for the SPA (dark/light friendly, timeline badges, typography). Professional markdown formatting with custom fonts and spacing. |
| webui/index.html | Web UI entry point. Main HTML file for the single-page application. |
| webui/favicon.svg | Favicon for the web application. |
| webui/package.json | Node.js dependencies for web UI development. |
| webui/service-worker.js | Service worker for PWA functionality. Enables offline support and caching. |
| webui/start_dashboard.js | Dashboard startup script. Initializes dashboard components. |
| webui/cfi_dashboard.html | CFI dashboard HTML. Standalone dashboard page for company financial analysis. |
| webui/cfi_dashboard.js | CFI dashboard JavaScript. Dashboard logic and interactivity. |
| webui/cfi_dashboard.css | CFI dashboard styling. Dashboard-specific CSS. |
| webui/cfi_compare.html | CFI compare view HTML. Comparison dashboard for multiple companies. |
| webui/cfi_compare.js | CFI compare view JavaScript. Comparison logic and interactivity. |
| webui/cfi_compare.css | CFI compare view styling. Comparison-specific CSS. |
| webui/cfi_dense.html | CFI dense view HTML. Compact dashboard view. |
| webui/cfi_dense.js | CFI dense view JavaScript. Dense view logic. |
| webui/cfi_dense.css | CFI dense view styling. Dense view-specific CSS. |
| src/finanlyzeos_chatbot/static/app.js | Frontend application logic (SPA). Main JavaScript for web UI. |
| src/finanlyzeos_chatbot/static/styles.css | UI styling (markdown, progress indicator). Comprehensive CSS for all UI components. |
| src/finanlyzeos_chatbot/static/index.html | Web UI entry point. Main HTML file. |
| src/finanlyzeos_chatbot/static/favicon.svg | Favicon. |
| src/finanlyzeos_chatbot/static/cfi_dashboard.html | CFI dashboard HTML. |
| src/finanlyzeos_chatbot/static/cfi_dashboard.js | CFI dashboard JavaScript. |
| src/finanlyzeos_chatbot/static/cfi_dashboard.css | CFI dashboard styling. |
| src/finanlyzeos_chatbot/static/portfolio_dashboard.html | Portfolio dashboard HTML. Portfolio analysis dashboard. |
| src/finanlyzeos_chatbot/static/portfolio_dashboard.js | Portfolio dashboard JavaScript. Portfolio dashboard logic. |
| src/finanlyzeos_chatbot/static/data/company_universe.json | Company universe metadata. Precompiled company data for web UI. |
| src/finanlyzeos_chatbot/static/data/kpi_library.json | KPI library definitions. Precompiled KPI definitions for web UI. |

### 🧪 Tests

#### Unit Tests

| File | Description |
|------|-------------|
| tests/unit/test_analytics.py | Analytics unit tests. Tests analytics engine functionality. |
| tests/unit/test_analytics_engine.py | Analytics engine unit tests. Tests core analytics calculations. |
| tests/unit/test_cli_tables.py | CLI table rendering tests. Tests ASCII table formatting. |
| tests/unit/test_database.py | Database unit tests. Tests database operations and queries. |
| tests/unit/test_data_ingestion.py | Data ingestion unit tests. Tests data ingestion pipeline. |

#### Integration Tests

| File | Description |
|------|-------------|
| tests/integration/test_chatbot_sec_fix.py | SEC integration tests. Tests SEC API integration and error handling. |
| tests/integration/test_sec_api_fix.py | SEC API integration tests. Tests SEC API client functionality. |
| tests/integration/test_new_analytics.py | New analytics integration tests. Tests new analytics features. |
| tests/integration/test_dashboard_flow.py | Dashboard workflow integration tests. Tests end-to-end dashboard generation. |
| tests/integration/test_fixes.py | General fixes integration tests. Tests various bug fixes. |
| tests/integration/test_enhanced_routing.py | Enhanced routing integration tests. Tests intent routing functionality. |

#### End-to-End Tests

| File | Description |
|------|-------------|
| tests/e2e/test_all_sp500_dashboards.py | Full S&P 500 dashboard test. Tests dashboard generation for all S&P 500 companies. |
| tests/e2e/test_sample_companies.py | Sample companies test (10 companies). Tests dashboard generation for sample companies. |
| tests/e2e/test_single_company.py | Single company test (Apple). Tests dashboard generation for single company. |
| tests/e2e/test_chatbot_stress_test.py | FinalyzeOS stress test. Tests chatbot under high load. |
| tests/e2e/test_chatgpt_style.py | ChatGPT-style test. Tests ChatGPT-style responses. |
| tests/e2e/test_comprehensive_sources.py | Comprehensive sources test. Tests multi-source data aggregation. |
| tests/e2e/test_ml_detailed_answers.py | ML detailed answers test. Tests ML forecast response detail and verification. |

#### Parser & NLP Tests

| File | Description |
|------|-------------|
| tests/test_alias_resolution.py | Alias resolution tests. Validates alias coverage, manual overrides, fuzzy warnings, and ordering. |
| tests/test_time_grammar.py | Time grammar tests. Ensures time grammar handles ranges, lists, quarter formats, and two-digit years. |
| tests/test_nl_parser.py | Natural language parser tests. End-to-end structured intent checks for compare/trend prompts and parser warnings. |
| tests/test_abbreviations.py | Abbreviation tests. Tests abbreviation expansion functionality. |
| tests/test_advanced_followups.py | Advanced follow-up tests. Tests follow-up question handling. |
| tests/test_company_groups.py | Company group tests. Tests company group detection. |
| tests/test_comparative_language.py | Comparative language tests. Tests comparative query parsing. |
| tests/test_conditionals.py | Conditional statement tests. Tests conditional query parsing. |
| tests/test_enhanced_intents.py | Enhanced intent tests. Tests enhanced intent detection. |
| tests/test_enhanced_metric_synonyms.py | Enhanced metric synonym tests. Tests metric synonym expansion. |
| tests/test_enhanced_question_patterns.py | Enhanced question pattern tests. Tests question pattern recognition. |
| tests/test_followup_features_unit.py | Follow-up feature unit tests. Tests follow-up feature functionality. |
| tests/test_fuzzy_quantities.py | Fuzzy quantity tests. Tests fuzzy quantity parsing. |
| tests/test_metric_inference.py | Metric inference tests. Tests metric inference from context. |
| tests/test_multi_intent.py | Multi-intent tests. Tests multi-intent detection. |
| tests/test_natural_filters.py | Natural filter tests. Tests natural language filter parsing. |
| tests/test_negation_handling.py | Negation handling tests. Tests negation handling in queries. |
| tests/test_performance_benchmarks.py | Performance benchmark tests. Tests parser performance. |
| tests/test_period_normalization.py | Period normalization tests. Tests period normalization. |
| tests/test_pronoun_resolution.py | Pronoun resolution tests. Tests pronoun resolution in queries. |
| tests/test_question_chaining.py | Question chaining tests. Tests question chaining detection. |
| tests/test_sentiment.py | Sentiment analysis tests. Tests sentiment analysis functionality. |
| tests/test_spelling_correction.py | Spelling correction tests. Tests spelling correction functionality. |
| tests/test_temporal_relationships.py | Temporal relationship tests. Tests temporal relationship parsing. |
| tests/test_time_period_enhancement.py | Time period enhancement tests. Tests time period enhancement. |
| tests/test_trend_direction.py | Trend direction tests. Tests trend detection. |

#### Portfolio Tests

| File | Description |
|------|-------------|
| tests/test_portfolio_detection_working.py | Portfolio detection tests. Tests portfolio detection from user queries. |
| tests/test_portfolio_patterns.py | Portfolio pattern tests. Tests portfolio pattern recognition. |
| tests/test_portfolio_questions.py | Portfolio question tests. Tests portfolio question handling. |
| tests/test_portfolio_stress_test.py | Portfolio stress test. Tests portfolio analysis under stress scenarios. |

#### ML Forecasting Tests

| File | Description |
|------|-------------|
| tests/test_all_forecast_prompts.py | All forecast prompt tests. Tests all ML forecasting prompt patterns. |
| tests/test_forecast_detection.py | Forecast detection tests. Tests forecast query detection. |
| tests/test_forecast_prompts.py | Forecast prompt tests. Tests forecast prompt patterns. |
| tests/test_ml_context_debug.py | ML context debug tests. Tests ML context building and debugging. |
| tests/test_ml_detailed_response.py | ML detailed response tests. Tests ML forecast response detail and verification. |

## ✅ Quality and Testing

- Run the suite: `pytest`
- Parser & alias focus: `pytest tests/test_alias_resolution.py tests/test_time_grammar.py tests/test_nl_parser.py`
- Target a single test: `pytest tests/test_cli_tables.py::test_table_command_formats_rows`
- Manual sanity: point LLM_PROVIDER=local to avoid burning API credits during smoke tests.
- Database reset: delete finanlyzeos_chatbot.sqlite3 and rerun ingestion—migrations run automatically on startup.

CI isn't configured by default, but pytest -ra (preconfigured in pyproject.toml) surfaces skipped/xfail tests neatly. Consider adding ruff or black once your team standardises formatting.

## 🔧 Troubleshooting

### ⚠️ General Issues

- **"OpenAI API key not found"** – set OPENAI_API_KEY, store it via keyring, or create ~/.config/finanlyzeos-chatbot/openai_api_key.
- **WinError 10048 when starting the server** – another process is on the port. Run `Get-NetTCPConnection -LocalPort 8000` and terminate it, or start with `--port 8001`.
- **PostgreSQL auth failures** – confirm SSL/network settings, then double-check POSTGRES_* vars; the DSN is logged at debug level when DATABASE_TYPE=postgresql is active.
- **Pytest cannot locate modules** – run from the repo root so the pythonpath = ["src", "."] entry in pyproject.toml kicks in.

### 📥 Data Ingestion Issues

#### ❌ "No data showing up in chatbot after ingestion"
**Cause:** Metrics need to be refreshed after data ingestion.
**Solution:**
```bash
python -c "from finanlyzeos_chatbot.config import load_settings; from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine; AnalyticsEngine(load_settings()).refresh_metrics(force=True)"
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
DATABASE_PATH=./data/sqlite/finanlyzeos_chatbot.sqlite3
```
Or use the full path:
```bash
DATABASE_PATH=C:/Users/YOUR_USERNAME/Documents/GitHub/Project/finanlyzeos_chatbot.sqlite3
```

#### "ModuleNotFoundError: finanlyzeos_chatbot"
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
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/finanlyzeos_chatbot.sqlite3'); cursor = conn.cursor(); print(f'financial_facts: {cursor.execute(\"SELECT COUNT(*) FROM financial_facts\").fetchone()[0]:,}'); print(f'metric_snapshots: {cursor.execute(\"SELECT COUNT(*) FROM metric_snapshots\").fetchone()[0]:,}'); conn.close()"

# 2. Check year coverage
python -c "import sqlite3; conn = sqlite3.connect('C:/Users/YOUR_PATH/finanlyzeos_chatbot.sqlite3'); cursor = conn.cursor(); cursor.execute('SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(DISTINCT ticker) FROM financial_facts'); print('Years: %s-%s | Companies: %s' % cursor.fetchone()); conn.close()"

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

- 📖 [`docs/orchestration_playbook.md`](docs/orchestration_playbook.md) – Three ingestion/orchestration patterns (local queue, serverless fetchers, batch jobs) and how to wire them into FinalyzeOSChatbot
- 💻 **Inline Module Documentation** - Comprehensive docs across `src/finanlyzeos_chatbot/` describe invariants, data contracts, and extension hooks
- 🔧 **Versioning Best Practices** - Consider versioning your `.env` templates and deployment runbooks alongside these docs as the project evolves

## 🎓 System Overview (Professor Summary)

### Core Components
| Layer | Function | Key files |
|-------|----------|-----------|
| Experiences | Web dashboard, CLI, REST API | webui/, 
un_chatbot.py, serve_chatbot.py |
| Parsing | Ticker/period normalisation | src/finanlyzeos_chatbot/parsing/alias_builder.py, 	ime_grammar.py |
| Retrieval & Analytics | KPI calculations, scenarios | src/finanlyzeos_chatbot/analytics_engine.py, database.py, data_ingestion.py |
| RAG Orchestration | Prompt assembly, LLM calls | src/finanlyzeos_chatbot/chatbot.py, llm_client.py |
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

**FinalyzeOS** - Institutional-grade analytics tooling for finance teams

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