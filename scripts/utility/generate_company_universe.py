"""Generate company_universe.json with all companies from database."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Import sector map from sector_analytics
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent / 'src'))
    from finanlyzeos_chatbot.sector_analytics import SECTOR_MAP
except ImportError:
    # Fallback if import fails
    SECTOR_MAP = {}

# Try to import yfinance for fetching sectors
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️  yfinance not available. Install with: pip install yfinance")
    print("   Will skip Yahoo Finance sector fetching.\n")

# Use the correct database path
db_path = Path(r'C:\Users\Hania\Documents\GitHub\Project\benchmarkos_chatbot.sqlite3')

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    exit(1)

print("📊 Generating company_universe.json from database...")
print(f"Database: {db_path}")
print(f"Size: {db_path.stat().st_size / (1024*1024):.2f} MB\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all companies with their data
print("Fetching company data...")
companies_query = """
    SELECT DISTINCT 
        f.ticker,
        COALESCE(f.company_name, f.ticker) as company_name,
        MIN(f.fiscal_year) as min_year,
        MAX(f.fiscal_year) as max_year,
        COUNT(DISTINCT f.fiscal_year) as years_count,
        COUNT(DISTINCT f.metric) as metrics_count,
        COUNT(*) as total_facts
    FROM financial_facts f
    WHERE f.ticker IS NOT NULL
    GROUP BY f.ticker, f.company_name
    ORDER BY f.ticker
