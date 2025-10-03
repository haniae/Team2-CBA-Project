# BenchmarkOS Chatbot Starter

A production-ready scaffold for building institutional finance chatbots on top of BenchmarkOS data services. The project emphasises clarity: clean Python packaging, explicit configuration, and well-documented analytics pipelines so teams can customise quickly.

## Table of Contents
- [Highlights](#highlights)
- [System Overview](#system-overview)
- [Architecture Tree](#architecture-tree)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running the Chatbot](#running-the-chatbot)
- [Data Ingestion Workflows](#data-ingestion-workflows)
- [Testing](#testing)
- [Extending the Platform](#extending-the-platform)
- [Available Metrics](#available-metrics)

## Highlights
- **Python-first workflow** – Standard package layout that works in VS Code, PyCharm, or a terminal editor.
- **Portable persistence** – SQLite by default with optional PostgreSQL (SEC datasets) via `psycopg2-binary`.
- **Pluggable language models** – Local echo model for offline development; OpenAI client when credentials are present.
- **Environment-driven settings** – All secrets and runtime toggles live in `.env` or environment variables.
- **Rich analytics** – Derives growth, profitability, valuation, and shareholder-return metrics out of the box.

## System Overview
1. **Configuration** – `load_settings()` builds a `Settings` dataclass from `.env`/environment variables.
2. **Data layer** – `database.py` (SQLite) and `secdb.py` (PostgreSQL) expose consistent query helpers.
3. **Analytics engine** – `AnalyticsEngine` computes snapshots/derived metrics and refreshes quotes.
4. **LLM interface** – `llm_client.py` selects the local stub or OpenAI client.
5. **Chatbot orchestration** – `BenchmarkOSChatbot` routes user input to analytics commands or the LLM.
6. **Presentation** – CLI (`run_chatbot.py`/`main.py`) or custom web UI (`webui/`, `web.py`).

## Architecture Tree
```
Project/
├── README.md
├── pyproject.toml              # Build metadata + pytest config (pythonpath includes src and project root)
├── requirements.txt            # Optional dependency pinning
├── .env.example                # Template showing SQLite + PostgreSQL options
├── benchmarkos_chatbot.sqlite3 # Default SQLite database (WAL/SHM files adjacent)
├── cache/                      # Intermediate ingestion caches (created at runtime)
├── data/                       # Raw data payloads used by ingestion scripts
├── docs/                       # Additional specification material
├── src/
│   └── benchmarkos_chatbot/
│       ├── __init__.py              # Public API exports (chatbot, analytics engine, ingestion hook)
│       ├── analytics_engine.py      # Metrics pipeline & optional PostgreSQL/SEC integration
│       ├── chatbot.py               # Conversation flow and command handling
│       ├── config.py                # Settings dataclass + environment loader
│       ├── data_ingestion.py        # Bootstrap + batch ingestion helpers
│       ├── data_sources.py          # Adapters for EDGAR, Yahoo Finance, Bloomberg*
│       ├── database.py              # SQLite schema management and query helpers
│       ├── llm_client.py            # Local echo + OpenAI API clients
│       ├── secdb.py                 # PostgreSQL store for SEC datasets (requires DATABASE_TYPE=postgresql)
│       ├── table_renderer.py        # ASCII table rendering for table/compare commands
│       ├── tasks.py                 # Background ingestion task definitions
│       ├── ticker_universe.py       # Universe loaders and ticker synonym handling
│       └── web.py                   # Web service glue (FastAPI/Flask ready)
├── webui/
│   ├── index.html                  # UI shell
│   ├── app.js                      # Browser-side chatbot client
│   └── styles.css                  # Styling
├── tests/                          # Pytest suites covering analytics, ingestion, database, CLI
│   ├── test_analytics.py
│   ├── test_analytics_engine.py
│   ├── test_cli_tables.py
│   ├── test_data_ingestion.py
│   └── test_database.py
├── run_chatbot.py                  # Minimal REPL for local experimentation
├── serve_chatbot.py                # Example service launcher
├── main.py                         # Legacy CLI entry point (hosts `_try_table_command` used by tests)
└── ingest_*.py / batch_ingest.py   # Scripts for populating datasets (company facts, frames, etc.)
```
*Bloomberg connectivity activates when `ENABLE_BLOOMBERG=1` and `blpapi` is installed.*

## Prerequisites
- Python 3.10+
- (Optional) PostgreSQL server if you want the SEC-backed data store
- (Optional) OpenAI API key for non-local LLM responses

## Setup
```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
1. Copy the template and customise values:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` (or export directly) to control:
   - `DATABASE_TYPE` (`sqlite` default, `postgresql` for SEC DB)
   - `DATABASE_PATH` (SQLite file location)
   - `POSTGRES_*` (host, port, user, password, schema)
   - `LLM_PROVIDER` (`local` or `openai`)
   - `OPENAI_MODEL`, `OPENAI_API_KEY`
   - `SEC_API_USER_AGENT`
   - `ENABLE_BLOOMBERG`, `BLOOMBERG_HOST`, `BLOOMBERG_PORT`

`load_settings()` in `config.py` normalises these values, creates cache directories, and validates constraints (for example, positive timeouts and integer ports).

## Running the Chatbot
Launch the REPL:
```bash
python run_chatbot.py
```
- By default the local echo model mirrors your input (`LLM_PROVIDER=local`).
- Switch to OpenAI by setting `LLM_PROVIDER=openai` and supplying `OPENAI_API_KEY`.
- Commands like `table` and `compare` render ASCII tables via `table_renderer.py`:
  ```text
  table AAPL MSFT metrics revenue net_income layout=metrics years=2021-2024
  compare NVDA AMD metrics all
  ```

## Data Ingestion Workflows
- `ingest_universe.py` downloads large universes (e.g., S&P 500 fundamentals).
  ```bash
  python ingest_universe.py --years 10 --chunk-size 25 --sleep 2.0 --resume
  ```
- `batch_ingest.py`, `ingest_companyfacts.py`, `ingest_frames.py`, and related scripts populate specialised datasets.
- Ingestion scripts rely on `data_ingestion.py`, `data_sources.py`, and `database.py` to normalise tickers, enforce UTC timestamps, and refresh metric snapshots.
- When `DATABASE_TYPE=postgresql`, ingestion routes via `secdb.py` to the configured PostgreSQL schema.

## Testing
```bash
pytest
```
> Tip: Some tests construct `Settings` manually; ensure fixtures provide all required arguments or call `load_settings()` when extending the suite.

## Extending the Platform
- **New analytics** – augment `analytics_engine.py` and add schema/migration logic in `database.py`.
- **Additional LLM providers** – implement a new client in `llm_client.py` and register it in `BenchmarkOSChatbot`.
- **Web deployment** – reuse `BenchmarkOSChatbot` inside `web.py` (FastAPI/Flask) or the provided `webui/` assets.
- **Metrics/KPIs** – capture latency, satisfaction, or custom KPIs by extending the SQLite schema and adding collection hooks in `chatbot.py`.

## Available Metrics
| Category            | Metrics                                                                 |
|---------------------|-------------------------------------------------------------------------|
| Growth              | `revenue_cagr`, `eps_cagr`, `ebitda_growth`                             |
| Profitability       | `profit_margin`, `net_margin`, `operating_margin`, `return_on_assets` (`roa`), `return_on_equity` (`roe`), `return_on_invested_capital` (`roic`) |
| Capital efficiency  | `free_cash_flow`, `free_cash_flow_margin`, `cash_conversion`, `working_capital`, `working_capital_change` |
| Valuation           | `pe_ratio`, `ev_ebitda`, `pb_ratio`, `peg_ratio`, `dividend_yield`      |
| Shareholder return  | `tsr`, `share_buyback_intensity`                                        |

Underlying fundamentals (revenue, net income, EPS, assets, liabilities, cash flows, etc.) remain accessible for tabular comparisons and analytics extensions.

---
Questions, deployment notes, or design decisions can be recorded in `docs/` so collaborators and graders can trace how the chatbot evolves.
