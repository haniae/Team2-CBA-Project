# System Flow: How a Query is Processed

## Overview

This document traces a single user query through the entire FinalyzeOS system, showing exactly what happens **before** and **after** a prompt is sent. This provides a complete understanding of how the system actually solves a user's question.

---

## Example Query

**User Query**: "Can you compare Apple and Meta's revenue in FY2024?"

---

## Part 1: BEFORE the Prompt is Sent

### System Initialization (Happens Once at Startup)

**1. Application Startup**
- Web server starts (`serve_chatbot.py` or `run_chatbot.py`)
- Database connection initialized
- Settings loaded from configuration

**2. Chatbot Instance Creation**
- `FinanlyzeOSChatbot.create()` is called
- Components initialized:
  - `AnalyticsEngine`: For metric calculations
  - `LLMClient`: For GPT-4 API calls
  - `Settings`: Configuration and database paths
  - `Conversation`: Conversation state management

**3. RAG Orchestrator Lazy Initialization (Prepared but Not Yet Created)**
- RAG Orchestrator is NOT created yet (lazy initialization)
- Components are ready to be initialized when first query arrives

**4. Vector Store Initialization (If Available)**
- ChromaDB client initialized
- Embedding model loaded: `all-MiniLM-L6-v2` (384 dimensions)
- Collections checked: `sec_narratives`, `uploaded_documents`
- Sparse retriever prepared (BM25 index will be built on first use)

**5. Database Connection**
- SQLite/PostgreSQL connection established
- Tables verified: `metric_snapshots`, `financial_facts`, `sec_filings`, etc.

**System is now ready to receive queries.**

---

## Part 2: WHEN the Prompt is Sent

### Step 1: Query Reception (Frontend → Backend)

**Location**: `app/serve_chatbot.py` or `run_chatbot.py`

**What Happens**:
1. User types query in WebUI: "Can you compare Apple and Meta's revenue in FY2024?"
2. Frontend sends HTTP POST request to `/api/chat` endpoint
3. Request includes:
   - `message`: The user query
   - `conversation_id`: Current conversation ID (or new one created)
   - Session information

**Code Path**: `POST /api/chat` → `chatbot.ask(user_input, conversation_id)`

---

### Step 2: Chatbot Entry Point

**Location**: `src/finanlyzeos_chatbot/chatbot.py` → `FinanlyzeOSChatbot.ask()`

**What Happens**:
1. Method receives: `user_input` and `conversation_id`
2. Logs incoming query
3. Checks if query is empty or too short
4. Determines if RAG Orchestrator should be used (default: yes)

**Code**: 
```python
def ask(self, user_input: str, conversation_id: Optional[str] = None):
    # Entry point - query received
    LOGGER.info(f"Processing query: {user_input[:100]}")
```

---

### Step 3: RAG Orchestrator Initialization (Lazy)

**Location**: `src/finanlyzeos_chatbot/chatbot.py` → `_get_rag_orchestrator()`

**What Happens** (First Query Only):
1. Checks if `_rag_orchestrator` is None
2. If None, creates `RAGOrchestrator` instance:
   - Initializes `RAGRetriever` with database path and analytics engine
   - Initializes `VectorStore` (ChromaDB) for semantic search
   - Initializes `SparseRetriever` (BM25) for keyword search
   - Initializes `HybridRetriever` (combines sparse + dense)
   - Initializes `IntentPolicyManager` for intent detection
   - Initializes `TemporalQueryParser` for time parsing
   - Initializes `Reranker` for cross-encoder reranking
   - Initializes `SourceFusion` for score normalization
   - Initializes `GroundedDecisionLayer` for safety checks
   - Initializes `MemoryAugmentedRAG` for document tracking
   - Initializes `TableAwareRetriever` for table queries
   - Initializes `ClaimVerifier` for post-generation verification
   - Initializes `FeedbackCollector` for learning
   - Initializes `KnowledgeGraph` (optional)
3. All components are now ready

**Code**:
```python
def _get_rag_orchestrator(self):
    if self._rag_orchestrator is None:
        self._rag_orchestrator = RAGOrchestrator(
            database_path=Path(self.settings.database_path),
            analytics_engine=self.analytics_engine,
            use_hybrid_retrieval=True,
            use_intent_policies=True,
            use_temporal=True,
            # ... all features enabled
        )
```

---

### Step 4: RAG Orchestrator Processing

**Location**: `src/finanlyzeos_chatbot/rag_orchestrator.py` → `RAGOrchestrator.process_query()`

