# 🚀 Complete Full Ingestion Scripts Guide

## 📋 Main Ingestion Scripts (Run These)

### 1. **S&P 500 Financial Data** (Primary - Run This First!)
```powershell
python scripts/ingestion/ingest_sp500_15years.py
```
**What it does:**
- Ingests all 500+ S&P 500 companies
- Gets 15 years of financial data (2010-2025)
- Auto-resumes if interrupted
- Processes 20 companies at a time
- **Time:** 2-3 hours
- **Result:** 50,000+ financial facts

### 2. **Historical Stock Prices** (Run After Financial Data)
```powershell
python scripts/ingestion/load_historical_prices_15years.py
```
**What it does:**
- Loads 15 years of daily stock prices
- Uses Yahoo Finance
- Saves all historical quotes to database
- **Time:** 1-2 hours
- **Result:** 1.7M+ price records

### 3. **Custom Universe Ingestion** (Alternative to #1)
```powershell
# For S&P 500
python scripts/ingestion/ingest_universe.py --universe sp500 --years 15 --resume

# For custom ticker file
python scripts/ingestion/ingest_universe.py --universe-file my_tickers.txt --years 15 --resume
```

---

## 🔧 Helper Scripts

### Monitor Progress
```powershell
python scripts/ingestion/monitor_ingestion.py
```

### Fill Data Gaps (Backfill Missing Years)
```powershell
python scripts/ingestion/fill_data_gaps.py --target-years "2019,2020,2025" --years-back 7 --batch-size 10
```

### Check Database Status
```powershell
python scripts/utility/check_ingestion_status.py
```

### Refresh Quotes (Update Latest Prices)
```powershell
python scripts/ingestion/refresh_quotes.py
```

---

## 📝 Complete Ingestion Sequence

### Step-by-Step Full Ingestion:

```powershell
# Step 1: Ingest S&P 500 Financial Data (2-3 hours)
python scripts/ingestion/ingest_sp500_15years.py

# Step 2: Load Historical Prices (1-2 hours)
python scripts/ingestion/load_historical_prices_15years.py

# Step 3: Verify Results
python scripts/utility/check_ingestion_status.py
```

---

## 🎯 All Available Ingestion Scripts

### Main Scripts:
1. `ingest_sp500_15years.py` - **Main S&P 500 script (use this!)**
2. `ingest_universe.py` - Generic universe ingestion
3. `load_historical_prices_15years.py` - Historical price data
4. `ingest_20years_sp500.py` - 20 years instead of 15
5. `ingest_extended_universe.py` - Beyond S&P 500 (1500+ companies)

### Utility Scripts:
6. `fill_data_gaps.py` - Backfill missing years
7. `monitor_ingestion.py` - Monitor progress
8. `refresh_quotes.py` - Update latest prices
9. `backfill_metrics.py` - Backfill calculated metrics
10. `batch_ingest.py` - Batch ingestion utility

### Specialized Scripts:
11. `ingest_companyfacts.py` - SEC company facts
12. `ingest_companyfacts_batch.py` - Batch company facts
13. `ingest_frames.py` - SEC frame data
14. `ingest_from_file.py` - Ingest from file
15. `ingest_more_years.py` - Add more years
16. `load_prices_stooq.py` - Prices from Stooq
17. `load_prices_yfinance.py` - Prices from Yahoo Finance
18. `load_ticker_cik.py` - Load ticker-CIK mappings
19. `parse_raw_sec_filings.py` - Parse SEC filings
20. `fetch_imf_sector_kpis.py` - IMF sector data

---

## 🚀 Quick Start Commands

### For S&P 500 (500 companies):
```powershell
python scripts/ingestion/ingest_sp500_15years.py
python scripts/ingestion/load_historical_prices_15years.py
```

### For S&P 1500 (1500 companies):
```powershell
python scripts/ingestion/ingest_extended_universe.py
```

