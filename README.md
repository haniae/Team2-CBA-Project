# BenchmarkOS Chatbot Platform

BenchmarkOS is an institutional-grade finance copilot. It combines deterministic market analytics with retrieval-augmented generation (RAG) so analysts can interrogate KPIs in natural language, trace lineage, and export audit-ready dashboards.

---

## 1. Architecture Overview

| Layer | Key modules | Responsibilities |
|-------|-------------|------------------|
| Experiences | `webui/`, `run_chatbot.py`, `serve_chatbot.py` | Browser dashboard, CLI REPL, and FastAPI REST service. |
| Natural-language parsing | `src/benchmarkos_chatbot/parsing/alias_builder.py`, `time_grammar.py` | Normalises noisy company names (aliases, fuzzy windows) and flexible periods (`FY-24`, `fiscal 2015-2018`, mistyped `fisical`). |
| Retrieval & analytics | `src/benchmarkos_chatbot/analytics_engine.py`, `database.py`, `data_ingestion.py` | Deterministic KPI calculations, scenario planning, audit logging, datastore access. |
| RAG + generation | `src/benchmarkos_chatbot/chatbot.py`, `llm_client.py` | Packages retrieved facts into structured prompts and calls the configured LLM (local echo or OpenAI). |
| Data acquisition | `scripts/ingestion/*.py` | Pull SEC filings, refresh quotes, backfill KPIs, maintain baselines. |

---

## 2. File & Directory Layout

```
repo/
├── analysis/
│   ├── experiments/              # Ad-hoc notebooks & parser experiments (kept for reference)
│   ├── reports/                  # Markdown/JSON reports and investigation notes
│   └── scripts/                  # Utility harnesses used during large fix rollouts
├── data/
│   └── sqlite/benchmarkos_chatbot.sqlite3  # Default datastore (mirrors production schema)
├── docs/                         # Generated documentation, ticker name lookup, onboarding
├── scripts/
│   └── ingestion/
│       ├── ingest_extended_universe.py     # Ingest any ticker universe (file/predefined) w/ deep history
│       ├── backfill_metrics.py             # Recompute KPI snapshots + optional IMF baselines
│       ├── refresh_quotes.py               # Refresh quotes, recompute valuation ratios
│       ├── ingest_universe.py              # Baseline S&P 500 ingest (10 years default)
│       └── fetch_imf_sector_kpis.py        # Optional macro baseline loader
├── src/
│   └── benchmarkos_chatbot/
│       ├── analytics_engine.py             # Deterministic KPI engine, scenario planner
│       ├── chatbot.py                      # RAG orchestration, citation injection
│       ├── data_ingestion.py               # Shared ingestion helpers (SEC facts, quotes)
│       ├── database.py                     # SQLite/Postgres abstraction, audit trail helpers
│       ├── external_data.py                # Optional IMF data ingestion
│       └── parsing/
│           ├── alias_builder.py            # Alias generation, fuzzy window resolution, warnings
│           └── time_grammar.py             # Tolerant grammar for periods/quarters/typos
├── tests/
│   └── regression/
│       ├── test_ticker_resolution.py       # Regression suite for alias resolution
│       └── test_time_fixes.py              # Regression suite for time grammar parsing
└── webui/                                   # Plotly dashboard, export helpers, demo payloads
```

> Any new reports or experimental scripts should live in the `analysis/` tree so the repo root stays clean.

---

## 3. RAG Workflow (Detailed)

1. **Intent parsing** – alias + time grammars convert free text into structured requests (tickers, metrics, periods, parser warnings).
2. **Deterministic retrieval** – `AnalyticsEngine` queries `metric_snapshots`, fills gaps, and bundles citations (SEC accession, quote timestamps, adjustment notes).
3. **Prompt assembly** – `chatbot.py` formats comparison tables, highlight bullets, trend snippets, and citations into system messages. It also attaches dashboard payloads reused by the SPA/exports.
4. **LLM generation** – `llm_client.py` invokes the configured provider. Responses echo citations, highlight stale data, and include dashboard payload metadata when present.
5. **Persistence & export** – responses, artefacts, and audit metadata are stored so chat answers, dashboards, and `/api/export/cfi` exports stay consistent.

---

## 4. Natural-Language Parsing Strategies

- **Company aliases** – tokens are normalised (strip suffixes, collapse ampersands, drop leading "the"), 1–4 word windows are checked against alias maps, and fuzzy matches (SequenceMatcher ≥ 0.78) are accepted with `fuzzy_match` warnings. Compact forms (`JPM`, `BRKB`) and misspellings (`Gooogle`, `JP morgan chase`) resolve to canonical tickers.
- **Period grammar** – accepts `FY-24`, `FY'24E`, `fiscal 2015-18`, `Q3 FY'22`, `calendar 2024`, `last 6 quarters`, and tolerant variations (`fisical`, `calender`). Digits are cleaned (O→0, I/L→1) before conversion and quarters normalise even when punctuation is misplaced.
- **Routing hints** – parser outputs include `normalize_to_fiscal` flags so analytics knows whether to use fiscal or calendar axes.

