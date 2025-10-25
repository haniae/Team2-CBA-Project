# How to Expand Your Database Beyond 391k Rows

## Current Status
- ✅ 475 companies ingested (97% of S&P 500)
- ✅ 33,648 financial facts
- ⚠️ Only 46 tickers have price data
- ⚠️ Average 4.1 years of data (mostly 2021-2024)
- ⚠️ 14 S&P 500 tickers still missing

## 🚀 Ways to Add More Data

### Option 1: Complete S&P 500 (Quick - 5 minutes)
Add the remaining 14 S&P 500 companies:

```bash
python scripts/ingestion/ingest_sp500_15years.py
```

**Will add:** ~1,000-1,500 more financial facts

---

### Option 2: Load Historical Prices (1-2 hours)
You only have 46 tickers with price data. Load prices for all 475:

```bash
python scripts/ingestion/load_historical_prices_15years.py
```

**Will add:** 
- 15 years × 252 trading days × 475 tickers = ~1.8 million price points
- But stored as latest quotes, so ~475 new market_quotes rows

---

### Option 3: Ingest More Years (2-3 hours)
Currently you have mostly 2021-2024 data. Get full 15 years (2010-2025):

```bash
# This will add older years for existing companies
python scripts/ingestion/ingest_sp500_15years.py
```

The system automatically fetches all available years when you run ingestion.

**Will add:** ~100,000-150,000 more financial facts (older years)

---

### Option 4: Add More Companies Beyond S&P 500 (Hours to Days)

#### A. Nasdaq 100
Create a ticker file and ingest:

```bash
# Create nasdaq100.txt with one ticker per line
python scripts/ingestion/ingest_universe.py \
  --universe-file nasdaq100.txt \
  --years 15 \
  --resume
```

#### B. Russell 2000
```bash
python scripts/ingestion/ingest_universe.py \
  --universe-file russell2000.txt \
  --years 15 \
  --chunk-size 20 \
  --sleep 2.0 \
  --resume
```

#### C. All US Public Companies (Massive - Days)
```bash
python scripts/ingestion/ingest_universe.py \
  --universe-file all_us_tickers.txt \
  --years 10 \
  --chunk-size 25 \
  --sleep 2.0 \
  --resume
```

**Will add:** Hundreds of thousands to millions of facts depending on universe size

---

### Option 5: Ingest Specific Companies

Create a custom ticker file:

```bash
# Create my_companies.txt
echo TSLA > my_companies.txt
echo NVDA >> my_companies.txt
echo AMD >> my_companies.txt
echo PLTR >> my_companies.txt

# Ingest them
python scripts/ingestion/ingest_universe.py \
  --universe-file my_companies.txt \
  --years 15 \
  --resume
```

---

## 📊 Recommended Sequence for Maximum Data

### Step 1: Complete Current S&P 500 (5 min)
```bash
python scripts/ingestion/ingest_sp500_15years.py
```
Adds: ~1,500 facts

### Step 2: Load All Historical Prices (1-2 hours)
```bash
python scripts/ingestion/load_historical_prices_15years.py
```
Adds: ~475 latest quotes + price history

### Step 3: Backfill Older Years (2-3 hours)
The S&P 500 script will automatically get older years on re-run if available.

### Step 4: Expand Universe (Optional)
Add Nasdaq 100, Russell 2000, or other indices.

---

## 🎯 Quick Commands to Add More Data NOW

### To add ~150,000 more rows (3-4 hours):

```bash
# 1. Complete S&P 500 missing tickers
python scripts/ingestion/ingest_sp500_15years.py

# 2. Load historical prices for all companies
python scripts/ingestion/load_historical_prices_15years.py

# 3. Check your progress
python check_database_simple.py
```

### To add ~500,000+ more rows (1-2 days):

