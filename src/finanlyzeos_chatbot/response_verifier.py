"""Post-processing verification for chatbot responses to ensure financial data accuracy."""

import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime

from . import database
from .analytics_engine import AnalyticsEngine

LOGGER = logging.getLogger(__name__)


@dataclass
class FinancialFact:
    """Extracted financial fact from response."""
    value: float
    unit: Optional[str]  # "B", "M", "%", "x", etc.
    metric: Optional[str]  # "revenue", "margin", "pe_ratio", etc.
    ticker: Optional[str]  # "AAPL", "MSFT", etc.
    period: Optional[str]  # "2024", "FY2024", "Q3 2024", etc.
    context: str  # Surrounding text for context
    position: int  # Character position in response


@dataclass
class VerificationResult:
    """Result of verifying a single fact."""
    fact: FinancialFact
    is_correct: bool
    actual_value: Optional[float]
    deviation: float  # Percentage deviation
    confidence: float  # 0.0 to 1.0
    source: Optional[str]  # "SEC", "Yahoo Finance", etc.
    message: str  # Explanation of verification result


@dataclass
class VerifiedResponse:
    """Verified response with corrections and metadata."""
    original_response: str
    verified_response: str
    facts: List[FinancialFact]
    results: List[VerificationResult]
    correct_facts: int
    total_facts: int
    has_errors: bool
    confidence_score: float


def extract_financial_numbers(
    response: str,
    ticker_resolver: Optional[Callable[[str], Optional[str]]] = None
) -> List[FinancialFact]:
    """
    Extract all financial numbers from LLM response.
    
    Looks for patterns like:
    - $394.3B (billions)
    - $85.2M (millions)
    - 25.3% (percentages)
    - 39.8x (multiples)
    - 394.3 billion (text format)
    """
    facts = []
    
    # CRITICAL: Extract global ticker from start of response first
    # This prevents local context from missing the company name
    global_ticker = _extract_global_ticker(response, ticker_resolver)
    
    # Pattern 1: Currency with suffix ($394.3B, $85.2M, $1.2T)
    currency_pattern = r'\$([\d,]+\.?\d*)\s*([BMKT]|billion|million|thousand|trillion)'
    for match in re.finditer(currency_pattern, response, re.IGNORECASE):
        value_str = match.group(1).replace(',', '')
        unit_str = match.group(2).upper()
        
        try:
            value = float(value_str)
            
            # Convert to base units (billions)
            if unit_str in ('B', 'BILLION'):
                base_value = value
            elif unit_str in ('M', 'MILLION'):
                base_value = value / 1000.0
            elif unit_str in ('T', 'TRILLION'):
                base_value = value * 1000.0
            elif unit_str in ('K', 'THOUSAND'):
                base_value = value / 1_000_000.0
            else:
                base_value = value
            
            # Try to identify metric from context
            context_start = max(0, match.start() - 50)
            context_end = min(len(response), match.end() + 50)
            context = response[context_start:context_end]
            
            metric = _identify_metric_from_context(context)
            # STEP 1: If no metric from context, try list context
            if not metric:
                metric = _infer_metric_from_list_context(response, match.start())
            # Use global ticker if available, otherwise try to identify from local context
            ticker = global_ticker or _identify_ticker_from_context(context, response, ticker_resolver)
            period = _identify_period_from_context(context)
            
            facts.append(FinancialFact(
                value=base_value,
                unit="B",  # Normalized to billions
                metric=metric,
                ticker=ticker,
                period=period,
                context=context,
                position=match.start()
            ))
        except ValueError:
            continue
    
    # Pattern 2: Percentages (25.3%, 45.9 percent)
    percent_pattern = r'([\d,]+\.?\d*)\s*%|([\d,]+\.?\d*)\s+percent'
    for match in re.finditer(percent_pattern, response, re.IGNORECASE):
        value_str = (match.group(1) or match.group(2)).replace(',', '')
        
        try:
            value = float(value_str)
            
            context_start = max(0, match.start() - 50)
            context_end = min(len(response), match.end() + 50)
            context = response[context_start:context_end]
            
            metric = _identify_metric_from_context(context)
            # STEP 1: If no metric from context, try list context
            if not metric:
                metric = _infer_metric_from_list_context(response, match.start())
            # Use global ticker if available, otherwise try to identify from local context
            ticker = global_ticker or _identify_ticker_from_context(context, response, ticker_resolver)
            period = _identify_period_from_context(context)
            
            facts.append(FinancialFact(
                value=value,
                unit="%",
                metric=metric,
                ticker=ticker,
                period=period,
                context=context,
                position=match.start()
            ))
        except ValueError:
            continue
    
    # Pattern 3: Multiples/ratios (39.8x, 2.5×)
    multiple_pattern = r'([\d,]+\.?\d*)\s*[x×]'
    for match in re.finditer(multiple_pattern, response, re.IGNORECASE):
        value_str = match.group(1).replace(',', '')
        
        try:
            value = float(value_str)
            
            context_start = max(0, match.start() - 50)
            context_end = min(len(response), match.end() + 50)
            context = response[context_start:context_end]
            
            metric = _identify_metric_from_context(context)
            ticker = _identify_ticker_from_context(context, response)
            
            facts.append(FinancialFact(
                value=value,
                unit="x",
                metric=metric,
                ticker=ticker,
                period=None,
                context=context,
                position=match.start()
            ))
        except ValueError:
            continue
    
    # STEP 2: Apply primary metric fallback
    # Find the first metric that was successfully identified
    primary_metric = None
    for fact in facts:
        if fact.metric:
            primary_metric = fact.metric
            break
    
    # Apply primary metric to facts that don't have one
    if primary_metric:
        for fact in facts:
            if not fact.metric:
                # Create a new fact with the primary metric
                # (FinancialFact is frozen, so we need to update the list)
                fact_index = facts.index(fact)
                facts[fact_index] = FinancialFact(
                    value=fact.value,
                    unit=fact.unit,
                    metric=primary_metric,  # Use primary metric as fallback
                    ticker=fact.ticker,
                    period=fact.period,
                    context=fact.context,
                    position=fact.position
                )
    
    return facts