---

## 5. Data Pipeline & Current Coverage

1. **SEC EDGAR facts** – `ingest_universe.py` / `ingest_extended_universe.py` pull CompanyFacts JSON + filing metadata (CIK, accession, period start/end) into `financial_facts` and `company_filings`.
2. **Quote refresh** – `refresh_quotes.py` (and legacy `load_prices_yfinance.py`/`load_prices_stooq.py`) update `market_quotes`.
3. **Metric backfill** – `backfill_metrics.py` recomputes YoY, TTM, valuation ratios, and scenario anchors while recording lineage.
4. **Audit trail** – every ingest writes to `audit_events` capturing source system, timestamp, and checksum for reproducibility.

**SQLite snapshot**

| Table | Rows |
|-------|------|
| `metric_snapshots` | 322,741 |
| `financial_facts` | 47,325 |
| `company_filings` | 26,200 |
| `market_quotes` | 471 |
| `audit_events` | 1,087 |
| `ticker_aliases` | 54 |
| `kpi_values` | 4,384 |

Total footprint ≈ **0.40 million rows (~88 MB)** covering fiscal years **2016 – 2027** for **521** tickers.

To extend coverage (e.g., 20 years):

```powershell
python scripts/ingestion/ingest_extended_universe.py `
  --universe-file data/tickers/universe_sp500.txt `
  --years 20 `
  --chunk-size 25 `
  --resume
python scripts/ingestion/backfill_metrics.py
```

---

## 6. Database & Backend Options

- **Default**: SQLite located at `data/sqlite/benchmarkos_chatbot.sqlite3`.
- **Production**: set `DATABASE_TYPE=postgresql` and provide `POSTGRES_*` env vars, then re-run ingestion/backfill.
- Key tables include `financial_facts`, `metric_snapshots`, `market_quotes`, `audit_events`, `conversations`, and `scenario_results`.
- Checkpoints (`.ingestion_progress*.json`) allow resuming long ingests; delete or rename to start fresh.

---

## 7. Ingestion & Maintenance Toolkit

| Script | Purpose |
|--------|---------|
| `scripts/ingestion/ingest_extended_universe.py` | Ingest predefined or custom universes (file-based) with deep fiscal history. |
| `scripts/ingestion/ingest_universe.py` | Baseline S&P 500 ingest (10-year default). |
| `scripts/ingestion/backfill_metrics.py` | Recompute KPI snapshots & optional IMF baselines after new data lands. |
| `scripts/ingestion/refresh_quotes.py` | Refresh price-based metrics (P/E, EV/EBITDA, TSR) daily. |
| `scripts/ingestion/fetch_imf_sector_kpis.py` | Optional macro baseline loader. |

Automate these via Task Scheduler, cron, or CI to keep data fresh.

---

## 8. Dashboard & Exports

- Default CFI Compare view (multi-company KPIs, valuation football field, trend explorer, peer comparison).
- Audit drawer surfaces lineage per metric (filing accession, quote timestamp, adjustment notes).
- `/api/export/cfi` generates PDF/PPTX/Excel using the same payload as chat responses.
- Offline demos use `webui/data/*.json` payloads when the API is offline.

---

## 9. Testing & Quality

- Regression suites live in `tests/regression/` (`test_ticker_resolution.py`, `test_time_fixes.py`, `comprehensive_chatbot_test.py`).
- Run `pytest` before submitting changes and add regression cases for new edge scenarios.
- Apply formatters (`ruff`, `black`) for consistency.

---

## 10. Getting Started

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
$env:SEC_API_USER_AGENT = "BenchmarkOSBot/1.0 (you@example.com)"

python scripts/ingestion/ingest_extended_universe.py --universe sp500 --years 10 --resume
python scripts/ingestion/backfill_metrics.py
python serve_chatbot.py --port 8000
```

Visit `http://localhost:8000` for the dashboard or run `python run_chatbot.py` for the CLI.

---

## 11. Contributing

1. Fork or clone the repo.
2. Add tests (`pytest`).
3. Run formatters (`black`, `ruff`).
4. Submit PRs with before/after notes, updated docs, and UI screenshots when relevant.

With resilient parsing, deterministic analytics, and a clear ingestion toolkit, BenchmarkOS stays audit-ready while scaling to new universes and time horizons.
