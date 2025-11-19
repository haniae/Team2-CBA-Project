"""Debug why company name recognition is low."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import load_aliases, normalize_alias, resolve_tickers_freeform

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

def main():
    """Debug company name recognition."""
    print("=" * 80)
    print("Debugging Company Name Recognition")
    print("=" * 80)
    
    # Load data
    aliases = load_aliases()
    name_map = load_ticker_names()
    
    # Test a few examples
    test_cases = [
        ("AA", "Alcoa Corp"),
        ("AAPL", "Apple Inc."),
        ("MSFT", "Microsoft Corporation"),
        ("ABT", "Abbott Laboratories"),
        ("ACGL", "Arch Capital Group Ltd."),
    ]
    
    print("\nTesting specific examples:\n")
    
    for ticker, company_name in test_cases:
        print(f"Ticker: {ticker}")
        print(f"Company Name: {company_name}")
        
        # Show aliases
        if ticker in aliases:
            print(f"Generated aliases: {list(aliases[ticker])[:10]}")
        else:
            print("No aliases found!")
        
        # Test queries
        queries = [
            f"What is {company_name}'s revenue?",
            f"Show me {company_name} revenue",
            f"{company_name} revenue",
        ]
        
        print("Query tests:")
        for query in queries:
            matches, warnings = resolve_tickers_freeform(query)
            found = [m.get("ticker") for m in matches]
            normalized = normalize_alias(company_name.lower())
            print(f"  '{query[:50]}...' -> Found: {found}, Normalized: '{normalized}'")
        
        print()
    
    # Check normalization
    print("\nNormalization examples:")
    examples = [
        "Alcoa Corp",
        "Abbott Laboratories",
        "Arch Capital Group Ltd.",
        "Apple Inc.",
        "Microsoft Corporation",
    ]
    
    for name in examples:
        normalized = normalize_alias(name.lower())
        print(f"  '{name}' -> '{normalized}'")

if __name__ == "__main__":
    main()