```bash
# 1. Create a larger universe file (example: top 1000 US stocks)
# Download from: https://www.slickcharts.com/sp500
# Or create your own list

# 2. Ingest the universe
python scripts/ingestion/ingest_universe.py \
  --universe-file sp1000.txt \
  --years 15 \
  --chunk-size 20 \
  --sleep 2.0 \
  --resume
```

---

## 💡 Tips for Large Ingestions

### 1. Use Resume Capability
Always use `--resume` flag so you can stop and restart:
```bash
python scripts/ingestion/ingest_universe.py \
  --universe-file large_list.txt \
  --years 15 \
  --resume
```

### 2. Run Overnight
Large ingestions take hours - start before bed:
```bash
# Start in evening, check in morning
python scripts/ingestion/ingest_universe.py \
  --universe-file russell2000.txt \
  --years 10 \
  --resume
```

### 3. Monitor Progress
Check status while running (in another terminal):
```bash
python check_ingestion_status.py
```

### 4. Adjust Performance
For faster ingestion (but respect rate limits):
```bash
python scripts/ingestion/ingest_universe.py \
  --universe-file tickers.txt \
  --chunk-size 30 \        # Larger chunks
  --sleep 1.5 \            # Less sleep (careful!)
  --years 10 \             # Fewer years = faster
  --resume
```

---

## 📈 Expected Growth

| Action | Time | Rows Added | Total After |
|--------|------|------------|-------------|
| Current | - | - | 391,000 |
| Complete S&P 500 | 5 min | +1,500 | 392,500 |
| Load prices (all) | 1-2 hr | +430 | 392,930 |
| Backfill older years | 2-3 hr | +150,000 | 542,930 |
| Add Nasdaq 100 | 2-3 hr | +100,000 | 642,930 |
| Add Russell 2000 | 2-3 days | +2,000,000 | 2,642,930 |

---

## 🔍 Check What You Need

Run this to see what's missing:

```bash
# Overall status
python check_database_simple.py

# Detailed progress
python check_ingestion_status.py
```

Look for:
- Remaining S&P 500 tickers
- Price data coverage (should be 475/475)
- Year coverage (should show 2010-2025)
- Companies you want but don't have

---

## 🎯 My Recommendation

**For immediate expansion (3-4 hours, adds ~150k rows):**

```bash
# Run these three commands in sequence:
python scripts/ingestion/ingest_sp500_15years.py
python scripts/ingestion/load_historical_prices_15years.py
python check_database_simple.py
```

This will:
1. ✅ Complete all 482 S&P 500 companies (100%)
2. ✅ Add historical prices for all companies
3. ✅ Backfill any missing years
4. ✅ Give you comprehensive S&P 500 coverage

**Result:** ~540,000 total rows with complete S&P 500 data

---

## 📚 Advanced: Custom Data Sources

### Add International Stocks
```bash
# Create file with international tickers
echo "BABA" > international.txt
echo "TSM" >> international.txt
echo "NVO" >> international.txt

python scripts/ingestion/ingest_universe.py \
  --universe-file international.txt \
  --years 10 \
  --resume
```

### Add Crypto/ETF Tickers
Some may work if they have SEC filings:
```bash
echo "GBTC" > crypto_etfs.txt
echo "ETHE" >> crypto_etfs.txt
echo "SPY" >> crypto_etfs.txt
echo "QQQ" >> crypto_etfs.txt

python scripts/ingestion/ingest_universe.py \
  --universe-file crypto_etfs.txt \
  --years 5 \
  --resume
```

---

## ✅ Next Steps

1. **Decide your goal:**
   - Complete S&P 500 only? → Run ingest_sp500_15years.py
   - Add more companies? → Create ticker file + use ingest_universe.py
   - Add more years? → Re-run ingestion scripts
   - Add prices? → Run load_historical_prices_15years.py

2. **Run the command**

3. **Monitor progress:**
   ```bash
   python check_ingestion_status.py
   ```

4. **Verify results:**
   ```bash
   python check_database_simple.py
   ```

---

**Ready to expand? Pick an option above and run the command!** 🚀

