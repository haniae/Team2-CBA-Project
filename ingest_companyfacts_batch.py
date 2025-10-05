import os, time, argparse, requests, psycopg2
from psycopg2.extras import execute_batch
from dateutil import parser

PG = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "secdb"),
    user=os.getenv("PGUSER", "postgres"),
    password=os.getenv("PGPASSWORD", "hania123"),
)

UA_STR = os.getenv("SEC_API_USER_AGENT", "Hania MSBA / SEC loader (hania@gwu.edu)")
UA = {"User-Agent": UA_STR}
BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

def to_date(s):
    """Parse SEC date strings into `datetime.date` instances, tolerating blanks.
    """
    if not s: return None
    try: return parser.parse(s).date()
    except Exception: return None

def to_num(x):
    """Convert numeric-looking strings to floats, returning ``None`` when empty.
    """
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        return float(str(x).replace(",", ""))
    except Exception:
        return None

def ensure_meta_tables(conn):
    """Ensure helper tables exist to track ingest checkpoints and metadata.
    """
    with conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sec.etl_companyfacts (
            cik BIGINT PRIMARY KEY,
            last_status INT,
            last_fetched TIMESTAMP DEFAULT now()
        );
        """)

def get_tickers():
    """Return the ordered list of tickers to ingest for this batch execution.
    """
    env = os.getenv("SEC_TICKERS", "").strip()
    if env:
        parts = [t.strip().upper() for t in env.replace("\n"," ").replace("\t"," ").split(",") if t.strip()]
        if parts: return parts
    if os.path.exists("tickers.txt"):
        with open("tickers.txt","r",encoding="utf-8") as f:
            raw = f.read()
        parts = [t.strip().upper() for t in raw.replace("\n",",").replace("\t",",").split(",") if t.strip()]
        return parts
    return ["MSFT","GE","F"]

def tickers_to_ciks(conn, tickers):
    """Map tickers to their CIK identifiers using checkpoint metadata.
    """
    with conn, conn.cursor() as cur:
        cur.execute("SELECT ticker, cik FROM sec.ticker_cik WHERE ticker = ANY(%s)", (tickers,))
        d = dict(cur.fetchall())
    missing = sorted(set(tickers) - set(d.keys()))
    if missing:
        print(f"⚠️  {len(missing)} tickers missing from sec.ticker_cik (e.g., {', '.join(missing[:8])})")
    return [d[t] for t in tickers if t in d]

def process_companyfacts(cik, js):
    """Transform raw companyfacts JSON into dictionaries ready for bulk upsert.
    """
    rows = []
    entity = js.get("entityName")
    facts = js.get("facts") or {}
    for taxonomy, tags in facts.items():
        for tag, body in tags.items():
            units = body.get("units") or {}
            for unit, obs in units.items():
                for o in obs:
                    rows.append(dict(
                        cik=cik, entity_name=entity, tag=tag, taxonomy=taxonomy, unit=unit,
                        fy=o.get("fy"), fp=o.get("fp"), form=o.get("form"),
                        filed=to_date(o.get("filed")), period_start=to_date(o.get("start")),
                        period_end=to_date(o.get("end")), frame=o.get("frame"),
                        val=to_num(o.get("val")), accn=o.get("accn"),
                        uom=o.get("uom"), qc=o.get("qtrs") or o.get("qtr")
                    ))
    return rows

def upsert_facts(conn, rows):
    """Insert or update fact rows in bulk inside the destination database.
    """
    if not rows: return
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO sec.facts
            (cik, entity_name, tag, taxonomy, unit, fy, fp, form, filed,
             period_start, period_end, frame, val, accn, uom, qc)
            VALUES
            (%(cik)s, %(entity_name)s, %(tag)s, %(taxonomy)s, %(unit)s, %(fy)s, %(fp)s, %(form)s, %(filed)s,
             %(period_start)s, %(period_end)s, %(frame)s, %(val)s, %(accn)s, %(uom)s, %(qc)s)
            ON CONFLICT ON CONSTRAINT facts_pkey DO UPDATE
            SET val   = EXCLUDED.val,
                filed = EXCLUDED.filed,
                fy    = EXCLUDED.fy,
                fp    = EXCLUDED.fp,
                form  = EXCLUDED.form
        """, rows, page_size=1000)

def update_checkpoint(conn, cik, status):
    """Persist the most recent successful ingest checkpoint for resuming later.
    """
    with conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sec.etl_companyfacts (cik, last_status, last_fetched)
            VALUES (%s, %s, now())
            ON CONFLICT (cik) DO UPDATE
            SET last_status = EXCLUDED.last_status, last_fetched = now();
        """, (cik, status))

def polite_get(url, headers, timeout, max_retries=5, base_delay=0.5):
    """Perform a GET request with exponential backoff tailored for the SEC API.
    """
    for i in range(max_retries):
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code in (200, 404): return r
        if r.status_code in (429, 503):
            sleep_s = base_delay * (2 ** i)
            print(f"   Got {r.status_code}, backing off {sleep_s:.1f}s …")
            time.sleep(sleep_s); continue
        r.raise_for_status()
    return r

def main():
    """Main entry point driving paginated ingestion of SEC companyfacts.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300, help="Max tickers to process this run")
    ap.add_argument("--rps", type=float, default=3.0, help="Requests per second")
    args = ap.parse_args()

    delay = 1.0 / max(0.1, args.rps)
    tickers = get_tickers()
    print(f"Loading {len(tickers)} tickers (limit {args.limit}) …")

    conn = psycopg2.connect(**PG); conn.autocommit = True
    ensure_meta_tables(conn)

    ciks = tickers_to_ciks(conn, tickers)[: args.limit]
    print(f"CIKs to process: {len(ciks)}")

    for idx, cik in enumerate(ciks, 1):
        url = BASE.format(cik=str(cik).zfill(10))
        print(f"[{idx}/{len(ciks)}] {url}")
        r = polite_get(url, UA, timeout=60)
        if r.status_code == 404:
            print("   404 — no companyfacts (skipping)")
            update_checkpoint(conn, cik, 404)
            time.sleep(delay); continue
        js = r.json()
        rows = process_companyfacts(cik, js)
        print(f"   Upserting {len(rows)} rows …")
        upsert_facts(conn, rows)
        update_checkpoint(conn, cik, 200)
        time.sleep(delay)
    print("Done.")

if __name__ == "__main__":
    main()
