# BenchmarkOS Chatbot Platform

BenchmarkOS is an institutional-grade copilot for finance teams. It pairs deterministic market analytics with a conversational interface so analysts can ask natural-language questions, inspect lineage, and keep data pipelines auditable.

---

## Practicum context
This repository underpins our Fall 2025 DNSC 6317 practicum at The George Washington University, where we are building and governing an explainable finance copilot that can support regulated teams. Our objectives include stress-testing BenchmarkOS against real analyst workflows, documenting orchestration strategies for enterprise rollouts, and demonstrating responsible AI guardrails around data access, lineage, and scenario planning.

### Team
- Hania A.
- Van Nhi Vuong
- Malcolm Muoriyarwa
- Devarsh Patel
- Supervising faculty: Professor Patrick Hall (The George Washington University)

### Project focus
- Translate classroom techniques into a production-grade analytics assistant that blends deterministic KPI calculations with auditable LLM experiences.
- Stand up KPI coverage pipelines that stay resilient when market data lags or filing assumptions drift.
- Deliver practitioner-ready documentation, including deployment runbooks and testing strategies, so stakeholders can re-create the practicum outcomes after the semester concludes.

### User story and pain points
Picture a Monday 8 a.m. stand-up in GW's practicum lab. Hania, acting as the analytics lead at a mid-sized asset manager, receives an urgent request from Van Nhi, who plays the portfolio strategist responsible for deciding which industrial names to overweight this quarter. Malcolm, the risk officer, wants to confirm that every metric driving the recommendation can be traced back to a filing or price feed, while Devarsh, modeling the compliance analyst, needs evidence that no unvetted prompt will expose sensitive data. Before BenchmarkOS, the team burned hours stitching CSVs from EDGAR, refreshing brittle spreadsheets, and copy-pasting numbers into chat threads-introducing latency, version drift, and audit nightmares. With the chatbot, they ask "Compare RTX and LMT revenue trajectories post-2022" and receive deterministic KPIs, lineage breadcrumbs, and warnings when data freshness slips. The story mirrors the real stakeholders we observed during practicum interviews: analysts juggling multiple tickers, risk partners demanding reproducibility, and compliance leaders seeking transparent guardrails. BenchmarkOS exists to calm that Monday chaos by fusing reliable data pipelines with an explainable conversational layer.

| Main group                               | Sub-group                | Role / examples                                   | Goals when using chatbot                                                                 | Current pain points                                                                                   | Key needs from chatbot                                                                                 |
|------------------------------------------|--------------------------|---------------------------------------------------|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Financial industry (professional users)  | CFO / FP&A / IR          | CFOs, finance directors, investor relations leads | Generate peer comparisons in minutes; ensure KPI standardisation and source traceability  | Data collection and reconciliation takes 3–5 days; KPI definitions drift; no audit trail for the board | Peer packets in under five minutes; standardised KPI dictionary with lineage; export-ready reports     |
|                                          | Corporate development / M&A teams | Corporate development, strategy, M&A analysts      | Benchmark targets quickly for acquisitions; compare competitors by segment and geography  | Manual benchmarking is slow; limited ability to expand peer sets                                       | Dynamic peer set management; audit trail per KPI; override controls for peers, KPIs, and timeframes    |
|                                          | Consulting and advisory  | Consulting analysts, advisory teams                | Deliver rapid, credible benchmarks; produce slide-ready, verifiable outputs               | Data gathering and normalisation are time-consuming; clients question credibility without lineage      | KPI metrics with click-through lineage; segment normalisation; multi-dimensional benchmarking          |
| Non-financial users (non-professional)   | Business decision makers | CEOs, COOs, heads of strategy                     | See competitor and market context without deep finance expertise; decide quickly          | Financial data feels complex; no time to compute KPIs; reports lack actionable insights                | Strategic summaries tied to KPIs; clear visuals; action-oriented insights                              |
|                                          | Students and learners    | Students, researchers, MBA learners               | Learn to read 10-K/10-Q filings; understand KPI calculations                              | Unsure how to compute KPIs; do not know reliable data sources                                          | Step-by-step KPI explanations; guided drill-down from KPI to tables to source filings                  |
| Semi-professional users                  | Investors and analysts   | Buy-side and sell-side analysts, individual investors | Make faster investment calls with peer benchmarks                                          | Hard to compare multiple companies quickly; limited reliable data sources                              | Dynamic peer comparisons by ticker; exportable reports; transparent source traceability                |

