# BenchmarkOS Chatbot Platform

BenchmarkOS is an institutional-grade finance copilot. It blends deterministic market analytics with retrieval-augmented generation (RAG) so analysts can interrogate data in natural language, trace lineage, and export audit-ready reports.

---

## 1. Architecture at a Glance

| Layer | Key modules | Responsibilities |
|-------|-------------|------------------|
| Experiences | `webui/`, `run_chatbot.py`, `serve_chatbot.py` | Browser dashboard, CLI REPL, and FastAPI service for integrations. |
| Natural-language parsing | `src/benchmarkos_chatbot/parsing/alias_builder.py`, `time_grammar.py` | Normalises noisy company names (`"Gooogle"`, `"JP Morgan"`) and flexible periods (`FY-24`, `fiscal 2015-2018`). |
| Retrieval & analytics | `src/benchmarkos_chatbot/analytics_engine.py`, `database.py`, `data_ingestion.py` | Deterministic KPI calculations, scenario planning, audit logging, and datastore access. |
| RAG + generation | `src/benchmarkos_chatbot/chatbot.py`, `llm_client.py` | Packages retrieved facts into system prompts and calls the selected LLM (local echo or OpenAI). |
| Data acquisition | `scripts/ingestion/*.py` | Pull SEC filings & quotes, refresh metrics, backfill baselines. |

---

## 2. Repository Layout

| Path | Description |
|------|-------------|
| `analysis/experiments/` | One-off investigative scripts (time parser experiments, metric prototypes). |
| `analysis/reports/` | Markdown / JSON reports documenting analysis runs. |
| `data/sqlite/benchmarkos_chatbot.sqlite3` | Default SQLite datastore (mirrored in root for convenience). |
| `docs/` | Generated reference docs (ticker names, onboarding material). |
| `scripts/ingestion/` | Production-ready ingestion & maintenance commands. |
| `src/benchmarkos_chatbot/` | Main application package (parsing, analytics, RAG orchestration). |
| `tests/` | Automated tests (`tests/regression/` contains recent parsing regression suites). |
| `webui/` | Plotly-powered dashboard + export helpers. |

### Notable Python modules

- `src/benchmarkos_chatbot/analytics_engine.py` – deterministic KPI engine & scenario planner.
- `src/benchmarkos_chatbot/parsing/alias_builder.py` – alias generation, fuzzy window matching, ticker resolution warnings.
- `src/benchmarkos_chatbot/parsing/time_grammar.py` – tolerant grammar (supports typos like `fisical`, apostrophes, and O/0 confusion).
- `src/benchmarkos_chatbot/chatbot.py` – orchestrates retrieval, summarisation, citation injection.
- `src/benchmarkos_chatbot/indexers/` *(if present)* – helper index builders for ingestion pipelines.
- `scripts/ingestion/ingest_extended_universe.py` – ingest any ticker universe for deep history (up to 20+ fiscal years).
- `scripts/ingestion/backfill_metrics.py` – recompute KPI snapshots and optional IMF baselines.
- `scripts/ingestion/refresh_quotes.py` – refresh quotes then recalc valuation metrics.

---

## 3. Data Pipeline & Current Coverage

1. **SEC EDGAR ingestion** – `ingest_universe.py` / `ingest_extended_universe.py` pull CompanyFacts JSON plus filing metadata (CIK, accession, period start/end) into `financial_facts` & `company_filings`.
2. **Market quotes** – `refresh_quotes.py` (and legacy `load_prices_yfinance.py`) hydrate `market_quotes` with price/share-count snapshots.
3. **Metric refresh** – `backfill_metrics.py` recomputes YoY, TTM, scenario-ready KPIs and logs lineage events.
4. **Audit trail** – every ingestion writes to `audit_events` with the source system, timestamp, and checksum so responses remain defensible.

**SQLite dataset snapshot**

| Table | Rows |
|-------|------|
| `metric_snapshots` | 322,741 |
| `financial_facts` | 47,325 |
| `company_filings` | 26,200 |
| `market_quotes` | 471 |
| `audit_events` | 1,087 |
| `ticker_aliases` | 54 |
| `kpi_values` | 4,384 |

Total footprint ≈ **0.40 million rows (~88 MB)** covering fiscal years **2016 – 2027** for **521** tickers. To deepen history (e.g., 20 fiscal years) run:

