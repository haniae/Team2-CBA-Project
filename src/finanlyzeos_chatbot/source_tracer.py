"""
Source Tracing and Data Lineage System

Provides full traceability from calculated metrics back to their source data,
enabling drill-downs and audit trails.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import database

LOGGER = logging.getLogger(__name__)


@dataclass
class SourceTrace:
    """Represents a complete trace from a metric back to its sources."""
    ticker: str
    metric: str
    period: str
    value: Optional[float]
    trace_path: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "period": self.period,
            "value": self.value,
            "trace_path": self.trace_path,
            "sources": self.sources,
        }


@dataclass
class FactDetail:
    """Detailed information about a financial fact."""
    fact_id: int
    ticker: str
    metric: str
    fiscal_year: Optional[int]
    fiscal_period: Optional[str]
    value: Optional[float]
    unit: Optional[str]
    source_filing: Optional[str]
    source_url: Optional[str]
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    raw_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fact_id": self.fact_id,
            "ticker": self.ticker,
            "metric": self.metric,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period,
            "value": self.value,
            "unit": self.unit,
            "source_filing": self.source_filing,
            "source_url": self.source_url,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "raw_data": self.raw_data,
        }


class SourceTracer:
    """Traces data lineage from metrics to their sources."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def trace_metric(
        self,
        ticker: str,
        metric: str,
        period: Optional[str] = None,
        fiscal_year: Optional[int] = None
    ) -> SourceTrace:
        """Trace a metric back to its sources."""
        trace_path = []
        sources = []
        
        # Step 1: Check metric_snapshots
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get metric snapshot
            query = """
                SELECT value, period, start_year, end_year, source, updated_at
                FROM metric_snapshots
                WHERE ticker = ? AND metric = ?
            """
            params = [ticker.upper(), metric.lower()]
            
            if fiscal_year:
                query += " AND (end_year = ? OR start_year = ?)"
                params.extend([fiscal_year, fiscal_year])
            elif period:
                query += " AND period = ?"
                params.append(period)
            
            query += " ORDER BY updated_at DESC LIMIT 1"
            
            snapshot = conn.execute(query, params).fetchone()
            value = None
            
            if snapshot:
                value = snapshot["value"]
                trace_path.append({
                    "step": "metric_snapshot",
                    "description": f"Metric snapshot from {snapshot['source']}",
                    "value": value,
                    "period": snapshot["period"],
                    "updated_at": snapshot["updated_at"],
                })
            
            # Step 2: Trace to financial_facts
            if snapshot and snapshot["source"] == "edgar":
                facts = self._get_facts_for_metric(
                    conn, ticker, metric, period, fiscal_year
                )
                
                for fact in facts:
                    fact_detail = self._get_fact_detail(conn, fact["id"])
                    if fact_detail:
                        sources.append(fact_detail.to_dict())
                        trace_path.append({
                            "step": "financial_fact",
                            "description": f"Financial fact from {fact_detail.source_filing}",
                            "fact_id": fact_detail.fact_id,
                            "value": fact_detail.value,
                            "source_filing": fact_detail.source_filing,
                            "source_url": fact_detail.source_url,
                        })
            
            # Step 3: Trace to filings
            filing_sources = self._get_filing_sources(conn, ticker, metric, period, fiscal_year)
            for filing in filing_sources:
                sources.append(filing)
                trace_path.append({
                    "step": "filing",
                    "description": f"SEC filing: {filing.get('form_type', 'Unknown')}",
                    "filing_id": filing.get("id"),
                    "accession_number": filing.get("accession_number"),
                    "filed_at": filing.get("filed_at"),
                    "sec_url": filing.get("sec_url"),
                })
        
        return SourceTrace(
            ticker=ticker,
            metric=metric,
            period=period or "latest",
            value=value,
            trace_path=trace_path,
            sources=sources,
        )
    
    def _get_facts_for_metric(
        self,
        conn: sqlite3.Connection,
        ticker: str,
        metric: str,
        period: Optional[str],
        fiscal_year: Optional[int]
    ) -> List[sqlite3.Row]:
        """Get financial facts for a metric."""
        query = """
            SELECT id, value, fiscal_year, fiscal_period, source_filing
            FROM financial_facts
            WHERE ticker = ? AND metric = ?
        """
        params = [ticker.upper(), metric.lower()]
        
        if fiscal_year:
            query += " AND fiscal_year = ?"
            params.append(fiscal_year)
        elif period:
            query += " AND period = ?"
            params.append(period)
        
        query += " ORDER BY ingested_at DESC LIMIT 10"
        
        return conn.execute(query, params).fetchall()
    
    def _get_fact_detail(self, conn: sqlite3.Connection, fact_id: int) -> Optional[FactDetail]:
        """Get detailed information about a financial fact."""
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT 
                id, ticker, metric, fiscal_year, fiscal_period, value, unit,
                source_filing, period_start, period_end, raw, cik
            FROM financial_facts
            WHERE id = ?
            """,
            (fact_id,),
        ).fetchone()
        
        if not row:
            return None
        
        # Build SEC URL
        source_url = None
        if row["source_filing"] and row["cik"]:
            source_url = self._build_sec_url(row["source_filing"], row["cik"])
        
        # Parse raw data
        import json
        raw_data = {}
        if row["raw"]:
            try:
                raw_data = json.loads(row["raw"]) if isinstance(row["raw"], str) else row["raw"]
            except:
                pass
        
        # Parse dates
        period_start = None
        period_end = None
        if row["period_start"]:
            try:
                period_start = datetime.fromisoformat(row["period_start"])
            except:
                pass
        if row["period_end"]:
            try:
                period_end = datetime.fromisoformat(row["period_end"])
            except:
                pass
        
        return FactDetail(
            fact_id=row["id"],
            ticker=row["ticker"],
            metric=row["metric"],
            fiscal_year=row["fiscal_year"],
            fiscal_period=row["fiscal_period"],
            value=row["value"],
            unit=row["unit"],
            source_filing=row["source_filing"],
            source_url=source_url,
            period_start=period_start,
            period_end=period_end,
            raw_data=raw_data,
        )
    
    def _get_filing_sources(
        self,
        conn: sqlite3.Connection,
        ticker: str,
        metric: str,
        period: Optional[str],
        fiscal_year: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Get SEC filing sources for a metric."""
        # Get unique filings from financial_facts
        query = """
            SELECT DISTINCT source_filing, cik
            FROM financial_facts
            WHERE ticker = ? AND metric = ?
        """
        params = [ticker.upper(), metric.lower()]
        
        if fiscal_year:
            query += " AND fiscal_year = ?"
            params.append(fiscal_year)
        
        fact_rows = conn.execute(query, params).fetchall()
        
        filings = []
        for row in fact_rows:
            if not row[0]:  # source_filing
                continue
            
            # Parse source_filing format (e.g., "10-K/0001234567-23-000123")
            parts = row[0].split("/")
            form_type = parts[0] if parts else "Unknown"
            accession = parts[1] if len(parts) > 1 else None
            
            # Get filing details from company_filings
            if accession:
                conn.row_factory = sqlite3.Row
                filing_row = conn.execute(
                    """
                    SELECT id, form_type, filed_at, accession_number, period_of_report
                    FROM company_filings
                    WHERE accession_number = ?
                    """,
                    (accession,),
                ).fetchone()
                
                if filing_row:
                    cik = row[1] if len(row) > 1 else None
                    sec_url = self._build_sec_url(accession, cik) if cik else None
                    
                    filings.append({
                        "id": filing_row["id"],
                        "form_type": filing_row["form_type"],
                        "filed_at": filing_row["filed_at"],
                        "accession_number": filing_row["accession_number"],
                        "period_of_report": filing_row["period_of_report"],
                        "sec_url": sec_url,
                    })
        
        return filings
    
    def _build_sec_url(self, accession: str, cik: str) -> Optional[str]:
        """Build SEC EDGAR URL from accession number and CIK."""
        if not accession or not cik:
            return None
        
        clean_cik = cik.lstrip("0") or cik
        acc_no_dash = accession.replace("-", "")
        
        return f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={clean_cik}&accession_number={accession}&xbrl_type=v"
    
    def get_fact_drilldown(self, fact_id: int) -> Optional[FactDetail]:
        """Get detailed drill-down information for a specific fact."""
        with sqlite3.connect(self.db_path) as conn:
            return self._get_fact_detail(conn, fact_id)
    
    def get_metric_lineage(
        self,
        ticker: str,
        metric: str,
        period: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get complete data lineage for a metric."""
        trace = self.trace_metric(ticker, metric, period)
        
        # Build lineage graph
        lineage = {
            "metric": {
                "ticker": ticker,
                "name": metric,
                "period": trace.period,
                "value": trace.value,
            },
            "sources": trace.sources,
            "trace_path": trace.trace_path,
        }
        
        return lineage



