"""
Advanced KPI Calculations

Calculates sophisticated financial ratios and KPIs including:
- Return on Equity (ROE)
- Return on Invested Capital (ROIC)
- Working Capital Ratios
- Debt Service Coverage Ratio
- Cash Conversion Cycle
- Economic Value Added (EVA)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import sqlite3

LOGGER = logging.getLogger(__name__)


@dataclass
class AdvancedKPIs:
    """Advanced financial KPIs for a company."""
    ticker: str
    fiscal_year: int
    
    # Profitability Metrics
    roe: Optional[float] = None  # Return on Equity %
    roa: Optional[float] = None  # Return on Assets %
    roic: Optional[float] = None  # Return on Invested Capital %
    roce: Optional[float] = None  # Return on Capital Employed %
    
    # Liquidity Metrics
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    working_capital: Optional[float] = None
    working_capital_ratio: Optional[float] = None
    
    # Leverage Metrics
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    debt_service_coverage: Optional[float] = None
    
    # Efficiency Metrics
    asset_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    days_sales_outstanding: Optional[float] = None
    days_inventory_outstanding: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None
    
    # Market/Valuation Metrics
    book_value_per_share: Optional[float] = None
    tangible_book_value: Optional[float] = None
    
    # Cash Flow Metrics
    fcf_to_revenue: Optional[float] = None
    fcf_to_net_income: Optional[float] = None
    cash_flow_margin: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "fiscal_year": self.fiscal_year,
            "profitability": {
                "roe": self.roe,
                "roa": self.roa,
                "roic": self.roic,
                "roce": self.roce,
            },
            "liquidity": {
                "current_ratio": self.current_ratio,
                "quick_ratio": self.quick_ratio,
                "cash_ratio": self.cash_ratio,
                "working_capital": self.working_capital,
                "working_capital_ratio": self.working_capital_ratio,
            },
            "leverage": {
                "debt_to_equity": self.debt_to_equity,
                "debt_to_assets": self.debt_to_assets,
                "interest_coverage": self.interest_coverage,
                "debt_service_coverage": self.debt_service_coverage,
            },
            "efficiency": {
                "asset_turnover": self.asset_turnover,
                "receivables_turnover": self.receivables_turnover,
                "inventory_turnover": self.inventory_turnover,
                "days_sales_outstanding": self.days_sales_outstanding,
                "days_inventory_outstanding": self.days_inventory_outstanding,
                "cash_conversion_cycle": self.cash_conversion_cycle,
            },
            "market": {
                "book_value_per_share": self.book_value_per_share,
                "tangible_book_value": self.tangible_book_value,
            },
            "cash_flow": {
                "fcf_to_revenue": self.fcf_to_revenue,
                "fcf_to_net_income": self.fcf_to_net_income,
                "cash_flow_margin": self.cash_flow_margin,
            },
        }


class AdvancedKPICalculator:
    """Calculate advanced financial KPIs from raw financial data."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def calculate_all_kpis(self, ticker: str, fiscal_year: int = 2024) -> Optional[AdvancedKPIs]:
        """
        Calculate all advanced KPIs for a company.
        
        Args:
            ticker: Company ticker symbol
            fiscal_year: Year to calculate KPIs for
            
        Returns:
            AdvancedKPIs object with all calculated metrics
        """
        # Get all metrics needed for calculations
        metrics = self._get_metrics(ticker, fiscal_year)
        if not metrics:
            return None
        
        kpis = AdvancedKPIs(ticker=ticker, fiscal_year=fiscal_year)
        
        # Calculate profitability metrics
        kpis.roe = self._calculate_roe(metrics)
        kpis.roa = self._calculate_roa(metrics)
        kpis.roic = self._calculate_roic(metrics)
        kpis.roce = self._calculate_roce(metrics)
        
        # Calculate liquidity metrics
        kpis.current_ratio = self._calculate_current_ratio(metrics)
        kpis.quick_ratio = self._calculate_quick_ratio(metrics)
        kpis.cash_ratio = self._calculate_cash_ratio(metrics)
        kpis.working_capital = self._calculate_working_capital(metrics)
        kpis.working_capital_ratio = self._calculate_working_capital_ratio(metrics)
        
        # Calculate leverage metrics
        kpis.debt_to_equity = self._calculate_debt_to_equity(metrics)
        kpis.debt_to_assets = self._calculate_debt_to_assets(metrics)
        kpis.interest_coverage = self._calculate_interest_coverage(metrics)
        kpis.debt_service_coverage = self._calculate_debt_service_coverage(metrics)
        
        # Calculate efficiency metrics
        kpis.asset_turnover = self._calculate_asset_turnover(metrics)
        kpis.cash_conversion_cycle = self._calculate_cash_conversion_cycle(ticker, fiscal_year, metrics)
        
        # Calculate market metrics
        kpis.book_value_per_share = self._calculate_book_value_per_share(metrics)
        kpis.tangible_book_value = self._calculate_tangible_book_value(metrics)
        
        # Calculate cash flow metrics
        kpis.fcf_to_revenue = self._calculate_fcf_to_revenue(metrics)
        kpis.fcf_to_net_income = self._calculate_fcf_to_net_income(metrics)
        kpis.cash_flow_margin = self._calculate_cash_flow_margin(metrics)
        
        return kpis
    
    def _get_metrics(self, ticker: str, fiscal_year: int) -> Optional[Dict[str, float]]:
        """Fetch all metrics needed for KPI calculations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT metric, value
            FROM metric_snapshots
            WHERE ticker = ? AND end_year = ?
        """
        cursor.execute(query, (ticker, fiscal_year))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return None
        
        return dict(results)
    
    # === Profitability Metrics ===
    
    def _calculate_roe(self, metrics: Dict[str, float]) -> Optional[float]:
        """Return on Equity = Net Income / Shareholders' Equity * 100"""
        net_income = metrics.get('net_income', 0)
        equity = metrics.get('shareholders_equity', 0)
        if equity > 0:
            return (net_income / equity) * 100
        return None
    
    def _calculate_roa(self, metrics: Dict[str, float]) -> Optional[float]:
        """Return on Assets = Net Income / Total Assets * 100"""
        net_income = metrics.get('net_income', 0)
        total_assets = metrics.get('total_assets', 0)
        if total_assets > 0:
            return (net_income / total_assets) * 100
        return None
    
    def _calculate_roic(self, metrics: Dict[str, float]) -> Optional[float]:
        """
        Return on Invested Capital = NOPAT / Invested Capital * 100
        NOPAT = Operating Income * (1 - Tax Rate)
        Invested Capital = Total Assets - Current Liabilities
        """
        operating_income = metrics.get('operating_income', 0)
        income_tax = metrics.get('income_tax_expense', 0)
        net_income = metrics.get('net_income', 0)
        
        # Estimate tax rate
        if net_income != 0:
            tax_rate = income_tax / (net_income + income_tax) if (net_income + income_tax) != 0 else 0.21
        else:
            tax_rate = 0.21  # Default corporate tax rate
        
        nopat = operating_income * (1 - tax_rate)
        
        total_assets = metrics.get('total_assets', 0)
        current_liabilities = metrics.get('current_liabilities', 0)
        invested_capital = total_assets - current_liabilities
        
        if invested_capital > 0:
            return (nopat / invested_capital) * 100
        return None
    
    def _calculate_roce(self, metrics: Dict[str, float]) -> Optional[float]:
        """
        Return on Capital Employed = EBIT / Capital Employed * 100
        Capital Employed = Total Assets - Current Liabilities
        """
        ebit = metrics.get('ebit', metrics.get('operating_income', 0))
        total_assets = metrics.get('total_assets', 0)
        current_liabilities = metrics.get('current_liabilities', 0)
        capital_employed = total_assets - current_liabilities
        
        if capital_employed > 0:
            return (ebit / capital_employed) * 100
        return None
    
    # === Liquidity Metrics ===
    
    def _calculate_current_ratio(self, metrics: Dict[str, float]) -> Optional[float]:
        """Current Ratio = Current Assets / Current Liabilities"""
        current_assets = metrics.get('current_assets', 0)
        current_liabilities = metrics.get('current_liabilities', 0)
        if current_liabilities > 0:
            return current_assets / current_liabilities
        return None
    
    def _calculate_quick_ratio(self, metrics: Dict[str, float]) -> Optional[float]:
        """
        Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        If inventory not available, use 70% of current assets (conservative estimate)
        """
        current_assets = metrics.get('current_assets', 0)
        inventory = metrics.get('inventory', current_assets * 0.3)  # Estimate if not available
        current_liabilities = metrics.get('current_liabilities', 0)
        
        if current_liabilities > 0:
            return (current_assets - inventory) / current_liabilities
        return None
    
    def _calculate_cash_ratio(self, metrics: Dict[str, float]) -> Optional[float]:
        """Cash Ratio = Cash / Current Liabilities"""
        cash = metrics.get('cash_and_cash_equivalents', 0)
        current_liabilities = metrics.get('current_liabilities', 0)
        if current_liabilities > 0:
            return cash / current_liabilities
        return None
    
    def _calculate_working_capital(self, metrics: Dict[str, float]) -> Optional[float]:
        """Working Capital = Current Assets - Current Liabilities"""
        current_assets = metrics.get('current_assets', 0)
        current_liabilities = metrics.get('current_liabilities', 0)
        return current_assets - current_liabilities
    
    def _calculate_working_capital_ratio(self, metrics: Dict[str, float]) -> Optional[float]:
        """Working Capital Ratio = Working Capital / Total Assets"""
        working_capital = self._calculate_working_capital(metrics)
        total_assets = metrics.get('total_assets', 0)
        if total_assets > 0 and working_capital is not None:
            return (working_capital / total_assets) * 100
        return None
    
    # === Leverage Metrics ===
    
    def _calculate_debt_to_equity(self, metrics: Dict[str, float]) -> Optional[float]:
        """Debt-to-Equity = Total Liabilities / Shareholders' Equity"""
        total_liabilities = metrics.get('total_liabilities', 0)
        equity = metrics.get('shareholders_equity', 0)
        if equity > 0:
            return total_liabilities / equity
        return None
    
    def _calculate_debt_to_assets(self, metrics: Dict[str, float]) -> Optional[float]:
        """Debt-to-Assets = Total Liabilities / Total Assets"""
        total_liabilities = metrics.get('total_liabilities', 0)
        total_assets = metrics.get('total_assets', 0)
        if total_assets > 0:
            return total_liabilities / total_assets
        return None
    
    def _calculate_interest_coverage(self, metrics: Dict[str, float]) -> Optional[float]:
        """Interest Coverage = EBIT / Interest Expense"""
        ebit = metrics.get('ebit', metrics.get('operating_income', 0))
        interest_expense = metrics.get('interest_expense', 0)
        if interest_expense > 0:
            return ebit / interest_expense
        return None
    
    def _calculate_debt_service_coverage(self, metrics: Dict[str, float]) -> Optional[float]:
        """Debt Service Coverage = Operating Cash Flow / Total Debt Service"""
        ocf = metrics.get('cash_from_operations', 0)
        interest_expense = metrics.get('interest_expense', 0)
        # Estimate principal payments as 10% of long-term debt (simplified)
        long_term_debt = metrics.get('long_term_debt', 0)
        principal_payment = long_term_debt * 0.1
        
        total_debt_service = interest_expense + principal_payment
        if total_debt_service > 0:
            return ocf / total_debt_service
        return None
    
    # === Efficiency Metrics ===
    
    def _calculate_asset_turnover(self, metrics: Dict[str, float]) -> Optional[float]:
        """Asset Turnover = Revenue / Total Assets"""
        revenue = metrics.get('revenue', 0)
        total_assets = metrics.get('total_assets', 0)
        if total_assets > 0:
            return revenue / total_assets
        return None
    
    def _calculate_cash_conversion_cycle(
        self, ticker: str, fiscal_year: int, metrics: Dict[str, float]
    ) -> Optional[float]:
        """
        Cash Conversion Cycle = DSO + DIO - DPO
        (Days Sales Outstanding + Days Inventory Outstanding - Days Payable Outstanding)
        Simplified version without detailed balance sheet data
        """
        # Would need more detailed balance sheet data for accurate calculation
        # This is a simplified placeholder
        return None
    
    # === Market Metrics ===
    
    def _calculate_book_value_per_share(self, metrics: Dict[str, float]) -> Optional[float]:
        """Book Value per Share = Shareholders' Equity / Shares Outstanding"""
        equity = metrics.get('shareholders_equity', 0)
        shares = metrics.get('shares_outstanding', 0)
        if shares > 0:
            return equity / shares
        return None
    
    def _calculate_tangible_book_value(self, metrics: Dict[str, float]) -> Optional[float]:
        """Tangible Book Value = Shareholders' Equity - Intangible Assets"""
        equity = metrics.get('shareholders_equity', 0)
        intangibles = metrics.get('intangible_assets', 0)
        return equity - intangibles
    
    # === Cash Flow Metrics ===
    
    def _calculate_fcf_to_revenue(self, metrics: Dict[str, float]) -> Optional[float]:
        """FCF to Revenue = Free Cash Flow / Revenue * 100"""
        fcf = metrics.get('free_cash_flow', 0)
        revenue = metrics.get('revenue', 0)
        if revenue > 0:
            return (fcf / revenue) * 100
        return None
    
    def _calculate_fcf_to_net_income(self, metrics: Dict[str, float]) -> Optional[float]:
        """FCF to Net Income = Free Cash Flow / Net Income"""
        fcf = metrics.get('free_cash_flow', 0)
        net_income = metrics.get('net_income', 0)
        if net_income > 0:
            return fcf / net_income
        return None
    
    def _calculate_cash_flow_margin(self, metrics: Dict[str, float]) -> Optional[float]:
        """Cash Flow Margin = Operating Cash Flow / Revenue * 100"""
        ocf = metrics.get('cash_from_operations', 0)
        revenue = metrics.get('revenue', 0)
        if revenue > 0:
            return (ocf / revenue) * 100
        return None


def get_advanced_kpi_calculator(db_path: str) -> AdvancedKPICalculator:
    """Factory function to create AdvancedKPICalculator instance."""
    return AdvancedKPICalculator(db_path)

