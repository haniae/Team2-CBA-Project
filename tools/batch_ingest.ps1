# Batch ingest tickers into Postgres via ingest_companyfacts.py
# Usage: .\batch_ingest.ps1 -TickersFile .\data\sec_top100_tickers.txt -BatchSize 20 -PauseSeconds 2
param(
    [string]$TickersFile = "data\sec_top100_tickers.txt",
    [int]$BatchSize = 20,
    [int]$PauseSeconds = 2
)

if (-not (Test-Path $TickersFile)) {
    Write-Error "Tickers file not found: $TickersFile"
    exit 1
}

$tickers = Get-Content $TickersFile | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" } | ForEach-Object { $_.ToUpper() }
$total = $tickers.Count
Write-Host "Found $total tickers. Batch size: $BatchSize"

for ($i = 0; $i -lt $total; $i += $BatchSize) {
    $batch = $tickers[$i..([Math]::Min($i + $BatchSize - 1, $total - 1))] -join ","
    Write-Host "Processing batch $([int]($i / $BatchSize) + 1): $batch"
    $env:SEC_TICKERS = $batch
    # Run the ingest script from the repo root
    Push-Location $PSScriptRoot\..\
    try {
        python src\ingest_companyfacts.py
    } catch {
        Write-Error "Ingest script failed for batch starting at index $i"
    } finally {
        Pop-Location
    }
    Start-Sleep -Seconds $PauseSeconds
}

Write-Host "Batch ingestion finished."