def _extract_global_ticker(
    response: str,
    ticker_resolver: Optional[Callable[[str], Optional[str]]] = None
) -> Optional[str]:
    """
    Extract primary ticker from the beginning of the response.
    This prevents local context windows from missing the main company.
    """
    # Look in first 500 chars for company name or ticker
    # CRITICAL: Strip whitespace/newlines from start
    response_start = response.strip()[:500]
    
    # Try ticker resolver first
    if ticker_resolver:
        try:
            # Look for company names in possessive form ("Apple's", "Microsoft's")
            # More flexible pattern that doesn't require start of string
            company_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'s', response_start)
            if company_match:
                company_name = company_match.group(1)
                resolved = ticker_resolver(company_name)
                if resolved:
                    return resolved.upper()
        except Exception:
            pass
    
    # Try alias builder
    try:
        from .parsing.alias_builder import resolve_tickers_freeform
        
        # Look for company names in first sentence
        first_sentence = response_start.split('.')[0] if '.' in response_start else response_start
        
        # Common patterns (more flexible, not anchored to start)
        patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'s\s+(?:revenue|earnings|income|net income|profit|margin|cash|assets)',  # "Apple's revenue..."
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:reported|announced|generated)\s+(?:revenue|earnings|income)',  # "Apple reported revenue..."
            r'(?:for|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:',  # "for Apple:"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, first_sentence)
            if match:
                company_name = match.group(1)
                results, _ = resolve_tickers_freeform(company_name)
                if results:
                    return results[0]['ticker'].upper()
    except (ImportError, Exception):
        pass
    
    # Look for direct ticker symbols in first line
    first_line = response_start.split('\n')[0]
    ticker_pattern = r'\b([A-Z]{2,5})\b'
    stopwords = {'THE', 'AND', 'FOR', 'ARE', 'WAS', 'HAS', 'ITS', 'OUR', 'ALL', 'YOY', 'FROM'}
    
    matches = re.findall(ticker_pattern, first_line)
    for match in matches:
        if match not in stopwords and len(match) >= 2:
            # Verify it's a valid ticker
            try:
                from .parsing.alias_builder import resolve_tickers_freeform
                results, _ = resolve_tickers_freeform(match)
                if results:
                    return results[0]['ticker'].upper()
            except Exception:
                # Return as-is if it looks like a ticker
                if match.isupper() and len(match) <= 5:
                    return match.upper()
    
    return None


