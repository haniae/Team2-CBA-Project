# Portfolio Test Files

This directory contains test portfolio files for different use cases.

## Available Portfolios

### `mizuho_fi_capital_portfolio.csv`
**Institutional Portfolio for Mizuho, FI (Financial Institution), and Capital**

A diversified institutional portfolio with 35 holdings representing typical investments for major financial institutions.

#### Portfolio Characteristics:
- **Total Holdings**: 35 companies
- **Total Weight**: 100.00% (normalized)
- **Sector Diversification**: Financial Services, Technology, Healthcare, Consumer, Energy

#### Top 10 Holdings:
1. JPM (JPMorgan Chase) - 6.50%
2. BAC (Bank of America) - 5.51%
3. AAPL (Apple) - 5.51%
4. WFC (Wells Fargo) - 5.20%
5. MSFT (Microsoft) - 5.20%
6. GS (Goldman Sachs) - 4.21%
7. GOOGL (Alphabet) - 4.21%
8. MS (Morgan Stanley) - 4.06%
9. BLK (BlackRock) - 3.67%
10. AMZN (Amazon) - 3.67%

#### Sector Breakdown:
- **Financial Services** (12 holdings): JPM, BAC, WFC, GS, MS, BLK, SCHW, COF, AXP, BK, MA, V
- **Technology** (11 holdings): AAPL, MSFT, GOOGL, AMZN, META, NVDA, AVGO, AMD, INTC, TSLA, CRM
- **Healthcare** (4 holdings): UNH, JNJ, ABBV, ABT
- **Consumer** (6 holdings): PG, KO, WMT, HD, NFLX, DIS
- **Energy** (2 holdings): XOM, CVX

#### Why These Companies?
This portfolio represents typical institutional holdings for:
- **Mizuho** (Japanese bank): Large-cap financial services and technology companies with global presence
- **FI (Financial Institution)**: Financial services companies, payment processors, and fintech
- **Capital**: Diversified blue-chip companies with strong fundamentals, dividends, and growth potential

All companies are from the S&P 1500 universe supported by the chatbot.

## Usage

To upload this portfolio to the chatbot:

1. **Via Web UI**: 
   - Go to Portfolio Management section
   - Click "Upload Portfolio"
   - Select `mizuho_fi_capital_portfolio.csv`

2. **Via Chatbot Query**:
   ```
   "Upload portfolio from data/portfolios/mizuho_fi_capital_portfolio.csv"
   ```

3. **Programmatically**:
   ```python
   from finanlyzeos_chatbot.portfolio import ingest_holdings_csv
   holdings = ingest_holdings_csv('data/portfolios/mizuho_fi_capital_portfolio.csv')
   ```

## File Format

The CSV file uses the following format:
- **ticker** (required): Stock ticker symbol
- **weight** (required): Portfolio weight as percentage (0-100)

Optional columns (not included but supported):
- shares: Number of shares
- price: Current price per share
- cost_basis: Purchase price per share
- currency: Currency code (default: USD)

