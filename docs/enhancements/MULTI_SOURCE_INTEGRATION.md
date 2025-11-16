# Multi-Source Data Integration

## Overview

The chatbot now fetches financial data from **multiple free sources** to provide comprehensive, non-generic answers:

1. **SEC EDGAR** - Official 10-K/10-Q filings (already integrated)
2. **Yahoo Finance** - Real-time data, analyst ratings, news (NEW ✅)
3. **FRED** - Federal Reserve economic data (NEW ✅)
4. **IMF** - Macroeconomic indicators (NEW ✅)

## Why Multiple Sources?

### Before (Generic)
```
User: "What is Apple's P/E ratio?"

Response:
Based on SEC filings, Apple's fundamentals show:
- Revenue: $296.1B
- Net Income: $84.5B
...

📊 Sources:
- [10-K FY2025](sec.gov/...)
```

**Problem**: No P/E ratio (not in SEC filings), no analyst views, no market sentiment.

### After (Comprehensive)
```
User: "What is Apple's P/E ratio?"

Response:
Apple currently trades at a **P/E ratio of 28.5x**, which is above the tech 
sector average of 24.2x but justified by strong fundamentals.

**Valuation Context:**
- **Current Price**: $175.32 (Yahoo Finance, real-time)
- **Target Price (Analysts)**: $195.50 (11.5% upside)
- **Analyst Rating**: BUY (27 analysts)

The elevated P/E reflects:
1. Strong revenue growth (7.5% YoY per SEC 10-K)
2. Market-leading margins (32.1% EBITDA margin)
3. Growing Services segment (high margins, recurring revenue)

**Economic Context (FRED data):**
- Fed Funds Rate: 5.33% - Higher rates pressure valuations
- 10-Year Treasury: 4.25% - Tech stocks remain attractive vs. bonds

📊 Sources:
- [Yahoo Finance - AAPL](https://finance.yahoo.com/quote/AAPL)
- [Apple 10-K FY2025](https://www.sec.gov/...)
- [FRED - Federal Funds Rate](https://fred.stlouisfed.org/series/FEDFUNDS)
```

**Improvement**: Complete answer with valuation, analyst views, economic context, multiple sources!

## Data Sources Breakdown

### 1. Yahoo Finance (`yfinance`)

**What it provides:**
- **Real-time prices** and market data
- **Valuation metrics**: P/E, P/B, PEG, Price/Sales
- **Profitability metrics**: Margins, ROE, ROA
- **Growth metrics**: Revenue growth, earnings growth
- **Analyst data**: 
  - Recommendations (Buy/Sell/Hold)
  - Number of analysts covering the stock
  - Target prices (mean, high, low)
  - Implied upside/downside
- **Recent news**: Latest 5 news articles with links
- **Historical performance**: YTD return, 52-week high/low
- **Dividend information**: Yield, payout ratio, ex-dividend date
- **Company info**: Sector, industry, employees, business summary

**Example data:**
```python
{
    'current_price': 175.32,
    'pe_ratio': 28.45,
    'target_mean_price': 195.50,
    'recommendation_key': 'buy',
    'number_of_analyst_opinions': 27,
    'ytd_return': 45.2,
    'profit_margin': 0.285,
    'news': [
        {'title': 'Apple unveils new AI features', 'publisher': 'Bloomberg'},
        ...
    ]
}
```

**Source URL**: `https://finance.yahoo.com/quote/{TICKER}`

### 2. FRED (Federal Reserve Economic Data)

**What it provides:**
- **GDP** - Gross Domestic Product
- **Unemployment Rate** - Labor market health
- **CPI** - Consumer Price Index (inflation)
- **Federal Funds Rate** - Interest rate policy
- **10-Year Treasury Yield** - Risk-free rate
- **USD/EUR Exchange Rate** - Currency markets
- **VIX** - Market volatility index

