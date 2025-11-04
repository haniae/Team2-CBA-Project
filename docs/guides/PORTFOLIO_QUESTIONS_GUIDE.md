# 📊 Portfolio Questions Guide - What Each Question Returns

## Overview

This guide documents **all portfolio-related questions** the chatbot can handle and **exactly what data each one returns**.

---

## 1. 📋 Portfolio Holdings

### Example Questions:
- "Show my portfolio holdings"
- "What are the holdings for port_abc123?"
- "Show holdings for port_abc123"
- "Use portfolio port_abc123"

### What You Get:

**Response includes:**
- ✅ All tickers in portfolio
- ✅ Portfolio weights (% allocation)
- ✅ Share quantities
- ✅ Current prices
- ✅ Market values
- ✅ Sectors (GICS classification)
- ✅ Fundamental metrics (P/E, dividend yield, ROE, ROIC)
- ✅ Holdings sorted by weight (descending)

**Key fields:**
- `ticker`, `weight`, `shares`, `price`, `market_value`
- `sector`, `pe_ratio`, `dividend_yield`, `roe`, `roic`

---

## 2. 📊 Portfolio Exposure

### Example Questions:
- "What's my portfolio exposure?"
- "Show portfolio sector exposure"
- "Analyze exposure for port_abc123"
- "What's my factor exposure?"

### What You Get:

**Response includes:**
- ✅ **Sector Breakdown**: Weight in each GICS sector
- ✅ **Factor Exposure**: Beta, momentum, value, size, quality
- ✅ **Concentration Metrics**: HHI, top 10 concentration, max weights
- ✅ **Snapshot Date**: When the analysis was calculated

**Key fields:**
- `sector_exposure`: Dictionary of sector → weight
- `factor_exposure`: Beta, momentum, value, size, quality
- `concentration_metrics`: HHI, top_10_concentration, max weights

---

## 3. 📈 Portfolio Summary Statistics

### Example Questions:
- "Show portfolio summary"
- "What's my portfolio stats?"
- "Analyze portfolio port_abc123"

### What You Get:

**Response includes:**
- ✅ **Portfolio Size**: Number of holdings, total value
- ✅ **Valuation Metrics**: Weighted average P/E
- ✅ **Income Metrics**: Weighted average dividend yield
- ✅ **Concentration**: Top 10 concentration ratio
- ✅ **Diversification**: Number of sectors
- ✅ **Sector Breakdown**: Full sector allocation

**Key fields:**
- `num_holdings`, `total_market_value`
- `weighted_avg_pe`, `weighted_avg_dividend_yield`
- `top_10_concentration`, `num_sectors`, `sector_breakdown`

---

## 4. 🎯 Portfolio Optimization

### Example Questions:
- "Optimize my portfolio"
- "Rebalance portfolio port_abc123"
- "Optimize for maximum Sharpe ratio"

### What You Get:

**Response includes:**
- ✅ **Current vs. Optimized Weights**: Before/after comparison
- ✅ **Expected Performance**: Expected return, variance, Sharpe ratio
- ✅ **Rebalancing Cost**: Portfolio turnover required
- ✅ **Constraint Status**: Whether policy constraints are satisfied
- ✅ **Trade Recommendations**: What to buy/sell

**Key fields:**
- `current_holdings`, `optimized_holdings`
- `expected_return`, `portfolio_variance`, `sharpe_ratio`, `turnover`
- `constraints_satisfied`, `violations`

---

## 5. 📉 Performance Attribution

### Example Questions:
- "Show portfolio attribution"
- "What's driving my portfolio performance?"
- "Attribution analysis for port_abc123"

### What You Get:

**Response includes:**
- ✅ **Active Return Decomposition**: Total, allocation, selection, interaction
- ✅ **Top Contributors**: Best performing positions and their contribution
- ✅ **Top Detractors**: Worst performing positions and their impact
- ✅ **Sector-Level Analysis**: Which sectors drove performance
- ✅ **Time Period**: Analysis period specified

**Key fields:**
- `total_active_return`, `allocation_effect`, `selection_effect`, `interaction_effect`
- `top_contributors`, `top_detractors` (lists with ticker, contribution, return)

---

## 6. 🔮 Scenario Analysis / Stress Testing

### Example Questions:
- "What if the market crashes 20%?"
- "Stress test my portfolio"
- "What happens if tech sector drops 30%?"
- "Monte Carlo simulation for port_abc123"

### What You Get:

**Response includes:**
- ✅ **Portfolio Impact**: Total value change, percentage change
- ✅ **Position-Level Impacts**: How each holding would be affected
- ✅ **Sector-Level Impacts**: Sector-by-sector breakdown
- ✅ **Risk Metrics**: VaR, CVaR, max drawdown
- ✅ **Beta Analysis**: How beta affects individual positions

**Key fields:**
- `baseline_value`, `scenario_value`, `value_change`, `percent_change`
- `position_impacts`, `sector_impacts`
- `risk_metrics`: var_95, cvar_95, max_drawdown

---

## 7. ⚠️ Conditional Value at Risk (CVaR)

### Example Questions:
- "What's my portfolio CVaR?"
- "Calculate CVaR for port_abc123"
- "Portfolio expected shortfall"

### What You Get:

**Response includes:**
- ✅ **Portfolio-Level CVaR**: Expected loss in worst-case scenarios
- ✅ **VaR**: Value at Risk (less conservative than CVaR)
- ✅ **Expected Loss**: Dollar amount of expected loss
- ✅ **Position Contributions**: Which holdings drive tail risk
- ✅ **Confidence Level**: Specified confidence level (typically 95%)

