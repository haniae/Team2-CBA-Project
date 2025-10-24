"""
Advanced Sector Benchmarking and Analytics Module

Provides industry-level analysis, peer comparisons, and sector benchmarking
for S&P 500 companies. Enables powerful comparative analytics across industries.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import sqlite3

LOGGER = logging.getLogger(__name__)

# S&P 500 Sector Classifications (GICS Sectors)
SECTOR_MAP = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AVGO": "Technology",
    "ORCL": "Technology", "CSCO": "Technology", "ADBE": "Technology", "CRM": "Technology",
    "INTC": "Technology", "AMD": "Technology", "QCOM": "Technology", "TXN": "Technology",
    "AMAT": "Technology", "MU": "Technology", "LRCX": "Technology", "KLAC": "Technology",
    "SNPS": "Technology", "CDNS": "Technology", "MCHP": "Technology", "NXPI": "Technology",
    "ADI": "Technology", "ON": "Technology", "MPWR": "Technology", "TER": "Technology",
    "GOOGL": "Communication Services", "GOOG": "Communication Services", "META": "Communication Services",
    "NFLX": "Communication Services", "DIS": "Communication Services", "CMCSA": "Communication Services",
    "T": "Communication Services", "VZ": "Communication Services", "TMUS": "Communication Services",
    "CHTR": "Communication Services", "EA": "Communication Services", "TTWO": "Communication Services",
    "MTCH": "Communication Services", "LYV": "Communication Services", "OMC": "Communication Services",
    "IPG": "Communication Services", "FOX": "Communication Services", "FOXA": "Communication Services",
    "NWSA": "Communication Services", "NWS": "Communication Services", "PARA": "Communication Services",
    "WBD": "Communication Services",
    
    # Financials
    "JPM": "Financials", "V": "Financials", "MA": "Financials", "BAC": "Financials",
    "WFC": "Financials", "MS": "Financials", "GS": "Financials", "SPGI": "Financials",
    "BLK": "Financials", "C": "Financials", "SCHW": "Financials", "AXP": "Financials",
    "PNC": "Financials", "USB": "Financials", "TFC": "Financials", "BK": "Financials",
    "COF": "Financials", "AIG": "Financials", "MET": "Financials", "PRU": "Financials",
    "AFL": "Financials", "ALL": "Financials", "TRV": "Financials", "PGR": "Financials",
    "CB": "Financials", "MMC": "Financials", "AON": "Financials", "AJG": "Financials",
    "BRO": "Financials", "WRB": "Financials", "RE": "Financials", "FIS": "Financials",
    "FI": "Financials", "GPN": "Financials", "PYPL": "Financials", "TROW": "Financials",
    "BEN": "Financials", "IVZ": "Financials", "STT": "Financials", "NTRS": "Financials",
    "PFG": "Financials", "KEY": "Financials", "CFG": "Financials", "HBAN": "Financials",
    "RF": "Financials", "FITB": "Financials", "MTB": "Financials", "RJF": "Financials",
    
    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "LLY": "Healthcare", "ABBV": "Healthcare",
    "MRK": "Healthcare", "PFE": "Healthcare", "TMO": "Healthcare", "ABT": "Healthcare",
    "DHR": "Healthcare", "BMY": "Healthcare", "AMGN": "Healthcare", "GILD": "Healthcare",
    "CVS": "Healthcare", "CI": "Healthcare", "ELV": "Healthcare", "HUM": "Healthcare",
    "MCK": "Healthcare", "COR": "Healthcare", "CAH": "Healthcare", "SYK": "Healthcare",
    "BSX": "Healthcare", "ISRG": "Healthcare", "MDT": "Healthcare", "VRTX": "Healthcare",
    "REGN": "Healthcare", "ZTS": "Healthcare", "BIIB": "Healthcare", "IDXX": "Healthcare",
    "IQV": "Healthcare", "CRL": "Healthcare", "A": "Healthcare", "EW": "Healthcare",
    "RMD": "Healthcare", "DXCM": "Healthcare", "ALGN": "Healthcare", "HOLX": "Healthcare",
    "TECH": "Healthcare", "BDX": "Healthcare", "BAX": "Healthcare", "WAT": "Healthcare",
    "MTD": "Healthcare", "STE": "Healthcare", "TFX": "Healthcare", "PKI": "Healthcare",
    
    # Consumer Discretionary
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "MCD": "Consumer Discretionary", "NKE": "Consumer Discretionary", "LOW": "Consumer Discretionary",
    "SBUX": "Consumer Discretionary", "TJX": "Consumer Discretionary", "BKNG": "Consumer Discretionary",
    "CMG": "Consumer Discretionary", "ABNB": "Consumer Discretionary", "F": "Consumer Discretionary",
    "GM": "Consumer Discretionary", "MAR": "Consumer Discretionary", "HLT": "Consumer Discretionary",
    "DHI": "Consumer Discretionary", "LEN": "Consumer Discretionary", "YUM": "Consumer Discretionary",
    "ORLY": "Consumer Discretionary", "AZO": "Consumer Discretionary", "RCL": "Consumer Discretionary",
    "CCL": "Consumer Discretionary", "NCLH": "Consumer Discretionary", "LVS": "Consumer Discretionary",
    "WYNN": "Consumer Discretionary", "MGM": "Consumer Discretionary", "CZR": "Consumer Discretionary",
    "POOL": "Consumer Discretionary", "BBY": "Consumer Discretionary", "ULTA": "Consumer Discretionary",
    "DPZ": "Consumer Discretionary", "QSR": "Consumer Discretionary", "DRI": "Consumer Discretionary",
    "RL": "Consumer Discretionary", "LULU": "Consumer Discretionary", "TPR": "Consumer Discretionary",
    
    # Consumer Staples
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "COST": "Consumer Staples", "WMT": "Consumer Staples", "PM": "Consumer Staples",
    "MO": "Consumer Staples", "CL": "Consumer Staples", "MDLZ": "Consumer Staples",
    "GIS": "Consumer Staples", "KHC": "Consumer Staples", "K": "Consumer Staples",
    "HSY": "Consumer Staples", "CPB": "Consumer Staples", "SJM": "Consumer Staples",
    "CAG": "Consumer Staples", "KMB": "Consumer Staples", "CLX": "Consumer Staples",
    "CHD": "Consumer Staples", "TSN": "Consumer Staples", "HRL": "Consumer Staples",
    "MNST": "Consumer Staples", "KDP": "Consumer Staples", "TAP": "Consumer Staples",
    "BF-B": "Consumer Staples", "STZ": "Consumer Staples", "EL": "Consumer Staples",
    
    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "EOG": "Energy", "PXD": "Energy", "MPC": "Energy", "PSX": "Energy",
    "VLO": "Energy", "OXY": "Energy", "HAL": "Energy", "WMB": "Energy",
    "KMI": "Energy", "OKE": "Energy", "TRGP": "Energy", "HES": "Energy",
    "BKR": "Energy", "FANG": "Energy", "DVN": "Energy", "MRO": "Energy",
    "APA": "Energy", "CTRA": "Energy",
    
    # Industrials
    "CAT": "Industrials", "HON": "Industrials", "RTX": "Industrials", "BA": "Industrials",
    "UNP": "Industrials", "GE": "Industrials", "DE": "Industrials", "LMT": "Industrials",
    "MMM": "Industrials", "ETN": "Industrials", "PH": "Industrials", "ITW": "Industrials",
    "EMR": "Industrials", "GD": "Industrials", "NOC": "Industrials", "CSX": "Industrials",
    "NSC": "Industrials", "FDX": "Industrials", "UPS": "Industrials", "WM": "Industrials",
    "RSG": "Industrials", "CARR": "Industrials", "OTIS": "Industrials", "PCAR": "Industrials",
    "JCI": "Industrials", "ROK": "Industrials", "DAL": "Industrials", "UAL": "Industrials",
    "LUV": "Industrials", "AAL": "Industrials", "AME": "Industrials", "IR": "Industrials",
    "SWK": "Industrials", "DOV": "Industrials", "FTV": "Industrials", "ALLE": "Industrials",
    
    # Materials
    "LIN": "Materials", "APD": "Materials", "ECL": "Materials", "DD": "Materials",
    "SHW": "Materials", "FCX": "Materials", "NEM": "Materials", "DOW": "Materials",
    "NUE": "Materials", "VMC": "Materials", "MLM": "Materials", "CF": "Materials",
    "MOS": "Materials", "ALB": "Materials", "IFF": "Materials", "CE": "Materials",
    "EMN": "Materials", "FMC": "Materials", "LYB": "Materials", "PPG": "Materials",
    "BALL": "Materials", "AVY": "Materials", "AMCR": "Materials", "PKG": "Materials",
    "IP": "Materials", "SEE": "Materials",
    
    # Real Estate
    "PLD": "Real Estate", "AMT": "Real Estate", "EQIX": "Real Estate", "PSA": "Real Estate",
    "DLR": "Real Estate", "SPG": "Real Estate", "O": "Real Estate", "WELL": "Real Estate",
    "EQR": "Real Estate", "AVB": "Real Estate", "VTR": "Real Estate", "VICI": "Real Estate",
    "ARE": "Real Estate", "SBAC": "Real Estate", "INVH": "Real Estate", "MAA": "Real Estate",
    "ESS": "Real Estate", "DRE": "Real Estate", "UDR": "Real Estate", "HST": "Real Estate",
    "REG": "Real Estate", "BXP": "Real Estate", "KIM": "Real Estate", "FRT": "Real Estate",
    
    # Utilities
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities", "D": "Utilities",
    "AEP": "Utilities", "EXC": "Utilities", "SRE": "Utilities", "XEL": "Utilities",
    "WEC": "Utilities", "ED": "Utilities", "PEG": "Utilities", "ES": "Utilities",
    "DTE": "Utilities", "EIX": "Utilities", "FE": "Utilities", "PPL": "Utilities",
    "AES": "Utilities", "AWK": "Utilities", "ATO": "Utilities", "CMS": "Utilities",
    "CNP": "Utilities", "ETR": "Utilities", "EVRG": "Utilities", "LNT": "Utilities",
    "NI": "Utilities", "NRG": "Utilities", "PCG": "Utilities", "PNW": "Utilities",
}


@dataclass
class SectorBenchmark:
    """Sector-level aggregated metrics for benchmarking."""
    sector: str
    companies_count: int
    avg_revenue: float
    median_revenue: float
    avg_net_margin: float
    median_net_margin: float
    avg_operating_margin: float
    median_operating_margin: float
    avg_roe: float
    median_roe: float
    avg_roa: float
    median_roa: float
    avg_debt_to_equity: float
    median_debt_to_equity: float
    avg_current_ratio: float
    median_current_ratio: float
    revenue_growth_rate: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sector": self.sector,
            "companies_count": self.companies_count,
            "metrics": {
                "revenue": {"avg": self.avg_revenue, "median": self.median_revenue},
                "net_margin": {"avg": self.avg_net_margin, "median": self.median_net_margin},
                "operating_margin": {"avg": self.avg_operating_margin, "median": self.median_operating_margin},
                "roe": {"avg": self.avg_roe, "median": self.median_roe},
                "roa": {"avg": self.avg_roa, "median": self.median_roa},
                "debt_to_equity": {"avg": self.avg_debt_to_equity, "median": self.median_debt_to_equity},
                "current_ratio": {"avg": self.avg_current_ratio, "median": self.median_current_ratio},
                "revenue_growth_rate": self.revenue_growth_rate,
            }
        }


@dataclass
class CompanyVsSector:
    """Company performance compared to sector benchmarks."""
    ticker: str
    company_name: str
    sector: str
    metrics: Dict[str, float]
    sector_benchmarks: SectorBenchmark
    percentile_ranks: Dict[str, float]  # 0-100, where 50 = median
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "metrics": self.metrics,
            "sector_benchmarks": self.sector_benchmarks.to_dict(),
            "percentile_ranks": self.percentile_ranks,
        }


class SectorAnalytics:
    """Advanced sector-level analytics and benchmarking."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.sector_map = SECTOR_MAP
    
    def get_company_sector(self, ticker: str) -> Optional[str]:
        """Get the sector for a given ticker."""
        return self.sector_map.get(ticker.upper())
    
    def get_sector_companies(self, sector: str) -> List[str]:
        """Get all companies in a sector."""
        return [t for t, s in self.sector_map.items() if s == sector]
    
    def get_all_sectors(self) -> List[str]:
        """Get list of all sectors."""
        return sorted(set(self.sector_map.values()))
    
    def calculate_sector_benchmarks(self, sector: str, fiscal_year: int = 2024) -> Optional[SectorBenchmark]:
        """
        Calculate aggregated metrics for an entire sector.
        
        Args:
            sector: Sector name (e.g., "Technology", "Financials")
            fiscal_year: Year to calculate benchmarks for
            
        Returns:
            SectorBenchmark with aggregated sector metrics
        """
        companies = self.get_sector_companies(sector)
        if not companies:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Gather metrics for all companies in sector
        revenues = []
        net_margins = []
        operating_margins = []
        roes = []
        roas = []
        debt_to_equities = []
        current_ratios = []
        
        for ticker in companies:
            # Get metrics from metric_snapshots
            query = """
                SELECT metric, value
                FROM metric_snapshots
                WHERE ticker = ? AND end_year = ?
                AND metric IN ('revenue', 'net_income', 'operating_income', 
                             'total_assets', 'shareholders_equity', 'total_liabilities',
                             'current_assets', 'current_liabilities')
            """
            cursor.execute(query, (ticker, fiscal_year))
            metrics = dict(cursor.fetchall())
            
            if not metrics:
                continue
            
            # Calculate derived metrics
            revenue = metrics.get('revenue', 0)
            net_income = metrics.get('net_income', 0)
            operating_income = metrics.get('operating_income', 0)
            total_assets = metrics.get('total_assets', 0)
            equity = metrics.get('shareholders_equity', 0)
            total_liabilities = metrics.get('total_liabilities', 0)
            current_assets = metrics.get('current_assets', 0)
            current_liabilities = metrics.get('current_liabilities', 0)
            
            if revenue > 0:
                revenues.append(revenue)
                net_margins.append((net_income / revenue) * 100)
                operating_margins.append((operating_income / revenue) * 100)
            
            if equity > 0:
                roes.append((net_income / equity) * 100)
                if total_liabilities > 0:
                    debt_to_equities.append(total_liabilities / equity)
            
            if total_assets > 0:
                roas.append((net_income / total_assets) * 100)
            
            if current_liabilities > 0:
                current_ratios.append(current_assets / current_liabilities)
        
        conn.close()
        
        if not revenues:
            return None
        
        # Calculate sector aggregates
        return SectorBenchmark(
            sector=sector,
            companies_count=len(revenues),
            avg_revenue=statistics.mean(revenues) if revenues else 0,
            median_revenue=statistics.median(revenues) if revenues else 0,
            avg_net_margin=statistics.mean(net_margins) if net_margins else 0,
            median_net_margin=statistics.median(net_margins) if net_margins else 0,
            avg_operating_margin=statistics.mean(operating_margins) if operating_margins else 0,
            median_operating_margin=statistics.median(operating_margins) if operating_margins else 0,
            avg_roe=statistics.mean(roes) if roes else 0,
            median_roe=statistics.median(roes) if roes else 0,
            avg_roa=statistics.mean(roas) if roas else 0,
            median_roa=statistics.median(roas) if roas else 0,
            avg_debt_to_equity=statistics.mean(debt_to_equities) if debt_to_equities else 0,
            median_debt_to_equity=statistics.median(debt_to_equities) if debt_to_equities else 0,
            avg_current_ratio=statistics.mean(current_ratios) if current_ratios else 0,
            median_current_ratio=statistics.median(current_ratios) if current_ratios else 0,
        )
    
    def compare_company_to_sector(self, ticker: str, fiscal_year: int = 2024) -> Optional[CompanyVsSector]:
        """
        Compare a company's performance to its sector benchmarks.
        
        Args:
            ticker: Company ticker symbol
            fiscal_year: Year to compare
            
        Returns:
            CompanyVsSector with detailed comparison
        """
        sector = self.get_company_sector(ticker)
        if not sector:
            LOGGER.warning(f"Ticker {ticker} not found in sector map")
            return None
        
        # Get sector benchmarks
        benchmarks = self.calculate_sector_benchmarks(sector, fiscal_year)
        if not benchmarks:
            return None
        
        # Get company metrics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT company_name FROM ticker_aliases WHERE ticker = ?
        """, (ticker,))
        result = cursor.fetchone()
        company_name = result[0] if result else ticker
        
        query = """
            SELECT metric, value
            FROM metric_snapshots
            WHERE ticker = ? AND end_year = ?
        """
        cursor.execute(query, (ticker, fiscal_year))
        metrics = dict(cursor.fetchall())
        conn.close()
        
        if not metrics:
            return None
        
        # Calculate percentile ranks within sector
        percentile_ranks = self._calculate_percentile_ranks(
            ticker, sector, fiscal_year, metrics
        )
        
        return CompanyVsSector(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            metrics=metrics,
            sector_benchmarks=benchmarks,
            percentile_ranks=percentile_ranks,
        )
    
    def _calculate_percentile_ranks(
        self, ticker: str, sector: str, fiscal_year: int, company_metrics: Dict
    ) -> Dict[str, float]:
        """Calculate where company ranks in sector (0-100 percentile)."""
        companies = self.get_sector_companies(sector)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        percentiles = {}
        
        # Revenue percentile
        query = """
            SELECT ticker, value
            FROM metric_snapshots
            WHERE ticker IN ({}) AND end_year = ? AND metric = 'revenue'
        """.format(','.join('?' * len(companies)))
        cursor.execute(query, companies + [fiscal_year])
        revenues = {t: v for t, v in cursor.fetchall()}
        
        if ticker in revenues and revenues:
            company_revenue = revenues[ticker]
            sorted_revenues = sorted(revenues.values())
            rank = sorted_revenues.index(company_revenue) + 1
            percentiles['revenue'] = (rank / len(sorted_revenues)) * 100
        
        conn.close()
        return percentiles
    
    def get_top_performers_by_sector(
        self, sector: str, metric: str = 'revenue', limit: int = 10, fiscal_year: int = 2024
    ) -> List[Tuple[str, float]]:
        """
        Get top performing companies in a sector by a specific metric.
        
        Args:
            sector: Sector name
            metric: Metric to rank by (e.g., 'revenue', 'net_income')
            limit: Number of top companies to return
            fiscal_year: Year to analyze
            
        Returns:
            List of (ticker, value) tuples sorted by metric descending
        """
        companies = self.get_sector_companies(sector)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT ticker, value
            FROM metric_snapshots
            WHERE ticker IN ({}) AND end_year = ? AND metric = ?
            ORDER BY value DESC
            LIMIT ?
        """.format(','.join('?' * len(companies)))
        
        cursor.execute(query, companies + [fiscal_year, metric, limit])
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_sector_growth_trends(self, sector: str, years: int = 5) -> Dict[int, Dict[str, float]]:
        """
        Get year-over-year growth trends for a sector.
        
        Args:
            sector: Sector name
            years: Number of years of history to include
            
        Returns:
            Dict mapping year to aggregated sector metrics
        """
        companies = self.get_sector_companies(sector)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_year = 2024
        trends = {}
        
        for year in range(current_year - years + 1, current_year + 1):
            query = """
                SELECT metric, AVG(value) as avg_value
                FROM metric_snapshots
                WHERE ticker IN ({}) AND end_year = ?
                AND metric IN ('revenue', 'net_income', 'operating_income')
                GROUP BY metric
            """.format(','.join('?' * len(companies)))
            
            cursor.execute(query, companies + [year])
            year_metrics = dict(cursor.fetchall())
            trends[year] = year_metrics
        
        conn.close()
        return trends


def get_sector_analytics(db_path: str) -> SectorAnalytics:
    """Factory function to create SectorAnalytics instance."""
    return SectorAnalytics(db_path)

