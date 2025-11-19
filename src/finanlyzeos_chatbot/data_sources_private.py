"""Custom data source client for private companies and proprietary APIs.

This module provides a template for integrating proprietary APIs that provide
financial data for private companies. Modify the PrivateCompanyClient class
to match your specific API structure.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import requests

from .data_sources import FinancialFact, _parse_datetime, _parse_date

LOGGER = logging.getLogger(__name__)


class PrivateCompanyClient:
    """Client for proprietary private company data API.
    
    This is a template implementation. Modify the methods to match your
    specific API structure and authentication requirements.
    """
    
    def __init__(
        self,
        *,
        base_url: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: float = 30.0,
        min_interval: float = 0.1,  # Rate limiting
        session: Optional[requests.Session] = None,
    ):
        """Initialize the client with API credentials and settings.
        
        Args:
            base_url: Base URL of your proprietary API
            api_key: API key for authentication (if required)
            api_secret: API secret for authentication (if required)
            timeout: HTTP request timeout in seconds
            min_interval: Minimum seconds between API calls (rate limiting)
            session: Optional requests.Session for connection pooling
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.min_interval = min_interval
        self.session = session or requests.Session()
        self._last_request = 0.0
    
    def _headers(self) -> Dict[str, str]:
        """Return HTTP headers required for API requests.
        
        Modify this method to match your API's authentication requirements.
        Common patterns:
        - Bearer token: {"Authorization": f"Bearer {self.api_key}"}
        - API key header: {"X-API-Key": self.api_key}
        - Basic auth: Use requests.auth.HTTPBasicAuth
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            # Example: Bearer token authentication
            headers["Authorization"] = f"Bearer {self.api_key}"
            # Alternative: API key in header
            # headers["X-API-Key"] = self.api_key
        
        return headers
    
    def _maybe_throttle(self) -> None:
        """Sleep when necessary to respect upstream rate limits."""
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
    
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform an HTTP request and return JSON response.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path (e.g., "/companies/123/financials")
            params: URL query parameters
            json: JSON request body (for POST/PUT)
        
        Returns:
            Parsed JSON response
        
        Raises:
            requests.HTTPError: If the API returns an error status
        """
        self._maybe_throttle()
        url = f"{self.base_url}{path}"
        
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._last_request = time.monotonic()
            return response.json()
        except requests.HTTPError as exc:
            LOGGER.error(
                "Private API request failed: %s %s -> %s",
                method,
                path,
                exc.response.status_code if exc.response else "unknown",
            )
            raise
        except Exception as exc:
            LOGGER.error("Private API request error: %s", exc)
            raise
    
    def list_companies(self) -> List[Dict[str, Any]]:
        """List all available private companies.
        
        Returns:
            List of company dictionaries with at least:
            - company_id: Unique identifier
            - name: Company name
            - industry: Optional industry classification
        """
        # Example implementation - modify to match your API
        data = self._request("GET", "/companies")
        return data.get("companies", [])
    
    def get_company_metadata(self, company_id: str) -> Dict[str, Any]:
        """Fetch metadata for a specific company.
        
        Args:
            company_id: Unique company identifier
        
        Returns:
            Company metadata dictionary
        """
        # Example implementation - modify to match your API
        return self._request("GET", f"/companies/{company_id}")
    
    def fetch_company_financials(
        self,
        company_id: str,
        *,
        years: int = 10,
        metrics: Optional[Sequence[str]] = None,
    ) -> List[FinancialFact]:
        """Fetch financial data for a private company.
        
        This method fetches financial data from your API and normalizes it
        into the FinancialFact format used by the chatbot.
        
        Args:
            company_id: Unique company identifier
            years: Number of years of historical data to fetch
            metrics: Optional list of specific metrics to fetch
        
        Returns:
            List of FinancialFact objects ready for database storage
        
        Example API Response Format:
        {
            "company_id": "PRIV-001",
            "name": "Acme Corporation",
            "periods": [
                {
                    "year": 2023,
                    "period": "FY",
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31",
                    "revenue": 50000000,
                    "net_income": 5000000,
                    "total_assets": 100000000,
                    "total_liabilities": 60000000,
                    "cash": 10000000,
                    # ... other metrics
                }
            ]
        }
        """
        # Fetch data from your API
        cutoff_year = datetime.now(timezone.utc).year - years + 1
        params = {
            "years": years,
            "start_year": cutoff_year,
        }
        if metrics:
            params["metrics"] = ",".join(metrics)
        
        data = self._request("GET", f"/companies/{company_id}/financials", params=params)
        
        company_name = data.get("name", company_id)
        periods = data.get("periods", [])
        
        # Map API response to FinancialFact format
        facts: List[FinancialFact] = []
        
        # Define metric mappings from your API to standard metric names
        # Modify this mapping to match your API's field names
        METRIC_MAPPING = {
            "revenue": "revenue",
            "net_income": "net_income",
            "operating_income": "operating_income",
            "ebitda": "ebitda",
            "total_assets": "total_assets",
            "total_liabilities": "total_liabilities",
            "shareholders_equity": "shareholders_equity",
            "cash": "cash_and_cash_equivalents",
            "cash_from_operations": "cash_from_operations",
            "capital_expenditures": "capital_expenditures",
            # Add more mappings as needed
        }
        
        for period_data in periods:
            fiscal_year = period_data.get("year")
            if fiscal_year and fiscal_year < cutoff_year:
                continue
            
            fiscal_period = period_data.get("period", "FY")
            period_start = _parse_datetime(period_data.get("start_date")) or _parse_date(
                period_data.get("start_date")
            )
            period_end = _parse_datetime(period_data.get("end_date")) or _parse_date(
                period_data.get("end_date")
            )
            
            # Create a FinancialFact for each metric in the period
            for api_field, metric_name in METRIC_MAPPING.items():
                value = period_data.get(api_field)
                if value is None:
                    continue
                
                # Convert to float if needed
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    continue
                
                # Generate period label
                if fiscal_period.upper() not in {"FY", "CY"}:
                    period_label = f"FY{fiscal_year}{fiscal_period.upper()}"
                else:
                    period_label = f"FY{fiscal_year}"
                
                fact = FinancialFact(
                    cik="",  # Not applicable for private companies
                    ticker=company_id,  # Use company_id as ticker
                    company_name=company_name,
                    metric=metric_name,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    period=period_label,
                    value=numeric_value,
                    unit="USD",  # Adjust if your API uses different currencies
                    source="private_api",
                    source_filing=None,  # Private companies don't have SEC filings
                    period_start=period_start,
                    period_end=period_end,
                    adjusted=False,
                    adjustment_note=None,
                    ingested_at=datetime.now(timezone.utc),
                    raw=period_data,  # Store raw API response for reference
                )
                facts.append(fact)
        
        return facts
    
    def fetch_company_quotes(
        self,
        company_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch current valuation/quote data for a private company.
        
        Private companies may have:
        - Last funding round valuation
        - Estimated valuation
        - Revenue multiples
        - Other valuation metrics
        
        Returns:
            Dictionary with quote-like data, or None if not available
        """
        try:
            data = self._request("GET", f"/companies/{company_id}/valuation")
            return data
        except requests.HTTPError:
            # Valuation data may not be available for all companies
            return None


def create_private_company_client(settings) -> Optional[PrivateCompanyClient]:
    """Factory function to create a PrivateCompanyClient from settings.
    
    Args:
        settings: Application Settings object
    
    Returns:
        PrivateCompanyClient instance if configured, None otherwise
    """
    # Check if private companies are enabled
    if not getattr(settings, "enable_private_companies", False):
        return None
    
    api_url = getattr(settings, "private_api_url", None)
    if not api_url:
        LOGGER.warning("Private companies enabled but PRIVATE_API_URL not set")
        return None
    
    api_key = getattr(settings, "private_api_key", None)
    api_secret = getattr(settings, "private_api_secret", None)
    timeout = getattr(settings, "private_api_timeout", 30.0)
    
    return PrivateCompanyClient(
        base_url=api_url,
        api_key=api_key,
        api_secret=api_secret,
        timeout=timeout,
    )

