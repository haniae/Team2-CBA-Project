"""Core chatbot orchestration logic with analytics-aware intents."""

from __future__ import annotations

# High-level conversation orchestrator: parses intents, calls the analytics engine, handles
# ingestion commands, and falls back to the configured language model. Used by CLI and web UI.

import copy
import json
import logging
import re
import time
import uuid
from collections import Counter, OrderedDict, defaultdict
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from enum import Enum

import requests

from . import database, tasks
from .data_sources import AuditEvent
from .analytics_engine import AnalyticsEngine
from .config import Settings
from .data_ingestion import IngestionReport, ingest_financial_data
from .help_content import HELP_TEXT
from .llm_client import LLMClient, build_llm_client
from .parsing.parse import parse_to_structured
from .table_renderer import METRIC_DEFINITIONS, render_table_command
from .dashboard_utils import (
    build_cfi_dashboard_payload,
    build_cfi_compare_payload,
    _display_ticker_symbol,
    _normalise_ticker_symbol,
)
from .routing import enhance_structured_parse, should_build_dashboard, EnhancedIntent
from .context_builder import build_financial_context

# Portfolio module imports (combined portfolio.py)
from .portfolio import (
    validate_holdings,
    enrich_holdings_with_fundamentals,
    calculate_portfolio_statistics,
    analyze_exposure,
    brinson_attribution,
    run_equity_drawdown_scenario,
    run_sector_rotation_scenario,
    run_custom_scenario,
    generate_committee_brief,
    EnrichedHolding,
)

LOGGER = logging.getLogger(__name__)

# Enhanced Error Handling
class ErrorCategory(Enum):
    """Error categories for enhanced error handling."""
    TICKER_NOT_FOUND = "ticker_not_found"
    METRIC_NOT_AVAILABLE = "metric_not_available"
    INVALID_PERIOD = "invalid_period"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    PARSING_ERROR = "parsing_error"
    UNKNOWN_ERROR = "unknown_error"

# Enhanced Error Messages with specific guidance
ERROR_MESSAGES = {
    ErrorCategory.TICKER_NOT_FOUND: {
        "message": "I couldn't find the ticker symbol '{ticker}'. Please check the spelling or try a different ticker.",
        "suggestions": [
            "Try searching for the company name instead",
            "Check if the ticker symbol is correct",
            "Use the 'help' command to see available tickers"
        ]
    },
    ErrorCategory.METRIC_NOT_AVAILABLE: {
        "message": "The metric '{metric}' is not available for {ticker}. Available metrics include: {available_metrics}",
        "suggestions": [
            "Try a different metric",
            "Check available metrics with 'help'",
            "Use a different time period"
        ]
    },
    ErrorCategory.INVALID_PERIOD: {
        "message": "The time period '{period}' is not valid. Please use a valid format like '2023', 'Q1 2023', or 'last 3 years'.",
        "suggestions": [
            "Use calendar years (e.g., '2023')",
            "Use quarters (e.g., 'Q1 2023')",
            "Use relative periods (e.g., 'last 3 years')"
        ]
    },
    ErrorCategory.NETWORK_ERROR: {
        "message": "I'm having trouble connecting to the data source. Please try again in a moment.",
        "suggestions": [
            "Check your internet connection",
            "Try again in a few minutes",
            "Contact support if the issue persists"
        ]
    },
    ErrorCategory.DATABASE_ERROR: {
        "message": "There's an issue accessing the financial database. Please try again later.",
        "suggestions": [
            "Try again in a few minutes",
            "Use a different query",
            "Contact support if the issue persists"
        ]
    },
    ErrorCategory.PARSING_ERROR: {
        "message": "I had trouble understanding your request. Please try rephrasing it.",
        "suggestions": [
            "Be more specific about what you want",
            "Use simpler language",
            "Try the 'help' command for examples"
        ]
    },
    ErrorCategory.UNKNOWN_ERROR: {
        "message": "I'm not sure how to help with that yet.",
        "suggestions": [
            "Try rephrasing your question",
            "Use the 'help' command for examples",
            "Be more specific about what you need"
        ]
    }
}

POPULAR_TICKERS: Sequence[str] = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "GS",
)


@dataclass
class _CachedReply:
    """Cached assistant response for prompt reuse."""

    reply: str
    structured: Dict[str, Any]
    created_at: float

