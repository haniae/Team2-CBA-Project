# BenchmarkOS Chatbot Architecture

This workflow mirrors the product storyboard: user prompts begin on the client surfaces, traverse back-end planners and analytics engines, then return enriched responses to the chat surface.

```mermaid
flowchart LR
    classDef front fill:#ffe57f,stroke:#d4a017,stroke-width:2px,color:#463c00,font-weight:bold
    classDef llm fill:#a8f0d8,stroke:#2f9e80,stroke-width:2px,color:#064340,font-weight:bold
    classDef sql fill:#8dc5ff,stroke:#1d6ee6,stroke-width:2px,color:#0b2c72,font-weight:bold
    classDef insight fill:#cabdff,stroke:#6d4dd7,stroke-width:2px,color:#2e1c62,font-weight:bold
    classDef speech fill:#ffffff,stroke:#94a3b8,stroke-width:2px,color:#1f2937

    subgraph FrontEnd["Front-End Interfaces"]
        direction TB
        userPrompt(["Input prompt\n(CLI, Web UI, API)"]):::front
        agentAvatar(["Chat session\ncontext & controls"]):::speech
        renderOutput(["Return final output\n(chat transcript)"]):::front
        publishArtifacts(["Generate packaged artifacts\n(tables, charts, slides)"]):::insight
    end
    style FrontEnd fill:#f8fafc,stroke:#cbd5f5,stroke-dasharray:8 4

    subgraph BackEnd["Back-End Services"]
        direction TB
        promptIngress(["Input prompt\n(validation & routing)"]):::front
        planQuery(["Convert to structured plan\n(prompt planner + LLM)"]):::llm
        runSQL(["Execute analytics query\n(AnalyticsEngine + database)"]):::sql
        analyzeResults(["Analyze query result\n(metric scripts, enrichers)"]):::llm
        packageReply(["Package narrative & evidence\n(response composer)"]):::insight
    end
    style BackEnd fill:#f0f9ff,stroke:#a5d8ff,stroke-dasharray:8 4

    userPrompt --> promptIngress
    promptIngress --> planQuery
    planQuery --> runSQL
    runSQL --> analyzeResults
    analyzeResults --> packageReply
    packageReply --> renderOutput
    renderOutput --> publishArtifacts
    userPrompt --> agentAvatar
    agentAvatar --> renderOutput

    subgraph Legend["Diagram keys"]
        direction LR
        keyFront(["User-facing surfaces"]):::front
        keyPlanner(["LLM orchestration"]):::llm
        keySQL(["Analytics & SQL layer"]):::sql
        keyInsight(["Narrative & visualization"]):::insight
    end
    style Legend fill:#ffffff,stroke:#e2e8f0,stroke-width:1.5px
```

**Interaction walk-through**
- Front-end clients (terminal, FastAPI-driven web UI, or batch API) capture a prompt and send it to the orchestrator.
- The orchestrator validates context, enriches the prompt, and delegates planning to the text-to-SQL / task LLM components.
- Planned queries execute against the financial datastore and analytics pipeline, producing structured metrics and facts.
- Result processors derive narratives, charts, and audit metadata, then package the response for the chat UI and downstream artifacts such as slides.

### Component Annotations
| Component | Layer | Responsibilities | Key Implementations |
| --- | --- | --- | --- |
| Input prompt (CLI, Web UI, API) | Front-End | Capture user questions, enforce basic validation, forward payload to orchestrator | main.py, webui/app.js, REST /chat endpoint |
| Prompt ingress | Back-End | Authenticate requests, bind conversation context, normalise prompt payloads | src/benchmarkos_chatbot/web.py::chat, BenchmarkOSChatbot |
| Plan query | Back-End / LLM | Expand prompt into structured tasks and SQL plans | src/benchmarkos_chatbot/chatbot.py::_handle_*, AnalyticsEngine.metric_value |
| Execute analytics query | Analytics | Run SQL/metric lookups, compute derived metrics, fetch facts | AnalyticsEngine.refresh_metrics, database.fetch_* |
| Analyse results | Insights / LLM | Interpret metrics, detect gaps, prepare narrative building blocks | chat_metrics.format_metrics_table, AnalyticsEngine.run_scenario |
| Package reply | Insights | Assemble narrative, tables, charts, audit links | src/benchmarkos_chatbot/web.py::chat, response composer |
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
- **Concurrency & scalability** – uvicorn serves the FastAPI app asynchronously; labour-intensive ingests run in the background task manager (src/benchmarkos_chatbot/tasks.py).
- **Auditability** – every prompt, metric snapshot, audit event, and scenario result is persisted via database.py, enabling replay and compliance reporting.
- **Extensibility** – LLM adapters live in llm_client.py; conforming to the LLMClient protocol allows swapping providers without touching orchestration code.
- **Reliability** – ingestion scripts (ingest_*) implement exponential backoff, checkpointing, and resumability to keep the analytics cache aligned with market filings.
