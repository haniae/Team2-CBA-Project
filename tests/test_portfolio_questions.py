"""
Test IVPA Portfolio Questions - Verify All Prompts Work

This script tests:
1. Routing pattern matching for portfolio questions
2. API endpoint availability
3. Portfolio functionality (with sample data if available)
4. Edge cases and variations
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from finanlyzeos_chatbot.routing.enhanced_router import enhance_structured_parse, EnhancedIntent
    ROUTING_AVAILABLE = True
except ImportError:
    ROUTING_AVAILABLE = False
    print("⚠️  Routing module not available")

# Core test cases from PORTFOLIO_QUESTIONS_GUIDE.md
CORE_TEST_CASES: List[Tuple[str, str, EnhancedIntent]] = [
    # Holdings
    ("Show my portfolio holdings", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("What are the holdings for port_abc123?", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("Show holdings for port_abc123", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("Use portfolio port_abc123", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    
    # Exposure
    ("What's my portfolio exposure?", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("Show portfolio sector exposure", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("Analyze exposure for port_abc123", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("What's my factor exposure?", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    
    # Summary
    ("Show portfolio summary", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    ("What's my portfolio stats?", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    ("Analyze portfolio port_abc123", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    
    # Optimization
    ("Optimize my portfolio", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    ("Rebalance portfolio port_abc123", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    ("Optimize for maximum Sharpe ratio", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    
    # Attribution
    ("Show portfolio attribution", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    ("What's driving my portfolio performance?", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    ("Attribution analysis for port_abc123", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    
    # Scenario
    ("What if the market crashes 20%?", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("Stress test my portfolio", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("What happens if tech sector drops 30%?", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("Monte Carlo simulation for port_abc123", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    
    # CVaR
    ("What's my portfolio CVaR?", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    ("Calculate CVaR for port_abc123", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    ("Portfolio expected shortfall", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    
    # ESG
    ("What's my portfolio ESG score?", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    ("Show ESG exposure for port_abc123", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    ("Analyze portfolio ESG", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    
    # Tax
    ("Tax analysis for my portfolio", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    ("What's my tax-adjusted return?", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    ("Tax-aware analysis for port_abc123", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    
    # Tracking Error
    ("What's my portfolio tracking error?", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    ("Active risk for port_abc123", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    ("Tracking error vs S&P 500", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    
    # Diversification
    ("How diversified is my portfolio?", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    ("Diversification score for port_abc123", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    ("Show portfolio concentration", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    
    # Export
    ("Export portfolio as PowerPoint", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
    ("Generate PDF report for port_abc123", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
    ("Export to Excel", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
]

# Extended test cases - edge cases and variations
EXTENDED_TEST_CASES: List[Tuple[str, str, EnhancedIntent]] = [
    # Holdings variations
    ("Display my current positions", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("List all holdings in port_test123", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("What stocks are in my portfolio?", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("Show me what I own", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    
    # Exposure variations
    ("Breakdown by sector", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("What sectors am I exposed to?", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("Show factor breakdown", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("Portfolio sector allocation", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    
    # Summary variations
    ("Give me a portfolio overview", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    ("Portfolio at a glance", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    ("Quick portfolio stats", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    ("What's in my portfolio summary?", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    
    # Optimization variations
    ("Re-optimize my portfolio", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    ("What's the optimal allocation?", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    ("Rebalance for better returns", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    ("Suggest portfolio changes", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
    
    # Attribution variations
    ("Breakdown of portfolio performance", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    ("What contributed to returns?", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    ("Performance attribution report", "portfolio_attribution", EnhancedIntent.PORTFOLIO_ATTRIBUTION),
    
    # Scenario variations
    ("Run a stress test", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("What if rates go up 2%?", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("Simulate market downturn", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    ("Model a recession scenario", "portfolio_scenario", EnhancedIntent.PORTFOLIO_SCENARIO),
    
    # CVaR variations
    ("What's my tail risk?", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    ("Calculate expected shortfall at 95%", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    ("CVaR analysis", "portfolio_cvar", EnhancedIntent.PORTFOLIO_CVAR),
    
    # ESG variations
    ("What's my ESG exposure?", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    ("ESG score breakdown", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    ("How sustainable is my portfolio?", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    
    # Tax variations
    ("After-tax returns", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    ("Tax efficiency analysis", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    ("What's my tax drag?", "portfolio_tax", EnhancedIntent.PORTFOLIO_TAX),
    
    # Tracking error variations
    ("How much active risk?", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    ("Tracking error relative to benchmark", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    ("Information ratio", "portfolio_tracking_error", EnhancedIntent.PORTFOLIO_TRACKING_ERROR),
    
    # Diversification variations
    ("What's my concentration risk?", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    ("Diversification metrics", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    ("How concentrated is my portfolio?", "portfolio_diversification", EnhancedIntent.PORTFOLIO_DIVERSIFICATION),
    
    # Export variations
    ("Create PowerPoint presentation", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
    ("Download portfolio report as PDF", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
    ("Export to spreadsheet", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
    ("Generate Excel file", "portfolio_export", EnhancedIntent.PORTFOLIO_EXPORT),
]

# Conversational/edge cases
EDGE_CASE_TESTS: List[Tuple[str, str, EnhancedIntent]] = [
    # Case variations
    ("SHOW PORTFOLIO HOLDINGS", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("show portfolio holdings", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("Show Portfolio Holdings", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    
    # With extra words
    ("Can you show my portfolio holdings?", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("I want to see my portfolio holdings", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("Please show portfolio summary", "portfolio_summary", EnhancedIntent.PORTFOLIO_SUMMARY),
    
    # Abbreviations
    ("Show port_123 holdings", "portfolio_holdings", EnhancedIntent.PORTFOLIO_HOLDINGS),
    ("What's port_test ESG?", "portfolio_esg", EnhancedIntent.PORTFOLIO_ESG),
    
    # Natural language
    ("Tell me about my portfolio exposure", "portfolio_exposure", EnhancedIntent.PORTFOLIO_EXPOSURE),
    ("I'd like to optimize my portfolio", "portfolio_optimize", EnhancedIntent.PORTFOLIO_OPTIMIZE),
]

# Combine all test cases
TEST_CASES = CORE_TEST_CASES + EXTENDED_TEST_CASES + EDGE_CASE_TESTS
