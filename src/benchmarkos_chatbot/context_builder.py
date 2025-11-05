"""Smart financial context builder for LLM-powered responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from datetime import datetime
import os

from .parsing.parse import parse_to_structured
from . import database

if TYPE_CHECKING:
    from .analytics_engine import AnalyticsEngine

LOGGER = logging.getLogger(__name__)

# Try to import multi-source aggregator
try:
    from .multi_source_aggregator import get_multi_source_context
    MULTI_SOURCE_AVAILABLE = True
except ImportError:
    MULTI_SOURCE_AVAILABLE = False
    LOGGER.warning("Multi-source aggregator not available - only SEC data will be used")

# Try to import macro data provider
try:
    from .macro_data import get_macro_provider
    MACRO_DATA_AVAILABLE = True
except ImportError:
    MACRO_DATA_AVAILABLE = False
    LOGGER.warning("Macro data provider not available - economic context will not be included")

# Try to import ML forecasting
try:
    from .ml_forecasting import get_ml_forecaster
    ML_FORECASTING_AVAILABLE = True
except ImportError:
    ML_FORECASTING_AVAILABLE = False
    LOGGER.debug("ML forecasting not available - forecasting will use basic methods")


def format_currency(value: Optional[float]) -> str:
    """Format currency value to human-readable string."""
    if value is None:
        return "N/A"
    
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    else:
        return f"${value:,.0f}"


def format_percent(value: Optional[float]) -> str:
    """Format percentage value."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def format_multiple(value: Optional[float]) -> str:
    """Format multiple/ratio value."""
    if value is None:
        return "N/A"
    return f"{value:.1f}×"


def _format_period_label(record: database.MetricRecord) -> str:
    """Extract human-readable period label from metric record."""
    if not record.period:
        return "latest available"
    
    # Parse period string (e.g., "2023-Q3", "2023-FY")
    period_str = record.period
    if "-FY" in period_str:
        return f"FY{period_str.split('-')[0]}"
    elif "-Q" in period_str:
        parts = period_str.split("-")
        return f"{parts[1]} FY{parts[0]}"
    
    return period_str


def _build_sec_url(accession: str, cik: str) -> str:
    """Build clickable SEC EDGAR URL from accession number and CIK."""
    if not accession or not cik:
        return ""
    
    clean_cik = cik.lstrip("0") or cik
    acc_no_dash = accession.replace("-", "")
    
    # Interactive viewer URL (preferred for viewing the filing)
    return f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={clean_cik}&accession_number={accession}&xbrl_type=v"


