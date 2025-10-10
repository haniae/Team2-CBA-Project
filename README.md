# BenchmarkOS Chatbot Platform

Institutional-grade analytics tooling for finance teams who need a conversational interface, reproducible metrics, and transparent data lineage. The codebase includes a CLI copilot, FastAPI service, single-page web client, and ingestion utilities that keep SEC filings and market data in sync.

## Table of contents
- [Overview](#overview)
- [Core capabilities](#core-capabilities)
- [Architecture map](#architecture-map)
- [Quick start](#quick-start)
- [Running the chatbot](#running-the-chatbot)
- [Data ingestion playbooks](#data-ingestion-playbooks)
- [Configuration reference](#configuration-reference)
- [Project layout](#project-layout)
- [File reference](#file-reference)
- [Quality and testing](#quality-and-testing)
- [Troubleshooting](#troubleshooting)
- [Further reading](#further-reading)

## Overview
BenchmarkOS ships a batteries-included template for building institutional finance copilots. It combines:

- Durable storage (SQLite by default, optional PostgreSQL) for conversations, facts, metrics, audit trails, and scenarios.
- An analytics engine that normalises SEC filings, enriches them with market quotes, and exposes both tabular and scenario APIs.
- A flexible LLM layer that runs either an offline echo model for tests or OpenAI models in production.
- Web and terminal experiences backed by the same FastAPI service so you can demo quickly and harden for production later.

The repository doubles as coursework and reference material: every module is heavily documented, and docs/orchestration_playbook.md explains scaling patterns for "any company" requests.

## Core capabilities
- **Multi-channel chat** - `run_chatbot.py` offers a REPL, `serve_chatbot.py` (or `uvicorn`) exposes REST endpoints, and `webui/` renders a browser client with live status indicators.
- **Deterministic analytics** - `AnalyticsEngine` calculates phase 1 and phase 2 metrics, growth rates, and valuation multiples from ingested filings and quotes.
- **Incremental ingestion** - `data_ingestion.py` plus helper scripts pull SEC EDGAR facts, Yahoo quotes, and optional Bloomberg feeds with retry and backoff.
- **Auditability** - `database.py` persists metric snapshots, raw financial facts, audit events, and full chat history for compliance reviews.
- **Extensible LLM layer** - swap between the local echo model and OpenAI by setting `LLM_PROVIDER`; extend `llm_client.py` for other vendors.
- **Task orchestration hooks** - `tasks.py` provides a queue abstraction you can wire into ingestion to hand off long-running fetches safely.

## Architecture map
See [`docs/architecture.md`](docs/architecture.md) for the high-level component diagram that accompanies this README. The doc highlights how the CLI, FastAPI service, analytics core, and ingestion pipelines collaborate.

## Quick start
These steps assume Python 3.10+ and Git are installed.

### 1. Clone and bootstrap
```bash
git clone https://github.com/haniae/Project.git
cd Project
python -m venv .venv
# PowerShell
.\.venv\Scripts\activate
# or, macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env   # PowerShell
# cp .env.example .env        # macOS/Linux
```

### 2. Review environment defaults
Open `.env` and customise database paths, API keys, and provider toggles (see [Configuration reference](#configuration-reference)).

### 3. Prime the datastore (optional for demos)
The project boots with SQLite and will lazily create tables on first run. To eagerly load metrics:
```bash
python ingest_universe.py --years 5 --chunk-size 25 --sleep 2 --resume
```
This pulls the sample ticker universe, respects SEC rate limits, and writes audit events.

## Running the chatbot
### CLI REPL
```bash
python run_chatbot.py
```
Inside the prompt, type `help` to list verbs. Highlights:

| Command | Example | Purpose |
|---------|---------|---------|
| `metrics` | `metrics AAPL 2022-2024` | Latest and historical KPI block for one ticker. |
| `compare` | `compare MSFT NVDA 2023` | Side-by-side metrics table. |
| `table` | `table TSLA metrics revenue net_income` | Low-level ASCII table renderer used in tests. |
| `fact` | `fact AMZN 2023 revenue` | Inspect a normalised financial fact. |
| `scenario` | `scenario GOOGL bull rev=+8% mult=+0.5` | Run a what-if analysis with deltas. |
| `ingest` | `ingest SHOP 5` | Trigger live ingestion (SEC, Yahoo, optional Bloomberg). |

### FastAPI service and web client
```bash
python serve_chatbot.py --port 8000
# or run the ASGI app directly
uvicorn benchmarkos_chatbot.web:app --reload --port 8000
```
Open http://127.0.0.1:8000 to load the single-page interface in `webui/`. The UI streams chat history, formats ASCII tables cleanly, and pings `/health` every 30 seconds to keep the status dot green.

Key REST endpoints once the server is running:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Submit a prompt, receive the assistant reply plus `conversation_id` for thread continuity. |
| `GET` | `/metrics` | Return computed metrics for one or more tickers; supports `start_year` and `end_year` filters. |
| `GET` | `/facts` | Fetch the normalised financial facts backing a statement. |
| `GET` | `/audit` | View the latest ingestion and audit events for a ticker. |
| `GET` | `/health` | Simple heartbeat used by load balancers and the web UI. |

## Data ingestion playbooks
Ingestion can happen synchronously from the CLI, scheduled batches, or background jobs.

### On-demand
`AnalyticsEngine.get_metrics` calls `ingest_live_tickers` when it detects missing coverage. You can wire this through `tasks.TaskManager` to queue jobs and poll for completion. See docstrings in `tasks.py` and the orchestration playbook for patterns.

### Batch scripts
| Script | When to use it | How to run |
|--------|----------------|------------|
| `ingest_universe.py` | Refresh a predefined ticker universe with rate-limit friendly batching and resume support. | `python ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2 --resume` |
| `batch_ingest.py` | Load the curated mega-cap list shipped with the repo (hard-coded tickers, retry with backoff). | `python batch_ingest.py` |
| `src/ingest_companyfacts.py` | Mirror SEC companyfacts into Postgres with metric aliases; configure via `SEC_TICKERS` and `PG*` env vars. | `SEC_TICKERS=MSFT,AAPL PGHOST=localhost python src/ingest_companyfacts.py` |
| `ingest_frames.py` | Fetch SEC data frames (e.g., revenues, net income) into Postgres for benchmarking. | `SEC_TICKERS=MSFT,AAPL python ingest_frames.py` |
| `load_prices_stooq.py` | Backfill prices from Stooq when Yahoo is rate limited; writes into Postgres. | `SEC_TICKERS=MSFT,AAPL python load_prices_stooq.py` |

All scripts honour the configuration loaded via `load_settings()` (where applicable) and persist audit events so the chatbot can explain sourcing decisions.

## Configuration reference
`load_settings()` reads environment variables (or `.env`) and provides sane defaults.

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_TYPE` | `sqlite` | Switch to `postgresql` for shared deployments. |
| `DATABASE_PATH` | `./benchmarkos_chatbot.sqlite3` | SQLite file location; auto-created if missing. |
| `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DATABASE` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | unset | Required when `DATABASE_TYPE=postgresql`; supports schema override via `POSTGRES_SCHEMA`. |
| `LLM_PROVIDER` | `local` | `local` uses the deterministic echo model. Set to `openai` for real completions. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name passed to the OpenAI Chat Completions API. |
| `SEC_API_USER_AGENT` | `BenchmarkOSBot/1.0 (support@benchmarkos.com)` | Required by SEC EDGAR. Use your organisation and contact info. |
| `EDGAR_BASE_URL` | `https://data.sec.gov` | Override for mirroring or proxying. |
| `YAHOO_QUOTE_URL` | `https://query1.finance.yahoo.com/v7/finance/quote` | Used to refresh live quotes. |
| `YAHOO_QUOTE_BATCH_SIZE` | `50` | Maximum tickers per Yahoo request (positive integer). |
| `HTTP_REQUEST_TIMEOUT` | `30` | Seconds before HTTP clients give up. |
| `INGESTION_MAX_WORKERS` | `8` | Thread pool size for ingestion routines. |
| `DATA_CACHE_DIR` | `./cache` | Stores downloaded filings, facts, and progress markers. |
| `ENABLE_BLOOMBERG` | `false` | Toggle Bloomberg integration; requires host, port, and timeout values. |
| `BLOOMBERG_HOST` / `BLOOMBERG_PORT` / `BLOOMBERG_TIMEOUT` | unset | Only used when Bloomberg ingestion is enabled. |
| `OPENAI_API_KEY` | unset | Optional: looks in env, then keyring, then `~/.config/benchmarkos-chatbot/openai_api_key`. |

Secrets belong in your `.env` (never commit it). For Windows developers, `keyring` support means you can store the OpenAI key securely outside the repo.

## Project layout
```
Project/
├── README.md
├── pyproject.toml               # Packaging and pytest config
├── requirements.txt             # Runtime dependencies
├── run_chatbot.py               # Terminal assistant entry point
├── serve_chatbot.py             # FastAPI launcher helper
├── main.py                      # Rich CLI surface for tables and metrics
├── src/
│   └── benchmarkos_chatbot/
│       ├── analytics_engine.py  # Metric calculations and scenario logic
│       ├── chatbot.py           # Conversation orchestration and intent routing
│       ├── config.py            # Environment and settings loader
│       ├── data_ingestion.py    # EDGAR, Yahoo, Bloomberg ingestion pipeline
│       ├── data_sources.py      # API clients and data transfer objects
│       ├── database.py          # SQLite or Postgres persistence helpers
│       ├── llm_client.py        # LLM abstractions (local and OpenAI)
│       ├── table_renderer.py    # ASCII table formatting utilities
│       ├── tasks.py             # Optional ingestion and job queue helpers
│       └── web.py               # FastAPI app and REST endpoints
├── webui/                       # Static SPA (HTML, JS, CSS)
├── docs/
│   └── orchestration_playbook.md# Scaling and ingestion strategies
├── data/                        # Sample CSVs and ticker lists
├── cache/                       # Populated at runtime; safe to delete
└── tests/
    ├── test_analytics.py
    ├── test_analytics_engine.py
    ├── test_cli_tables.py
    ├── test_data_ingestion.py
    └── test_database.py
```

## File reference

### Root scripts and helpers
| File | Description |
|------|-------------|
| `main.py` | Rich CLI wrapper that exposes table/metrics commands, metric abbreviations, and scenario helpers for power users. |
| `run_chatbot.py` | Lightweight REPL entry point that spins up `BenchmarkOSChatbot.create()` for interactive terminal chats. |
| `serve_chatbot.py` | Convenience launcher for the FastAPI app in `src/benchmarkos_chatbot/web.py`; hands arguments to `uvicorn`. |
| `batch_ingest.py` | Pulls a built-in mega-cap watch list through `ingest_live_tickers`, applying retry/backoff and basic rate limiting. |
| `ingest_universe.py` | Parameterised batch ingester with resume support; calls `AnalyticsEngine` to refresh snapshots after each chunk. |
| `ingest_frames.py` | Synchronously downloads SEC data frames for a fixed set of tags and writes them to Postgres for benchmarking. |
| `load_prices_stooq.py` | Imports historical price data from Stooq into Postgres, providing a fallback when Yahoo limits are hit. |
| `requirements.txt` | Runtime dependency pinning for local development and deployment targets. |
| `pyproject.toml` | Project metadata, dependency list, and pytest configuration (adds `src/` to `PYTHONPATH`). |

### Core package: `src/benchmarkos_chatbot/`
| Module | Description |
|--------|-------------|
| `__init__.py` | Exports `BenchmarkOSChatbot`, `AnalyticsEngine`, and `load_settings` for easy imports. |
| `analytics_engine.py` | Central analytics hub: loads fundamentals, computes base/derived/aggregate metrics, runs scenarios, and refreshes quote snapshots. |
| `chatbot.py` | Orchestrates intent parsing, command routing, ingestion triggers, and LLM fallbacks for the conversational interface. |
| `config.py` | Loads environment variables into the immutable `Settings` dataclass and exposes helper properties for SQLite/Postgres DSNs. |
| `data_ingestion.py` | Coordinates live SEC/Yahoo/Bloomberg ingestion, returns `IngestionReport` summaries, and records audit events. |
| `data_sources.py` | HTTP clients and DTOs for SEC EDGAR, Yahoo Finance, and Bloomberg integrations (caching, retry, normalisation). |
| `database.py` | SQLite persistence layer: schema creation, dataclasses for stored records, and CRUD helpers for conversations, metrics, facts, and audit logs. |
| `llm_client.py` | Language-model abstraction with a deterministic local echo client and an OpenAI-backed implementation. |
| `table_renderer.py` | Utilities for producing consistent ASCII tables used by CLI commands and automated tests. |
| `tasks.py` | Optional in-process task queue abstraction for scheduling ingestion/background jobs safely. |
| `ticker_universe.py` | Loader utilities for predefined ticker universes consumed by ingestion scripts. |
| `web.py` | FastAPI application exposing chat, metrics, facts, audit, and health endpoints; mounts the SPA assets. |
| `static/` | Packaged static assets served when the project-level `webui/` folder is absent. |

### Documentation and data
| Path | Description |
|------|-------------|
| `docs/orchestration_playbook.md` | Strategy note outlining three ingestion/orchestration patterns (local queue, serverless, batch). |
| `data/` | Sample CSV inputs and ticker lists used by ingestion scripts and tests. |
| `cache/` | Runtime artifact directory for downloaded filings and ingestion progress (created automatically). |
| `docs/ticker_names.md` | Full coverage universe listing each supported company name alongside its ticker. |

### Web client
| Path | Description |
|------|-------------|
| `webui/index.html` | Shell HTML document that boots the single-page app and loads API base overrides when provided. |
| `webui/app.js` | Front-end controller handling chat submission, conversation history rendering, table formatting, and status polling. |
| `webui/styles.css` | Styling for the SPA, including responsive layout, message bubbles, and status indicators. |

### Tests
| File | Description |
|------|-------------|
| `tests/test_database.py` | Verifies schema invariants and CRUD helpers in `database.py`. |
| `tests/test_analytics_engine.py` | Exercises growth, valuation metrics, and quote refresh behaviours. |
| `tests/test_analytics.py` | End-to-end chatbot scenarios covering prompts, ingestion triggers, and responses. |
| `tests/test_cli_tables.py` | Ensures the ASCII table renderer formats rows/columns as expected. |
| `tests/test_data_ingestion.py` | Validates ingestion workflows, audit event recording, and error handling. |

### Quick module guide
| Goal | Primary file(s) | Notes |
|------|-----------------|-------|
| Investigate how prompts become analytics plans | `src/benchmarkos_chatbot/chatbot.py`, `src/benchmarkos_chatbot/analytics_engine.py` | Intent handlers decide whether to run metrics, scenarios, or ingestion, then hand structured plans to the analytics engine. |
| Add or tweak financial metrics | `src/benchmarkos_chatbot/analytics_engine.py`, `src/benchmarkos_chatbot/database.py` | Metrics are computed in `refresh_metrics`; persisted snapshots live in `database.py` so downstream clients pick them up automatically. |
| Tune data ingestion or add new feeds | `src/benchmarkos_chatbot/data_ingestion.py`, `data_sources.py`, `data_sources_backup.py` | These modules manage SEC, Yahoo, and optional Bloomberg inputs with retry/backoff logic. |
| Extend the FastAPI surface | `src/benchmarkos_chatbot/web.py` | All REST endpoints (chat, metrics, facts, audit) are defined here; mount new routes alongside the existing routers. |
| Adjust the task queue / background jobs | `src/benchmarkos_chatbot/tasks.py` | Provides a lightweight in-process queue for long-running ingestion jobs. |
| Update the SPA chat client | `webui/app.js`, `webui/styles.css`, `webui/index.html` | Client-side prompt submission, transcript rendering, and status badges live here. |

### Script cheat sheet
- `run_chatbot.py` — launch the terminal REPL for quick experiments (uses the same backend as the web UI).
- `serve_chatbot.py` — run the FastAPI app with uvicorn; pass `--port` or `--reload` while iterating locally.
- `ingest_universe.py` — crawl a configurable ticker universe with checkpointing; ideal for keeping demo datasets fresh.
- `ingest_companyfacts.py` / `ingest_companyfacts_batch.py` — fetch SEC companyfacts for individual CIKs or large batches.
- `ingest_frames.py` — pull SEC XBRL frame data (useful for macro-style aggregates such as industry totals).
- `load_prices_stooq.py` – backfill historical prices when Yahoo rate limits hit or offline operation is required.
- `load_prices_yfinance.py` – grab the latest close/volume from Yahoo Finance and seed the SQLite cache (and Postgres, when configured) so price-based ratios populate.
- `load_ticker_cik.py` – populate the ticker → CIK lookup table; rerun whenever SEC publishes new mappings.
- `batch_ingest.py` – example of orchestrating a curated watch list with retry/backoff, suitable for cron jobs.
- `docs/ticker_names.md` – generated companion file enumerating the current coverage universe (see section below for how it is produced).

### Price data refresh in practice
Use this workflow to keep price-driven ratios (P/E, EV/EBITDA, dividend yield, TSR, buyback intensity) current without rerunning the full SEC ingestion:

```powershell
pip install yfinance                         # one-time dependency
$env:SEC_TICKERS = (Get-Content tickers.txt) -join ','
# Optional: seed Postgres as well
$env:PGHOST='127.0.0.1'; $env:PGPORT='5432'
$env:PGDATABASE='secdb'; $env:PGUSER='postgres'; $env:PGPASSWORD='hania123'
python load_prices_yfinance.py               # writes to SQLite and Postgres

$env:PYTHONPATH = (Resolve-Path .\src).Path
python -c "from benchmarkos_chatbot.config import load_settings; \
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine; \
AnalyticsEngine(load_settings()).refresh_metrics(force=True)"
```

Finish by restarting `serve_chatbot.py` so the web UI picks up the refreshed metrics.

### Coverage universe

The chatbot is preloaded with the latest S&P 500 style universe (482 tickers at generation time). A machine-generated appendix with all company names is available in [`docs/ticker_names.md`](docs/ticker_names.md). Regenerate it at any time with:

```powershell
$env:SEC_TICKERS = (Get-Content tickers.txt) -join ','
python - <<'PY'
import os
from pathlib import Path
import yfinance as yf

root = Path(__file__).resolve().parent
tickers = [line.strip() for line in (root / "tickers.txt").read_text().splitlines() if line.strip()]
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

This appendix keeps the README concise while still documenting every supported company for compliance and comms stakeholders.

### Configuration crib sheet
| File | Purpose |
|------|---------|
| `.env` | Local development defaults; mirrors the keys loaded in `config.py` (DB paths, API providers, feature flags). |
| `pyproject.toml` | Python packaging metadata plus tooling config (`pytest`, `ruff`/formatters if added later). |
| `.env.example` | Safe template you can share with collaborators; copy to `.env` and fill in secrets locally. |
| `docs/orchestration_playbook.md` | Design notes for scaling ingestion/orchestration patterns beyond the single-process defaults. |


## Quality and testing
- **Run the whole suite**: `pytest`
- **Focus on a file**: `pytest tests/test_cli_tables.py::test_table_command_formats_rows`
- **Manual sanity**: use the local echo model (`LLM_PROVIDER=local`) before burning OpenAI credits.
- **Database resets**: remove `benchmarkos_chatbot.sqlite3` and rerun ingestion; schema migrations happen automatically on startup.

CI/CD is not bundled, but `pytest -ra` (configured in `pyproject.toml`) surfaces skipped and xfail tests clearly. Consider integrating `ruff` or `black` if you standardise formatting.

## Troubleshooting
- **`OpenAI API key not found`** - set `OPENAI_API_KEY`, store it via `keyring`, or create `~/.config/benchmarkos-chatbot/openai_api_key`.
- **`WinError 10048` when starting the server** - another process is bound to the port. Run `Get-NetTCPConnection -LocalPort 8000` and terminate the offender or pass `--port 8001`.
- **Yahoo Finance 429 errors** - lower `YAHOO_QUOTE_BATCH_SIZE`, add sleeps between ingestion runs, or temporarily fall back to `load_prices_stooq.py`.
- **PostgreSQL auth failures** - confirm SSL and network rules, then verify `POSTGRES_*` variables. The DSN is logged at debug level when `DATABASE_TYPE=postgresql`.
- **Pytest cannot locate modules** - run commands from the project root so the `pythonpath = ["src", "."]` setting in `pyproject.toml` applies.

## Further reading
- `docs/orchestration_playbook.md` - three orchestration patterns (local queue, serverless fetchers, batch scripts) with wiring notes into `BenchmarkOSChatbot`.
- Inline module docs throughout `src/benchmarkos_chatbot/` explain invariants, data contracts, and extension hooks.
- Consider versioning your `.env` defaults and deployment runbooks under `docs/` as the project evolves.

Happy building!
