# Tests

This directory contains all test files and verification scripts.

## 📁 Directory Structure

```
tests/
├── README.md                          # This file
├── outputs/                           # Test output files (gitignored)
│   ├── *.txt                         # Test result files
│   ├── *.json                        # Test payload files
│   └── *.log                         # Test logs
├── regression/                        # Regression tests
│   └── *.py
└── *.py                              # Test scripts
```

## 🧪 Test Categories

### Comprehensive Tests
- **test_all_sp500_dashboards.py** - Tests all 476 SP500 companies
- **test_sample_companies.py** - Quick test on 10 sample companies
- **test_single_company.py** - Detailed test on single company (Apple)

### Feature Tests
- **test_new_analytics.py** - Analytics engine tests
- **test_chatbot_sec_fix.py** - SEC integration tests
- **test_sec_api_fix.py** - SEC API tests
- **test_dashboard_flow.py** - Dashboard workflow tests
- **test_fixes.py** - General fixes validation

### Verification Scripts
- **verify_metrics.py** - Metric validation
- **verify_new_data.py** - Data validation

### UI Tests
- **test_dashboard_sources.html** - Dashboard sources display test

### Existing Tests
- **test_analytics_engine.py** - Analytics engine unit tests
- **test_analytics.py** - Analytics module tests
- **test_cli_tables.py** - CLI table rendering tests
- **test_data_ingestion.py** - Data ingestion tests
- **test_database.py** - Database tests

## 🚀 Running Tests

### Quick Validation (1 company, ~10 seconds)
```bash
python tests/test_single_company.py
```

### Sample Test (10 companies, ~2 minutes)
```bash
python tests/test_sample_companies.py
```

### Full SP500 Test (476 companies, ~30-60 minutes)
```bash
python tests/test_all_sp500_dashboards.py
```

### Specific Feature Tests
```bash
python tests/test_new_analytics.py
python tests/test_chatbot_sec_fix.py
python tests/verify_metrics.py
```

## 📊 Test Output

Test outputs are saved to `tests/outputs/` directory:
- `sp500_dashboard_test_results.txt` - Full test results
- `test_single_company_payload.json` - Sample payload for inspection
- `*_test_output.txt` - Various test logs

**Note:** Output files are gitignored to keep the repository clean.

## ✅ Test Coverage

### Dashboard & Sources
- ✅ 100% source attribution validation
- ✅ SEC URL generation verification
- ✅ Calculation formula display
- ✅ Complete financial data validation

### Companies Tested
- ✅ Apple Inc. (AAPL)
- ✅ Microsoft (MSFT)
- ✅ Alphabet (GOOGL)
- ✅ Amazon (AMZN)
- ✅ Tesla (TSLA)
- ✅ JPMorgan Chase (JPM)
- ✅ Visa (V)
- ✅ Walmart (WMT)
- ✅ Procter & Gamble (PG)
- ✅ All 476 SP500 companies (comprehensive test)

## 🔍 Regression Tests

Located in `tests/regression/`:
- Multi-ticker regression tests
- Historical data validation
- System stability tests

## 📝 Notes

- Test outputs are automatically generated in `outputs/` directory
- Large test result files are gitignored
- Keep test scripts updated with latest features
- Add new tests for new features

