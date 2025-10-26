"""
Multi-source financial data aggregator.

Combines data from:
- Yahoo Finance (real-time quotes, analyst ratings, news)
- SEC EDGAR (filings - already integrated)
- IMF (macroeconomic data)
- FRED (Federal Reserve economic data)
- Financial news and sentiment
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests

LOGGER = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import yfinance as yf
except ImportError:
    yf = None
    LOGGER.warning("yfinance not installed - Yahoo Finance data unavailable")

try:
    from fredapi import Fred
except ImportError:
    Fred = None
    LOGGER.warning("fredapi not installed - FRED economic data unavailable")


class MultiSourceAggregator:
    """Aggregates financial data from multiple free sources."""
    
    def __init__(self, fred_api_key: Optional[str] = None):
        """Initialize the aggregator with API keys if available."""
        self.fred_api_key = fred_api_key
        self.fred_client = None
        if Fred is not None and fred_api_key:
            try:
                self.fred_client = Fred(api_key=fred_api_key)
            except Exception as e:
                LOGGER.warning(f"Failed to initialize FRED client: {e}")
    
    def fetch_yahoo_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch comprehensive data from Yahoo Finance.
        
        Returns:
        - Current price and market data
        - Analyst recommendations
        - Company info and metrics
        - Recent news
        - Historical performance
        """
        if yf is None:
            return {}
        
        try:
            stock = yf.Ticker(ticker)
            
            # Get info
            info = stock.info or {}
            
            # Get recommendations
            recommendations = None
            try:
                recommendations = stock.recommendations
                if recommendations is not None and not recommendations.empty:
                    recent_recs = recommendations.tail(5).to_dict('records')
                else:
                    recent_recs = None
            except Exception:
                recent_recs = None
            
            # Get news
            news = []
            try:
                news_items = stock.news or []
                for item in news_items[:5]:  # Latest 5 news items
                    news.append({
                        'title': item.get('title'),
                        'publisher': item.get('publisher'),
                        'link': item.get('link'),
                        'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)) if item.get('providerPublishTime') else None
                    })
            except Exception as e:
                LOGGER.debug(f"Could not fetch news for {ticker}: {e}")
            
            # Get key statistics
            key_stats = {
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'price_to_sales': info.get('priceToSalesTrailing12Months'),
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'target_mean_price': info.get('targetMeanPrice'),
                'target_high_price': info.get('targetHighPrice'),
                'target_low_price': info.get('targetLowPrice'),
                'recommendation_mean': info.get('recommendationMean'),
                'recommendation_key': info.get('recommendationKey'),
                'number_of_analyst_opinions': info.get('numberOfAnalystOpinions'),
                '52_week_high': info.get('fiftyTwoWeekHigh'),
                '52_week_low': info.get('fiftyTwoWeekLow'),
                'beta': info.get('beta'),
                'dividend_yield': info.get('dividendYield'),
                'dividend_rate': info.get('dividendRate'),
                'ex_dividend_date': info.get('exDividendDate'),
                'payout_ratio': info.get('payoutRatio'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'full_time_employees': info.get('fullTimeEmployees'),
                'website': info.get('website'),
                'business_summary': info.get('longBusinessSummary'),
            }
            
            # Get historical data for trend analysis
            hist = None
            try:
                hist = stock.history(period="1y")
                if hist is not None and not hist.empty:
                    ytd_return = ((hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0]) * 100
                    key_stats['ytd_return'] = ytd_return
            except Exception as e:
                LOGGER.debug(f"Could not fetch history for {ticker}: {e}")
            
            return {
                'source': 'Yahoo Finance',
                'ticker': ticker,
                'key_stats': key_stats,
                'analyst_recommendations': recent_recs,
                'news': news,
                'fetched_at': datetime.now(),
                'source_url': f'https://finance.yahoo.com/quote/{ticker}'
            }
        
        except Exception as e:
            LOGGER.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
            return {}
    
    def fetch_fred_economic_data(self, indicators: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch macroeconomic indicators from FRED (Federal Reserve Economic Data).
        
        Args:
            indicators: List of FRED series IDs (e.g., 'GDP', 'UNRATE', 'FEDFUNDS')
        
        Returns:
            Dictionary with economic indicators and their latest values
        """
        if self.fred_client is None:
            return {}
        
        # Default indicators if none specified
        if indicators is None:
            indicators = [
                'GDP',  # Gross Domestic Product
                'UNRATE',  # Unemployment Rate
                'CPIAUCSL',  # Consumer Price Index
                'FEDFUNDS',  # Federal Funds Rate
                'DGS10',  # 10-Year Treasury Rate
                'DEXUSEU',  # USD/EUR Exchange Rate
                'VIXCLS',  # VIX Volatility Index
            ]
        
        results = {}
        for series_id in indicators:
            try:
                data = self.fred_client.get_series(series_id)
                if data is not None and not data.empty:
                    latest_value = data.iloc[-1]
                    latest_date = data.index[-1]
                    
                    # Get series info
                    info = self.fred_client.get_series_info(series_id)
                    
                    results[series_id] = {
                        'value': float(latest_value),
                        'date': latest_date,
                        'title': info.get('title'),
                        'units': info.get('units'),
                        'frequency': info.get('frequency'),
                        'source_url': f'https://fred.stlouisfed.org/series/{series_id}'
                    }
            except Exception as e:
                LOGGER.debug(f"Could not fetch FRED series {series_id}: {e}")
        
        return {
            'source': 'FRED (Federal Reserve Economic Data)',
            'indicators': results,
            'fetched_at': datetime.now(),
            'source_url': 'https://fred.stlouisfed.org/'
        }
    
    def fetch_imf_data(self, country: str = 'USA') -> Dict[str, Any]:
        """
        Fetch macroeconomic data from IMF public APIs.
        
        Note: IMF sector proxy data is already handled by imf_proxy.py
        This fetches broader economic indicators.
        """
        try:
            # IMF Data API endpoint
            # Example: World Economic Outlook database
            url = 'http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/Q.'
            
            # Common indicators
            indicators = {
                'NGDP_R': 'Real GDP',
                'PCPI': 'Consumer Price Index',
                'FITB': 'Current Account Balance',
            }
            
            results = {}
            for code, name in indicators.items():
                try:
                    endpoint = f"{url}{country}.{code}"
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        # Parse IMF JSON structure (simplified)
                        results[code] = {
                            'name': name,
                            'data': 'Available',
                            'note': 'IMF data structure varies by indicator'
                        }
                except Exception as e:
                    LOGGER.debug(f"Could not fetch IMF {code}: {e}")
            
            return {
                'source': 'International Monetary Fund (IMF)',
                'country': country,
                'indicators': results,
                'fetched_at': datetime.now(),
                'source_url': 'https://www.imf.org/en/Data'
            }
        
        except Exception as e:
            LOGGER.error(f"Error fetching IMF data: {e}")
            return {}
    
    def format_for_llm_context(
        self,
        ticker: str,
        include_yahoo: bool = True,
        include_fred: bool = True,
        include_imf: bool = False,
    ) -> str:
        """
        Fetch and format data from multiple sources for LLM context.
        
        Returns a formatted markdown string with all relevant data and sources.
        """
        context_parts = []
        sources = []
        
        # Fetch Yahoo Finance data
        if include_yahoo:
            yahoo_data = self.fetch_yahoo_data(ticker)
            if yahoo_data:
                context_parts.append(self._format_yahoo_section(yahoo_data))
                sources.append(f"[Yahoo Finance - {ticker}]({yahoo_data.get('source_url')})")
        
        # Fetch FRED economic data
        if include_fred and self.fred_client:
            fred_data = self.fetch_fred_economic_data()
            if fred_data.get('indicators'):
                context_parts.append(self._format_fred_section(fred_data))
                sources.append(f"[FRED Economic Data]({fred_data.get('source_url')})")
        
        # Fetch IMF data
        if include_imf:
            imf_data = self.fetch_imf_data()
            if imf_data.get('indicators'):
                context_parts.append(self._format_imf_section(imf_data))
                sources.append(f"[IMF Data]({imf_data.get('source_url')})")
        
        # Combine all context
        full_context = "\n\n".join(context_parts)
        
        # Add sources section
        if sources:
            full_context += "\n\n📊 **ADDITIONAL DATA SOURCES** (Use these in your response):\n"
            for source in sources:
                full_context += f"  • {source}\n"
        
        return full_context
    
    def _format_yahoo_section(self, data: Dict[str, Any]) -> str:
        """Format Yahoo Finance data for LLM context."""
        ticker = data.get('ticker', '')
        stats = data.get('key_stats', {})
        
        lines = [
            "=" * 80,
            f"YAHOO FINANCE DATA - {ticker}",
            "=" * 80,
            ""
        ]
        
        # Current Market Data
        if stats.get('current_price'):
            lines.append("**Current Market Data:**")
            lines.append(f"  • Price: ${stats['current_price']:.2f}")
            if stats.get('52_week_high'):
                lines.append(f"  • 52-Week High: ${stats['52_week_high']:.2f}")
            if stats.get('52_week_low'):
                lines.append(f"  • 52-Week Low: ${stats['52_week_low']:.2f}")
            if stats.get('ytd_return'):
                lines.append(f"  • YTD Return: {stats['ytd_return']:.2f}%")
            if stats.get('market_cap'):
                lines.append(f"  • Market Cap: ${stats['market_cap']:,.0f}")
            if stats.get('volume'):
                lines.append(f"  • Volume: {stats['volume']:,.0f}")
            lines.append("")
        
        # Valuation Metrics
        valuation_metrics = []
        if stats.get('pe_ratio'):
            valuation_metrics.append(f"  • P/E Ratio: {stats['pe_ratio']:.2f}")
        if stats.get('peg_ratio'):
            valuation_metrics.append(f"  • PEG Ratio: {stats['peg_ratio']:.2f}")
        if stats.get('price_to_book'):
            valuation_metrics.append(f"  • Price/Book: {stats['price_to_book']:.2f}")
        if stats.get('price_to_sales'):
            valuation_metrics.append(f"  • Price/Sales: {stats['price_to_sales']:.2f}")
        
        if valuation_metrics:
            lines.append("**Valuation Metrics:**")
            lines.extend(valuation_metrics)
            lines.append("")
        
        # Profitability & Returns
        profitability = []
        if stats.get('profit_margin'):
            profitability.append(f"  • Profit Margin: {stats['profit_margin']*100:.2f}%")
        if stats.get('operating_margin'):
            profitability.append(f"  • Operating Margin: {stats['operating_margin']*100:.2f}%")
        if stats.get('roe'):
            profitability.append(f"  • ROE: {stats['roe']*100:.2f}%")
        if stats.get('roa'):
            profitability.append(f"  • ROA: {stats['roa']*100:.2f}%")
        
        if profitability:
            lines.append("**Profitability & Returns:**")
            lines.extend(profitability)
            lines.append("")
        
        # Growth Metrics
        growth = []
        if stats.get('revenue_growth'):
            growth.append(f"  • Revenue Growth: {stats['revenue_growth']*100:.2f}%")
        if stats.get('earnings_growth'):
            growth.append(f"  • Earnings Growth: {stats['earnings_growth']*100:.2f}%")
        
        if growth:
            lines.append("**Growth Metrics:**")
            lines.extend(growth)
            lines.append("")
        
        # Analyst Ratings
        if stats.get('recommendation_key'):
            lines.append("**Analyst Consensus:**")
            lines.append(f"  • Recommendation: {stats['recommendation_key'].upper()}")
            if stats.get('number_of_analyst_opinions'):
                lines.append(f"  • Number of Analysts: {stats['number_of_analyst_opinions']}")
            if stats.get('target_mean_price'):
                lines.append(f"  • Target Price (Mean): ${stats['target_mean_price']:.2f}")
                if stats.get('current_price'):
                    upside = ((stats['target_mean_price'] - stats['current_price']) / stats['current_price']) * 100
                    lines.append(f"  • Implied Upside: {upside:+.2f}%")
            if stats.get('target_high_price'):
                lines.append(f"  • Target High: ${stats['target_high_price']:.2f}")
            if stats.get('target_low_price'):
                lines.append(f"  • Target Low: ${stats['target_low_price']:.2f}")
            lines.append("")
        
        # Dividends
        if stats.get('dividend_yield'):
            lines.append("**Dividend Information:**")
            lines.append(f"  • Dividend Yield: {stats['dividend_yield']*100:.2f}%")
            if stats.get('dividend_rate'):
                lines.append(f"  • Annual Dividend: ${stats['dividend_rate']:.2f}")
            if stats.get('payout_ratio'):
                lines.append(f"  • Payout Ratio: {stats['payout_ratio']*100:.2f}%")
            lines.append("")
        
        # Company Info
        if stats.get('sector'):
            lines.append("**Company Information:**")
            lines.append(f"  • Sector: {stats['sector']}")
            if stats.get('industry'):
                lines.append(f"  • Industry: {stats['industry']}")
            if stats.get('full_time_employees'):
                lines.append(f"  • Employees: {stats['full_time_employees']:,}")
            lines.append("")
        
        # Recent News
        news = data.get('news', [])
        if news:
            lines.append("**Recent News:**")
            for item in news[:3]:
                if item.get('title'):
                    news_line = f"  • {item['title']}"
                    if item.get('publisher'):
                        news_line += f" ({item['publisher']})"
                    lines.append(news_line)
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_fred_section(self, data: Dict[str, Any]) -> str:
        """Format FRED economic data for LLM context."""
        lines = [
            "=" * 80,
            "FRED ECONOMIC INDICATORS",
            "=" * 80,
            ""
        ]
        
        indicators = data.get('indicators', {})
        if indicators:
            for series_id, info in indicators.items():
                title = info.get('title', series_id)
                value = info.get('value')
                units = info.get('units', '')
                date = info.get('date')
                
                line = f"  • {title}: {value:.2f}"
                if units:
                    line += f" {units}"
                if date:
                    line += f" (as of {date.strftime('%Y-%m-%d')})"
                lines.append(line)
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_imf_section(self, data: Dict[str, Any]) -> str:
        """Format IMF data for LLM context."""
        lines = [
            "=" * 80,
            "IMF MACROECONOMIC DATA",
            "=" * 80,
            ""
        ]
        
        country = data.get('country', '')
        indicators = data.get('indicators', {})
        
        if country:
            lines.append(f"Country: {country}")
            lines.append("")
        
        if indicators:
            for code, info in indicators.items():
                name = info.get('name', code)
                lines.append(f"  • {name}: {info.get('data', 'N/A')}")
            lines.append("")
        
        return "\n".join(lines)


def get_multi_source_context(
    ticker: str,
    fred_api_key: Optional[str] = None,
    include_yahoo: bool = True,
    include_fred: bool = False,  # FRED requires API key
    include_imf: bool = False,
) -> str:
    """
    Convenience function to fetch multi-source context.
    
    Args:
        ticker: Stock ticker symbol
        fred_api_key: Optional FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)
        include_yahoo: Include Yahoo Finance data
        include_fred: Include FRED economic data (requires API key)
        include_imf: Include IMF macroeconomic data
    
    Returns:
        Formatted string with data from all requested sources
    """
    aggregator = MultiSourceAggregator(fred_api_key=fred_api_key)
    return aggregator.format_for_llm_context(
        ticker=ticker,
        include_yahoo=include_yahoo,
        include_fred=include_fred,
        include_imf=include_imf,
    )