"""

companies_data = cursor.execute(companies_query).fetchall()

print(f"Found {len(companies_data)} companies\n")

# Get latest filing date for each company
print("Fetching latest filing dates...")
latest_filings = {}
for ticker, *_ in companies_data:
    result = cursor.execute("""
        SELECT MAX(period_end) 
        FROM financial_facts 
        WHERE ticker = ? AND period_end IS NOT NULL
    """, (ticker,)).fetchone()
    if result and result[0]:
        latest_filings[ticker] = result[0]

# Get market cap from multiple sources
print("Fetching market cap data...")
market_caps = {}
# First try metric_snapshots
for ticker, *_ in companies_data:
    result = cursor.execute("""
        SELECT value 
        FROM metric_snapshots 
        WHERE ticker = ? AND metric = 'market_cap' 
        ORDER BY updated_at DESC 
        LIMIT 1
    """, (ticker,)).fetchone()
    if result and result[0]:
        try:
            market_caps[ticker] = float(result[0])
        except (ValueError, TypeError):
            pass

# If not found, try calculating from price * shares_outstanding
for ticker, *_ in companies_data:
    if ticker in market_caps:
        continue
    # Get latest price
    price_result = cursor.execute("""
        SELECT price 
        FROM market_quotes 
        WHERE ticker = ? 
        ORDER BY quote_time DESC 
        LIMIT 1
    """, (ticker,)).fetchone()
    
    if price_result and price_result[0]:
        price = float(price_result[0])
        # Get shares outstanding from financial_facts or metric_snapshots
        shares_result = cursor.execute("""
            SELECT value 
            FROM metric_snapshots 
            WHERE ticker = ? AND metric = 'shares_outstanding' 
            ORDER BY updated_at DESC 
            LIMIT 1
        """, (ticker,)).fetchone()
        
        if not shares_result or not shares_result[0]:
            # Try financial_facts
            shares_result = cursor.execute("""
                SELECT value 
                FROM financial_facts 
                WHERE ticker = ? AND (metric = 'shares_outstanding' OR metric LIKE '%shares%outstanding%')
                ORDER BY fiscal_year DESC 
                LIMIT 1
            """, (ticker,)).fetchone()
        
        if shares_result and shares_result[0]:
            try:
                shares = float(shares_result[0])
                market_caps[ticker] = price * shares
            except (ValueError, TypeError):
                pass

# Fetch market cap from Yahoo Finance for remaining companies
if YFINANCE_AVAILABLE:
    missing_mcap_tickers = [ticker for ticker, *_ in companies_data if ticker not in market_caps]
    if missing_mcap_tickers:
        print(f"Fetching market cap from Yahoo Finance for {len(missing_mcap_tickers)} companies...")
        
        fetched_mcap_count = 0
        import time
        from yfinance.exceptions import YFRateLimitError
        
        for i, ticker in enumerate(missing_mcap_tickers, 1):
            if i % 50 == 0:
                print(f"  Market cap progress: {i}/{len(missing_mcap_tickers)} ({i/len(missing_mcap_tickers)*100:.1f}%) - Fetched: {fetched_mcap_count}")
            
            # Retry logic for rate limits
            max_retries = 3
            retry_delay = 2.0
            success = False
            
            for attempt in range(max_retries):
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # Try marketCap field (in USD)
                    mcap = info.get('marketCap') or info.get('enterpriseValue')
                    
                    if mcap and isinstance(mcap, (int, float)) and mcap > 0:
                        market_caps[ticker] = float(mcap)
                        fetched_mcap_count += 1
                        success = True
                        break
                    elif not info or len(info) == 0:
                        # Ticker might not exist or be delisted
                        break
                        
                except YFRateLimitError:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"    Rate limited, waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                    else:
                        print(f"    Rate limited for {ticker}, skipping...")
                        break
                except Exception as e:
                    # Log first few errors for debugging
                    if fetched_mcap_count < 3 and attempt == 0:
                        print(f"    Warning: {ticker} - {str(e)[:50]}")
                    break
            
            # Rate limiting - be more conservative
            time.sleep(0.5)  # Always wait between requests
            if i % 20 == 0:
                time.sleep(2.0)  # Longer pause every 20 requests
        
        print(f"✅ Fetched market cap for {fetched_mcap_count} companies from Yahoo Finance\n")

# Get sector information from multiple sources
print("Fetching sector data...")
sectors = {}
# First, use the sector map from sector_analytics (most reliable)
for ticker, *_ in companies_data:
    if ticker in SECTOR_MAP:
        sectors[ticker] = SECTOR_MAP[ticker]
        continue

# For companies not in the map, try database sources
for ticker, *_ in companies_data:
    if ticker in sectors:
        continue
    
    # Try sector_code from financial_facts (might be numeric, need to map)
    result = cursor.execute("""
        SELECT value 
        FROM financial_facts 
        WHERE ticker = ? AND metric = 'sector_code'
        LIMIT 1
    """, (ticker,)).fetchone()
    if result and result[0]:
        # Sector codes might be numeric, try to map them
        sector_code_val = result[0]
        # Handle both string and numeric codes
        if isinstance(sector_code_val, (int, float)):
            sector_code = str(int(sector_code_val))
        else:
            sector_code = str(sector_code_val).split('.')[0]  # Remove decimal if present
        
        # Common GICS sector code mappings (if numeric)
        sector_code_map = {
            "10": "Energy", "15": "Materials", "20": "Industrials",
            "25": "Consumer Discretionary", "30": "Consumer Staples",
            "35": "Health Care", "40": "Financials", "45": "Information Technology",
            "50": "Communication Services", "55": "Utilities", "60": "Real Estate"
        }
        if sector_code in sector_code_map:
            sectors[ticker] = sector_code_map[sector_code]
        else:
            sectors[ticker] = sector_code  # Use as-is if not numeric
        continue
    
    # Try other sector-related metrics
    result = cursor.execute("""
        SELECT value 
        FROM financial_facts 
        WHERE ticker = ? AND (metric LIKE '%sector%' OR metric LIKE '%industry%' OR metric LIKE '%GICS%')
        LIMIT 1
    """, (ticker,)).fetchone()
    if result and result[0]:
        sectors[ticker] = str(result[0])

conn.close()

# Fetch sectors from Yahoo Finance for remaining uncategorised companies
if YFINANCE_AVAILABLE:
    uncategorised_tickers = [ticker for ticker, *_ in companies_data if ticker not in sectors]
    if uncategorised_tickers:
        print(f"Fetching sectors from Yahoo Finance for {len(uncategorised_tickers)} companies...")
        
        # Yahoo Finance sector name mapping to our standard names
        yahoo_sector_map = {
            "Basic Materials": "Materials",
            "Financial Services": "Financials",
            "Healthcare": "Healthcare",
            "Consumer Cyclical": "Consumer Discretionary",
            "Consumer Defensive": "Consumer Staples",
            "Technology": "Technology",
            "Communication Services": "Communication Services",
            "Utilities": "Utilities",
            "Real Estate": "Real Estate",
            "Energy": "Energy",
            "Industrials": "Industrials"
        }
        
        fetched_count = 0
        import time
        from yfinance.exceptions import YFRateLimitError
        
        for i, ticker in enumerate(uncategorised_tickers, 1):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(uncategorised_tickers)} ({i/len(uncategorised_tickers)*100:.1f}%) - Fetched: {fetched_count}")
            
            # Retry logic for rate limits
            max_retries = 3
            retry_delay = 2.0
            success = False
            
            for attempt in range(max_retries):
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    # Check if info is valid (not empty dict)
                    if not info or len(info) == 0:
                        break
                    
                    # Try multiple fields
                    sector = info.get('sector') or info.get('gicsSector') or info.get('industry')
                    
                    if sector and sector.strip():
                        # Normalize sector name
                        sector_normalized = yahoo_sector_map.get(sector, sector)
                        sectors[ticker] = sector_normalized
                        fetched_count += 1
                        success = True
                        break
                        
                except YFRateLimitError:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"    Rate limited, waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                    else:
                        print(f"    Rate limited for {ticker}, skipping...")
                        break
                except Exception as e:
                    # Log first few errors for debugging
                    if fetched_count < 3 and attempt == 0:
                        print(f"    Warning: {ticker} - {str(e)[:50]}")
                    break
            
            # Rate limiting - be more conservative
            time.sleep(0.5)  # Always wait between requests
            if i % 20 == 0:
                time.sleep(2.0)  # Longer pause every 20 requests
        
        print(f"✅ Fetched sectors for {fetched_count} companies from Yahoo Finance\n")

# Build company universe JSON
print("\nBuilding company universe JSON...")
universe = []

for row in companies_data:
    ticker, company_name, min_year, max_year, years_count, metrics_count, total_facts = row
    
    # Determine coverage - realistic thresholds based on actual data distribution
    # Complete: Good historical coverage with comprehensive metrics (5+ years, 12+ metrics)
    if years_count >= 5 and metrics_count >= 12:
        coverage = "complete"
    # Partial: Some data but could use more years or metrics (2+ years, 6+ metrics)
    elif years_count >= 2 and metrics_count >= 6:
        coverage = "partial"
    # Missing: Very little data or no data
    else:
        coverage = "missing"
    
    # Get market cap
    market_cap = market_caps.get(ticker, None)
    if market_cap:
        if market_cap >= 1_000_000_000_000:
            market_cap_display = f"${market_cap / 1_000_000_000_000:.2f}T"
        elif market_cap >= 1_000_000_000:
            market_cap_display = f"${market_cap / 1_000_000_000:.2f}B"
        elif market_cap >= 1_000_000:
            market_cap_display = f"${market_cap / 1_000_000:.2f}M"
        else:
            market_cap_display = f"${market_cap:,.0f}"
    else:
        market_cap_display = None
    
    # Get latest filing
    latest_filing = latest_filings.get(ticker, None)
    if latest_filing:
        # Try to parse and format
        try:
            if isinstance(latest_filing, str):
                # Parse ISO format
                dt = datetime.fromisoformat(latest_filing.replace('Z', '+00:00'))
                latest_filing = dt.isoformat()
        except:
            pass
    
    # Get sector
    sector = sectors.get(ticker, "Uncategorised")
    
    universe.append({
        "company": company_name or ticker,
        "ticker": ticker,
        "sector": sector,
        "sub_industry": None,  # Can be enhanced later
        "hq": None,  # Can be enhanced later
        "latest_filing": latest_filing,
        "market_cap": market_cap,
        "market_cap_display": market_cap_display,
        "coverage": coverage,
        "years_count": years_count,
        "metrics_count": metrics_count,
        "total_facts": total_facts
    })

# Sort by ticker
universe.sort(key=lambda x: x['ticker'])

# Save to both locations
output_paths = [
    Path('webui/data/company_universe.json'),
    Path('src/finanlyzeos_chatbot/static/data/company_universe.json'),
    Path('webui/static/data/company_universe.json')  # If this directory exists
]

print(f"\n✅ Generated {len(universe)} companies")
print(f"   Complete coverage: {sum(1 for c in universe if c['coverage'] == 'complete')}")
print(f"   Partial coverage: {sum(1 for c in universe if c['coverage'] == 'partial')}")
print(f"   Missing coverage: {sum(1 for c in universe if c['coverage'] == 'missing')}")

for output_path in output_paths:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(universe, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Saved to: {output_path}")

print(f"\n📊 Summary:")
print(f"   Total companies: {len(universe)}")
print(f"   Companies with market cap: {sum(1 for c in universe if c['market_cap'])}")
print(f"   Companies with latest filing: {sum(1 for c in universe if c['latest_filing'])}")
print(f"\n🎉 Company universe generated successfully!")

