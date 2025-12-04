"""Finance Studio consolidation engine for multi-source data aggregation."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel

from . import database, load_settings

LOGGER = logging.getLogger(__name__)


class SourceConfig(BaseModel):
    """Configuration for a data source."""
    source_id: str  # e.g., 'excel', 'edgar', 'internal_db', 'google_sheets'
    connection_info: Dict  # generic payload, details vary per source


class ConsolidationFilters(BaseModel):
    """Filters for consolidation queries."""
    entities: Optional[List[str]] = None
    periods: Optional[List[str]] = None  # e.g., ['2025-Q1', '2025-Q2', '2025-Q3']
    scenarios: Optional[List[str]] = None  # e.g., ['Actual', 'Budget', 'Forecast']


class ConsolidatedRow(BaseModel):
    """A single row in a consolidated financial table."""
    line_item: str
    entity: Optional[str] = None
    period: Optional[str] = None
    scenario: Optional[str] = None
    actual: Optional[float] = None
    budget: Optional[float] = None
    forecast: Optional[float] = None
    variance_abs: Optional[float] = None
    variance_pct: Optional[float] = None
    level: Optional[str] = None  # 'parent', 'child', 'grandchild'


class ConsolidatedTable(BaseModel):
    """A consolidated financial table."""
    view: str  # 'pl', 'cashflow', 'balance_sheet', 'kpi', 'variance'
    period_label: Optional[str] = None
    rows: List[ConsolidatedRow]


class ConsolidationRequest(BaseModel):
    """Request model for consolidation endpoint."""
    sources: List[SourceConfig]
    filters: ConsolidationFilters
    view: str = "pl"


def consolidate_data(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
    view: str = "pl",
) -> ConsolidatedTable:
    """
    Consolidate data from multiple sources into a unified financial table.
    
    Steps:
    1. Load data from sources
    2. Normalize to a single schema: account/line_item, entity, period, scenario, amount, currency
    3. Union into one table
    4. Aggregate by (line_item, entity, period, scenario)
    5. Compute derived metrics like Gross Profit, EBITDA, variance_abs, variance_pct
    6. Return ConsolidatedTable
    """
    LOGGER.info(f"Consolidating data from {len(sources)} sources with view={view}")
    
    # Check if we should fetch from database
    use_db = any(s.source_id in ['internal_db', 'edgar'] for s in sources)
    
    if use_db:
        return consolidate_from_database(sources, filters, view)
    
    # Fallback to sample data for other sources
    return consolidate_sample_data(sources, filters, view)


def consolidate_from_database(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
    view: str = "pl",
) -> ConsolidatedTable:
    """Consolidate data from the internal database (S&P 1500 companies)."""
    try:
        settings = load_settings()
        db_path = Path(settings.database_path)
        
        # Map line items to database metrics
        metric_mapping = {
            "Revenue": ["revenue", "total_revenue", "net_sales", "sales"],
            "COGS": ["cost_of_revenue", "cogs", "cost_of_goods_sold"],
            "Gross Profit": ["gross_profit", "gross_income"],
            "R&D": ["research_and_development", "r_and_d", "rd_expense"],
            "S&M": ["selling_general_and_administrative", "sga", "sales_and_marketing"],
            "G&A": ["general_and_administrative", "ga_expense"],
            "Total OpEx": ["operating_expenses", "total_opex", "operating_expense"],
            "EBITDA": ["ebitda", "earnings_before_interest_taxes_depreciation_amortization"],
        }
        
        # Get S&P 1500 tickers
        # Use the database connection helper
        from .database import temporary_connection
        
        with temporary_connection(db_path) as conn:
            # Get all unique tickers from kpi_values or metric_snapshots
            tickers_query = """
                SELECT DISTINCT ticker 
                FROM kpi_values 
                WHERE ticker IS NOT NULL AND ticker != ''
                UNION
                SELECT DISTINCT ticker 
                FROM metric_snapshots 
                WHERE ticker IS NOT NULL AND ticker != ''
                LIMIT 1500
            """
            ticker_rows = conn.execute(tickers_query).fetchall()
            all_tickers = [row[0].upper() for row in ticker_rows if row[0]]
            
            if not all_tickers:
                LOGGER.warning("No tickers found in database, falling back to sample data")
                return consolidate_sample_data(sources, filters, view)
            
            LOGGER.info(f"Found {len(all_tickers)} tickers in database")
            
            # Parse periods
            periods = filters.periods or ["2025-Q1", "2025-Q2", "2025-Q3"]
            entities = filters.entities or ["Global"]
            
            rows: List[ConsolidatedRow] = []
            
            # For each line item, aggregate across tickers
            for line_item, metric_aliases in metric_mapping.items():
                # Try to find the metric in the database
                metric_found = None
                for alias in metric_aliases:
                    # Check if this metric exists
                    check_query = """
                        SELECT COUNT(*) FROM kpi_values 
                        WHERE metric_id LIKE ? OR metric_id = ?
                        LIMIT 1
                    """
                    count = conn.execute(check_query, (f"%{alias}%", alias)).fetchone()[0]
                    if count > 0:
                        metric_found = alias
                        break
                
                if not metric_found:
                    # Try metric_snapshots
                    for alias in metric_aliases:
                        check_query = """
                            SELECT COUNT(*) FROM metric_snapshots 
                            WHERE metric LIKE ? OR metric = ?
                            LIMIT 1
                        """
                        count = conn.execute(check_query, (f"%{alias}%", alias)).fetchone()[0]
                        if count > 0:
                            metric_found = alias
                            break
                
                # If metric found, aggregate data
                if metric_found:
                    for period in periods:
                        # Parse period (e.g., "2025-Q1" -> year=2025, quarter=1)
                        year = int(period.split('-')[0]) if '-' in period else int(period)
                        quarter = None
                        if 'Q' in period:
                            try:
                                quarter = int(period.split('Q')[1])
                            except:
                                pass
                        
                        # Aggregate across all tickers (or filtered entities if they map to tickers)
                        for entity in entities:
                            # Query kpi_values
                            query = """
                                SELECT SUM(value) as total_value, COUNT(*) as count
                                FROM kpi_values
                                WHERE metric_id LIKE ? 
                                AND fiscal_year = ?
                            """
                            params = [f"%{metric_found}%", year]
                            
                            if quarter:
                                query += " AND fiscal_quarter = ?"
                                params.append(quarter)
                            
                            result = conn.execute(query, params).fetchone()
                            total_value = result[0] if result and result[0] else 0
                            
                            # Also try metric_snapshots
                            query2 = """
                                SELECT SUM(value) as total_value, COUNT(*) as count
                                FROM metric_snapshots
                                WHERE metric LIKE ?
                                AND period LIKE ?
                            """
                            period_pattern = f"{year}%"
                            if quarter:
                                period_pattern = f"{year}-Q{quarter}%"
                            
                            result2 = conn.execute(query2, (f"%{metric_found}%", period_pattern)).fetchone()
                            total_value2 = result2[0] if result2 and result2[0] else 0
                            
                            # Use the larger value or sum
                            actual = max(total_value, total_value2) if (total_value > 0 or total_value2 > 0) else None
                            
                            # If we have aggregated data, use it; otherwise try per-ticker aggregation
                            if (actual is None or actual == 0) and all_tickers:
                                # Aggregate per ticker and sum
                                per_ticker_query = """
                                    SELECT ticker, SUM(value) as ticker_value
                                    FROM kpi_values
                                    WHERE metric_id LIKE ?
                                    AND fiscal_year = ?
                                    AND ticker IN ({})
                                    GROUP BY ticker
                                """.format(','.join(['?' for _ in all_tickers[:100]]))  # Limit to 100 tickers for performance
                                
                                params_pt = [f"%{metric_found}%", year] + all_tickers[:100]
                                if quarter:
                                    per_ticker_query = per_ticker_query.replace('AND fiscal_year = ?', 'AND fiscal_year = ? AND fiscal_quarter = ?')
                                    params_pt.insert(2, quarter)
                                
                                try:
                                    ticker_results = conn.execute(per_ticker_query, params_pt).fetchall()
                                    actual = sum(row[1] for row in ticker_results if row[1]) if ticker_results else 0
                                except Exception as e:
                                    LOGGER.warning(f"Error in per-ticker aggregation: {e}")
                            
                            if actual and actual > 0:
                                # Calculate budget and forecast (for now, use simple multipliers)
                                budget = actual * 1.05
                                forecast = actual * 1.02
                                variance_abs = actual - budget
                                variance_pct = (variance_abs / budget * 100) if budget != 0 else 0.0
                                
                                # Determine level
                                level = "parent" if line_item in ["Revenue", "Gross Profit", "Total OpEx", "EBITDA"] else "child"
                                
                                rows.append(ConsolidatedRow(
                                    line_item=line_item,
                                    entity=entity,
                                    period=period,
                                    scenario="Actual",
                                    actual=round(actual, 2),
                                    budget=round(budget, 2),
                                    forecast=round(forecast, 2),
                                    variance_abs=round(variance_abs, 2),
                                    variance_pct=round(variance_pct, 2),
                                    level=level,
                                ))
            
            # If we got data, return it
            if rows:
                # Calculate derived metrics
                rows = calculate_derived_metrics(rows)
                return ConsolidatedTable(
                    view=view,
                    period_label=f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else periods[0],
                    rows=rows,
                )
            else:
                LOGGER.warning("No data found in database, falling back to sample data")
                return consolidate_sample_data(sources, filters, view)
                
    except Exception as e:
        LOGGER.error(f"Error consolidating from database: {e}", exc_info=True)
        # Fallback to sample data on error
        return consolidate_sample_data(sources, filters, view)


def calculate_derived_metrics(rows: List[ConsolidatedRow]) -> List[ConsolidatedRow]:
    """Calculate derived metrics like Gross Profit, Total OpEx, EBITDA from base metrics."""
    # Group by period and entity
    grouped: Dict[tuple, Dict[str, float]] = {}
    
    for row in rows:
        key = (row.period, row.entity)
        if key not in grouped:
            grouped[key] = {}
        grouped[key][row.line_item] = row.actual or 0
    
    # Calculate Gross Profit = Revenue - COGS
    for key, values in grouped.items():
        revenue = values.get("Revenue", 0)
        cogs = values.get("COGS", 0)
        if revenue > 0 and cogs > 0:
            gross_profit = revenue - cogs
            # Update or add Gross Profit row
            for row in rows:
                if row.line_item == "Gross Profit" and row.period == key[0] and row.entity == key[1]:
                    row.actual = round(gross_profit, 2)
                    row.budget = round(gross_profit * 1.05, 2) if row.budget else None
                    row.forecast = round(gross_profit * 1.02, 2) if row.forecast else None
                    break
    
    # Calculate Total OpEx = R&D + S&M + G&A
    for key, values in grouped.items():
        rd = values.get("R&D", 0)
        sm = values.get("S&M", 0)
        ga = values.get("G&A", 0)
        total_opex = rd + sm + ga
        if total_opex > 0:
            for row in rows:
                if row.line_item == "Total OpEx" and row.period == key[0] and row.entity == key[1]:
                    row.actual = round(total_opex, 2)
                    row.budget = round(total_opex * 1.05, 2) if row.budget else None
                    row.forecast = round(total_opex * 1.02, 2) if row.forecast else None
                    break
    
    # Calculate EBITDA = Gross Profit - Total OpEx
    for key, values in grouped.items():
        gross_profit = values.get("Gross Profit", 0)
        total_opex = values.get("Total OpEx", 0)
        if gross_profit > 0:
            ebitda = gross_profit - total_opex
            for row in rows:
                if row.line_item == "EBITDA" and row.period == key[0] and row.entity == key[1]:
                    row.actual = round(ebitda, 2)
                    row.budget = round(ebitda * 1.05, 2) if row.budget else None
                    row.forecast = round(ebitda * 1.02, 2) if row.forecast else None
                    break
    
    return rows


def consolidate_sample_data(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
    view: str = "pl",
) -> ConsolidatedTable:
    """Generate sample data when database is not available."""
    LOGGER.info("Using sample data for consolidation")
    
    # Sample P&L structure
    pl_structure = [
        {"line_item": "Revenue", "level": "parent", "order": 1},
        {"line_item": "COGS", "level": "child", "order": 2},
        {"line_item": "Gross Profit", "level": "parent", "order": 3},
        {"line_item": "R&D", "level": "child", "order": 4},
        {"line_item": "S&M", "level": "child", "order": 5},
        {"line_item": "G&A", "level": "child", "order": 6},
        {"line_item": "Total OpEx", "level": "parent", "order": 7},
        {"line_item": "EBITDA", "level": "parent", "order": 8},
    ]
    
    # Generate sample periods if not provided
    periods = filters.periods or ["2025-Q1", "2025-Q2", "2025-Q3"]
    entities = filters.entities or ["Global", "EMEA", "Americas", "APAC"]
    scenarios = filters.scenarios or ["Actual", "Budget", "Forecast"]
    
    rows: List[ConsolidatedRow] = []
    
    # Generate sample data for each line item
    for item in pl_structure:
        for period in periods:
            for entity in entities:
                # Generate base values
                base_actual = 1000000.0 if item["line_item"] == "Revenue" else 500000.0
                base_budget = base_actual * 1.05
                base_forecast = base_actual * 1.02
                
                # Add some variation
                import random
                random.seed(hash(f"{item['line_item']}{period}{entity}"))
                variation = random.uniform(0.9, 1.1)
                actual = base_actual * variation
                budget = base_budget * variation
                forecast = base_forecast * variation
                
                # Calculate variance
                variance_abs = actual - budget
                variance_pct = (variance_abs / budget * 100) if budget != 0 else 0.0
                
                # For derived metrics, calculate from children
                if item["line_item"] == "Gross Profit":
                    # Would normally sum Revenue - COGS, but for stub, use formula
                    actual = actual * 0.6
                    budget = budget * 0.6
                    forecast = forecast * 0.6
                elif item["line_item"] == "Total OpEx":
                    # Sum of R&D, S&M, G&A
                    actual = actual * 0.3
                    budget = budget * 0.3
                    forecast = forecast * 0.3
                elif item["line_item"] == "EBITDA":
                    # Gross Profit - Total OpEx
                    actual = actual * 0.3
                    budget = budget * 0.3
                    forecast = forecast * 0.3
                
                row = ConsolidatedRow(
                    line_item=item["line_item"],
                    entity=entity,
                    period=period,
                    scenario="Actual",
                    actual=round(actual, 2),
                    budget=round(budget, 2),
                    forecast=round(forecast, 2),
                    variance_abs=round(variance_abs, 2),
                    variance_pct=round(variance_pct, 2),
                    level=item["level"],
                )
                rows.append(row)
    
    return ConsolidatedTable(
        view=view,
        period_label=f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else periods[0],
        rows=rows,
    )
    
    # Sample P&L structure
    pl_structure = [
        {"line_item": "Revenue", "level": "parent", "order": 1},
        {"line_item": "COGS", "level": "child", "order": 2},
        {"line_item": "Gross Profit", "level": "parent", "order": 3},
        {"line_item": "R&D", "level": "child", "order": 4},
        {"line_item": "S&M", "level": "child", "order": 5},
        {"line_item": "G&A", "level": "child", "order": 6},
        {"line_item": "Total OpEx", "level": "parent", "order": 7},
        {"line_item": "EBITDA", "level": "parent", "order": 8},
    ]
    
    # Generate sample periods if not provided
    periods = filters.periods or ["2025-Q1", "2025-Q2", "2025-Q3"]
    entities = filters.entities or ["Global", "EMEA", "Americas", "APAC"]
    scenarios = filters.scenarios or ["Actual", "Budget", "Forecast"]
    
    rows: List[ConsolidatedRow] = []
    
    # Generate sample data for each line item
    for item in pl_structure:
        for period in periods:
            for entity in entities:
                # Generate base values
                base_actual = 1000000.0 if item["line_item"] == "Revenue" else 500000.0
                base_budget = base_actual * 1.05
                base_forecast = base_actual * 1.02
                
                # Add some variation
                import random
                random.seed(hash(f"{item['line_item']}{period}{entity}"))
                variation = random.uniform(0.9, 1.1)
                actual = base_actual * variation
                budget = base_budget * variation
                forecast = base_forecast * variation
                
                # Calculate variance
                variance_abs = actual - budget
                variance_pct = (variance_abs / budget * 100) if budget != 0 else 0.0
                
                # For derived metrics, calculate from children
                if item["line_item"] == "Gross Profit":
                    # Would normally sum Revenue - COGS, but for stub, use formula
                    actual = actual * 0.6
                    budget = budget * 0.6
                    forecast = forecast * 0.6
                elif item["line_item"] == "Total OpEx":
                    # Sum of R&D, S&M, G&A
                    actual = actual * 0.3
                    budget = budget * 0.3
                    forecast = forecast * 0.3
                elif item["line_item"] == "EBITDA":
                    # Gross Profit - Total OpEx
                    actual = actual * 0.3
                    budget = budget * 0.3
                    forecast = forecast * 0.3
                
                row = ConsolidatedRow(
                    line_item=item["line_item"],
                    entity=entity,
                    period=period,
                    scenario="Actual",
                    actual=round(actual, 2),
                    budget=round(budget, 2),
                    forecast=round(forecast, 2),
                    variance_abs=round(variance_abs, 2),
                    variance_pct=round(variance_pct, 2),
                    level=item["level"],
                )
                rows.append(row)
    
    return ConsolidatedTable(
        view=view,
        period_label=f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else periods[0],
        rows=rows,
    )


def get_pl_consolidation(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
) -> ConsolidatedTable:
    """Get P&L consolidation view."""
    return consolidate_data(sources, filters, view="pl")


def get_variance_analysis(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
) -> ConsolidatedTable:
    """Get variance analysis view."""
    table = consolidate_data(sources, filters, view="variance")
    # Filter to only show rows with significant variance
    table.rows = [
        row for row in table.rows
        if row.variance_pct and abs(row.variance_pct) > 1.0
    ]
    return table


def get_three_statement_data(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
    statement_type: str = "pl",
) -> ConsolidatedTable:
    """Get three-statement data (P&L, Balance Sheet, or Cash Flow)."""
    return consolidate_data(sources, filters, view=statement_type)


def get_visualization_data(
    sources: List[SourceConfig],
    filters: ConsolidationFilters,
) -> Dict:
    """Get data formatted for visualization dashboards."""
    table = consolidate_data(sources, filters, view="kpi")
    
    # Aggregate for KPIs
    total_revenue = sum(
        row.actual or 0
        for row in table.rows
        if row.line_item == "Revenue"
    )
    
    total_gross_profit = sum(
        row.actual or 0
        for row in table.rows
        if row.line_item == "Gross Profit"
    )
    
    total_ebitda = sum(
        row.actual or 0
        for row in table.rows
        if row.line_item == "EBITDA"
    )
    
    gross_profit_pct = (total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    ebitda_pct = (total_ebitda / total_revenue * 100) if total_revenue > 0 else 0
    
    # Group by entity for charts
    entity_data: Dict[str, Dict] = {}
    for row in table.rows:
        if row.entity and row.line_item == "Revenue":
            if row.entity not in entity_data:
                entity_data[row.entity] = {"revenue": 0, "gross_profit": 0}
            entity_data[row.entity]["revenue"] += row.actual or 0
    
    return {
        "kpis": {
            "total_revenue": round(total_revenue, 2),
            "gross_profit": round(total_gross_profit, 2),
            "gross_profit_pct": round(gross_profit_pct, 2),
            "ebitda": round(total_ebitda, 2),
            "ebitda_pct": round(ebitda_pct, 2),
        },
        "entity_breakdown": entity_data,
        "periods": list(set(row.period for row in table.rows if row.period)),
        "raw_data": table,
    }


def get_drilldown_transactions(
    line_item: str,
    entity: Optional[str],
    period: Optional[str],
    statement_type: str,
    scenario: Optional[str] = None,
) -> List[Dict]:
    """Get transaction-level detail for drill-down."""
    # Stub: return sample transaction data
    import random
    random.seed(hash(f"{line_item}{entity}{period}{scenario}"))
    
    transactions = []
    num_transactions = random.randint(5, 15)
    
    for i in range(num_transactions):
        transactions.append({
            "date": f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "entity": entity or "Global",
            "cost_center": f"CC-{random.randint(1000, 9999)}",
            "account": f"Account-{random.randint(100, 999)}",
            "amount": round(random.uniform(1000, 50000), 2),
            "description": f"Transaction for {line_item} - {random.choice(['Invoice', 'Payment', 'Adjustment', 'Accrual'])}",
        })
    
    return transactions

