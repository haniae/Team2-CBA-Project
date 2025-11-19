"""Get complete list of all failures for fixing."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import _load_universe, resolve_tickers_freeform, _load_name_map

def get_all_company_failures():
    """Get all failing company names."""
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
    failures = get_all_company_failures()
    print(f"Total failures: {len(failures)}")
    print("\nAll failures:")
    for ticker, name in failures:
        # Generate variations for manual overrides
        name_lower = name.lower()
        base_name = re.sub(r'\s+(inc|incorporated|corp|corporation|ltd|company|co|group|holdings).*$', '', name_lower, flags=re.IGNORECASE)
        base_name = base_name.strip()
        
        print(f'    "{base_name}": "{ticker}",')
        if base_name != name_lower:
            print(f'    "{name_lower}": "{ticker}",')

