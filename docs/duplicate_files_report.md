# Duplicate Files Report

## 🔍 **Files Found with Duplicate Names:**

### 1. **enhanced_ticker_resolver.py**
- `./core/enhanced_ticker_resolver.py`
- `./analysis/experiments/enhanced_ticker_resolver.py`

### 2. **ingest_companyfacts.py**
- `./scripts/ingestion/ingest_companyfacts.py`
- `./src/ingest_companyfacts.py`

### 3. **load_ticker_cik.py**
- `./scripts/ingestion/load_ticker_cik.py`
- `./src/load_ticker_cik.py`

### 4. **main.py**
- `./analysis/scripts/main.py`
- `./scripts/utility/main.py`

### 5. **test_ticker_resolution.py**
- `./core/test_ticker_resolution.py`
- `./tests/regression/test_ticker_resolution.py`

## 📋 **Recommendations:**

### **Option 1: Keep Organized Structure (Recommended)**
- Keep files in their proper directories based on purpose
- Remove duplicates from less organized locations

### **Option 2: Consolidate**
- Move all duplicates to a single location
- Update imports and references

## 🎯 **Suggested Actions:**

1. **Keep in organized directories:**
   - `./scripts/ingestion/` for ingestion scripts
   - `./tests/` for test files
   - `./core/` for core functionality

2. **Remove from scattered locations:**
   - Remove from `./src/` (should only contain package code)
   - Remove from `./analysis/experiments/` (experimental code)

3. **Update imports** if any files reference the removed duplicates

## ✅ **Status:**
- All chatbot scripts (`serve_chatbot.py`, `run_chatbot.py`) are now properly located in root directory
- No more duplicates for chatbot launchers
- Other duplicates identified and can be cleaned up