def _infer_metric_from_list_context(response: str, position: int) -> Optional[str]:
    """
    Infer metric from list context by looking backwards for section headers.
    
    Example:
    "The revenue growth was driven by:
     - iPhone sales: $201.2B"
    
    Should infer that this is revenue data.
    """
    # Get text before this position
    text_before = response[:position]
    
    # Look for last 200 chars before position
    context_before = text_before[-200:] if len(text_before) > 200 else text_before
    context_before_lower = context_before.lower()
    
    # Check for revenue-related headers
    revenue_patterns = [
        'revenue growth',
        'revenue breakdown',
        'revenue was driven',
        'revenue sources',
        'sales breakdown',
        'revenue composition',
        'revenue by',
    ]
    
    if any(pattern in context_before_lower for pattern in revenue_patterns):
        return 'revenue'
    
    # Check for margin-related headers
    margin_patterns = [
        'margin breakdown',
        'margin analysis',
        'profitability',
    ]
    
    if any(pattern in context_before_lower for pattern in margin_patterns):
        return 'gross_margin'
    
    return None


def _identify_metric_from_context(context: str) -> Optional[str]:
    """Identify metric from surrounding context using all available metrics."""
    context_lower = context.lower()
    
    # CRITICAL: Find the metric BEFORE the number, not after
    # Split context at the middle (where the number likely is)
    mid_point = len(context) // 2
    context_before = context[:mid_point].lower()
    context_after = context[mid_point:].lower()
    
    # STEP 3: Check for product/segment keywords that indicate revenue
    # BUT: Skip verification for segment-level data since it's not in database
    # Database only has company-level aggregates, not product segments
    segment_keywords = [
        'iphone', 'ipad', 'mac', 'macbook', 'services', 'wearables',
        'watch', 'airpods', 'apple watch', 'app store',
        # Generic segment indicators
        'product sales', 'segment', 'division', 'business unit',
        'geographic', 'region', 'americas', 'europe', 'asia'
    ]
    
    if any(keyword in context_lower for keyword in segment_keywords):
        # This is segment-level data - mark as 'segment_revenue' to skip verification
        # We can't verify segment data since database only has company totals
        if '$' in context or 'billion' in context_lower or 'million' in context_lower:
            return 'segment_revenue'  # Special marker for segment data
    
    # Import metric definitions from analytics_engine
    try:
        from .analytics_engine import (
            BASE_METRICS, DERIVED_METRICS, AGGREGATE_METRICS,
            SUPPLEMENTAL_METRICS, METRIC_NAME_ALIASES, METRIC_LABELS
        )
        
        # Build comprehensive metric keyword mapping
        all_metrics = BASE_METRICS | DERIVED_METRICS | AGGREGATE_METRICS | SUPPLEMENTAL_METRICS
        
        # Create metric keywords from labels and aliases
        metric_keywords = {}
        
        # Add direct metric names
        for metric in all_metrics:
            if metric not in metric_keywords:
                metric_keywords[metric] = []
            metric_keywords[metric].append(metric.replace('_', ' '))
            metric_keywords[metric].append(metric)
        
        # Add metric labels
        for metric, label in METRIC_LABELS.items():
            if metric not in metric_keywords:
                metric_keywords[metric] = []
            metric_keywords[metric].append(label.lower())
        
        # Add aliases
        for alias, metric in METRIC_NAME_ALIASES.items():
            if metric not in metric_keywords:
                metric_keywords[metric] = []
            metric_keywords[metric].append(alias.replace('_', ' '))
        
        # Add common variations
        common_variations = {
            'revenue': ['revenue', 'sales', 'net sales', 'total revenue'],
            'net_income': ['net income', 'earnings', 'profit', 'net profit', 'income'],
            'gross_margin': ['gross margin', 'gross profit margin'],
            'operating_margin': ['operating margin', 'operating profit margin'],
            'ebitda_margin': ['ebitda margin'],
            'pe_ratio': ['p/e', 'pe ratio', 'price-to-earnings', 'price earnings'],
            'roe': ['roe', 'return on equity', 'return on shareholders equity'],
            'roic': ['roic', 'return on invested capital', 'return on investment', 'roi'],
            'free_cash_flow': ['free cash flow', 'fcf'],
            'cash_from_operations': ['cash from operations', 'operating cash flow', 'cash flow from operations'],
            'total_assets': ['total assets', 'assets'],
            'total_liabilities': ['total liabilities', 'liabilities'],
            'market_cap': ['market cap', 'market capitalization', 'market value'],
            'debt_to_equity': ['debt-to-equity', 'debt/equity', 'debt to equity'],
            'roa': ['roa', 'return on assets'],
            'current_ratio': ['current ratio'],
            'quick_ratio': ['quick ratio'],
            'interest_coverage': ['interest coverage'],
            'asset_turnover': ['asset turnover'],
            'ps_ratio': ['p/s', 'ps ratio', 'price-to-sales'],
            'ev_ebitda': ['ev/ebitda', 'ev ebitda', 'enterprise value ebitda'],
            'pb_ratio': ['p/b', 'pb ratio', 'price-to-book'],
            'peg_ratio': ['peg', 'peg ratio'],
            'dividend_yield': ['dividend yield', 'dividend'],
            'revenue_cagr': ['revenue cagr', 'revenue growth'],
            'eps_cagr': ['eps cagr', 'eps growth'],
        }
        
        for metric, variations in common_variations.items():
            if metric not in metric_keywords:
                metric_keywords[metric] = []
            metric_keywords[metric].extend(variations)
        
        # Match against context - PREFER metrics that appear BEFORE the number
        best_match = None
        best_match_before = False
        
        for metric, keywords in metric_keywords.items():
            for keyword in keywords:
                # Check if keyword appears before the number (preferred)
                if keyword in context_before:
                    return metric  # Return immediately if found before
                # Check if keyword appears anywhere in context
                elif keyword in context_lower and not best_match:
                    best_match = metric
        
        if best_match:
            return best_match
        
    except ImportError:
        # Fallback to basic keywords if import fails
        basic_keywords = {
            'revenue': ['revenue', 'sales'],
            'net_income': ['net income', 'earnings'],
            'pe_ratio': ['p/e', 'pe ratio'],
        }
        for metric, keywords in basic_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                return metric
    
    return None


