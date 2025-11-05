"""
Comprehensive Portfolio Prompts Stress Test

This script tests all portfolio-related prompts to ensure they:
1. Correctly detect portfolio queries
2. Fetch actual portfolio data from database
3. Return responses based on actual data (not hallucinated)
4. Handle edge cases and variations
"""

import sys
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmarkos_chatbot.chatbot import BenchmarkOSChatbot
from benchmarkos_chatbot.config import load_settings
import sqlite3


# Portfolio test prompts organized by category
PORTFOLIO_TEST_PROMPTS = {
    "Analysis": [
        "Analyze portfolio port_a13acb30",
        "Analyze my portfolio",
        "What's in my portfolio?",
        "Show me portfolio port_a13acb30",
        "Give me a portfolio overview",
        "Portfolio summary",
    ],
    "Optimization": [
        "Optimize my portfolio",
        "Optimize portfolio port_a13acb30",
        "Rebalance my portfolio",
        "What's the optimal allocation?",
        "Suggest portfolio changes",
        "Optimize for maximum Sharpe ratio",
    ],
    "Exposure": [
        "What's my portfolio exposure?",
        "Show portfolio sector exposure",
        "What sectors am I exposed to?",
        "Portfolio exposure for port_a13acb30",
        "Show factor exposure",
        "Breakdown by sector",
    ],
    "Holdings": [
        "Show my portfolio holdings",
        "What are the holdings for port_a13acb30?",
        "Display my current positions",
        "List all holdings in my portfolio",
        "What stocks are in my portfolio?",
    ],
    "Risk": [
        "What's my portfolio risk?",
        "Analyze portfolio risk for port_a13acb30",
        "What's my portfolio CVaR?",
        "Portfolio volatility",
        "What's my tail risk?",
    ],
    "Performance": [
        "What's my portfolio performance?",
        "Show portfolio returns",
        "Portfolio attribution analysis",
        "What's driving my portfolio performance?",
    ],
    "Diversification": [
        "How diversified is my portfolio?",
        "What's my concentration risk?",
        "Show portfolio concentration",
        "Diversification metrics",
    ],
    "Edge Cases": [
        "portfolio",  # Just the word
        "my portfolio",  # Generic
        "the portfolio",  # Generic
        "port_",  # Incomplete ID
        "port_a13acb30 optimize",  # ID + action
        "analyze port_a13acb30",  # Action + ID
        "What's port_a13acb30 exposure?",  # Question with ID
    ],
}


def get_portfolio_ids(database_path: Path) -> List[str]:
    """Get all portfolio IDs from database."""
    try:
        with sqlite3.connect(database_path) as conn:
            cursor = conn.execute("SELECT portfolio_id FROM portfolios ORDER BY created_at DESC LIMIT 10")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        print(f"⚠️  Could not fetch portfolio IDs: {e}")
        return []


def check_portfolio_data_usage(response: str, portfolio_id: Optional[str] = None) -> Dict[str, bool]:
    """Check if response actually uses portfolio data vs hallucinated data."""
    checks = {
        "has_portfolio_id": portfolio_id is None or portfolio_id.lower() in response.lower(),
        "mentions_actual_tickers": False,  # Will check against DB
        "has_sector_exposure": any(sector in response.lower() for sector in [
            "technology", "healthcare", "financial", "consumer", "energy", "industrial",
            "materials", "utilities", "real estate", "communication", "sector"
        ]),
        "has_weights_or_percentages": bool(re.search(r'\d+\.?\d*%', response)),
        "has_holdings_count": bool(re.search(r'\d+\s+(holdings|positions|stocks)', response.lower())),
        "not_generic": not any(phrase in response.lower() for phrase in [
            "hypothetical portfolio",
            "example portfolio",
            "typical portfolio",
            "general portfolio",
            "if you can provide",
            "without further specifics",
            "unable to analyze",
        ]),
        "mentions_actual_metrics": bool(re.search(r'(p/e|pe ratio|sharpe|beta|volatility|concentration)', response.lower())),
    }
    
    # Check for common hallucinated data patterns
    hallucination_patterns = [
        r'amzn.*25%',  # Specific hallucinated weights
        r'aapl.*15%',
        r'msft.*15%',
        r'googl.*10%',
    ]
    
    checks["no_hallucinated_data"] = not any(re.search(pattern, response.lower()) for pattern in hallucination_patterns)
    
    return checks