**Setup:**
1. Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
2. Set environment variable: `FRED_API_KEY=your_key_here`

**Example data:**
```python
{
    'GDP': {'value': 27890.5, 'units': 'Billions of Dollars', 'date': '2025-Q3'},
    'UNRATE': {'value': 3.9, 'units': 'Percent', 'date': '2025-10'},
    'FEDFUNDS': {'value': 5.33, 'units': 'Percent', 'date': '2025-10'},
}
```

**Source URL**: `https://fred.stlouisfed.org/series/{SERIES_ID}`

### 3. IMF (International Monetary Fund)

**What it provides:**
- **Sector benchmarks** (already integrated via `imf_proxy.py`)
- **Country-level economic indicators**
- **Global economic outlook data**

**Example use cases:**
- Sector-average profit margins
- Country GDP growth rates
- Global trade indicators

**Source URL**: `https://www.imf.org/en/Data`

### 4. SEC EDGAR (Already Integrated)

**What it provides:**
- Official financial statements
- Revenue, net income, cash flow
- Balance sheet items
- Historical filings (10 years)
- Filing metadata (form type, fiscal year, period)

**Source URLs**: Direct links to SEC EDGAR viewer

## Installation

### Install Required Packages

```bash
pip install yfinance fredapi pandas-datareader
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### Configure API Keys (Optional)

**FRED API Key** (recommended for economic data):
1. Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
2. Add to `.env` file:
```bash
FRED_API_KEY=your_fred_api_key_here
```

**No API key needed for:**
- Yahoo Finance (free, no limits for reasonable use)
- SEC EDGAR (free, rate-limited to 10 requests/second)
- IMF (free public API)

## How It Works

### 1. Context Builder Integration

When a user asks a question, the `context_builder.py`:
1. **Fetches SEC data** from local database (as before)
2. **NEW**: Fetches Yahoo Finance data via `yfinance`
3. **NEW**: Fetches FRED economic data (if API key available)
4. **NEW**: Optionally fetches IMF data
5. **Combines all** into comprehensive context for LLM

### 2. Multi-Source Aggregator

The `multi_source_aggregator.py` module:
- Fetches data from each source in parallel
- Handles errors gracefully (missing data, API failures)
- Formats data in natural language for LLM
- Provides clickable source URLs in markdown format

### 3. LLM Integration

The LLM receives:
```
╔═══════════════════════════════════════════════════════════════╗
║           COMPREHENSIVE FINANCIAL DATA CONTEXT                 ║
╚═══════════════════════════════════════════════════════════════╝

📋 DATA SOURCES:
SEC EDGAR, Yahoo Finance, FRED, IMF - all with clickable links

[SEC Data Section]
Apple Inc. (AAPL) - FY2025
Revenue: $296.1B
Net Income: $84.5B
...

[Yahoo Finance Section]
Current Price: $175.32
P/E Ratio: 28.45
Analyst Rating: BUY (27 analysts)
Target Price: $195.50 (+11.5% upside)
News: "Apple unveils new AI features" (Bloomberg)
...

[FRED Economic Section]
Federal Funds Rate: 5.33%
10-Year Treasury: 4.25%
GDP Growth: 2.5%
...

