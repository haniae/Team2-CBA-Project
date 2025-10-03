# BenchmarkOS Chatbot Platform

A full-stack reference implementation for building institutional finance copilots. This README is written for classmates, professors, or teammates who may be encountering the codebase for the first time. It walks through every moving part—files, configuration, commands, and workflows—with friendly explanations so you can get productive quickly.

---

## 1. TL;DR Quick Demo
If you just want to see the bot talk:
```bash
# from the project root
python -m venv .venv
.\.venv\Scripts\activate          # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
Copy-Item .env.example .env        # or `cp`
python run_chatbot.py              # starts the CLI
```
Type `help` and follow the menu. When you are ready for the web UI:
```bash
python serve_chatbot.py            # defaults to http://127.0.0.1:8000
```
Press `Ctrl+C` to stop either process.

---

## 2. What the Repository Contains
Here is the project at a glance. The table below describes every important file so newcomers know where to look.

| Path | Why it matters |
|------|----------------|
| `pyproject.toml` | Python packaging metadata, dependency list, and pytest configuration. `pythonpath = ["src", "."]` allows tests/scripts to import the package. |
| `.env.example` | Sample environment file listing knobs for SQLite, PostgreSQL, OpenAI, and Bloomberg integration. Copy to `.env` for local runs. |
| `run_chatbot.py` | Lightweight REPL for experimenting with the bot from the terminal. |
| `serve_chatbot.py` | Launches the FastAPI web service (defined in `src/benchmarkos_chatbot/web.py`) using `uvicorn`. |
| `src/benchmarkos_chatbot/config.py` | Loads and validates environment variables into an immutable `Settings` object so the rest of the code does not read from the environment directly. |
| `src/benchmarkos_chatbot/database.py` | SQLite layer: schema creation, typed record dataclasses, and CRUD helpers for conversations, metrics, facts, audit logs, and scenario results. |
| `src/benchmarkos_chatbot/secdb.py` | Optional PostgreSQL backend mirroring the SQLite helpers. Activated when `DATABASE_TYPE=postgresql`. |
| `src/benchmarkos_chatbot/data_sources.py` | HTTP clients for SEC EDGAR, Yahoo Finance, and optional Bloomberg feeds. Responsible for retries and payload normalisation. |
| `src/benchmarkos_chatbot/data_ingestion.py` | Orchestrates ingestion jobs (bootstrap sample data, live ticker refresh) and records audit events. Returns `IngestionReport` objects. |
| `src/benchmarkos_chatbot/analytics_engine.py` | Core analytics pipeline. Loads raw fundamentals, computes base/derived/aggregate metrics, refreshes market quotes, and exposes helpers like `get_metrics`, `run_scenario`, and `fetch_scenario_results`. |
| `src/benchmarkos_chatbot/chatbot.py` | Conversation orchestrator. Parses user intents, calls the analytics engine, runs ingestion commands, and falls back to the configured LLM. `BenchmarkOSChatbot.create()` is the entry point used by CLI/web. |
| `src/benchmarkos_chatbot/llm_client.py` | Language-model abstraction. Includes the offline echo model plus the OpenAI client. Automatically locates the API key via environment variables, OS keyring, or a fallback file. |
| `src/benchmarkos_chatbot/table_renderer.py` | Shared ASCII table renderer used by `compare` / `table` commands and tests. Supports year filters and alternate layouts. |
| `src/benchmarkos_chatbot/web.py` | FastAPI application exposing `/chat`, `/health`, and helper endpoints. Serves static assets from `webui/`. |
| `webui/index.html`, `webui/app.js`, `webui/styles.css` | Single-page web client. Handles chat submissions, status indicator, scrollable conversation log, and adaptive styling. |
| `tests/test_*.py` | Pytest suites covering analytics, ingestion, persistence, CLI tables, and chatbot behaviour. Designed to run offline using the local echo LLM. |
| `ingest_*.py`, `batch_ingest.py` | Command line utilities for pulling SEC fundamentals and related datasets. Include resume and throttling options. |
| `cache/`, `data/` | Working directories for ingestion artefacts and sample CSVs used by tests. Safe to delete—they are recreated automatically. |

