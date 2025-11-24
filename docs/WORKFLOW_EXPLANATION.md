# Complete Technical Workflow: Chatbot System with RAG, ChromaDB, and ML

## Table of Contents

1. [System Overview](#system-overview)
2. [Complete End-to-End Workflow](#complete-end-to-end-workflow)
3. [RAG System Architecture (In-Depth)](#rag-system-architecture-in-depth)
4. [ChromaDB Vector Database (In-Depth)](#chromadb-vector-database-in-depth)
5. [Machine Learning Components (In-Depth)](#machine-learning-components-in-depth)
6. [Detailed Step-by-Step Flow](#detailed-step-by-step-flow)
7. [Data Flow and Transformations](#data-flow-and-transformations)
8. [Performance and Timing Breakdown](#performance-and-timing-breakdown)

---

## System Overview

The FinalyzeOS chatbot is a production-grade financial analysis system that combines:

- **Frontend Interface**: Web UI, CLI, and REST API for user interaction
- **Chat Orchestrator**: Manages conversation context and routes queries
- **RAG System**: Advanced Retrieval-Augmented Generation with 16 production features
- **Vector Database**: ChromaDB for semantic search with embeddings
- **Machine Learning**: Embedding models, reranking, and cross-encoders
- **Analytics Engine**: Financial metric calculations and scenario planning
- **LLM Integration**: GPT-4 for natural language response generation

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vector Database** | ChromaDB (HNSW index) | Semantic search, document retrieval |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) | Text-to-vector conversion (384 dimensions) |
| **Sparse Retrieval** | BM25 (`rank-bm25`) | Keyword-based retrieval |
| **Reranking** | Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) | Relevance scoring |
| **Database** | SQLite/PostgreSQL | Structured financial data |
| **LLM** | GPT-4 (OpenAI API) | Response generation |

---

## Complete End-to-End Workflow

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
│            "Compare Apple and Meta's revenue in FY2024"         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND LAYER (WebUI/CLI/API)                │
│  - Captures user query                                          │
│  - Sends HTTP POST to /api/chat                                 │
│  - Includes conversation_id, session info                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER (FastAPI Backend)              │
│  - Request validation                                            │
│  - Authentication & context binding                              │
│  - Routes to chatbot.ask()                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              QUERY UNDERSTANDING LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Query Parsing (parse_to_structured)                      │   │
│  │ - Extracts tickers: ["AAPL", "META"]                     │   │
│  │ - Identifies metrics: ["revenue"]                        │   │
│  │ - Detects intent keywords: ["compare"]                   │   │
│  │ - Parses temporal: "FY2024" → fiscal_years=[2024]       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Intent Detection (IntentPolicyManager)                   │   │
│  │ - Intent: COMPARE                                        │   │
│  │ - Policy: multi-hop=True, k_docs=10,                    │   │
│  │           require_same_period=True                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Temporal Parsing (TemporalQueryParser)                   │   │
│  │ - Creates TimeFilter: fiscal_years=[2024]               │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG ORCHESTRATOR                             │
│  - Coordinates entire RAG pipeline                              │
│  - Manages 16 advanced features                                 │
│  - Routes to appropriate retrieval methods                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              HYBRID RETRIEVAL LAYER                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. SQL Deterministic Retrieval                           │   │
│  │    - Queries metric_snapshots table                      │   │
│  │    - Queries financial_facts table                       │   │
│  │    - Returns exact numbers:                              │   │
│  │      AAPL: $394.3B, META: $134.9B                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. Hybrid Semantic Search (Sparse + Dense)              │   │
│  │                                                          │   │
│  │    ┌──────────────────────────────────────────────┐     │   │
│  │    │ 2a. Dense Retrieval (Embeddings)            │     │   │
│  │    │     - Embeds query using SentenceTransformer│     │   │
│  │    │     - Query vector: 384-dimensional         │     │   │
│  │    │     - Searches ChromaDB with cosine         │     │   │
│  │    │       similarity                             │     │   │
│  │    │     - Returns top-20 semantically similar   │     │   │
│  │    │       chunks                                 │     │   │
│  │    └──────────────────────────────────────────────┘     │   │
│  │                                                          │   │
│  │    ┌──────────────────────────────────────────────┐     │   │
│  │    │ 2b. Sparse Retrieval (BM25)                 │     │   │
│  │    │     - Tokenizes query: ["compare",           │     │   │
│  │    │       "apple", "meta", "revenue", "fy2024"] │     │   │
│  │    │     - Computes BM25 scores for all docs      │     │   │
│  │    │     - Returns top-20 keyword matches         │     │   │
│  │    └──────────────────────────────────────────────┘     │   │
│  │                                                          │   │
│  │    ┌──────────────────────────────────────────────┐     │   │
│  │    │ 2c. Hybrid Fusion                            │     │   │
│  │    │     - Normalizes dense scores to [0,1]       │     │   │
│  │    │     - Normalizes sparse scores to [0,1]      │     │   │
│  │    │     - Fuses: 0.6*dense + 0.4*sparse          │     │   │
│  │    │     - Returns top-10 unified chunks           │     │   │
│  │    └──────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           ADVANCED PROCESSING PIPELINE                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. Temporal Filtering                                    │   │
│  │    - Filters to FY2024 documents only                   │   │
│  │    - Removes documents from other fiscal years          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. Cross-Encoder Reranking                               │   │
│  │    - Scores each (query, chunk) pair                    │   │
│  │    - Uses ML model: ms-marco-MiniLM-L-6-v2              │   │
│  │    - Reorders by true relevance                         │   │
│  │    - Returns top-5 SEC + top-2 uploaded                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. Source Fusion & Confidence                            │   │
│  │    - Normalizes scores across sources                   │   │
│  │    - Applies reliability weights:                       │   │
│  │      SEC=0.9, Uploaded=0.7                             │   │
│  │    - Computes overall confidence: 0.75                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. Multi-Hop Retrieval (if complex)                     │   │
│  │    - Decomposes query into sub-queries                  │   │
│  │    - Sequential retrieval for each sub-query            │   │
│  │    - Combines results                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              SAFETY & QUALITY LAYER                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Grounded Decision Layer                                  │   │
│  │ - Checks confidence: 0.75 ≥ 0.3 threshold → OK          │   │
│  │ - Verifies min documents: 7 ≥ 3 → OK                    │   │
│  │ - Checks for contradictions: None detected              │   │
│  │ - Decision: should_answer = True                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Observability & Guardrails                               │   │
│  │ - Logs retrieval metrics                                │   │
│  │ - Applies guardrails (max docs, max context)            │   │
│  │ - Tracks performance (retrieval time, rerank time)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Memory-Augmented RAG                                     │   │
│  │ - Tracks document access per conversation               │   │
│  │ - Updates access timestamps                             │   │
│  │ - Clusters documents by topic                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PROMPT ENGINEERING LAYER                           │
│                                                                 │
│  Builds structured RAG prompt with:                             │
│  - Retrieved context (metrics, SEC excerpts, uploaded docs)     │
│  - User query                                                   │
│  - Confidence instructions (High: 0.75)                         │
│  - Intent-specific formatting (COMPARE instructions)            │
│  - Citation requirements                                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              LLM RESPONSE GENERATION                            │
│                                                                 │
│  - Model: GPT-4                                                │
│  - Input: Complete RAG prompt                                   │
│  - Temperature: 0.7 (default)                                   │
│  - Max tokens: 4000                                             │
│  - Output: Natural language response with citations             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              POST-GENERATION VERIFICATION                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Claim-Level Verification                                 │   │
│  │ - Splits answer into sentences                           │   │
│  │ - Verifies each sentence against retrieved docs          │   │
│  │ - Labels: SUPPORTED (8), CONTRADICTED (0),              │   │
│  │          NOT_FOUND (1)                                   │   │
│  │ - Overall verification confidence: 0.85                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              RESPONSE FORMATTING & DELIVERY                     │
│                                                                 │
│  - Formats with citations                                       │
│  - Generates visualizations (charts, tables)                    │
│  - Adds confidence indicators                                   │
│  - Includes metadata (sources, stats)                           │
│  - Returns to frontend                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              USER SEES RESPONSE                                 │
│  - Answer text with citations                                   │
│  - Visualizations (bar charts, line graphs)                     │
│  - Confidence indicators (75% high)                             │
│  - Source links                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## RAG System Architecture (In-Depth)

### What is RAG?

**Retrieval-Augmented Generation (RAG)** combines:
1. **Retrieval**: Finding relevant information from knowledge bases
2. **Augmentation**: Enriching the LLM prompt with retrieved context
3. **Generation**: LLM generates answer using only the retrieved information

### Why RAG?

- **Reduces Hallucinations**: LLM only uses retrieved facts
- **Keeps Information Current**: Can update knowledge base without retraining
- **Provides Citations**: Can cite sources for every claim
- **Domain-Specific**: Works with private/internal documents

### The Complete RAG Pipeline

#### Stage 1: Document Ingestion (Offline Process)

**Location**: `scripts/index_documents_for_rag.py`

**Process**:

1. **Document Collection**:
   - SEC filings (10-K, 10-Q, 8-K) downloaded from EDGAR
   - User-uploaded documents (PDFs, Word docs, text files)
   - Financial reports and analyses

2. **Text Extraction**:
   - PDF parsing using PyPDF2 or pdfplumber
   - HTML parsing for SEC filings (BeautifulSoup)
   - Plain text extraction
   - Table extraction (structured data)

3. **Chunking Strategy**:
   ```python
   chunk_size = 1500 characters  # Optimal for financial text
   chunk_overlap = 200 characters  # Prevents context loss
   
   # Example:
   # Document: "Apple's revenue in FY2024 was $394.3 billion..."
   # Chunk 1: [0:1500] "Apple's revenue in FY2024 was $394.3 billion..."
   # Chunk 2: [1300:2800] "...$394.3 billion, representing 2.8% growth..."
   ```

4. **Embedding Generation**:
   - Model: `all-MiniLM-L6-v2` (SentenceTransformers)
   - Dimensions: 384
   - Process: Text → Tokens → Embeddings (384-dim vectors)
   ```python
   embedding = model.encode(chunk_text)
   # embedding shape: (384,)
   # embedding dtype: float32
   ```

5. **Storage in ChromaDB**:
   - Each chunk stored with:
     - `embedding`: 384-dimensional vector
     - `text`: Original chunk text
     - `metadata`: Ticker, fiscal_year, section, filing_type, URL, etc.
     - `id`: Unique identifier

#### Stage 2: Query-Time Retrieval

**Location**: `src/finanlyzeos_chatbot/rag_retriever.py`

**Components**:

##### 2.1 SQL Deterministic Retrieval

**Purpose**: Get exact numbers and structured data

**Process**:
```python
# Query: "What is Apple's revenue in FY2024?"
SELECT * FROM metric_snapshots 
WHERE ticker = 'AAPL' 
  AND metric = 'revenue' 
  AND period = 'FY2024'
  
# Result:
# {
#   "ticker": "AAPL",
#   "metric": "revenue",
#   "value": 394300000000,
#   "period": "FY2024",
#   "unit": "USD"
# }
```

**Advantages**:
- Exact numbers (no approximation)
- Fast (indexed database queries)
- Structured format (easy to format)

##### 2.2 Hybrid Semantic Search

**Purpose**: Find relevant narrative text and explanations

**Two Parallel Retrieval Methods**:

**A. Dense Retrieval (Semantic Search)**

**Technology**: ChromaDB + SentenceTransformers

**Process**:
```python
# 1. Embed query
query_text = "Compare Apple and Meta's revenue in FY2024"
query_embedding = embedding_model.encode(query_text)
# query_embedding shape: (384,)

# 2. Search ChromaDB
results = chromadb_collection.query(
    query_embeddings=[query_embedding],
    n_results=20,
    where={"fiscal_year": 2024},  # Metadata filter
    include=["documents", "metadatas", "distances"]
)

# 3. ChromaDB uses HNSW (Hierarchical Navigable Small World) index
#    for approximate nearest-neighbor search
#    - Fast: O(log n) search time
#    - Accurate: 95-99% recall

# 4. Results sorted by cosine similarity (distance)
#    - Lower distance = higher similarity
#    - Distance 0.0 = identical vectors
#    - Distance 1.0 = orthogonal (unrelated)
```

**B. Sparse Retrieval (Keyword Search)**

**Technology**: BM25 algorithm

**Process**:
```python
# 1. Tokenize query
query_tokens = ["compare", "apple", "meta", "revenue", "fy2024"]

# 2. BM25 scores each document
# BM25 formula:
# score(D, Q) = Σ IDF(qi) * f(qi, D) * (k1 + 1) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))
# where:
# - IDF(qi) = Inverse Document Frequency (rarity of term)
# - f(qi, D) = Term frequency in document
# - k1, b = Tuning parameters (default: k1=1.5, b=0.75)

# 3. Documents ranked by BM25 score
#    - Higher score = more keyword matches
#    - Handles exact phrases well
#    - Robust to typos/variants
```

**C. Hybrid Fusion**

**Purpose**: Combine strengths of both methods

**Process**:
```python
# 1. Normalize scores to [0, 1]
def normalize_dense(score):
    # ChromaDB returns distances, convert to similarity
    return 1.0 / (1.0 + score)

def normalize_sparse(score):
    # BM25 scores typically 0-20, normalize to [0, 1]
    return min(1.0, score / 10.0)

# 2. Fuse scores
for document in all_documents:
    dense_score = normalize_dense(document.dense_distance)
    sparse_score = normalize_sparse(document.bm25_score)
    
    # Weighted combination
    fused_score = 0.6 * dense_score + 0.4 * sparse_score
    document.final_score = fused_score

# 3. Sort by fused_score (descending)
# 4. Return top-K documents
```

**Why Hybrid?**
- **Dense retrieval** excels at semantic understanding ("revenue growth" matches "increasing sales")
- **Sparse retrieval** excels at exact matches ("AAPL" matches "Apple Inc." ticker)
- **Fusion** gives best of both worlds

##### 2.3 Advanced Processing

**A. Temporal Filtering**

**Purpose**: Ensure time-scoped queries get time-filtered results

**Process**:
```python
time_filter = TimeFilter(fiscal_years=[2024])

for document in retrieved_docs:
    doc_year = document.metadata.get("fiscal_year")
    if doc_year not in time_filter.fiscal_years:
        # Remove document (not in requested time period)
        continue
    # Keep document
```

**B. Cross-Encoder Reranking**

**Purpose**: Second-pass relevance scoring (more accurate than bi-encoder)

**Technology**: Cross-Encoder model (`ms-marco-MiniLM-L-6-v2`)

**Process**:
```python
# Bi-encoder (initial retrieval):
# - Encodes query and documents separately
# - Compares embeddings (fast but less accurate)
# - Used in initial retrieval (ChromaDB)

# Cross-encoder (reranking):
# - Encodes (query, document) pairs together
# - Considers query-document interactions
# - More accurate but slower (must encode each pair)

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

for document in retrieved_docs:
    # Create (query, document) pair
    pair = (query_text, document.text)
    
    # Score with cross-encoder
    rerank_score = reranker.predict([pair])[0]
    document.rerank_score = rerank_score

# Reorder by rerank_score (descending)
```

**C. Source Fusion**

**Purpose**: Normalize scores across different sources and compute confidence

**Process**:
```python
# Source reliability weights
SOURCE_WEIGHTS = {
    "sql_metrics": 1.0,      # Most reliable (exact numbers)
    "sec_narratives": 0.9,   # Highly reliable (SEC filings)
    "uploaded_docs": 0.7,    # Less reliable (user uploads)
}

for source_type, documents in sources.items():
    source_weight = SOURCE_WEIGHTS[source_type]
    
    for doc in documents:
        normalized_score = normalize(doc.score)  # [0, 1]
        fused_score = normalized_score * source_weight
        doc.fused_score = fused_score

# Compute overall confidence (average of top-K)
top_k_scores = sorted([d.fused_score for d in all_docs], reverse=True)[:5]
overall_confidence = sum(top_k_scores) / len(top_k_scores)
```

**D. Multi-Hop Retrieval**

**Purpose**: Handle complex queries by breaking into sub-queries

**Process**:
```python
# Query: "Why did Apple's revenue decline and how does it compare to Microsoft?"

# 1. Detect complexity: COMPLEX
complexity = detect_query_complexity(query)

# 2. Decompose into sub-queries
sub_queries = decompose_query(query)
# [
#   "Why did Apple's revenue decline?",
#   "Apple's revenue metrics",
#   "Microsoft's revenue metrics",
#   "Compare Apple and Microsoft revenue"
# ]

# 3. Sequential retrieval
all_results = []
for sub_query in sub_queries:
    results = retrieve(sub_query)
    all_results.extend(results)

# 4. Combine and deduplicate
final_results = merge_and_deduplicate(all_results)
```

#### Stage 3: Prompt Engineering

**Location**: `src/finanlyzeos_chatbot/rag_prompt_template.py`

**Purpose**: Build structured prompt that guides LLM to use only retrieved context

**Template Structure**:
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
[Source: SEC 10-K filing, URL: https://www.sec.gov/...]

[Document 2]: Meta's revenue growth in FY2024 was primarily from advertising...
[Source: SEC 10-K filing, URL: https://www.sec.gov/...]

...

❓ **USER QUESTION**:
Can you compare Apple and Meta's revenue in FY2024?

📝 **YOUR TASK**:
Using ONLY the retrieved documents, metrics, and data above, answer the user's question.
Cite specific sources (SEC filing URLs, document filenames, metric periods) in your response.
```

**Key Elements**:
- **Clear Instructions**: "USE ONLY THE DATA BELOW"
- **Confidence Level**: Adjusts LLM tone (High/Medium/Low)
- **Structured Format**: Metrics, narratives, sources clearly separated
- **Citation Requirements**: Explicit instruction to cite sources

#### Stage 4: Response Generation & Verification

**Location**: `src/finanlyzeos_chatbot/llm_client.py`

**A. LLM Generation**

**Process**:
```python
# 1. Prepare messages for GPT-4
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": rag_prompt}
]

# 2. Call GPT-4 API
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=messages,
    temperature=0.7,  # Creativity vs. consistency
    max_tokens=4000,
)

# 3. Extract generated answer
answer = response.choices[0].message.content
```

**B. Claim-Level Verification**

**Location**: `src/finanlyzeos_chatbot/rag_claim_verifier.py`

**Purpose**: Verify each sentence in the answer against retrieved documents

**Process**:
```python
# 1. Split answer into sentences
sentences = split_into_sentences(answer)
# [
#   "Apple's revenue was $394.3B in FY2024.",
#   "Meta's revenue was $134.9B in FY2024.",
#   "Apple's revenue is 2.9x larger than Meta's."
# ]

# 2. Verify each sentence
verification_results = []
for sentence in sentences:
    # Check keyword overlap with retrieved documents
    overlap_score = compute_keyword_overlap(sentence, retrieved_docs)
    
    # Label: SUPPORTED, CONTRADICTED, or NOT_FOUND
    if overlap_score > 0.7:
        label = "SUPPORTED"
    elif contradiction_detected(sentence, retrieved_docs):
        label = "CONTRADICTED"
    else:
        label = "NOT_FOUND"
    
    verification_results.append({
        "sentence": sentence,
        "label": label,
        "score": overlap_score
    })

# 3. Compute overall verification confidence
supported_count = sum(1 for r in verification_results if r["label"] == "SUPPORTED")
verification_confidence = supported_count / len(verification_results)
```

---

## ChromaDB Vector Database (In-Depth)

### What is ChromaDB?

**ChromaDB** is an open-source vector database designed for embeddings and semantic search.

### Architecture

#### Collections

**Collections** are separate namespaces for different document types:

```python
# Two main collections
sec_collection = chromadb.get_collection("sec_narratives")
uploaded_collection = chromadb.get_collection("uploaded_documents")
```

**Why Separate Collections?**
- Different metadata schemas (SEC filings have fiscal_year, uploaded docs have conversation_id)
- Independent querying (can search SEC only or uploaded only)
- Performance (smaller collections = faster queries)

#### Document Storage

Each document in ChromaDB contains:

```python
{
    "id": "AAPL_10K_2024_MD&A_0",  # Unique identifier
    "embedding": [0.123, -0.456, ..., 0.789],  # 384-dim vector
    "document": "Apple's revenue in FY2024...",  # Original text chunk
    "metadata": {
        "ticker": "AAPL",
        "fiscal_year": 2024,
        "section": "MD&A",
        "filing_type": "10-K",
        "url": "https://www.sec.gov/...",
        "source": "SEC EDGAR"
    }
}
```

#### Indexing: HNSW Algorithm

**HNSW (Hierarchical Navigable Small World)** is an approximate nearest-neighbor search algorithm.

**How It Works**:

1. **Graph Construction**:
   ```
   - Documents are nodes in a graph
   - Similar documents (low distance) are connected by edges
   - Multiple layers (hierarchical):
     * Layer 0: All documents (dense connections)
     * Layer 1: ~50% of documents (sparse connections)
     * Layer 2: ~25% of documents (very sparse)
     * Layer N: Very few documents (hub nodes)
   ```

2. **Search Process**:
   ```python
   # Query: Find nearest neighbors to query_embedding
   
   # Start at top layer (few nodes, fast navigation)
   current_node = find_entry_point(query_embedding, top_layer)
   
   # Navigate down layers, getting closer to query
   for layer in reversed(range(num_layers)):
       current_node = navigate_to_nearest(current_node, query_embedding, layer)
   
   # Final search in bottom layer (exact neighbors)
   nearest_neighbors = search_local_neighbors(current_node, query_embedding, k=20)
   ```

**Performance**:
- **Time Complexity**: O(log n) where n = number of documents
- **Space Complexity**: O(n) (linear in documents)
- **Accuracy**: 95-99% recall (finds almost all true nearest neighbors)

**Comparison with Brute Force**:
- **Brute Force**: Compare query with all documents → O(n)
- **HNSW**: Navigate graph → O(log n)
- **Speedup**: 100-1000x faster for large collections

#### Metadata Filtering

**Purpose**: Filter documents by metadata before/during search

**Example**:
```python
# Search only for Apple documents in FY2024
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=20,
    where={
        "ticker": "AAPL",
        "fiscal_year": 2024
    }
)
```

**How It Works**:
1. **Pre-filter**: Filter documents by metadata (fast, indexed)
2. **Search**: Only search in filtered subset (faster than full search)
3. **Post-filter**: Optionally filter results again

**Performance Benefit**:
- Full collection: 100,000 documents → Search 100,000
- Filtered: 1,000 documents → Search only 1,000 (100x faster)

#### Persistence

**ChromaDB** stores data on disk:

```
data/chroma_db/
├── chroma.sqlite3          # Metadata and indexes
├── <collection_id>/
│   ├── data_level0.bin     # Document embeddings (binary)
│   ├── data_level1.bin     # HNSW layer 1
│   └── ...
```

**Why SQLite?**
- Lightweight (no separate database server)
- Portable (single file)
- ACID compliant (data integrity)

### Embedding Generation Pipeline

#### Step-by-Step Process

**1. Text Input**:
```python
chunk_text = "Apple's revenue in FY2024 was $394.3 billion, representing 2.8% YoY growth..."
```

**2. Tokenization**:
```python
# SentenceTransformer tokenizer (WordPiece/BytePair encoding)
tokens = tokenizer.encode(chunk_text)
# tokens: [101, 7592, 2011, ..., 102]  # Token IDs
```

**3. Embedding Model Forward Pass**:
```python
# Model: all-MiniLM-L6-v2 (6 layers, 384 dimensions)
# Architecture:
# Input tokens → Embedding layer → Transformer layers → Pooling → Output

# Forward pass
token_embeddings = embedding_layer(tokens)  # (seq_len, 384)
hidden_states = transformer_layers(token_embeddings)  # (seq_len, 384)
sentence_embedding = mean_pooling(hidden_states)  # (384,)
```

**4. Normalization**:
```python
# L2 normalization (unit vector)
embedding = sentence_embedding / np.linalg.norm(sentence_embedding)
# Now embedding has length = 1.0
```

**5. Storage**:
```python
# Store in ChromaDB
collection.add(
    embeddings=[embedding.tolist()],  # Convert to list
    documents=[chunk_text],
    metadatas=[metadata],
    ids=[doc_id]
)
```

### Query-Time Search Process 

**1. Query Embedding**:
```python
query = "Compare Apple and Meta's revenue"
query_embedding = embedding_model.encode(query)
# Same process as document embedding generation
```

**2. ChromaDB Query**:
```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=20,
    where={"fiscal_year": 2024},
    include=["documents", "metadatas", "distances"]
)
```

**3. Internal Process**:
```
1. Apply metadata filter (if provided)
   → Filtered collection: 1,000 documents

2. HNSW search
   → Navigate graph to find nearest neighbors
   → Returns top-20 documents

3. Compute distances
   → Cosine distance between query_embedding and document embeddings
   → distance = 1 - cosine_similarity

4. Sort by distance (ascending)
   → Lower distance = more similar
```

**4. Results**:
```python
{
    "ids": [["doc1", "doc2", ...]],
    "distances": [[0.15, 0.23, ...]],  # Lower = more similar
    "documents": [["Apple's revenue...", "Meta's revenue...", ...]],
    "metadatas": [[{...}, {...}, ...]]
}
```

---

## Machine Learning Components (In-Depth)

### 1. Embedding Model: SentenceTransformers

#### Model Architecture

**Model**: `all-MiniLM-L6-v2`

**Specifications**:
- **Base Model**: Microsoft MiniLM (distilled from BERT)
- **Layers**: 6 transformer layers
- **Hidden Size**: 384 dimensions
- **Parameters**: ~22.7M
- **Input**: Text (max 256 tokens)
- **Output**: 384-dimensional vector

#### How It Works

**1. Tokenization**:
```python
# WordPiece tokenization (from BERT)
text = "Apple's revenue growth"
tokens = ["apple", "'", "s", "revenue", "growth"]
token_ids = [7592, 1005, 1055, 4135, 3134]
```

**2. Embedding Layer**:
```python
# Convert token IDs to embeddings
token_embeddings = embedding_layer(token_ids)
# Shape: (seq_len, 384)
```

**3. Transformer Layers** (6 layers):
```python
# Self-attention mechanism
hidden_states = token_embeddings
for layer in transformer_layers:
    hidden_states = layer(hidden_states)
    # Each layer refines understanding
    # Layer 1: Word-level features
    # Layer 2: Phrase-level features
    # Layer 3-4: Sentence-level features
    # Layer 5-6: Document-level features
```

**4. Pooling**:
```python
# Mean pooling (average all token embeddings)
sentence_embedding = mean(hidden_states, dim=0)
# Shape: (384,)
```

**5. Normalization**:
```python
# L2 normalization (unit vector)
embedding = sentence_embedding / norm(sentence_embedding)
# Ensures all embeddings have same length (enables cosine similarity)
```

#### Training Process

**Pre-training** (Done by SentenceTransformers team):
- Trained on large text corpus (Wikipedia, news, etc.)
- Objective: Similar sentences → similar embeddings

**Fine-tuning** (Optional):
- Can fine-tune on financial text for better domain performance
- Process:
  1. Collect financial sentence pairs (similar/dissimilar)
  2. Compute embeddings for both sentences
  3. Train to maximize similarity for similar pairs
  4. Train to minimize similarity for dissimilar pairs

#### Why This Model?

**Advantages**:
- **Fast**: Small model (6 layers) → fast inference
- **Efficient**: 384 dimensions (not too large, not too small)
- **Quality**: Good semantic understanding
- **Lightweight**: ~90MB model size

**Trade-offs**:
- **Smaller than larger models** (e.g., BERT-base: 768 dims, 12 layers)
- **Better than simple models** (e.g., TF-IDF: no semantic understanding)

### 2. Reranking Model: Cross-Encoder

#### Model Architecture

**Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

**Specifications**:
- **Architecture**: Cross-encoder (both query and document in same model)
- **Base Model**: MiniLM (same as embedding model)
- **Input**: [CLS] query [SEP] document [SEP]
- **Output**: Single relevance score (0-1)

#### How It Works

**1. Input Preparation**:
```python
query = "Compare Apple and Meta's revenue"
document = "Apple's revenue in FY2024 was $394.3 billion..."

# Concatenate with special tokens
input_text = f"[CLS] {query} [SEP] {document} [SEP]"
# [CLS] Compare Apple and Meta's revenue [SEP] Apple's revenue in FY2024 was $394.3 billion... [SEP]
```

**2. Tokenization**:
```python
tokens = tokenizer.encode(input_text, max_length=512, truncation=True)
# Shape: (seq_len,) where seq_len ≤ 512
```

**3. Transformer Forward Pass**:
```python
# Same architecture as embedding model, but:
# - Input is query+document together
# - Model can see interactions between query and document

hidden_states = transformer_layers(tokens)
# Shape: (seq_len, 384)
```

**4. Classification Head**:
```python
# Take [CLS] token embedding (represents query-document pair)
cls_embedding = hidden_states[0]  # (384,)

# Feed through classification head
relevance_score = sigmoid(linear_layer(cls_embedding))
# Output: 0.0 (irrelevant) to 1.0 (highly relevant)
```

#### Why Cross-Encoder vs. Bi-Encoder?

**Bi-Encoder** (Used in initial retrieval):
```python
# Query and document encoded separately
query_embedding = encode(query)      # (384,)
doc_embedding = encode(document)     # (384,)

# Compare embeddings
similarity = cosine_similarity(query_embedding, doc_embedding)
```

**Advantages**:
- **Fast**: Encode once, compare many times
- **Scalable**: Can pre-compute document embeddings

**Disadvantages**:
- **Less Accurate**: Can't see query-document interactions
- **Limited Context**: 256 tokens per text (separate limits)

**Cross-Encoder** (Used in reranking):
```python
# Query and document encoded together
pair_embedding = encode(query + document)  # Can see interactions
relevance = classify(pair_embedding)
```

**Advantages**:
- **More Accurate**: Can see query-document interactions
- **Better Understanding**: Understands how query relates to document

**Disadvantages**:
- **Slower**: Must encode each (query, document) pair
- **Not Scalable**: Can't pre-compute (needs query at runtime)

**Solution**: Use both!
1. **Bi-encoder** for initial retrieval (fast, finds candidate documents)
2. **Cross-encoder** for reranking (accurate, reorders candidates)

### 3. Sparse Retrieval: BM25

#### Algorithm Overview

**BM25 (Best Matching 25)** is a probabilistic ranking function.

**Formula**:
```
score(D, Q) = Σ IDF(qi) * f(qi, D) * (k1 + 1) / (f(qi, D) + k1 * (1 - b + b * |D|/avgdl))

Where:
- qi = query term i
- D = document
- Q = query
- IDF(qi) = Inverse Document Frequency (rarity of term)
- f(qi, D) = Term frequency in document
- |D| = Document length
- avgdl = Average document length
- k1, b = Tuning parameters (k1=1.5, b=0.75)
```

#### How It Works

**1. Tokenization**:
```python
query = "Compare Apple and Meta's revenue"
tokens = tokenize(query)
# ["compare", "apple", "meta", "revenue"]
```

**2. IDF Calculation**:
```python
# IDF measures term rarity (rare terms are more informative)
idf(term) = log((N - n(term) + 0.5) / (n(term) + 0.5))
# N = total documents
# n(term) = documents containing term

# Example:
# idf("apple") = log(10000 / 100) = 2.0  # Common term
# idf("revenue") = log(10000 / 5000) = 0.69  # Very common term
# idf("xyzzy") = log(10000 / 1) = 4.0  # Rare term (high IDF)
```

**3. Term Frequency Calculation**:
```python
# Count how many times each query term appears in document
f("apple", document) = 5  # "apple" appears 5 times
f("revenue", document) = 12  # "revenue" appears 12 times
```

**4. Length Normalization**:
```python
# Penalize very long documents (they tend to match more terms by chance)
normalization = 1 - b + b * (document_length / avg_document_length)
# b = 0.75 (default)
# Longer documents get lower scores (unless they truly match more)
```

**5. Score Computation**:
```python
# Combine IDF, TF, and normalization
for term in query_terms:
    term_score = idf(term) * (f(term, doc) * (k1 + 1)) / 
                 (f(term, doc) + k1 * normalization)
    document_score += term_score

# Final score: sum of all term scores
```

#### Why BM25?

**Advantages**:
- **Fast**: Simple calculation, no ML model needed
- **Effective**: Industry-standard (used by Google, Elasticsearch)
- **Robust**: Handles exact phrases, typos, variants
- **Interpretable**: Can see which terms contributed to score

**Disadvantages**:
- **No Semantic Understanding**: "revenue" and "sales" are different
- **Keyword-Based Only**: Can't understand context

**Solution**: Use BM25 + Embeddings (Hybrid)

---

## Detailed Step-by-Step Flow

### Complete Query Processing Timeline

**Example Query**: "Can you compare Apple and Meta's revenue in FY2024?"

#### Time: 0ms - Query Reception

**Location**: `app/serve_chatbot.py` → `POST /api/chat`

**Process**:
```python
request = ChatRequest(
    prompt="Can you compare Apple and Meta's revenue in FY2024?",
    conversation_id="conv_123",
    file_ids=None
)

# Validate request
if not request.prompt.strip():
    raise HTTPException(400, "Prompt cannot be empty")
```

#### Time: 10ms - Chatbot Entry Point

**Location**: `src/finanlyzeos_chatbot/chatbot.py` → `FinanlyzeOSChatbot.ask()`

**Process**:
```python
def ask(self, user_input: str, file_ids: Optional[List[str]] = None):
    # 1. Log incoming query
    LOGGER.info(f"Processing query: {user_input[:100]}")
    
    # 2. Store user message in database
    database.log_message(
        conversation_id=self.conversation.conversation_id,
        role="user",
        content=user_input
    )
    
    # 3. Query classification (fast path routing)
    complexity, query_type, metadata = classify_query(user_input)
    # complexity: COMPLEX
    # query_type: COMPARE
```

#### Time: 20ms - RAG Orchestrator Initialization (Lazy)

**Location**: `src/finanlyzeos_chatbot/chatbot.py` → `_get_rag_orchestrator()`

**Process** (First Query Only):
```python
if self._rag_orchestrator is None:
    self._rag_orchestrator = RAGOrchestrator(
        database_path=Path(self.settings.database_path),
        analytics_engine=self.analytics_engine,
        use_hybrid_retrieval=True,
        use_intent_policies=True,
        use_temporal=True,
        # ... all features enabled
    )
    
    # This initializes:
    # - RAGRetriever (with VectorStore, SparseRetriever, HybridRetriever)
    # - IntentPolicyManager
    # - TemporalQueryParser
    # - Reranker
    # - SourceFusion
    # - GroundedDecisionLayer
    # - MemoryAugmentedRAG
    # - All other components
```

#### Time: 30ms - Query Parsing

**Location**: `src/finanlyzeos_chatbot/parsing/parse.py` → `parse_to_structured()`

**Process**:
```python
structured_query = parse_to_structured(user_input)
# {
#     "tickers": [
#         {"ticker": "AAPL", "name": "Apple"},
#         {"ticker": "META", "name": "Meta"}
#     ],
#     "metrics": ["revenue"],
#     "intent_keywords": ["compare"],
#     "temporal_expressions": ["FY2024"],
#     "complexity": "COMPLEX"
# }
```

#### Time: 40ms - Intent Detection & Policy Selection

**Location**: `src/finanlyzeos_chatbot/rag_intent_policy.py` → `IntentPolicyManager.detect_intent()`

**Process**:
```python
intent = intent_manager.detect_intent(structured_query)
# intent: COMPARE

policy = intent_manager.get_policy(intent)
# RetrievalPolicy(
#     intent=COMPARE,
#     use_multi_hop=True,           # Complex queries need multi-hop
#     k_docs=10,                     # More documents for comparison
#     narrative_weight=0.6,          # Balance narratives and metrics
#     metric_weight=0.8,             # High metric weight
#     require_same_period=True,      # Critical for comparisons
#     require_same_units=True        # Critical for comparisons
# )
```

#### Time: 50ms - Temporal Parsing

**Location**: `src/finanlyzeos_chatbot/rag_temporal.py` → `TemporalQueryParser.parse_time_filter()`

**Process**:
```python
time_filter = temporal_parser.parse_time_filter(user_input)
# TimeFilter(
#     fiscal_years=[2024],
#     start_date=None,
#     end_date=None
# )
```

#### Time: 60ms - SQL Deterministic Retrieval

**Location**: `src/finanlyzeos_chatbot/rag_retriever.py` → `RAGRetriever._retrieve_sql_data()`

**Process**:
```python
# Query 1: Apple revenue
sql_result_aapl = database.fetch_metric(
    ticker="AAPL",
    metric="revenue",
    period="FY2024"
)
# {"value": 394300000000, "unit": "USD", "period": "FY2024"}

# Query 2: Meta revenue
sql_result_meta = database.fetch_metric(
    ticker="META",
    metric="revenue",
    period="FY2024"
)
# {"value": 134900000000, "unit": "USD", "period": "FY2024"}

# Additional metrics for context
additional_metrics = fetch_additional_metrics(["AAPL", "META"], "FY2024")
# Profit, margins, growth rates, etc.
```

#### Time: 100ms - Hybrid Semantic Search

**Location**: `src/finanlyzeos_chatbot/rag_hybrid_retriever.py` → `HybridRetriever.retrieve_sec_narratives()`

**Process**:

**A. Dense Retrieval** (70ms):
```python
# 1. Embed query
query_embedding = embedding_model.encode(query)
# Shape: (384,)
# Time: 20ms

# 2. Search ChromaDB
dense_results = vector_store.search_sec_narratives(
    query=query,
    n_results=20,
    filter_metadata={"fiscal_year": 2024}
)
# Time: 50ms (HNSW search)
# Results: 20 document chunks with cosine similarity scores
```

**B. Sparse Retrieval** (30ms):
```python
# 1. Tokenize query
query_tokens = tokenize(query)
# ["compare", "apple", "meta", "revenue", "fy2024"]
# Time: <1ms

# 2. BM25 search
sparse_results = sparse_retriever.search_sec(
    query=query,
    n_results=20,
    filter_metadata={"fiscal_year": 2024}
)
# Time: 30ms (BM25 score computation)
# Results: 20 document chunks with BM25 scores
```

**C. Hybrid Fusion** (10ms):
```python
# 1. Normalize scores
dense_normalized = normalize_dense_scores(dense_results)  # [0, 1]
sparse_normalized = normalize_sparse_scores(sparse_results)  # [0, 1]

# 2. Fuse scores
fused_results = []
for doc_id in all_document_ids:
    dense_score = dense_normalized.get(doc_id, 0.0)
    sparse_score = sparse_normalized.get(doc_id, 0.0)
    
    fused_score = 0.6 * dense_score + 0.4 * sparse_score
    fused_results.append((doc_id, fused_score))

# 3. Sort by fused_score (descending)
fused_results.sort(key=lambda x: x[1], reverse=True)

# 4. Return top-10
top_10_chunks = fused_results[:10]
```

#### Time: 140ms - Temporal Filtering

**Location**: `src/finanlyzeos_chatbot/rag_temporal.py` → `TemporalQueryParser.apply_time_filter()`

**Process**:
```python
filtered_chunks = []
for chunk in top_10_chunks:
    chunk_year = chunk.metadata.get("fiscal_year")
    if chunk_year in time_filter.fiscal_years:  # [2024]
        filtered_chunks.append(chunk)

# Before: 10 chunks
# After: 7 chunks (3 filtered out for wrong year)
```

#### Time: 220ms - Cross-Encoder Reranking

**Location**: `src/finanlyzeos_chatbot/rag_reranker.py` → `Reranker.rerank()`

**Process**:
```python
# Prepare (query, document) pairs
pairs = [
    (query, chunk.text)
    for chunk in filtered_chunks
]
# 7 pairs

# Score with cross-encoder
rerank_scores = reranker.model.predict(pairs, batch_size=7)
# Time: 80ms (cross-encoder inference)
# Scores: [0.85, 0.78, 0.72, 0.65, 0.58, 0.52, 0.45]

# Reorder by rerank_score
reranked_chunks = sorted(
    zip(filtered_chunks, rerank_scores),
    key=lambda x: x[1],
    reverse=True
)

# Return top-5 SEC + top-2 uploaded
top_5_sec = reranked_chunks[:5]
```

#### Time: 230ms - Source Fusion & Confidence

**Location**: `src/finanlyzeos_chatbot/rag_fusion.py` → `SourceFusion.fuse_all_sources()`

**Process**:
```python
# 1. Normalize scores by source
sec_fused = source_fusion.normalize_scores(top_5_sec, "sec_narratives")
# Source weight: 0.9 (SEC is highly reliable)
# Normalized scores: [0.94, 0.87, 0.80, 0.72, 0.64]
# Fused scores: [0.85, 0.78, 0.72, 0.65, 0.58]

# 2. Compute overall confidence
top_k_scores = [0.85, 0.78, 0.72, 0.65, 0.58]
overall_confidence = sum(top_k_scores) / len(top_k_scores)
# overall_confidence: 0.716 (High confidence)

# 3. Determine confidence level
if overall_confidence >= 0.7:
    confidence_level = "High"
elif overall_confidence >= 0.4:
    confidence_level = "Medium"
else:
    confidence_level = "Low"
```

#### Time: 250ms - Multi-Hop Retrieval (If Complex)

**Location**: `src/finanlyzeos_chatbot/rag_controller.py` → `RAGController.execute_multi_hop()`

**Process** (Because query is COMPLEX):
```python
# 1. Decompose query
sub_queries = decompose_query(query)
# [
#     "Apple revenue FY2024",
#     "Meta revenue FY2024",
#     "Apple SEC narratives FY2024",
#     "Meta SEC narratives FY2024"
# ]

# 2. Sequential retrieval for each sub-query
all_results = []
for sub_query in sub_queries:
    results = retrieve(sub_query)
    all_results.extend(results)

# 3. Combine and deduplicate
final_results = merge_and_deduplicate(all_results)
```

#### Time: 260ms - Grounded Decision Layer

**Location**: `src/finanlyzeos_chatbot/rag_grounded_decision.py` → `GroundedDecisionLayer.make_decision()`

**Process**:
```python
decision = grounded_decision.make_decision(
    overall_confidence=0.716,
    num_documents=7,
    retrieved_docs=final_results
)

# Checks:
# 1. Confidence: 0.716 >= 0.3 threshold → ✓
# 2. Min documents: 7 >= 3 → ✓
# 3. Contradictions: None detected → ✓

# Decision:
decision = {
    "should_answer": True,
    "suggested_response": None,  # No need for low-confidence warning
    "confidence": 0.716
}
```

#### Time: 270ms - Prompt Building

**Location**: `src/finanlyzeos_chatbot/rag_prompt_template.py` → `build_rag_prompt()`

**Process**:
```python
rag_prompt = build_rag_prompt(
    retrieved_context={
        "metrics": sql_results,  # AAPL: $394.3B, META: $134.9B
        "sec_narratives": top_5_sec,
        "uploaded_docs": top_2_uploaded
    },
    user_query=user_input,
    overall_confidence=0.716,
    intent="COMPARE"
)

# Prompt structure:
# - Instructions: "USE ONLY THE DATA BELOW"
# - Confidence: "High (71.6%). Provide a confident, detailed answer."
# - Metrics section: Formatted financial metrics
# - SEC excerpts section: Document chunks with sources
# - User question
# - Task: "Using ONLY the retrieved data, answer with citations"
```

#### Time: 3270ms - LLM Response Generation

**Location**: `src/finanlyzeos_chatbot/llm_client.py` → `LLMClient.generate_reply()`

**Process**:
```python
# 1. Prepare messages
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": rag_prompt}
]

# 2. Call GPT-4 API
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=messages,
    temperature=0.7,
    max_tokens=4000
)
# Time: 3000ms (API call latency)

# 3. Extract answer
answer = response.choices[0].message.content
```

**Generated Answer**:
```
Based on the retrieved data, here's a comparison of Apple and Meta's revenue in FY2024:

**Apple (AAPL)**: $394.3B revenue in FY2024, representing 2.8% YoY growth. 
The revenue was driven by strong iPhone sales and services growth...
[Source: SEC 10-K filing, URL: https://www.sec.gov/...]

**Meta (META)**: $134.9B revenue in FY2024, representing 15.7% YoY growth.
The revenue was primarily from advertising, with strong performance in Reels...
[Source: SEC 10-K filing, URL: https://www.sec.gov/...]

**Key Differences**:
- Apple's revenue is approximately 2.9x larger than Meta's ($394.3B vs $134.9B)
- Meta shows faster growth (15.7% vs 2.8% YoY)
- Apple's revenue is more diversified across hardware and services
- Meta's revenue is concentrated in advertising
```

#### Time: 3470ms - Claim-Level Verification

**Location**: `src/finanlyzeos_chatbot/rag_claim_verifier.py` → `ClaimVerifier.verify_answer()`

**Process**:
```python
# 1. Split answer into sentences
sentences = split_into_sentences(answer)
# 9 sentences

# 2. Verify each sentence
verification_results = []
for sentence in sentences:
    # Check keyword overlap with retrieved docs
    overlap_score = compute_keyword_overlap(sentence, retrieved_docs)
    
    if overlap_score > 0.7:
        label = "SUPPORTED"
    elif contradiction_detected(sentence, retrieved_docs):
        label = "CONTRADICTED"
    else:
        label = "NOT_FOUND"
    
    verification_results.append({
        "sentence": sentence,
        "label": label,
        "score": overlap_score
    })

# Results:
# SUPPORTED: 8 sentences
# CONTRADICTED: 0 sentences
# NOT_FOUND: 1 sentence (minor detail)

# Overall verification confidence
verification_confidence = 8 / 9 = 0.89 (High)
```

#### Time: 3480ms - Response Formatting

**Location**: `src/finanlyzeos_chatbot/chatbot.py` → Response formatting

**Process**:
```python
# 1. Format answer with citations
formatted_answer = format_with_citations(answer, retrieved_sources)

# 2. Generate visualizations
visualizations = generate_visualizations(sql_results)
# - Bar chart: Apple vs Meta revenue
# - Line graph: Growth trends
# - Comparison table

# 3. Add confidence indicators
response_metadata = {
    "retrieval_confidence": 0.716,
    "verification_confidence": 0.89,
    "sources": retrieved_sources,
    "retrieval_stats": {
        "sec_docs": 5,
        "uploaded_docs": 2,
        "retrieval_time_ms": 140,
        "reranking_time_ms": 80
    }
}
```

#### Time: 3500ms - Response Delivery

**Location**: `app/serve_chatbot.py` → Response to frontend

**Process**:
```python
response = ChatResponse(
    reply=formatted_answer,
    metadata=response_metadata,
    visualizations=visualizations
)

# HTTP response sent to frontend
return response
```

#### Time: 3510ms - Display to User

**Location**: Frontend WebUI

**User Sees**:
- Answer text with citations
- Bar chart comparing Apple and Meta revenue
- Line graph showing growth trends
- Comparison table
- Confidence indicators (71.6% retrieval confidence)
- Source links (SEC filing URLs)

---

## Data Flow and Transformations

### Data Transformation Pipeline

```
Raw Text
    ↓
[Text Extraction]
    ↓
Plain Text Chunks (1500 chars, 200 overlap)
    ↓
[Tokenization]
    ↓
Token IDs (WordPiece encoding)
    ↓
[Embedding Model Forward Pass]
    ↓
384-dimensional Embeddings
    ↓
[L2 Normalization]
    ↓
Unit Vectors (length = 1.0)
    ↓
[Storage in ChromaDB]
    ↓
HNSW Index (for fast search)
    ↓
[Query-Time: Query Embedding]
    ↓
Query Vector (384-dim)
    ↓
[HNSW Search in ChromaDB]
    ↓
Top-K Document Chunks (sorted by cosine similarity)
    ↓
[BM25 Search (Parallel)]
    ↓
Top-K Document Chunks (sorted by BM25 score)
    ↓
[Hybrid Fusion]
    ↓
Top-K Unified Chunks (fused scores)
    ↓
[Temporal Filtering]
    ↓
Time-Filtered Chunks
    ↓
[Cross-Encoder Reranking]
    ↓
Reranked Chunks (true relevance scores)
    ↓
[Source Fusion]
    ↓
Fused Documents (normalized, weighted)
    ↓
[Prompt Assembly]
    ↓
RAG Prompt (structured context + query)
    ↓
[LLM Generation]
    ↓
Natural Language Answer
    ↓
[Claim Verification]
    ↓
Verified Answer (with confidence)
    ↓
[Response Formatting]
    ↓
Final Response (answer + citations + visualizations)
```

### Embedding Space Visualization

**Conceptual Representation**:

```
Embedding Space (384-dimensional, projected to 2D for visualization):

    Revenue-related documents
    ● ● ● ● ●
         │
         │ Query: "Compare revenue"
         │ (closer = more similar)
         │
    ● ● ● ● ●
         │
         │
    Apple-related documents
    ● ● ● ● ●
         │
         │
    Meta-related documents
    ● ● ● ● ●

Cosine Similarity:
- Documents near query = high similarity (low distance)
- Documents far from query = low similarity (high distance)
```

**Real-World Example**:
- Query embedding: `[0.1, -0.3, 0.5, ..., 0.2]` (384-dim)
- Document 1 (Apple revenue): `[0.12, -0.28, 0.48, ..., 0.22]` → Distance: 0.15 (similar)
- Document 2 (Meta revenue): `[0.11, -0.31, 0.49, ..., 0.21]` → Distance: 0.18 (similar)
- Document 3 (Unrelated): `[-0.5, 0.8, -0.2, ..., -0.6]` → Distance: 1.2 (dissimilar)

---

## Performance and Timing Breakdown

### Complete Timeline (Example Query)

| Time | Stage | Component | Duration | Details |
|------|-------|-----------|----------|---------|
| 0ms | Query Reception | FastAPI | 10ms | HTTP POST validation |
| 10ms | Chatbot Entry | `chatbot.py` | 10ms | Logging, classification |
| 20ms | RAG Init | `rag_orchestrator.py` | 10ms | Lazy initialization |
| 30ms | Query Parsing | `parse.py` | 10ms | Extract entities |
| 40ms | Intent Detection | `rag_intent_policy.py` | 10ms | Detect COMPARE intent |
| 50ms | Temporal Parsing | `rag_temporal.py` | 10ms | Parse FY2024 |
| 60ms | SQL Retrieval | `database.py` | 40ms | Query database |
| 100ms | Dense Retrieval | `vector_store.py` | 70ms | Embed query + ChromaDB search |
| 100ms | Sparse Retrieval | `rag_sparse_retriever.py` | 30ms | BM25 search (parallel) |
| 140ms | Hybrid Fusion | `rag_hybrid_retriever.py` | 10ms | Normalize + fuse scores |
| 140ms | Temporal Filtering | `rag_temporal.py` | <1ms | Filter to FY2024 |
| 140ms | Cross-Encoder Reranking | `rag_reranker.py` | 80ms | Rerank with ML model |
| 230ms | Source Fusion | `rag_fusion.py` | 10ms | Normalize + compute confidence |
| 250ms | Multi-Hop | `rag_controller.py` | 10ms | Decompose + retrieve |
| 260ms | Grounded Decision | `rag_grounded_decision.py` | <1ms | Check confidence |
| 270ms | Prompt Building | `rag_prompt_template.py` | 10ms | Format RAG prompt |
| 280ms | LLM Generation | `llm_client.py` | 3000ms | GPT-4 API call |
| 3280ms | Claim Verification | `rag_claim_verifier.py` | 100ms | Verify sentences |
| 3380ms | Response Formatting | `chatbot.py` | 10ms | Add citations, charts |
| 3390ms | Response Delivery | `web.py` | 10ms | HTTP response |
| 3400ms | **TOTAL** | **All** | **3400ms** | **~3.4 seconds** |

### Performance Breakdown

**Retrieval Time**: ~140ms
- SQL retrieval: 40ms (30%)
- Dense retrieval: 70ms (50%)
- Sparse retrieval: 30ms (20%) - parallel with dense

**Processing Time**: ~130ms
- Hybrid fusion: 10ms
- Temporal filtering: <1ms
- Reranking: 80ms (largest component)
- Source fusion: 10ms
- Multi-hop: 10ms
- Grounded decision: <1ms

**Generation Time**: ~3000ms
- LLM API call: 3000ms (88% of total time)

**Verification Time**: ~100ms
- Claim verification: 100ms

**Total**: ~3400ms

### Optimization Opportunities

1. **Parallel Retrieval**: Already doing dense + sparse in parallel ✓
2. **Caching**: Cache embeddings for common queries
3. **Batch Reranking**: Batch cross-encoder calls
4. **LLM Optimization**: Use faster models for simple queries
5. **Database Indexing**: Ensure SQL queries are indexed

### Scalability Considerations

**Current Limits**:
- ChromaDB: ~100,000 documents (tested)
- BM25: ~100,000 documents (tested)
- Embeddings: Real-time generation (~20ms per query)

**Scaling Strategies**:
1. **Horizontal Scaling**: Multiple ChromaDB instances (sharding)
2. **Caching**: Redis cache for common queries
3. **Async Processing**: Background reranking for non-critical queries
4. **Model Optimization**: Quantization, distillation for faster inference

---

## Conclusion

This document provides a complete, in-depth explanation of the chatbot's technical workflow, covering:

1. **Complete End-to-End Flow**: From user query to response
2. **RAG System**: All 16 advanced features explained in detail
3. **ChromaDB**: Vector database architecture, HNSW indexing, embeddings
4. **Machine Learning**: Embedding models, reranking, BM25 algorithm
5. **Detailed Step-by-Step**: Exact process with timing breakdown
6. **Data Transformations**: How data flows through the system
7. **Performance Analysis**: Timing breakdown and optimization opportunities

The system combines state-of-the-art techniques (RAG, hybrid retrieval, cross-encoder reranking) with production-grade features (grounded decision, claim verification, observability) to deliver accurate, cited, and reliable financial analysis.
