# FinalyzeOS Presentation Structure for FI
## Conversational Q&A Format - Thursday Meeting

---

## 🎯 **PRESENTATION PHILOSOPHY**

**FI's Request**: Conversational session with Q&A, not a strict presentation  
**Our Approach**: Use slides as visual anchors, focus on dialogue and deep dives  
**Tone**: Professional but approachable, technical but accessible

---

## 📊 **SLIDE STRUCTURE (6-8 slides max)**

### **Slide 1: Title & Team**
**Visual**: Clean, professional title slide

**Content:**
- **FinalyzeOS: AI Agent for Finance Teams**
- Built by: Devarsh, Hania, Vannhi, Malcolm
- GW Business & Data Science Practicum (Fall 2025)
- **Logos**: GW | FinalyzeOS | FI (optional)

**Talking Points:**
- "We're excited to share how we built FinalyzeOS in 3 months"
- "This is a conversational session - please interrupt with questions"
- "We'll walk through our tech stack, workflows, and lessons learned"

---

### **Slide 2: Problem & Opportunity**
**Visual**: Simple problem statement with opportunity callout

**Content (Bullet Points):**
- Financial analysis is slow, inconsistent, and manually intensive
- Analysts use many disconnected tools (Excel, EDGAR, dashboards)
- Hard to trace formulas, methods, and narrative back to source data
- **Opportunity**: Build an audit-ready AI copilot for institutional finance

**Talking Points:**
- "We started by understanding the pain points of financial analysts"
- "The key insight: analysts spend 80% of time gathering data, 20% analyzing"
- "We wanted to flip that ratio with AI-powered automation"

---

### **Slide 3: What FinalyzeOS Does**
**Visual**: 3-5 icons representing key capabilities

**High-Level Capabilities:**
- Natural-language Q&A on SEC-verified financials
- Real-time KPI generation with provenance
- Forecasting, benchmarking, scenario modeling
- Compliance-ready audit logs
- Deterministic SQL + retrieval augmented generation (RAG)

**Talking Points:**
- "Think of it as ChatGPT for finance, but with full source traceability"
- "Every number links back to the exact SEC filing"
- "We handle 1,599 companies, 18 years of data, 93 financial metrics"

---

### **Slide 4: Architecture Overview (One Clean Diagram)**
**Visual**: Simple flow diagram showing major layers

**Layers (Top to Bottom):**
1. **Frontend** → React/Next.js, Chat interface
2. **LLM Reasoning** → Codex, GPT-4, GPT-4.1
3. **RAG Pipeline** → Hybrid search (SQL + semantic embeddings)
4. **Processing** → ETL pipelines (Python, SQLite, ChromaDB)
5. **Ingestion** → SEC filings + APIs (Yahoo Finance, FRED, IMF)

**Talking Points:**
- "We use a hybrid approach: deterministic SQL for numbers, semantic search for narratives"
- "The RAG pipeline is the heart - it combines retrieval with generation"
- "Everything is orchestrated through Python, with FastAPI for the backend"

---

### **Slide 5: Key Technologies & Why We Chose Them**
**Visual**: Technology logos/icons in a grid

**Technologies & Rationale:**

| Technology | Why We Chose It | Key Benefit |
|------------|----------------|-------------|
| **Codex / GPT-4** | Code generation & reasoning | Natural language → SQL, explanations |
| **Cursor AI** | Development acceleration | AI pair programming, faster iteration |
| **ETL Pipelines (Python)** | Deterministic data prep | Reliable, auditable data processing |
| **SQLite + ChromaDB** | Fast local storage | Structured + unstructured retrieval |
| **FastAPI** | Lightweight API routing | Fast, secure endpoints |
| **RAG (16 features)** | Production-grade retrieval | Hybrid sparse+dense, reranking, verification |
| **SentenceTransformers** | Embeddings | Semantic search over SEC filings |

**Talking Points:**
- **Codex**: "We used Codex to generate SQL queries from natural language - huge time saver"
- **Cursor**: "Cursor AI was our secret weapon - it accelerated development by 3-4x"
- **RAG**: "We implemented 16 advanced RAG features - hybrid retrieval, reranking, claim verification"
- **ChromaDB**: "Vector database for semantic search - allows us to find relevant SEC filing excerpts"

---

### **Slide 5A: The Four Pillars (If Time Permits)**
**Visual**: Four quadrants showing the core areas FI is interested in

