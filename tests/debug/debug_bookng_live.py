"""Live debug script to understand why 'Bookng Holdings' is not being recognized."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform, normalize_alias, _MANUAL_OVERRIDES, _base_tokens
from src.finanlyzeos_chatbot.parsing.alias_builder import load_aliases

def debug_bookng():
    text = "What is Bookng Holdings revenue?"
    print(f"Original text: {text}")
    print()
    
    # Load aliases to ensure lookup is loaded
    alias_map, lookup, ticker_set = load_aliases()
    print(f"Ticker set has BKNG: {'BKNG' in ticker_set}")
    print(f"Manual override 'bookng': {_MANUAL_OVERRIDES.get('bookng')}")
    print(f"Manual override 'bookng holdings': {_MANUAL_OVERRIDES.get('bookng holdings')}")
    print()
    
    # Check tokenization
    tokens = _base_tokens(text.lower())
    print(f"Tokens after _base_tokens: {tokens}")
    print()
    
    # Check normalization
    for token in tokens:
        norm = normalize_alias(token)
        print(f"Token: '{token}' -> normalized: '{norm}'")
        print(f"  In manual overrides: {norm in _MANUAL_OVERRIDES if norm else False}")
        print(f"  In lookup: {norm in lookup if norm else False}")
    print()
    
    # Check phrase normalization
    phrase = "bookng holdings"
    norm_phrase = normalize_alias(phrase)
    print(f"Phrase: '{phrase}' -> normalized: '{norm_phrase}'")
    print(f"  In manual overrides: {norm_phrase in _MANUAL_OVERRIDES if norm_phrase else False}")
    print(f"  In lookup: {norm_phrase in lookup if norm_phrase else False}")
    print()
    
    # Try resolution
    result, warnings = resolve_tickers_freeform(text)
    print(f"Result: {result}")
    print(f"Warnings: {warnings}")

if __name__ == "__main__":
    debug_bookng()

