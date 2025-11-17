"""
Predictive Trend Analysis and Forecasting

Uses historical financial data to predict future trends using statistical methods.
Implements linear regression, moving averages, and growth rate projections.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import sqlite3

LOGGER = logging.getLogger(__name__)


@dataclass
class Forecast:
    """Predicted future value for a metric."""
    ticker: str
    metric: str
    fiscal_year: int
    predicted_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    method: str  # "linear_regression", "moving_average", "growth_rate"
    confidence: float  # 0-1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "fiscal_year": self.fiscal_year,
            "predicted_value": self.predicted_value,
            "confidence_interval": {
                "low": self.confidence_interval_low,
                "high": self.confidence_interval_high,
            },
            "method": self.method,
            "confidence": self.confidence,
        }


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis results."""
    ticker: str
    metric: str
    historical_data: List[Tuple[int, float]]  # (year, value) pairs
    trend: str  # "increasing", "decreasing", "stable", "volatile"
    growth_rate: float  # CAGR %
    volatility: float  # Standard deviation of growth rates
    forecasts: List[Forecast]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "historical_data": [{"year": y, "value": v} for y, v in self.historical_data],
            "trend": self.trend,
            "growth_rate": self.growth_rate,
            "volatility": self.volatility,
            "forecasts": [f.to_dict() for f in self.forecasts],
        }


