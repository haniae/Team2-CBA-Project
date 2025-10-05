import time, os, requests, psycopg2
from psycopg2.extras import execute_batch
from datetime import date

PG = dict(host=os.getenv("PGHOST","localhost"),
          port=int(os.getenv("PGPORT","5432")),
          dbname=os.getenv("PGDATABASE","secdb"),
          user=os.getenv("PGUSER","postgres"),
          password=os.getenv("PGPASSWORD","hania123"))

UA = {"User-Agent": os.getenv("SEC_API_USER_AGENT", "Hania MSBA / frames loader (hania@gwu.edu)")}

TAGS = [
  "Revenues","NetIncomeLoss","OperatingIncomeLoss","GrossProfit",
  "Assets","Liabilities","StockholdersEquity",
  "CashAndCashEquivalentsAtCarryingValue",
  "NetCashProvidedByUsedInOperatingActivities",
  "PaymentsToAcquirePropertyPlantAndEquipment",
  "CommonStockSharesOutstanding"
]

YEAR_SPAN = 5
THIS_YEAR = date.today().year
YEARS = list(range(THIS_YEAR, THIS_YEAR - YEAR_SPAN, -1))

DURATION = {"Revenues","NetIncomeLoss","OperatingIncomeLoss","GrossProfit",
            "NetCashProvidedByUsedInOperatingActivities",
            "PaymentsToAcquirePropertyPlantAndEquipment"}
INSTANT  = {"Assets","Liabilities","StockholdersEquity",
            "CashAndCashEquivalentsAtCarryingValue",
            "CommonStockSharesOutstanding"}

def polite_get(url, tries=5, base=0.4):
    """Download a frame payload with polite retry/backoff handling.

    Args:
        url: Frame endpoint to query.
        tries: Number of attempts before giving up.
        base: Base delay used in the exponential backoff.
    Returns:
        `requests.Response` object from the SEC API.
    """
    for i in range(tries):
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code in (200, 404):
            return r
        if r.status_code in (429, 503):
            time.sleep(base * (2 ** i))
            continue
        r.raise_for_status()
    return r

def upsert_rows(conn, rows):
    """Insert fetched frame rows into the Postgres frames table.
    """
    if not rows:
        return
    with conn.cursor() as cur:
        execute_batch(cur, """
      INSERT INTO sec.frames (tag, unit, frame, cik, filed, val, uom, accn)
      VALUES (%(tag)s,%(unit)s,%(frame)s,%(cik)s,%(filed)s,%(val)s,%(uom)s,%(accn)s)
      ON CONFLICT (tag, unit, frame, cik, accn) DO UPDATE
      SET val = EXCLUDED.val, filed = EXCLUDED.filed, uom = EXCLUDED.uom
    """, rows, page_size=5000)

def main():
    """Iterate across target tags/years and persist SEC XBRL frame data.
    """
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    for tag in TAGS:
        for y in YEARS:
            frame = f"CY{y}" if tag in DURATION else f"CY{y}I"
            url = f"https://data.sec.gov/api/xbrl/frames/US-GAAP/{tag}/USD/{frame}.json"
            print("GET", url)
            r = polite_get(url)
            if r.status_code == 404:
                print("  404 – skip")
                continue
            js = r.json()
            rows = []
            for o in js.get("data", []):
                rows.append(dict(
                    tag=tag,
                    unit="USD",
                    frame=frame,
                    cik=int(o["cik"]),
                    filed=None,
                    val=o.get("val"),
                    uom=o.get("uom"),
                    accn=o.get("accn")
                ))
            print(f"  rows: {len(rows)}")
            upsert_rows(conn, rows)
            time.sleep(0.25)  # ~4 req/s
    print("Done.")

if __name__ == "__main__":
    main()
