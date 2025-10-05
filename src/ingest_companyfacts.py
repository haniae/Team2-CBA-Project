"""Pull SEC companyfacts into PostgreSQL with canonical metric aliases."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg2
from dateutil import parser
from psycopg2.extras import execute_batch
from requests import Response, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

SEC_COMPANY_FACTS_PRIMARY = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_COMPANY_FACTS_FALLBACK = "https://www.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_TICKER_LIST = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_TICKERS = [ticker.strip().upper() for ticker in os.getenv("SEC_TICKERS", "MSFT,AAPL,AMZN").split(",") if ticker.strip()]
DEFAULT_MIN_INTERVAL = float(os.getenv("SEC_MIN_INTERVAL", "0.3"))

TAG_ALIASES: Dict[Tuple[str, str], str] = {
    ("us-gaap", "Revenues"): "revenue",
    ("us-gaap", "SalesRevenueNet"): "revenue",
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"): "revenue",
    ("us-gaap", "NetIncomeLoss"): "net_income",
    ("us-gaap", "ProfitLoss"): "net_income",
    ("us-gaap", "OperatingIncomeLoss"): "operating_income",
    ("us-gaap", "GrossProfit"): "gross_profit",
    ("us-gaap", "Assets"): "total_assets",
    ("us-gaap", "Liabilities"): "total_liabilities",
    ("us-gaap", "StockholdersEquity"): "shareholders_equity",
    ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"): "shareholders_equity",
    ("us-gaap", "AssetsCurrent"): "current_assets",
    ("us-gaap", "LiabilitiesCurrent"): "current_liabilities",
    ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"): "cash_and_cash_equivalents",
    ("us-gaap", "CashCashEquivalentsAndShortTermInvestments"): "cash_and_cash_equivalents",
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"): "cash_from_operations",
    ("us-gaap", "NetCashProvidedByUsedInFinancingActivities"): "cash_from_financing",
    ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"): "capital_expenditures",
    ("us-gaap", "DepreciationAndAmortization"): "depreciation_and_amortization",
    ("us-gaap", "DepreciationDepletionAndAmortization"): "depreciation_and_amortization",
    ("us-gaap", "EarningsBeforeInterestAndTaxes"): "ebit",
    ("us-gaap", "IncomeTaxExpenseBenefit"): "income_tax_expense",
    ("us-gaap", "InterestExpense"): "interest_expense",
    ("us-gaap", "LongTermDebtNoncurrent"): "long_term_debt",
    ("us-gaap", "LongTermDebtCurrent"): "long_term_debt_current",
    ("us-gaap", "ShortTermBorrowings"): "short_term_debt",
    ("us-gaap", "ShortTermDebt"): "short_term_debt",
    ("us-gaap", "CommonStockSharesOutstanding"): "shares_outstanding",
    ("us-gaap", "EntityCommonStockSharesOutstanding"): "shares_outstanding",
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"): "weighted_avg_diluted_shares",
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"): "weighted_avg_basic_shares",
    ("us-gaap", "DividendsPerShareDeclared"): "dividends_per_share",
    ("us-gaap", "CommonStockDividendsPerShareDeclared"): "dividends_per_share",
    ("us-gaap", "PaymentsOfDividendsCommonStock"): "dividends_paid",
    ("us-gaap", "PaymentsOfDividends"): "dividends_paid",
    ("us-gaap", "PaymentsForRepurchaseOfCommonStock"): "share_repurchases",
    ("us-gaap", "PaymentsForRepurchaseOfCommonStockAndPreferredStock"): "share_repurchases",
}

DERIVED_METRICS = {
    "free_cash_flow": ("cash_from_operations", "capital_expenditures", "subtract"),
}


@dataclass
class PostgresSettings:
    """Connection parameters for writing SEC data to Postgres."""
    host: str = os.getenv("PGHOST", "localhost")
    port: int = int(os.getenv("PGPORT", "5432"))
    dbname: str = os.getenv("PGDATABASE", "secdb")
    user: str = os.getenv("PGUSER", "postgres")
    password: str = os.getenv("PGPASSWORD", "hania123")

    def dsn(self) -> str:
        """Return the psycopg connection string for the configured Postgres target."""
        return f"host={self.host} port={self.port} dbname={self.dbname} user={self.user} password={self.password}"


@dataclass
class RunSettings:
    """Runtime configuration for the SEC company facts ingest."""
    tickers: List[str]
    schema: str = os.getenv("PGSCHEMA", "sec")
    min_interval: float = DEFAULT_MIN_INTERVAL


class SecClient:
    """Thin SEC API client with basic throttling and caching."""
    def __init__(self, *, user_agent: str, min_interval: float) -> None:
        """Initialise the SEC client with configuration and optional session."""
        if not user_agent:
            raise ValueError("SEC_API_USER_AGENT must be set (e.g. 'Firstname Lastname email@example.com')")
        self._session = _build_session(user_agent)
        self._last_call = 0.0
        self._min_interval = min_interval

    def _throttle(self) -> None:
        """Respect SEC rate limits by sleeping between requests."""
        elapsed = time.monotonic() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _request(self, url: str) -> Response:
        """Perform a GET request to the SEC API with error handling."""
        self._throttle()
        resp = self._session.get(url, timeout=60)
        if resp.status_code == 404 and url.startswith("https://data.sec.gov"):
            alt = url.replace("https://data.sec.gov", "https://www.sec.gov")
            self._throttle()
            resp = self._session.get(alt, timeout=60)
        resp.raise_for_status()
        self._last_call = time.monotonic()
        return resp

    def fetch_companyfacts(self, cik: str) -> Dict:
        """Download the SEC companyfacts payload for a given CIK."""
        url = SEC_COMPANY_FACTS_PRIMARY.format(cik=cik.zfill(10))
        try:
            return self._request(url).json()
        except Exception:
            fallback = SEC_COMPANY_FACTS_FALLBACK.format(cik=cik.zfill(10))
            return self._request(fallback).json()

    def fetch_ticker_map(self) -> Dict[str, str]:
        """Fetch the helper mapping between tickers and CIK identifiers."""
        payload = self._request(SEC_TICKER_LIST).json()
        mapping: Dict[str, str] = {}
        iterable = payload.values() if isinstance(payload, dict) else payload
        for entry in iterable:
            ticker = str(entry["ticker"]).upper()
            cik = str(entry["cik_str"]).zfill(10)
            mapping[ticker] = cik
        return mapping


def _build_session(user_agent: str) -> Session:
    """Create a shared HTTP session with retry/backoff behaviour."""
    session = Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    })
    return session


def to_date(value: Optional[str]):
    """Convert SEC date fields into Python date objects."""
    if not value:
        return None
    try:
        return parser.isoparse(value).date()
    except Exception:
        return None


def to_num(value):
    """Coerce potentially numeric strings into floats, ignoring blanks."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def ensure_schema(pg: PostgresSettings, schema: str) -> None:
    """Create target tables and indexes required for ingestion outputs."""
    with psycopg2.connect(pg.dsn()) as conn, conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        # Fixed: nullable fy/fp can't be in PK; use accn/period_end instead
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.facts (
                cik TEXT NOT NULL,
                entity_name TEXT,
                metric TEXT,
                raw_tag TEXT,
                taxonomy TEXT,
                unit TEXT,
                fy INT,
                fp TEXT,
                form TEXT,
                filed DATE,
                period_start DATE,
                period_end DATE,
                frame TEXT,
                val DOUBLE PRECISION,
                accn TEXT,
                uom TEXT,
                qc INT,
                frame_key TEXT GENERATED ALWAYS AS (COALESCE(frame, '')) STORED,
                PRIMARY KEY (cik, metric, taxonomy, unit, period_end, frame_key, accn)
            )
            """
        )

        # Upgrade legacy tables that might be missing newer columns
        required_columns = {
            "metric": "TEXT",
            "raw_tag": "TEXT",
            "taxonomy": "TEXT",
            "unit": "TEXT",
            "fy": "INT",
            "fp": "TEXT",
            "form": "TEXT",
            "filed": "DATE",
            "period_start": "DATE",
            "period_end": "DATE",
            "frame": "TEXT",
            "val": "DOUBLE PRECISION",
            "accn": "TEXT",
            "uom": "TEXT",
            "qc": "INT",
            "frame_key": "TEXT GENERATED ALWAYS AS (COALESCE(frame, '')) STORED",
        }

        cur.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, "facts"),
        )
        column_info = {row[0]: row[1] for row in cur.fetchall()}
        existing = set(column_info)

        for column, definition in required_columns.items():
            if column in existing:
                continue
            cur.execute(
                f"ALTER TABLE {schema}.facts ADD COLUMN {column} {definition}"
            )

        # Populate missing canonical metric names for legacy rows
        cur.execute(
            f"""
            UPDATE {schema}.facts
            SET metric = COALESCE(metric, raw_tag)
            WHERE metric IS NULL AND raw_tag IS NOT NULL
            """
        )

        if "tag" in existing:
            cur.execute(
                f"""
                UPDATE {schema}.facts
                SET raw_tag = COALESCE(raw_tag, tag)
                WHERE tag IS NOT NULL AND (raw_tag IS NULL OR raw_tag = '')
                """
            )
            if column_info.get("tag") == "NO":
                cur.execute(
                    f"ALTER TABLE {schema}.facts ALTER COLUMN tag DROP NOT NULL"
                )

        cur.execute(
            f"DELETE FROM {schema}.facts WHERE metric IS NULL"
        )

        # Remove duplicate rows that would violate the primary key we expect
        cur.execute(
            f"""
            DELETE FROM {schema}.facts AS a
            USING {schema}.facts AS b
            WHERE a.ctid < b.ctid
              AND COALESCE(a.cik::TEXT, '') = COALESCE(b.cik::TEXT, '')
              AND COALESCE(a.metric, '') = COALESCE(b.metric, '')
              AND COALESCE(a.taxonomy, '') = COALESCE(b.taxonomy, '')
              AND COALESCE(a.unit, '') = COALESCE(b.unit, '')
              AND COALESCE(a.period_end::TEXT, '') = COALESCE(b.period_end::TEXT, '')
              AND COALESCE(a.frame_key, '') = COALESCE(b.frame_key, '')
              AND COALESCE(a.accn, '') = COALESCE(b.accn, '')
            """
        )

        desired_pk = (
            "cik",
            "metric",
            "taxonomy",
            "unit",
            "period_end",
            "frame_key",
            "accn",
        )

        cur.execute(
            """
            SELECT conname, ARRAY_AGG(att.attname ORDER BY att.attnum) AS columns
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN unnest(con.conkey) WITH ORDINALITY AS cols(attnum, ord) ON true
            JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = cols.attnum
            WHERE con.contype = 'p'
              AND rel.relname = %s
              AND nsp.nspname = %s
            GROUP BY conname
            """,
            ("facts", schema),
        )
        pk_row = cur.fetchone()
        if pk_row is not None:
            pk_name, columns = pk_row
            if tuple(columns) != desired_pk:
                cur.execute(f"ALTER TABLE {schema}.facts DROP CONSTRAINT {pk_name}")
                cur.execute(
                    f"ALTER TABLE {schema}.facts ADD PRIMARY KEY ({', '.join(desired_pk)})"
                )
        else:
            cur.execute(
                f"ALTER TABLE {schema}.facts ADD PRIMARY KEY ({', '.join(desired_pk)})"
            )

        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.ticker_cik (
                ticker TEXT PRIMARY KEY,
                cik TEXT NOT NULL
            )
            """
        )


