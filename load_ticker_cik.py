import requests, psycopg2
from psycopg2.extras import execute_batch

PG = dict(host="localhost", port=5432, dbname="secdb", user="postgres", password="hania123")
UA = {"User-Agent": "Hania MSBA / secdb loader (hania@gwu.edu)"}  # include your email for SEC

URL = "https://www.sec.gov/files/company_tickers.json"

def main():
    """Populate the SQLite ticker→CIK mapping table from SEC data.

    The script fetches the latest SEC ticker list, normalises it, and stores
    the results in the local database used by the rest of the project.
    """
    """CLI helper that populates the ticker→CIK lookup table."""
    r = requests.get(URL, headers=UA, timeout=60)
    r.raise_for_status()
    data = r.json()  # {"0": {"cik_str":..., "ticker":..., "title":...}, ...}
    rows = [(int(v["cik_str"]), v["ticker"], v["title"]) for v in data.values()]

    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    with conn, conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS sec.ticker_cik (
            cik BIGINT PRIMARY KEY,
            ticker TEXT UNIQUE,
            title TEXT
        )""")
        execute_batch(cur, """
            INSERT INTO sec.ticker_cik (cik, ticker, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (cik) DO UPDATE
            SET ticker = EXCLUDED.ticker, title = EXCLUDED.title
        """, rows, page_size=1000)
    print(f"Upserted {len(rows)} rows into sec.ticker_cik")

if __name__ == "__main__":
    main()
