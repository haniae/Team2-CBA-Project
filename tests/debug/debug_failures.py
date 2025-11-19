"""Debug why certain tickers and company names are failing."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, load_aliases, normalize_alias
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def load_ticker_names():
    """Load company names."""
    names_path = Path(__file__).parent / "docs" / "guides" / "ticker_names.md"
    if not names_path.exists():
        return {}
    
    name_map = {}
    pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z0-9.-]+)\)")
    
    with open(names_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                ticker = match.group("ticker").upper()
                name = match.group("name").strip()
                name_map[ticker] = name
    
    return name_map

def test_failing_tickers():
    """Test the failing ticker symbols."""
    print("=" * 80)
    print("Testing Failing Ticker Symbols: AN, DO, ON")
    print("=" * 80)
    
    failing_tickers = ["AN", "DO", "ON"]
    tickers = _load_universe()
    aliases = load_aliases()
    
    for ticker in failing_tickers:
        print(f"\nTicker: {ticker}")
        print(f"In universe: {ticker in tickers}")
        print(f"Has aliases: {ticker in aliases}")
        if ticker in aliases:
            print(f"Aliases: {list(aliases[ticker])}")
        
        # Test queries
        queries = [
            f"What is {ticker}'s revenue?",
            f"Show me {ticker} revenue",
            f"{ticker} revenue",
        ]
        
        for query in queries:
            matches, warnings = resolve_tickers_freeform(query)
            found = [m.get("ticker") for m in matches]
            print(f"  Query: '{query}' -> Found: {found}")
            if warnings:
                print(f"    Warnings: {warnings}")

def find_failing_company_names():
    """Find which company names are failing."""
    print("\n" + "=" * 80)
    print("Finding Failing Company Names")
    print("=" * 80)
    
    tickers = _load_universe()
    name_map = load_ticker_names()
    aliases = load_aliases()
    
    failures = []
    tested = 0
    
    print("\nTesting company names...")
    print("Progress: ", end="", flush=True)
    
    for ticker in list(tickers)[:200]:  # Test first 200 to find patterns
        if ticker not in name_map:
            continue
        
        tested += 1
        if tested % 20 == 0:
            print(".", end="", flush=True)
        
        company_name = name_map[ticker]
        query = f"What is {company_name}'s revenue?"
        
        matches, warnings = resolve_tickers_freeform(query)
        found = [m.get("ticker") for m in matches]
        
        if ticker not in found:
            normalized = normalize_alias(company_name.lower())
            failures.append({
                "ticker": ticker,
                "name": company_name,
                "normalized": normalized,
                "aliases": list(aliases.get(ticker, []))[:5],
                "found": found
            })
    
    print(f"\n\nFound {len(failures)} failures in first 200:")
    for i, fail in enumerate(failures[:20]):
        print(f"\n{i+1}. {fail['ticker']}: {fail['name']}")
        print(f"   Normalized: '{fail['normalized']}'")
        print(f"   Aliases: {fail['aliases']}")
        print(f"   Found instead: {fail['found']}")

if __name__ == "__main__":
    test_failing_tickers()
    find_failing_company_names()

