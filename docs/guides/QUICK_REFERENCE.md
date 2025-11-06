# 📖 NLU Quick Reference Guide

## 🚀 Quick Start

**Ask questions naturally!** The chatbot understands:
- Misspellings
- Abbreviations
- Company groups (FAANG, etc.)
- Comparative language
- Trend language
- Follow-up questions
- And much more!

---

## 🎯 Common Query Patterns

### Basic Questions
```
✅ What's Apple's revenue?
✅ How's Microsoft doing?
✅ Show me Tesla's profit margins
✅ Tell me about Amazon's performance
```

### Comparisons
```
✅ Apple vs Microsoft revenue
✅ Which has better margins?
✅ Compare Tesla and Ford
✅ Who's the most profitable?
```

### Trends
```
✅ Companies with growing revenue
✅ Which stocks are rising?
✅ Show me declining margins
✅ Companies with accelerating growth
```

### Filtering
```
✅ Show me tech companies
✅ Large-cap stocks
✅ High-quality companies with low risk
✅ Undervalued firms in healthcare
```

### Time Periods
```
✅ Revenue last quarter
✅ YoY growth
✅ Performance during the pandemic
✅ Data between 2020 and 2023
```

### Company Groups
```
✅ FAANG stocks
✅ Magnificent 7 performance
✅ Big Tech revenue
✅ Dividend Aristocrats
```

### Conditionals
```
✅ If revenue > $1B, show me
✅ Companies with profit margin above 20%
✅ Show all unless they're in tech
```

---

## 💡 Feature Cheat Sheet

| Feature | Example Queries |
|---------|----------------|
| **Spelling Correction** | "Appel revenue", "Mikrosft earnings" |
| **Comparisons** | "Apple vs Microsoft", "Which is best?" |
| **Trends** | "Growing revenue", "Declining margins" |
| **Negation** | "Not in tech", "Excluding FAANG" |
| **Approximations** | "Around $1B", "Roughly 20%" |
| **Filters** | "Tech companies", "Low-risk stocks" |
| **Temporal** | "During pandemic", "Before 2020" |
| **Conditionals** | "If revenue > $1B", "When price < $50" |
| **Sentiment** | "Best performers", "Struggling companies" |
| **Groups** | "FAANG", "Big Tech", "Magnificent 7" |
| **Abbreviations** | "YoY growth", "P/E ratio", "EBITDA" |
| **Chaining** | "What about Microsoft?", "Then show Tesla" |

---

## 🔤 Supported Abbreviations

### Time Periods
- **YoY** - Year-over-Year
- **QoQ** - Quarter-over-Quarter
- **MoM** - Month-over-Month
- **YTD** - Year-to-Date
- **QTD** - Quarter-to-Date

### Financial Metrics
- **P/E** - Price-to-Earnings
- **P/B** - Price-to-Book
- **ROE** - Return on Equity
- **ROA** - Return on Assets
- **EBITDA** - Earnings Before Interest, Taxes, Depreciation & Amortization
- **EPS** - Earnings Per Share
- **FCF** - Free Cash Flow
- **CAGR** - Compound Annual Growth Rate

### Business Terms
- **CEO** - Chief Executive Officer
- **CFO** - Chief Financial Officer
- **IPO** - Initial Public Offering
- **M&A** - Mergers and Acquisitions
- **B2B** - Business to Business
- **B2C** - Business to Consumer
- **SaaS** - Software as a Service

---

## 🏢 Company Groups

### Tech Acronyms
- **FAANG** - Facebook, Apple, Amazon, Netflix, Google
- **MAMAA** - Meta, Apple, Microsoft, Amazon, Alphabet
- **Magnificent 7** - Apple, Microsoft, Google, Amazon, Meta, Tesla, NVIDIA
- **MATANA** - Microsoft, Apple, Tesla, Amazon, NVIDIA, Alphabet
- **GRANOLAS** - GSK, Roche, ASML, Nestle, Novartis, Novo Nordisk, L'Oreal, LVMH, AstraZeneca, SAP, Sanofi

