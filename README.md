# BenchmarkOS Chatbot Platform

A full-stack reference implementation for building institutional finance copilots on top of BenchmarkOS data services. The repository combines a hardened analytics engine, pluggable language models, data-ingestion utilities, and both CLI and web experiences. Everything is written in plain Python so you can run it locally, extend it for class projects, or deploy it to production infrastructure.

## Table of Contents
- [Key Capabilities](#key-capabilities)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration & Secrets](#configuration--secrets)
  - [SQLite vs PostgreSQL](#sqlite-vs-postgresql)
  - [Managing the OpenAI API Key Securely](#managing-the-openai-api-key-securely)
- [Running the Chatbot](#running-the-chatbot)
  - [Command Line](#command-line)
  - [Web UI](#web-ui)
  - [Supported Chat Commands](#supported-chat-commands)
- [Data Ingestion Workflows](#data-ingestion-workflows)
- [Testing & Quality](#testing--quality)
- [Extending the Platform](#extending-the-platform)
- [Troubleshooting](#troubleshooting)
- [Reference](#reference)

## Key Capabilities
- **Python-first workflow** – Standard package layout that works out of the box with VS Code, PyCharm, or terminal toolchains.
- **Robust analytics layer** – `AnalyticsEngine` refreshes fundamentals, computes growth/profitability/valuation metrics, and pulls quotes when available.
- **Flexible LLM integration** – Swap between the local echo model (offline development) and OpenAI Chat Completions with a single configuration change.
- **Secure secret handling** – API keys are never stored in code; the client reads from environment variables, OS keyrings, or a user config file.
- **CLI and web experiences** – `run_chatbot.py` provides a REPL, while `serve_chatbot.py` launches the FastAPI-powered UI in `webui/`.
- **Ingestion utilities** – Batch scripts populate fundamentals from SEC/Yahoo data, with audit logging and restart-safe progress tracking.

## Architecture
## File-by-File Overview
The project is intentionally organised so each module has a single, well-defined responsibility. Use this table as a quick reference when you or a teammate needs to dive into a new area.

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Build metadata, dependency list, pytest configuration (sets `pythonpath = ["src", "."]`). |
| `.env.example` | Template showing recommended environment variables (SQLite defaults, optional PostgreSQL, Bloomberg toggles). Copy to `.env` for local configuration. |
| `run_chatbot.py` | Minimal CLI runner; instantiates `BenchmarkOSChatbot` and starts the REPL. |
| `serve_chatbot.py` | Convenience wrapper around `uvicorn` to launch the FastAPI app in `src/benchmarkos_chatbot/web.py`. |
| `src/benchmarkos_chatbot/__init__.py` | Public API exports: chatbot, analytics engine, settings loader, ingestion hook, ticker utilities. |
| `src/benchmarkos_chatbot/config.py` | `Settings` dataclass plus `load_settings()`. Validates environment variables, ensures cache directories exist, and normalises types (integers, floats, booleans). |
| `src/benchmarkos_chatbot/database.py` | SQLite schema management, connection helpers, and CRUD utilities for metrics, facts, messages, audits, and scenario results. Handles WAL mode, UTC timestamps, ticker normalisation, and JSON serialisation. |
| `src/benchmarkos_chatbot/secdb.py` | Optional PostgreSQL backend for SEC data. Mirrors the SQLite helpers but uses `psycopg2-binary`. Activated when `DATABASE_TYPE=postgresql`. |
| `src/benchmarkos_chatbot/data_sources.py` | Clients for EDGAR, Yahoo Finance, and (optionally) Bloomberg. Responsible for HTTP requests, retries, and payload normalisation. |
| `src/benchmarkos_chatbot/data_ingestion.py` | High-level ingestion workflows (bootstrap sample data, streaming updates, live ticker ingestion). Produces `IngestionReport` objects and records audit events. |
| `src/benchmarkos_chatbot/analytics_engine.py` | Core analytics pipeline. Loads facts, computes base/derived/aggregate metrics, refreshes market quotes, and exposes helpers like `get_metrics`, `run_scenario`, and `fetch_scenario_results`. |
| `src/benchmarkos_chatbot/table_renderer.py` | Shared ASCII table builder used by CLI commands (`table`/`compare`) and the chatbot. Supports custom layouts, metric abbreviations, year filters, and chunked output. |
| `src/benchmarkos_chatbot/llm_client.py` | Language model abstraction. Provides `LocalEchoLLM` for offline testing and `OpenAILLMClient` which resolves the API key via environment, OS keyring, or config file. |
| `src/benchmarkos_chatbot/chatbot.py` | Orchestrates conversation flow: intent parsing, table generation, ingestion commands, audit lookups, LLM grounding, and message logging. `BenchmarkOSChatbot.create()` is the primary entry point. |
| `src/benchmarkos_chatbot/tasks.py` | Background task definitions (e.g., ingestion queues). Useful when integrating with task runners or async frameworks. |
| `src/benchmarkos_chatbot/ticker_universe.py` | Loads ticker universes, synonyms, and search utilities used for fuzzy matching of company names. |
| `src/benchmarkos_chatbot/web.py` | FastAPI application exposing REST endpoints (`/chat`, `/health`, metrics/audit endpoints). Serves the static assets in `webui/`. |
| `webui/index.html`, `webui/app.js`, `webui/styles.css` | Single-page web client for the chatbot. Handles chat form submission, status indicators, message rendering (including tables), and responsive styling. |
| `tests/test_*.py` | Pytest suites covering analytics calculations, ingestion flows, database persistence, CLI table rendering, and chatbot interactions. Fixtures use the local echo model so tests run offline. |
| `ingest_*.py`, `batch_ingest.py` | Command-line utilities for populating the database with SEC fundamentals, frames, and other datasets. Include resume capability and throttling options. |

Feel free to extend this table as the project evolves—keeping it current helps new contributors (and future you) ramp up quickly.
```
Project/
├── README.md                     # This guide
├── pyproject.toml                # Build metadata + pytest configuration
├── requirements.txt              # Dependency snapshot (optional)
├── .env.example                  # Sample environment configuration
├── cache/                        # Generated ingestion caches
├── data/                         # Sample CSVs used by tests/ingestion
├── docs/                         # Extra documentation / design notes
├── src/
│   └── benchmarkos_chatbot/
│       ├── __init__.py              # Public API exports
│       ├── analytics_engine.py      # Metrics pipeline + quote refresh
│       ├── chatbot.py               # Conversation orchestrator
│       ├── config.py                # Settings dataclass & loader
│       ├── data_ingestion.py        # Batch/bootstrap ingestion helpers
│       ├── data_sources.py          # External data adapters (SEC, Yahoo, …)
│       ├── database.py              # SQLite schema + helpers
│       ├── llm_client.py            # Local echo + OpenAI clients
│       ├── secdb.py                 # Optional PostgreSQL/SEC store
│       ├── table_renderer.py        # ASCII renderer for compare/table commands
│       ├── tasks.py                 # Background task definitions
│       ├── ticker_universe.py       # Universe and synonym loaders
│       └── web.py                   # FastAPI application powering the UI
├── tests/                         # Pytest suites for analytics, CLI, ingestion
├── webui/                         # Static assets for the web chatbot
├── run_chatbot.py                 # CLI runner
├── serve_chatbot.py               # Web server launcher (uvicorn)
└── ingest_*.py / batch_ingest.py  # Data ingestion entry points
```

## Quick Start
```bash
# 1. Clone and enter the project
git clone https://github.com/haniae/Project.git
cd Project

# 2. Create a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a working .env from the template
cp .env.example .env  # or: Copy-Item .env.example .env
```
You now have everything you need to run the chatbot locally.

## Configuration & Secrets
Configuration is centralised in `config.py` through the `Settings` dataclass. `load_settings()` reads from environment variables (including values in `.env`) and performs validation before any component is initialised.

Important variables:
- `DATABASE_TYPE`: `sqlite` (default) or `postgresql`.
- `DATABASE_PATH`: location of the SQLite file.
- `LLM_PROVIDER`: `local` or `openai`.
- `OPENAI_MODEL`: OpenAI chat model to use (e.g. `gpt-3.5-turbo`, `gpt-4o-mini`).
- `SEC_API_USER_AGENT`: Required by the SEC for EDGAR access.
- `YAHOO_QUOTE_BATCH_SIZE`: Number of tickers per quote refresh (adjust to avoid rate limits).
- `ENABLE_BLOOMBERG`, `BLOOMBERG_*`: Optional real-time quote integration.

### SQLite vs PostgreSQL
- **SQLite** is the default and works out of the box. `DATABASE_PATH` controls where the `.sqlite3` file lives.
- **PostgreSQL** support is provided via `secdb.py`. Set `DATABASE_TYPE=postgresql` and supply `POSTGRES_*` variables. The analytics engine will then prefer live data from the SEC store.

### Managing the OpenAI API Key Securely
`llm_client.py` resolves the key in the following order:
1. `OPENAI_API_KEY` environment variable (including values in `.env`).
2. OS keyring entry: service `benchmarkos-chatbot`, username `openai-api-key`.
3. Fallback file `~/.config/benchmarkos-chatbot/openai_api_key` (outside the repo).

Recommended approach (Windows PowerShell example):
```powershell
pip install keyring
python -c "import keyring; keyring.set_password('benchmarkos-chatbot', 'openai-api-key', 'sk-your-real-key')"
```
Then set in `.env`:
```
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-3.5-turbo
```
No API key is committed or stored in plaintext.

## Running the Chatbot
### Command Line
```bash
python run_chatbot.py
```
The REPL prints a banner and waits for prompts. Type `help` to see available commands.

### Web UI
```bash
python serve_chatbot.py            # defaults to http://127.0.0.1:8000
python serve_chatbot.py --port 8001  # choose another port if 8000 is busy
```
Visit the address in your browser to interact with the single-page UI. The status dot indicates API health; the app formats both free-form chat and rendered tables.

If you receive `WinError 10048` the port is in use. Either stop the process holding it (`taskkill /PID <pid> /F`) or pass `--port` to use a different socket.

### Supported Chat Commands
The chatbot handles several finance-aware commands before falling back to the language model:
- `help` – show the reference card.
- `metrics <TICKER> [YYYY | YYYY-YYYY] [vs <OTHER> ...]` – KPI summary or comparison table.
- `compare <TICKER_A> <TICKER_B> [MORE] [YEAR]` – quick comparison across tickers.
- `table <TICKERS...> metrics <METRICS...> [year=YYYY | years=YYYY-YYYY] [layout=metrics]` – fine-grained ASCII tables (used in the test suite).
- `fact <TICKER> <YEAR> [metric]` – raw financial fact lookups.
- `audit <TICKER> [YEAR]` – recent audit log entries.
- `ingest <TICKER> [years]` – pull fresh SEC/Yahoo data and refresh metrics.
- `scenario <TICKER> <NAME> rev=+5% margin=+1% mult=+0.5%` – run a what-if scenario.

All other prompts are passed to the configured LLM. When tickers are detected in the question, the chatbot assembles a short “financial context” block to ground the model’s response.

## Data Ingestion Workflows
- `ingest_universe.py` – orchestrates large-scale SEC ingestion (e.g. S&P 500 fundamentals). Progress is tracked so interrupted runs can resume.
  ```bash
  python ingest_universe.py --years 10 --chunk-size 25 --sleep 2.0 --resume
  ```
- `batch_ingest.py`, `ingest_companyfacts.py`, `ingest_frames.py`, etc. – specialised jobs for different EDGAR datasets.
- `data_ingestion.py` – the bootstrap hook invoked on startup to seed sample data. Logs are written via `database.record_audit_event`.

## Testing & Quality
Pytest is already configured in `pyproject.toml`:
```bash
pytest
```
Selected suites:
- `tests/test_database.py` – schema and query guarantees.
- `tests/test_analytics_engine.py` – metric computations and quote refresh.
- `tests/test_cli_tables.py` – ASCII table renderer sanity checks.
- `tests/test_data_ingestion.py` – ingestion setup and audit trails.
- `tests/test_analytics.py` – end-to-end chatbot behaviours.

Some fixtures rely on the local echo model; no external network access is required.

## Extending the Platform
- **Analytics**: add derived metrics or alternate time horizons in `analytics_engine.py`, and persist them via `database.py`.
- **LLM providers**: implement another client (Anthropic, Azure OpenAI, local embedding model) in `llm_client.py` and enhance `build_llm_client`.
- **Retrieval**: augment `_build_rag_context` in `chatbot.py` with vector search or knowledge graphs.
- **UI**: customise `webui/` or wrap `BenchmarkOSChatbot` inside a FastAPI/Flask/Streamlit app using `web.py`.
- **Ops**: containerise with Docker, deploy uvicorn behind Nginx, or integrate with your CI pipeline (pytest already set up).

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `gaierror` or `Too Many Requests` on startup | Yahoo refresh hit rate limits | Lower `YAHOO_QUOTE_BATCH_SIZE`, disable refresh temporarily, or rely on cached quotes. |
| `WinError 10048` when running `serve_chatbot.py` | Port 8000 already bound | Kill the existing process (`taskkill /PID <pid> /F`) or pass `--port 8001`. |
| `OpenAI API key not found` | No key in env/keyring/fallback file | Add `OPENAI_API_KEY` to `.env`, store it with `keyring`, or create the fallback file. |
| Tests complain about missing arguments to `Settings` | Ensure fixtures align with the current dataclass signature (see examples in `tests/`). |

## Reference
- **CLI**: `python run_chatbot.py`
- **Web**: `python serve_chatbot.py --reload`
- **Ingestion**: `python ingest_universe.py --help`
- **API surface**: `BenchmarkOSChatbot.create(settings)` returns a chatbot you can embed elsewhere. Use `bot.ask("...")` to generate replies.

Document decisions, metrics, or deployment notes in `docs/` so teammates and reviewers can audit your work. Enjoy building on BenchmarkOS!