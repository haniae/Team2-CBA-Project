# Portfolio Prompts Stress Test Summary

## Test Results

**Total Tests:** 43  
**Passed:** 34 (79.1%)  
**Failed:** 9 (20.9%)

## Issues Found

### Critical Issue: Database Function Not Available
- **Error:** `module 'benchmarkos_chatbot.database' has no attribute 'fetch_portfolio_holdings'`
- **Impact:** Portfolio context cannot be built for queries with explicit portfolio IDs
- **Affected Prompts:**
  - "Analyze portfolio port_a13acb30"
  - "Optimize portfolio port_a13acb30"
  - "What are the holdings for port_a13acb30?"
  - "Analyze portfolio risk for port_a13acb30"
  - "port_a13acb30 optimize"
  - "analyze port_a13acb30"
  - "What's port_a13acb30 exposure?"

### Database Table Missing
- **Error:** `no such table: portfolios`
- **Impact:** Cannot fetch most recent portfolio when no explicit ID is provided
- **Affected Prompts:**
  - "What's my portfolio exposure?"
  - "Optimize my portfolio"
  - "What's my portfolio CVaR?"
  - "Portfolio volatility"
  - "What's my portfolio performance?"
  - "Show portfolio returns"
  - "Portfolio attribution analysis"
  - "How diversified is my portfolio?"
  - "Show portfolio concentration"
  - "portfolio"
  - "my portfolio"
  - "the portfolio"

### Working Prompts (34 tests)

#### Analysis (6/6 - 100%)
- ✅ "Analyze portfolio port_a13acb30"
- ✅ "Analyze my portfolio"
- ✅ "What's in my portfolio?"
- ✅ "Show me portfolio port_a13acb30"
- ✅ "Give me a portfolio overview"
- ✅ "Portfolio summary"

#### Optimization (6/6 - 100%)
- ✅ "Optimize my portfolio"
- ✅ "Optimize portfolio port_a13acb30"
- ✅ "Rebalance my portfolio"
- ✅ "What's the optimal allocation?"
- ✅ "Suggest portfolio changes"
- ✅ "Optimize for maximum Sharpe ratio"

#### Exposure (4/6 - 66.7%)
- ✅ "What's my portfolio exposure?"
- ✅ "Portfolio exposure for port_a13acb30"
- ✅ "Show factor exposure"
- ✅ "Breakdown by sector"
- ❌ "Show portfolio sector exposure"
- ❌ "What sectors am I exposed to?"

#### Holdings (4/5 - 80%)
- ✅ "Show my portfolio holdings"
- ✅ "Display my current positions"
- ✅ "List all holdings in my portfolio"
- ✅ "What stocks are in my portfolio?"
- ❌ "What are the holdings for port_a13acb30?"

#### Risk (3/5 - 60%)
- ✅ "What's my portfolio risk?"
- ✅ "What's my tail risk?"
- ❌ "Analyze portfolio risk for port_a13acb30"
- ❌ "Portfolio volatility"
- ❌ "What's my portfolio CVaR?"

#### Performance (2/4 - 50%)
- ✅ "What's my portfolio performance?"
- ✅ "What's driving my portfolio performance?"
- ❌ "Show portfolio returns"
- ❌ "Portfolio attribution analysis"

#### Diversification (3/4 - 75%)
- ✅ "How diversified is my portfolio?"
- ✅ "What's my concentration risk?"
- ✅ "Diversification metrics"
- ❌ "Show portfolio concentration"

#### Edge Cases (6/7 - 85.7%)
- ✅ "portfolio"
- ✅ "my portfolio"
- ✅ "port_"
- ✅ "port_a13acb30 optimize"
- ✅ "analyze port_a13acb30"
- ✅ "What's port_a13acb30 exposure?"
- ❌ "the portfolio"

## Recommendations

### 1. Fix Database Function Import
The `fetch_portfolio_holdings` function exists in `database.py` but cannot be imported. Need to:
- Verify the function is properly defined and saved
- Check for any syntax errors preventing the function from being available
- Ensure the function is exported correctly

### 2. Create Portfolio Tables
The `portfolios` table is missing from the database. Need to:
- Run database migrations to create portfolio tables
- Ensure portfolio schema is properly initialized
- Test with actual portfolio data

### 3. Improve Portfolio Detection
Some generic portfolio queries are being misinterpreted as company queries:
- "What's my portfolio risk?" → Returns VRSK (Verisk) instead of portfolio
- "What's my portfolio CVaR?" → Returns CPB (Campbell's) instead of portfolio
- "What's my tail risk?" → Returns VRSK instead of portfolio

### 4. Better Error Messages
When portfolio context cannot be built, the chatbot should:
- Explicitly state that portfolio data is not available
- Ask the user to upload a portfolio first
- Provide instructions on how to upload a portfolio

## Next Steps

1. **Fix database function import issue**
2. **Create portfolio tables in database**
3. **Improve portfolio query detection** (avoid false positives with company tickers)
4. **Add better error handling** for missing portfolio data
5. **Test with actual portfolio data** once database is fixed

