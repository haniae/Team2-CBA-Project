"""Combined portfolio management module for IVPA."""

from __future__ import annotations

import csv
import json
import logging
import re
import sqlite3
import sqlite3 as _sqlite3
import uuid
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cvxpy as cp
import numpy as np
import pandas as pd
import pdfplumber
import PyPDF2
import scipy.optimize as sco
from scipy import stats
import yfinance as yf

from . import database
from .sector_analytics import SECTOR_MAP

LOGGER = logging.getLogger(__name__)

# ============================================================================
# Performance Optimization: Caching and Connection Pooling
# ============================================================================

# Cache for frequently accessed data
_PRICE_CACHE: Dict[str, Tuple[float, float]] = {}  # ticker -> (price, timestamp)
_CACHE_DURATION = 300  # 5 minutes in seconds

def _get_cached_price(ticker: str) -> Optional[float]:
    """Get cached price if still valid."""
    if ticker in _PRICE_CACHE:
        price, timestamp = _PRICE_CACHE[ticker]
        if time.time() - timestamp < _CACHE_DURATION:
            return price
        else:
            del _PRICE_CACHE[ticker]
    return None

def _cache_price(ticker: str, price: float) -> None:
    """Cache price with timestamp."""
    _PRICE_CACHE[ticker] = (price, time.time())

# Cache will be populated by load_sp500_benchmark_weights
_SP500_WEIGHTS_CACHE: Optional[Dict[str, float]] = None

# Database connection pooling
_DB_CONNECTIONS: Dict[str, sqlite3.Connection] = {}

