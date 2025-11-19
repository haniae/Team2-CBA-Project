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
    "netincome": "net_income",
    "net profit": "net_income",
    "profit": "net_income",
    "profi": "net_income",  # Common misspelling (but may also map to gross_profit based on context)
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
    # Common misspellings
    "earnngs per share": "eps_diluted",
    "earnings per shar": "eps_diluted",
    "earnngs per shar": "eps_diluted",
    
    # Operating metrics
    "ebitda": "ebitda",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "ebit": "operating_income",
    "gross profit": "gross_profit",
    "gross profi": "gross_profit",  # Common misspelling
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
    "margin": "net_margin",
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
    # Common misspellings
    "retrn on equity": "roe",
    "return on equty": "roe",
    "retrn on equty": "roe",
    
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
    "p e": "pe_ratio",
    "P E": "pe_ratio",
    "price to earnings": "pe_ratio",
    "price/earnings": "pe_ratio",  # Slash variation
    "pe ratio": "pe_ratio",
    "price earnings": "pe_ratio",
    # NEW: P/E natural language
    "price earnings ratio": "pe_ratio",
    "earnings multiple": "pe_ratio",
    "trading at": "pe_ratio",
    "trading multiple": "pe_ratio",
    "p e ratio": "pe_ratio",
    "p to e": "pe_ratio",
    # Common misspellings
    "price to earnngs": "pe_ratio",
    "price to earnigs": "pe_ratio",
    "prie to earnings": "pe_ratio",
    
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
    "marketcap": "market_cap",
    
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
    "debt to equity": "debt_equity",
    "debt equity ratio": "debt_equity",
    "leverage": "debt_equity",
    "leverage ratio": "debt_equity",
    "financial leverage": "debt_equity",
    "gearing": "debt_equity",
    "gearing ratio": "debt_equity",
    
    # NEW: Credit and solvency metrics
    "credit rating": "credit_rating",
    "credit score": "credit_rating",
    "bond rating": "credit_rating",
    "default risk": "credit_rating",
    "solvency": "debt_equity",
    "solvency ratio": "debt_equity",
    "interest coverage": "interest_coverage",
    "times interest earned": "interest_coverage",
    "debt service coverage": "interest_coverage",
    
    # NEW: Liquidity metrics
    "current ratio": "current_ratio",
    "currentratio": "current_ratio",
    "working capital": "working_capital",
    "workingcapital": "working_capital",
    "wc": "working_capital",
    "quick ratio": "quick_ratio",
    "quickratio": "quick_ratio",
    "acid test": "quick_ratio",
    "liquidity": "current_ratio",
    "liquidity ratio": "current_ratio",
    "cash position": "cash",
    "cash reserves": "cash",
    "cash on hand": "cash",
    
    # NEW: Capital structure metrics
    "capital structure": "debt_equity",
    "equity structure": "equity",
    "share capital": "equity",
    "outstanding shares": "shares_outstanding",
    "shares outstanding": "shares_outstanding",
    "authorized shares": "shares_outstanding",
    "share buyback": "share_buyback_intensity",
    "stock buyback": "share_buyback_intensity",
    "share repurchase": "share_buyback_intensity",
    "buyback program": "share_buyback_intensity",
    "capital allocation": "share_buyback_intensity",
    "capital expenditure": "capex",
    "capex": "capex",
    "capital spending": "capex",
    "investments": "capex",
    
    # NEW: Operating metrics
    "operating cash flow": "cash_operations",
    "OCF": "cash_operations",
    "cash from operations": "cash_operations",
    "operating expenses": "operating_expenses",
    "opex": "operating_expenses",
    "operating costs": "operating_expenses",
    "R&D": "rd_expenses",
    "research and development": "rd_expenses",
    "R&D expenses": "rd_expenses",
    "research expenses": "rd_expenses",
    "development expenses": "rd_expenses",
    
    # NEW: Efficiency metrics
    "asset turnover": "asset_turnover",
    "assetturnover": "asset_turnover",
    "inventory turnover": "inventory_turnover",
    "inventoryturnover": "inventory_turnover",
    "receivables turnover": "receivables_turnover",
    "days sales outstanding": "dsi",
    "DSO": "dsi",
    "days inventory": "dsi",
    "inventory days": "dsi",
    
    # NEW: Valuation multiples
    "price to sales": "price_to_sales",
    "P/S": "price_to_sales",
    "P/S ratio": "price_to_sales",
    "price sales": "price_to_sales",
    "sales multiple": "price_to_sales",
    "EV/Sales": "ev_sales",
    "enterprise value to sales": "ev_sales",
    "EV/Revenue": "ev_sales",
    "enterprise value to revenue": "ev_sales",
    
    # NEW: Profitability ratios
    "gross profit": "gross_profit",
    "grossprofit": "gross_profit",
    "gross profit margin": "gross_margin",
    "operating profit": "operating_income",
    "operating profit margin": "operating_margin",
    "net profit margin": "net_margin",
    "profitability": "net_margin",
    "margins": "net_margin",
    
    # NEW: Market metrics
    "market share": "market_share",
    "market position": "market_share",
    "competitive position": "market_share",
    "beta": "beta",
    "volatility": "beta",
    "stock volatility": "beta",
    
    # NEW: Dividend metrics
    "dividend per share": "dividend_per_share",
    "DPS": "dividend_per_share",
    "dividend payout ratio": "payout_ratio",
    "payout ratio": "payout_ratio",
    "dividend coverage": "payout_ratio",
    
    # NEW: Economic indicators
    "GDP": "gdp",
    "gross domestic product": "gdp",
    "inflation": "inflation",
    "CPI": "inflation",
    "consumer price index": "inflation",
    "unemployment": "unemployment",
    "unemployment rate": "unemployment",
    "interest rate": "interest_rate",
    "fed rate": "interest_rate",
    "federal funds rate": "interest_rate",
    
    # NEW: ESG metrics
    "ESG score": "esg_score",
    "ESG rating": "esg_score",
    "environmental score": "esg_score",
    "social score": "esg_score",
    "governance score": "esg_score",
    "carbon footprint": "carbon_footprint",
    "emissions": "carbon_footprint",
    "GHG emissions": "carbon_footprint",
    "greenhouse gas": "carbon_footprint",
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
    "r&d": "rd_expenses",  # Map to rd_expenses for consistency
    "research development": "rd_expenses",  # Alternative phrasing
    "rd": "rd_expenses",  # Abbreviation
    "how much on research": "rd_expenses",
    
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
    
    # Missing metrics - comprehensive natural language support
    
    # Adjusted EBITDA
    "adjusted ebitda": "adjusted_ebitda",
    "adjusted-ebitda": "adjusted_ebitda",
    "adj ebitda": "adjusted_ebitda",
    "normalized ebitda": "adjusted_ebitda",
    
    # Adjusted EBITDA Margin
    "adjusted ebitda margin": "adjusted_ebitda_margin",
    "adjusted-ebitda-margin": "adjusted_ebitda_margin",
    "adj ebitda margin": "adjusted_ebitda_margin",
    "normalized ebitda margin": "adjusted_ebitda_margin",
    
    # Capital Expenditures (already has "capex" but adding more)
    "capital expenditures": "capital_expenditures",
    "capital-expenditures": "capital_expenditures",
    "cap ex": "capital_expenditures",
    "cap-ex": "capital_expenditures",
    "capital spending": "capital_expenditures",
    "capex spending": "capital_expenditures",
    
    # Cash and Cash Equivalents (already has "cash" but adding more)
    "cash and cash equivalents": "cash_and_cash_equivalents",
    "cash-and-cash-equivalents": "cash_and_cash_equivalents",
    "cash equivalents": "cash_and_cash_equivalents",
    "cash & equivalents": "cash_and_cash_equivalents",
    "total cash": "cash_and_cash_equivalents",
    
    # Cash from Financing
    "cash from financing": "cash_from_financing",
    "cash-from-financing": "cash_from_financing",
    "financing cash flow": "cash_from_financing",
    "cash flow from financing": "cash_from_financing",
    "CFF": "cash_from_financing",
    "cff": "cash_from_financing",
    
    # Cash from Operations (already has some but adding more)
    "cash from operations": "cash_from_operations",
    "cash-from-operations": "cash_from_operations",
    "operating cash flow": "cash_from_operations",
    "cash flow from operations": "cash_from_operations",
    "operational cash flow": "cash_from_operations",
    "CFO": "cash_from_operations",
    "cfo": "cash_from_operations",
    
    # Current Assets
    "current assets": "current_assets",
    "current-assets": "current_assets",
    "short term assets": "current_assets",
    "short-term assets": "current_assets",
    
    # Current Liabilities
    "current liabilities": "current_liabilities",
    "current-liabilities": "current_liabilities",
    "short term liabilities": "current_liabilities",
    "short-term liabilities": "current_liabilities",
    
    # Debt to Equity (mapping to correct ID)
    "debt to equity": "debt_to_equity",
    "debt-to-equity": "debt_to_equity",
    "debt/equity": "debt_to_equity",
    "D/E ratio": "debt_to_equity",
    "d/e ratio": "debt_to_equity",
    "debt equity": "debt_to_equity",
    # Common misspellings
    "deb to equity": "debt_to_equity",
    "debt to equty": "debt_to_equity",
    "deb to equty": "debt_to_equity",
    
    # Depreciation and Amortization
    "depreciation and amortization": "depreciation_and_amortization",
    "depreciation-and-amortization": "depreciation_and_amortization",
    "D&A": "depreciation_and_amortization",
    "d&a": "depreciation_and_amortization",
    "depreciation amortization": "depreciation_and_amortization",
    "depreciation": "depreciation_and_amortization",
    "amortization": "depreciation_and_amortization",
    
    # Dividends Paid
    "dividends paid": "dividends_paid",
    "dividends-paid": "dividends_paid",
    "total dividends": "dividends_paid",
    "dividend payments": "dividends_paid",
    "dividend payout": "dividends_paid",
    
    # Dividends Per Share
    "dividends per share": "dividends_per_share",
    "dividends-per-share": "dividends_per_share",
    "DPS": "dividends_per_share",
    "dps": "dividends_per_share",
    "dividend per share": "dividends_per_share",
    
    # EBIT (already has "operating income" but adding EBIT specifically)
    "EBIT": "ebit",
    "ebit": "ebit",
    "earnings before interest and tax": "ebit",
    "operating earnings": "ebit",
    
    # EBITDA Growth
    "ebitda growth": "ebitda_growth",
    "ebitda-growth": "ebitda_growth",
    "ebitda growth rate": "ebitda_growth",
    "ebitda expansion": "ebitda_growth",
    
    # EBITDA Margin
    "ebitda margin": "ebitda_margin",
    "ebitda-margin": "ebitda_margin",
    "ebitda profitability": "ebitda_margin",
    "ebitda margins": "ebitda_margin",
    
    # Enterprise Value
    "enterprise value": "enterprise_value",
    "enterprise-value": "enterprise_value",
    "EV": "enterprise_value",
    "ev": "enterprise_value",
    "firm value": "enterprise_value",
    "total enterprise value": "enterprise_value",
    
    # EPS Basic
    "eps basic": "eps_basic",
    "eps-basic": "eps_basic",
    "basic eps": "eps_basic",
    "basic earnings per share": "eps_basic",
    "basic EPS": "eps_basic",
    
    # EPS CAGR
    "eps cagr": "eps_cagr",
    "eps-cagr": "eps_cagr",
    "eps compound annual growth": "eps_cagr",
    "eps growth rate": "eps_cagr",
    "earnings per share cagr": "eps_cagr",
    
    # EPS CAGR 3Y
    "eps cagr 3y": "eps_cagr_3y",
    "eps-cagr-3y": "eps_cagr_3y",
    "eps cagr 3 year": "eps_cagr_3y",
    "eps 3 year cagr": "eps_cagr_3y",
    "3 year eps cagr": "eps_cagr_3y",
    
    # Free Cash Flow Margin
    "free cash flow margin": "free_cash_flow_margin",
    "free-cash-flow-margin": "free_cash_flow_margin",
    "FCF margin": "free_cash_flow_margin",
    "fcf margin": "free_cash_flow_margin",
    "fcf margins": "free_cash_flow_margin",
    "free cash flow margins": "free_cash_flow_margin",
    # Common misspellings
    "free cash flow margn": "free_cash_flow_margin",
    "free cash flow margen": "free_cash_flow_margin",
    "free cash flow marginn": "free_cash_flow_margin",
    
    # Income Tax Expense
    "income tax expense": "income_tax_expense",
    "income-tax-expense": "income_tax_expense",
    "tax expense": "income_tax_expense",
    "income taxes": "income_tax_expense",
    "taxes": "income_tax_expense",
    
    # Interest Expense
    "interest expense": "interest_expense",
    "interest-expense": "interest_expense",
    "interest cost": "interest_expense",
    "interest paid": "interest_expense",
    "interest charges": "interest_expense",
    
    # Long Term Debt
    "long term debt": "long_term_debt",
    "long-term-debt": "long_term_debt",
    "long term liabilities": "long_term_debt",
    "long-term liabilities": "long_term_debt",
    "LTD": "long_term_debt",
    "ltd": "long_term_debt",
    
    # Long Term Debt Current
    "long term debt current": "long_term_debt_current",
    "long-term-debt-current": "long_term_debt_current",
    "current portion of long term debt": "long_term_debt_current",
    "current long term debt": "long_term_debt_current",
    
    # Price
    "stock price": "price",
    "share price": "price",
    "price": "price",
    "current price": "price",
    "trading price": "price",
    
    # Profit Margin (already has "net margin" but adding profit margin specifically)
    "profit margin": "profit_margin",
    "profit-margin": "profit_margin",
    "profit margins": "profit_margin",
    "net profit margin": "profit_margin",
    
    # P/S Ratio
    "P/S": "ps_ratio",
    "p/s": "ps_ratio",
    "P S": "ps_ratio",
    "p s": "ps_ratio",
    "ps ratio": "ps_ratio",
    "ps-ratio": "ps_ratio",
    "price to sales": "ps_ratio",
    "price-to-sales": "ps_ratio",
    "price/sales": "ps_ratio",
    "price sales": "ps_ratio",
    
    # Return on Assets (already has "roa" but adding full name)
    "return on assets": "return_on_assets",
    "return-on-assets": "return_on_assets",
    "ROA": "return_on_assets",
    "roa": "return_on_assets",
    "asset returns": "return_on_assets",
    
    # Return on Equity (already has "roe" but adding full name)
    "return on equity": "return_on_equity",
    "return-on-equity": "return_on_equity",
    "ROE": "return_on_equity",
    "roe": "return_on_equity",
    "equity returns": "return_on_equity",
    
    # Return on Invested Capital (already has "roic" but adding full name)
    "return on invested capital": "return_on_invested_capital",
    "return-on-invested-capital": "return_on_invested_capital",
    "ROIC": "return_on_invested_capital",
    "roic": "return_on_invested_capital",
    "ROI": "return_on_invested_capital",
    "roi": "return_on_invested_capital",
    "capital returns": "return_on_invested_capital",
    
    # Revenue CAGR
    "revenue cagr": "revenue_cagr",
    "revenue-cagr": "revenue_cagr",
    "revenue compound annual growth": "revenue_cagr",
    "revenue growth rate": "revenue_cagr",
    "sales cagr": "revenue_cagr",
    
    # Revenue CAGR 3Y
    "revenue cagr 3y": "revenue_cagr_3y",
    "revenue-cagr-3y": "revenue_cagr_3y",
    "revenue cagr 3 year": "revenue_cagr_3y",
    "revenue 3 year cagr": "revenue_cagr_3y",
    "3 year revenue cagr": "revenue_cagr_3y",
    
    # Share Repurchases
    "share repurchases": "share_repurchases",
    "share-repurchases": "share_repurchases",
    "stock repurchases": "share_repurchases",
    "share buybacks": "share_repurchases",
    "stock buybacks": "share_repurchases",
    "buybacks": "share_repurchases",
    "repurchases": "share_repurchases",
    
    # Short Term Debt
    "short term debt": "short_term_debt",
    "short-term-debt": "short_term_debt",
    "STD": "short_term_debt",
    "std": "short_term_debt",
    "current debt": "short_term_debt",
    
    # Total Debt
    "total debt": "total_debt",
    "total-debt": "total_debt",
    "all debt": "total_debt",
    "combined debt": "total_debt",
    "total borrowings": "total_debt",
    
    # Weighted Avg Diluted Shares
    "weighted avg diluted shares": "weighted_avg_diluted_shares",
    "weighted-avg-diluted-shares": "weighted_avg_diluted_shares",
    "weighted average diluted shares": "weighted_avg_diluted_shares",
    "diluted shares outstanding": "weighted_avg_diluted_shares",
    "average diluted shares": "weighted_avg_diluted_shares",
    
    # Working Capital Change
    "working capital change": "working_capital_change",
    "working-capital-change": "working_capital_change",
    "WC change": "working_capital_change",
    "wc change": "working_capital_change",
    "working capital delta": "working_capital_change",
    "change in working capital": "working_capital_change",
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
