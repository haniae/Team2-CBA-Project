# BenchmarkOS Chatbot Platform

BenchmarkOS is an institutional-grade finance copilot. It pairs deterministic market analytics with retrieval-augmented generation (RAG) so analysts can ask natural-language questions, inspect lineage, and export audit-ready dashboards.

---

## 1. High-level Architecture

| Layer | Key files | What happens |
|-------|-----------|--------------|
| User experiences | `webui/`, `run_chatbot.py`, `serve_chatbot.py` | Single-page dashboard, CLI REPL, and FastAPI REST endpoints expose the chatbot. |
| Natural language parsing | `src/benchmarkos_chatbot/parsing/alias_builder.py`, `time_grammar.py` | Cleans noisy company names (typos, abbreviations) and flexible period expressions (e.g., `FY'24`, `fiscal 2015-2018`). |
| Retrieval & analytics | `src/benchmarkos_chatbot/analytics_engine.py`, `database.py`, `data_ingestion.py` | Deterministic KPI calculations, scenario planning, and database access. |
| RAG + generation | `src/benchmarkos_chatbot/llm_client.py`, `chatbot.py` | Structured facts feed the LLM (local echo or OpenAI) to craft natural-language responses with citations. |
| Data ingest scripts | `scripts/ingestion/*.py` | Pull SEC filings, quotes, backfill KPIs, and refresh dashboards. |

---

## 2. Repository Tour

- `src/benchmarkos_chatbot/`
  - `analytics_engine.py` – deterministic KPI calculations, scenario builders, and metric refresh logic.
  - `parsing/` – resilient alias + time parsing (handles `fisical`, `FY-24`, `Gooogle`, etc.).
  - `data_ingestion.py` – core ingestion helpers used by CLI scripts.
  - `database.py` – abstraction for SQLite/Postgres (metric snapshots, audit events, conversations).
  - `external_data.py` – optional IMF baselines and enrichment hooks.
  - `llm_client.py` – provider-agnostic wrapper (local echo or OpenAI).
- `scripts/ingestion/`
  - `ingest_extended_universe.py` – ingest any ticker universe (file or predefined) for up to 20+ fiscal years with checkpoints.
  - `backfill_metrics.py` – recompute KPI snapshots & optional IMF enrichments after new data lands.
  - `refresh_quotes.py` – load daily prices and refresh valuation metrics.
  - `load_prices_yfinance.py`, `load_prices_stooq.py` – targeted price backfills.
  - `ingest_universe.py`, `ingest_companyfacts.py` – baseline ingest utilities.
- `data/`
  - `sqlite/benchmarkos_chatbot.sqlite3` – default datastore.
  - `tickers/` – universe definitions (`universe_sp500.txt`, etc.).
- `webui/`
  - SPA dashboard powered by Plotly; supports CFI dashboards, audit drawer, KPI drill-down.
- `docs/` – generated artifacts (e.g., ticker name lookup).

---

## 3. Data Pipeline & Current Coverage

1. **SEC EDGAR facts:** `scripts/ingestion/ingest_universe.py` and `ingest_extended_universe.py` fetch CompanyFacts JSON + filings metadata (accession, period start/end).
2. **Quote refresh:** `scripts/ingestion/refresh_quotes.py` and `load_prices_yfinance.py` hydrate price tables.
3. **Metric backfill:** `scripts/ingestion/backfill_metrics.py` recalculates YoY, TTM, and scenario-ready KPIs.
4. **Lineage & audit trails:** every ingest writes to `audit_events` (source system, timestamp, hash).

**Current dataset snapshot (SQLite)**

| Table | Rows |
|-------|------|
| `metric_snapshots` | 322,741 |
| `financial_facts` | 47,325 |
| `company_filings` | 26,200 |
| `market_quotes` | 471 |
| `audit_events` | 1,087 |
| `ticker_aliases` | 54 |
| `kpi_values` | 4,384 |

Total footprint ≈ **0.40 million rows (~88 MB)** covering fiscal years **2016–2027** for **521 tickers**. Extend the coverage by rerunning:

```powershell
python scripts/ingestion/ingest_extended_universe.py `
  --universe-file data/tickers/universe_sp500.txt `
  --years 20 `
  --chunk-size 25 `
  --resume
python scripts/ingestion/backfill_metrics.py
```

---

## 4. Natural Language Handling

- **Company names:** `resolve_tickers_freeform` collapses “The Amazon Company”, “Gooogle”, or “JP Morgan Chase” into canonical tickers using aliases + fuzzy window matching. The parser returns warnings when fuzzy matches are used.
- **Time expressions:** `parse_periods` accepts `FY-24`, `fiscal 2015-2018`, `Q3 FY'22`, `calendar 2024`, and even mistyped variants like `fisical 2021`. It normalises O → 0 / I,L → 1 in years and interprets ranges, quarters, and relative windows (`last 6 quarters`).
- **Routing:** Structured intents flow to `AnalyticsEngine`, and the retrieved facts become RAG inputs for the LLM so responses retain numerical accuracy.

---

## 5. RAG & Machine Learning Workflow

1. **Intent parsing:** alias + time grammars convert text into structured requests (tickers, metrics, periods).
2. **Deterministic retrieval:** `AnalyticsEngine` queries metric snapshots, recalculates where required, and collects audit citations.
3. **RAG assembly:** `chatbot.py` packages tables (`comparison_table`, `highlights`, `trends`, `citations`) as system messages for the model.
4. **Generation:** `llm_client.py` talks to the configured provider (local echo or OpenAI). Responses include citations, warnings (e.g., stale quotes), and optional dashboard payloads.
5. **Exports:** the same structured payload powers PDF/PPTX/Excel exports and the dashboard, guaranteeing consistency.

---

## 6. Database & Schema

- Default backend: SQLite (`data/sqlite/benchmarkos_chatbot.sqlite3`).
- Recommended production backend: Postgres (`DATABASE_TYPE=postgresql`).
- Core tables:
  - `financial_facts` – raw SEC data (metric, ticker, fiscal year/period, units, source filing).
  - `metric_snapshots` – precomputed KPIs, scenarios, cache for RAG retrieval.
  - `market_quotes` – price snapshots powering valuation ratios.
  - `audit_events` – ingest lineage.
  - `conversations` – chat history (not shown above for brevity).

Switching to Postgres is as simple as setting `DATABASE_TYPE=postgresql` env vars (`POSTGRES_HOST`, etc.) and rerunning ingestion.

---

## 7. Getting Started

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

## 8. Web Dashboard & Exports

- Launches with the CFI Compare view (multi-company KPIs, valuation football field, trend explorer, peer comparison).
- Audit drawer shows lineage per metric (filing accession, quote timestamp).
- Export buttons generate PDF/PPTX/Excel via `/api/export/cfi`.
- Demo payloads live under `webui/data/*.json` for offline presentations.

---

## 9. Maintenance Checklist

| Task | Command |
|------|---------|
| Extended ingest | `scripts/ingestion/ingest_extended_universe.py` |
| Backfill KPIs | `scripts/ingestion/backfill_metrics.py` |
| Daily quotes | `scripts/ingestion/refresh_quotes.py` |
| IMF baselines | `scripts/ingestion/fetch_imf_sector_kpis.py` |

Automate these via Task Scheduler or CI for production deployments.

---

## 10. Contributing

1. Fork or clone the repo.
2. Add tests (`pytest`).
3. Run formatters (`black`, `ruff`).
4. Submit PRs with clear before/after notes and updated docs.

With robust parsing, deterministic analytics, and a clear ingestion story, the BenchmarkOS chatbot stays audit-ready while scaling to new universes and time horizons.
