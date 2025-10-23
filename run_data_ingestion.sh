#!/bin/bash
# Comprehensive data ingestion to fill all gaps

echo "=========================================="
echo "COMPREHENSIVE DATA INGESTION PLAN"
echo "=========================================="
echo ""
echo "This will fill data gaps for years 2019-2025"
echo "Estimated time: ~2-3 hours"
echo ""

# Phase 1: Fill gaps for all years
echo "📊 Phase 1: Ingesting all tickers with 7 years of history..."
python scripts/ingestion/fill_data_gaps.py \
    --target-years "2019,2020,2025" \
    --years-back 7 \
    --batch-size 10

# Phase 2: Verify coverage
echo ""
echo "📊 Phase 2: Verifying data coverage..."
python analyze_data_gaps.py

# Phase 3: Check row counts
echo ""
echo "📊 Phase 3: Checking final row counts..."
python check_row_counts.py

echo ""
echo "✅ Ingestion complete!"
echo "📊 Check 'fill_gaps_summary.json' for details"

