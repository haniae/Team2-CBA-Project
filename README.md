# BenchmarkOS Chatbot Starter

This repository provides a clean, well-documented Python codebase you can use in Ubuntu (or any Linux subsystem) to build an institutional-grade finance chatbot for the BenchmarkOS platform. The focus is on clarity: the project layout, modules, and configuration are deliberately simple so you can extend them quickly in your own environment.

## Key Features

- **Python-first workflow** – Structured as a standard Python package that works well in VS Code, PyCharm, or any terminal-based editor.
- **SQLite persistence** – Conversations are stored locally using SQLite so you can analyse or replay them later with SQL queries.
- **Pluggable language model layer** – Swap between a dummy local model for quick testing and a real OpenAI-powered implementation when you are ready.
- **Institutional data ingestion** – Built-in clients for the SEC EDGAR XBRL API and Yahoo Finance so you can normalise filings, compute KPIs, and benchmark performance with traceability.
- **Configuration via environment variables** – Keep secrets (like API keys) out of your codebase and under your control.
- **Extensive inline documentation** – Each module explains its purpose, inputs, and extension points.

## Repository Layout

```
Project/
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml
├── src/
│   └── benchmarkos_chatbot/
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── llm_client.py
│       └── chatbot.py
├── main.py
└── tests/
    └── test_database.py
```

- `src/benchmarkos_chatbot/config.py` centralises settings (database path, model choice, etc.).
- `src/benchmarkos_chatbot/database.py` wraps SQLite operations, ensuring the schema is always in place.
- `src/benchmarkos_chatbot/llm_client.py` contains lightweight client classes for calling language models.
- `src/benchmarkos_chatbot/data_sources.py` wraps SEC EDGAR and Yahoo Finance downloads with production-ready headers and validation.
- `src/benchmarkos_chatbot/analytics.py` converts raw disclosures and price history into BenchmarkOS KPIs with CAGR, margin, and volatility calculations.
- `src/benchmarkos_chatbot/data_pipeline.py` orchestrates the end-to-end workflow (fetch → normalise → summarise) and exposes a helper used by the chatbot for instant analysis.
- `src/benchmarkos_chatbot/chatbot.py` orchestrates prompts, responses, and logging.
- `main.py` offers a simple command-line interface to interact with the chatbot.
- `tests/` contains a starter Pytest suite.

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

   While chatting you can type `show deliverables` (or `list deliverables`) to see the BenchmarkOS core deliverables seeded from your stand-up tracker. Update progress inline with natural commands such as `mark deliverable 3 complete` or `set deliverable 5 in progress`.

   To pull institutional-grade data you can use natural phrases such as `run sec analysis for AAPL`, `benchmark market data on MSFT`, or `generate KPI report for AMZN`. The chatbot will retrieve the latest 10-K facts, compute revenue CAGR, operating/net margins, and review market risk metrics (CAGR, volatility, drawdown) before listing the most recent filings.

5. **Run tests**

   ```bash
   pytest
   ```

## Configuration

The `Settings` dataclass in `config.py` reads environment variables and provides a single configuration object used across the application. Key options include:

- `DATABASE_PATH` – Change where the SQLite database file is stored.
- `LLM_PROVIDER` – Choose between `"local"` (default) and `"openai"` clients.
- `OPENAI_MODEL` – Which OpenAI chat completion model to call when using the OpenAI provider.

You can override any setting by exporting an environment variable, for example:

```bash
export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-4o-mini
```

## Extending the Chatbot

- **Add retrieval or analytics** by expanding the database schema and adding helper functions in `database.py`.
- **Introduce new model providers** by subclassing `LLMClient` in `llm_client.py`.
- **Build a web UI** by reusing `BenchmarkOSChatbot` in `chatbot.py` inside a FastAPI, Flask, or Streamlit app.
- **Track KPIs** by extending `analytics.py` with additional ratios, scenario modelling, and compliance checks.
- **Coordinate deliverables** using the built-in tracker for the BenchmarkOS finance workstreams.
- **Extend data coverage** by updating `data_pipeline.CompanyRegistry` with new tickers and CIKs and wiring additional data sources (Bloomberg, Capital IQ, etc.) into the orchestration layer.

