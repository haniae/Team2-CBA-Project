# New ChromaDB Collections for Enhanced Financial Analysis

## Overview

The vector database now supports **7 document collections** for comprehensive financial analysis:

1. ✅ **SEC Narratives** - Already implemented
2. ✅ **Uploaded Documents** - Already implemented
3. 🆕 **Earnings Transcripts** - New collection (ready for implementation)
4. 🆕 **Financial News** - New collection (ready for implementation)
5. 🆕 **Analyst Reports** - New collection (ready for implementation)
6. 🆕 **Press Releases** - New collection (ready for implementation)
7. 🆕 **Industry Research** - New collection (ready for implementation)

---

## Collections Added

### 1. Earnings Transcripts (`earnings_transcripts`)

**Purpose**: Management commentary, Q&A sessions, forward guidance

**Metadata Structure**:
```python
{
    "ticker": "AAPL",
    "date": "2024-01-25",
    "quarter": "Q1-2024",
    "source_type": "earnings_transcript",
    "source_url": "https://...",
    "chunk_index": 0,
    "total_chunks": 50
}
```

**Use Cases**:
- "What did Apple's CEO say about iPhone sales?"
- "Why did revenue miss expectations?"
- "What guidance did management provide?"

---

### 2. Financial News (`financial_news`)

**Purpose**: Real-time market sentiment, breaking news, industry trends

**Metadata Structure**:
```python
{
    "ticker": "AAPL",
    "date": "2024-11-23",
    "publisher": "Bloomberg",
    "title": "Apple Expands AI Features",
    "source_type": "news",
    "source_url": "https://...",
    "chunk_index": 0,
    "total_chunks": 3
}
```

**Use Cases**:
- "What recent news affected Tesla's stock?"
- "What's driving today's price movement?"
- "What are analysts saying about the sector?"

---

### 3. Analyst Reports (`analyst_reports`)

**Purpose**: Professional equity research, price targets, investment theses

**Metadata Structure**:
```python
{
    "ticker": "AAPL",
    "date": "2024-11-20",
    "analyst": "Goldman Sachs",
    "rating": "Buy",
    "target_price": 200.0,
    "source_type": "analyst_report",
    "source_url": "https://...",
    "chunk_index": 0,
    "total_chunks": 25
}
```

**Use Cases**:
- "What do analysts say about Apple's valuation?"
- "What's the investment thesis?"
- "What are the price targets?"

---

### 4. Press Releases (`press_releases`)

**Purpose**: Official company announcements, strategic updates

**Metadata Structure**:
```python
{
    "ticker": "AAPL",
    "date": "2024-11-15",
    "title": "Apple Announces New Product Line",
    "category": "Product Launch",
    "source_type": "press_release",
    "source_url": "https://...",
    "chunk_index": 0,
    "total_chunks": 5
}
```

**Use Cases**:
- "What did Apple announce about their AI strategy?"
- "What products were launched?"
- "What strategic initiatives were announced?"

---

### 5. Industry Research (`industry_research`)

**Purpose**: Sector analysis, market trends, competitive landscape

**Metadata Structure**:
```python
{
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "date": "2024-11-01",
    "title": "Smartphone Market Analysis 2024",
    "source_type": "industry_research",
    "source_url": "https://...",
    "chunk_index": 0,
    "total_chunks": 30
}
```

**Use Cases**:
- "How does Apple compare to the smartphone market?"
- "What are the industry trends?"
- "What's the competitive landscape?"

---

## API Usage

### Adding Documents

```python
from finanlyzeos_chatbot.rag_retriever import VectorStore
from pathlib import Path

vector_store = VectorStore(Path("data/financial.db"))

# Earnings transcripts
earnings_docs = [
    {
        "text": "Management commentary text...",
        "metadata": {
            "ticker": "AAPL",
            "date": "2024-01-25",
            "quarter": "Q1-2024",
            "source_type": "earnings_transcript",
            "source_url": "https://...",
            "chunk_index": 0,
            "total_chunks": 50
        }
    }
]
vector_store.add_earnings_transcripts(earnings_docs)

# Financial news
news_docs = [
    {
        "text": "News article text...",
        "metadata": {
            "ticker": "AAPL",
            "date": "2024-11-23",
            "publisher": "Bloomberg",
            "title": "Apple Expands AI Features",
            "source_type": "news",
            "source_url": "https://...",
            "chunk_index": 0,
            "total_chunks": 3
        }
    }
]
vector_store.add_financial_news(news_docs)

# Analyst reports
analyst_docs = [
    {
        "text": "Analyst report text...",
        "metadata": {
            "ticker": "AAPL",
            "date": "2024-11-20",
            "analyst": "Goldman Sachs",
            "rating": "Buy",
            "target_price": 200.0,
            "source_type": "analyst_report",
            "source_url": "https://...",
            "chunk_index": 0,
            "total_chunks": 25
        }
    }
]
vector_store.add_analyst_reports(analyst_docs)

# Press releases
press_docs = [
    {
        "text": "Press release text...",
        "metadata": {
            "ticker": "AAPL",
            "date": "2024-11-15",
            "title": "Apple Announces New Product Line",
            "category": "Product Launch",
            "source_type": "press_release",
            "source_url": "https://...",
            "chunk_index": 0,
            "total_chunks": 5
        }
    }
]
vector_store.add_press_releases(press_docs)

# Industry research
industry_docs = [
    {
        "text": "Industry research text...",
        "metadata": {
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "date": "2024-11-01",
            "title": "Smartphone Market Analysis 2024",
            "source_type": "industry_research",
            "source_url": "https://...",
            "chunk_index": 0,
            "total_chunks": 30
        }
    }
]
vector_store.add_industry_research(industry_docs)
```

