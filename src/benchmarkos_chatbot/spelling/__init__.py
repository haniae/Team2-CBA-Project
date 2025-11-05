"""
Spelling correction module for natural language queries.

Provides fuzzy matching and typo correction for:
- Company names and tickers
- Metric names
- Common financial terms
"""

from .correction_engine import SpellingCorrectionEngine, CorrectionResult
from .fuzzy_matcher import FuzzyMatcher, calculate_similarity

__all__ = [
    'SpellingCorrectionEngine',
    'CorrectionResult',
    'FuzzyMatcher',
    'calculate_similarity',
]