## Development Tips

- Use the docstrings and type hints as your quick reference while coding in VS Code or PyCharm.
- Enable `PYTHONPATH=src` (or use the provided `pyproject.toml`) so that imports resolve cleanly during development and testing.
- Treat `tests/test_database.py` as a template for further unit tests covering prompts, adapters, and data quality checks.

## Working in VS Code

If you prefer Visual Studio Code on Ubuntu/WSL, the project is already structured to slot in smoothly. The checklist below walks through the most common setup tasks:

1. **Open the folder** – Launch VS Code and choose **File ▸ Open Folder…**, then select the repository root (`Project/`). The editor will automatically detect the Python sources under `src/` and the tests in `tests/`.
2. **Select an interpreter** – When the Python extension prompts you, create or pick a virtual environment (for example the `.venv` created in the steps above). You can also open the command palette (`Ctrl+Shift+P`) and run “Python: Select Interpreter”.
3. **Install dependencies** – Open an integrated terminal (`Ctrl+``) and run `pip install -r requirements.txt`. VS Code will use the active interpreter to install packages, keeping them isolated from your system Python.
4. **Configure environment variables** – Create a `.env` file in the project root with entries such as `OPENAI_API_KEY=` and `LLM_PROVIDER=`. The Python extension automatically loads this file when you run or debug scripts, so the chatbot picks up your secrets and overrides.
5. **Create run configurations** – Open the Run and Debug panel and add a new configuration using the Python template. Point the `program` field at `main.py` so you can start the chatbot loop with a single click. You can duplicate the configuration for Pytest by changing the `request` to `test` and setting `args` to `-m pytest`.
6. **Leverage linting and formatting** – Enable linting (for example, `ruff` or `flake8`) and formatting (`black`) from the command palette to keep the codebase consistent as you iterate. These tools respect the interpreter and dependencies you just configured.

With this setup, you can edit the chatbot modules, run the CLI, and execute the tests entirely inside VS Code on Linux without extra boilerplate.

Happy building! This scaffold is intentionally lightweight so you can iterate quickly while keeping the codebase easy to reason about.

## Publishing the project to your own GitHub repository

Follow the steps below when you are ready to copy this scaffold into a fresh GitHub repository that you can later open from VS Code or PyCharm:

1. **Create a GitHub repository** – Visit <https://github.com/new>, choose a name (for example `benchmarkos-chatbot`), set the visibility, and leave the repository empty (no README/license/gitignore).
2. **Initialise Git locally (if needed)** – Run `git init` inside the project folder if it is not already a Git repository, then stage the current files:

   ```bash
   git init
   git add .
   git commit -m "Initial BenchmarkOS chatbot scaffold"
   ```

3. **Point the repository at GitHub** – Add your GitHub URL as the `origin` remote. Replace `<your-username>` and `<repo-name>` with the values you used when creating the repository:

   ```bash
   git remote add origin git@github.com:<your-username>/<repo-name>.git
   ```

   If you prefer HTTPS you can instead use `https://github.com/<your-username>/<repo-name>.git`.

4. **Push the code** – Send the local commits to GitHub. The `-u` flag sets `origin/main` as the upstream branch so future pushes are a single `git push`:

   ```bash
   git push -u origin main
   ```

5. **Clone from VS Code or PyCharm** – On your Ubuntu or WSL machine, open VS Code, choose **File ▸ Clone Repository…**, paste the GitHub URL, and select a destination folder. PyCharm offers the same workflow under **Get from VCS**.

Once the repository lives on GitHub you can keep iterating locally, commit new changes, and push them so your IDEs and collaborators stay in sync.