**1. Codex - Code Generation & Reasoning**
- **Use Cases**: SQL generation, Python ETL scripts, test case creation
- **Example**: "Generate SQL to calculate ROE for all S&P 500 companies" → Codex produces optimized query
- **Impact**: Reduced SQL writing time by 70%

**2. GenAI Workflows - RAG Pipeline Orchestration**
- **Components**: Intent detection → Hybrid retrieval → Reranking → Generation → Verification
- **Example**: User asks "Why did Apple's revenue decline?" → System retrieves relevant SEC excerpts → Generates explanation with citations
- **Impact**: 16 advanced features working together seamlessly

**3. Data-Processing Pipelines - ETL & Ingestion**
- **Process**: SEC EDGAR → XBRL parsing → Normalization → SQLite storage → ChromaDB indexing
- **Scale**: 1,599 companies, 18 years, 2.8M+ rows processed
- **Impact**: Automated what would take months manually

**4. Supporting Tools - Development Acceleration**
- **Tools**: Cursor AI, ChromaDB, SentenceTransformers, FastAPI
- **Role**: Each tool solved a specific problem (development speed, vector search, embeddings, API)
- **Impact**: 3-4x faster development, production-ready in 3 months

---

### **Slide 6: How We Built It in 3 Months**
**Visual**: Timeline or phase breakdown

**Phases:**

**Month 1: Foundation**
- Data ingestion from SEC EDGAR
- Schema design for financial data
- KPI dictionary (93 metrics)
- Basic SQL retrieval

**Month 2: Intelligence Layer**
- RAG pipeline implementation
- Embeddings & semantic search
- Validation layers & guardrails
- Hybrid retrieval (sparse + dense)

**Month 3: Production Polish**
- UI/UX development
- Orchestration & API endpoints
- Testing & compliance features
- Demo preparation

**Talking Points:**
- "Month 1 was all about data - we ingested 1,599 companies from SEC EDGAR"
- "Month 2 we built the intelligence - RAG pipeline with 16 advanced features"
- "Month 3 was polish - making it production-ready with full audit trails"

---

### **Slide 7: Demo & Use Case Examples**
**Visual**: Screenshots or mockups of the interface

**Two Use Cases to Show:**

1. **"Compare Apple vs Microsoft net income over 5 years"**
   - Shows: Multi-company comparison, time-series analysis
   - Highlights: SQL retrieval, RAG context, source citations

2. **"Forecast Tesla's revenue for the next 4 quarters"**
   - Shows: ML forecasting, confidence intervals
   - Highlights: 8 ML models, explainable predictions

**Talking Points:**
- "Let me show you a quick demo..."
- "Notice how every number has a source link"
- "The system generates this in under 30 seconds"

---

### **Slide 8: Q&A**
**Visual**: Simple "Q&A" title slide

**Talking Points:**
- "We're happy to dive deeper into any aspect"
- "Questions about our tech stack, workflows, or lessons learned?"

---

## 🗣️ **Q&A PREPARATION BY CATEGORY**

### **CATEGORY 0: THE FOUR PILLARS (FI's Core Interests)**

**Expected Questions:**

**Q: "How did you leverage Codex specifically?"**
- **Answer**: "We used Codex in three main ways: (1) SQL generation from natural language queries, (2) Python ETL script generation for data processing, (3) Test case creation for validation. It was especially powerful for generating complex SQL queries that would have taken hours to write manually."
- **Concrete Example**: "When we needed to calculate 93 different financial metrics, we'd prompt Codex: 'Generate SQL to calculate ROE (return on equity) for all companies in the database, handling edge cases like negative equity.' Codex would produce a complete, optimized query in seconds."
- **Impact**: "Reduced SQL writing time by about 70%. What took 2-3 hours now took 20-30 minutes."

**Q: "Can you walk us through your GenAI workflows?"**
- **Answer**: "Our GenAI workflow is a complete RAG pipeline: (1) Query comes in → (2) Intent detection determines what type of question it is → (3) Hybrid retrieval (SQL + semantic search) finds relevant data → (4) Reranking improves relevance → (5) LLM generates answer using only retrieved context → (6) Claim verification checks each sentence → (7) Response formatting adds citations."
- **Workflow Diagram**: "The key is orchestration - we have 16 advanced features working together. For example, if it's a 'why' question, we use multi-hop retrieval to break it into sub-queries. If it's a comparison, we enforce same time periods."
- **Why It Matters**: "This workflow ensures accuracy - the LLM can only use what we retrieve, so hallucinations are minimized."

