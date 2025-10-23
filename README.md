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
- **Default landing page** uses the CFI Compare layout (multi-company KPIs, valuation football field, trend explorer, peer comparison).
- **Audit drawer** surfaces lineage per metric (filing accession, quote timestamp, transformation applied).
- **Export functionality** (`/api/export/cfi`) produces client-ready PDF, PowerPoint, and Excel reports using the same payload delivered to the web UI.
- **Demo payloads** under `webui/data/` allow offline presentations when the API is unavailable.

### PowerPoint Export & Analyst Documentation

The PowerPoint export generates a comprehensive **12-slide CFI-style presentation** suitable for client presentations, investment committee meetings, and academic deliverables. Each deck is automatically generated from live dashboard data with zero manual formatting required.

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
- [BenchmarkOS GitHub Repository](https://github.com/haniae/Team2-CBA-Project)

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
5. File downloads automatically: `benchmarkos-{ticker}-{date}.pptx`

*Programmatic (Python SDK):*
```python
from benchmarkos_chatbot import AnalyticsEngine, load_settings
from benchmarkos_chatbot.export_pipeline import generate_dashboard_export

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
