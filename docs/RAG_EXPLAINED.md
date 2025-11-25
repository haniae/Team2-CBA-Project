# RAG (Retrieval-Augmented Generation) - Complete Explanation

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that enhances LLM responses by:
1. **Retrieving** relevant documents/data from a knowledge base
2. **Augmenting** the user's query with this retrieved context
3. **Generating** an answer using both the query AND the retrieved context

### Why RAG Matters

**Without RAG:**
- LLM relies only on its training data (which may be outdated)
- Can hallucinate facts
- No way to cite sources
- Limited to what it "knows" from training

**With RAG:**
- ✅ Answers grounded in real, up-to-date documents
- ✅ Can cite specific sources (SEC filings, uploaded docs, etc.)
- ✅ Reduces hallucinations by constraining to retrieved data
- ✅ Handles domain-specific knowledge without retraining

---

## The Three Core Components

### 1. **Retriever** 🔍
Finds relevant information from your knowledge base

### 2. **Augmenter** 📝
Combines the user query with retrieved context into a prompt

### 3. **Generator** 🤖
LLM generates the final answer using the augmented prompt

---

## How RAG Works in Your Chatbot

### Complete Flow Diagram

```
User Query: "Compare Apple and Meta's revenue in FY2024"
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 1: QUERY PARSING & INTENT DETECTION                │
└─────────────────────────────────────────────────────────┘
    ↓
    • Extract tickers: ["AAPL", "META"]
    • Detect intent: COMPARE
    • Parse time: FY2024
    • Determine complexity: COMPLEX → use multi-hop
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: RETRIEVAL (Multiple Sources in Parallel)       │
└─────────────────────────────────────────────────────────┘
    ↓
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ SQL Retrieval   │  │ Vector Search  │  │ Hybrid Search   │
    │ (Structured)    │  │ (Semantic)     │  │ (Sparse+Dense)  │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
    │                    │                    │
    • Metrics            • SEC Narratives     • BM25 + Embeddings
    • Financial Facts    • Uploaded Docs      • Better recall
    • Deterministic      • Earnings Calls     • Keyword + Semantic
    ↓                    ↓                    ↓
    ┌─────────────────────────────────────────────────────────┐
    │ RETRIEVAL RESULT:                                        │
    │ • 15 metrics (revenue, profit, growth, etc.)            │
    │ • 10 SEC filing excerpts (semantic matches)             │
    │ • 3 uploaded documents (if any)                          │
    └─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: RERANKING (Improve Precision)                 │
└─────────────────────────────────────────────────────────┘
    ↓
    • Cross-encoder reranking
    • Score documents by relevance to query
    • Keep top 5 SEC docs, top 3 uploaded docs
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: SOURCE FUSION (Combine & Score)                │
└─────────────────────────────────────────────────────────┘
    ↓
    • Normalize scores across sources
    • Calculate overall confidence: 0.75 (High)
    • Fuse documents by relevance
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 5: GROUNDED DECISION (Safety Check)                │
└─────────────────────────────────────────────────────────┘
    ↓
    • Check: Do we have enough info?
    • Confidence: 0.75 → HIGH → Should answer
    • If confidence < 0.3 → Don't answer, suggest clarification
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 6: PROMPT BUILDING (Augmentation)                 │
└─────────────────────────────────────────────────────────┘
    ↓
    Build RAG prompt:
    ╔═══════════════════════════════════════════════════════╗
    ║  RAG CONTEXT - USE ONLY THE DATA BELOW                ║
    ╚═══════════════════════════════════════════════════════╝
    
    📋 INSTRUCTIONS:
    Read the following retrieved documents, metrics, and data.
    Use ONLY this information to answer the user's question.
    
    🎯 RETRIEVAL CONFIDENCE: High (75%)
    
    📊 FINANCIAL METRICS (from database):
    **AAPL (FY2024)**:
      - Revenue: $394.3B
      - Profit: $97.0B
      - Growth Rate: 2.8% YoY
    
    **META (FY2024)**:
      - Revenue: $134.9B
      - Profit: $39.1B
      - Growth Rate: 15.7% YoY
    
    📄 SEC FILING EXCERPTS (semantic search):
    [Excerpt 1] - Management Discussion Section
    Source: 10-K FY2024
    URL: https://www.sec.gov/...
    
    Apple's revenue in FY2024 was $394.3 billion, driven by 
    strong iPhone sales and services growth...
    
    [Excerpt 2] - Management Discussion Section
    Source: 10-K FY2024
    Meta's revenue in FY2024 reached $134.9 billion, primarily
    from advertising revenue...
    
    ═══════════════════════════════════════════════════════
    
    ❓ USER QUESTION:
    Compare Apple and Meta's revenue in FY2024
    
    📝 YOUR TASK:
    Using ONLY the retrieved documents above, answer the question.
    Cite specific sources (SEC filing URLs, metric periods).
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 7: GENERATION (LLM Produces Answer)               │
└─────────────────────────────────────────────────────────┘
    ↓
    LLM generates answer using ONLY the retrieved context:
    
    "Based on the retrieved financial data for FY2024:
    
    **Apple (AAPL)** reported revenue of $394.3 billion, 
    representing 2.8% year-over-year growth. This was driven 
    by strong iPhone sales and services growth.
    
    **Meta (META)** reported revenue of $134.9 billion, 
    representing 15.7% year-over-year growth, primarily 
    from advertising revenue.
    
    **Comparison**: While Apple's revenue is approximately 
    2.9x larger than Meta's, Meta showed significantly 
    higher growth (15.7% vs 2.8%).
    
    Sources:
    - SEC 10-K filings FY2024 (AAPL, META)
    - Financial metrics database"
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 8: CLAIM VERIFICATION (Post-Generation)            │
└─────────────────────────────────────────────────────────┘
    ↓
    • Verify each claim in the answer
    • Check if supported by retrieved documents
    • Flag unsupported claims
    ↓
    ✅ Answer verified and returned to user
```

