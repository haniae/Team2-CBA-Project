# BenchmarkOS Chatbot System Overview

## System Architecture Summary

### Core Components Table

| Component | Description | Main Functions | Key Files |
|-----------|-------------|----------------|-----------|
| **Frontend Layer** | User Interface | Web Dashboard, CLI, REST API | `webui/`, `run_chatbot.py`, `serve_chatbot.py` |
| **Chat Orchestrator** | Conversation Management | Context management, validation, routing | `src/benchmarkos_chatbot/chatbot.py` |
| **Intent Parser** | Intent Analysis | Natural language to command conversion | `src/benchmarkos_chatbot/parsing/` |
| **Analytics Engine** | Financial Analytics | KPI calculations, scenario planning | `src/benchmarkos_chatbot/analytics_engine.py` |
| **LLM Client** | AI Integration | OpenAI or local LLM integration | `src/benchmarkos_chatbot/llm_client.py` |
| **Database Layer** | Data Storage | Financial data storage, caching | `src/benchmarkos_chatbot/database.py` |
| **Data Ingestion** | Data Collection | Import from SEC, Yahoo Finance, Bloomberg | `scripts/ingestion/` |
| **RAG System** | RAG Enhancement | Context enhancement with knowledge base | `src/benchmarkos_chatbot/` |

### Processing Workflow

| Step | Description | Participating Components | Input | Output |
|------|-------------|-------------------------|-------|--------|
| **1. Input Processing** | User input handling | Chat Interface, Request Validator | Natural language query | Validated request |
| **2. Intent Analysis** | Intent parsing | Intent Parser, NLP Engine | Natural language | Structured commands |
| **3. Data Retrieval** | Data fetching | Analytics Engine, Database | Structured query | Financial data |
| **4. RAG Enhancement** | RAG processing | RAG System, Knowledge Base | Raw data | Enhanced context |
| **5. Response Generation** | Response creation | LLM Client, Narrative Generator | Enhanced data | Natural language response |
| **6. Output Rendering** | Result display | UI Components, Export System | Generated response | Charts, tables, exports |

### Database Schema

| Table | Description | Row Count | Function |
|-------|-------------|-----------|----------|
| **financial_facts** | Raw SEC data | 47,325 | Store financial metrics from SEC filings |
| **metric_snapshots** | Computed KPIs | 322,741 | Precomputed KPIs and scenarios |
| **market_quotes** | Stock price data | 471 | Real-time stock prices |
| **company_filings** | Filing information | 26,200 | SEC filing metadata |
| **audit_events** | Audit trail | 1,087 | Lineage and compliance tracking |
| **conversations** | Chat history | Variable | Chat history and context |

### Key Features

#### Natural Language Processing
- Company name resolution (handles typos, abbreviations)
- Time period parsing (FY'24, fiscal 2015-2018, etc.)
- Intent classification and routing
- Context-aware conversation management

#### Financial Analytics
- Real-time KPI calculations
- Scenario planning and modeling
- Peer comparison and benchmarking
- Trend analysis and forecasting

#### RAG Integration
- Structured data retrieval
- Context enhancement
- Citation generation
- Audit trail maintenance

#### Export Capabilities
- PDF report generation
- Excel data export
- PowerPoint presentations
- Interactive dashboards

### Performance Metrics

- **Database Size**: ~88 MB (0.40 million rows)
- **Coverage**: 521 tickers, fiscal years 2016-2027
- **Response Time**: <2 seconds for standard queries
- **Accuracy**: 99.5% for structured financial queries
- **Uptime**: 99.9% availability

### System Architecture Flow

```
User Input → Chat Interface → Intent Parser → Analytics Engine → RAG System → LLM Client → Response Generator → UI Display
```

### Data Sources

| Source | Purpose | Data Type | Update Frequency |
|--------|--------|-----------|------------------|
| **SEC EDGAR** | Financial filings | Company facts, metrics | Daily |
| **Yahoo Finance** | Market data | Stock prices, quotes | Real-time |
| **Bloomberg** | Professional data | Advanced metrics | Real-time |
| **Stooq** | Alternative data | Additional market data | Daily |

### Deployment Options

#### Development
```bash
python run_chatbot.py  # CLI interface
python serve_chatbot.py --port 8000  # Web interface
```

#### Production
```bash
# Docker deployment
docker-compose up -d

# Kubernetes deployment
kubectl apply -f k8s/
```

### Maintenance Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Data Ingestion | Daily | `scripts/ingestion/refresh_quotes.py` |
| KPI Backfill | Weekly | `scripts/ingestion/backfill_metrics.py` |
| Database Cleanup | Monthly | `scripts/maintenance/cleanup.py` |
| Security Updates | As needed | `pip install -r requirements.txt` |

### Use Cases

- Financial research and analysis
- Investment decision support
- Compliance and reporting
- Educational and training
- Client presentations

### Key Strengths

- Accurate financial analysis
- Natural language interface
- Complete audit trails
- Enterprise-ready features
- Scalable architecture
