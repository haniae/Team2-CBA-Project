"""
Fuzzy matching utilities for spelling correction.

Uses multiple algorithms:
- Levenshtein distance (edit distance)
- Jaro-Winkler similarity
- Common typo patterns
- Phonetic matching (Soundex)
"""

from typing import List, Tuple, Optional, Set
import re
from difflib import SequenceMatcher


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein (edit) distance between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Number of single-character edits needed to change s1 into s2
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def jaro_winkler_similarity(s1: str, s2: str) -> float:
    """
    Calculate Jaro-Winkler similarity (0.0 to 1.0).
    
    Good for detecting typos at the beginning of words.
    """
    # Use SequenceMatcher as a simple approximation
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def soundex(s: str) -> str:
    """
    Generate Soundex code for phonetic matching.
    
    Useful for matching words that sound similar but are spelled differently.
    Example: "Microsoft" and "Microsaft" have similar Soundex codes.
    """
    if not s:
        return "0000"
    
    s = s.upper()
    
    # Keep first letter
    soundex_code = s[0]
    
    # Mapping of letters to digits
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    
    # Convert remaining letters
    for char in s[1:]:
        if char in mapping:
            code = mapping[char]
            # Don't add duplicate consecutive codes
            if code != soundex_code[-1]:
                soundex_code += code
    
    # Pad with zeros or truncate to 4 characters
    soundex_code = (soundex_code + "000")[:4]
    
    return soundex_code


def calculate_similarity(s1: str, s2: str, use_phonetic: bool = True) -> float:
    """
    Calculate overall similarity score between two strings (0.0 to 1.0).
    
    Combines multiple similarity metrics:
    - Edit distance similarity
    - Jaro-Winkler similarity
    - Phonetic similarity (optional)
    
    Args:
        s1: First string
        s2: Second string
        use_phonetic: Whether to include phonetic matching
        
    Returns:
        Similarity score from 0.0 (completely different) to 1.0 (identical)
    """
    if not s1 or not s2:
        return 0.0
    
    s1_lower = s1.lower()
    s2_lower = s2.lower()
    
    # Exact match
    if s1_lower == s2_lower:
        return 1.0
    
    # Edit distance similarity
    max_len = max(len(s1), len(s2))
    edit_dist = levenshtein_distance(s1_lower, s2_lower)
    edit_similarity = 1.0 - (edit_dist / max_len)
    
    # Jaro-Winkler similarity
    jw_similarity = jaro_winkler_similarity(s1, s2)
    
    # Combine metrics (weighted average)
    similarity = (edit_similarity * 0.6) + (jw_similarity * 0.4)
    
    # Phonetic bonus (if enabled and phonetically similar)
    if use_phonetic:
        if soundex(s1) == soundex(s2):
            similarity = min(1.0, similarity + 0.1)
    
    return similarity


class FuzzyMatcher:
    """
    Fuzzy matching engine for finding similar strings in a corpus.
    """
    
    def __init__(self, corpus: List[str], case_sensitive: bool = False):
        """
        Initialize fuzzy matcher with a corpus of valid strings.
        
        Args:
            corpus: List of valid strings to match against
            case_sensitive: Whether matching should be case-sensitive
        """
        self.corpus = corpus
        self.case_sensitive = case_sensitive
        self._index = self._build_index()
    
    def _build_index(self) -> dict:
        """Build index for faster lookups"""
        index = {}
        for item in self.corpus:
            key = item if self.case_sensitive else item.lower()
            index[key] = item
        return index
    
    def find_exact(self, query: str) -> Optional[str]:
        """Find exact match in corpus"""
        key = query if self.case_sensitive else query.lower()
        return self._index.get(key)
    
    def find_best_match(
        self,
        query: str,
        threshold: float = 0.6,
        top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find best matching strings in corpus.
        
        Args:
            query: Query string to match
            threshold: Minimum similarity threshold (0.0 to 1.0)
            top_n: Number of top matches to return
            
        Returns:
            List of (match, similarity_score) tuples, sorted by score descending
        """
        # Check for exact match first
        exact = self.find_exact(query)
        if exact:
            return [(exact, 1.0)]
        
        # Calculate similarity for all corpus items
        matches = []
        for item in self.corpus:
            similarity = calculate_similarity(query, item, use_phonetic=True)
            if similarity >= threshold:
                matches.append((item, similarity))
        
        # Sort by similarity (descending) and return top N
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_n]
    
    def find_with_prefix(self, prefix: str, max_results: int = 10) -> List[str]:
        """
        Find items that start with the given prefix.
        
        Useful for autocomplete-style matching.
        """
        prefix_lower = prefix.lower() if not self.case_sensitive else prefix
        matches = []
        
        for item in self.corpus:
            item_key = item if self.case_sensitive else item.lower()
            if item_key.startswith(prefix_lower):
                matches.append(item)
                if len(matches) >= max_results:
                    break
        
        return matches


class TypoPatternMatcher:
    """
    Detect and correct common typo patterns.
    """
    
    # Common keyboard adjacency errors
    ADJACENT_KEYS = {
        'a': 'qwsz',
        'b': 'vghn',
        'c': 'xdfv',
        'd': 'sfcx',
        'e': 'wrd',
        'f': 'dgcv',
        'g': 'fhtb',
        'h': 'gyju',
        'i': 'uok',
        'j': 'hukn',
        'k': 'jilm',
        'l': 'kop',
        'm': 'njk',
        'n': 'bhjm',
        'o': 'iklp',
        'p': 'ol',
        'q': 'wa',
        'r': 'etf',
        's': 'awedxz',
        't': 'ryfg',
        'u': 'yihj',
        'v': 'cfgb',
        'w': 'qase',
        'x': 'zsdc',
        'y': 'tghu',
        'z': 'asx',
    }
    
    # Common letter substitutions
    COMMON_SUBSTITUTIONS = {
        ('ei', 'ie'): ['receive', 'believe'],
        ('s', 'c'): ['license', 'practice'],
        ('c', 's'): ['advice', 'defense'],
    }
    
    @classmethod
    def is_adjacent_key_typo(cls, c1: str, c2: str) -> bool:
        """Check if two characters are adjacent on keyboard"""
        c1_lower = c1.lower()
        c2_lower = c2.lower()
        return c2_lower in cls.ADJACENT_KEYS.get(c1_lower, '')
    
    @classmethod
    def generate_typo_variants(cls, word: str, max_variants: int = 20) -> Set[str]:
        """
        Generate common typo variants of a word.
        
        Includes:
        - Single character deletions
        - Single character insertions (adjacent keys)
        - Single character substitutions (adjacent keys)
        - Adjacent character transpositions
        """
        variants = set()
        word_lower = word.lower()
        
        # Single deletions
        for i in range(len(word_lower)):
            variant = word_lower[:i] + word_lower[i+1:]
            variants.add(variant)
            if len(variants) >= max_variants:
                return variants
        
        # Single transpositions
        for i in range(len(word_lower) - 1):
            variant = word_lower[:i] + word_lower[i+1] + word_lower[i] + word_lower[i+2:]
            variants.add(variant)
            if len(variants) >= max_variants:
                return variants
        
        # Single substitutions (adjacent keys only for efficiency)
        for i, char in enumerate(word_lower):
            if char in cls.ADJACENT_KEYS:
                for adj_char in cls.ADJACENT_KEYS[char]:
                    variant = word_lower[:i] + adj_char + word_lower[i+1:]
                    variants.add(variant)
                    if len(variants) >= max_variants:
                        return variants
        
        return variants

