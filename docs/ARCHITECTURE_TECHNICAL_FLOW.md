# System Architecture: Technical Flow with Advanced RAG

## Table of Contents

1. [Overview](#overview)
2. [System Architecture Overview](#system-architecture-overview)
3. [Frontend Interface](#frontend-interface)
4. [Backend Logic](#backend-logic)
   - [API & Orchestration](#1-api--orchestration)
   - [Analytics & NLP](#2-analytics--nlp)
   - [RAG Orchestrator](#3-rag-orchestrator)
   - [Metrics Query & Derivation](#4-metrics-query--derivation)
   - [LLM Response Engine](#5-llm-response-engine)
   - [Post-Generation Verification](#6-post-generation-verification)
   - [Response Processing & Assembly](#7-response-processing--assembly)
5. [Data Pipeline](#data-pipeline)
6. [Complete Query Flow Example](#complete-query-flow-example)
7. [Key Features Integration](#key-features-integration)
8. [Performance Characteristics](#performance-characteristics)
9. [Summary](#summary)

---

## Overview

This document provides a detailed technical flow description of FinalyzeOS, incorporating all 16 advanced RAG features into the system architecture.

---

## System Architecture Overview

The FinalyzeOS system consists of three main logical sections:

1. **Frontend Interface**: WebUI for user interaction
2. **Backend Logic**: Complete RAG pipeline with all advanced features
3. **Data Pipeline**: Data ingestion, computation, storage, and vector indexing

---

## Frontend Interface

### WebUI (Browser Interface)

The frontend provides a web-based chat interface where users can:
- Enter natural language queries (e.g., "Can you compare Apple and Meta in FY2024?")
- View system responses with visualizations (bar charts, pie charts, line graphs)
- See citations and confidence indicators
- Interact with the chatbot in real-time

**User Query Example**: "Can you compare Apple and Meta in FY2024?"

**System Response**: Includes formatted answer with visualizations, citations, and confidence indicators.

---

## Backend Logic

### 1. API & Orchestration

**Function**: Route and manage requests.

**Process**:
- Receives user query from WebUI
- Routes to appropriate handler (`chatbot.ask()`)
- Manages conversation state
- Handles request/response lifecycle

**Output**: Routed query to Analytics & NLP.

---

### 2. Analytics & NLP

**Function**: Understand intent and normalize prompt.

**Components**:

**Query Parsing** (`parse_to_structured`):
- Extracts tickers (e.g., AAPL, META)
- Identifies metrics and intent
- Handles spelling mistakes (90% company name success, 100% metric success)
- Supports 150+ question patterns and 40+ intent types

**Intent Detection** (`IntentPolicyManager`):
- Detects intent type: METRIC_LOOKUP, WHY, COMPARE, RISK, FORECAST, or GENERAL
- Selects appropriate retrieval policy based on intent
- Each intent has optimized retrieval strategy

**Temporal Parsing** (`TemporalQueryParser`):
- Parses temporal expressions: "FY2023", "last year", "last 5 years", "from 2020 to 2023"
- Creates TimeFilter with fiscal_years, quarters, or date ranges
- Enables time-scoped document filtering

**Query Rewriting**:
- Rewrites query based on detected intent
- Adds intent-specific instructions (e.g., "Focus on risk factors" for RISK intent)

**Output**: Structured query with tickers, intent, time filter, and retrieval policy.

---

### 3. RAG Orchestrator

**Function**: Complete RAG pipeline with all 16 advanced features.

The RAG Orchestrator is the central component that coordinates all retrieval and generation features. It processes queries through multiple stages:

#### A. Query Analysis & Routing

**Components**:

**Table Query Detection** (`TableAwareRetriever`):
- Checks if query asks for table data (keywords: "by segment", "by region", "breakdown")
- Routes to table-specific retrieval if detected

**Knowledge Graph Query Detection** (`KGRAGHybrid`):
- Checks if query asks about relationships (keywords: "relationship", "common", "both")
- Routes to KG+RAG hybrid retrieval if detected

**Complexity Detection** (`RAGController`):
- Analyzes query complexity (SIMPLE, MODERATE, COMPLEX)
- Decides whether to use multi-hop retrieval

**Output**: Routing decision (table query, KG query, multi-hop needed)

---

#### B. Hybrid Retrieval Layer

The hybrid retrieval layer combines multiple retrieval methods for robustness:

**B1. SQL Deterministic Retrieval**

**Sources**: SQLite/PostgreSQL database
- `metric_snapshots`: Computed metrics
- `financial_facts`: Structured facts
- Data sources: SEC, Yahoo Finance, FRED, IMF

**Process**:
- Queries database for exact metrics and facts
- Returns structured data with precise numbers
- No semantic search needed for structured data

**Output**: Exact metrics (e.g., revenue, profit, margins) for specified tickers and periods

---

**B2. Hybrid Semantic Search (Sparse + Dense)**

This is the core innovation that combines two retrieval methods:

**B2a. Dense Retrieval (Embeddings)**

**Components**:
- `VectorStore` (ChromaDB)
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions)
- Collections: `sec_narratives`, `uploaded_documents`

**Process**:
1. Embeds query using sentence transformer
2. Searches ChromaDB using cosine similarity
3. Returns top-K most semantically similar chunks

**Output**: Top-20 relevant document chunks based on semantic meaning

**B2b. Sparse Retrieval (BM25)**

**Components**:
- `SparseRetriever` (rank-bm25)
- BM25 algorithm for keyword matching

**Process**:
1. Tokenizes query and documents
2. Computes BM25 scores based on keyword frequency
3. Returns top-K chunks with highest keyword overlap

**Output**: Top-20 relevant document chunks based on exact keywords

**B2c. Hybrid Fusion**

**Components**:
- `SourceFusion.fuse_sparse_dense()`

**Process**:
1. Normalizes dense scores to [0, 1] range
2. Normalizes sparse scores to [0, 1] range
3. Fuses scores: `fused_score = 0.6 * dense_score + 0.4 * sparse_score`
4. Ranks by fused score
5. Returns top-K unified results

**Output**: Top-10 unified ranked chunks combining semantic and keyword relevance

**Benefits**:
- Dense retrieval excels at semantic understanding
- Sparse retrieval excels at exact phrases, ticker variants, misspellings
- Fusion gives best of both worlds

---

**B3. Table-Aware Retrieval**

**Components**:
- `StructureAwareParser`: Parses tables from documents
- `TableAwareRetriever`: Routes table queries

**Process** (if table query detected):
1. Parses tables from SEC filings (markdown-style or structured)
2. Extracts table headers and rows
3. Serializes as structured text: "Table: Segment Revenue | Segment=Services | FY2023 | Revenue=85.1B"
4. Returns structured table data

**Output**: Structured table data for queries asking for breakdowns

---

**B4. Knowledge Graph Retrieval**

**Components**:
- `KnowledgeGraph`: Entity/relation extraction
- `KGRAGHybrid`: Hybrid KG+RAG approach

**Process** (if relationship query detected):
1. Extracts entities from documents (companies, segments, products, risks, metrics)
2. Extracts relations ("has_segment", "faces_risk", "has_metric")
3. Builds knowledge graph (using networkx)
4. Traverses graph to find related entities
5. Uses RAG to explain relations

**Output**: Related entities and explanations for relationship queries

---

#### C. Advanced Processing Pipeline

**C1. Temporal Filtering**

**Components**:
- `TemporalQueryParser.apply_time_filter()`

**Process**:
1. Applies TimeFilter to retrieved documents
2. Filters SEC chunks by fiscal_year or filing_date
3. Filters uploaded docs by date range
4. Ensures consistent time horizons for comparisons

**Output**: Time-filtered documents matching query's temporal scope

---

**C2. Cross-Encoder Reranking**

**Components**:
- `Reranker`: Cross-encoder model from sentence-transformers

**Process**:
1. Takes top-K chunks from initial retrieval (e.g., 20)
2. Re-scores each (query, chunk) pair using cross-encoder
3. Cross-encoder provides better relevance scoring than bi-encoder
4. Reorders chunks by true relevance
5. Returns top-N most relevant (e.g., 5-10)

**Output**: Top-N most relevant chunks (10-20% improvement in precision)

---

**C3. Source Fusion & Confidence**

**Components**:
- `SourceFusion`: Score normalization and confidence computation

**Process**:
1. Normalizes scores across sources (SEC narratives, uploaded docs, metrics)
2. Applies reliability weights:
   - SQL metrics: 1.0 (most reliable)
   - SEC narratives: 0.9 (highly reliable)
   - Uploaded docs: 0.7 (less reliable)
   - Macro data: 0.6 (context only)
3. Computes fused scores: `fused_score = normalized_score * source_weight`
4. Calculates overall confidence: weighted average of top-K fused scores

**Output**: Fused documents with normalized scores and overall confidence (0-1)

---

**C4. Multi-Hop Retrieval**

**Components**:
- `RAGController`: Query decomposition and sequential retrieval

**Process** (if complex query):
1. Decomposes complex query into sub-queries
   - Example: "Why did Apple's revenue decline and how does it compare to Microsoft?"
   - Sub-queries:
     - "Why did Apple's revenue decline?"
     - "Apple's revenue metrics"
     - "Microsoft's revenue metrics"
     - "Compare Apple and Microsoft revenue"
2. Performs sequential retrieval for each sub-query
3. Stitches results together
4. Applies reranking and fusion to combined results

**Output**: Comprehensive retrieval result from multiple sequential queries

---

#### D. Safety & Quality Layer

**D1. Grounded Decision Layer**

**Components**:
- `GroundedDecisionLayer`: Safety checks before answering

**Process**:
1. Checks overall retrieval confidence
   - If confidence < 0.3 → Don't answer
2. Verifies minimum document count
   - If no documents retrieved → Don't answer
3. Detects contradictions
   - If contradictory information found → Flag warning
4. Returns decision: `should_answer` (True/False)
5. Provides suggested response if low confidence

**Output**: Decision whether to answer, with suggested response if needed

---

**D2. Observability & Guardrails**

**Components**:
- `RAGObserver`: Logging, metrics, guardrails

**Process**:
1. Logs retrieval metrics:
   - Number of documents retrieved (SEC, uploaded)
   - Similarity scores
   - Retrieval time, reranking time
   - Sparse vs dense contributions
2. Applies guardrails:
   - Minimum relevance score threshold (0.3)
   - Maximum context length (15,000 chars)
   - Maximum document count (10)
   - Smart truncation (drops low-scoring chunks first)
3. Detects anomalies:
   - Low score warnings
   - Empty retrieval warnings

**Output**: Logged metrics and filtered results within guardrails

---

**D3. Memory-Augmented RAG**

**Components**:
- `MemoryAugmentedRAG`: Per-conversation document tracking

**Process**:
1. Tracks document access per conversation/user
2. Updates access timestamps
3. Clusters documents by topic
4. Filters uploaded documents by conversation_id

**Output**: Conversation-specific document access tracking

---

#### E. Prompt Engineering Template

**Components**:
- `build_rag_prompt()`: Formats retrieved context into RAG prompt

**Process**:
1. Structures prompt with clear sections:
   - Instructions: "Use ONLY the retrieved data below"
   - Metrics: SQL-retrieved metrics
   - SEC Narratives: Semantic search results
   - Uploaded Documents: User document results
   - Table Data: Structured table data (if applicable)
   - User Question: Original query
   - Task: Instructions for LLM
2. Adds confidence instruction based on overall confidence:
   - High (≥0.7): "Provide a confident, detailed answer"
   - Medium (0.4-0.7): "Provide a helpful answer but acknowledge uncertainties"
   - Low (<0.4): "Be cautious and explicit about information gaps"
3. Formats tables cleanly (if table data present)
4. Includes intent-specific formatting

**Output**: Complete RAG prompt ready for LLM

---

### 4. Metrics Query & Derivation

**Function**: Numeric retrieval and calculations

**Components**:
- `AnalyticsEngine`: Computes derived metrics

**Process**:
1. Retrieves base metrics from database
2. Computes derived metrics:
   - Growth rates (YoY, QoQ)
   - Margins (gross, operating, net)
   - Ratios (P/E, EV/EBITDA, etc.)
3. Portfolio metrics (if portfolio query):
   - Portfolio holdings
   - Exposure data
   - Risk metrics
   - Attribution results
4. ML forecasts (if forecast query):
   - Historical time series
   - Forecast results from 8 ML models
   - Confidence intervals

**Output**: Computed metrics for prompt

---

### 5. LLM Response Engine

**Function**: Generate natural language response

**Components**:
- LLM client (GPT-4 or configured model)

**Input**:
- RAG prompt (from RAG Orchestrator)
- Metrics (from Metrics Query & Derivation)

**Process**:
1. Receives formatted RAG prompt
2. Generates answer using ONLY retrieved context
3. Tone adjusted based on retrieval confidence:
   - High confidence → Confident tone
   - Medium confidence → Cautious tone
   - Low confidence → Explicit about gaps
4. Includes citations (SEC filing URLs, document filenames, metric periods)

**Output**: Natural language response with citations

---

### 6. Post-Generation Verification

**A. Claim-Level Verification**

**Components**:
- `ClaimVerifier`: Sentence-level verification

**Process**:
1. Splits answer into sentences
2. For each sentence:
   - Checks keyword overlap with retrieved documents
   - Labels as: SUPPORTED, CONTRADICTED, or NOT_FOUND
   - Computes confidence score
3. Computes overall verification confidence
4. Decides if regeneration needed:
   - If too many CONTRADICTED or NOT_FOUND → Regenerate
   - If overall confidence < 0.5 → Regenerate

**Output**: Verification result with claim labels and overall confidence

**B. Feedback Collection**

**Components**:
- `FeedbackCollector`: Records user feedback
- `ScoreCalibrator`: Adjusts scores based on feedback

**Process**:
1. Records feedback after user interaction:
   - Query, doc_ids, scores, answer
   - Label: good, bad, or partial
   - Reason (optional)
2. Analyzes feedback patterns
3. Calibrates retrieval scores:
   - Boosts scores from sources with good feedback
   - Reduces scores from sources with bad feedback
4. Adjusts thresholds automatically

**Output**: Feedback recorded for continuous improvement

---

### 7. Response Processing & Assembly

**Function**: Visualize, verify, and format response

**Process**:
1. Formats response with citations
2. Generates visualizations:
   - Bar charts for comparisons
   - Pie charts for breakdowns
   - Line graphs for trends
3. Adds confidence indicators
4. Includes claim verification summary (if enabled)
5. Formats for display

**Output**: Formatted response sent to WebUI

---

## Data Pipeline

### 1. Data Ingestion

**Function**: Fetch and normalize data

**Sources**:
- **SEC EDGAR**: 10-K, 10-Q filings
- **Yahoo Finance**: Real-time prices, P/E ratios, analyst ratings, news
- **FRED**: Macroeconomic indicators (GDP, rates, inflation, VIX)
- **IMF**: Sector benchmarks, macroeconomic data
- **Stooq**: Historical price backfills
- **User Uploads**: Documents uploaded via WebUI

**Process**:
1. Fetches data from external sources
2. Normalizes formats
3. Extracts text from SEC filings
4. Chunks documents (1500 chars, 200 overlap) for semantic search

**Output**: Normalized data ready for processing

---

### 2. Metrics Computation Engine

**Function**: KPI computation and backfill

**Process**:
1. Computes 93+ financial metrics:
   - Revenue, profit, margins
   - Growth rates (YoY, QoQ)
   - Ratios (P/E, EV/EBITDA, etc.)
2. Time series backfilling
3. Portfolio calculations
4. ML forecast generation (8 models)

**Output**: Computed metrics stored in database

---

### 3. SQLite Database

**Function**: Store and query structured data

**Tables**:
- `metric_snapshots`: Computed metrics
- `financial_facts`: Structured facts
- `sec_filings`: Filing metadata
- `uploaded_documents`: User documents
- `portfolio_holdings`: Portfolio data
- `ml_forecasts`: Forecast results

**Usage**:
- SQL retrieval for exact metrics/facts
- Metadata for filtering (ticker, period, etc.)
- Provides data to RAG Context Builder and Metrics Query & Derivation

---

### 4. Vector Store (ChromaDB)

**Function**: Semantic search index

**Collections**:
- `sec_narratives`: SEC filing chunks with embeddings
- `uploaded_documents`: User document chunks with embeddings

**Index**:
- HNSW (Hierarchical Navigable Small World) for approximate nearest-neighbor search
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions)

**Process**:
1. Generates embeddings for document chunks
2. Stores embeddings in ChromaDB
3. Enables semantic search via cosine similarity
4. Supports metadata filtering (ticker, conversation_id, etc.)

**Usage**:
- Dense semantic search (embeddings)
- Sparse index (BM25) built from same documents

---

## Complete Query Flow Example

**User Query**: "Can you compare Apple and Meta in FY2024?"

### Step-by-Step Flow:

1. **Frontend**: User enters query in WebUI

2. **API & Orchestration**: Routes query to `chatbot.ask()`

3. **Analytics & NLP**:
   - Parses query: Extracts tickers (AAPL, META), intent (COMPARE), period (FY2024)
   - Detects intent: COMPARE → Uses multi-hop policy, requires same period/units
   - Parses temporal: FY2024 → TimeFilter(fiscal_years=[2024])
   - Rewrites query: Adds comparison-specific instructions

4. **RAG Orchestrator - Query Analysis**:
   - Table query? No
   - KG query? No
   - Complexity: COMPLEX → Use multi-hop

5. **RAG Orchestrator - Hybrid Retrieval**:
   - **SQL Retrieval**: Queries database for Apple and Meta metrics in FY2024
   - **Dense Retrieval**: Embeds query, searches ChromaDB, returns top-20 SEC chunks
   - **Sparse Retrieval**: BM25 keyword matching, returns top-20 chunks
   - **Hybrid Fusion**: Combines dense + sparse, returns top-10 unified chunks

6. **RAG Orchestrator - Advanced Processing**:
   - **Temporal Filtering**: Filters documents to only FY2024
   - **Reranking**: Re-scores chunks, returns top-5 most relevant
   - **Source Fusion**: Normalizes scores, computes confidence=0.75 (high)
   - **Multi-Hop**: Decomposes into sub-queries, retrieves sequentially

7. **RAG Orchestrator - Safety & Quality**:
   - **Grounded Decision**: Confidence=0.75, sufficient docs → should_answer=True
   - **Observability**: Logs metrics, applies guardrails
   - **Memory**: Tracks document access

8. **RAG Orchestrator - Prompt Building**:
   - Formats prompt with metrics, SEC narratives, instructions
   - Adds confidence instruction: "High confidence - provide detailed answer"

9. **Metrics Query & Derivation**:
   - Computes comparison metrics (growth rates, margins, ratios)

10. **LLM Response Engine**:
    - Generates answer using RAG prompt
    - Includes citations and comparisons

11. **Post-Generation Verification**:
    - **Claim Verification**: Verifies each sentence (8 supported, 0 contradicted, 1 not found)
    - **Feedback Collection**: Records for learning

12. **Response Processing & Assembly**:
    - Formats response with citations
    - Generates comparison charts
    - Adds confidence indicators

13. **Frontend**: Displays formatted response with visualizations

---

## Key Features Integration

### All 16 RAG Features in Flow

1. **Hybrid Sparse + Dense Retrieval**: B2a + B2b + B2c (Hybrid Retrieval Layer)
2. **Structure-Aware RAG**: B3 (Table-Aware Retrieval)
3. **Claim-Level Verification**: 6A (Post-Generation Verification)
4. **Intent-Specific Policies**: 2 (Analytics & NLP - Intent Detection)
5. **Temporal RAG**: C1 (Advanced Processing - Temporal Filtering)
6. **Online Feedback**: 6B (Post-Generation Verification - Feedback Collection)
7. **Knowledge Graph**: B4 (Hybrid Retrieval - KG Retrieval)
8. **Cross-Encoder Reranking**: C2 (Advanced Processing - Reranking)
9. **Source Fusion**: C3 (Advanced Processing - Source Fusion)
10. **Grounded Decision**: D1 (Safety & Quality - Grounded Decision)
11. **Retrieval Confidence**: C3 + E (Source Fusion + Prompt Template)
12. **Memory-Augmented RAG**: D3 (Safety & Quality - Memory)
13. **Multi-Hop Retrieval**: C4 (Advanced Processing - Multi-Hop)
14. **Evaluation Harness**: (Used for testing, not in production flow)
15. **Observability**: D2 (Safety & Quality - Observability)
16. **RAG Orchestrator**: Complete pipeline (3 - RAG Orchestrator)

---

## Performance Characteristics

### Latency Breakdown

| Stage | Time | Notes |
|-------|------|-------|
| Query Parsing | 10-20ms | Fast NLP processing |
| Intent Detection | <1ms | Policy lookup |
| Temporal Parsing | <1ms | Regex matching |
| SQL Retrieval | 20-50ms | Database query |
| Dense Retrieval | 50-100ms | Embedding + similarity |
| Sparse Retrieval | 20-50ms | BM25 matching |
| Hybrid Fusion | 5-10ms | Score normalization |
| Reranking | 80-150ms | Cross-encoder scoring |
| Source Fusion | 5-10ms | Score normalization |
| Temporal Filtering | <1ms | Document filtering |
| Grounded Decision | <1ms | Confidence check |
| Prompt Building | 5-10ms | String formatting |
| LLM Generation | 1000-3000ms | GPT-4 API call |
| Claim Verification | 100-200ms | Sentence verification |
| **Total** | **~1300-3600ms** | End-to-end |

### Memory Usage

| Component | Memory | Notes |
|-----------|--------|-------|
| Embedding Model | ~90MB | all-MiniLM-L6-v2 |
| ChromaDB | 50-200MB | Depends on document count |
| BM25 Index | 5-20MB | Depends on document count |
| Knowledge Graph | 10-50MB | Optional |
| **Total** | **~150-360MB** | Typical |

---

## Summary

This architecture document describes the complete technical flow of FinalyzeOS with all 16 advanced RAG features integrated. The system processes queries through:

1. **Frontend**: User interaction via WebUI
2. **Backend**: Complete RAG pipeline with hybrid retrieval, intent policies, temporal awareness, and all advanced features
3. **Data Pipeline**: Ingestion, computation, storage, and vector indexing

The architecture demonstrates production-grade RAG capabilities that go far beyond vanilla RAG, incorporating research-level techniques for enhanced relevance, robustness, and explainability.
