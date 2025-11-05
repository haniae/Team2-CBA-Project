# 🤖 Natural Language Understanding - User Guide

## Overview

The BenchmarkOS Chatbot now understands a wide variety of natural language queries about financial data. You can ask questions naturally, without worrying about exact syntax or keywords.

---

## 📚 Table of Contents

1. [Basic Question Patterns](#basic-question-patterns)
2. [Spelling Correction](#1-spelling-correction)
3. [Comparative Language](#2-comparative-language)
4. [Trend Direction Language](#3-trend-direction-language)
5. [Contextual Metric Inference](#4-contextual-metric-inference)
6. [Negation Handling](#5-negation-handling)
7. [Multi-Intent Queries](#6-multi-intent-queries)
8. [Fuzzy Quantities & Approximations](#7-fuzzy-quantities--approximations)
9. [Natural Filtering](#8-natural-filtering)
10. [Temporal Relationships](#9-temporal-relationships)
11. [Conditional Statements](#10-conditional-statements)
12. [Sentiment Detection](#11-sentiment-detection)
13. [Company Groups](#12-company-groups)
14. [Abbreviations & Acronyms](#13-abbreviations--acronyms)
15. [Question Chaining](#14-question-chaining)
16. [Performance](#performance)
17. [Tips for Best Results](#tips-for-best-results)

---

## Basic Question Patterns

The chatbot recognizes various question patterns and provides conversational responses.

### Examples:
```
✅ "What's Apple's revenue?"
✅ "How's Microsoft doing?"
✅ "Tell me about Tesla's performance"
✅ "Can you show me Amazon's profit margins?"
✅ "I'd like to know Google's market cap"
✅ "Which company has higher revenue?"
✅ "What are the best tech stocks?"
```

---

## 1. Spelling Correction

**Feature:** Automatically corrects misspellings in company names, tickers, and financial metrics.

### What It Handles:

#### Company Names & Tickers
```
✅ "What's Appel's revenue?"              → Apple
✅ "Show me Mikrosft earnings"            → Microsoft
✅ "How's Teslo doing?"                   → Tesla
✅ "GOGL stock price"                     → GOOGL
✅ "Compare Amazn and Googel"             → Amazon and Google
```

#### Financial Metrics
```
✅ "What's the P/E ratioo?"               → P/E ratio
✅ "Show me proffit margins"              → profit margins
✅ "Apple's reveneu last year"            → revenue
✅ "Microsoft maket cap"                  → market cap
✅ "What's the operatig income?"          → operating income
```

#### Techniques Used:
- **Levenshtein Distance** - Edit distance matching
- **Soundex** - Phonetic matching (e.g., "Amazn" sounds like "Amazon")
- **Jaro-Winkler** - Prefix-weighted similarity
- **Context-Aware** - Uses surrounding words for disambiguation
- **Confidence Scoring** - Only corrects when confident

### Tips:
- The system is forgiving with 1-2 character typos
- Ticker symbols are checked against known tickers
- Possessives are handled correctly (e.g., "Apple's" won't be "corrected")

---

## 2. Comparative Language

**Feature:** Understands comparisons between companies across various dimensions.

### What It Handles:

#### Basic Comparisons
```
✅ "Which company is larger?"
✅ "Apple vs Microsoft revenue"
✅ "Compare Tesla and Ford profits"
✅ "Amazon versus Google market cap"
```

#### Superlatives
```
✅ "Which has the best margins?"
✅ "What's the most profitable company?"
✅ "Who has the worst debt ratio?"
✅ "Show me the highest revenue company"
```

#### Relative Comparisons
```
✅ "Apple is twice as profitable as Tesla"
✅ "Microsoft has 3x the revenue of Netflix"
✅ "Amazon's margin is 50% higher than Walmart's"
```

#### Directional Comparisons
```
✅ "Which company is outperforming?"
✅ "Is Apple underperforming Microsoft?"
✅ "Who's beating the market?"
✅ "Companies exceeding expectations"
```

#### Question Comparisons
```
✅ "Does Apple have higher revenue than Microsoft?"
✅ "Is Tesla more profitable than Ford?"
✅ "Which has better margins?"
```

### Comparison Dimensions Detected:
- Revenue, profit, earnings
- Margins (profit margin, operating margin)
- Size, scale, market cap
- Growth rates
- Risk, volatility
- Valuation (P/E ratio, etc.)
- Performance, returns

---

## 3. Trend Direction Language

**Feature:** Understands trend directions and momentum in financial metrics.

### What It Handles:

#### Positive Trends
```
✅ "Companies with growing revenue"
✅ "Which stocks are rising?"
✅ "Show me improving margins"
✅ "Stocks on the upswing"
✅ "Companies gaining momentum"
```

#### Negative Trends
```
✅ "Companies with declining revenue"
✅ "Which stocks are falling?"
✅ "Show me deteriorating margins"
✅ "Stocks losing ground"
✅ "Companies with shrinking profits"
```

#### Stable Trends
```
✅ "Companies with steady revenue"
✅ "Which stocks are flat?"
✅ "Show me stable margins"
✅ "Consistent performers"
```

#### Volatile Trends
```
✅ "Companies with volatile revenue"
✅ "Which stocks are erratic?"
✅ "Show me fluctuating margins"
✅ "Unpredictable stocks"
```

#### Velocity (Speed of Change)
```
✅ "Companies with accelerating growth"
✅ "Which stocks are rapidly rising?"
✅ "Show me decelerating revenue"
✅ "Slowly improving margins"
```

#### Magnitude (Size of Change)
```
✅ "Companies with dramatic growth"
✅ "Which stocks are slightly rising?"
✅ "Show me significant improvements"
✅ "Modestly declining revenue"
```

### Trend Dimensions Detected:
- Revenue, sales, income
- Profit, earnings, margins
- Growth rates
- Stock price, market cap
- Risk, volatility

---

## 4. Contextual Metric Inference

**Feature:** Infers financial metrics from context when not explicitly mentioned.

### What It Handles:

#### Value-Based Inference
```
✅ "Companies over $100M"                 → Revenue > $100M
✅ "Stocks under $50"                     → Price < $50
✅ "Margins above 20%"                    → Profit Margin > 20%
✅ "Companies worth over $1B"             → Market Cap > $1B
```

#### Verb-Based Inference
```
✅ "Companies earning over $1M"           → Earnings > $1M
✅ "Stocks trading under $100"            → Price < $100
✅ "Companies valued over $1B"            → Market Cap > $1B
✅ "Firms grossing $500M+"                → Gross Revenue > $500M
```

#### Context-Based Inference
```
✅ "Show me high-margin companies"        → Profit Margin (high)
✅ "Which are the fastest growing?"       → Growth Rate (high)
✅ "Most expensive stocks"                → Price (high)
✅ "Best performers last quarter"         → Return/Performance (high)
```

### Metrics Inferred:
- Revenue, sales, income
- Earnings, profit, net income
- Margins (profit, operating, gross)
- Price, stock price
- Market cap, valuation
- Growth rate, revenue growth
- Debt, liabilities
- Cash flow, free cash flow
- Return on equity (ROE)
- Return on assets (ROA)
- Dividend yield
- P/E ratio, valuation multiples
- Volume, trading volume
- Volatility, beta

---

## 5. Negation Handling

**Feature:** Understands and processes negation in various forms.

### What It Handles:

#### Basic Negation
```
✅ "Companies not in tech"
✅ "Stocks without debt"
✅ "Show me non-profitable companies"
✅ "Never exceeded $1B revenue"
```

#### Exclusion
```
✅ "All companies except Apple"
✅ "Everyone but Microsoft"
✅ "Tech stocks excluding FAANG"
✅ "Show me everything other than Tesla"
```

#### Threshold Negation
```
✅ "Companies with no more than 10% debt"
✅ "Stocks under $50"
✅ "Revenue below $1B"
✅ "Margins less than 15%"
```

### How It Works:
- Detects negation keywords (not, without, no, never, etc.)
- Determines scope (what's being negated)
- Transforms filters appropriately
- Handles double negatives correctly

---

## 6. Multi-Intent Queries

**Feature:** Handles queries with multiple distinct intents.

### What It Handles:

#### Sequential (THEN)
```
✅ "Show me Apple's revenue then compare it to Microsoft"
✅ "Get Tesla's profit and then analyze the trend"
✅ "Look at Amazon first, then show Google"
```

#### Additive (ALSO/AND)
```
✅ "Show Apple's revenue and also its profit"
✅ "Compare Tesla to Ford and additionally check margins"
✅ "Get Microsoft's data and Amazon's too"
```

#### Alternative (OR)
```
✅ "Show me Apple or Microsoft"
✅ "Compare Tesla versus Ford"
✅ "Either Amazon's revenue or Google's earnings"
```

#### List (COMMA)
```
✅ "Show me Apple, Microsoft, Google"
✅ "Compare revenue, profit, margins"
✅ "Tech stocks: Apple, Tesla, Amazon"
```

### How It Works:
- Detects conjunction patterns (then, and, also, or, comma)
- Splits query into sub-intents
- Classifies each sub-intent separately
- Maintains original order and relationships

---

## 7. Fuzzy Quantities & Approximations

**Feature:** Understands approximate values and ranges.

### What It Handles:

#### Approximations
```
✅ "Revenue around $1B"
✅ "Roughly $500M in profit"
✅ "About 20% margin"
✅ "Approximately $50 per share"
✅ "More or less $100M"
✅ "$1B or so"
```

#### Upper Thresholds
```
✅ "Revenue over $1B"
✅ "More than 20% margin"
✅ "Above $50 per share"
✅ "At least $100M profit"
✅ "No less than 15%"
```

#### Lower Thresholds
```
✅ "Revenue under $1B"
✅ "Less than 20% margin"
✅ "Below $50 per share"
✅ "At most $100M profit"
✅ "No more than 15%"
```

#### Ranges
```
✅ "Revenue between $500M and $1B"
✅ "Margins from 10% to 20%"
✅ "Price ranging $50-$100"
✅ "$1M-$5M in profit"
```

### Tolerance Levels:
- **"Around/about"**: ±10% tolerance
- **"Roughly/approximately"**: ±15% tolerance
- **"More or less"**: ±20% tolerance
- **Ranges**: Explicit bounds

---

## 8. Natural Filtering

**Feature:** Understands natural language filters for company characteristics.

### What It Handles:

#### Sector Filters
```
✅ "Show me tech companies"
✅ "Healthcare stocks"
✅ "Financial sector"
✅ "Energy companies"
✅ "Consumer goods firms"
✅ "Industrial stocks"
✅ "Telecom companies"
✅ "Real estate firms"
✅ "Materials sector"
✅ "Media companies"
```

#### Quality Filters
```
✅ "High-quality companies"
✅ "Blue chip stocks"
✅ "Investment-grade firms"
✅ "Premium companies"
✅ "Top-tier stocks"
```

#### Risk Filters
```
✅ "Low-risk companies"
✅ "Safe investments"
✅ "Conservative stocks"
✅ "Stable companies"
✅ "High-risk stocks"
✅ "Volatile companies"
```

#### Size Filters
```
✅ "Large-cap companies"
✅ "Big corporations"
✅ "Small-cap stocks"
✅ "Mid-sized firms"
✅ "Mega-cap companies"
```

#### Performance Filters
```
✅ "High-performing companies"
✅ "Top performers"
✅ "Best stocks"
✅ "Underperforming companies"
✅ "Worst performers"
```

#### Valuation Filters
```
✅ "Undervalued companies"
✅ "Cheap stocks"
✅ "Overvalued companies"
✅ "Expensive stocks"
✅ "Fairly valued companies"
```

---

## 9. Temporal Relationships

**Feature:** Understands time-based relationships and events.

### What It Handles:

#### Before/After
```
✅ "Revenue before 2020"
✅ "Profit after Q2 2023"
✅ "Performance following the recession"
✅ "Data preceding the merger"
```

#### During/Within
```
✅ "Revenue during the pandemic"
✅ "Profit within 2022"
✅ "Performance throughout Q4"
✅ "Data over the last year"
```

#### Since/Until
```
✅ "Revenue since 2020"
✅ "Profit until Q2 2023"
✅ "Growth from 2019"
✅ "Performance up to now"
```

#### Between
```
✅ "Revenue between 2020 and 2023"
✅ "Profit from Q1 to Q3"
✅ "Data spanning 2019-2022"
```

#### Event-Based
```
✅ "Performance during the pandemic"       → 2020-2023
✅ "Revenue before the financial crisis"   → Pre-2008
✅ "Data after the dot-com bubble"         → Post-2001
✅ "During the recession"                  → 2008-2009 or 2020
✅ "Following the crisis"                  → Post-2008/2020
```

---

## 10. Conditional Statements

**Feature:** Understands if-then logic and conditional queries.

### What It Handles:

#### If-Then
```
✅ "If revenue > $1B then show me"
✅ "If Apple's margin is above 20% show it"
✅ "If profit exceeds $100M, display the data"
✅ "Provided that debt < 30%, show companies"
✅ "Assuming growth > 10%, which stocks qualify?"
```

#### When-Then
```
✅ "When price < $50, alert me"
✅ "When revenue reaches $1B, notify"
✅ "When margin improves, show data"
```

#### Unless
```
✅ "Show all companies unless they're in tech"
✅ "Display data unless revenue < $100M"
✅ "Alert unless margin < 10%"
```

#### Whenever
```
✅ "Whenever profit increases, show me"
✅ "Whenever price drops below $50, alert"
```

### Operators Supported:
- **Symbolic**: `>`, `<`, `=`, `>=`, `<=`, `!=`
- **Natural Language**:
  - Greater: "greater than", "above", "over", "exceeds", "surpasses", "more than", "higher than", "beyond", "north of"
  - Less: "less than", "below", "under", "beneath", "lower than", "falls short of", "south of"
  - Equal: "equals", "is", "matches", "same as", "equivalent to"
  - Greater/Equal: "at least", "no less than", "minimum"
  - Less/Equal: "at most", "no more than", "maximum", "up to"
  - Not Equal: "not equal", "different from", "other than"

---

## 11. Sentiment Detection

**Feature:** Detects sentiment and emotional tone in queries.

### What It Handles:

#### Positive Sentiment
```
✅ "Which companies are thriving?"         → Strong Positive
✅ "Show me excellent performers"          → Strong Positive
✅ "Good stocks to buy"                    → Mild Positive
✅ "Decent revenue growth"                 → Mild Positive
```

#### Negative Sentiment
```
✅ "Which companies are struggling?"       → Strong Negative
✅ "Show me terrible performers"           → Strong Negative
✅ "Poor profit margins"                   → Mild Negative
✅ "Weak revenue growth"                   → Mild Negative
```

#### Financial Sentiment
```
✅ "Bullish stocks"                        → Financial Positive
✅ "Bearish outlook"                       → Financial Negative
✅ "Optimistic forecast"                   → Positive
✅ "Pessimistic projections"               → Negative
```

#### Intensity Levels
- **Strong**: "outstanding", "terrible", "exceptional", "disastrous"
- **Moderate**: "good", "bad", "solid", "weak"
- **Mild**: "decent", "poor", "okay", "so-so"

#### Modifiers
- **Intensifiers**: "very", "extremely", "incredibly", "massively"
- **Diminishers**: "somewhat", "slightly", "a bit", "fairly"

---

## 12. Company Groups

**Feature:** Recognizes and expands predefined company groups.

### What It Handles:

#### Tech Acronyms
```
✅ "Show me FAANG stocks"
   → Facebook (Meta), Apple, Amazon, Netflix, Google

✅ "MAMAA companies"
   → Meta, Apple, Microsoft, Amazon, Alphabet

✅ "Magnificent 7"
   → Apple, Microsoft, Google, Amazon, Meta, Tesla, NVIDIA

✅ "MATANA stocks"
   → Microsoft, Apple, Tesla, Amazon, NVIDIA, Alphabet

✅ "GRANOLAS"
   → GSK, Roche, ASML, Nestle, Novartis, Novo Nordisk, 
      L'Oreal, LVMH, AstraZeneca, SAP, Sanofi
```

#### Industry Groups
```
✅ "Big Tech companies"
   → Apple, Microsoft, Google, Amazon, Meta

✅ "Cloud providers"
   → Amazon (AWS), Microsoft (Azure), Google (GCP)

✅ "Chip makers"
   → Intel, AMD, NVIDIA, TSMC

✅ "Big Auto"
   → Ford, GM, Toyota, Volkswagen

✅ "Big Oil"
   → ExxonMobil, Chevron, Shell, BP

✅ "Big Pharma"
   → Pfizer, J&J, Merck, Novartis

✅ "Big Banks"
   → JPMorgan, Bank of America, Wells Fargo, Citigroup
```

#### Index Groups
```
✅ "S&P 500 Leaders"
   → Top 10 S&P 500 companies by market cap

✅ "Dow 30 components"
   → All 30 Dow Jones Industrial Average stocks
```

#### Category Groups
```
✅ "Dividend Aristocrats"
   → Companies with 25+ years of consecutive dividend increases

✅ "Growth stocks"
   → High-growth companies (tech, biotech, etc.)

✅ "Value stocks"
   → Undervalued companies with strong fundamentals

✅ "ESG leaders"
   → Top-rated environmental, social, governance companies
```

---

## 13. Abbreviations & Acronyms

**Feature:** Expands common financial and business abbreviations.

### What It Handles:

#### Time Periods
```
✅ "YoY growth"             → Year-over-Year
✅ "QoQ revenue"            → Quarter-over-Quarter
✅ "MoM change"             → Month-over-Month
✅ "WoW trend"              → Week-over-Week
✅ "YTD performance"        → Year-to-Date
✅ "QTD earnings"           → Quarter-to-Date
✅ "MTD sales"              → Month-to-Date
✅ "WTD volume"             → Week-to-Date
```

#### Financial Metrics
```
✅ "P/E ratio"              → Price-to-Earnings
✅ "P/B ratio"              → Price-to-Book
✅ "ROE"                    → Return on Equity
✅ "ROA"                    → Return on Assets
✅ "EBITDA"                 → Earnings Before Interest, Taxes, 
                              Depreciation & Amortization
✅ "EPS"                    → Earnings Per Share
✅ "FCF"                    → Free Cash Flow
✅ "CAGR"                   → Compound Annual Growth Rate
✅ "ARR"                    → Annual Recurring Revenue
✅ "MRR"                    → Monthly Recurring Revenue
✅ "LTV"                    → Lifetime Value
✅ "CAC"                    → Customer Acquisition Cost
✅ "WACC"                   → Weighted Average Cost of Capital
✅ "NPV"                    → Net Present Value
✅ "IRR"                    → Internal Rate of Return
```

#### Business Terms
```
✅ "CEO"                    → Chief Executive Officer
✅ "CFO"                    → Chief Financial Officer
✅ "SMB"                    → Small and Medium Business
✅ "B2B"                    → Business to Business
✅ "B2C"                    → Business to Consumer
✅ "SaaS"                   → Software as a Service
✅ "IPO"                    → Initial Public Offering
✅ "M&A"                    → Mergers and Acquisitions
✅ "VC"                     → Venture Capital
✅ "PE"                     → Private Equity
✅ "AI/ML"                  → Artificial Intelligence / Machine Learning
✅ "KPI"                    → Key Performance Indicator
```

#### General Financial
```
✅ "NYSE"                   → New York Stock Exchange
✅ "NASDAQ"                 → National Association of Securities Dealers 
                              Automated Quotations
✅ "S&P"                    → Standard & Poor's
✅ "ETF"                    → Exchange-Traded Fund
✅ "GAAP"                   → Generally Accepted Accounting Principles
✅ "SEC"                    → Securities and Exchange Commission
✅ "FDIC"                   → Federal Deposit Insurance Corporation
```

---

## 14. Question Chaining

**Feature:** Understands multi-turn conversation flow and context.

### What It Handles:

#### Sequential Chains
```
✅ "Now show me Microsoft"
✅ "Next, compare to Google"
✅ "Then check Tesla"
✅ "Subsequently, analyze Amazon"
✅ "After that, look at Netflix"
```

#### Comparative Chains
```
✅ "How does that compare to Apple?"
✅ "In comparison to last quarter"
✅ "Versus Microsoft"
✅ "Relative to the industry average"
✅ "How does it differ from Google?"
```

#### Exploratory Chains
```
✅ "What about Microsoft?"
✅ "How about Tesla?"
✅ "What if we look at Amazon?"
✅ "Consider Google as well"
✅ "Maybe check Netflix too"
```

#### Continuation Chains
```
✅ "And also show profit"
✅ "Plus their market cap"
✅ "On top of that, show margins"
✅ "Additionally, check growth"
✅ "Furthermore, display debt"
```

#### Elaboration Chains
```
✅ "Tell me more about that"
✅ "Expand on the revenue trend"
✅ "Go deeper into the margins"
✅ "Break down the earnings"
✅ "Elaborate on the growth rate"
```

### Context Requirements:
- **Requires Previous Context**: Sequential, Continuation
- **May Use Context**: Comparative, Exploratory, Elaboration
- **Optional Context**: All chain types can work independently

---

## Performance

### ⚡ Response Times

The chatbot is optimized for fast responses:

- **Simple queries**: ~12ms
- **Typical queries**: 26-68ms
- **Complex queries**: 68-117ms
- **Very complex queries**: 117-167ms

All parsing is done in **under 200ms**, ensuring a smooth user experience.

---

## Tips for Best Results

### ✅ Do's

1. **Ask naturally** - Don't worry about exact keywords
   ```
   Good: "What's Apple's revenue last year?"
   Also Good: "how much did apple make in 2023?"
   ```

2. **Use abbreviations** - They're automatically expanded
   ```
   ✅ "Show me YoY growth"
   ✅ "What's the P/E ratio?"
   ✅ "FAANG stocks performance"
   ```

3. **Combine features** - The chatbot handles complex queries
   ```
   ✅ "Show me high-growth tech companies with revenue over $1B 
       during the pandemic, excluding FAANG"
   ```

4. **Follow up naturally** - Context is maintained
   ```
   You: "What's Apple's revenue?"
   Bot: [shows data]
   You: "How about Microsoft?"
   Bot: [shows Microsoft's revenue]
   ```

5. **Use approximations** - No need for exact values
   ```
   ✅ "Companies with revenue around $500M"
   ✅ "Margins roughly 20%"
   ```

### ⚠️ Limitations

1. **Data Availability** - The chatbot can only access data in the system
2. **Time Sensitivity** - "Latest" data depends on when it was last updated
3. **Ambiguity** - Very vague queries may need clarification
4. **Real-time Data** - Not connected to live market feeds

---

## Examples: Putting It All Together

### Example 1: Multi-Feature Query
```
"Show me high-quality tech companies with YoY revenue growth 
above 20%, excluding FAANG, that are undervalued"
```

**Features Used:**
- Natural Filtering (quality, tech, undervalued)
- Abbreviations (YoY)
- Fuzzy Quantities (above 20%)
- Company Groups (FAANG)
- Negation (excluding)

### Example 2: Follow-up Chain
```
You: "What's Apple's revenue last quarter?"
Bot: [shows Q4 2023 revenue: $119.58B]

You: "How does that compare to Microsoft?"
Bot: [compares Apple vs Microsoft Q4 revenue]

You: "What about their profit margins?"
Bot: [shows profit margins for both companies]
```

**Features Used:**
- Question Detection
- Temporal Relationships (last quarter)
- Question Chaining (compare, what about)
- Contextual Metric Inference (profit margins)

### Example 3: Complex Conditional
```
"If revenue exceeds $1B and profit margin is above 15%, 
show me the top 5 tech companies during the pandemic"
```

**Features Used:**
- Conditional Statements (if-then)
- Fuzzy Quantities ($1B, 15%)
- Comparative Language (top 5)
- Natural Filtering (tech companies)
- Temporal Relationships (during the pandemic)

---

## Need Help?

If the chatbot doesn't understand your query:
1. **Try rephrasing** - Use synonyms or simpler language
2. **Break it down** - Split complex queries into smaller parts
3. **Be specific** - Add more context (time periods, companies, metrics)
4. **Check spelling** - While the chatbot corrects typos, extreme misspellings may confuse it

---

**Version:** 1.0  
**Last Updated:** November 2025  
**Total NLU Features:** 14  
**Test Coverage:** 790 tests, 100% passing