def get_ciks(pg: PostgresSettings, tickers: Iterable[str], schema: str) -> List[str]:
    """Resolve the list of CIKs that should be processed this run."""
    tickers = [t.upper() for t in tickers]
    sql = f"SELECT cik FROM {schema}.ticker_cik WHERE ticker = ANY(%s)"
    with psycopg2.connect(pg.dsn()) as conn, conn.cursor() as cur:
        cur.execute(sql, (tickers,))
        return [str(row[0]).zfill(10) for row in cur.fetchall()]


def populate_ticker_map(pg: PostgresSettings, schema: str, client: SecClient) -> None:
    """Build an in-memory ticker-to-CIK mapping for lookups."""
    mapping = client.fetch_ticker_map()
    payload = [(ticker, cik) for ticker, cik in mapping.items()]
    with psycopg2.connect(pg.dsn()) as conn, conn.cursor() as cur:
        execute_batch(
            cur,
            f"INSERT INTO {schema}.ticker_cik (ticker, cik) VALUES (%s, %s) ON CONFLICT (ticker) DO UPDATE SET cik = excluded.cik",
            payload,
            page_size=500,
        )


def _canonical_metric(taxonomy: str, tag: str) -> Optional[str]:
    """Normalise SEC metric names to the canonical identifiers used here."""
    key = (taxonomy.lower(), tag)
    if key in TAG_ALIASES:
        return TAG_ALIASES[key]
    key = (taxonomy.lower(), tag.rstrip("0123456789"))
    return TAG_ALIASES.get(key)


