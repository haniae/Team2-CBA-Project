# Fetcher Scripts Usage Guide

## Overview

All 5 fetcher scripts have been created and integrated into the indexing pipeline:

1. ✅ **Earnings Transcripts** - `scripts/fetchers/fetch_earnings_transcripts.py`
2. ✅ **Financial News** - `scripts/fetchers/fetch_financial_news.py`
3. ✅ **Analyst Reports** - `scripts/fetchers/fetch_analyst_reports.py`
4. ✅ **Press Releases** - `scripts/fetchers/fetch_press_releases.py`
5. ✅ **Industry Research** - `scripts/fetchers/fetch_industry_research.py`

---

## Quick Start

### Using the Main Indexing Script

```bash
# Index all document types for a ticker
python scripts/index_documents_for_rag.py --database data/financial.db --type all --ticker AAPL

# Index specific types
python scripts/index_documents_for_rag.py --database data/financial.db --type earnings --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type news --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type analyst --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type press --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type industry --sector Technology
```

### Using Individual Fetcher Scripts

```bash
# Earnings transcripts
python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker AAPL

# Financial news
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --limit 20

# Analyst reports
python scripts/fetchers/fetch_analyst_reports.py --database data/financial.db --ticker AAPL --limit 10

# Press releases
python scripts/fetchers/fetch_press_releases.py --database data/financial.db --ticker AAPL --limit 20

# Industry research
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology --limit 10
```

---

## Detailed Usage

### 1. Earnings Transcripts

**Sources**: Seeking Alpha, Company IR pages

```bash
# Basic usage
python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker AAPL

# Specify source
python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker AAPL --source seeking_alpha
python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker AAPL --source company_ir
python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker AAPL --source all
```

**What it does**:
- Fetches earnings call transcripts from Seeking Alpha or company IR pages
- Extracts Q&A sections and management commentary
- Chunks and indexes into `earnings_transcripts` collection

**Requirements**:
- `requests`, `beautifulsoup4`

---

### 2. Financial News

**Sources**: Yahoo Finance, NewsAPI

```bash
# Basic usage (Yahoo Finance)
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL

# Specify source
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --source yahoo
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --source newsapi
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --source all

# Limit articles
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --limit 20

# Days back
python scripts/fetchers/fetch_financial_news.py --database data/financial.db --ticker AAPL --days-back 7
```

**What it does**:
- Fetches recent news articles from Yahoo Finance or NewsAPI
- Extracts article text and metadata
- Chunks and indexes into `financial_news` collection

**Requirements**:
- `yfinance` (for Yahoo Finance)
- `requests`, `beautifulsoup4`
- `NEWSAPI_KEY` environment variable (optional, for NewsAPI)

---

### 3. Analyst Reports

**Sources**: Seeking Alpha

```bash
# Basic usage
python scripts/fetchers/fetch_analyst_reports.py --database data/financial.db --ticker AAPL

# Limit reports
python scripts/fetchers/fetch_analyst_reports.py --database data/financial.db --ticker AAPL --limit 20
```

**What it does**:
- Fetches analyst research articles from Seeking Alpha
- Extracts ratings, price targets, and analysis
- Chunks and indexes into `analyst_reports` collection

**Requirements**:
- `requests`, `beautifulsoup4`

---

### 4. Press Releases

**Sources**: Company IR pages

```bash
# Basic usage
python scripts/fetchers/fetch_press_releases.py --database data/financial.db --ticker AAPL

# Limit releases
python scripts/fetchers/fetch_press_releases.py --database data/financial.db --ticker AAPL --limit 30
```

**What it does**:
- Fetches press releases from company investor relations pages
- Extracts announcements, product launches, strategic updates
- Chunks and indexes into `press_releases` collection

**Requirements**:
- `requests`, `beautifulsoup4`

---

### 5. Industry Research

**Sources**: SSRN, Government sources

```bash
# Basic usage
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology

# Specify source
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology --source ssrn
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology --source government
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology --source all

# Limit reports
python scripts/fetchers/fetch_industry_research.py --database data/financial.db --sector Technology --limit 20
```

**What it does**:
- Fetches industry research papers from SSRN or government sources
- Extracts sector analysis and market trends
- Chunks and indexes into `industry_research` collection

**Requirements**:
- `requests`, `beautifulsoup4`

---

## Integration with Main Indexing Script

All fetchers are integrated into `scripts/index_documents_for_rag.py`:

```bash
# Index all types for a ticker
python scripts/index_documents_for_rag.py --database data/financial.db --type all --ticker AAPL

# Index specific types
python scripts/index_documents_for_rag.py --database data/financial.db --type earnings --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type news --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type analyst --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type press --ticker AAPL
python scripts/index_documents_for_rag.py --database data/financial.db --type industry --sector Technology
```

---

## Batch Processing

### Process Multiple Tickers

```bash
# Process earnings transcripts for multiple tickers
for ticker in AAPL MSFT GOOGL AMZN; do
    python scripts/fetchers/fetch_earnings_transcripts.py --database data/financial.db --ticker $ticker
done
```

### Process All Types for Multiple Tickers

```bash
# Process all document types for multiple tickers
for ticker in AAPL MSFT GOOGL; do
    python scripts/index_documents_for_rag.py --database data/financial.db --type all --ticker $ticker
done
```

---

## Dependencies

Install required packages:

```bash
pip install requests beautifulsoup4 yfinance
```

Optional (for NewsAPI):
```bash
# Set environment variable
export NEWSAPI_KEY=your_api_key_here
```

---

## Notes

1. **Rate Limiting**: All fetchers include rate limiting to avoid overwhelming sources
2. **Error Handling**: Fetchers gracefully handle missing data or API failures
3. **Chunking**: All documents are automatically chunked (1500 chars, 200 overlap)
4. **Metadata**: Rich metadata is preserved for filtering and citation

---

## Troubleshooting

### "Module not found" errors
- Make sure you're running from the project root directory
- Check that `scripts/fetchers/` directory exists

### "No data found" errors
- Some sources may require API keys (NewsAPI)
- Some companies may not have public transcripts/releases
- Try different tickers or sources

### Rate limiting errors
- Fetchers include delays, but some sources may still rate limit
- Reduce `--limit` parameter
- Add longer delays if needed

---

## Next Steps

1. **Test with a single ticker**: Start with one ticker to verify everything works
2. **Batch process**: Process multiple tickers once verified
3. **Monitor storage**: Check ChromaDB size as you index more documents
4. **Update regularly**: Re-run fetchers periodically to get latest data

---

## Summary

✅ **5 Fetcher Scripts Created**
✅ **All Integrated into Main Indexing Script**
✅ **Shared Chunking Utility**
✅ **Comprehensive Error Handling**
✅ **Rich Metadata Support**

All fetchers are ready to use! Start with earnings transcripts for highest value.