---

## Detailed Component Breakdown

### 1. Retriever Component

Your chatbot uses **multiple retrieval strategies** working together:

#### A. SQL Retrieval (Deterministic)
```python
# From rag_retriever.py
def _retrieve_sql_data(self, tickers: List[str]):
    """Retrieve deterministic data from SQL database."""
    metrics = []
    facts = []
    
    for ticker in tickers:
        # Fetch metric snapshots (revenue, profit, etc.)
        records = database.fetch_metric_snapshots(self.database_path, ticker)
        for record in records:
            metrics.append({
                "ticker": ticker,
                "metric": record.metric,
                "period": record.period,
                "value": record.value,
                "source": record.source,
            })
    
    return metrics, facts
```

**What it retrieves:**
- Financial metrics (revenue, profit, growth rates, etc.)
- Financial facts from database
- Structured, exact data

#### B. Vector Search (Semantic)
```python
# From rag_retriever.py - VectorStore
def search_sec_narratives(self, query: str, n_results: int = 5):
    """Semantic search over SEC filing narratives."""
    # 1. Embed the query
    query_embedding = self.embedding_model.encode(query)
    
    # 2. Search ChromaDB for similar documents
    results = self.sec_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"ticker": ticker}
    )
    
    # 3. Return documents ranked by similarity
    return retrieved_documents
```

**What it retrieves:**
- SEC filing excerpts (10-K, 10-Q narratives)
- Uploaded documents
- Earnings call transcripts
- Financial news articles
- Analyst reports

**How it works:**
1. **Embedding**: Convert text to vectors (384-dimensional embeddings)
2. **Similarity Search**: Find documents with similar embeddings
3. **Ranking**: Return documents sorted by similarity score

#### C. Hybrid Retrieval (Sparse + Dense)
```python
# From rag_hybrid_retriever.py
class HybridRetriever:
    def retrieve_sec_narratives(self, query: str, n_results: int):
        # 1. Sparse retrieval (BM25 - keyword matching)
        sparse_results = self.sparse_retriever.search(query, n_results * 2)
        
        # 2. Dense retrieval (embeddings - semantic matching)
        dense_results = self.vector_store.search_sec_narratives(query, n_results * 2)
        
        # 3. Fusion: Combine and re-rank
        fused_results = self.fusion.fuse(sparse_results, dense_results)
        
        # 4. Return top N
        return fused_results[:n_results]
```

