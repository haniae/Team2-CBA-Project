"""Debug script to understand why 'Bookng Holdings' is not being recognized."""

from src.finanlyzeos_chatbot.parsing.alias_builder import resolve_tickers_freeform, normalize_alias, _MANUAL_OVERRIDES
from src.finanlyzeos_chatbot.parsing.alias_builder import _base_tokens

def debug_bookng():
    text = "What is Bookng Holdings revenue?"
    print(f"Original text: {text}")
    print()
    
    # Check tokenization
    tokens = _base_tokens(text.lower())
    print(f"Tokens after _base_tokens: {tokens}")
    print()
    
    # Check normalization
    for token in tokens:
        norm = normalize_alias(token)
        print(f"Token: '{token}' -> normalized: '{norm}'")
    print()
    
    # Check manual overrides
    print("Manual overrides check:")
    for token in tokens:
        if token in _MANUAL_OVERRIDES:
            print(f"  '{token}' -> {_MANUAL_OVERRIDES[token]}")
        norm = normalize_alias(token)
        if norm and norm in _MANUAL_OVERRIDES:
            print(f"  '{token}' (normalized to '{norm}') -> {_MANUAL_OVERRIDES[norm]}")
    print()
    
    # Check phrase normalization
    phrase = "bookng holdings"
    norm_phrase = normalize_alias(phrase)
    print(f"Phrase: '{phrase}' -> normalized: '{norm_phrase}'")
    if norm_phrase in _MANUAL_OVERRIDES:
        print(f"  '{norm_phrase}' -> {_MANUAL_OVERRIDES[norm_phrase]}")
    print()
    
    # Try resolution
    result, warnings = resolve_tickers_freeform(text)
    print(f"Result: {result}")
    print(f"Warnings: {warnings}")
    print()
    
    # Also check what happens with just "bookng"
    print("Testing just 'bookng':")
    result2, warnings2 = resolve_tickers_freeform("bookng")
    print(f"Result: {result2}")
    print(f"Warnings: {warnings2}")

if __name__ == "__main__":
    debug_bookng()

