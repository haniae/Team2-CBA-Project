"""
Intent-Specific Retrieval Policies

Defines different retrieval strategies based on query intent:
- METRIC_LOOKUP: Mostly SQL, small context, no multi-hop
- WHY/EXPLANATION: Narratives + metrics, multi-hop on SEC + macro
- COMPARE: Enforce same period, same units, multi-entity retrieval
- RISK: Bias toward "Risk Factors", "Uncertainties", downside scenarios
- FORECAST: Emphasize ML forecast tables + sector benchmarks
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

LOGGER = logging.getLogger(__name__)


class RetrievalIntent(Enum):
    """Retrieval intent types for policy-based retrieval."""
    METRIC_LOOKUP = "metric_lookup"  # Simple metric queries
    WHY = "why"  # Explanation queries
    COMPARE = "compare"  # Comparison queries
    RISK = "risk"  # Risk-related queries
    FORECAST = "forecast"  # Forecasting queries
    GENERAL = "general"  # General queries


@dataclass
class RetrievalPolicy:
    """Retrieval policy configuration for a specific intent."""
    intent: RetrievalIntent
    use_multi_hop: bool
    k_docs: int  # Number of documents to retrieve
    narrative_weight: float  # Weight for narrative sources (0-1)
    metric_weight: float  # Weight for metric sources (0-1)
    use_reranking: bool
    max_sec_results: int
    max_uploaded_results: int
    bias_sections: Optional[List[str]] = None  # Section names to bias toward (e.g., ["Risk Factors"])
    require_same_period: bool = False  # For comparisons
    require_same_units: bool = False  # For comparisons


class IntentPolicyManager:
    """
    Manages intent-specific retrieval policies.
    
    Determines retrieval strategy based on query intent and applies appropriate policy.
    """
    
    # Default policies for each intent
    DEFAULT_POLICIES = {
        RetrievalIntent.METRIC_LOOKUP: RetrievalPolicy(
            intent=RetrievalIntent.METRIC_LOOKUP,
            use_multi_hop=False,
            k_docs=3,
            narrative_weight=0.3,
            metric_weight=0.9,
            use_reranking=False,
            max_sec_results=2,
            max_uploaded_results=1,
        ),
        RetrievalIntent.WHY: RetrievalPolicy(
            intent=RetrievalIntent.WHY,
            use_multi_hop=True,
            k_docs=8,
            narrative_weight=0.8,
            metric_weight=0.5,
            use_reranking=True,
            max_sec_results=6,
            max_uploaded_results=3,
        ),
        RetrievalIntent.COMPARE: RetrievalPolicy(
            intent=RetrievalIntent.COMPARE,
            use_multi_hop=True,
            k_docs=10,
            narrative_weight=0.6,
            metric_weight=0.8,
            use_reranking=True,
            max_sec_results=8,
            max_uploaded_results=2,
            require_same_period=True,
            require_same_units=True,
        ),
        RetrievalIntent.RISK: RetrievalPolicy(
            intent=RetrievalIntent.RISK,
            use_multi_hop=False,
            k_docs=5,
            narrative_weight=0.9,
            metric_weight=0.3,
            use_reranking=True,
            max_sec_results=5,
            max_uploaded_results=2,
            bias_sections=["Risk Factors", "Uncertainties", "Risk Management"],
        ),
        RetrievalIntent.FORECAST: RetrievalPolicy(
            intent=RetrievalIntent.FORECAST,
            use_multi_hop=True,
            k_docs=6,
            narrative_weight=0.4,
            metric_weight=0.7,
            use_reranking=False,
            max_sec_results=3,
            max_uploaded_results=1,
        ),
        RetrievalIntent.GENERAL: RetrievalPolicy(
            intent=RetrievalIntent.GENERAL,
            use_multi_hop=False,
            k_docs=5,
            narrative_weight=0.6,
            metric_weight=0.6,
            use_reranking=True,
            max_sec_results=5,
            max_uploaded_results=3,
        ),
    }
    
    def __init__(self, custom_policies: Optional[Dict[RetrievalIntent, RetrievalPolicy]] = None):
        """
        Initialize intent policy manager.
        
        Args:
            custom_policies: Custom policies to override defaults
        """
        self.policies = self.DEFAULT_POLICIES.copy()
        if custom_policies:
            self.policies.update(custom_policies)
    
    def detect_intent(self, query: str, parsed: Optional[Dict[str, Any]] = None) -> RetrievalIntent:
        """
        Detect retrieval intent from query.
        
        Args:
            query: User query
            parsed: Parsed query structure (optional)
        
        Returns:
            Detected RetrievalIntent
        """
        query_lower = query.lower()
        
        # Check for forecasting intent
        forecast_keywords = ["forecast", "predict", "project", "outlook", "future", "will", "expect"]
        if any(keyword in query_lower for keyword in forecast_keywords):
            return RetrievalIntent.FORECAST
        
        # Check for risk intent
        risk_keywords = ["risk", "uncertainty", "threat", "vulnerability", "exposure", "downside"]
        if any(keyword in query_lower for keyword in risk_keywords):
            return RetrievalIntent.RISK
        
        # Check for comparison intent
        compare_keywords = ["compare", "versus", "vs", "difference", "better", "worse", "relative"]
        if any(keyword in query_lower for keyword in compare_keywords):
            return RetrievalIntent.COMPARE
        
        # Check for explanation intent (why/how)
        why_keywords = ["why", "how", "explain", "reason", "cause", "because", "due to"]
        if any(keyword in query_lower for keyword in why_keywords):
            return RetrievalIntent.WHY
        
        # Check for simple metric lookup
        metric_patterns = [
            r"what (is|are) .* (revenue|earnings|profit|margin|ratio|price)",
            r"show (me )?.* (revenue|earnings|profit|margin|ratio)",
            r".* (revenue|earnings|profit|margin|ratio) (is|are|was|were)",
        ]
        if any(re.search(pattern, query_lower) for pattern in metric_patterns):
            return RetrievalIntent.METRIC_LOOKUP
        
        # Default to general
        return RetrievalIntent.GENERAL
    
    def get_policy(self, intent: RetrievalIntent) -> RetrievalPolicy:
        """
        Get retrieval policy for intent.
        
        Args:
            intent: RetrievalIntent
        
        Returns:
            RetrievalPolicy for the intent
        """
        return self.policies.get(intent, self.policies[RetrievalIntent.GENERAL])
    
    def rewrite_query(self, query: str, intent: RetrievalIntent) -> str:
        """
        Rewrite query based on intent to improve retrieval.
        
        Args:
            query: Original query
            intent: Detected intent
        
        Returns:
            Rewritten query
        """
        if intent == RetrievalIntent.COMPARE:
            # Expand comparison queries
            query_lower = query.lower()
            if "compare" in query_lower or "vs" in query_lower or "versus" in query_lower:
                # Add explicit request for same period, same units
                return f"{query} Ensure same reporting period and units for comparison."
        
        elif intent == RetrievalIntent.RISK:
            # Bias toward risk-related sections
            return f"{query} Focus on risk factors, uncertainties, and downside scenarios."
        
        elif intent == RetrievalIntent.FORECAST:
            # Emphasize forecasting context
            return f"{query} Include historical trends, sector benchmarks, and forecast models."
        
        elif intent == RetrievalIntent.METRIC_LOOKUP:
            # Keep simple for metric lookups
            return query
        
        return query