class PredictiveAnalytics:
    """Statistical forecasting and trend analysis for financial metrics."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def analyze_metric_trend(
        self, ticker: str, metric: str, years_history: int = 5, years_forecast: int = 3
    ) -> Optional[TrendAnalysis]:
        """
        Analyze historical trend and forecast future values.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to analyze (e.g., 'revenue', 'net_income')
            years_history: Number of historical years to include
            years_forecast: Number of years to forecast
            
        Returns:
            TrendAnalysis with historical data and forecasts
        """
        # Get historical data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT end_year, value
            FROM metric_snapshots
            WHERE ticker = ? AND metric = ?
            ORDER BY end_year DESC
            LIMIT ?
        """
        cursor.execute(query, (ticker, metric, years_history))
        results = cursor.fetchall()
        conn.close()
        
        if len(results) < 3:
            return None  # Need at least 3 years for meaningful forecasts
        
        historical_data = sorted(results, key=lambda x: x[0])  # Sort by year ascending
        
        # Calculate growth rates
        growth_rates = []
        for i in range(1, len(historical_data)):
            prev_value = historical_data[i-1][1]
            curr_value = historical_data[i][1]
            if prev_value > 0:
                growth_rate = ((curr_value - prev_value) / prev_value) * 100
                growth_rates.append(growth_rate)
        
        # Calculate CAGR (Compound Annual Growth Rate)
        if len(historical_data) >= 2:
            first_value = historical_data[0][1]
            last_value = historical_data[-1][1]
            n_periods = len(historical_data) - 1
            if first_value > 0:
                cagr = (((last_value / first_value) ** (1/n_periods)) - 1) * 100
            else:
                cagr = 0
        else:
            cagr = 0
        
        # Calculate volatility
        volatility = statistics.stdev(growth_rates) if len(growth_rates) > 1 else 0
        
        # Determine trend
        trend = self._classify_trend(cagr, volatility)
        
        # Generate forecasts using multiple methods
        forecasts = []
        last_year = historical_data[-1][0]
        
        for year_offset in range(1, years_forecast + 1):
            forecast_year = last_year + year_offset
            
            # Method 1: Linear regression forecast
            linear_forecast = self._linear_regression_forecast(
                historical_data, forecast_year
            )
            if linear_forecast:
                forecasts.append(linear_forecast)
            
            # Method 2: Growth rate projection (using CAGR)
            growth_forecast = self._growth_rate_forecast(
                ticker, metric, historical_data, forecast_year, cagr, volatility
            )
            if growth_forecast:
                forecasts.append(growth_forecast)
        
        return TrendAnalysis(
            ticker=ticker,
            metric=metric,
            historical_data=historical_data,
            trend=trend,
            growth_rate=cagr,
            volatility=volatility,
            forecasts=forecasts,
        )
    
    def forecast_revenue(
        self, ticker: str, years_history: int = 5, years_forecast: int = 3
    ) -> Optional[TrendAnalysis]:
        """Forecast future revenue."""
        return self.analyze_metric_trend(ticker, 'revenue', years_history, years_forecast)
    
    def forecast_net_income(
        self, ticker: str, years_history: int = 5, years_forecast: int = 3
    ) -> Optional[TrendAnalysis]:
        """Forecast future net income."""
        return self.analyze_metric_trend(ticker, 'net_income', years_history, years_forecast)
    
    def forecast_cash_flow(
        self, ticker: str, years_history: int = 5, years_forecast: int = 3
    ) -> Optional[TrendAnalysis]:
        """Forecast future cash flow."""
        return self.analyze_metric_trend(ticker, 'cash_from_operations', years_history, years_forecast)
    
    def forecast_multiple_metrics(
        self, ticker: str, metrics: List[str], years_history: int = 5, years_forecast: int = 3
    ) -> Dict[str, Optional[TrendAnalysis]]:
        """
        Forecast multiple metrics at once.
        
        Args:
            ticker: Company ticker symbol
            metrics: List of metrics to forecast
            years_history: Number of historical years to include
            years_forecast: Number of years to forecast
            
        Returns:
            Dictionary mapping metric name to TrendAnalysis
        """
        forecasts = {}
        for metric in metrics:
            forecasts[metric] = self.analyze_metric_trend(
                ticker, metric, years_history, years_forecast
            )
        return forecasts
    
    def _linear_regression_forecast(
        self, historical_data: List[Tuple[int, float]], forecast_year: int
    ) -> Optional[Forecast]:
        """Simple linear regression forecast."""
        if len(historical_data) < 2:
            return None
        
        # Calculate linear regression coefficients
        years = [y for y, _ in historical_data]
        values = [v for _, v in historical_data]
        
        n = len(years)
        sum_x = sum(years)
        sum_y = sum(values)
        sum_xx = sum(y * y for y in years)
        sum_xy = sum(years[i] * values[i] for i in range(n))
        
        # y = mx + b
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0:
            return None
        
        m = (n * sum_xy - sum_x * sum_y) / denominator
        b = (sum_y - m * sum_x) / n
        
        # Forecast
        predicted_value = m * forecast_year + b
        
        # Calculate confidence interval (simplified)
        residuals = [values[i] - (m * years[i] + b) for i in range(n)]
        std_error = statistics.stdev(residuals) if len(residuals) > 1 else 0
        
        # 95% confidence interval (~2 std errors)
        margin = 2 * std_error
        
        ticker = "N/A"
        metric = "N/A"
        
        return Forecast(
            ticker=ticker,
            metric=metric,
            fiscal_year=forecast_year,
            predicted_value=max(0, predicted_value),  # Don't allow negative values
            confidence_interval_low=max(0, predicted_value - margin),
            confidence_interval_high=predicted_value + margin,
            method="linear_regression",
            confidence=0.75,  # Moderate confidence for linear regression
        )
    
    def _growth_rate_forecast(
        self,
        ticker: str,
        metric: str,
        historical_data: List[Tuple[int, float]],
        forecast_year: int,
        cagr: float,
        volatility: float,
    ) -> Optional[Forecast]:
        """Forecast using compound growth rate."""
        if not historical_data:
            return None
        
        last_year, last_value = historical_data[-1]
        years_ahead = forecast_year - last_year
        
        # Project using CAGR
        growth_multiplier = (1 + cagr / 100) ** years_ahead
        predicted_value = last_value * growth_multiplier
        
        # Confidence interval based on volatility
        # Higher volatility = wider confidence interval
        confidence_width = (volatility / 100) * predicted_value * years_ahead
        
        # Confidence decreases with forecast distance and volatility
        confidence = max(0.3, 0.9 - (years_ahead * 0.1) - (volatility / 100))
        
        return Forecast(
            ticker=ticker,
            metric=metric,
            fiscal_year=forecast_year,
            predicted_value=max(0, predicted_value),
            confidence_interval_low=max(0, predicted_value - confidence_width),
            confidence_interval_high=predicted_value + confidence_width,
            method="growth_rate",
            confidence=confidence,
        )
    
    def _classify_trend(self, cagr: float, volatility: float) -> str:
        """Classify trend based on growth rate and volatility."""
        if volatility > 30:
            return "volatile"
        elif abs(cagr) < 2:
            return "stable"
        elif cagr > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def calculate_scenario_projections(
        self, ticker: str, metric: str, scenarios: Dict[str, float]
    ) -> Dict[str, List[Forecast]]:
        """
        Calculate projections under different growth scenarios.
        
        Args:
            ticker: Company ticker symbol
            metric: Metric to project
            scenarios: Dict of scenario names to growth rates (e.g., {"optimistic": 15, "base": 10, "pessimistic": 5})
            
        Returns:
            Dictionary mapping scenario name to list of forecasts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT value
            FROM metric_snapshots
            WHERE ticker = ? AND metric = ?
            ORDER BY end_year DESC
            LIMIT 1
        """
        cursor.execute(query, (ticker, metric))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {}
        
        last_value = result[0]
        current_year = 2024
        
        projections = {}
        for scenario_name, growth_rate in scenarios.items():
            forecasts = []
            for year_offset in range(1, 6):  # 5-year projections
                forecast_year = current_year + year_offset
                growth_multiplier = (1 + growth_rate / 100) ** year_offset
                predicted_value = last_value * growth_multiplier
                
                # Confidence interval scales with time
                margin_pct = 0.1 + (year_offset * 0.05)  # 10% + 5% per year
                margin = predicted_value * margin_pct
                
                forecasts.append(Forecast(
                    ticker=ticker,
                    metric=metric,
                    fiscal_year=forecast_year,
                    predicted_value=predicted_value,
                    confidence_interval_low=predicted_value - margin,
                    confidence_interval_high=predicted_value + margin,
                    method=f"scenario_{scenario_name}",
                    confidence=max(0.5, 0.9 - (year_offset * 0.08)),
                ))
            
            projections[scenario_name] = forecasts
        
        return projections


def get_predictive_analytics(db_path: str) -> PredictiveAnalytics:
    """Factory function to create PredictiveAnalytics instance."""
    return PredictiveAnalytics(db_path)

