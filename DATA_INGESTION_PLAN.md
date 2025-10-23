# 📊 Data Ingestion Plan - Making All Years Solid

## Current Status (Before Ingestion)

| Year | Companies | Status |
|------|-----------|--------|
| 2019 | 8 (1.7%) | 🔴 **WEAK** |
| 2020 | 8 (1.7%) | 🔴 **WEAK** |
| 2021 | 467 (98.3%) | 🟢 **SOLID** |
| 2022 | 468 (98.5%) | 🟢 **SOLID** |
| 2023 | 472 (99.4%) | 🟢 **SOLID** |
| 2024 | 464 (97.7%) | 🟢 **SOLID** |
| 2025 | 59 (12.4%) | 🔴 **WEAK** |

**Total Companies**: 475  
**Data Gaps**: 467 companies missing 2019-2020, 416 missing 2025

---

## Goal: 100% Coverage for 2019-2025

| Year | Target | Increase |
|------|--------|----------|
| 2019 | 475 companies | +467 (+5,838%) |
| 2020 | 475 companies | +467 (+5,838%) |
| 2021 | 475 companies | +8 |
| 2022 | 475 companies | +7 |
| 2023 | 475 companies | +3 |
| 2024 | 475 companies | +11 |
| 2025 | 475 companies | +416 (+705%) |

**Expected New Records**: ~30,000 records  
**Additional Storage**: ~15 MB  
**Estimated Time**: 2-3 hours

---

## Ingestion Strategy

### Method 1: Quick Test (DRY RUN - RECOMMENDED FIRST)
```powershell
# Test first 10 companies to see what will happen
python scripts/ingestion/fill_data_gaps.py --dry-run --max-tickers 10
```

### Method 2: Small Batch Test (10 companies)
```powershell
# Actually ingest first 10 companies
python scripts/ingestion/fill_data_gaps.py --max-tickers 10 --batch-size 5
```

### Method 3: Full Ingestion (ALL 475 companies)
```powershell
# RECOMMENDED: Run the full automated script
.\run_data_ingestion.ps1
```

Or manually:
```powershell
python scripts/ingestion/fill_data_gaps.py `
    --target-years "2019,2020,2025" `
    --years-back 7 `
    --batch-size 10
```

---

## What the Script Does

1. **📊 Analysis Phase**
   - Identifies all tickers in your database
   - Determines which companies need historical data

2. **🚀 Ingestion Phase**
   - Fetches 7 years of data from SEC for each company
   - Processes in batches of 10 companies
   - Respects SEC rate limits (10 requests/second)
   - Retries failed requests up to 3 times

3. **🔄 Refresh Phase**
   - Recalculates all derived metrics
   - Updates KPI values
   - Refreshes metric snapshots

4. **📝 Reporting Phase**
   - Saves summary to `fill_gaps_summary.json`
   - Shows success/failure counts
   - Displays total records loaded

---

## Progress Tracking

The script will show real-time progress:

```
[15/48 - 31.3%] Processing: AAPL, MSFT, GOOGL, ...
   ✅ Loaded 234 records (Total: 3,456)

📊 Progress Report:
   Batches processed: 20/48
   Total records loaded: 8,234
   Successes: 192
   Failures: 8
```

---

## After Ingestion: Verification

### Step 1: Check Coverage
```powershell
python analyze_data_gaps.py
```

Expected output:
```
  2019: 475 companies (100.0%) 🟢
  2020: 475 companies (100.0%) 🟢
  2021: 475 companies (100.0%) 🟢
  2022: 475 companies (100.0%) 🟢
  2023: 475 companies (100.0%) 🟢
  2024: 475 companies (100.0%) 🟢
  2025: 475 companies (100.0%) 🟢
```

### Step 2: Check Row Counts
```powershell
python check_row_counts.py
```

Expected increase:
- `financial_facts`: 33,648 → ~63,000+ rows
- `metric_snapshots`: 319,842 → ~400,000+ rows
- `kpi_values`: 9,969 → ~20,000+ rows

---

## Troubleshooting

### Issue: Rate Limiting
**Symptom**: `429 Too Many Requests`  
**Solution**: The script automatically handles this with retries and backoff

### Issue: Timeout Errors
**Symptom**: `Connection timeout`  
**Solution**: 
- Reduce batch size: `--batch-size 5`
- The script will retry automatically

### Issue: Missing CIK for Ticker
**Symptom**: `Ticker XYZ not found in CIK mapping`  
**Solution**: Some tickers may not be in SEC database (delisted, non-US, etc.)
- Script will skip these automatically
- Check `fill_gaps_summary.json` for details

### Issue: Out of Memory
**Symptom**: Python crashes  
**Solution**: 
- Process in smaller batches: `--max-tickers 100`
- Run multiple times to complete all companies

---

## Command Reference

### Dry Run (Safe - No Changes)
```powershell
python scripts/ingestion/fill_data_gaps.py --dry-run
```

### Test First 50 Companies
```powershell
python scripts/ingestion/fill_data_gaps.py --max-tickers 50
```

### Custom Years
```powershell
python scripts/ingestion/fill_data_gaps.py --target-years "2018,2019,2020"
```

### Smaller Batches (Safer)
```powershell
python scripts/ingestion/fill_data_gaps.py --batch-size 5
```

### More History (10 years)
```powershell
python scripts/ingestion/fill_data_gaps.py --years-back 10
```

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Dry Run** | 1 second | Validate setup |
| **Small Test (10)** | 1-2 minutes | Test 10 companies |
| **Medium Test (50)** | 5-10 minutes | Test 50 companies |
| **Full Run (475)** | 2-3 hours | All companies |

---

## Success Criteria

✅ All years show 100% coverage  
✅ Database size increases by ~15 MB  
✅ Row counts increase by ~30,000 records  
✅ No fatal errors in `fill_gaps_summary.json`  
✅ Analytics engine refreshes successfully  

---

## Next Steps After Completion

1. ✅ Verify coverage with `analyze_data_gaps.py`
2. ✅ Test dashboard with historical data
3. ✅ Run analytics on complete dataset
4. ✅ Commit and push changes (new data won't be in git, but scripts will be)

---

## Notes

- **Safe**: Script includes dry-run mode for testing
- **Resumable**: Can stop and restart anytime
- **Rate Limited**: Respects SEC's 10 req/sec limit
- **Retries**: Automatically retries failed requests
- **Logging**: All activity logged to console and summary file

---

**Ready to Start?**

1. Run dry-run first: `python scripts/ingestion/fill_data_gaps.py --dry-run`
2. Test with 10 companies: `python scripts/ingestion/fill_data_gaps.py --max-tickers 10`
3. Run full ingestion: `.\run_data_ingestion.ps1`

🎯 **Goal**: Transform your dataset from 4 solid years to 7 solid years!