---

## 3. Step-by-Step Setup (beginner friendly)
Follow these steps even if you have never touched this project before.

### 3.1 Install Python & Git
- Windows: [Install Python 3.10+](https://www.python.org/downloads/) and Git. Ensure “Add python.exe to PATH” is checked.
- macOS: `xcode-select --install` for developer tools, then `brew install python git`.
- Linux: use your package manager (`sudo apt install python3 python3-venv git`).

### 3.2 Clone the repository
```bash
git clone https://github.com/haniae/Project.git
cd Project
```

### 3.3 Create and activate a virtual environment
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3.4 Install dependencies
```bash
pip install -r requirements.txt
```

### 3.5 Create your `.env`
```bash
Copy-Item .env.example .env   # Windows PowerShell
# or cp .env.example .env     # macOS/Linux
```
Open `.env` and customise values (see the next section for explanations).

---

## 4. Configuration & Secrets
All configuration flows through `load_settings()` in `config.py`. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_TYPE` | `sqlite` (local file) or `postgresql` (SEC data warehouse). | `sqlite` |
| `DATABASE_PATH` | Path to SQLite database file. | `benchmarkos_chatbot.sqlite3` |
| `LLM_PROVIDER` | `local` (echo) or `openai`. | `local` |
| `OPENAI_MODEL` | OpenAI chat model id (`gpt-3.5-turbo`, `gpt-4o-mini`, etc.). | `gpt-4o-mini` |
| `SEC_API_USER_AGENT` | Required by SEC EDGAR (`Org Name Contact`). | `BenchmarkOSBot/1.0 ...` |
| `YAHOO_QUOTE_BATCH_SIZE` | Yahoo quote batch size. Lower this if you hit HTTP 429. | `50` |
| `ENABLE_BLOOMBERG` | `0`/`1` toggle. Requires `blpapi`. | `0` |
| `POSTGRES_*` | Host, port, user, password, schema for SEC PostgreSQL store. | n/a |

### 4.1 Securely storing the OpenAI API key
The project will never hard-code your key. `_resolve_openai_api_key()` looks in this order:
1. `OPENAI_API_KEY` environment variable (values in `.env` count).
2. OS keyring entry `benchmarkos-chatbot` / `openai-api-key` (recommended).
3. Fallback file `~/.config/benchmarkos-chatbot/openai_api_key` (outside the repo).

**Store it in the keyring (Windows example):**
```powershell
pip install keyring
python -c "import keyring; keyring.set_password('benchmarkos-chatbot', 'openai-api-key', 'sk-your-real-key')"
```
Then set in `.env`:
```
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-3.5-turbo
```
You can omit `OPENAI_API_KEY` from `.env` entirely once the key lives in the keyring.

---

## 5. Running the Chatbot
### 5.1 Command line interface
```bash
python run_chatbot.py
```
The prompt shows `BenchmarkOS Chatbot quick runner`. Type `help` for the command menu. A typical session might look like:
```
> help
Commands:
  metrics <TICKER> ...
  compare ...
  ...
> metrics AAPL 2023
Phase1 KPIs for AAPL ...
```
Press `Ctrl+C` or type `exit` to quit.

### 5.2 Web user interface
```bash
python serve_chatbot.py --port 8000
```
Open http://127.0.0.1:8000 in your browser. Features include:
- Status dot that polls `/health` every 30 seconds.
- Scrollable conversation log showing user/assistant messages and rendered tables.
- Keyboard shortcut: `Enter` sends, `Shift+Enter` adds a newline.

If you receive `WinError 10048`, another process is using the port. Either terminate it (`taskkill /PID <pid> /F`) or launch on another port (`--port 8001`).

### 5.3 Chatbot command cheat sheet
| Command | Example | Description |
|---------|---------|-------------|
| `help` | `help` | Shows the list of supported commands. |
| `metrics` | `metrics AAPL 2022-2024 vs MSFT` | KPI summary or comparison table. Optional year filters. |
| `compare` | `compare NVDA AMD 2023` | Quick cross-ticker comparison (metrics in rows, tickers in columns). |
| `table` | `table AAPL MSFT metrics revenue net_income layout=metrics years=2021-2023` | Low-level access to the ASCII table renderer; used in tests. |
| `fact` | `fact TSLA 2022 revenue` | Raw financial fact lookup. |
| `audit` | `audit AAPL 2021` | Shows recent audit log entries. |
| `ingest` | `ingest TSLA 5` | Pulls fresh SEC/Yahoo data and refreshes metrics for the ticker. |
| `scenario` | `scenario MSFT bull rev=+8% margin=+2% mult=+0.5` | Runs a what-if analysis. |
| anything else | `How is MSFT performing vs AAPL?` | Routed to the configured LLM with grounding context if tickers are detected. |

---

## 6. Data Flow & Ingestion
1. `ingest_*.py` scripts fetch SEC data (company facts, frames, etc.) and populate SQLite or PostgreSQL tables.
2. `data_ingestion.py` orchestrates bootstrap ingestion at startup and logs audit events via `database.record_audit_event`.
3. `analytics_engine.refresh_metrics()` pulls the latest facts, computes derived metrics (margins, ROE, growth rates), and stores them in `metric_snapshots` for fast lookup.
4. The chatbot, CLI, and web API all query `AnalyticsEngine` for metrics, facts, audit trails, and scenario results.

### 6.1 Running a full ingestion demo
```bash
python ingest_universe.py --years 10 --chunk-size 25 --sleep 2 --resume
```
This command pulls ten years of fundamentals for the sample universe, pausing 2 seconds between batches to respect SEC rate limits. Progress is stored in `.ingestion_progress.json` so you can restart after interruptions.

---

## 7. Testing & Quality
Pytest is configured via `pyproject.toml`. Tests use the local echo LLM so they do not require network access.
```bash
pytest                 # run everything
pytest tests/test_cli_tables.py::test_table_command_formats_rows
```
Key suites:
- `test_database.py` – validates schema invariants and helper functions.
- `test_analytics_engine.py` – checks growth/valuation metrics and quote refresh logic.
- `test_cli_tables.py` – exercises the ASCII renderer used in CLI commands.
- `test_data_ingestion.py` – ensures ingestion populates facts and audit logs.
- `test_analytics.py` – end-to-end chatbot behaviour tests.

---

## 8. Troubleshooting FAQ
| Issue | Cause | Resolution |
|-------|-------|------------|
| `Failed to refresh quotes ... 429 Too Many Requests` on startup | Yahoo Finance rate limit triggered. | Lower `YAHOO_QUOTE_BATCH_SIZE` in `.env`, disable refresh temporarily, or rely on cached quotes. |
| `WinError 10048` when running `serve_chatbot.py` | Port 8000 already in use. | `Get-NetTCPConnection -LocalPort 8000` → `taskkill /PID <pid> /F`, or run `--port 8001`. |
| `OpenAI API key not found` | Key not present in env, keyring, or fallback file. | Store it with the keyring command above or set `OPENAI_API_KEY` in `.env`. |
| Tests complain about missing constructor args for `Settings` | Fixtures out of sync with dataclass signature. | See examples in `tests/` and mirror the required parameters. |
| `ModuleNotFoundError: No module named 'main'` during pytest | `pythonpath` not set. | Ensure you run tests via the project root (pyproject sets the path automatically). |

---

## 9. Extending the Platform
- **New metrics**: add calculations in `analytics_engine.py` and extend the schema if necessary (use `database.py`).
- **Alternative LLM providers**: implement `LLMClient` in `llm_client.py` and update `build_llm_client`.
- **Retrieval augmentation**: enrich `_build_rag_context` in `chatbot.py` with vector search or a knowledge graph.
- **Web features**: customise the FastAPI routes in `web.py` or enhance the SPA in `webui/`.
- **Deployment**: package with Docker or a PaaS. `serve_chatbot.py` already exposes a standard ASGI app.

Document decisions, experiments, and deployment notes in `docs/` so other collaborators (and future you) can follow the reasoning behind each change.

Happy building!