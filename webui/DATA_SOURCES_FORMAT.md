# Data Sources - Accurate Citation Format

**Purpose:** Use the exact same citation format as the audit drawer for accurate SEC filing links

---

## 📋 Required Format

The `sources` array should use **the exact same structure** as the `citations` format in the main app (see `app.js` lines 3246-3273, 3521-3550).

### **Complete Format:**

```javascript
{
  sources: [
    {
      ticker: "AAPL",               // Company ticker symbol
      label: "Revenue",             // Metric name/label
      period: "FY2023",             // Time period (e.g., FY2023, Q4 2023)
      value: 574800,                // Raw numeric value (optional)
      formatted_value: "$574.8B",   // Pre-formatted display value (optional)
      source: "SEC 10-K 2023",      // Source description (optional)
      description: "Annual report...", // Additional context (optional)
      urls: {
        detail: "https://www.sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-23-000077&xbrl_type=v",
        interactive: "https://www.sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-23-000077&xbrl_type=v"
      }
    },
    // ... more sources
  ]
}
```

---

## ⚠️ Critical: Use Real URLs

### **❌ DON'T Generate Fake URLs:**
```javascript
// BAD - Don't do this
url: "https://www.sec.gov/edgar/search/"  // Generic search page

// BAD - Don't do this
url: generateSourceURL(sourceText)  // Auto-generated guess
```

### **✅ DO Use Actual Filing URLs:**
```javascript
// GOOD - Use exact filing URLs from your data pipeline
urls: {
  detail: "https://www.sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-23-000077&xbrl_type=v",
  interactive: "https://www.sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-23-000077&xbrl_type=v"
}
```

---

## 🎯 How It Works

### **1. System Uses `urls.detail` or `urls.interactive`**
```javascript
const filingUrl = source.urls?.detail || source.urls?.interactive || null;
```

If neither URL exists, the source card is displayed **without a clickable link**.

### **2. Display Format**
```
┌──────────────────────────────────┐
│ AAPL • Revenue         FY2023    │
│ $574.8B                          │
│ SEC 10-K 2023 ↗                  │
│ Annual report filed with the SEC │
└──────────────────────────────────┘
```

When clicked, opens the **exact SEC filing** where the data was sourced.

---

## 📊 Field Details

### **Required Fields:**
- `ticker` - Ticker symbol (e.g., "AAPL", "MSFT")
- `label` - Metric name (e.g., "Revenue", "Net Income")
- `period` - Time period (e.g., "FY2023", "Q4 2023")

### **Optional but Recommended:**
- `urls.detail` - Primary SEC filing URL
- `urls.interactive` - Alternative filing URL
- `formatted_value` - Pre-formatted display (e.g., "$574.8B")
- `value` - Raw numeric value (will be auto-formatted)
- `source` - Source description (e.g., "SEC 10-K 2023")
- `description` - Additional context

---

## 🔗 URL Sources

### **Where to Get Accurate URLs:**

1. **From Your Data Pipeline:**
   ```python
   # When you fetch SEC data, capture the filing URLs
   {
       'ticker': 'AAPL',
       'label': 'Revenue',
       'value': 574800,
       'urls': {
           'detail': filing_url,  # From SEC API response
           'interactive': interactive_url
       }
   }
   ```

2. **SEC API Response:**
   When fetching companyfacts or submissions, the SEC API returns:
   ```json
   {
     "filings": {
       "recent": {
         "accessionNumber": ["0000320193-23-000077"],
         "filingDate": ["2023-11-03"],
         // ... build URL from accessionNumber and CIK
       }
     }
   }
   ```

3. **Build URL from Accession Number:**
   ```javascript
   function buildSECUrl(cik, accessionNumber) {
     const paddedCik = cik.toString().padStart(10, '0');
     const accNoNoDashes = accessionNumber.replace(/-/g, '');
     return `https://www.sec.gov/cgi-bin/viewer?action=view&cik=${paddedCik}&accession_number=${accessionNumber}&xbrl_type=v`;
   }
   ```

---

## 📝 Example Integration

### **Backend (Python):**
```python
def get_sources_for_ticker(ticker, fiscal_year):
    """Return sources with accurate SEC URLs"""
    sources = []
    
    # Get SEC filings for this ticker/year
    filings = get_sec_filings(ticker, fiscal_year)
    
    for filing in filings:
        source = {
            'ticker': ticker,
            'label': filing['metric'],
            'period': filing['period'],
            'value': filing['value'],
            'formatted_value': format_value(filing['value']),
            'source': f"SEC {filing['form_type']} {fiscal_year}",
            'urls': {
                'detail': build_sec_filing_url(
                    filing['cik'], 
                    filing['accession_number']
                ),
                'interactive': build_sec_interactive_url(
                    filing['cik'],
                    filing['accession_number']
                )
            },
            'description': get_filing_description(filing['form_type'])
        }
        sources.append(source)
    
    return sources
