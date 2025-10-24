# Team Setup Guide - S&P 500 Data Ingestion

Complete guide for team members to set up and populate the BenchmarkOS database with 15 years of S&P 500 data.

## 🚀 Quick Start (3-5 Hours Total)

### Prerequisites

1. **Python 3.8+** installed
2. **Git** installed
3. **Internet connection** (for downloading SEC data)

### Step 1: Clone and Setup (5 minutes)

```bash
# Clone the repository
git clone <your-repo-url>
cd Team2-CBA-Project

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Ingest S&P 500 Financial Data (2-3 hours)

```bash
# Run the main ingestion script
python scripts/ingestion/ingest_sp500_15years.py
```

**What this does:**
- Downloads 15 years of financial data for all 500+ S&P 500 companies
- Pulls data from SEC EDGAR database
- Processes ~50,000+ financial facts
- Automatically saves progress (can resume if interrupted)
- Respects SEC API rate limits

**Progress tracking:**
- The script shows real-time progress
- Creates `.ingestion_progress.json` for resume capability
- Processes 20 companies at a time
- Sleeps 2 seconds between batches

### Step 3: Load Historical Prices (1-2 hours)

```bash
# Run the price loading script
python scripts/ingestion/load_historical_prices_15years.py
```

**What this does:**
- Downloads 15 years of daily stock prices
- Uses Yahoo Finance as data source
- Loads closing prices, adjusted prices, and volume
- Saves latest quotes to database
- Rate limited to respect API guidelines

### Step 4: Verify Installation

```bash
# Check database status
python check_database_simple.py

# Check detailed ingestion progress
python check_ingestion_status.py
```

## 📊 Expected Results

After successful completion, you should have:

- ✅ **500+ S&P 500 companies** in the database
- ✅ **15 years** of financial data (2010-2025)
- ✅ **50,000+** financial facts covering:
  - Income statement metrics (revenue, net income, operating income)
  - Balance sheet metrics (assets, liabilities, equity)
  - Cash flow metrics (operating cash flow, free cash flow, CapEx)
  - Key ratios and per-share data
- ✅ **Historical price data** for all tickers
- ✅ **Market quotes** with latest prices

## ⏱️ Time Estimates

| Task | Time | Can Run Overnight |
|------|------|-------------------|
| Repository setup | 5 min | No |
| Financial data ingestion | 2-3 hours | Yes ✅ |
| Historical prices | 1-2 hours | Yes ✅ |
| Verification | 1 min | No |
| **Total** | **3-5 hours** | **Yes** |

## 🔧 Features

### Resume Capability

If ingestion is interrupted (network issues, computer shutdown, etc.):

```bash
# Simply run the same command again
python scripts/ingestion/ingest_sp500_15years.py
```

The script will:
- ✅ Load progress from `.ingestion_progress.json`
- ✅ Skip already-completed tickers
- ✅ Continue from where it left off
- ✅ Show remaining tickers

### Progress Tracking

Check progress at any time:

```bash
# Detailed status report
python check_ingestion_status.py
```

Output includes:
- Overall progress percentage
- Progress bar visualization
- Completed vs remaining tickers
- Data quality metrics
- Next steps

### Database Analysis

Comprehensive database analysis:

```bash
# Full database report
python check_database_simple.py
```

Output includes:
- Row counts for all tables
- Ticker coverage statistics
- Data quality metrics
- Metric distribution
- Year coverage
- Recent activity
- Sample data

## 📁 File Structure

### Core Ingestion Scripts

```
scripts/ingestion/
├── ingest_sp500_15years.py          # Main S&P 500 ingestion (15 years)
├── load_historical_prices_15years.py # Historical price data loader
└── ingest_universe.py                # Flexible universe ingestion (fixed import paths)
```

### Monitoring Tools

```
.
├── check_ingestion_status.py         # Progress tracking and resume info
└── check_database_simple.py          # Database analysis and status
```

### Configuration Files

```
.
├── .ingestion_progress.json          # Auto-generated progress tracking
└── pyproject.toml                     # Project configuration
```

## 🛠️ Advanced Usage

### Custom Time Period

If you want a different time period, modify the scripts:

```python
# In ingest_sp500_15years.py
years = 10  # Change from 15 to 10 years
```

### Selective Ingestion

To ingest specific tickers only:

```bash
# Use the flexible universe script
python scripts/ingestion/ingest_universe.py \
  --universe-file my_tickers.txt \
  --years 15 \
  --resume