**Key fields:**
- `confidence_level`, `var`, `cvar`, `portfolio_value`, `expected_loss`
- `position_cvar`: List showing CVaR contribution by position

---

## 8. 🌱 ESG Exposure

### Example Questions:
- "What's my portfolio ESG score?"
- "Show ESG exposure for port_abc123"
- "Analyze portfolio ESG"

### What You Get:

**Response includes:**
- ✅ **Overall ESG Score**: Weighted average across portfolio
- ✅ **Component Scores**: Environmental, Social, Governance separately
- ✅ **Holding-Level ESG**: ESG score for each position
- ✅ **Sector ESG**: Average ESG by sector
- ✅ **Controversy Level**: Portfolio controversy rating

**Key fields:**
- `overall_esg_score`, `environmental_score`, `social_score`, `governance_score`
- `holdings_esg`, `sector_esg`, `controversy_level`

---

## 9. 💰 Tax Analysis

### Example Questions:
- "Tax analysis for my portfolio"
- "What's my tax-adjusted return?"
- "Tax-aware analysis for port_abc123"

### What You Get:

**Response includes:**
- ✅ **Tax Liability**: Estimated taxes if positions were sold
- ✅ **Tax-Adjusted Returns**: Returns after accounting for taxes
- ✅ **Gain/Loss Breakdown**: Unrealized gains and losses by position
- ✅ **Holding Periods**: Short-term vs. long-term classification
- ✅ **Wash Sale Detection**: Potential wash sale issues

**Key fields:**
- `total_unrealized_gains`, `estimated_tax_liability`, `tax_adjusted_return`
- `holdings_tax_status`: Cost basis, gains, tax rates by position
- `wash_sale_warnings`

---

## 10. 📊 Tracking Error

### Example Questions:
- "What's my portfolio tracking error?"
- "Active risk for port_abc123"
- "Tracking error vs S&P 500"

### What You Get:

**Response includes:**
- ✅ **Tracking Error**: Annualized active risk vs. benchmark
- ✅ **Information Ratio**: Risk-adjusted active return metric
- ✅ **Correlation & Beta**: Relationship with benchmark
- ✅ **Active Weights**: Overweight/underweight vs. benchmark
- ✅ **Factor Decomposition**: What drives the tracking error

**Key fields:**
- `benchmark`, `tracking_error`, `active_return`, `information_ratio`
- `correlation`, `beta`, `active_weights`, `factor_contributions`

---

## 11. 🎲 Diversification Analysis

### Example Questions:
- "How diversified is my portfolio?"
- "Diversification score for port_abc123"
- "Show portfolio concentration"

### What You Get:

**Response includes:**
- ✅ **Diversification Ratio**: Measure of diversification benefit
- ✅ **Effective Holdings**: Equivalent number of equal-weighted positions
- ✅ **Concentration Metrics**: HHI, top 10, max weights
- ✅ **Risk Contribution**: Which positions drive portfolio risk
- ✅ **Recommendations**: Suggestions to improve diversification

**Key fields:**
- `diversification_ratio`, `effective_number_of_holdings`
- `concentration_metrics`: HHI, top_10_concentration, max weights
- `risk_contribution`, `recommendations`

---

## 12. 📝 Export Reports

### Example Questions:
- "Export portfolio as PowerPoint"
- "Generate PDF report for port_abc123"
- "Export to Excel"

### What You Get:

**PowerPoint Export (.pptx):**
- 12-slide professional presentation
- Portfolio summary, holdings, exposure charts
- Performance attribution, risk metrics
- Recommendations slide

**PDF Export (.pdf):**
- Multi-page PDF report
- Executive summary, holdings table
- Charts, risk analysis

**Excel Export (.xlsx):**
- Multi-tab workbook
- Holdings sheet, exposure breakdowns
- Performance attribution table, risk metrics

---

## 📋 Quick Reference Table

| Question Type | Example Query | Key Metrics Returned |
|--------------|---------------|---------------------|
| **Holdings** | "Show holdings" | Tickers, weights, shares, prices, fundamentals |
| **Exposure** | "What's my exposure?" | Sector weights, factor exposure, concentration |
| **Summary** | "Portfolio summary" | Total value, weighted P/E, dividend yield, concentration |
| **Optimize** | "Optimize portfolio" | Recommended weights, expected return, Sharpe ratio |
| **Attribution** | "Performance attribution" | Active return, allocation/selection effects, top contributors |
| **Scenario** | "What if market crashes?" | Value change, position impacts, risk metrics |
| **CVaR** | "Calculate CVaR" | Expected shortfall, VaR, position contributions |
| **ESG** | "ESG score" | Overall ESG, E/S/G components, controversy level |
| **Tax** | "Tax analysis" | Tax liability, tax-adjusted returns, gains/losses |
| **Tracking Error** | "Tracking error" | Active risk, information ratio, correlation |
| **Diversification** | "How diversified?" | Diversification ratio, HHI, recommendations |
| **Export** | "Export to PDF" | PowerPoint/PDF/Excel files |

---

## 💡 Tips for Using Portfolio Questions

1. **Start with Holdings**: Always begin by viewing holdings to see what you're working with
2. **Check Exposure**: Understand your sector and factor exposures before optimizing
3. **Run Scenarios**: Test how your portfolio would perform in different market conditions
4. **Monitor Attribution**: Regularly check what's driving your performance
5. **Use CVaR for Risk**: CVaR gives better tail risk insight than standard deviation
6. **Export for Reports**: Use export functions to create reports for stakeholders