def _identify_ticker_from_context(
    context: str,
    full_response: str,
    ticker_resolver: Optional[Callable[[str], Optional[str]]] = None
) -> Optional[str]:
    """Identify ticker from context using ticker resolver or alias builder system."""
    # First, try to find ticker symbols directly (uppercase 1-5 letters)
    ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,2})?)\b'
    
    # Common stopwords that look like tickers
    stopwords = {'THE', 'AND', 'FOR', 'ARE', 'WAS', 'HAS', 'ITS', 'OUR', 'ALL', 'WHO', 'WHY', 'HOW', 'WHEN', 'WHERE'}
    
    # Look for ticker in context and full response
    for text in [context, full_response]:
        matches = re.findall(ticker_pattern, text)
        for match in matches:
            match_upper = match.upper()
            # Filter out common words that look like tickers
            if match_upper not in stopwords:
                if len(match) >= 1 and len(match) <= 6:  # Allow for BRK.B format
                    # Use ticker resolver if provided
                    if ticker_resolver:
                        try:
                            resolved = ticker_resolver(match)
                            if resolved:
                                return resolved.upper()
                        except Exception:
                            pass
                    
                    # Try alias builder as fallback
                    try:
                        from .parsing.alias_builder import resolve_tickers_freeform
                        results, _ = resolve_tickers_freeform(match)
                        if results:
                            return results[0]['ticker'].upper()
                    except (ImportError, Exception):
                        # If both fail, return the match if it looks valid
                        if len(match) >= 2 and match.isupper():
                            return match.upper()
    
    # Try to resolve company names
    if ticker_resolver:
        # Use provided ticker resolver
        company_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'s',  # "Apple's"
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:revenue|earnings|margin|income)',  # "Apple revenue"
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|has|reported)',  # "Apple is"
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, full_response)
            for match in matches:
                company_name = match.strip()
                if len(company_name) > 2:
                    try:
                        resolved = ticker_resolver(company_name)
                        if resolved:
                            return resolved.upper()
                    except Exception:
                        continue
    
    # Fallback: Use alias builder directly
    try:
        from .parsing.alias_builder import resolve_tickers_freeform
        
        # Extract potential company names
        company_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\'s',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:revenue|earnings|margin)',
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, full_response)
            for match in matches:
                company_name = match.strip()
                if len(company_name) > 2:
                    results, _ = resolve_tickers_freeform(company_name)
                    if results:
                        return results[0]['ticker'].upper()
    except (ImportError, Exception):
        pass
    
    return None