### Searching Documents

```python
# Search individual collections
earnings_results = vector_store.search_earnings_transcripts(
    query="What did management say about revenue?",
    n_results=5,
    filter_metadata={"ticker": "AAPL"}
)

news_results = vector_store.search_financial_news(
    query="What recent news affected the stock?",
    n_results=5,
    filter_metadata={"ticker": "AAPL"}
)

# Search all collections at once
all_results = vector_store.search_all_sources(
    query="What's driving Apple's performance?",
    n_results_per_source=3,
    filter_metadata={"ticker": "AAPL"}
)

# Results structure:
# {
#     "sec_filings": [...],
#     "uploaded_docs": [...],
#     "earnings_transcripts": [...],
#     "financial_news": [...],
#     "analyst_reports": [...],
#     "press_releases": [...],
#     "industry_research": [...]
# }
```

---

## Indexing Script Usage

The indexing script now supports the new document types:

```bash
# Index all document types
python scripts/index_documents_for_rag.py --database data/financial.db --type all

# Index specific types
python scripts/index_documents_for_rag.py --database data/financial.db --type earnings
python scripts/index_documents_for_rag.py --database data/financial.db --type news
python scripts/index_documents_for_rag.py --database data/financial.db --type analyst
python scripts/index_documents_for_rag.py --database data/financial.db --type press
python scripts/index_documents_for_rag.py --database data/financial.db --type industry
```

**Note**: Currently, these new types show "Not yet implemented" messages. The collections are ready, but data fetchers and parsers need to be implemented.

---

## Next Steps

### Phase 1: Earnings Transcripts (Highest Priority)

1. **Data Source**: Seeking Alpha, Fintel.io, or company IR pages
2. **Parser**: Extract Q&A sections, management commentary
3. **Indexing**: Add to `earnings_transcripts` collection

### Phase 2: Financial News

1. **Data Source**: Yahoo Finance news, RSS feeds, NewsAPI
2. **Parser**: Extract article text, metadata
3. **Indexing**: Add to `financial_news` collection

### Phase 3: Analyst Reports, Press Releases, Industry Research

1. **Data Sources**: Various (Seeking Alpha, company IR, industry associations)
2. **Parsers**: Extract relevant text sections
3. **Indexing**: Add to respective collections

---

## Benefits

### Enhanced Query Coverage

**Before** (SEC filings only):
- ✅ "What is Apple's revenue?" → SEC 10-K
- ❌ "What did management say about guidance?" → No answer

**After** (All collections):
- ✅ "What is Apple's revenue?" → SEC 10-K
- ✅ "What did management say about guidance?" → Earnings transcript
- ✅ "What recent news affected the stock?" → Financial news
- ✅ "What do analysts say?" → Analyst reports
- ✅ "What did the company announce?" → Press releases
- ✅ "How does this compare to the industry?" → Industry research

### Richer Context

The chatbot can now provide:
- **Management perspective** (earnings transcripts)
- **Market sentiment** (financial news)
- **Professional analysis** (analyst reports)
- **Official announcements** (press releases)
- **Sector context** (industry research)

---

## Implementation Status

| Collection | Status | Next Steps |
|------------|--------|------------|
| SEC Narratives | ✅ Implemented | Continue indexing |
| Uploaded Documents | ✅ Implemented | User uploads |
| Earnings Transcripts | 🆕 Ready | Add fetcher/parser |
| Financial News | 🆕 Ready | Add fetcher/parser |
| Analyst Reports | 🆕 Ready | Add fetcher/parser |
| Press Releases | 🆕 Ready | Add fetcher/parser |
| Industry Research | 🆕 Ready | Add fetcher/parser |

---

## Technical Details

### Collection Names

All collections follow the pattern: `{collection_name}_{type}`

- `financial_documents_sec`
- `financial_documents_uploaded`
- `financial_documents_earnings`
- `financial_documents_news`
- `financial_documents_analyst`
- `financial_documents_press`
- `financial_documents_industry`

### ID Generation

Document IDs are generated based on source type:
- SEC: `{ticker}_{filing_type}_{fiscal_year}_{section}_{index}`
- Earnings: `{ticker}_earnings_{date}_{quarter}_{index}`
- News: `{ticker}_news_{date}_{publisher}_{index}`
- Analyst: `{ticker}_analyst_{date}_{analyst}_{index}`
- Press: `{ticker}_press_{date}_{index}`
- Industry: `industry_{sector}_{date}_{index}`

---

## Summary

✅ **Collections Created**: 5 new collections added to ChromaDB  
✅ **API Methods**: Add and search methods for each collection  
✅ **Unified Search**: `search_all_sources()` method for cross-collection search  
✅ **Indexing Script**: Updated to support new document types  
⏳ **Data Fetchers**: Need to be implemented for each source type  

The infrastructure is ready. Next step: Implement data fetchers and parsers for each source type.