def process_companyfacts(cik: str, data: Dict) -> Tuple[List[Dict], Dict[Tuple[str, str, str], Dict[str, Any]]]:
    """Transform SEC companyfacts JSON into structured row records."""
    rows: List[Dict] = []
    index: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    entity = data.get("entityName")
    facts = data.get("facts") or {}
    for taxonomy, tags in facts.items():
        for tag, body in tags.items():
            metric = _canonical_metric(taxonomy, tag)
            if metric is None:
                continue
            units = body.get("units") or {}
            for unit, observations in units.items():
                for obs in observations:
                    value = to_num(obs.get("val"))
                    fy = obs.get("fy")
                    fp = obs.get("fp")
                    row = {
                        "cik": cik,
                        "entity_name": entity,
                        "metric": metric,
                        "raw_tag": tag,
                        "taxonomy": taxonomy,
                        "unit": unit,
                        "fy": fy,
                        "fp": fp,
                        "form": obs.get("form"),
                        "filed": to_date(obs.get("filed")),
                        "period_start": to_date(obs.get("start")),
                        "period_end": to_date(obs.get("end")),
                        "frame": obs.get("frame"),
                        "val": value,
                        "accn": obs.get("accn"),
                        "uom": obs.get("uom"),
                        "qc": obs.get("qtrs") or obs.get("qtr"),
                    }
                    rows.append(row)
                    key = (metric, str(fy), str(fp))
                    if value is not None:
                        index[key] = {
                            "value": value,
                            "fy": fy,
                            "fp": fp,
                            "period_start": row["period_start"],
                            "period_end": row["period_end"],
                            "filed": row["filed"],
                            "unit": unit,
                            "form": row["form"],
                            "frame": row["frame"],
                            "accn": row["accn"],
                            "qc": row["qc"],
                            "cik": cik,
                            "entity_name": entity,
                        }
    return rows, index