# --------------------------------------------------------------------------------------
# Company name → ticker resolver built from SEC company_tickers.json + local aliases
# --------------------------------------------------------------------------------------
class _CompanyNameIndex:
    _SUFFIXES = (
        "inc", "inc.", "corporation", "corp", "corp.", "co", "co.",
        "company", "ltd", "ltd.", "plc", "llc", "lp", "s.a.", "sa",
        "holdings", "holding", "group"
    )

    @staticmethod
    def _normalize(s: str) -> str:
        s = unicodedata.normalize("NFKD", s.lower().strip())
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = re.sub(r"[^a-z0-9 &\-]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        parts = [p for p in s.split(" ") if p]
        while parts and parts[-1] in _CompanyNameIndex._SUFFIXES:
            parts.pop()
        return " ".join(parts)

    def __init__(self) -> None:
        self.by_exact: Dict[str, str] = {}        # normalized name -> ticker
        self.rows: List[tuple[str, str]] = []     # (normalized name, ticker)
        self._add_builtin_aliases()

    def _add_builtin_aliases(self) -> None:
        """Seed the index with a handful of high-usage aliases."""
        extras = {
            # Mega-cap technology
            "apple": "AAPL",
            "apple inc": "AAPL",
            "apple incorporated": "AAPL",
            "apple computer": "AAPL",
            "microsoft": "MSFT",
            "microsoft corp": "MSFT",
            "microsoft corporation": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "alphabet inc": "GOOGL",
            "amazon": "AMZN",
            "amazon.com": "AMZN",
            "meta": "META",
            "facebook": "META",
            "tesla": "TSLA",
            "tesla motors": "TSLA",
            "nvidia": "NVDA",
            "nvidia corporation": "NVDA",
            # Financial heavyweights
            "jpmorgan": "JPM",
            "jpmorgan chase": "JPM",
            "goldman sachs": "GS",
            "bank of america": "BAC",
            # Consumer staples
            "coca cola": "KO",
            "coca-cola": "KO",
            "pepsi": "PEP",
            "pepsico": "PEP",
            # Industrials / others
            "berkshire hathaway": "BRK-B",
            "berkshire": "BRK-B",
        }
        for name, ticker in extras.items():
            norm = self._normalize(name)
            if not norm or not ticker:
                continue
            ticker = ticker.upper()
            if norm not in self.by_exact:
                self.by_exact[norm] = ticker
                self.rows.append((norm, ticker))

    def build_from_sec(self, base_url: str, user_agent: str, timeout: float = 20.0) -> None:
        """Populate the index from database data instead of SEC API to avoid 404 errors."""
        # Use database data instead of SEC API to avoid 404 errors
        try:
            from benchmarkos_chatbot.config import load_settings
            import sqlite3
            
            settings = load_settings()
            with sqlite3.connect(settings.database_path) as conn:
                cursor = conn.execute("SELECT ticker, company_name FROM ticker_aliases")
                ticker_data = cursor.fetchall()
                
                LOGGER.info("Using database data instead of SEC API to avoid 404 errors")
                
                for ticker, company_name in ticker_data:
                    if not company_name or not ticker:
                        continue
                    norm = self._normalize(company_name)
                    if norm:
                        if norm not in self.by_exact or "-" not in ticker:  # prefer common shares
                            self.by_exact[norm] = ticker
                        self.rows.append((norm, ticker))
                        
        except Exception as exc:
            LOGGER.warning("Failed to load ticker data from database: %s", exc)
            # Fallback to empty data instead of SEC API
            LOGGER.info("Using empty ticker data to avoid SEC API 404 errors")

        # friendly short names (seed)
        extras = {
            "alphabet": "GOOGL",
            "google": "GOOGL",
            "meta": "META",
            "facebook": "META",
            "berkshire hathaway": "BRK-B",
            "berkshire": "BRK-B",
            "coca cola": "KO",
            "coca-cola": "KO",
        }
        for k, v in extras.items():
            self.by_exact.setdefault(self._normalize(k), v)

    def load_local_aliases(self, path: str | Path) -> None:
        try:
            p = Path(path)
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                added = 0
                for k, v in (data or {}).items():
                    norm = self._normalize(k)
                    if norm and v and norm not in self.by_exact:
                        self.by_exact[norm] = str(v).upper()
                        self.rows.append((norm, self.by_exact[norm]))
                        added += 1
                LOGGER.info("Loaded %d local name aliases from %s", added, p)
            else:
                LOGGER.warning("Local alias file not found: %s", p)
        except Exception:
            LOGGER.exception("Failed loading local alias file %s", path)

    def resolve(self, phrase: str) -> Optional[str]:
        if not phrase:
            return None
        q = self._normalize(phrase)
        if not q:
            return None

        # 1) exact normalized
        t = self.by_exact.get(q)
        if t:
            return t

        # 2) prefix (e.g., "apple" vs "apple computer")
        for name, tic in self.rows:
            if name.startswith(q):
                return tic

        # 3) contains (e.g., "bank of america" vs "bank of america corp")
        for name, tic in self.rows:
            if q in name:
                return tic

        # 4) light token-overlap score
        q_tokens = set(q.split())
        best, best_score = None, 0.0
        for name, tic in self.rows:
            n_tokens = set(name.split())
            inter = len(q_tokens & n_tokens)
            if not inter:
                continue
            score = inter / max(len(q_tokens), 1)
            if score > best_score:
                best, best_score = tic, score
        return best

    def resolve_fuzzy(
        self,
        phrase: str,
        *,
        n: int = 3,
        cutoff: float = 0.65,
    ) -> List[tuple[str, float]]:
        """Return fuzzy ticker matches ranked by similarity score."""
        norm = self._normalize(phrase)
        if not norm:
            return []

        scored: List[tuple[str, float]] = []
        for name, ticker in self.rows:
            if not name:
                continue
            score = SequenceMatcher(None, norm, name).ratio()
            if score >= cutoff:
                scored.append((ticker, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        unique: List[tuple[str, float]] = []
        seen = set()
        for ticker, score in scored:
            if ticker in seen:
                continue
            unique.append((ticker, score))
            seen.add(ticker)
            if len(unique) >= n:
                break
        return unique


# --------------------------------------------------------------------------------------
# Metric formatting categories mirrored from analytics_engine.generate_summary
# --------------------------------------------------------------------------------------
PERCENT_METRICS = {
    "revenue_cagr_3y",
    "eps_cagr_3y",
    "adjusted_ebitda_margin",
    "return_on_equity",
    "fcf_margin",
    "return_on_assets",
    "operating_margin",
    "net_margin",
    "cash_conversion_ratio",
    "tsr_3y",
    "dividend_yield",
}

MULTIPLE_METRICS = {
    "net_debt_to_ebitda",
    "ev_to_adjusted_ebitda",
    "peg_ratio",
    "working_capital_turnover",
    "buyback_intensity",
    "pe_ratio",
    "pb_ratio",
}

# Metrics highlighted in retrieval-augmented context for the language model.
CONTEXT_SUMMARY_METRICS: Sequence[str] = (
    "revenue",
    "net_income",
    "operating_margin",
    "net_margin",
    "return_on_equity",
    "free_cash_flow",
    "free_cash_flow_margin",
    "pe_ratio",
)

# Enhanced Context Metrics for comprehensive financial analysis
ENHANCED_CONTEXT_SUMMARY_METRICS: Sequence[str] = (
    # Core Financials
    "revenue",
    "net_income", 
    "gross_margin",
    "operating_margin",
    "net_margin",
    "ebitda",
    "ebitda_margin",
    
    # Profitability
    "return_on_equity",
    "return_on_assets",
    "return_on_invested_capital",
    
    # Liquidity
    "current_ratio",
    "quick_ratio",
    "free_cash_flow",
    "free_cash_flow_margin",
    
    # Leverage
    "debt_to_equity",
    "debt_to_assets",
    "interest_coverage_ratio",
    
    # Efficiency
    "asset_turnover",
    "inventory_turnover",
    
    # Growth
    "revenue_growth",
    "earnings_growth",
    
    # Valuation
    "pe_ratio",
    "price_to_book",
    "price_to_sales",
    "market_cap",
    
    # Market
    "beta",
    "volatility"
)

# Enhanced Context Categories for organized financial analysis
CONTEXT_CATEGORIES = {
    "Core Financials": ["revenue", "net_income", "gross_margin", "operating_margin", "net_margin", "ebitda", "ebitda_margin"],
    "Profitability": ["return_on_equity", "return_on_assets", "return_on_invested_capital"],
    "Liquidity": ["current_ratio", "quick_ratio", "free_cash_flow", "free_cash_flow_margin"],
    "Leverage": ["debt_to_equity", "debt_to_assets", "interest_coverage_ratio"],
    "Efficiency": ["asset_turnover", "inventory_turnover"],
    "Growth": ["revenue_growth", "earnings_growth"],
    "Valuation": ["pe_ratio", "price_to_book", "price_to_sales", "market_cap"],
    "Market": ["beta", "volatility"]
}

BENCHMARK_KEY_METRICS: Dict[str, str] = {
    "adjusted_ebitda_margin": "Adjusted EBITDA margin",
    "net_margin": "Adjusted net margin",
    "return_on_equity": "Return on equity",
    "pe_ratio": "P/E ratio",
}
TREND_METRICS: Sequence[str] = (
    "revenue",
    "net_income",
    "free_cash_flow",
    "operating_income",
)

_METRIC_LABEL_MAP: Dict[str, str] = {
    definition.name: definition.description for definition in METRIC_DEFINITIONS
}

_TICKER_TOKEN_PATTERN = re.compile(r"\b[A-Z]{1,5}(?:-[A-Z]{1,2})?\b")
_COMPANY_PHRASE_PATTERN = re.compile(
    r"\b(?:[A-Za-z][A-Za-z&.]+(?:\s+[A-Za-z][A-Za-z&.]+){0,3})\b"
)
_COMMON_WORDS = {
    "AND",
    "OR",
    "THE",
    "A",
    "AN",
    "OF",
    "FOR",
    "WITH",
    "VS",
    "VERSUS",
    "PLEASE",
    "SHOW",
    "ME",
    "TELL",
    "WHAT",
    "HOW",
    "WHY",
    "IS",
    "ARE",
    "ON",
    "IN",
    "TO",
    "HELP",
    # Corporate suffixes that shouldn't be treated as tickers
    "INC",
    "CORP",
    "CO",
    "LTD",
    "LLC",
    "LP",
    "PLC",
    "SA",
    "AG",
    "NV",
    "GROUP",
    "CORPORATION",
    "INCORPORATED",
    "LIMITED",
    "COMPANY",
    "HOLDINGS",
    "HOLDING",
    "SYSTEMS",
    "TECHNOLOGIES",
    "SERVICES",
}

_METRICS_PATTERN = re.compile(r"^metrics(?:(?:\s+for)?\s+)(.+)$", re.IGNORECASE)

FACT_METRIC_ALIASES: Dict[str, str] = {
    "total revenue": "revenue",
    "revenue": "revenue",
    "sales": "revenue",
    "quarterly revenue": "revenue",
    "annual revenue": "revenue",
    "net income": "net_income",
    "quarterly net income": "net_income",
    "net earnings": "net_income",
    "net profit": "net_income",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "gross profit": "gross_profit",
    "gross margin": "gross_margin",
    "earnings per share": "eps",
    "diluted eps": "eps",
    "eps": "eps",
    "free cash flow": "free_cash_flow",
    "fcf": "free_cash_flow",
    "ebitda": "ebitda",
    "adjusted ebitda": "adjusted_ebitda",
    "operating cash flow": "cash_from_operations",
    "cash from operations": "cash_from_operations",
}


@dataclass
class Conversation:
    """Tracks a single chat session."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Mapping[str, str]] = field(default_factory=list)

    def as_llm_messages(self) -> List[Mapping[str, str]]:
        """Render the conversation history in chat-completions format."""
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self.messages]


SYSTEM_PROMPT = (
    "You are BenchmarkOS, an institutional-grade financial analyst. Provide comprehensive, data-rich analysis "
    "that answers the user's question with depth and multiple sources.\n\n"
    
    "## Core Approach\n\n"
    "1. **Lead with the direct answer** - First sentence answers the question\n"
    "2. **Then provide comprehensive depth** - Multiple data points, context, analysis\n"
    "3. **Use ALL available data sources** - SEC filings, Yahoo Finance, analyst ratings, institutional ownership, news, economic data\n"
    "4. **Include multiple perspectives** - Historical trends, current market view, future outlook\n"
    "5. **Cite many sources** - Link to all relevant sources (5-10 links minimum)\n\n"
    
    "## Portfolio Analysis - CRITICAL RULES\n\n"
    "When portfolio data is provided in the context:\n"
    "1. **USE ONLY THE PROVIDED DATA** - You MUST use ONLY the specific holdings, weights, sectors, and statistics shown in the portfolio data\n"
    "2. **DO NOT HALLUCINATE** - NEVER make up portfolio data. If you don't see it in the provided data, say so explicitly\n"
    "3. **Quote actual numbers** - Reference the EXACT tickers, weights, and metrics from the portfolio data (e.g., 'AAPL is 15.2% of the portfolio')\n"
    "4. **Provide specific recommendations** - Based on the ACTUAL portfolio composition shown, suggest specific rebalancing actions (e.g., 'Reduce AAPL from 15.2% to 10%')\n"
    "5. **Analyze actual exposure** - Use the sector and factor exposure percentages provided in the data, not generic examples\n"
    "6. **Reference actual statistics** - Use the portfolio statistics (P/E, dividend yield, concentration) shown in the data\n"
    "7. **USE CALCULATED RISK METRICS** - When asked about risk metrics (CVaR, VaR, volatility, Sharpe ratio, Sortino ratio, alpha, beta, tracking error):\n"
    "   - These metrics are ALREADY CALCULATED and shown in the 'Calculated Risk & Performance Metrics' section of the portfolio context\n"
    "   - DO NOT say you cannot calculate these metrics - they are already calculated from historical portfolio returns\n"
    "   - Use the ACTUAL calculated values shown in that section (e.g., 'The portfolio CVaR is X%' using the value shown)\n"
    "   - If a metric is shown, reference it directly (e.g., 'Based on the calculated CVaR of X%, the portfolio has...')\n"
    "   - If a metric is not shown (e.g., 'Risk metrics: Unable to calculate'), explain that insufficient historical data is available\n"
    "   - NEVER estimate or calculate these metrics yourself - use the pre-calculated values provided\n"
    "   - Interpret the calculated values: Explain what the CVaR, Sharpe ratio, etc. mean for this portfolio\n"
    "8. **If data is missing** - If the portfolio data doesn't include a metric you need, explicitly state 'This metric is not available in the portfolio data' BUT still try to provide estimates based on available data\n"
    "9. **DO NOT provide generic advice** - If portfolio data is provided, you MUST analyze THAT SPECIFIC portfolio, not a hypothetical one\n"
    "10. **Verify against data** - Before mentioning any ticker, weight, or metric, verify it exists in the provided portfolio data\n"
    "11. **Answer the actual question** - If asked about 'portfolio exposure', use the sector/factor exposure data provided. If asked to 'analyze portfolio', analyze the actual holdings shown. If asked about 'CVaR' or risk, use the pre-calculated metrics from the portfolio context\n"
    "12. **MANDATORY: Include comprehensive sources** - ALWAYS end portfolio responses with a '📊 Sources:' section containing:\n"
    "    - SEC filing links for top holdings (10-K, 10-Q) from the portfolio context\n"
    "    - Yahoo Finance links for all holdings\n"
    "    - Benchmark ETF sources (SPY, QQQ, DIA, IWM) for risk calculations\n"
    "    - Portfolio metadata (portfolio ID, holdings count)\n"
    "    - Risk calculation methodology references\n"
    "    - Minimum 5-10 source links per portfolio response\n"
    "    - Format all sources as markdown links: [Name](URL)\n"
    "    - Use the source links provided in the 'PORTFOLIO DATA SOURCES' section of the context\n\n"
    
    "## Response Structure\n\n"
    "**Direct Answer (1-2 sentences)**\n"
    "- State the answer immediately\n\n"
    "**Comprehensive Data (3-5 sections)**\n"
    "Break down the analysis with headers:\n"
    "- ### Key Metrics (with specific numbers)\n"
    "- ### Market Context (analyst ratings, institutional ownership, price targets)\n"
    "- ### Historical Trends (multi-year data, growth rates)\n"
    "- ### Business Drivers (what's causing the numbers)\n"
    "- ### Future Outlook (implications, catalysts, risks)\n\n"
    
    "🚨 **MANDATORY SOURCES REQUIREMENT - EVERY RESPONSE MUST INCLUDE:**\n\n"
    "**CRITICAL: You MUST include a '📊 Sources:' section at the END of EVERY response with clickable links.**\n\n"
    "**Requirements:**\n"
    "- **Minimum 5-10 source links** per response\n"
    "- **ALL sources must be clickable markdown links**: [Name](URL)\n"
    "- **Use ACTUAL URLs from the context provided** - never use placeholder URLs\n"
    "- **Include SEC filing links** when available (10-K, 10-Q, 8-K, etc.)\n"
    "- **Include Yahoo Finance links** for ticker data\n"
    "- **Include FRED economic data links** when macro context is relevant\n"
    "- **Include news/article links** when referenced\n"
    "- **Format example:**\n"
    "  📊 **Sources:**\n"
    "  - [10-K FY2024](https://www.sec.gov/...)\n"
    "  - [10-K FY2023](https://www.sec.gov/...)\n"
    "  - [10-Q Q4 FY2024](https://www.sec.gov/...)\n"
    "  - [Yahoo Finance - AAPL](https://finance.yahoo.com/quote/AAPL)\n"
    "  - [FRED Economic Data - GDP](https://fred.stlouisfed.org/series/GDP)\n\n"
    "**❌ NEVER send a response without:**\n"
    "- A '📊 Sources:' section at the very end\n"
    "- At least 5-10 clickable source links\n"
    "- Real URLs (not placeholders like 'url' or 'https://example.com')\n"
    "- If context provides source URLs, you MUST use them - no excuses\n\n"
    
    "## Data Integration - Use Everything\n\n"
    "Your context includes multiple data sources. **USE THEM ALL:**\n\n"
    
    "**SEC Filings:**\n"
    "- Financial statements (revenue, earnings, margins, cash flow)\n"
    "- Multi-year trends (3-5 year history)\n"
    "- Segment breakdowns, geographic data\n"
    "- Management commentary from MD&A\n\n"
    
    "**Yahoo Finance:**\n"
    "- Current price, market cap, P/E ratio, valuation multiples\n"
    "- Analyst consensus (Buy/Hold/Sell ratings)\n"
    "- Target prices (mean, high, low) and implied upside\n"
    "- Number of analysts covering the stock\n"
    "- Top 5-10 institutional holders with ownership %\n"
    "- Recent insider transactions (buys/sells)\n"
    "- Earnings estimates and quarterly history\n"
    "- ESG scores (if available)\n"
    "- Recent news headlines (5-10 articles)\n\n"
    
    "**Macro Economic Context (CRITICAL - Use This!):**\n"
    "- GDP growth rate - contextualize company growth vs. economic expansion\n"
    "- Interest rates (Fed Funds) - impact on borrowing costs, valuations\n"
    "- Inflation (CPI) - pricing power, input cost pressures\n"
    "- Unemployment rate - consumer spending strength, labor market tightness\n"
    "- **SECTOR BENCHMARKS** - compare company metrics to sector averages:\n"
    "  * Revenue CAGR vs. sector\n"
    "  * Margin performance vs. sector benchmarks\n"
    "  * ROIC vs. sector standards\n"
    "  * Leverage vs. sector norms\n"
    "- **ALWAYS explain company performance in macro context**\n"
    "- Example: \"Tesla's 15% revenue growth significantly outpaces the 2.5% GDP growth\n"
    "  and the 8% automotive sector average, driven by strong EV demand despite\n"
    "  high interest rates (Fed Funds at 4.5%) that typically constrain auto purchases.\"\n\n"
    
    "## Length & Depth Requirements\n\n"
    "**Target Length:**\n"
    "- Simple questions: 400-600 words\n"
    "- Complex questions: 600-1000 words\n"
    "- Comparison questions: 800-1200 words\n\n"
    
    "**Data Point Minimums:**\n"
    "- Include at least 10-15 specific numbers/metrics\n"
    "- Reference at least 3 different years of data\n"
    "- Cite at least 5-10 different sources\n"
    "- Include at least 2-3 analyst perspectives\n\n"
    
    "## Financial Professional Query Types\n\n"
    "You should expertly handle these types of questions:\n\n"
    
    "**Valuation & Multiples:**\n"
    "- \"What's Apple's P/E ratio vs. peers?\"\n"
    "- \"Is Tesla overvalued?\"\n"
    "- \"What multiples is Microsoft trading at?\"\n"
    "- \"What's the fair value of Amazon?\"\n"
    "- \"Compare valuation metrics for FAANG stocks\"\n\n"
    
    "**Financial Health & Risk:**\n"
    "- \"What's Tesla's debt-to-equity ratio?\"\n"
    "- \"How leveraged is Apple?\"\n"
    "- \"What's Microsoft's interest coverage?\"\n"
    "- \"Is Amazon's balance sheet strong?\"\n"
    "- \"What are the key risks for Tesla?\"\n\n"
    
    "**Profitability & Margins:**\n"
    "- \"What's Apple's gross margin trend?\"\n"
    "- \"Which is more profitable: Microsoft or Google?\"\n"
    "- \"How are Amazon's margins changing?\"\n"
    "- \"What's driving Tesla's margin compression?\"\n"
    "- \"Compare EBITDA margins across FAANG\"\n\n"
    
    "**Growth & Performance:**\n"
    "- \"Is Apple growing faster than Microsoft?\"\n"
    "- \"What's Tesla's revenue CAGR?\"\n"
    "- \"How fast is Amazon's cloud business growing?\"\n"
    "- \"What's Apple's earnings growth outlook?\"\n"
    "- \"Which tech stock has the best growth trajectory?\"\n\n"
    
    "**Cash Flow & Returns:**\n"
    "- \"What's Apple's free cash flow?\"\n"
    "- \"How much cash does Microsoft generate?\"\n"
    "- \"What's Tesla's return on equity?\"\n"
    "- \"Compare ROI across mega-cap tech\"\n"
    "- \"What's Amazon's cash conversion cycle?\"\n\n"
    
    "**Investment Analysis:**\n"
    "- \"Should I invest in Apple or Microsoft?\"\n"
    "- \"What's the bull case for Tesla?\"\n"
    "- \"What are the catalysts for Amazon?\"\n"
    "- \"Why is Netflix stock down?\"\n"
    "- \"What's the investment thesis for Google?\"\n\n"
    
    "**Market Position & Competition:**\n"
    "- \"Who are Apple's main competitors?\"\n"
    "- \"What's Tesla's market share?\"\n"
    "- \"How does Amazon compare to Walmart?\"\n"
    "- \"What's Microsoft's competitive advantage?\"\n"
    "- \"Is Apple losing market share to Samsung?\"\n\n"
    
    "**Management & Strategy:**\n"
    "- \"How is Apple's management performing?\"\n"
    "- \"What's Tesla's strategy for growth?\"\n"
    "- \"How is Amazon allocating capital?\"\n"
    "- \"What's Microsoft's dividend policy?\"\n"
    "- \"Is Apple doing share buybacks?\"\n\n"
    
    "**Sector & Industry Analysis:**\n"
    "- \"How is the tech sector performing?\"\n"
    "- \"What's the outlook for semiconductors?\"\n"
    "- \"How are EV stocks performing?\"\n"
    "- \"Compare retail vs. e-commerce stocks\"\n"
    "- \"What's driving cloud computing growth?\"\n\n"
    
    "**Analyst & Institutional Views:**\n"
    "- \"What do analysts think of Apple?\"\n"
    "- \"What's the consensus rating on Tesla?\"\n"
    "- \"Are institutions buying or selling Amazon?\"\n"
    "- \"What's the price target for Microsoft?\"\n"
    "- \"Have there been recent insider purchases at Apple?\"\n\n"
    
    "**Macroeconomic Context:**\n"
    "- \"How do interest rates affect tech stocks?\"\n"
    "- \"What's the impact of inflation on Apple?\"\n"
    "- \"How does GDP growth affect consumer stocks?\"\n"
    "- \"What's the recession risk for tech?\"\n"
    "- \"How do currency fluctuations impact Apple's earnings?\"\n\n"
    
    "**ESG & Sustainability:**\n"
    "- \"What's Apple's ESG score?\"\n"
    "- \"How sustainable is Tesla's business?\"\n"
    "- \"What are Amazon's environmental initiatives?\"\n"
    "- \"Does Microsoft have good governance?\"\n"
    "- \"What are the social impact risks for tech companies?\"\n\n"
    
    "**Portfolio Analysis - EXAMPLES:**\n"
    "- \"What's my portfolio risk?\" → Use portfolio data to calculate risk metrics (volatility, beta, CVaR)\n"
    "- \"Analyze my portfolio exposure\" → Use sector/factor exposure data from portfolio context\n"
    "- \"What are my holdings?\" → List actual holdings with weights from portfolio data\n"
    "- \"What's my portfolio diversification?\" → Use HHI and concentration metrics from portfolio data\n"
    "- \"Optimize my portfolio\" → Analyze current holdings and suggest specific rebalancing based on actual weights\n"
    "- \"What's my portfolio performance?\" → Calculate returns using actual holdings and their weights\n"
    "- \"Show me my portfolio exposure by sector\" → Use sector exposure percentages from portfolio data\n"
    "- \"What's my portfolio CVaR?\" → Calculate conditional value at risk using actual holdings\n"
    "- \"Analyze port_xxxxx\" → Use portfolio ID to fetch and analyze that specific portfolio\n"
    "- \"What's my portfolio allocation?\" → Show actual allocation by ticker/sector from portfolio data\n\n"
    
    "**Portfolio Query Interpretation:**\n"
    "- When user asks \"What's my portfolio risk?\" → They want risk metrics for THEIR portfolio, not a generic portfolio\n"
    "- When user asks \"What's my portfolio exposure?\" → They want sector/factor exposure for THEIR holdings\n"
    "- When user asks \"What are my holdings?\" → They want the ACTUAL holdings from the portfolio data\n"
    "- When user asks \"Optimize my portfolio\" → They want recommendations based on THEIR current holdings\n"
    "- When portfolio data is provided, ALWAYS analyze THAT SPECIFIC portfolio, not a hypothetical one\n"
    "- NEVER say \"Here's a sample portfolio\" when actual portfolio data is provided\n"
    "- ALWAYS reference specific tickers, weights, and metrics from the portfolio data\n\n"
    
    "## Example Response Template\n\n"
    "**Q:** \"What is Apple's revenue?\"\n\n"
    "**A:** \"Apple's revenue for FY2024 was **$394.3 billion**, up 7.2% year-over-year from $367.8B in FY2023.\n\n"
    
    "### Revenue Breakdown\n\n"
    "The revenue growth was driven by three key segments:\n"
    "- **iPhone**: $200.6B (+6.1% YoY), representing 51% of total revenue\n"
    "- **Services**: $85.2B (+14.2% YoY), now 22% of revenue with 68% gross margin\n"
    "- **Mac**: $29.4B (+8.5% YoY), benefiting from M3 chip upgrades\n"
    "- **iPad**: $28.3B (+3.2% YoY)\n"
    "- **Wearables**: $39.8B (+1.8% YoY)\n\n"
    
    "### Historical Context\n\n"
    "Apple's revenue has grown consistently:\n"
    "- FY2022: $394.3B (current)\n"
    "- FY2023: $383.3B\n"
    "- FY2022: $365.8B\n"
    "- 3-year CAGR: **8.5%**\n\n"
    
    "This growth is particularly impressive given the smartphone market shrank 3.2% globally in 2024.\n\n"
    
    "### Market Reaction & Analyst Views\n\n"
    "Wall Street is bullish on these results (Yahoo Finance data):\n"
    "- **41 analysts** cover Apple\n"
    "- **35 rate it a BUY**, 6 HOLD, 0 SELL\n"
    "- **Target price: $253** (current: $262.82)\n"
    "- **P/E ratio: 39.8x** (vs. S&P 500 avg of 22.5x)\n\n"
    
    "**Institutional ownership stands at 61.5%:**\n"
    "- Vanguard: 8.4% of shares outstanding (+0.3% this quarter)\n"
    "- BlackRock: 6.9% (+0.2%)\n"
    "- State Street: 4.1% (unchanged)\n\n"
    
    "The increase in institutional ownership signals confidence from sophisticated investors.\n\n"
    
    "### Business Drivers\n\n"
    "**What's fueling the growth:**\n"
    "1. **Geographic expansion**: India revenue up 42% YoY, now $8.7B\n"
    "2. **Services momentum**: High-margin recurring revenue (App Store, iCloud, Apple TV+)\n"
    "3. **Product refresh cycles**: M3 chips driving Mac upgrades, iPhone 15 uptake\n"
    "4. **Installed base**: 2.2 billion active devices (+150M YoY)\n\n"
    
    "### Economic Context\n\n"
    "Apple's growth aligns with broader economic strength:\n"
    "- U.S. GDP grew **2.8%** in Q4 2024 (FRED)\n"
    "- Unemployment at **3.7%**, supporting consumer spending\n"
    "- Consumer sentiment at **72.6**, above historical average\n\n"
    
    "### Future Outlook\n\n"
    "Analysts expect continued growth:\n"
    "- FY2025 revenue estimate: **$420B** (+6.5%)\n"
    "- Services to reach **$95B** (+11.5%)\n"
    "- Gross margin expansion to **46.5%** (vs. 45.9% in FY2024)\n\n"
    
    "**Key catalysts:**\n"
    "- Vision Pro scaling in year 2\n"
    "- AI features in iOS 18 driving upgrades\n"
    "- India market penetration (only 7% smartphone share currently)\n\n"
    
    "**Risks:**\n"
    "- China revenue pressure (down 2.1% YoY to $68.3B)\n"
    "- Regulatory challenges (App Store fees under scrutiny)\n"
    "- Premium pricing in economic downturn\n\n"
    
    "📊 **Sources:**\n"
    "- [Apple 10-K FY2024](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000123)\n"
    "- [Apple 10-K FY2023](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-23-000106)\n"
    "- [Apple 10-Q Q4 FY2024](https://www.sec.gov/cgi-bin/viewer?action=view&cik=320193&accession_number=0000320193-24-000089)\n"
    "- [Yahoo Finance - AAPL](https://finance.yahoo.com/quote/AAPL)\n"
    "- [FRED GDP Data](https://fred.stlouisfed.org/series/GDP)\n"
    "- [FRED Unemployment](https://fred.stlouisfed.org/series/UNRATE)\n"
    "- [FRED Consumer Sentiment](https://fred.stlouisfed.org/series/UMCSENT)\n\n"
    "**REMEMBER: This sources section is MANDATORY for every response, not optional.**\n\n"
    
    "## Formatting Rules\n\n"
    "- Use **bold** for all key numbers and metrics\n"
    "- Use ### for section headers\n"
    "- Use bullet points extensively\n"
    "- Include specific numbers with units ($, %, etc.)\n"
    "- Format all source URLs as markdown links: [Name](URL)\n"
    "- NEVER use placeholder URLs - only real URLs from context\n\n"
    
    "## Key Principles\n\n"
    "✅ **DO:**\n"
    "- Answer directly in first sentence\n"
    "- Then provide comprehensive depth (400-1000 words)\n"
    "- Use 10-15+ specific data points\n"
    "- Include multiple sections with headers\n"
    "- **ALWAYS include a '📊 Sources:' section with 5-10+ clickable links at the end**\n"
    "- Reference all available sources (5-10 minimum)\n"
    "- Show historical trends (3-5 years)\n"
    "- Include analyst views and institutional ownership\n"
    "- Connect to economic context when relevant\n"
    "- Provide forward outlook\n\n"
    
    "❌ **DON'T:**\n"
    "- Write short 200-word responses (too brief)\n"
    "- **EVER send a response without a '📊 Sources:' section**\n"
    "- Use only 1-2 sources (need 5-10)\n"
    "- Use placeholder URLs (like 'url' or 'https://example.com')\n"
    "- Skip historical context\n"
    "- Omit analyst/market perspective\n"
    "- **NEVER omit the sources section** - it's mandatory, not optional\n\n"
    
    "## Pre-Send Checklist (VERIFY BEFORE RESPONDING):\n\n"
    "Before sending your response, verify:\n"
    "1. ✅ Response includes comprehensive analysis (400-1000 words)\n"
    "2. ✅ Response includes at least 10-15 specific data points\n"
    "3. ✅ Response includes multiple sections with headers\n"
    "4. ✅ **Response ends with a '📊 Sources:' section**\n"
    "5. ✅ **Sources section contains at least 5-10 clickable markdown links**\n"
    "6. ✅ **All source links are real URLs (not placeholders)**\n"
    "7. ✅ **All URLs from context are included in sources**\n"
    "8. ✅ Response references historical trends (3-5 years)\n"
    "9. ✅ Response includes analyst/market perspective\n"
    "10. ✅ Response provides forward outlook\n\n"
    "**If any item is missing, especially the sources section, DO NOT send the response until it's complete.**\n\n"
    "- Never use placeholder links like '[URL]' or 'url' - always use real URLs from context\n"
)


@dataclass
# Wraps settings, analytics, ingestion hooks, and the LLM client into a stateful conversation
# object. Use `BenchmarkOSChatbot.create()` before calling `ask()`.
class BenchmarkOSChatbot:
    """High-level interface wrapping the entire chatbot pipeline."""

    _MAX_CACHE_ENTRIES = 32
    _REPLY_CACHE_TTL_SECONDS = 300.0
    _CONTEXT_CACHE_TTL_SECONDS = 180.0
    _METRICS_CACHE_TTL_SECONDS = 300.0
    _SUMMARY_CACHE_TTL_SECONDS = 600.0
    _MAX_HISTORY_MESSAGES = 12

    settings: Settings
    llm_client: LLMClient
    analytics_engine: AnalyticsEngine
    ingestion_report: Optional[IngestionReport] = None
    conversation: Conversation = field(default_factory=Conversation)
    # new: SEC-backed index
    name_index: _CompanyNameIndex = field(default_factory=_CompanyNameIndex)
    ticker_sector_map: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    last_structured_response: Dict[str, Any] = field(default_factory=dict, init=False)
    _reply_cache: "OrderedDict[str, _CachedReply]" = field(default_factory=OrderedDict, init=False, repr=False)
    _context_cache: "OrderedDict[str, Tuple[str, float]]" = field(default_factory=OrderedDict, init=False, repr=False)
    _metrics_cache: "OrderedDict[Tuple[str, Tuple[Tuple[int, int], ...]], Tuple[List[database.MetricRecord], float]]" = field(default_factory=OrderedDict, init=False, repr=False)
    _summary_cache: "OrderedDict[str, Tuple[str, float]]" = field(default_factory=OrderedDict, init=False, repr=False)
    _active_progress_callback: Optional[Callable[[str, str], None]] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialise mutable response state containers."""
        self._reset_structured_response()

    def _reset_structured_response(self) -> None:
        """Clear any structured payload captured during the last response."""
        self.last_structured_response = {
            "highlights": [],
            "trends": [],
            "comparison_table": None,
            "citations": [],
            "exports": [],
            "conclusion": "",
            "parser": {},
            "dashboard": None,
        }

    def _progress(self, stage: str, detail: str) -> None:
        """Dispatch progress events to the active callback, if any."""
        callback = getattr(self, "_active_progress_callback", None)
        if not callback:
            return
        try:
            callback(stage, detail)
        except Exception:  # pragma: no cover - progress hooks are best-effort
            LOGGER.debug("Progress callback raised an exception", exc_info=True)

    @staticmethod
    def _current_time() -> float:
        """Return a monotonic timestamp for cache expiry bookkeeping."""
        return time.monotonic()

    @staticmethod
    def _canonical_prompt(original: str, normalized: Optional[str]) -> str:
        """Normalise prompts so cache lookups remain stable."""
        candidate = normalized if normalized else original
        return " ".join(candidate.strip().split()).lower()

    @staticmethod
    def _should_cache_prompt(prompt: str) -> bool:
        """Decide whether a prompt is safe to reuse across requests."""
        lowered = prompt.strip().lower()
        if not lowered:
            return False
        allowed_prefixes = (
            "compare",
            "fact",
            "fact-range",
            "table",
            "scenario",
            "metric",
            "summary",
            "snapshot",
            "overview",
            "help",
        )
        if not any(lowered.startswith(prefix) for prefix in allowed_prefixes):
            return False
        skip_prefixes = (
            "ingest",
            "ingest status",
            "audit",
            "update ",
            "refresh ",
        )
        return not any(lowered.startswith(prefix) for prefix in skip_prefixes)

    def _get_cached_reply(self, key: str) -> Optional[_CachedReply]:
        """Return a cached reply if still fresh."""
        entry = self._reply_cache.get(key)
        if not entry:
            return None
        if self._current_time() - entry.created_at > self._REPLY_CACHE_TTL_SECONDS:
            self._reply_cache.pop(key, None)
            return None
        self._reply_cache.move_to_end(key)
        return entry

    def _store_cached_reply(self, key: str, reply: str) -> None:
        """Persist a reply for quick re-use."""
        snapshot = copy.deepcopy(self.last_structured_response)
        self._reply_cache[key] = _CachedReply(
            reply=reply,
            structured=snapshot,
            created_at=self._current_time(),
        )
        self._reply_cache.move_to_end(key)
        while len(self._reply_cache) > self._MAX_CACHE_ENTRIES:
            self._reply_cache.popitem(last=False)

    def _get_cached_context(self, key: str) -> Optional[str]:
        """Return cached RAG context if available."""
        entry = self._context_cache.get(key)
        if not entry:
            return None
        context, created_at = entry
        if self._current_time() - created_at > self._CONTEXT_CACHE_TTL_SECONDS:
            self._context_cache.pop(key, None)
            return None
        self._context_cache.move_to_end(key)
        return context

    def _store_cached_context(self, key: str, context: str) -> None:
        """Cache frequently requested RAG context snippets."""
        self._context_cache[key] = (context, self._current_time())
        self._context_cache.move_to_end(key)
        while len(self._context_cache) > self._MAX_CACHE_ENTRIES:
            self._context_cache.popitem(last=False)

    def _fetch_metrics_cached(
        self,
        ticker: str,
        *,
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
    ) -> List[database.MetricRecord]:
        """Fetch metrics with a lightweight in-memory cache."""
        normalized = ticker.upper()
        period_key: Tuple[Tuple[int, int], ...]
        if period_filters:
            period_key = tuple(tuple(filter_item) for filter_item in period_filters if filter_item)
        else:
            period_key = tuple()
        cache_key = (normalized, period_key)
        entry = self._metrics_cache.get(cache_key)
        if entry:
            records, created_at = entry
            if self._current_time() - created_at <= self._METRICS_CACHE_TTL_SECONDS:
                self._metrics_cache.move_to_end(cache_key)
                return records
            self._metrics_cache.pop(cache_key, None)

        records = self.analytics_engine.get_metrics(
            normalized,
            period_filters=period_filters,
        )
        self._metrics_cache[cache_key] = (records, self._current_time())
        self._metrics_cache.move_to_end(cache_key)
        while len(self._metrics_cache) > self._MAX_CACHE_ENTRIES:
            self._metrics_cache.popitem(last=False)
        return records

    def _get_ticker_summary(self, ticker: str) -> str:
        """Return a narrative summary for ``ticker`` with caching."""
        normalized = ticker.upper()
        entry = self._summary_cache.get(normalized)
        if entry:
            summary, created_at = entry
            if self._current_time() - created_at <= self._SUMMARY_CACHE_TTL_SECONDS:
                self._summary_cache.move_to_end(normalized)
                self._progress("summary_cache_hit", f"Using cached snapshot for {normalized}")
                return summary
            self._summary_cache.pop(normalized, None)

        self._progress("summary_build_start", f"Generating snapshot for {normalized}")
        try:
            summary = self.analytics_engine.generate_summary(normalized)
        except Exception:
            LOGGER.warning("Unable to generate summary for %s", normalized, exc_info=True)
            summary = (
                f"No cached metrics for {normalized}. "
                f"Run 'ingest {normalized}' to pull the latest filings."
            )
        else:
            if not summary.strip():
                summary = (
                    f"No cached metrics for {normalized}. "
                    f"Run 'ingest {normalized}' to pull the latest filings."
                )

        self._progress("summary_build_complete", f"Snapshot generated for {normalized}")
        self._summary_cache[normalized] = (summary, self._current_time())
        self._summary_cache.move_to_end(normalized)
        while len(self._summary_cache) > self._MAX_CACHE_ENTRIES:
            self._summary_cache.popitem(last=False)
        return summary

    def _detect_summary_target(
        self,
        user_input: str,
        normalized_command: Optional[str],
    ) -> Optional[str]:
        """Detect if the prompt requests a quick metrics summary for a single ticker."""
        normalized = (normalized_command or "").strip().lower()
        lowered = user_input.strip().lower()
        summary_prefixes = ("summary", "metrics", "snapshot", "overview")
        summary_keywords = (
            "summary",
            "snapshot",
            "overview",
            "metrics",
            "metric",
            "kpi",
            "performance",
            "report",
        )

        should_attempt = False
        for prefix in summary_prefixes:
            if normalized.startswith(prefix + " "):
                should_attempt = True
                break
        if not should_attempt:
            should_attempt = any(keyword in lowered for keyword in summary_keywords)
        if not should_attempt:
            return None

        tickers = self._detect_tickers(user_input)
        if not tickers:
            return None
        
        # If multiple tickers detected, filter to those with actual data
        # and prefer the last one mentioned (likely the subject of the query)
        valid_tickers = []
        for ticker in tickers:
            ticker_upper = ticker.upper()
            try:
                records = self._fetch_metrics_cached(ticker_upper)
                if records:
                    valid_tickers.append(ticker_upper)
            except Exception:
                continue
        
        if len(valid_tickers) == 1:
            return valid_tickers[0]
        elif len(valid_tickers) > 1:
            # Prefer the last valid ticker (typically the actual company mentioned)
            return valid_tickers[-1]
        
        return None

    def _prepare_llm_messages(self, rag_context: Optional[str]) -> List[Mapping[str, str]]:
        """Trim history before sending to the LLM and append optional RAG context."""
        history = self.conversation.as_llm_messages()
        if not history:
            return []
        system_message, *chat_history = history
        if len(chat_history) > self._MAX_HISTORY_MESSAGES:
            chat_history = chat_history[-self._MAX_HISTORY_MESSAGES :]
        messages: List[Mapping[str, str]] = [system_message]
        if rag_context:
            messages.append({"role": "system", "content": rag_context})
        messages.extend(chat_history)
        return messages

    def _preload_popular_metrics(self) -> None:
        """Warm cached metrics for high-traffic tickers to reduce first-response latency."""
        for ticker in POPULAR_TICKERS:
            try:
                self._fetch_metrics_cached(ticker)
                self._get_ticker_summary(ticker)
            except Exception:  # pragma: no cover - defensive caching preload
                LOGGER.debug("Preload for %s failed", ticker, exc_info=True)

    @classmethod
    def create(cls, settings: Settings) -> "BenchmarkOSChatbot":
        """Factory that wires analytics, storage, and the LLM client together."""
        llm_client = build_llm_client(
            settings.llm_provider,
            model=settings.openai_model,
        )

        database.initialise(settings.database_path)

        ingestion_report: Optional[IngestionReport] = None
        try:
            ingestion_report = ingest_financial_data(settings)
        except Exception as exc:  # pragma: no cover - defensive guard
            database.record_audit_event(
                settings.database_path,
                AuditEvent(
                    ticker="__system__",
                    event_type="ingestion_error",
                    entity_id="startup",
                    details={"error": str(exc)},
                    created_at=datetime.utcnow(),
                    created_by="chatbot",
                ),
            )

        analytics_engine = AnalyticsEngine(settings)
        analytics_engine.refresh_metrics(force=True)

        # Build the SEC-backed name index once; always attempt local alias fallback
        index = _CompanyNameIndex()
        base = getattr(settings, "edgar_base_url", None) or "https://www.sec.gov"
        ua = getattr(settings, "sec_api_user_agent", None) or "BenchmarkOSBot/1.0 (support@benchmarkos.com)"
        try:
            index.build_from_sec(base, ua)
            LOGGER.info("SEC company index built with %d names", len(index.by_exact))
        except Exception as e:
            LOGGER.warning("SEC company index build failed: %s", e)

        # Always attempt local fallback (data/name_aliases.json)
        try:
            alias_path = Path(__file__).resolve().parent.parent / "data" / "name_aliases.json"
            index.load_local_aliases(alias_path)
        except Exception:
            LOGGER.exception("Failed while loading local aliases")

        LOGGER.info("Final name->ticker index size: %d", len(index.by_exact))

        sector_map = cls._load_sector_map()

        chatbot = cls(
            settings=settings,
            llm_client=llm_client,
            analytics_engine=analytics_engine,
            ingestion_report=ingestion_report,
            name_index=index,
            ticker_sector_map=sector_map,
        )
        chatbot._preload_popular_metrics()
        return chatbot

    # ----------------------------------------------------------------------------------
    # NL → command normalization (accept natural company names)
    # ----------------------------------------------------------------------------------
    def _name_to_ticker(self, term: str) -> Optional[str]:
        """Resolve free-text company names to tickers using:
           1) engine.lookup_ticker (if provided)
           2) SEC-backed name index (exact/prefix/contains/token overlap)
           3) local alias fallback
        """
        if not term:
            return None
        t = term.strip()

        # engine's own mapping first
        lookup = getattr(self.analytics_engine, "lookup_ticker", None)
        if callable(lookup):
            try:
                tk = lookup(t, allow_partial=True)  # type: ignore[misc]
            except TypeError:
                tk = lookup(t)  # type: ignore[misc]
            except Exception:
                tk = None
            if tk:
                return tk.upper()

        # SEC/local name index
        tk = self.name_index.resolve(t)
        if tk:
            return tk.upper()

        fuzzy = self.name_index.resolve_fuzzy(t, cutoff=0.7)
        if fuzzy:
            return fuzzy[0][0].upper()

        return None

    @staticmethod
    def _load_sector_map() -> Dict[str, Dict[str, Optional[str]]]:
        """Load sector and sub-industry metadata for tickers."""
        path = Path(__file__).resolve().parents[2] / "webui" / "data" / "company_universe.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.warning("Unable to load company universe metadata: %s", exc)
            return {}

        mapping: Dict[str, Dict[str, Optional[str]]] = {}
        for entry in payload:
            ticker = str(entry.get("ticker", "")).strip().upper()
            if not ticker:
                continue
            mapping[ticker] = {
                "sector": entry.get("sector"),
                "sub_industry": entry.get("sub_industry") or entry.get("subIndustry"),
            }
        return mapping

    def _sector_label(self, ticker: str) -> Optional[str]:
        """Return a combined sector/sub-industry label for `ticker`."""
        info = self.ticker_sector_map.get(ticker.upper())
        if not info:
            return None
        sector = (info.get("sector") or "").strip()
        sub = (info.get("sub_industry") or "").strip()
        if sector and sub:
            return f"{sector} – {sub}"
        return sector or sub or None

    def _detect_fact_metric(self, text: str) -> Optional[str]:
        """Identify if the prompt references a specific fact metric."""
        cleaned = re.sub(r"[^a-z0-9\s/.-]", " ", text.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None

        best_match: Optional[str] = None
        best_len = -1
        for alias, canonical in FACT_METRIC_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", cleaned):
                alias_len = len(alias)
                if alias_len > best_len:
                    best_match = canonical
                    best_len = alias_len
        return best_match

    def _normalize_nl_to_command(self, text: str) -> Optional[str]:
        """Turn flexible NL prompts into the strict CLI-style commands this class handles."""
        t = text.strip()

        def _canon_year_span(txt: str) -> Optional[str]:
            if not txt:
                return None
            m = re.search(r"(?:FY\s*)?(\d{4})\s*(?:[-/]\s*(?:FY\s*)?(\d{4}))?$", txt.strip(), re.IGNORECASE)
            if not m:
                return None
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else None
            if b and b < a:
                a, b = b, a
            return f"{a}-{b}" if b else f"{a}"

        def _extract_year_phrase(full_text: str) -> Optional[str]:
            """Handle richer year phrasing such as 'between 2020 and 2022'."""
            if not full_text:
                return None
            current_year = datetime.utcnow().year
            if re.search(r"\b(this|current)\s+year\b", full_text, re.IGNORECASE):
                return str(current_year)
            if re.search(r"\bnext\s+year\b", full_text, re.IGNORECASE):
                return str(current_year + 1)
            if re.search(r"\blast\s+year\b", full_text, re.IGNORECASE):
                return str(current_year - 1)
            if re.search(r"\blast\s+fiscal\s+year\b", full_text, re.IGNORECASE):
                return str(current_year - 1)
            patterns = [
                r"(?:between|from)\s+(?:fy\s*)?(\d{4})\s+(?:and|to|through)\s+(?:fy\s*)?(\d{4})",
                r"(?:for|during|over)\s+(?:fy\s*)?(\d{4})\s+(?:and|&)\s+(?:fy\s*)?(\d{4})",
                r"(?:fy\s*)?(\d{4})\s+(?:through|to)\s+(?:fy\s*)?(\d{4})",
            ]
            for pattern in patterns:
                found = re.search(pattern, full_text, re.IGNORECASE)
                if found:
                    start = int(found.group(1))
                    end = int(found.group(2))
                    if end < start:
                        start, end = end, start
                    if start == end:
                        return f"{start}"
                    return f"{start}-{end}"

            quarter_match = re.search(
                r"(?:q[1-4]|quarter\s+[1-4])\s+(?:fy\s*)?(\d{4})", full_text, re.IGNORECASE
            )
            if quarter_match:
                return str(int(quarter_match.group(1)))

            years = [int(y) for y in re.findall(r"(?:fy\s*)?(20\d{2})", full_text, re.IGNORECASE)]
            unique_years = sorted(set(years))
            if len(unique_years) >= 2:
                start, end = unique_years[0], unique_years[-1]
                if start != end:
                    return f"{start}-{end}"
            if unique_years:
                return str(unique_years[0])
            return None

        def _extract_quarter_phrase(full_text: str) -> Optional[tuple[int, str]]:
            if not full_text:
                return None
            quarter_words = {
                "first": "Q1",
                "1st": "Q1",
                "second": "Q2",
                "2nd": "Q2",
                "third": "Q3",
                "3rd": "Q3",
                "fourth": "Q4",
                "4th": "Q4",
            }

            match = re.search(
                r"\bQ([1-4])\s*(?:of\s+)?(?:FY\s*)?(\d{2,4})\b",
                full_text,
                re.IGNORECASE,
            )
            if match:
                quarter = f"Q{match.group(1)}"
                year = int(match.group(2))
                if year < 100:
                    year += 2000 if year < 70 else 1900
                return (year, quarter)

            match = re.search(
                r"\b(?:FY\s*)?(\d{2,4})\s*Q([1-4])\b",
                full_text,
                re.IGNORECASE,
            )
            if match:
                year = int(match.group(1))
                if year < 100:
                    year += 2000 if year < 70 else 1900
                quarter = f"Q{match.group(2)}"
                return (year, quarter)

            match = re.search(
                r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter\s+(?:of\s+)?(?:FY\s*)?(\d{2,4})\b",
                full_text,
                re.IGNORECASE,
            )
            if match:
                quarter = quarter_words[match.group(1).lower()]
                year = int(match.group(2))
                if year < 100:
                    year += 2000 if year < 70 else 1900
                return (year, quarter)

            return None

        def _resolve_company_phrase(phrase: str) -> Optional[str]:
            cleaned_phrase = re.sub(r"[\u2019']", " ", phrase)
            tokens = [tok for tok in re.split(r"\s+", cleaned_phrase.strip()) if tok]
            if not tokens:
                return None
            n = len(tokens)
            for length in range(n, 0, -1):
                for start in range(0, n - length + 1):
                    candidate_tokens = tokens[start : start + length]
                    candidate = " ".join(candidate_tokens)
                    ticker = self._name_to_ticker(candidate)
                    if ticker:
                        return ticker.upper()
            return None

        def _split_entities(value: str) -> List[str]:
            s = value.strip().strip(",")
            if not s:
                return []
            quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', s)
            taken, out = set(), []
            for a, b in quoted:
                name = (a or b).strip()
                if name:
                    out.append(name); taken.add(name)
            s_clean = re.sub(r'"[^"]+"|\'[^\']+\'', "", s).strip()
            parts = [p for p in re.split(r"\s*,\s*", s_clean)] if "," in s_clean else \
                    [p for p in re.split(r"\s+and\s+", s_clean, flags=re.IGNORECASE)]
            for p in parts:
                p = p.strip()
                if p and p not in taken:
                    out.append(p)
            return out or [s]

        def _to_ticker(name_or_ticker: str) -> str:
            return (self._name_to_ticker(name_or_ticker) or name_or_ticker).upper()

        lower = t.lower()
        skip_prefixes = (
            "metrics",
            "metric ",
            "compare",
            "versus",
            "vs ",
            "vs.",
            "fact",
            "facts",
            "audit",
            "ingest",
            "fetch",
            "hydrate",
            "update",
            "scenario",
            "what-if",
            "what if",
            "table",
        )
        metric_terms = {
            "eps",
            "ebitda",
            "roe",
            "roa",
            "fcf",
            "peg",
            "pe",
            "p/e",
            "cagr",
        }

        range_match = re.search(
            r"(?P<company>[\w&'.-]+(?:\s+[\w&'.-]+){0,3})(?:['’]s)?\s+(?P<metric>[\w/&\-\s]+?)\s+(?:between|from)\s+(?:fy\s*)?(?P<start>\d{4})\s+(?:and|to|through)\s+(?:fy\s*)?(?P<end>\d{4})",
            t,
            re.IGNORECASE,
        )
        handled_direct = False
        if range_match:
            company_phrase = range_match.group("company")
            metric_phrase = range_match.group("metric").strip()
            start_year = int(range_match.group("start"))
            end_year = int(range_match.group("end"))
            if end_year < start_year:
                start_year, end_year = end_year, start_year
            resolved_ticker_for_range = _resolve_company_phrase(company_phrase)
            if resolved_ticker_for_range:
                metric_key = self._detect_fact_metric(metric_phrase) or "revenue"
                handled_direct = True
                return " ".join(["fact-range", resolved_ticker_for_range, f"{start_year}-{end_year}", metric_key])

        if not handled_direct:
            year_token = re.search(
                r"(?:fy\s*)?(?P<year>\d{4})(?:\s*(?:q|quarter)\s*(?P<quarter>[1-4]))?",
                t,
                re.IGNORECASE,
            )
            if year_token:
                year = year_token.group("year")
                quarter = year_token.group("quarter")
                pre_text = t[: year_token.start()]
                post_text = t[year_token.end() :]

                company_phrase_candidates = [
                    " ".join(pre_text.split()[-6:]),
                    " ".join(t.split()[:6]),
                ]
                resolved_ticker = None
                for candidate in company_phrase_candidates:
                    if not candidate:
                        continue
                    resolved_ticker = _resolve_company_phrase(candidate)
                    if resolved_ticker:
                        break

                if resolved_ticker:
                    metric_candidates = [
                        " ".join(post_text.split()[:6]),
                        " ".join(pre_text.split()[-6:]),
                    ]
                    metric_key = None
                    for candidate in metric_candidates:
                        if not candidate:
                            continue
                        metric_key = self._detect_fact_metric(candidate)
                        if metric_key:
                            break
                    if not metric_key:
                        metric_key = "revenue"

                    period_token = f"{year}Q{quarter}" if quarter else year
                    return " ".join(["fact", resolved_ticker, period_token, metric_key])

        if not any(lower.startswith(prefix) for prefix in skip_prefixes):
            detected_entities = self._detect_tickers(text)

            def _has_metrics(candidate: str) -> bool:
                try:
                    records = self._fetch_metrics_cached(candidate)
                except Exception:
                    return False
                return bool(records)

            ordered_subjects: List[str] = []
            seen_subjects: set[str] = set()
            ticker_pattern = re.compile(r"[A-Z]{1,5}(?:-[A-Z]{1,2})?")

            for raw in detected_entities:
                candidate = self._name_to_ticker(raw)
                if candidate:
                    resolved = candidate.upper()
                else:
                    upper_raw = raw.upper()
                    if not ticker_pattern.fullmatch(upper_raw):
                        continue
                    if not _has_metrics(upper_raw):
                        continue
                    resolved = upper_raw

                if resolved.lower() in metric_terms:
                    continue
                if resolved in seen_subjects:
                    continue
                seen_subjects.add(resolved)
                ordered_subjects.append(resolved)

            if ordered_subjects:
                # Initialize fact_metric before first usage
                fact_metric = self._detect_fact_metric(t)
                
                span_match = re.search(
                    r"(?:fy\s*)?\d{4}(?:\s*[-/]\s*(?:fy\s*)?\d{4})?",
                    t,
                    re.IGNORECASE,
                )
                period_token = _canon_year_span(span_match.group(0)) if span_match else None
                if not period_token:
                    period_token = _extract_year_phrase(t)

                if (
                    fact_metric
                    and period_token
                    and "-" in period_token
                    and len(ordered_subjects) == 1
                ):
                    return " ".join(["fact-range", ordered_subjects[0], period_token, fact_metric])

                quarter_info = _extract_quarter_phrase(t)
                quarter_token: Optional[str] = None
                if quarter_info:
                    quarter_year, quarter_label = quarter_info
                    period_token = period_token or str(quarter_year)
                    quarter_token = f"{quarter_year}{quarter_label}"
                if (
                    fact_metric
                    and period_token
                    and "-" not in period_token
                    and len(ordered_subjects) == 1
                ):
                    year_token = period_token.split("-", 1)[0]
                    if quarter_token:
                        return " ".join(["fact", ordered_subjects[0], quarter_token, fact_metric])
                    return " ".join(["fact", ordered_subjects[0], year_token, fact_metric])

                # Enhanced compare triggers detection
                compare_triggers = bool(
                    re.search(r"\b(compare|versus|vs\.?|against|between|relative)\b", lower)
                    or "better than" in lower
                    or "outperform" in lower
                    or "beats" in lower
                    or "and" in lower  # Add "and" as compare trigger
                )
                
                # Check if we have enough subjects for comparison
                if compare_triggers and len(ordered_subjects) >= 2:
                    parts = ["compare", *ordered_subjects]
                    if period_token:
                        parts.append(period_token)
                    return " ".join(parts)
                
                # Special handling for "compare X and Y" patterns
                if (re.search(r"\bcompare\b", lower) and 
                    re.search(r"\band\b", lower) and 
                    len(ordered_subjects) >= 2):
                    parts = ["compare", *ordered_subjects]
                    if period_token:
                        parts.append(period_token)
                    return " ".join(parts)

                parts = ["metrics", *ordered_subjects]
                if period_token:
                    parts.append(period_token)
                return " ".join(parts)

        # METRICS
        m = re.match(
            r'^(?:show|give me|get|what (?:are|is) the|list)?\s*(?:kpis?|metrics?|financials?)\s+(?:for\s+)?(?P<ents>.+?)(?:\s+(?:in|for)\s+(?P<per>(?:fy)?\d{4}(?:\s*[-/]\s*(?:fy)?\d{4})?))?\s*$',
            t, re.IGNORECASE,
        )
        if m:
            tickers = [_to_ticker(e) for e in _split_entities(m.group("ents")) if e]
            per = _canon_year_span(m.group("per") or "")
            if tickers:
                return " ".join(["metrics", *tickers, *(per and [per] or [])])

        # COMPARE
        m = re.match(r"^(?:compare|versus|vs\.?|against)\s+(?P<body>.+)$", t, re.IGNORECASE)
        if m:
            body = m.group("body").strip()
            yr = None
            myr = re.search(r"(\d{4})\s*$", body)
            if myr:
                yr = myr.group(1)
                body = body[: myr.start()].strip()
            normalized_body = re.sub(r"\s+(?:vs\.?|versus|against)\s+", ",", body, flags=re.IGNORECASE)
            normalized_body = re.sub(r"[&/]", ",", normalized_body)
            raw_entities: List[str] = []
            for chunk in re.split(r",|\band\b", normalized_body, flags=re.IGNORECASE):
                chunk = chunk.strip()
                if not chunk:
                    continue
                raw_entities.extend(_split_entities(chunk))
            if len(raw_entities) <= 1:
                raw_entities = [part for part in body.split() if part]
            tickers = []
            for entity in raw_entities:
                ticker = _to_ticker(entity)
                if ticker and ticker not in tickers:
                    tickers.append(ticker)
            if len(tickers) >= 2:
                parts = ["compare", *tickers]
                if yr:
                    parts.append(yr)
                return " ".join(parts)

        # FACTS
        m = re.match(r'^(?:show|get|give me)?\s*(?:fact|facts?)\s+(?:for\s+)?(?P<e>.+?)\s+(?:fy)?(?P<y>\d{4})(?:\s+(?P<mtr>[A-Za-z0-9_]+))?\s*$', t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["fact", tk, m.group("y"), m.group("mtr")]))

        # AUDIT
        m = re.match(r'^(?:show|get|give me)?\s*(?:audit|audit trail|ingestion log)s?\s+(?:for\s+)?(?P<e>.+?)(?:\s+(?:fy)?(?P<y>\d{4}))?\s*$', t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["audit", tk, m.group("y")]))

        # INGEST
        m = re.match(r"^(?:ingest|fetch|hydrate|update)\s+(?P<e>.+?)(?:\s+(?P<yrs>\d{1,2}))?\s*$", t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            return " ".join(filter(None, ["ingest", tk, m.group("yrs")]))

        # SCENARIO / WHAT-IF
        m = re.match(r"^(?:scenario|what[- ]?if)\s+(?P<e>.+?)\s+(?P<name>[A-Za-z0-9_\-]+)(?:\s+(?P<rest>.*))?$", t, re.IGNORECASE)
        if m:
            tk = _to_ticker(_split_entities(m.group("e"))[0])
            rest = (m.group("rest") or "")
            rest_norm = []
            for tok in re.split(r"\s+", rest.strip()):
                if not tok:
                    continue
                tl = tok.lower()
                if tl.startswith(("rev=", "revenue=")):
                    rest_norm.append("rev=" + tok.split("=", 1)[1])
                elif tl.startswith(("margin=", "ebitda=", "ebitda_margin=")):
                    rest_norm.append("margin=" + tok.split("=", 1)[1])
                elif tl.startswith(("mult=", "multiple=")):
                    rest_norm.append("mult=" + tok.split("=", 1)[1])
            return " ".join(["scenario", tk, m.group("name"), *rest_norm]).strip()

        return None

    # ----------------------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------------------
    def ask(
        self,
        user_input: str,
        *,
        progress_callback: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        """Generate a reply and persist both sides of the exchange."""

        previous_callback = getattr(self, "_active_progress_callback", None)
        self._active_progress_callback = progress_callback

        def emit(stage: str, detail: str) -> None:
            self._progress(stage, detail)

        try:
            self._reset_structured_response()
            emit("start", "Working on your request")
            timestamp = datetime.utcnow()
            database.log_message(
                self.settings.database_path,
                self.conversation.conversation_id,
                role="user",
                content=user_input,
                created_at=timestamp,
            )
            self.conversation.messages.append({"role": "user", "content": user_input})
            emit("message_logged", "Chat history updated")

            reply: Optional[str] = None
            lowered_input = user_input.strip().lower()
            emit("intent_analysis_start", "Analyzing prompt phrasing")
            normalized_command = self._normalize_nl_to_command(user_input)
            canonical_prompt = self._canonical_prompt(user_input, normalized_command)
            if normalized_command:
                emit("intent_analysis_complete", f"Intent candidate: {normalized_command}")
            else:
                emit("intent_analysis_complete", "Proceeding with natural language handling")
            cacheable = self._should_cache_prompt(canonical_prompt)

            cached_entry: Optional[_CachedReply] = None
            if cacheable:
                emit("cache_lookup", "Checking recent answers")
                cached_entry = self._get_cached_reply(canonical_prompt)
                if cached_entry:
                    emit("cache_hit", "Reusing earlier answer from cache")
                    reply = cached_entry.reply
                    self.last_structured_response = copy.deepcopy(cached_entry.structured)
                else:
                    emit("cache_miss", "No reusable answer found")
            else:
                emit("cache_skip", "Skipping cache for bespoke request")

            if reply is None:
                if lowered_input == "help":
                    emit("help_lookup", "Retrieving help guide")
                    reply = HELP_TEXT
                    emit("help_complete", "Help guide ready")
                else:
                    attempted_intent = False
                    # Try structured parsing first (Priority 1)
                    emit("intent_routed_structured", "Trying structured parsing first")
                    try:
                        reply = self._handle_financial_intent(user_input)
                        attempted_intent = True
                    except Exception as e:
                        LOGGER.exception(f"Error in _handle_financial_intent: {e}")
                        emit("intent_error", f"Structured parsing error: {str(e)}")
                        attempted_intent = True
                        reply = None
                    
                    # Fallback to normalized command if structured parsing fails
                    if reply is None and normalized_command and normalized_command.strip().lower() != lowered_input:
                        emit("intent_normalised", "Falling back to normalized command")
                        emit("intent_routed_structured", f"Executing structured command: {normalized_command}")
                        reply = self._handle_financial_intent(normalized_command)
                        attempted_intent = True
                    if attempted_intent:
                        if reply is not None:
                            emit("intent_complete", "Analytics intent resolved")
                        else:
                            emit("intent_complete", "Intent routing completed with no direct answer")

            if reply is None:
                # Check if this is a question - if so, skip summary and let LLM handle it
                lowered_input = user_input.lower()
                question_patterns = [
                    # CRITICAL: Contractions MUST come first
                    r'\bwhat\'s\b',  # "what's" contraction - CRITICAL
                    r'\bhow\'s\b',   # "how's" contraction
                    r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would|about|does|did)\b',
                    r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would|about|to|do|profitable|fast|good|bad|strong|weak)\b',
                    r'\bwhy\b',
                    r'\bexplain\b',
                    r'\btell\s+me\s+(?:about|why|how)\b',
                    r'\bis\s+\w+\s+(?:more|less|better|worse|higher|lower)',
                    r'\bis\s+\w+\s+(?:overvalued|undervalued|expensive|cheap|good|bad|risky|safe|strong|weak|profitable|worth)',
                    r'\bwhich\s+(?:company|stock|one|is|has|have)\b',
                    r'\bcan\s+you\b',
                    r'\bdoes\s+\w+\s+have\b',
                    r'\bshould\s+i\b',
                    r'\bwhen\s+(?:is|are|was|were|did|will)\b',
                    r'\bwhere\s+(?:is|are|can|do)\b',
                ]
                is_question = any(re.search(pattern, lowered_input) for pattern in question_patterns)
                
                # CRITICAL: Check for filter queries FIRST - these should NEVER generate dashboards
                filter_query_patterns = [
                    r'\b(?:show|list|find|get|give)\s+(?:me\s+)?(?:all\s+)?(?:the\s+)?(?:tech|technology|financial|healthcare|energy|consumer|industrial|utility|real estate)\s+(?:companies|stocks|firms)',
                    r'\b(?:companies|stocks|firms)\s+(?:in\s+)?(?:the\s+)?(?:tech|technology|financial|healthcare|energy|consumer|industrial|utility|real estate)\s+(?:sector|industry)',
                    r'\b(?:tech|technology|financial|healthcare|energy|consumer|industrial)\s+(?:sector|industry)\s+(?:companies|stocks)',
                    r'\b(?:companies|stocks|firms)\s+with\s+(?:revenue|sales)\s+(?:around|about|near|over|under|above|below|between)',
                    r'\b(?:revenue|sales)\s+(?:around|about|near|over|under|above|below)\s+\$?\d+',
                    r'\b(?:companies|stocks|firms)\s+with\s+(?:growing|increasing|declining|decreasing)\s+(?:revenue|sales|earnings|profit)',
                    r'\b(?:growing|increasing|high-growth|fast-growing)\s+(?:companies|stocks|firms)',
                    r'\b(?:companies|stocks|firms)\s+(?:that are|that have|with)\s+(?:growing|increasing)',
                    r'\b(?:large|small|mid|mega)\s+cap\s+(?:companies|stocks)',
                    r'\b(?:companies|stocks|firms)\s+with\s+market\s+cap\s+(?:over|under|above|below)',
                    r'\b(?:companies|stocks|firms)\s+(?:in|from)\s+.*\s+with\s+',
                ]
                is_filter_query = any(re.search(pattern, lowered_input) for pattern in filter_query_patterns)
                
                # Only do ticker summary for bare ticker mentions, NOT questions or filter queries
                if not is_question and not is_filter_query:
                    # Check for dashboard keyword first
                    dashboard_keywords = ["dashboard", "full dashboard", "comprehensive dashboard", 
                                         "detailed dashboard", "show me dashboard", "give me dashboard"]
                    should_build_dashboard = any(kw in lowered_input for kw in dashboard_keywords)
                    
                    if should_build_dashboard:
                        # Dashboard request - detect all tickers
                        all_tickers = self._detect_tickers(user_input)
                        emit("ticker_detection", f"Detected tickers from '{user_input}': {all_tickers}")
                        if len(all_tickers) >= 2:
                            # Multi-ticker dashboard - build dashboards for each ticker
                            emit("multi_ticker_dashboard", f"Building dashboards for {len(all_tickers)} companies")
                            
                            # Build individual dashboards for each ticker
                            dashboards = []
                            for ticker in all_tickers:
                                dashboard_payload = build_cfi_dashboard_payload(self.analytics_engine, ticker)
                                if dashboard_payload:
                                    display = _display_ticker_symbol(_normalise_ticker_symbol(ticker))
                                    dashboards.append({
                                        "kind": "cfi-classic",
                                        "ticker": display,
                                        "payload": dashboard_payload,
                                    })
                            
                            if dashboards:
                                # Store all dashboards for multi-ticker display
                                # Use a special structure to indicate multiple dashboards
                                self.last_structured_response["dashboard"] = {
                                    "kind": "multi-cfi-classic",
                                    "dashboards": dashboards,
                                }
                                company_names = [d["payload"].get("meta", {}).get("company", d["ticker"]) for d in dashboards]
                                reply = f"Displaying financial dashboards for {', '.join(company_names)}."
                                emit("summary_complete", f"Dashboards prepared for {len(dashboards)} companies")
                            else:
                                reply = "Unable to build dashboards for the requested companies."
                                emit("summary_unavailable", "Dashboard data unavailable")
                        elif len(all_tickers) == 1:
                            # Single-ticker dashboard
                            ticker = all_tickers[0]
                            emit("summary_attempt", f"Compiling dashboard for {ticker}")
                            dashboard_payload = build_cfi_dashboard_payload(self.analytics_engine, ticker)
                            if dashboard_payload:
                                display = _display_ticker_symbol(_normalise_ticker_symbol(ticker))
                                self.last_structured_response["dashboard"] = {
                                    "kind": "cfi-classic",
                                    "ticker": display,
                                    "payload": dashboard_payload,
                                }
                                # Return brief message since dashboard shows all the data
                                company_name = dashboard_payload.get("meta", {}).get("company", "")
                                if company_name and company_name.upper() != display.upper():
                                    reply = f"Displaying financial dashboard for {company_name} ({display})."
                                else:
                                    reply = f"Displaying financial dashboard for {display}."
                                emit("summary_complete", f"Dashboard prepared for {ticker}")
                            else:
                                emit("summary_unavailable", f"Dashboard unavailable for {ticker}")
                        # If no tickers detected, fall through to other handlers
                    else:
                        # Not a dashboard request - check for regular summary
                        summary_target = self._detect_summary_target(user_input, normalized_command)
                        if summary_target:
                            # Use text summary for regular ticker queries (bare mentions only)
                            emit("summary_attempt", f"Compiling text summary for {summary_target}")
                            reply = self._get_ticker_summary(summary_target)
                            if reply:
                                emit("summary_complete", f"Text snapshot prepared for {summary_target}")
                            else:
                                emit("summary_unavailable", f"No cached snapshot available for {summary_target}")

            if reply is None:
                emit("context_build_start", "Gathering enhanced financial context")
                
                # Check if this is a portfolio query FIRST - portfolio queries get special handling
                portfolio_context = self._build_portfolio_context(user_input)
                
                if portfolio_context:
                    # For portfolio queries, use portfolio context as PRIMARY context
                    # This ensures the LLM focuses on the actual portfolio data
                    context = portfolio_context
                    LOGGER.info("Using portfolio context for query")
                    emit("context_build_ready", "Portfolio context compiled - using actual portfolio data")
                else:
                    # For non-portfolio queries, use regular financial context
                    context = self._build_enhanced_rag_context(user_input)
                    emit(
                        "context_build_ready",
                        "Context compiled" if context else "Context not required",
                    )
                
                messages = self._prepare_llm_messages(context)
                LOGGER.debug(f"Prepared {len(messages)} messages for LLM")
                emit("llm_query_start", "Composing explanation")
                reply = self.llm_client.generate_reply(messages)
                emit("llm_query_complete", "Explanation drafted")
                LOGGER.info(f"Generated reply length: {len(reply) if reply else 0} characters")

            if reply is None:
                emit("fallback", "Using enhanced fallback reply")
                reply = self._handle_enhanced_error(ErrorCategory.UNKNOWN_ERROR)

            emit("finalize", "Finalising response")
            database.log_message(
                self.settings.database_path,
                self.conversation.conversation_id,
                role="assistant",
                content=reply,
                created_at=datetime.utcnow(),
            )
            self.conversation.messages.append({"role": "assistant", "content": reply})

            if cacheable and not cached_entry and reply:
                emit("cache_store", "Caching response for future reuse")
                self._store_cached_reply(canonical_prompt, reply)

            emit("complete", "Response ready")
            return reply
        finally:
            self._active_progress_callback = previous_callback


    def history(self) -> Iterable[database.Message]:
        """Return the stored conversation from the database."""
        return database.fetch_conversation(
            self.settings.database_path, self.conversation.conversation_id
        )

    def reset(self) -> None:
        """Start a fresh conversation while keeping the same configuration."""
        self.conversation = Conversation()

    # ----------------------------------------------------------------------------------
    # Intent handling helpers
    # ----------------------------------------------------------------------------------
    def _handle_financial_intent(self, text: str) -> Optional[str]:
        """Route based on query type - prefer natural language for questions."""
        
        lowered = text.strip().lower()
        
        # 1. Help command
        if lowered == "help":
            return HELP_TEXT
        
        # 2. Explicit legacy commands (highest priority - exact matches)
        if lowered.startswith("fact "):
            return self._handle_fact_command(text)
        if lowered.startswith("fact-range "):
            return self._handle_fact_range_command(text)
        if lowered.startswith("table "):
            table_output = render_table_command(text, self.analytics_engine)
            if table_output is None:
                return "Unable to generate a table for that request."
            return table_output
        if lowered.startswith("audit "):
            return self._handle_audit_command(text)
        if lowered.startswith("ingest "):
            return self._handle_ingest_command(text)
        if lowered.startswith("scenario "):
            return self._handle_scenario_command(text)

        # 3. Explicit comparison with "vs" (table format)
        if lowered.startswith("compare ") and self._is_legacy_compare_command(text):
            tokens = text.split()[1:]
            return self._handle_metrics_comparison(tokens)
        
        # 4. Check if this is a natural language QUESTION (not a table request)
        question_patterns = [
            # CRITICAL: Contractions MUST come first to catch "What's", "How's" etc.
            r'\bwhat\'s\b',  # "what's" contraction - CRITICAL for "What's Apple revenue?"
            r'\bhow\'s\b',   # "how's" contraction
            r'\bwhat\s+(?:is|are|was|were|has|have|will|can|should|would|about|does|did)\b',
            r'\bhow\s+(?:much|many|does|did|is|are|has|have|will|can|should|would|about|to|do|profitable|fast|good|bad|strong|weak)\b',
            r'\bwhy\b',
            r'\bexplain\b',
            r'\btell\s+me\s+(?:about|why|how)\b',
            r'\bis\s+\w+\s+(?:more|less|better|worse|higher|lower)',
            r'\bis\s+\w+\s+(?:overvalued|undervalued|expensive|cheap|good|bad|risky|safe|strong|weak|profitable|worth)',  # "Is X overvalued?"
            r'\bwhich\s+(?:company|stock|one|is|has|have)\b',
            r'\bcan\s+you\b',
            r'\bdoes\s+\w+\s+have\b',
            r'\bshould\s+i\b',
            r'\bwhen\s+(?:is|are|was|were|did|will)\b',
            r'\bwhere\s+(?:is|are|can|do)\b',
            # Follow-up question patterns
            r'^\s*(?:what|how)\s+about\b',  # "What about..." "How about..."
            r'\b(?:their|its|theirs)\b',  # Pronouns indicating context reference
            r'\b(?:them|it)\s+(?:compare|versus|vs)\b',  # "compare them", "compare it"
            r'\bcompare\s+(?:them|those|these)\b',  # "compare them"
        ]
        
        is_question = any(re.search(pattern, lowered) for pattern in question_patterns)
        
        if is_question:
            # Natural language question - let LLM handle with context
            self._progress("intent_question", "Natural language question detected")
            return None  # Will trigger LLM with enhanced context
        
        # 5. Check for explicit "show X kpis/metrics/table" pattern (table request)
        if re.search(r'\bshow\s+.*\s+(?:kpis?|metrics?|table)', lowered):
            structured = parse_to_structured(text)
            self.last_structured_response["parser"] = structured

            # Optional: Enhanced routing
            if self.settings.enable_enhanced_routing:
                enhanced_routing = enhance_structured_parse(text, structured)
                # Check for portfolio intents early
                if enhanced_routing and enhanced_routing.intent.value.startswith("portfolio_"):
                    # Portfolio intents should be handled by LLM with portfolio context
                    return None
                self.last_structured_response["enhanced_routing"] = {
                    "intent": enhanced_routing.intent.value,
                    "confidence": enhanced_routing.confidence,
                }
                # Lower threshold for table commands
                if enhanced_routing.confidence < 0.5:
                    return None
            
            if structured:
                structured_reply = self._handle_structured_metrics(structured)
                if structured_reply:
                    return structured_reply

        # 6. Check for complex natural language that should use LLM
        if self._is_complex_natural_language_query(text):
            return None
        
        # 7. Try structured parsing as fallback (but with lower priority)
        try:
            structured = parse_to_structured(text)
        except Exception as e:
            LOGGER.debug(f"Structured parsing failed: {e}")
            structured = {}
        
        self.last_structured_response["parser"] = structured
        
        # Optional: Enhanced routing
        enhanced_routing = None
        if self.settings.enable_enhanced_routing:
            try:
                enhanced_routing = enhance_structured_parse(text, structured)
            except Exception as e:
                LOGGER.debug(f"Enhanced routing failed: {e}")
                enhanced_routing = None
            
            if enhanced_routing:
                try:
                    self.last_structured_response["enhanced_routing"] = {
                        "intent": enhanced_routing.intent.value,
                        "confidence": enhanced_routing.confidence,
                        "force_dashboard": enhanced_routing.force_dashboard,
                        "force_text_only": enhanced_routing.force_text_only,
                    }
                except Exception as e:
                    LOGGER.debug(f"Failed to store enhanced routing: {e}")
                
                # Higher threshold now - prefer LLM unless very confident
                if enhanced_routing.confidence < 0.8:
                    return None
                
                # Check for portfolio intents first (before other checks)
                if enhanced_routing.intent.value.startswith("portfolio_"):
                    # Portfolio intents should be handled by LLM with portfolio context
                    # Don't try to process them as structured metrics
                    return None
        
        # If structured parsing detected compare intent, handle it
        if structured:
            tickers_list = structured.get('tickers')
            if tickers_list is None:
                tickers_list = []
            if (isinstance(tickers_list, list) and
                len(tickers_list) >= 2 and
                structured.get('intent') == 'compare'):
                try:
                    structured_reply = self._handle_structured_metrics(structured)
                    if structured_reply:
                        return structured_reply
                except Exception as e:
                    LOGGER.debug(f"Failed to handle structured metrics: {e}")

        # Check for natural language fallback conditions
        try:
            if self._should_fallback_to_llm(structured):
                return None
        except Exception as e:
            LOGGER.debug(f"Failed to check fallback: {e}")
            # If fallback check fails, default to LLM
            return None
        
        # 8. Default: Let LLM handle with context
        return None

    def _is_legacy_compare_command(self, text: str) -> bool:
        """Determine if this is a legacy compare command vs natural language comparison."""
        # Legacy compare commands are typically: "compare AAPL MSFT" or "compare AAPL MSFT GOOGL"
        # Natural language comparisons are: "Compare Apple vs Microsoft revenue"
        
        tokens = text.split()
        if len(tokens) < 3:  # "compare AAPL" is too short
            return False
        
        # Check if there are natural language words like "vs", "versus", "revenue", etc., it's natural language
        natural_language_words = ["vs", "versus", "revenue", "earnings", "profit", "income", "sales", "growth", "performance", "results", "financial", "metrics", "data", "analysis"]
        has_natural_language = any(word.lower() in text.lower() for word in natural_language_words)
        
        if has_natural_language:
            return False  # It's natural language, not legacy command
        
        # Check if tokens after "compare" look like ticker symbols (uppercase, 1-5 chars)
        ticker_like_tokens = []
        for token in tokens[1:]:  # Skip "compare"
            if token.isupper() and len(token) <= 5 and token.isalpha():
                ticker_like_tokens.append(token)
        
        # If most tokens look like ticker symbols, it's likely a legacy command
        if len(ticker_like_tokens) >= 2:
            return True
        
        # Default to not legacy command if unclear
        return False

    def _is_complex_natural_language_query(self, text: str) -> bool:
        """Detect complex natural language queries that should go directly to LLM."""
        lowered = text.lower()
        
        # Complex query patterns that should bypass structured parsing
        complex_patterns = [
            "tell me about", "how is", "what are the key", "explain the risks",
            "sector analysis", "market outlook", "investment advice", "what's the",
            "how do you", "can you explain", "what does it mean", "how does",
            "what are the", "what is the", "how are the", "can you tell me"
        ]
        
        for pattern in complex_patterns:
            if pattern in lowered:
                return True
        
        # Queries with multiple question words
        question_words = ["what", "how", "why", "when", "where", "which"]
        question_count = sum(1 for word in question_words if word in lowered)
        if question_count >= 2:
            return True
        
        # Sector/industry related queries
        sector_keywords = ["sector", "industry", "market", "economy", "outlook", "trends"]
        for keyword in sector_keywords:
            if keyword in lowered:
                return True
        
        return False

    def _should_fallback_to_llm(self, structured: Optional[Dict[str, Any]]) -> bool:
        """Determine if the query should fall back to LLM instead of structured parsing."""
        if not structured:
            return True
        try:
            intent = structured.get("intent")
            tickers_raw = structured.get("tickers")
            metrics_raw = structured.get("vmetrics")
            norm_text = structured.get("norm_text", "") or ""
            
            # Safely extract tickers - handle None and non-list values
            tickers = []
            if tickers_raw is not None:
                if isinstance(tickers_raw, list):
                    # Filter out None values and extract ticker strings from dicts
                    for item in tickers_raw:
                        if item is None:
                            continue
                        if isinstance(item, dict):
                            ticker = item.get("ticker")
                            if ticker and isinstance(ticker, str):
                                tickers.append(ticker)
                        elif isinstance(item, str):
                            tickers.append(item)
            
            # Safely extract metrics
            metrics = []
            if metrics_raw is not None:
                if isinstance(metrics_raw, list):
                    metrics = [m for m in metrics_raw if m is not None]
            
            # Fall back to LLM if:
            # 1. Intent is unclear or parsing seems forced
            if not intent or (intent == "lookup" and not tickers and not metrics):
                return True
            
            # 2. Too many ambiguous tickers parsed (likely over-parsing)
            if len(tickers) > 3:
                return True
                
            # 3. Complex natural language patterns that don't fit structured intents
            complex_patterns = [
                "tell me about", "how is", "what are the key", "explain the risks",
                "sector analysis", "market outlook", "investment advice"
            ]
            
            for pattern in complex_patterns:
                if norm_text and pattern in norm_text.lower():
                    return True
                    
            # 4. Ambiguous ticker parsing for ranking/explain queries
            if intent in ["rank", "explain_metric"]:
                # If tickers were parsed but shouldn't have been
                if tickers and norm_text:
                    # Filter out None values from tickers list
                    valid_tickers = [t for t in tickers if t is not None and isinstance(t, str)]
                    if valid_tickers:
                        # Check if any ticker is in the norm_text
                        norm_upper = norm_text.upper()
                        if not any(ticker in norm_upper for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]):
                            return True
            
            return False
        except Exception as e:
            LOGGER.debug(f"Error in _should_fallback_to_llm: {e}")
            # If any error occurs, default to LLM
            return True

    def _get_company_name(self, ticker: str) -> str:
        """Get company name for ticker symbol."""
        try:
            # Try to get company name from database
            from .web import _lookup_company_name
            company_name = _lookup_company_name(ticker)
            if company_name:
                return company_name
        except Exception:
            pass
        
        # Fallback to ticker symbol
        return ticker

    def _handle_metrics_comparison(self, tokens: Sequence[str]) -> str:
        """Render a comparison table for the resolved tickers/metrics."""
        cleaned_tokens: List[str] = []
        for token in tokens:
            stripped = token.strip()
            if not stripped:
                continue
            upper = stripped.upper().rstrip(',')
            if upper in {"VS", "AND", "FOR"}:
                continue
            cleaned_tokens.append(stripped)

        tickers, period_filters = self._split_tickers_and_periods(cleaned_tokens)
        if len(tickers) < 2:
            return "Usage: compare <TICKER_A> <TICKER_B> [MORE] [YEAR]"
        resolution = self._resolve_tickers(tickers)
        if resolution.missing:
            return self._format_missing_message(tickers, resolution.available or [])
        if not resolution.available:
            return self._format_missing_message(tickers, [])
        return self._format_metrics_table(
            resolution.available, period_filters=period_filters
        )

    def _dispatch_metrics_request(
        self,
        tickers: Sequence[str],
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
    ) -> str:
        """Fetch metrics and build a response message for the chat."""
        if not tickers:
            return "Provide at least one ticker for metrics."
        
        # Always use text table format for chat responses
        # Dashboards are only built via explicit "dashboard" keyword
        return self._format_metrics_table(
            tickers,
            period_filters=period_filters,
        )

    def _handle_structured_metrics(self, structured: Dict[str, Any]) -> Optional[str]:
        """Handle parsed structured intents without relying on legacy commands."""
        if not structured:
            return None
        tickers = structured.get("tickers")
        if tickers is None:
            tickers = []
        if not isinstance(tickers, list):
            return None
        unique_tickers: List[str] = []
        for entry in tickers:
            if entry is None:
                continue
            if not isinstance(entry, dict):
                continue
            ticker = entry.get("ticker")
            if ticker and isinstance(ticker, str) and ticker not in unique_tickers:
                unique_tickers.append(ticker)

        if not unique_tickers:
            return None

        resolution = self._resolve_tickers(unique_tickers)
        if resolution.missing and (not resolution.available or len(resolution.available) == 0):
            return self._format_missing_message(unique_tickers, resolution.available or [])

        resolved_tickers = resolution.available if resolution.available else unique_tickers
        period_filters = self._periods_to_filters(structured.get("periods", {}))

        intent = structured.get("intent")
        if intent == "compare" and len(resolved_tickers) >= 2:
            # Check if specific metrics are requested
            requested_metrics = structured.get("vmetrics", []) or []
            if requested_metrics and isinstance(requested_metrics, list):
                # Filter to only requested metrics
                metric_keys = []
                for metric in requested_metrics:
                    if metric is None:
                        continue
                    if not isinstance(metric, dict):
                        continue
                    key = metric.get("key")
                    if key and isinstance(key, str):
                        metric_keys.append(key)
                if metric_keys:
                    return self._format_metrics_table(resolved_tickers, period_filters=period_filters, metric_filter=metric_keys)
            return self._format_metrics_table(resolved_tickers, period_filters=period_filters)

        if intent in {"lookup", "trend", "rank"}:
            return self._dispatch_metrics_request(resolved_tickers, period_filters)

        return None

    @staticmethod
    def _periods_to_filters(periods: Dict[str, Any]) -> Optional[List[tuple[int, int]]]:
        """Convert parsed period metadata into fiscal year filters."""
        if not periods:
            return None
        items = periods.get("items") or []
        if periods.get("type") == "range" and len(items) >= 2:
            start = items[0].get("fy")
            end = items[-1].get("fy")
            if start is not None and end is not None:
                if end < start:
                    start, end = end, start
                return [(start, end)]

        years: List[int] = []
        for item in items:
            year = item.get("fy")
            if year is None or year in years:
                continue
            years.append(year)

        if not years:
            return None

        years_sorted = sorted(years)
        if periods.get("type") == "multi":
            return [(year, year) for year in years_sorted]
        return [(years_sorted[0], years_sorted[-1])]

    def _handle_ingest_command(self, text: str) -> str:
        """Execute ingestion commands issued by the user."""
        parts = text.split()
        if len(parts) < 2:
            return "Usage: ingest <TICKER> [years]"
        if parts[1].lower() == "status":
            if len(parts) < 3:
                return "Usage: ingest status <TICKER>"
            ticker = parts[2].upper()
            manager = tasks.get_task_manager(self.settings)
            status = manager.get_status(ticker)
            if not status:
                return f"No ingestion task found for {ticker}."
            return (
                f"Ingestion status for {ticker}: {status.summary()} "
                f"(submitted {status.submitted_at:%Y-%m-%d %H:%M:%S} UTC)"
            )

        ticker = parts[1].upper()
        years = 5
        if len(parts) >= 3:
            try:
                years = int(parts[2])
            except ValueError:
                return "Years must be an integer (e.g. ingest TSLA 5)."
        manager = tasks.get_task_manager(self.settings)
        manager.submit_ingest(ticker, years=years)
        current_status = manager.get_status(ticker)
        summary = current_status.summary() if current_status else "queued"
        return (
            f"Ingestion for {ticker} queued (status: {summary}). "
            f"Use 'ingest status {ticker}' to check progress."
        )

    def _handle_scenario_command(self, text: str) -> str:
        """Run scenario modelling commands and persist the results."""
        parts = text.split()
        if len(parts) < 3:
            return "Usage: scenario <TICKER> <NAME> [rev=+5% margin=+1% mult=+0.5%]"

        ticker = parts[1].upper()
        name = parts[2]
        deltas = {
            "revenue_growth_delta": 0.0,
            "ebitda_margin_delta": 0.0,
            "multiple_delta": 0.0,
        }
        for token in parts[3:]:
            token_lower = token.lower()
            if token_lower.startswith("rev="):
                deltas["revenue_growth_delta"] = self._parse_percent(token_lower[4:])
            elif token_lower.startswith("margin="):
                deltas["ebitda_margin_delta"] = self._parse_percent(token_lower[7:])
            elif token_lower.startswith("mult="):
                deltas["multiple_delta"] = self._parse_percent(token_lower[5:])

        runner = getattr(self.analytics_engine, 'run_scenario', None)
        if not callable(runner):
            return 'Scenario analysis is not available in this configuration.'

        summary = runner(
            ticker,
            scenario_name=name,
            **deltas,
        )
        return getattr(summary, 'narrative', str(summary))

    # ----------------------------------------------------------------------------------
    # Fact and audit helpers
    # ----------------------------------------------------------------------------------
    def _handle_fact_command(self, text: str) -> str:
        """Return detailed fact rows for the requested ticker/year."""
        match = re.match(
            r"fact\s+([A-Za-z0-9.-]+)\s+(?:FY)?(\d{4})(?:\s*Q([1-4]))?(?:\s+([A-Za-z0-9_]+))?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return "Usage: fact <TICKER> <YEAR>[Q#] [metric]"
        raw_ticker = match.group(1).upper()
        fiscal_year = int(match.group(2))
        quarter_token = match.group(3)
        quarter_label = f"Q{quarter_token}" if quarter_token else None
        metric = match.group(4)
        metric_key = metric.lower() if metric else None

        resolution = self._resolve_tickers([raw_ticker])
        if resolution.missing and not resolution.available:
            return self._format_missing_message([raw_ticker], [])
        ticker = resolution.available[0] if resolution.available else raw_ticker
        resolved_note = None
        if resolution.available and raw_ticker not in resolution.available and ticker != raw_ticker:
            resolved_note = f"(resolved {raw_ticker} to {ticker})"

        facts = self.analytics_engine.financial_facts(
            ticker=ticker,
            fiscal_year=fiscal_year,
            metric=metric_key,
            limit=20,
        )
        if metric_key:
            facts = [fact for fact in facts if fact.metric.lower() == metric_key]
        if quarter_label:
            quarter_upper = quarter_label.upper()
            facts = [
                fact
                for fact in facts
                if (
                    (fact.fiscal_period and quarter_upper in fact.fiscal_period.upper())
                    or (fact.period and quarter_upper in fact.period.upper())
                )
            ]
        if not facts:
            if metric_key:
                if quarter_label:
                    return (
                        f"No {metric_key} facts stored for {ticker} in FY{fiscal_year} {quarter_label}."
                    )
                return (
                    f"No {metric_key} facts stored for {ticker} in FY{fiscal_year}."
                )
            if quarter_label:
                return f"No financial facts stored for {ticker} in FY{fiscal_year} {quarter_label}."
            return f"No financial facts stored for {ticker} in FY{fiscal_year}."

        title_metric = metric_key.replace('_', ' ') if metric_key else 'financial facts'
        heading = f"{title_metric.title()} for {ticker} FY{fiscal_year}"
        if quarter_label:
            heading += f" {quarter_label}"
        if resolved_note:
            heading += f" {resolved_note}"
        lines_out = [heading + ":"]
        for fact in facts:
            label = fact.metric.replace('_', ' ')
            value_text = self._format_fact_value(fact.value)
            parts = [f"source={fact.source}"]
            period_hint = fact.period or fact.fiscal_period
            if period_hint:
                parts.append(f"period={period_hint}")
            if fact.adjusted:
                parts.append("adjusted")
            if fact.adjustment_note:
                parts.append(f"note: {fact.adjustment_note}")
            detail = ", ".join(parts)
            lines_out.append(f"- {label}: {value_text} ({detail})")
        return "\n".join(lines_out)

    def _handle_fact_range_command(self, text: str) -> str:
        """Return year-over-year fact series for a ticker."""
        match = re.match(
            r"fact-range\s+([A-Za-z0-9.-]+)\s+(\d{4})-(\d{4})(?:\s+([A-Za-z0-9_]+))?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return "Usage: fact-range <TICKER> <START-END> [metric]"
        raw_ticker = match.group(1).upper()
        start_year = int(match.group(2))
        end_year = int(match.group(3))
        if end_year < start_year:
            start_year, end_year = end_year, start_year
        metric = match.group(4) or "revenue"
        metric_key = metric.lower()

        resolution = self._resolve_tickers([raw_ticker])
        if resolution.missing and not resolution.available:
            return self._format_missing_message([raw_ticker], [])
        ticker = resolution.available[0] if resolution.available else raw_ticker
        resolved_note = ""
        if resolution.available and raw_ticker not in resolution.available and ticker != raw_ticker:
            resolved_note = f" (resolved {raw_ticker} to {ticker})"

        rows: List[tuple[int, Optional[str]]] = []
        for year in range(start_year, end_year + 1):
            facts = self.analytics_engine.financial_facts(
                ticker=ticker,
                fiscal_year=year,
                metric=metric_key,
                limit=20,
            )
            if metric_key:
                facts = [fact for fact in facts if fact.metric.lower() == metric_key]
            value_display: Optional[str] = None
            for fact in facts:
                if fact.fiscal_period and fact.fiscal_period.upper().startswith("Q"):
                    continue
                value_display = self._format_fact_value(fact.value)
                break
            if value_display is None and facts:
                value_display = self._format_fact_value(facts[0].value)
            rows.append((year, value_display))

        if not any(value for _, value in rows):
            metric_label = metric_key.replace("_", " ")
            return (
                f"No {metric_label} facts stored for {ticker} between FY{start_year} and FY{end_year}."
            )

        metric_label = metric_key.replace('_', ' ')
        lines = [
            f"{metric_label.title()} for {ticker} FY{start_year}-{end_year}{resolved_note}:",
            "Year | Value",
            "-----|------",
        ]
        for year, value in rows:
            value_display = value if value is not None else "n/a"
            lines.append(f"{year} | {value_display}")
        return "\n".join(lines)

    def _handle_audit_command(self, text: str) -> str:
        """Summarise audit events for a given ticker."""
        match = re.match(r"audit\s+([A-Za-z0-9.-]+)(?:\s+(?:FY)?(\d{4}))?", text, re.IGNORECASE)
        if not match:
            return "Usage: audit <TICKER> [YEAR]"
        raw_ticker = match.group(1).upper()
        year_token = match.group(2)
        fiscal_year = int(year_token) if year_token else None

        resolution = self._resolve_tickers([raw_ticker])
        if resolution.missing and not resolution.available:
            return self._format_missing_message([raw_ticker], [])
        ticker = resolution.available[0] if resolution.available else raw_ticker

        events = self.analytics_engine.audit_events(
            ticker,
            fiscal_year=fiscal_year,
            limit=10,
        )
        if not events:
            suffix = f" in FY{fiscal_year}" if fiscal_year else ""
            return f"No audit events recorded for {ticker}{suffix}."

        header = f"Audit trail for {ticker}"
        if fiscal_year:
            header += f" FY{fiscal_year}"
        lines_out = [header + ":"]
        for event in events:
            timestamp = event.created_at.strftime("%Y-%m-%d %H:%M")
            entity = f" [{event.entity_id}]" if event.entity_id else ""
            lines_out.append(
                f"- {timestamp}{entity} ({event.event_type}) {event.details} [by {event.created_by}]"
            )
        return "\n".join(lines_out)

    # ----------------------------------------------------------------------------------
    # Parsing helpers
    # ----------------------------------------------------------------------------------
    @staticmethod
    def _parse_percent(value: str) -> float:
        """Interpret percentage tokens and return them as floats."""
        value = value.strip().rstrip("%")
        try:
            return float(value) / 100.0
        except ValueError:
            return 0.0

    def _parse_metrics_request(self, text: str) -> Optional["BenchmarkOSChatbot._MetricsRequest"]:
        """Convert free-form text into a structured metrics request."""
        match = _METRICS_PATTERN.match(text.strip())
        if not match:
            return None
        remainder = match.group(1)
        remainder = remainder.replace(",", " ")
        remainder = remainder.replace(" vs ", " ")
        remainder = remainder.replace(" and ", " ")
        tokens = [token for token in remainder.split() if token]
        tickers, period_filters = self._split_tickers_and_periods(tokens)
        return BenchmarkOSChatbot._MetricsRequest(
            tickers=tickers,
            period_filters=period_filters,
        )

    def _split_tickers_and_periods(
        self, tokens: Sequence[str]
    ) -> tuple[List[str], Optional[List[tuple[int, int]]]]:
        """Separate ticker symbols from potential period filters."""
        period_filters: List[tuple[int, int]] = []
        tickers: List[str] = []
        for token in tokens:
            parsed = self._parse_period_token(token)
            if parsed:
                period_filters.append(parsed)
                continue
            cleaned = token.strip().upper().rstrip(',')
            if not cleaned or cleaned in {"VS", "AND", "FOR"}:
                continue
            tickers.append(cleaned)
        return tickers, (period_filters or None)

    @staticmethod
    def _parse_period_token(token: str) -> Optional[tuple[int, int]]:
        """Convert textual period filters into numeric start/end years."""
        cleaned = token.strip().upper().rstrip(',')
        if cleaned.startswith('FY'):
            cleaned = cleaned[2:]
        cleaned = cleaned.strip()
        if not cleaned:
            return None
        match = re.fullmatch(r"(\d{4})(?:\s*[-/]\s*(\d{4}))?", cleaned)
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        if end < start:
            start, end = end, start
        return (start, end)

    # ----------------------------------------------------------------------------------
    # Metrics formatting helpers
    # ----------------------------------------------------------------------------------
    @dataclass
    class _MetricsRequest:
        """Structured representation of a parsed metrics request."""
        tickers: List[str]
        period_filters: Optional[List[tuple[int, int]]]

    @dataclass
    class _TickerResolution:
        """Tracks which tickers resolved successfully versus missing."""
        available: List[str]
        missing: List[str]

    def _resolve_tickers(self, subjects: Sequence[str]) -> "BenchmarkOSChatbot._TickerResolution":
        """Resolve tickers against the dataset, recording missing entries."""
        subjects_list = list(subjects)
        if subjects_list:
            joined = ", ".join(subjects_list)
            self._progress("ticker_resolution_start", f"Resolving tickers: {joined}")

        available: List[str] = []
        missing: List[str] = []
        lookup = getattr(self.analytics_engine, "lookup_ticker", None)
        for subject in subjects_list:
            resolved: Optional[str] = None
            if callable(lookup):
                try:
                    resolved = lookup(subject, allow_partial=True)  # type: ignore[misc]
                except TypeError:
                    try:
                        resolved = lookup(subject)  # type: ignore[misc]
                    except Exception:
                        resolved = None
                except Exception:
                    resolved = None
            if not resolved:
                resolved = self._name_to_ticker(subject)
            if resolved:
                resolved = resolved.upper()
                if resolved not in available:
                    available.append(resolved)
                continue

            candidate = subject.upper()
            try:
                records = self._fetch_metrics_cached(candidate)
            except Exception:
                records = []
            if records:
                if candidate not in available:
                    available.append(candidate)
                continue
            suggestions = self._suggest_tickers([subject], limit=1)
            if suggestions:
                suggestion = suggestions[0].upper()
                if suggestion not in available:
                    available.append(suggestion)
                continue
            missing.append(subject)

        if subjects_list:
            if available:
                detail = f"Resolved: {', '.join(available)}"
                if missing:
                    detail += f" | Missing: {', '.join(missing)}"
            elif missing:
                detail = f"Unable to resolve: {', '.join(missing)}"
            else:
                detail = "No tickers provided"
            self._progress("ticker_resolution_complete", detail)

        return BenchmarkOSChatbot._TickerResolution(available=available, missing=missing)

    def _format_missing_message(
        self, requested: Sequence[str], available: Optional[Sequence[str]]
    ) -> str:
        """Build a friendly message for unresolved tickers."""
        if available is None:
            available = []
        missing = [ticker for ticker in requested if ticker.upper() not in available]
        suggestions = self._suggest_tickers(missing)
        hint_parts: List[str] = []
        if available:
            hint_parts.extend(sorted({ticker.upper() for ticker in available}))
        if suggestions:
            hint_parts.extend(suggestions)
        if hint_parts:
            hint = ", ".join(dict.fromkeys(hint_parts))
            return (
                "Unable to resolve one or more tickers. Try specifying: "
                f"{hint}."
            )
        missing_list = ", ".join(missing)
        return (
            f"Unable to resolve: {missing_list}. Ingest the data first using "
            "'ingest <ticker>'."
        )

    def _suggest_tickers(
        self,
        subjects: Sequence[str],
        limit: int = 5,
    ) -> List[str]:
        """Offer fuzzy ticker suggestions for unresolved names."""
        suggestions: List[str] = []
        seen = set()
        for subject in subjects:
            for ticker, score in self.name_index.resolve_fuzzy(subject, n=limit, cutoff=0.6):
                ticker = ticker.upper()
                if ticker in seen:
                    continue
                suggestions.append(ticker)
                seen.add(ticker)
                if len(suggestions) >= limit:
                    return suggestions
        return suggestions

    def _record_span(self, record: database.MetricRecord) -> Optional[tuple[int, int]]:
        """Best-effort extraction of a (start_year, end_year) tuple for a metric snapshot."""
        if record.period:
            try:
                return self.analytics_engine._period_span(record.period)
            except Exception:
                pass
        start = record.start_year or record.end_year or 0
        end = record.end_year or record.start_year or 0
        if not start and not end:
            return None
        if start and not end:
            end = start
        if end and not start:
            start = end
        return (start, end)

    def _format_period_label(
        self,
        record: database.MetricRecord,
        span: Optional[tuple[int, int]] = None,
    ) -> Optional[str]:
        """Return a human readable label for a metric snapshot period."""
        if record.period:
            return record.period
        span = span or self._record_span(record)
        if not span:
            return None
        start, end = span
        if start and end and start != end:
            return f"FY{start}-FY{end}"
        year = end or start
        return f"FY{year}" if year else None

    def _build_trend_series(
        self,
        histories: Mapping[str, Sequence[database.MetricRecord]],
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        """Compile time series data suitable for lightweight trend visualisations."""
        trend_series: List[Dict[str, Any]] = []
        allowed_metrics = {metric.lower() for metric in TREND_METRICS}
        for ticker in tickers:
            records = histories.get(ticker)
            if not records:
                continue
            metric_points: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for record in records:
                metric_name = record.metric.lower()
                if metric_name not in allowed_metrics:
                    continue
                if record.value is None:
                    continue
                span = self._record_span(record)
                sort_key = span or (
                    record.start_year or 0,
                    record.end_year or 0,
                )
                label = self._format_period_label(record, span)
                formatted = self._format_metric_value(
                    metric_name,
                    {metric_name: record},
                )
                metric_points[metric_name].append(
                    {
                        "sort": sort_key,
                        "period": label or record.period or "",
                        "value": record.value,
                        "formatted": formatted,
                    }
                )
            for metric_name, points in metric_points.items():
                if not points:
                    continue
                points.sort(key=lambda item: (item["sort"][0], item["sort"][1]))
                serialised_points = [
                    {
                        "period": point["period"],
                        "value": point["value"],
                        "formatted_value": point["formatted"],
                    }
                    for point in points
                    if point["period"]
                ]
                if len(serialised_points) < 2:
                    continue
                trend_series.append(
                    {
                        "ticker": ticker,
                        "metric": metric_name,
                        "label": _METRIC_LABEL_MAP.get(
                            metric_name, metric_name.replace("_", " ").title()
                        ),
                        "points": serialised_points,
                    }
                )
        return trend_series

    def _build_filing_urls(
        self, accession: Optional[str], cik: Optional[str]
    ) -> Dict[str, Optional[str]]:
        """Mirror the filing URL helpers used by the FastAPI layer for reuse in chat."""
        if not accession:
            return {"interactive": None, "detail": None, "search": None}
        if cik:
            clean_cik = cik.lstrip("0") or cik
            accession_no_dash = accession.replace("-", "")
            interactive = (
                "https://www.sec.gov/cgi-bin/viewer"
                f"?action=view&cik={clean_cik}&accession_number={accession}&xbrl_type=v"
            )
            detail = (
                f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/"
                f"{accession_no_dash}/{accession}-index.html"
            )
            search = (
                f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={clean_cik}"
            )
            return {"interactive": interactive, "detail": detail, "search": search}
        return {"interactive": None, "detail": None, "search": None}

    def _build_metric_citations(
        self,
        metrics_per_ticker: Mapping[str, Dict[str, database.MetricRecord]],
        tickers: Sequence[str],
        limit: int = 24,
    ) -> List[Dict[str, Any]]:
        """Generate a concise list of fact sources underpinning the response."""
        citations: List[Dict[str, Any]] = []
        for ticker in tickers:
            metric_map = metrics_per_ticker.get(ticker)
            if not metric_map:
                continue
            for metric_name, record in metric_map.items():
                if len(citations) >= limit:
                    break
                label = _METRIC_LABEL_MAP.get(
                    metric_name, metric_name.replace("_", " ").title()
                )
                span = self._record_span(record)
                period_label = self._format_period_label(record, span)
                formatted_value = self._format_metric_value(
                    metric_name, {metric_name: record}
                )
                citation: Dict[str, Any] = {
                    "ticker": ticker,
                    "metric": metric_name,
                    "label": label,
                    "period": period_label,
                    "value": record.value,
                    "formatted_value": formatted_value,
                    "source": getattr(record, "source", None),
                }
                fiscal_year = None
                if span and span[1]:
                    fiscal_year = span[1]
                elif record.end_year:
                    fiscal_year = record.end_year
                fact_records: Sequence[database.FinancialFactRecord] = ()
                try:
                    fact_records = self.analytics_engine.financial_facts(
                        ticker=ticker,
                        fiscal_year=fiscal_year,
                        metric=metric_name,
                        limit=1,
                    )
                except Exception:  # pragma: no cover - safety guard
                    fact_records = ()
                if fact_records:
                    fact = fact_records[0]
                    citation["filing"] = fact.source_filing
                    citation["unit"] = fact.unit
                    raw_payload: Any = fact.raw or {}
                    if isinstance(raw_payload, str):
                        try:
                            raw_payload = json.loads(raw_payload)
                        except Exception:
                            raw_payload = {}
                    accession = None
                    if isinstance(raw_payload, dict):
                        accession = raw_payload.get("accn") or raw_payload.get("accession")
                        if not citation.get("filing") and raw_payload.get("filed"):
                            citation["filed_at"] = raw_payload.get("filed")
                        if raw_payload.get("form"):
                            citation["form"] = raw_payload.get("form")
                    accession = accession or fact.source_filing
                    urls = self._build_filing_urls(accession, getattr(fact, "cik", None))
                    citation["urls"] = urls
                citations.append(citation)
            if len(citations) >= limit:
                break
        return citations

    def _build_export_payloads(
        self,
        table_data: Optional[Dict[str, Any]],
        highlights: Sequence[str],
        citations: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Prepare lightweight export descriptors consumed by the web UI."""
        if not table_data:
            return []
        headers = table_data.get("headers") or []
        rows = table_data.get("rows") or []
        if not headers or not rows:
            return []
        descriptor = table_data.get("descriptor")
        tickers = table_data.get("tickers") or []
        slug = "-vs-".join(ticker.lower().replace(" ", "-") for ticker in tickers if ticker)
        if not slug:
            slug = "metrics"
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        base_name = f"benchmarkos-{slug}-{timestamp}"
        csv_payload = {
            "type": "csv",
            "label": "Download CSV",
            "filename": f"{base_name}.csv",
            "headers": headers,
            "rows": rows,
            "descriptor": descriptor,
        }
        pdf_payload = {
            "type": "pdf",
            "label": "Download PDF",
            "filename": f"{base_name}.pdf",
            "headers": headers,
            "rows": rows,
            "descriptor": descriptor,
            "highlights": list(highlights),
            "title": table_data.get("title"),
        }
        sources: List[Dict[str, str]] = []
        for citation in citations or []:
            if not isinstance(citation, dict):
                continue
            parts = [
                str(citation.get("ticker") or "").strip() or None,
                str(citation.get("label") or "").strip() or None,
                str(citation.get("period") or "").strip() or None,
                str(citation.get("formatted_value") or "").strip()
                or (
                    str(citation.get("value"))
                    if citation.get("value") is not None
                    else None
                ),
                str(citation.get("form") or "").strip() or None,
            ]
            descriptor = " • ".join(part for part in parts if part)
            urls = citation.get("urls") if isinstance(citation.get("urls"), dict) else {}
            url = urls.get("detail") or urls.get("interactive")
            if descriptor or url:
                entry: Dict[str, str] = {"text": descriptor}
                if url:
                    entry["url"] = url
                sources.append(entry)
        if sources:
            pdf_payload["sources"] = sources
        return [csv_payload, pdf_payload]

    def _format_metrics_table(
        self,
        tickers: Sequence[str],
        *,
        period_filters: Optional[Sequence[tuple[int, int]]] = None,
        metric_filter: Optional[List[str]] = None,
    ) -> str:
        """Render metrics output as a table suitable for chat."""
        metrics_per_ticker: Dict[str, Dict[str, database.MetricRecord]] = {}
        histories: Dict[str, List[database.MetricRecord]] = {}
        kpi_overrides: Dict[str, Dict[str, Tuple[database.KpiValueRecord, bool]]] = {}
        missing: List[str] = []
        latest_spans: Dict[str, tuple[int, int]] = {}
        for ticker in tickers:
            self._progress("metrics_fetch_start", f"Fetching metrics for {ticker}")
            records = self._fetch_metrics_cached(
                ticker,
                period_filters=period_filters,
            )
            if not records:
                missing.append(ticker)
                self._progress("metrics_fetch_missing", f"No metrics available for {ticker}")
                continue
            histories[ticker] = list(records)
            selected = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            metrics_per_ticker[ticker] = selected
            if selected:
                span = max(
                    (
                        self.analytics_engine._period_span(record.period)
                        for record in selected.values()
                    ),
                    key=lambda value: value[1],
                )
                latest_spans[ticker] = span
                fiscal_end = span[1]
                if fiscal_end:
                    overrides: Dict[str, Tuple[database.KpiValueRecord, bool]] = {}
                    try:
                        kpi_rows = database.fetch_kpi_values(
                            self.settings.database_path,
                            ticker,
                            fiscal_year=fiscal_end,
                        )
                    except Exception:
                        kpi_rows = []
                    for kpi_record in kpi_rows:
                        used_override = False
                        existing = selected.get(kpi_record.metric_id)
                        if existing is None or existing.value is None:
                            period_label = (
                                f"FY{kpi_record.fiscal_year}"
                                if kpi_record.fiscal_year
                                else f"FY{fiscal_end}"
                            )
                            selected[kpi_record.metric_id] = database.MetricRecord(
                                ticker=ticker,
                                metric=kpi_record.metric_id,
                                period=period_label,
                                value=kpi_record.value,
                                source=f"kpi:{kpi_record.method}",
                                updated_at=kpi_record.updated_at,
                                start_year=kpi_record.fiscal_year,
                                end_year=kpi_record.fiscal_year,
                            )
                            used_override = True
                        overrides[kpi_record.metric_id] = (kpi_record, used_override)
                    if overrides:
                        kpi_overrides[ticker] = overrides

            self._progress("metrics_fetch_progress", f"Loaded {len(records)} rows for {ticker}")

        if not metrics_per_ticker:
            if missing:
                missing_detail = ", ".join(missing)
                self._progress("metrics_fetch_notice", f"Metrics unavailable for {missing_detail}")
            if period_filters:
                desc = self._describe_period_filters(period_filters)
                return f"No metrics available for {', '.join(tickers)} in {desc}."
            return "No metrics available for the requested tickers."

        if metrics_per_ticker:
            prepared = ", ".join(metrics_per_ticker.keys())
            self._progress("metrics_fetch_complete", f"Prepared metrics for {prepared}")
        if missing and metrics_per_ticker:
            missing_detail = ", ".join(missing)
            self._progress("metrics_fetch_notice", f"Metrics unavailable for {missing_detail}")

        benchmark_label: Optional[str] = None
        compute_benchmark = getattr(self.analytics_engine, "compute_benchmark_metrics", None)
        if callable(compute_benchmark):
            metrics_needed = {definition.name for definition in METRIC_DEFINITIONS}
            metrics_needed.update(BENCHMARK_KEY_METRICS.keys())
            try:
                benchmark_metrics = compute_benchmark(
                    sorted(metrics_needed),
                    period_filters=period_filters,
                )
            except Exception:
                benchmark_metrics = {}
            if benchmark_metrics:
                label_getter = getattr(self.analytics_engine, "benchmark_label", None)
                benchmark_label = (
                    label_getter()
                    if callable(label_getter)
                    else getattr(self.analytics_engine, "BENCHMARK_LABEL", "Benchmark")
                )
                metrics_per_ticker[benchmark_label] = benchmark_metrics

        ordered_tickers = [ticker for ticker in tickers if ticker in metrics_per_ticker]
        display_tickers = list(ordered_tickers)
        if benchmark_label:
            display_tickers.append(benchmark_label)
        headers = ["Metric"] + display_tickers
        rows: List[List[str]] = []
        cell_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {}
        metric_keys: List[str] = []
        # Filter metrics if specific metrics are requested
        definitions_to_use = METRIC_DEFINITIONS
        if metric_filter:
            definitions_to_use = [defn for defn in METRIC_DEFINITIONS if defn.name in metric_filter]
        
        for definition in definitions_to_use:
            label = definition.description
            metric_keys.append(definition.name)
            row = [label]
            for ticker in display_tickers:
                formatted_value = self._format_metric_value(
                    definition.name, metrics_per_ticker[ticker]
                )
                row.append(formatted_value)
                override_entry = kpi_overrides.get(ticker, {}).get(definition.name)
                if override_entry:
                    record, used_override = override_entry
                    if record.value is not None and (used_override or record.method == "external"):
                        meta_bucket = cell_metadata.setdefault(definition.name, {})
                        meta_bucket[ticker] = {
                            "method": record.method,
                            "source": record.source,
                            "source_ref": record.source_ref,
                            "warning": record.warning,
                            "unit": record.unit,
                            "updated_at": record.updated_at.isoformat(),
                            "used_override": used_override,
                        }
            rows.append(row)

        descriptor_filters: List[tuple[int, int]]
        if period_filters:
            descriptor_filters = list(period_filters)
        else:
            descriptor_filters = list(latest_spans.values())
        descriptor = (
            self._describe_period_filters(descriptor_filters)
            if descriptor_filters
            else "latest available"
        )

        highlights = self._compose_benchmark_summary(
            metrics_per_ticker,
            benchmark_label=benchmark_label,
        )

        table_payload = {
            "headers": headers,
            "rows": rows,
            "descriptor": descriptor,
            "tickers": display_tickers,
            "title": f"Benchmark summary for {', '.join(ordered_tickers)}",
            "cell_metadata": cell_metadata,
            "metric_keys": metric_keys,
        }

        trends_payload = self._build_trend_series(histories, ordered_tickers)
        citations_payload = self._build_metric_citations(
            metrics_per_ticker, ordered_tickers
        )
        exports_payload = self._build_export_payloads(
            table_payload, highlights, citations_payload
        )
        conclusion = ""

        dashboard_descriptor = None
        # Build multiple single-company dashboards for multi-ticker requests
        if len(display_tickers) >= 2 and not metric_filter:
            dashboards_list = []
            for ticker in ordered_tickers[:3]:  # Limit to 3 tickers for performance
                try:
                    single_payload = build_cfi_dashboard_payload(
                        self.analytics_engine,
                        ticker,
                    )
                    if single_payload:
                        dashboards_list.append({
                            "ticker": _display_ticker_symbol(ticker),
                            "payload": single_payload,
                        })
                except Exception as e:
                    LOGGER.warning(f"Failed to build dashboard for {ticker}: {e}")
                    continue
            
            if dashboards_list:
                dashboard_descriptor = {
                    "kind": "multi-classic",
                    "dashboards": dashboards_list,
                }

        self.last_structured_response = {
            "highlights": highlights,
            "trends": trends_payload,
            "comparison_table": table_payload,
            "citations": citations_payload,
            "exports": exports_payload,
            "conclusion": conclusion,
            "dashboard": dashboard_descriptor,
        }

        output_lines: List[str] = []
        output_lines.append(self._render_table(headers, rows))
        if conclusion:
            output_lines.append("")
            output_lines.append(conclusion)
        if missing:
            context = (
                self._describe_period_filters(period_filters)
                if period_filters
                else "the requested periods"
            )
            output_lines.append(
                f"No metrics for {', '.join(missing)} in {context}."
            )
        return "\n".join(output_lines)

    def _describe_period_filters(
        self, period_filters: Sequence[tuple[int, int]]
    ) -> str:
        """Render a human-readable summary of applied period filters."""
        labels = []
        for start, end in period_filters:
            if start == 0 and end == 0:
                continue
            if start == end:
                labels.append(f"FY{start}")
            else:
                labels.append(f"FY{start}-FY{end}")
        return ", ".join(labels) if labels else "the requested periods"

    def _build_benchmark_conclusion(
        self,
        highlights: Sequence[str],
        tickers: Sequence[str],
        descriptor: str,
        benchmark_label: Optional[str],
    ) -> str:
        """Derive a short narrative summary and action prompt from highlight bullets."""
        if not highlights:
            return ""

        leadership_counter: Counter[str] = Counter()
        summary_fragments: List[str] = []
        sector_labels: Dict[str, Optional[str]] = {}

        def _format_ticker(ticker: str) -> str:
            label = sector_labels.get(ticker)
            if label is None:
                label = self._sector_label(ticker)
                sector_labels[ticker] = label
            return f"{ticker} ({label})" if label else ticker

        for entry in highlights:
            if ":" not in entry:
                continue
            metric_label, remainder = entry.split(":", 1)
            remainder = remainder.strip()
            best_segment = remainder.split(" vs ")[0]
            tokens = best_segment.split()
            if not tokens:
                continue
            best_ticker = tokens[0]
            leadership_counter[best_ticker] += 1
            value_tokens = " ".join(tokens[1:]).strip().rstrip(",")
            metric_phrase = metric_label.strip().lower()
            sentence = f"{_format_ticker(best_ticker)} leads {metric_phrase}"
            if value_tokens:
                sentence = f"{sentence} at {value_tokens}"
            comparatives = remainder.split(" vs ")[1:]
            if comparatives:
                formatted_comparatives = "; ".join(comparatives)
                sentence = f"{sentence}, ahead of {formatted_comparatives}"
            summary_fragments.append(sentence + ".")

        if not summary_fragments:
            return ""

        total = len(summary_fragments)
        summary_sentence = " ".join(summary_fragments)

        action_sentence = ""
        if leadership_counter:
            max_count = max(leadership_counter.values())
            if max_count > 0:
                leaders = [ticker for ticker, count in leadership_counter.items() if count == max_count]
                if len(leaders) == 1:
                    leader = leaders[0]
                    others = [ticker for ticker in tickers if ticker != leader]
                    action_sentence = (
                        f"{_format_ticker(leader)} leads {max_count} of {total} highlighted KPIs"
                    )
                    if benchmark_label:
                        action_sentence += f" relative to {benchmark_label}"
                    if others:
                        action_sentence += (
                            ". Consider tilting exposure toward the leader while monitoring "
                            + ", ".join(_format_ticker(t) for t in others)
                            + " for catalysts."
                        )
                    else:
                        action_sentence += (
                            ". Consider tilting exposure toward the leader while monitoring macro risks."
                        )
                else:
                    leader_text = ", ".join(_format_ticker(t) for t in leaders)
                    sectors = {sector_labels.get(t) or self._sector_label(t) for t in leaders}
                    sectors.discard(None)
                    sector_clause = ""
                    if len(sectors) == 1:
                        only_sector = sectors.pop()
                        sector_clause = f" (shared exposure to {only_sector})"
                    action_sentence = (
                        f"Leadership is split across {leader_text}{sector_clause}; keep positions balanced and watch the next catalysts closely."
                    )

        return " ".join(filter(None, [summary_sentence, action_sentence]))

    def _select_latest_records(
        self,
        records: Iterable[database.MetricRecord],
        *,
        span_fn,
    ) -> Dict[str, database.MetricRecord]:
        """Choose latest metric snapshots for each metric name."""
        selected: Dict[str, database.MetricRecord] = {}
        for record in records:
            existing = selected.get(record.metric)
            if existing is None:
                selected[record.metric] = record
                continue
            if record.value is not None and existing.value is None:
                selected[record.metric] = record
                continue
            if record.value is None and existing.value is not None:
                continue
            new_span = span_fn(record.period)
            old_span = span_fn(existing.period)
            if new_span[1] > old_span[1] or (
                new_span[1] == old_span[1] and new_span[0] > old_span[0]
            ):
                selected[record.metric] = record
        return selected

    def _build_rag_context(self, user_input: str) -> Optional[str]:
        """Assemble finance facts to ground the LLM response."""
        tickers = self._detect_tickers(user_input)
        if not tickers:
            return None
        normalized_tickers: List[str] = []
        seen_tickers: set[str] = set()
        for ticker in tickers:
            if not ticker:
                continue
            upper = ticker.upper()
            if upper in seen_tickers:
                continue
            seen_tickers.add(upper)
            normalized_tickers.append(upper)
        if normalized_tickers:
            self._progress("context_sources_scan", f"Scanning context for {', '.join(normalized_tickers)}")
        tickers = normalized_tickers or tickers
        cache_key = "|".join(sorted(normalized_tickers)) if normalized_tickers else None
        if cache_key:
            cached = self._get_cached_context(cache_key)
            if cached:
                self._progress("context_cache_hit", "Reusing cached context bundle")
                return cached

        context_sections: List[str] = []
        for ticker in tickers:
            try:
                records = self._fetch_metrics_cached(ticker)
            except Exception:  # pragma: no cover - database path
                continue
            if not records:
                continue

            latest = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            if not latest:
                continue

            spans = [
                self.analytics_engine._period_span(record.period)
                for record in latest.values()
                if record.period
            ]
            descriptor = (
                self._describe_period_filters(spans) if spans else "latest available"
            )

            lines = [f"{ticker} ({descriptor})"]
            for metric_name in CONTEXT_SUMMARY_METRICS:
                formatted = self._format_metric_value(metric_name, latest)
                if formatted == "n/a":
                    continue
                label = _METRIC_LABEL_MAP.get(
                    metric_name, metric_name.replace("_", " ").title()
                )
                lines.append(f"- {label}: {formatted}")

            if len(lines) > 1:
                lines_text = "\n".join(lines)
                context_sections.append(lines_text)

        if not context_sections:
            self._progress("context_sources_empty", "No supplemental context located")
            return None
        combined = "\n".join(context_sections)
        final_context = "Financial context:\n" + combined
        self._progress("context_sources_ready", f"Added {len(context_sections)} context sections")
        if cache_key:
            self._store_cached_context(cache_key, final_context)
        return final_context

    def _build_portfolio_context(self, user_input: str) -> Optional[str]:
        """Build comprehensive portfolio context for portfolio-related queries."""
        import re
        lowered = user_input.lower()
        
        # Check if this is a portfolio query (even without explicit ID)
        portfolio_keywords = [
            "portfolio", "my portfolio", "the portfolio", "this portfolio",
            "portfolio exposure", "portfolio analysis", "portfolio optimize",
            "portfolio holdings", "portfolio risk", "portfolio allocation",
            "portfolio diversification", "portfolio performance"
        ]
        is_portfolio_query = any(kw in lowered for kw in portfolio_keywords)
        
        # Extract portfolio ID from query - try multiple patterns
        portfolio_id_patterns = [
            r"\bport_[\w]{4,12}\b",  # Standard format: port_xxxxx
            r"\bportfolio\s+([a-z0-9_]{4,12})\b",  # "portfolio xxxxx"
            r"\bportfolio\s+id[:\s]+([a-z0-9_]{4,12})\b",  # "portfolio id: xxxxx"
        ]
        
        portfolio_id = None
        for pattern in portfolio_id_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                portfolio_id = match.group(0) if len(match.groups()) == 0 else match.group(1)
                LOGGER.info(f"Found explicit portfolio ID: {portfolio_id}")
                break
        
        if not portfolio_id and is_portfolio_query:
            # If it's a portfolio query but no explicit ID, try to get the most recent portfolio
            try:
                # Try to get list of portfolios from database
                import sqlite3
                with sqlite3.connect(self.settings.database_path) as conn:
                    cursor = conn.execute(
                        "SELECT portfolio_id FROM portfolio_metadata ORDER BY created_at DESC LIMIT 1"
                    )
                    row = cursor.fetchone()
                    if row:
                        portfolio_id = row[0]
                        LOGGER.info(f"Using most recent portfolio: {portfolio_id}")
            except Exception as e:
                LOGGER.warning(f"Could not fetch most recent portfolio: {e}")
        
        if not portfolio_id:
            if is_portfolio_query:
                LOGGER.warning(f"Portfolio query detected but no portfolio ID found: {user_input}")
                # Return helpful error message for user
                return (
                    "PORTFOLIO QUERY DETECTED BUT NO PORTFOLIO FOUND\n\n"
                    "I detected that you're asking about a portfolio, but I couldn't find a portfolio in the database.\n\n"
                    "To analyze your portfolio:\n"
                    "1. Go to the Portfolio Management section\n"
                    "2. Upload your portfolio (CSV, Excel, or JSON format)\n"
                    "3. Once uploaded, you can ask questions like:\n"
                    "   - 'What's my portfolio risk?'\n"
                    "   - 'Analyze my portfolio exposure'\n"
                    "   - 'What are my holdings?'\n\n"
                    "If you have a portfolio ID (e.g., port_xxxxx), include it in your question."
                )
            return None
        
        try:
            from .portfolio import (
                get_portfolio_holdings,
                enrich_holdings_with_fundamentals,
                calculate_portfolio_statistics,
                analyze_exposure,
                calculate_portfolio_volatility,
                calculate_portfolio_sharpe,
                calculate_portfolio_sortino,
                calculate_portfolio_alpha,
                calculate_tracking_error,
                calculate_portfolio_beta,
            )
            from .portfolio_risk_metrics import calculate_cvar
            
            # Fetch holdings
            holdings = get_portfolio_holdings(self.settings.database_path, portfolio_id)
            if not holdings:
                LOGGER.warning(f"No holdings found for portfolio {portfolio_id}")
                return None
            
            LOGGER.info(f"Fetched {len(holdings)} holdings for portfolio {portfolio_id}")
            
            # Enrich with fundamentals
            enriched_holdings = enrich_holdings_with_fundamentals(
                self.settings.database_path, holdings
            )
            
            if not enriched_holdings:
                return None
            
            # Calculate portfolio statistics
            stats = calculate_portfolio_statistics(enriched_holdings)
            
            # Analyze exposure
            exposure = analyze_exposure(enriched_holdings, self.settings.database_path)
            
            # Calculate risk metrics
            risk_metrics = {}
            try:
                cvar_result = calculate_cvar(self.settings.database_path, portfolio_id, confidence_level=0.95)
                if cvar_result:
                    risk_metrics['cvar'] = cvar_result.cvar
                    risk_metrics['var'] = cvar_result.var
                    risk_metrics['expected_loss'] = cvar_result.expected_loss
            except Exception as e:
                LOGGER.warning(f"Could not calculate CVaR: {e}")
            
            try:
                volatility = calculate_portfolio_volatility(self.settings.database_path, portfolio_id)
                if volatility is not None:
                    risk_metrics['volatility'] = volatility
            except Exception as e:
                LOGGER.warning(f"Could not calculate volatility: {e}")
            
            try:
                sharpe = calculate_portfolio_sharpe(self.settings.database_path, portfolio_id)
                if sharpe is not None:
                    risk_metrics['sharpe'] = sharpe
            except Exception as e:
                LOGGER.warning(f"Could not calculate Sharpe ratio: {e}")
            
            try:
                sortino = calculate_portfolio_sortino(self.settings.database_path, portfolio_id)
                if sortino is not None:
                    risk_metrics['sortino'] = sortino
            except Exception as e:
                LOGGER.warning(f"Could not calculate Sortino ratio: {e}")
            
            try:
                beta = calculate_portfolio_beta(self.settings.database_path, portfolio_id)
                if beta is not None:
                    risk_metrics['beta'] = beta
            except Exception as e:
                LOGGER.warning(f"Could not calculate beta: {e}")
            
            try:
                alpha = calculate_portfolio_alpha(self.settings.database_path, portfolio_id)
                if alpha is not None:
                    risk_metrics['alpha'] = alpha
            except Exception as e:
                LOGGER.warning(f"Could not calculate alpha: {e}")
            
            try:
                tracking_error = calculate_tracking_error(self.settings.database_path, portfolio_id)
                if tracking_error is not None:
                    risk_metrics['tracking_error'] = tracking_error
            except Exception as e:
                LOGGER.warning(f"Could not calculate tracking error: {e}")
            
            # Build comprehensive context
            context_parts = []
            context_parts.append("=" * 80)
            context_parts.append("PORTFOLIO ANALYSIS DATA - USE THIS DATA ONLY")
            context_parts.append(f"Portfolio ID: {portfolio_id}")
            context_parts.append("=" * 80)
            context_parts.append("")
            context_parts.append("CRITICAL INSTRUCTIONS:")
            context_parts.append("- You MUST use ONLY the data provided below")
            context_parts.append("- DO NOT make up or hallucinate portfolio data")
            context_parts.append("- USE CALCULATED RISK METRICS: When asked about CVaR, VaR, volatility, Sharpe ratio, Sortino ratio, alpha, beta, or tracking error:")
            context_parts.append("  * Use the ACTUAL calculated values shown in the 'Calculated Risk & Performance Metrics' section below")
            context_parts.append("  * These values have been calculated from historical portfolio returns and are ACCURATE")
            context_parts.append("  * DO NOT say you cannot calculate these metrics - they are already calculated and shown below")
            context_parts.append("  * Reference the specific calculated values (e.g., 'The portfolio CVaR is X%' using the value shown)")
            context_parts.append("  * If a metric is not shown (e.g., 'Risk metrics: Unable to calculate'), explain that insufficient historical data is available")
            context_parts.append("- If data is missing, say so explicitly - but use the calculated values when available")
            context_parts.append("- Reference specific tickers, weights, and metrics from below")
            context_parts.append("- Quote the actual numbers from the data provided")
            context_parts.append("")
            context_parts.append("HOW TO INTERPRET THESE METRICS:")
            context_parts.append("- CVaR (Conditional Value at Risk): Expected loss in worst 5% of scenarios. Higher = more risk.")
            context_parts.append("- VaR (Value at Risk): Maximum expected loss at 95% confidence. Higher = more risk.")
            context_parts.append("- Volatility: Standard deviation of returns. Higher = more price fluctuation.")
            context_parts.append("- Sharpe Ratio: Risk-adjusted return (excess return / volatility). Higher is better (typically >1 is good).")
            context_parts.append("- Sortino Ratio: Downside risk-adjusted return. Higher is better (only penalizes negative volatility).")
            context_parts.append("- Beta: Sensitivity to market movements. 1.0 = market, >1.0 = more volatile, <1.0 = less volatile.")
            context_parts.append("- Alpha: Excess return vs benchmark. Positive = outperformance, negative = underperformance.")
            context_parts.append("- Tracking Error: Volatility of excess returns vs benchmark. Lower = more consistent relative performance.")
            context_parts.append("")
            
            # Portfolio Statistics
            context_parts.append("### Portfolio Statistics")
            if stats:
                if stats.total_market_value:
                    context_parts.append(f"Total Market Value: ${stats.total_market_value:,.2f}")
                if stats.num_holdings:
                    context_parts.append(f"Number of Positions: {stats.num_holdings}")
                if stats.weighted_avg_pe:
                    context_parts.append(f"Weighted Average P/E Ratio: {stats.weighted_avg_pe:.2f}")
                if stats.weighted_avg_dividend_yield:
                    context_parts.append(f"Weighted Average Dividend Yield: {stats.weighted_avg_dividend_yield:.2%}")
                if stats.top_10_weight:
                    context_parts.append(f"Top 10 Holdings Concentration: {stats.top_10_weight:.1%}")
                if stats.num_sectors:
                    context_parts.append(f"Number of Sectors: {stats.num_sectors}")
            context_parts.append("")
            
            # Sector Exposure
            context_parts.append("### Sector Exposure (by weight)")
            if exposure and exposure.sector_exposure:
                for sector, weight in sorted(exposure.sector_exposure.items(), key=lambda x: x[1], reverse=True)[:10]:
                    context_parts.append(f"{sector}: {weight:.1%}")
            elif stats and stats.sector_concentration:
                for sector, weight in sorted(stats.sector_concentration.items(), key=lambda x: x[1], reverse=True)[:10]:
                    context_parts.append(f"{sector}: {weight:.1%}")
            context_parts.append("")
            
            # Factor Exposure
            context_parts.append("### Factor Exposure")
            if exposure and exposure.factor_exposure:
                for factor, value in sorted(exposure.factor_exposure.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
                    context_parts.append(f"{factor}: {value:.3f}")
            context_parts.append("")
            
            # Top Holdings - DETAILED
            context_parts.append("### Top Holdings (by weight)")
            sorted_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)[:20]
            for i, holding in enumerate(sorted_holdings, 1):
                parts = [f"{i}. {holding.ticker}"]
                if holding.weight:
                    parts.append(f"({holding.weight:.1%} weight)")
                if holding.shares:
                    parts.append(f"{holding.shares:.0f} shares")
                if holding.market_value:
                    parts.append(f"${holding.market_value:,.0f}")
                if holding.sector:
                    parts.append(f"[{holding.sector}]")
                if holding.pe_ratio:
                    parts.append(f"P/E: {holding.pe_ratio:.1f}")
                if holding.dividend_yield:
                    parts.append(f"Div: {holding.dividend_yield:.2%}")
                if holding.roe:
                    parts.append(f"ROE: {holding.roe:.1%}")
                if holding.roic:
                    parts.append(f"ROIC: {holding.roic:.1%}")
                context_parts.append(" ".join(parts))
            context_parts.append("")
            
            # Risk/Concentration Metrics
            context_parts.append("### Concentration & Risk Metrics")
            if exposure and exposure.concentration_metrics:
                hhi = exposure.concentration_metrics.get("hhi")
                if hhi:
                    context_parts.append(f"Herfindahl-Hirschman Index (HHI): {hhi:.0f}")
            if stats and stats.top_10_weight:
                context_parts.append(f"Top 10 Holdings Weight: {stats.top_10_weight:.1%}")
            context_parts.append("")
            
            # Calculated Risk & Performance Metrics
            context_parts.append("### Calculated Risk & Performance Metrics")
            context_parts.append("These metrics have been calculated from historical portfolio returns and are ready to use:")
            context_parts.append("")
            if risk_metrics:
                if 'cvar' in risk_metrics:
                    context_parts.append(f"• CVaR (Conditional Value at Risk, 95%): {risk_metrics['cvar']:.4f} ({risk_metrics['cvar']*100:.2f}%)")
                    context_parts.append("  → Expected loss in worst 5% of scenarios")
                if 'var' in risk_metrics:
                    context_parts.append(f"• VaR (Value at Risk, 95%): {risk_metrics['var']:.4f} ({risk_metrics['var']*100:.2f}%)")
                    context_parts.append("  → Maximum expected loss at 95% confidence level")
                if 'expected_loss' in risk_metrics:
                    context_parts.append(f"• Expected Loss (95% confidence): {risk_metrics['expected_loss']:.4f} ({risk_metrics['expected_loss']*100:.2f}%)")
                if 'volatility' in risk_metrics:
                    context_parts.append(f"• Annualized Volatility: {risk_metrics['volatility']:.4f} ({risk_metrics['volatility']*100:.2f}%)")
                    context_parts.append("  → Standard deviation of returns (higher = more price fluctuation)")
                if 'sharpe' in risk_metrics:
                    context_parts.append(f"• Sharpe Ratio (annualized): {risk_metrics['sharpe']:.3f}")
                    context_parts.append("  → Risk-adjusted return (higher is better, typically >1 is good)")
                if 'sortino' in risk_metrics:
                    context_parts.append(f"• Sortino Ratio (annualized): {risk_metrics['sortino']:.3f}")
                    context_parts.append("  → Downside risk-adjusted return (higher is better)")
                if 'beta' in risk_metrics:
                    context_parts.append(f"• Beta (vs benchmark): {risk_metrics['beta']:.3f}")
                    context_parts.append("  → Sensitivity to market (1.0 = market, >1.0 = more volatile, <1.0 = less volatile)")
                if 'alpha' in risk_metrics:
                    context_parts.append(f"• Alpha (vs benchmark, annualized): {risk_metrics['alpha']:.4f} ({risk_metrics['alpha']*100:.2f}%)")
                    context_parts.append("  → Excess return vs benchmark (positive = outperformance)")
                if 'tracking_error' in risk_metrics:
                    context_parts.append(f"• Tracking Error (vs benchmark, annualized): {risk_metrics['tracking_error']:.4f} ({risk_metrics['tracking_error']*100:.2f}%)")
                    context_parts.append("  → Volatility of excess returns (lower = more consistent relative performance)")
            else:
                context_parts.append("Risk metrics: Unable to calculate (insufficient historical data)")
                context_parts.append("  → This means there is not enough historical price data to calculate these metrics")
            context_parts.append("")
            
            context_parts.append("=" * 80)
            context_parts.append("PORTFOLIO DATA SOURCES - MANDATORY TO INCLUDE IN RESPONSE")
            context_parts.append("=" * 80)
            context_parts.append("")
            context_parts.append("📊 **CRITICAL: You MUST include a '📊 Sources:' section at the end of your response with:**")
            context_parts.append("")
            
            # Portfolio metadata source
            context_parts.append("### Portfolio Data Sources")
            context_parts.append(f"- Portfolio ID: {portfolio_id}")
            context_parts.append(f"- Portfolio Holdings: {len(enriched_holdings)} positions")
            context_parts.append(f"- Total Market Value: ${stats.total_market_value:,.2f}" if stats and stats.total_market_value else "- Total Market Value: Calculated from holdings")
            context_parts.append("")
            
            # Top holdings SEC filing sources
            context_parts.append("### SEC Filing Sources for Top Holdings")
            top_holdings = sorted(enriched_holdings, key=lambda h: h.weight or 0, reverse=True)[:10]
            from .context_builder import _get_filing_sources
            
            for holding in top_holdings:
                if not holding.ticker:
                    continue
                filing_sources = _get_filing_sources(holding.ticker, self.settings.database_path)
                if filing_sources:
                    # Get most recent filing
                    recent_filing = filing_sources[0]
                    form_type = recent_filing.get("form_type", "SEC filing")
                    fiscal_year = recent_filing.get("fiscal_year")
                    sec_url = recent_filing.get("sec_url")
                    
                    if sec_url and fiscal_year:
                        context_parts.append(f"- **{holding.ticker}** ({holding.weight:.1%}): [{form_type} FY{fiscal_year}]({sec_url})")
                    elif sec_url:
                        context_parts.append(f"- **{holding.ticker}** ({holding.weight:.1%}): [{form_type}]({sec_url})")
                    else:
                        # Fallback to Yahoo Finance if no SEC URL available
                        context_parts.append(f"- **{holding.ticker}** ({holding.weight:.1%}): [Yahoo Finance - {holding.ticker}](https://finance.yahoo.com/quote/{holding.ticker})")
                else:
                    # Fallback to Yahoo Finance when no filing sources found
                    context_parts.append(f"- **{holding.ticker}** ({holding.weight:.1%}): [Yahoo Finance - {holding.ticker}](https://finance.yahoo.com/quote/{holding.ticker})")
            
            context_parts.append("")
            
            # Yahoo Finance sources for all holdings
            context_parts.append("### Yahoo Finance Sources for Holdings")
            unique_tickers = list(set([h.ticker for h in enriched_holdings if h.ticker]))[:15]
            for ticker in unique_tickers:
                context_parts.append(f"- [{ticker}](https://finance.yahoo.com/quote/{ticker})")
            context_parts.append("")
            
            # Benchmark data sources
            context_parts.append("### Benchmark Data Sources")
            context_parts.append("- **SPY (S&P 500 ETF)**: [Yahoo Finance - SPY](https://finance.yahoo.com/quote/SPY) | [SPDR S&P 500 ETF Trust](https://www.ssga.com/us/en/institutional/etfs/funds/spdr-sp-500-etf-trust-spy)")
            context_parts.append("- **QQQ (Nasdaq 100 ETF)**: [Yahoo Finance - QQQ](https://finance.yahoo.com/quote/QQQ) | [Invesco QQQ Trust](https://www.invesco.com/us/financial-products/etfs/product-detail?productId=QQQ)")
            context_parts.append("- **DIA (Dow Jones ETF)**: [Yahoo Finance - DIA](https://finance.yahoo.com/quote/DIA) | [SPDR Dow Jones Industrial Average ETF](https://www.ssga.com/us/en/institutional/etfs/funds/spdr-dow-jones-industrial-average-etf-trust-dia)")
            context_parts.append("- **IWM (Russell 2000 ETF)**: [Yahoo Finance - IWM](https://finance.yahoo.com/quote/IWM) | [iShares Russell 2000 ETF](https://www.ishares.com/us/products/239710/ishares-russell-2000-etf)")
            context_parts.append("")
            
            # Risk calculation methodology
            context_parts.append("### Risk & Performance Calculation Methodology")
            context_parts.append("- **CVaR & VaR**: Calculated using historical portfolio returns (252 trading days) with 95% confidence level")
            context_parts.append("- **Volatility**: Annualized standard deviation of portfolio returns (√252 × daily std)")
            context_parts.append("- **Sharpe Ratio**: (Portfolio Return - Risk-Free Rate) / Portfolio Volatility (annualized)")
            context_parts.append("- **Sortino Ratio**: (Portfolio Return - Risk-Free Rate) / Downside Deviation (annualized)")
            context_parts.append("- **Beta**: Covariance(Portfolio, Benchmark) / Variance(Benchmark) - calculated vs SPY or alternative benchmark")
            context_parts.append("- **Alpha**: Portfolio Return - (Risk-Free Rate + Beta × (Benchmark Return - Risk-Free Rate)) (annualized)")
            context_parts.append("- **Tracking Error**: Annualized standard deviation of excess returns (Portfolio - Benchmark)")
            context_parts.append("- **Historical Price Data**: Sourced from database and Yahoo Finance API")
            context_parts.append("")
            
            # Portfolio statistics source
            context_parts.append("### Portfolio Statistics Sources")
            context_parts.append("- **Holdings Data**: Portfolio holdings database")
            context_parts.append("- **Fundamental Data**: SEC filings (10-K, 10-Q) and Yahoo Finance")
            context_parts.append("- **Sector Classifications**: GICS sector classifications from holdings data")
            context_parts.append("- **Market Values**: Calculated from current share prices and holdings quantities")
            context_parts.append("")
            
            context_parts.append("=" * 80)
            context_parts.append("END OF PORTFOLIO DATA")
            context_parts.append("=" * 80)
            context_parts.append("")
            context_parts.append("FINAL REMINDER - CRITICAL RULES:")
            context_parts.append("1. You MUST use ONLY the data shown above")
            context_parts.append("2. DO NOT invent or hallucinate any portfolio data")
            context_parts.append("3. Reference the ACTUAL tickers and weights listed above")
            context_parts.append("4. Use the ACTUAL sector exposure percentages provided")
            context_parts.append("5. Calculate recommendations based on THESE SPECIFIC holdings")
            context_parts.append("6. Quote the ACTUAL numbers (weights, values, metrics) from above")
            context_parts.append("7. If data is missing, explicitly state it - do not make up numbers")
            context_parts.append("8. DO NOT provide generic portfolio advice - analyze THIS SPECIFIC portfolio")
            context_parts.append("9. **MANDATORY: Include a '📊 Sources:' section at the end with clickable links from the sources above**")
            context_parts.append("10. **Include at least 5-10 source links**: SEC filings for top holdings, Yahoo Finance links, benchmark sources")
            context_parts.append("")
            context_parts.append("USER QUESTION: " + user_input)
            context_parts.append("")
            context_parts.append("Now answer the user's question using ONLY the portfolio data shown above.")
            context_parts.append("")
            context_parts.append("**REMEMBER: End your response with a '📊 Sources:' section listing all relevant sources from the sections above.**")
            
            context_str = "\n".join(context_parts)
            LOGGER.info(f"Built portfolio context for {portfolio_id}: {len(context_str)} characters, {len(enriched_holdings)} holdings")
            return context_str
        except Exception as e:
            LOGGER.exception(f"Could not build portfolio context: {e}")
            return None
    
    def _build_enhanced_rag_context(self, user_input: str) -> Optional[str]:
        """Enhanced RAG context building with comprehensive financial data."""
        # Skip financial context for portfolio queries (they have their own context)
        portfolio_id_pattern = r"\bport_[\w]{4,12}\b"
        if re.search(portfolio_id_pattern, user_input, re.IGNORECASE):
            return None
        
        # First, try the smart context builder for natural language formatting
        try:
            financial_context = build_financial_context(
                query=user_input,
                analytics_engine=self.analytics_engine,
                database_path=self.settings.database_path,
                max_tickers=3
            )
            if financial_context:
                return financial_context
        except Exception as e:
            LOGGER.debug(f"Smart context builder failed, falling back: {e}")
        
        # Fallback to existing context building
        tickers = self._detect_tickers(user_input)
        if not tickers:
            return None
        
        # Normalize tickers
        normalized_tickers: List[str] = []
        seen_tickers: set[str] = set()
        for ticker in tickers:
            if not ticker:
                continue
            upper = ticker.upper()
            if upper in seen_tickers:
                continue
            seen_tickers.add(upper)
            normalized_tickers.append(upper)
        
        if normalized_tickers:
            self._progress("context_sources_scan", f"Scanning enhanced context for {', '.join(normalized_tickers)}")
        
        tickers = normalized_tickers or tickers
        cache_key = "|".join(sorted(normalized_tickers)) if normalized_tickers else None
        
        if cache_key:
            cached = self._get_cached_context(cache_key)
            if cached:
                self._progress("context_cache_hit", "Reusing cached enhanced context bundle")
                return cached
        
        context_sections: List[str] = []
        
        for ticker in tickers:
            try:
                records = self._fetch_metrics_cached(ticker)
            except Exception:
                continue
            if not records:
                continue
            
            latest = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            if not latest:
                continue
            
            # Build enhanced context with categories
            ticker_context = self._build_ticker_enhanced_context(ticker, latest)
            if ticker_context:
                context_sections.append(ticker_context)
        
        if not context_sections:
            self._progress("context_sources_empty", "No enhanced context located")
            return None
        
        combined = "\n".join(context_sections)
        final_context = "Enhanced Financial Context:\n" + combined
        
        self._progress("context_sources_ready", f"Added {len(context_sections)} enhanced context sections")
        if cache_key:
            self._store_cached_context(cache_key, final_context)
        
        return final_context

    def _build_ticker_enhanced_context(self, ticker: str, latest: Dict[str, database.MetricRecord]) -> str:
        """Build enhanced context for a single ticker with categorized metrics."""
        
        spans = [
            self.analytics_engine._period_span(record.period)
            for record in latest.values()
            if record.period
        ]
        descriptor = (
            self._describe_period_filters(spans) if spans else "latest available"
        )
        
        lines = [f"{ticker} ({descriptor})"]
        
        # Build context by category
        for category, metrics in CONTEXT_CATEGORIES.items():
            category_lines = []
            for metric_name in metrics:
                formatted = self._format_metric_value(metric_name, latest)
                if formatted == "n/a":
                    continue
                label = _METRIC_LABEL_MAP.get(
                    metric_name, metric_name.replace("_", " ").title()
                )
                category_lines.append(f"  • {label}: {formatted}")
            
            if category_lines:
                lines.append(f"  {category}:")
                lines.extend(category_lines)
        
        return "\n".join(lines) if len(lines) > 1 else ""

    def _handle_enhanced_error(self, error_category: ErrorCategory, **kwargs) -> str:
        """Handle errors with specific messages and suggestions."""
        error_info = ERROR_MESSAGES.get(error_category, ERROR_MESSAGES[ErrorCategory.UNKNOWN_ERROR])
        
        message = error_info["message"].format(**kwargs)
        suggestions = error_info["suggestions"]
        
        response = f"{message}\n\n"
        if suggestions:
            response += "Here are some suggestions:\n"
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
        
        return response

    def _detect_ticker_error(self, ticker: str) -> Optional[ErrorCategory]:
        """Detect if ticker is not found."""
        try:
            # Try to fetch metrics for the ticker
            records = self._fetch_metrics_cached(ticker)
            if not records:
                return ErrorCategory.TICKER_NOT_FOUND
        except Exception:
            return ErrorCategory.TICKER_NOT_FOUND
        return None

    def _detect_metric_error(self, metric: str, ticker: str) -> Optional[ErrorCategory]:
        """Detect if metric is not available."""
        try:
            records = self._fetch_metrics_cached(ticker)
            if not records:
                return ErrorCategory.METRIC_NOT_AVAILABLE
            
            # Check if metric exists in records
            latest = self._select_latest_records(
                records, span_fn=self.analytics_engine._period_span
            )
            if metric not in latest:
                return ErrorCategory.METRIC_NOT_AVAILABLE
        except Exception:
            return ErrorCategory.METRIC_NOT_AVAILABLE
        return None

    def _detect_period_error(self, period: str) -> Optional[ErrorCategory]:
        """Detect if period is invalid."""
        # Basic period validation
        if not period or period.strip() == "":
            return ErrorCategory.INVALID_PERIOD
        
        # Check for valid year format
        if re.match(r'^\d{4}$', period.strip()):
            year = int(period.strip())
            if year < 1900 or year > 2030:
                return ErrorCategory.INVALID_PERIOD
            return None
        
        # Check for valid quarter format
        if re.match(r'^Q[1-4]\s+\d{4}$', period.strip(), re.IGNORECASE):
            return None
        
        # Check for relative periods
        if any(keyword in period.lower() for keyword in ['last', 'previous', 'recent']):
            return None
        
        # If none of the above patterns match, it's likely invalid
        return ErrorCategory.INVALID_PERIOD

    # Enhanced Visual Formatting Methods
    def _generate_line_chart(self, data: Dict[str, List[float]], title: str, 
                            x_labels: List[str] = None) -> str:
        """Generate line chart for time series data."""
        if not data or not any(data.values()):
            return ""
        
        # Create ASCII line chart
        chart_lines = [f"📈 {title}", "=" * 50]
        
        # Find max value for scaling
        max_value = max(max(values) for values in data.values() if values)
        min_value = min(min(values) for values in data.values() if values)
        range_value = max_value - min_value if max_value != min_value else 1
        
        # Create chart for each series
        for series_name, values in data.items():
            if not values:
                continue
                
            chart_lines.append(f"\n{series_name}:")
            chart_lines.append("┌" + "─" * 48 + "┐")
            
            # Create ASCII line chart
            for i, value in enumerate(values):
                if value is None:
                    continue
                    
                # Scale value to 0-40 range
                scaled_value = int((value - min_value) / range_value * 40) if range_value > 0 else 20
                bar = "█" * scaled_value + " " * (40 - scaled_value)
                
                label = x_labels[i] if x_labels and i < len(x_labels) else f"Point {i+1}"
                chart_lines.append(f"│ {bar} │ {label}: {value:,.1f}")
            
            chart_lines.append("└" + "─" * 48 + "┘")
        
        return "\n".join(chart_lines)

    def _generate_bar_chart(self, data: Dict[str, float], title: str) -> str:
        """Generate bar chart for comparison data."""
        if not data:
            return ""
        
        chart_lines = [f"📊 {title}", "=" * 50]
        
        # Find max value for scaling
        max_value = max(data.values()) if data.values() else 1
        min_value = min(data.values()) if data.values() else 0
        range_value = max_value - min_value if max_value != min_value else 1
        
        # Create bar chart
        for label, value in data.items():
            if value is None:
                continue
                
            # Scale value to 0-40 range
            scaled_value = int((value - min_value) / range_value * 40) if range_value > 0 else 20
            bar = "█" * scaled_value + " " * (40 - scaled_value)
            
            chart_lines.append(f"{label:20} │{bar}│ {value:,.1f}")
        
        return "\n".join(chart_lines)

    def _generate_pie_chart(self, data: Dict[str, float], title: str) -> str:
        """Generate pie chart for distribution data."""
        if not data:
            return ""
        
        chart_lines = [f"🥧 {title}", "=" * 50]
        
        # Calculate percentages
        total = sum(data.values()) if data.values() else 1
        percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in data.items()}
        
        # Create pie chart representation
        for label, value in data.items():
            percentage = percentages[label]
            bar_length = int(percentage / 2)  # Scale to 0-50 range
            bar = "█" * bar_length + " " * (50 - bar_length)
            
            chart_lines.append(f"{label:20} │{bar}│ {percentage:.1f}% ({value:,.1f})")
        
        return "\n".join(chart_lines)

    def _format_enhanced_table(self, headers: List[str], rows: List[List[str]], 
                              title: str = None, chart_type: str = None) -> str:
        """Format table with enhanced visual styling."""
        if not headers or not rows:
            return ""
        
        # Add title if provided
        result_lines = []
        if title:
            result_lines.append(f"📋 {title}")
            result_lines.append("=" * len(title) + "=" * 4)
        
        # Calculate column widths
        col_widths = [len(str(header)) for header in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Create table header
        header_line = "┌" + "┬".join("─" * (width + 2) for width in col_widths) + "┐"
        result_lines.append(header_line)
        
        # Add header row
        header_cells = [f" {str(header):<{col_widths[i]}} " for i, header in enumerate(headers)]
        result_lines.append("│" + "│".join(header_cells) + "│")
        
        # Add separator
        separator = "├" + "┼".join("─" * (width + 2) for width in col_widths) + "┤"
        result_lines.append(separator)
        
        # Add data rows
        for row in rows:
            row_cells = []
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    row_cells.append(f" {str(cell):<{col_widths[i]}} ")
                else:
                    row_cells.append(" " * (col_widths[i] + 2))
            
            result_lines.append("│" + "│".join(row_cells) + "│")
        
        # Add footer
        footer_line = "└" + "┴".join("─" * (width + 2) for width in col_widths) + "┘"
        result_lines.append(footer_line)
        
        # Add chart if requested
        if chart_type and len(rows) > 0:
            result_lines.append("\n")
            if chart_type == "line" and len(rows) > 1:
                # Generate line chart for time series data
                chart_data = {}
                for i, row in enumerate(rows):
                    if len(row) > 1:
                        series_name = row[0]
                        values = []
                        for j in range(1, len(row)):
                            try:
                                value = float(row[j].replace(',', '').replace('%', ''))
                                values.append(value)
                            except (ValueError, IndexError):
                                continue
                        if values:
                            chart_data[series_name] = values
                if chart_data:
                    result_lines.append(self._generate_line_chart(chart_data, f"{title} - Trend Analysis"))
            
            elif chart_type == "bar":
                # Generate bar chart for comparison data
                chart_data = {}
                for row in rows:
                    if len(row) >= 2:
                        try:
                            value = float(row[1].replace(',', '').replace('%', ''))
                            chart_data[row[0]] = value
                        except (ValueError, IndexError):
                            continue
                if chart_data:
                    result_lines.append(self._generate_bar_chart(chart_data, f"{title} - Comparison"))
        
        return "\n".join(result_lines)

    def _export_to_csv(self, data: Dict[str, Any], filename: str) -> str:
        """Export data to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        if 'headers' in data:
            writer.writerow(data['headers'])
        
        # Write rows
        if 'rows' in data:
            for row in data['rows']:
                writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        # Save to file
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
        
        return f"📁 Data exported to {filename}"

    def _export_to_pdf(self, data: Dict[str, Any], filename: str) -> str:
        """Export data to PDF format."""
        try:
            try:
                from reportlab.lib.pagesizes import letter  # type: ignore
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # type: ignore
                from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
                from reportlab.lib import colors  # type: ignore
            except ImportError:
                raise ImportError("reportlab is required for PDF export. Install it with: pip install reportlab")
            
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            if 'title' in data:
                title = Paragraph(data['title'], styles['Title'])
                story.append(title)
                story.append(Spacer(1, 12))
            
            # Add table
            if 'headers' in data and 'rows' in data:
                table_data = [data['headers']] + data['rows']
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            
            doc.build(story)
            return f"📄 PDF exported to {filename}"
            
        except ImportError:
            return "❌ PDF export requires reportlab package. Install with: pip install reportlab"
        except Exception as e:
            return f"❌ PDF export failed: {str(e)}"

    def _add_visual_indicators(self, text: str) -> str:
        """Add visual indicators to text responses."""
        # Add emojis and visual indicators
        enhanced_text = text
        
        # Add indicators for different types of content
        if "revenue" in text.lower():
            enhanced_text = enhanced_text.replace("revenue", "💰 Revenue")
        if "profit" in text.lower():
            enhanced_text = enhanced_text.replace("profit", "📈 Profit")
        if "growth" in text.lower():
            enhanced_text = enhanced_text.replace("growth", "📊 Growth")
        if "ratio" in text.lower():
            enhanced_text = enhanced_text.replace("ratio", "📏 Ratio")
        
        return enhanced_text

    def _format_financial_metrics(self, metrics: Dict[str, float]) -> str:
        """Format financial metrics with visual enhancements."""
        if not metrics:
            return ""
        
        result_lines = ["📊 Financial Metrics Summary", "=" * 40]
        
        for metric, value in metrics.items():
            if value is None:
                continue
                
            # Add visual indicators based on metric type
            if "revenue" in metric.lower():
                indicator = "💰"
            elif "profit" in metric.lower() or "income" in metric.lower():
                indicator = "📈"
            elif "ratio" in metric.lower():
                indicator = "📏"
            elif "growth" in metric.lower():
                indicator = "📊"
            else:
                indicator = "📋"
            
            # Format value with appropriate precision
            if isinstance(value, float):
                if abs(value) >= 1e9:
                    formatted_value = f"{value/1e9:.2f}B"
                elif abs(value) >= 1e6:
                    formatted_value = f"{value/1e6:.2f}M"
                elif abs(value) >= 1e3:
                    formatted_value = f"{value/1e3:.2f}K"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            
            result_lines.append(f"{indicator} {metric.replace('_', ' ').title()}: {formatted_value}")
        
        return "\n".join(result_lines)

    def _detect_tickers(self, text: str) -> List[str]:
        """Best-effort ticker extraction from user text (tickers + company names)."""
        candidates: List[str] = []
        seen = set()

        for token in _TICKER_TOKEN_PATTERN.findall(text.upper()):
            normalized = token.upper()
            if normalized in _COMMON_WORDS:
                continue
            if normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

        # Also resolve company phrases to tickers
        for match in _COMPANY_PHRASE_PATTERN.findall(text):
            phrase = match.strip()
            if not phrase:
                continue
            phrase = re.sub(r"(?:'s|'s)$", "", phrase, flags=re.IGNORECASE).strip()
            if phrase.upper() in _COMMON_WORDS:
                continue
            # Debug: log phrase resolution attempts
            print(f"[DEBUG] Trying to resolve phrase: '{phrase}'")
            ticker = self._name_to_ticker(phrase)
            print(f"[DEBUG] Resolved '{phrase}' -> {ticker}")
            if ticker and ticker not in seen:
                seen.add(ticker)
                candidates.append(ticker)

        # Additional pass: try individual words in case multi-word phrases didn't resolve
        # This helps when users say "dashboard apple microsoft" - try each word separately
        command_words = {"dashboard", "show", "display", "compare", "view", "get", "give", "full", "comprehensive", "detailed"}
        words = text.split()
        for word in words:
            word = word.strip()
            if len(word) < 2:
                continue
            if word.lower() in command_words:
                continue
            if word.upper() in _COMMON_WORDS:
                continue
            if word.upper() in seen:
                continue
            # Try to resolve this individual word as a company name or ticker
            print(f"[DEBUG] Trying individual word: '{word}'")
            ticker = self._name_to_ticker(word)
            print(f"[DEBUG] Resolved individual word '{word}' -> {ticker}")
            if ticker and ticker not in seen:
                seen.add(ticker)
                candidates.append(ticker)

        return candidates

    def _compose_benchmark_summary(
        self,
        metrics_per_ticker: Dict[str, Dict[str, database.MetricRecord]],
        *,
        benchmark_label: Optional[str] = None,
    ) -> List[str]:
        """Summarise how tickers stack up against an optional benchmark column."""
        if not metrics_per_ticker:
            return []

        contenders = {
            ticker: records
            for ticker, records in metrics_per_ticker.items()
            if ticker != benchmark_label
        }
        if not contenders:
            return []

        benchmark_metrics = (
            metrics_per_ticker.get(benchmark_label) if benchmark_label else None
        )

        highlights: List[str] = []
        for metric, label in BENCHMARK_KEY_METRICS.items():
            best_ticker: Optional[str] = None
            best_value: Optional[float] = None
            best_display: Optional[str] = None
            for ticker, records in contenders.items():
                record = records.get(metric)
                if not record or record.value is None:
                    continue
                if best_value is None or record.value > best_value:
                    best_value = record.value
                    best_ticker = ticker
                    best_display = self._format_metric_value(metric, records)
            if best_ticker is None or best_value is None or best_display is None:
                continue

            line = f"{label}: {best_ticker} {best_display}"

            benchmark_display: Optional[str] = None
            benchmark_value: Optional[float] = None
            if benchmark_metrics:
                benchmark_record = benchmark_metrics.get(metric)
                if benchmark_record and benchmark_record.value is not None:
                    benchmark_value = benchmark_record.value
                    benchmark_display = self._format_metric_value(metric, benchmark_metrics)

            if benchmark_display:
                benchmark_name = benchmark_label or "Benchmark"
                line += f" vs {benchmark_name} {benchmark_display}"
                delta_note = self._format_benchmark_delta(metric, best_value, benchmark_value)
                if delta_note is not None and benchmark_value is not None:
                    direction = "above" if (best_value - benchmark_value) >= 0 else "below"
                    line += f" ({delta_note} {direction})"

            highlights.append(line)
        return highlights

    def _format_benchmark_delta(
        self,
        metric_name: str,
        best_value: Optional[float],
        benchmark_value: Optional[float],
    ) -> Optional[str]:
        """Express the difference between the leader and benchmark in human terms."""
        if best_value is None or benchmark_value is None:
            return None
        delta = best_value - benchmark_value
        if abs(delta) < 1e-9:
            return None
        if metric_name in PERCENT_METRICS:
            return f"{delta * 100:+.1f} pts"
        if metric_name in MULTIPLE_METRICS:
            return f"{delta:+.2f}x"
        return f"{delta:+,.0f}"

    @staticmethod
    def _format_metric_value(
        metric_name: str, metrics: Dict[str, database.MetricRecord]
    ) -> str:
        """Format metric values with appropriate precision and units."""
        record = metrics.get(metric_name)
        if not record or record.value is None:
            return "n/a"
        value = record.value
        if metric_name in PERCENT_METRICS:
            return f"{value:.1%}"
        if metric_name in MULTIPLE_METRICS:
            return f"{value:.2f}"
        return f"{value:,.0f}"

    @staticmethod
    def _format_fact_value(value: float) -> str:
        """Format fact values for display, preserving units where possible."""
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"{value/1_000_000:,.2f}M"
        if absolute >= 1_000:
            return f"{value:,.0f}"
        if absolute >= 10:
            return f"{value:,.2f}"
        return f"{value:.4f}"

    @staticmethod
    def _render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
        """Render rows and headers into a markdown-style table."""
        if not rows:
            return "No data available."

        alignments = ["left"] + ["right"] * (len(headers) - 1)
        widths = [len(header) for header in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))

        def format_row(values: Sequence[str]) -> str:
            """Format a single row tuple for display in tables."""
            formatted = []
            for idx, value in enumerate(values):
                if alignments[idx] == "left":
                    formatted.append(value.ljust(widths[idx]))
                else:
                    formatted.append(value.rjust(widths[idx]))
            return " | ".join(formatted)

        header_line = format_row(headers)
        separator = "-+-".join("-" * width for width in widths)
        body = "\n".join(format_row(row) for row in rows)
        return "\n".join([header_line, separator, body])

    # Enhanced Error Handling Methods
    def _detect_error_category(self, error_message: str) -> ErrorCategory:
        """Detect error category based on error message content."""
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ["not found", "missing", "unavailable"]):
            return ErrorCategory.DATA_NOT_FOUND
        elif any(keyword in error_lower for keyword in ["invalid", "incorrect", "wrong"]):
            return ErrorCategory.INVALID_INPUT
        elif any(keyword in error_lower for keyword in ["timeout", "connection", "network"]):
            return ErrorCategory.NETWORK_ERROR
        elif any(keyword in error_lower for keyword in ["permission", "access", "unauthorized"]):
            return ErrorCategory.PERMISSION_ERROR
        elif any(keyword in error_lower for keyword in ["limit", "quota", "exceeded"]):
            return ErrorCategory.QUOTA_EXCEEDED
        elif any(keyword in error_lower for keyword in ["server", "internal", "system"]):
            return ErrorCategory.SERVER_ERROR
        else:
            return ErrorCategory.UNKNOWN_ERROR

    def _format_error_message(self, error: Exception, context: str = "") -> str:
        """Format error message with specific guidance based on error category."""
        error_message = str(error)
        category = self._detect_error_category(error_message)
        
        base_message = ERROR_MESSAGES.get(category, ERROR_MESSAGES[ErrorCategory.UNKNOWN_ERROR])
        
        # Add context-specific suggestions
        suggestions = []
        if context:
            suggestions.append(f"Context: {context}")
        
        if category == ErrorCategory.DATA_NOT_FOUND:
            suggestions.extend([
                "• Try using a different company name or ticker symbol",
                "• Check if the company is publicly traded",
                "• Verify the time period is available"
            ])
        elif category == ErrorCategory.INVALID_INPUT:
            suggestions.extend([
                "• Check your query format",
                "• Ensure ticker symbols are valid",
                "• Verify time period format (e.g., 2023, Q1 2023)"
            ])
        elif category == ErrorCategory.NETWORK_ERROR:
            suggestions.extend([
                "• Check your internet connection",
                "• Try again in a few moments",
                "• Contact support if the issue persists"
            ])
        
        if suggestions:
            base_message += "\n\nSuggestions:\n" + "\n".join(suggestions)
        
        return base_message

    # Enhanced Chart Generation Methods
    def _generate_chart(self, data: Dict[str, List[float]], title: str, chart_type: str = "line") -> str:
        """Generate various types of charts based on data."""
        if chart_type == "line":
            return self._generate_line_chart(data, title)
        elif chart_type == "bar":
            return self._generate_bar_chart(data, title)
        elif chart_type == "pie":
            return self._generate_pie_chart(data, title)
        else:
            return f"❌ Unsupported chart type: {chart_type}"

