# 🎯 Enable FRED Economic Data (2-Minute Setup)

## ✅ Status: fredapi Package Installed

The FRED API package is now installed. To enable Federal Reserve economic data in your responses, you just need a free API key.

---

## 🚀 Quick Setup (2 Minutes)

### Step 1: Get Free API Key

1. **Go to:** https://fred.stlouisfed.org/docs/api/api_key.html
2. **Click:** "Request API Key"
3. **Fill out simple form:**
   - Email address
   - Organization (can be "Personal" or your company)
   - Intended use (e.g., "Financial analysis research")
4. **Submit** - API key sent instantly to your email
5. **Copy your API key** (looks like: `abc123def456ghi789...`)

**Total time:** ~2 minutes  
**Cost:** FREE forever  
**Rate limits:** 120 requests/minute (more than enough)

---

### Step 2: Set Environment Variable

#### **Windows (PowerShell):**
```powershell
# Temporary (current session only)
$env:FRED_API_KEY="your_api_key_here"

# Permanent (add to your profile)
[System.Environment]::SetEnvironmentVariable("FRED_API_KEY", "your_api_key_here", "User")
```

#### **Windows (Command Prompt):**
```cmd
setx FRED_API_KEY "your_api_key_here"
```

#### **Mac/Linux:**
```bash
# Temporary (current session)
export FRED_API_KEY="your_api_key_here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export FRED_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

---

### Step 3: Restart Your Chatbot

```bash
# Kill the old server
# Then restart:
python serve_chatbot.py
```

---

## 📊 What FRED Data Adds to Your Responses

Once enabled, every response will include macroeconomic context:

### Economic Indicators (27 total)

**Macro Economy:**
- GDP (Gross Domestic Product)
- Unemployment Rate
- Nonfarm Payroll (job creation)

**Inflation & Prices:**
- CPI (Consumer Price Index)
- Core CPI (ex food & energy)
- PCE Price Index

**Interest Rates:**
- Federal Funds Rate
- 10-Year Treasury Yield
- 2-Year Treasury Yield
- Yield Curve Spread (recession indicator)

**Market Indicators:**
- VIX (volatility/fear gauge)
- S&P 500 Index
- USD Index
- Consumer Sentiment

**And more:** Retail sales, housing starts, industrial production, money supply, corporate profits

---

## 🔍 Before vs. After FRED

### ❌ Without FRED
```
Apple's revenue for FY2024 was $394.3B, up 7.2% YoY.

The growth was driven by Services ($85.2B, +14% YoY) and iPhone 
sales in emerging markets.

📊 Sources:
- [Apple 10-K FY2024](url)
- [Yahoo Finance](url)
```

### ✅ With FRED
```
Apple's revenue for FY2024 was $394.3B, up 7.2% YoY.

The growth was driven by Services ($85.2B, +14% YoY) and iPhone 
sales in emerging markets.

### Economic Context

Apple's growth aligns with broader economic strength:
- **U.S. GDP** grew **2.8%** in Q4 2024 (FRED)
- **Unemployment** at **3.7%**, supporting consumer spending
- **Consumer Sentiment** at **72.6**, above historical average
- **VIX** at **14.2**, indicating low market volatility

This supportive macro environment (strong GDP, low unemployment, 
confident consumers) creates favorable conditions for premium 
consumer tech spending, benefiting Apple's high-margin products.

📊 Sources:
- [Apple 10-K FY2024](url)
- [Yahoo Finance](url)
- [FRED GDP](https://fred.stlouisfed.org/series/GDP)
- [FRED Unemployment](https://fred.stlouisfed.org/series/UNRATE)
- [FRED Consumer Sentiment](https://fred.stlouisfed.org/series/UMCSENT)
- [FRED VIX](https://fred.stlouisfed.org/series/VIXCLS)
```

**Added value:**
- ✅ Macroeconomic context
- ✅ Industry headwinds/tailwinds
- ✅ Recession indicators
- ✅ 3-4 additional sources cited
- ✅ More comprehensive analysis

---

## 💡 Use Cases Where FRED Shines

### 1. **Investment Analysis**
**Q:** "Should I invest in Apple?"  
**With FRED:** Can assess if macro environment favors tech (GDP growth, interest rates, consumer spending)

### 2. **Risk Assessment**
**Q:** "What are the risks for Tesla?"  
**With FRED:** Can identify macro risks (recession probability via yield curve, consumer confidence trends)

### 3. **Sector Analysis**
**Q:** "How is the tech sector performing?"  
**With FRED:** Can connect tech performance to GDP, inflation, interest rates

### 4. **Comparison with Context**
**Q:** "Is Microsoft growing faster than Apple?"  
**With FRED:** Can contextualize growth rates vs. overall economic growth

### 5. **Forward Outlook**
**Q:** "What's the outlook for Amazon?"  
**With FRED:** Can assess if macro trends (consumer spending, retail sales) support growth

---

## 🔧 Troubleshooting

### Issue: "fredapi not installed"
**Solution:** Already fixed! ✅ We installed it in this session.

### Issue: "FRED data not showing in responses"
**Cause:** No API key set  
**Solution:** Follow Step 2 above to set environment variable

### Issue: "Invalid API key"
**Cause:** Typo in API key  
**Solution:** Double-check the key, ensure no extra spaces

### Issue: "FRED request failed"
**Cause:** Network issue or rate limit  
**Solution:** 
- Check internet connection
- Wait 1 minute (rate limit resets)
- Check FRED status: https://fred.stlouisfed.org/

---

## ✅ Verification

After setting up FRED, test it:

**Ask:** "What is Apple's revenue?"

**You should see:**
- ✅ Revenue data (from SEC)
- ✅ Market data (from Yahoo Finance)
- ✅ **Economic context section** (from FRED) ← NEW
- ✅ **FRED source links** in Sources section ← NEW

If you see economic context (GDP, unemployment, etc.), FRED is working! 🎉

---

## 📚 FRED Documentation

**Official Docs:** https://fred.stlouisfed.org/docs/api/fred/  
**Series List:** https://fred.stlouisfed.org/tags/series  
**Python Package:** https://github.com/mortada/fredapi

---

## 🚀 Summary

**Current Status:**
- ✅ **fredapi package:** Installed
- ✅ **Code integration:** Enabled by default
- ⚠️ **API key:** You need to set this (2 minutes)

**Once you set the API key:**
- ✅ All responses will include macroeconomic context
- ✅ 27 economic indicators will be available
- ✅ More comprehensive, institutional-grade analysis
- ✅ 3-4 additional sources per response

**It's a 2-minute setup for massively better responses!** 📊

