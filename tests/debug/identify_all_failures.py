"""Identify all failing company names for manual overrides."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, _load_name_map

def find_all_failures():
    """Find all failing company names."""
    tickers = _load_universe()
    name_map = _load_name_map()
    
    failures = []
    
    for ticker in tickers:
        if ticker not in name_map:
            continue
        
        company_name = name_map[ticker]
        query = f"What is {company_name}'s revenue?"
        
        matches, warnings = resolve_tickers_freeform(query)
        found_tickers = [m.get("ticker") for m in matches]
        
        if ticker not in found_tickers:
            failures.append((ticker, company_name))
    
    return failures

if __name__ == "__main__":
    failures = find_all_failures()
    print(f"Found {len(failures)} failures")
    print("\nManual overrides needed:")
    for ticker, name in failures:
        # Generate common variations
        name_lower = name.lower()
        # Remove common suffixes
        base_name = re.sub(r'\s+(inc|incorporated|corp|corporation|ltd|company|co|group|holdings).*$', '', name_lower, flags=re.IGNORECASE)
        base_name = base_name.strip()
        
        print(f'    "{base_name}": "{ticker}",')
        # Also add full name variations
        if base_name != name_lower:
            print(f'    "{name_lower}": "{ticker}",')