**Why Hybrid?**
- **Sparse (BM25)**: Great for exact keyword matches ("revenue", "FY2024")
- **Dense (Embeddings)**: Great for semantic matches ("financial performance" → "revenue growth")
- **Combined**: Best of both worlds - catches both exact and semantic matches

### 2. Reranking Component

After initial retrieval, documents are reranked for better precision:

```python
# From rag_reranker.py
class Reranker:
    def rerank_multi_source(self, query: str, sec_docs: List, uploaded_docs: List):
        """Rerank documents using cross-encoder model."""
        # Cross-encoder: More accurate than embedding similarity
        # It sees query + document together, not separately
        
        for doc in sec_docs + uploaded_docs:
            # Score: How relevant is this document to the query?
            score = self.cross_encoder.predict([query, doc.text])
            doc.rerank_score = score
        
        # Sort by rerank score
        sec_docs.sort(key=lambda x: x.rerank_score, reverse=True)
        uploaded_docs.sort(key=lambda x: x.rerank_score, reverse=True)
        
        return sec_docs[:max_sec], uploaded_docs[:max_uploaded]
```

**Why Reranking?**
- Initial retrieval might miss the best documents
- Cross-encoder sees query + document together → more accurate
- Improves precision (top documents are truly most relevant)

### 3. Source Fusion Component

Combines results from multiple sources and calculates confidence:

```python
# From rag_fusion.py
class SourceFusion:
    def fuse_all_sources(self, result: RetrievalResult):
        """Fuse documents from all sources with normalized scores."""
        all_docs = []
        
        # Normalize scores across sources (0-1 scale)
        for doc in result.sec_narratives:
            normalized_score = self.normalize_score(doc.score, source="sec")
            all_docs.append((doc, normalized_score))
        
        for doc in result.uploaded_docs:
            normalized_score = self.normalize_score(doc.score, source="uploaded")
            all_docs.append((doc, normalized_score))
        
        # Sort by normalized score
        all_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate overall confidence
        confidence = self.calculate_confidence(all_docs, result.metrics)
        
        return [doc for doc, _ in all_docs], confidence
```

**What it does:**
- Normalizes scores from different sources (SEC vs uploaded docs)
- Combines documents into unified ranked list
- Calculates overall confidence (0.0 - 1.0)

### 4. Grounded Decision Layer

Safety check: Should we answer this query?

```python
# From rag_grounded_decision.py
class GroundedDecisionLayer:
    def make_decision(self, query: str, result: RetrievalResult, confidence: float):
        """Decide if we should answer based on retrieved context."""
        
        # Check 1: Do we have enough documents?
        if len(result.sec_narratives) == 0 and len(result.uploaded_docs) == 0:
            return GroundedDecision(
                should_answer=False,
                reason="No relevant documents found",
                suggested_response="I couldn't find relevant information. Please try rephrasing."
            )
        
        # Check 2: Is confidence too low?
        if confidence < 0.3:
            return GroundedDecision(
                should_answer=False,
                reason=f"Low confidence ({confidence:.2f})",
                suggested_response="I found some information, but I'm not confident it fully answers your question. Could you provide more context?"
            )
        
        # Check 3: Do we have metrics for the tickers?
        if tickers and len(result.metrics) == 0:
            return GroundedDecision(
                should_answer=False,
                reason="No metrics found for requested tickers",
                suggested_response=f"I couldn't find financial data for {tickers}. Please ensure these companies have been ingested."
            )
        
        # All checks passed
        return GroundedDecision(
            should_answer=True,
            reason="Sufficient context and confidence",
            suggested_response=None
        )
```

**Purpose:**
- Prevents hallucination by declining low-confidence queries
- Suggests better questions when context is insufficient
- Improves user experience with honest responses

### 5. Prompt Building (Augmentation)

The retrieved context is formatted into a RAG prompt:

