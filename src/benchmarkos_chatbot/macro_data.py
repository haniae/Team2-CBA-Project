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
- FRED API (Federal Reserve Economic Data) - requires API key for reliable access
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
# Removed unused imports - no longer using CSV fallback
# from urllib.request import urlopen, Request
# from urllib.error import URLError, HTTPError

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
    
    # FRED API endpoints (requires API key)
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
            "fred_series": "CPIAUCSL",  # Consumer Price Index (needs YoY calculation)
            "name": "CPI Inflation",
            "unit": "%",
            "description": "Consumer Price Index YoY inflation rate (calculated from CPI index)"
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
    
    def __init__(self, imf_data_path: Optional[Path] = None, cache_ttl_hours: int = 24, fred_api_key: Optional[str] = None):
        """
        Initialize macro data provider.
        
        Args:
            imf_data_path: Path to IMF sector KPIs JSON file
            cache_ttl_hours: Default hours to cache FRED API data (can be overridden per indicator)
            fred_api_key: Optional FRED API key for real-time data (free from https://fred.stlouisfed.org/docs/api/api_key.html)
        """
        self.imf_data_path = imf_data_path or Path("data/external/imf_sector_kpis.json")
        self.default_cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # Smart caching: Different TTL based on indicator update frequency
        # Daily indicators (Fed Funds, S&P 500): 6 hours
        # Monthly indicators (CPI, Unemployment): 24 hours
        # Quarterly indicators (GDP): 7 days
        self.cache_ttl_map = {
            "gdp_growth": timedelta(days=7),      # Quarterly - update weekly
            "fed_funds_rate": timedelta(hours=6), # Daily - update 4x per day
            "inflation": timedelta(hours=24),     # Monthly - update daily
            "unemployment": timedelta(hours=24),  # Monthly - update daily
            "sp500": timedelta(hours=6),          # Daily - update 4x per day
        }
        
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self.fred_api_key = fred_api_key
        self._fred_client = None
        
        # Try to initialize FRED client if API key provided
        if fred_api_key:
            try:
                from fredapi import Fred
                self._fred_client = Fred(api_key=fred_api_key)
                logger.info("FRED client initialized successfully")
            except ImportError:
                logger.warning("fredapi not installed - install with: pip install fredapi")
            except Exception as e:
                logger.warning(f"Failed to initialize FRED client: {e}")
        
    def _fetch_fred_data(self, series_id: str, limit: int = 1, months_back: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch data from FRED API.
        
        Args:
            series_id: FRED series ID (e.g., 'A191RL1Q225SBEA', 'DFF', 'UNRATE', 'CPIAUCSL')
            limit: Number of most recent observations to fetch
            months_back: Optional number of months back to fetch (for YoY calculations, e.g., 12 for CPI)
            
        Returns:
            Dict with observation data or None if error.
            For CPI (CPIAUCSL) with months_back=12, returns YoY percentage change instead of index value.
        """
        # Use FRED client if available
        if self._fred_client:
            try:
                # For CPI YoY calculation, need 12+ months of data
                if series_id == "CPIAUCSL" and months_back:
                    logger.info(f"Fetching FRED data for series {series_id} (need {months_back} months for YoY calculation)")
                    # Fetch more data points to ensure we have enough months back
                    # CPI is monthly, so need months_back + 1 observations
                    data = self._fred_client.get_series(series_id, limit=months_back + 1)
                    if data is not None and not data.empty and len(data) >= months_back + 1:
                        latest_value = float(data.iloc[-1])
                        latest_date = data.index[-1]
                        # Find value from approximately 12 months ago
                        # Since data might not be exactly monthly aligned, take the earliest available
                        year_ago_idx = max(0, len(data) - months_back - 1)
                        year_ago_value = float(data.iloc[year_ago_idx])
                        year_ago_date = data.index[year_ago_idx]
                        
                        # Calculate YoY percentage change: ((current - year_ago) / year_ago) * 100
                        if year_ago_value > 0:
                            yoy_change = ((latest_value - year_ago_value) / year_ago_value) * 100
                        else:
                            logger.warning(f"Invalid year-ago CPI value: {year_ago_value}")
                            return None
                        
                        # Get series info
                        info = self._fred_client.get_series_info(series_id)
                        
                        logger.info(f"CPI YoY calculation: {latest_value:.2f} (current, {latest_date}) vs {year_ago_value:.2f} (year ago, {year_ago_date}) = {yoy_change:.2f}% YoY")
                        
                        return {
                            'value': yoy_change,  # Return YoY percentage, not index
                            'date': latest_date,
                            'title': info.get('title', f'FRED Series {series_id}'),
                            'units': 'Percent',
                            'frequency': info.get('frequency', ''),
                            'index_current': latest_value,
                            'index_year_ago': year_ago_value,
                        }
                else:
                    # Standard fetch for non-CPI or when months_back not specified
                    logger.info(f"Fetching FRED data for series {series_id}")
                    data = self._fred_client.get_series(series_id, limit=limit)
                    if data is not None and not data.empty:
                        latest_value = float(data.iloc[-1])
                        latest_date = data.index[-1]
                        
                        # Get series info
                        info = self._fred_client.get_series_info(series_id)
                        
                        return {
                            'value': latest_value,
                            'date': latest_date,
                            'title': info.get('title', series_id),
                            'units': info.get('units', ''),
                            'frequency': info.get('frequency', ''),
                        }
            except Exception as e:
                logger.warning(f"Failed to fetch FRED data for {series_id} via API: {e}")
                # If we have API key but it fails, don't fallback to CSV
                # Return None to use default values instead
                return None
        
        # No API key available - return None to use default values
        # We don't use CSV fallback anymore to ensure data quality and consistency
        logger.debug(f"No FRED API key available for {series_id}, will use default values")
        return None
    
    def get_macro_snapshot(self) -> Dict[str, MacroIndicator]:
        """
        Get current snapshot of key macro indicators.
        
        Attempts to fetch from FRED API if available, otherwise uses default values.
        
        Returns:
            Dict mapping indicator name to MacroIndicator
        """
        indicators = {}
        
        # Try to fetch from FRED API first, with fallback to defaults
        for key, config in self.INDICATORS.items():
            fred_series = config.get("fred_series")
            default_value = None
            default_date = None
            
            # Set defaults based on indicator type
            if key == "gdp_growth":
                default_value = 2.5
                default_date = "2024-Q4"
            elif key == "fed_funds_rate":
                default_value = 4.5
                default_date = "2025-01"
            elif key == "inflation":
                default_value = 3.2
                default_date = "2025-01"
            elif key == "unemployment":
                default_value = 3.8
                default_date = "2025-01"
            elif key == "sp500":
                default_value = 4500.0
                default_date = "2025-01"
            
            # Try to fetch from FRED
            value = default_value
            date = default_date
            source = "FRED (default)"
            
            if fred_series:
                # Get cache TTL for this specific indicator (smart caching)
                indicator_cache_ttl = self.cache_ttl_map.get(key, self.default_cache_ttl)
                
                # Check cache first
                cache_key = f"{key}_{fred_series}"
                if cache_key in self._cache:
                    cached_data, cached_time = self._cache[cache_key]
                    cache_age = datetime.now() - cached_time
                    if cache_age < indicator_cache_ttl:
                        logger.debug(f"Using cached FRED data for {key} (age: {cache_age}, TTL: {indicator_cache_ttl})")
                        value = cached_data.get('value', default_value)
                        date = str(cached_data.get('date', default_date))
                        source = "FRED (cached)"
                    else:
                        # Cache expired, remove it
                        logger.debug(f"Cache expired for {key} (age: {cache_age}, TTL: {indicator_cache_ttl})")
                        del self._cache[cache_key]
                
                # If not cached or expired, try to fetch
                if cache_key not in self._cache or datetime.now() - self._cache[cache_key][1] >= indicator_cache_ttl:
                    # For CPI inflation, need 12 months of data to calculate YoY
                    months_back = 12 if key == "inflation" and fred_series == "CPIAUCSL" else None
                    fred_data = self._fetch_fred_data(fred_series, months_back=months_back)
                    if fred_data and fred_data.get('value') is not None:
                        value = fred_data['value']
                        date_obj = fred_data.get('date', default_date)
                        # Convert date to string if it's a datetime/date object
                        if isinstance(date_obj, (datetime,)):
                            date = date_obj.strftime('%Y-%m-%d')
                        elif hasattr(date_obj, 'strftime'):
                            date = date_obj.strftime('%Y-%m-%d')
                        else:
                            date = str(date_obj) if date_obj else default_date
                        source = "FRED (live)"
                        # Cache the result
                        self._cache[cache_key] = (fred_data, datetime.now())
                        logger.info(f"Fetched live FRED data for {key}: {value:.2f}{config.get('unit', '')} (date: {date})")
                    else:
                        logger.debug(f"Using default value for {key} (FRED data not available)")
            
            # For inflation, if value still looks like CPI index (> 100), it wasn't converted
            # This shouldn't happen if _fetch_fred_data worked correctly, but keep as safety check
            if key == "inflation" and value and value > 100:
                # If CPI index (e.g., ~300), not percentage - skip and use default
                logger.warning(f"Inflation value {value} looks like CPI index, not percentage - using default 3.2%")
                value = 3.2
            
            indicators[key] = MacroIndicator(
                name=config["name"],
                value=value,
                date=date or default_date,
                unit=config["unit"],
                source=source,
                description=config["description"]
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
        
        Uses highly structured format with clear visual separation and examples
        to prevent confusion with company financial data.
        
        Args:
            company_sector: Sector of the company being analyzed
            
        Returns:
            Formatted string with macro context
        """
        indicators = self.get_macro_snapshot()
        sector_benchmarks = self.get_sector_benchmarks(company_sector)
        
        context_parts = []
        
        # CRITICAL: Visual separator to clearly distinguish macro data from company data
        context_parts.append("\n" + "█" * 80)
        context_parts.append("█" + " " * 78 + "█")
        context_parts.append("█" + " " * 15 + "🚨 MACRO ECONOMIC INDICATORS - READ CAREFULLY 🚨" + " " * 18 + "█")
        context_parts.append("█" + " " * 78 + "█")
        context_parts.append("█" * 80)
        context_parts.append("")
        
        # CRITICAL WARNINGS - Very explicit
        context_parts.append("⚠️ **CRITICAL INSTRUCTIONS FOR MACRO INDICATORS:**")
        context_parts.append("")
        context_parts.append("1. **THESE ARE PERCENTAGES ONLY** - All values below are PERCENTAGES (e.g., 2.5%, 4.5%)")
        context_parts.append("2. **NOT DOLLAR AMOUNTS** - These are NOT revenue numbers, NOT company data")
        context_parts.append("3. **USE THE VALUES SHOWN BELOW** - Values are VALIDATED and CORRECT (live from FRED when available)")
        context_parts.append("")
        context_parts.append("📡 **LIVE DATA INDICATOR:** Values marked '📡 LIVE from FRED' are fetched in real-time from FRED API")
        context_parts.append("📋 **DEFAULT VALUES:** Values marked '📋 Default value' are reasonable defaults when FRED data unavailable")
        context_parts.append("")
        
        # Examples of WRONG vs RIGHT - Very explicit
        context_parts.append("❌ **WRONG EXAMPLES (DO NOT USE):**")
        context_parts.append("   - GDP Growth Rate: $391B ❌ (WRONG: this is company revenue, not macro indicator)")
        context_parts.append("   - GDP Growth Rate: 391035000000.0% ❌ (WRONG: astronomical percentage - formatting error)")
        context_parts.append("   - Federal Funds Rate: $416B ❌ (WRONG: this is company revenue, not interest rate)")
        context_parts.append("   - Federal Funds Rate: 416161000000.0% ❌ (WRONG: astronomical percentage - formatting error)")
        context_parts.append("")
        context_parts.append("✅ **CORRECT EXAMPLES (USE THESE - FROM BELOW):**")
        context_parts.append("   - GDP Growth Rate: Use the validated percentage shown below ✅")
        context_parts.append("   - Federal Funds Rate: Use the validated percentage shown below ✅")
        context_parts.append("   - CPI Inflation: Use the validated percentage shown below ✅")
        context_parts.append("   - Unemployment Rate: Use the validated percentage shown below ✅")
        context_parts.append("")
        
        # Structured macro indicators table format
        context_parts.append("─" * 80)
        context_parts.append("**MACRO ECONOMIC INDICATORS (VALIDATED & READY TO USE):**")
        context_parts.append("─" * 80)
        context_parts.append("")
        context_parts.append("**All values below are VALIDATED and CORRECT - use them directly in your response:**")
        context_parts.append("")
        
        for key, indicator in indicators.items():
            # CRITICAL: Validate indicator value is in reasonable range BEFORE formatting
            original_value = indicator.value
            if indicator.unit == "%":
                # Ensure percentage is in valid range (0-100% for most indicators)
                if key == "gdp_growth":
                    # GDP growth can be negative or positive, typically -5% to +10%
                    if not (-5 <= indicator.value <= 10):
                        logger.warning(f"🔧 GDP growth rate {indicator.value}% is outside normal range (-5% to 10%), using default 2.5%")
                        indicator.value = 2.5
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key == "fed_funds_rate":
                    # Fed funds rate typically 0-10%
                    if not (0 <= indicator.value <= 10):
                        logger.warning(f"🔧 Fed funds rate {indicator.value}% is outside normal range (0% to 10%), using default 4.5%")
                        indicator.value = 4.5
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key == "inflation":
                    # Inflation typically 0-10%
                    if not (0 <= indicator.value <= 10):
                        logger.warning(f"🔧 Inflation rate {indicator.value}% is outside normal range (0% to 10%), using default 3.2%")
                        indicator.value = 3.2
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key == "unemployment":
                    # Unemployment typically 2-15%
                    if not (2 <= indicator.value <= 15):
                        logger.warning(f"🔧 Unemployment rate {indicator.value}% is outside normal range (2% to 15%), using default 3.8%")
                        indicator.value = 3.8
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
            
            # Format with clear structure - show VALIDATED LIVE value only
            formatted_value = f"{indicator.value:.1f}" if isinstance(indicator.value, float) else str(indicator.value)
            
            # Determine if this is live FRED data or default
            is_live_data = "live" in indicator.source.lower()
            data_source_note = "📡 LIVE from FRED" if is_live_data else "📋 Default value"
            
            context_parts.append(f"📊 {indicator.name}: **{formatted_value}{indicator.unit}** {data_source_note}")
            context_parts.append(f"   Date: {indicator.date} | Source: {indicator.source}")
            context_parts.append(f"   {indicator.description}")
            context_parts.append("")
        
        # Final reminder with comparison
        context_parts.append("─" * 80)
        context_parts.append("**REMEMBER:**")
        context_parts.append("")
        context_parts.append("- Macro indicators = PERCENTAGES (2.5%, 4.5%, 3.2%, 3.8%)")
        context_parts.append("- Company revenue = DOLLARS ($391B, $416B, $281B)")
        context_parts.append("- **DO NOT MIX THEM** - If you see a number > 1000% for macro indicators, it's WRONG!")
        context_parts.append("")
        
        # Add sector benchmarks if available (clearly separated)
        if sector_benchmarks:
            sector_name = company_sector or "Global"
            context_parts.append("─" * 80)
            context_parts.append(f"**{sector_name} SECTOR BENCHMARKS (For Comparison):**")
            context_parts.append("─" * 80)
            context_parts.append("")
            
            # Format sector benchmarks with validation
            # NOTE: JSON values are decimals (0.045 = 4.5%), need to convert to percentage
            revenue_cagr = sector_benchmarks.get('revenue_cagr', 0)
            if isinstance(revenue_cagr, (int, float)):
                # Convert decimal to percentage (0.045 -> 4.5%)
                revenue_cagr_pct = revenue_cagr * 100 if revenue_cagr <= 1 else revenue_cagr
                # Revenue CAGR typically 0-30%
                if revenue_cagr_pct > 100:  # Likely a formatting error
                    logger.warning(f"🔧 Sector Revenue CAGR {revenue_cagr_pct}% is too high, using 4.5% default")
                    revenue_cagr_pct = 4.5
                context_parts.append(f"- Revenue CAGR: **{revenue_cagr_pct:.1f}%**")
            
            ebitda_margin = sector_benchmarks.get('ebitda_margin', 0)
            if isinstance(ebitda_margin, (int, float)):
                # Convert decimal to percentage (0.18 -> 18.0%)
                ebitda_pct = ebitda_margin * 100 if ebitda_margin <= 1 else ebitda_margin
                # EBITDA Margin typically 5-40%
                if ebitda_pct > 100:  # Likely a formatting error
                    logger.warning(f"🔧 Sector EBITDA Margin {ebitda_pct}% is too high, using 15.0% default")
                    ebitda_pct = 15.0
                context_parts.append(f"- EBITDA Margin: **{ebitda_pct:.1f}%**")
            
            net_margin = sector_benchmarks.get('net_margin', 0)
            if isinstance(net_margin, (int, float)):
                # Convert decimal to percentage (0.11 -> 11.0%)
                net_pct = net_margin * 100 if net_margin <= 1 else net_margin
                # Net Margin typically 0-25%
                if net_pct > 100:
                    logger.warning(f"🔧 Sector Net Margin {net_pct}% is too high, using 11.0% default")
                    net_pct = 11.0
                context_parts.append(f"- Net Margin: **{net_pct:.1f}%**")
            
            fcf_margin = sector_benchmarks.get('free_cash_flow_margin', 0)
            if isinstance(fcf_margin, (int, float)):
                # Convert decimal to percentage (0.09 -> 9.0%)
                fcf_pct = fcf_margin * 100 if fcf_margin <= 1 else fcf_margin
                # FCF Margin typically 0-30%
                if fcf_pct > 100:
                    logger.warning(f"🔧 Sector FCF Margin {fcf_pct}% is too high, using 10.0% default")
                    fcf_pct = 10.0
                context_parts.append(f"- Free Cash Flow Margin: **{fcf_pct:.1f}%**")
            
            debt_to_equity = sector_benchmarks.get('debt_to_equity', 0)
            if isinstance(debt_to_equity, (int, float)):
                context_parts.append(f"- Debt/Equity: **{debt_to_equity:.2f}x**")
            
            context_parts.append("")
            context_parts.append("Note: These sector benchmarks are PERCENTAGES (for margins and CAGR) from IMF data")
            context_parts.append("")
        
        # Final visual separator
        context_parts.append("█" * 80)
        context_parts.append("**END OF MACRO ECONOMIC INDICATORS SECTION**")
        context_parts.append("█" * 80)
        context_parts.append("")
        context_parts.append("**The company financial data section starts below this line.**")
        context_parts.append("")
        
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


def get_macro_provider(fred_api_key: Optional[str] = None) -> MacroDataProvider:
    """
    Get or create the global macro data provider instance.
    
    Args:
        fred_api_key: Optional FRED API key for real-time data.
                     If None, will try to get from environment variable FRED_API_KEY.
                     Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
    
    Returns:
        MacroDataProvider instance
    """
    global _macro_provider
    
    # Always recreate if FRED API key is provided (to use live data)
    if fred_api_key is None:
        import os
        fred_api_key = os.getenv('FRED_API_KEY')
    
    # If FRED API key changed or provider doesn't exist, create new one
    if _macro_provider is None or (fred_api_key and _macro_provider.fred_api_key != fred_api_key):
        _macro_provider = MacroDataProvider(fred_api_key=fred_api_key)
    
    return _macro_provider

