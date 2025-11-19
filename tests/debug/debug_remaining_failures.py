"""Debug remaining failures to understand why they're not matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, _load_name_map, load_aliases, normalize_alias

def debug_failures():
    """Debug remaining failures."""
    tickers = _load_universe()
    name_map = _load_name_map()
    alias_map = load_aliases()
    
    failures = []
    
    for ticker in tickers:
        if ticker not in name_map:
            continue
        
        company_name = name_map[ticker]
        query = f"What is {company_name}'s revenue?"
        
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if ticker not in found_tickers:
            # Check what aliases exist for this ticker
            aliases = alias_map.get(ticker, set())
            normalized_name = normalize_alias(company_name)
            
            failures.append({
                'ticker': ticker,
                'name': company_name,
                'normalized': normalized_name,
                'aliases': sorted(aliases),
                'found': found_tickers,
                'warnings': warnings
            })
    
    # Show first 20 failures with details
    print(f"Total failures: {len(failures)}")
    print("\nFirst 20 failures:")
    for i, f in enumerate(failures[:20]):
        print(f"\n{i+1}. {f['ticker']}: {f['name']}")
        print(f"   Normalized: {f['normalized']}")
        print(f"   Aliases: {f['aliases'][:5]}")
        print(f"   Found: {f['found']}")

if __name__ == "__main__":
    debug_failures()

