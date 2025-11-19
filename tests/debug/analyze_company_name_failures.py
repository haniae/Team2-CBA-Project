"""Analyze which company names are failing and why."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, load_aliases, normalize_alias, _load_name_map

def find_all_failures():
    """Find all failing company names."""
    print("=" * 80)
    print("Analyzing Company Name Recognition Failures")
    print("=" * 80)
    
    tickers = _load_universe()
    name_map = _load_name_map()
    aliases = load_aliases()
    
    failures = []
    
    print(f"\nTesting {len([t for t in tickers if t in name_map])} companies with names...")
    print("Progress: ", end="", flush=True)
    
    for idx, ticker in enumerate(tickers):
        if ticker not in name_map:
            continue
        
        if idx % 200 == 0 and idx > 0:
            print(".", end="", flush=True)
        
        company_name = name_map[ticker]
        
        # Test different query formats
        queries = [
            f"What is {company_name}'s revenue?",
            f"Show me {company_name} revenue",
            f"{company_name} revenue",
        ]
        
        found = False
        for query in queries:
            matches, warnings = resolve_tickers_freeform(query)
            found_tickers = [m.get("ticker") for m in matches]
            
            if ticker in found_tickers:
                found = True
                break
        
        if not found:
            normalized = normalize_alias(company_name.lower())
            ticker_aliases = list(aliases.get(ticker, []))[:10]
            
            failures.append({
                "ticker": ticker,
                "name": company_name,
                "normalized": normalized,
                "aliases": ticker_aliases,
            })
    
    print(f"\n\nFound {len(failures)} failures out of {len([t for t in tickers if t in name_map])} companies")
    
    # Categorize failures
    categories = {
        "short_names": [],
        "common_words": [],
        "missing_aliases": [],
        "normalization_issues": [],
        "other": []
    }
    
    common_words = {"bill", "booking", "alpha", "bread", "aspen", "enact", "adtran", "amentum", "bj"}
    
    for fail in failures:
        name_lower = fail["name"].lower()
        normalized = fail["normalized"]
        
        if len(normalized) <= 3:
            categories["short_names"].append(fail)
        elif any(word in name_lower for word in common_words):
            categories["common_words"].append(fail)
        elif len(fail["aliases"]) <= 2:
            categories["missing_aliases"].append(fail)
        elif normalized != normalize_alias(name_lower):
            categories["normalization_issues"].append(fail)
        else:
            categories["other"].append(fail)
    
    print("\n" + "=" * 80)
    print("Failure Categories")
    print("=" * 80)
    for category, items in categories.items():
        print(f"\n{category}: {len(items)} failures")
        if items:
            print("  Examples:")
            for item in items[:5]:
                print(f"    {item['ticker']}: {item['name']} -> '{item['normalized']}'")
                print(f"      Aliases: {item['aliases'][:5]}")
    
    return failures, categories

if __name__ == "__main__":
    failures, categories = find_all_failures()
    
    print("\n" + "=" * 80)
    print("All Failures")
    print("=" * 80)
    for fail in failures[:20]:
        print(f"{fail['ticker']}: {fail['name']} -> '{fail['normalized']}'")
        print(f"  Aliases: {fail['aliases']}")