```

### **Frontend (Payload):**
```javascript
const payload = {
  meta: { ... },
  key_financials: { ... },
  // ... other data
  
  // Sources array - same format as citations!
  sources: await fetchSourcesForDashboard(ticker, fiscalYear)
};

window.CFI.render(payload);
```

---

## ✅ Validation

### **Valid Source (Has URL):**
```javascript
{
  ticker: "AAPL",
  label: "Revenue",
  period: "FY2023",
  formatted_value: "$574.8B",
  urls: {
    detail: "https://www.sec.gov/cgi-bin/viewer?..." // ✅ Real URL
  }
}
// Result: Clickable card with "View filing" link
```

### **Valid Source (No URL):**
```javascript
{
  ticker: "AAPL",
  label: "EBITDA Margin",
  period: "FY2023",
  formatted_value: "17.8%",
  source: "BenchmarkOS Model",
  // No urls field ✅ OK for derived metrics
}
// Result: Non-clickable card showing "BenchmarkOS Model"
```

### **Invalid Source:**
```javascript
{
  label: "Revenue",  // ❌ Missing ticker
  // ❌ Missing period
  urls: {
    detail: "https://www.sec.gov/edgar/search/"  // ❌ Generic, not specific filing
  }
}
// Result: Will display but not ideal
```

---

## 🎯 Benefits of This Approach

### **1. Accuracy**
- ✅ Links go to **exact SEC filings**
- ✅ Same URLs as comparison/audit features
- ✅ Verifiable data sources

### **2. Consistency**
- ✅ Same format across entire app
- ✅ Reuses existing citation infrastructure
- ✅ No duplicate URL generation logic

### **3. Compliance**
- ✅ Audit trail to primary sources
- ✅ Meets regulatory requirements
- ✅ Professional data attribution

### **4. User Trust**
- ✅ Users can verify every number
- ✅ Direct link to source documents
- ✅ Transparent data lineage

---

## 📚 Related Code

### **Citation System (Main App):**
- `webui/app.js` lines 3246-3273 - Dashboard footer citations
- `webui/app.js` lines 3506-3554 - Citation section rendering
- Uses same `urls.detail` / `urls.interactive` structure

### **Audit Drawer:**
- `webui/app.js` lines 3580-3653 - Audit trail fetching
- `webui/app.js` lines 3727-3778 - Event detail rendering
- Fetches data from `/api/audit` endpoint

### **Data Sources (CFI Dashboard):**
- `webui/cfi_dashboard.js` lines 2181-2270 - renderDataSources
- Uses same citation format
- Matches audit drawer linking

---

## 🚀 Quick Start

### **Minimal Example:**
```javascript
sources: [
  {
    ticker: "AAPL",
    label: "Revenue",
    period: "FY2023",
    formatted_value: "$383.3B",
    urls: {
      detail: "https://www.sec.gov/cgi-bin/viewer?action=view&cik=0000320193&accession_number=0000320193-23-000106&xbrl_type=v"
    }
  }
]
```

This will create a **clickable source card** with an accurate link to Apple's FY2023 10-K filing.

---

## ❓ FAQ

### **Q: What if I don't have the filing URL?**
A: Omit the `urls` field. The card will display as non-clickable with source description.

### **Q: Can I use generic SEC search URLs?**
A: No. Use specific filing URLs or omit URLs entirely. Generic search URLs don't provide value.

### **Q: How do I get accession numbers?**
A: From SEC companyfacts API or submissions API. They're included in filing metadata.

### **Q: What about derived/calculated metrics?**
A: Omit `urls` field and set `source: "BenchmarkOS Model"` or similar.

### **Q: Can I mix sources with and without URLs?**
A: Yes! Sources with URLs are clickable, others display source text only.

---

## ✅ Checklist

Before deploying:
- [ ] Sources array uses same format as citations
- [ ] URLs are actual SEC filing links (not generic search)
- [ ] Accession numbers are correct
- [ ] CIK numbers are properly padded
- [ ] Tested clicking through to verify filing opens
- [ ] Derived metrics have descriptive source text
- [ ] All tickers are included in descriptor
- [ ] Formatted values are human-readable

---

**Status:** ✅ Matches audit drawer and citation system exactly

*Use this format to ensure data sources are accurate, verifiable, and professional.*