```python
# From rag_prompt_template.py
def build_rag_prompt(user_query: str, retrieval_result: RetrievalResult):
    """Build RAG-style prompt with retrieved context."""
    
    prompt = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    RAG CONTEXT - USE ONLY THE DATA BELOW                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📋 **INSTRUCTIONS**:
Read the following retrieved documents, metrics, and data excerpts.
Use ONLY this information to answer the user's question.
Cite sources with URLs and filenames where provided.
Do NOT use information from your training data that contradicts the retrieved data.

🎯 **RETRIEVAL CONFIDENCE**: High (75%). Provide a confident, detailed answer.

📊 **FINANCIAL METRICS** (from database):
**AAPL (FY2024)**:
  - Revenue: $394.3B (FY2024) [Source: SEC 10-K]
  - Profit: $97.0B (FY2024) [Source: SEC 10-K]
  - Growth Rate: 2.8% YoY [Source: Analytics Engine]

**META (FY2024)**:
  - Revenue: $134.9B (FY2024) [Source: SEC 10-K]
  - Profit: $39.1B (FY2024) [Source: SEC 10-K]
  - Growth Rate: 15.7% YoY [Source: Analytics Engine]

📄 **SEC FILING EXCERPTS** (semantic search results):

**Excerpt 1** - Management Discussion Section
Source: 10-K FY2024
URL: https://www.sec.gov/Archives/edgar/data/320193/000032019324000006/aapl-20240928.htm
Relevance Score: 0.92

Apple's revenue in FY2024 was $394.3 billion, driven by strong iPhone sales 
and services growth. The company saw 2.8% year-over-year growth...

────────────────────────────────────────────────────────────────────────────────

**Excerpt 2** - Management Discussion Section
Source: 10-K FY2024
URL: https://www.sec.gov/Archives/edgar/data/1326801/000132680124000006/meta-20231231.htm
Relevance Score: 0.88

Meta's revenue in FY2024 reached $134.9 billion, primarily from advertising 
revenue. The company achieved 15.7% year-over-year growth...

────────────────────────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════

❓ **USER QUESTION**:
Compare Apple and Meta's revenue in FY2024

📝 **YOUR TASK**:
Using ONLY the retrieved documents, metrics, and data above, answer the user's question.
Cite specific sources (SEC filing URLs, document filenames, metric periods) in your response.
"""
    
    return prompt
```

**Key Features:**
- Clear instructions: "Use ONLY this information"
- Structured sections: Metrics, SEC excerpts, uploaded docs
- Source citations: URLs, filenames, periods
- Confidence indicator: Tells LLM how confident to be

### 6. Generation (LLM)

The LLM receives the augmented prompt and generates an answer:

```python
# From chatbot.py
def ask(self, user_input: str):
    # 1. Get RAG context
    rag_prompt, rag_result, metadata = rag_orchestrator.process_query(user_input)
    
    # 2. Prepare LLM messages
    messages = [
        {"role": "system", "content": rag_prompt},  # RAG context as system message
        {"role": "user", "content": user_input}     # User query
    ]
    
    # 3. Generate answer
    response = self.llm_client.generate(messages)
    
    # 4. Verify claims (optional)
    verification = rag_orchestrator.verify_answer_claims(response, rag_result)
    
    return response
```

**What happens:**
- LLM sees the full RAG context (metrics + documents)
- LLM is instructed to use ONLY this context
- LLM generates answer grounded in retrieved data
- Claims can be verified post-generation

### 7. Claim Verification (Post-Generation)

After generation, verify that claims are supported:

```python
# From rag_claim_verifier.py
class ClaimVerifier:
    def verify_answer(self, answer: str, retrieved_docs: List[str]):
        """Verify each claim in the answer against retrieved documents."""
        
        # Extract claims from answer
        claims = self.extract_claims(answer)
        # Example: ["Apple's revenue was $394.3B", "Meta grew 15.7%"]
        
        verification_results = []
        for claim in claims:
            # Check if claim is supported by any document
            is_supported = self.check_support(claim, retrieved_docs)
            
            verification_results.append({
                "claim": claim,
                "supported": is_supported,
                "supporting_docs": self.find_supporting_docs(claim, retrieved_docs)
            })
        
        # Calculate overall confidence
        num_supported = sum(1 for r in verification_results if r["supported"])
        overall_confidence = num_supported / len(verification_results)
        
        return ClaimVerificationResult(
            num_supported=num_supported,
            num_contradicted=0,  # Could detect contradictions
            num_not_found=len(verification_results) - num_supported,
            overall_confidence=overall_confidence
        )
```

