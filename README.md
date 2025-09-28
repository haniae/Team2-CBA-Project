# BenchmarkOS Chatbot Starter

This repository provides a clean, well-documented Python codebase you can use in Ubuntu (or any Linux subsystem) to build an institutional-grade finance chatbot for the BenchmarkOS platform. The focus is on clarity: the project layout, modules, and configuration are deliberately simple so you can extend them quickly in your own environment.

## Key Features

- **Python-first workflow** – Structured as a standard Python package that works well in VS Code, PyCharm, or any terminal-based editor.
- **SQLite persistence** – Conversations are stored locally using SQLite so you can analyse or replay them later with SQL queries.
- **Pluggable language model layer** – Swap between a dummy local model for quick testing and a real OpenAI-powered implementation when you are ready.
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
- **Track KPIs** by adding tables for metrics (response latency, user sentiment, etc.) and computing them with SQL.

## Development Tips

- Use the docstrings and type hints as your quick reference while coding in VS Code or PyCharm.
- Enable `PYTHONPATH=src` (or use the provided `pyproject.toml`) so that imports resolve cleanly during development and testing.
- Treat `tests/test_database.py` as a template for further unit tests covering prompts, adapters, and data quality checks.

Happy building! This scaffold is intentionally lightweight so you can iterate quickly while keeping the codebase easy to reason about.
