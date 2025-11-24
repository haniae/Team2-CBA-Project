# Vector Database Ingestion Guide

## Overview

This guide explains how to populate the vector database (ChromaDB) with SEC filing data for RAG (Retrieval-Augmented Generation) functionality.

**Quick Status Check:**
```cmd
python check_vector_db.py
```

## Database Location

The script works with any SQLite database. Common locations:
- `data/financial.db` - BenchmarkOS financial database
- `data/sqlite/finanlyzeos_chatbot.sqlite3` - Default chatbot database
- `benchmarkos_chatbot.sqlite3` - Alternative location

## Quick Start

### 0. Check Vector Database Status

**Windows PowerShell/CMD:**
```cmd
REM Quick status check
python check_vector_db.py
```

This shows:
- Number of SEC narratives indexed
- Number of uploaded documents indexed
- Total document count
- Sample documents

### 1. Check Your Database

First, identify which database has your data:

```bash
# Check if database has company_filings table
python -c "import sqlite3; from pathlib import Path; db = Path('YOUR_DATABASE_PATH'); conn = sqlite3.connect(str(db)); print('Has company_filings:', 'company_filings' in [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]); conn.close()"
```

### 2. Index from Existing Database

If your database already has `company_filings` table:

**Windows PowerShell or CMD:**
```cmd
python scripts/index_documents_for_rag.py --database data/financial.db --type sec
```

### 3. Fetch from SEC API (Recommended if Database is Empty)

**Option A: Single Ticker**

**Windows PowerShell or CMD:**
```cmd
REM Fetch and index filings for Apple
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --ticker AAPL --fetch-from-sec --limit 10

REM Fetch for Microsoft (run separately)
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --ticker MSFT --fetch-from-sec --limit 10
```

**Option B: All Tickers (S&P 500 or S&P 1500)**

**Windows PowerShell or CMD:**
```cmd
REM Process all S&P 500 tickers (500 companies)
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --universe sp500 --fetch-from-sec --limit 5

REM Process all S&P 1500 tickers (1500 companies) - takes longer!
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --universe sp1500 --fetch-from-sec --limit 5

REM Test with first 10 tickers only
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --universe sp500 --fetch-from-sec --limit 3 --max-tickers 10

REM Resume from a specific ticker (if interrupted)
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --universe sp500 --fetch-from-sec --limit 5 --start-from MSFT
```

### 4. Index Specific Filing Types

**Windows PowerShell or CMD:**
```cmd
REM Only 10-K annual reports
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --ticker AAPL --filing-type 10-K --fetch-from-sec --limit 5
```

## What Gets Indexed

The script extracts and indexes these narrative sections from SEC filings:

1. **Management's Discussion and Analysis (MD&A)** - Management's perspective on financial results
2. **Risk Factors** - Company risk disclosures
3. **Business Overview** - Company business description

Each section is:
- Chunked into 1500-character segments with 200-character overlap
- Embedded using the `all-MiniLM-L6-v2` model
- Stored in ChromaDB for semantic search

## Required Packages

```bash
pip install chromadb sentence-transformers requests beautifulsoup4
```

## Script Options

```
--database DATABASE     Path to SQLite database (required)
--type {sec,uploaded,all}  What to index (default: all)
--ticker TICKER         Filter SEC filings by ticker (or use --universe)
--universe {sp500,sp1500}  Process all tickers from universe
--filing-type FILING_TYPE  Filter by form type (e.g., 10-K, 10-Q)
--fetch-from-sec        Fetch filings from SEC API if not in database
--limit LIMIT           Limit number of filings per ticker to process
--max-tickers MAX       Limit number of tickers (when using --universe)
--start-from TICKER     Resume from this ticker (useful for interrupted runs)
```

## Processing All Tickers

### Time Estimates

- **S&P 500**: ~500 tickers × ~2-5 minutes per ticker = **16-40 hours**
- **S&P 1500**: ~1500 tickers × ~2-5 minutes per ticker = **50-125 hours**

### Recommendations

1. **Start Small**: Test with `--max-tickers 10` first
2. **Use Limits**: `--limit 5` gets 5 filings per ticker (enough for recent data)
3. **Run Overnight**: Process all tickers in background
4. **Resume Support**: Use `--start-from` if interrupted
5. **Monitor Progress**: Script shows progress for each ticker

### Example: Process S&P 500 Overnight

```cmd
REM This will process all 500 tickers, 5 filings each
python scripts/index_documents_for_rag.py --database data/financial.db --type sec --universe sp500 --fetch-from-sec --limit 5
```

**Expected Result**: ~2,500-5,000 filings indexed, producing ~125,000-500,000 document chunks in vector DB

## Troubleshooting

### No Filings Found

If you see "No filings found in database":
1. Use `--fetch-from-sec` flag to download from SEC API
2. Specify `--ticker` to fetch for a specific company
3. Make sure you have internet connection for SEC API access

### Vector Store Not Available

If you see "Vector store not available":
```bash
pip install chromadb sentence-transformers
```

### Download Errors

If filing downloads fail:
- Check your internet connection
- Verify SEC API is accessible
- Ensure your User-Agent is set (configured in settings)

## Verification

After indexing, verify data is in vector DB:

**Windows PowerShell/CMD:**
```cmd
REM Quick status check
python check_vector_db.py
```

**Python Code:**
```python
from pathlib import Path
from finanlyzeos_chatbot.rag_retriever import VectorStore

vector_store = VectorStore(Path("data/financial.db"))
if vector_store._available:
    sec_count = vector_store.sec_collection.count()
    uploaded_count = vector_store.uploaded_collection.count()
    print(f"SEC narratives: {sec_count:,} documents")
    print(f"Uploaded documents: {uploaded_count:,} documents")
    print(f"Total: {sec_count + uploaded_count:,} documents")
```

## Next Steps

Once indexed, the vector database will be used automatically by the RAG retriever for:
- Semantic search over SEC filing narratives
- Context retrieval for LLM responses
- Hybrid retrieval (combining dense + sparse search)