---

## Table of contents
- [Practicum context](#practicum-context)
- [Overview](#overview)
- [Core capabilities](#core-capabilities)
- [Architecture map](#architecture-map)
- [Retrieval & ML internals](#retrieval--ml-internals)
- [Quick start](#quick-start)
- [Running the chatbot](#running-the-chatbot)
- [Data ingestion playbooks](#data-ingestion-playbooks)
- [Ingest and quote loading (English quick guide)](#ingest-and-quote-loading-english-quick-guide)
- [Configuration reference](#configuration-reference)
- [Database schema](#database-schema)
- [Project layout](#project-layout)
- [File reference](#file-reference)
- [Quality and testing](#quality-and-testing)
- [Troubleshooting](#troubleshooting)
- [Further reading](#further-reading)

---

## Overview
BenchmarkOS ships as a batteries-included template for building finance copilots. Out of the box you gain:

- **Durable storage** (SQLite by default, PostgreSQL optional) for conversations, facts, metrics, audit trails, and scenarios.
- **Analytics engines** that normalise SEC filings, hydrate them with market quotes, and expose tabular as well as scenario-ready metrics.
- **Flexible LLM integration** with a deterministic echo model for testing or OpenAI for production deployments.
- **Multi-channel experiences** (CLI REPL, FastAPI REST service, single-page web UI) so you can prototype quickly and scale later.
- **Rich documentation** (`docs/orchestration_playbook.md`) that explains how to scale “any company” requests and replicate the workflows in production.

---

## Core capabilities
- **Multi-channel chat** – `run_chatbot.py` offers a REPL, `serve_chatbot.py` (or `uvicorn`) exposes REST endpoints, and `webui/` renders a browser client complete with live status indicators.
- **Deterministic analytics** – `AnalyticsEngine` calculates primary/secondary metrics, growth rates, valuation multiples, and derived KPIs from the latest filings and quotes.
- **Incremental ingestion** – `data_ingestion.py` and helper scripts pull SEC EDGAR facts, Yahoo quotes, and optional Bloomberg feeds with retry/backoff.
- **Audit-ready storage** – `database.py` writes metric snapshots, raw financial facts, audit events, and full chat history for compliance reviews.
- **Extensible LLM layer** – toggle between the local echo model and OpenAI via `LLM_PROVIDER`, or extend `llm_client.py` for other vendors.
- **Task orchestration hooks** – `tasks.py` provides a queue abstraction you can plug into ingestion or long-running commands.

---

## Architecture map
See [`docs/architecture.md`](docs/architecture.md) for the component diagram. The latest revision includes the structured parsing pipeline (`alias_builder.py`, `parse.py`, `time_grammar.py`) and the retrieval layer that feeds grounded artefacts into the LLM alongside the existing CLI, FastAPI, analytics, and ingestion components.

---

## Retrieval & ML internals
BenchmarkOS combines deterministic data prep with retrieval-augmented generation (RAG) so every answer traces back to persisted facts.

1. **Natural-language parsing (deterministic)**  
   - `src/benchmarkos_chatbot/parsing/alias_builder.py` loads a generated `aliases.json` covering the S&P 500. It normalises free-text mentions, resolves ticker aliases, applies manual overrides (Alphabet, Berkshire share classes, JP Morgan, AT&T), and when needed performs a fuzzy fallback and emits warnings.  
   - `parse_to_structured` in `parsing/parse.py` orchestrates alias resolution, metric synonym detection, and the flexible time grammar (`time_grammar.py`). It returns a strict JSON intent schema that downstream planners consume and store (`conversation.last_structured_response["parser"]`).

2. **Retrieval layer (RAG)**  
   - Structured intents route directly into `AnalyticsEngine`, which reads metric snapshots, KPI overrides, and fact tables from SQLite/Postgres.  
   - Retrieved artefacts (tables, benchmark comparisons, audit trails) become RAG “system” messages that condition the LLM, ensuring no fabricated values slip through.

3. **Generation / machine learning**  
   - `llm_client.py` abstracts provider selection (local echo vs. OpenAI). The model verbalises retrieved metrics, summarises trends, and surfaces parser warnings.  
   - Scenario and benchmarking flows blend deterministic calculations (growth rates, spreads) with LLM narration, preserving numeric accuracy while keeping explanations natural.

4. **Tooling & coverage**  
   - Regenerate the alias universe with:  
     ```bash
     export PYTHONPATH=./src
     python scripts/generate_aliases.py
     ```  
     The script reads `data/tickers/universe_sp500.txt`, applies the same normalisation rules as runtime, and rewrites `aliases.json` with coverage stats.  
   - Guardrails live in `tests/test_alias_resolution.py`, `tests/test_time_grammar.py`, and `tests/test_nl_parser.py`, ensuring alias coverage, period parsing, and structured intents stay within spec.

---

## Quick start
These steps assume Python 3.10+ and Git are installed.

### 1. Clone and set up the virtual environment
```bash
git clone https://github.com/haniae/Project.git
cd Project
python -m venv .venv
# PowerShell
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env   # PowerShell
# cp .env.example .env        # macOS/Linux
```

### 2. Configure environment defaults
Open `.env` and update database paths, API keys, and provider toggles. Prefer not to store an OpenAI key in the repo? Put it in `~/.config/benchmarkos-chatbot/openai_api_key` and the loader will pick it up automatically.

### 3. (Optional) Warm the datastore
SQLite tables are created lazily, but you can preload metrics with:
```bash
python scripts/ingestion/ingest_universe.py --years 5 --chunk-size 25 --sleep 2 --resume
```
This pulls the sample watch list, respects SEC rate limits, and writes audit events.

---

## Running the chatbot
### CLI REPL
```bash
python run_chatbot.py
```
Inside the prompt, type `help` to see available commands. Common examples:

| Command | Example | What it does |
|---------|---------|--------------|
| `metrics` | `metrics AAPL 2022-2024` | Latest and historical KPI block for one ticker. |
| `compare` | `compare MSFT NVDA 2023` | Side-by-side metrics table. |
| `table` | `table TSLA metrics revenue net_income` | Renders a low-level ASCII table (useful in tests). |
| `fact` | `fact AMZN 2023 revenue` | Inspect a normalised financial fact. |
| `scenario` | `scenario GOOGL bull rev=+8% mult=+0.5` | Run a what-if scenario with metric deltas. |
| `ingest` | `ingest SHOP 5` | Trigger live ingestion (SEC, Yahoo, optional Bloomberg). |

Comparison responses append an “S&P 500 Avg” column highlighting how each ticker stacks up on margins, ROE, and valuation multiples.

### FastAPI + SPA
```bash
python serve_chatbot.py --port 8000
# or run the ASGI app directly
uvicorn benchmarkos_chatbot.web:app --reload --port 8000
```
Navigate to `http://localhost:8000`. The SPA exposes:
- Real-time request timeline (intent, cache, context, compose) with slow-step hints.
- Export shortcuts (CSV, PDF) and in-line benchmarks.
- Settings panel to toggle data sources, timeline detail, and export defaults.

#### CFI dashboards (Compare, Classic, Dense)
- The web UI now launches straight into the **CFI Compare** experience powered by `/api/dashboard/cfi-compare`, showing multi-company KPIs, trend charts, valuation football fields, and a peer scatter map.
- Need to flip layouts during QA? Run `showCfiDashboard()`, `showCfiCompareDashboard()`, or `showCfiDenseDashboard()` in the browser console to jump between the classic single-company view, the new compare grid, and the dense summary.
- For stand-alone demos or embedding, open `webui/cfi_compare_standalone.html` directly. It fetches live data when the server is running and gracefully falls back to the baked-in demo payload when offline.

### REST endpoints
| Method | Route | Purpose |
|--------|-------|---------|
| `POST` | `/chat` | Submit a prompt. Returns `reply`, `conversation_id`, structured artefacts, and progress events. |
| `GET`  | `/metrics` | Retrieve numeric metrics for one or more tickers (`start_year` / `end_year` filters supported). |
| `GET`  | `/facts` | Fetch normalised financial facts backing the numbers. |
| `GET`  | `/audit` | View the latest ingestion/audit events for a ticker. |
| `GET`  | `/health` | Basic readiness/liveness check for load balancers. |

The `/chat` response includes structured extras (`highlights`, `trends`, `comparison_table`, `citations`, `exports`, `conclusion`) so downstream integrations can reuse the analytics without re-parsing text.

---

## Data ingestion playbooks
### On-demand
`AnalyticsEngine.get_metrics` calls `ingest_live_tickers` when it detects missing coverage. You can route this through `tasks.TaskManager` to queue and monitor ingestion jobs—see inline docstrings for patterns.

### Batch scripts
| Script | When to use it | Example |
|--------|----------------|---------|
| `scripts/ingestion/ingest_universe.py` | Refresh a watch list with resume support and polite rate limiting. | `python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2 --resume` |
| `scripts/ingestion/batch_ingest.py` | Pull the built-in mega-cap list through `ingest_live_tickers` with retry/backoff. | `python scripts/ingestion/batch_ingest.py` |
| `scripts/ingestion/ingest_companyfacts.py` | Mirror SEC companyfacts into Postgres (configure `SEC_TICKERS` and `PG*` env vars). | `SEC_TICKERS=MSFT,AAPL PGHOST=localhost python scripts/ingestion/ingest_companyfacts.py` |
| `scripts/ingestion/ingest_frames.py` | Download SEC data frames for benchmarking in Postgres. | `SEC_TICKERS=MSFT,AAPL python scripts/ingestion/ingest_frames.py` |
| `scripts/ingestion/load_prices_stooq.py` | Backfill prices from Stooq when Yahoo throttles. | `SEC_TICKERS=MSFT,AAPL python scripts/ingestion/load_prices_stooq.py` |

All scripts honour the configuration from `load_settings()` and write audit events so the chatbot can justify sourcing decisions.

### Price-refresh workflow
Use this to keep price-driven ratios current without re-ingesting everything:
```powershell
pip install yfinance  # one-time
$env:SEC_TICKERS = (Get-Content data/tickers/universe_sp500.txt) -join ','
# Optional Postgres target
$env:PGHOST='127.0.0.1'; $env:PGPORT='5432'
$env:PGDATABASE='secdb'; $env:PGUSER='postgres'; $env:PGPASSWORD='hania123'
python scripts/ingestion/load_prices_yfinance.py

$env:PYTHONPATH = (Resolve-Path .\src).Path
python - <<'PY'
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
AnalyticsEngine(load_settings()).refresh_metrics(force=True)
PY
```
Restart `serve_chatbot.py` afterwards so the SPA sees the refreshed metrics.

---

## Ingest and quote loading (English quick guide)

### Prerequisites
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
SQLite path defaults to `data/sqlite/benchmarkos_chatbot.sqlite3` (configurable via `DATABASE_PATH`).

Pick one of the following forms (both equivalent if you ran `pip install -e .`).
- Module form:
```bash
python -m scripts.ingestion.ingest_universe --universe sp500 --years 10 --chunk-size 25 --sleep 2
```
- Script path form:
```bash
python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2
```

Notes:
- `--years 10` pulls the most recent 10 fiscal years (cutoff = current_year - years + 1).
- The job uses a progress file `.ingestion_progress.json` so re-runs can `--resume` where they left off.
- If you see "Nothing to do" but the DB is empty, delete the progress file and re-run:
```bash
rm -f .ingestion_progress.json
```

Verify counts:
```bash
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
```bash
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
```bash
python - <<'PY'
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
AnalyticsEngine(load_settings()).refresh_metrics(force=True)
print('Refreshed metric_snapshots.')
PY
```

Check the latest quote timestamp:
```bash
python - <<'PY'
import sqlite3
con=sqlite3.connect('data/sqlite/benchmarkos_chatbot.sqlite3')
print('quotes=',con.execute('select count(*) from market_quotes').fetchone()[0])
print('latest=',con.execute('select max(quote_time) from market_quotes').fetchone()[0])
PY
```

### Windows notes (PowerShell)
- Activate: ` .\\.venv\\Scripts\\Activate.ps1`
- Use the script path variant if `python -m` complains about imports:
```powershell
python scripts/ingestion/ingest_universe.py --universe sp500 --years 10 --chunk-size 25 --sleep 2
```
- If you see `ModuleNotFoundError: benchmarkos_chatbot`, ensure you ran `pip install -e .` or set:
```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

### Common issues
- "Nothing to do" with `--resume`: delete `.ingestion_progress.json` and re-run.
- Yahoo 429: reduce batch size (env `YAHOO_QUOTE_BATCH_SIZE`) and add small sleeps; retry.
- DB path: override with `DATABASE_PATH` if you don’t want the default under `data/sqlite/`.

---
### Coverage universe
`docs/ticker_names.md` lists every tracked company (482 tickers at generation time). Regenerate it—and keep the parser aligned—whenever the universe changes:
```powershell
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

---

## Configuration reference
`load_settings()` reads environment variables (or `.env`) and provides sensible defaults.

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_TYPE` | `sqlite` | Switch to `postgresql` for shared deployments. |
| `DATABASE_PATH` | `./data/sqlite/benchmarkos_chatbot.sqlite3` | SQLite file location; created automatically. |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | unset | Required when `DATABASE_TYPE=postgresql`; `POSTGRES_SCHEMA` overrides the default `sec`. |
| `LLM_PROVIDER` | `local` | `local` uses the deterministic echo model; set to `openai` for real completions. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Passed verbatim to the OpenAI Chat Completions API. |
| `SEC_API_USER_AGENT` | `BenchmarkOSBot/1.0 (support@benchmarkos.com)` | Mandatory for SEC EDGAR requests. Customize it for your org. |
| `EDGAR_BASE_URL` | `https://data.sec.gov` | Override if you proxy or mirror EDGAR. |
| `YAHOO_QUOTE_URL` | `https://query1.finance.yahoo.com/v7/finance/quote` | Used to refresh quotes. |
| `YAHOO_QUOTE_BATCH_SIZE` | `50` | Maximum tickers per Yahoo batch. |
| `HTTP_REQUEST_TIMEOUT` | `30` | Seconds before HTTP clients give up. |
| `INGESTION_MAX_WORKERS` | `8` | Thread pool size for ingestion routines. |
| `DATA_CACHE_DIR` | `./cache` | Stores downloaded filings, facts, and progress markers. |
| `ENABLE_BLOOMBERG` | `false` | Toggle Bloomberg ingestion; requires host/port/timeout values. |
| `BLOOMBERG_HOST`, `BLOOMBERG_PORT`, `BLOOMBERG_TIMEOUT` | unset | Only used if Bloomberg is enabled. |
| `OPENAI_API_KEY` | unset | Looked up in env, then keyring, then `~/.config/benchmarkos-chatbot/openai_api_key`. |

Secrets belong in your local `.env`. Windows developers can rely on `keyring` so API keys live outside the repo.

---

## Database schema
BenchmarkOS intentionally supports two storage backends, but your deployment uses **only one** at a time—by default it’s SQLite:

1. **SQLite (default / implied in this repo)** – shipping the database as a file keeps setup frictionless for development, tests, and CI. All conversations, metrics, and audit events live in the path defined by `DATABASE_PATH`. For this reason, the stock `.env` (and most tests such as `test_ingestion_perf.py`) run purely on SQLite. It was chosen because it “just works”: no external server to provision, a trivial backup story, and fast enough for single-user workflows. PRAGMAs (`WAL`, `synchronous=NORMAL`, `temp_store=MEMORY`, `cache_size=-16000`) are applied automatically so sustained writes remain smooth.
2. **PostgreSQL (optional)** – the same helper module can target Postgres when you set `DATABASE_TYPE=postgresql` and supply the `POSTGRES_*` DSN variables. Teams switch to Postgres when chat sessions are shared across analysts, when concurrency or replication matters, or when governance requires managed backups. If you haven’t changed those settings, Postgres is unused.

In other words, you are currently using a single database—SQLite—because it was selected for simplicity and portability. The PostgreSQL path is documented for teams that choose to run BenchmarkOS in a multi-user/shared environment later.

Regardless of backend, both share the same schema:

Key tables:

| Table | Purpose | Notable columns |
|-------|---------|-----------------|
| `conversations` | Stores chat turns for resumable threads. | `conversation_id`, `role`, `content`, `created_at` |
| `cached_prompts` | Deduplicates prompts so identical requests reuse cached replies. | `prompt_hash`, `payload`, `created_at`, `reply` |
| `metric_snapshots` | Persisted analytics snapshot consumed by the chatbot/UI. | `ticker`, `metric`, `period`, `value`, `start_year`, `end_year`, `updated_at`, `source` |
| `company_filings` | Metadata for SEC filings pulled during ingestion. | `ticker`, `accession_number`, `form_type`, `filed_at`, `data` |
| `financial_facts` | Normalised SEC fact rows (revenues, margins, etc.). | `ticker`, `metric`, `fiscal_year`, `period`, `value`, `unit`, `source_filing`, `raw` |
| `market_quotes` | Latest quotes from Yahoo/Bloomberg/Stooq loaders. | `ticker`, `price`, `currency`, `timestamp`, `source` |
| `kpi_values` | KPI backfill overrides that smooth derived metrics. | `ticker`, `fiscal_year`, `fiscal_quarter`, `metric_id`, `value`, `method`, `warning` |
| `audit_events` | Traceability for ingestion and scenario runs. | `ticker`, `event_type`, `entity_id`, `details`, `created_at` |
| `ticker_aliases` | Maps tickers to CIK/company names to speed ingestion. | `ticker`, `cik`, `company_name`, `updated_at` |

On startup `database.initialise()` applies schema migrations idempotently. When running in SQLite mode the PRAGMAs mentioned above are applied automatically; switching to Postgres only requires setting the DSN variables—the rest of the code paths remain identical.

---

## Project layout
```
Project/
├── README.md
├── pyproject.toml
├── requirements.txt
├── run_chatbot.py
├── serve_chatbot.py
├── scripts/
│   ├── generate_aliases.py
│   ├── ingestion/
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
│       ├── chat_metrics.py
│       ├── data_sources_backup.py
│       └── main.py
├── src/
│   └── benchmarkos_chatbot/
│       ├── analytics_engine.py
│       ├── chatbot.py
│       ├── config.py
│       ├── data_ingestion.py
│       ├── data_sources.py
│       ├── database.py
│       ├── parsing/
│       │   ├── alias_builder.py
│       │   ├── aliases.json
│       │   ├── ontology.py
│       │   ├── parse.py
│       │   └── time_grammar.py
│       ├── llm_client.py
│       ├── table_renderer.py
│       ├── tasks.py
│       └── web.py
├── docs/
│   ├── orchestration_playbook.md
│   └── ticker_names.md
├── data/
│   ├── sample_financials.csv
│   ├── sqlite/benchmarkos_chatbot.sqlite3 (created on demand)
│   └── tickers/
│       ├── universe_sp500.txt
│       ├── sec_top100.txt
│       └── sample_watchlist.txt
├── cache/            # generated at runtime
├── webui/
└── tests/
    ├── test_alias_resolution.py
    ├── test_analytics.py
    ├── test_analytics_engine.py
    ├── test_cli_tables.py
    ├── test_data_ingestion.py
    ├── test_database.py
    ├── test_ingestion_perf.py
    ├── test_kpi_backfill.py
    ├── test_nl_parser.py
    └── test_time_grammar.py
```

---

## File reference

### Root scripts & helpers
| File | Description |
|------|-------------|
| `scripts/utility/main.py` | Rich CLI wrapper exposing metrics/table commands, abbreviations, and scenario helpers. |
| `run_chatbot.py` | Lightweight REPL entry point that calls `BenchmarkOSChatbot.create()`. |
| `serve_chatbot.py` | Convenience launcher for the FastAPI app (`src/benchmarkos_chatbot/web.py`). |
| `scripts/ingestion/batch_ingest.py` | Loads the curated watch list with retry/backoff. |
| `scripts/ingestion/ingest_universe.py` | Batch ingester with resume support; refreshes metrics after each chunk. |
| `scripts/ingestion/ingest_frames.py` | Downloads SEC data frames into Postgres for benchmarking. |
| `scripts/ingestion/load_prices_stooq.py` | Imports Stooq prices as a fallback when Yahoo throttles. |
| `scripts/generate_aliases.py` | Regenerates the S&P 500 alias universe (`aliases.json`). |
| `requirements.txt` | Runtime dependency lockfile. |
| `pyproject.toml` | Project metadata, dependencies, and pytest configuration (adds `src/` to `PYTHONPATH`). |

### Parsing & retrieval components
| File | Description |
|------|-------------|
| `parsing/alias_builder.py` | Normalises company mentions, loads alias sets, applies overrides, and resolves tickers with fuzzy fallbacks. |
| `parsing/aliases.json` | Generated alias universe consumed at runtime. |
| `parsing/parse.py` | Converts prompts into structured intents (tickers, metrics, periods, warnings). |
| `parsing/time_grammar.py` | Flexible period parser covering fiscal/calendar ranges, lists, quarters, and relative windows. |

### Parser-focused tests
| File | Description |
|------|-------------|
| `tests/test_alias_resolution.py` | Validates alias coverage, manual overrides, fuzzy warnings, and ordering. |
| `tests/test_time_grammar.py` | Ensures the time grammar handles ranges, lists, quarter formats, and two-digit years. |
| `tests/test_nl_parser.py` | End-to-end structured intent checks for compare/trend prompts and parser warnings. |

### Web assets
| Path | Description |
|------|-------------|
| `webui/app.js` | SPA logic, progress timeline updates, settings panel, and chat interactions. |
| `webui/styles.css` | Styling for the SPA (dark/light friendly, timeline badges, typography). |
| `webui/static/data/*.json` | Precompiled KPI library and company universe metadata. |

---

## Quality and testing
- **Run the suite**: `pytest`
- **Parser & alias focus**: `pytest tests/test_alias_resolution.py tests/test_time_grammar.py tests/test_nl_parser.py`
- **Target a single test**: `pytest tests/test_cli_tables.py::test_table_command_formats_rows`
- **Manual sanity**: point `LLM_PROVIDER=local` to avoid burning API credits during smoke tests.
- **Database reset**: delete `benchmarkos_chatbot.sqlite3` and rerun ingestion—migrations run automatically on startup.

CI isn’t configured by default, but `pytest -ra` (preconfigured in `pyproject.toml`) surfaces skipped/xfail tests neatly. Consider adding `ruff` or `black` once your team standardises formatting.

---

## Troubleshooting
- **“OpenAI API key not found”** – set `OPENAI_API_KEY`, store it via `keyring`, or create `~/.config/benchmarkos-chatbot/openai_api_key`.
- **`WinError 10048` when starting the server** – another process is on the port. Run `Get-NetTCPConnection -LocalPort 8000` and terminate it, or start with `--port 8001`.
- **Yahoo Finance 429 errors** – lower `YAHOO_QUOTE_BATCH_SIZE`, add delays between runs, or temporarily use `scripts/ingestion/load_prices_stooq.py`.
- **PostgreSQL auth failures** – confirm SSL/network settings, then double-check `POSTGRES_*` vars; the DSN is logged at debug level when `DATABASE_TYPE=postgresql` is active.
- **Pytest cannot locate modules** – run from the repo root so the `pythonpath = ["src", "."]` entry in `pyproject.toml` kicks in.

---

## Further reading
- `docs/orchestration_playbook.md` – outlines three ingestion/orchestration patterns (local queue, serverless fetchers, batch jobs) and how to wire them into `BenchmarkOSChatbot`.
- Inline module docs across `src/benchmarkos_chatbot/` describe invariants, data contracts, and extension hooks.
- Consider versioning your `.env` templates and deployment runbooks alongside these docs as the project evolves.

Happy building! 👋
