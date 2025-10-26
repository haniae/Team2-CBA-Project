"""
Test script to check:
1. How many companies are in the database
2. If the chatbot can handle prompts for all of them
3. Data quality across different companies
"""

import sqlite3
from pathlib import Path
from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
import random


def check_company_coverage():
    """Check what companies are available and test coverage."""
    
    print("=" * 80)
    print("COMPANY COVERAGE & PROMPT HANDLING TEST")
    print("=" * 80)
    print()
    
    # Load settings
    settings = load_settings()
    db_path = settings.database_path
    
    if not Path(db_path).exists():
        print(f"[ERROR] Database not found at: {db_path}")
        return
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("1. CHECKING DATABASE CONTENT:")
    print("-" * 80)
    
    # Check ticker_aliases table (all known companies)
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM ticker_aliases")
    total_tickers = cursor.fetchone()[0]
    print(f"   Total unique tickers in catalog: {total_tickers}")
    
    # Check which have actual financial data
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM financial_facts")
    tickers_with_data = cursor.fetchone()[0]
    print(f"   Tickers with financial data: {tickers_with_data}")
    
    # Check metric_snapshots (computed metrics)
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM metric_snapshots")
    tickers_with_metrics = cursor.fetchone()[0]
    print(f"   Tickers with computed metrics: {tickers_with_metrics}")
    
    # Get sample of companies with data
    cursor.execute("""
        SELECT DISTINCT ticker, company_name 
        FROM ticker_aliases 
        WHERE ticker IN (SELECT DISTINCT ticker FROM financial_facts)
        ORDER BY ticker
        LIMIT 20
    """)
    sample_companies = cursor.fetchall()
    
    print()
    print("2. SAMPLE COMPANIES WITH DATA:")
    print("-" * 80)
    for ticker, name in sample_companies[:10]:
        print(f"   {ticker:6s} - {name}")
    if len(sample_companies) > 10:
        print(f"   ... and {len(sample_companies) - 10} more")
    
    # Check S&P 500 coverage
    sp500_common = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 
                    'UNH', 'JNJ', 'JPM', 'V', 'XOM', 'WMT', 'PG', 'MA', 'HD', 'CVX', 
                    'LLY', 'ABBV', 'MRK', 'KO', 'PEP', 'COST', 'AVGO', 'TMO', 'CSCO']
    
    print()
    print("3. S&P 500 TOP COMPANIES CHECK:")
    print("-" * 80)
    
    placeholders = ','.join(['?' for _ in sp500_common])
    cursor.execute(f"""
        SELECT ticker FROM ticker_aliases 
        WHERE ticker IN ({placeholders})
    """, sp500_common)
    
    available_sp500 = [row[0] for row in cursor.fetchall()]
    print(f"   Checked {len(sp500_common)} major S&P 500 tickers")
    print(f"   Available: {len(available_sp500)} ({len(available_sp500)/len(sp500_common)*100:.1f}%)")
    
    missing = set(sp500_common) - set(available_sp500)
    if missing:
        print(f"   Missing: {', '.join(sorted(missing))}")
    
    # Test actual prompts
    print()
    print("4. TESTING PROMPTS WITH DIFFERENT COMPANIES:")
    print("-" * 80)
    print()
    
    chatbot = BenchmarkOSChatbot.create(settings)
    
    # Test with 5 random companies
    test_tickers = random.sample(available_sp500[:15], min(5, len(available_sp500[:15])))
    
    prompts = [
        ("revenue", "What is {}'s revenue?"),
        ("margin", "What is {}'s EBITDA margin?"),
        ("comparison", "Is {} profitable?"),
    ]
    
    results = {
        "success": 0,
        "has_data": 0,
        "chatgpt_style": 0,
        "has_sources": 0,
        "total": 0
    }
    
    for ticker in test_tickers:
        print(f"\nTesting with {ticker}:")
        print("-" * 40)
        
        for prompt_type, template in prompts[:1]:  # Just test one prompt per ticker
            question = template.format(ticker)
            print(f"  Q: {question}")
            
            try:
                response = chatbot.ask(question)
                results["total"] += 1
                
                # Check if response has data
                if ticker in response.upper() and any(word in response.lower() for word in ['billion', 'million', '%', 'revenue', 'margin']):
                    results["has_data"] += 1
                    status = "[HAS DATA]"
                else:
                    status = "[NO DATA]"
                
                # Check if ChatGPT-style
                if "**" in response and len(response.split('\n\n')) >= 2:
                    results["chatgpt_style"] += 1
                    style = "[CHATGPT-STYLE]"
                else:
                    style = "[STRUCTURED]"
                
                # Check if has sources
                if "sec.gov" in response.lower() or "](" in response:
                    results["has_sources"] += 1
                    sources = "[HAS SOURCES]"
                else:
                    sources = "[NO SOURCES]"
                
                if results["has_data"] and results["chatgpt_style"]:
                    results["success"] += 1
                
                print(f"     {status} {style} {sources}")
                print(f"     Response length: {len(response)} chars")
                
            except Exception as e:
                print(f"     [ERROR]: {e}")
                results["total"] += 1
        
        print()
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print()
    print(f"Database Coverage:")
    print(f"  - Total tickers in catalog: {total_tickers}")
    print(f"  - Tickers with financial data: {tickers_with_data}")
    print(f"  - S&P 500 major tickers available: {len(available_sp500)}/{len(sp500_common)}")
    print()
    print(f"Prompt Test Results (from {results['total']} tests):")
    print(f"  - Successfully answered: {results['success']}/{results['total']} ({results['success']/max(results['total'],1)*100:.1f}%)")
    print(f"  - Had relevant data: {results['has_data']}/{results['total']} ({results['has_data']/max(results['total'],1)*100:.1f}%)")
    print(f"  - ChatGPT-style format: {results['chatgpt_style']}/{results['total']} ({results['chatgpt_style']/max(results['total'],1)*100:.1f}%)")
    print(f"  - Included SEC sources: {results['has_sources']}/{results['total']} ({results['has_sources']/max(results['total'],1)*100:.1f}%)")
    
    print()
    if tickers_with_data >= 450:
        print("[SUCCESS] You have comprehensive S&P 500 coverage!")
        print("The chatbot can handle prompts for most major companies.")
    elif tickers_with_data >= 100:
        print("[GOOD] You have substantial company coverage.")
        print("The chatbot works for many companies, but may need more data ingestion.")
    else:
        print("[LIMITED] Limited company data available.")
        print("You may need to run data ingestion for more companies.")
        print()
        print("To ingest S&P 500 data, run:")
        print("  python ingest_20years_sp500.py")
    
    print()
    print("To ingest specific companies:")
    print("  python -m benchmarkos_chatbot.cli ingest <TICKER>")
    
    conn.close()


if __name__ == "__main__":
    check_company_coverage()

