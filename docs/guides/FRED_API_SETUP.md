# 🚀 FRED API Setup Guide

## Quick Start (2 Minutes)

### Step 1: Get Your Free API Key

1. **Visit:** https://fred.stlouisfed.org/docs/api/api_key.html
2. **Click:** "Request API Key"
3. **Fill out the form:**
   - Email address
   - Organization (can be "Personal")
   - Intended use (e.g., "Financial analysis research")
4. **Submit** - API key sent instantly to your email
5. **Copy your API key**

**Cost:** FREE forever  
**Rate limits:** 120 requests/minute (more than enough)

---

### Step 2: Run Setup Script

```bash
# Activate virtual environment
source .venv/bin/activate

# Run interactive setup
python scripts/setup_fred_api.py
```

The script will:
- ✅ Check if `fredapi` is installed
- ✅ Test your API key connection
- ✅ Save the key to `.env` file
- ✅ Verify everything works

---

### Step 3: Alternative Manual Setup

If you prefer to set it up manually:

#### Option A: Create `.env` file

```bash
# Create .env file in project root
cat > .env << EOF
FRED_API_KEY=your_api_key_here
EOF
```

#### Option B: Set environment variable

```bash
# Temporary (current session)
export FRED_API_KEY="your_api_key_here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export FRED_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

---

### Step 4: Test the Connection

```bash
# Test FRED API connection
python scripts/test_fred_api.py
```

You should see:
```
✅ FRED_API_KEY found: abc123def4...xyz9
✅ Gross Domestic Product (GDP)
   Value: 27,890,500.00 Billions of Dollars
   Date: 2025-01-01
...
🎉 FRED API is working correctly!
```

---

### Step 5: Restart Your Chatbot

```bash
# Restart the server to load the new API key
# (Kill existing server first if running)
uvicorn src.finanlyzeos_chatbot.web:app --reload --host 0.0.0.0 --port 8000
```

---

## What FRED Data Adds

Once enabled, every chatbot response will include **macroeconomic context**:

### Economic Indicators (27+ total)

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

## Example Response with FRED

### ❌ Without FRED
```
Apple's revenue for FY2024 was $394.3B, up 7.2% YoY.

📊 Sources:
- [Apple 10-K FY2024](url)
- [Yahoo Finance](url)
```

### ✅ With FRED
```
Apple's revenue for FY2024 was $394.3B, up 7.2% YoY.

### Economic Context

Apple's growth aligns with broader economic strength:
- **U.S. GDP** grew **2.8%** in Q4 2024 (FRED)
- **Unemployment** at **3.7%**, supporting consumer spending
- **Consumer Sentiment** at **72.6**, above historical average
- **VIX** at **14.2**, indicating low market volatility

📊 Sources:
- [Apple 10-K FY2024](url)
- [Yahoo Finance](url)
- [FRED GDP](https://fred.stlouisfed.org/series/GDP)
- [FRED Unemployment](https://fred.stlouisfed.org/series/UNRATE)
- [FRED Consumer Sentiment](https://fred.stlouisfed.org/series/UMCSENT)
```

---

## Troubleshooting

### Issue: "fredapi not installed"
```bash
pip install fredapi>=0.5.0
```

### Issue: "FRED_API_KEY not set"
- Check if `.env` file exists and contains `FRED_API_KEY=...`
- Or set environment variable: `export FRED_API_KEY="your_key"`
- Restart your server after setting

### Issue: "Invalid API key"
- Double-check the key (no extra spaces)
- Verify you copied the full key from email
- Test with: `python scripts/test_fred_api.py`

### Issue: "FRED request failed"
- Check internet connection
- Wait 1 minute (rate limit: 120 requests/minute)
- Check FRED status: https://fred.stlouisfed.org/

### Issue: "FRED data not showing in responses"
- Verify API key is set: `echo $FRED_API_KEY`
- Test connection: `python scripts/test_fred_api.py`
- Check server logs for FRED-related errors
- Restart server after setting API key

---

## Verification

After setup, test with:

**Query:** "What is Apple's revenue?"

**You should see:**
- ✅ Revenue data (from SEC)
- ✅ Market data (from Yahoo Finance)
- ✅ **Economic context section** (from FRED) ← NEW
- ✅ **FRED source links** in Sources section ← NEW

If you see economic context (GDP, unemployment, etc.), FRED is working! 🎉

---

## Additional Resources

- **FRED Official Docs:** https://fred.stlouisfed.org/docs/api/fred/
- **Series List:** https://fred.stlouisfed.org/tags/series
- **Python Package:** https://github.com/mortada/fredapi
- **Detailed Guide:** `docs/guides/ENABLE_FRED_GUIDE.md`

---

## Summary

**Current Status:**
- ✅ **fredapi package:** Installed
- ✅ **Code integration:** Enabled by default
- ⚠️ **API key:** You need to set this (2 minutes)

**Once you set the API key:**
- ✅ All responses will include macroeconomic context
- ✅ 27+ economic indicators will be available
- ✅ More comprehensive, institutional-grade analysis
- ✅ 3-4 additional sources per response

**It's a 2-minute setup for massively better responses!** 📊

