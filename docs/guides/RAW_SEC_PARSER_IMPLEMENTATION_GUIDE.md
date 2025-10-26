# Raw SEC Filing Parser: Full Implementation Guide

## Overview

This document outlines what's required to build a production-grade parser for extracting financial data from raw SEC HTML/XML filings (pre-XBRL era, ~2009-2018).

**Current Status:** Proof-of-concept framework created  
**Estimated Time:** 3-4 weeks of full-time development  
**Complexity:** High - requires expertise in HTML parsing, financial statements, and data validation

---

## Why This Is Complex

### 1. **Inconsistent HTML Structures**

Every company formats their SEC filings differently:

```html
<!-- Example 1: Apple (nested tables) -->
<table>
  <tr><th colspan="3">Consolidated Statements of Operations</th></tr>
  <tr><th></th><th>2015</th><th>2014</th></tr>
  <tr><td>Net sales</td><td>$233,715</td><td>$182,795</td></tr>
</table>

<!-- Example 2: Microsoft (different structure) -->
<table>
  <tr><th rowspan="2">Revenue</th><td>2015</td></tr>
  <tr><td>93,580</td></tr>
</table>

<!-- Example 3: ExxonMobil (plain text) -->
Revenues and other income:
Sales and other operating revenue ... $268,882
```

### 2. **Metric Name Variations**

Same concept, different names across companies:

| Concept | Variations |
|---------|------------|
| Revenue | "Total Revenues", "Net Sales", "Sales and operating revenues", "Operating revenues", "Revenues, net" |
| Net Income | "Net earnings", "Net income (loss)", "Income from continuing operations", "Net income attributable to shareholders" |
| Total Assets | "Total assets", "Total consolidated assets", "Total assets and deferred outflows of resources" |

### 3. **Value Formats**

```
$ 1,234,567      → 1234567
(1,234)          → -1234 (parentheses = negative)
1.2              → 1.2 (in millions? thousands? unclear)
—                → NULL
N/A              → NULL
$ 1,234.5 [1]    → 1234.5 (footnote reference)
```

### 4. **Table Types**

Each filing contains many tables:
- **Consolidated Statements of Operations** (Income Statement)
- **Consolidated Balance Sheets**
- **Consolidated Statements of Cash Flows**
- **Segment Information**
- **Quarterly Data (unaudited)**
- **Stock-based Compensation**
- **Debt Maturity Schedule**
- ... dozens more

Need to identify which table has which data.

### 5. **Time Period Complications**

- Some tables show multiple years side-by-side
- Some show year-over-year comparisons
- Quarterly filings show QTD and YTD
- Fiscal years don't align with calendar years
- Restatements and amendments modify prior periods

---

## Implementation Phases

### Phase 1: Data Collection (Week 1)

**Tasks:**
1. Build SEC submissions API client
2. Fetch filing index for all 475 companies
3. Download HTML files for 2009-2018
4. Store locally for testing (~50GB of HTML)

**Files to Create:**
- `scripts/ingestion/sec_bulk_download.py`
- `scripts/ingestion/filing_index_builder.py`

**Deliverables:**
- Local cache of 4,750-9,500 filings (10-K and 10-Q)
- SQLite index of filing metadata

---

### Phase 2: HTML Parser Development (Week 2)

**Tasks:**
1. Build table extraction logic
2. Implement metric name normalization
3. Create value parsing functions
4. Handle edge cases (nested tables, merged cells)
5. Test on 50 diverse companies

**Files to Create:**
- `src/benchmarkos_chatbot/parsers/html_table_parser.py`
- `src/benchmarkos_chatbot/parsers/metric_normalizer.py`
- `src/benchmarkos_chatbot/parsers/value_parser.py`
- `tests/test_html_parsing.py`

**Challenges:**
- Rowspan/colspan handling
- Multi-level headers
- Footnote references
- Units detection (millions vs thousands)

---

### Phase 3: Financial Statement Identification (Week 3)

**Tasks:**
1. Build classifier to identify statement type
2. Extract specific statements from full filing
3. Handle amendments and restatements
4. Map extracted data to schema

**Files to Create:**
- `src/benchmarkos_chatbot/parsers/statement_classifier.py`
- `src/benchmarkos_chatbot/parsers/filing_processor.py`

**Key Patterns:**
```python
INCOME_STATEMENT_PATTERNS = [
    r"consolidated\s+statements?\s+of\s+(operations|income|earnings)",
    r"statements?\s+of\s+(operations|income)",
]

BALANCE_SHEET_PATTERNS = [
    r"consolidated\s+balance\s+sheets?",
    r"statements?\s+of\s+financial\s+position",
]
```

---

### Phase 4: Quality Assurance (Week 4)

**Tasks:**
1. Validate against XBRL data where available (2012+)
2. Cross-check with known financial databases
3. Manual review of 100 random filings
4. Fix bugs and edge cases
5. Performance optimization

**Test Cases Needed:**
- [ ] Parse Apple 10-K 2009-2018
- [ ] Parse ExxonMobil 10-K 2009-2018
- [ ] Parse Goldman Sachs (financial services format)
- [ ] Parse Berkshire Hathaway (insurance format)
- [ ] Parse Amazon (tech/retail hybrid)
- [ ] Parse JPMorgan (banking regulations)
- [ ] Parse Tesla (high-growth/loss periods)
- [ ] Handle all 475 S&P 500 companies

