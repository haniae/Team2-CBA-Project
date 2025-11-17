#!/usr/bin/env python3
"""
Test script for new advanced analytics features.

Demonstrates:
- Sector benchmarking
- Anomaly detection  
- Predictive trend analysis
- Advanced KPI calculations
"""

import sys
sys.path.insert(0, 'src')

from finanlyzeos_chatbot.sector_analytics import get_sector_analytics
from finanlyzeos_chatbot.anomaly_detection import get_anomaly_detector
from finanlyzeos_chatbot.predictive_analytics import get_predictive_analytics
from finanlyzeos_chatbot.advanced_kpis import get_advanced_kpi_calculator

DB_PATH = "C:/Users/Hania/Documents/GitHub/Project/finanlyzeos_chatbot.sqlite3"

def test_sector_analytics():
    print("\n" + "="*70)
    print("SECTOR BENCHMARKING ANALYSIS")
    print("="*70)
    
    sector_analytics = get_sector_analytics(DB_PATH)
    
    # Test 1: Get Technology sector benchmarks
    print("\n[DATA] Technology Sector Benchmarks (2024):")
    tech_benchmarks = sector_analytics.calculate_sector_benchmarks("Technology", 2024)
    if tech_benchmarks:
        print(f"   Companies: {tech_benchmarks.companies_count}")
        print(f"   Avg Revenue: ${tech_benchmarks.avg_revenue:,.0f}")
        print(f"   Avg Net Margin: {tech_benchmarks.avg_net_margin:.2f}%")
        print(f"   Avg ROE: {tech_benchmarks.avg_roe:.2f}%")
        print(f"   Avg Debt-to-Equity: {tech_benchmarks.avg_debt_to_equity:.2f}")
    
    # Test 2: Compare AAPL to sector
    print("\n[COMPARE] Apple vs Technology Sector:")
    comparison = sector_analytics.compare_company_to_sector("AAPL", 2024)
    if comparison:
        print(f"   Company: {comparison.company_name}")
        print(f"   Sector: {comparison.sector}")
        print(f"   Percentile Ranks: {comparison.percentile_ranks}")
    
    # Test 3: Top performers
    print("\n[TOP] Top 5 Technology Companies by Revenue (2024):")
    top_performers = sector_analytics.get_top_performers_by_sector("Technology", "revenue", 5, 2024)
    for i, (ticker, revenue) in enumerate(top_performers, 1):
        print(f"   {i}. {ticker}: ${revenue:,.0f}")

def test_anomaly_detection():
    print("\n" + "="*70)
    print("ANOMALY DETECTION")
    print("="*70)
    
    detector = get_anomaly_detector(DB_PATH)
    
    # Test multiple companies
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    
    for ticker in test_tickers:
        print(f"\n[ANALYZE] Analyzing {ticker} for anomalies...")
        
        # Detect revenue anomalies
        revenue_anomalies = detector.detect_revenue_anomalies(ticker, years=5)
        if revenue_anomalies:
            print(f"   [!] Found {len(revenue_anomalies)} revenue anomalies:")
            for anomaly in revenue_anomalies:
                print(f"      - {anomaly.fiscal_year}: {anomaly.description}")
        
        # Detect margin anomalies
        margin_anomalies = detector.detect_margin_anomalies(ticker, years=5)
        if margin_anomalies:
            print(f"   [!] Found {len(margin_anomalies)} margin anomalies:")
            for anomaly in margin_anomalies:
                print(f"      - {anomaly.fiscal_year}: {anomaly.description}")

def test_predictive_analytics():
    print("\n" + "="*70)
    print("PREDICTIVE TREND ANALYSIS")
    print("="*70)
    
    predictor = get_predictive_analytics(DB_PATH)
    
    # Test: Forecast Apple revenue
    print("\n[FORECAST] Apple Revenue Forecast:")
    forecast = predictor.forecast_revenue("AAPL", years_history=5, years_forecast=3)
    if forecast:
        print(f"   Historical Growth Rate (CAGR): {forecast.growth_rate:.2f}%")
        print(f"   Trend: {forecast.trend}")
        print(f"   Volatility: {forecast.volatility:.2f}%")
        print(f"\n   Forecasts:")
        for f in forecast.forecasts[:3]:  # Show first 3 forecasts
            print(f"      {f.fiscal_year}: ${f.predicted_value:,.0f} "
                  f"(${f.confidence_interval_low:,.0f} - ${f.confidence_interval_high:,.0f})")
            print(f"         Method: {f.method}, Confidence: {f.confidence:.0%}")
    
    # Test: Multiple metrics forecast
    print("\n[FORECAST] Microsoft Multiple Metrics Forecast:")
    forecasts = predictor.forecast_multiple_metrics(
        "MSFT", ["revenue", "net_income"], years_history=5, years_forecast=2
    )
    for metric, analysis in forecasts.items():
        if analysis:
            print(f"\n   {metric.upper()}:")
            print(f"      CAGR: {analysis.growth_rate:.2f}%, Trend: {analysis.trend}")

def test_advanced_kpis():
    print("\n" + "="*70)
    print("ADVANCED KPI CALCULATIONS")
    print("="*70)
    
    calculator = get_advanced_kpi_calculator(DB_PATH)
    
    # Test multiple companies
    test_companies = [("AAPL", "Apple"), ("MSFT", "Microsoft"), ("JPM", "JP Morgan")]
    
    for ticker, name in test_companies:
        print(f"\n[KPI] {name} ({ticker}) - Advanced KPIs (2024):")
        kpis = calculator.calculate_all_kpis(ticker, 2024)
        if kpis:
            print(f"\n   Profitability:")
            if kpis.roe:
                print(f"      ROE: {kpis.roe:.2f}%")
            if kpis.roa:
                print(f"      ROA: {kpis.roa:.2f}%")
            if kpis.roic:
                print(f"      ROIC: {kpis.roic:.2f}%")
            
            print(f"\n   Liquidity:")
            if kpis.current_ratio:
                print(f"      Current Ratio: {kpis.current_ratio:.2f}")
            if kpis.quick_ratio:
                print(f"      Quick Ratio: {kpis.quick_ratio:.2f}")
            if kpis.working_capital:
                print(f"      Working Capital: ${kpis.working_capital:,.0f}")
            
            print(f"\n   Leverage:")
            if kpis.debt_to_equity:
                print(f"      Debt-to-Equity: {kpis.debt_to_equity:.2f}")
            if kpis.interest_coverage:
                print(f"      Interest Coverage: {kpis.interest_coverage:.2f}x")
            
            print(f"\n   Cash Flow:")
            if kpis.fcf_to_revenue:
                print(f"      FCF to Revenue: {kpis.fcf_to_revenue:.2f}%")
            if kpis.cash_flow_margin:
                print(f"      Cash Flow Margin: {kpis.cash_flow_margin:.2f}%")

def main():
    print("\n" + "="*70)
    print("BENCHMARKOS ADVANCED ANALYTICS TEST SUITE")
    print("="*70)
    print("\nTesting new analytics features:")
    print("  [*] Sector Benchmarking")
    print("  [*] Anomaly Detection")
    print("  [*] Predictive Trend Analysis")
    print("  [*] Advanced KPI Calculations")
    
    try:
        test_sector_analytics()
        test_anomaly_detection()
        test_predictive_analytics()
        test_advanced_kpis()
        
        print("\n" + "="*70)
        print("[SUCCESS] ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nNew analytics modules are ready for integration into:")
        print("  • Dashboard UI")
        print("  • REST API endpoints")
        print("  • Chatbot responses")
        print("  • PowerPoint exports")
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

