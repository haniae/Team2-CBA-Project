# Private Company & Proprietary Data API Integration Guide

## Current State

The chatbot currently supports **public companies only** through:
- **SEC EDGAR API** - Public company filings (10-K, 10-Q, etc.)
- **Yahoo Finance API** - Market data for publicly traded stocks
- **Bloomberg API** (optional) - Professional market data

**Limitation**: Private companies don't file with the SEC, so they're not accessible through the current data sources.

---

## Solution: Custom API Integration for Private Companies

Yes, the chatbot **can be extended** to support private companies and proprietary data through custom API integrations. Here's how:

---

## Architecture Overview

The chatbot uses a **modular data source architecture** that makes it straightforward to add new data providers:

```
┌─────────────────────────────────────────┐
│         Chatbot Core                    │
│  (chatbot.py, analytics_engine.py)      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Data Source Clients                │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Edgar    │  │ Yahoo    │  │ Custom│ │
│  │ Client   │  │ Finance  │  │ API   │ │
│  └──────────┘  └──────────┘  └───────┘ │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Data Ingestion Pipeline            │
│  (data_ingestion.py)                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Database (SQLite/PostgreSQL)      │
└─────────────────────────────────────────┘
```

---

## Implementation Approach

### Option 1: Custom Data Source Client (Recommended)

Create a new client class similar to `EdgarClient` or `YahooFinanceClient` that:
1. Connects to your proprietary API
2. Fetches private company financial data
3. Normalizes data into the same format as public companies
4. Stores it in the same database schema

**Example Structure:**

```python
# src/finanlyzeos_chatbot/data_sources.py

class PrivateCompanyClient:
    """Client for proprietary private company data API."""
    
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()
    
    def fetch_company_financials(
        self,
        company_id: str,  # Your internal company identifier
        years: int = 10,
    ) -> List[FinancialFact]:
        """Fetch financial data for a private company."""
        # 1. Call your API
        response = self.session.get(
            f"{self.base_url}/companies/{company_id}/financials",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"years": years},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        
        # 2. Normalize to FinancialFact format
        facts = []
        for period_data in data.get("periods", []):
            # Map your API response to FinancialFact dataclass
            facts.append(
                FinancialFact(
                    cik="",  # Not applicable for private companies
                    ticker=company_id,  # Use your internal ID
                    company_name=data.get("name"),
                    metric="revenue",  # Map from your API
                    fiscal_year=period_data.get("year"),
                    fiscal_period=period_data.get("period"),
                    period=f"FY{period_data.get('year')}",
                    value=period_data.get("revenue"),
                    unit="USD",
                    source="private_api",  # Custom source identifier
                    source_filing=None,
                    period_start=_parse_datetime(period_data.get("start")),
                    period_end=_parse_datetime(period_data.get("end")),
                    adjusted=False,
                    adjustment_note=None,
                    ingested_at=datetime.now(timezone.utc),
                    raw=period_data,
                )
            )
        return facts
```

### Option 2: Extend Data Ingestion Pipeline

Modify `data_ingestion.py` to support private companies:

```python
# src/finanlyzeos_chatbot/data_ingestion.py

async def _fetch_private_company_data(
    company_id: str,
    years: int,
    private_client: PrivateCompanyClient,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Fetch data for a private company."""
    async with semaphore:
        try:
            facts = await asyncio.to_thread(
                private_client.fetch_company_financials,
                company_id,
                years,
            )
            return {
                "ticker": company_id,
                "facts": facts,
                "error": None,
            }
        except Exception as exc:
            return {
                "ticker": company_id,
                "facts": [],
                "error": str(exc),
            }

def ingest_private_companies(
    settings: Settings,
    company_ids: Sequence[str],
    *,
    years: int = 10,
    private_api_url: str,
    private_api_key: str,
) -> IngestionReport:
    """Ingest data for private companies from proprietary API."""
    private_client = PrivateCompanyClient(
        base_url=private_api_url,
        api_key=private_api_key,
    )
    
    # Use same ingestion logic as public companies
    # Store in same database tables
    # ...
```

### Option 3: Hybrid Approach (Public + Private)

Extend the chatbot to handle both public and private companies:

```python
# src/finanlyzeos_chatbot/chatbot.py

def _identify_company_type(self, identifier: str) -> str:
    """Determine if identifier is a public ticker or private company ID."""
    # Check if it's a known public ticker
    if identifier.upper() in self._ticker_index:
        return "public"
    # Check if it's a private company ID (from your database)
    if self._is_private_company(identifier):
        return "private"
    return "unknown"

def _fetch_company_data(self, identifier: str, company_type: str):
    """Route to appropriate data source based on company type."""
    if company_type == "public":
        return self._fetch_public_company_data(identifier)
    elif company_type == "private":
        return self._fetch_private_company_data(identifier)
    else:
        raise ValueError(f"Unknown company type: {company_type}")
```

---

## Database Schema Considerations

The existing database schema can handle private companies with minimal changes:

### Current Tables (Already Compatible):
- `financial_facts` - Stores financial metrics (works for private companies)
- `metric_snapshots` - Pre-calculated KPIs (works for private companies)
- `ticker_aliases` - Company name mappings (can include private companies)