**Q: "Tell us about your data-processing pipelines."**
- **Answer**: "Our pipeline has five stages: (1) Ingestion from SEC EDGAR (download 10-K/10-Q filings), (2) XBRL parsing to extract structured financial data, (3) Normalization (fiscal periods, metric names, units), (4) Storage in SQLite for structured queries, (5) Chunking and embedding for ChromaDB vector search."
- **Scale**: "We processed 1,599 companies, 18 years of data, resulting in 2.8M+ rows in SQLite and 100,000+ document chunks in ChromaDB."
- **Challenges**: "XBRL tags change over time, fiscal periods vary by company, and some filings have errors. We built robust error handling and normalization layers."
- **Automation**: "The entire pipeline runs automatically - we can ingest a new company in about 5 minutes."

**Q: "What supporting tools were most critical?"**
- **Answer**: "Four tools were game-changers: (1) Cursor AI for development acceleration - it was like having an AI pair programmer, (2) ChromaDB for vector search - fast semantic retrieval over SEC filings, (3) SentenceTransformers for embeddings - converts text to vectors for semantic search, (4) FastAPI for the backend - lightweight, fast API endpoints."
- **Cursor Impact**: "Cursor probably accelerated development by 3-4x. We'd describe what we wanted, and it would generate code, refactor, debug, and write tests. Especially helpful for complex RAG orchestration logic."
- **ChromaDB Impact**: "ChromaDB enabled semantic search over 100,000+ SEC filing chunks in 50ms. Without it, we'd need a cloud vector database service, which would add cost and latency."

---

### **CATEGORY 1: TECHNOLOGY STACK**

**Expected Questions:**

**Q: "Why Codex?"**
- **Answer**: "We used Codex for code generation - it helped us write SQL queries from natural language, generate Python scripts for ETL, and create test cases. It accelerated development significantly."
- **Example**: "Instead of manually writing SQL for each metric, we'd prompt Codex: 'Generate SQL to calculate ROE for all S&P 500 companies' and it would produce the query."
- **Specific Use Cases**: 
  - SQL generation: "Calculate revenue growth YoY for all companies"
  - ETL scripts: "Create Python script to parse XBRL and normalize fiscal periods"
  - Test cases: "Generate test cases for metric calculation edge cases"
- **Time Savings**: "Reduced SQL writing time by 70% - what took 2-3 hours now takes 20-30 minutes"

**Q: "Why semantic embedding search?"**
- **Answer**: "Financial questions often need narrative context, not just numbers. Semantic search finds relevant SEC filing excerpts that explain 'why' revenue changed, not just 'what' the number is."
- **Trade-off**: "We combine it with SQL for exact numbers - hybrid approach gives us both accuracy and context."

**Q: "How did you avoid hallucinations?"**
- **Answer**: "Multiple layers: (1) Grounded decision layer checks retrieval confidence before answering, (2) Claim-level verification verifies each sentence, (3) RAG forces LLM to use only retrieved context, (4) Source citations for every claim."
- **Example**: "If retrieval confidence is below 30%, we don't answer - we say 'I don't have enough information' instead of guessing."

**Q: "How did you use Cursor in development?"**
- **Answer**: "Cursor was our AI pair programmer. We'd describe what we wanted, and it would generate code, refactor, debug, and write tests. It was especially helpful for RAG pipeline implementation - complex orchestration logic."
- **Impact**: "Probably 3-4x faster development. What took days took hours."
- **Specific Examples**:
  - RAG orchestrator: "Implement a multi-hop retrieval system that decomposes complex queries"
  - Error handling: "Add robust error handling for missing SEC filings"
  - API endpoints: "Create FastAPI endpoints for chat, metrics, and forecasts"
- **Learning Curve**: "First week was learning how to prompt effectively, but after that it became second nature"

---

### **CATEGORY 2: DATA PIPELINES & INGESTION**

**Expected Questions:**

**Q: "How did you normalize XBRL tags?"**
- **Answer**: "We built a mapping layer that standardizes XBRL tags to our internal metric names. For example, 'us-gaap:Revenues' maps to 'revenue'. We also handle variations across filing periods."
- **Challenge**: "XBRL tags change over time - we maintain a versioned mapping table."

**Q: "How did you handle inconsistencies over time?"**
- **Answer**: "We use fiscal period normalization - convert all dates to fiscal year/quarter. We also track filing revisions and use the most recent version. For missing data, we backfill using interpolation or mark as 'not available'."
- **Example**: "Apple's fiscal year ends in September, but we normalize to calendar year for comparisons."

