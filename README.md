<div align="center">

# 📊 FinalyzeOS Chatbot Platform

### Institutional-Grade Finance Copilot with Explainable AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/haniae/Team2-CBA-Project)
[![Data Coverage](https://img.shields.io/badge/data-1,599%20companies%20%7C%2018%20years-success)](https://github.com/haniae/Team2-CBA-Project)
[![NLU Coverage](https://img.shields.io/badge/NLU-100%25%20patterns%20%7C%2093%20metrics-blue)](https://github.com/haniae/Team2-CBA-Project)
[![ML Models](https://img.shields.io/badge/ML-8%20forecasting%20models-purple)](https://github.com/haniae/Team2-CBA-Project)
[![Intents](https://img.shields.io/badge/intents-40%2B%20types-orange)](https://github.com/haniae/Team2-CBA-Project)
[![Spelling](https://img.shields.io/badge/spelling-90%25%20company%20%7C%20100%25%20metric-green)](https://github.com/haniae/Team2-CBA-Project)

**FinalyzeOS** is an institutional-grade copilot for finance teams. It pairs deterministic market analytics with a conversational interface so analysts can ask natural-language questions, inspect lineage, and keep data pipelines auditable. This repository underpins our Fall 2025 DNSC 6317 practicum 🎓at The George Washington University, where we are building and governing an explainable finance copilot that can support regulated teams. Our objectives include stress-testing FinalyzeOS against real analyst workflows, documenting orchestration strategies for enterprise rollouts, and demonstrating responsible AI guardrails around data access, lineage, and scenario planning.

Contributors  
**Hania A.** haniaa@gwmail.gwu.edu

**Van Nhi Vuong** vannhi.vuong@gwmail.gwu.edu

**Malcolm Muoriyarwa** malcolm.munoriyarwa@gwmail.gwu.edu

**Devarsh Patel** devarsh.patel@gwmail.gwu.edu . 

**Acknowledgments** Special thanks to Professor Patrick Hall (The George Washington University) for his outstanding mentorship and tireless support. His guidance and encouragement made this project possible.

[Setup Guide](#️-complete-setup-guide) • [Documentation](docs/) • [Features](#core-capabilities) • [Contributing](CONTRIBUTING.md)

---

## ⚡Quick Start

**Get started in 30 seconds:**

```bash
# 1. Clone and setup
git clone https://github.com/haniae/Team2-CBA-Project.git
cd Team2-CBA-Project
python -m venv .venv
.\.venv\Scripts\activate  # Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 2. Quick test (100 companies, ~15-30 min)
python scripts/ingestion/ingest_universe.py --universe-file data/tickers/test_100.txt --years 5

# 3. Run the chatbot
python run_chatbot.py
# Or web UI: python serve_chatbot.py --port 8000
```

**Try these queries:**
 `"What is Apple's revenue?"`
 `"Compare Microsoft and Google's profit margins"`
 `"Show me Tesla's free cash flow in 2023"`
 `"Why is NVDA's stock price increasing?"`

📖 **For detailed setup with options (100/250/500/1500 companies), see [Complete Setup Guide](#️-complete-setup-guide)**

---

</div>

## 📚 Table of Contents

### Getting Started
- [⚡ Quick Start](#-quick-start)
- [🛠️ Complete Setup Guide](#️-complete-setup-guide)
- [📊 Current Data Coverage](#-current-data-coverage)

### Core Features
- [⚡ Core Capabilities](#-core-capabilities)
- [🚀 Advanced Analytics](#-advanced-analytics)
- [🤖 Machine Learning Forecasting](#-machine-learning-forecasting-new)
- [📚 Retrieval-Augmented Generation](#-retrieval-augmented-generation)
- [📊 Portfolio Management](#-portfolio-management)

### Technical Documentation
- [🏗️ Architecture Map](#️-architecture-map)
- [🧠 Retrieval & ML Internals](#-retrieval--ml-internals)
- [💬 Running FinalyzeOS](#-running-finalyzeos)
- [📥 Data Ingestion Guide](#-data-ingestion-guide)
- [⚙️ Configuration Reference](#️-configuration-reference)
- [🗄️ Database Schema](#️-database-schema)

### Project Structure
- [📁 Project Layout](#-project-layout)
- [📝 File Reference](#-file-reference)

### Support
- [✅ Quality and Testing](#-quality-and-testing)
- [🔧 Troubleshooting](#-troubleshooting)
- [📚 Further Reading](#-further-reading)
- [🎓 System Overview (Professor Summary)](#-system-overview-professor-summary)
- [🧭 Full Docs Index](docs/README.md)



### 🎯 Project Focus

- 🔧 **Production-Grade Analytics** - Translate classroom techniques into a production-grade analytics assistant that blends deterministic KPI calculations with auditable LLM experiences
- 🛡️ **Resilient Pipelines** - Stand up KPI coverage pipelines that stay resilient when market data lags or filing assumptions drift
- 📚 **Practitioner-Ready Documentation** - Deliver deployment runbooks and testing strategies so stakeholders can re-create the practicum outcomes after the semester concludes



## 📖 Overview

FinalyzeOS ships as a **batteries-included template** for building finance copilots. Out of the box you gain:

- 🗄️ **Durable Storage** - SQLite by default, PostgreSQL optional for conversations, facts, metrics, audit trails, and scenarios
- 📊 **Analytics Engines** - Normalise SEC filings, hydrate them with market quotes, and expose tabular as well as scenario-ready metrics
- 🤖 **Flexible LLM Integration** - Deterministic echo model for testing or OpenAI for production deployments
- 🖥️ **Multi-Channel Experiences** - CLI REPL, FastAPI REST service, single-page web UI so you can prototype quickly and scale later
- 📚 **Rich Documentation** - Complete guides for scaling "any company" requests and replicating workflows in production

### 🎯 What Can You Do?

Ask natural language questions and get instant, sourced financial insights:

**Single Company Analysis:**
- `"What is Apple's revenue?"` → Get revenue with YoY growth, CAGR, and business drivers
- `"Show me Tesla's free cash flow"` → Detailed FCF analysis with trends and context
- `"What's Microsoft's P/E ratio?"` → Valuation metrics with historical comparison
- `"What is Appel's revenue?"` → Automatically corrects spelling mistakes (90% success rate)
- `"Show me revenu for Apple"` → Handles metric typos (100% success rate)

**Comparisons:**
- `"Compare Apple vs Microsoft's profit margins"` → Side-by-side analysis with sector benchmarks
- `"How do tech companies stack up on ROE?"` → Multi-company ranking and percentile analysis
- `"Compare Microsft and Googl"` → Spelling mistakes automatically corrected

**Deep Analysis:**
- `"Why is Tesla's margin declining?"` → Multi-factor explanation with quantified impacts
- `"What's driving Amazon's revenue growth?"` → Business segment breakdown and drivers
- `"Is NVDA overvalued?"` → Valuation analysis with peer comparison

**Forecasting & Scenarios:**
- `"Forecast Microsoft's revenue for 2026"` → ML-powered forecasts with confidence intervals
- `"What if Apple's revenue grows 10% faster?"` → Scenario analysis with impact on valuation

**Portfolio Management:**
- `"Show me my portfolio performance"` → Portfolio analytics with risk metrics
- `"What's my portfolio's sector exposure?"` → Diversification analysis

**Query Flexibility:**
- `"Apple revenue"` → Minimal queries work perfectly
- `"Revenue for Apple"` → Reversed word order supported
- `"What was Tesla's profit last quarter?"` → Temporal queries with natural language
- `"Top 5 companies by revenue"` → Ranking queries
- `"How has Microsoft's revenue changed over time?"` → Trend analysis queries

All responses include clickable SEC filing sources, charts, and exportable reports (PowerPoint, PDF, Excel).

---

## 🛠️ Complete Setup Guide

### **Step 1: Install Dependencies**

#### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **pip** (Python package manager)
- **Git** (to clone the repository)

#### Installation Steps

**1. Clone the Repository**
```bash
git clone https://github.com/haniae/Team2-CBA-Project.git
cd Team2-CBA-Project
```

**2. Create Virtual Environment**
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install Python Dependencies**
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

**4. Verify Installation**
```bash
# Check Python version (should be 3.10+)
python --version

# Verify key packages are installed
python -c "import fastapi, openai, pandas, sqlalchemy; print('✅ Core packages installed')"

# Verify FinalyzeOS imports
python -c "from finanlyzeos_chatbot import load_settings; print('✅ FinalyzeOS setup complete')"
```

**5. Configure Environment**
```bash
# Copy environment template
# Windows
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env

# Edit .env file and add your OpenAI API key (optional for testing)
# OPENAI_API_KEY=your_key_here
```

---

### **Step 2: Choose Your Data Ingestion Option**

Select the option that best fits your needs:

#### **Option 1: Quick Test (100 Companies) - ⚡ Fastest**
**Best for**: Quick testing, demos, learning the system  
**Time**: ~15-30 minutes  
**Database Size**: ~20-30 MB

```bash
# Create a custom ticker file with 100 companies
# Create file: data/tickers/test_100.txt with one ticker per line:
# AAPL
# MSFT
# GOOGL
# AMZN
# ... (add 100 tickers)

# Run ingestion
python scripts/ingestion/ingest_universe.py --universe-file data/tickers/test_100.txt --years 5 --chunk-size 10

# Load prices (optional, adds ~10 minutes)
python scripts/ingestion/load_historical_prices_15years.py
```

**Expected Results**:
- ~5,000-8,000 financial facts
- ~10,000-15,000 metric snapshots
- ~100,000 price records (if prices loaded)
- Database size: ~20-30 MB

---

#### **Option 2: Medium Coverage (250 Companies) - ⚖️ Balanced**
**Best for**: Testing with good coverage, small teams  
**Time**: ~1-2 hours  
**Database Size**: ~50-80 MB

```bash
# Create a custom ticker file with 250 companies
# Create file: data/tickers/test_250.txt with 250 tickers

# Run ingestion
python scripts/ingestion/ingest_universe.py --universe-file data/tickers/test_250.txt --years 10 --chunk-size 15 --resume

# Load prices (optional, adds ~30 minutes)
python scripts/ingestion/load_historical_prices_15years.py
```

**Expected Results**:
- ~15,000-25,000 financial facts
- ~40,000-60,000 metric snapshots
- ~250,000 price records (if prices loaded)
- Database size: ~50-80 MB

---

#### **Option 3: S&P 500 (500 Companies) - 🎯 Recommended**
**Best for**: Production use, comprehensive analysis  
**Time**: ~2-3 hours  
**Database Size**: ~150-200 MB

```bash
# Ingest S&P 500 financial data (15 years)
python scripts/ingestion/ingest_sp500_15years.py

# Load historical prices (1-2 hours)
python scripts/ingestion/load_historical_prices_15years.py

# Verify ingestion
python scripts/utility/check_ingestion_status.py
```

**Expected Results**:
- ~50,000-80,000 financial facts
- ~150,000-250,000 metric snapshots
- ~1.7M+ price records
- Database size: ~150-200 MB
- **Coverage**: 500 companies, 15 years of data

---

#### **Option 4: S&P 1500 (1,500 Companies) - 🚀 Full Coverage**
**Best for**: Maximum coverage, institutional use  
**Time**: ~6-9 hours  
**Database Size**: ~850 MB

```bash
# Ingest S&P 1500 (S&P 500 + MidCap + SmallCap)
python scripts/ingestion/ingest_extended_universe.py

# Load historical prices (2-3 hours)
python scripts/ingestion/load_historical_prices_15years.py

# Verify ingestion
python scripts/utility/check_ingestion_status.py
```

**Expected Results**:
- ~240,000+ financial facts
- ~750,000+ metric snapshots
- ~1.7M+ price records
- Database size: ~850 MB
- **Coverage**: 1,500 companies, 18 years of data

---

### **Step 3: Verify Your Setup**

After ingestion completes, verify everything works:

```bash
# Check database status
python scripts/utility/check_ingestion_status.py

# Or use the simple checker
python scripts/utility/check_correct_database.py

# Test the chatbot
python run_chatbot.py
```

**Test Queries**:
- "Show me Apple's revenue"
- "Compare Microsoft and Google's profit margins"
- "What's Tesla's free cash flow in 2023?"

---

### **Step 4: Start Using FinalyzeOS**

#### **Option A: Command Line Interface (CLI)**
```bash
python run_chatbot.py
```

#### **Option B: Web Interface**
```bash
python serve_chatbot.py --port 8000
```
Then open: `http://localhost:8000`

---

### 🚀 Quick Start Examples

**Try these queries immediately after setup:**

#### In CLI (`python run_chatbot.py`):
```
> What is Apple's revenue?
> Compare Microsoft and Google's profit margins
> Show me Tesla's free cash flow in 2023
> Why is NVDA's stock price increasing?
> Forecast Microsoft's revenue for 2026
```

#### In Web UI (`http://localhost:8000`):
1. Type: `"Show me Apple's dashboard"`
2. Type: `"Compare AAPL vs MSFT vs GOOGL"`
3. Type: `"What's driving Tesla's revenue growth?"`
4. Click **"Export PowerPoint"** to download a presentation

**Expected Response Times:**
- Simple queries: < 2 seconds
- Comparisons: 3-5 seconds
- Dashboards: 5-8 seconds
- Forecasts: 10-15 seconds

---

## 📊 Ingestion Comparison Table

| Option | Companies | Time | Database Size | Best For |
|--------|-----------|------|---------------|----------|
| **Quick Test** | 100 | 15-30 min | 20-30 MB | Learning, demos |
| **Medium** | 250 | 1-2 hours | 50-80 MB | Testing, small teams |
| **S&P 500** | 500 | 2-3 hours | 150-200 MB | Production use ⭐ |
| **S&P 1500** | 1,500 | 6-9 hours | 850 MB | Full coverage |

---

## 🔧 Troubleshooting Setup

### **Issue: Package Installation Fails**
```bash
# Upgrade pip first
pip install --upgrade pip

# Try installing in smaller batches
pip install fastapi uvicorn python-dotenv
pip install openai requests httpx
pip install pandas numpy sqlalchemy
pip install -r requirements.txt
```

### **Issue: Database Not Found**
```bash
# The database will be created automatically on first run
# Or manually initialize:
python -c "from finanlyzeos_chatbot.database import initialise; from pathlib import Path; initialise(Path('data/sqlite/finanlyzeos_chatbot.sqlite3'))"
```

### **Issue: Ingestion Stops or Fails**
```bash
# Most scripts support resume capability
# Just run the same command again - it will resume from where it stopped

# Check progress
python scripts/ingestion/monitor_ingestion.py

# Check for errors
python scripts/utility/check_ingestion_status.py
```

### **Issue: Out of Memory During Ingestion**
```bash
# Reduce batch size
python scripts/ingestion/ingest_universe.py --universe-file your_tickers.txt --years 10 --chunk-size 5

# Or process in smaller chunks
# Split your ticker file into multiple smaller files and process separately
```

---


## 📊 Current Data Coverage

The database currently contains **2,880,138 total rows** of financial data across 1,505 companies:

| Table | Rows | Description |
|-------|------|-------------|
| market_quotes | 1,730,061 | Historical daily price data (15+ years) |
| metric_snapshots | 777,979 | Pre-calculated analytics and KPIs |
| financial_facts | 243,777 | Raw SEC filing data (revenue, expenses, etc.) |
| company_filings | 80,332 | SEC filing metadata (10-K, 10-Q forms) |
| audit_events | 26,338 | Data ingestion and processing logs |
| kpi_values | 16,071 | KPI backfill and override values |
| ticker_aliases | 1,507 | Company ticker mappings |
| conversations | 3,979 | Chat history and user interactions |
| portfolio_holdings | 14 | Portfolio positions |
| scenario_results | 2 | Saved scenario analysis results |

### 📈 Data Characteristics

- 📅 **Year Range:** 2009-2027 (18 years of coverage)
- 🏢 **Companies:** 1,599 unique tickers supported (S&P 1500: S&P 500 + S&P 400 + S&P 600)
- 📊 **Metrics:** 93 unique financial metrics with 200+ natural language synonyms
- 🔤 **Natural Language:** 150+ question patterns, 40+ intent types, spelling mistake handling
- 📡 **Data Sources:** SEC EDGAR (10-K, 10-Q filings), Yahoo Finance (market quotes), FRED, IMF
- 🔄 **Update Frequency:** On-demand ingestion with smart gap detection
- 🔍 **Audit Trail:** Full lineage tracking for every data point
- 💾 **Database Size:** ~850 MB (SQLite file)

### 📊 Coverage Status Definitions

The Company Universe view categorizes companies by data completeness:

| Status | Criteria | Description |
|--------|----------|-------------|
| **✅ Complete** | 5+ years AND 12+ metrics | Good historical coverage with comprehensive metrics |
| **⚠️ Partial** | 2-4 years OR 6-11 metrics | Some data available but could use more years or metrics |
| **❌ Missing** | <2 years OR <6 metrics | Very little data or no data available |

**Note:** The chatbot can access **all 2.88M rows** of data regardless of coverage status. The coverage label is a UI indicator showing data completeness, not access restrictions.

**Current Coverage:**
- ✅ **Complete:** 1,035 companies (68%)
- ⚠️ **Partial:** 469 companies (31%)
- ❌ **Missing:** 13 companies (1%)

To improve coverage, run: `python scripts/ingestion/full_coverage_ingestion.py --years 20`

## ⚡ Core Capabilities

- 💬 **Multi-Channel Chat** – CLI REPL, REST API endpoints, and browser client with live status indicators
- 📊 **Deterministic Analytics** – Calculate primary/secondary metrics, growth rates, valuation multiples, and derived KPIs from the latest filings and quotes
- 📥 **Incremental Ingestion** – Pull SEC EDGAR facts, Yahoo quotes, and optional Bloomberg feeds with retry/backoff
- 🔒 **Audit-Ready Storage** – Complete metric snapshots, raw financial facts, audit events, and full chat history for compliance reviews
- 🤖 **Extensible LLM Layer** – Toggle between local echo model and OpenAI, or extend for other vendors
- 🔄 **Task Orchestration** – Queue abstraction for ingestion and long-running commands
- 🎯 **Advanced Natural Language Processing** – 100% query pattern detection, 90% company name spelling correction, 100% metric spelling correction, 40+ intent types, 150+ question patterns, 200+ metric synonyms
- 🏢 **Comprehensive Company Coverage** – Full support for all 1,599 S&P 1500 companies (S&P 500 + S&P 400 + S&P 600) via ticker symbol or company name
- 🤖 **8 ML Forecasting Models** – ARIMA, Prophet, ETS, LSTM, GRU, Transformer, Ensemble, and Auto selection for institutional-grade predictions
- 📚 **Enhanced RAG Integration** – Explicit data dumps, comprehensive context building, response verification, and technical detail enforcement for ML forecasts

## 🚀 Advanced Analytics 

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

FinalyzeOS blends deterministic analytics with a modular ML layer so finance teams can prototype forecasts without giving up auditability. The ML forecasting system integrates seamlessly with the advanced natural language processing layer, automatically handling spelling mistakes in company names and metrics, and recognizing forecast-related queries through 40+ intent types.

### Architecture Overview

- **Data Foundation:** `analytics_engine.AnalyticsEngine.refresh_metrics()` normalises SEC filings into `metric_snapshots`. Forecast pipelines consume the same curated metrics, keeping model inputs aligned with what the dashboard renders.
- **Model Registry:** Classical (Prophet, ARIMA/ETS) and ML estimators (LSTM, GRU, Transformer) live under `src/finanlyzeos_chatbot/ml_forecasting/`. **8 forecasting models** available: ARIMA, Prophet, ETS, LSTM, GRU, Transformer, Ensemble, and Auto (automatic selection). Shared base classes (`ml_forecasting.ml_forecaster`) expose a consistent interface so new models can be dropped in with minimal wiring.
- **Context Builder:** `context_builder.build_forecast_context()` assembles explicit data dumps (predictions, confidence bands, training diagnostics, model architecture, hyperparameters) that are injected verbatim into the LLM prompt. The bot cannot answer without citing these artefacts. Includes comprehensive technical details for institutional analysts.
- **Natural Language Integration:** The ML forecasting system automatically recognizes forecast queries through advanced intent detection, handles spelling mistakes in company names (90% success rate) and metrics (100% success rate), and supports natural language variations like "forecast", "predict", "project", "outlook", "what if", etc.

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

Natural-language answers are grounded in auditable data through a **production-grade RAG stack** that combines structured metrics, uploaded documents, semantic search, and advanced retrieval features.


### Document Lifecycle

1. **Upload:** The frontend posts to `/api/documents/upload`; FastAPI persists the binary, metadata, and extracted text alongside the active `conversation_id` (`web.py`, `database.store_uploaded_document`).  
2. **Extraction:** File-type specific parsers normalise text and capture warnings (e.g., OCR failures) that are surfaced back to the user and stored for context generation.  
3. **Indexing:** Documents are **automatically indexed** into ChromaDB for semantic search, with fallback to SQLite for deterministic recall. Every snippet can be reviewed in audits.

### Prompt-Aware Retrieval

- **Semantic Search**: `document_context.build_uploaded_document_context()` uses vector embeddings for semantic search over uploaded documents, with automatic fallback to token overlap matching.
- **Vector Store**: ChromaDB with `all-MiniLM-L6-v2` embeddings (384 dimensions) for fast semantic search.
- **Chunking Strategy**: 1500 characters with 200 overlap to prevent breaking mid-sentence.
- **Reranking**: Cross-encoder reranking improves relevance by ~10-20% over initial retrieval.
- Chunk overlap, snippet length, and stop-word lists are configurable, letting admins tighten or loosen recall depending on compliance needs.
- Matched terms, file metadata, and extraction warnings are embedded directly in the context so the model can cite sources verbatim.

### Context Fusion

- `FinalyzeOSChatbot.ask()` merges multiple layers: portfolio analytics, financial KPI context, SEC filing narratives (semantic search), and uploaded document snippets.  
- **Source Fusion**: Normalizes scores across sources and applies reliability weights (SQL=1.0, SEC=0.9, Uploaded=0.7).
- **Confidence Scoring**: Computes overall retrieval confidence and adjusts LLM tone accordingly.
- A document-follow-up heuristic (`_is_document_followup`) skips ticker summary heuristics when the user says "summarise it" immediately after an upload.  
- When heuristics cannot serve the request, the bot falls back to a plain conversational instruction set ensuring non-financial prompts still receive responses.

### Quality & Monitoring

- **Unit Tests:** `pytest tests/unit/test_document_upload.py tests/unit/test_uploaded_document_context.py` guard conversation linkage and snippet relevance.  
- **Evaluation Harness:** `scripts/evaluate_rag.py` computes retrieval metrics (Recall@K, MRR, nDCG) and QA metrics (exact match, factual consistency).
- **Observability:** Comprehensive logging of retrieval counts, scores, timing, document IDs, and anomalies via `RAGObserver`.
- **Guardrails:** Min relevance score (0.3), max context chars (15000), max documents (10), anomaly detection.
- **Telemetry:** Progress events (e.g., `context_sources_ready`, `upload_complete`) are emitted via Server-Sent Events so the UI can surface status breadcrumbs.  
- **Operational Runbooks:** Refer to `docs/guides/PORTFOLIO_QUESTIONS_GUIDE.md` (upload section) and inline module docstrings for end-to-end walkthroughs when onboarding analysts.

### Key Modules

- `src/finanlyzeos_chatbot/rag_retriever.py` – Unified retrieval interface (SQL + vector search)
- `src/finanlyzeos_chatbot/rag_reranker.py` – Cross-encoder reranking
- `src/finanlyzeos_chatbot/rag_fusion.py` – Source fusion and confidence scoring
- `src/finanlyzeos_chatbot/rag_grounded_decision.py` – Grounded decision layer
- `src/finanlyzeos_chatbot/rag_memory.py` – Memory-augmented RAG
- `src/finanlyzeos_chatbot/rag_controller.py` – Multi-hop query decomposition
- `src/finanlyzeos_chatbot/rag_observability.py` – Observability and guardrails
- `src/finanlyzeos_chatbot/rag_orchestrator.py` – Complete RAG orchestrator
- `src/finanlyzeos_chatbot/rag_prompt_template.py` – RAG prompt template builder
- `src/finanlyzeos_chatbot/document_context.py` – Prompt-aware chunking and snippet assembly
- `src/finanlyzeos_chatbot/chatbot.py` – Document-aware intent routing and context fusion
- `src/finanlyzeos_chatbot/static/app.js` & `webui/app.js` – Frontend upload orchestration with persistent `conversation_id`s
- `src/finanlyzeos_chatbot/web.py` – Backend API endpoint, validation, and database persistence

## 🔧 Troubleshooting

- Virtual environment not activating (Windows PowerShell): run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate with `.\.venv\Scripts\Activate.ps1`.
- SQLite locked errors: stop running servers/REPLs, wait a few seconds, try again. On Windows, ensure no other process (e.g., file indexers) holds the DB.
- pip install issues: upgrade pip (`python -m pip install --upgrade pip`) and retry `pip install -r requirements.txt`.
- Missing quotes/market data: re-run an ingestion command (e.g., `python scripts/ingestion/fill_data_gaps.py --years-back 3 --batch-size 10`) or narrow to specific tickers using `--ticker`.
- Port already in use: change `--port` (e.g., `python app/serve_chatbot.py --port 8010`) or stop the conflicting process.

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


#### 3. **Portfolio Exposure Analysis**
- **Sector Exposure**: Weight breakdown across 11 GICS sectors (Technology, Financials, Healthcare, etc.)
- **Factor Exposure**: Beta, momentum, value, size, and quality factor exposures
- **Concentration Analysis**: HHI, top 10 concentration ratio, maximum position weights
- **Geographic Exposure**: Regional allocation (if available in data)


#### 4. **Portfolio Optimization**
- **Mean-Variance Optimization**: Optimize for maximum Sharpe ratio, minimum variance, or target return
- **Constraint Support**: Sector limits, position limits, turnover constraints
- **Rebalancing Recommendations**: Specific buy/sell recommendations with expected impact
- **Performance Projections**: Expected return, variance, and Sharpe ratio for optimized portfolio


#### 5. **Performance Attribution (Brinson-Fachler)**
- **Active Return Decomposition**: Total active return broken down into allocation, selection, and interaction effects
- **Top Contributors**: Best performing positions and their contribution to portfolio returns
- **Top Detractors**: Worst performing positions and their impact
- **Sector-Level Analysis**: Which sectors drove portfolio performance


#### 6. **Risk Metrics & Stress Testing**
- **CVaR (Conditional Value at Risk)**: Expected shortfall at 95% confidence level
- **VaR (Value at Risk)**: Maximum expected loss at specified confidence level
- **Volatility**: Portfolio volatility and individual position contributions
- **Sharpe Ratio**: Risk-adjusted return metric
- **Sortino Ratio**: Downside risk-adjusted return
- **Tracking Error**: Active risk vs. benchmark (S&P 500)
- **Beta**: Portfolio beta vs. market


#### 7. **Scenario Analysis & Stress Testing**
- **Equity Drawdown Scenarios**: Test portfolio performance under market crashes (e.g., -20%, -30%)
- **Sector Rotation Scenarios**: Analyze impact of sector-specific shocks (e.g., tech sector -30%)
- **Custom Scenarios**: Define custom market scenarios with position-specific impacts
- **Monte Carlo Simulation**: Probabilistic scenario analysis with thousands of simulations


#### 8. **ESG & Sustainability Analysis**
- **ESG Scores**: Overall portfolio ESG score and component scores (Environmental, Social, Governance)
- **Holding-Level ESG**: ESG scores for individual positions
- **Sector ESG**: Average ESG scores by sector
- **Controversy Detection**: Portfolio controversy level and flagging of controversial holdings


#### 9. **Tax Analysis**
- **Tax Liability Estimation**: Estimated taxes if positions were sold
- **Tax-Adjusted Returns**: Returns after accounting for tax implications
- **Gain/Loss Breakdown**: Unrealized gains and losses by position
- **Holding Period Classification**: Short-term vs. long-term capital gains
- **Wash Sale Detection**: Identification of potential wash sale issues


#### 10. **Diversification Analysis**
- **Diversification Ratio**: Measure of diversification benefit
- **Effective Number of Holdings**: Equivalent number of equal-weighted positions
- **Risk Contribution Analysis**: Which positions drive portfolio risk
- **Diversification Recommendations**: Specific suggestions to improve diversification


#### 11. **Portfolio Export & Reporting**
- **PowerPoint Export**: 12-slide professional presentation with portfolio summary, holdings, exposure charts, performance attribution, risk metrics, and recommendations
- **PDF Export**: Multi-page PDF report with executive summary, holdings table, charts, and risk analysis
- **Excel Export**: Multi-tab workbook with holdings sheet, exposure breakdowns, performance attribution table, and risk metrics


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

The ML forecasting system is **deeply integrated with the RAG layer** to provide comprehensive, technically detailed forecasts. The system automatically handles spelling mistakes in company names and metrics, recognizes forecast-related queries through 40+ intent types, and supports natural language variations.

#### **1. Explicit Data Dump Section**
- **Purpose**: Ensures LLM receives ALL technical details in structured format
- **Content**: Model architecture (layers, units, activation functions), hyperparameters (learning rate, batch size, epochs, optimizer), training details (loss values, validation metrics, early stopping), computational details (training time, memory usage), model-specific parameters (ARIMA orders, Prophet seasonality, LSTM/GRU/Transformer architecture)
- **Format**: Key-value pairs for easy extraction and inclusion in responses
- **Mandate**: LLM is explicitly instructed to include EVERY value from this section without summarization
- **Spelling Handling**: Company names and metrics in forecasts are automatically corrected for spelling mistakes before model execution

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


### 📚 Documentation

- **Complete Prompt Guide**: See `docs/guides/ALL_ML_FORECASTING_PROMPTS.md` for all working forecast prompts
- **Quick Reference**: See `docs/guides/ML_FORECASTING_QUICK_REFERENCE.md` for quick reference guide
- **Technical Details**: See `src/finanlyzeos_chatbot/ml_forecasting/` for implementation details

## 🏗️ Architecture Map

See [`docs/architecture.md`](docs/architecture.md) for the complete component diagram. The latest revision includes the structured parsing pipeline (alias_builder.py, parse.py, time_grammar.py) and the retrieval layer that feeds grounded artefacts into the LLM alongside the existing CLI, FastAPI, analytics, and ingestion components.

## 🧠 Retrieval & ML Internals

FinalyzeOS combines **deterministic data prep** with **retrieval-augmented generation (RAG)** so every answer traces back to persisted facts. The RAG layer has been significantly enhanced to support portfolio management and machine learning forecasting with comprehensive technical details.

### 🔤 Natural-Language Parsing (Deterministic)

- **S&P 1500 Coverage**: `src/finanlyzeos_chatbot/parsing/alias_builder.py` loads a generated `aliases.json` covering all **1,599 S&P 1500 companies** (S&P 500 + S&P 400 + S&P 600). It normalises free-text mentions, resolves ticker aliases, applies 85+ manual overrides (common misspellings, share classes), and when needed performs fuzzy fallback with spelling mistake handling.
- **Advanced NLP**: `parse_to_structured` in `parsing/parse.py` orchestrates alias resolution, metric synonym detection (93 metrics with 200+ synonyms), and the flexible time grammar (`time_grammar.py`). It returns a strict JSON intent schema that downstream planners consume.
- **Spelling Mistake Handling**: 
  - **90% Company Name Correction**: Automatically corrects misspellings (e.g., "Appel" → "Apple", "Microsft" → "Microsoft", "Bookng Holdings" → "Booking Holdings") using fuzzy matching with progressive cutoffs (0.85, 0.80, 0.75, 0.70, 0.65) and manual overrides.
  - **100% Metric Correction**: Handles metric typos (e.g., "revenu" → "revenue", "earnngs" → "earnings", "operatng" → "operating") using multi-level fuzzy matching with adaptive thresholds.
- **Intent Recognition**: Recognizes **40+ intent types** including compare, trend, rank, explain, forecast, scenario, relationship, benchmark, when, why, what-if, recommendation, risk, valuation, and more.
- **Query Pattern Detection**: Supports **150+ question patterns** covering what, how, why, when, where, who, which, contractions, commands, and natural language variations with **100% detection rate**.
- **Portfolio Detection**: The parser automatically detects portfolio-related queries and extracts portfolio identifiers (e.g., `port_abc123`) from user queries.
- **ML Forecast Detection**: The parser detects forecast-related keywords (`forecast`, `predict`, `estimate`, `projection`, etc.) and routes queries to the ML forecasting system.

### 🔍 Retrieval Layer (RAG) - Production-Grade Implementation

FinalyzeOS implements a **production-grade RAG system** that goes far beyond vanilla RAG with advanced retrieval, reranking, and safety features.

#### **Core Retrieval Architecture**

- 📊 **SQL Deterministic Retrieval**: Structured intents route directly into AnalyticsEngine, reading metric snapshots, KPI overrides, and fact tables from SQLite/Postgres. **Spelling mistakes in company names and metrics are automatically corrected** before retrieval (90% company name success, 100% metric success).
- 🔐 **Semantic Search**: Vector embeddings for SEC filing narratives and uploaded documents using ChromaDB with `all-MiniLM-L6-v2` embeddings (384 dimensions)
- 🔐 Retrieved artefacts (tables, benchmark comparisons, audit trails) become RAG "system" messages that condition the LLM, ensuring no fabricated values slip through
- **Natural Language Processing**: The RAG layer leverages advanced NLP capabilities including **150+ question patterns**, **40+ intent types**, and **spelling mistake handling** to accurately interpret user queries before retrieval.
- **S&P 1500 Coverage**: Retrieves data for all **1,599 S&P 1500 companies** (S&P 500 + S&P 400 + S&P 600) with automatic company name and ticker resolution, including common misspellings.
- **Portfolio Context**: When portfolio queries are detected, the system retrieves portfolio holdings, exposure data, risk metrics, and attribution results from the portfolio database
- **ML Forecast Context**: When forecast queries are detected (via intent detection), the system retrieves historical time series data, runs ML forecasting models (**8 models available**), and builds comprehensive technical context including model architecture, hyperparameters, training details, and forecast results
- **Multi-Source Aggregation**: The RAG layer aggregates data from multiple sources (SEC EDGAR, Yahoo Finance, FRED, IMF) to provide comprehensive context for financial queries

#### **Advanced RAG Features** ⭐ Production-Grade

**1. Cross-Encoder Reranking** (⭐ MOST IMPORTANT)
- **Second-pass relevance scoring** using `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **~10-20% relevance improvement** over bi-encoder similarity alone
- **Far fewer hallucinations** through better document ranking
- Shows understanding of retrieval quality bottlenecks and Transformer cross-attention (Lecture 2 concept)
- **Performance**: Adds ~50-100ms per query (cross-encoder inference)

**2. Source Fusion (Score Normalization & Confidence Fusion)**
- **Normalizes similarity scores** across sources (SEC narratives, uploaded docs, SQL metrics)
- **Applies reliability weights**: SQL (1.0), SEC (0.9), Uploaded (0.7), Macro (0.6), Forecasts (0.5)
- **Computes overall retrieval confidence** (0-1) for answer quality assessment
- **Merges sources** into single ranked list with fused scores
- Shows research-level retrieval engineering

**3. Grounded Decision Layer**
- **Safety checks before answering**: Detects low confidence, source contradictions, missing information
- **Prevents hallucinations**: Returns "I don't have enough information" when confidence < 0.25
- **Source contradiction detection**: Flags when SQL contradicts narrative sources
- **Missing information detection**: Warns when tickers parsed but no data found
- Aligns with Lecture 2's emphasis on grounded, observable systems

**4. Retrieval Confidence Scoring**
- **Computes weighted average** of top-K similarity scores
- **Adjusts LLM tone** based on confidence level (high/medium/low)
- **High confidence (≥0.7)**: "Provide a confident, detailed answer"
- **Medium confidence (0.4-0.7)**: "Provide a helpful answer but acknowledge uncertainties"
- **Low confidence (<0.4)**: "Be cautious and explicit about information gaps"
- Aligns answer tone with retrieval uncertainty - exactly what financial institutions need

**5. Memory-Augmented RAG**
- **Per-conversation document tracking**: Isolates documents by conversation_id
- **Per-user document tracking**: Tracks documents across all user conversations
- **Document lifetime tracking**: Marks stale documents (default 90 days)
- **Topic clustering**: Clusters documents by topic (financial_metrics, risk_analysis, forecasting, governance, operations)
- **Automatic registration**: Documents automatically registered in memory on upload
- Unique feature that treats uploaded docs as ephemeral memory

**6. Multi-Hop Retrieval (Agentic Behavior)**
- **Query decomposition**: Breaks complex questions into sub-queries
- **Sequential retrieval**: Performs multiple retrieval steps (metrics → narratives → macro → portfolio)
- **Complexity detection**: Automatically detects simple/moderate/complex queries
- **Example**: "Why did Apple's revenue decline, and how does this compare to the tech sector?"
  - Step 1: Retrieve Apple's revenue metrics
  - Step 2: Retrieve SEC narratives explaining decline
  - Step 3: Retrieve macro/economic context
  - Step 4: Retrieve sector benchmarks
- Shows agentic behavior beyond simple RAG

**7. Evaluation Harness**
- **Retrieval metrics**: Recall@K, MRR (Mean Reciprocal Rank), nDCG (Normalized Discounted Cumulative Gain)
- **QA metrics**: Exact match, factual consistency, source citation accuracy
- **Evaluation script**: `scripts/evaluate_rag.py` for quantitative assessment
- **Test dataset**: JSON format with queries, expected documents, ground truth answers
- Research-grade evaluation system

**8. Observability & Guardrails**
- **Comprehensive logging**: Retrieval counts, scores, timing, document IDs, anomalies
- **Context window control**: Smart truncation (drops low-scoring documents first)
- **Anomaly detection**: Warns if all scores below threshold, warns if empty retrieval
- **Guardrails**: Min relevance score (0.3), max context chars (15000), max documents (10)
- **Audit trail**: Full traceability of which documents were retrieved and why

**9. Complete RAG Orchestrator**
- **Single entry point**: `RAGOrchestrator` orchestrates all features in one pipeline
- **Automatic feature selection**: Enables/disables features based on query complexity
- **Unified interface**: `process_query()` returns prompt, result, and metadata
- **Production-ready**: All features integrated and tested

#### **RAG Components**

- **`RAGRetriever`**: Unified retrieval interface combining SQL + vector search + uploaded docs
- **`Reranker`**: Cross-encoder reranking for better relevance
- **`SourceFusion`**: Score normalization and confidence fusion
- **`GroundedDecisionLayer`**: Safety checks before answering
- **`MemoryAugmentedRAG`**: Per-conversation/user document tracking
- **`RAGController`**: Multi-hop query decomposition
- **`RAGObserver`**: Observability and guardrails
- **`RAGOrchestrator`**: Complete pipeline orchestrator

#### **Documentation**

- **Complete Guide**: See `docs/RAG_COMPLETE_GUIDE.md` for comprehensive RAG documentation
- **Architecture**: Detailed explanation of all components and features
- **Usage Examples**: Code examples for all advanced features
- **Testing**: Test scripts for verifying functionality

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

### 📦 Complete Package List

> **Note**: For installation steps, see the [Complete Setup Guide](#️-complete-setup-guide) above. This section lists all packages for reference.

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

> **📖 For installation verification and troubleshooting, see the [Complete Setup Guide](#️-complete-setup-guide) above.**

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

> **📖 For first-time setup with options for 100, 250, 500, or 1500 companies, see the [Complete Setup Guide - Step 2](#-step-2-choose-your-data-ingestion-option) above.**

FinalyzeOS provides **multiple ingestion strategies** to fit different use cases. This section explains advanced ingestion techniques and gap-filling strategies for existing databases.

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

> **📖 For complete data ingestion instructions with options for 100, 250, 500, or 1500 companies, see the [Complete Setup Guide - Step 2](#-step-2-choose-your-data-ingestion-option) above.**

## 📊 Advanced Ingestion Techniques

> **📖 For basic setup and ingestion options (100, 250, 500, or 1500 companies), see the [Complete Setup Guide](#️-complete-setup-guide) above.**

This section covers advanced ingestion techniques for users who have already completed the basic setup.

### Advanced Ingestion Options

**Module vs Script Path Forms:**
```bash
# Module form (requires pip install -e .)
python -m scripts.ingestion.ingest_universe --universe sp500 --years 10 --chunk-size 25 --sleep 2

# Script path form (works without installation)
python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2
```

**Key Options:**
- `--years 10` - Pulls the most recent 10 fiscal years
- `--chunk-size 25` - Processes 25 companies per batch
- `--sleep 2` - Delay between batches (respects SEC rate limits)
- `--resume` - Resume from last checkpoint (uses `.ingestion_progress.json`)

**Verify Ingestion:**
```bash
python scripts/utility/check_ingestion_status.py
# Or use the simple checker
python scripts/utility/check_correct_database.py
```

**Common Issues:**
- "Nothing to do" with `--resume`: Delete `.ingestion_progress.json` and re-run
- Yahoo 429 errors: Reduce batch size and add delays between requests
- DB path: Override with `DATABASE_PATH` environment variable
- ModuleNotFoundError: Ensure you ran `pip install -e .` or set `PYTHONPATH=./src`

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
├── pyproject.toml                     # Project metadata, dependencies, pytest config
├── requirements.txt                   # Python dependencies lockfile
├── finanlyzeos_chatbot.sqlite3        # Main SQLite database (created on demand)
├── benchmarkos_chatbot.sqlite3        # Benchmark SQLite database
├── test.db                            # Test database
│
├── app/                               # Application entry points
│   ├── run_chatbot.py                 # CLI chatbot entry point (REPL)
│   ├── run_server.py                  # Web server entry point (FastAPI)
│   ├── serve_chatbot.py               # Alternative web server entry point
│   └── start_server.sh                # Server startup script (Unix/Linux)
│
├── scripts/                           # Scripts and utilities
│   ├── check_packages.py              # Package verification utility
│   ├── evaluate_rag.py                # RAG evaluation script
│   ├── index_documents_for_rag.py     # Document indexing for RAG
│   ├── quick_rag_test.py              # Quick RAG testing
│   ├── test_complete_rag.py           # Complete RAG testing
│   ├── test_rag_advanced.py           # Advanced RAG testing
│   ├── test_rag_integration.py        # RAG integration testing
│   ├── test_rag_working.py            # RAG working tests
│   ├── run_data_ingestion.ps1         # Windows PowerShell ingestion script
│   ├── run_data_ingestion.sh          # Unix/Linux ingestion script
│   │
│   ├── analysis/                      # Analysis scripts
│   │   └── analyze_coverage_gaps.py   # Analyze coverage gaps (complete/partial/missing)
│   │
│   ├── demos/                         # Demo scripts
│   │   └── (demo scripts for presentations)
│   │
│   ├── ingestion/                     # Data ingestion scripts
│   │   ├── fill_data_gaps.py          # ⭐ Recommended: Smart gap-filling script
│   │   ├── full_coverage_ingestion.py # ⭐ Full coverage ingestion (20+ years)
│   │   ├── ingest_20years_sp500.py    # Full 20-year historical ingestion
│   │   ├── ingest_sp500_15years.py    # S&P 500 15-year ingestion
│   │   ├── ingest_more_years.py       # Extend historical years for existing tickers
│   │   ├── ingest_extended_universe.py # Extended universe ingestion
│   │   ├── batch_ingest.py            # Batch ingestion with retry/backoff
│   │   ├── ingest_companyfacts.py     # SEC CompanyFacts API ingestion
│   │   ├── ingest_companyfacts_batch.py # Batch CompanyFacts ingestion
│   │   ├── ingest_frames.py           # SEC data frames ingestion
│   │   ├── ingest_from_file.py        # Ingestion from file input
│   │   ├── ingest_universe.py         # Universe-based ingestion with resume support
│   │   ├── load_prices_stooq.py       # Stooq price loader (fallback)
│   │   ├── load_prices_yfinance.py    # Yahoo Finance price loader
│   │   ├── load_historical_prices_15years.py # Historical price loader (15 years)
│   │   ├── load_ticker_cik.py         # Ticker to CIK mapping loader
│   │   ├── refresh_quotes.py          # Refresh market quotes
│   │   ├── backfill_metrics.py        # Backfill missing metrics
│   │   ├── fetch_imf_sector_kpis.py   # Fetch IMF sector KPI benchmarks
│   │   ├── parse_raw_sec_filings.py   # Parse raw SEC filing data
│   │   └── monitor_ingestion.py       # Monitor ingestion progress
│   │
│   ├── sp1500/                        # S&P 1500 setup and verification scripts
│   │   ├── complete_sp1500.py         # Build complete S&P 1500 list from Wikipedia
│   │   ├── create_sp1500_file.py      # Create S&P 1500 ticker file
│   │   ├── extract_tickers_from_db.py # Extract tickers from database
│   │   ├── find_and_test_sp1500.py    # Find and test S&P 1500 file
│   │   ├── setup_and_test_sp1500.py   # Setup and test S&P 1500
│   │   ├── setup_sp1500.py            # Setup S&P 1500 universe
│   │   ├── verify_sp1500_file.py      # Verify S&P 1500 file exists
│   │   └── verify_sp1500_setup.py     # Quick verification script
│   │
│   └── utility/                       # Utility and helper scripts
│       ├── check_database_simple.py   # Database verification utility
│       ├── check_correct_database.py  # Verify correct database path
│       ├── check_data_coverage.py     # Check data coverage statistics
│       ├── check_dashboard_data.py    # Verify dashboard data integrity
│       ├── check_ingestion_status.py  # Ingestion status checker
│       ├── check_kpi_values.py        # KPI validation utility
│       ├── check_test_progress.py     # Test progress tracker
│       ├── check_braces.py            # Syntax checking utility
│       ├── check_syntax.py            # Code syntax validation
│       ├── find_unclosed_brace.py     # Brace matching utility
│       ├── combine_portfolio_files.py # Portfolio file combiner
│       ├── chat_terminal.py           # Terminal chat interface
│       ├── monitor_progress.py        # Progress monitoring utility
│       ├── quick_status.py            # Quick status check
│       ├── show_complete_attribution.py # Attribution display utility
│       ├── show_detailed_results.py   # Show detailed test results
│       ├── show_test_results.py       # Display test results
│       ├── plotly_demo.py             # Plotly chart examples
│       ├── chat_metrics.py            # Chat metrics utility
│       ├── data_sources_backup.py     # Data sources backup utility
│       ├── refresh_ticker_catalog.py  # Ticker catalog refresh utility
│       ├── improve_kpi_coverage.py    # Improve KPI coverage analysis
│       ├── fix_remaining_kpis.py      # Fix remaining KPI issues
│       ├── kpi_registry_cli.py        # KPI registry CLI tool
│       ├── generate_company_universe.py # Generate company universe JSON for UI
│       ├── generate_sp1500_names.py   # Generate S&P 1500 company names from SEC
│       ├── generate_help_center_verification_tracker.py # Help center tracker generator
│       ├── print_failed_prompts.py    # Print failed test prompts
│       ├── smoke_chat_api.py          # Smoke test for chat API
│       ├── verify_chatbot_connection.py # Verify chatbot connection
│       └── main.py                    # Main utility CLI wrapper
│
├── src/
│   ├── __init__.py                    # Source package initialization
│   ├── data/
│   │   └── kpi_library.json           # KPI library definitions
│   │
│   ├── benchmarkos_chatbot/           # Benchmark chatbot module
│   │   └── (benchmark chatbot files)
│   │
│   └── finanlyzeos_chatbot/           # Main chatbot source code
│       ├── __init__.py                # Package initialization
│       │
│       ├── Core Components:
│       ├── chatbot.py                 # Main chatbot orchestration (RAG, LLM integration)
│       ├── config.py                  # Configuration management (settings loader)
│       ├── database.py                # Database abstraction layer (SQLite/Postgres)
│       ├── llm_client.py              # LLM provider abstraction (OpenAI/local echo)
│       ├── web.py                     # FastAPI web server (REST API endpoints)
│       │
│       ├── Analytics & Data:
│       ├── analytics_engine.py        # Core analytics engine (KPI calculations)
│       ├── analytics_workspace.py     # Analytics workspace management
│       ├── advanced_kpis.py           # Advanced KPI calculator (30+ ratios)
│       ├── anomaly_detection.py       # Anomaly detection (Z-score analysis)
│       ├── predictive_analytics.py    # Predictive analytics (regression, CAGR)
│       ├── sector_analytics.py        # Sector benchmarking (GICS sectors)
│       │
│       ├── Data Sources & Ingestion:
│       ├── data_ingestion.py          # Data ingestion pipeline (SEC, Yahoo, Bloomberg)
│       ├── data_sources.py            # Data source integrations (SEC EDGAR, Yahoo Finance)
│       ├── data_sources_private.py    # Private data source configurations
│       ├── data_validator.py          # Data validation utilities
│       ├── external_data.py           # External data providers (FRED, IMF)
│       ├── macro_data.py              # Macroeconomic data provider
│       ├── multi_source_aggregator.py # Multi-source data aggregation
│       ├── sec_bulk.py                # SEC bulk data access
│       ├── sec_filing_parser.py       # SEC filing parser
│       ├── secdb.py                   # SEC database utilities
│       │
│       ├── Context & RAG System:
│       ├── context_builder.py         # Financial context builder for RAG
│       ├── context_validator.py       # Context validation utilities
│       ├── document_context.py        # Document context management
│       ├── document_processor.py      # Document processing utilities
│       ├── followup_context.py        # Follow-up question context management
│       ├── intent_carryover.py        # Intent carryover between conversations
│       ├── rag_claim_verifier.py      # RAG claim verification
│       ├── rag_controller.py          # RAG controller
│       ├── rag_evaluation.py          # RAG evaluation utilities
│       ├── rag_feedback.py            # RAG feedback system
│       ├── rag_fusion.py              # RAG fusion techniques
│       ├── rag_grounded_decision.py   # RAG grounded decision making
│       ├── rag_hybrid_retriever.py    # Hybrid retrieval system
│       ├── rag_intent_policies.py     # RAG intent policies
│       ├── rag_knowledge_graph.py     # Knowledge graph integration
│       ├── rag_memory.py              # RAG memory management
│       ├── rag_observability.py       # RAG observability
│       ├── rag_orchestrator.py        # RAG orchestration
│       ├── rag_prompt_template.py     # RAG prompt templates
│       ├── rag_reranker.py            # RAG reranking
│       ├── rag_retriever.py           # RAG retrieval system
│       ├── rag_sparse_retriever.py    # Sparse retrieval system
│       ├── rag_structure_aware.py     # Structure-aware RAG
│       ├── rag_temporal.py            # Temporal RAG
│       │
│       ├── Quality & Verification:
│       ├── confidence_scorer.py       # Confidence scoring for responses
│       ├── response_corrector.py      # Response correction utilities
│       ├── response_verifier.py       # Response verification system
│       ├── source_tracer.py           # Source tracing utilities
│       ├── source_verifier.py         # Source verification system
│       ├── hallucination_detector.py  # Hallucination detection
│       ├── ml_response_verifier.py    # ML forecast response verification
│       │
│       ├── Formatting & Templates:
│       ├── finance_forecast_formatter.py # Finance forecast formatting
│       ├── rewrite_formatter.py       # Response rewrite formatting
│       ├── template_processor.py      # Template processing utilities
│       ├── universal_ml_formatter.py  # Universal ML forecast formatter
│       ├── framework_processor.py     # Framework processing utilities
│       ├── table_renderer.py          # ASCII table rendering
│       │
│       ├── Parsing & NLP:
│       ├── parsing/
│       │   ├── __init__.py            # Parsing package initialization
│       │   ├── alias_builder.py       # Ticker alias resolution (S&P 1500, 90% spelling correction)
│       │   ├── aliases.json           # Generated ticker aliases (S&P 1500 coverage)
│       │   ├── ontology.py            # Metric ontology (93 KPIs, 200+ synonyms)
│       │   ├── parse.py               # Natural language parser (40+ intents, 150+ patterns)
│       │   ├── time_grammar.py        # Time period parser (FY, quarters, ranges)
│       │   ├── abbreviations.py       # Abbreviation expansion
│       │   ├── company_groups.py      # Company group detection
│       │   ├── comparative.py         # Comparative language parsing
│       │   ├── conditionals.py        # Conditional statement parsing
│       │   ├── fuzzy_quantities.py    # Fuzzy quantity parsing
│       │   ├── metric_inference.py    # Metric inference from context
│       │   ├── multi_intent.py        # Multi-intent detection
│       │   ├── natural_filters.py     # Natural language filters
│       │   ├── negation.py            # Negation handling
│       │   ├── question_chaining.py   # Question chaining detection
│       │   ├── sentiment.py           # Sentiment analysis
│       │   ├── temporal_relationships.py # Temporal relationship parsing
│       │   └── trends.py              # Trend detection
│       │
│       ├── Spelling & Correction:
│       ├── spelling/
│       │   ├── __init__.py            # Spelling package initialization
│       │   ├── company_corrector.py   # Company name spelling correction
│       │   ├── correction_engine.py   # Main correction engine
│       │   ├── fuzzy_matcher.py       # Fuzzy matching utilities
│       │   └── metric_corrector.py    # Metric spelling correction
│       │
│       ├── Routing:
│       ├── routing/
│       │   ├── __init__.py            # Routing package initialization
│       │   └── enhanced_router.py     # Enhanced intent routing (dashboard detection)
│       │
│       ├── Portfolio Management:
│       ├── portfolio.py               # Main portfolio management module (combined)
│       ├── portfolio_attribution.py   # Performance attribution (Brinson-Fachler)
│       ├── portfolio_calculations.py  # Portfolio calculation utilities
│       ├── portfolio_enhancements.py  # Portfolio enhancement utilities
│       ├── portfolio_enrichment.py    # Portfolio enrichment with fundamentals
│       ├── portfolio_export.py        # Portfolio export (PowerPoint, PDF, Excel)
│       ├── portfolio_exposure.py      # Exposure analysis (sector, factor)
│       ├── portfolio_optimizer.py     # Portfolio optimization (mean-variance)
│       ├── portfolio_ppt_builder.py   # Portfolio PowerPoint builder
│       ├── portfolio_reporting.py     # Portfolio reporting utilities
│       ├── portfolio_risk_metrics.py  # Risk metrics (CVaR, VaR, Sharpe, Sortino)
│       ├── portfolio_scenarios.py     # Scenario analysis & stress testing
│       └── portfolio_trades.py        # Trade recommendation utilities
│       │
│       ├── ML Forecasting:
│       ├── ml_forecasting/
│       │   ├── __init__.py            # ML forecasting package initialization
│       │   ├── ml_forecaster.py       # Main ML forecaster (model selection)
│       │   ├── arima_forecaster.py    # ARIMA model (statistical time series)
│       │   ├── prophet_forecaster.py  # Prophet model (seasonal patterns)
│       │   ├── ets_forecaster.py      # ETS model (exponential smoothing)
│       │   ├── lstm_forecaster.py     # LSTM model (deep learning RNN)
│       │   ├── transformer_forecaster.py # Transformer model (attention-based)
│       │   ├── multivariate_forecaster.py # Multivariate forecasting
│       │   ├── preprocessing.py       # Data preprocessing (scaling, normalization)
│       │   ├── feature_engineering.py # Feature engineering utilities
│       │   ├── hyperparameter_tuning.py # Hyperparameter optimization (Optuna)
│       │   ├── backtesting.py         # Model backtesting utilities
│       │   ├── validation.py          # Model validation utilities
│       │   ├── explainability.py      # Model explainability (SHAP, attention)
│       │   ├── uncertainty.py         # Uncertainty quantification
│       │   ├── regime_detection.py    # Regime detection (market states)
│       │   ├── technical_indicators.py # Technical indicators for features
│       │   ├── external_factors.py    # External factor integration
│       │   └── user_plugins.py        # User plugin system
│       │
│       ├── Export & Presentation:
│       ├── export_pipeline.py         # Export pipeline (PDF, PPTX, Excel)
│       ├── cfi_ppt_builder.py         # CFI-style PowerPoint builder (12 slides)
│       │
│       ├── Utilities:
│       ├── tasks.py                   # Task queue management
│       ├── help_content.py            # Help content and documentation
│       ├── dashboard_utils.py         # Dashboard utility functions
│       ├── imf_proxy.py               # IMF data proxy
│       ├── kpi_backfill.py            # KPI backfill utilities
│       ├── kpi_lookup.py              # KPI lookup utilities
│       ├── custom_kpis.py             # Custom KPI definitions
│       ├── backfill_policy.py         # Backfill policy management
│       ├── ticker_universe.py         # Ticker universe management
│       ├── interactive_modeling.py    # Interactive modeling utilities
│       │
│       └── Static Assets:
│       └── static/
│           ├── app.js                 # Frontend application logic (SPA)
│           ├── styles.css             # UI styling (markdown, progress indicator)
│           ├── index.html             # Web UI entry point
│           ├── favicon.svg            # Favicon
│           ├── cfi_dashboard.css      # CFI dashboard styling
│           ├── cfi_dashboard.js       # CFI dashboard JavaScript
│           ├── portfolio_dashboard.js # Portfolio dashboard JavaScript
│           └── data/
│               ├── company_universe.json # Company universe metadata
│               └── kpi_library.json   # KPI library definitions
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
│   │   ├── EXPANDED_QUERY_CAPABILITIES.md # Expanded query capabilities guide
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
│   │   ├── ticker_names.md           # Ticker coverage list (1,599 S&P 1500 companies)
│   │   └── (additional guides)
│   │
│   ├── ingestion/                      # Ingestion documentation
│   │   ├── FULL_COVERAGE_GUIDE.md     # Full coverage ingestion guide
│   │   └── FULL_INGESTION_SCRIPTS.md  # Full ingestion scripts guide
│   │
│   ├── database/                       # Database documentation
│   │   ├── DATABASE_STRUCTURE_POSTER.md # Database structure poster
│   │   ├── EXPECTED_DATA_VOLUMES.md   # Expected data volumes
│   │   └── full_coverage_summary.json # Full coverage summary data
│   │
│   ├── accuracy/                       # Accuracy testing documentation
│   │   ├── README_ACCURACY_TESTING.md # Accuracy testing guide
│   │   ├── 100_PERCENT_ACCURACY_ACHIEVED.md # 100% accuracy achievement
│   │   ├── ACCURACY_100_PERCENT_PROOF.md # Accuracy proof documentation
│   │   ├── ACCURACY_EXECUTIVE_SUMMARY.md # Executive summary
│   │   ├── ACCURACY_FINAL_PROOF.md    # Final accuracy proof
│   │   ├── ACCURACY_IMPROVEMENT_PLAN.md # Improvement plan
│   │   ├── ACCURACY_METRICS_DETAILED.md # Detailed metrics
│   │   ├── ACCURACY_SLIDE_SUMMARY.md  # Slide summary
│   │   ├── ACCURACY_STATS_FOR_SLIDES.md # Stats for slides
│   │   ├── ACCURACY_VERIFICATION_SLIDES.md # Verification slides
│   │   ├── help_center_confidence_workflow.md # Help center workflow
│   │   └── help_center_verification_tracker.csv # Verification tracker
│   │
│   ├── executive/                      # Executive documentation
│   │   ├── BENCHMARKOS_SLIDE.md       # BenchmarkOS slide
│   │   ├── COMPREHENSIVE_ACCURACY_FIX_SUMMARY.md # Accuracy fix summary
│   │   ├── CRITICAL_ACCURACY_FIX.md   # Critical accuracy fix
│   │   ├── FINAL_SP500_ALL_KPIS_REPORT.md # Final S&P 500 KPI report
│   │   ├── FIX_CHATBOT_ACCURACY_ISSUE.md # Chatbot accuracy fix
│   │   └── HOW_TO_MAKE_ALL_ANSWERS_TRUSTED.md # Trusted answers guide
│   │
│   ├── plans/                          # Planning documentation
│   │   └── ML_PROMPT_TESTING_PLAN.md  # ML prompt testing plan
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
│   │   ├── PATTERN_EXPANSION_SUMMARY.md # Pattern expansion summary
│   │   └── (28 summary files documenting various features and improvements)
│   │
│   ├── analysis/                       # Analysis documentation
│   │   ├── README.md                   # Analysis documentation index
│   │   └── (25+ analysis reports and documentation files)
│   │
│   ├── sp1500/                         # S&P 1500 documentation
│   │   ├── SP1500_SETUP_COMPLETE.md   # S&P 1500 setup completion
│   │   ├── SP1500_TESTING_INSTRUCTIONS.md # S&P 1500 testing guide
│   │   ├── SP1500_SUPPORT_ANALYSIS.md # S&P 1500 support analysis
│   │   ├── SP1500_SUPPORT_STATUS.md   # S&P 1500 support status
│   │   ├── SP1500_FIXES_COMPLETE.md   # S&P 1500 fixes completion
│   │   └── ADD_SP1500_SUPPORT.md      # Adding S&P 1500 support guide
│   │
│   ├── improvements/                   # Improvement documentation
│   │   ├── COMPREHENSIVE_COVERAGE_REPORT.md # Coverage report
│   │   ├── COMPREHENSIVE_IMPROVEMENTS_COMPLETE.md # Improvements completion
│   │   ├── FINAL_IMPROVEMENTS_SUMMARY.md # Final improvements summary
│   │   ├── IMPROVEMENTS_TO_100_PERCENT.md # Improvements to 100% accuracy
│   │   └── (additional improvement docs)
│   │
│   └── reports/                        # Generated reports
│       └── (various analysis and improvement reports)
│
├── data/                              # Data files and databases
│   ├── sample_financials.csv          # Sample financial data
│   ├── test_chatbot.db                # Test database
│   │
│   ├── cache/                         # Cached data
│   │   └── edgar_tickers.json         # Cached EDGAR ticker data
│   │
│   ├── chroma_db/                     # ChromaDB vector database
│   │   └── chroma.sqlite3             # ChromaDB SQLite file
│   │
│   ├── evaluation/                    # Evaluation datasets
│   │   └── rag_test_set.json          # RAG evaluation test set
│   │
│   ├── external/                      # External data sources
│   │   └── imf_sector_kpis.json       # IMF sector KPI benchmarks
│   │
│   ├── portfolios/                    # Portfolio data files
│   │   ├── mizuho_fi_capital_portfolio.csv # Sample portfolio (Mizuho)
│   │   └── README.md                  # Portfolio data documentation
│   │
│   ├── sqlite/                        # SQLite databases
│   │   ├── finanlyzeos_chatbot.sqlite3 # Main SQLite database
│   │   ├── finanlyzeos_chatbot.sqlite3-shm # SQLite shared memory
│   │   ├── finanlyzeos_chatbot.sqlite3-wal # SQLite write-ahead log
│   │   ├── benchmarkos_chatbot.sqlite3 # Benchmark database
│   │   ├── benchmarkos_chatbot.sqlite3-shm # Benchmark shared memory
│   │   └── benchmarkos_chatbot.sqlite3-wal # Benchmark write-ahead log
│   │
│   └── tickers/                       # Ticker universe files
│       ├── universe_sp500.txt         # S&P 500 ticker list (475 companies)
│       ├── universe_sp1500.txt        # S&P 1500 ticker list (1,599 companies)
│       ├── sec_top100.txt             # Top 100 SEC companies
│       ├── universe_custom.txt        # Custom universe list
│       └── sample_watchlist.txt       # Sample watchlist
│
├── cache/                              # Generated at runtime (gitignored)
│   ├── edgar_tickers.json             # Cached EDGAR ticker data
│   └── progress/
│       └── fill_gaps_summary.json     # Ingestion progress tracking
│
├── research/                           # Research and analysis code
│   └── analysis/                      # Analysis scripts (28 Python files)
│       ├── analyze_accuracy_improvements.py # Accuracy improvement analysis
│       ├── analyze_chatbot_performance.py # Chatbot performance analysis
│       ├── analyze_coverage_gaps.py   # Coverage gap analysis
│       ├── analyze_data_quality.py    # Data quality analysis
│       ├── analyze_kpi_coverage.py    # KPI coverage analysis
│       ├── analyze_metric_coverage.py # Metric coverage analysis
│       ├── analyze_portfolio_performance.py # Portfolio performance analysis
│       ├── analyze_query_patterns.py  # Query pattern analysis
│       ├── analyze_response_quality.py # Response quality analysis
│       ├── analyze_source_coverage.py # Source coverage analysis
│       ├── benchmark_chatbot.py       # Chatbot benchmarking
│       ├── compare_models.py          # Model comparison analysis
│       ├── evaluate_accuracy.py       # Accuracy evaluation
│       ├── evaluate_completeness.py   # Completeness evaluation
│       ├── evaluate_performance.py    # Performance evaluation
│       ├── generate_accuracy_report.py # Accuracy report generation
│       ├── generate_coverage_report.py # Coverage report generation
│       ├── generate_performance_report.py # Performance report generation
│       ├── measure_latency.py         # Latency measurement
│       ├── profile_memory_usage.py    # Memory usage profiling
│       ├── test_data_integrity.py     # Data integrity testing
│       ├── test_model_accuracy.py     # Model accuracy testing
│       ├── test_query_performance.py  # Query performance testing
│       ├── validate_data_sources.py   # Data source validation
│       ├── validate_kpi_calculations.py # KPI calculation validation
│       ├── validate_metrics.py        # Metrics validation
│       ├── validate_portfolio_calculations.py # Portfolio calculation validation
│       └── validate_responses.py      # Response validation
│
├── temp/                               # Temporary files (gitignored)
│   ├── apple-companyfacts.json        # Temporary SEC data
│   ├── apple-q4-2024-results.html     # Temporary HTML
│   ├── extract_pdf.py                 # PDF extraction utility
│   ├── FY24_Q4_Consolidated_Financial_Statements.pdf # Sample PDF
│   ├── msft-2024-10k.htm              # Sample SEC filing
│   └── msft-companyfacts.json         # Sample company facts
│
├── archive/                            # Archived files
│   └── arxiv_2509_26632.txt           # Archived research paper
│
├── webui/                              # Web UI files
│   ├── index.html                      # Web UI entry point
│   ├── app.js                          # Frontend application logic
│   ├── styles.css                      # UI styling (7432 lines)
│   ├── package.json                    # Node.js dependencies
│   ├── service-worker.js               # Service worker for PWA
│   ├── start_dashboard.js              # Dashboard startup script
│   ├── favicon.svg                     # Favicon
│   │
│   ├── CFI Dashboards:                 # CFI (Corporate Finance Institute) style dashboards
│   ├── cfi_dashboard.html              # Main CFI dashboard HTML
│   ├── cfi_dashboard.js                # CFI dashboard JavaScript
│   ├── cfi_dashboard.css               # CFI dashboard styling
│   ├── cfi_dashboard_v2.html           # CFI dashboard version 2
│   ├── cfi_dashboard_improved.html     # Improved CFI dashboard
│   ├── cfi_dashboard_backup_original.html # Original backup
│   ├── cfi_dashboard_old_backup.html   # Old backup
│   │
│   ├── CFI Compare Views:              # CFI comparison interfaces
│   ├── cfi_compare.html                # CFI compare view HTML
│   ├── cfi_compare.js                  # CFI compare view JavaScript
│   ├── cfi_compare.css                 # CFI compare view styling
│   ├── cfi_compare_demo.html           # CFI compare demo
│   ├── cfi_compare_standalone.html     # CFI compare standalone
│   │
│   ├── CFI Dense Views:                # CFI dense layout interfaces
│   ├── cfi_dense.html                  # CFI dense view HTML
│   ├── cfi_dense.js                    # CFI dense view JavaScript
│   ├── cfi_dense.css                   # CFI dense view styling
│   │
│   ├── data/                           # Web UI data files
│   │   ├── company_universe.json       # Company universe for dropdowns
│   │   └── kpi_definitions.json        # KPI definitions for UI
│   │
│   └── static/                         # Static assets
│       └── portfolio_data.json         # Portfolio data for demos
│
└── tests/                              # Comprehensive test suite (145 files)
    ├── README.md                       # Testing documentation
    ├── conftest.py                     # Pytest configuration and fixtures
    │
    ├── unit/                           # Unit tests (25+ files)
    │   ├── test_analytics.py           # Analytics unit tests
    │   ├── test_analytics_engine.py    # Analytics engine unit tests
    │   ├── test_analysis_templates.py  # Analysis template unit tests
    │   ├── test_cli_tables.py          # CLI table rendering tests
    │   ├── test_custom_kpis_workspace.py # Custom KPIs workspace tests
    │   ├── test_database.py            # Database unit tests
    │   ├── test_data_dictionary.py     # Data dictionary tests
    │   ├── test_data_ingestion.py      # Data ingestion unit tests
    │   ├── test_document_upload.py     # Document upload tests
    │   ├── test_router_kpi_intents.py  # Router KPI intent tests
    │   ├── test_uploaded_document_context.py # Uploaded document context tests
    │   ├── test_parsing.py             # Parsing unit tests
    │   ├── test_portfolio.py           # Portfolio unit tests
    │   ├── test_ml_forecasting.py      # ML forecasting unit tests
    │   ├── test_rag_components.py      # RAG components unit tests
    │   ├── test_verification.py        # Verification unit tests
    │   ├── test_export.py              # Export functionality unit tests
    │   ├── test_utilities.py           # Utilities unit tests
    │   └── (additional unit tests)
    │
    ├── integration/                    # Integration tests (15+ files)
    │   ├── test_chatbot_sec_fix.py     # SEC integration tests
    │   ├── test_sec_api_fix.py         # SEC API integration tests
    │   ├── test_new_analytics.py       # New analytics integration tests
    │   ├── test_dashboard_flow.py      # Dashboard workflow integration tests
    │   ├── test_fixes.py               # General fixes integration tests
    │   ├── test_enhanced_routing.py    # Enhanced routing integration tests
    │   ├── test_data_pipeline.py       # Data pipeline integration tests
    │   ├── test_ml_pipeline.py         # ML pipeline integration tests
    │   ├── test_portfolio_integration.py # Portfolio integration tests
    │   ├── test_rag_integration.py     # RAG integration tests
    │   └── (additional integration tests)
    │
    ├── e2e/                            # End-to-end tests (20+ files)
    │   ├── test_all_sp500_dashboards.py # Full S&P 500 dashboard test
    │   ├── test_sample_companies.py    # Sample companies test (10 companies)
    │   ├── test_single_company.py      # Single company test (Apple)
    │   ├── test_chatbot_stress_test.py # FinalyzeOS stress test
    │   ├── test_chatgpt_style.py       # ChatGPT-style test
    │   ├── test_comprehensive_sources.py # Comprehensive sources test
    │   ├── test_ml_detailed_answers.py # ML detailed answers test
    │   ├── test_portfolio_workflows.py # Portfolio workflow tests
    │   ├── test_export_workflows.py    # Export workflow tests
    │   ├── test_user_journeys.py       # User journey tests
    │   ├── PORTFOLIO_STRESS_TEST_SUMMARY.md # Portfolio stress test summary
    │   └── (additional e2e tests)
    │
    ├── metric_recognition/             # Metric recognition tests (15+ files)
    │   ├── test_metric_variations.py   # Metric variation tests
    │   ├── test_metric_edge_cases.py   # Metric edge case tests
    │   ├── test_metric_patterns.py     # Metric pattern tests
    │   ├── test_metric_recognition.py  # Metric recognition tests
    │   ├── test_comprehensive_coverage.py # Comprehensive metric coverage
    │   ├── test_comprehensive_spelling.py # Comprehensive spelling tests
    │   ├── test_metric_spelling_comprehensive.py # Metric spelling comprehensive
    │   ├── test_spelling_mistakes.py   # Spelling mistake tests
    │   ├── test_ontology.py            # Ontology tests
    │   ├── test_synonyms.py            # Synonym recognition tests
    │   ├── test_abbreviations.py       # Abbreviation tests
    │   └── (additional metric tests)
    │
    ├── sp1500/                         # S&P 1500 tests (10+ files)
    │   ├── test_all_sp1500_companies.py # All S&P 1500 companies test
    │   ├── test_all_sp1500_tickers.py  # All S&P 1500 tickers test
    │   ├── test_sp1500_comprehensive.py # Comprehensive S&P 1500 test
    │   ├── test_sp1500_support.py      # S&P 1500 support test
    │   ├── test_sp1500_coverage.py     # S&P 1500 coverage test
    │   ├── test_sp1500_accuracy.py     # S&P 1500 accuracy test
    │   └── (additional S&P 1500 tests)
    │
    ├── debug/                          # Debug and troubleshooting scripts (20+ files)
    │   ├── debug_company_names.py      # Debug company name recognition
    │   ├── debug_failures.py           # Debug recognition failures
    │   ├── debug_remaining_failures.py # Debug remaining failures
    │   ├── debug_bookng.py             # Debug specific company (Booking)
    │   ├── debug_bookng_detailed.py    # Detailed Booking debug
    │   ├── debug_bookng_live.py        # Live Booking debug
    │   ├── analyze_company_name_failures.py # Analyze company name failures
    │   ├── get_all_failures.py         # Get all failures
    │   ├── identify_all_failures.py    # Identify all failures
    │   ├── test_all_failures_detailed.py # Detailed failure tests
    │   ├── test_specific_failures.py   # Specific failure tests
    │   ├── test_specific_spelling_failures.py # Spelling failure tests
    │   └── (additional debug scripts)
    │
    ├── verification/                   # Verification scripts (10+ files)
    │   ├── verify_metrics.py           # Metric verification
    │   ├── verify_new_data.py          # New data verification
    │   ├── verify_100_percent_complete.py # 100% completeness verification
    │   ├── check_sources.py            # Source checking utility
    │   ├── verify_accuracy.py          # Accuracy verification
    │   ├── verify_completeness.py      # Completeness verification
    │   ├── verify_performance.py       # Performance verification
    │   └── (additional verification scripts)
    │
    ├── ui/                             # UI test files (5+ files)
    │   ├── test_dashboard_sources.html  # Dashboard sources test
    │   ├── test_upload_button.html     # Upload button test
    │   ├── VERIFY_MARKDOWN_WORKS.html  # Markdown verification test
    │   ├── test_responsive_design.html # Responsive design test
    │   └── test_accessibility.html     # Accessibility test
    │
    ├── regression/                     # Regression tests (10+ files)
    │   ├── test_ticker_resolution.py   # Ticker resolution regression
    │   ├── test_time_fixes.py          # Time parsing fixes regression
    │   ├── test_parsing_regression.py  # Parsing regression tests
    │   ├── test_accuracy_regression.py # Accuracy regression tests
    │   ├── test_performance_regression.py # Performance regression tests
    │   └── (additional regression tests)
    │
    ├── manual/                         # Manual test scripts (25+ files)
    │   ├── test_100_percent_accuracy.py # 100% accuracy manual test
    │   ├── test_100_percent_confidence.py # 100% confidence manual test
    │   ├── test_100_prompts_accuracy.py # 100 prompts accuracy test
    │   ├── test_accuracy_100_prompts.py # Accuracy 100 prompts test
    │   ├── test_all_sp500_all_kpis.py  # All S&P 500 all KPIs test
    │   ├── test_all_sp500_base_metrics.py # All S&P 500 base metrics test
    │   ├── test_comprehensive_manual.py # Comprehensive manual tests
    │   ├── test_edge_cases_manual.py   # Edge cases manual tests
    │   ├── test_stress_manual.py       # Stress testing manual
    │   └── (additional manual tests)
    │
    ├── performance/                    # Performance tests (10+ files)
    │   ├── test_query_performance.py   # Query performance tests
    │   ├── test_memory_usage.py        # Memory usage tests
    │   ├── test_latency.py             # Latency tests
    │   ├── test_throughput.py          # Throughput tests
    │   ├── test_scalability.py         # Scalability tests
    │   └── (additional performance tests)
    │
    ├── security/                       # Security tests (5+ files)
    │   ├── test_input_validation.py    # Input validation tests
    │   ├── test_sql_injection.py       # SQL injection tests
    │   ├── test_xss_protection.py      # XSS protection tests
    │   └── (additional security tests)
    │
    └── fixtures/                       # Test fixtures and data (10+ files)
        ├── sample_data.json            # Sample test data
        ├── mock_responses.json         # Mock API responses
        ├── test_portfolios.csv         # Test portfolio data
        ├── test_companies.json         # Test company data
        └── (additional test fixtures)
```
    │   ├── test_fixed_accuracy.py      # Fixed accuracy test
    │   ├── test_global_ticker_fix.py   # Global ticker fix test
    │   ├── test_real_chatbot_accuracy.py # Real chatbot accuracy test
    │   ├── test_show_failed_facts.py   # Show failed facts test
    │   ├── test_stress_50_companies.py # Stress test 50 companies
    │   ├── test_stress_all_metrics.py  # Stress test all metrics
    │   ├── test_stress_edge_cases.py   # Stress test edge cases
    │   ├── test_stress_performance.py  # Stress test performance
    │   ├── test_verification_coverage.py # Verification coverage test
    │   └── test_verification_system.py # Verification system test
    │
    ├── standalone/                     # Standalone ML forecast tests
    │   ├── test_all_ml_forecast_prompts.py # All ML forecast prompts
    │   ├── test_all_ml_patterns_comprehensive.py # All ML patterns comprehensive
    │   ├── test_all_ml_prompts_comprehensive.py # All ML prompts comprehensive
    │   ├── test_ml_batch.py            # ML batch test
    │   ├── test_ml_debug.py            # ML debug test
    │   ├── test_ml_focused.py          # ML focused test
    │   ├── test_ml_forecast_prompts.py # ML forecast prompts test
    │   ├── test_ml_forecast_quality.py # ML forecast quality test
    │   ├── test_ml_forecast_quick.py   # ML forecast quick test
    │   └── test_ml_incremental.py      # ML incremental test
    │
    ├── outputs/                        # Test output files
    │   ├── sp500_dashboard_test_results.txt # S&P 500 dashboard results
    │   ├── sp500_test_output.txt       # S&P 500 test output
    │   ├── ml_test_output.txt          # ML test output
    │   └── test_single_company_payload.json # Single company test payload
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
| scripts/generate_aliases.py | Regenerates the S&P 1500 alias universe (aliases.json) covering all 1,599 companies. Updates ticker aliases for parser with company names and spelling corrections. |

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
| src/finanlyzeos_chatbot/parsing/alias_builder.py | Ticker alias resolution for **S&P 1500 (1,599 companies)**. Normalizes company mentions, loads alias sets, applies 85+ manual overrides for common misspellings, and resolves tickers with advanced fuzzy fallbacks. Handles 90% of company name spelling mistakes using progressive cutoff matching (0.85-0.65) and manual overrides. |
| src/finanlyzeos_chatbot/parsing/aliases.json | Generated ticker aliases covering **all 1,599 S&P 1500 companies**. Includes company names, ticker symbols, and common variations. Consumed at runtime by parser for ticker resolution. |
| src/finanlyzeos_chatbot/parsing/ontology.py | Metric ontology defining **93 KPI definitions** with **200+ synonyms** and natural language variations. Provides structured knowledge base for financial metrics. Handles 100% of metric spelling mistakes using multi-level fuzzy matching with adaptive thresholds. |
| src/finanlyzeos_chatbot/parsing/parse.py | Natural language parser converting prompts into structured intents. Extracts tickers (with spelling correction), metrics (with spelling correction), periods, and recognizes **40+ intent types**. Supports **150+ question patterns** with 100% detection rate. |
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

### ✏️ Spelling & Correction (Integrated in Parsing)

**Note:** Spelling correction is integrated directly into `alias_builder.py` and `parse.py` rather than being a separate module. This ensures seamless spelling mistake handling during query parsing and ticker/metric resolution.

| File | Description |
|------|-------------|
| src/finanlyzeos_chatbot/parsing/alias_builder.py | Company name spelling correction with **90% success rate**. Uses progressive cutoff matching (0.85-0.65), 85+ manual overrides, and fuzzy fallback. Handles all 1,599 S&P 1500 companies with common misspellings. |
| src/finanlyzeos_chatbot/parsing/parse.py | Metric name spelling correction with **100% success rate**. Uses multi-level fuzzy matching with adaptive thresholds. Handles 93 metrics with 200+ synonyms and common misspellings. |

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