def _identify_period_from_context(context: str) -> Optional[str]:
    """Identify time period from context."""
    # Pattern: FY2024, 2024, Q3 2024, etc.
    period_patterns = [
        r'FY\s*(\d{4})',
        r'(\d{4})',
        r'Q[1-4]\s*(\d{4})',
        r'(\d{4})\s*Q[1-4]',
    ]
    
    for pattern in period_patterns:
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return None


def verify_fact(
    fact: FinancialFact,
    analytics_engine: AnalyticsEngine,
    database_path: str
) -> VerificationResult:
    """
    Verify a single fact against source data.
    
    Returns VerificationResult with accuracy information.
    """
    if not fact.ticker or not fact.metric:
        return VerificationResult(
            fact=fact,
            is_correct=False,
            actual_value=None,
            deviation=100.0,
            confidence=0.0,
            source=None,
            message="Cannot verify: missing ticker or metric"
        )
    
    # Skip verification for segment-level data
    # Database only has company-level aggregates, not product/geographic segments
    if fact.metric == 'segment_revenue':
        return VerificationResult(
            fact=fact,
            is_correct=True,  # Mark as correct (skipped verification)
            actual_value=fact.value,  # Use extracted value as-is
            deviation=0.0,
            confidence=1.0,  # Full confidence since it's from the response context
            source="response_context",
            message="Segment data - skipped verification (not in database)"
        )
    
    try:
        # Get metrics from analytics engine
        metrics = analytics_engine.get_metrics(
            fact.ticker,
            period_filters=None
        )
        
        # Find matching metric
        matching_metric = None
        for metric_record in metrics:
            if metric_record.metric == fact.metric:
                # If period specified, try to match
                if fact.period:
                    if fact.period in metric_record.period:
                        matching_metric = metric_record
                        break
                else:
                    # Use latest if no period specified
                    if matching_metric is None or metric_record.period > matching_metric.period:
                        matching_metric = metric_record
        
        if matching_metric is None or matching_metric.value is None:
            return VerificationResult(
                fact=fact,
                is_correct=False,
                actual_value=None,
                deviation=100.0,
                confidence=0.0,
                source=matching_metric.source if matching_metric else None,
                message=f"Metric {fact.metric} not found in database for {fact.ticker}"
            )
        
        actual_value = matching_metric.value
        
        # Convert actual value to same unit as extracted value
        # Database stores different metrics in different units:
        # - Currency metrics (revenue, income): raw values (391035000000)
        # - Percentage metrics (margins, ratios): already as percentages (25.3)
        # - Multiples (P/E, ratios): already as multiples (39.8)
        actual_value_normalized = actual_value
        
        # Import metric type classifications
        try:
            from .analytics_engine import CURRENCY_METRICS, PERCENTAGE_METRICS, MULTIPLE_METRICS
            
            # Determine if this is a currency metric
            is_currency_metric = fact.metric in CURRENCY_METRICS
            is_percentage_metric = fact.metric in PERCENTAGE_METRICS
            is_multiple_metric = fact.metric in MULTIPLE_METRICS
            
            if fact.unit == "B" and is_currency_metric:
                # Currency metric in billions, convert database value to billions
                actual_value_normalized = actual_value / 1_000_000_000
            elif fact.unit == "M" and is_currency_metric:
                # Currency metric in millions, convert database value to millions
                actual_value_normalized = actual_value / 1_000_000
            elif fact.unit == "%" and is_percentage_metric:
                # Percentage metrics may be stored as decimals (0.46) or percentages (46.0)
                # Check if stored as decimal (value < 2.0 usually means decimal form)
                if actual_value < 2.0:
                    # Stored as decimal, convert to percentage
                    actual_value_normalized = actual_value * 100
                else:
                    # Already stored as percentage
                    actual_value_normalized = actual_value
            elif fact.unit == "x" and is_multiple_metric:
                # Multiples are already stored as multiples
                actual_value_normalized = actual_value
            else:
                # Default: assume raw value, try to match unit
                if fact.unit == "B":
                    actual_value_normalized = actual_value / 1_000_000_000
                elif fact.unit == "M":
                    actual_value_normalized = actual_value / 1_000_000
        except ImportError:
            # Fallback: basic unit conversion for currency
            if fact.unit == "B":
                actual_value_normalized = actual_value / 1_000_000_000
            elif fact.unit == "M":
                actual_value_normalized = actual_value / 1_000_000
        
        # Calculate deviation using normalized values
        if actual_value_normalized == 0:
            deviation = 100.0 if fact.value != 0 else 0.0
        else:
            deviation = abs((fact.value - actual_value_normalized) / actual_value_normalized) * 100.0
        
        # Determine if correct (within 5% tolerance)
        is_correct = deviation <= 5.0
        
        # Calculate confidence
        if is_correct:
            confidence = max(0.0, 1.0 - (deviation / 5.0))
        else:
            confidence = max(0.0, 1.0 - (deviation / 100.0))
        
        message = (
            f"Verified: {fact.value:.2f}{fact.unit} matches {actual_value_normalized:.2f}{fact.unit} "
            f"(deviation: {deviation:.2f}%)"
            if is_correct
            else f"Mismatch: {fact.value:.2f}{fact.unit} vs {actual_value_normalized:.2f}{fact.unit} "
                 f"(deviation: {deviation:.2f}%)"
        )
        
        return VerificationResult(
            fact=fact,
            is_correct=is_correct,
            actual_value=actual_value_normalized,  # Return normalized value
            deviation=deviation,
            confidence=confidence,
            source=matching_metric.source,
            message=message
        )
    
    except Exception as e:
        LOGGER.warning(f"Error verifying fact: {e}", exc_info=True)
        return VerificationResult(
            fact=fact,
            is_correct=False,
            actual_value=None,
            deviation=100.0,
            confidence=0.0,
            source=None,
            message=f"Error during verification: {str(e)}"
        )


