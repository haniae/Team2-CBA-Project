"""
Macro Economic Data Integration Module

Fetches and provides macro economic indicators to contextualize company performance:
- GDP growth rates
- Interest rates (Fed Funds Rate, 10-Year Treasury Yield)
- Inflation (CPI)
- Unemployment rates
- Market indices (S&P 500, VIX)
- Consumer sentiment (Consumer Confidence Index)
- Economic activity (Manufacturing PMI)
- Sector-specific trends

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
from typing import Dict, List, Optional, Any, Tuple
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
        },
        "treasury_10y": {
            "fred_series": "DGS10",  # 10-Year Treasury Constant Maturity Rate
            "name": "10-Year Treasury Yield",
            "unit": "%",
            "description": "10-year Treasury constant maturity rate (risk-free rate for valuation)"
        },
        "vix": {
            "fred_series": "VIXCLS",  # CBOE Volatility Index
            "name": "VIX (Volatility Index)",
            "unit": "Points",
            "description": "CBOE Volatility Index (market fear gauge)"
        },
        "consumer_confidence": {
            "fred_series": "UMCSENT",  # University of Michigan Consumer Sentiment Index
            "name": "Consumer Confidence Index",
            "unit": "Index",
            "description": "University of Michigan Consumer Sentiment Index (consumer spending predictor)"
        },
        "manufacturing_pmi": {
            "fred_series": "NAPM",  # ISM Manufacturing PMI
            "name": "Manufacturing PMI",
            "unit": "Index",
            "description": "ISM Manufacturing Purchasing Managers Index (manufacturing health indicator, >50 = expansion)"
        },
        "core_cpi": {
            "fred_series": "CPILFESL",  # Core CPI (CPI Less Food & Energy) - BLS
            "name": "Core CPI Inflation",
            "unit": "%",
            "description": "Core Consumer Price Index YoY inflation rate (excludes food & energy, more stable measure)"
        },
        "nonfarm_payrolls": {
            "fred_series": "PAYEMS",  # All Employees, Total Nonfarm - BLS
            "name": "Nonfarm Payrolls",
            "unit": "Thousands",
            "description": "Total nonfarm employment (millions of jobs, monthly change is key indicator)"
        },
        "core_pce": {
            "fred_series": "PCEPILFE",  # Core PCE Price Index Less Food & Energy - BEA
            "name": "Core PCE Inflation",
            "unit": "%",
            "description": "Core Personal Consumption Expenditures Price Index YoY (Fed's preferred inflation measure, excludes food & energy)"
        },
        "pce": {
            "fred_series": "PCEPI",  # Personal Consumption Expenditures Price Index - BEA
            "name": "PCE Inflation",
            "unit": "%",
            "description": "Personal Consumption Expenditures Price Index YoY (Fed's preferred inflation measure, broader than CPI)"
        },
        "dxy": {
            "fred_series": "DTWEXBGS",  # Trade-Weighted U.S. Dollar Index: Broad, Goods and Services - Federal Reserve
            "name": "Trade-Weighted USD Index",
            "unit": "Index",
            "description": "Trade-weighted U.S. dollar index (broad, goods and services) - measures USD strength against major trading partners"
        },
        "eur_usd": {
            "fred_series": "DEXUSEU",  # U.S. / Euro Foreign Exchange Rate - Federal Reserve
            "name": "EUR/USD Exchange Rate",
            "unit": "USD per EUR",
            "description": "U.S. dollars per Euro exchange rate (higher = stronger USD, weaker EUR)"
        },
        "cny_usd": {
            "fred_series": "DEXCHUS",  # China / U.S. Foreign Exchange Rate - Federal Reserve
            "name": "CNY/USD Exchange Rate",
            "unit": "CNY per USD",
            "description": "Chinese yuan per U.S. dollar exchange rate (higher = stronger USD, weaker CNY)"
        },
        "jpy_usd": {
            "fred_series": "DEXJPUS",  # Japan / U.S. Foreign Exchange Rate - Federal Reserve
            "name": "JPY/USD Exchange Rate",
            "unit": "JPY per USD",
            "description": "Japanese yen per U.S. dollar exchange rate (higher = stronger USD, weaker JPY)"
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
        # Daily indicators (Fed Funds, S&P 500, VIX, Treasury 10Y): 6 hours
        # Weekly indicators (Manufacturing PMI): 12 hours
        # Monthly indicators (CPI, Unemployment, Consumer Confidence): 24 hours
        # Quarterly indicators (GDP): 7 days
        self.cache_ttl_map = {
            "gdp_growth": timedelta(days=7),      # Quarterly - update weekly
            "fed_funds_rate": timedelta(hours=6), # Daily - update 4x per day
            "inflation": timedelta(hours=24),     # Monthly - update daily
            "unemployment": timedelta(hours=24),  # Monthly - update daily
            "sp500": timedelta(hours=6),          # Daily - update 4x per day
            "treasury_10y": timedelta(hours=6),   # Daily - update 4x per day
            "vix": timedelta(hours=6),            # Daily - update 4x per day
            "consumer_confidence": timedelta(hours=24),  # Monthly - update daily
            "manufacturing_pmi": timedelta(hours=12),     # Weekly - update 2x per day
            "core_cpi": timedelta(hours=24),      # Monthly - update daily (BLS)
            "nonfarm_payrolls": timedelta(hours=24),  # Monthly - update daily (BLS, released first Friday of month)
            "core_pce": timedelta(hours=24),      # Monthly - update daily (BEA, Fed's preferred)
            "pce": timedelta(hours=24),           # Monthly - update daily (BEA, Fed's preferred)
            "dxy": timedelta(hours=6),            # Daily - update 4x per day (FX rates)
            "eur_usd": timedelta(hours=6),        # Daily - update 4x per day (FX rates)
            "cny_usd": timedelta(hours=6),        # Daily - update 4x per day (FX rates)
            "jpy_usd": timedelta(hours=6),        # Daily - update 4x per day (FX rates)
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
                # For inflation indicators (CPI, Core CPI, Core PCE, PCE) YoY calculation, need 12+ months of data
                inflation_series = ["CPIAUCSL", "CPILFESL", "PCEPILFE", "PCEPI"]
                if series_id in inflation_series and months_back:
                    logger.info(f"Fetching FRED data for series {series_id} (need {months_back} months for YoY calculation)")
                    # Fetch more data points to ensure we have enough months back
                    # CPI is monthly, so need months_back + 1 observations
                    # Fetch more to ensure we get recent data (FRED may return old data first)
                    # CRITICAL: Fetch recent data only (last 5 years) to ensure we get latest observations
                    from datetime import datetime, timedelta
                    observation_start = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
                    
                    fetch_limit = max(months_back + 1, 100)
                    
                    # Try to fetch with observation_start first (recent data only)
                    try:
                        data = self._fred_client.get_series(
                            series_id, 
                            limit=fetch_limit,
                            observation_start=observation_start
                        )
                    except Exception as e:
                        # Fallback: try without observation_start if it fails
                        logger.debug(f"Failed to fetch CPI with observation_start, trying without: {e}")
                        data = self._fred_client.get_series(series_id, limit=fetch_limit)
                    
                    if data is not None and not data.empty:
                        # CRITICAL: Sort by date descending to get LATEST observations first
                        data_sorted = data.sort_index(ascending=False)
                        
                        if len(data_sorted) >= months_back + 1:
                            latest_value = float(data_sorted.iloc[0])  # Latest value
                            latest_date = data_sorted.index[0]  # Latest date
                            
                            # Find value from approximately 12 months ago (months_back positions later)
                            year_ago_idx = min(months_back, len(data_sorted) - 1)
                            year_ago_value = float(data_sorted.iloc[year_ago_idx])
                            year_ago_date = data_sorted.index[year_ago_idx]
                        else:
                            logger.warning(f"Insufficient CPI data: got {len(data_sorted)} observations, need {months_back + 1}")
                            return None
                        
                        # Calculate YoY percentage change: ((current - year_ago) / year_ago) * 100
                        if year_ago_value > 0:
                            yoy_change = ((latest_value - year_ago_value) / year_ago_value) * 100
                        else:
                            logger.warning(f"Invalid year-ago CPI value: {year_ago_value}")
                            return None
                        
                        # Get series info
                        info = self._fred_client.get_series_info(series_id)
                        
                        series_name = {
                            "CPIAUCSL": "CPI",
                            "CPILFESL": "Core CPI",
                            "PCEPILFE": "Core PCE",
                            "PCEPI": "PCE"
                        }.get(series_id, series_id)
                        logger.info(f"{series_name} YoY calculation: {latest_value:.2f} (current, {latest_date}) vs {year_ago_value:.2f} (year ago, {year_ago_date}) = {yoy_change:.2f}% YoY")
                        
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
                        series_name = {
                            "CPIAUCSL": "CPI",
                            "CPILFESL": "Core CPI",
                            "PCEPILFE": "Core PCE",
                            "PCEPI": "PCE"
                        }.get(series_id, series_id)
                        logger.warning(f"Insufficient {series_name} data for YoY calculation")
                        return None
                else:
                    # Standard fetch for non-inflation indicators or when months_back not specified
                    logger.info(f"Fetching FRED data for series {series_id}")
                    # Fetch enough data points to ensure we get recent data
                    # FRED API returns data in ascending date order, so we need enough to get latest
                    fetch_limit = max(limit, 100) if limit else 100
                    
                    # CRITICAL: Fetch recent data only (last 5 years) to ensure we get latest observations
                    from datetime import datetime, timedelta
                    observation_start = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
                    
                    # Try to fetch with observation_start first (recent data only)
                    try:
                        data = self._fred_client.get_series(
                            series_id, 
                            limit=fetch_limit,
                            observation_start=observation_start
                        )
                    except Exception as e:
                        # Fallback: try without observation_start if it fails
                        logger.debug(f"Failed to fetch with observation_start, trying without: {e}")
                        data = self._fred_client.get_series(series_id, limit=fetch_limit)
                    
                    if data is not None and not data.empty:
                        # CRITICAL: Sort by date descending to get LATEST observation first
                        # FRED API returns data in ascending date order, so sort descending
                        data_sorted = data.sort_index(ascending=False)
                        latest_value = float(data_sorted.iloc[0])  # First element after sorting descending
                        latest_date = data_sorted.index[0]  # Latest date
                        
                        logger.info(f"FRED series {series_id}: Latest observation on {latest_date} = {latest_value}")
                        
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
            # IMPORTANT: These defaults are fallbacks only when FRED API is unavailable
            # They should be updated regularly to reflect current market conditions
            # As of January 2025 (updated with latest 2025 data), approximate current values:
            if key == "gdp_growth":
                # Real GDP growth rate (Q1 2025 data, ~2-3 months lag)
                default_value = 2.0  # Updated: ~2.0% YoY (Q1 2025, from 2.8% Q3 2024)
                default_date = "2025-Q1"  # Quarterly data (Q1 2025 latest available)
            elif key == "fed_funds_rate":
                # Fed Funds Rate (July 2025: 4.3%, projected 4.2% for 2025)
                # Note: Actual rate may vary, but trend is downward from 5.25-5.50%
                default_value = 4.3  # Updated: ~4.3% (July 2025, from 5.25%)
                default_date = "2025-07"  # Monthly (July 2025 latest available)
            elif key == "inflation":
                # CPI YoY inflation (September 2025: 2.73%, latest available)
                default_value = 2.7  # Updated: ~2.7% YoY (September 2025, from 2.7% Dec 2024)
                default_date = "2025-09"  # YoY September 2025 (specify YoY for clarity)
            elif key == "unemployment":
                # Unemployment rate (August 2025: 4.3%, latest available)
                default_value = 4.3  # Updated: ~4.3% (August 2025, from 4.0% Dec 2024)
                default_date = "2025-08"  # Monthly data (August 2025 latest available)
            elif key == "sp500":
                # S&P 500 Index (July 2025: ~6,363 points, latest available)
                default_value = 6363.0  # Updated: ~6,363 points (July 2025, from 4,500 Jan 2025)
                default_date = "2025-07"  # Daily (July 2025 latest available)
            elif key == "treasury_10y":
                # 10-Year Treasury Yield (July 2025: 4.4%, latest available)
                default_value = 4.4  # Updated: ~4.4% (July 2025, from 4.2% Jan 2025)
                default_date = "2025-07"  # Daily (July 2025 latest available)
            elif key == "vix":
                # VIX Volatility Index (July 2025: ~15.5, latest available)
                default_value = 15.5  # Updated: ~15.5 (July 2025, from 15.0)
                default_date = "2025-07"  # Daily (July 2025 latest available)
            elif key == "consumer_confidence":
                # University of Michigan Consumer Sentiment (latest: varies, typically 60-65 range)
                default_value = 62.0  # Typical range: 60-65 (unchanged from Dec 2024)
                default_date = "2025-07"  # Monthly (July 2025, approximate)
            elif key == "manufacturing_pmi":
                # ISM Manufacturing PMI (latest: typically 48-52 range)
                default_value = 51.0  # Typical range: 48-52 (unchanged from Dec 2024, slight expansion >50)
                default_date = "2025-07"  # Monthly (July 2025, approximate)
            elif key == "core_cpi":
                # Core CPI YoY inflation (excludes food & energy, typically lower than headline CPI)
                default_value = 2.5  # Updated: ~2.5% YoY (September 2025, slightly lower than headline CPI)
                default_date = "2025-09"  # YoY September 2025
            elif key == "nonfarm_payrolls":
                # Nonfarm Payrolls (Total employment in thousands)
                default_value = 159700.0  # Updated: ~159.7 million jobs (August 2025, from ~158 million)
                default_date = "2025-08"  # Monthly (August 2025 latest available)
            elif key == "core_pce":
                # Core PCE YoY inflation (Fed's preferred measure, excludes food & energy)
                default_value = 2.4  # Updated: ~2.4% YoY (September 2025, Fed's target is 2.0%)
                default_date = "2025-09"  # YoY September 2025
            elif key == "pce":
                # PCE YoY inflation (Fed's preferred measure, broader than CPI)
                default_value = 2.5  # Updated: ~2.5% YoY (September 2025, Fed's preferred measure)
                default_date = "2025-09"  # YoY September 2025
            elif key == "dxy":
                # Trade-Weighted USD Index (broad, goods and services) - Base year 2006=100
                default_value = 120.0  # Approximate current level (varies, typically 110-130 range)
                default_date = "2025-07"  # Daily (July 2025, approximate)
            elif key == "eur_usd":
                # EUR/USD exchange rate (USD per EUR)
                default_value = 1.08  # Approximate current level (varies, typically 1.05-1.12 range)
                default_date = "2025-07"  # Daily (July 2025, approximate)
            elif key == "cny_usd":
                # CNY/USD exchange rate (CNY per USD)
                default_value = 7.25  # Approximate current level (varies, typically 7.0-7.5 range)
                default_date = "2025-07"  # Daily (July 2025, approximate)
            elif key == "jpy_usd":
                # JPY/USD exchange rate (JPY per USD)
                default_value = 155.0  # Approximate current level (varies, typically 140-160 range)
                default_date = "2025-07"  # Daily (July 2025, approximate)
            
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
                    # For inflation indicators (CPI, Core CPI, Core PCE, PCE), need 12 months of data to calculate YoY
                    needs_yoy_calc = key in ["inflation", "core_cpi", "core_pce", "pce"]
                    months_back = 12 if needs_yoy_calc else None
                    fred_data = self._fetch_fred_data(fred_series, months_back=months_back)
                    if fred_data and fred_data.get('value') is not None:
                        value = fred_data['value']
                        date_obj = fred_data.get('date', default_date)
                        
                        # CRITICAL: Convert date to string with proper formatting
                        if isinstance(date_obj, (datetime,)):
                            date = date_obj.strftime('%Y-%m-%d')
                            date_for_age_check = date_obj
                        elif hasattr(date_obj, 'strftime'):
                            date = date_obj.strftime('%Y-%m-%d')
                            date_for_age_check = date_obj
                        else:
                            date = str(date_obj) if date_obj else default_date
                            # Try to parse date string to check age
                            try:
                                if len(date) == 7:  # YYYY-MM format
                                    date_for_age_check = datetime.strptime(date, '%Y-%m')
                                elif len(date) == 10:  # YYYY-MM-DD format
                                    date_for_age_check = datetime.strptime(date, '%Y-%m-%d')
                                else:
                                    date_for_age_check = None
                            except (ValueError, TypeError):
                                date_for_age_check = None
                        
                        # CRITICAL: Check data freshness and REJECT if too old
                        data_age_days = None
                        if date_for_age_check:
                            if isinstance(date_for_age_check, datetime):
                                data_age = datetime.now() - date_for_age_check
                                data_age_days = data_age.days
                        
                        # CRITICAL: Define maximum acceptable age for each indicator type
                        max_age_days = None
                        if key in ["fed_funds_rate", "treasury_10y", "sp500", "vix"]:
                            max_age_days = 7  # Daily indicators - max 7 days old
                        elif key in ["inflation", "unemployment", "consumer_confidence", "manufacturing_pmi", "core_cpi", "nonfarm_payrolls", "core_pce", "pce"]:
                            max_age_days = 90  # Monthly indicators - max 90 days old
                        elif key in ["dxy", "eur_usd", "cny_usd", "jpy_usd"]:
                            max_age_days = 7  # FX rates - max 7 days old (daily data)
                        elif key == "gdp_growth":
                            max_age_days = 180  # Quarterly indicators - max 180 days old
                        
                        # REJECT data if too old
                        if data_age_days is not None and max_age_days is not None:
                            if data_age_days > max_age_days:
                                logger.warning(f"🔴 REJECTED {key} data: {data_age_days} days old (max: {max_age_days} days)")
                                logger.warning(f"   Date: {date} - Using default value instead")
                                value = default_value
                                date = default_date
                                source = f"FRED (default - data too old: {data_age_days} days, max: {max_age_days} days)"
                            else:
                                # Data is fresh enough, proceed with validation
                                period_note = ""
                                if key in ["inflation", "core_cpi", "core_pce", "pce"]:
                                    period_note = " (YoY)"  # Year-over-Year inflation rate
                                
                                # Validate value is reasonable (prevent obviously wrong data)
                                is_valid, validation_msg = self._validate_indicator_value(key, value)
                                if not is_valid:
                                    logger.warning(f"🔴 VALIDATION FAILED for {key}: {validation_msg}")
                                    logger.warning(f"   Value {value} rejected, using default {default_value}")
                                    value = default_value
                                    date = default_date
                                    source = f"FRED (default - validation failed: {validation_msg})"
                                else:
                                    source = "FRED (live)"
                                    # Add freshness warning to source if data is getting old
                                    if data_age_days > max_age_days * 0.7:  # Warn if >70% of max age
                                        source = f"FRED (live - data {data_age_days} days old)"
                                    
                                    # Cache the result
                                    self._cache[cache_key] = (fred_data, datetime.now())
                                    logger.info(f"Fetched live FRED data for {key}: {value:.2f}{config.get('unit', '')}{period_note} (date: {date}, age: {data_age_days} days)")
                        else:
                            # Could not determine age, validate value but proceed
                            period_note = ""
                            if key in ["inflation", "core_cpi", "core_pce", "pce"]:
                                period_note = " (YoY)"
                            
                            is_valid, validation_msg = self._validate_indicator_value(key, value)
                            if not is_valid:
                                logger.warning(f"🔴 VALIDATION FAILED for {key}: {validation_msg}")
                                logger.warning(f"   Value {value} rejected, using default {default_value}")
                                value = default_value
                                date = default_date
                                source = f"FRED (default - validation failed: {validation_msg})"
                            else:
                                source = "FRED (live - age unknown)"
                                self._cache[cache_key] = (fred_data, datetime.now())
                                logger.info(f"Fetched live FRED data for {key}: {value:.2f}{config.get('unit', '')}{period_note} (date: {date})")
                    else:
                        logger.debug(f"Using default value for {key} (FRED data not available)")
            
            # For inflation, if value still looks like CPI index (> 100), it wasn't converted
            # This shouldn't happen if _fetch_fred_data worked correctly, but keep as safety check
            if key == "inflation" and value and value > 100:
                # If CPI index (e.g., ~300), not percentage - skip and use default
                logger.warning(f"🔴 Inflation value {value} looks like CPI index, not percentage - using default 3.2%")
                value = 3.2
            
            # Final validation check before creating indicator
            is_valid, validation_msg = self._validate_indicator_value(key, value)
            if not is_valid:
                logger.warning(f"🔴 FINAL VALIDATION FAILED for {key}: {validation_msg}")
                logger.warning(f"   Value {value} rejected, using default {default_value}")
                value = default_value
                source = f"{source} (validation failed, using default)"
            
            # Format date with period clarity
            formatted_date = self._format_indicator_date(key, date or default_date)
            
            indicators[key] = MacroIndicator(
                name=config["name"],
                value=value,
                date=formatted_date,
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
                    # Fed funds rate typically 0-10% (current: 5.25-5.50% as of Jan 2025)
                    if not (0 <= indicator.value <= 10):
                        logger.warning(f"🔧 Fed funds rate {indicator.value}% is outside normal range (0% to 10%), using default 5.25%")
                        indicator.value = 5.25
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                    # Special check: reject obviously outdated values
                    elif indicator.value < 3.0:
                        logger.warning(f"🔴 Fed funds rate {indicator.value}% is too low (current: 5.25-5.50%). Data may be outdated, using default 5.25%")
                        indicator.value = 5.25
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}% - outdated)"
                    elif indicator.value > 8.0:
                        logger.warning(f"🔴 Fed funds rate {indicator.value}% is too high (current: 5.25-5.50%). Data may be wrong, using default 5.25%")
                        indicator.value = 5.25
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}% - invalid)"
                elif key == "inflation":
                    # Inflation typically 0-10%
                    if not (0 <= indicator.value <= 10):
                        logger.warning(f"🔧 Inflation rate {indicator.value}% is outside normal range (0% to 10%), using default 2.7%")
                        indicator.value = 2.7
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key in ["core_cpi", "core_pce", "pce"]:
                    # Core CPI, Core PCE, PCE typically 0-10%
                    if not (0 <= indicator.value <= 10):
                        default_val = 2.5 if key == "core_cpi" else 2.4 if key == "core_pce" else 2.5
                        logger.warning(f"🔧 {key} rate {indicator.value}% is outside normal range (0% to 10%), using default {default_val}%")
                        indicator.value = default_val
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key == "unemployment":
                    # Unemployment typically 2-15%
                    if not (2 <= indicator.value <= 15):
                        logger.warning(f"🔧 Unemployment rate {indicator.value}% is outside normal range (2% to 15%), using default 3.8%")
                        indicator.value = 3.8
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
                elif key == "treasury_10y":
                    # Treasury 10Y typically 0-10%
                    if not (0 <= indicator.value <= 10):
                        logger.warning(f"🔧 Treasury 10Y yield {indicator.value}% is outside normal range (0% to 10%), using default 4.5%")
                        indicator.value = 4.5
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f}%)"
            
            # Validation for non-percentage indicators
            if indicator.unit != "%":
                if key == "vix":
                    # VIX typically 10-50 (can spike higher during crises, but >100 is likely wrong)
                    if not (10 <= indicator.value <= 100):
                        logger.warning(f"🔧 VIX {indicator.value} is outside normal range (10 to 100), using default 15.0")
                        indicator.value = 15.0
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f})"
                elif key == "consumer_confidence":
                    # Consumer confidence typically 50-120 (historical range)
                    if not (50 <= indicator.value <= 120):
                        logger.warning(f"🔧 Consumer confidence {indicator.value} is outside normal range (50 to 120), using default 70.0")
                        indicator.value = 70.0
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f})"
                elif key == "manufacturing_pmi":
                    # PMI typically 30-70 (>50 = expansion, <50 = contraction)
                    if not (30 <= indicator.value <= 70):
                        logger.warning(f"🔧 Manufacturing PMI {indicator.value} is outside normal range (30 to 70), using default 50.0")
                        indicator.value = 50.0
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f})"
                elif key == "dxy":
                    # Trade-Weighted USD Index typically 90-150 (base year 2006=100)
                    if not (90 <= indicator.value <= 150):
                        logger.warning(f"🔧 USD Index {indicator.value} is outside normal range (90 to 150), using default 120.0")
                        indicator.value = 120.0
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f})"
                elif key == "eur_usd":
                    # EUR/USD typically 0.8-1.4 (USD per EUR)
                    if not (0.8 <= indicator.value <= 1.4):
                        logger.warning(f"🔧 EUR/USD {indicator.value} is outside normal range (0.8 to 1.4), using default 1.08")
                        indicator.value = 1.08
                        indicator.source = f"{indicator.source} (corrected from {original_value:.2f})"
                elif key == "cny_usd":
                    # CNY/USD typically 6.0-8.0 (CNY per USD)
                    if not (6.0 <= indicator.value <= 8.0):
                        logger.warning(f"🔧 CNY/USD {indicator.value} is outside normal range (6.0 to 8.0), using default 7.25")
                        indicator.value = 7.25
                        indicator.source = f"{indicator.source} (corrected from {original_value:.2f})"
                elif key == "jpy_usd":
                    # JPY/USD typically 80-200 (JPY per USD)
                    if not (80 <= indicator.value <= 200):
                        logger.warning(f"🔧 JPY/USD {indicator.value} is outside normal range (80 to 200), using default 155.0")
                        indicator.value = 155.0
                        indicator.source = f"{indicator.source} (corrected from {original_value:.1f})"
            
            # Format with clear structure - show VALIDATED LIVE value only
            formatted_value = f"{indicator.value:.1f}" if isinstance(indicator.value, float) else str(indicator.value)
            
            # Determine if this is live FRED data or default
            is_live_data = "live" in indicator.source.lower()
            has_warning = "⚠️" in indicator.source or "OLD DATA" in indicator.source
            
            if is_live_data and not has_warning:
                data_source_note = "📡 LIVE from FRED"
            elif is_live_data and has_warning:
                data_source_note = "⚠️ FRED (OLD DATA - verify current)"
            else:
                data_source_note = "📋 Default value (use with caution - may be outdated)"
            
            context_parts.append(f"📊 {indicator.name}: **{formatted_value}{indicator.unit}** {data_source_note}")
            context_parts.append(f"   📅 Date: {indicator.date} | Source: {indicator.source}")
            context_parts.append(f"   {indicator.description}")
            
            # Add warning if data is old
            if has_warning:
                context_parts.append(f"   ⚠️ WARNING: This data may be outdated. Verify current value before using.")
            
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
        
        # Add macro economic insights summary (if relevant)
        market_regime = self.detect_market_regime()
        cycle_position = self.get_economic_cycle_position()
        
        context_parts.append("─" * 80)
        context_parts.append("**MACRO ECONOMIC INSIGHTS & IMPLICATIONS:**")
        context_parts.append("─" * 80)
        context_parts.append("")
        
        # Market Regime
        if market_regime["regime"]:
            regime_emoji = "⚠️" if market_regime["regime"] == "risk_off" else "✅"
            context_parts.append(f"{regime_emoji} **Market Regime: {market_regime['regime'].upper().replace('_', '-')}**")
            context_parts.append(f"   Confidence: {market_regime['confidence']:.0%}")
            if market_regime.get("signals"):
                for signal_type, description in market_regime["signals"][:3]:  # Limit to top 3
                    context_parts.append(f"   - {description}")
            context_parts.append("")
        
        # Economic Cycle
        if cycle_position["phase"]:
            cycle_emoji = "📈" if cycle_position["phase"] == "expansion" else "📉"
            context_parts.append(f"{cycle_emoji} **Economic Cycle: {cycle_position['phase'].title()}**")
            if cycle_position.get("signals"):
                context_parts.append("   Key signals:")
                for signal in cycle_position["signals"][:3]:  # Limit to top 3
                    context_parts.append(f"   - {signal}")
            context_parts.append("")
        
        # General macro insights (key combinations)
        general_insights = self._generate_general_macro_insights(indicators, sector_benchmarks, company_sector)
        if general_insights:
            context_parts.append("💡 **Key Macro Implications:**")
            for insight in general_insights[:5]:  # Limit to top 5
                context_parts.append(f"   - {insight}")
            context_parts.append("")
        
        context_parts.append("**Note:** Use the macro indicators above to contextualize company performance.")
        context_parts.append("For specific metric insights, refer to the enhanced macro analysis in your response.")
        context_parts.append("")
        
        # Final visual separator
        context_parts.append("█" * 80)
        context_parts.append("**END OF MACRO ECONOMIC INDICATORS SECTION**")
        context_parts.append("█" * 80)
        context_parts.append("")
        context_parts.append("**The company financial data section starts below this line.**")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    def get_macro_insights(
        self, 
        metric: str, 
        value: float, 
        company_sector: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> List[str]:
        """
        Generate comprehensive macro-informed insights about a company metric.
        
        Uses all 9 macro indicators with sector-specific analysis to provide
        deep, contextual insights for chatbot responses.
        
        Args:
            metric: Metric name (e.g., 'revenue_growth', 'pe_ratio', 'margin')
            value: Company's metric value
            company_sector: Company's sector for benchmarking (e.g., 'TECH', 'RETAIL')
            ticker: Optional ticker symbol for additional context
            
        Returns:
            List of insight strings with macro context
        """
        insights = []
        macro_data = self.get_macro_snapshot()
        sector_benchmarks = self.get_sector_benchmarks(company_sector)
        sector_upper = (company_sector or "").upper()
        
        # 1. VALUATION INSIGHTS (10-Year Treasury Yield)
        if "treasury_10y" in macro_data and metric == "pe_ratio" and value > 0:
            treasury_10y = macro_data["treasury_10y"].value
            earnings_yield = (1 / value) * 100
            if earnings_yield < treasury_10y:
                insights.append(
                    f"Earnings yield ({earnings_yield:.1f}%) is below 10-year Treasury yield "
                    f"({treasury_10y:.1f}%), suggesting the stock may be expensive unless growth "
                    f"expectations justify the premium."
                )
            elif earnings_yield > treasury_10y + 2:
                insights.append(
                    f"Earnings yield ({earnings_yield:.1f}%) is well above risk-free rate "
                    f"({treasury_10y:.1f}%), indicating potential value opportunity."
                )
        
        # 2. RISK SENTIMENT (VIX)
        if "vix" in macro_data and metric in ["volatility", "beta"]:
            vix = macro_data["vix"].value
            if vix > 25:
                insights.append(
                    f"Elevated market volatility (VIX at {vix:.1f}) suggests broader market concerns. "
                    f"Stock movements may reflect market sentiment rather than company-specific factors."
                )
            elif vix < 12:
                insights.append(
                    f"Low market volatility (VIX at {vix:.1f}) indicates calm market conditions. "
                    f"Company-specific news may have more impact on stock price."
                )
        
        # 3. CONSUMER SPENDING (Consumer Confidence)
        consumer_sectors = ["RETAIL", "CONSUMER_DISCRETIONARY", "AUTOMOTIVE", "TRAVEL", "HOSPITALITY"]
        if "consumer_confidence" in macro_data and sector_upper in consumer_sectors:
            confidence = macro_data["consumer_confidence"].value
            if metric == "revenue_growth":
                if confidence < 60:
                    insights.append(
                        f"Low consumer confidence ({confidence:.0f}) may constrain discretionary spending, "
                        f"impacting revenue growth potential for consumer-facing businesses."
                    )
                elif confidence > 85:
                    insights.append(
                        f"High consumer confidence ({confidence:.0f}) supports discretionary spending, "
                        f"providing tailwind for revenue growth in consumer sectors."
                    )
        
        # 4. MANUFACTURING CYCLE (PMI)
        cyclical_sectors = ["INDUSTRIALS", "MATERIALS", "ENERGY", "MANUFACTURING"]
        if "manufacturing_pmi" in macro_data and sector_upper in cyclical_sectors:
            pmi = macro_data["manufacturing_pmi"].value
            if metric == "revenue_growth":
                if pmi < 50:
                    insights.append(
                        f"Manufacturing PMI below 50 ({pmi:.1f}) indicates contraction in manufacturing sector, "
                        f"which may impact cyclical company revenue."
                    )
                elif pmi > 55:
                    insights.append(
                        f"Strong manufacturing PMI ({pmi:.1f}) indicates expansion, supporting revenue growth "
                        f"for cyclical companies in Industrials and Materials sectors."
                    )
        
        # 5. INTEREST RATE IMPACT (Fed Rate)
        if "fed_funds_rate" in macro_data:
            fed_rate = macro_data["fed_funds_rate"].value
            # Debt-heavy companies
            debt_heavy_sectors = ["REAL_ESTATE", "REIT", "UTILITIES", "TELECOM"]
            if metric in ["debt", "interest_expense", "debt_to_equity"]:
                if fed_rate > 4.0:
                    insights.append(
                        f"Elevated Fed Funds Rate ({fed_rate:.1f}%) increases borrowing costs, "
                        f"particularly impactful for debt-heavy companies."
                    )
            # Growth stocks (Tech)
            if metric == "pe_ratio" and sector_upper == "TECH" and fed_rate > 4.5:
                insights.append(
                    f"High interest rates ({fed_rate:.1f}%) typically compress valuation multiples for "
                    f"growth stocks as discount rates increase."
                )
        
        # 6. GDP GROWTH CONTEXT
        if "gdp_growth" in macro_data:
            gdp_growth = macro_data["gdp_growth"].value
            if metric == "revenue_growth":
                if value > gdp_growth * 2:
                    insights.append(
                        f"Strong revenue growth ({value:.1f}%) significantly outpaces GDP growth ({gdp_growth:.1f}%), "
                        f"indicating market share gains or strong sector dynamics."
                    )
                elif value < gdp_growth:
                    insights.append(
                        f"Revenue growth ({value:.1f}%) below GDP growth ({gdp_growth:.1f}%) may indicate "
                        f"market share loss or sector headwinds."
                    )
        
        # 7. INFLATION IMPACT
        if "inflation" in macro_data:
            inflation = macro_data["inflation"].value
            if metric in ["operating_margin", "gross_margin", "net_margin"]:
                if inflation > 4.0:
                    insights.append(
                        f"Elevated inflation ({inflation:.1f}%) may pressure margins if company cannot "
                        f"fully pass through cost increases to consumers."
                    )
                elif inflation < 2.0:
                    insights.append(
                        f"Low inflation ({inflation:.1f}%) provides cost stability, supporting margin "
                        f"expansion potential."
                    )
        
        # 8. UNEMPLOYMENT & SPENDING
        if "unemployment" in macro_data:
            unemployment = macro_data["unemployment"].value
            if sector_upper in consumer_sectors:
                if metric == "revenue_growth" and unemployment < 4.0:
                    insights.append(
                        f"Low unemployment ({unemployment:.1f}%) supports consumer spending, "
                        f"though may also increase labor costs."
                    )
                elif unemployment > 5.5:
                    insights.append(
                        f"Elevated unemployment ({unemployment:.1f}%) may constrain consumer spending, "
                        f"impacting revenue growth for consumer-facing businesses."
                    )
        
        # 9. SECTOR BENCHMARKS
        if metric == "revenue_growth" and "revenue_cagr" in sector_benchmarks:
            sector_avg = sector_benchmarks["revenue_cagr"]
            if isinstance(sector_avg, (int, float)):
                # Convert decimal to percentage if needed (0.045 -> 4.5%)
                sector_avg_pct = sector_avg * 100 if sector_avg <= 1 else sector_avg
                if value > sector_avg_pct * 1.2:
                    insights.append(
                        f"Revenue growth ({value:.1f}%) significantly exceeds sector average ({sector_avg_pct:.1f}%), "
                        f"indicating strong competitive position."
                    )
                elif value < sector_avg_pct * 0.8:
                    insights.append(
                        f"Revenue growth ({value:.1f}%) below sector average ({sector_avg_pct:.1f}%), "
                        f"suggesting competitive challenges."
                    )
        
        # 10. MARGIN BENCHMARKS
        if metric in ["operating_margin", "net_margin", "ebitda_margin"]:
            margin_key = metric.replace("_margin", "_margin")
            if margin_key in sector_benchmarks:
                sector_margin = sector_benchmarks[margin_key]
                if isinstance(sector_margin, (int, float)):
                    sector_margin_pct = sector_margin * 100 if sector_margin <= 1 else sector_margin
                    if value > sector_margin_pct * 1.15:
                        insights.append(
                            f"{metric.replace('_', ' ').title()} ({value:.1f}%) above sector average ({sector_margin_pct:.1f}%), "
                            f"indicating operational efficiency."
                        )
                    elif value < sector_margin_pct * 0.85:
                        insights.append(
                            f"{metric.replace('_', ' ').title()} ({value:.1f}%) below sector average ({sector_margin_pct:.1f}%), "
                            f"suggesting margin improvement opportunities."
                        )
        
        return insights
    
    def detect_market_regime(self) -> Dict[str, Any]:
        """
        Detect current market regime (risk-on vs risk-off).
        
        Combines VIX, Treasury yields, and other indicators to determine
        overall market sentiment and risk appetite.
        
        Returns:
            Dict with regime, confidence, and supporting signals
        """
        macro_data = self.get_macro_snapshot()
        
        regime_signals = []
        
        # VIX-based signals
        if "vix" in macro_data:
            vix = macro_data["vix"].value
            if vix > 25:
                regime_signals.append(("risk_off", f"High VIX ({vix:.1f}) indicates elevated market fear"))
            elif vix < 12:
                regime_signals.append(("risk_on", f"Low VIX ({vix:.1f}) indicates calm market conditions"))
        
        # Treasury yield signals
        if "treasury_10y" in macro_data:
            treasury_10y = macro_data["treasury_10y"].value
            if treasury_10y > 5.0:
                regime_signals.append(("risk_off", f"High Treasury yield ({treasury_10y:.1f}%) compresses valuations"))
            elif treasury_10y < 3.0:
                regime_signals.append(("risk_on", f"Low rates ({treasury_10y:.1f}%) support growth stocks"))
        
        # Fed Funds Rate signals
        if "fed_funds_rate" in macro_data:
            fed_rate = macro_data["fed_funds_rate"].value
            if fed_rate > 5.0:
                regime_signals.append(("risk_off", f"High Fed Funds Rate ({fed_rate:.1f}%) increases borrowing costs"))
            elif fed_rate < 2.0:
                regime_signals.append(("risk_on", f"Low rates ({fed_rate:.1f}%) support risk assets"))
        
        # Determine dominant regime
        if not regime_signals:
            return {
                "regime": "neutral",
                "confidence": 0.5,
                "signals": []
            }
        
        risk_off_count = sum(1 for sig, _ in regime_signals if sig == "risk_off")
        risk_on_count = sum(1 for sig, _ in regime_signals if sig == "risk_on")
        
        if risk_off_count > risk_on_count:
            regime = "risk_off"
            confidence = risk_off_count / len(regime_signals) if regime_signals else 0.5
        elif risk_on_count > risk_off_count:
            regime = "risk_on"
            confidence = risk_on_count / len(regime_signals) if regime_signals else 0.5
        else:
            regime = "neutral"
            confidence = 0.5
        
        return {
            "regime": regime,
            "confidence": confidence,
            "signals": regime_signals
        }
    
    def get_economic_cycle_position(self) -> Dict[str, Any]:
        """
        Determine position in economic cycle.
        
        Combines GDP, Inflation, Unemployment, and PMI to identify
        the current phase of the economic cycle.
        
        Returns:
            Dict with cycle phase, signals, and sector implications
        """
        macro_data = self.get_macro_snapshot()
        
        signals = []
        phase_indicators = {
            "expansion": 0,
            "contraction": 0,
            "late_cycle": 0
        }
        
        # GDP growth analysis
        if "gdp_growth" in macro_data:
            gdp_growth = macro_data["gdp_growth"].value
            if gdp_growth > 3.0:
                signals.append("Strong GDP growth")
                phase_indicators["expansion"] += 1
            elif gdp_growth > 2.0:
                signals.append("Moderate GDP growth")
                phase_indicators["expansion"] += 1
            elif gdp_growth < 1.0:
                signals.append("Weak GDP growth")
                phase_indicators["contraction"] += 1
        
        # PMI analysis
        if "manufacturing_pmi" in macro_data:
            pmi = macro_data["manufacturing_pmi"].value
            if pmi > 55:
                signals.append("Strong manufacturing expansion")
                phase_indicators["expansion"] += 1
            elif pmi > 50:
                signals.append("Moderate manufacturing expansion")
                phase_indicators["expansion"] += 1
            elif pmi < 45:
                signals.append("Manufacturing contraction")
                phase_indicators["contraction"] += 1
            elif 45 <= pmi < 50:
                signals.append("Manufacturing slowing")
                phase_indicators["late_cycle"] += 1
        
        # Inflation analysis
        if "inflation" in macro_data:
            inflation = macro_data["inflation"].value
            if inflation > 4.0:
                signals.append("Elevated inflation")
                phase_indicators["late_cycle"] += 1
            elif inflation < 2.0:
                signals.append("Low inflation")
                phase_indicators["expansion"] += 1
        
        # Unemployment analysis
        if "unemployment" in macro_data:
            unemployment = macro_data["unemployment"].value
            if unemployment < 4.0:
                signals.append("Tight labor market")
                phase_indicators["late_cycle"] += 1
            elif unemployment > 5.5:
                signals.append("Elevated unemployment")
                phase_indicators["contraction"] += 1
        
        # Determine dominant phase
        max_phase = max(phase_indicators.items(), key=lambda x: x[1])
        if max_phase[1] > 0:
            phase = max_phase[0].replace("_", "-")
        else:
            phase = "expansion"  # default
        
        # Sector implications
        if phase == "expansion":
            favorable_sectors = ["TECH", "CONSUMER_DISCRETIONARY", "INDUSTRIALS"]
            unfavorable_sectors = ["UTILITIES", "CONSUMER_STAPLES"]
        elif phase == "contraction":
            favorable_sectors = ["CONSUMER_STAPLES", "UTILITIES", "HEALTHCARE"]
            unfavorable_sectors = ["CONSUMER_DISCRETIONARY", "INDUSTRIALS"]
        else:  # late-cycle
            favorable_sectors = ["CONSUMER_STAPLES", "UTILITIES", "HEALTHCARE"]
            unfavorable_sectors = ["CONSUMER_DISCRETIONARY", "INDUSTRIALS", "MATERIALS"]
        
        return {
            "phase": phase,
            "signals": signals,
            "favorable_sectors": favorable_sectors,
            "unfavorable_sectors": unfavorable_sectors
        }
    
    def adjust_forecast_for_macro(
        self,
        base_forecast: float,
        metric: str,
        sector: Optional[str] = None,
        forecast_period: int = 1
    ) -> Dict[str, Any]:
        """
        Adjust forecast based on macro economic environment.
        
        Args:
            base_forecast: Base forecast value (growth rate in % or absolute value)
            metric: Metric being forecasted (e.g., 'revenue', 'earnings', 'margin')
            sector: Company sector for sector-specific adjustments
            forecast_period: Number of periods ahead (default: 1 year)
            
        Returns:
            Dict with adjusted forecast, adjustment factors, and reasoning
        """
        macro_data = self.get_macro_snapshot()
        adjustments = []
        adjustment_factor = 1.0
        
        sector_upper = (sector or "").upper()
        
        # GDP growth adjustment for revenue
        if metric == "revenue" and "gdp_growth" in macro_data:
            gdp_growth = macro_data["gdp_growth"].value
            # If GDP is strong (> 3%), slightly boost revenue forecast
            if gdp_growth > 3.0:
                adjustment_factor *= 1.05
                adjustments.append(f"GDP growth ({gdp_growth:.1f}%) supports revenue (+5%)")
            elif gdp_growth < 1.5:
                adjustment_factor *= 0.95
                adjustments.append(f"Slow GDP growth ({gdp_growth:.1f}%) tempers revenue (-5%)")
        
        # Consumer confidence for consumer sectors
        consumer_sectors = ["RETAIL", "CONSUMER_DISCRETIONARY", "AUTOMOTIVE", "TRAVEL", "HOSPITALITY"]
        if metric == "revenue" and sector_upper in consumer_sectors:
            if "consumer_confidence" in macro_data:
                confidence = macro_data["consumer_confidence"].value
                if confidence > 85:
                    adjustment_factor *= 1.08
                    adjustments.append(f"High consumer confidence ({confidence:.0f}) supports spending (+8%)")
                elif confidence < 60:
                    adjustment_factor *= 0.92
                    adjustments.append(f"Low consumer confidence ({confidence:.0f}) constrains spending (-8%)")
        
        # PMI for cyclical sectors
        cyclical_sectors = ["INDUSTRIALS", "MATERIALS", "ENERGY", "MANUFACTURING"]
        if metric == "revenue" and sector_upper in cyclical_sectors:
            if "manufacturing_pmi" in macro_data:
                pmi = macro_data["manufacturing_pmi"].value
                if pmi > 55:
                    adjustment_factor *= 1.10
                    adjustments.append(f"Strong PMI ({pmi:.1f}) supports cyclical revenue (+10%)")
                elif pmi < 45:
                    adjustment_factor *= 0.90
                    adjustments.append(f"Weak PMI ({pmi:.1f}) challenges cyclical revenue (-10%)")
        
        # Inflation impact on margins
        if metric in ["operating_margin", "net_margin", "gross_margin"] and "inflation" in macro_data:
            inflation = macro_data["inflation"].value
            if inflation > 4.0:
                adjustment_factor *= 0.95
                adjustments.append(f"High inflation ({inflation:.1f}%) may pressure margins (-5%)")
            elif inflation < 2.0:
                adjustment_factor *= 1.03
                adjustments.append(f"Low inflation ({inflation:.1f}%) supports margin stability (+3%)")
        
        # Interest rate impact on revenue (for rate-sensitive sectors)
        rate_sensitive_sectors = ["REAL_ESTATE", "REIT", "UTILITIES", "AUTOMOTIVE"]
        if metric == "revenue" and sector_upper in rate_sensitive_sectors:
            if "fed_funds_rate" in macro_data:
                fed_rate = macro_data["fed_funds_rate"].value
                if fed_rate > 5.0:
                    adjustment_factor *= 0.97
                    adjustments.append(f"High interest rates ({fed_rate:.1f}%) may slow demand (-3%)")
                elif fed_rate < 2.0:
                    adjustment_factor *= 1.03
                    adjustments.append(f"Low interest rates ({fed_rate:.1f}%) support demand (+3%)")
        
        adjusted_forecast = base_forecast * adjustment_factor
        
        return {
            "base_forecast": base_forecast,
            "adjusted_forecast": adjusted_forecast,
            "adjustment_factor": adjustment_factor,
            "adjustments": adjustments,
            "reasoning": "; ".join(adjustments) if adjustments else "No macro adjustments applied"
        }
    
    def _generate_general_macro_insights(
        self,
        indicators: Dict[str, Any],
        sector_benchmarks: Dict[str, float],
        company_sector: Optional[str] = None
    ) -> List[str]:
        """
        Generate general macro insights based on current indicator values.
        
        Returns:
            List of insight strings
        """
        insights = []
        
        # High interest rates impact
        if "fed_funds_rate" in indicators and "treasury_10y" in indicators:
            fed_rate = indicators["fed_funds_rate"].value
            treasury_10y = indicators["treasury_10y"].value
            if fed_rate > 5.0 or treasury_10y > 5.0:
                insights.append(
                    f"High interest rates (Fed: {fed_rate:.1f}%, Treasury 10Y: {treasury_10y:.1f}%) "
                    f"may compress valuation multiples and impact debt-heavy companies"
                )
        
        # VIX and market sentiment
        if "vix" in indicators:
            vix = indicators["vix"].value
            if vix > 25:
                insights.append(f"Elevated VIX ({vix:.1f}) indicates heightened market volatility and risk-off sentiment")
            elif vix < 12:
                insights.append(f"Low VIX ({vix:.1f}) suggests calm market conditions and risk-on sentiment")
        
        # GDP and growth environment
        if "gdp_growth" in indicators:
            gdp_growth = indicators["gdp_growth"].value
            if gdp_growth > 3.0:
                insights.append(f"Strong GDP growth ({gdp_growth:.1f}%) provides favorable environment for corporate revenue growth")
            elif gdp_growth < 1.5:
                insights.append(f"Slow GDP growth ({gdp_growth:.1f}%) may constrain corporate revenue growth")
        
        # Inflation and margins
        if "inflation" in indicators:
            inflation = indicators["inflation"].value
            if inflation > 4.0:
                insights.append(f"Elevated inflation ({inflation:.1f}%) may pressure margins if companies cannot fully pass through costs")
        
        # Combined insights
        if "consumer_confidence" in indicators and "unemployment" in indicators:
            confidence = indicators["consumer_confidence"].value
            unemployment = indicators["unemployment"].value
            if confidence < 60 and unemployment > 5.0:
                insights.append("Weak consumer confidence combined with elevated unemployment suggests cautious consumer spending outlook")
        
        return insights
    
    def _validate_indicator_value(self, key: str, value: float) -> Tuple[bool, str]:
        """
        Validate indicator value is within reasonable range.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if value is None:
            return False, "Value is None"
        
        # Strict validation ranges for critical indicators
        validation_ranges = {
            "fed_funds_rate": (0.0, 10.0, "Fed Funds Rate must be between 0% and 10% (current: 5.25-5.50%)"),
            "treasury_10y": (0.0, 10.0, "Treasury 10Y must be between 0% and 10%"),
            "gdp_growth": (-10.0, 15.0, "GDP growth must be between -10% and +15%"),
            "inflation": (-5.0, 15.0, "Inflation must be between -5% and +15%"),
            "unemployment": (2.0, 20.0, "Unemployment must be between 2% and 20%"),
            "vix": (5.0, 150.0, "VIX must be between 5 and 150"),
            "consumer_confidence": (30.0, 150.0, "Consumer Confidence must be between 30 and 150"),
            "manufacturing_pmi": (20.0, 80.0, "Manufacturing PMI must be between 20 and 80"),
            "dxy": (90.0, 150.0, "USD Index must be between 90 and 150 (base year 2006=100)"),
            "eur_usd": (0.8, 1.4, "EUR/USD must be between 0.8 and 1.4 (USD per EUR)"),
            "cny_usd": (6.0, 8.0, "CNY/USD must be between 6.0 and 8.0 (CNY per USD)"),
            "jpy_usd": (80.0, 200.0, "JPY/USD must be between 80 and 200 (JPY per USD)"),
        }
        
        if key in validation_ranges:
            min_val, max_val, msg = validation_ranges[key]
            if value < min_val or value > max_val:
                return False, f"{msg}. Got {value:.2f}"
        
        # Special check for Fed Funds Rate - reject obviously outdated values
        if key == "fed_funds_rate":
            # As of Jan 2025, Fed Funds Rate is 5.25-5.50%
            # Values below 3% or above 8% are likely outdated or wrong
            if value < 3.0:
                return False, f"Fed Funds Rate {value:.2f}% is too low (current range: 5.25-5.50%). Data may be outdated."
            if value > 8.0:
                return False, f"Fed Funds Rate {value:.2f}% is too high (current range: 5.25-5.50%). Data may be wrong."
        
        return True, "OK"
    
    def _format_indicator_date(self, key: str, date_str: str) -> str:
        """
        Format date string with period clarity for better understanding.
        
        For example:
        - CPI: "YoY December 2024" instead of "2024-12"
        - Fed Funds: "January 2025" instead of "2025-01"
        - GDP: "Q4 2024" instead of "2024-Q4"
        """
        if not date_str:
            return date_str
        
        try:
            # Handle different date formats
            if len(date_str) == 7 and '-' in date_str:  # YYYY-MM
                year, month = date_str.split('-')
                month_int = int(month)
                month_names = ["", "January", "February", "March", "April", "May", "June",
                             "July", "August", "September", "October", "November", "December"]
                month_name = month_names[month_int] if 1 <= month_int <= 12 else month
                
                # For inflation indicators, specify YoY (Year-over-Year)
                if key in ["inflation", "core_cpi", "core_pce", "pce"]:
                    return f"YoY {month_name} {year}"
                else:
                    return f"{month_name} {year}"
            
            elif 'Q' in date_str.upper() or '-' in date_str and len(date_str.split('-')) == 2:  # YYYY-QX or similar
                return date_str  # Keep as-is for quarterly
            
            elif len(date_str) == 10 and '-' in date_str:  # YYYY-MM-DD
                year, month, day = date_str.split('-')
                month_int = int(month)
                month_names = ["", "January", "February", "March", "April", "May", "June",
                             "July", "August", "September", "October", "November", "December"]
                month_name = month_names[month_int] if 1 <= month_int <= 12 else month
                return f"{month_name} {day}, {year}"
            
            else:
                return date_str  # Return as-is if can't parse
        except (ValueError, IndexError, AttributeError):
            return date_str  # Return as-is if parsing fails


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