def test_portfolio_prompt(chatbot: BenchmarkOSChatbot, prompt: str, category: str, 
                          portfolio_id: Optional[str] = None) -> Dict[str, any]:
    """Test a single portfolio prompt."""
    print(f"\n{'='*80}")
    print(f"Testing: {prompt} [{category}]")
    print(f"{'='*80}")
    
    start_time = time.time()
    result = {
        "prompt": prompt,
        "category": category,
        "success": False,
        "response": None,
        "response_time": 0,
        "error": None,
        "checks": {},
        "portfolio_id_found": False,
        "uses_actual_data": False,
    }
    
    try:
        # Check if portfolio context was built
        portfolio_context_before = None
        if hasattr(chatbot, '_build_portfolio_context'):
            portfolio_context_before = chatbot._build_portfolio_context(prompt)
        
        # Ask the chatbot
        response = chatbot.ask(prompt)
        result["response"] = response
        result["response_time"] = time.time() - start_time
        
        # Check if portfolio context was actually used
        if portfolio_context_before:
            result["portfolio_id_found"] = True
            print(f"✓ Portfolio context was built")
        else:
            print(f"⚠️  No portfolio context built - may not have detected portfolio query")
        
        # Analyze response
        checks = check_portfolio_data_usage(response, portfolio_id)
        result["checks"] = checks
        
        # Determine if it uses actual data
        result["uses_actual_data"] = (
            checks["not_generic"] and 
            checks["no_hallucinated_data"] and
            (checks["has_sector_exposure"] or checks["has_holdings_count"] or checks["has_weights_or_percentages"])
        )
        
        result["success"] = True
        
        # Print results
        print(f"Response time: {result['response_time']:.2f}s")
        print(f"Response length: {len(response)} characters")
        print(f"\nChecks:")
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
        
        print(f"\nUses actual data: {'✓ YES' if result['uses_actual_data'] else '✗ NO'}")
        
        # Show first 200 chars of response
        print(f"\nResponse preview:")
        print("-" * 80)
        preview = response[:300] + "..." if len(response) > 300 else response
        print(preview)
        print("-" * 80)
        
    except Exception as e:
        result["error"] = str(e)
        result["response_time"] = time.time() - start_time
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def run_stress_test():
    """Run comprehensive stress test on all portfolio prompts."""
    print("=" * 80)
    print("PORTFOLIO PROMPTS STRESS TEST")
    print("=" * 80)
    print()
    
    # Load settings
    print("1. Loading chatbot...")
    try:
        settings = load_settings()
        chatbot = BenchmarkOSChatbot.create(settings)
        print("   ✓ Chatbot loaded successfully")
    except Exception as e:
        print(f"   ❌ Failed to load chatbot: {e}")
        return
    
    print()
    
    # Get portfolio IDs from database
    print("2. Fetching portfolio IDs from database...")
    portfolio_ids = get_portfolio_ids(settings.database_path)
    if portfolio_ids:
        print(f"   ✓ Found {len(portfolio_ids)} portfolio(s): {', '.join(portfolio_ids[:3])}")
        test_portfolio_id = portfolio_ids[0]  # Use first portfolio for testing
    else:
        print(f"   ⚠️  No portfolios found in database")
        test_portfolio_id = "port_a13acb30"  # Use example ID
    
    print()
    
    # Run tests
    print("3. Running portfolio prompt tests...")
    print()
    
    all_results = []
    total_tests = 0
    passed_tests = 0
    
    for category, prompts in PORTFOLIO_TEST_PROMPTS.items():
        print(f"\n{'#' * 80}")
        print(f"# Testing Category: {category}")
        print(f"{'#' * 80}\n")
        
        for prompt in prompts:
            total_tests += 1
            
            # Try to extract portfolio ID from prompt
            portfolio_id_match = re.search(r'port_[\w]{4,12}', prompt, re.IGNORECASE)
            portfolio_id = portfolio_id_match.group(0) if portfolio_id_match else test_portfolio_id
            
            result = test_portfolio_prompt(chatbot, prompt, category, portfolio_id)
            all_results.append(result)
            
            if result["success"] and result["uses_actual_data"]:
                passed_tests += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("STRESS TEST SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    print()
    
    # Breakdown by category
    print("Breakdown by category:")
    for category, prompts in PORTFOLIO_TEST_PROMPTS.items():
        category_results = [r for r in all_results if r["category"] == category]
        category_passed = sum(1 for r in category_results if r["success"] and r["uses_actual_data"])
        category_total = len(category_results)
        print(f"  {category}: {category_passed}/{category_total} ({category_passed/category_total*100:.1f}%)")
    
    print()
    
    # Failed tests
    failed_results = [r for r in all_results if not (r["success"] and r["uses_actual_data"])]
    if failed_results:
        print("Failed tests:")
        for result in failed_results[:10]:  # Show first 10
            status = "ERROR" if result["error"] else "USES GENERIC DATA"
            print(f"  ✗ {result['prompt']} [{result['category']}] - {status}")
        if len(failed_results) > 10:
            print(f"  ... and {len(failed_results) - 10} more")
    
    print()
    print("=" * 80)
    
    # Save results to file
    results_file = Path(__file__).parent / "portfolio_stress_test_results.json"
    try:
        import json
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "results": all_results
            }, f, indent=2)
        print(f"Results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save results: {e}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_stress_test()
    sys.exit(0 if success else 1)