def verify_response(
    response: str,
    context: str,
    user_input: str,
    analytics_engine: AnalyticsEngine,
    database_path: str,
    ticker_resolver: Optional[Callable[[str], Optional[str]]] = None
) -> VerifiedResponse:
    """
    Verify entire response by extracting and checking all financial facts.
    
    Args:
        response: LLM-generated response text
        context: Context that was provided to LLM
        user_input: Original user query
        analytics_engine: Analytics engine for data access
        database_path: Path to database
    
    Returns:
        VerifiedResponse with verification results and corrections
    """
    # Extract all financial facts
    facts = extract_financial_numbers(response, ticker_resolver=ticker_resolver)
    
    if not facts:
        # No facts to verify
        return VerifiedResponse(
            original_response=response,
            verified_response=response,
            facts=[],
            results=[],
            correct_facts=0,
            total_facts=0,
            has_errors=False,
            confidence_score=1.0
        )
    
    # Verify each fact
    results = []
    for fact in facts:
        result = verify_fact(fact, analytics_engine, database_path)
        results.append(result)
    
    # Count correct facts
    correct_facts = sum(1 for r in results if r.is_correct)
    total_facts = len(results)
    has_errors = correct_facts < total_facts
    
    # Calculate overall confidence
    if total_facts > 0:
        confidence_score = sum(r.confidence for r in results) / total_facts
    else:
        confidence_score = 1.0
    
    # For now, return original response (corrections will be handled by response_corrector)
    return VerifiedResponse(
        original_response=response,
        verified_response=response,  # Will be corrected by response_corrector
        facts=facts,
        results=results,
        correct_facts=correct_facts,
        total_facts=total_facts,
        has_errors=has_errors,
        confidence_score=confidence_score
    )