**What Happens**:

#### 4.1 Query Parsing

**Component**: `parse_to_structured()` from `parsing/parse.py`

**Process**:
1. Analyzes query text: "Can you compare Apple and Meta's revenue in FY2024?"
2. Extracts entities:
   - Tickers: ["AAPL", "META"] (with spelling correction if needed)
   - Metrics: ["revenue"]
   - Intent keywords: ["compare"]
3. Returns structured query:
   ```python
   {
       "tickers": [{"ticker": "AAPL"}, {"ticker": "META"}],
       "metrics": ["revenue"],
       "intent": "compare",
       "period": "FY2024"
   }
   ```

**Output**: Structured query with tickers, metrics, intent

---

#### 4.2 Intent Detection & Policy Selection

**Component**: `IntentPolicyManager.detect_intent()`

**Process**:
1. Analyzes query for intent keywords:
   - "compare" → Detects COMPARE intent
2. Selects retrieval policy:
   ```python
   RetrievalPolicy(
       intent=COMPARE,
       use_multi_hop=True,      # Complex queries need multi-hop
       k_docs=10,                # More documents for comparison
       narrative_weight=0.6,     # Balance narratives and metrics
       metric_weight=0.8,         # High metric weight for comparison
       require_same_period=True,  # Critical for comparisons
       require_same_units=True,   # Critical for comparisons
   )
   ```
3. Rewrites query with comparison-specific instructions:
   - Adds: "Ensure same reporting period and units for comparison."

**Output**: Intent=COMPARE, Policy selected, Query rewritten

---

#### 4.3 Temporal Parsing

**Component**: `TemporalQueryParser.parse_time_filter()`

**Process**:
1. Analyzes query for temporal expressions:
   - "FY2024" → Detected
2. Parses fiscal year:
   - Extracts: 2024
3. Creates TimeFilter:
   ```python
   TimeFilter(
       fiscal_years=[2024],
       start_date=None,
       end_date=None,
   )
   ```

**Output**: TimeFilter for FY2024

---

#### 4.4 Query Analysis & Routing

**Component**: `TableAwareRetriever.is_table_query()`, `KGRAGHybrid.is_relationship_query()`, `RAGController.decompose_query()`