📊 SOURCES:
  • [10-K FY2025](https://www.sec.gov/...)
  • [Yahoo Finance - AAPL](https://finance.yahoo.com/quote/AAPL)
  • [FRED - Federal Funds Rate](https://fred.stlouisfed.org/series/FEDFUNDS)
```

The LLM is instructed to:
✅ Use data from ALL sources
✅ Cite ALL sources in response
✅ Provide comprehensive analysis with multiple perspectives

## Example Queries & Responses

### Query 1: "What is Tesla's P/E ratio?"

**Data Sources Used:**
1. Yahoo Finance → Current P/E ratio, analyst targets
2. SEC → Historical earnings
3. FRED → Market context (interest rates)

**Response:**
```markdown
Tesla's P/E ratio is currently **52.3x**, significantly above the auto 
industry average of 12.5x but reflecting its positioning as a growth/tech 
company rather than traditional automaker.

**Valuation Analysis:**
- **Current Price**: $245.67 (Yahoo Finance)
- **P/E Ratio**: 52.3x (vs. Ford at 7.2x, GM at 5.8x)
- **PEG Ratio**: 1.8x (factoring in 29% earnings growth)

**Why the Premium?**
1. **Growth Profile**: 29% earnings CAGR vs. <5% for traditional auto
2. **Technology Focus**: AI, autonomy valued like tech companies
3. **Analyst Confidence**: HOLD rating, target $265 (+7.8% upside)

**Economic Context:**
With the Fed Funds Rate at 5.33%, high-growth stocks face valuation 
pressure. Tesla's premium P/E requires sustained high growth to justify.

📊 Sources:
- [Yahoo Finance - TSLA](https://finance.yahoo.com/quote/TSLA)
- [Tesla 10-K FY2024](https://www.sec.gov/...)
- [FRED - Fed Funds Rate](https://fred.stlouisfed.org/series/FEDFUNDS)
```

### Query 2: "Is Microsoft a good investment?"

**Data Sources Used:**
1. Yahoo Finance → Price, ratings, news, valuation
2. SEC → Fundamentals, growth
3. FRED → Interest rate environment

**Response:**
```markdown
Based on current data, Microsoft presents a **compelling investment case** 
with strong fundamentals and positive analyst sentiment.

**Investment Highlights:**
✅ **Strong Buy Rating**: 35 of 40 analysts rate it BUY/STRONG BUY
✅ **Upside Potential**: Trading at $378.50, target $425 (+12.3% upside)
✅ **Reasonable Valuation**: P/E of 32.5x justified by:
   - 15% revenue growth (per SEC 10-K)
   - Expanding Azure cloud margins (48.5% EBITDA margin)
   - High capital efficiency (ROE of 42.1%)

**Key Strengths:**
1. **Cloud Leadership**: Azure growing 27% YoY, duopoly with AWS
2. **AI Positioning**: Early OpenAI partnership, Copilot integration
3. **Profitability**: 48.5% EBITDA margin (industry-leading)
4. **Balance Sheet**: $111B cash, minimal debt

**Risks to Consider:**
- **Economic Sensitivity**: Tech spending exposed to recession risk
- **Fed Policy**: 5.33% rates pressure high-P/E stocks
- **Competition**: Google, Amazon investing heavily in AI

**Recent Catalyst:**
"Microsoft reports Azure beats estimates, AI driving adoption" 
(CNBC, 2 days ago)

📊 Sources:
- [Yahoo Finance - MSFT](https://finance.yahoo.com/quote/MSFT)
- [Microsoft 10-K FY2024](https://www.sec.gov/...)
- [FRED - Fed Funds Rate](https://fred.stlouisfed.org/series/FEDFUNDS)
```

## Source Citation Format

### In Response Body

**Inline citations (natural):**
```markdown
According to the latest 10-K filing, revenue grew 7.5%...
Yahoo Finance shows the stock trading at $175.32 with a P/E of 28.5x...
FRED data indicates the Federal Funds Rate is currently 5.33%...
```

**At End of Response:**
```markdown
📊 Sources:
- [10-K FY2025 Filing](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-25-000123)
- [Yahoo Finance - AAPL](https://finance.yahoo.com/quote/AAPL)
- [FRED - Federal Funds Rate](https://fred.stlouisfed.org/series/FEDFUNDS)
- [FRED - 10-Year Treasury](https://fred.stlouisfed.org/series/DGS10)
```

### Format Requirements

✅ **Always use markdown links**: `[Text](URL)`
✅ **Never show raw URLs**: No `https://...` in body
✅ **Include ALL sources used**: SEC + Yahoo + FRED + IMF
✅ **Descriptive link text**: "10-K FY2025" not "Link"

## Configuration

### Enable/Disable Sources

In your code or environment:

```python
# Enable all sources (default)
context = get_multi_source_context(
    ticker="AAPL",
    include_yahoo=True,     # Real-time data, analysts
    include_fred=True,      # Requires API key
    include_imf=False,      # Optional, less frequently needed
)

# Yahoo only (no API keys needed)
context = get_multi_source_context(
    ticker="AAPL",
    include_yahoo=True,
    include_fred=False,
    include_imf=False,
)
```

### Environment Variables

```bash
# Optional: FRED API key for economic data
FRED_API_KEY=your_key_here

# Optional: Configure fetch timeout
YAHOO_TIMEOUT=10
FRED_TIMEOUT=10
```

## Testing

### Test Multi-Source Fetch

```bash
# Test Yahoo Finance data
python -c "
from finanlyzeos_chatbot.multi_source_aggregator import get_multi_source_context
print(get_multi_source_context('AAPL', include_yahoo=True))
"

# Test with FRED (requires API key)
export FRED_API_KEY=your_key
python -c "
from finanlyzeos_chatbot.multi_source_aggregator import get_multi_source_context
print(get_multi_source_context('AAPL', include_yahoo=True, include_fred=True))
"
```

### Test Full Chatbot

```bash
python -m finanlyzeos_chatbot.cli chat
```

**Try these queries:**
- "What is Apple's P/E ratio?" (Yahoo Finance)
- "What is Microsoft's target price?" (Yahoo analyst data)
- "Is Tesla overvalued?" (Multi-source analysis)
- "How does the Fed rate affect tech stocks?" (FRED + Yahoo)

## Benefits

### 1. Non-Generic Answers
- Real-time market data, not just historical SEC data
- Analyst opinions and price targets
- Recent news and market sentiment

### 2. Comprehensive Analysis
- Company fundamentals (SEC)
- Market valuation (Yahoo)
- Economic context (FRED)
- Sector benchmarks (IMF)

### 3. Institutional-Grade Insights
- Multiple data points cross-referenced
- Diverse perspectives (company, analysts, macro)
- Source attribution for credibility

### 4. Always Up-to-Date
- Yahoo Finance: Real-time quotes
- FRED: Updated economic indicators
- SEC: Latest filings as they're released

## Limitations

1. **Yahoo Finance**: 
   - Rate limits for very high-frequency requests
   - Data quality depends on Yahoo's sources

2. **FRED**:
   - Requires free API key
   - Economic data, not company-specific

3. **IMF**:
   - Broader economic indicators
   - Not real-time

4. **Network Dependency**:
   - Requires internet connection
   - API failures handled gracefully

## Future Enhancements

Potential additions:
- [ ] **Alpha Vantage**: Technical indicators
- [ ] **Finnhub**: Real-time news sentiment
- [ ] **World Bank**: Global economic data
- [ ] **FINRA**: Trading volume, short interest
- [ ] **Twitter/X**: Social sentiment analysis

## Related Files

- `src/finanlyzeos_chatbot/multi_source_aggregator.py` - Multi-source fetcher
- `src/finanlyzeos_chatbot/context_builder.py` - Context integration
- `src/finanlyzeos_chatbot/external_data.py` - Existing Yahoo integration
- `src/finanlyzeos_chatbot/imf_proxy.py` - Existing IMF integration
- `requirements.txt` - Package dependencies

## Support

**API Keys:**
- FRED: https://fred.stlouisfed.org/docs/api/api_key.html (free)

**Issues:**
- Yahoo Finance not working → Check `yfinance` version
- FRED not working → Verify API key in `.env`
- Missing data → Sources may be temporarily unavailable

---

*Last Updated: 2025-10-26*  
*Feature: Multi-Source Data Integration*  
*Status: ✅ Production Ready*

