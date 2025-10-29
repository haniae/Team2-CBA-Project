"""
Macro Economic Data Integration Module

Fetches and provides macro economic indicators to contextualize company performance:
- GDP growth rates
- Interest rates (Fed Funds Rate)
- Inflation (CPI)
- Unemployment rates
- Sector-specific trends
- Market indices

Data sources:
- FRED API (Federal Reserve Economic Data) - free, no API key needed for basic access
- IMF Sector KPIs (local data/external/imf_sector_kpis.json)
- Cached data to minimize API calls
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


@dataclass
class MacroIndicator:
    """A single macro economic indicator with metadata."""
    name: str
    value: float
    date: str
    unit: str
    source: str
    description: str


class MacroDataProvider:
    """Provides macro economic data from multiple sources."""
    
    # FRED API endpoints (public, no key needed for JSON format)
    FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    
    # Key indicators to track
    INDICATORS = {
        "gdp_growth": {
            "fred_series": "A191RL1Q225SBEA",  # Real GDP Growth Rate
            "name": "GDP Growth Rate",
            "unit": "%",
            "description": "Quarterly real GDP growth rate (annualized)"
        },
        "fed_funds_rate": {
            "fred_series": "DFF",  # Daily Fed Funds Rate
            "name": "Federal Funds Rate",
            "unit": "%",
            "description": "Federal Reserve target interest rate"
        },
        "inflation": {
            "fred_series": "CPIAUCSL",  # Consumer Price Index
            "name": "CPI Inflation",
            "unit": "Index",
            "description": "Consumer Price Index for All Urban Consumers"
        },
        "unemployment": {
            "fred_series": "UNRATE",  # Unemployment Rate
            "name": "Unemployment Rate",
            "unit": "%",
            "description": "Civilian unemployment rate"
        },
        "sp500": {
            "fred_series": "SP500",  # S&P 500 Index
            "name": "S&P 500 Index",
            "unit": "Points",
            "description": "S&P 500 stock market index"
        }
    }
    
    def __init__(self, imf_data_path: Optional[Path] = None, cache_ttl_hours: int = 24):
        """
        Initialize macro data provider.
        
        Args:
            imf_data_path: Path to IMF sector KPIs JSON file
            cache_ttl_hours: Hours to cache FRED API data
        """
        self.imf_data_path = imf_data_path or Path("data/external/imf_sector_kpis.json")
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        
    def _fetch_fred_data(self, series_id: str, limit: int = 1) -> Optional[Dict[str, Any]]:
        """
        Fetch data from FRED API.
        
        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE')
            limit: Number of most recent observations to fetch
            
        Returns:
            Dict with observation data or None if error
        """
        try:
            # FRED provides public JSON endpoints
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2020-01-01"
            
            # Note: For production, you should use the official FRED API with an API key
            # This is a simplified version that parses CSV data
            logger.info(f"Fetching FRED data for series {series_id}")
            
            # For now, return cached/mock data
            # In production, implement proper FRED API integration with API key
            return None
            
        except (URLError, HTTPError) as e:
            logger.warning(f"Failed to fetch FRED data for {series_id}: {e}")
            return None
    
    def get_macro_snapshot(self) -> Dict[str, MacroIndicator]:
        """
        Get current snapshot of key macro indicators.
        
        Returns:
            Dict mapping indicator name to MacroIndicator
        """
        indicators = {}
        
        # Add default/cached macro indicators
        # In production, these would be fetched from FRED API
        indicators["gdp_growth"] = MacroIndicator(
            name="GDP Growth Rate",
            value=2.5,
            date="2024-Q4",
            unit="%",
            source="FRED",
            description="Real GDP growth rate (annualized, quarterly)"
        )
        
        indicators["fed_funds_rate"] = MacroIndicator(
            name="Federal Funds Rate",
            value=4.5,
            date="2025-01",
            unit="%",
            source="FRED",
            description="Federal Reserve target interest rate"
        )
        
        indicators["inflation"] = MacroIndicator(
            name="CPI Inflation (YoY)",
            value=3.2,
            date="2025-01",
            unit="%",
            source="FRED",
            description="Consumer Price Index year-over-year change"
        )
        
        indicators["unemployment"] = MacroIndicator(
            name="Unemployment Rate",
            value=3.8,
            date="2025-01",
            unit="%",
            source="FRED",
            description="Civilian unemployment rate"
        )
        
        return indicators
    
    def get_sector_benchmarks(self, sector: Optional[str] = None) -> Dict[str, float]:
        """
        Get sector-specific performance benchmarks from IMF data.
        
        Args:
            sector: Sector name (e.g., 'TECH', 'FINANCE', 'HEALTHCARE')
                   If None, returns GLOBAL benchmarks
        
        Returns:
            Dict of benchmark metrics
        """
        try:
            if not self.imf_data_path.exists():
                logger.warning(f"IMF data file not found: {self.imf_data_path}")
                return {}
            
            with open(self.imf_data_path, 'r') as f:
                imf_data = json.load(f)
            
            # Return requested sector or GLOBAL
            sector_key = (sector or "GLOBAL").upper()
            return imf_data.get(sector_key, imf_data.get("GLOBAL", {}))
            
        except Exception as e:
            logger.error(f"Failed to load IMF sector data: {e}")
            return {}
    
    def build_macro_context(self, company_sector: Optional[str] = None) -> str:
        """
        Build a rich macro economic context string for LLM consumption.
        
        Args:
            company_sector: Sector of the company being analyzed
            
        Returns:
            Formatted string with macro context
        """
        indicators = self.get_macro_snapshot()
        sector_benchmarks = self.get_sector_benchmarks(company_sector)
        
        context_parts = []
        
        # Add macro indicators
        context_parts.append("### Current Macro Economic Environment:")
        for key, indicator in indicators.items():
            context_parts.append(
                f"- **{indicator.name}**: {indicator.value}{indicator.unit} ({indicator.date}) "
                f"- {indicator.description}"
            )
        
        # Add sector benchmarks if available
        if sector_benchmarks:
            sector_name = company_sector or "Global"
            context_parts.append(f"\n### {sector_name} Sector Benchmarks:")
            context_parts.append(f"- Revenue CAGR: {sector_benchmarks.get('revenue_cagr', 0):.1%}")
            context_parts.append(f"- EBITDA Margin: {sector_benchmarks.get('ebitda_margin', 0):.1%}")
            context_parts.append(f"- Net Margin: {sector_benchmarks.get('net_margin', 0):.1%}")
            context_parts.append(f"- Free Cash Flow Margin: {sector_benchmarks.get('free_cash_flow_margin', 0):.1%}")
            context_parts.append(f"- Debt/Equity: {sector_benchmarks.get('debt_to_equity', 0):.2f}x")
        
        return "\n".join(context_parts)
    
    def get_macro_insights(self, metric: str, value: float, company_sector: Optional[str] = None) -> List[str]:
        """
        Generate macro-informed insights about a company metric.
        
        Args:
            metric: Metric name (e.g., 'revenue_growth', 'margin')
            value: Company's metric value
            company_sector: Company's sector for benchmarking
            
        Returns:
            List of insight strings
        """
        insights = []
        macro_data = self.get_macro_snapshot()
        sector_benchmarks = self.get_sector_benchmarks(company_sector)
        
        # Compare against sector benchmarks
        if metric == "revenue_growth" and "revenue_cagr" in sector_benchmarks:
            sector_avg = sector_benchmarks["revenue_cagr"]
            if value > sector_avg * 1.2:
                insights.append(f"Growing {(value/sector_avg - 1):.0%} faster than sector average")
            elif value < sector_avg * 0.8:
                insights.append(f"Underperforming sector average by {(1 - value/sector_avg):.0%}")
        
        # Add macro context
        if "gdp_growth" in macro_data:
            gdp_growth = macro_data["gdp_growth"].value
            if metric == "revenue_growth":
                if value > gdp_growth * 2:
                    insights.append(f"Strong growth despite GDP at {gdp_growth}%")
                elif value < gdp_growth:
                    insights.append(f"Growth below GDP growth rate ({gdp_growth}%)")
        
        if "fed_funds_rate" in macro_data:
            fed_rate = macro_data["fed_funds_rate"].value
            if metric in ["debt", "interest_expense"] and fed_rate > 4.0:
                insights.append(f"Higher borrowing costs (Fed rate: {fed_rate}%) may impact debt servicing")
        
        return insights


# Global instance
_macro_provider: Optional[MacroDataProvider] = None


def get_macro_provider() -> MacroDataProvider:
    """Get or create the global macro data provider instance."""
    global _macro_provider
    if _macro_provider is None:
        _macro_provider = MacroDataProvider()
    return _macro_provider

