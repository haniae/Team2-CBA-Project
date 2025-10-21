#!/usr/bin/env python3
"""Enhanced Ticker Resolver with improved pattern matching, fuzzy matching, and priority system."""

import re
import difflib
import sys
import os
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from benchmarkos_chatbot.parsing.alias_builder import (
    load_aliases,
    normalize_alias,
    _base_tokens,
    _ensure_lookup_loaded
)

class EnhancedTickerResolver:
    """Enhanced ticker resolver with improved pattern matching and fuzzy matching."""
    
    def __init__(self):
        self.alias_map, self.lookup, self.ticker_set = _ensure_lookup_loaded()
        
        # Enhanced patterns for better ticker detection
        self.enhanced_patterns = [
            re.compile(r"\b([A-Za-z0-9]{1,5})(?:\.[A-Za-z0-9]{1,2})?\b"),  # Standard tickers
            re.compile(r"\b\d+[A-Za-z]+\b"),  # Numbers + letters (3M, 1A, etc.)
            re.compile(r"\b[A-Za-z]+&\w+\b"),  # & symbols (AT&T)
            re.compile(r"\b[A-Za-z]+\s+&\s+[A-Za-z]+\b"),  # Spaced & symbols
            re.compile(r"\b[A-Za-z]+-[A-Za-z]+\b"),  # Hyphenated tickers (BRK-B)
        ]
        
        # Priority-based manual overrides
        self.manual_overrides_priority = {
            # High priority (company-specific)
            "alphabet": {"ticker": "GOOGL", "priority": 1, "context": "company"},
            "alphabet inc": {"ticker": "GOOGL", "priority": 1, "context": "company"},
            "alphabet class a": {"ticker": "GOOGL", "priority": 1, "context": "company"},
            "alphabet class c": {"ticker": "GOOG", "priority": 1, "context": "company"},
            "google": {"ticker": "GOOGL", "priority": 1, "context": "brand"},
            "googl": {"ticker": "GOOGL", "priority": 1, "context": "ticker"},
            "goog": {"ticker": "GOOG", "priority": 1, "context": "ticker"},
            
            "meta": {"ticker": "META", "priority": 1, "context": "company"},
            "facebook": {"ticker": "META", "priority": 1, "context": "legacy"},
            
            "berkshire hathaway": {"ticker": "BRK-B", "priority": 1, "context": "company"},
            "berkshire class b": {"ticker": "BRK-B", "priority": 1, "context": "class"},
            "berkshire class a": {"ticker": "BRK-A", "priority": 1, "context": "class"},
            "berkshire b": {"ticker": "BRK-B", "priority": 2, "context": "abbrev"},
            "berkshire a": {"ticker": "BRK-A", "priority": 2, "context": "abbrev"},
            
            "att": {"ticker": "T", "priority": 1, "context": "abbrev"},
            "at t": {"ticker": "T", "priority": 1, "context": "spaced"},
            
            "jp morgan": {"ticker": "JPM", "priority": 1, "context": "company"},
            "jpmorgan": {"ticker": "JPM", "priority": 1, "context": "company"},
            "j.p. morgan": {"ticker": "JPM", "priority": 1, "context": "formal"},
            
            "unitedhealth": {"ticker": "UNH", "priority": 1, "context": "company"},
            "united health": {"ticker": "UNH", "priority": 1, "context": "spaced"},
        }
        
        # Adaptive fuzzy matching thresholds
        self.fuzzy_thresholds = {
            "strict": 0.9,    # For short tokens
            "normal": 0.85,   # For medium tokens
            "lenient": 0.8,   # For long tokens or phrases
        }
    
    def resolve_tickers_enhanced(self, text: str) -> Tuple[List[Dict[str, str]], List[str]]:
        """Enhanced ticker resolution with improved pattern matching and fuzzy matching."""
        if not text:
            return [], []
        
        matches = []
        seen = set()
        warnings = []
        
        # Step 1: Enhanced pattern matching
        pattern_matches = self._enhanced_pattern_matching(text)
        for match in pattern_matches:
            if match['ticker'] not in seen:
                matches.append(match)
                seen.add(match['ticker'])
        
        # Step 2: Priority-based manual overrides
        override_matches = self._priority_manual_overrides(text)
        for match in override_matches:
            if match['ticker'] not in seen:
                matches.append(match)
                seen.add(match['ticker'])
        
        # Step 3: Alias matching
        alias_matches = self._enhanced_alias_matching(text)
        for match in alias_matches:
            if match['ticker'] not in seen:
                matches.append(match)
                seen.add(match['ticker'])
        
        # Step 4: Enhanced fuzzy matching
        if not matches:
            fuzzy_matches, fuzzy_warnings = self._enhanced_fuzzy_matching(text)
            matches.extend(fuzzy_matches)
            warnings.extend(fuzzy_warnings)
        
        # Sort by position and priority
        matches.sort(key=lambda x: (x.get('position', 0), -x.get('priority', 0)))
        
        return matches, warnings
    
    def _enhanced_pattern_matching(self, text: str) -> List[Dict[str, str]]:
        """Enhanced pattern matching for better ticker detection."""
        matches = []
        
        for pattern in self.enhanced_patterns:
            for match in pattern.finditer(text):
                token = match.group(0).upper()
                
                # Check if it's a valid ticker
                if token in self.ticker_set:
                    matches.append({
                        'input': token,
                        'ticker': token,
                        'position': match.start(),
                        'confidence': 1.0,
                        'method': 'direct_pattern',
                        'priority': 1
                    })
                # Check without dots
                elif token.replace('.', '') in self.ticker_set:
                    clean_token = token.replace('.', '')
                    matches.append({
                        'input': token,
                        'ticker': clean_token,
                        'position': match.start(),
                        'confidence': 0.95,
                        'method': 'pattern_no_dot',
                        'priority': 1
                    })
                # Check hyphenated versions
                elif token.replace('-', '') in self.ticker_set:
                    clean_token = token.replace('-', '')
                    matches.append({
                        'input': token,
                        'ticker': clean_token,
                        'position': match.start(),
                        'confidence': 0.9,
                        'method': 'pattern_no_hyphen',
                        'priority': 1
                    })
        
        return matches
    
    def _priority_manual_overrides(self, text: str) -> List[Dict[str, str]]:
        """Priority-based manual override checking."""
        matches = []
        text_lower = text.lower()
        
        # Find all applicable overrides
        applicable_overrides = []
        for alias, override_info in self.manual_overrides_priority.items():
            if alias in text_lower:
                position = text_lower.find(alias)
                applicable_overrides.append({
                    'alias': alias,
                    'position': position,
                    'ticker': override_info['ticker'],
                    'priority': override_info['priority'],
                    'context': override_info['context']
                })
        
        # Sort by priority (higher priority first) and position
        applicable_overrides.sort(key=lambda x: (-x['priority'], x['position']))
        
        # Take the highest priority match for each position
        for override in applicable_overrides:
            matches.append({
                'input': override['alias'],
                'ticker': override['ticker'],
                'position': override['position'],
                'confidence': 1.0,
                'method': 'manual_override',
                'priority': override['priority'],
                'context': override['context']
            })
            break  # Only take the first (highest priority) match
        
        return matches
    
    def _enhanced_alias_matching(self, text: str) -> List[Dict[str, str]]:
        """Enhanced alias matching with better filtering."""
        matches = []
        text_normalized = self._normalize_text(text)
        
        for alias, tickers in self.lookup.items():
            if len(alias) <= 2:  # Skip short aliases
                continue
                
            marker = f" {alias} "
            position = text_normalized.find(marker)
            if position != -1:
                for ticker in tickers:
                    matches.append({
                        'input': alias,
                        'ticker': ticker,
                        'position': position,
                        'confidence': 0.8,
                        'method': 'alias_match',
                        'priority': 2
                    })
                    break  # Take first ticker for this alias
        
        return matches
    
    def _enhanced_fuzzy_matching(self, text: str) -> Tuple[List[Dict[str, str]], List[str]]:
        """Enhanced fuzzy matching with adaptive thresholds and multi-token support."""
        matches = []
        warnings = []
        
        tokens = self._tokenize_text(text)
        alias_candidates = list(self.lookup.keys())
        
        # Single token fuzzy matching with adaptive thresholds
        for token in tokens:
            if len(token) < 3:  # Skip short tokens
                continue
            
            # Determine threshold based on token length
            if len(token) <= 3:
                threshold = self.fuzzy_thresholds["strict"]
            elif len(token) <= 6:
                threshold = self.fuzzy_thresholds["normal"]
            else:
                threshold = self.fuzzy_thresholds["lenient"]
            
            candidates = difflib.get_close_matches(
                token, alias_candidates, n=2, cutoff=threshold
            )
            
            for candidate in candidates:
                for ticker in self.lookup.get(candidate, []):
                    matches.append({
                        'input': token,
                        'ticker': ticker,
                        'confidence': 0.6,
                        'method': 'fuzzy_single',
                        'priority': 3
                    })
                    warnings.append("fuzzy_match")
                    break
        
        # Multi-token fuzzy matching (up to 3 tokens)
        for i in range(len(tokens)):
            for j in range(i+1, min(i+4, len(tokens)+1)):
                phrase = " ".join(tokens[i:j])
                if len(phrase) < 5:  # Skip short phrases
                    continue
                
                candidates = difflib.get_close_matches(
                    phrase, alias_candidates, n=1, cutoff=0.8
                )
                
                for candidate in candidates:
                    for ticker in self.lookup.get(candidate, []):
                        matches.append({
                            'input': phrase,
                            'ticker': ticker,
                            'confidence': 0.7,
                            'method': 'fuzzy_multi',
                            'priority': 3
                        })
                        warnings.append("fuzzy_match")
                        break
        
        return matches, warnings
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        normalized = text.lower()
        normalized = re.sub(r'\s+', ' ', normalized)
        return f" {normalized} "
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into words."""
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        tokens = cleaned.split()
        return [token.lower() for token in tokens if len(token) > 1]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get resolver statistics."""
        return {
            'total_tickers': len(self.ticker_set),
            'total_aliases': sum(len(aliases) for aliases in self.alias_map.values()),
            'manual_overrides': len(self.manual_overrides_priority),
            'lookup_entries': len(self.lookup),
            'enhanced_patterns': len(self.enhanced_patterns)
        }