**Process**:
1. **Table Query Check**:
   - Checks for keywords: "by segment", "by region", "breakdown"
   - Result: No (query doesn't ask for table breakdown)

2. **KG Query Check**:
   - Checks for keywords: "relationship", "common", "both"
   - Result: No (query doesn't ask about relationships)

3. **Complexity Detection**:
   - Analyzes query complexity
   - Two tickers + comparison + temporal → COMPLEX
   - Decision: Use multi-hop retrieval

**Output**: Routing decisions (no table, no KG, use multi-hop)

---

### Step 5: Hybrid Retrieval Layer

**Location**: `src/finanlyzeos_chatbot/rag_retriever.py` → `RAGRetriever.retrieve()`

#### 5.1 SQL Deterministic Retrieval

**Component**: `RAGRetriever._retrieve_sql_data()`

**Process**:
1. For each ticker (AAPL, META):
   - Queries `metric_snapshots` table:
     ```sql
     SELECT * FROM metric_snapshots 
     WHERE ticker = 'AAPL' AND metric = 'revenue' AND period = 'FY2024'
     ```
   - Queries `financial_facts` table:
     ```sql
     SELECT * FROM financial_facts 
     WHERE ticker = 'AAPL' AND period = 'FY2024'
     ```
2. Retrieves exact numbers:
   - AAPL revenue FY2024: $394.3B
   - META revenue FY2024: $134.9B
   - Additional metrics: profit, margins, growth rates

**Output**: Structured metrics and facts for both companies

---

#### 5.2 Hybrid Semantic Search (Sparse + Dense)

**Component**: `HybridRetriever.retrieve_sec_narratives()`

**Process**:

**5.2a. Dense Retrieval (Embeddings)**:
1. Embeds query using sentence transformer:
   - Query: "Can you compare Apple and Meta's revenue in FY2024?"
   - Embedding: 384-dimensional vector
2. Searches ChromaDB `sec_narratives` collection:
   - Filters by ticker: `{"ticker": "AAPL"}` and `{"ticker": "META"}`
   - Cosine similarity search
   - Returns top-20 most semantically similar chunks
3. Results include:
   - SEC filing excerpts (MD&A, Risk Factors)
   - Similarity scores (0.0-1.0, where 1.0 = identical)

**5.2b. Sparse Retrieval (BM25)**:
1. Tokenizes query: ["can", "you", "compare", "apple", "meta", "revenue", "fy2024"]
2. Searches BM25 index:
   - Computes BM25 scores for each document
   - Keyword matching: "Apple", "Meta", "revenue", "FY2024"
   - Returns top-20 chunks with highest keyword overlap
3. Results include:
   - Documents with exact keyword matches
   - BM25 scores (higher = more keyword overlap)

**5.2c. Hybrid Fusion**:
1. Normalizes dense scores to [0, 1] range
2. Normalizes sparse scores to [0, 1] range
3. Fuses scores:
   ```python
   fused_score = 0.6 * dense_score + 0.4 * sparse_score
   ```
4. Ranks by fused score
5. Returns top-10 unified ranked chunks

**Output**: Top-10 fused SEC narrative chunks

---

#### 5.3 Uploaded Documents Retrieval

**Component**: `HybridRetriever.retrieve_uploaded_docs()`

**Process** (if conversation has uploaded documents):
1. Filters by `conversation_id`
2. Performs same hybrid retrieval (dense + sparse + fusion)
3. Returns top-3 uploaded document chunks

**Output**: Top-3 uploaded document chunks (if any)

---

### Step 6: Advanced Processing Pipeline

#### 6.1 Temporal Filtering

**Component**: `TemporalQueryParser.apply_time_filter()`

**Process**:
1. Applies TimeFilter to retrieved documents:
   - Checks each document's `fiscal_year` metadata
   - Keeps only documents with `fiscal_year == 2024`
   - Filters out documents from other years
2. Result:
   - Before: 10 SEC chunks
   - After: 7 SEC chunks (3 filtered out for wrong year)

**Output**: Time-filtered documents (only FY2024)

---

#### 6.2 Cross-Encoder Reranking

**Component**: `Reranker.rerank_multi_source()`

**Process**:
1. Takes all retrieved chunks (7 SEC + 3 uploaded)
2. For each chunk:
   - Creates (query, chunk) pair
   - Scores using cross-encoder model
   - Cross-encoder provides better relevance than bi-encoder
3. Reorders chunks by true relevance
4. Returns top-5 SEC chunks and top-2 uploaded chunks

**Output**: Top-5 SEC + top-2 uploaded (reranked by relevance)

---

#### 6.3 Source Fusion & Confidence

**Component**: `SourceFusion.fuse_all_sources()`

**Process**:
1. Normalizes scores for each source:
   - SEC narratives: Normalize to [0, 1]
   - Uploaded docs: Normalize to [0, 1]
2. Applies reliability weights:
   - SEC narratives: weight = 0.9 (highly reliable)
   - Uploaded docs: weight = 0.7 (less reliable)
3. Computes fused scores:
   ```python
   fused_score = normalized_score * source_weight
   ```
4. Calculates overall confidence:
   ```python
   overall_confidence = average(top_5_fused_scores) = 0.75
   ```
5. Confidence level: High (≥0.7)

**Output**: Fused documents with normalized scores, overall_confidence = 0.75

---

#### 6.4 Multi-Hop Retrieval

**Component**: `RAGController.execute_multi_hop()`

**Process** (because query is COMPLEX):
1. Decomposes query into sub-queries:
   - Sub-query 1: "Apple revenue FY2024"
   - Sub-query 2: "Meta revenue FY2024"
   - Sub-query 3: "Apple SEC narratives FY2024"
   - Sub-query 4: "Meta SEC narratives FY2024"
2. Executes sequential retrieval:
   - Step 1: Retrieve Apple metrics and narratives
   - Step 2: Retrieve Meta metrics and narratives
   - Step 3: Combine results
3. Applies reranking and fusion to combined results

**Output**: Comprehensive retrieval result from multiple sequential queries

---

### Step 7: Safety & Quality Layer

#### 7.1 Grounded Decision Layer

**Component**: `GroundedDecisionLayer.make_decision()`

**Process**:
1. Checks overall confidence: 0.75 (high)
   - Threshold: 0.3
   - Decision: Confidence is sufficient
2. Verifies minimum documents:
   - SEC docs: 5 (sufficient)
   - Uploaded docs: 2 (sufficient)
   - Total: 7 documents
3. Checks for contradictions:
   - Compares retrieved documents for conflicting information
   - Result: No contradictions detected
4. Makes decision:
   ```python
   should_answer = True
   suggested_response = None  # No need for low-confidence response
   ```

**Output**: Decision to answer (should_answer = True)

---

#### 7.2 Observability & Guardrails

**Component**: `RAGObserver.log_retrieval()` and `RAGObserver.apply_guardrails()`

**Process**:
1. Logs retrieval metrics:
   - Query: "Can you compare Apple and Meta's revenue in FY2024?"
   - SEC docs: 5
   - Uploaded docs: 2
   - Metrics: 10 (5 per company)
   - Retrieval time: 150ms
   - Reranking time: 80ms
   - Hybrid stats: 3 dense contributions, 2 sparse contributions
2. Applies guardrails:
   - Minimum relevance score: 0.3 (all chunks above threshold)
   - Maximum documents: 10 (current: 7, within limit)
   - Maximum context length: 15,000 chars (current: 8,500, within limit)
3. No anomalies detected

**Output**: Logged metrics, guardrails applied

---

#### 7.3 Memory-Augmented RAG

**Component**: `MemoryAugmentedRAG.update_access()`

**Process**:
1. For each retrieved uploaded document:
   - Updates access timestamp
   - Tracks document ID and conversation ID
2. Clusters documents by topic (if multiple documents)
3. Updates memory state

**Output**: Document access tracked in memory

---

### Step 8: Prompt Engineering

**Component**: `build_rag_prompt()` from `rag_prompt_template.py`

**Process**:
1. Formats retrieved context into structured prompt:
   ```
   ╔═══════════════════════════════════════════════════════════════════════════════╗
   ║                    RAG CONTEXT - USE ONLY THE DATA BELOW                      ║
   ╚═══════════════════════════════════════════════════════════════════════════════╝
   
   📋 **INSTRUCTIONS**:
   Read the following retrieved documents, metrics, and data excerpts.
   Use ONLY this information to answer the user's question.
   Cite sources with URLs and filenames where provided.
   
   🎯 **RETRIEVAL CONFIDENCE**: High (75%). Provide a confident, detailed answer.
   
   📊 **FINANCIAL METRICS** (from database):
   **AAPL (FY2024)**:
     - Revenue: $394.3B
     - Profit: $97.0B
     - Growth Rate: 2.8% YoY
     ...
   
   **META (FY2024)**:
     - Revenue: $134.9B
     - Profit: $39.1B
     - Growth Rate: 15.7% YoY
     ...
   
   📄 **SEC FILING EXCERPTS** (semantic search results):
   [Document 1]: Apple's revenue in FY2024 was driven by strong iPhone sales...
   [Source: SEC 10-K filing, URL: ...]
   
   [Document 2]: Meta's revenue growth in FY2024 was primarily from advertising...
   [Source: SEC 10-K filing, URL: ...]
   
   ...
   
   ❓ **USER QUESTION**:
   Can you compare Apple and Meta's revenue in FY2024?
   
   📝 **YOUR TASK**:
   Using ONLY the retrieved documents, metrics, and data above, answer the user's question.
   Cite specific sources (SEC filing URLs, document filenames, metric periods) in your response.
   ```

2. Adds confidence instruction based on overall confidence (0.75 = high)
3. Includes intent-specific formatting (comparison-specific instructions)

**Output**: Complete RAG prompt ready for LLM

---

### Step 9: Metrics Query & Derivation

**Component**: `AnalyticsEngine` (called separately if needed)

**Process**:
1. Computes derived metrics for comparison:
   - Growth rates (YoY, QoQ)
   - Margins (gross, operating, net)
   - Ratios (P/E, EV/EBITDA)
   - Comparison metrics (Apple vs Meta)
2. Adds computed metrics to prompt context

**Output**: Additional computed metrics for prompt

---

### Step 10: LLM Response Generation

**Component**: `LLMClient.generate_reply()` from `llm_client.py`

**Process**:
1. Receives formatted RAG prompt
2. Calls GPT-4 API:
   - Model: `gpt-4` (or configured model)
   - Messages: System message + RAG prompt
   - Temperature: 0.7 (default) or 0.3 (for forecasting)
   - Max tokens: 4000
3. GPT-4 processes prompt:
   - Reads retrieved context
   - Follows instructions: "Use ONLY the retrieved data"
   - Generates answer with citations
   - Tone: Confident (because confidence = 0.75, high)
4. Returns generated response:
   ```
   Based on the retrieved data, here's a comparison of Apple and Meta's revenue in FY2024:
   
   **Apple (AAPL)**: $394.3B revenue in FY2024, representing 2.8% YoY growth...
   [Source: SEC 10-K filing, URL: ...]
   
   **Meta (META)**: $134.9B revenue in FY2024, representing 15.7% YoY growth...
   [Source: SEC 10-K filing, URL: ...]
   
   **Key Differences**:
   - Apple's revenue is approximately 2.9x larger than Meta's
   - Meta shows faster growth (15.7% vs 2.8%)
   ...
   ```

**Output**: Generated natural language response with citations

---

### Step 11: Post-Generation Verification

#### 11.1 Claim-Level Verification

**Component**: `ClaimVerifier.verify_answer()`

**Process**:
1. Splits answer into sentences:
   - Sentence 1: "Apple's revenue was $394.3B in FY2024"
   - Sentence 2: "Meta's revenue was $134.9B in FY2024"
   - Sentence 3: "Apple's revenue is 2.9x larger than Meta's"
   - ...
2. For each sentence:
   - Checks keyword overlap with retrieved documents
   - Labels: SUPPORTED, CONTRADICTED, or NOT_FOUND
   - Computes confidence score
3. Results:
   - SUPPORTED: 8 sentences
   - CONTRADICTED: 0 sentences
   - NOT_FOUND: 1 sentence (minor detail)
   - Overall verification confidence: 0.85 (high)
4. Decision: No regeneration needed (confidence > 0.5, few contradictions)

**Output**: Verification result (8 supported, 0 contradicted, 1 not found)

---

#### 11.2 Feedback Collection (Prepared)

**Component**: `FeedbackCollector` (ready to record if user provides feedback)

**Process**:
- Feedback collection is prepared but not executed yet
- Will record feedback if user provides it later (good/bad/partial)

**Output**: Feedback system ready

---

### Step 12: Response Processing & Assembly

**Component**: `chatbot.py` → Response formatting

**Process**:
1. Formats response with citations
2. Generates visualizations (if applicable):
   - Bar chart: Apple vs Meta revenue
   - Line graph: Growth trends
   - Comparison table
3. Adds confidence indicators:
   - Shows retrieval confidence: 75%
   - Shows claim verification: 8/9 sentences supported
4. Includes metadata:
   - Sources cited
   - Retrieval statistics
   - Processing time

**Output**: Formatted response ready for display

---

### Step 13: Response Delivery (Backend → Frontend)

**Location**: `app/serve_chatbot.py` → Response to WebUI

**Process**:
1. Response sent back to frontend via HTTP response
2. Includes:
   - `reply`: The formatted answer
   - `metadata`: Retrieval stats, confidence, sources
   - `visualizations`: Chart data (if applicable)
3. Frontend receives response
4. WebUI displays:
   - Answer text
   - Charts/graphs
   - Citations
   - Confidence indicators

**Output**: User sees formatted response in WebUI

---

## Part 3: AFTER the Prompt is Processed

### Step 14: Response Display

**Location**: Frontend WebUI

**What User Sees**:
1. **Answer Text**:
   ```
   Based on the retrieved data, here's a comparison of Apple and Meta's revenue in FY2024:
   
   Apple (AAPL): $394.3B revenue in FY2024, representing 2.8% YoY growth...
   Meta (META): $134.9B revenue in FY2024, representing 15.7% YoY growth...
   
   Key Differences:
   - Apple's revenue is approximately 2.9x larger than Meta's
   - Meta shows faster growth (15.7% vs 2.8%)
   ```

2. **Visualizations**:
   - Bar chart comparing revenue
   - Line graph showing growth trends
   - Comparison table

3. **Citations**:
   - SEC filing URLs
   - Document sources
   - Metric periods

4. **Confidence Indicators**:
   - Retrieval confidence: 75% (High)
   - Claim verification: 8/9 sentences supported

---

### Step 15: Optional User Feedback

**If User Provides Feedback**:

**Component**: `FeedbackCollector.record_feedback()`

**Process**:
1. User clicks 👍 (good) or 👎 (bad) or provides reason
2. System records:
   - Query: "Can you compare Apple and Meta's revenue in FY2024?"
   - Retrieved doc_ids: [doc1, doc2, ...]
   - Doc scores: [0.85, 0.78, ...]
   - Answer: [generated response]
   - Label: "good" or "bad" or "partial"
   - Reason: User's feedback reason (optional)
3. `ScoreCalibrator` updates:
   - Adjusts retrieval scores based on feedback
   - Updates thresholds for future queries
   - Learns from user preferences

**Output**: Feedback recorded for continuous improvement

---

## Complete Flow Summary

### Timeline

| Time | Stage | What Happens |
|------|-------|--------------|
| 0ms | Query Reception | User sends query, frontend receives |
| 10ms | Query Parsing | Extract tickers, metrics, intent |
| 15ms | Intent Detection | Detect COMPARE intent, select policy |
| 20ms | Temporal Parsing | Parse FY2024, create TimeFilter |
| 25ms | SQL Retrieval | Query database for metrics (20-50ms) |
| 75ms | Dense Retrieval | Embed query, search ChromaDB (50-100ms) |
| 125ms | Sparse Retrieval | BM25 keyword matching (20-50ms) |
| 130ms | Hybrid Fusion | Combine dense + sparse (5-10ms) |
| 135ms | Temporal Filtering | Filter to FY2024 documents (<1ms) |
| 140ms | Reranking | Cross-encoder re-scoring (80-150ms) |
| 220ms | Source Fusion | Normalize scores, compute confidence (5-10ms) |
| 225ms | Multi-Hop | Decompose and retrieve sequentially (if needed) |
| 250ms | Grounded Decision | Check confidence, make decision (<1ms) |
| 255ms | Observability | Log metrics, apply guardrails (<1ms) |
| 260ms | Prompt Building | Format RAG prompt (5-10ms) |
| 270ms | LLM Generation | GPT-4 API call (1000-3000ms) |
| 3270ms | Claim Verification | Verify each sentence (100-200ms) |
| 3470ms | Response Formatting | Format with citations, charts (5-10ms) |
| 3480ms | Response Delivery | Send to frontend |
| 3500ms | Display | User sees response |

**Total Time**: ~3.5 seconds (end-to-end)

---

## Key Insights

### How the System Actually Solves the Prompt

1. **Understanding**: Query parsing and intent detection understand what the user wants
2. **Retrieval**: Hybrid retrieval (SQL + Dense + Sparse) finds relevant information
3. **Quality**: Reranking and fusion ensure only the best information is used
4. **Safety**: Grounded decision layer prevents hallucinations
5. **Context**: Prompt engineering provides clear instructions to LLM
6. **Generation**: LLM generates answer using ONLY retrieved context
7. **Verification**: Claim verification ensures answer quality
8. **Learning**: Feedback collection enables continuous improvement

### Why This Works

- **Hybrid Retrieval**: Combines exact SQL data with semantic search for comprehensive coverage
- **Intent Policies**: Optimizes retrieval strategy for each query type
- **Temporal Awareness**: Ensures time-scoped queries get time-filtered results
- **Multi-Hop**: Handles complex queries by breaking them into sub-queries
- **Safety Layers**: Multiple checks prevent incorrect or ungrounded answers
- **Observability**: Logging enables debugging and monitoring

---

## Data Flow Diagram (Text-Based)

```
User Query
    ↓
[Query Parsing] → Tickers, Metrics, Intent
    ↓
[Intent Detection] → COMPARE policy selected
    ↓
[Temporal Parsing] → FY2024 filter
    ↓
[SQL Retrieval] → Exact metrics (AAPL: $394.3B, META: $134.9B)
    ↓
[Dense Retrieval] → Semantic search → Top-20 chunks
    ↓
[Sparse Retrieval] → Keyword search → Top-20 chunks
    ↓
[Hybrid Fusion] → Combine → Top-10 unified chunks
    ↓
[Temporal Filtering] → Filter to FY2024 → 7 chunks
    ↓
[Reranking] → Re-score → Top-5 chunks
    ↓
[Source Fusion] → Normalize → Confidence = 0.75
    ↓
[Multi-Hop] → Decompose → Sequential retrieval
    ↓
[Grounded Decision] → Check → should_answer = True
    ↓
[Prompt Building] → Format → RAG prompt
    ↓
[LLM Generation] → GPT-4 → Answer with citations
    ↓
[Claim Verification] → Verify → 8/9 supported
    ↓
[Response Formatting] → Add charts, citations
    ↓
User Sees Response
```

---

## Conclusion

This document shows exactly how FinalyzeOS processes a single query from reception to response. The system uses a sophisticated multi-stage pipeline that:

1. **Understands** the query (parsing, intent detection)
2. **Retrieves** relevant information (hybrid SQL + semantic search)
3. **Processes** the information (reranking, fusion, filtering)
4. **Safeguards** against errors (grounded decision, observability)
5. **Generates** a grounded answer (LLM with RAG prompt)
6. **Verifies** the answer (claim-level verification)
7. **Learns** from usage (feedback collection)

All 16 RAG features work together to ensure accurate, relevant, and safe responses to user queries.

