# BenchmarkOS Chatbot Architecture

This workflow mirrors the product storyboard: user prompts begin on the client surfaces, traverse back-end planners and analytics engines, then return enriched responses to the chat surface.

```mermaid
flowchart LR
    %% Class definitions
    classDef front fill:#fde68a,stroke:#f59e0b,stroke-width:2px,color:#78350f,font-weight:bold
    classDef orchestrator fill:#bbf7d0,stroke:#15803d,stroke-width:2px,color:#064e3b,font-weight:bold
    classDef llm fill:#c7d2fe,stroke:#4338ca,stroke-width:2px,color:#1e1b4b,font-weight:bold
    classDef data fill:#bae6fd,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,font-weight:bold
    classDef ops fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#1f2937,font-weight:bold
    classDef external fill:#e9d5ff,stroke:#7c3aed,stroke-width:2px,color:#4c1d95,font-weight:bold
    classDef artifact fill:#fbcfe8,stroke:#db2777,stroke-width:2px,color:#831843,font-weight:bold

    subgraph FE["Front-End Channels"]
        WebUI["Web UI\n(streaming chat)"]:::front
        CLI["CLI\n(ad-hoc prompts)"]:::front
        Batch["Batch API\n(partner jobs)"]:::front
        Auth["Auth gateway\n(optional)"]:::front
    end
    style FE fill:#fffbeb,stroke:#fde68a,stroke-dasharray:8 4

    subgraph ORCH["Orchestration & Guardrails"]
        Ingress["FastAPI /chat\nrequest validation"]:::orchestrator
        Session["Chat orchestrator\ncontext & guardrails"]:::orchestrator
        Composer["Response composer\npayload assembly"]:::orchestrator
    end
    style ORCH fill:#ecfdf5,stroke:#bbf7d0,stroke-dasharray:8 4

    subgraph LLM["LLM Layer"]
        Planner["Planner LLM\n(intent & SQL plan)"]:::llm
        Generator["Narrative LLM\n(response drafting)"]:::llm
    end
    style LLM fill:#eef2ff,stroke:#c7d2fe,stroke-dasharray:8 4

    subgraph ANALYTICS["Analytics & Insights"]
        Analytics["Analytics engine\nSQL + metric compute"]:::data
        Metrics["Metrics API\n& calculators"]:::data
        Facts["Facts API\nscenario models"]:::data
        Insights["Insight formatter\nnarrative blocks"]:::data
    end
    style ANALYTICS fill:#f0f9ff,stroke:#bae6fd,stroke-dasharray:8 4

    subgraph DATA["Data & Storage"]
        Database["Operational database\n(conversations, metrics, quotes)"]:::data
        Audit["Audit trail\nlineage & replay"]:::data
    end
    style DATA fill:#f8fafc,stroke:#bae6fd,stroke-dasharray:8 4

    subgraph INGEST["Ingestion & Background"]
        Ingestion["Ingestion manager\non-demand loaders"]:::orchestrator
        Queue["Task queue\n(background jobs)"]:::ops
    end
    style INGEST fill:#f5f3ff,stroke:#e9d5ff,stroke-dasharray:8 4

    subgraph OPS["Platform Operations"]
        Keyring["Secrets vault\n(API keys)"]:::ops
        Config["Config (.env)\nfeature flags"]:::ops
        Observability["Observability\nlogs & health"]:::ops
    end
    style OPS fill:#f8fafc,stroke:#cbd5f5,stroke-dasharray:8 4

    subgraph ARTIFACT["Delivery & Artifacts"]
        ChatSurface["Chat surfaces\n(web, CLI transcripts)"]:::artifact
        Exporters["Artifact exporters\n(CSV, PPTX, PDF)"]:::artifact
    end
    style ARTIFACT fill:#fff5f7,stroke:#fbcfe8,stroke-dasharray:8 4

    subgraph SOURCES["External Data Providers"]
        Edgar["SEC EDGAR"]:::external
        Yahoo["Yahoo Finance"]:::external
        Stooq["Stooq"]:::external
        Bloomberg["Bloomberg\n(optional)"]:::external
    end
    style SOURCES fill:#faf5ff,stroke:#e9d5ff,stroke-dasharray:8 4

    WebUI --> Auth
    CLI --> Auth
    Batch --> Auth
    Auth --> Ingress

    Ingress --> Session
    Session --> Planner
    Planner --> Session
    Session --> Generator
    Generator --> Composer

    Session --> Analytics
    Planner --> Analytics
    Analytics --> Metrics
    Analytics --> Facts
    Metrics --> Insights
    Facts --> Insights
    Insights --> Composer
    Composer --> ChatSurface
    Composer --> Exporters

    Analytics --> Database
    Database --> Analytics
    Session --> Database
    Session --> Audit
    Analytics --> Audit
    Audit --> Exporters

    Analytics -. data gap .-> Ingestion
    Ingestion --> Queue
    Queue --> Ingestion
    Ingestion --> Database
    Ingestion --> Edgar
    Ingestion --> Yahoo
    Ingestion --> Stooq
    Ingestion --> Bloomberg

    Keyring --> Session
    Keyring --> Ingestion
    Config --> Ingress
    Config --> Analytics
    Config --> Ingestion
    Queue --> Observability
    Analytics --> Observability
    Session --> Observability
```

