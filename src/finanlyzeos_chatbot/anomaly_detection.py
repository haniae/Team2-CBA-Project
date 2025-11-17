"""
Anomaly Detection for Financial Metrics

Identifies unusual patterns, outliers, and anomalies in financial data.
Uses statistical methods and historical patterns to flag potential issues or opportunities.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import sqlite3

LOGGER = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """Detected anomaly in financial data."""
    ticker: str
    metric: str
    fiscal_year: int
    value: float
    expected_value: float
    deviation_pct: float
    severity: str  # "low", "medium", "high", "critical"
    description: str
    confidence: float  # 0-1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "fiscal_year": self.fiscal_year,
            "value": self.value,
            "expected_value": self.expected_value,
            "deviation_pct": self.deviation_pct,
            "severity": self.severity,
            "description": self.description,
            "confidence": self.confidence,
        }


class AnomalyDetector:
    """Statistical anomaly detection for financial metrics."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def detect_revenue_anomalies(
        self, ticker: str, years: int = 5, std_threshold: float = 2.0
    ) -> List[Anomaly]:
        """
        Detect anomalies in revenue growth patterns.
        
        Args:
            ticker: Company ticker symbol
            years: Number of years to analyze
            std_threshold: Number of standard deviations for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get revenue history
        query = """
            SELECT end_year, value
            FROM metric_snapshots
            WHERE ticker = ? AND metric = 'revenue'
            ORDER BY end_year DESC
            LIMIT ?
        """
        cursor.execute(query, (ticker, years))
        results = cursor.fetchall()
        conn.close()
        
        if len(results) < 3:
            return []  # Need at least 3 years for meaningful analysis
        
        results = sorted(results, key=lambda x: x[0])  # Sort by year ascending
        anomalies = []
        
        # Calculate year-over-year growth rates
        growth_rates = []
        for i in range(1, len(results)):
            prev_revenue = results[i-1][1]
            curr_revenue = results[i][1]
            if prev_revenue > 0:
                growth_rate = ((curr_revenue - prev_revenue) / prev_revenue) * 100
                growth_rates.append((results[i][0], growth_rate, curr_revenue))
        
        if len(growth_rates) < 2:
            return []
        
        # Calculate mean and std of growth rates
        rates_only = [gr[1] for gr in growth_rates]
        mean_growth = statistics.mean(rates_only)
        std_growth = statistics.stdev(rates_only) if len(rates_only) > 1 else 0
        
        # Detect anomalies
        for year, growth_rate, revenue in growth_rates:
            if std_growth > 0:
                z_score = abs(growth_rate - mean_growth) / std_growth
                
                if z_score > std_threshold:
                    deviation_pct = abs(growth_rate - mean_growth)
                    severity = self._calculate_severity(z_score, std_threshold)
                    
                    direction = "spike" if growth_rate > mean_growth else "drop"
                    description = (
                        f"Revenue growth {direction} detected: {growth_rate:.1f}% vs "
                        f"historical avg {mean_growth:.1f}% (±{std_growth:.1f}%). "
                        f"Deviation: {z_score:.1f} std devs."
                    )
                    
                    anomalies.append(Anomaly(
                        ticker=ticker,
                        metric="revenue_growth",
                        fiscal_year=year,
                        value=growth_rate,
                        expected_value=mean_growth,
                        deviation_pct=deviation_pct,
                        severity=severity,
                        description=description,
                        confidence=min(z_score / (std_threshold * 2), 1.0),
                    ))
        
        return anomalies
    
    def detect_margin_anomalies(
        self, ticker: str, years: int = 5, std_threshold: float = 2.0
    ) -> List[Anomaly]:
        """
        Detect anomalies in profit margin trends.
        
        Args:
            ticker: Company ticker symbol
            years: Number of years to analyze
            std_threshold: Number of standard deviations for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get revenue and net income history
        query = """
            SELECT end_year, metric, value
            FROM metric_snapshots
            WHERE ticker = ? AND metric IN ('revenue', 'net_income')
            ORDER BY end_year DESC
            LIMIT ?
        """
        cursor.execute(query, (ticker, years * 2))  # *2 because we need both metrics
        results = cursor.fetchall()
        conn.close()
        
        # Calculate margins per year
        margins_by_year = {}
        for year, metric, value in results:
            if year not in margins_by_year:
                margins_by_year[year] = {}
            margins_by_year[year][metric] = value
        
        margins = []
        for year, metrics in sorted(margins_by_year.items()):
            revenue = metrics.get('revenue', 0)
            net_income = metrics.get('net_income', 0)
            if revenue > 0:
                margin = (net_income / revenue) * 100
                margins.append((year, margin))
        
        if len(margins) < 3:
            return []
        
        # Calculate statistics
        margin_values = [m[1] for m in margins]
        mean_margin = statistics.mean(margin_values)
        std_margin = statistics.stdev(margin_values) if len(margin_values) > 1 else 0
        
        anomalies = []
        for year, margin in margins:
            if std_margin > 0:
                z_score = abs(margin - mean_margin) / std_margin
                
                if z_score > std_threshold:
                    deviation_pct = abs(margin - mean_margin)
                    severity = self._calculate_severity(z_score, std_threshold)
                    
                    direction = "expansion" if margin > mean_margin else "contraction"
                    description = (
                        f"Net margin {direction} detected: {margin:.1f}% vs "
                        f"historical avg {mean_margin:.1f}% (±{std_margin:.1f}%). "
                        f"Deviation: {z_score:.1f} std devs."
                    )
                    
                    anomalies.append(Anomaly(
                        ticker=ticker,
                        metric="net_margin",
                        fiscal_year=year,
                        value=margin,
                        expected_value=mean_margin,
                        deviation_pct=deviation_pct,
                        severity=severity,
                        description=description,
                        confidence=min(z_score / (std_threshold * 2), 1.0),
                    ))
        
        return anomalies
    
    def detect_cash_flow_anomalies(
        self, ticker: str, years: int = 5, std_threshold: float = 2.0
    ) -> List[Anomaly]:
        """
        Detect anomalies in cash flow patterns.
        
        Args:
            ticker: Company ticker symbol
            years: Number of years to analyze
            std_threshold: Number of standard deviations for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get cash flow history
        query = """
            SELECT end_year, metric, value
            FROM metric_snapshots
            WHERE ticker = ? AND metric IN ('cash_from_operations', 'free_cash_flow')
            ORDER BY end_year DESC
            LIMIT ?
        """
        cursor.execute(query, (ticker, years * 2))
        results = cursor.fetchall()
        conn.close()
        
        if len(results) < 3:
            return []
        
        # Group by metric type
        ocf_data = [(y, v) for y, m, v in results if m == 'cash_from_operations']
        fcf_data = [(y, v) for y, m, v in results if m == 'free_cash_flow']
        
        anomalies = []
        
        # Analyze operating cash flow
        if len(ocf_data) >= 3:
            anomalies.extend(self._analyze_metric_series(
                ticker, 'operating_cash_flow', ocf_data, std_threshold
            ))
        
        # Analyze free cash flow
        if len(fcf_data) >= 3:
            anomalies.extend(self._analyze_metric_series(
                ticker, 'free_cash_flow', fcf_data, std_threshold
            ))
        
        return anomalies
    
    def detect_balance_sheet_anomalies(
        self, ticker: str, years: int = 5, std_threshold: float = 2.0
    ) -> List[Anomaly]:
        """
        Detect anomalies in balance sheet ratios.
        
        Args:
            ticker: Company ticker symbol
            years: Number of years to analyze
            std_threshold: Number of standard deviations for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get balance sheet metrics
        query = """
            SELECT end_year, metric, value
            FROM metric_snapshots
            WHERE ticker = ? AND metric IN (
                'current_assets', 'current_liabilities',
                'total_assets', 'total_liabilities', 'shareholders_equity'
            )
            ORDER BY end_year DESC
            LIMIT ?
        """
        cursor.execute(query, (ticker, years * 5))
        results = cursor.fetchall()
        conn.close()
        
        # Calculate ratios per year
        ratios_by_year = {}
        for year, metric, value in results:
            if year not in ratios_by_year:
                ratios_by_year[year] = {}
            ratios_by_year[year][metric] = value
        
        current_ratios = []
        debt_to_equity_ratios = []
        
        for year, metrics in sorted(ratios_by_year.items()):
            # Current ratio
            current_assets = metrics.get('current_assets', 0)
            current_liabilities = metrics.get('current_liabilities', 0)
            if current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
                current_ratios.append((year, current_ratio))
            
            # Debt-to-equity ratio
            total_liabilities = metrics.get('total_liabilities', 0)
            equity = metrics.get('shareholders_equity', 0)
            if equity > 0:
                dte_ratio = total_liabilities / equity
                debt_to_equity_ratios.append((year, dte_ratio))
        
        anomalies = []
        
        # Analyze current ratio
        if len(current_ratios) >= 3:
            anomalies.extend(self._analyze_metric_series(
                ticker, 'current_ratio', current_ratios, std_threshold
            ))
        
        # Analyze debt-to-equity ratio
        if len(debt_to_equity_ratios) >= 3:
            anomalies.extend(self._analyze_metric_series(
                ticker, 'debt_to_equity', debt_to_equity_ratios, std_threshold
            ))
        
        return anomalies
    
    def detect_all_anomalies(
        self, ticker: str, years: int = 5, std_threshold: float = 2.0
    ) -> Dict[str, List[Anomaly]]:
        """
        Run all anomaly detection methods and return consolidated results.
        
        Args:
            ticker: Company ticker symbol
            years: Number of years to analyze
            std_threshold: Number of standard deviations for anomaly detection
            
        Returns:
            Dictionary mapping category to list of anomalies
        """
        return {
            "revenue": self.detect_revenue_anomalies(ticker, years, std_threshold),
            "margins": self.detect_margin_anomalies(ticker, years, std_threshold),
            "cash_flow": self.detect_cash_flow_anomalies(ticker, years, std_threshold),
            "balance_sheet": self.detect_balance_sheet_anomalies(ticker, years, std_threshold),
        }
    
    def _analyze_metric_series(
        self, ticker: str, metric_name: str, data: List[Tuple[int, float]], std_threshold: float
    ) -> List[Anomaly]:
        """Helper to analyze a time series of metrics."""
        if len(data) < 3:
            return []
        
        values = [v for _, v in data]
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        
        if std_val == 0:
            return []
        
        anomalies = []
        for year, value in data:
            z_score = abs(value - mean_val) / std_val
            
            if z_score > std_threshold:
                deviation_pct = abs(value - mean_val)
                severity = self._calculate_severity(z_score, std_threshold)
                
                direction = "high" if value > mean_val else "low"
                description = (
                    f"{metric_name.replace('_', ' ').title()} unusually {direction}: "
                    f"{value:.2f} vs historical avg {mean_val:.2f} (±{std_val:.2f}). "
                    f"Deviation: {z_score:.1f} std devs."
                )
                
                anomalies.append(Anomaly(
                    ticker=ticker,
                    metric=metric_name,
                    fiscal_year=year,
                    value=value,
                    expected_value=mean_val,
                    deviation_pct=deviation_pct,
                    severity=severity,
                    description=description,
                    confidence=min(z_score / (std_threshold * 2), 1.0),
                ))
        
        return anomalies
    
    def _calculate_severity(self, z_score: float, threshold: float) -> str:
        """Calculate severity level based on z-score."""
        if z_score > threshold * 3:
            return "critical"
        elif z_score > threshold * 2:
            return "high"
        elif z_score > threshold * 1.5:
            return "medium"
        else:
            return "low"


def get_anomaly_detector(db_path: str) -> AnomalyDetector:
    """Factory function to create AnomalyDetector instance."""
    return AnomalyDetector(db_path)

