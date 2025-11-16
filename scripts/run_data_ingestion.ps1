# PowerShell script for comprehensive data ingestion

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "COMPREHENSIVE DATA INGESTION PLAN" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will fill data gaps for years 2019-2025"
Write-Host "Estimated time: ~2-3 hours"
Write-Host ""

# Phase 1: Fill gaps for all years
Write-Host "📊 Phase 1: Ingesting all tickers with 7 years of history..." -ForegroundColor Yellow
python scripts/ingestion/fill_data_gaps.py `
    --target-years "2019,2020,2025" `
    --years-back 7 `
    --batch-size 10

# Phase 2: Verify coverage
Write-Host ""
Write-Host "📊 Phase 2: Verifying data coverage..." -ForegroundColor Yellow
python analyze_data_gaps.py

# Phase 3: Check row counts
Write-Host ""
Write-Host "📊 Phase 3: Checking final row counts..." -ForegroundColor Yellow
python check_row_counts.py

Write-Host ""
Write-Host "✅ Ingestion complete!" -ForegroundColor Green
Write-Host "📊 Check 'fill_gaps_summary.json' for details"

