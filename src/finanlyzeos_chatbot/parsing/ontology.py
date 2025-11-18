"""Shared ontology helpers for natural-language parsing."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict

METRIC_SYNONYMS: Dict[str, str] = {
    # Revenue / sales
    "revenue": "revenue",
    "sales": "revenue",
    "top line": "revenue",
    "topline": "revenue",
    "rev": "revenue",
    # NEW: Natural language revenue variations
    "money they make": "revenue",
    "money they made": "revenue",
    "money made": "revenue",
    "how much they make": "revenue",
    "how much they made": "revenue",
    "money did": "revenue",  # "how much money did X make"
    "make": "revenue",  # Contextual: "how much did they make"
    "total revenue": "revenue",
    "net revenue": "revenue",
    "gross revenue": "revenue",
    "total sales": "revenue",
    "sales figures": "revenue",
    
    # Profitability
    "net income": "net_income",
    "net profit": "net_income",
    "profit": "net_income",
    "earnings": "net_income",
    "bottom line": "net_income",
    # NEW: Natural language profit variations
    "how much profit": "net_income",
    "how much they earn": "net_income",
    "how much they earned": "net_income",
    "net earnings": "net_income",
    "total profit": "net_income",
    "total earnings": "net_income",
    
    # Earnings per share
    "earnings per share": "eps_diluted",
    "eps": "eps_diluted",
    "diluted eps": "eps_diluted",
    # NEW: EPS variations
    "earnings a share": "eps_diluted",
    "profit per share": "eps_diluted",
    "eps diluted": "eps_diluted",
    
    # Operating metrics
    "ebitda": "ebitda",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "ebit": "operating_income",
    "gross profit": "gross_profit",
    "gross margin": "gross_margin",
    "operating margin": "operating_margin",
    "net margin": "net_margin",
    "profit margin": "net_margin",
    
    # NEW: Margin and profitability natural language
    "profitability": "net_margin",
    "how profitable": "net_margin",
    "how profitable are they": "net_margin",
    "profit margins": "net_margin",
    "profitability margin": "net_margin",
    "margins": "net_margin",
    "operating margins": "operating_margin",
    "gross margins": "gross_margin",
    
    # Cash flow & returns
    "free cash flow": "free_cash_flow",
    "fcf": "free_cash_flow",
    # NEW: Cash flow natural language
    "cash generated": "free_cash_flow",
    "cash they make": "free_cash_flow",
    "cash they generate": "free_cash_flow",
    "cash generation": "free_cash_flow",
    "free cash": "free_cash_flow",
    "cash does": "free_cash_flow",  # "how much cash does X generate"
    "generate": "free_cash_flow",  # Contextual: "how much cash does X generate"
    "cash from operations": "cash_operations",
    "operating cash flow": "cash_operations",
    "cash flow from operations": "cash_operations",
    "cash flow from ops": "cash_operations",
    "operational cash flow": "cash_operations",
    
    # Returns
    "cash conversion": "cash_conversion",
    "return on equity": "roe",
    "roe": "roe",
    # NEW: ROE variations
    "return on shareholders equity": "roe",
    "shareholder returns": "roe",
    "equity returns": "roe",
    
    "return on assets": "roa",
    "roa": "roa",
    # NEW: ROA variations
    "asset returns": "roa",
    "return on total assets": "roa",
    
    "return on invested capital": "roic",
    "roic": "roic",
    # NEW: ROIC variations
    "return on investment": "roic",
    "roi": "roic",
    "return on capital": "roic",
    "investment return": "roic",
    "invested capital returns": "roic",
    
    # Valuation
    "pe": "pe_ratio",
    "p/e": "pe_ratio",
    "price to earnings": "pe_ratio",
    "pe ratio": "pe_ratio",
    "price earnings": "pe_ratio",
    # NEW: P/E natural language
    "price earnings ratio": "pe_ratio",
    "earnings multiple": "pe_ratio",
    "trading at": "pe_ratio",
    "trading multiple": "pe_ratio",
    "p e ratio": "pe_ratio",
    "p to e": "pe_ratio",
    
    "ev/ebitda": "ev_ebitda",
    "enterprise value to ebitda": "ev_ebitda",
    # NEW: EV/EBITDA variations
    "ev ebitda": "ev_ebitda",
    "enterprise value": "ev_ebitda",
    "ev multiple": "ev_ebitda",
    
    "pb": "pb_ratio",
    "p/b": "pb_ratio",
    "price to book": "pb_ratio",
    # NEW: P/B variations
    "price book": "pb_ratio",
    "price to book value": "pb_ratio",
    "book value multiple": "pb_ratio",
    
    "peg": "peg_ratio",
    "peg ratio": "peg_ratio",
    # NEW: PEG variations
    "price earnings growth": "peg_ratio",
    "pe to growth": "peg_ratio",
    
    # NEW: General valuation terms
    "valuation": "market_cap",
    "how much they worth": "market_cap",
    "how much are they worth": "market_cap",
    "worth": "market_cap",
    "value": "market_cap",
    "market value": "market_cap",
    "market capitalization": "market_cap",
    "market cap": "market_cap",
    
    # Shareholder returns
    "dividend yield": "dividend_yield",
    # NEW: Dividend variations
    "dividends": "dividend_yield",
    "dividend": "dividend_yield",
    "div yield": "dividend_yield",
    "dividend payout": "dividend_yield",
    
    "tsr": "tsr",
    "total shareholder return": "tsr",
    # NEW: TSR variations
    "shareholder return": "tsr",
    "total return": "tsr",
    "stock return": "tsr",
    
    "buyback": "share_buyback_intensity",
    "repurchase": "share_buyback_intensity",
    "share repurchase": "share_buyback_intensity",
    # NEW: Buyback variations
    "buybacks": "share_buyback_intensity",
    "stock buyback": "share_buyback_intensity",
    "share buyback": "share_buyback_intensity",
    
    # NEW: Growth metrics (natural language)
    "growth": "revenue_growth",
    "growth rate": "revenue_growth",
    "how fast they growing": "revenue_growth",
    "how fast are they growing": "revenue_growth",
    "growing": "revenue_growth",
    "expansion": "revenue_growth",
    "revenue growth": "revenue_growth",
    "sales growth": "revenue_growth",
    "top line growth": "revenue_growth",
    
    # NEW: Leverage/debt metrics
    "debt": "debt_equity",
    "debt level": "debt_equity",
    "how much debt": "debt_equity",
    "leverage": "debt_equity",
    "debt burden": "debt_equity",
    "financial leverage": "debt_equity",
    "debt to equity": "debt_equity",
    "debt equity": "debt_equity",
    "debt equity ratio": "debt_equity",
    "d/e": "debt_equity",
    "leveraged": "debt_equity",
    
    # NEW: Performance metrics
    "performance": "net_income",
    "how they performing": "net_income",
    "how are they performing": "net_income",
    "doing": "net_income",
    "how they doing": "net_income",
    "how are they doing": "net_income",
    "performing": "net_income",  # "how is X performing"
    "is performing": "net_income",  # Explicit pattern
    "financial performance": "net_income",
    "business performance": "net_income",
    "company performance": "net_income",
    
    # NEW: Assets & Balance Sheet
    "assets": "total_assets",
    "total assets": "total_assets",
    "asset base": "total_assets",
    "asset value": "total_assets",
    "how much assets": "total_assets",
    
    "liabilities": "total_liabilities",
    "total liabilities": "total_liabilities",
    "how much debt they owe": "total_liabilities",
    "obligations": "total_liabilities",
    
    "equity": "shareholders_equity",
    "shareholders equity": "shareholders_equity",
    "shareholder equity": "shareholders_equity",
    "book value": "shareholders_equity",
    "owner equity": "shareholders_equity",
    
    # NEW: Liquidity metrics
    "liquidity": "current_ratio",
    "how liquid": "current_ratio",
    "liquid": "current_ratio",
    "current ratio": "current_ratio",
    "quick ratio": "quick_ratio",
    "acid test": "quick_ratio",
    
    # NEW: Efficiency metrics
    "efficiency": "asset_turnover",
    "how efficient": "asset_turnover",
    "asset turnover": "asset_turnover",
    "asset utilization": "asset_turnover",
    "inventory turnover": "inventory_turnover",
    
    # NEW: Market metrics
    "stock price": "stock_price",
    "share price": "stock_price",
    "price": "stock_price",
    "trading at": "stock_price",
    "current price": "stock_price",
    
    "volume": "trading_volume",
    "trading volume": "trading_volume",
    "share volume": "trading_volume",
    "daily volume": "trading_volume",
    
    # NEW: Risk metrics
    "risk": "beta",
    "volatility": "beta",
    "how risky": "beta",
    "beta": "beta",
    "market risk": "beta",
    "price volatility": "beta",
    
    # NEW: Quality metrics
    "quality": "roe",
    "financial quality": "roe",
    "business quality": "roe",
    "how good": "roe",
    "how strong": "roe",
    
    # NEW: Sustainability metrics
    "sustainable": "debt_equity",
    "sustainability": "debt_equity",
    "how sustainable": "debt_equity",
    "financial health": "debt_equity",
    "financial strength": "debt_equity",
    "how healthy": "debt_equity",
    
    # NEW: Investment metrics
    "investment": "roic",
    "investor returns": "roic",
    "investment returns": "roic",
    "capital returns": "roic",
    "return on capital": "roic",
    
    # NEW: Cash metrics
    "cash": "cash_and_equivalents",
    "cash on hand": "cash_and_equivalents",
    "cash reserves": "cash_and_equivalents",
    "how much cash": "cash_and_equivalents",
    "cash position": "cash_and_equivalents",
    "cash holdings": "cash_and_equivalents",
    
    # NEW: Expense metrics
    "expenses": "operating_expenses",
    "costs": "operating_expenses",
    "operating expenses": "operating_expenses",
    "opex": "operating_expenses",
    "how much they spend": "operating_expenses",
    "spending": "operating_expenses",
    
    # NEW: Investment spending
    "capex": "capex",
    "capital expenditure": "capex",
    "capital spending": "capex",
    "investment spending": "capex",
    "how much they invest": "capex",
    
    # NEW: Research & Development
    "r&d": "r_and_d",
    "research and development": "r_and_d",
    "research development": "r_and_d",
    "rd": "r_and_d",
    "how much on research": "r_and_d",
    
    # NEW: Employee metrics
    "employees": "employee_count",
    "workforce": "employee_count",
    "headcount": "employee_count",
    "how many employees": "employee_count",
    "staff": "employee_count",
    
    # NEW: Revenue breakdown
    "revenue breakdown": "revenue",
    "sales breakdown": "revenue",
    "revenue by segment": "revenue",
    "sales by segment": "revenue",
    "revenue sources": "revenue",
    "where revenue comes from": "revenue",
    
    # NEW: Geographic metrics
    "geographic": "revenue",
    "by region": "revenue",
    "by geography": "revenue",
    "international": "revenue",
    "domestic": "revenue",
    
    # NEW: Product/service metrics
    "products": "revenue",
    "services": "revenue",
    "product revenue": "revenue",
    "service revenue": "revenue",
    
    # NEW: Customer metrics
    "customers": "revenue",
    "customer base": "revenue",
    "customer count": "revenue",
    "how many customers": "revenue",
    
    # NEW: Market share
    "market share": "revenue",
    "market position": "revenue",
    "market dominance": "revenue",
    "competitive position": "revenue",
    
    # NEW: Aggregation metrics
    "sum": "revenue",
    "total": "revenue",
    "aggregate": "revenue",
    "combined": "revenue",
    "collective": "revenue",
    "cumulative": "revenue",
    "overall": "revenue",
    
    # NEW: Average/Mean metrics
    "average": "revenue",
    "mean": "revenue",
    "median": "revenue",
    "midpoint": "revenue",
    
    # NEW: Percentage/Share metrics
    "percent": "revenue",
    "percentage": "revenue",
    "share": "revenue",
    "portion": "revenue",
    "fraction": "revenue",
    "ratio": "revenue",
    "proportion": "revenue",
    
    # NEW: Change magnitude
    "increase by": "revenue",
    "decrease by": "revenue",
    "grow by": "revenue",
    "shrink by": "revenue",
    "rise by": "revenue",
    "fall by": "revenue",
    "up by": "revenue",
    "down by": "revenue",
    
    # NEW: Relative position
    "above average": "revenue",
    "below average": "revenue",
    "above median": "revenue",
    "below median": "revenue",
    "top percentile": "revenue",
    "bottom percentile": "revenue",
    
    # NEW: Temporal modifiers
    "recently": "revenue",
    "lately": "revenue",
    "currently": "revenue",
    "previously": "revenue",
    "historically": "revenue",
    "going forward": "revenue",
    "in the future": "revenue",
    
    # NEW: Sector/Industry
    "sector": "revenue",
    "industry": "revenue",
    "sector wide": "revenue",
    "industry wide": "revenue",
    "across sectors": "revenue",
    "across industries": "revenue",
    
    # NEW: Multi-company
    "all of them": "revenue",
    "both of them": "revenue",
    "together": "revenue",
    "combined": "revenue",
    "collectively": "revenue",
    "as a group": "revenue",
    "as a whole": "revenue",
    
    # NEW: Causal
    "because of": "revenue",
    "due to": "revenue",
    "as a result of": "revenue",
    "owing to": "revenue",
    "attributed to": "revenue",
    "caused by": "revenue",
    "resulted from": "revenue",
    "led to": "revenue",
    "resulted in": "revenue",
    
    # NEW: Negation
    "not profitable": "net_income",
    "not growing": "revenue_growth",
    "no revenue": "revenue",
    "no profit": "net_income",
    "lack of": "revenue",
    "missing": "revenue",
    "without": "revenue",
    
    # NEW: Progressive/Adverb
    "increasingly": "revenue_growth",
    "decreasingly": "revenue_growth",
    "gradually": "revenue_growth",
    "rapidly": "revenue_growth",
    "steadily": "revenue_growth",
    "consistently": "revenue_growth",
    "dramatically": "revenue_growth",
    "significantly": "revenue_growth",
    
    # NEW: Certainty
    "definitely": "revenue",
    "certainly": "revenue",
    "probably": "revenue",
    "possibly": "revenue",
    "likely": "revenue",
    "unlikely": "revenue",
    
    # NEW: Frequency
    "always": "revenue",
    "often": "revenue",
    "sometimes": "revenue",
    "rarely": "revenue",
    "never": "revenue",
    "usually": "revenue",
    "typically": "revenue",
    "frequently": "revenue",
}


def _normalize_alias(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _simplify_company_name(name: str) -> str:
    simplified = re.sub(
        r"\b(the|incorporated|inc|corporation|corp|company|co|plc|ltd|limited|group|holding|holdings)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )
    simplified = re.sub(r"\s+", " ", simplified).strip()
    return simplified


@lru_cache(maxsize=1)
def load_ticker_aliases() -> Dict[str, str]:
    """Load company name aliases from documentation."""
    base_path = Path(__file__).resolve().parents[3]
    mapping: Dict[str, str] = {}
    source = base_path / "docs" / "ticker_names.md"
    if not source.exists():
        return mapping

    line_pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z.-]+)\)")
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        match = line_pattern.match(raw_line.strip())
        if not match:
            continue
        name = match.group("name")
        ticker = match.group("ticker").upper()

        aliases = {
            _normalize_alias(name),
            _normalize_alias(_simplify_company_name(name)),
            _normalize_alias(ticker),
        }

        words = _simplify_company_name(name).split()
        if words:
            aliases.add(_normalize_alias(words[0]))

        for alias in aliases:
            if not alias:
                continue
            mapping.setdefault(alias, ticker)

    return mapping


TICKER_ALIASES: Dict[str, str] = load_ticker_aliases()

for canonical in list({v for v in METRIC_SYNONYMS.values()}):
    METRIC_SYNONYMS.setdefault(canonical, canonical)