Layer colors reinforce separation of concerns: yellow for front-end channels, green for orchestration, purple-lavender for LLM services, blue for analytics and storage, gray for platform operations, pink for delivery artifacts, and violet for external data providers.

**Interaction walk-through**
- Front-end clients (terminal, FastAPI-driven web UI, or batch API) capture a prompt and send it to the orchestrator.
- The orchestrator validates context, enriches the prompt, and delegates planning to the text-to-SQL / task LLM components.
- Planned queries execute against the financial datastore and analytics pipeline, producing structured metrics and facts.
- Result processors derive narratives, charts, and audit metadata, then package the response for the chat UI and downstream artifacts such as slides.

### Component Annotations
| Component | Layer | Responsibilities | Key Implementations |
| --- | --- | --- | --- |
| Input prompt (CLI, Web UI, API) | Front-End | Capture user questions, enforce basic validation, forward payload to orchestrator | main.py, webui/app.js, REST /chat endpoint |
| Prompt ingress | Back-End | Authenticate requests, bind conversation context, normalise prompt payloads | src/finanlyzeos_chatbot/web.py::chat, BenchmarkOSChatbot |
| Plan query | Back-End / LLM | Expand prompt into structured tasks and SQL plans | src/finanlyzeos_chatbot/chatbot.py::_handle_*, AnalyticsEngine.metric_value |
| Execute analytics query | Analytics | Run SQL/metric lookups, compute derived metrics, fetch facts | AnalyticsEngine.refresh_metrics, database.fetch_* |
| Analyse results | Insights / LLM | Interpret metrics, detect gaps, prepare narrative building blocks | chat_metrics.format_metrics_table, AnalyticsEngine.run_scenario |
| Package reply | Insights | Assemble narrative, tables, charts, audit links | src/finanlyzeos_chatbot/web.py::chat, response composer |
| Render output & artifacts | Front-End | Stream reply to UI, generate downloads (CSV, PPTX) | webui/app.js, exporters under docs/ |

### End-to-End Timeline
1. **Conversation capture** – terminal and FastAPI entry points (main.py, /chat) serialise each prompt, attach conversation metadata, and queue it for orchestration.
2. **Guardrails & enrichment** – BenchmarkOSChatbot validates context (auth, project scope), injects previous exchanges, and enriches the prompt with defaults like base tickers or fiscal calendars.
3. **Intent planning** – specialised handlers (_metrics_, _scenario_, _ingest_) translate natural-language requests into structured tasks, leveraging the LLM planner where required.
4. **Data execution** – the analytics layer hydrates the plan: SQL runs against SQLite/Postgres, fact tables are assembled, and quote gaps trigger on-demand loaders (Yahoo Finance, Stooq).
5. **Insight generation** – numerical outputs are formatted into narratives, tabular comparisons, and guardrail notices; unresolved tickers surface suggestions or ingest prompts.
6. **Response packaging** – the orchestrator composes the final payload (narrative paragraphs, tables, chart specs, audit trails) and returns it to the caller.
7. **Artifact publishing** – the web UI renders the transcript, while optional exporters emit CSV extracts, slides, or PDF summaries for stakeholders.

### Operational Notes
- **Concurrency & scalability** – uvicorn serves the FastAPI app asynchronously; labour-intensive ingests run in the background task manager (src/finanlyzeos_chatbot/tasks.py).
- **Auditability** – every prompt, metric snapshot, audit event, and scenario result is persisted via database.py, enabling replay and compliance reporting.
- **Extensibility** – LLM adapters live in llm_client.py; conforming to the LLMClient protocol allows swapping providers without touching orchestration code.
- **Reliability** – ingestion scripts (ingest_*) implement exponential backoff, checkpointing, and resumability to keep the analytics cache aligned with market filings.
