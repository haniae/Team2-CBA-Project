"""Debug why bookng isn't matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform, load_aliases, normalize_alias, _base_tokens

query = "What is Bookng Holdings revenue?"
print(f"Query: {query}")

# Check aliases
alias_map = load_aliases()
print(f"\nBKNG aliases in alias_map: {sorted(alias_map.get('BKNG', set()))}")

# Check lookup
from finanlyzeos_chatbot.parsing.alias_builder import _ensure_lookup_loaded
alias_map, lookup, ticker_set = _ensure_lookup_loaded()
print(f"\n'bookng' in lookup: {'bookng' in lookup}")
if 'bookng' in lookup:
    print(f"  -> {lookup['bookng']}")
print(f"'bookng holdings' in lookup: {'bookng holdings' in lookup}")
if 'bookng holdings' in lookup:
    print(f"  -> {lookup['bookng holdings']}")

# Check normalization
tokens = _base_tokens(query.lower())
print(f"\nTokens: {tokens}")
for token in tokens:
    norm = normalize_alias(token)
    print(f"  '{token}' -> '{norm}'")

# Check phrase normalization
phrase = "bookng holdings"
norm_phrase = normalize_alias(phrase)
print(f"\nPhrase '{phrase}' normalized: '{norm_phrase}'")

# Try resolution
matches, warnings = resolve_tickers_freeform(query)
print(f"\nMatches: {matches}")
print(f"Warnings: {warnings}")

