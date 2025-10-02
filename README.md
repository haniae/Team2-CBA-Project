# BenchmarkOS Chatbot Starter

This repository provides a clean, well-documented Python codebase you can use in Ubuntu (or any Linux subsystem) to build an institutional-grade finance chatbot for the BenchmarkOS platform. The focus is on clarity: the project layout, modules, and configuration are deliberately simple so you can extend them quickly in your own environment.

## Key Features

- **Python-first workflow** Ã¢â‚¬â€œ Structured as a standard Python package that works well in VS Code, PyCharm, or any terminal-based editor.
- **SQLite persistence** Ã¢â‚¬â€œ Conversations are stored locally using SQLite so you can analyse or replay them later with SQL queries.
- **Pluggable language model layer** Ã¢â‚¬â€œ Swap between a dummy local model for quick testing and a real OpenAI-powered implementation when you are ready.
- **Configuration via environment variables** Ã¢â‚¬â€œ Keep secrets (like API keys) out of your codebase and under your control.
- **Extensive inline documentation** Ã¢â‚¬â€œ Each module explains its purpose, inputs, and extension points.

## Repository Layout

```
Project/
â”œâ”€â”€ .gitignore
â”œâ”€â”€ README.md
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ pyproject.toml
â”œâ”€â”€ src/
â”‚   â””â”€â”€ benchmarkos_chatbot/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ analytics_engine.py
â”‚       â”œâ”€â”€ chatbot.py
â”‚       â”œâ”€â”€ config.py
â”‚       â”œâ”€â”€ data_ingestion.py
â”‚       â”œâ”€â”€ data_sources.py
â”‚       â”œâ”€â”€ database.py
â”‚       â”œâ”€â”€ llm_client.py
â”‚       â””â”€â”€ ticker_universe.py
â”œâ”€â”€ ingest_universe.py
â”œâ”€â”€ main.py
â””â”€â”€ tests/
    â””â”€â”€ test_database.py
```


- `src/benchmarkos_chatbot/config.py` centralises runtime settings, secrets, and API configuration.
- `src/benchmarkos_chatbot/database.py` wraps SQLite operations and manages the analytics schema.
- `src/benchmarkos_chatbot/data_sources.py` houses the EDGAR, Yahoo Finance, and (optional) Bloomberg clients.
- `src/benchmarkos_chatbot/data_ingestion.py` orchestrates multi-source ingestion and normalisation.
- `src/benchmarkos_chatbot/analytics_engine.py` computes derived metrics used by the web/API layer.
- `src/benchmarkos_chatbot/chatbot.py` orchestrates prompts, responses, and logging.
- `ingest_universe.py` runs large-universe ingestion batches with progress tracking.
- `main.py` offers a simple command-line interface to interact with the chatbot.
- `tests/` contains a Pytest suite covering database and ingestion helpers.

## Getting Started

1. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional) Provide an OpenAI API key**

   Create a `.env` file (ignored by Git) or export directly in your shell:

   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

4. **Run the chatbot**

   ```bash
   python main.py
   ```

   The CLI boots with a dummy echo model by default so you can test the conversation loop without any external services. Switch to the OpenAI client by editing `config.py` (see below).

   While chatting, you can render quick comparison tables directly from the CLI:

   ```text
   compare AAPL MSFT on revenue net_income years=2022-2024
   ```

   The command above prints an ASCII table with the latest available metrics per ticker. Use `year=YYYY` or `years=YYYY-YYYY` to pin the fiscal span.
   Use `metrics all` as a shortcut to expand every available field. Add `layout=metrics` (or use the `compare` command) to pivot the output so metrics sit in the first column and tickers appear across the row with abbreviated labels.
   Example:
   ```text
   table AAPL MSFT metrics all layout=metrics years=2021-2024
   ```

5. **Run tests**

   ```bash
   pytest
   ```

## Configuration

The `Settings` dataclass in `config.py` reads environment variables and provides a single configuration object used across the application. Key options include:

- `DATABASE_PATH` – Change where the SQLite database file is stored.
- `LLM_PROVIDER` – Choose between "local" (default) and "openai" clients.
- `OPENAI_MODEL` – Which OpenAI chat completion model to call when using the OpenAI provider.
- `SEC_API_USER_AGENT` – Required identifier for SEC EDGAR requests (`Org Name Contact` format).
- `HTTP_REQUEST_TIMEOUT` – Seconds to wait before aborting upstream HTTP calls.
- `YAHOO_QUOTE_BATCH_SIZE` – Control Yahoo Finance quote batching (default 50).
- `ENABLE_BLOOMBERG` – Set to `1` to activate Bloomberg ingestion (requires `blpapi`).
- `BLOOMBERG_HOST` / `BLOOMBERG_PORT` / `BLOOMBERG_TIMEOUT` – Connection settings for Bloomberg sessions.

You can override any setting by exporting an environment variable, for example:

```bash
export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-4o-mini
```

## Extending the Chatbot

- **Add retrieval or analytics** by expanding the database schema and adding helper functions in `database.py`.
- **Introduce new model providers** by subclassing `LLMClient` in `llm_client.py`.
- **Build a web UI** by reusing `BenchmarkOSChatbot` in `chatbot.py` inside a FastAPI, Flask, or Streamlit app.
- **Track KPIs** by adding tables for metrics (response latency, user sentiment, etc.) and computing them with SQL.

## Development Tips

- Use the docstrings and type hints as your quick reference while coding in VS Code or PyCharm.
- Enable `PYTHONPATH=src` (or use the provided `pyproject.toml`) so that imports resolve cleanly during development and testing.
- Treat `tests/test_database.py` as a template for further unit tests covering prompts, adapters, and data quality checks.

Happy building! This scaffold is intentionally lightweight so you can iterate quickly while keeping the codebase easy to reason about.


### Large-scale ingestion

To populate the datastore with the entire S&P 500 universe (roughly 500 companies), "ingest_universe.py" orchestrates batched downloads and tracks progress so you can restart safely.

```bash
# optional: resume from a prior run
python ingest_universe.py --years 10 --chunk-size 25 --sleep 2.0 --resume
```

By default this script writes progress into `.ingestion_progress.json`.
You must set the SEC user agent (`SEC_API_USER_AGENT`) and ensure `DATABASE_PATH` points
to the SQLite (or Postgres) target before running. After ingestion, metrics are
refreshed automatically. If you have Bloomberg access, export `ENABLE_BLOOMBERG=1` (and
optionally `BLOOMBERG_HOST`/`BLOOMBERG_PORT`) to enrich the live quote store.

## Available Metrics

Growth metrics: `revenue_cagr`, `eps_cagr`, `ebitda_growth`.

Profitability metrics: `profit_margin`, `net_margin`, `operating_margin`, `return_on_assets`/`roa`, `return_on_equity`/`roe`, `return_on_invested_capital`/`roic`.

Capital efficiency metrics: `free_cash_flow`, `free_cash_flow_margin`, `cash_conversion`, `working_capital`, `working_capital_change`.

Valuation metrics: `pe_ratio`, `ev_ebitda`, `pb_ratio`, `peg_ratio`, `dividend_yield`.

Shareholder return metrics: `tsr`, `share_buyback_intensity`.

All underlying fundamentals (revenue, net income, operating income, EPS, assets, liabilities, cash flow, etc.) remain available for tabular comparisons.