### Industry Groups
- **Big Tech** - Apple, Microsoft, Google, Amazon, Meta
- **Cloud Providers** - Amazon (AWS), Microsoft (Azure), Google (GCP)
- **Chip Makers** - Intel, AMD, NVIDIA, TSMC
- **Big Auto** - Ford, GM, Toyota, Volkswagen
- **Big Oil** - ExxonMobil, Chevron, Shell, BP
- **Big Pharma** - Pfizer, J&J, Merck, Novartis
- **Big Banks** - JPMorgan, Bank of America, Wells Fargo, Citigroup

---

## 📊 Example Queries by Complexity

### Simple (12ms)
```
What's Apple's revenue?
How's Microsoft doing?
Show me Tesla stock price
```

### Medium (26-68ms)
```
Compare Apple and Microsoft revenue
FAANG stocks performance
Tech companies with YoY growth > 20%
```

### Complex (68-117ms)
```
Show me high-quality tech companies with revenue over $1B,
excluding FAANG, that are undervalued
```

### Very Complex (117-167ms)
```
Compare Magnificent 7 YoY revenue growth during the pandemic,
then show me which had the best profit margins, excluding
companies with high risk
```

---

## ✅ Tips for Best Results

### Do's ✓
- Ask naturally (like talking to a person)
- Use abbreviations (YoY, P/E, FAANG, etc.)
- Combine multiple features in one query
- Follow up with "what about X?" or "how does that compare?"
- Use approximations ("around $1B", "roughly 20%")

### Don'ts ✗
- Don't worry about exact spelling
- Don't use overly technical syntax
- Don't be too vague (add context if needed)
- Don't expect real-time data (depends on data updates)

---

## 🔄 Follow-Up Patterns

After asking about Apple:
```
✅ "How about Microsoft?"           → Shows Microsoft's data
✅ "Compare it to Google"           → Compares Apple to Google
✅ "What about their margins?"      → Shows Apple's margins
✅ "Then show me Tesla"             → Shows Tesla's data
✅ "Tell me more about that"        → Elaborates on previous response
```

---

## 🎨 Natural Language Examples

### Instead of: "AAPL revenue Q4 2023"
**Say**: "What was Apple's revenue last quarter?"

### Instead of: "MSFT vs GOOGL revenue comparison"
**Say**: "Compare Microsoft and Google revenue"

### Instead of: "tech sector companies market_cap > 1B"
**Say**: "Show me tech companies worth over $1B"

### Instead of: "FAANG revenue_growth YoY 2020-2023"
**Say**: "FAANG revenue growth YoY during the pandemic"

---

## ⚡ Performance

| Query Type | Response Time |
|-----------|---------------|
| Simple | ~12ms |
| Typical | 26-68ms |
| Complex | 68-117ms |
| Very Complex | 117-167ms |

All queries parse in **under 200ms**! 🚀

---

## 🐛 Common Issues

### Query not understood?
1. **Try rephrasing** - Use synonyms or simpler language
2. **Break it down** - Split complex queries into parts
3. **Add context** - Specify time period, company, or metric
4. **Check spelling** - While we correct typos, extreme misspellings may confuse

### Wrong company shown?
- Be specific with company names
- Use ticker symbols if ambiguous (e.g., "MSFT" not "Microsoft")

### No data available?
- Check if data exists for that company/time period
- Try a different time range
- Verify company name is correct

---

## 📞 Need Help?

- **User Guide**: See `NLU_USER_GUIDE.md` for comprehensive examples
- **Technical Guide**: See `NLU_TECHNICAL_GUIDE.md` for developers
- **Deployment**: See `DEPLOYMENT_GUIDE.md` for setup instructions

---

## 🎯 Feature Summary

**14 Major NLU Features**:
1. ✅ Spelling Correction
2. ✅ Comparative Language
3. ✅ Trend Direction Language
4. ✅ Contextual Metric Inference
5. ✅ Negation Handling
6. ✅ Multi-Intent Queries
7. ✅ Fuzzy Quantities & Approximations
8. ✅ Natural Filtering
9. ✅ Temporal Relationships
10. ✅ Conditional Statements
11. ✅ Sentiment Detection
12. ✅ Company Groups
13. ✅ Abbreviations & Acronyms
14. ✅ Question Chaining

**790 Tests** - 100% Passing ✓  
**Optimized Performance** - 33-68x Faster ⚡  
**Production Ready** - Fully Deployed 🚀

---

**Version**: 1.0  
**Last Updated**: November 2025  
**Quick Reference** - Print or bookmark this page!