```

### Parallel Processing

For faster ingestion, adjust chunk size:

```python
# In ingest_sp500_15years.py
chunk_size = 30  # Process more tickers at once (default: 20)
sleep_seconds = 1.5  # Reduce sleep time (careful with rate limits!)
```

## 🔍 Troubleshooting

### Issue: Import Errors

**Problem:** `ModuleNotFoundError: No module named 'benchmarkos_chatbot'`

**Solution:**
```bash
# Make sure you're in the project root
cd Team2-CBA-Project

# Reinstall dependencies
pip install -e .
```

### Issue: SEC API Rate Limiting

**Problem:** "Too many requests" or 429 errors

**Solution:** The scripts automatically handle rate limiting, but if needed:
```python
# Increase sleep time in ingest_sp500_15years.py
sleep_seconds = 3.0  # Increase from 2.0 to 3.0
```

### Issue: Database Locked

**Problem:** "Database is locked" error

**Solution:**
```bash
# Close any applications using the database
# Stop the chatbot if it's running
# Then restart ingestion
python scripts/ingestion/ingest_sp500_15years.py
```

### Issue: Network Interruption

**Problem:** Script stops due to network issues

**Solution:**
```bash
# The script automatically saves progress
# Just run it again to resume
python scripts/ingestion/ingest_sp500_15years.py
```

### Issue: Incomplete Data

**Problem:** Some tickers have missing data

**Solution:** This is normal - not all companies have complete data:
```bash
# Check which tickers failed
python check_ingestion_status.py

# Review specific ticker status
python check_database_simple.py
```

## 📈 Data Quality

### What Data is Collected

**Financial Metrics:**
- Revenue (multiple XBRL tags normalized)
- Net Income
- Operating Income  
- Gross Profit
- Total Assets
- Total Liabilities
- Shareholders' Equity
- Current Assets/Liabilities
- Cash and Cash Equivalents
- Operating Cash Flow
- Free Cash Flow (calculated)
- Capital Expenditures
- Depreciation & Amortization
- EBIT
- Long-term/Short-term Debt
- Shares Outstanding
- Dividends

**Time Coverage:**
- 15 years of historical data
- Annual (10-K) filings
- Quarterly (10-Q) filings (where available)

**Price Data:**
- Daily closing prices
- Adjusted prices (for splits/dividends)
- Trading volume
- 15 years of history

### Data Normalization

The system automatically:
- ✅ Normalizes different XBRL tags to standard metrics
- ✅ Handles different accounting standards
- ✅ Calculates derived metrics (e.g., Free Cash Flow)
- ✅ Stores data in consistent format
- ✅ Tracks data provenance and sources

## 🎯 Next Steps After Setup

### 1. Run the Chatbot

```bash
python run_chatbot.py
```

Test with queries like:
- "Show me Apple's revenue trends"
- "Compare Microsoft and Google's profit margins"
- "What's Tesla's free cash flow?"

### 2. Explore the Web UI

```bash
python serve_chatbot.py
```

Then open: http://localhost:8000

### 3. Run Analytics

```bash
python -c "from benchmarkos_chatbot import AnalyticsEngine, load_settings; \
           engine = AnalyticsEngine(load_settings()); \
           print(engine.analyze_company('AAPL'))"
```

### 4. Export Data

Export data for external analysis:
```python
from benchmarkos_chatbot import database, load_settings

settings = load_settings()
facts = database.fetch_financial_facts(settings.database_path, "AAPL")
# Process as needed
```

## 🔄 Keeping Data Updated

### Refresh Financial Data

To update with latest filings:
```bash
python scripts/ingestion/ingest_sp500_15years.py
```

The system will:
- Check for new filings
- Update existing records
- Add new data points

### Refresh Price Data

To update with latest prices:
```bash
python scripts/ingestion/load_historical_prices_15years.py
```

### Automated Updates

Set up a cron job (Linux/Mac) or Task Scheduler (Windows):

```bash
# Daily price updates
0 18 * * * cd /path/to/project && python scripts/ingestion/load_historical_prices_15years.py

