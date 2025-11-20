# Your RAG System: What You Actually Have Now

## Overview

Your chatbot has a **hybrid RAG system** that combines:
1. **SQL Retrieval** - Exact metrics from your database
2. **Semantic Search** - Vector embeddings for narrative text (SEC filings, uploaded docs)
3. **Token Overlap Fallback** - Keyword matching when semantic search isn't available

---

## What's Currently Running

### 1. **SQL Retrieval (Deterministic)**
**Location**: `src/finanlyzeos_chatbot/context_builder.py` → `build_financial_context()`

**What it does**:
- Queries your SQLite database for exact metrics (revenue, earnings, margins, etc.)
- Gets structured data from `metric_snapshots` table
- Retrieves financial facts from `financial_facts` table
- Fetches data from multiple sources: SEC EDGAR, Yahoo Finance, FRED, IMF

**Example**:
```python
# When you ask "What is Apple's revenue?"
# System queries:
SELECT metric, value, period 
FROM metric_snapshots 
WHERE ticker = 'AAPL' AND metric = 'revenue'

# Returns: revenue: $394.3B (FY2023)
```

**Status**: ✅ **Fully working** - This is your primary retrieval method

---

### 2. **Semantic Search for Uploaded Documents**
**Location**: `src/finanlyzeos_chatbot/document_context.py` → `build_uploaded_document_context()`

**What it does**:
- **First tries semantic search** using ChromaDB vector store
- Converts your query to embeddings (384-dim vectors)
- Searches uploaded documents by meaning (not just keywords)
- **Falls back to token overlap** if vector store unavailable

**How it works**:
1. User uploads a PDF/Word doc via web UI
2. Document is **automatically indexed** into ChromaDB (chunked into 1500-char pieces)
3. When you ask a question, it searches these chunks semantically
4. Returns most relevant excerpts

**Example**:
```python
# You upload "Q3_Report.pdf" 
# You ask: "What were the main risks mentioned?"
# System:
# 1. Embeds query: "What were the main risks mentioned?" → vector
# 2. Searches ChromaDB for similar document chunks
# 3. Returns relevant excerpts from your uploaded PDF
```

**Status**: ✅ **Working** - Semantic search enabled with automatic fallback

**Infrastructure**:
- **Vector Store**: ChromaDB with `uploaded_documents` collection
- **Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Chunking**: 1500 characters with 200 overlap
- **Indexing**: Automatic on upload via `web.py`

---

### 3. **Token Overlap Fallback**
**Location**: `src/finanlyzeos_chatbot/document_context.py` → `build_uploaded_document_context()`

**What it does**:
- If semantic search fails or isn't available, uses keyword matching
- Tokenizes your query and document text
- Scores chunks by overlapping tokens
- Returns best-matching snippets

**Status**: ✅ **Working** - Always available as fallback

---

## Current Integration in Chatbot

### How It Works Now

**In `chatbot.py` → `ask()` method**:

```python
# Step 1: Build uploaded document context (with semantic search)
doc_context = build_uploaded_document_context(
    user_input,
    conversation_id,
    database_path,
    use_semantic_search=True,  # ✅ Enabled!
)

# Step 2: Build financial context (SQL retrieval)
context = build_financial_context(
    query=user_input,
    analytics_engine=self.analytics_engine,
    database_path=database_path,
    max_tickers=3,
    include_macro_context=True
)

# Step 3: Combine and send to LLM
full_context = f"{context}\n\n{doc_context}" if doc_context else context
reply = llm_client.generate_reply([...])
```

**Flow**:
1. User asks question
2. System retrieves:
   - SQL metrics (from `build_financial_context()`)
   - Uploaded docs (from `build_uploaded_document_context()` with semantic search)
3. Combines both into context
4. Sends to GPT-4
5. GPT-4 generates answer using retrieved context

---

## What You Have vs. What's Available

### ✅ **Currently Active in Chatbot**

1. **SQL Retrieval** - ✅ Active (via `build_financial_context()`)
2. **Semantic Search for Uploaded Docs** - ✅ Active (via `build_uploaded_document_context()`)
3. **Token Overlap Fallback** - ✅ Active (automatic fallback)

### 🔧 **Available But Not Yet Integrated**

These modules exist but are **not yet wired into the main chatbot flow**:

1. **RAGRetriever** (`rag_retriever.py`) - Unified retrieval interface
2. **Reranker** (`rag_reranker.py`) - Cross-encoder reranking
3. **Source Fusion** (`rag_fusion.py`) - Score normalization
4. **Grounded Decision Layer** (`rag_grounded_decision.py`) - Safety checks
5. **Memory-Augmented RAG** (`rag_memory.py`) - Document tracking
6. **Multi-Hop Controller** (`rag_controller.py`) - Query decomposition
7. **RAG Orchestrator** (`rag_orchestrator.py`) - Complete pipeline
8. **RAG Prompt Template** (`rag_prompt_template.py`) - Structured prompts

**To use these**: You'd need to modify `chatbot.ask()` to use `RAGOrchestrator` instead of the current `build_financial_context()` + `build_uploaded_document_context()` approach.

---

## Data Sources

### What Gets Retrieved

**SQL Retrieval** (via `build_financial_context()`):
- ✅ Metrics from database (revenue, earnings, margins, etc.)
- ✅ Financial facts from SEC filings
- ✅ Yahoo Finance data (prices, ratios)
- ✅ FRED economic indicators
- ✅ IMF sector KPIs
- ✅ Portfolio data (if portfolio queries)
- ✅ ML forecasts (if forecasting queries)

**Semantic Search** (via `build_uploaded_document_context()`):
- ✅ User-uploaded PDFs, Word docs, text files
- ✅ Filtered by conversation_id (only your conversation's docs)

**Not Yet Indexed for Semantic Search**:
- ⚠️ SEC filing narratives (MD&A, Risk Factors) - infrastructure exists but not indexed
- ⚠️ Yahoo Finance news - not indexed

---

## Technical Details

### Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Architecture**: 6-layer BERT encoder
- **Performance**: ~50ms per document embedding

### Vector Store
- **Technology**: ChromaDB
- **Storage**: SQLite + numpy arrays
- **Indexing**: HNSW (Hierarchical Navigable Small World) graph
- **Search Time**: ~5-10ms for 10K-100K documents

### Chunking
- **Size**: 1500 characters per chunk
- **Overlap**: 200 characters
- **Why**: Prevents breaking mid-sentence, fits within model limits

---

## Example: How It Works End-to-End

**User Query**: "What is Apple's revenue, and what does the uploaded report say about their risks?"

**Step 1: SQL Retrieval**
```
build_financial_context() queries database:
→ Finds: revenue = $394.3B (FY2023)
→ Adds to context
```

**Step 2: Semantic Search**
```
build_uploaded_document_context() searches ChromaDB:
→ Embeds query: "what does the uploaded report say about their risks"
→ Searches uploaded_documents collection
→ Finds relevant chunks from uploaded PDF
→ Returns: "The company faces risks related to supply chain disruptions..."
```

**Step 3: Combine**
```
Context = SQL metrics + Semantic search results
→ Sent to GPT-4
```

**Step 4: Generate**
```
GPT-4 receives:
- "Apple's revenue is $394.3B"
- "Uploaded report mentions: supply chain risks..."

GPT-4 generates answer using both sources
```

---

## Summary: What You Actually Have

### ✅ **Working Now**
1. **SQL Retrieval** - Exact metrics from database ✅
2. **Semantic Search for Uploaded Docs** - Vector search with automatic indexing ✅
3. **Token Overlap Fallback** - Keyword matching when needed ✅
4. **Automatic Document Indexing** - Documents indexed on upload ✅
5. **Conversation Filtering** - Only searches your conversation's docs ✅

### 🔧 **Available But Not Active**
- Cross-encoder reranking
- Source fusion
- Grounded decision layer
- Memory-augmented tracking
- Multi-hop retrieval
- RAG orchestrator

### 📊 **Current Architecture**

```
User Query
    ↓
┌─────────────────────────────────────┐
│  Current RAG (What's Running)      │
│                                     │
│  1. build_financial_context()      │
│     → SQL retrieval (metrics)      │
│                                     │
│  2. build_uploaded_document_       │
│     context()                       │
│     → Semantic search (ChromaDB)    │
│     → Token overlap (fallback)     │
└─────────────────────────────────────┘
    ↓
Combined Context → GPT-4 → Answer
```

---

## Bottom Line

**Your chatbot currently has**:
- ✅ **Hybrid RAG**: SQL + semantic search working together
- ✅ **Automatic indexing**: Uploaded docs automatically searchable
- ✅ **Robust fallback**: Token overlap if semantic search fails
- ✅ **Multi-source**: SQL pulls from SEC, Yahoo, FRED, IMF

**What's available but not yet integrated**:
- Advanced features (reranking, fusion, multi-hop) exist as separate modules
- Can be integrated by switching to `RAGOrchestrator` in `chatbot.ask()`

**Your RAG is functional and production-ready** for the current use case. The advanced features are available when you're ready to integrate them.

