import os, csv, io, datetime, requests, psycopg2
from psycopg2.extras import execute_batch

PG = dict(host=os.getenv("PGHOST","localhost"),
          port=int(os.getenv("PGPORT","5432")),
          dbname=os.getenv("PGDATABASE","secdb"),
          user=os.getenv("PGUSER","postgres"),
          password=os.getenv("PGPASSWORD","hania123"))

ENV_TICKERS = [t.strip().upper() for t in os.getenv("SEC_TICKERS","MSFT,GE,AAPL,AMZN").split(",") if t.strip()]
DAYS = int(os.getenv("PRICE_DAYS","1200"))  # ~5 years

def stooq_symbol(ticker):  # US tickers need .us
    """Translate a standard ticker into Stooq's expected symbol.

    Args:
        ticker: Ticker symbol (e.g. 'MSFT').
    Returns:
        Stooq-formatted symbol string (e.g. 'msft.us').
    """
    return f"{ticker.lower()}.us"

def stooq_url(ticker):
    """Return the download URL for a Stooq CSV once provided a symbol.
    """
    return f"https://stooq.com/q/d/l/?s={stooq_symbol(ticker)}&i=d"

def fetch_csv(ticker):
    """Download and return the historical price CSV payload from Stooq.
    """
    r = requests.get(stooq_url(ticker), timeout=30)
    if r.status_code != 200 or not r.text.startswith("Date,Open,High,Low,Close,Volume"):
        print(f"{ticker}: no data (HTTP {r.status_code})"); return []
    rows = []
    f = io.StringIO(r.text)
    rdr = csv.DictReader(f)
    for row in rdr:
        try:
            dt = datetime.date.fromisoformat(row["Date"])
            close = float(row["Close"]) if row["Close"] else None
            adj = close
            vol = int(row["Volume"]) if row["Volume"] else None
            rows.append((ticker, dt, close, adj, vol))
        except Exception:
            pass
    rows.sort(key=lambda x: x[1])
    if DAYS and len(rows) > DAYS:
        rows = rows[-DAYS:]
    return rows

def ensure_table(conn):
    """Create the prices table if it does not exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS sec")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sec.prices_daily (
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                close DOUBLE PRECISION,
                adj_close DOUBLE PRECISION,
                volume BIGINT,
                PRIMARY KEY (ticker, date)
            )
            """
        )


def upsert(conn, rows):
    """Insert or update Stooq price rows into the local SQLite database.
    """
    if not rows: return
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO sec.prices_daily (ticker, date, close, adj_close, volume)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (ticker, date) DO UPDATE
            SET close = EXCLUDED.close,
                adj_close = EXCLUDED.adj_close,
                volume = EXCLUDED.volume
        """, rows, page_size=2000)

def main():
    """Load historical price data for the configured `TICKERS` collection.
    """
    conn = psycopg2.connect(**PG); conn.autocommit = True
    ensure_table(conn)
    tickers = ENV_TICKERS
    print("Tickers:", ",".join(tickers))
    for t in tickers:
        rows = fetch_csv(t)
        print(f"{t}: {len(rows)} rows")
        upsert(conn, rows)
    print("Done.")

if __name__ == "__main__":
    main()
