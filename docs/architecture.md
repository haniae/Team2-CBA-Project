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