**Purpose:**
- Catch unsupported claims
- Flag potential hallucinations
- Provide confidence scores

---

## Advanced Features in Your RAG System

### 1. Multi-Hop Retrieval

For complex queries, break into multiple retrieval steps:

```python
# Example: "What was Apple's revenue growth when they launched the iPhone?"
# Step 1: Retrieve Apple's revenue data
# Step 2: Retrieve iPhone launch date
# Step 3: Retrieve revenue around that time
# Step 4: Combine results
```

### 2. Intent-Based Policies

Different retrieval strategies for different intents:

```python
# COMPARE intent: Need same metrics, same periods
# FORECAST intent: Need historical trends
# FACT intent: Need exact values
```

### 3. Temporal Filtering

Filter documents by time period:

```python
# Query: "Apple's revenue in FY2024"
# Filter: Only retrieve documents from FY2024
```

### 4. Memory-Augmented RAG

Track which documents were useful in past conversations:

```python
# If user asked about Apple before, prioritize those documents
# Track document access patterns
```

### 5. Table-Aware Retrieval

Special handling for table queries:

```python
# Query: "Show me Apple's income statement"
# Retrieve: Structured table data, not just narratives
```

---

## Performance Optimizations

### Parallel Retrieval
```python
# Retrieve for multiple tickers in parallel (3-5x faster)
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(retrieve_for_ticker, ticker) for ticker in tickers]
    results = [f.result() for f in futures]
```

### Caching
```python
# Cache embeddings and retrieval results
@cache_embeddings
def encode_query(query: str):
    return embedding_model.encode(query)
```

### Hybrid Retrieval
```python
# Combine sparse (fast) + dense (accurate) for best of both
sparse_results = bm25_search(query)  # Fast keyword matching
dense_results = vector_search(query)  # Accurate semantic matching
fused = fuse(sparse_results, dense_results)  # Best of both
```

---

## Summary: Why RAG Works

1. **Grounded Answers**: Every claim can be traced to a source document
2. **Up-to-Date**: Uses latest data from SEC filings, not training cutoff
3. **Citable**: Can provide URLs, filenames, periods for every fact
4. **Accurate**: Reduces hallucinations by constraining to retrieved context
5. **Flexible**: Can handle new companies, new documents without retraining

---

## Key Files in Your Codebase

- `rag_orchestrator.py` - Main RAG pipeline coordinator
- `rag_retriever.py` - Retrieval logic (SQL + Vector + Hybrid)
- `rag_prompt_template.py` - Prompt building
- `rag_reranker.py` - Document reranking
- `rag_fusion.py` - Source fusion and confidence
- `rag_grounded_decision.py` - Safety checks
- `rag_claim_verifier.py` - Post-generation verification
- `rag_hybrid_retriever.py` - Sparse + Dense retrieval
- `rag_retriever.py` - VectorStore (ChromaDB integration)

---

## Example: Complete RAG Flow

**User Query**: "What was Apple's revenue growth in FY2024?"

1. **Parse**: Extract ticker="AAPL", time="FY2024", intent="FACT"
2. **Retrieve**:
   - SQL: Get revenue metrics for AAPL FY2024
   - Vector: Search SEC filings for "revenue growth" + "FY2024"
   - Hybrid: Combine keyword + semantic matches
3. **Rerank**: Top 5 most relevant SEC excerpts
4. **Fuse**: Combine metrics + documents, confidence=0.82
5. **Decide**: Confidence high → proceed
6. **Build Prompt**: Format metrics + documents into RAG prompt
7. **Generate**: LLM produces answer using retrieved context
8. **Verify**: All claims supported by documents ✅

**Result**: Accurate, citable answer grounded in real SEC filings!