def test_enhanced_resolver():
    """Test the enhanced ticker resolver."""
    
    print("ENHANCED TICKER RESOLVER TESTING")
    print("=" * 70)
    
    resolver = EnhancedTickerResolver()
    
    # Test cases organized by category
    test_cases = [
        # Enhanced Pattern Matching Tests
        ("AAPL stock price", "Standard ticker"),
        ("MSFT earnings", "Standard ticker"),
        ("3M company performance", "Number + letter ticker"),
        ("AT&T dividend yield", "Ampersand ticker"),
        ("BRK-B analysis", "Hyphenated ticker"),
        ("BRK.A and BRK.B", "Multiple hyphenated tickers"),
        
        # Priority-based Manual Overrides
        ("alphabet earnings", "High priority override"),
        ("google revenue", "Brand override"),
        ("facebook stock", "Legacy override"),
        ("berkshire hathaway", "Company override"),
        ("berkshire b", "Lower priority override"),
        ("jp morgan", "Company override"),
        ("att dividend", "Abbrev override"),
        
        # Enhanced Fuzzy Matching
        ("aple stock", "Typo - should work with adaptive threshold"),
        ("microsft earnings", "Typo - should work"),
        ("nividia gpu", "Typo - should work"),
        ("amazn revenue", "Typo - should work"),
        ("netflx streaming", "Typo - should work"),
        
        # Edge Cases
        ("Johnson & Johnson", "Company with ampersand"),
        ("Apple Inc.", "Company with suffix"),
        ("Microsoft Corporation", "Full company name"),
        ("Tesla Motors Inc.", "Multi-word company name"),
        
        # Complex Queries
        ("Compare Apple and Microsoft", "Multi-company query"),
        ("Show me Tesla, NVIDIA, and AMD", "Multiple companies"),
        ("What is Google's revenue?", "Question format"),
        ("Analyze 3M and AT&T performance", "Special tickers"),
        
        # Edge Cases that were problematic
        ("123AAPL456", "Numbers with ticker"),
        ("Apple123", "Company name with numbers"),
        ("VeryLongCompanyName", "Very long name"),
        ("", "Empty string"),
        ("   ", "Whitespace only"),
    ]
    
    print(f"{'Input':<40} | {'Description':<25} | {'Result':<20} | {'Method':<15}")
    print("-" * 100)
    
    passed = 0
    total = len(test_cases)
    
    for text, description in test_cases:
        try:
            resolved, warnings = resolver.resolve_tickers_enhanced(text)
            
            if resolved:
                result = ", ".join([f"{r['ticker']}({r['confidence']:.1f})" for r in resolved])
                method = resolved[0].get('method', 'unknown')
                passed += 1
            else:
                result = "None"
                method = "none"
            
            warning_str = f" (Warnings: {warnings})" if warnings else ""
            print(f"{text:<40} | {description:<25} | {result:<20} | {method:<15}")
            
        except Exception as e:
            print(f"{text:<40} | {description:<25} | ERROR: {str(e):<15} | error")
    
    print("-" * 100)
    print(f"ENHANCED RESOLVER RESULTS: {passed}/{total} ({passed/total*100:.1f}% success)")
    
    # Show statistics
    print(f"\nEnhanced Resolver Statistics:")
    stats = resolver.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()

if __name__ == "__main__":
    test_enhanced_resolver()
