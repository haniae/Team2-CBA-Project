# BenchmarkOS Copilot — Professor Patrick Briefing

## Executive Summary
BenchmarkOS is the practicum team’s finance copilot. It combines deterministic KPI pipelines with retrieval-augmented generation (RAG) so an analyst can ask natural-language questions, inspect lineage, and export an audit-ready dashboard in minutes. This README is designed as an onboarding packet for you, Professor Patrick, or any reviewer encountering the project for the first time.

---

## System Architecture
A layered architecture keeps deterministic analytics and the LLM cleanly separated. The conceptual diagram is documented in `docs/architecture.md`; the table below summarises each layer and the principal modules.

| Layer | Key modules | Responsibilities |
|-------|-------------|------------------|
| Experiences | `webui/`, `run_chatbot.py`, `serve_chatbot.py` | Single-page dashboard, CLI REPL, and REST API surface the copilot. |
| Natural-language parsing | `src/benchmarkos_chatbot/parsing/alias_builder.py`, `time_grammar.py` | Normalises noisy company names (aliases + fuzzy windows) and flexible periods (`FY-24`, `fiscal 2015–2018`, mistyped `fisical`). |
| Retrieval & analytics | `src/benchmarkos_chatbot/analytics_engine.py`, `database.py`, `data_ingestion.py` | Deterministic KPI calculations, scenario planning, audit logging, datastore access. |
| RAG + generation | `src/benchmarkos_chatbot/chatbot.py`, `llm_client.py` | Packages retrieved facts into structured prompts and calls the configured LLM (local echo or OpenAI). |
| Data acquisition | `scripts/ingestion/*.py` | Pull SEC filings, refresh quotes, backfill KPIs, maintain macro baselines. |

---

## Repository Layout
```
repo/
├── analysis/
│   ├── experiments/              # ad-hoc parser/metric experiments retained for reference
│   ├── reports/                  # Markdown/JSON reports documenting investigation outcomes
│   └── scripts/                  # harnesses used during large-scale fixes & validation
├── data/
│   └── sqlite/benchmarkos_chatbot.sqlite3  # default datastore (mirrors production schema)
├── docs/                         # architecture diagram, ticker name lookup, onboarding notes
├── scripts/ingestion/            # production ingestion/backfill/refresh commands (see below)
├── src/benchmarkos_chatbot/      # main application package (parsing, analytics, RAG orchestration)
├── tests/regression/             # regression suites for ticker + time parsing
└── webui/                        # Plotly dashboard, export helpers, demo payloads
```

### Core Python modules
- `analytics_engine.py` – deterministic KPI engine and scenario planner.
- `chatbot.py` – orchestrates retrieval, summarisation, and citation injection.
- `data_ingestion.py` – shared helpers for SEC filings and quote ingestion.
- `database.py` – thin layer over SQLite/Postgres with audit logging helpers.
- `external_data.py` – optional IMF baseline loader to enrich KPI explanations.
- `parsing/alias_builder.py` – alias generation, multi-token scanning, fuzzy fallback with warnings.
- `parsing/time_grammar.py` – tolerant grammar that handles typos, apostrophes, O/0 swaps, ranges, quarters, and relative windows.

---

## Data Sources & Ingestion Methods
| Dataset | Origin | How we ingest | Destination tables |
|---------|--------|---------------|--------------------|
| SEC CompanyFacts & filings | `https://data.sec.gov` | `scripts/ingestion/ingest_universe.py` (baseline) or `ingest_extended_universe.py` (custom universes, deep history). | `financial_facts`, `company_filings`, `audit_events` |
| Market quotes | Yahoo Finance (`/v7/finance/quote`), optional Stooq fallback | `scripts/ingestion/refresh_quotes.py`, `load_prices_yfinance.py`, `load_prices_stooq.py` | `market_quotes`, citation metadata |
| IMF sector baselines (optional) | IMF API (stored JSON) | `scripts/ingestion/fetch_imf_sector_kpis.py` or `external_data.ingest_imf_kpis` | `kpi_values`, dashboard annotations |
| Static universe files | `data/tickers/*.txt`, `webui/data/*.json` | Seed universes, offline dashboard demos | Used by parsers + demo payloads |

**Current SQLite snapshot**

| Table | Rows |
|-------|------|
| `metric_snapshots` | 322,741 |
| `financial_facts` | 47,325 |
| `company_filings` | 26,200 |
| `market_quotes` | 471 |
| `audit_events` | 1,087 |
| `ticker_aliases` | 54 |
| `kpi_values` | 4,384 |