def derive_metrics(rows: List[Dict], value_index: Dict[Tuple[str, str, str], Dict[str, Any]]) -> None:
    """Compute derivative metrics (margins, ratios) from fact rows."""
    if not rows:
        return
    for metric, (numer_key, denom_key, operation) in DERIVED_METRICS.items():
        additions: List[Dict] = []
        for (base_metric, fy_key, fp_key), numer_record in value_index.items():
            if base_metric != numer_key:
                continue
            numer = numer_record.get("value")
            if numer is None:
                continue
            denom_record = value_index.get((denom_key, fy_key, fp_key))
            if denom_record is None or denom_record.get("value") is None:
                continue
            denom = denom_record["value"]

            # Fixed: subtract for FCF, not add
            if operation == "subtract":
                result = numer - abs(denom)  # CapEx is usually negative, make it positive
            else:
                result = numer + denom

            period_end = numer_record.get("period_end") or denom_record.get("period_end")
            if period_end is None:
                continue
            period_start = numer_record.get("period_start") or denom_record.get("period_start")
            filed = numer_record.get("filed") or denom_record.get("filed")
            frame = numer_record.get("frame") or denom_record.get("frame")
            unit = numer_record.get("unit") or denom_record.get("unit")
            qc = numer_record.get("qc") or denom_record.get("qc")
            cik = numer_record.get("cik")
            entity_name = numer_record.get("entity_name")

            fy_value = numer_record.get("fy")
            if isinstance(fy_value, str):
                fy_clean = int(fy_value) if fy_value.isdigit() else None
            elif isinstance(fy_value, (int, float)):
                fy_clean = int(fy_value)
            else:
                fy_clean = None

            fp_value = numer_record.get("fp")
            if fp_value in ("None", "", None):
                fp_clean = None
            else:
                fp_clean = fp_value

            additions.append(
                {
                    "cik": cik,
                    "entity_name": entity_name,
                    "metric": metric,
                    "raw_tag": f"derived:{metric}",
                    "taxonomy": "derived",
                    "unit": unit,
                    "fy": fy_clean,
                    "fp": fp_clean,
                    "form": numer_record.get("form") or denom_record.get("form"),
                    "filed": filed,
                    "period_start": period_start,
                    "period_end": period_end,
                    "frame": frame,
                    "val": result,
                    "accn": f"derived-{fy_key}-{fp_key}",
                    "uom": None,
                    "qc": qc,
                }
            )
        rows.extend(additions)