def _get_filing_sources(
    ticker: str,
    database_path: str,
    fiscal_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetch filing metadata with SEC URLs for source citations."""
    try:
        facts = database.fetch_financial_facts(
            database_path,
            ticker=ticker,
            fiscal_year=fiscal_year,
            limit=100
        )
        
        # Extract unique filing sources with metadata
        filings_map: Dict[str, Dict[str, Any]] = {}
        for fact in facts:
            if fact.source_filing and fact.source_filing not in filings_map:
                # Parse source_filing format (typically "10-K/0001234567-23-000123" or just form type)
                parts = fact.source_filing.split("/")
                form_type = parts[0] if parts else "SEC filing"
                accession = parts[1] if len(parts) > 1 else None
                
                # Build SEC URL if we have accession and CIK
                sec_url = ""
                if accession and fact.cik:
                    sec_url = _build_sec_url(accession, fact.cik)
                
                filings_map[fact.source_filing] = {
                    "form_type": form_type,
                    "fiscal_year": fact.fiscal_year,
                    "fiscal_period": fact.fiscal_period,
                    "period_end": fact.period_end,
                    "accession": accession,
                    "sec_url": sec_url,
                }
        
        return list(filings_map.values())
    except Exception as e:
        LOGGER.debug(f"Could not fetch filing sources for {ticker}: {e}")
        return []


def _is_forecasting_query(query: str) -> bool:
    """Check if query is asking for forecasting/prediction."""
    import re
    forecasting_keywords = [
        r'\bforecast\b',
        r'\bpredict\b',
        r'\bestimate\b',
        r'\bprojection\b',
        r'\bproject\b',
        r'\boutlook\b',
        r'\bfuture\b',
        r'\bnext\s+\d+\s+years?\b',
        r'\bupcoming\s+years?\b',
    ]
    query_lower = query.lower()
    return any(re.search(pattern, query_lower) for pattern in forecasting_keywords)


def _extract_forecast_metric(query: str) -> Optional[str]:
    """Extract metric name from forecasting query."""
    import re
    query_lower = query.lower()
    
    # Common metric keywords
    metric_keywords = ['revenue', 'sales', 'income', 'earnings', 'cash flow', 'free cash flow', 
                       'net income', 'ebitda', 'profit', 'margin', 'eps', 'assets', 'liabilities']
    
    # Pattern 1: "Forecast Apple's revenue using LSTM" - extract after possessive
    match = re.search(r"(?:forecast|predict|estimate)\s+\w+\'?s?\s+(\w+(?:\s+\w+)?)\s*(?:using|with|$)", query_lower)
    if match:
        metric = match.group(1).strip()
        if metric in metric_keywords or any(kw in metric for kw in metric_keywords):
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(metric, metric.replace(' ', '_'))
    
    # Pattern 2: "Forecast revenue for Apple" - extract before "for"
    match = re.search(r"(?:forecast|predict|estimate)\s+(\w+(?:\s+\w+)?)\s+(?:for|of)", query_lower)
    if match:
        metric = match.group(1).strip()
        if metric in metric_keywords or any(kw in metric for kw in metric_keywords):
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(metric, metric.replace(' ', '_'))
    
    # Pattern 4: Look for metric keywords anywhere in query
    for keyword in metric_keywords:
        if keyword in query_lower:
            metric_map = {
                'revenue': 'revenue',
                'sales': 'revenue',
                'income': 'net_income',
                'net income': 'net_income',
                'earnings': 'net_income',
                'cash flow': 'cash_from_operations',
                'free cash flow': 'free_cash_flow',
            }
            return metric_map.get(keyword, keyword.replace(' ', '_'))
    
    # Default to revenue if no specific metric mentioned
    return 'revenue'


def _extract_forecast_method(query: str) -> str:
    """Extract forecasting method from query (ARIMA, Prophet, ETS, LSTM, GRU, Transformer, ensemble, or auto)."""
    import re
    query_lower = query.lower()
    
    # Check for specific method mentions (order matters - check specific methods first)
    if re.search(r'\b(?:using|with|via)\s+transformer', query_lower):
        return "transformer"
    elif re.search(r'\b(?:using|with|via)\s+lstm', query_lower):
        return "lstm"
    elif re.search(r'\b(?:using|with|via)\s+gru', query_lower):
        return "gru"
    elif re.search(r'\b(?:using|with|via)\s+arima', query_lower):
        return "arima"
    elif re.search(r'\b(?:using|with|via)\s+prophet', query_lower):
        return "prophet"
    elif re.search(r'\b(?:using|with|via)\s+ets', query_lower):
        return "ets"
    elif re.search(r'\b(?:using|with|via)\s+ensemble', query_lower):
        return "ensemble"
    elif re.search(r'\b(?:using|with|via)\s+(?:best|auto|automatic|ml)', query_lower):
        return "auto"
    # Check for direct method mentions without "using"
    elif re.search(r'\btransformer\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "transformer"
    elif re.search(r'\blstm\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "lstm"
    elif re.search(r'\bgru\b', query_lower) and re.search(r'\b(?:forecast|predict|estimate)\b', query_lower):
        return "gru"
    
    # Default to auto if no method specified
    return "auto"


def _build_ml_forecast_context(
    ticker: str,
    metric: str,
    database_path: str,
    periods: int = 3,
    method: str = "auto"
) -> Optional[str]:
    """Build ML forecasting context for a ticker and metric."""
    if not ML_FORECASTING_AVAILABLE:
        return None
    
    try:
        LOGGER.info(f"Generating ML forecast for {ticker} {metric} using {method}")
        ml_forecaster = get_ml_forecaster(database_path)
        
        # Check if requested method is available
        if method == "lstm" or method == "gru":
            if ml_forecaster.lstm_forecaster is None:
                LOGGER.warning(f"LSTM/GRU not available (TensorFlow missing), falling back to auto-select")
                method = "auto"
        elif method == "transformer":
            if ml_forecaster.transformer_forecaster is None:
                LOGGER.warning(f"Transformer not available (PyTorch missing), falling back to auto-select")
                method = "auto"
        
        # Validate we have a forecaster available
        if method == "auto":
            # Check what's available
            available_methods = []
            if ml_forecaster.arima_forecaster:
                available_methods.append("ARIMA")
            if ml_forecaster.prophet_forecaster:
                available_methods.append("Prophet")
            if ml_forecaster.ets_forecaster:
                available_methods.append("ETS")
            if ml_forecaster.lstm_forecaster:
                available_methods.append("LSTM")
            if ml_forecaster.transformer_forecaster:
                available_methods.append("Transformer")
            
            if not available_methods:
                LOGGER.error(f"No ML forecasting methods available - all dependencies missing")
                error_context = f"\n{'='*80}\n⚠️ ML FORECASTING UNAVAILABLE\n{'='*80}\n"
                error_context += f"**Reason:** No ML forecasting methods are available. Required dependencies are missing.\n"
                error_context += f"**Required:** Install pmdarima, statsmodels, prophet, tensorflow, or torch\n"
                error_context += f"**Fallback:** The system will use historical data analysis instead.\n"
                error_context += f"{'='*80}\n"
                return error_context
        
        forecast = ml_forecaster.forecast(
            ticker=ticker,
            metric=metric,
            periods=periods,
            method=method
        )
        
        if forecast is None:
            LOGGER.warning(f"ML forecast generation returned None for {ticker} {metric} using {method}")
            # Check if we can get more info about why it failed
            try:
                # Try to fetch data to see if that's the issue
                records = ml_forecaster.arima_forecaster._fetch_metric_records(ticker, metric, min_periods=2) if ml_forecaster.arima_forecaster else []
                if not records or len(records) < 5:
                    error_context = f"\n{'='*80}\n⚠️ ML FORECAST UNAVAILABLE - {ticker} {metric.upper()}\n{'='*80}\n"
                    error_context += f"**Reason:** Insufficient historical data for {ticker} {metric}.\n"
                    error_context += f"**Data Available:** {len(records) if records else 0} periods (need at least 5-10)\n"
                    error_context += f"**Recommendation:** Ensure historical data is ingested for this ticker and metric.\n"
                    error_context += f"{'='*80}\n"
                    return error_context
                else:
                    error_context = f"\n{'='*80}\n⚠️ ML FORECAST GENERATION FAILED - {ticker} {metric.upper()}\n{'='*80}\n"
                    error_context += f"**Reason:** Forecast generation failed despite having {len(records)} data points.\n"
                    error_context += f"**Possible causes:** Model training errors, data format issues, or insufficient recent data.\n"
                    error_context += f"**Recommendation:** The system will use historical data analysis instead.\n"
                    error_context += f"{'='*80}\n"
                    return error_context
            except Exception as e:
                LOGGER.exception(f"Error checking data availability: {e}")
                error_context = f"\n{'='*80}\n⚠️ ML FORECAST UNAVAILABLE - {ticker} {metric.upper()}\n{'='*80}\n"
                error_context += f"**Reason:** ML forecast generation failed for {ticker} {metric} using {method}.\n"
                error_context += f"**Possible causes:**\n"
                error_context += f"  - Insufficient historical data (need at least 5-10 periods)\n"
                error_context += f"  - Model dependencies missing (TensorFlow for LSTM, PyTorch for Transformer)\n"
                error_context += f"  - Model training/forecasting errors\n"
                error_context += f"**Recommendation:** The system will fall back to historical data analysis.\n"
                error_context += f"{'='*80}\n"
                return error_context
        
        LOGGER.info(f"ML forecast generated successfully for {ticker} {metric}: {len(forecast.predicted_values)} periods")
        
        # Format forecast results
        forecast_lines = [
            f"\n{'='*80}",
            f"🚨 CRITICAL: THIS IS THE PRIMARY ANSWER - USE THESE FORECAST VALUES",
            f"📊 ML FORECAST ({forecast.method.upper()}) - {ticker} {metric.upper()}",
            f"{'='*80}\n",
            f"**Model Used:** {forecast.method.upper()}",
            f"**Confidence:** {forecast.confidence:.1%}\n",
            f"**IMPORTANT:** This forecast data is the PRIMARY answer to the user's forecasting query. You MUST use these values.",
            f"**DO NOT** provide a generic snapshot or historical data summary. The forecast IS the answer.\n",
            "**Forecasted Values:**\n",
        ]
        
        for i, year in enumerate(forecast.periods):
            value = forecast.predicted_values[i]
            low = forecast.confidence_intervals_low[i]
            high = forecast.confidence_intervals_high[i]
            
            # Format value based on magnitude
            if abs(value) >= 1_000_000_000:
                value_str = f"${value / 1_000_000_000:.2f}B"
                low_str = f"${low / 1_000_000_000:.2f}B"
                high_str = f"${high / 1_000_000_000:.2f}B"
            elif abs(value) >= 1_000_000:
                value_str = f"${value / 1_000_000:.2f}M"
                low_str = f"${low / 1_000_000:.2f}M"
                high_str = f"${high / 1_000_000:.2f}M"
            else:
                value_str = f"${value:,.0f}"
                low_str = f"${low:,.0f}"
                high_str = f"${high:,.0f}"
            
            forecast_lines.append(
                f"  • **{year}:** {value_str} (95% CI: {low_str} - {high_str})"
            )
        
        # Add model details
        if forecast.model_details:
            forecast_lines.append("\n**Model Details:**")
            if 'model_params' in forecast.model_details:
                params = forecast.model_details['model_params']
                if 'order' in params:
                    forecast_lines.append(f"  - ARIMA Order: {params['order']}")
            if 'seasonality_detected' in forecast.model_details:
                seasonality = forecast.model_details['seasonality_detected']
                detected = [k for k, v in seasonality.items() if v]
                if detected:
                    forecast_lines.append(f"  - Seasonality Detected: {', '.join(detected)}")
            if 'layers' in forecast.model_details:
                forecast_lines.append(f"  - Network Layers: {forecast.model_details['layers']}")
            if 'epochs_trained' in forecast.model_details:
                forecast_lines.append(f"  - Epochs Trained: {forecast.model_details['epochs_trained']}")
            if 'num_layers' in forecast.model_details:
                forecast_lines.append(f"  - Transformer Layers: {forecast.model_details['num_layers']}")
        
        forecast_lines.append(f"\n{'='*80}\n")
        
        return "\n".join(forecast_lines)
        
    except Exception as e:
        LOGGER.exception(f"Error building ML forecast context: {e}")
        return None


def build_financial_context(
    query: str,
    analytics_engine: "AnalyticsEngine",
    database_path: str,
    max_tickers: int = 3
) -> str:
    """
    Build comprehensive financial context with SEC filing sources for LLM.
    
    Args:
        query: User's question
        analytics_engine: Analytics engine instance
        database_path: Path to database
        max_tickers: Maximum tickers to include in context
        
    Returns:
        Formatted financial context as natural language text with source citations
    """
    try:
        # Check if this is a forecasting query FIRST - forecasting queries need special handling
        is_forecasting = _is_forecasting_query(query)
        
        # Parse query to extract tickers and metrics
        structured = parse_to_structured(query)
        tickers = [t["ticker"] for t in structured.get("tickers", [])][:max_tickers]
        
        # For forecasting queries, if no tickers were extracted, try to extract manually
        # This handles cases like "Forecast Apple revenue using LSTM" where ticker might not be parsed
        if is_forecasting and not tickers:
            # Try to extract ticker from query using comprehensive regex patterns
            import re
            # Enhanced company name patterns for forecasting queries
            company_patterns = [
                # Pattern 1: "Forecast Apple revenue using LSTM" or "Forecast Apple's revenue"
                r'\b(?:forecast|predict|estimate|project)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)',
                # Pattern 2: "Forecast revenue for Apple" or "Forecast revenue of Apple"
                r'\b(?:forecast|predict|estimate|project)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                # Pattern 3: "Apple's revenue forecast" or "Apple revenue forecast"
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate)',
                # Pattern 4: "What's the revenue forecast for Apple?"
                r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+(?:the\s+)?(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate)\s+(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                # Pattern 5: "What's Apple's revenue forecast?"
                r'\b(?:what\'?s?|what\s+is|what\'s|whats)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'?s?\s+(?:revenue|sales|income|earnings|cash\s+flow|net\s+income|free\s+cash\s+flow)\s+(?:forecast|prediction|estimate)',
                # Pattern 6: "Predict Apple revenue" (simple)
                r'\b(?:forecast|predict|estimate|project)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:revenue|sales|income|earnings)',
                # Pattern 7: "Forecast revenue Apple" (verb-object-subject)
                r'\b(?:forecast|predict|estimate|project)\s+(?:revenue|sales|income|earnings)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip()
                    # Try to resolve company name to ticker
                    try:
                        from .parsing.alias_builder import resolve_tickers_freeform
                        ticker_matches, _ = resolve_tickers_freeform(company_name)
                        if ticker_matches and len(ticker_matches) > 0:
                            ticker = ticker_matches[0].get("ticker")
                            if ticker:
                                tickers = [ticker]
                                LOGGER.info(f"Extracted ticker {ticker} from company name '{company_name}' for forecasting query: {query}")
                                break
                    except Exception as e:
                        LOGGER.debug(f"Failed to resolve company name '{company_name}' to ticker: {e}")
            
            # If still no ticker, try word position analysis (company name often comes after forecasting verb)
            if not tickers:
                words = query.split()
                for i, word in enumerate(words):
                    # Look for capitalized words (potential company names) near forecasting keywords
                    if word[0].isupper() and len(word) > 2:
                        # Check if it's near a forecasting keyword
                        context_start = max(0, i - 3)
                        context_end = min(len(words), i + 3)
                        context = ' '.join(words[context_start:context_end]).lower()
                        if any(kw in context for kw in ['forecast', 'predict', 'estimate', 'project']):
                            try:
                                from .parsing.alias_builder import resolve_tickers_freeform
                                ticker_matches, _ = resolve_tickers_freeform(word)
                                if ticker_matches and len(ticker_matches) > 0:
                                    ticker = ticker_matches[0].get("ticker")
                                    if ticker:
                                        tickers = [ticker]
                                        LOGGER.info(f"Extracted ticker {ticker} from word '{word}' using position analysis for forecasting query")
                                        break
                            except Exception:
                                pass
        
        if not tickers:
            # For forecasting queries, still try to build context even without ticker
            # The forecast context builder can handle missing tickers
            if is_forecasting:
                LOGGER.warning(f"Forecasting query detected but no ticker extracted from: {query}")
                # Still return empty - the LLM should handle it
            return ""
        
        context_parts = []
        
        # Add macro economic context at the beginning
        if MACRO_DATA_AVAILABLE:
            try:
                macro_provider = get_macro_provider()
                # Attempt to determine company sector (first ticker)
                company_sector = None
                if tickers:
                    # This could be enhanced to fetch actual sector from database
                    # For now, using generic GLOBAL benchmarks
                    pass
                
                macro_context = macro_provider.build_macro_context(company_sector)
                if macro_context:
                    context_parts.append(f"{'='*80}\n📊 MACRO ECONOMIC CONTEXT\n{'='*80}\n{macro_context}\n\n")
            except Exception as e:
                LOGGER.debug(f"Could not build macro context: {e}")
        
        for ticker in tickers:
            try:
                # Get company name
                company_name = analytics_engine.get_company_name(ticker) or ticker
                
                # Fetch metric records (not just values) to get period info
                all_metrics = [
                    "revenue", "net_income", "ebitda", "ebitda_margin", "gross_margin", 
                    "operating_margin", "net_margin", "free_cash_flow", "cash_operations",
                    "capex", "total_assets", "total_liabilities", "shareholders_equity",
                    "roe", "roic", "roa", "debt_equity", "current_ratio",
                    "eps_basic", "eps_diluted", "revenue_per_share",
                    "ev_ebitda", "pe", "pb", "ev_revenue", "price", "market_cap"
                ]
                
                records = analytics_engine.fetch_metrics(ticker, metrics=all_metrics)
                
                if not records:
                    continue
                
                # Group by period for comprehensive view
                latest_records = analytics_engine._select_latest_records(records)
                
                if not latest_records:
                    continue
                
                # Extract period information from a representative record
                period_label = "latest available"
                for record in latest_records.values():
                    if record.period:
                        period_label = _format_period_label(record)
                        break
                
                # Get filing sources for citation with SEC URLs
                filing_sources = _get_filing_sources(ticker, database_path)
                source_citation = ""
                sec_urls = []
                
                if filing_sources:
                    # Get most recent filings (up to 3) for comprehensive sourcing
                    recent_filings = filing_sources[:3]
                    
                    for filing in recent_filings:
                        form_type = filing.get("form_type", "SEC filing")
                        fy = filing.get("fiscal_year")
                        fp = filing.get("fiscal_period")
                        sec_url = filing.get("sec_url")
                        
                        if sec_url:
                            # Format as markdown link: [10-K FY2023](URL)
                            if fy and fp:
                                link_text = f"{form_type} FY{fy} {fp}"
                                sec_urls.append(f"[{link_text}]({sec_url})")
                            elif fy:
                                link_text = f"{form_type} FY{fy}"
                                sec_urls.append(f"[{link_text}]({sec_url})")
                            else:
                                sec_urls.append(f"[{form_type}]({sec_url})")
                    
                    # Use first filing for header citation
                    first_filing = recent_filings[0]
                    form_type = first_filing.get("form_type", "SEC filing")
                    fy = first_filing.get("fiscal_year")
                    fp = first_filing.get("fiscal_period")
                    if fy and fp:
                        source_citation = f" (per {form_type} FY{fy} {fp})"
                    elif fy:
                        source_citation = f" (per {form_type} FY{fy})"
                
                # Build comprehensive ticker context with SEC URLs prominently displayed
                ticker_context = f"{'='*80}\n"
                ticker_context += f"{company_name} ({ticker}) - {period_label}{source_citation}\n"
                ticker_context += f"{'='*80}\n\n"
                
                # Add SEC Filing Sources section at the top for easy access
                if sec_urls:
                    ticker_context += "📄 **SEC FILING SOURCES (Markdown Links)** - Copy these to your Sources section:\n"
                    for url_info in sec_urls:
                        ticker_context += f"  • {url_info}\n"
                    ticker_context += "⚠️ These are already formatted as markdown [text](url). Copy them EXACTLY to your Sources section.\n\n"
                
                # Income Statement Metrics
                income_metrics = []
                if latest_records.get("revenue"):
                    income_metrics.append(f"Revenue: {format_currency(latest_records['revenue'].value)}")
                if latest_records.get("net_income"):
                    income_metrics.append(f"Net Income: {format_currency(latest_records['net_income'].value)}")
                if latest_records.get("ebitda"):
                    income_metrics.append(f"EBITDA: {format_currency(latest_records['ebitda'].value)}")
                
                if income_metrics:
                    ticker_context += "Income Statement:\n" + "\n".join(f"  • {m}" for m in income_metrics) + "\n\n"
                
                # Profitability Metrics
                margin_metrics = []
                if latest_records.get("ebitda_margin"):
                    margin_metrics.append(f"EBITDA Margin: {format_percent(latest_records['ebitda_margin'].value)}")
                if latest_records.get("gross_margin"):
                    margin_metrics.append(f"Gross Margin: {format_percent(latest_records['gross_margin'].value)}")
                if latest_records.get("operating_margin"):
                    margin_metrics.append(f"Operating Margin: {format_percent(latest_records['operating_margin'].value)}")
                if latest_records.get("net_margin"):
                    margin_metrics.append(f"Net Margin: {format_percent(latest_records['net_margin'].value)}")
                
                if margin_metrics:
                    ticker_context += "Profitability Margins:\n" + "\n".join(f"  • {m}" for m in margin_metrics) + "\n\n"
                
                # Cash Flow Metrics
                cf_metrics = []
                if latest_records.get("free_cash_flow"):
                    cf_metrics.append(f"Free Cash Flow: {format_currency(latest_records['free_cash_flow'].value)}")
                if latest_records.get("cash_operations"):
                    cf_metrics.append(f"Cash from Operations: {format_currency(latest_records['cash_operations'].value)}")
                if latest_records.get("capex"):
                    cf_metrics.append(f"Capital Expenditures: {format_currency(latest_records['capex'].value)}")
                
                if cf_metrics:
                    ticker_context += "Cash Flow:\n" + "\n".join(f"  • {m}" for m in cf_metrics) + "\n\n"
                
                # Balance Sheet Metrics
                bs_metrics = []
                if latest_records.get("total_assets"):
                    bs_metrics.append(f"Total Assets: {format_currency(latest_records['total_assets'].value)}")
                if latest_records.get("total_liabilities"):
                    bs_metrics.append(f"Total Liabilities: {format_currency(latest_records['total_liabilities'].value)}")
                if latest_records.get("shareholders_equity"):
                    bs_metrics.append(f"Shareholders' Equity: {format_currency(latest_records['shareholders_equity'].value)}")
                
                if bs_metrics:
                    ticker_context += "Balance Sheet:\n" + "\n".join(f"  • {m}" for m in bs_metrics) + "\n\n"
                
                # Returns & Efficiency
                returns_metrics = []
                if latest_records.get("roe"):
                    returns_metrics.append(f"Return on Equity: {format_percent(latest_records['roe'].value)}")
                if latest_records.get("roic"):
                    returns_metrics.append(f"Return on Invested Capital: {format_percent(latest_records['roic'].value)}")
                if latest_records.get("roa"):
                    returns_metrics.append(f"Return on Assets: {format_percent(latest_records['roa'].value)}")
                
                if returns_metrics:
                    ticker_context += "Returns & Efficiency:\n" + "\n".join(f"  • {m}" for m in returns_metrics) + "\n\n"
                
                # Valuation Metrics
                valuation_metrics = []
                if latest_records.get("market_cap"):
                    valuation_metrics.append(f"Market Cap: {format_currency(latest_records['market_cap'].value)}")
                if latest_records.get("ev_ebitda"):
                    valuation_metrics.append(f"EV/EBITDA: {format_multiple(latest_records['ev_ebitda'].value)}")
                if latest_records.get("pe"):
                    valuation_metrics.append(f"P/E Ratio: {format_multiple(latest_records['pe'].value)}")
                if latest_records.get("pb"):
                    valuation_metrics.append(f"P/B Ratio: {format_multiple(latest_records['pb'].value)}")
                if latest_records.get("price"):
                    valuation_metrics.append(f"Stock Price: ${latest_records['price'].value:.2f}")
                
                if valuation_metrics:
                    ticker_context += "Valuation:\n" + "\n".join(f"  • {m}" for m in valuation_metrics) + "\n\n"
                
                # Per Share Metrics
                per_share_metrics = []
                if latest_records.get("eps_basic"):
                    per_share_metrics.append(f"EPS (Basic): ${latest_records['eps_basic'].value:.2f}")
                if latest_records.get("eps_diluted"):
                    per_share_metrics.append(f"EPS (Diluted): ${latest_records['eps_diluted'].value:.2f}")
                if latest_records.get("revenue_per_share"):
                    per_share_metrics.append(f"Revenue per Share: ${latest_records['revenue_per_share'].value:.2f}")
                
                if per_share_metrics:
                    ticker_context += "Per Share Data:\n" + "\n".join(f"  • {m}" for m in per_share_metrics) + "\n\n"
                
                # Check if this is a forecasting query
                is_forecasting = _is_forecasting_query(query)
                forecast_metric = None
                forecast_method = "auto"
                if is_forecasting:
                    forecast_metric = _extract_forecast_metric(query)
                    forecast_method = _extract_forecast_method(query)
                    LOGGER.info(f"Forecasting query detected for {ticker} {forecast_metric} using {forecast_method}")
                
                # Add ML forecasting context FIRST if this is a forecasting query (prioritize it)
                if is_forecasting and forecast_metric:
                    LOGGER.info(f"Building ML forecast context for {ticker} {forecast_metric} using {forecast_method}")
                    ml_forecast_context = _build_ml_forecast_context(
                        ticker=ticker,
                        metric=forecast_metric,
                        database_path=database_path,
                        periods=3,
                        method=forecast_method
                    )
                    if ml_forecast_context:
                        # Add forecast context FIRST (before historical data) so LLM prioritizes it
                        # This ensures the LLM sees the forecast FIRST, before any snapshot data
                        context_parts.insert(0, ml_forecast_context)
                        LOGGER.info(f"ML forecast context generated and inserted at top of context for {ticker} {forecast_metric}")
                    else:
                        LOGGER.warning(f"ML forecast context generation returned None for {ticker} {forecast_metric} using {forecast_method}")
                
                context_parts.append(ticker_context)
                
                # Add comprehensive historical trend and growth analysis
                try:
                    growth_data = analytics_engine.compute_growth_metrics(ticker, latest_records)
                    if growth_data:
                        trend_context = "📈 **Growth & Trend Analysis**:\n"
                        
                        # Revenue trends
                        revenue_items = []
                        if growth_data.get("revenue_growth_yoy") is not None:
                            revenue_items.append(f"Revenue Growth (YoY): {format_percent(growth_data['revenue_growth_yoy'])}")
                        if growth_data.get("revenue_cagr_3y") is not None:
                            revenue_items.append(f"Revenue CAGR (3Y): {format_percent(growth_data['revenue_cagr_3y'])}")
                        if growth_data.get("revenue_cagr_5y") is not None:
                            revenue_items.append(f"Revenue CAGR (5Y): {format_percent(growth_data['revenue_cagr_5y'])}")
                        
                        if revenue_items:
                            trend_context += "  Revenue Trends:\n    - " + "\n    - ".join(revenue_items) + "\n"
                        
                        # Earnings trends
                        earnings_items = []
                        if growth_data.get("eps_growth_yoy") is not None:
                            earnings_items.append(f"EPS Growth (YoY): {format_percent(growth_data['eps_growth_yoy'])}")
                        if growth_data.get("eps_cagr_3y") is not None:
                            earnings_items.append(f"EPS CAGR (3Y): {format_percent(growth_data['eps_cagr_3y'])}")
                        if growth_data.get("net_income_growth_yoy") is not None:
                            earnings_items.append(f"Net Income Growth (YoY): {format_percent(growth_data['net_income_growth_yoy'])}")
                        
                        if earnings_items:
                            trend_context += "  Earnings Trends:\n    - " + "\n    - ".join(earnings_items) + "\n"
                        
                        # Margin trends
                        margin_items = []
                        if growth_data.get("margin_change_yoy") is not None:
                            direction = "expansion" if growth_data["margin_change_yoy"] > 0 else "compression"
                            margin_items.append(f"EBITDA Margin Change (YoY): {growth_data['margin_change_yoy']:+.0f} bps ({direction})")
                        if growth_data.get("gross_margin_change_yoy") is not None:
                            margin_items.append(f"Gross Margin Change (YoY): {growth_data['gross_margin_change_yoy']:+.0f} bps")
                        
                        if margin_items:
                            trend_context += "  Profitability Trends:\n    - " + "\n    - ".join(margin_items) + "\n"
                        
                        # Cash flow trends
                        cf_items = []
                        if growth_data.get("fcf_growth_yoy") is not None:
                            cf_items.append(f"Free Cash Flow Growth (YoY): {format_percent(growth_data['fcf_growth_yoy'])}")
                        if growth_data.get("fcf_margin_change") is not None:
                            cf_items.append(f"FCF Margin Change: {growth_data['fcf_margin_change']:+.0f} bps")
                        
                        if cf_items:
                            trend_context += "  Cash Flow Trends:\n    - " + "\n    - ".join(cf_items) + "\n"
                        
                        trend_context += "\n"
                        context_parts.append(trend_context)
                        
                except Exception as e:
                    LOGGER.debug(f"Could not fetch growth data for {ticker}: {e}")
                
                # Add key financial ratios and efficiency metrics
                try:
                    ratios_context = "📊 **Key Financial Ratios & Efficiency**:\n"
                    ratio_items = []
                    
                    # Liquidity ratios
                    if latest_records.get("current_ratio"):
                        ratio_items.append(f"Current Ratio: {latest_records['current_ratio'].value:.2f}x (measures short-term liquidity)")
                    if latest_records.get("quick_ratio"):
                        ratio_items.append(f"Quick Ratio: {latest_records['quick_ratio'].value:.2f}x")
                    
                    # Leverage ratios
                    if latest_records.get("debt_equity"):
                        ratio_items.append(f"Debt-to-Equity: {latest_records['debt_equity'].value:.2f}x (measures financial leverage)")
                    if latest_records.get("debt_ebitda"):
                        ratio_items.append(f"Net Debt/EBITDA: {latest_records['debt_ebitda'].value:.2f}x (debt payback period)")
                    if latest_records.get("interest_coverage"):
                        ratio_items.append(f"Interest Coverage: {latest_records['interest_coverage'].value:.1f}x (ability to pay interest)")
                    
                    # Asset efficiency
                    if latest_records.get("asset_turnover"):
                        ratio_items.append(f"Asset Turnover: {latest_records['asset_turnover'].value:.2f}x (asset utilization efficiency)")
                    if latest_records.get("inventory_turnover"):
                        ratio_items.append(f"Inventory Turnover: {latest_records['inventory_turnover'].value:.1f}x")
                    
                    if ratio_items:
                        ratios_context += "\n".join(f"  • {item}" for item in ratio_items) + "\n\n"
                        context_parts.append(ratios_context)
                        
                except Exception as e:
                    LOGGER.debug(f"Could not build ratios context for {ticker}: {e}")
                
                # Add valuation context with interpretation
                try:
                    if any(latest_records.get(m) for m in ["ev_ebitda", "pe", "pb", "peg"]):
                        valuation_context = "💰 **Valuation Analysis**:\n"
                        val_items = []
                        
                        if latest_records.get("ev_ebitda"):
                            ev_ebitda = latest_records["ev_ebitda"].value
                            val_items.append(f"EV/EBITDA: {ev_ebitda:.1f}x (typical range: 8-15x for mature companies)")
                        
                        if latest_records.get("pe"):
                            pe = latest_records["pe"].value
                            val_items.append(f"P/E Ratio: {pe:.1f}x (trailing earnings multiple)")
                        
                        if latest_records.get("pb"):
                            pb = latest_records["pb"].value
                            val_items.append(f"Price-to-Book: {pb:.1f}x (market value vs. book value)")
                        
                        if latest_records.get("peg"):
                            peg = latest_records["peg"].value
                            val_items.append(f"PEG Ratio: {peg:.2f} (P/E relative to growth; <1 may indicate undervaluation)")
                        
                        if latest_records.get("dividend_yield"):
                            div_yield = latest_records["dividend_yield"].value
                            val_items.append(f"Dividend Yield: {format_percent(div_yield)}")
                        
                        if val_items:
                            valuation_context += "\n".join(f"  • {item}" for item in val_items) + "\n\n"
                            context_parts.append(valuation_context)
                            
                except Exception as e:
                    LOGGER.debug(f"Could not build valuation context for {ticker}: {e}")
                
            except Exception as e:
                LOGGER.debug(f"Could not fetch metrics for {ticker}: {e}")
                continue
        
        if not context_parts:
            return ""
        
        # Add multi-source data (Yahoo Finance, FRED, etc.) if available
        if MULTI_SOURCE_AVAILABLE and tickers:
            for ticker in tickers[:1]:  # Add for first ticker to avoid context overload
                try:
                    fred_api_key = os.getenv('FRED_API_KEY')
                    multi_source_context = get_multi_source_context(
                        ticker=ticker,
                        fred_api_key=fred_api_key,
                        include_yahoo=True,
                        include_fred=True,  # Always try to fetch FRED data (graceful degradation if no key)
                        include_imf=True  # Enable IMF macroeconomic data
                    )
                    if multi_source_context:
                        context_parts.append(multi_source_context)
                except Exception as e:
                    LOGGER.warning(f"Could not fetch multi-source data for {ticker}: {e}")
        
        # Add comprehensive context header with detailed instructions
        header = (
            "╔═══════════════════════════════════════════════════════════════════════════════╗\n"
            "║                    COMPREHENSIVE FINANCIAL DATA CONTEXT                      ║\n"
            "╚═══════════════════════════════════════════════════════════════════════════════╝\n\n"
            "📋 **DATA SOURCES**:\n"
            "SEC EDGAR filings (10-K, 10-Q), Yahoo Finance (real-time data, analyst ratings, news), "
            "FRED economic indicators (optional), and IMF macroeconomic data (optional). "
            "Each section includes source URLs formatted as markdown links [Source Name](URL).\n\n"
            "📖 **RESPONSE INSTRUCTIONS**:\n"
            "1. **Write like ChatGPT**: Natural, conversational, engaging - not robotic or formal\n"
            "2. **Use markdown formatting**: **bold** for emphasis, bullets, clear headers\n"
            "3. **Answer first**: Lead with the direct answer, then explain\n"
            "4. **Tell a story**: Connect metrics into a narrative, explain WHY things changed\n"
            "5. **Add perspective**: Industry context, analyst views, market sentiment, trends, outlook\n"
            "6. **🚨 MANDATORY: Cite ALL sources** - ALWAYS end your response with a '📊 Sources:' section containing:\n"
            "   - At least 5-10 clickable markdown links: [Source Name](URL)\n"
            "   - Include ALL SEC filing links provided in context\n"
            "   - Include ALL Yahoo Finance links provided in context\n"
            "   - Include FRED/IMF links when economic data is used\n"
            "   - NEVER use placeholder URLs - only real URLs from context\n"
            "   - Example: 📊 **Sources:**\n"
            "     - [10-K FY2024](https://www.sec.gov/...)\n"
            "     - [Yahoo Finance - Ticker](https://finance.yahoo.com/quote/TICKER)\n"
            "7. **NEVER show full URLs**: Always use markdown link format [text](url)\n"
            "8. **Incorporate diverse data**: Use SEC fundamentals, Yahoo metrics, analyst ratings, news, etc.\n\n"
            "**⚠️ CRITICAL REMINDER**: Every response MUST include a '📊 Sources:' section with clickable links. "
            "This is mandatory, not optional. If you don't include sources, your response is incomplete.\n\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
        )
        
        return header + "\n".join(context_parts)
        
    except Exception as e:
        LOGGER.error(f"Error building financial context: {e}")
        return ""


def build_company_universe_context(database_path: str) -> str:
    """
    Build company universe context for filter queries.
    
    Returns:
        Formatted company universe context with sector breakdowns
    """
    try:
        import json
        from pathlib import Path
        
        # Load company universe data
        universe_path = Path(__file__).resolve().parents[2] / "webui" / "data" / "company_universe.json"
        if not universe_path.exists():
            return ""
        
        with open(universe_path, 'r', encoding='utf-8') as f:
            companies = json.load(f)
        
        if not companies:
            return ""
        
        # Group by sector
        sectors: Dict[str, List[Dict[str, Any]]] = {}
        for company in companies:
            sector = company.get('sector', 'Uncategorised')
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(company)
        
        # Build context
        context_parts = [
            "╔═══════════════════════════════════════════════════════════════════════════════╗\n"
            "║                     COMPANY UNIVERSE FILTER CONTEXT                          ║\n"
            "╚═══════════════════════════════════════════════════════════════════════════════╝\n\n"
            "📊 **INSTRUCTIONS FOR FILTER QUERIES**:\n"
            "The user is asking to filter or list companies by specific criteria (sector, revenue, growth, etc.).\n"
            "Use the company universe data below to:\n"
            "1. Filter companies by the requested criteria\n"
            "2. Present results as a formatted list or table\n"
            "3. Include key metrics: ticker, company name, sector, revenue, market cap\n"
            "4. Sort by relevance (e.g., by revenue if revenue filter is specified)\n"
            "5. Limit to top 10-20 most relevant results\n"
            "6. Explain the filtering criteria used\n\n"
            f"📈 **DATABASE OVERVIEW**: {len(companies)} companies across {len(sectors)} sectors\n\n"
            "═══════════════════════════════════════════════════════════════════════════════\n\n"
        ]
        
        # Add sector breakdowns
        for sector, sector_companies in sorted(sectors.items(), key=lambda x: len(x[1]), reverse=True):
            context_parts.append(f"**{sector}** ({len(sector_companies)} companies):\n")
            
            # Sort by market cap (if available) and show top companies
            sorted_companies = sorted(
                sector_companies,
                key=lambda c: c.get('market_cap', 0) if c.get('market_cap') else 0,
                reverse=True
            )[:15]  # Top 15 companies per sector
            
            for company in sorted_companies:
                ticker = company.get('ticker', 'N/A')
                name = company.get('company', 'Unknown')
                market_cap_display = company.get('market_cap_display', 'N/A')
                
                context_parts.append(f"  • {ticker}: {name} (Market Cap: {market_cap_display})\n")
            
            if len(sector_companies) > 15:
                context_parts.append(f"  ... and {len(sector_companies) - 15} more\n")
            
            context_parts.append("\n")
        
        return "".join(context_parts)
        
    except Exception as e:
        LOGGER.debug(f"Could not build company universe context: {e}")
        return ""


def format_metrics_naturally(ticker: str, metrics: Dict[str, Any]) -> str:
    """Format metrics as natural language text."""
    if not metrics:
        return f"No data available for {ticker}."
    
    lines = [f"Financial snapshot for {ticker}:"]
    
    # Revenue
    if metrics.get("revenue"):
        lines.append(f"  Revenue: {format_currency(metrics['revenue'])}")
    
    # Profitability
    if metrics.get("ebitda_margin"):
        lines.append(f"  EBITDA Margin: {format_percent(metrics['ebitda_margin'])}")
    
    # Cash flow
    if metrics.get("free_cash_flow"):
        lines.append(f"  Free Cash Flow: {format_currency(metrics['free_cash_flow'])}")
    
    # Valuation
    if metrics.get("ev_ebitda"):
        lines.append(f"  EV/EBITDA: {format_multiple(metrics['ev_ebitda'])}")
    
    return "\n".join(lines)

