"""Helpers for interacting with the Postgres-based SEC fact store (secdb)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence

from .config import Settings
from .database import FinancialFactRecord


def _to_datetime(value: Optional[date | datetime]) -> Optional[datetime]:
    """Convert date/datetime from Postgres into timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _period_label(fiscal_year: Optional[int], fiscal_period: Optional[str]) -> str:
    """Parse SEC period labels into canonical display strings."""
    if fiscal_year is None:
        return (fiscal_period or "unknown").upper()
    period = (fiscal_period or "").strip().upper()
    if period and period not in {"FY", "CY"}:
        return f"FY{fiscal_year}{period}"
    return f"FY{fiscal_year}"


@dataclass(frozen=True)
class _PostgresParams:
    """Connection parameters required to reach the SEC Postgres mirror."""
    host: str
    port: int
    dbname: str
    user: str
    password: Optional[str]
    schema: str


class SecPostgresStore:
    """Lightweight client for reading SEC facts from Postgres."""

    def __init__(self, settings: Settings) -> None:
        """Store settings used for building Postgres connections."""
        if settings.database_type != "postgresql":
            raise ValueError("SecPostgresStore requires DATABASE_TYPE=postgresql")
        if not settings.postgres_host or not settings.postgres_database or not settings.postgres_user:
            raise ValueError(
                "Postgres settings must be provided (POSTGRES_HOST, POSTGRES_DATABASE, POSTGRES_USER)."
            )

        try:  # Lazy import so sqlite-only environments keep working
            import psycopg2  # type: ignore
            from psycopg2.extras import RealDictCursor  # type: ignore
        except ImportError as exc:  # pragma: no cover - only raised if dependency missing
            raise RuntimeError(
                "psycopg2 is required to use the Postgres SEC fact store. Install psycopg2-binary."
            ) from exc

        self._psycopg2 = psycopg2
        self._cursor_factory = RealDictCursor
        self._params = _PostgresParams(
            host=settings.postgres_host,
            port=settings.postgres_port or 5432,
            dbname=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
            schema=settings.postgres_schema or "sec",
        )

    @contextmanager
    def _connection(self) -> Iterator["psycopg2.extensions.connection"]:  # type: ignore[name-defined]
        """Yield a Postgres connection using application settings."""
        conn = self._psycopg2.connect(
            host=self._params.host,
            port=self._params.port,
            dbname=self._params.dbname,
            user=self._params.user,
            password=self._params.password,
        )
        try:
            yield conn
        finally:
            conn.close()

    def fetch_base_facts(
        self,
        metrics: Sequence[str],
        *,
        tickers: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch base fact rows for the requested metrics/tickers."""
        if not metrics:
            return []

        schema = self._params.schema
        filters = ["f.metric = ANY(%s)", "f.fy IS NOT NULL"]
        params: List[Any] = [list(metrics)]

        if tickers:
            filters.append("tc.ticker = ANY(%s)")
            params.append([ticker.upper() for ticker in tickers])

        query = f"""
            SELECT tc.ticker,
                   f.metric,
                   f.fy AS fiscal_year,
                   f.fp AS fiscal_period,
                   f.val AS value,
                   f.period_end,
                   f.filed,
                   f.taxonomy
            FROM {schema}.facts AS f
            JOIN {schema}.ticker_cik AS tc
              ON tc.cik = f.cik
            WHERE {' AND '.join(filters)}
        """

        with self._connection() as conn:
            with conn.cursor(cursor_factory=self._cursor_factory) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            ticker = (row.get("ticker") or "").upper()
            fiscal_year = row.get("fiscal_year")
            if not ticker or fiscal_year is None:
                continue
            fiscal_period = row.get("fiscal_period")
            period = _period_label(fiscal_year, fiscal_period)
            filed_at = _to_datetime(row.get("filed")) or _to_datetime(row.get("period_end"))
            results.append(
                {
                    "ticker": ticker,
                    "metric": (row.get("metric") or "").lower(),
                    "fiscal_year": fiscal_year,
                    "period": period,
                    "value": row.get("value"),
                    "source": "derived" if (row.get("taxonomy") or "").lower() == "derived" else "edgar",
                    "ingested_at": (filed_at or datetime.now(timezone.utc)).isoformat(),
                }
            )
        return results

    def fetch_financial_facts(
        self,
        ticker: str,
        *,
        fiscal_year: Optional[int] = None,
        metric: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[FinancialFactRecord]:
        """Fetch detailed financial fact rows from Postgres."""
        schema = self._params.schema
        clauses = ["tc.ticker = %s"]
        params: List[Any] = [ticker.upper()]

        if fiscal_year is not None:
            clauses.append("f.fy = %s")
            params.append(fiscal_year)
        if metric is not None:
            clauses.append("f.metric = %s")
            params.append(metric.lower())

        order_by = "ORDER BY f.fy DESC NULLS LAST, f.period_end DESC NULLS LAST, f.metric ASC"
        query = f"""
            SELECT f.metric,
                   f.fy,
                   f.fp,
                   f.val,
                   f.unit,
                   f.form,
                   f.filed,
                   f.period_start,
                   f.period_end,
                   f.accn,
                   f.taxonomy,
                   tc.cik
            FROM {schema}.facts AS f
            JOIN {schema}.ticker_cik AS tc
              ON tc.cik = f.cik
            WHERE {' AND '.join(clauses)}
            {order_by}
        """

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        with self._connection() as conn:
            with conn.cursor(cursor_factory=self._cursor_factory) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        records: List[FinancialFactRecord] = []
        for row in rows:
            fiscal_year_row = row.get("fy")
            fiscal_period = row.get("fp")
            period = _period_label(fiscal_year_row, fiscal_period)
            filed = _to_datetime(row.get("filed"))
            period_start = _to_datetime(row.get("period_start"))
            period_end = _to_datetime(row.get("period_end"))
            form = (row.get("form") or "")
            taxonomy = (row.get("taxonomy") or "").lower()
            accession = row.get("accn")
            raw_payload = {
                "accn": accession,
                "form": form or None,
                "filed": filed.isoformat() if filed else None,
                "fy": fiscal_year_row,
                "fp": fiscal_period,
            }
            records.append(
                FinancialFactRecord(
                    ticker=ticker.upper(),
                    metric=(row.get("metric") or "").lower(),
                    fiscal_year=fiscal_year_row,
                    fiscal_period=fiscal_period,
                    period=period,
                    value=row.get("val"),
                    unit=row.get("unit"),
                    source="derived" if taxonomy == "derived" else "edgar",
                    source_filing=row.get("accn"),
                    period_start=period_start,
                    period_end=period_end,
                    adjusted=form.endswith("/A"),
                    adjustment_note=form or None,
                    ingested_at=filed,
                    cik=row.get("cik"),
                    raw=raw_payload,
                )
            )
        return records

    def list_tickers(self) -> List[str]:
        """Return a list of tickers available in the SEC Postgres store."""
        schema = self._params.schema
        query = f"SELECT DISTINCT ticker FROM {schema}.ticker_cik ORDER BY ticker"
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return [str(row[0]).upper() for row in rows if row and row[0]]