def upsert_rows(conn, rows: List[Dict], schema: str) -> None:
    """Bulk upsert processed rows into the destination database."""
    if not rows:
        return
    # Fixed: use ON CONFLICT with the actual PK constraint
    sql = f"""
        INSERT INTO {schema}.facts (
            cik, entity_name, metric, raw_tag, taxonomy, unit, fy, fp, form,
            filed, period_start, period_end, frame, val, accn, uom, qc
        ) VALUES (
            %(cik)s, %(entity_name)s, %(metric)s, %(raw_tag)s, %(taxonomy)s,
            %(unit)s, %(fy)s, %(fp)s, %(form)s, %(filed)s, %(period_start)s,
            %(period_end)s, %(frame)s, %(val)s, %(accn)s, %(uom)s, %(qc)s
        )
        ON CONFLICT (cik, metric, taxonomy, unit, period_end, frame, accn) DO UPDATE SET
            val = EXCLUDED.val,
            filed = EXCLUDED.filed,
            fy = EXCLUDED.fy,
            fp = EXCLUDED.fp,
            form = EXCLUDED.form
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=1000)


def run_ingest() -> None:
    """Entry point that orchestrates fetching, transforming, and writing facts."""
    pg_settings = PostgresSettings()
    run_settings = RunSettings(tickers=DEFAULT_TICKERS)
    ua = os.getenv("SEC_API_USER_AGENT") or os.getenv("SEC_USER_AGENT")
    client = SecClient(user_agent=ua, min_interval=run_settings.min_interval)

    ensure_schema(pg_settings, run_settings.schema)

    ciks = get_ciks(pg_settings, run_settings.tickers, run_settings.schema)
    if not ciks:
        populate_ticker_map(pg_settings, run_settings.schema, client)
        ciks = get_ciks(pg_settings, run_settings.tickers, run_settings.schema)

    print("Tickers:", run_settings.tickers)
    print("CIKs:", ciks)

    with psycopg2.connect(pg_settings.dsn()) as conn:
        conn.autocommit = True
        for ticker, cik in zip(run_settings.tickers, ciks):
            print(f"Fetching companyfacts for {ticker} ({cik})")
            try:
                payload = client.fetch_companyfacts(cik)
            except Exception as exc:
                print(f"  Failed: {exc}")
                continue
            rows, index = process_companyfacts(cik, payload)
            derive_metrics(rows, index)
            print(f"  Upserting {len(rows)} rows")
            upsert_rows(conn, rows, run_settings.schema)
    print("Done.")

    try:
        from benchmarkos_chatbot.analytics_engine import AnalyticsEngine
        from benchmarkos_chatbot.config import load_settings

        settings = load_settings()
        engine = AnalyticsEngine(settings)
        print("Refreshing SQLite metric snapshots from secdb …")
        engine.refresh_metrics(force=True)
        print("Metric snapshots refreshed.")
    except Exception as exc:  # pragma: no cover - best effort refresh
        print(f"Warning: unable to refresh metric snapshots automatically: {exc}")


if __name__ == "__main__":
    run_ingest()