### Optional Enhancements:
```sql
-- Add a flag to distinguish public vs private
ALTER TABLE ticker_aliases ADD COLUMN is_private BOOLEAN DEFAULT 0;

-- Or create a separate table for private company metadata
CREATE TABLE private_companies (
    company_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    api_source TEXT NOT NULL,
    last_synced_at TIMESTAMP,
    metadata JSON
);
```

---

## Configuration

Add settings for private company API:

```python
# src/finanlyzeos_chatbot/config.py

@dataclass(frozen=True)
class Settings:
    # ... existing fields ...
    
    # Private Company API Settings
    enable_private_companies: bool = False
    private_api_url: Optional[str] = None
    private_api_key: Optional[str] = None
    private_api_timeout: float = 30.0
```

Environment variables:
```bash
ENABLE_PRIVATE_COMPANIES=true
PRIVATE_API_URL=https://api.yourcompany.com/v1
PRIVATE_API_KEY=your_api_key_here
PRIVATE_API_TIMEOUT=30.0
```

---

## API Requirements

Your proprietary API should provide:

### Minimum Required Endpoints:

1. **Company Financials**
   ```
   GET /companies/{company_id}/financials
   Query params: years=10
   Response: {
     "company_id": "PRIV-001",
     "name": "Acme Corp",
     "periods": [
       {
         "year": 2023,
         "period": "FY",
         "start": "2023-01-01",
         "end": "2023-12-31",
         "revenue": 50000000,
         "net_income": 5000000,
         "assets": 100000000,
         # ... other metrics
       }
     ]
   }
   ```

2. **Company Metadata**
   ```
   GET /companies/{company_id}
   Response: {
     "company_id": "PRIV-001",
     "name": "Acme Corp",
     "industry": "Technology",
     "founded": "2010",
     # ... other metadata
   }
   ```

### Recommended Data Format:

- **Standardized Metrics**: Revenue, Net Income, EBITDA, Assets, Liabilities, etc.
- **Time Periods**: Fiscal years and quarters
- **Currency**: USD (or normalized to USD)
- **Timestamps**: ISO 8601 format

---

## Integration Steps

### Step 1: Create Custom Client
1. Add `PrivateCompanyClient` class to `data_sources.py`
2. Implement API authentication
3. Map API responses to `FinancialFact` format

### Step 2: Extend Ingestion
1. Add `ingest_private_companies()` function to `data_ingestion.py`
2. Support both public and private company ingestion
3. Use same database storage mechanism

### Step 3: Update Chatbot Logic
1. Modify `_CompanyNameIndex` to include private companies
2. Update company identification logic
3. Route queries to appropriate data source

### Step 4: Configure Settings
1. Add private API configuration to `Settings` class
2. Load from environment variables
3. Enable/disable via feature flag

### Step 5: Test Integration
1. Test with sample private company data
2. Verify data normalization
3. Test chatbot queries for private companies

---

## Example: Complete Integration

```python
# 1. Create client
private_client = PrivateCompanyClient(
    base_url=settings.private_api_url,
    api_key=settings.private_api_key,
)

# 2. Fetch data
company_id = "PRIV-001"
facts = private_client.fetch_company_financials(company_id, years=10)

# 3. Store in database (same as public companies)
for fact in facts:
    database.insert_financial_fact(settings.database_path, fact)

# 4. Query via chatbot
chatbot = FinanlyzeOSChatbot.create(settings)
response = chatbot.ask("What is PRIV-001's revenue for 2023?")
# Chatbot will use the same analytics engine and respond normally
```

---

## Benefits of This Approach

✅ **No Synthetic Data**: Uses real data from your proprietary API  
✅ **Same Interface**: Private companies work the same as public companies  
✅ **Unified Analytics**: Same KPI calculations and analytics engine  
✅ **Consistent Experience**: Users can't tell the difference  
✅ **Extensible**: Easy to add more private data sources  

---

## Security Considerations

1. **API Key Management**: Store keys in environment variables, not code
2. **Data Isolation**: Consider separate database or schema for private data
3. **Access Control**: Implement user permissions for private company access
4. **Audit Trail**: Log all private company data access
5. **Encryption**: Encrypt sensitive data at rest and in transit

---

## Alternative: Direct Database Integration

If you already have a database with private company data, you can:

1. **Direct Database Connection**: Connect to your existing database
2. **ETL Pipeline**: Extract, transform, and load into chatbot database
3. **Scheduled Sync**: Keep data synchronized automatically

This avoids API calls but requires database access and schema mapping.

---

## Next Steps

1. **Review Your API**: Ensure it provides the required financial data
2. **Design Data Mapping**: Map your API format to `FinancialFact` structure
3. **Implement Client**: Create `PrivateCompanyClient` class
4. **Test Integration**: Start with one private company
5. **Scale Up**: Add more companies once verified

---

## Questions to Consider

1. **What data do you have?** Financial statements? Metrics? Both?
2. **What's your API format?** REST? GraphQL? Database?
3. **How many private companies?** Affects ingestion strategy
4. **Update frequency?** Real-time? Daily? Monthly?
5. **Access control?** Who can query which companies?

---

## Support

For implementation help, refer to:
- `src/finanlyzeos_chatbot/data_sources.py` - Example client implementations
- `src/finanlyzeos_chatbot/data_ingestion.py` - Ingestion pipeline
- `src/finanlyzeos_chatbot/chatbot.py` - Company identification logic