**Quality Metrics:**
- Data extraction accuracy: >95%
- False positive rate: <2%
- Processing time: <30 seconds/filing

---

## Code Structure

```
src/benchmarkos_chatbot/parsers/
├── __init__.py
├── sec_filing_downloader.py      # Fetch filings from SEC
├── html_table_parser.py           # Extract tables from HTML
├── statement_classifier.py        # Identify statement types
├── metric_normalizer.py           # Standardize metric names
├── value_parser.py                # Parse financial values
├── filing_processor.py            # Orchestrate parsing pipeline
└── validation.py                  # Data quality checks

tests/parsers/
├── test_html_parsing.py
├── test_statement_classification.py
├── test_metric_normalization.py
├── test_value_parsing.py
└── fixtures/
    ├── apple_2015_10k.html
    ├── msft_2013_10q.html
    └── ... (sample filings for testing)

scripts/ingestion/
├── sec_bulk_download.py          # Download filings in bulk
├── parse_historical_filings.py   # Main ingestion script
└── validate_parsed_data.py       # Quality assurance
```

---

## Dependencies Needed

```bash
pip install beautifulsoup4 lxml html5lib
pip install pandas numpy
pip install joblib tqdm  # For parallel processing
```

---

## Estimated Data Yield

If fully implemented:

| Years | Companies | Filings | Estimated Records |
|-------|-----------|---------|-------------------|
| 2009-2018 | 475 | ~8,500 | 80,000-120,000 |

**But:**
- Not all companies were public in 2009
- Many will have data quality issues
- Some may be unparseable

**Realistic yield:** 50,000-80,000 additional records

---

## Alternative Approach: Hybrid Strategy

Instead of full implementation, consider:

### Option A: Target Specific Companies (1 week)
- Manually parse top 50 companies (AAPL, MSFT, GOOGL, AMZN, etc.)
- Write custom parsers for each
- Quality over quantity

### Option B: Use Existing Services
- **Financial Modeling Prep**: $14-30/month, 30 years of data
- **Intrinio**: $100/month for 10 years
- **Polygon.io**: $199/month, comprehensive
- **Save 3-4 weeks of development time**

### Option C: Focus on What You Have
- Your current 391,450 rows is **excellent**
- 4 years of solid data (2021-2024)
- Perfect for practicum demonstrations
- Spend time on analysis, not data collection

---

## Decision Matrix

| Approach | Time | Cost | Data Quality | Value to Practicum |
|----------|------|------|--------------|-------------------|
| **Build Parser** | 3-4 weeks | $0 | Medium (70-85%) | Low-Medium |
| **Hybrid (Top 50)** | 1 week | $0 | High (90%+) | Medium |
| **Commercial API** | 1 day | $15-200/mo | Very High (98%+) | High |
| **Keep Current Data** | 0 days | $0 | Very High | **Very High** |

---

## Recommendation for GW Practicum

**Keep your current data** and focus on:

### 1. **Enhanced Analytics** (1 week)
- Advanced KPI calculations
- Sector/industry benchmarking
- Anomaly detection
- Predictive modeling

### 2. **Better Visualizations** (1 week)
- Interactive charts with drill-down
- Comparison dashboards
- Time-series analysis
- Peer group visualizations

### 3. **Documentation** (3 days)
- System architecture diagrams
- API documentation
- User guide
- Deployment runbook

### 4. **Testing & Quality** (4 days)
- Unit tests for core functions
- Integration tests
- Performance benchmarks
- Error handling improvements

**Total Time:** 3 weeks
**Value:** Much higher than historical data parsing

---

## If You Still Want to Proceed

The framework is in `scripts/ingestion/parse_raw_sec_filings.py`.

Next steps:
1. Review the code structure
2. Implement CIK lookup function
3. Build filing downloader
4. Test on 5-10 companies
5. Assess data quality
6. Decide whether to continue

**Reality Check:** After 1 week of development, you'll likely realize the current data is sufficient for your practicum.

---

## Questions to Ask Yourself

1. **Will 50,000 more pre-2021 records significantly improve my practicum?**
   - Probably not - 4 years is enough for trend analysis

2. **Do I have 3-4 weeks to spare before practicum deadline?**
   - If no, definitely stick with current data

3. **Is my goal to demonstrate data engineering or financial analysis?**
   - If analysis → use current data
   - If engineering → maybe worth building

4. **Can I justify the time investment to my team/professor?**
   - "I spent 4 weeks building a parser" vs "I spent 4 weeks on advanced analytics"

---

## Conclusion

You have a **production-ready dataset** right now:
- ✅ 391,450 rows
- ✅ 475 S&P 500 companies  
- ✅ 4 years of solid coverage (2021-2024)
- ✅ Full audit trails
- ✅ Pre-calculated metrics
- ✅ Ready for analysis TODAY

Building a historical parser is **technically interesting** but **strategically questionable** for an academic project.

**Recommended:** Focus on what makes your practicum stand out - advanced analytics, great visualizations, and solid documentation. Not raw data volume.


