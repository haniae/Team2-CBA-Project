"""
Enhanced deterministic router that wraps existing parsing with strict pattern rules.
This is a NON-INVASIVE layer that can be enabled via config without changing existing behavior.
"""

from __future__ import annotations

import re
from typing import Dict, Any, Optional
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


@dataclass
class EnhancedRouting:
    """Enhanced routing metadata to guide chatbot processing."""
    intent: EnhancedIntent
    force_dashboard: bool = False  # Override dashboard decision
    force_text_only: bool = False  # Never build dashboard
    legacy_command: Optional[str] = None  # If legacy, pass this through
    confidence: float = 1.0  # Confidence in routing decision
    

def enhance_structured_parse(
    text: str, 
    existing_structured: Dict[str, Any]
) -> EnhancedRouting:
    """
    Enhance existing parse_to_structured output with deterministic pattern matching.
    
    This DOES NOT replace existing parsing - it adds a confidence layer on top.
    
    Args:
        text: Original user input
        existing_structured: Output from parse_to_structured()
        
    Returns:
        EnhancedRouting with intent classification and dashboard hints
    """
    lowered = text.strip().lower()
    
    # ========================================
    # 1. LEGACY COMMANDS (Highest Priority)
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
        tickers = existing_structured.get("tickers", [])
        if len(tickers) == 1:
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
    existing_intent = existing_structured.get("intent")
    tickers = existing_structured.get("tickers", [])
    
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