**Q: "What schema decisions mattered most?"**
- **Answer**: "Three key decisions: (1) Separate tables for metrics vs. narratives, (2) Time-series structure with fiscal periods, (3) Metadata-rich schema for filtering. This enabled fast SQL queries and efficient RAG retrieval."
- **Impact**: "Our schema design allowed us to query 1,599 companies in milliseconds."

---

### **CATEGORY 3: RAG PIPELINE & MODEL ORCHESTRATION**

**Expected Questions:**

**Q: "How do you decide between SQL vs embeddings?"**
- **Answer**: "Intent-based routing. Simple metric queries → SQL. Explanation queries → Embeddings. Comparison queries → Both. We use an IntentPolicyManager that selects the right retrieval strategy."
- **Example**: "'What is Apple's revenue?' → SQL. 'Why did Apple's revenue decline?' → Embeddings + SQL."

**Q: "How do you enforce citations?"**
- **Answer**: "Three mechanisms: (1) RAG prompt explicitly instructs LLM to cite sources, (2) Post-generation verification checks for citations, (3) Response formatter adds SEC URLs to every number."
- **Result**: "Every response has clickable SEC filing links."

**Q: "How does the multi-layer retrieval work?"**
- **Answer**: "We use hybrid retrieval: (1) Dense (embeddings) for semantic similarity, (2) Sparse (BM25) for exact keyword matches, (3) Fusion combines both with 60/40 weighting, (4) Reranking with cross-encoder for final ordering."
- **Why**: "Dense finds 'revenue growth' even if document says 'increasing sales'. Sparse finds exact ticker matches. Fusion gives best of both."

**Q: "How does your cross-checking reduce hallucination?"**
- **Answer**: "Multiple verification layers: (1) Grounded decision checks confidence before answering, (2) Claim verification checks each sentence against retrieved docs, (3) Source fusion weights reliability (SEC > uploaded docs), (4) Temporal filtering ensures time consistency."
- **Example**: "If a claim isn't supported by retrieved docs, we either regenerate or flag it as uncertain."

---

### **CATEGORY 4: PRODUCT STRATEGY + UX**

**Expected Questions:**

**Q: "Why build a chat interface?"**
- **Answer**: "Natural language is the most intuitive interface. Analysts already ask questions in plain English - we just made the system understand them. No training needed."
- **Impact**: "Adoption is instant - no learning curve."

**Q: "What feedback did judges give?"**
- **Answer**: "Positive feedback on: (1) Full source traceability, (2) Speed (<30 seconds), (3) Accuracy (95%+). Areas for improvement: (1) More ML models, (2) Better visualization, (3) Export formats."
- **Takeaway**: "Judges valued auditability and speed most."

**Q: "How does a CFO actually use this?"**
- **Answer**: "Use case: Board presentation prep. CFO asks 'Compare our margins to sector peers' → System generates peer comparison with citations in <30 seconds. Export to PowerPoint with embedded source links."
- **Value**: "What takes 3-5 days manually now takes minutes."

---

### **CATEGORY 5: TEAM COLLABORATION & PROCESS**

**Expected Questions:**

**Q: "How did you divide responsibilities?"**
- **Answer**: "We used agile sprints with rotating ownership: (1) Data ingestion - Devarsh, (2) RAG pipeline - Hania, (3) ML forecasting - Vannhi, (4) UI/UX - Malcolm. But we all contributed to each area."
- **Process**: "Daily standups, weekly demos, shared code reviews."

**Q: "What part took the longest?"**
- **Answer**: "RAG pipeline implementation - 16 advanced features took about 6 weeks. Getting hybrid retrieval, reranking, and verification working together was complex."
- **Challenge**: "Orchestrating all the components - retrieval, processing, generation, verification - required careful design."

**Q: "What would you do differently?"**
- **Answer**: "Three things: (1) Start with simpler RAG, add features incrementally, (2) More testing earlier - we tested late, (3) Better documentation - we wrote docs as we went, but should have started earlier."
- **Lesson**: "Build incrementally, test continuously, document as you go."

---

## 🔄 **CONCRETE WORKFLOW EXAMPLE: How The Four Pillars Work Together**

**Scenario**: User asks "Why did Apple's revenue decline in FY2023 compared to Microsoft?"

### **Step-by-Step Workflow:**

**1. Data-Processing Pipeline (Background)**
- SEC EDGAR ingestion downloaded Apple and Microsoft 10-K filings
- XBRL parsing extracted revenue numbers and MD&A sections
- Normalization converted to fiscal periods and standardized units
- Storage: Revenue metrics → SQLite, MD&A text → ChromaDB (chunked & embedded)