### For Custom List:
```powershell
# Create ticker file (one per line)
# sp1500_tickers.txt:
# AAPL
# MSFT
# GOOGL
# ...

python scripts/ingestion/ingest_universe.py --universe-file sp1500_tickers.txt --years 15 --resume
```

---

## 📊 Expected Results After Full Ingestion

| Metric | Before | After |
|--------|--------|-------|
| **Companies** | 8 | 500+ |
| **Financial Facts** | 968 | 50,000+ |
| **Metric Snapshots** | 1,592 | 30,000+ |
| **Market Quotes** | 0 | 1.7M+ |
| **Database Size** | 1.16 MB | 150-200 MB |
| **Fiscal Years** | 2019-2023 | 2010-2025 |

---

## ⚙️ Script Options

### `ingest_universe.py` Options:
```powershell
python scripts/ingestion/ingest_universe.py \
    --universe sp500              # Use built-in universe
    --universe-file file.txt      # Or custom file
    --years 15                    # Years of data
    --chunk-size 20               # Companies per batch
    --sleep 2.0                   # Seconds between batches
    --resume                      # Resume from checkpoint
    --progress-file .progress.json
```

### `fill_data_gaps.py` Options:
```powershell
python scripts/ingestion/fill_data_gaps.py \
    --target-years "2019,2020,2025"  # Years to fill
    --years-back 7                    # How many years to fetch
    --batch-size 10                   # Companies per batch
    --max-tickers 50                  # Limit to N companies
    --dry-run                          # Test without ingesting
```

---

## 🔄 Automated Scripts

### PowerShell (Windows):
```powershell
.\scripts\run_data_ingestion.ps1
```

### Bash (Linux/Mac):
```bash
./scripts/run_data_ingestion.sh
```

---

## 📍 Script Locations

All scripts are in: `scripts/ingestion/`

**Main scripts:**
- `scripts/ingestion/ingest_sp500_15years.py` ⭐ **START HERE**
- `scripts/ingestion/load_historical_prices_15years.py` ⭐ **RUN SECOND**

**Helper scripts:**
- `scripts/utility/check_ingestion_status.py`
- `scripts/ingestion/monitor_ingestion.py`

---

## ✅ Verification Commands

After ingestion, verify with:

```powershell
# Check database stats
python -c "import sqlite3; conn = sqlite3.connect('benchmarkos_chatbot.sqlite3'); print('Companies:', conn.execute('SELECT COUNT(DISTINCT ticker) FROM financial_facts').fetchone()[0]); print('Facts:', conn.execute('SELECT COUNT(*) FROM financial_facts').fetchone()[0])"

# Check ingestion status
python scripts/utility/check_ingestion_status.py
```

---

## 🎯 Recommended Workflow

1. **Start with S&P 500:**
   ```powershell
   python scripts/ingestion/ingest_sp500_15years.py
   ```

2. **Load prices:**
   ```powershell
   python scripts/ingestion/load_historical_prices_15years.py
   ```

3. **Verify:**
   ```powershell
   python scripts/utility/check_ingestion_status.py
   ```

4. **Test chatbot:**
   ```powershell
   python app/run_chatbot.py
   ```

---

## 💡 Tips

- ✅ Always use `--resume` flag (auto-resumes if interrupted)
- ✅ Run during off-peak hours (faster API responses)
- ✅ Monitor progress with `monitor_ingestion.py`
- ✅ Backup database before large ingestion
- ✅ Check disk space (need ~1GB for full ingestion)

---

## 🎓 Conclusion

This comprehensive ingestion system enables robust financial data collection and analysis across the S&P 1500 and extended market universes. By following the scripts and workflows outlined in this guide, users can build a comprehensive financial database with historical data spanning multiple years, supporting advanced analytics and chatbot capabilities.

---

## 🙏 Acknowledgments

We would like to extend our sincere gratitude to **Professor Patrick** for his invaluable guidance and mentorship throughout this project. We also express our deep appreciation to all the judges from **Capital One**, **EY**, **Mizuho**, and **FI Consulting** for their expert feedback, insights, and support that have been instrumental in shaping and improving this work.
