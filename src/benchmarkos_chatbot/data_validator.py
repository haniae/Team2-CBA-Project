"""Cross-validation system for financial data from multiple sources."""

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from . import database
from .analytics_engine import AnalyticsEngine

LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of cross-validating a metric between sources."""
    ticker: str
    metric: str
    period: str
    sec_value: Optional[float]
    yahoo_value: Optional[float]
    discrepancy: float  # Percentage difference
    is_consistent: bool
    message: str


@dataclass
class DataIssue:
    """Data inconsistency issue found during validation."""
    ticker: str
    metric: str
    period: str
    issue_type: str  # "discrepancy", "missing_source", "outdated"
    severity: str  # "low", "medium", "high", "critical"
    message: str
    sec_value: Optional[float]
    yahoo_value: Optional[float]


def cross_validate_metric(
    ticker: str,
    metric: str,
    period: str,
    analytics_engine: AnalyticsEngine,
    database_path: str,
    max_deviation: float = 5.0
) -> ValidationResult:
    """
    Cross-validate a metric between SEC and Yahoo Finance sources.
    
    Args:
        ticker: Company ticker symbol
        metric: Metric name (e.g., "revenue", "net_income")
        period: Time period (e.g., "2024", "FY2024")
        analytics_engine: Analytics engine for data access
        database_path: Path to database
        max_deviation: Maximum allowed deviation percentage (default 5%)
    
    Returns:
        ValidationResult with cross-validation results
    """
    try:
        # Get SEC value from database
        sec_value = _get_sec_value(ticker, metric, period, analytics_engine)
        
        # Get Yahoo Finance value (if available)
        yahoo_value = _get_yahoo_value(ticker, metric, period, database_path)
        
        # Compare values
        if sec_value is None and yahoo_value is None:
            return ValidationResult(
                ticker=ticker,
                metric=metric,
                period=period,
                sec_value=None,
                yahoo_value=None,
                discrepancy=100.0,
                is_consistent=False,
                message="No data available from either source"
            )
        
        if sec_value is None:
            return ValidationResult(
                ticker=ticker,
                metric=metric,
                period=period,
                sec_value=None,
                yahoo_value=yahoo_value,
                discrepancy=100.0,
                is_consistent=False,
                message=f"SEC data missing, Yahoo Finance has {yahoo_value}"
            )
        
        if yahoo_value is None:
            return ValidationResult(
                ticker=ticker,
                metric=metric,
                period=period,
                sec_value=sec_value,
                yahoo_value=None,
                discrepancy=0.0,
                is_consistent=True,
                message=f"Yahoo Finance data missing, using SEC value {sec_value}"
            )
        
        # Calculate discrepancy
        if sec_value == 0:
            discrepancy = 100.0 if yahoo_value != 0 else 0.0
        else:
            discrepancy = abs((yahoo_value - sec_value) / sec_value) * 100.0
        
        is_consistent = discrepancy <= max_deviation
        
        message = (
            f"Consistent: SEC {sec_value:.2f} vs Yahoo {yahoo_value:.2f} "
            f"(deviation: {discrepancy:.2f}%)"
            if is_consistent
            else f"Inconsistent: SEC {sec_value:.2f} vs Yahoo {yahoo_value:.2f} "
                 f"(deviation: {discrepancy:.2f}%)"
        )
        
        return ValidationResult(
            ticker=ticker,
            metric=metric,
            period=period,
            sec_value=sec_value,
            yahoo_value=yahoo_value,
            discrepancy=discrepancy,
            is_consistent=is_consistent,
            message=message
        )
    
    except Exception as e:
        LOGGER.warning(f"Error cross-validating {ticker} {metric} {period}: {e}", exc_info=True)
        return ValidationResult(
            ticker=ticker,
            metric=metric,
            period=period,
            sec_value=None,
            yahoo_value=None,
            discrepancy=100.0,
            is_consistent=False,
            message=f"Error during cross-validation: {str(e)}"
        )


def _get_sec_value(
    ticker: str,
    metric: str,
    period: str,
    analytics_engine: AnalyticsEngine
) -> Optional[float]:
    """Get metric value from SEC database."""
    try:
        metrics = analytics_engine.get_metrics(ticker, period_filters=None)
        
        for metric_record in metrics:
            if metric_record.metric == metric:
                # Try to match period
                if period in metric_record.period or metric_record.period in period:
                    return metric_record.value
        
        # If no period match, return latest
        for metric_record in metrics:
            if metric_record.metric == metric:
                return metric_record.value
        
        return None
    except Exception as e:
        LOGGER.debug(f"Error getting SEC value for {ticker} {metric}: {e}")
        return None


def _get_yahoo_value(
    ticker: str,
    metric: str,
    period: str,
    database_path: str
) -> Optional[float]:
    """Get metric value from Yahoo Finance (if available in database)."""
    try:
        # Check if we have Yahoo Finance data in market_quotes or other tables
        # For now, return None as Yahoo Finance integration may vary
        # This can be extended based on actual data storage structure
        return None
    except Exception as e:
        LOGGER.debug(f"Error getting Yahoo Finance value for {ticker} {metric}: {e}")
        return None


def validate_context_data(
    context: str,
    analytics_engine: AnalyticsEngine,
    database_path: str
) -> List[DataIssue]:
    """
    Parse context for all financial data points and cross-validate them.
    
    Args:
        context: Context string that was provided to LLM
        analytics_engine: Analytics engine for data access
        database_path: Path to database
    
    Returns:
        List of DataIssue objects for any inconsistencies found
    """
    issues = []
    
    # Extract data points from context
    # This is a simplified parser - can be enhanced based on actual context format
    data_points = _extract_data_points_from_context(context)
    
    for data_point in data_points:
        validation_result = cross_validate_metric(
            data_point['ticker'],
            data_point['metric'],
            data_point.get('period', 'latest'),
            analytics_engine,
            database_path
        )
        
        if not validation_result.is_consistent:
            severity = _determine_severity(validation_result.discrepancy)
            issues.append(DataIssue(
                ticker=validation_result.ticker,
                metric=validation_result.metric,
                period=validation_result.period,
                issue_type="discrepancy",
                severity=severity,
                message=validation_result.message,
                sec_value=validation_result.sec_value,
                yahoo_value=validation_result.yahoo_value
            ))
    
    return issues


def _extract_data_points_from_context(context: str) -> List[Dict[str, Any]]:
    """
    Extract financial data points from context string.
    
    This is a simplified implementation - can be enhanced based on actual context format.
    """
    data_points = []
    
    # Look for patterns like "AAPL revenue: $394.3B (FY2024)"
    pattern = r'([A-Z]{1,5})\s+(\w+):\s*\$?([\d,]+\.?\d*)\s*([BMKT]?)\s*(?:\(([^)]+)\))?'
    
    for match in re.finditer(pattern, context, re.IGNORECASE):
        ticker = match.group(1).upper()
        metric_name = match.group(2).lower()
        value_str = match.group(3).replace(',', '')
        unit = match.group(4).upper() if match.group(4) else ''
        period = match.group(5) if match.group(5) else 'latest'
        
        # Map metric names to standard metric names
        metric_map = {
            'revenue': 'revenue',
            'sales': 'revenue',
            'net income': 'net_income',
            'earnings': 'net_income',
            'profit': 'net_income',
            'margin': 'gross_margin',  # Simplified
            'pe': 'pe_ratio',
            'p/e': 'pe_ratio',
        }
        
        metric = metric_map.get(metric_name, metric_name)
        
        try:
            value = float(value_str)
            # Convert to base units if needed
            if unit == 'M':
                value = value / 1000.0
            elif unit == 'T':
                value = value * 1000.0
            
            data_points.append({
                'ticker': ticker,
                'metric': metric,
                'value': value,
                'period': period
            })
        except ValueError:
            continue
    
    return data_points


def _determine_severity(discrepancy: float) -> str:
    """Determine severity level based on discrepancy percentage."""
    if discrepancy > 50.0:
        return "critical"
    elif discrepancy > 20.0:
        return "high"
    elif discrepancy > 10.0:
        return "medium"
    else:
        return "low"