**2. GenAI Workflow (Query Processing)**
- **Intent Detection**: Detects "WHY" + "COMPARE" intent → Uses multi-hop policy
- **Hybrid Retrieval**: 
  - SQL query (generated by Codex) fetches exact revenue numbers
  - Semantic search (ChromaDB) finds relevant MD&A excerpts explaining decline
  - BM25 search finds exact keyword matches
- **Reranking**: Cross-encoder reorders results by true relevance
- **Generation**: GPT-4 generates answer using only retrieved context
- **Verification**: Claim verifier checks each sentence against sources

**3. Codex Usage (Throughout)**
- Generated SQL query: "SELECT revenue FROM metric_snapshots WHERE ticker IN ('AAPL', 'MSFT') AND fiscal_year = 2023"
- Generated Python code for multi-hop decomposition
- Generated test cases for validation

**4. Supporting Tools (Infrastructure)**
- **ChromaDB**: Fast semantic search (50ms for 100K chunks)
- **Cursor**: Helped implement the orchestration logic
- **FastAPI**: Serves the API endpoint
- **SentenceTransformers**: Generates embeddings for semantic search

### **Result:**
- Complete answer with citations in <30 seconds
- Every number links to SEC filing
- Explanation based on actual MD&A text, not hallucination

**Key Insight**: "The four pillars aren't separate - they're integrated. Codex generates code for the pipeline, the pipeline feeds the GenAI workflow, and supporting tools enable it all to run fast and reliably."

---

## ⭐ **CONVERSATIONAL FLOW TIPS**

### **The "Question → Repeat → Answer → Example" Pattern**

**Example 1:**
- **Question**: "How did you enforce accuracy?"
- **Repeat**: "So you're asking how we prevented hallucinations?"
- **Answer**: "We use multiple layers: grounded decision checks confidence, claim verification checks each sentence, and RAG forces the LLM to use only retrieved context."
- **Example**: "When the model gives a KPI, we force a SQL verification step. If the SQL result doesn't match, we regenerate."

**Example 2:**
- **Question**: "Why ChromaDB?"
- **Repeat**: "You want to know why we chose ChromaDB over other vector databases?"
- **Answer**: "Three reasons: (1) Local-first - no cloud dependency, (2) Fast HNSW indexing for semantic search, (3) Easy Python integration. We also considered Pinecone and Weaviate, but ChromaDB fit our needs best."
- **Example**: "We can search 100,000 SEC filing chunks in 50ms using ChromaDB's HNSW index."

---

## 📋 **KEY METRICS TO MENTION**

**Performance:**
- Response time: <30 seconds for comprehensive analysis
- Accuracy: 95%+ on structured financial queries
- Data coverage: 1,599 S&P 1500 companies, 18 years (2009-2027)
- Database size: 2.8M+ rows of financial data

**Capabilities:**
- 93 financial metrics
- 150+ question patterns
- 40+ intent types
- 90% company name spelling correction
- 100% metric spelling correction

**Technical:**
- 16 advanced RAG features
- Hybrid retrieval (sparse + dense)
- 8 ML forecasting models
- Full audit trail with SEC filing links

---

## 🎯 **CLOSING REMARKS**

**If Asked: "What's Next?"**
- "We're exploring: (1) Real-time data updates, (2) More ML models, (3) Multi-language support, (4) Enterprise deployment patterns."
- "We're open to feedback and collaboration opportunities."

**If Asked: "Can We Use This?"**
- "The codebase is available - we're happy to discuss licensing or collaboration."
- "We built it as a learning project, but it's production-ready."

---

## 📝 **PRE-MEETING CHECKLIST**

- [ ] Review all slides (6-8 max)
- [ ] Prepare demo queries (2-3 examples)
- [ ] Test demo environment (ensure it works)
- [ ] Review Q&A categories (5 categories)
- [ ] Practice conversational flow (Question → Repeat → Answer → Example)
- [ ] Prepare key metrics (performance, capabilities, technical)
- [ ] Bring laptop for live demo (if possible)
- [ ] Prepare backup slides (in case of deep dives)

---

## 🎤 **PRESENTATION TIPS**

1. **Be Conversational**: Don't read slides - use them as anchors
2. **Encourage Questions**: "Feel free to interrupt - this is a conversation"
3. **Show, Don't Tell**: Use demos and examples
4. **Be Honest**: Acknowledge challenges and trade-offs
5. **Highlight Learning**: Emphasize what you learned, not just what you built

---

**Good luck with your presentation! 🚀**

