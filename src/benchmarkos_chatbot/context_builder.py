"""Smart financial context builder for LLM-powered responses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from .parsing.parse import parse_to_structured

if TYPE_CHECKING:
    from .analytics_engine import AnalyticsEngine

LOGGER = logging.getLogger(__name__)


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


def build_financial_context(
    query: str,
    analytics_engine: "AnalyticsEngine",
    database_path: str,
    max_tickers: int = 3
) -> str:
    """
    Build relevant financial context for LLM based on the query.
    
    Args:
        query: User's question
        analytics_engine: Analytics engine instance
        database_path: Path to database
        max_tickers: Maximum tickers to include in context
        
    Returns:
        Formatted financial context as natural language text
    """
    try:
        # Parse query to extract tickers and metrics
        structured = parse_to_structured(query)
        tickers = [t["ticker"] for t in structured.get("tickers", [])][:max_tickers]
        metrics_mentioned = [m["key"] for m in structured.get("vmetrics", [])]
        
        if not tickers:
            return ""
        
        context_parts = []
        
        for ticker in tickers:
            try:
                # Get latest metrics using the analytics engine
                latest_metrics = analytics_engine.latest_metrics(ticker)
                
                if not latest_metrics:
                    continue
                
                # Format core financial data as natural text
                ticker_context = f"Financial data for {ticker}:\n"
                
                # Add key metrics
                if latest_metrics.get("revenue"):
                    ticker_context += f"- Revenue (TTM): {format_currency(latest_metrics.get('revenue'))}\n"
                
                if latest_metrics.get("ebitda_margin"):
                    ticker_context += f"- EBITDA Margin: {format_percent(latest_metrics.get('ebitda_margin'))}\n"
                
                if latest_metrics.get("net_margin"):
                    ticker_context += f"- Net Margin: {format_percent(latest_metrics.get('net_margin'))}\n"
                
                if latest_metrics.get("free_cash_flow"):
                    ticker_context += f"- Free Cash Flow: {format_currency(latest_metrics.get('free_cash_flow'))}\n"
                
                if latest_metrics.get("return_on_equity"):
                    ticker_context += f"- Return on Equity: {format_percent(latest_metrics.get('return_on_equity'))}\n"
                
                # Add valuation metrics
                if latest_metrics.get("ev_ebitda"):
                    ticker_context += f"- EV/EBITDA: {format_multiple(latest_metrics.get('ev_ebitda'))}\n"
                
                if latest_metrics.get("pe_ratio"):
                    ticker_context += f"- P/E Ratio: {format_multiple(latest_metrics.get('pe_ratio'))}\n"
                
                context_parts.append(ticker_context)
                
                # Add growth context if available
                try:
                    growth_data = analytics_engine.compute_growth_metrics(ticker)
                    if growth_data:
                        growth_context = f"\nGrowth trends for {ticker}:\n"
                        
                        if growth_data.get("revenue_growth_yoy"):
                            growth_context += f"- Revenue growth (YoY): {format_percent(growth_data.get('revenue_growth_yoy'))}\n"
                        
                        if growth_data.get("revenue_cagr_3y"):
                            growth_context += f"- Revenue CAGR (3Y): {format_percent(growth_data.get('revenue_cagr_3y'))}\n"
                        
                        if growth_data.get("margin_change_yoy"):
                            growth_context += f"- Margin change (YoY): {growth_data.get('margin_change_yoy'):+.0f} basis points\n"
                        
                        context_parts.append(growth_context)
                except Exception as e:
                    LOGGER.debug(f"Could not fetch growth data for {ticker}: {e}")
                
            except Exception as e:
                LOGGER.debug(f"Could not fetch metrics for {ticker}: {e}")
                continue
        
        if not context_parts:
            return ""
        
        # Add context header
        header = "Relevant financial data from SEC filings and market data:\n\n"
        return header + "\n".join(context_parts)
        
    except Exception as e:
        LOGGER.error(f"Error building financial context: {e}")
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