```powershell
python scripts/ingestion/ingest_extended_universe.py `
  --universe-file data/tickers/universe_sp500.txt `
  --years 20 `
  --chunk-size 25 `
  --resume
python scripts/ingestion/backfill_metrics.py
```

---

## 4. Natural-Language Parsing & Error Recovery

- **Company names**: `resolve_tickers_freeform` scans overlapping 1–4 word windows, applies alias variants (strip suffixes, compact spacing), and falls back to fuzzy matching (SequenceMatcher ≥ 0.78). Misspellings such as `Gooogle`, `JP morgan chase`, or compact forms (`UNH`, `BRKB`) resolve to canonical tickers with `fuzzy_match` warnings for traceability.
- **Periods**: `parse_periods` normalises typos (`fisical`, `calender`), apostrophes (`FY'24`, `FY"); converts O/0/I/1 digits, handles ranges (`fiscal 2015-2018`), quarters (`FY2023 Q4`, `Q3 FY-22`), and relative windows (`last 6 quarters`).
- **Routing**: Parsed intents include `normalize_to_fiscal` hints so downstream analytics know whether to use fiscal or calendar calendars.

---

## 5. Retrieval-Augmented Generation (RAG)

1. **Intent structuring** – parser outputs tickers, metrics, periods, and error hints.
2. **Deterministic retrieval** – `AnalyticsEngine` queries `metric_snapshots`, recalculates gaps, and combines citations (SEC accession, quote timestamps).
3. **Prompt assembly** – `chatbot.py` formats comparison tables, highlight bullets, time-series snippets, and citations into structured `system` messages.
4. **Model generation** – `llm_client.py` dispatches to the configured model (local echo for tests, OpenAI in production). Responses include citations, stale-data warnings, and optional dashboard payloads.
5. **Persistence & exports** – the same payload feeds the dashboard renderer and `/api/export/cfi` endpoints, guaranteeing consistency between chat answers and exported slides.

---

## 6. Database & Schema Notes

- Default deployment uses SQLite; switch to Postgres by setting `DATABASE_TYPE=postgresql` and providing `POSTGRES_*` env vars.
- Key tables: `financial_facts`, `metric_snapshots`, `market_quotes`, `audit_events`, `conversations`, `scenario_results` (if enabled).
- The ingestion scripts are idempotent and checkpointed (`.ingestion_progress*.json`); delete or rename the progress file to start a clean run.

---

## 7. Ingestion & Maintenance Scripts

| Script | Purpose |
|--------|---------|
| `scripts/ingestion/ingest_extended_universe.py` | Ingest arbitrary ticker lists (file or predefined) for long history. |
| `scripts/ingestion/ingest_universe.py` | Baseline S&P 500 ingest (10 fiscal years by default). |
| `scripts/ingestion/backfill_metrics.py` | Recompute KPI snapshots and optional IMF baselines. |
| `scripts/ingestion/refresh_quotes.py` | Refresh price-based metrics daily. |
| `scripts/ingestion/fetch_imf_sector_kpis.py` | Auxiliary macro baselines (optional). |

Schedule these via Task Scheduler / cron / CI to keep the dataset fresh.

---

## 8. Dashboard & Exports

- CFI Compare dashboard (default) visualises multi-company KPIs, valuation football fields, and trend explorer.
- Audit drawer surfaces lineage for every metric (filing accession, quote timestamp, transformation).
- Export buttons call `/api/export/cfi` to render PDF/PPTX/Excel. The same structured payload ensures parity between chat, dashboard, and exports.
- Offline demos use `webui/data/*.json` payloads when the API is offline.

---

## 9. Getting Started

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
$env:SEC_API_USER_AGENT = "BenchmarkOSBot/1.0 (you@example.com)"

# Ingest baseline data
python scripts/ingestion/ingest_extended_universe.py --universe sp500 --years 10 --resume
python scripts/ingestion/backfill_metrics.py

# Launch the dashboard
python serve_chatbot.py --port 8000
```

Visit `http://localhost:8000` for the web UI or run `python run_chatbot.py` for the CLI.

---

## 10. Contributing

1. Fork or clone the repo.
2. Add tests (`pytest`).
3. Run formatters (`black`, `ruff`).
4. Submit PRs with before/after notes, updated docs, and screenshots for UI changes.

With robust parsing, deterministic analytics, and clear ingestion tooling, BenchmarkOS stays audit-ready while scaling to new universes and time horizons.
