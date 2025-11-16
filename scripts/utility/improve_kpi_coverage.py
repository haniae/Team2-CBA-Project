#!/usr/bin/env python3
"""
Script to improve KPI coverage by identifying and fixing missing metrics.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine


def analyze_missing_kpis(db_path: str) -> dict:
    """Analyze which KPIs are missing for which tickers."""
    con = sqlite3.connect(db_path)
    
    # Key KPIs to check
    key_kpis = [
        'pe_ratio', 'ev_ebitda', 'pb_ratio', 'peg_ratio', 'dividend_yield',
        'debt_to_equity', 'ebitda', 'ebitda_margin', 'return_on_equity',
        'return_on_assets', 'free_cash_flow_margin', 'cash_conversion'
    ]
    
    # Get all tickers
    tickers = [row[0] for row in con.execute("SELECT DISTINCT ticker FROM financial_facts ORDER BY ticker").fetchall()]
    
    missing_analysis = {}
    
    for ticker in tickers:
        missing_kpis = []
        for kpi in key_kpis:
            result = con.execute("""
            SELECT COUNT(*) FROM metric_snapshots 
            WHERE ticker=? AND metric=? AND value IS NOT NULL
            """, (ticker, kpi)).fetchone()[0]
            if result == 0:
                missing_kpis.append(kpi)
        
        if missing_kpis:
            missing_analysis[ticker] = missing_kpis
    
    con.close()
    return missing_analysis


def identify_root_causes(db_path: str, ticker: str, missing_kpis: list) -> dict:
    """Identify root causes for missing KPIs."""
    con = sqlite3.connect(db_path)
    
    causes = {}
    
    # Check base data availability
    base_metrics = [
        'revenue', 'net_income', 'operating_income', 'total_assets', 
        'shareholders_equity', 'cash_from_operations', 'shares_outstanding',
        'long_term_debt', 'depreciation_and_amortization'
    ]
    
    available_base = {}
    for metric in base_metrics:
        count = con.execute("""
        SELECT COUNT(*) FROM financial_facts 
        WHERE ticker=? AND metric=?
        """, (ticker, metric)).fetchone()[0]
        available_base[metric] = count > 0
    
    # Check market quotes
    quote_count = con.execute("SELECT COUNT(*) FROM market_quotes WHERE ticker=?", (ticker,)).fetchone()[0]
    has_quotes = quote_count > 0
    
    # Analyze each missing KPI
    for kpi in missing_kpis:
        cause = []
        
        if kpi == 'pe_ratio':
            if not available_base.get('net_income') or not available_base.get('shares_outstanding'):
                cause.append("Missing net_income or shares_outstanding")
            if not has_quotes:
                cause.append("Missing market quotes")
                
        elif kpi == 'ev_ebitda':
            if not available_base.get('operating_income') or not available_base.get('depreciation_and_amortization'):
                cause.append("Missing operating_income or depreciation")
            if not has_quotes:
                cause.append("Missing market quotes")
                
        elif kpi == 'debt_to_equity':
            if not available_base.get('long_term_debt') or not available_base.get('shareholders_equity'):
                cause.append("Missing debt or equity data")
                
        elif kpi == 'dividend_yield':
            if not has_quotes:
                cause.append("Missing market quotes")
            # Note: dividend_yield can be 0% if no dividends paid
                
        causes[kpi] = cause if cause else ["Unknown cause"]
    
    con.close()
    return causes


def main():
    """Main function to analyze and report on KPI coverage."""
    settings = load_settings()
    db_path = settings.database_path
    
    print("=== KPI COVERAGE IMPROVEMENT ANALYSIS ===")
    
    # Analyze missing KPIs
    missing_analysis = analyze_missing_kpis(db_path)
    
    print(f"Found {len(missing_analysis)} tickers with missing KPIs")
    
    # Show worst offenders
    worst_tickers = sorted(missing_analysis.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    
    print(f"\n=== TOP 10 TICKERS WITH MOST MISSING KPIs ===")
    for ticker, missing_kpis in worst_tickers:
        print(f"{ticker:6}: Missing {len(missing_kpis):2d} KPIs - {', '.join(missing_kpis[:5])}{'...' if len(missing_kpis) > 5 else ''}")
    
    # Analyze root causes for a few examples
    print(f"\n=== ROOT CAUSE ANALYSIS (Sample) ===")
    for ticker, missing_kpis in worst_tickers[:3]:
        print(f"\n{ticker} missing KPIs:")
        causes = identify_root_causes(db_path, ticker, missing_kpis)
        for kpi, cause_list in causes.items():
            print(f"  {kpi}: {', '.join(cause_list)}")
    
    # Refresh metrics to apply improvements
    print(f"\n=== REFRESHING METRICS ===")
    engine = AnalyticsEngine(settings)
    engine.refresh_metrics(force=True)
    print("Metrics refreshed with improved calculation logic")
    
    # Show improvement summary
    print(f"\n=== IMPROVEMENT SUMMARY ===")
    key_kpis = ['debt_to_equity', 'ev_ebitda', 'peg_ratio', 'ebitda', 'dividend_yield']
    
    con = sqlite3.connect(db_path)
    total_tickers = con.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts").fetchone()[0]
    
    for kpi in key_kpis:
        count = con.execute("""
        SELECT COUNT(DISTINCT ticker) FROM metric_snapshots 
        WHERE metric=? AND value IS NOT NULL
        """, (kpi,)).fetchone()[0]
        percentage = (count / total_tickers) * 100
        print(f"{kpi:15}: {count:3d}/{total_tickers} ({percentage:5.1f}%)")
    
    con.close()


if __name__ == "__main__":
    main()
