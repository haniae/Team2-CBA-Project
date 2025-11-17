"""Context completeness validation before generating response."""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class ContextCompletenessCheck:
    """Result of context completeness check."""
    is_complete: bool
    missing_elements: List[str]
    confidence: float  # 0.0 to 1.0
    recommendations: List[str]
    warnings: List[str]


def validate_context_completeness(
    context: str,
    user_query: str,
    expected_metrics: Optional[List[str]] = None
) -> ContextCompletenessCheck:
    """
    Validate that context has sufficient data before generating response.
    
    Checks for:
    1. Presence of financial data sections
    2. Required metrics based on query
    3. Data freshness indicators
    4. Source citations in context
    
    Args:
        context: Context to validate
        user_query: User's query to understand what data is needed
        expected_metrics: Optional list of metrics that should be present
    
    Returns:
        ContextCompletenessCheck with validation results
    """
    missing_elements = []
    warnings = []
    recommendations = []
    
    # Check 1: Basic financial data presence
    has_financial_data = bool(
        re.search(r'FINANCIAL DATA|DATABASE RECORDS|REVENUE|NET INCOME|EBITDA', context, re.IGNORECASE)
    )
    
    if not has_financial_data:
        missing_elements.append("Financial data section")
        warnings.append("No financial data found in context")
        recommendations.append("Consider ingesting data for the requested company")
    
    # Check 2: Extract expected metrics from query
    if expected_metrics is None:
        expected_metrics = _extract_expected_metrics(user_query)
    
    # Check 3: Verify expected metrics are in context
    for metric in expected_metrics:
        metric_patterns = {
            "revenue": r'revenue|net sales|total revenue',
            "net_income": r'net income|profit|earnings',
            "ebitda": r'ebitda|adjusted ebitda',
            "margin": r'margin|gross margin|operating margin|net margin',
            "pe_ratio": r'p/e|pe ratio|price.*earnings',
            "growth": r'growth|cagr|year.*over.*year',
        }
        
        if metric in metric_patterns:
            pattern = metric_patterns[metric]
            if not re.search(pattern, context, re.IGNORECASE):
                missing_elements.append(f"{metric} data")
                warnings.append(f"Expected {metric} data not found in context")
    
    # Check 4: Data freshness indicators
    has_dates = bool(re.search(r'\d{4}|\d{4}-\d{2}|FY\d{4}|Q\d\s+\d{4}', context))
    if not has_dates:
        warnings.append("No date indicators found - data may be outdated")
        recommendations.append("Verify data freshness")
    
    # Check 5: Source citations
    source_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)|https?://', context))
    if source_count < 3:
        warnings.append(f"Only {source_count} sources found - may need more citations")
        recommendations.append("Include more source links in response")
    
    # Check 6: Ticker/company identification
    has_ticker = bool(re.search(r'\b[A-Z]{1,5}\b|ticker|symbol', context, re.IGNORECASE))
    if not has_ticker:
        warnings.append("No ticker symbol found in context")
    
    # Calculate confidence
    total_checks = 6
    passed_checks = total_checks - len(missing_elements) - len([w for w in warnings if "critical" in w.lower()])
    confidence = passed_checks / total_checks if total_checks > 0 else 0.0
    
    is_complete = len(missing_elements) == 0 and confidence >= 0.7
    
    return ContextCompletenessCheck(
        is_complete=is_complete,
        missing_elements=missing_elements,
        confidence=confidence,
        recommendations=recommendations,
        warnings=warnings
    )


def _extract_expected_metrics(query: str) -> List[str]:
    """Extract expected metrics from user query."""
    query_lower = query.lower()
    expected = []
    
    metric_keywords = {
        "revenue": ["revenue", "sales", "top line"],
        "net_income": ["net income", "profit", "earnings", "bottom line"],
        "ebitda": ["ebitda", "adjusted ebitda"],
        "margin": ["margin", "profitability"],
        "pe_ratio": ["p/e", "pe ratio", "price earnings", "valuation"],
        "growth": ["growth", "cagr", "increase", "decrease"],
        "cash_flow": ["cash flow", "fcf", "free cash flow"],
        "debt": ["debt", "leverage", "liabilities"],
    }
    
    for metric, keywords in metric_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            expected.append(metric)
    
    return expected


def suggest_context_improvements(
    check: ContextCompletenessCheck,
    user_query: str
) -> str:
    """
    Generate suggestions for improving context completeness.
    
    Returns:
        Formatted string with suggestions
    """
    if check.is_complete:
        return ""
    
    suggestions = []
    suggestions.append("**Context Completeness Issues Detected:**\n")
    
    if check.missing_elements:
        suggestions.append(f"**Missing Elements:** {', '.join(check.missing_elements)}")
    
    if check.warnings:
        suggestions.append(f"**Warnings:** {len(check.warnings)} issue(s) found")
        for warning in check.warnings[:3]:  # Limit to top 3
            suggestions.append(f"  - {warning}")
    
    if check.recommendations:
        suggestions.append(f"**Recommendations:**")
        for rec in check.recommendations:
            suggestions.append(f"  - {rec}")
    
    return "\n".join(suggestions)