@contextmanager
def _get_db_connection(database_path: Path):
    """Get or create a database connection with pooling."""
    db_path_str = str(database_path.absolute())
    
    if db_path_str not in _DB_CONNECTIONS:
        conn = sqlite3.connect(database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _DB_CONNECTIONS[db_path_str] = conn
    else:
        conn = _DB_CONNECTIONS[db_path_str]
    
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    # Don't close connection, keep it for reuse

def monitor_performance(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            if duration > 0.1:  # Only log slow operations
                LOGGER.debug(f"{func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            LOGGER.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper


# ============================================================================
# Portfolio Error Handling
# ============================================================================

class PortfolioError(Exception):
    """Base exception for portfolio operations."""
    
    def __init__(self, message: str, error_code: str = None, suggestions: List[str] = None):
        self.message = message
        self.error_code = error_code or "portfolio_error"
        self.suggestions = suggestions or []
        super().__init__(self.message)


class InvalidHoldingsError(PortfolioError):
    """Raised when holdings are invalid."""
    
    def __init__(self, message: str, errors: List[str] = None, warnings: List[str] = None):
        suggestions = [
            "Check that your file has required columns: ticker, and either weight or shares+price",
            "Ensure weights sum to 100% (±5% tolerance for rounding)",
            "Verify ticker symbols are valid (e.g., AAPL, MSFT, GOOGL)",
            "Check for empty rows or malformed data"
        ]
        super().__init__(
            message,
            error_code="invalid_holdings",
            suggestions=suggestions
        )
        self.errors = errors or []
        self.warnings = warnings or []


class OptimizationFailedError(PortfolioError):
    """Raised when optimization cannot converge."""
    
    def __init__(self, message: str, status: str = None):
        suggestions = [
            "Try relaxing policy constraints",
            "Increase turnover limit",
            "Check that fundamentals data is available for all holdings",
            "Verify that expected returns and covariance are valid"
        ]
        super().__init__(
            message,
            error_code="optimization_failed",
            suggestions=suggestions
        )
        self.status = status


class PolicyConstraintError(PortfolioError):
    """Raised when policy constraints are violated."""
    
    def __init__(self, message: str, violations: List[str] = None):
        suggestions = [
            "Review portfolio investment policy statement",
            "Adjust holdings to meet constraints",
            "Contact portfolio administrator for constraint modifications"
        ]
        super().__init__(
            message,
            error_code="policy_violation",
            suggestions=suggestions
        )
        self.violations = violations or []


class PortfolioNotFoundError(PortfolioError):
    """Raised when portfolio is not found."""
    
    def __init__(self, portfolio_id: str):
        message = f"Portfolio '{portfolio_id}' not found"
        suggestions = [
            "Check portfolio ID spelling",
            "Use 'list portfolios' to see available portfolios",
            "Verify portfolio was uploaded successfully"
        ]
        super().__init__(message, error_code="portfolio_not_found", suggestions=suggestions)
        self.portfolio_id = portfolio_id


# User-friendly error messages
ERROR_MESSAGES = {
    'invalid_holdings': {
        'title': 'Invalid Portfolio File',
        'message': 'Your portfolio file has some issues that need to be fixed.',
        'common_causes': [
            'Missing required columns (ticker, weight or shares+price)',
            'Weights don\'t sum to 100%',
            'Invalid ticker symbols',
            'Empty rows or malformed data'
        ],
        'solutions': [
            'Check the file format guide',
            'Verify all ticker symbols are valid (e.g., AAPL, MSFT, GOOGL)',
            'Ensure weights sum to approximately 100% (±5% tolerance)',
            'Remove empty rows and check for formatting issues'
        ]
    },
    'optimization_failed': {
        'title': 'Optimization Did Not Converge',
        'message': 'The portfolio optimization could not find an optimal solution.',
        'common_causes': [
            'Policy constraints are too restrictive',
            'Insufficient historical data for calculations',
            'Numerical instability in covariance matrix',
            'Solver could not find feasible solution'
        ],
        'solutions': [
            'Try relaxing policy constraints',
            'Increase turnover limit',
            'Add more historical data for holdings',
            'Check that fundamentals data is available for all holdings'
        ]
    },
    'policy_violation': {
        'title': 'Policy Constraint Violation',
        'message': 'One or more portfolio holdings violate investment policy constraints.',
        'common_causes': [
            'Position size exceeds maximum limit',
            'Sector exposure exceeds policy limit',
            'Concentration limits violated',
            'Restricted securities in portfolio'
        ],
        'solutions': [
            'Review portfolio investment policy statement',
            'Adjust holdings to meet constraints',
            'Contact portfolio administrator for constraint modifications',
            'Consider rebalancing to comply with policy'
        ]
    },
    'portfolio_not_found': {
        'title': 'Portfolio Not Found',
        'message': 'The requested portfolio could not be found.',
        'common_causes': [
            'Portfolio ID is incorrect',
            'Portfolio was deleted',
            'Typo in portfolio name or ID'
        ],
        'solutions': [
            'Check portfolio ID spelling',
            'Use "list portfolios" to see available portfolios',
            'Verify portfolio was uploaded successfully'
        ]
    }
}

def format_portfolio_error(error: PortfolioError, include_technical: bool = False) -> Dict[str, Any]:
    """Format portfolio error for API response with user-friendly messages."""
    error_info = ERROR_MESSAGES.get(error.error_code, {})
    
    response = {
        "success": False,
        "error_code": error.error_code,
        "title": error_info.get('title', 'An Error Occurred'),
        "message": error_info.get('message', error.message),
        "common_causes": error_info.get('common_causes', []),
        "solutions": error_info.get('solutions', error.suggestions),
    }
    
    # Add specific error details
    if isinstance(error, InvalidHoldingsError):
        response["validation_errors"] = error.errors
        response["validation_warnings"] = error.warnings
    elif isinstance(error, OptimizationFailedError):
        response["optimization_status"] = error.status
    elif isinstance(error, PolicyConstraintError):
        response["violations"] = error.violations
    elif isinstance(error, PortfolioNotFoundError):
        response["portfolio_id"] = error.portfolio_id
    
    # Include technical details only in debug mode
    if include_technical:
        response["technical_details"] = str(error)
    
    return response

@dataclass
class HoldingsValidationResult:
    """Result of holdings validation with errors and warnings."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    total_weight: float
    normalized_holdings: List[Dict[str, Any]]



@dataclass
class EnrichedHolding:
    """Enriched holding with fundamentals and sector classification."""

    ticker: str
    weight: Optional[float]
    shares: Optional[float]
    price: Optional[float]
    market_value: Optional[float]
    sector: Optional[str]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    revenue_growth: Optional[float]
    roe: Optional[float]
    roic: Optional[float]


@dataclass

@dataclass

class PortfolioStatistics:
    """Aggregate portfolio statistics."""

    total_market_value: float
    num_holdings: int
    weighted_avg_pe: Optional[float]
    weighted_avg_dividend_yield: Optional[float]
    sector_concentration: Dict[str, float]  # sector -> weight
    top_10_weight: float
    num_sectors: int



@dataclass
class ExposureAnalysis:
    """Multi-dimensional portfolio exposure analysis."""

    sector_exposure: Dict[str, float]  # sector -> weight
    factor_exposure: Dict[str, float]  # factor -> exposure
    issuer_exposure: Dict[str, float]  # ticker -> weight
    geographic_exposure: Dict[str, float]  # country -> weight
    concentration_metrics: Dict[str, float]  # HHI, top_n_concentration, etc.



@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    optimized_weights: Dict[str, float]
    proposed_trades: List[Dict[str, Any]]
    objective_value: Optional[float]
    iterations: int
    status: str
    policy_flags: List[str]
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]


@dataclass

@dataclass

class PolicyConstraint:
    """Portfolio policy constraint definition."""

    constraint_type: str  # allocation_cap, sector_limit, tracking_error, etc.
    dimension: Optional[str]  # ticker or sector name
    min_value: Optional[float]
    max_value: Optional[float]



# AttributionResult, ScenarioResult, and CommitteeBrief are defined later in their respective sections




# ======================================================================
# INGESTION
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class HoldingsValidationResult:
    """Result of holdings validation with errors and warnings."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    total_weight: float
    normalized_holdings: List[Dict[str, Any]]


def ingest_holdings_csv(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Parse CSV file with holdings data.

    Expected columns: ticker, shares (optional), weight (optional), price (optional),
    cost_basis (optional), currency (optional), account_id (optional), date (optional)

    Returns list of holdings dictionaries.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Holdings file not found: {file_path}")

    holdings = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = [h.lower().strip() for h in reader.fieldnames or []]

        # Normalize column names
        column_map = {}
        for header in headers:
            if header in ["ticker", "symbol", "ticker_symbol"]:
                column_map["ticker"] = header
            elif header in ["shares", "quantity", "qty"]:
                column_map["shares"] = header
            elif header in ["weight", "allocation", "percent", "percentage"]:
                column_map["weight"] = header
            elif header in ["price", "current_price", "market_price"]:
                column_map["price"] = header
            elif header in ["cost_basis", "cost", "basis"]:
                column_map["cost_basis"] = header
            elif header in ["currency", "curr"]:
                column_map["currency"] = header
            elif header in ["account_id", "account", "account_name"]:
                column_map["account_id"] = header
            elif header in ["date", "position_date", "as_of_date"]:
                column_map["date"] = header

        for row_num, row in enumerate(reader, start=2):
            try:
                holding: Dict[str, Any] = {}

                # Extract ticker (required)
                if "ticker" not in column_map:
                    raise ValueError("Missing required 'ticker' column")
                holding["ticker"] = str(row[column_map["ticker"]]).strip().upper()

                # Extract optional fields
                if "shares" in column_map:
                    holding["shares"] = _parse_float(row[column_map["shares"]])
                if "weight" in column_map:
                    holding["weight"] = _parse_float(row[column_map["weight"]])
                if "price" in column_map:
                    holding["price"] = _parse_float(row[column_map["price"]])
                if "cost_basis" in column_map:
                    holding["cost_basis"] = _parse_float(row[column_map["cost_basis"]])
                if "currency" in column_map:
                    holding["currency"] = str(row[column_map["currency"]]).strip()
                if "account_id" in column_map:
                    holding["account_id"] = str(row[column_map["account_id"]]).strip()
                if "date" in column_map:
                    holding["date"] = str(row[column_map["date"]]).strip()

                holdings.append(holding)

            except Exception as e:
                LOGGER.warning(f"Row {row_num}: Skipping invalid holding: {e}")
                continue

    LOGGER.info(f"Parsed {len(holdings)} holdings from CSV")
    return holdings


def ingest_holdings_excel(file_path: Union[str, Path], sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Parse Excel workbook with holdings data.

    Supports multiple sheets if needed. Reads holdings from specified sheet or first sheet.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Holdings file not found: {file_path}")

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")

    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()
    df.columns = df.columns.str.replace(" ", "_")

    holdings = []
    for _, row in df.iterrows():
        try:
            holding: Dict[str, Any] = {}

            # Required ticker
            if "ticker" not in df.columns and "symbol" not in df.columns:
                raise ValueError("Missing required 'ticker' column")
            holding["ticker"] = str(row.get("ticker") or row.get("symbol")).strip().upper()

            # Optional fields
            if "shares" in df.columns:
                holding["shares"] = _parse_float(row.get("shares"))
            if "weight" in df.columns or "allocation" in df.columns:
                holding["weight"] = _parse_float(row.get("weight") or row.get("allocation"))
            if "price" in df.columns:
                holding["price"] = _parse_float(row.get("price"))
            if "cost_basis" in df.columns:
                holding["cost_basis"] = _parse_float(row.get("cost_basis"))
            if "currency" in df.columns:
                holding["currency"] = str(row.get("currency")).strip()
            if "account_id" in df.columns:
                holding["account_id"] = str(row.get("account_id")).strip()
            if "date" in df.columns:
                holding["date"] = str(row.get("date"))

            holdings.append(holding)

        except Exception as e:
            LOGGER.warning(f"Skipping invalid holding: {e}")
            continue

    LOGGER.info(f"Parsed {len(holdings)} holdings from Excel")
    return holdings


def ingest_holdings_json(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Parse JSON file with holdings data."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Holdings file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support multiple JSON formats
    if isinstance(data, list):
        holdings = data
    elif isinstance(data, dict) and "holdings" in data:
        holdings = data["holdings"]
    elif isinstance(data, dict) and "positions" in data:
        holdings = data["positions"]
    else:
        raise ValueError("Invalid JSON structure. Expected list or dict with 'holdings' or 'positions' key")

    # Normalize holdings
    normalized = []
    for holding in holdings:
        normalized_holding: Dict[str, Any] = {}
        if "ticker" in holding:
            normalized_holding["ticker"] = str(holding["ticker"]).strip().upper()
        elif "symbol" in holding:
            normalized_holding["ticker"] = str(holding["symbol"]).strip().upper()
        else:
            LOGGER.warning(f"Skipping holding without ticker: {holding}")
            continue

        for key in ["shares", "weight", "price", "cost_basis"]:
            if key in holding:
                normalized_holding[key] = _parse_float(holding[key])
        for key in ["currency", "account_id", "date"]:
            if key in holding:
                normalized_holding[key] = str(holding[key]).strip()

        normalized.append(normalized_holding)

    LOGGER.info(f"Parsed {len(normalized)} holdings from JSON")
    return normalized


def _parse_float(value: Any) -> Optional[float]:
    """Safely parse float, handling None and string formats."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove commas, currency symbols, etc.
        cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def validate_holdings(
    holdings: List[Dict[str, Any]], portfolio_id: str, base_currency: str = "USD"
) -> HoldingsValidationResult:
    """
    Validate and clean portfolio holdings.

    Performs data cleaning:
    - Removes empty/invalid holdings
    - Normalizes ticker symbols (uppercase, strip)
    - Deduplicates holdings by ticker (aggregates values)
    - Normalizes weight format (detects percentage vs decimal)

    Checks:
    - Ticker validity (basic format check)
    - No negative shares or weights
    - Weight sum = 100% (if weights provided)
    - Required fields present
    """
    errors = []
    warnings = []
    raw_normalized = []
    total_weight = 0.0

    # Step 1: Parse and normalize individual holdings
    for idx, holding in enumerate(holdings):
        # Check ticker
        if "ticker" not in holding or not holding["ticker"]:
            errors.append(f"Holding {idx + 1}: Missing ticker symbol")
            continue

        ticker = str(holding["ticker"]).strip().upper()
        if not _is_valid_ticker_format(ticker):
            errors.append(f"Holding {idx + 1}: Invalid ticker format '{ticker}'")
            continue

        # Normalize weight: detect if percentage (0-100) or decimal (0-1)
        raw_weight = _parse_float(holding.get("weight"))
        weight = None
        if raw_weight is not None:
            # If weight > 1, assume percentage format; otherwise assume decimal
            if raw_weight > 1:
                weight = raw_weight  # Already in percentage
            else:
                weight = raw_weight * 100  # Convert decimal to percentage

        normalized: Dict[str, Any] = {
            "ticker": ticker,
            "portfolio_id": portfolio_id,
            "position_date": _parse_date(holding.get("date")) or datetime.now(timezone.utc),
            "shares": _parse_float(holding.get("shares")),
            "weight": weight,
            "cost_basis": _parse_float(holding.get("cost_basis")),
            "market_value": None,
            "currency": holding.get("currency", base_currency).upper(),
            "account_id": holding.get("account_id"),
        }

        # Validate numeric fields
        if normalized["shares"] is not None and normalized["shares"] < 0:
            errors.append(f"{ticker}: Negative shares")
        if normalized["weight"] is not None and normalized["weight"] < 0:
            errors.append(f"{ticker}: Negative weight")

        # Calculate market value if shares and price provided
        if normalized["shares"] and "price" in holding:
            price = _parse_float(holding["price"])
            if price:
                normalized["market_value"] = normalized["shares"] * price
        elif normalized["shares"] is None and normalized["weight"] is None:
            warnings.append(f"{ticker}: No shares or weight provided")

        raw_normalized.append(normalized)

    # Step 2: Deduplicate holdings by ticker (aggregate values)
    deduplicated: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0
    
    for holding in raw_normalized:
        ticker = holding["ticker"]
        
        if ticker in deduplicated:
            duplicate_count += 1
            existing = deduplicated[ticker]
            
            # Aggregate shares (sum)
            if holding["shares"] is not None:
                if existing["shares"] is not None:
                    existing["shares"] += holding["shares"]
                else:
                    existing["shares"] = holding["shares"]
            
            # Aggregate weights (sum)
            if holding["weight"] is not None:
                if existing["weight"] is not None:
                    existing["weight"] += holding["weight"]
                else:
                    existing["weight"] = holding["weight"]
            
            # Aggregate market_value (sum)
            if holding["market_value"] is not None:
                if existing["market_value"] is not None:
                    existing["market_value"] += holding["market_value"]
                else:
                    existing["market_value"] = holding["market_value"]
            
            # Aggregate cost_basis (sum)
            if holding["cost_basis"] is not None:
                if existing["cost_basis"] is not None:
                    existing["cost_basis"] += holding["cost_basis"]
                else:
                    existing["cost_basis"] = holding["cost_basis"]
            
            # Use most recent position_date
            if holding["position_date"] > existing["position_date"]:
                existing["position_date"] = holding["position_date"]
            
            # Merge account_id if different
            if holding["account_id"] and existing["account_id"] and holding["account_id"] != existing["account_id"]:
                warnings.append(f"{ticker}: Multiple account IDs found, using first: {existing['account_id']}")
        else:
            # First occurrence of this ticker
            deduplicated[ticker] = holding.copy()

    if duplicate_count > 0:
        warnings.append(f"Deduplicated {duplicate_count} duplicate holdings by aggregating values")

    # Step 3: Convert back to list and calculate total weight
    normalized_holdings = list(deduplicated.values())
    for holding in normalized_holdings:
        if holding["weight"] is not None:
            total_weight += holding["weight"]

    # Step 4: Validate weight sum
    if normalized_holdings and any(h["weight"] is not None for h in normalized_holdings):
        if abs(total_weight - 100.0) > 0.01:  # Allow small rounding
            errors.append(f"Weight sum is {total_weight:.2f}%, expected 100%")
        elif abs(total_weight - 100.0) > 0.0001:
            warnings.append(f"Weight sum is {total_weight:.2f}%, slight rounding deviation")

    is_valid = len(errors) == 0

    LOGGER.info(f"Validation result: {len(errors)} errors, {len(warnings)} warnings, {len(normalized_holdings)} holdings after deduplication")
    return HoldingsValidationResult(
        is_valid=is_valid, errors=errors, warnings=warnings, total_weight=total_weight, normalized_holdings=normalized_holdings
    )


def _is_valid_ticker_format(ticker: str) -> bool:
    """Basic ticker format validation (1-5 uppercase letters/digits)."""
    return bool(re.match(r"^[A-Z0-9]{1,5}$", ticker))


def _parse_date(value: Any) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                # Try common formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            except Exception:
                pass
    return None


def normalize_currencies(
    holdings: List[Dict[str, Any]], base_currency: str = "USD", fx_rates: Optional[Dict[str, float]] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Normalize multi-currency holdings to base currency.

    Returns (normalized_holdings, warnings).
    """
    if fx_rates is None:
        fx_rates = {}

    warnings = []
    normalized = []

    for holding in holdings:
        curr = holding.get("currency", base_currency)

        if curr == base_currency:
            normalized.append(holding)
            continue

        # Get FX rate
        if curr not in fx_rates:
            # Try to fetch from yfinance (basic implementation)
            try:
                pair = f"{curr}{base_currency}=X"
                ticker = yf.Ticker(pair)
                rate = ticker.history(period="1d")["Close"].iloc[-1]
                fx_rates[curr] = rate
                LOGGER.info(f"Fetched FX rate {curr}/{base_currency}: {rate:.4f}")
            except Exception as e:
                warnings.append(f"Could not fetch FX rate for {curr}/{base_currency}: {e}")
                # Use 1.0 as fallback
                fx_rates[curr] = 1.0

        rate = fx_rates[curr]

        # Convert market_value and cost_basis
        normalized_holding = holding.copy()
        if normalized_holding.get("market_value"):
            normalized_holding["market_value"] = normalized_holding["market_value"] * rate
        if normalized_holding.get("cost_basis"):
            normalized_holding["cost_basis"] = normalized_holding["cost_basis"] * rate
        normalized_holding["currency"] = base_currency

        normalized.append(normalized_holding)

    return normalized, warnings


def parse_ips_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse structured JSON policy file.

    Expected format:
    {
        "constraints": [
            {"type": "allocation_cap", "ticker": "*", "max_weight": 0.05},
            {"type": "sector_limit", "sector": "Technology", "min_weight": 0.15, "max_weight": 0.35},
            {"type": "tracking_error", "max_value": 0.025}
        ]
    }
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Policy file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "constraints" not in data:
        raise ValueError("Missing 'constraints' key in JSON")

    return data


def parse_ips_pdf(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract policy constraints from PDF document.

    Uses keyword matching to find constraints like:
    - "maximum allocation", "allocation cap", "cannot exceed"
    - "sector limit", "sector allocation"
    - "tracking error", "maximum tracking error"
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Policy file not found: {file_path}")

    # Try pdfplumber first (better text extraction)
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        LOGGER.info(f"Extracted {len(text)} characters from PDF using pdfplumber")
    except Exception as e:
        LOGGER.warning(f"pdfplumber failed: {e}, trying PyPDF2")
        # Fallback to PyPDF2
        try:
            text = ""
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            LOGGER.info(f"Extracted {len(text)} characters from PDF using PyPDF2")
        except Exception as e2:
            raise ValueError(f"Failed to extract text from PDF: {e2}")

    # Parse constraints using regex patterns
    constraints = []

    # Allocation cap patterns
    allocation_patterns = [
        r"maximum\s+(?:allocation|position)\s+(?:per\s+)?(?:security|holding)\s*:?\s*(\d+(?:\.\d+)?)%?",
        r"allocation\s+cap\s*:?\s*(\d+(?:\.\d+)?)%?",
        r"(?:no\s+)?(?:single\s+)?(?:security|holding)\s+shall\s+(?:exceed|cannot\s+exceed)\s+(\d+(?:\.\d+)?)%?",
    ]
    for pattern in allocation_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1)) / 100.0
            constraints.append({"type": "allocation_cap", "ticker": "*", "max_weight": value})
            break

    # Sector limit patterns
    sector_pattern = r"(?:sector\s+)?(?:allocation|limit)\s+(?:for\s+)?([A-Za-z]+)\s*:?\s*(\d+(?:\.\d+)?)%?\s*(?:to|-|\s+)?(\d+(?:\.\d+)?)?%?"
    for match in re.finditer(sector_pattern, text, re.IGNORECASE):
        sector = match.group(1)
        min_val = float(match.group(2)) / 100.0 if match.group(2) else None
        max_val = float(match.group(3)) / 100.0 if match.group(3) else None
        constraints.append({"type": "sector_limit", "sector": sector, "min_weight": min_val, "max_weight": max_val})

    # Tracking error patterns
    te_patterns = [
        r"maximum\s+tracking\s+error\s*:?\s*(\d+(?:\.\d+)?)%?",
        r"tracking\s+error\s+(?:limit|threshold|cannot\s+exceed)\s*:?\s*(\d+(?:\.\d+)?)%?",
    ]
    for pattern in te_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value = float(match.group(1)) / 100.0
            constraints.append({"type": "tracking_error", "max_value": value})
            break

    LOGGER.info(f"Extracted {len(constraints)} constraints from PDF")

    return {"constraints": constraints}


def save_portfolio_to_database(
    database_path: Path,
    portfolio_id: str,
    name: str,
    base_currency: str,
    holdings: List[Dict[str, Any]],
    benchmark_index: Optional[str] = None,
    strategy_type: Optional[str] = None,
) -> None:
    """Save portfolio holdings to database."""
    # Create portfolio metadata
    metadata = database.PortfolioMetadataRecord(
        portfolio_id=portfolio_id,
        name=name,
        base_currency=base_currency,
        benchmark_index=benchmark_index,
        inception_date=datetime.now(timezone.utc),
        strategy_type=strategy_type,
        created_at=datetime.now(timezone.utc),
    )
    database.upsert_portfolio_metadata(database_path, metadata)

    # Convert holdings to records
    holding_records = []
    for holding in holdings:
        holding_record = database.PortfolioHoldingRecord(
            ticker=holding["ticker"],
            portfolio_id=portfolio_id,
            position_date=holding["position_date"],
            shares=holding.get("shares"),
            weight=holding.get("weight"),
            cost_basis=holding.get("cost_basis"),
            market_value=holding.get("market_value"),
            currency=holding.get("currency", base_currency),
            account_id=holding.get("account_id"),
        )
        holding_records.append(holding_record)

    # Bulk insert holdings
    if not holding_records:
        LOGGER.warning(f"No holding records to save for portfolio '{name}' ({portfolio_id}). Holdings list may be empty or invalid.")
    else:
        database.bulk_insert_portfolio_holdings(database_path, holding_records)
        LOGGER.info(f"Saved portfolio '{name}' ({portfolio_id}) with {len(holding_records)} holdings")


def save_policy_to_database(
    database_path: Path,
    portfolio_id: str,
    constraints: List[Dict[str, Any]],
    document_type: str = "IPS",
    file_path: Optional[str] = None,
) -> None:
    """Save policy constraints to database."""
    # Save policy document
    document_id = str(uuid.uuid4())
    document = database.PolicyDocumentRecord(
        document_id=document_id,
        portfolio_id=portfolio_id,
        document_type=document_type,
        file_path=file_path,
        parsed_constraints={"constraints": constraints},
        uploaded_at=datetime.now(timezone.utc),
    )
    database.upsert_policy_document(database_path, document)

    # Save individual constraints
    for constraint in constraints:
        constraint_id = str(uuid.uuid4())
        dimension = constraint.get("ticker") or constraint.get("sector")
        constraint_record = database.PolicyConstraintRecord(
            constraint_id=constraint_id,
            portfolio_id=portfolio_id,
            constraint_type=constraint["type"],
            target_value=constraint.get("target_value"),
            min_value=constraint.get("min_weight") or constraint.get("min_value"),
            max_value=constraint.get("max_weight") or constraint.get("max_value"),
            unit="percent" if constraint["type"] in ["allocation_cap", "sector_limit"] else None,
            active=True,
            dimension=dimension,
        )
        database.upsert_policy_constraint(database_path, constraint_record)

    LOGGER.info(f"Saved {len(constraints)} policy constraints for portfolio {portfolio_id}")



# ======================================================================
# ENRICHMENT
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class EnrichedHolding:
    """Enriched holding with fundamentals and sector classification."""

    ticker: str
    weight: Optional[float]
    shares: Optional[float]
    price: Optional[float]
    market_value: Optional[float]
    sector: Optional[str]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    revenue_growth: Optional[float]
    roe: Optional[float]
    roic: Optional[float]


@dataclass
class PortfolioStatistics:
    """Aggregate portfolio statistics."""

    total_market_value: float
    num_holdings: int
    weighted_avg_pe: Optional[float]
    weighted_avg_dividend_yield: Optional[float]
    sector_concentration: Dict[str, float]  # sector -> weight
    top_10_weight: float
    num_sectors: int


def map_sector_classification(ticker: str) -> Optional[str]:
    """Map ticker to GICS sector using sector_analytics mapping."""
    return SECTOR_MAP.get(ticker.upper())


@monitor_performance
def enrich_holdings_with_fundamentals(
    database_path: database.Path,
    holdings: List[Dict[str, Any]],
    enrich_metrics: Optional[List[str]] = None,
) -> List[EnrichedHolding]:
    """
    Join portfolio holdings with fundamentals from metric_snapshots.

    Args:
        database_path: Path to database
        holdings: List of holding dicts with ticker, weight, shares, etc.
        enrich_metrics: Optional list of metrics to fetch (default: common metrics)

    Returns:
        List of enriched holdings with fundamentals
    """
    if enrich_metrics is None:
        enrich_metrics = ["pe_ratio", "dividend_yield", "revenue_cagr_3y", "roe", "roic"]

    enriched = []

    with _get_db_connection(database_path) as conn:
        for holding in holdings:
            ticker = holding.get("ticker", "").upper()

            enriched_holding = EnrichedHolding(
                ticker=ticker,
                weight=holding.get("weight"),
                shares=holding.get("shares"),
                price=holding.get("price"),
                market_value=holding.get("market_value"),
                sector=map_sector_classification(ticker),
                market_cap=None,
                pe_ratio=None,
                dividend_yield=None,
                revenue_growth=None,
                roe=None,
                roic=None,
            )

            # Fetch fundamentals for each metric
            for metric in enrich_metrics:
                try:
                    row = conn.execute(
                        """
                        SELECT value
                        FROM metric_snapshots
                        WHERE ticker = ? AND metric = ?
                        ORDER BY start_year DESC, end_year DESC
                        LIMIT 1
                        """,
                        (ticker, metric),
                    ).fetchone()

                    if row and row["value"] is not None:
                        setattr(enriched_holding, metric, row["value"])

                except Exception as e:
                    LOGGER.debug(f"Could not fetch {metric} for {ticker}: {e}")

            # Fetch market cap if not provided
            if enriched_holding.market_cap is None:
                try:
                    row = conn.execute(
                        """
                        SELECT value
                        FROM metric_snapshots
                        WHERE ticker = ? AND metric = 'market_cap'
                        ORDER BY start_year DESC
                        LIMIT 1
                        """,
                        (ticker,),
                    ).fetchone()
                    if row and row["value"]:
                        enriched_holding.market_cap = row["value"]
                except Exception as e:
                    LOGGER.debug(f"Could not fetch market_cap for {ticker}: {e}")

            enriched.append(enriched_holding)

    LOGGER.info(f"Enriched {len(enriched)} holdings with fundamentals")
    return enriched


def fetch_missing_fundamentals(database_path: database.Path, tickers: List[str]) -> List[str]:
    """
    Identify tickers in portfolio but not in database.

    Returns list of tickers missing from metric_snapshots.
    """
    missing = []

    with _get_db_connection(database_path) as conn:
        for ticker in tickers:
            row = conn.execute(
                """
                SELECT COUNT(*) as count
                FROM metric_snapshots
                WHERE ticker = ?
                """,
                (ticker.upper(),),
            ).fetchone()

            if row and row["count"] == 0:
                missing.append(ticker.upper())

    LOGGER.info(f"Found {len(missing)} tickers missing fundamentals: {missing}")
    return missing


def calculate_portfolio_statistics(enriched_holdings: List[EnrichedHolding]) -> PortfolioStatistics:
    """
    Calculate aggregate portfolio statistics from enriched holdings.

    Returns portfolio statistics including weighted averages, sector concentration, etc.
    """
    # Total market value
    total_mv = sum(h.market_value or 0 for h in enriched_holdings if h.market_value)

    # Sector concentration
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    # Sort holdings by weight (descending) for top 10 calculation
    sorted_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)
    top_10_weight = sum((h.weight or 0) for h in sorted_holdings[:10])

    # Weighted average calculations
    weighted_pe_sum = 0.0
    weighted_pe_denom = 0.0
    weighted_div_sum = 0.0
    weighted_div_denom = 0.0

    for holding in enriched_holdings:
        if holding.weight:
            if holding.pe_ratio is not None and holding.pe_ratio > 0:
                weighted_pe_sum += holding.weight * holding.pe_ratio
                weighted_pe_denom += holding.weight
            if holding.dividend_yield is not None and holding.dividend_yield > 0:
                weighted_div_sum += holding.weight * holding.dividend_yield
                weighted_div_denom += holding.weight

    weighted_avg_pe = weighted_pe_sum / weighted_pe_denom if weighted_pe_denom > 0 else None
    weighted_avg_div = weighted_div_sum / weighted_div_denom if weighted_div_denom > 0 else None

    stats = PortfolioStatistics(
        total_market_value=total_mv,
        num_holdings=len(enriched_holdings),
        weighted_avg_pe=weighted_avg_pe,
        weighted_avg_dividend_yield=weighted_avg_div,
        sector_concentration=dict(sector_weights),
        top_10_weight=top_10_weight,
        num_sectors=len(sector_weights),
    )

    LOGGER.info(f"Calculated portfolio statistics: {stats.num_holdings} holdings, {stats.num_sectors} sectors")
    return stats


def get_holdings_by_sector(enriched_holdings: List[EnrichedHolding]) -> Dict[str, List[EnrichedHolding]]:
    """Group holdings by GICS sector."""
    by_sector = defaultdict(list)

    for holding in enriched_holdings:
        sector = holding.sector or "Unknown"
        by_sector[sector].append(holding)

    return dict(by_sector)


@monitor_performance
def load_sp500_benchmark_weights() -> Dict[str, float]:
    """
    Load S&P 500 benchmark weights from market-cap weighted data.
    
    Returns:
        Dict of ticker -> weight (normalized to sum to 1.0)
    
    Uses real market-cap weighted distributions from data/sp500_benchmark_weights.csv
    Falls back to equal weights if file not found.
    Cached for performance.
    """
    global _SP500_WEIGHTS_CACHE
    
    # Use cached version if available
    if _SP500_WEIGHTS_CACHE is not None:
        return _SP500_WEIGHTS_CACHE
    
    # Try to load from CSV file
    csv_path = Path(__file__).parent.parent.parent / "data" / "sp500_benchmark_weights.csv"
    
    if csv_path.exists():
        try:
            import csv
            weights = {}
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row['ticker']
                    weight = float(row['weight'])
                    weights[ticker] = weight
            LOGGER.info(f"Loaded {len(weights)} S&P 500 benchmark weights from {csv_path}")
            _SP500_WEIGHTS_CACHE = weights
            return weights
        except Exception as e:
            LOGGER.warning(f"Failed to load benchmark weights from CSV: {e}. Using equal weights.")
    
    # Fallback to equal weights
    from .ticker_universe import load_ticker_universe
    
    tickers = load_ticker_universe("sp500")
    n = len(tickers)
    
    if n == 0:
        _SP500_WEIGHTS_CACHE = {}
        return {}
    
    # Equal weight distribution (1/n)
    weight = 1.0 / n
    weights = {ticker: weight for ticker in tickers}
    _SP500_WEIGHTS_CACHE = weights
    return weights


def calculate_active_weights(
    portfolio_weights: Dict[str, float], benchmark_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate active weights (over/underweights vs benchmark).

    Args:
        portfolio_weights: Dict of ticker -> weight for portfolio
        benchmark_weights: Dict of ticker -> weight for benchmark

    Returns:
        Dict of ticker -> active weight (portfolio - benchmark)
    """
    all_tickers = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
    active_weights = {}

    for ticker in all_tickers:
        port_wt = portfolio_weights.get(ticker, 0.0)
        bmk_wt = benchmark_weights.get(ticker, 0.0)
        active_weights[ticker] = port_wt - bmk_wt

    return active_weights


def calculate_sector_active_weights(
    enriched_holdings: List[EnrichedHolding], benchmark_sector_weights: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate active weights by sector.

    Args:
        enriched_holdings: Enriched portfolio holdings
        benchmark_sector_weights: Benchmark sector weights (sector -> weight)

    Returns:
        Dict of sector -> active weight
    """
    portfolio_sectors = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            portfolio_sectors[holding.sector] += holding.weight

    active_weights = {}
    all_sectors = set(portfolio_sectors.keys()) | set(benchmark_sector_weights.keys())

    for sector in all_sectors:
        port_wt = portfolio_sectors.get(sector, 0.0)
        bmk_wt = benchmark_sector_weights.get(sector, 0.0)
        active_weights[sector] = port_wt - bmk_wt

    return active_weights


def compare_with_benchmark_stats(
    portfolio_stats: PortfolioStatistics, benchmark_stats: PortfolioStatistics
) -> Dict[str, Any]:
    """
    Compare portfolio statistics vs benchmark.

    Returns comparison metrics including active returns, sector tilts, etc.
    """
    comparison = {
        "num_holdings": portfolio_stats.num_holdings - benchmark_stats.num_holdings,
        "num_sectors": portfolio_stats.num_sectors - benchmark_stats.num_sectors,
        "top_10_concentration": portfolio_stats.top_10_weight - benchmark_stats.top_10_weight,
        "weighted_pe_spread": None,
        "weighted_dividend_spread": None,
        "sector_tilts": {},
    }

    # PE and dividend yield spreads
    if portfolio_stats.weighted_avg_pe and benchmark_stats.weighted_avg_pe:
        comparison["weighted_pe_spread"] = portfolio_stats.weighted_avg_pe - benchmark_stats.weighted_avg_pe

    if portfolio_stats.weighted_avg_dividend_yield and benchmark_stats.weighted_avg_dividend_yield:
        comparison["weighted_dividend_spread"] = (
            portfolio_stats.weighted_avg_dividend_yield - benchmark_stats.weighted_avg_dividend_yield
        )

    # Sector tilts (active weights)
    all_sectors = set(portfolio_stats.sector_concentration.keys()) | set(benchmark_stats.sector_concentration.keys())
    for sector in all_sectors:
        port_wt = portfolio_stats.sector_concentration.get(sector, 0.0)
        bmk_wt = benchmark_stats.sector_concentration.get(sector, 0.0)
        comparison["sector_tilts"][sector] = port_wt - bmk_wt

    return comparison


def save_enriched_holdings_to_exposure_snapshots(
    database_path: database.Path,
    portfolio_id: str,
    enriched_holdings: List[EnrichedHolding],
    snapshot_date: Optional[datetime] = None,
) -> None:
    """
    Save enriched holdings as exposure snapshot for historical tracking.

    Creates exposure snapshots for sector and individual holding exposures.
    """
    if snapshot_date is None:
        snapshot_date = datetime.now(timezone.utc)

    snapshots = []

    # Sector exposures
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    for sector, weight in sector_weights.items():
        snapshot_id = f"{portfolio_id}_{snapshot_date.isoformat()}_{sector}_sector"
        snapshots.append(
            database.ExposureSnapshotRecord(
                snapshot_id=snapshot_id,
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date,
                exposure_type="sector",
                dimension=sector,
                value=None,
                weight=weight,
            )
        )

    # Individual holding exposures
    for holding in enriched_holdings:
        if holding.weight:
            snapshot_id = f"{portfolio_id}_{snapshot_date.isoformat()}_{holding.ticker}_holding"
            snapshots.append(
                database.ExposureSnapshotRecord(
                    snapshot_id=snapshot_id,
                    portfolio_id=portfolio_id,
                    snapshot_date=snapshot_date,
                    exposure_type="issuer",
                    dimension=holding.ticker,
                    value=holding.market_value,
                    weight=holding.weight,
                )
            )

    database.bulk_insert_exposure_snapshots(database_path, snapshots)
    LOGGER.info(f"Saved {len(snapshots)} exposure snapshots for portfolio {portfolio_id}")



# ======================================================================
# CALCULATIONS
# ======================================================================


LOGGER = logging.getLogger(__name__)


def fetch_historical_prices(
    database_path: database.Path,
    ticker: str,
    start_date: datetime,
    end_date: datetime,
) -> List[Tuple[datetime, float]]:
    """
    Fetch historical prices for a ticker from the database.
    
    Returns list of (date, price) tuples sorted by date.
    """
    with database._connect(database_path) as conn:
        conn.row_factory = _sqlite3.Row
        rows = conn.execute(
            """
            SELECT quote_time, price
            FROM market_quotes
            WHERE ticker = ? AND quote_time >= ? AND quote_time <= ?
            ORDER BY quote_time ASC
            """,
            (
                database._normalize_ticker(ticker),
                database._iso_utc(start_date),
                database._iso_utc(end_date),
            ),
        ).fetchall()
    
    prices = []
    for row in rows:
        quote_time = database._parse_dt(row["quote_time"])
        if quote_time:
            prices.append((quote_time, row["price"]))
    
    return prices


def calculate_returns(prices: List[Tuple[datetime, float]]) -> np.ndarray:
    """
    Calculate daily returns from price series.
    
    Returns numpy array of daily returns (pct_change).
    """
    if len(prices) < 2:
        return np.array([])
    
    price_values = np.array([p[1] for p in prices])
    returns = np.diff(price_values) / price_values[:-1]
    return returns


def calculate_covariance_matrix(
    database_path: database.Path,
    ticker_list: List[str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 252,
) -> Tuple[np.ndarray, List[str]]:
    """
    Calculate covariance matrix from historical price data.
    
    Args:
        database_path: Path to database
        ticker_list: List of tickers to include
        start_date: Start date (defaults to lookback_days ago)
        end_date: End date (defaults to today)
        lookback_days: Number of trading days to look back (default 252 = 1 year)
    
    Returns:
        Tuple of (covariance_matrix, valid_ticker_list)
        Only includes tickers with sufficient historical data.
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=lookback_days * 2)  # Extra buffer for weekends
    
    # Fetch historical prices for all tickers
    ticker_returns: Dict[str, np.ndarray] = {}
    valid_tickers = []
    
    for ticker in ticker_list:
        prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
        
        if len(prices) < 2:
            LOGGER.warning(f"Insufficient price data for {ticker}: {len(prices)} observations")
            continue
        
        returns = calculate_returns(prices)
        
        if len(returns) < 20:  # Need at least 20 observations
            LOGGER.warning(f"Insufficient returns for {ticker}: {len(returns)} observations")
            continue
        
        ticker_returns[ticker] = returns
        valid_tickers.append(ticker)
    
    if not valid_tickers:
        LOGGER.warning("No valid tickers with sufficient historical data")
        # Return identity matrix as fallback
        n = len(ticker_list)
        return np.eye(n) * 0.04, ticker_list
    
    # Align returns by date (if we had date info, but we'll use length matching for now)
    # For simplicity, we'll use the minimum length across all tickers
    min_length = min(len(returns) for returns in ticker_returns.values())
    
    # Truncate all returns to same length (take most recent)
    aligned_returns = np.array([
        ticker_returns[ticker][-min_length:] for ticker in valid_tickers
    ])
    
    # Calculate covariance matrix
    # Shape: (n_tickers, n_days) -> (n_tickers, n_tickers)
    covariance_matrix = np.cov(aligned_returns) * 252  # Annualize (252 trading days)
    
    # Ensure positive semi-definite
    covariance_matrix = (covariance_matrix + covariance_matrix.T) / 2
    
    # Add small regularization term if needed
    eigenvals = np.linalg.eigvals(covariance_matrix)
    if np.any(eigenvals < 0):
        LOGGER.warning("Covariance matrix not positive semi-definite, adding regularization")
        regularization = np.abs(np.min(eigenvals)) + 0.01
        covariance_matrix += np.eye(len(valid_tickers)) * regularization
    
    return covariance_matrix, valid_tickers


def calculate_beta(
    database_path: database.Path,
    ticker: str,
    benchmark: str = "SPY",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 252,
) -> Optional[float]:
    """
    Calculate beta via regression of ticker returns vs benchmark returns.
    
    Args:
        database_path: Path to database
        ticker: Ticker to calculate beta for
        benchmark: Benchmark ticker (default: SPY for S&P 500)
        start_date: Start date (defaults to lookback_days ago)
        end_date: End date (defaults to today)
        lookback_days: Number of trading days to look back (default 252 = 1 year)
    
    Returns:
        Beta coefficient, or None if insufficient data
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    if start_date is None:
        start_date = end_date - timedelta(days=lookback_days * 2)
    
    # Fetch historical prices
    ticker_prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
    benchmark_prices = fetch_historical_prices(database_path, benchmark, start_date, end_date)
    
    if len(ticker_prices) < 20 or len(benchmark_prices) < 20:
        LOGGER.warning(f"Insufficient data for beta calculation: {ticker} ({len(ticker_prices)} obs), {benchmark} ({len(benchmark_prices)} obs)")
        return None
    
    # Calculate returns
    ticker_returns = calculate_returns(ticker_prices)
    benchmark_returns = calculate_returns(benchmark_prices)
    
    if len(ticker_returns) < 20 or len(benchmark_returns) < 20:
        return None
    
    # Align by length (take most recent overlapping period)
    min_length = min(len(ticker_returns), len(benchmark_returns))
    ticker_returns_aligned = ticker_returns[-min_length:]
    benchmark_returns_aligned = benchmark_returns[-min_length:]
    
    # Calculate beta via linear regression: y = alpha + beta * x + epsilon
    # Where y = ticker returns, x = benchmark returns
    slope, intercept, r_value, p_value, std_err = stats.linregress(
        benchmark_returns_aligned, ticker_returns_aligned
    )
    
    LOGGER.debug(f"Beta for {ticker} vs {benchmark}: {slope:.3f} (R²={r_value**2:.3f}, p={p_value:.3f})")
    
    return float(slope)


def calculate_betas_batch(
    database_path: database.Path,
    ticker_list: List[str],
    benchmark: str = "SPY",
    lookback_days: int = 252,
) -> Dict[str, float]:
    """
    Calculate betas for multiple tickers in batch.
    
    Returns dict of ticker -> beta.
    Missing/invalid betas are not included in the result.
    """
    betas = {}
    for ticker in ticker_list:
        beta = calculate_beta(
            database_path,
            ticker,
            benchmark=benchmark,
            lookback_days=lookback_days,
        )
        if beta is not None:
            betas[ticker] = beta
    
    return betas


def calculate_expected_returns(
    database_path: database.Path,
    ticker_list: List[str],
    method: str = "historical",
    lookback_days: int = 252,
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """
    Calculate expected returns for tickers.
    
    Args:
        database_path: Path to database
        ticker_list: List of tickers
        method: "historical" (default) or "capm"
        lookback_days: Number of days for historical calculation
        risk_free_rate: Risk-free rate for CAPM (default 2% = 0.02)
    
    Returns:
        Dict of ticker -> expected return
    """
    if method == "historical":
        # Calculate mean historical return (annualized)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=lookback_days * 2)
        
        returns_dict = {}
        for ticker in ticker_list:
            prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
            if len(prices) < 2:
                continue
            
            daily_returns = calculate_returns(prices)
            if len(daily_returns) > 0:
                mean_daily_return = np.mean(daily_returns)
                annualized_return = mean_daily_return * 252  # Annualize
                returns_dict[ticker] = annualized_return
        
        return returns_dict
    
    elif method == "capm":
        # CAPM: E[R] = Rf + Beta * (E[Rm] - Rf)
        # Assume market return is 8% (E[Rm] = 0.08)
        market_return = 0.08
        
        betas = calculate_betas_batch(database_path, ticker_list, lookback_days=lookback_days)
        
        returns_dict = {}
        for ticker in ticker_list:
            beta = betas.get(ticker, 1.0)  # Default beta = 1.0
            expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
            returns_dict[ticker] = expected_return
        
        return returns_dict
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'historical' or 'capm'")


# ======================================================================
# EXPOSURE
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class ExposureAnalysis:
    """Multi-dimensional portfolio exposure analysis."""

    sector_exposure: Dict[str, float]  # sector -> weight
    factor_exposure: Dict[str, float]  # factor -> exposure
    issuer_exposure: Dict[str, float]  # ticker -> weight
    geographic_exposure: Dict[str, float]  # country -> weight
    concentration_metrics: Dict[str, float]  # HHI, top_n_concentration, etc.


def calculate_sector_exposure(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate sector exposure by GICS sector.

    Returns dict of sector -> portfolio weight.
    """
    sector_weights = defaultdict(float)
    for holding in enriched_holdings:
        if holding.sector and holding.weight:
            sector_weights[holding.sector] += holding.weight

    return dict(sector_weights)


def calculate_factor_exposure(
    enriched_holdings: List[EnrichedHolding],
    database_path: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Calculate factor exposures using simplified factor model.

    Factors: beta, value, momentum, size, quality, volatility
    Returns dict of factor -> exposure.
    
    Args:
        enriched_holdings: List of enriched holdings
        database_path: Optional database path for beta calculation (if None, uses fallback)
    """
    factor_exposures = defaultdict(float)
    total_weight = sum(h.weight or 0 for h in enriched_holdings)

    if total_weight == 0:
        return {}

    # Calculate betas from database if available
    betas = {}
    if database_path:
        try:
            ticker_list = [h.ticker for h in enriched_holdings if h.ticker]
            betas = calculate_betas_batch(
                database_path,
                ticker_list,
                benchmark="SPY",
                lookback_days=252,
            )
        except Exception as e:
            LOGGER.debug(f"Could not calculate betas from database: {e}")

    for holding in enriched_holdings:
        weight = holding.weight or 0.0

        # Beta (use database calculation if available, fallback to yfinance)
        if holding.ticker:
            beta = None
            if database_path and holding.ticker in betas:
                beta = betas[holding.ticker]
            else:
                # Fallback to yfinance if database unavailable
                try:
                    ticker_data = yf.Ticker(holding.ticker)
                    hist = ticker_data.history(period="1y")
                    if not hist.empty:
                        sp500 = yf.Ticker("^GSPC").history(period="1y")
                        if not sp500.empty:
                            stock_returns = hist["Close"].pct_change().dropna()
                            market_returns = sp500["Close"].pct_change().dropna()
                            if len(stock_returns) > 10 and len(market_returns) > 10:
                                common_dates = stock_returns.index.intersection(market_returns.index)
                                if len(common_dates) > 10:
                                    stock_ret = stock_returns.loc[common_dates]
                                    mkt_ret = market_returns.loc[common_dates]
                                    beta = stock_ret.cov(mkt_ret) / mkt_ret.var() if mkt_ret.var() > 0 else 1.0
                except Exception as e:
                    LOGGER.debug(f"Could not calculate beta for {holding.ticker}: {e}")
            
            if beta is not None:
                factor_exposures["beta"] += weight * beta

        # Value (inverse of P/E)
        if holding.pe_ratio and holding.pe_ratio > 0:
            value_score = 1.0 / holding.pe_ratio
            factor_exposures["value"] += weight * value_score

        # Momentum (revenue growth proxy)
        if holding.revenue_growth:
            momentum_score = max(0, min(1, holding.revenue_growth / 20))  # Normalize to 0-1
            factor_exposures["momentum"] += weight * momentum_score

        # Quality (ROE proxy)
        if holding.roe:
            quality_score = max(0, min(1, holding.roe / 30))  # Normalize to 0-1
            factor_exposures["quality"] += weight * quality_score

    return dict(factor_exposures)


def calculate_issuer_exposure(enriched_holdings: List[EnrichedHolding], top_n: int = 10) -> Dict[str, float]:
    """
    Calculate issuer concentration.

    Returns dict of ticker -> weight for top N holdings.
    """
    sorted_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)
    issuer_weights = {holding.ticker: holding.weight for holding in sorted_holdings[:top_n] if holding.weight}

    return issuer_weights


def calculate_concentration_metrics(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate concentration metrics: HHI, top 5/10/20 concentration.

    HHI (Herfindahl-Hirschman Index) measures concentration (0-1, higher = more concentrated).
    """
    weights = [h.weight or 0.0 for h in enriched_holdings if h.weight]
    total_weight = sum(weights)

    if total_weight == 0:
        return {}

    # Normalize weights to sum to 1
    normalized_weights = [w / total_weight for w in weights]

    # HHI
    hhi = sum(w**2 for w in normalized_weights)

    # Top N concentration
    sorted_weights = sorted(normalized_weights, reverse=True)
    top_5_concentration = sum(sorted_weights[:5])
    top_10_concentration = sum(sorted_weights[:10])
    top_20_concentration = sum(sorted_weights[:20])

    return {
        "hhi": hhi,
        "top_5_concentration": top_5_concentration,
        "top_10_concentration": top_10_concentration,
        "top_20_concentration": top_20_concentration,
        "effective_num_positions": 1.0 / hhi if hhi > 0 else 0,
    }


def calculate_geographic_exposure(enriched_holdings: List[EnrichedHolding]) -> Dict[str, float]:
    """
    Calculate geographic exposure by company headquarters country.

    This is a simplified implementation. A full version would use country mapping data.
    """
    # Simplified mapping for major US stocks
    us_tickers = {"AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "V", "MA", "JPM"}
    geography_weights = defaultdict(float)

    for holding in enriched_holdings:
        if holding.weight:
            if holding.ticker in us_tickers:
                geography_weights["United States"] += holding.weight
            else:
                geography_weights["Other"] += holding.weight

    return dict(geography_weights)


def analyze_exposure(
    enriched_holdings: List[EnrichedHolding],
    database_path: Optional[Path] = None,
) -> ExposureAnalysis:
    """
    Perform comprehensive exposure analysis across all dimensions.

    Returns ExposureAnalysis with sector, factor, issuer, and geographic exposures.
    """
    sector_exp = calculate_sector_exposure(enriched_holdings)
    factor_exp = calculate_factor_exposure(enriched_holdings, database_path=database_path)
    issuer_exp = calculate_issuer_exposure(enriched_holdings, top_n=10)
    geographic_exp = calculate_geographic_exposure(enriched_holdings)
    concentration = calculate_concentration_metrics(enriched_holdings)

    analysis = ExposureAnalysis(
        sector_exposure=sector_exp,
        factor_exposure=factor_exp,
        issuer_exposure=issuer_exp,
        geographic_exposure=geographic_exp,
        concentration_metrics=concentration,
    )

    LOGGER.info(f"Exposure analysis completed: {len(sector_exp)} sectors, HHI={concentration.get('hhi', 0):.3f}")
    return analysis


def compare_exposures_vs_benchmark(
    portfolio_holdings: List[EnrichedHolding], benchmark_holdings: List[EnrichedHolding]
) -> Dict[str, Any]:
    """
    Compare portfolio exposures vs benchmark holdings.

    Returns comparison breakdowns by sector, factor, and issuer.
    """
    portfolio_analysis = analyze_exposure(portfolio_holdings)
    benchmark_analysis = analyze_exposure(benchmark_holdings)

    comparison = {
        "sector_tilts": {},
        "factor_tilts": {},
        "issuer_tilts": {},
        "concentration_difference": {},
    }

    # Sector tilts (active weights)
    all_sectors = set(portfolio_analysis.sector_exposure.keys()) | set(benchmark_analysis.sector_exposure.keys())
    for sector in all_sectors:
        port_wt = portfolio_analysis.sector_exposure.get(sector, 0.0)
        bmk_wt = benchmark_analysis.sector_exposure.get(sector, 0.0)
        comparison["sector_tilts"][sector] = port_wt - bmk_wt

    # Factor tilts
    all_factors = set(portfolio_analysis.factor_exposure.keys()) | set(benchmark_analysis.factor_exposure.keys())
    for factor in all_factors:
        port_exp = portfolio_analysis.factor_exposure.get(factor, 0.0)
        bmk_exp = benchmark_analysis.factor_exposure.get(factor, 0.0)
        comparison["factor_tilts"][factor] = port_exp - bmk_exp

    # Issuer tilts
    all_issuers = set(portfolio_analysis.issuer_exposure.keys()) | set(benchmark_analysis.issuer_exposure.keys())
    for issuer in all_issuers:
        port_wt = portfolio_analysis.issuer_exposure.get(issuer, 0.0)
        bmk_wt = benchmark_analysis.issuer_exposure.get(issuer, 0.0)
        comparison["issuer_tilts"][issuer] = port_wt - bmk_wt

    # Concentration differences
    if portfolio_analysis.concentration_metrics and benchmark_analysis.concentration_metrics:
        comparison["concentration_difference"] = {
            "hhi_spread": portfolio_analysis.concentration_metrics.get("hhi", 0)
            - benchmark_analysis.concentration_metrics.get("hhi", 0),
            "top_10_spread": portfolio_analysis.concentration_metrics.get("top_10_concentration", 0)
            - benchmark_analysis.concentration_metrics.get("top_10_concentration", 0),
        }

    return comparison


def format_exposure_table(exposure_dict: Dict[str, float], title: str = "Exposure") -> str:
    """
    Format exposure dictionary as a formatted table string.

    Useful for chatbot/CLI output.
    """
    if not exposure_dict:
        return f"{title}: No data"

    lines = [f"\n{title}:", "=" * 50]
    sorted_items = sorted(exposure_dict.items(), key=lambda x: x[1], reverse=True)

    for key, value in sorted_items:
        lines.append(f"  {key:30s}: {value:7.2%}")

    return "\n".join(lines)


def check_policy_compliance(
    exposure_analysis: ExposureAnalysis, policy_constraints: List[Any]  # PolicyConstraint type
) -> List[Dict[str, Any]]:
    """
    Check if portfolio exposures comply with policy constraints.

    Returns list of violations with details.
    """
    violations = []

    for constraint in policy_constraints:
        if constraint.constraint_type == "allocation_cap":
            if constraint.dimension == "*":  # Universal cap
                for ticker, weight in exposure_analysis.issuer_exposure.items():
                    if constraint.max_value and weight > constraint.max_value:
                        violations.append(
                            {
                                "constraint_type": "allocation_cap",
                                "dimension": ticker,
                                "current_value": weight,
                                "limit": constraint.max_value,
                                "violation": weight - constraint.max_value,
                            }
                        )

        elif constraint.constraint_type == "sector_limit":
            sector = constraint.dimension
            current_wt = exposure_analysis.sector_exposure.get(sector, 0.0)
            if constraint.min_value and current_wt < constraint.min_value:
                violations.append(
                    {
                        "constraint_type": "sector_limit",
                        "dimension": sector,
                        "current_value": current_wt,
                        "limit": constraint.min_value,
                        "violation": current_wt - constraint.min_value,
                    }
                )
            if constraint.max_value and current_wt > constraint.max_value:
                violations.append(
                    {
                        "constraint_type": "sector_limit",
                        "dimension": sector,
                        "current_value": current_wt,
                        "limit": constraint.max_value,
                        "violation": current_wt - constraint.max_value,
                    }
                )

    if violations:
        LOGGER.warning(f"Policy violations detected: {len(violations)}")
    else:
        LOGGER.info("All policy constraints satisfied")

    return violations


def compare_exposures_before_after_rebalance(
    before_holdings: List[EnrichedHolding], after_holdings: List[EnrichedHolding]
) -> Dict[str, Any]:
    """
    Show exposure changes from proposed rebalance.

    Returns comparison showing sector and factor changes.
    """
    before_analysis = analyze_exposure(before_holdings)
    after_analysis = analyze_exposure(after_holdings)

    changes = {
        "sector_changes": {},
        "factor_changes": {},
        "concentration_changes": {},
    }

    # Sector changes
    all_sectors = set(before_analysis.sector_exposure.keys()) | set(after_analysis.sector_exposure.keys())
    for sector in all_sectors:
        before_wt = before_analysis.sector_exposure.get(sector, 0.0)
        after_wt = after_analysis.sector_exposure.get(sector, 0.0)
        if abs(after_wt - before_wt) > 0.001:  # Only show non-trivial changes
            changes["sector_changes"][sector] = {"before": before_wt, "after": after_wt, "change": after_wt - before_wt}

    # Factor changes
    all_factors = set(before_analysis.factor_exposure.keys()) | set(after_analysis.factor_exposure.keys())
    for factor in all_factors:
        before_exp = before_analysis.factor_exposure.get(factor, 0.0)
        after_exp = after_analysis.factor_exposure.get(factor, 0.0)
        if abs(after_exp - before_exp) > 0.001:
            changes["factor_changes"][factor] = {"before": before_exp, "after": after_exp, "change": after_exp - before_exp}

    # Concentration changes
    if before_analysis.concentration_metrics and after_analysis.concentration_metrics:
        changes["concentration_changes"] = {
            "hhi_change": after_analysis.concentration_metrics.get("hhi", 0) - before_analysis.concentration_metrics.get("hhi", 0),
            "top_10_change": after_analysis.concentration_metrics.get("top_10_concentration", 0)
            - before_analysis.concentration_metrics.get("top_10_concentration", 0),
        }

    return changes



# ======================================================================
# OPTIMIZER
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of portfolio optimization."""

    optimized_weights: Dict[str, float]
    proposed_trades: List[Dict[str, Any]]
    objective_value: Optional[float]
    iterations: int
    status: str
    policy_flags: List[str]
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]


@dataclass
class PolicyConstraint:
    """Portfolio policy constraint definition."""

    constraint_type: str  # allocation_cap, sector_limit, tracking_error, etc.
    dimension: Optional[str]  # ticker or sector name
    min_value: Optional[float]
    max_value: Optional[float]


@monitor_performance
def optimize_portfolio_sharpe(
    current_holdings: Dict[str, float],  # ticker -> weight
    expected_returns: Dict[str, float],
    covariance_matrix: np.ndarray,
    ticker_list: List[str],
    constraints: List[PolicyConstraint],
    turnover_limit: Optional[float] = None,
    objective: str = "maximize_sharpe",
) -> OptimizationResult:
    """
    Optimize portfolio to maximize Sharpe ratio subject to policy constraints.

    Args:
        current_holdings: Current portfolio weights
        expected_returns: Expected returns for each ticker
        covariance_matrix: Covariance matrix (symmetric, positive semi-definite)
        ticker_list: Ordered list of tickers matching covariance matrix
        constraints: List of policy constraints to enforce
        turnover_limit: Maximum portfolio turnover (0-1)
        objective: Optimization objective (maximize_sharpe, minimize_tracking_error, maximize_return)

    Returns:
        OptimizationResult with optimized weights and trades
    """
    n = len(ticker_list)
    if n == 0:
        raise ValueError("Empty ticker list")
    
    # Validate covariance matrix
    if covariance_matrix.shape != (n, n):
        raise ValueError(f"Covariance matrix shape {covariance_matrix.shape} does not match ticker count {n}")
    
    # Ensure covariance matrix is positive semi-definite and well-conditioned
    # Add small regularization to diagonal to avoid numerical issues
    regularization = np.eye(n) * 1e-6
    covariance_matrix_reg = covariance_matrix + regularization
    
    # Check if matrix is symmetric (should be, but verify)
    if not np.allclose(covariance_matrix_reg, covariance_matrix_reg.T, atol=1e-6):
        LOGGER.warning("Covariance matrix is not symmetric, symmetrizing...")
        covariance_matrix_reg = (covariance_matrix_reg + covariance_matrix_reg.T) / 2
    
    # Ensure all eigenvalues are non-negative (positive semi-definite)
    eigenvalues = np.linalg.eigvals(covariance_matrix_reg)
    if np.any(eigenvalues < -1e-6):  # Allow small numerical errors
        LOGGER.warning(f"Negative eigenvalues detected (min: {np.min(eigenvalues)}), adjusting...")
        # Project to positive semi-definite cone
        w, v = np.linalg.eigh(covariance_matrix_reg)
        w = np.maximum(w, 1e-6)  # Set negative eigenvalues to small positive value
        covariance_matrix_reg = v @ np.diag(w) @ v.T

    # Initialize optimization variables
    weights = cp.Variable(n)

    # Convert to numpy arrays
    returns_vec = np.array([expected_returns.get(ticker, 0.0) for ticker in ticker_list])
    current_weights_vec = np.array([current_holdings.get(ticker, 0.0) for ticker in ticker_list])
    
    # Normalize current weights to ensure they sum to 1.0
    current_weight_sum = np.sum(current_weights_vec)
    if current_weight_sum > 0:
        current_weights_vec = current_weights_vec / current_weight_sum

    # Portfolio expected return
    portfolio_return = returns_vec @ weights

    # Portfolio variance (using regularized covariance matrix)
    portfolio_var = cp.quad_form(weights, covariance_matrix_reg)

    # Constraints list
    optimization_constraints = []

    # Constraint: weights sum to 1.0
    optimization_constraints.append(cp.sum(weights) == 1.0)

    # Constraint: no shorting
    optimization_constraints.append(weights >= 0.0)

    # Apply policy constraints
    policy_flags = []
    for constraint in constraints:
        if constraint.constraint_type == "allocation_cap":
            if constraint.dimension == "*":  # Universal cap on all positions
                if constraint.max_value is not None:
                    optimization_constraints.append(weights <= constraint.max_value)
                    policy_flags.append(f"Allocation cap: max {constraint.max_value*100:.1f}% per position")
            else:  # Specific ticker cap
                if constraint.dimension in ticker_list:
                    idx = ticker_list.index(constraint.dimension)
                    if constraint.max_value is not None:
                        optimization_constraints.append(weights[idx] <= constraint.max_value)

        elif constraint.constraint_type == "sector_limit":
            # For sector limits, we'd need sector mapping - simplified here
            if constraint.min_value is not None or constraint.max_value is not None:
                LOGGER.warning(f"Sector limit constraints require sector mapping (not implemented here)")

        elif constraint.constraint_type == "tracking_error":
            # Tracking error constraint would need benchmark weights
            LOGGER.warning(f"Tracking error constraint requires benchmark data")

    # Turnover limit
    if turnover_limit is not None:
        turnover = cp.sum(cp.abs(weights - current_weights_vec))
        optimization_constraints.append(turnover <= turnover_limit)
        policy_flags.append(f"Turnover limit: max {turnover_limit*100:.0f}%")

    # Objective function
    if objective == "maximize_sharpe":
        # Maximize Sharpe ratio = (return - risk_free_rate) / sqrt(variance)
        # This is a non-convex fractional program, so we need to reformulate it.
        # Approach 1: Use SOCP reformulation (works with ECOS/SCS but not OSQP)
        # Approach 2: Maximize return subject to risk budget (QP, works with OSQP)
        # Approach 3: Minimize variance subject to return target (QP, works with OSQP)
        
        risk_free_rate = 0.0  # Can be parameterized
        
        # We'll use Approach 2: Maximize excess return subject to risk constraint
        # This approximates Sharpe maximization and is convex (QP)
        # Set risk budget based on current portfolio variance
        current_portfolio_var = float(current_weights_vec @ covariance_matrix_reg @ current_weights_vec)
        
        # Calculate risk budget - allow improvement but don't be too restrictive
        if current_portfolio_var > 1e-6:
            # Allow variance reduction up to 80% of current, or increase up to 120%
            risk_budget = max(current_portfolio_var * 0.8, 1e-4)
            risk_ceiling = current_portfolio_var * 1.2  # Allow some increase
        else:
            # If current variance is very small, use a minimum based on average asset variance
            avg_var = float(np.mean(np.diag(covariance_matrix_reg)))
            risk_budget = max(avg_var * 0.1, 1e-4)
            risk_ceiling = max(avg_var * 0.5, risk_budget * 1.1)  # Ensure ceiling > budget
        
        # Ensure risk_ceiling > risk_budget (should always be true, but double-check)
        if risk_ceiling <= risk_budget:
            risk_ceiling = risk_budget * 1.5
        
        # Maximize excess return subject to risk budget
        objective_fn = cp.Maximize(portfolio_return - risk_free_rate)
        # Constrain variance to be within acceptable range (upper bound only for Sharpe-like optimization)
        optimization_constraints.append(portfolio_var <= risk_ceiling)
        
        policy_flags.append("Objective: Maximize Sharpe ratio (via risk-constrained return maximization)")
    elif objective == "minimize_tracking_error":
        # Would need benchmark weights
        objective_fn = cp.Minimize(portfolio_var)
        policy_flags.append("Objective: Minimize risk")
    elif objective == "maximize_return":
        objective_fn = cp.Maximize(portfolio_return)
        policy_flags.append("Objective: Maximize return")
    else:
        raise ValueError(f"Unknown objective: {objective}")

    # Solve optimization problem
    problem = cp.Problem(objective_fn, optimization_constraints)

    try:
        # Try OSQP first (good for QP problems)
        try:
            problem.solve(solver=cp.OSQP, verbose=False, warm_start=True)
            status = problem.status
        except Exception as solver_error:
            LOGGER.warning(f"OSQP solver failed: {solver_error}, trying ECOS...")
            # Try ECOS as fallback (handles more problem types)
            try:
                problem.solve(solver=cp.ECOS, verbose=False)
                status = problem.status
            except Exception as ecos_error:
                LOGGER.warning(f"ECOS solver failed: {ecos_error}, trying SCS...")
                # Try SCS as last resort
                problem.solve(solver=cp.SCS, verbose=False, max_iters=5000)
                status = problem.status
        
        iterations = 0  # Most solvers don't expose iteration count directly

        if status not in ["optimal", "optimal_inaccurate"]:
            LOGGER.warning(f"Optimization status: {status}, problem size: {n}x{n}")
            # Return error with more context
            return OptimizationResult(
                optimized_weights={},
                proposed_trades=[],
                objective_value=None,
                iterations=0,
                status=status,
                policy_flags=policy_flags + [f"Solver status: {status}"],
                metrics_before={},
                metrics_after={},
            )

        # Extract optimized weights
        if weights.value is None:
            LOGGER.error("Optimization solver returned None weights")
            return OptimizationResult(
                optimized_weights={},
                proposed_trades=[],
                objective_value=None,
                iterations=0,
                status="error",
                policy_flags=policy_flags + ["Solver returned None weights"],
                metrics_before={},
                metrics_after={},
            )
        
        optimized_weights_vec = np.array(weights.value)
        
        # Normalize weights to ensure they sum to 1.0 (handle numerical errors)
        weight_sum = np.sum(optimized_weights_vec)
        if abs(weight_sum - 1.0) > 1e-3:  # If significant difference
            if weight_sum > 0:
                optimized_weights_vec = optimized_weights_vec / weight_sum
            else:
                LOGGER.warning("Optimized weights sum to zero, using equal weights as fallback")
                optimized_weights_vec = np.ones(n) / n
        
        optimized_weights_dict = {ticker: float(w) for ticker, w in zip(ticker_list, optimized_weights_vec) if w > 1e-6}

        # Calculate metrics before/after
        metrics_before = {
            "expected_return": float(returns_vec @ current_weights_vec),
            "portfolio_variance": float(current_weights_vec @ covariance_matrix @ current_weights_vec),
            "num_positions": sum(1 for w in current_weights_vec if w > 1e-6),
        }

        metrics_after = {
            "expected_return": float(returns_vec @ optimized_weights_vec),
            "portfolio_variance": float(optimized_weights_vec @ covariance_matrix @ optimized_weights_vec),
            "num_positions": sum(1 for w in optimized_weights_vec if w > 1e-6),
        }

        # Calculate proposed trades
        proposed_trades = []
        for ticker in ticker_list:
            idx = ticker_list.index(ticker)
            current_wt = float(current_weights_vec[idx])
            new_wt = float(optimized_weights_vec[idx])

            if abs(new_wt - current_wt) > 1e-6:
                action = "buy" if new_wt > current_wt else "sell"
                proposed_trades.append(
                    {
                        "ticker": ticker,
                        "action": action,
                        "from_weight": current_wt,
                        "to_weight": new_wt,
                        "shares": None,  # Would need portfolio value to calculate
                    }
                )

        result = OptimizationResult(
            optimized_weights=optimized_weights_dict,
            proposed_trades=proposed_trades,
            objective_value=float(objective_fn.value) if objective_fn.value is not None else None,
            iterations=iterations,
            status=status,
            policy_flags=policy_flags,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
        )

        LOGGER.info(f"Optimization completed: {len(proposed_trades)} trades, status={status}")
        return result

    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        LOGGER.error(f"Optimization failed: {error_type}: {error_msg}", exc_info=True)
        
        # Provide more context in error message
        context_msg = f"{error_type}: {error_msg}"
        if "cvxpy" in error_msg.lower() or "solver" in error_msg.lower():
            context_msg += " (Solver issue - check if cvxpy and solvers are properly installed)"
        elif "dimension" in error_msg.lower() or "shape" in error_msg.lower():
            context_msg += f" (Dimension mismatch - matrix shape: {covariance_matrix.shape}, n: {n})"
        elif "singular" in error_msg.lower() or "invert" in error_msg.lower():
            context_msg += " (Numerical issue - covariance matrix may be singular or ill-conditioned)"
        
        return OptimizationResult(
            optimized_weights={},
            proposed_trades=[],
            objective_value=None,
            iterations=0,
            status="error",
            policy_flags=policy_flags + [context_msg],
            metrics_before={},
            metrics_after={},
        )


def optimize_portfolio_simple(
    current_holdings: Dict[str, float],
    expected_returns: Dict[str, float],
    risk_free_rate: float = 0.02,
    max_position_size: float = 0.12,
    turnover_limit: Optional[float] = None,
) -> Dict[str, float]:
    """
    Simplified optimization using scipy (no external solver required).

    For demonstration purposes when cvxpy is not available or desired.
    """
    n = len(current_holdings)
    if n == 0:
        return {}

    ticker_list = list(current_holdings.keys())
    current_weights_vec = np.array([current_holdings[ticker] for ticker in ticker_list])
    returns_vec = np.array([expected_returns.get(ticker, risk_free_rate) for ticker in ticker_list])

    # Objective: maximize mean-variance utility
    def objective(weights):
        portfolio_return = np.dot(returns_vec, weights)
        # Simple risk measure (could use actual variance)
        portfolio_risk = np.std(weights)
        return -(portfolio_return - 0.5 * portfolio_risk)  # Maximize utility

    # Constraints
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]  # Weights sum to 1

    # Bounds: no shorting, max position size
    bounds = [(0.0, max_position_size) for _ in range(n)]

    # Initial guess: current weights
    initial_guess = current_weights_vec.copy()

    try:
        result = sco.minimize(
            objective, initial_guess, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000}
        )

        if result.success:
            optimized_weights = {ticker: float(w) for ticker, w in zip(ticker_list, result.x) if w > 1e-6}
            LOGGER.info(f"Simple optimization completed: {len(optimized_weights)} positions")
            return optimized_weights
        else:
            LOGGER.warning(f"Simple optimization failed: {result.message}")
            return {}

    except Exception as e:
        LOGGER.error(f"Simple optimization error: {e}")
        return {}


def save_optimization_trades_to_database(
    database_path: database.Path,
    portfolio_id: str,
    optimization_result: OptimizationResult,
    trade_date: Optional[datetime] = None,
) -> None:
    """
    Save proposed optimization trades to database as transaction records.

    Marks trades as "proposed" (not executed) until user approves.
    """
    if trade_date is None:
        trade_date = datetime.now(timezone.utc)

    for trade in optimization_result.proposed_trades:
        transaction_id = str(uuid.uuid4())
        transaction = database.PortfolioTransactionRecord(
            transaction_id=transaction_id,
            portfolio_id=portfolio_id,
            ticker=trade["ticker"],
            trade_date=trade_date,
            action=f"{trade['action']}_proposed",
            shares=trade.get("shares"),
            price=None,
            commission=None,
            notes=f"Optimization result - {optimization_result.status}",
        )
        database.insert_portfolio_transaction(database_path, transaction)

    LOGGER.info(f"Saved {len(optimization_result.proposed_trades)} proposed trades for portfolio {portfolio_id}")



# ======================================================================
# ATTRIBUTION
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class AttributionResult:
    """Brinson attribution analysis result."""

    total_active_return: float
    allocation_effect: Dict[str, float]  # sector -> contribution
    selection_effect: Dict[str, float]  # sector -> contribution
    interaction_effect: Dict[str, float]  # sector -> contribution
    top_contributors: List[Dict[str, Any]]
    top_detractors: List[Dict[str, Any]]


def brinson_attribution(
    portfolio_weights: Dict[str, float],
    portfolio_returns: Dict[str, float],
    benchmark_weights: Dict[str, float],
    benchmark_returns: Dict[str, float],
    sectors: Dict[str, str],  # ticker -> sector
) -> AttributionResult:
    """
    Perform Brinson attribution analysis.

    Decomposes active return into:
    - Allocation effect: (portfolio_sector_wt - benchmark_sector_wt) × benchmark_sector_return
    - Selection effect: benchmark_sector_wt × (portfolio_return - benchmark_return)
    - Interaction effect: (portfolio_wt - benchmark_wt) × (portfolio_return - benchmark_return)

    Returns AttributionResult with breakdowns by sector.
    """
    # Calculate portfolio and benchmark returns
    portfolio_return = sum(portfolio_weights[ticker] * portfolio_returns.get(ticker, 0.0) for ticker in portfolio_weights)
    benchmark_return = sum(benchmark_weights[ticker] * benchmark_returns.get(ticker, 0.0) for ticker in benchmark_weights)

    total_active_return = portfolio_return - benchmark_return

    # Group by sector
    portfolio_sector_weights = defaultdict(float)
    portfolio_sector_returns = defaultdict(float)
    benchmark_sector_weights = defaultdict(float)
    benchmark_sector_returns = defaultdict(float)

    for ticker, sector in sectors.items():
        if ticker in portfolio_weights:
            weight = portfolio_weights[ticker]
            ret = portfolio_returns.get(ticker, 0.0)
            portfolio_sector_weights[sector] += weight
            portfolio_sector_returns[sector] += weight * ret

        if ticker in benchmark_weights:
            weight = benchmark_weights[ticker]
            ret = benchmark_returns.get(ticker, 0.0)
            benchmark_sector_weights[sector] += weight
            benchmark_sector_returns[sector] += weight * ret

    # Normalize sector returns (weighted average within sector)
    for sector in portfolio_sector_returns:
        if portfolio_sector_weights[sector] > 0:
            portfolio_sector_returns[sector] /= portfolio_sector_weights[sector]
    for sector in benchmark_sector_returns:
        if benchmark_sector_weights[sector] > 0:
            benchmark_sector_returns[sector] /= benchmark_sector_weights[sector]

    # Calculate attribution effects
    allocation_effect = {}
    selection_effect = {}
    interaction_effect = {}

    all_sectors = set(portfolio_sector_weights.keys()) | set(benchmark_sector_weights.keys())

    for sector in all_sectors:
        port_wt = portfolio_sector_weights.get(sector, 0.0)
        bmk_wt = benchmark_sector_weights.get(sector, 0.0)
        port_ret = portfolio_sector_returns.get(sector, 0.0)
        bmk_ret = benchmark_sector_returns.get(sector, 0.0)

        # Allocation effect
        allocation_effect[sector] = (port_wt - bmk_wt) * bmk_ret

        # Selection effect (security-level, not sector-level)
        selection_contribution = 0.0
        for ticker, ticker_sector in sectors.items():
            if ticker_sector == sector:
                port_wt_ticker = portfolio_weights.get(ticker, 0.0)
                bmk_wt_ticker = benchmark_weights.get(ticker, 0.0)
                port_ret_ticker = portfolio_returns.get(ticker, 0.0)
                bmk_ret_ticker = benchmark_returns.get(ticker, 0.0)
                selection_contribution += bmk_wt_ticker * (port_ret_ticker - bmk_ret_ticker)

        selection_effect[sector] = selection_contribution

        # Interaction effect (security-level)
        interaction_contribution = 0.0
        for ticker, ticker_sector in sectors.items():
            if ticker_sector == sector:
                port_wt_ticker = portfolio_weights.get(ticker, 0.0)
                bmk_wt_ticker = benchmark_weights.get(ticker, 0.0)
                port_ret_ticker = portfolio_returns.get(ticker, 0.0)
                bmk_ret_ticker = benchmark_returns.get(ticker, 0.0)
                interaction_contribution += (port_wt_ticker - bmk_wt_ticker) * (port_ret_ticker - bmk_ret_ticker)

        interaction_effect[sector] = interaction_contribution

    # Calculate total effects
    total_allocation = sum(allocation_effect.values())
    total_selection = sum(selection_effect.values())
    total_interaction = sum(interaction_effect.values())

    # Top contributors and detractors
    ticker_contributions = []
    for ticker in set(portfolio_weights.keys()) | set(benchmark_weights.keys()):
        port_wt = portfolio_weights.get(ticker, 0.0)
        bmk_wt = benchmark_weights.get(ticker, 0.0)
        port_ret = portfolio_returns.get(ticker, 0.0)
        bmk_ret = benchmark_returns.get(ticker, 0.0)

        contribution = port_wt * port_ret - bmk_wt * bmk_ret
        ticker_contributions.append({"ticker": ticker, "contribution": contribution})

    top_contributors = sorted(ticker_contributions, key=lambda x: x["contribution"], reverse=True)[:5]
    top_detractors = sorted(ticker_contributions, key=lambda x: x["contribution"])[:5]

    LOGGER.info(
        f"Brinson attribution: Active return={total_active_return:.2%}, Allocation={total_allocation:.2%}, "
        f"Selection={total_selection:.2%}, Interaction={total_interaction:.2%}"
    )

    return AttributionResult(
        total_active_return=total_active_return,
        allocation_effect=allocation_effect,
        selection_effect=selection_effect,
        interaction_effect=interaction_effect,
        top_contributors=top_contributors,
        top_detractors=top_detractors,
    )


def calculate_portfolio_return(weights: Dict[str, float], returns: Dict[str, float]) -> float:
    """Calculate portfolio return from weights and returns."""
    return sum(weights.get(ticker, 0.0) * returns.get(ticker, 0.0) for ticker in weights)


# ============================================================================
# Helper Functions for Advanced Features
# ============================================================================

def get_portfolio_holdings(database_path: Path, portfolio_id: str) -> List[Dict[str, Any]]:
    """
    Get portfolio holdings from database.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
    
    Returns:
        List of holding dictionaries with ticker, weight, shares, etc.
    """
    holdings = database.fetch_portfolio_holdings(database_path, portfolio_id)
    
    result = []
    for holding in holdings:
        result.append({
            'ticker': holding.ticker,
            'weight': holding.weight,
            'shares': holding.shares,
            'price': None,  # Would need to calculate from market_value / shares
            'market_value': holding.market_value,
            'cost_basis': holding.cost_basis,
            'currency': holding.currency,
            'account_id': holding.account_id
        })
    
    return result


def get_portfolio(database_path: Path, portfolio_id: str) -> Dict[str, Any]:
    """
    Get portfolio metadata from database.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
    
    Returns:
        Portfolio metadata dictionary
    """
    metadata = database.fetch_portfolio_metadata(database_path, portfolio_id)
    
    if not metadata:
        raise PortfolioNotFoundError(portfolio_id)
    
    return {
        'portfolio_id': metadata.portfolio_id,
        'name': metadata.name,
        'base_currency': metadata.base_currency,
        'benchmark_index': metadata.benchmark_index,
        'strategy_type': metadata.strategy_type,
        'inception_date': metadata.inception_date,
        'created_at': metadata.created_at
    }


def get_portfolio_returns(database_path: Path, portfolio_id: str, lookback_days: int = 252) -> pd.Series:
    """
    Get portfolio historical returns.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        lookback_days: Number of days to look back
    
    Returns:
        Pandas Series of portfolio returns
    """
    holdings = get_portfolio_holdings(database_path, portfolio_id)
    ticker_list = [h['ticker'] for h in holdings]
    weights = {h['ticker']: h['weight'] / 100.0 if h['weight'] else 0.0 for h in holdings}
    
    # Get historical prices for all tickers
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=lookback_days)
    
    returns_data = {}
    for ticker in ticker_list:
        prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
        if len(prices) >= 2:
            price_values = [p[1] for p in prices]
            ticker_returns = np.diff(price_values) / price_values[:-1]
            dates = [p[0] for p in prices[1:]]
            returns_data[ticker] = pd.Series(ticker_returns, index=dates)
    
    if not returns_data:
        return pd.Series([], dtype=float)
    
    # Combine returns into DataFrame
    returns_df = pd.DataFrame(returns_data)
    
    # Calculate portfolio returns
    portfolio_returns = pd.Series(index=returns_df.index, dtype=float)
    for date in returns_df.index:
        portfolio_return = sum(
            weights.get(ticker, 0.0) * returns_df.loc[date, ticker]
            for ticker in ticker_list
            if ticker in returns_df.columns and not pd.isna(returns_df.loc[date, ticker])
        )
        portfolio_returns[date] = portfolio_return
    
    return portfolio_returns


def get_benchmark_returns(database_path: Path, benchmark_id: str = "sp500", lookback_days: int = 252) -> pd.Series:
    """
    Get benchmark historical returns.
    
    Args:
        database_path: Path to database
        benchmark_id: Benchmark identifier (default: "sp500")
        lookback_days: Number of days to look back
    
    Returns:
        Pandas Series of benchmark returns
    """
    if benchmark_id.lower() == "sp500":
        # Use SPY as proxy for S&P 500
        benchmark_ticker = "SPY"
    else:
        benchmark_ticker = benchmark_id
    
    # Get historical prices for benchmark
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=lookback_days)
    
    prices = fetch_historical_prices(database_path, benchmark_ticker, start_date, end_date)
    
    if len(prices) < 2:
        LOGGER.warning(f"Insufficient data for benchmark {benchmark_ticker}")
        return pd.Series([], dtype=float)
    
    price_values = [p[1] for p in prices]
    returns = np.diff(price_values) / price_values[:-1]
    dates = [p[0] for p in prices[1:]]
    
    return pd.Series(returns, index=dates)


def calculate_portfolio_beta(database_path: Path, portfolio_id: str, benchmark: str = "SPY", lookback_days: int = 252) -> float:
    """
    Calculate portfolio beta vs benchmark.
    
    Args:
        database_path: Path to database
        portfolio_id: Portfolio ID
        benchmark: Benchmark ticker (default: SPY)
        lookback_days: Number of days to look back
    
    Returns:
        Portfolio beta
    """
    portfolio_returns = get_portfolio_returns(database_path, portfolio_id, lookback_days)
    benchmark_returns = get_benchmark_returns(database_path, benchmark, lookback_days)
    
    # Align dates
    common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
    if len(common_dates) < 20:
        LOGGER.warning(f"Insufficient overlapping data for beta calculation: {len(common_dates)} days")
        return 1.0  # Default to market beta
    
    portfolio_aligned = portfolio_returns.loc[common_dates]
    benchmark_aligned = benchmark_returns.loc[common_dates]
    
    # Calculate beta using covariance
    covariance = np.cov(portfolio_aligned, benchmark_aligned)[0, 1]
    benchmark_variance = np.var(benchmark_aligned)
    
    if benchmark_variance == 0:
        return 1.0
    
    beta = covariance / benchmark_variance
    return float(beta)


def get_historical_returns(database_path: Path, ticker_list: List[str], periods: int = 252) -> pd.DataFrame:
    """
    Get historical returns for multiple tickers.
    
    Args:
        database_path: Path to database
        ticker_list: List of tickers
        periods: Number of periods (trading days) to retrieve
    
    Returns:
        DataFrame with columns for each ticker and rows for each date
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=periods * 2)  # Get more data to ensure we have enough
    
    returns_data = {}
    
    for ticker in ticker_list:
        prices = fetch_historical_prices(database_path, ticker, start_date, end_date)
        if len(prices) >= 2:
            price_values = [p[1] for p in prices]
            ticker_returns = np.diff(price_values) / price_values[:-1]
            dates = [p[0] for p in prices[1:]]
            returns_data[ticker] = pd.Series(ticker_returns, index=dates)
    
    if not returns_data:
        return pd.DataFrame()
    
    # Combine into DataFrame
    returns_df = pd.DataFrame(returns_data)
    
    # Take last N periods
    if len(returns_df) > periods:
        returns_df = returns_df.tail(periods)
    
    return returns_df


def format_attribution_table(attribution: AttributionResult) -> str:
    """Format attribution result as readable table."""
    lines = ["\nPerformance Attribution Analysis", "=" * 60]

    lines.append(f"\nTotal Active Return: {attribution.total_active_return:.2%}")
    lines.append("\nBy Sector:")

    all_sectors = set(attribution.allocation_effect.keys()) | set(attribution.selection_effect.keys())

    lines.append(f"{'Sector':30s} {'Allocation':>12s} {'Selection':>12s} {'Interaction':>12s}")
    lines.append("-" * 66)

    for sector in sorted(all_sectors):
        alloc = attribution.allocation_effect.get(sector, 0.0)
        select = attribution.selection_effect.get(sector, 0.0)
        interact = attribution.interaction_effect.get(sector, 0.0)
        lines.append(f"{sector:30s} {alloc:12.2%} {select:12.2%} {interact:12.2%}")

    # Totals
    total_alloc = sum(attribution.allocation_effect.values())
    total_select = sum(attribution.selection_effect.values())
    total_interact = sum(attribution.interaction_effect.values())
    lines.append("-" * 66)
    lines.append(f"{'TOTAL':30s} {total_alloc:12.2%} {total_select:12.2%} {total_interact:12.2%}")

    # Top contributors/detractors
    lines.append("\nTop Contributors:")
    for i, item in enumerate(attribution.top_contributors[:5], 1):
        lines.append(f"  {i}. {item['ticker']:10s}: {item['contribution']:+.2%}")

    lines.append("\nTop Detractors:")
    for i, item in enumerate(attribution.top_detractors[:5], 1):
        lines.append(f"  {i}. {item['ticker']:10s}: {item['contribution']:+.2%}")

    return "\n".join(lines)



# ======================================================================
# SCENARIOS
# ======================================================================


LOGGER = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of portfolio scenario analysis."""

    portfolio_value_change: float  # absolute change
    portfolio_return: float  # percentage return
    pnl_attribution: Dict[str, float]  # component -> contribution
    top_gainers: List[Dict[str, Any]]
    top_losers: List[Dict[str, Any]]
    risk_metrics: Dict[str, float]  # VaR, CVaR, max drawdown, etc.


def run_equity_drawdown_scenario(
    holdings: Dict[str, float],  # ticker -> weight
    betas: Dict[str, float],
    drawdown_pct: float,  # e.g., -0.20 for 20% market decline
) -> ScenarioResult:
    """
    Run equity drawdown scenario.

    Applies beta-adjusted returns to portfolio holdings.
    """
    if drawdown_pct >= 0:
        LOGGER.warning("Drawdown should be negative (e.g., -0.20 for 20% decline)")

    ticker_returns = {}
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        beta = betas.get(ticker, 1.0)  # Default beta = 1.0
        ticker_return = drawdown_pct * beta  # Beta-adjusted return
        ticker_returns[ticker] = ticker_return
        ticker_pnl[ticker] = weight * ticker_return

    # Calculate portfolio impact
    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return  # Weighted by portfolio value

    # Attribution by rate/equity component
    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    # Top gainers/losers
    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    # Risk metrics
    risk_metrics = {
        "portfolio_drawdown": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    LOGGER.info(f"Equity drawdown scenario: portfolio return={portfolio_return:.2%}")

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_sector_rotation_scenario(
    holdings: Dict[str, float],
    ticker_sectors: Dict[str, str],
    sector_shifts: Dict[str, float],  # sector -> return %
) -> ScenarioResult:
    """
    Run sector rotation scenario.

    Applies sector-specific return shocks to portfolio.
    """
    ticker_returns = {}
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        sector = ticker_sectors.get(ticker, "Unknown")
        sector_return = sector_shifts.get(sector, 0.0)
        ticker_returns[ticker] = sector_return
        ticker_pnl[ticker] = weight * sector_return

    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return

    # Attribution
    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    risk_metrics = {
        "portfolio_return": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    LOGGER.info(f"Sector rotation scenario: portfolio return={portfolio_return:.2%}")

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_custom_scenario(
    holdings: Dict[str, float],
    custom_returns: Dict[str, float],  # ticker -> return %
) -> ScenarioResult:
    """
    Run custom scenario with user-provided return assumptions.

    Returns scenario result with portfolio impact.
    """
    ticker_pnl = {}

    for ticker, weight in holdings.items():
        return_pct = custom_returns.get(ticker, 0.0)
        ticker_pnl[ticker] = weight * return_pct

    portfolio_return = sum(ticker_pnl.values())
    portfolio_value_change = portfolio_return

    pnl_attribution = {"equity": portfolio_return, "rate": 0.0, "spread": 0.0, "fx": 0.0, "residual": 0.0}

    sorted_impacts = sorted(ticker_pnl.items(), key=lambda x: x[1])
    top_losers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[:5]]
    top_gainers = [{"ticker": t, "impact": impact} for t, impact in sorted_impacts[-5:]][::-1]

    risk_metrics = {
        "portfolio_return": portfolio_return,
        "max_holding_loss": min(ticker_pnl.values()) if ticker_pnl else 0.0,
    }

    return ScenarioResult(
        portfolio_value_change=portfolio_value_change,
        portfolio_return=portfolio_return,
        pnl_attribution=pnl_attribution,
        top_gainers=top_gainers,
        top_losers=top_losers,
        risk_metrics=risk_metrics,
    )


def run_multiple_scenarios(
    holdings: Dict[str, float],
    scenarios: Dict[str, Any],  # scenario_name -> parameters
    ticker_betas: Optional[Dict[str, float]] = None,
    ticker_sectors: Optional[Dict[str, str]] = None,
) -> Dict[str, ScenarioResult]:
    """
    Run multiple scenarios and compare results.

    Returns dict of scenario_name -> ScenarioResult.
    """
    results = {}

    for scenario_name, params in scenarios.items():
        scenario_type = params.get("type")
        parameters = params.get("parameters", {})

        if scenario_type == "equity_drawdown":
            betas = ticker_betas or {}
            drawdown = parameters.get("drawdown_pct", -0.20)
            results[scenario_name] = run_equity_drawdown_scenario(holdings, betas, drawdown)

        elif scenario_type == "sector_rotation":
            sectors = ticker_sectors or {}
            shifts = parameters.get("sector_shifts", {})
            results[scenario_name] = run_sector_rotation_scenario(holdings, sectors, shifts)

        elif scenario_type == "custom":
            custom_returns = parameters.get("returns", {})
            results[scenario_name] = run_custom_scenario(holdings, custom_returns)

        else:
            LOGGER.warning(f"Unknown scenario type: {scenario_type}")

    LOGGER.info(f"Ran {len(results)} scenarios")
    return results


def format_scenario_results(scenario_results: Dict[str, ScenarioResult]) -> str:
    """Format multiple scenario results as table."""
    lines = ["\nScenario Analysis Results", "=" * 70]
    lines.append(f"{'Scenario':30s} {'Portfolio Return':>15s} {'Value Impact':>15s}")
    lines.append("-" * 60)

    for name, result in scenario_results.items():
        lines.append(f"{name:30s} {result.portfolio_return:15.2%} {result.portfolio_value_change:15.2%}")

    return "\n".join(lines)



# ======================================================================
# REPORTING
# ======================================================================


@dataclass
class CommitteeBrief:
    """Auto-generated committee brief for meeting agendas."""

    insights: List[str]
    key_metrics: Dict[str, Any]
    recommendations: List[str]


def generate_committee_brief(
    portfolio_name: str,
    attribution_result: Optional[AttributionResult] = None,
    optimization_result: Optional[OptimizationResult] = None,
    scenario_results: Optional[Dict[str, ScenarioResult]] = None,
    policy_violations: Optional[List[Dict[str, Any]]] = None,
) -> CommitteeBrief:
    """
    Generate 3-5 key insights for investment committee meeting agenda.

    Creates natural language summaries from attribution, optimization, and scenario analysis.
    """
    insights = []
    key_metrics = {}
    recommendations = []

    # Attribution insights
    if attribution_result:
        active_return = attribution_result.total_active_return
        if active_return > 0.005:  # >0.5%
            insights.append(f"Portfolio outperformed benchmark by {active_return*100:.1f} bps this period.")

            # Identify main driver
            total_allocation = sum(attribution_result.allocation_effect.values())
            total_selection = sum(attribution_result.selection_effect.values())

            if abs(total_allocation) > abs(total_selection):
                insights.append(f"Outperformance driven primarily by allocation effect (+{total_allocation*100:.1f} bps).")
            else:
                insights.append(f"Outperformance driven primarily by security selection (+{total_selection*100:.1f} bps).")

            # Top contributor
            if attribution_result.top_contributors:
                top_contrib = attribution_result.top_contributors[0]
                insights.append(
                    f"Top contributor: {top_contrib['ticker']} added {abs(top_contrib['contribution'])*100:.1f} bps to returns."
                )

        elif active_return < -0.005:  # Underperformance
            insights.append(f"Portfolio underperformed benchmark by {abs(active_return)*100:.1f} bps this period.")

        # Key metrics
        key_metrics["active_return"] = active_return
        key_metrics["allocation_effect"] = sum(attribution_result.allocation_effect.values())
        key_metrics["selection_effect"] = sum(attribution_result.selection_effect.values())

    # Optimization insights
    if optimization_result:
        num_trades = len(optimization_result.proposed_trades)
        if num_trades > 0:
            insights.append(f"Proposed rebalance: {num_trades} trades recommended to optimize portfolio efficiency.")

            # Expected improvement
            if optimization_result.metrics_before and optimization_result.metrics_after:
                before_ret = optimization_result.metrics_before.get("expected_return", 0)
                after_ret = optimization_result.metrics_after.get("expected_return", 0)
                if after_ret > before_ret:
                    improvement = (after_ret - before_ret) * 100
                    recommendations.append(f"Expected return improvement of {improvement:.1f} bps from optimization.")

            # Policy flags
            if optimization_result.policy_flags:
                recommendations.append(f"All proposed trades respect policy constraints: {len(optimization_result.policy_flags)} limits applied.")

    # Policy violations
    if policy_violations:
        num_violations = len(policy_violations)
        insights.append(f"⚠️ Policy violations detected: {num_violations} constraints breached requiring immediate action.")
        recommendations.append("Review and rebalance portfolio to restore policy compliance.")

    # Scenario analysis
    if scenario_results:
        bear_result = scenario_results.get("Bear")
        if bear_result:
            bear_return = bear_result.portfolio_return
            if bear_return < -0.10:  # -10% or worse
                insights.append(f"Stress test: portfolio would decline {abs(bear_return)*100:.0f}% in bear market scenario.")

    # Default if no insights
    if not insights:
        insights.append(f"Portfolio performance in-line with benchmark.")
        insights.append("No policy violations or required actions.")

    LOGGER.info(f"Generated committee brief with {len(insights)} insights for {portfolio_name}")

    return CommitteeBrief(insights=insights, key_metrics=key_metrics, recommendations=recommendations)


def generate_optimization_summary(optimization_result: OptimizationResult) -> str:
    """
    Generate narrative explaining proposed optimization trades.

    Returns natural language summary for user review.
    """
    lines = []

    num_trades = len(optimization_result.proposed_trades)
    if num_trades == 0:
        return "No trades recommended. Current portfolio is already optimal within constraints."

    lines.append(f"Proposed Optimization Summary ({optimization_result.status}):")
    lines.append(f"\n{num_trades} trades recommended to improve portfolio efficiency.")

    # Key changes
    buy_trades = [t for t in optimization_result.proposed_trades if t["action"] == "buy"]
    sell_trades = [t for t in optimization_result.proposed_trades if t["action"] == "sell"]

    if buy_trades:
        top_buy = sorted(buy_trades, key=lambda t: t["to_weight"], reverse=True)[0]
        lines.append(f"Largest addition: {top_buy['ticker']} +{top_buy['to_weight']*100:.1f}% weight")
    if sell_trades:
        top_sell = sorted(sell_trades, key=lambda t: t["from_weight"], reverse=True)[0]
        lines.append(f"Largest reduction: {top_sell['ticker']} -{top_sell['from_weight']*100:.1f}% weight")

    # Expected impact
    if optimization_result.metrics_before and optimization_result.metrics_after:
        before_ret = optimization_result.metrics_before.get("expected_return", 0)
        after_ret = optimization_result.metrics_after.get("expected_return", 0)
        before_var = optimization_result.metrics_before.get("portfolio_variance", 0)
        after_var = optimization_result.metrics_after.get("portfolio_variance", 0)

        lines.append(f"\nExpected Impact:")
        lines.append(f"  Return: {before_ret:.2%} → {after_ret:.2%} ({'+' if after_ret >= before_ret else ''}{(after_ret-before_ret)*100:.2f} bps)")

        if before_var > 0 and after_var > 0:
            risk_change = ((after_var**0.5 / before_var**0.5) - 1) * 100
            lines.append(f"  Risk: {before_var**0.5:.2%} → {after_var**0.5:.2%} ({'+' if risk_change >= 0 else ''}{risk_change:.1f}%)")

    # Constraints respected
    if optimization_result.policy_flags:
        lines.append(f"\nConstraints Applied:")
        for flag in optimization_result.policy_flags:
            lines.append(f"  • {flag}")

    return "\n".join(lines)


def generate_attribution_narrative(attribution: AttributionResult, period: str = "Q4 2024") -> str:
    """
    Generate natural language explanation of attribution results.

    Returns narrative describing allocation, selection, and interaction effects.
    """
    lines = []

    lines.append(f"Performance Attribution for {period}:")
    lines.append(f"\nTotal Active Return: {attribution.total_active_return:+.2%}")

    # Decompose by effect
    total_alloc = sum(attribution.allocation_effect.values())
    total_select = sum(attribution.selection_effect.values())
    total_interact = sum(attribution.interaction_effect.values())

    lines.append("\nDecomposition:")
    if abs(total_alloc) > 0.0001:
        lines.append(f"  • Allocation effect: {total_alloc:+.2%} (sector over/underweights)")
    if abs(total_select) > 0.0001:
        lines.append(f"  • Selection effect: {total_select:+.2%} (security selection within sectors)")
    if abs(total_interact) > 0.0001:
        lines.append(f"  • Interaction effect: {total_interact:+.2%} (combined effect)")

    # Top contributors/detractors
    if attribution.top_contributors:
        lines.append("\nTop Contributors:")
        for i, item in enumerate(attribution.top_contributors[:3], 1):
            lines.append(f"  {i}. {item['ticker']}: {item['contribution']:+.2%}")

    if attribution.top_detractors:
        lines.append("\nTop Detractors:")
        for i, item in enumerate(attribution.top_detractors[:3], 1):
            if item['contribution'] < -0.0001:
                lines.append(f"  {i}. {item['ticker']}: {item['contribution']:+.2%}")

    return "\n".join(lines)


def format_committee_brief(brief: CommitteeBrief) -> str:
    """Format committee brief as markdown-ready text."""
    lines = ["## Investment Committee Brief", ""]

    lines.append("### Key Insights")
    for i, insight in enumerate(brief.insights, 1):
        lines.append(f"{i}. {insight}")

    if brief.key_metrics:
        lines.append("\n### Performance Metrics")
        for key, value in brief.key_metrics.items():
            if isinstance(value, float):
                lines.append(f"- {key.replace('_', ' ').title()}: {value:+.2%}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    if brief.recommendations:
        lines.append("\n### Recommendations")
        for i, rec in enumerate(brief.recommendations, 1):
            lines.append(f"{i}. {rec}")

    return "\n".join(lines)


def generate_portfolio_summary(
    portfolio_name: str,
    num_holdings: int,
    total_value: float,
    sector_exposure: Dict[str, float],
    top_holdings: List[Dict[str, Any]],
) -> str:
    """Generate executive summary of portfolio composition."""
    lines = [f"## {portfolio_name} - Portfolio Summary"]

    lines.append(f"\nPortfolio value: ${total_value:,.0f}")
    lines.append(f"Number of holdings: {num_holdings}")
    lines.append(f"Sectors: {len(sector_exposure)}")

    # Top sectors
    lines.append("\nTop Sectors:")
    sorted_sectors = sorted(sector_exposure.items(), key=lambda x: x[1], reverse=True)
    for sector, weight in sorted_sectors[:5]:
        lines.append(f"  • {sector}: {weight*100:.1f}%")

    # Top holdings
    if top_holdings:
        lines.append("\nTop Holdings:")
        for i, holding in enumerate(top_holdings[:10], 1):
            ticker = holding.get("ticker", "?")
            weight = holding.get("weight", 0)
            lines.append(f"  {i:2d}. {ticker:10s}: {weight*100:5.1f}%")

    return "\n".join(lines)

