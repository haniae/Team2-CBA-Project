# Team Setup Guide - S&P 500 Data Ingestion

## 🚀 Quick Start for Team Members

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd Team2-CBA-Project-1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Ingest S&P 500 Data (15 years)
```bash
# This will take ~2-3 hours
python ingest_sp500_15years.py
```

### Step 4: Load Historical Prices
```bash
# This will take ~1-2 hours  
python load_historical_prices_15years.py
```

### Step 5: Check Results
```bash
python check_database_simple.py
```

## 📊 Expected Results
- ✅ 500 S&P 500 companies
- ✅ 15 years of financial data
- ✅ Historical price data
- ✅ Market quotes
- ✅ ~50,000+ financial facts

## ⏱️ Total Time: ~3-5 hours
- Financial data: 2-3 hours
- Historical prices: 1-2 hours
- Can run overnight

## 🔧 Troubleshooting
- If interrupted, just run the same command again (resume capability)
- Check progress with: `python check_database_simple.py`
- Monitor with: `python check_ingestion_status.py`