# Weekly financial data updates (Sundays)
0 2 * * 0 cd /path/to/project && python scripts/ingestion/ingest_sp500_15years.py
```

## 📊 Performance Tips

### Optimize Ingestion Speed

1. **Adjust chunk size** (default: 20)
   - Larger chunks = faster, but more memory
   - Smaller chunks = slower, but safer

2. **Reduce sleep time** (default: 2s)
   - Faster ingestion, but risk rate limiting
   - Only reduce if you're not hitting limits

3. **Run overnight**
   - Let it run unattended
   - Check progress in the morning

### Database Optimization

After initial ingestion:
```bash
# Analyze and optimize database
python -c "from benchmarkos_chatbot import database, load_settings; \
           db = load_settings().database_path; \
           import sqlite3; \
           conn = sqlite3.connect(db); \
           conn.execute('VACUUM'); \
           conn.execute('ANALYZE')"
```

## 🤝 Team Coordination

### Multiple Team Members

If multiple people are ingesting data:

1. **Use separate branches:**
   ```bash
   git checkout -b ingestion-yourname
   ```

2. **Don't commit the progress file:**
   ```bash
   # Already in .gitignore
   .ingestion_progress.json
   ```

3. **Commit the database:**
   ```bash
   git add data/sqlite/benchmarkos_chatbot.sqlite3
   git commit -m "Add S&P 500 data ingestion"
   git push origin ingestion-yourname
   ```

### Shared Database

One person can:
1. Run full ingestion
2. Commit the database to git
3. Other team members pull the database

```bash
# Team member 2-N:
git pull origin main
# Database is ready to use!
```

## 📚 Additional Resources

### Documentation

- [Architecture Guide](architecture.md) - System architecture
- [Data Ingestion Plan](DATA_INGESTION_PLAN.md) - Detailed ingestion strategy
- [API Documentation](../README.md) - Full API reference

### Scripts Reference

- `ingest_sp500_15years.py` - Main ingestion script
- `load_historical_prices_15years.py` - Price data loader
- `ingest_universe.py` - Flexible universe ingestion
- `check_ingestion_status.py` - Progress tracker
- `check_database_simple.py` - Database analyzer

## ❓ FAQ

**Q: How long does ingestion take?**  
A: 2-3 hours for financial data, 1-2 hours for prices. Can run overnight.

**Q: Can I pause and resume?**  
A: Yes! Progress is automatically saved. Just run the script again.

**Q: What if some tickers fail?**  
A: Normal. Not all companies have complete data. Check with `check_ingestion_status.py`.

**Q: How much disk space needed?**  
A: ~500MB-1GB for complete S&P 500 dataset.

**Q: Can I ingest other stock indices?**  
A: Yes! Create a ticker list file and use `ingest_universe.py --universe-file`.

**Q: How do I update data later?**  
A: Run the same ingestion scripts. They'll update existing records and add new ones.

**Q: What if I get rate limited?**  
A: The scripts handle this automatically. If needed, increase `sleep_seconds`.

**Q: Can I run this in the cloud?**  
A: Yes! Works on any platform with Python 3.8+. Tested on AWS, Azure, GCP.

## ✅ Success Checklist

After setup, verify everything is working:

- [ ] Repository cloned
- [ ] Dependencies installed
- [ ] Financial data ingestion completed (500+ tickers)
- [ ] Historical prices loaded
- [ ] `check_database_simple.py` shows complete data
- [ ] `check_ingestion_status.py` shows 100% progress
- [ ] Chatbot runs successfully
- [ ] Can query company data

Congratulations! Your BenchmarkOS database is ready! 🎉

## 🆘 Getting Help

If you encounter issues:

1. **Check status:** `python check_ingestion_status.py`
2. **Review database:** `python check_database_simple.py`
3. **Check logs:** Look for error messages in terminal output
4. **Consult documentation:** Review guides in `docs/` folder
5. **Ask team:** Post in team chat with error details

## 🔐 Best Practices

### Security

- ✅ Never commit API keys or credentials
- ✅ Use environment variables for sensitive config
- ✅ Don't push large databases to public repos

### Performance

- ✅ Run ingestion during off-hours
- ✅ Monitor disk space
- ✅ Optimize database periodically
- ✅ Use SSD for database storage if possible

### Maintenance

- ✅ Update data weekly or monthly
- ✅ Backup database before major updates
- ✅ Clean up old progress files
- ✅ Monitor data quality metrics

---

**Last Updated:** 2025-01-24  
**Version:** 1.0  
**Maintainer:** Team 2 CBA Project
