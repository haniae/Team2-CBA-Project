"""
Enhanced deterministic router that wraps existing parsing with strict pattern rules.
This is a NON-INVASIVE layer that can be enabled via config without changing existing behavior.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional, List, Sequence
from dataclasses import dataclass
from enum import Enum


class EnhancedIntent(Enum):
    """Enhanced intent classification for deterministic routing."""
    METRICS_SINGLE = "metrics_single"
    METRICS_MULTI = "metrics_multi"
    COMPARE_TWO = "compare_two"
    COMPARE_MULTI = "compare_multi"
    FACT_SINGLE = "fact_single"
    FACT_RANGE = "fact_range"
    SCENARIO = "scenario"
    INGEST = "ingest"
    AUDIT = "audit"
    DASHBOARD_EXPLICIT = "dashboard_explicit"
    LEGACY_COMMAND = "legacy_command"  # Pass through to existing handlers
    NATURAL_LANGUAGE = "natural_language"  # Pass through to LLM
    # Portfolio intents
    PORTFOLIO_UPLOAD = "portfolio_upload"
    PORTFOLIO_LIST = "portfolio_list"
    PORTFOLIO_HOLDINGS = "portfolio_holdings"
    PORTFOLIO_EXPOSURE = "portfolio_exposure"
    PORTFOLIO_OPTIMIZE = "portfolio_optimize"
    PORTFOLIO_ATTRIBUTION = "portfolio_attribution"
    PORTFOLIO_SCENARIO = "portfolio_scenario"
    PORTFOLIO_EXPORT = "portfolio_export"
    PORTFOLIO_CVAR = "portfolio_cvar"
    PORTFOLIO_VOLATILITY = "portfolio_volatility"
    PORTFOLIO_ESG = "portfolio_esg"
    PORTFOLIO_TAX = "portfolio_tax"
    PORTFOLIO_TRACKING_ERROR = "portfolio_tracking_error"
    PORTFOLIO_DIVERSIFICATION = "portfolio_diversification"
    PORTFOLIO_SENTIMENT = "portfolio_sentiment"
    PORTFOLIO_POLICY = "portfolio_policy"
    PORTFOLIO_COMPLIANCE = "portfolio_compliance"
    PORTFOLIO_MULTI_PERIOD = "portfolio_multi_period"
    PORTFOLIO_RISK_PARITY = "portfolio_risk_parity"
    PORTFOLIO_FACTOR_ATTRIBUTION = "portfolio_factor_attribution"
    PORTFOLIO_BACKTEST = "portfolio_backtest"
    PORTFOLIO_TRADES = "portfolio_trades"
    PORTFOLIO_CUSTOM_REPORT = "portfolio_custom_report"
    PORTFOLIO_DASHBOARD_LAYOUT = "portfolio_dashboard_layout"
    PORTFOLIO_PREFERENCES = "portfolio_preferences"
    PORTFOLIO_BROKERAGE = "portfolio_brokerage"
    PORTFOLIO_ALERTS = "portfolio_alerts"
    PORTFOLIO_SCHEDULE = "portfolio_schedule"
    PORTFOLIO_ENRICHMENT = "portfolio_enrichment"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    # KPI intents
    CREATE_KPI = "create_kpi"
    COMPUTE_KPI = "compute_kpi"
    MANAGE_KPI = "manage_kpi"
    TEMPLATE_SAVE = "template_save"
    TEMPLATE_RUN = "template_run"
    SOURCE_LOOKUP = "source_lookup"
    HELP = "help"
    # ML Forecasting intents
    ML_FORECAST_ARIMA = "ml_forecast_arima"
    ML_FORECAST_PROPHET = "ml_forecast_prophet"
    ML_FORECAST_ETS = "ml_forecast_ets"
    ML_FORECAST_LSTM = "ml_forecast_lstm"
    ML_FORECAST_GRU = "ml_forecast_gru"
    ML_FORECAST_TRANSFORMER = "ml_forecast_transformer"
    ML_FORECAST_ENSEMBLE = "ml_forecast_ensemble"
    ML_FORECAST_AUTO = "ml_forecast_auto"


@dataclass
class EnhancedRouting:
    """Enhanced routing metadata to guide chatbot processing."""
    intent: EnhancedIntent
    force_dashboard: bool = False  # Override dashboard decision
    force_text_only: bool = False  # Never build dashboard
    legacy_command: Optional[str] = None  # If legacy, pass this through
    confidence: float = 1.0  # Confidence in routing decision
    # Optional hints/slots to help downstream handlers (backwards compatible)
    slots: Optional[Dict[str, Any]] = None
    missing_slots: Optional[List[str]] = None
    disambiguation_questions: Optional[List[str]] = None
    

def enhance_structured_parse(
    text: str, 
    existing_structured: Optional[Dict[str, Any]]
) -> EnhancedRouting:
    """
    Enhance existing parse_to_structured output with deterministic pattern matching.
    
    This DOES NOT replace existing parsing - it adds a confidence layer on top.
    
    Args:
        text: Original user input
        existing_structured: Output from parse_to_structured() (may be None)
        
    Returns:
        EnhancedRouting with intent classification and dashboard hints
    """
    # Handle None case
    if existing_structured is None:
        existing_structured = {}
    
    clean_text = text.strip()
    lowered = clean_text.lower()

    def with_conf(c: float) -> float:
        """Clamp and discretize confidence values for stability."""
        return max(0.0, min(1.0, round(c, 2)))
    
    def extract_period_from_structured(periods_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(periods_data, dict):
            return None
        items = periods_data.get("items") or []
        if not items:
            return None
        first = items[0]
        if not isinstance(first, dict):
            return None
        year = first.get("fy")
        quarter = first.get("fq")
        period_type = periods_data.get("type")
        result: Dict[str, Any] = {
            "basis": "QUARTER" if quarter not in (None, "", -1) else "FY",
            "year": year,
            "quarter": quarter if quarter not in (None, "", -1) else None,
            "ttm": False,
        }
        if period_type in {"ytd", "qtd"}:
            result["basis"] = period_type.upper()
        if period_type in {"latest", "future"}:
            result["tag"] = period_type
        if periods_data.get("normalize_to_fiscal") is False and result["basis"] == "FY":
            result["basis"] = "YEAR"
        return result
    
    def extract_tickers_from_structured(structured: Optional[Dict[str, Any]]) -> List[str]:
        if not structured:
            return []
        raw = structured.get("tickers") or []
        tickers: List[str] = []
        if isinstance(raw, Sequence):
            for item in raw:
                if isinstance(item, dict):
                    ticker = item.get("ticker")
                    if ticker:
                        tickers.append(str(ticker).upper())
                elif isinstance(item, str):
                    tickers.append(item.upper())
        return tickers
    
    def extract_metric_candidate(structured: Optional[Dict[str, Any]]) -> Optional[str]:
        if not structured:
            return None
        metrics = structured.get("vmetrics") or []
        if not metrics:
            return None
        first = metrics[0]
        if isinstance(first, dict):
            value = first.get("key") or first.get("input")
            if value:
                return str(value).strip()
        elif isinstance(first, str):
            return first.strip()
        return None
    
    def build_source_lookup_routing(kpi_name: str, extra_slots: Optional[Dict[str, Any]] = None, *, missing_slots: Optional[List[str]] = None) -> EnhancedRouting:
        slots = {
            "kpi_name": kpi_name,
            "lookup_scope": ["internal_dictionary", "financial_glossary", "web"],
        }
        if extra_slots:
            slots.update(extra_slots)
        return EnhancedRouting(
            intent=EnhancedIntent.SOURCE_LOOKUP,
            confidence=with_conf(0.78),
            force_text_only=True,
            slots=slots,
            missing_slots=missing_slots or [],
            disambiguation_questions=[],
        )
    
    structured_intent = existing_structured.get("intent")
    if structured_intent in {"create_kpi", "compute_kpi"}:
        slots = existing_structured.get("slots") or {}
        if not isinstance(slots, dict):
            slots = {}
        formula_text = slots.get("formula_text") or existing_structured.get("formula_text")
        kpi_name = slots.get("kpi_name") or existing_structured.get("kpi_name")
        if not kpi_name:
            metrics = existing_structured.get("vmetrics") or []
            if isinstance(metrics, list) and metrics:
                first = metrics[0]
                if isinstance(first, dict):
                    kpi_name = first.get("input") or first.get("key")
        if (formula_text is None or str(formula_text).strip() == "") and kpi_name:
            return build_source_lookup_routing(str(kpi_name).strip(), slots)
    
    # ========================================
    # 0. PORTFOLIO INTENTS (Highest Priority)
    # ========================================
    # Detect portfolio IDs (typically start with "port_")
    portfolio_id_pattern = r"\bport_[\w]+"
    
    # Portfolio-specific patterns (with ID detection)
    # Priority: Catch portfolio queries BEFORE ticker resolution to prevent false positives
    portfolio_patterns = [
        # Generic portfolio queries (highest priority to prevent false positives)
        (r"\b(?:what'?s?|what\s+is)\s+(?:my\s+)?portfolio\s+(?:risk|cvar|volatility|diversification|exposure|performance|allocation|attribution|beta|alpha|sharpe|sortino)", EnhancedIntent.PORTFOLIO_SUMMARY),
        (r"\b(?:show|analyze|calculate|get)\s+(?:my\s+)?portfolio\s+(?:risk|cvar|volatility|diversification|exposure|performance|allocation|attribution|beta|alpha|sharpe|sortino)", EnhancedIntent.PORTFOLIO_SUMMARY),
        (r"\b(?:what'?s?|what\s+is)\s+(?:my\s+)?portfolio\s+(?:sector|factor|geographic|style)\s+exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
        (r"\b(?:show|analyze|get)\s+(?:my\s+)?portfolio\s+(?:sector|factor|geographic|style)\s+exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
        (r"\b(?:use|switch|set|select)\s+portfolio\s+port_[\w]+", EnhancedIntent.PORTFOLIO_HOLDINGS),  # "use portfolio port_xxx"
        (r"\b(?:use|switch|set|select)\s+portfolio", EnhancedIntent.PORTFOLIO_HOLDINGS),  # "use portfolio" (will extract ID)
        (r"\b(?:upload|load|import)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_UPLOAD),
        (r"\b(?:list|show\s+all)\s+portfolios", EnhancedIntent.PORTFOLIO_LIST),
        # Holdings patterns - check for "holdings" + optional portfolio ID
        (r"\b(?:holdings|positions)\s+(?:for|of)\s+port_[\w]+", EnhancedIntent.PORTFOLIO_HOLDINGS),
        (r"\b(?:show|get|display|view)\s+(?:my\s+)?(?:portfolio\s+)?holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
        (r"\b(?:what\s+(?:are|is))?\s*(?:the\s+)?holdings\s+(?:for|of)\s+port_[\w]+", EnhancedIntent.PORTFOLIO_HOLDINGS),
        # Exposure patterns
        (r"\b(?:what'?s?|what\s+is)\s+(?:my\s+)?(?:portfolio\s+)?(?:sector|factor|exposure)", EnhancedIntent.PORTFOLIO_EXPOSURE),
        (r"\b(?:analyze|show|get)\s+(?:exposure|sector|factor)\s+(?:for|of)\s+port_[\w]+", EnhancedIntent.PORTFOLIO_EXPOSURE),
        (r"\b(?:optimize|rebalance|rebalance)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_OPTIMIZE),
        (r"\b(?:attribute|attribution|performance\s+attribution)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
        (r"\b(?:what\s+if|scenario|stress\s+test)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:what\s+happens|simulate)\s+(?:if|when)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:run|execute)\s+(?:stress\s+test|scenario)", EnhancedIntent.PORTFOLIO_SCENARIO),
        # Market crash scenarios (without explicit "portfolio")
        (r"\b(?:what\s+if|what\s+happens)\s+(?:the\s+)?market\s+(?:crashes|drops|falls|declines)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:what\s+if|what\s+happens)\s+(?:tech|technology|sector)\s+(?:sector\s+)?(?:drops|falls|declines|rotates)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:what\s+if|what\s+happens)\s+(?:if\s+)?(?:AAPL|MSFT|GOOGL|TSLA|META|NVDA|AMZN|NFLX|\w+)\s+(?:drops|falls|declines|increases|rises)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:stress\s+test|run\s+scenario)\s+(?:with|on)\s+(?:\d+%|percent)", EnhancedIntent.PORTFOLIO_SCENARIO),
        # Monte Carlo simulation patterns
        (r"\b(?:monte\s+carlo|monte\s+carlo\s+simulation|run\s+monte\s+carlo)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:simulate|simulation)\s+(?:portfolio|returns|performance)", EnhancedIntent.PORTFOLIO_SCENARIO),
        # Export patterns
        (r"\b(?:export|generate|download|create)\s+(?:portfolio\s+)?port_[\w]+\s+(?:as\s+)?(?:powerpoint|ppt|pptx)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:export|generate|download|create)\s+(?:portfolio\s+)?port_[\w]+\s+(?:as\s+)?(?:pdf|pdf\s+report)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:export|generate|download|create)\s+(?:portfolio\s+)?port_[\w]+\s+(?:as\s+)?(?:excel|xlsx|spreadsheet)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:export|generate|download|create)\s+(?:my\s+)?(?:portfolio\s+)?(?:as\s+)?(?:powerpoint|ppt|pptx)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:export|generate|download|create)\s+(?:my\s+)?(?:portfolio\s+)?(?:as\s+)?(?:pdf|pdf\s+report)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:export|generate|download|create)\s+(?:my\s+)?(?:portfolio\s+)?(?:as\s+)?(?:excel|xlsx|spreadsheet)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:generate|create|download)\s+(?:powerpoint|ppt|pptx)\s+(?:for|of)\s+(?:portfolio\s+)?port_[\w]+", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:generate|create|download)\s+(?:pdf|pdf\s+report)\s+(?:for|of)\s+(?:portfolio\s+)?port_[\w]+", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:generate|create|download)\s+(?:excel|xlsx)\s+(?:for|of)\s+(?:portfolio\s+)?port_[\w]+", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\bexport\s+(?:to\s+)?(?:excel|xlsx|powerpoint|ppt|pdf|spreadsheet)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:create|generate)\s+(?:powerpoint|ppt)\s+(?:presentation|for)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:download|generate)\s+(?:portfolio\s+)?(?:report\s+as\s+)?(?:pdf|powerpoint|ppt|excel)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:generate|create)\s+(?:excel|xlsx)\s+(?:file|for)", EnhancedIntent.PORTFOLIO_EXPORT),
        # CVaR patterns
        (r"\b(?:calculate|compute|show|what\s+is)\s+(?:cvar|conditional\s+value\s+at\s+risk|expected\s+shortfall)", EnhancedIntent.PORTFOLIO_CVAR),
        (r"\b(?:cvar|conditional\s+value\s+at\s+risk|expected\s+shortfall)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_CVAR),
        (r"\b(?:show\s+me|calculate)\s+cvar\s+(?:at|for)", EnhancedIntent.PORTFOLIO_CVAR),
        # Volatility patterns
        (r"\b(?:forecast|predict|estimate|show|what\s+is)\s+(?:volatility|vol)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_VOLATILITY),
        (r"\b(?:what\s+volatility\s+regime|volatility\s+regime|regime\s+detection)", EnhancedIntent.PORTFOLIO_VOLATILITY),
        (r"\b(?:garch|ewma)\s+(?:volatility|forecast)", EnhancedIntent.PORTFOLIO_VOLATILITY),
        # ESG patterns
        (r"\b(?:what\s+is|show|calculate|analyze)\s+(?:my\s+)?(?:portfolio\s+)?(?:esg|esg\s+score)", EnhancedIntent.PORTFOLIO_ESG),
        (r"\b(?:esg|esg\s+exposure|esg\s+score)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_ESG),
        (r"\b(?:optimize|rebalance)\s+(?:with|for)\s+esg\s+(?:constraints?|requirements?)", EnhancedIntent.PORTFOLIO_ESG),
        (r"\b(?:how\s+can\s+I\s+)?(?:improve|enhance)\s+(?:my\s+)?esg\s+score", EnhancedIntent.PORTFOLIO_ESG),
        # Tax patterns
        (r"\b(?:calculate|show|what\s+is)\s+(?:tax|tax-adjusted|after-tax)\s+(?:returns?|impact)", EnhancedIntent.PORTFOLIO_TAX),
        (r"\b(?:tax|tax-aware|tax-efficient)\s+(?:optimization|optimize|rebalance)", EnhancedIntent.PORTFOLIO_TAX),
        (r"\b(?:find|show|identify)\s+(?:tax-loss\s+harvesting|tax\s+loss)", EnhancedIntent.PORTFOLIO_TAX),
        # Tracking error patterns
        (r"\b(?:what\s+is|calculate|show)\s+(?:my\s+)?(?:tracking\s+error|active\s+risk)", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
        (r"\b(?:optimize|minimize)\s+(?:tracking\s+error|active\s+risk)", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
        (r"\b(?:maximize|optimize)\s+information\s+ratio", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
        # Diversification patterns
        (r"\b(?:what\s+is|calculate|show)\s+(?:my\s+)?(?:diversification\s+ratio|diversification)", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
        (r"\b(?:optimize|maximize)\s+(?:for\s+)?(?:maximum|better)\s+diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
        (r"\b(?:show|what\s+is)\s+(?:concentration\s+risk|concentration)", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
        # Sentiment patterns
        (r"\b(?:what\s+is|show)\s+(?:the\s+)?(?:sentiment|sentiment\s+score)\s+(?:for|of)\s+(\w+)", EnhancedIntent.PORTFOLIO_SENTIMENT),
        (r"\b(?:enrich|show)\s+(?:portfolio|holdings)\s+(?:with\s+)?sentiment", EnhancedIntent.PORTFOLIO_SENTIMENT),
        # Policy/IPS patterns
        (r"\b(?:upload|load|import|add)\s+(?:investment\s+)?(?:policy\s+statement|ips|policy)", EnhancedIntent.PORTFOLIO_POLICY),
        (r"\b(?:show|get|what\s+are)\s+(?:my\s+)?(?:portfolio\s+)?(?:policy\s+constraints?|constraints?|policy)", EnhancedIntent.PORTFOLIO_POLICY),
        (r"\b(?:check|verify|validate)\s+(?:policy\s+compliance|compliance)", EnhancedIntent.PORTFOLIO_COMPLIANCE),
        (r"\b(?:policy\s+compliance|compliance\s+check|policy\s+violations?)", EnhancedIntent.PORTFOLIO_COMPLIANCE),
        # Multi-period optimization patterns
        (r"\b(?:multi-period|multi\s+period|strategic\s+planning)\s+(?:optimization|optimize|rebalance)", EnhancedIntent.PORTFOLIO_MULTI_PERIOD),
        (r"\b(?:optimize|rebalance)\s+(?:for\s+)?(?:multi-period|multiple\s+periods|strategic)", EnhancedIntent.PORTFOLIO_MULTI_PERIOD),
        (r"\b(?:plan|create)\s+(?:multi-period|strategic)\s+(?:portfolio|plan)", EnhancedIntent.PORTFOLIO_MULTI_PERIOD),
        # Risk parity patterns
        (r"\b(?:risk\s+parity|equal\s+risk)\s+(?:optimization|optimize|rebalance|portfolio)", EnhancedIntent.PORTFOLIO_RISK_PARITY),
        (r"\b(?:optimize|rebalance)\s+(?:for\s+)?(?:risk\s+parity|equal\s+risk)", EnhancedIntent.PORTFOLIO_RISK_PARITY),
        # Factor attribution patterns
        (r"\b(?:factor\s+attribution|factor\s+analysis|factor\s+exposure)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_FACTOR_ATTRIBUTION),
        (r"\b(?:show|get|calculate)\s+(?:factor\s+attribution|factor\s+analysis)", EnhancedIntent.PORTFOLIO_FACTOR_ATTRIBUTION),
        (r"\b(?:what\s+are|what\s+is)\s+(?:my\s+)?(?:factor\s+exposure|factor\s+loadings?)", EnhancedIntent.PORTFOLIO_FACTOR_ATTRIBUTION),
        # Backtesting patterns
        (r"\b(?:backtest|backtest\s+portfolio|historical\s+backtest)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_BACKTEST),
        (r"\b(?:run|execute|perform)\s+(?:backtest|backtesting|historical\s+test)", EnhancedIntent.PORTFOLIO_BACKTEST),
        (r"\b(?:validate|test)\s+(?:strategy|portfolio)\s+(?:with|using)\s+backtest", EnhancedIntent.PORTFOLIO_BACKTEST),
        # Trade management patterns
        (r"\b(?:generate|create|show)\s+(?:trade\s+list|trades?|rebalancing\s+trades?)", EnhancedIntent.PORTFOLIO_TRADES),
        (r"\b(?:export|download)\s+(?:trade\s+list|trades?)\s+(?:as|in)\s+(?:csv|fix|excel)", EnhancedIntent.PORTFOLIO_TRADES),
        (r"\b(?:analyze|simulate|what\s+if)\s+(?:trade\s+impact|proposed\s+trades?)", EnhancedIntent.PORTFOLIO_TRADES),
        (r"\b(?:estimate|calculate)\s+(?:trade\s+costs?|execution\s+costs?)", EnhancedIntent.PORTFOLIO_TRADES),
        # Custom report patterns
        (r"\b(?:create|generate|build)\s+(?:custom\s+report|custom\s+portfolio\s+report)", EnhancedIntent.PORTFOLIO_CUSTOM_REPORT),
        (r"\b(?:save|load|get)\s+(?:report\s+template|template)", EnhancedIntent.PORTFOLIO_CUSTOM_REPORT),
        (r"\b(?:list|show)\s+(?:report\s+templates?|available\s+templates?)", EnhancedIntent.PORTFOLIO_CUSTOM_REPORT),
        # Dashboard layout patterns
        (r"\b(?:save|load|get|set)\s+(?:dashboard\s+layout|layout|dashboard\s+configuration)", EnhancedIntent.PORTFOLIO_DASHBOARD_LAYOUT),
        (r"\b(?:customize|configure)\s+(?:dashboard|layout)", EnhancedIntent.PORTFOLIO_DASHBOARD_LAYOUT),
        (r"\b(?:list|show)\s+(?:my\s+)?(?:dashboard\s+layouts?|saved\s+layouts?)", EnhancedIntent.PORTFOLIO_DASHBOARD_LAYOUT),
        # User preferences patterns
        (r"\b(?:set|change|save|update)\s+(?:my\s+)?(?:preferences?|settings?|user\s+preferences?)", EnhancedIntent.PORTFOLIO_PREFERENCES),
        (r"\b(?:get|show|load)\s+(?:my\s+)?(?:preferences?|settings?|user\s+preferences?)", EnhancedIntent.PORTFOLIO_PREFERENCES),
        (r"\b(?:set\s+theme|change\s+theme|dark\s+mode|light\s+mode|font\s+size)", EnhancedIntent.PORTFOLIO_PREFERENCES),
        # Brokerage integration patterns
        (r"\b(?:connect|link|sync)\s+(?:brokerage|broker)\s+(?:account|to\s+portfolio)", EnhancedIntent.PORTFOLIO_BROKERAGE),
        (r"\b(?:sync|import)\s+(?:holdings|positions)\s+(?:from\s+)?(?:brokerage|broker)", EnhancedIntent.PORTFOLIO_BROKERAGE),
        (r"\b(?:execute|place)\s+(?:trades?|orders?)\s+(?:via|through|on)\s+(?:brokerage|broker)", EnhancedIntent.PORTFOLIO_BROKERAGE),
        # Alerts patterns
        (r"\b(?:set|create|configure)\s+(?:alert|alerts?|notification)", EnhancedIntent.PORTFOLIO_ALERTS),
        (r"\b(?:show|get|list)\s+(?:my\s+)?(?:alerts?|notifications?)", EnhancedIntent.PORTFOLIO_ALERTS),
        (r"\b(?:rebalancing\s+alert|rebalance\s+alert|drift\s+alert)", EnhancedIntent.PORTFOLIO_ALERTS),
        (r"\b(?:check|when)\s+(?:do\s+I\s+need\s+to\s+rebalance|rebalancing\s+needed)", EnhancedIntent.PORTFOLIO_ALERTS),
        # Scheduled reports patterns
        (r"\b(?:schedule|set\s+up)\s+(?:automated|scheduled)\s+(?:report|reports?)", EnhancedIntent.PORTFOLIO_SCHEDULE),
        (r"\b(?:daily|weekly|monthly)\s+(?:report|portfolio\s+report)", EnhancedIntent.PORTFOLIO_SCHEDULE),
        (r"\b(?:list|show)\s+(?:scheduled\s+reports?|report\s+schedule)", EnhancedIntent.PORTFOLIO_SCHEDULE),
        # Portfolio enrichment patterns
        (r"\b(?:enrich|add|include)\s+(?:portfolio|holdings)\s+(?:with\s+)?(?:alternative\s+data|fundamentals?|data)", EnhancedIntent.PORTFOLIO_ENRICHMENT),
        (r"\b(?:show|get)\s+(?:enriched|full|detailed)\s+(?:portfolio|holdings)", EnhancedIntent.PORTFOLIO_ENRICHMENT),
        (r"\b(?:add|include)\s+(?:economic\s+indicators?|macro\s+data|sentiment)", EnhancedIntent.PORTFOLIO_ENRICHMENT),
        # Committee brief patterns
        (r"\b(?:generate|create|build)\s+(?:committee\s+brief|brief|executive\s+summary)", EnhancedIntent.PORTFOLIO_SUMMARY),
        (r"\b(?:committee\s+brief|executive\s+brief)\s+(?:for|of)\s+(?:my\s+)?portfolio", EnhancedIntent.PORTFOLIO_SUMMARY),
        # Additional optimization patterns
        (r"\b(?:optimize|rebalance)\s+(?:with|for)\s+(?:turnover\s+limit|turnover\s+constraint)", EnhancedIntent.PORTFOLIO_OPTIMIZE),
        (r"\b(?:optimize|rebalance)\s+(?:batch|multiple)\s+(?:portfolios?)", EnhancedIntent.PORTFOLIO_OPTIMIZE),
        # Additional scenario patterns
        (r"\b(?:run|execute)\s+(?:geopolitical|trade\s+war|conflict)\s+(?:scenario|stress\s+test)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:what\s+if|what\s+happens)\s+(?:interest\s+rates?|rates?)\s+(?:rise|fall|change)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:what\s+if|what\s+happens)\s+(?:fx|currency|exchange\s+rate)\s+(?:drops?|rises?|changes?)", EnhancedIntent.PORTFOLIO_SCENARIO),
        (r"\b(?:run|execute)\s+(?:sector\s+shock|sector\s+rotation)\s+(?:scenario|stress\s+test)", EnhancedIntent.PORTFOLIO_SCENARIO),
        # Additional export patterns
        (r"\b(?:export|download)\s+(?:interactive\s+charts?|charts?)\s+(?:as|in)\s+(?:html|interactive)", EnhancedIntent.PORTFOLIO_EXPORT),
        (r"\b(?:generate|create)\s+(?:custom\s+)?(?:presentation|slides?)", EnhancedIntent.PORTFOLIO_EXPORT),
        # Additional analysis patterns
        (r"\b(?:calculate|show|what\s+is)\s+(?:beta|portfolio\s+beta|market\s+beta)", EnhancedIntent.PORTFOLIO_SUMMARY),
        (r"\b(?:calculate|show|what\s+is)\s+(?:alpha|portfolio\s+alpha|excess\s+return)", EnhancedIntent.PORTFOLIO_SUMMARY),
        (r"\b(?:calculate|show|what\s+is)\s+(?:information\s+ratio|sharpe|sortino)", EnhancedIntent.PORTFOLIO_SUMMARY),
        # IPS document patterns
        (r"\b(?:upload|load|import|parse)\s+(?:ips|investment\s+policy|policy\s+document)", EnhancedIntent.PORTFOLIO_POLICY),
        (r"\b(?:extract|parse|read)\s+(?:constraints?|policy\s+constraints?)\s+(?:from|in)\s+(?:ips|document)", EnhancedIntent.PORTFOLIO_POLICY),
    ]
    
    for pattern, intent in portfolio_patterns:
        if re.search(pattern, lowered):
            return EnhancedRouting(
                intent=intent,
                confidence=0.95,  # Increased confidence for portfolio intents
                force_text_only=True  # Prevent dashboard rendering for portfolio queries
            )
    
    # ========================================
    # 1. ML FORECASTING INTENTS
    # ========================================
    # ML Forecasting patterns
    ml_forecast_patterns = [
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+arima", EnhancedIntent.ML_FORECAST_ARIMA),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+prophet", EnhancedIntent.ML_FORECAST_PROPHET),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+ets", EnhancedIntent.ML_FORECAST_ETS),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+lstm", EnhancedIntent.ML_FORECAST_LSTM),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+gru", EnhancedIntent.ML_FORECAST_GRU),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+transformer", EnhancedIntent.ML_FORECAST_TRANSFORMER),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+ensemble", EnhancedIntent.ML_FORECAST_ENSEMBLE),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)\s+(?:using|with)\s+(?:best|auto|automatic|ml)\s+model", EnhancedIntent.ML_FORECAST_AUTO),
        (r"\b(?:forecast|predict|estimate|project)\s+(?:.+?)", EnhancedIntent.ML_FORECAST_AUTO),  # General forecast
    ]
    
    for pattern, intent in ml_forecast_patterns:
        if re.search(pattern, lowered):
            return EnhancedRouting(
                intent=intent,
                confidence=0.90,
                force_text_only=True  # Prevent dashboard for forecasts
            )
    
    # Also check if query contains portfolio ID + keywords
    if re.search(portfolio_id_pattern, lowered):
        # If just "use portfolio port_xxx" without other keywords, treat as holdings query
        if re.search(r"\b(?:use|switch|set|select)\s+portfolio\s+port_[\w]+", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_HOLDINGS,
                confidence=0.9
            )
        elif re.search(r"\b(?:analyze|analysis|summary)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SUMMARY,
                confidence=0.9
            )
        elif re.search(r"\b(?:holdings|positions|stocks)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_HOLDINGS,
                confidence=0.85
            )
        elif re.search(r"\b(?:exposure|sector|factor)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_EXPOSURE,
                confidence=0.85
            )
        elif re.search(r"\b(?:optimize|rebalance)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_OPTIMIZE,
                confidence=0.85
            )
        elif re.search(r"\b(?:attribution|attribute)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_ATTRIBUTION,
                confidence=0.85
            )
        elif re.search(r"\b(?:scenario|stress\s+test|what\s+if)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SCENARIO,
                confidence=0.85
            )
        elif re.search(r"\b(?:export|generate|download|create)\s+(?:powerpoint|ppt|pptx|pdf|excel|xlsx)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_EXPORT,
                confidence=0.85
            )
        elif re.search(r"\b(?:cvar|conditional\s+value\s+at\s+risk|expected\s+shortfall)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_CVAR,
                confidence=0.85
            )
        elif re.search(r"\b(?:volatility|vol|garch|ewma|regime)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_VOLATILITY,
                confidence=0.85
            )
        elif re.search(r"\b(?:esg|esg\s+score)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_ESG,
                confidence=0.85
            )
        elif re.search(r"\b(?:tax|tax-aware|tax-adjusted)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_TAX,
                confidence=0.85
            )
        elif re.search(r"\b(?:tracking\s+error|active\s+risk|information\s+ratio)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_TRACKING_ERROR,
                confidence=0.85
            )
        elif re.search(r"\b(?:diversification|concentration)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_DIVERSIFICATION,
                confidence=0.85
            )
        elif re.search(r"\b(?:sentiment)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SENTIMENT,
                confidence=0.85
            )
        elif re.search(r"\b(?:policy|ips|constraints?|compliance)", lowered):
            if "compliance" in lowered or "violation" in lowered:
                return EnhancedRouting(
                    intent=EnhancedIntent.PORTFOLIO_COMPLIANCE,
                    confidence=0.85
                )
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_POLICY,
                confidence=0.85
            )
        elif re.search(r"\b(?:multi-period|strategic\s+planning|multiple\s+periods)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_MULTI_PERIOD,
                confidence=0.85
            )
        elif re.search(r"\b(?:risk\s+parity|equal\s+risk)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_RISK_PARITY,
                confidence=0.85
            )
        elif re.search(r"\b(?:factor\s+attribution|factor\s+analysis|factor\s+exposure)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_FACTOR_ATTRIBUTION,
                confidence=0.85
            )
        elif re.search(r"\b(?:backtest|backtesting|historical\s+test)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_BACKTEST,
                confidence=0.85
            )
        elif re.search(r"\b(?:trade\s+list|trades?|rebalancing\s+trades?)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_TRADES,
                confidence=0.85
            )
        elif re.search(r"\b(?:custom\s+report|report\s+template)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_CUSTOM_REPORT,
                confidence=0.85
            )
        elif re.search(r"\b(?:dashboard\s+layout|layout|dashboard\s+configuration)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_DASHBOARD_LAYOUT,
                confidence=0.85
            )
        elif re.search(r"\b(?:preferences?|settings?|theme|font)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_PREFERENCES,
                confidence=0.85
            )
        elif re.search(r"\b(?:brokerage|broker|sync\s+holdings)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_BROKERAGE,
                confidence=0.85
            )
        elif re.search(r"\b(?:alert|alerts?|notification|rebalancing\s+needed)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_ALERTS,
                confidence=0.85
            )
        elif re.search(r"\b(?:scheduled|automated)\s+(?:report|reports?)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SCHEDULE,
                confidence=0.85
            )
        elif re.search(r"\b(?:enrich|alternative\s+data|fundamentals?)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_ENRICHMENT,
                confidence=0.85
            )
        elif re.search(r"\b(?:committee\s+brief|executive\s+brief)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SUMMARY,
                confidence=0.85
            )
        elif re.search(r"\b(?:beta|alpha|information\s+ratio|sharpe|sortino)", lowered):
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_SUMMARY,
                confidence=0.85
            )
        else:
            # If portfolio ID is mentioned without specific intent, default to holdings
            return EnhancedRouting(
                intent=EnhancedIntent.PORTFOLIO_HOLDINGS,
                confidence=0.7
            )
    
    # ========================================
    # 1A. KPI / TEMPLATE INTENTS
    # ========================================
    PERIOD_RX = r"(?P<period>(?:fy(?P<fy>\d{4})|q(?P<q>[1-4])\s*fy(?P<qfy>\d{4})|latest\s+quarter|ttm))"
    ENTITY_RX = r"(?P<entity>[A-Za-z0-9&.\-\s]+?)"
    KPI_NAME_RX = r"(?P<kpi>[\w\s\-%/()\.]+?)"

    # CREATE_KPI with explicit formula
    m = re.search(
        r"\b(?:create|define|add)\s+(?:a\s+)?kpi[:\s]+" + KPI_NAME_RX + r"\s*=\s*(?P<formula>[^;]+)$",
        clean_text,
        re.IGNORECASE,
    )
    if m:
        kpi = m.group("kpi").strip()
        formula = m.group("formula").strip()
        return EnhancedRouting(
            intent=EnhancedIntent.CREATE_KPI,
            confidence=with_conf(0.95),
            force_text_only=True,
            slots={"kpi_name": kpi, "formula_text": formula, "scope": "user"},
            missing_slots=[],
            disambiguation_questions=[],
        )

    # CREATE_KPI without formula -> SOURCE_LOOKUP
    m = re.search(
        r"\b(?:create|define|add)\s+(?:a\s+)?kpi[:\s]+" + KPI_NAME_RX + r"$",
        clean_text,
        re.IGNORECASE,
    )
    if m:
        kpi = m.group("kpi").strip()
        return build_source_lookup_routing(kpi)

    # COMPUTE_KPI for entity + period
    m = re.search(
        r"\b(?:show|compute|calculate)\s+(?:my\s+custom\s+)?kpi\s*" + KPI_NAME_RX
        + r"\s+(?:for|on)\s+" + ENTITY_RX + r"\s+" + PERIOD_RX + r"\b",
        clean_text,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r"\b(?:show|compute|calculate)\s+" + KPI_NAME_RX + r"\s+(?:for|on)\s+"
            + ENTITY_RX + r"\s+" + PERIOD_RX + r"\b",
            clean_text,
            re.IGNORECASE,
        )

    if m:
        kpi = m.group("kpi").strip()
        entity = m.group("entity").strip()
        period_text = m.group("period")
        period_text_lower = period_text.lower() if period_text else ""

        period_info = extract_period_from_structured(existing_structured.get("periods"))
        period = period_info or {"basis": None, "year": None, "quarter": None, "ttm": False}

        if not period_info:
            if m.group("fy"):
                period["basis"] = "FY"
                period["year"] = int(m.group("fy"))
            elif m.group("q") and m.group("qfy"):
                period["basis"] = "QUARTER"
                period["quarter"] = int(m.group("q"))
                period["year"] = int(m.group("qfy"))
            elif "latest quarter" in period_text_lower:
                period["basis"] = "QUARTER"
                period["quarter"] = "LATEST"
            elif "ttm" in period_text_lower:
                period["basis"] = "TTM"
                period["ttm"] = True
            elif "financial year" in period_text_lower or "fiscal year" in period_text_lower:
                digits = re.findall(r"\d{4}", period_text)
                if digits:
                    period["basis"] = "FY"
                    period["year"] = int(digits[0])
            elif re.search(r"\b20\d{2}\b", period_text_lower):
                digits = re.findall(r"\b20\d{2}\b", period_text_lower)
                if digits:
                    period["basis"] = "FY"
                    period["year"] = int(digits[0])

        if period_text:
            period["text"] = period_text.strip()

        tickers_slot = extract_tickers_from_structured(existing_structured)
        if not tickers_slot and entity:
            primary = entity.strip().split()
            if primary:
                tickers_slot.append(primary[0].upper())
        tickers_slot = list(dict.fromkeys(tickers_slot))

        slots_payload = {
            "kpi_name": kpi,
            "tickers": tickers_slot,
            "entity_text": entity,
            "period": period,
            "scope": "user",
        }

        missing_slots: List[str] = []
        if not tickers_slot:
            missing_slots.append("tickers")
        if not period.get("basis") or (period.get("basis") in {"FY", "YEAR"} and period.get("year") is None):
            missing_slots.append("period")

        if missing_slots:
            return build_source_lookup_routing(kpi, slots_payload, missing_slots=missing_slots)

        return EnhancedRouting(
            intent=EnhancedIntent.COMPUTE_KPI,
            confidence=with_conf(0.9),
            force_text_only=True,
            slots=slots_payload,
            missing_slots=[],
            disambiguation_questions=[],
        )

    # MANAGE_KPI: list/delete/rename
    if re.search(r"\b(?:list|show)\s+(?:my\s+)?custom\s+kpis?\b", clean_text, re.IGNORECASE):
        return EnhancedRouting(
            intent=EnhancedIntent.MANAGE_KPI,
            confidence=with_conf(0.9),
            slots={"action": "list"},
            force_text_only=True,
        )
    m = re.search(r"\bdelete\s+kpi\s+(.+)$", clean_text, re.IGNORECASE)
    if m:
        return EnhancedRouting(
            intent=EnhancedIntent.MANAGE_KPI,
            confidence=with_conf(0.9),
            slots={"action": "delete", "kpi_name": m.group(1).strip()},
            force_text_only=True,
        )
    m = re.search(r"\brename\s+kpi\s+(.+?)\s+to\s+(.+)$", clean_text, re.IGNORECASE)
    if m:
        return EnhancedRouting(
            intent=EnhancedIntent.MANAGE_KPI,
            confidence=with_conf(0.9),
            slots={
                "action": "rename",
                "kpi_name": m.group(1).strip(),
                "new_name": m.group(2).strip(),
            },
            force_text_only=True,
        )

    # Structured parser detected KPI + ticker (+/- period) - promote to compute/lookup
    metric_candidate = extract_metric_candidate(existing_structured)
    structured_tickers = extract_tickers_from_structured(existing_structured)
    structured_period = extract_period_from_structured(existing_structured.get("periods"))

    if metric_candidate and structured_tickers:
        slots = {
            "kpi_name": metric_candidate,
            "tickers": structured_tickers,
            "period": structured_period or {"basis": None, "year": None, "quarter": None, "ttm": False},
            "scope": "user",
        }
        if not structured_period:
            return build_source_lookup_routing(metric_candidate, slots, missing_slots=["period"])

        return EnhancedRouting(
            intent=EnhancedIntent.COMPUTE_KPI,
            confidence=with_conf(0.82),
            force_text_only=True,
            slots=slots,
            missing_slots=[],
            disambiguation_questions=[],
        )

    # TEMPLATE SAVE/RUN
    m = re.search(r'\b(?:save|store)\s+(?:this|it)\s+as\s+"([^"]+)"', clean_text, re.IGNORECASE)
    if m:
        return EnhancedRouting(
            intent=EnhancedIntent.TEMPLATE_SAVE,
            confidence=with_conf(0.95),
            slots={"template_name": m.group(1)},
            force_text_only=True,
        )

    m = re.search(
        r'\b(?:run|load)\s+my\s+"([^"]+)"\s+for\s+([A-Za-z0-9,\s]+)\s+(?:with\s+)?(?:fiscal_)?year\s*=\s*(\d{4})',
        clean_text,
        re.IGNORECASE,
    )
    if m:
        tickers = [t.strip().upper() for t in re.split(r"[,\s]+", m.group(2)) if t.strip()]
        return EnhancedRouting(
            intent=EnhancedIntent.TEMPLATE_RUN,
            confidence=with_conf(0.93),
            force_text_only=True,
            slots={
                "template_name": m.group(1),
                "tickers": tickers,
                "period": {"basis": "FY", "year": int(m.group(3))},
            },
        )

    # Generic KPI mention -> SOURCE_LOOKUP fallback
    maybe_kpi = re.search(r"\b(show|compute|calculate)\s+([A-Za-z][\w\s\-/%()\.]+)\b", clean_text, re.IGNORECASE)
    if maybe_kpi and not any(w in lowered for w in [" vs ", " compare ", " dashboard "]):
        kpi_guess = maybe_kpi.group(2).strip()
        return EnhancedRouting(
            intent=EnhancedIntent.SOURCE_LOOKUP,
            confidence=with_conf(0.8),
            force_text_only=True,
            slots={
                "kpi_name": kpi_guess,
                "lookup_scope": ["internal_dictionary", "financial_glossary", "web"],
            },
            missing_slots=[],
            disambiguation_questions=[],
        )

    # ========================================
    # 1. LEGACY COMMANDS (High Priority)
    # ========================================
    # Pass these through unchanged to preserve existing behavior
    legacy_prefixes = ["fact ", "fact-range ", "audit ", "ingest ", "scenario ", "table "]
    if any(lowered.startswith(cmd) for cmd in legacy_prefixes):
        return EnhancedRouting(
            intent=EnhancedIntent.LEGACY_COMMAND,
            legacy_command=text,
            confidence=1.0
        )
    
    # ========================================
    # 2. EXPLICIT DASHBOARD REQUEST
    # ========================================
    dashboard_keywords = ["dashboard", "full dashboard", "comprehensive dashboard", "detailed dashboard"]
    if any(kw in lowered for kw in dashboard_keywords):
        # Check if it's a single ticker dashboard request
        tickers = existing_structured.get("tickers", []) if existing_structured else []
        if isinstance(tickers, list) and len(tickers) == 1:
            return EnhancedRouting(
                intent=EnhancedIntent.DASHBOARD_EXPLICIT,
                force_dashboard=True,
                confidence=1.0
            )
        # Multi-ticker dashboard request
        return EnhancedRouting(
            intent=EnhancedIntent.DASHBOARD_EXPLICIT,
            force_dashboard=True,
            force_text_only=False,
            confidence=1.0
        )
    
    # ========================================
    # 3. DETERMINISTIC PATTERN MATCHING
    # ========================================
    
    # "Show X KPIs" pattern (single or multiple tickers)
    # Lower confidence to prefer LLM for conversational mode
    show_kpi_match = re.search(r'\bshow\s+([\w\s,]+?)\s+(?:kpis?|metrics?|table)', lowered)
    if show_kpi_match:
        entities_text = show_kpi_match.group(1)
        # Check if it's multiple tickers
        has_and = ' and ' in entities_text
        has_comma = ',' in entities_text
        
        if has_and or has_comma:
            return EnhancedRouting(
                intent=EnhancedIntent.METRICS_MULTI,
                force_text_only=True,  # Multi-ticker = text table
                confidence=0.7  # Lowered from 0.9
            )
        else:
            # Single ticker - only route to table if explicit "kpis/metrics/table"
            return EnhancedRouting(
                intent=EnhancedIntent.METRICS_SINGLE,
                force_text_only=True,
                confidence=0.6  # Lowered from 0.9 - prefer LLM
            )
    
    # "Compare X vs Y" pattern (exactly 2)
    compare_two = re.search(r'\bcompare\s+(\w+)\s+(?:vs|versus)\s+(\w+)', lowered)
    if compare_two:
        return EnhancedRouting(
            intent=EnhancedIntent.COMPARE_TWO,
            force_text_only=True,  # Comparisons always text
            confidence=1.0
        )
    
    # "Compare X, Y, and Z" pattern (3+)
    compare_multi = re.search(r'\bcompare\s+((?:\w+\s*,\s*)+\w+\s+and\s+\w+)', lowered)
    if compare_multi:
        return EnhancedRouting(
            intent=EnhancedIntent.COMPARE_MULTI,
            force_text_only=True,  # Multi-compare always text
            confidence=1.0
        )
    
    # ========================================
    # 4. FALLBACK TO EXISTING PARSER
    # ========================================
    # Use existing structured parser's intent
    # Handle None/empty structured response
    existing_intent = existing_structured.get("intent") if existing_structured else None
    tickers = existing_structured.get("tickers", []) if existing_structured else []
    
    if existing_intent == "compare":
        if len(tickers) >= 3:
            return EnhancedRouting(
                intent=EnhancedIntent.COMPARE_MULTI,
                force_text_only=True,
                confidence=0.8
            )
        elif len(tickers) == 2:
            return EnhancedRouting(
                intent=EnhancedIntent.COMPARE_TWO,
                force_text_only=True,
                confidence=0.8
            )
        elif len(tickers) == 1:
            # Single ticker with compare intent is ambiguous
            return EnhancedRouting(
                intent=EnhancedIntent.METRICS_SINGLE,
                force_dashboard=False,
                confidence=0.6
            )
    
    elif existing_intent in ["lookup", "trend"]:
        # Prefer natural language for these - lower confidence
        if len(tickers) == 1:
            return EnhancedRouting(
                intent=EnhancedIntent.NATURAL_LANGUAGE,  # Changed: route to LLM
                confidence=0.5  # Lowered to prefer LLM
            )
        elif len(tickers) >= 2:
            return EnhancedRouting(
                intent=EnhancedIntent.METRICS_MULTI,
                force_text_only=True,
                confidence=0.6  # Lowered from 0.8
            )
    
    elif existing_intent == "rank":
        # Ranking queries should use natural language / LLM
        return EnhancedRouting(
            intent=EnhancedIntent.NATURAL_LANGUAGE,
            confidence=0.4
        )
    
    elif existing_intent == "explain_metric":
        # Explanation queries should use natural language / LLM
        return EnhancedRouting(
            intent=EnhancedIntent.NATURAL_LANGUAGE,
            confidence=0.4
        )
    
    # ========================================
    # 5. NATURAL LANGUAGE (Low Confidence)
    # ========================================
    # Complex queries should go to LLM
    return EnhancedRouting(
        intent=EnhancedIntent.NATURAL_LANGUAGE,
        confidence=0.5  # Low confidence = try LLM
    )


def should_build_dashboard(
    routing: EnhancedRouting,
    existing_decision: bool
) -> bool:
    """
    Determine if dashboard should be built, respecting both new routing and existing logic.
    
    Args:
        routing: Enhanced routing decision
        existing_decision: What the existing code would have done
        
    Returns:
        True if dashboard should be built
    """
    # Force dashboard if explicitly requested
    if routing.force_dashboard:
        return True
    
    # Never build dashboard if force_text_only
    if routing.force_text_only:
        return False
    
    # Otherwise, respect existing decision
    return existing_decision