Total footprint ≈ **0.40 million rows (~88 MB)** covering fiscal years **2016 – 2027** for **521** tickers. To extend history (e.g., 20 fiscal years):
```powershell
python scripts/ingestion/ingest_extended_universe.py `
  --universe-file data/tickers/universe_sp500.txt `
  --years 20 `
  --chunk-size 25 `
  --resume
python scripts/ingestion/backfill_metrics.py
```

---

## Natural-Language Understanding
- **Company aliases:** tokens are normalised (strip suffixes, collapse ampersands, drop leading “the”), 1–4 word windows are matched against alias maps, and fuzzy matches (SequenceMatcher ≥ 0.78) are accepted with `fuzzy_match` warnings. Compact forms (`JPM`, `BRKB`) and misspellings (`Gooogle`, `JP morgan chase`) resolve to canonical tickers.
- **Period grammar:** accepts `FY-24`, `FY'24E`, `fiscal 2015–18`, `Q3 FY'22`, `calendar 2024`, `last 6 quarters`, and tolerant variations (`fisical`, `calender`). Digits are cleaned (O→0, I/L→1) before conversion and quarters normalise even when punctuation is misplaced.
- **Routing hints:** parser outputs include `normalize_to_fiscal` flags so the analytics layer knows whether to use fiscal or calendar axes downstream.

---

## RAG Workflow (Step-by-step)
1. **Intent parsing** – alias/time grammars convert free text into structured requests (tickers, metrics, periods, parser warnings).
2. **Deterministic retrieval** – `AnalyticsEngine` queries `metric_snapshots`, fills missing KPIs on the fly, and bundles citations (SEC accession, quote timestamps, adjustment notes).
3. **Prompt assembly** – `chatbot.py` formats comparison tables, highlight bullets, trend snippets, and citations into system messages. It also attaches dashboard payload metadata reused by the SPA and exports.
4. **LLM generation** – `llm_client.py` invokes the configured model (local echo for tests, OpenAI for production). Responses include citations, stale-data warnings, and any dashboard payload reference.
5. **Persistence & export** – responses, artefacts, and audit metadata are stored so chat answers, dashboards, and `/api/export/cfi` outputs remain consistent.

---

## Dashboard & Export Experience
- Default landing page uses the CFI Compare layout (multi-company KPIs, valuation football field, trend explorer, peer comparison).
- Audit drawer surfaces lineage per metric (filing accession, quote timestamp, transformation applied).
- `/api/export/cfi` produces PDF/PPTX/Excel using the same payload delivered to the web UI.
- Demo payloads under `webui/data/` allow offline presentations when the API is unavailable.

---

## Operating Guide
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
$env:SEC_API_USER_AGENT = "BenchmarkOSBot/1.0 (you@example.com)"

# Ingest baseline history
python scripts/ingestion/ingest_extended_universe.py --universe sp500 --years 10 --resume
python scripts/ingestion/backfill_metrics.py

# Launch the dashboard
python serve_chatbot.py --port 8000
```
Visit `http://localhost:8000` for the dashboard or run `python run_chatbot.py` for the CLI interface.

**Maintenance cadence**
| Task | Command |
|------|---------|
| Deep ingest | `scripts/ingestion/ingest_extended_universe.py` |
| KPI backfill | `scripts/ingestion/backfill_metrics.py` |
| Daily quotes | `scripts/ingestion/refresh_quotes.py` |
| IMF baselines | `scripts/ingestion/fetch_imf_sector_kpis.py` |
Schedule these via Task Scheduler/cron/CI to keep metrics fresh.

---

## Testing & Quality
- Regression suites live in `tests/regression/` (`test_ticker_resolution.py`, `test_time_fixes.py`, `comprehensive_chatbot_test.py`).
- Run `pytest` before submitting changes and add regression cases for new edge scenarios.
- Apply formatters (`ruff`, `black`) for consistency.

---

## Contributing & Next Steps
1. Fork or clone the repo.
2. Add tests (`pytest`).
3. Run formatters (`black`, `ruff`).
4. Submit PRs with before/after notes, updated docs, and UI screenshots when relevant.

With resilient parsing, deterministic analytics, and a clear ingestion toolkit, BenchmarkOS stays audit-ready while scaling to new universes and time horizons.
