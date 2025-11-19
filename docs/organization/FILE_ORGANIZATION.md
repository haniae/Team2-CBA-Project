# File Organization

This document describes the organization of project files.

## Directory Structure

### `/tests/`
Test files organized by category:

#### `/tests/sp1500/`
- `test_all_sp1500_companies.py` - Tests all S&P 1500 company name recognition
- `test_all_sp1500_tickers.py` - Tests all S&P 1500 ticker symbol recognition
- `test_sp1500_comprehensive.py` - Comprehensive S&P 1500 tests
- `test_sp1500_support.py` - S&P 1500 support verification

#### `/tests/metric_recognition/`
- `test_metric_edge_cases.py` - Edge cases for metric recognition
- `test_metric_patterns.py` - Metric pattern matching tests
- `test_metric_recognition.py` - Basic metric recognition tests
- `test_metric_spelling_comprehensive.py` - Comprehensive metric spelling tests
- `test_metric_variations.py` - Metric name variation tests
- `test_comprehensive_coverage.py` - Coverage tests for metrics
- `test_comprehensive_spelling.py` - Spelling mistake tests
- `test_spelling_mistakes.py` - Spelling mistake handling tests

#### `/tests/debug/`
- `debug_company_names.py` - Debug company name recognition
- `debug_failures.py` - Debug specific failures
- `debug_remaining_failures.py` - Debug remaining failures
- `analyze_company_name_failures.py` - Analyze company name failures
- `get_all_failures.py` - Get all failure cases
- `identify_all_failures.py` - Identify all failures
- `test_specific_failures.py` - Test specific failure cases

### `/scripts/`
Utility and setup scripts:

#### `/scripts/sp1500/`
- `setup_sp1500.py` - Set up S&P 1500 ticker list
- `setup_and_test_sp1500.py` - Setup and test S&P 1500
- `verify_sp1500_file.py` - Verify S&P 1500 file exists
- `verify_sp1500_setup.py` - Verify S&P 1500 setup
- `create_sp1500_file.py` - Create S&P 1500 file
- `complete_sp1500.py` - Complete S&P 1500 setup
- `find_and_test_sp1500.py` - Find and test S&P 1500 file
- `extract_tickers_from_db.py` - Extract tickers from database

### `/docs/`
Documentation files:

#### `/docs/sp1500/`
- `SP1500_FIXES_COMPLETE.md` - S&P 1500 fixes summary
- `SP1500_SETUP_COMPLETE.md` - S&P 1500 setup completion
- `SP1500_TESTING_INSTRUCTIONS.md` - Testing instructions
- `SP1500_SUPPORT_ANALYSIS.md` - Support analysis
- `SP1500_SUPPORT_STATUS.md` - Support status
- `ADD_SP1500_SUPPORT.md` - How to add S&P 1500 support

#### `/docs/improvements/`
- `COMPREHENSIVE_COVERAGE_REPORT.md` - Coverage report
- `COMPREHENSIVE_IMPROVEMENTS_COMPLETE.md` - Improvements summary
- `FINAL_IMPROVEMENTS_SUMMARY.md` - Final improvements summary
- `IMPROVEMENTS_TO_100_PERCENT.md` - Improvements to reach 100%

#### `/docs/guides/`
- `PROMPT_EXAMPLES_GUIDE.md` - Prompt examples guide
- `QUICK_PROMPT_REFERENCE.md` - Quick prompt reference

## Root Directory Files

Files that remain in the root directory:
- `README.md` - Main project README
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project configuration
- `LICENSE` - License file
- Test database files (`.db`, `.sqlite3`)
- Configuration files

## Running Tests

### S&P 1500 Tests
```bash
python tests/sp1500/test_all_sp1500_companies.py
python tests/sp1500/test_all_sp1500_tickers.py
```

### Metric Recognition Tests
```bash
python tests/metric_recognition/test_metric_variations.py
python tests/metric_recognition/test_spelling_mistakes.py
```

### Debug Scripts
```bash
python tests/debug/debug_remaining_failures.py
python tests/debug/analyze_company_name_failures.py
```

## Setup Scripts

### S&P 1500 Setup
```bash
python scripts/sp1500/setup_sp1500.py
python scripts/sp1500/verify_sp1500_setup.py
```

