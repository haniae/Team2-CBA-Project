import requests, psycopg2, time
from psycopg2.extras import execute_batch
from dateutil import parser

PG = dict(host="localhost", port=5432, dbname="secdb", user="postgres", password="hania123")
UA = {"User-Agent": "Hania MSBA / companyfacts ingester (hania@gwu.edu)"}  # use your email

BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEED_TICKERS = ["MSFT","GE","F"]  # change this list as needed

def to_date(s):
    """Parse SEC date strings into `datetime.date` objects.

    Args:
        s: Raw date string from the SEC payload.
    Returns:
        Parsed date or ``None`` when the field is missing or malformed.
    """
    if not s:
        return None
    try:
        return parser.parse(s).date()
    except Exception:
        return None

def get_ciks():
    """Return the list of CIK identifiers corresponding to `SEED_TICKERS`.

    Returns:
        A list of integer CIKs sorted as returned by the database.
    """
    conn = psycopg2.connect(**PG)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT cik FROM sec.ticker_cik WHERE ticker = ANY(%s)", (SEED_TICKERS,))
        return [r[0] for r in cur.fetchall()]

def process(cik, js):
    """Transform the SEC companyfacts JSON payload into database rows.

    Args:
        cik: Integer CIK identifier being processed.
        js: Parsed companyfacts JSON document.
    Returns:
        List of dictionaries ready for the ``upsert`` routine.
    """
    rows = []
    entity = js.get("entityName")
    for taxonomy, tags in (js.get("facts") or {}).items():
        for tag, body in tags.items():
            for unit, obs in (body.get("units") or {}).items():
                for o in obs:
                    rows.append(
                        dict(
                            cik=cik,
                            entity_name=entity,
                            tag=tag,
                            taxonomy=taxonomy,
                            unit=unit,
                            fy=o.get("fy"),
                            fp=o.get("fp"),
                            form=o.get("form"),
                            filed=to_date(o.get("filed")),
                            period_start=to_date(o.get("start")),
                            period_end=to_date(o.get("end")),
                            frame=o.get("frame"),
                            val=o.get("val"),
                            accn=o.get("accn"),
                            uom=o.get("uom"),
                            qc=o.get("qtrs") or o.get("qtr"),
                        )
                    )
    return rows

def upsert(conn, rows):
    """Bulk upsert transformed rows into the Postgres facts table.

    Args:
        conn: Open psycopg2 connection.
        rows: Row dictionaries produced by ``process``.
    """
    if not rows:
        return
    with conn.cursor() as cur:
        execute_batch(
            cur,
            """
            INSERT INTO sec.facts (
                cik, entity_name, metric, raw_tag, taxonomy, unit, fy, fp, form,
                filed, period_start, period_end, frame, val, accn, uom, qc
            ) VALUES (
                %(cik)s, %(entity_name)s, %(tag)s, %(tag)s, %(taxonomy)s,
                %(unit)s, %(fy)s, %(fp)s, %(form)s, %(filed)s,
                %(period_start)s, %(period_end)s, %(frame)s, %(val)s,
                %(accn)s, %(uom)s, %(qc)s
            )
            ON CONFLICT (cik, metric, taxonomy, unit, period_end, frame_key, accn) DO UPDATE SET
                val = EXCLUDED.val,
                filed = EXCLUDED.filed,
                fy = EXCLUDED.fy,
                fp = EXCLUDED.fp,
                form = EXCLUDED.form
            """,
            rows,
            page_size=1000,
        )

def main():
    """Run ingestion for `SEED_TICKERS`, fetching companyfacts and persisting them.
    """
    ciks = get_ciks()
    print("CIKs:", ciks)
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    for cik in ciks:
        url = BASE.format(cik=str(cik).zfill(10))
        print("Fetching", url)
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 404:
            print("  404 — skipping", cik)
            continue
        r.raise_for_status()
        rows = process(cik, r.json())
        print(f"  Upserting {len(rows)} rows …")
        upsert(conn, rows)
        time.sleep(0.3)  # be polite to SEC
    print("Done.")

if __name__ == "__main__":
    main()
