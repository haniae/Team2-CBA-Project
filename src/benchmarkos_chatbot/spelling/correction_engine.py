"""
Main spelling correction engine.

Orchestrates all spelling correction components and provides
a unified interface for correcting queries.
"""

from typing import List, Tuple, Optional, Dict, NamedTuple
import re
from .company_corrector import CompanyCorrector
from .metric_corrector import MetricCorrector
from .fuzzy_matcher import calculate_similarity


class Correction(NamedTuple):
    """Represents a single correction"""
    original: str
    corrected: str
    confidence: float
    type: str  # 'company', 'metric', 'word', 'ticker'
    position: Tuple[int, int]  # start, end positions in original text


class CorrectionResult(NamedTuple):
    """Result of spelling correction"""
    corrected_text: str
    corrections: List[Correction]
    should_confirm: bool  # Whether to ask user for confirmation
    confidence: float  # Overall confidence (0.0 to 1.0)


class SpellingCorrectionEngine:
    """
    Main spelling correction engine.
    
    Coordinates:
    - Company name correction
    - Ticker correction
    - Metric name correction
    - General word correction
    """
    
    # Confidence thresholds
    CONFIDENCE_AUTO_CORRECT = 0.95  # Auto-correct silently
    CONFIDENCE_AUTO_NOTIFY = 0.80   # Auto-correct with notification
    CONFIDENCE_SUGGEST = 0.60       # Suggest with confirmation
    
    # Additional false positive prevention patterns
    FALSE_POSITIVE_PATTERNS = {
        # Common question words that might match company names
        'what', 'when', 'where', 'who', 'why', 'how',
        'whats', 'whens', 'wheres', 'whos', 'whys', 'hows',
        'which', 'whose', 'whom',
        
        # Common verbs
        'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'done',
        'can', 'could', 'would', 'should', 'will', 'shall', 'may', 'might', 'must',
        
        # Determiners and prepositions
        'the', 'a', 'an', 'this', 'that', 'these', 'those',
        'in', 'on', 'at', 'to', 'from', 'by', 'with', 'about',
        'for', 'of', 'as', 'into', 'onto', 'upon',
        
        # Pronouns
        'it', 'its', 'they', 'them', 'their', 'theirs',
        'he', 'she', 'him', 'her', 'his', 'hers',
        'we', 'us', 'our', 'ours', 'you', 'your', 'yours',
        
        # Common adjectives that might be misidentified
        'good', 'bad', 'high', 'low', 'big', 'small',
        'new', 'old', 'first', 'last', 'next', 'best', 'worst',
        
        # Financial context words (should not be corrected)
        'trading', 'stock', 'shares', 'market', 'price',
        'buy', 'sell', 'hold', 'invest', 'investment',
        
        # Time words
        'year', 'month', 'quarter', 'day', 'today', 'yesterday',
        'now', 'then', 'latest', 'current', 'recent',
    }
    
    def __init__(self, sec_index=None, ticker_list: Optional[List[str]] = None):
        """
        Initialize spelling correction engine.
        
        Args:
            sec_index: Optional SEC index for company lookups
            ticker_list: Optional list of valid tickers
        """
        self.company_corrector = CompanyCorrector(sec_index, ticker_list)
        self.metric_corrector = MetricCorrector()
        
        # Common financial words (to avoid false positives)
        self.financial_vocabulary = self._build_financial_vocabulary()
        
        # Common typo patterns
        self.typo_patterns = self._build_typo_patterns()
    
    def _build_financial_vocabulary(self) -> set:
        """Build set of common financial and business words"""
        return {
            # Question words (should not be corrected)
            'what', 'how', 'why', 'when', 'where', 'who', 'which',
            'whats', 'hows', 'is', 'are', 'was', 'were', 'do', 'does', 'did',
            'can', 'could', 'would', 'should', 'will', 'shall',
            
            # Common words
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'from', 'by', 'about', 'as', 'into', 'like', 'through',
            'their', 'them', 'they', 'this', 'that', 'these', 'those',
            'tell', 'show', 'explain', 'compare', 'give', 'find',
            'help', 'understand', 'know', 'see', 'look',
            
            # Financial terms
            'stock', 'stocks', 'share', 'shares', 'trading', 'market',
            'company', 'companies', 'business', 'corporate', 'industry',
            'quarter', 'quarterly', 'annual', 'year', 'month',
            'high', 'low', 'good', 'bad', 'better', 'worse', 'best', 'worst',
            'up', 'down', 'increase', 'decrease', 'change',
            'report', 'statement', 'filing', 'earnings',
            'financial', 'fiscal', 'performance',
            
            # Time expressions
            'today', 'yesterday', 'tomorrow', 'now', 'current', 'latest',
            'last', 'next', 'previous', 'recent', 'past', 'future',
            
            # Numbers and quantifiers
            'all', 'some', 'many', 'few', 'more', 'less', 'most', 'least',
            'much', 'little', 'every', 'each', 'any', 'none',
        }
    
    def _build_typo_patterns(self) -> Dict[str, str]:
        """Build dictionary of common typo patterns"""
        return {
            # Common contractions that might be mistyped
            "what's": "what's",
            "whats": "what's",
            "how's": "how's",
            "hows": "how's",
            "it's": "it's",
            "its": "its",  # not a typo, but watch for context
            "that's": "that's",
            "thats": "that's",
            "there's": "there's",
            "theres": "there's",
            
            # Common word variants
            "tho": "though",
            "thru": "through",
            "gonna": "going to",
            "wanna": "want to",
        }
    
    def correct_query(
        self,
        text: str,
        correct_companies: bool = True,
        correct_metrics: bool = True,
        correct_tickers: bool = True
    ) -> CorrectionResult:
        """
        Correct spelling errors in a query.
        
        Args:
            text: Input query text
            correct_companies: Whether to correct company names
            correct_metrics: Whether to correct metric names
            correct_tickers: Whether to correct ticker symbols
            
        Returns:
            CorrectionResult with corrected text and metadata
        """
        if not text or not text.strip():
            return CorrectionResult(
                corrected_text=text,
                corrections=[],
                should_confirm=False,
                confidence=1.0
            )
        
        corrections = []
        corrected_text = text
        
        # Tokenize the text (simple word-based tokenization)
        words = self._tokenize(text)
        
        # Track position offset as we make corrections
        offset = 0
        
        for word_info in words:
            word = word_info['word']
            start_pos = word_info['start']
            end_pos = word_info['end']
            
            # Skip very short words or words in our vocabulary
            if len(word) <= 1 or word.lower() in self.financial_vocabulary:
                continue
            
            # ENHANCED: Skip false positive patterns
            if word.lower() in self.FALSE_POSITIVE_PATTERNS:
                continue
            
            # ENHANCED: Calculate context-aware confidence boost
            context_boost = self._calculate_context_boost(word, words, word_info)
            
            # Try corrections in order of priority
            correction = None
            correction_type = None
            
            # 1. Check if it's a potential ticker (all caps, 1-5 chars)
            # BUT: Don't "correct" valid tickers to company names
            if correct_tickers and word.isupper() and 2 <= len(word) <= 5:
                corrected, confidence, should_confirm = self.company_corrector.correct_ticker(word)
                # Only apply correction if the corrected form is also a ticker (uppercase)
                # This prevents "AAPL" → "Apple" type corrections
                if corrected and corrected != word and corrected.isupper():
                    correction = (corrected, confidence, should_confirm)
                    correction_type = 'ticker'
            
            # 2. Check if it's a potential company name (capitalized)
            # BUT: Don't try to correct all-caps words that look like tickers (2-5 chars)
            # This prevents "AAPL" from being "corrected" to "Apple"
            is_potential_ticker = word.isupper() and 2 <= len(word) <= 5
            if not correction and correct_companies and not is_potential_ticker and (word[0].isupper() or len(word) >= 4):
                corrected, confidence, should_confirm = self.company_corrector.correct_company_name(word)
                if corrected and corrected.lower() != word.lower():
                    correction = (corrected, confidence, should_confirm)
                    correction_type = 'company'
            
            # 3. Check if it's a potential metric name
            if not correction and correct_metrics:
                corrected, confidence, should_confirm = self.metric_corrector.correct_metric(word)
                if corrected and corrected.lower() != word.lower():
                    correction = (corrected, confidence, should_confirm)
                    correction_type = 'metric'
            
            # 4. Check typo patterns
            if not correction and word.lower() in self.typo_patterns:
                corrected = self.typo_patterns[word.lower()]
                correction = (corrected, 0.95, False)
                correction_type = 'word'
            
            # Apply correction if found
            if correction:
                corrected, base_confidence, should_confirm = correction
                
                # ENHANCED: Apply context boost to confidence
                confidence = min(1.0, base_confidence + context_boost)
                
                # Apply correction to text
                adjusted_start = start_pos + offset
                adjusted_end = end_pos + offset
                corrected_text = (
                    corrected_text[:adjusted_start] +
                    corrected +
                    corrected_text[adjusted_end:]
                )
                
                # Update offset for future corrections
                offset += len(corrected) - len(word)
                
                # Record correction
                corrections.append(Correction(
                    original=word,
                    corrected=corrected,
                    confidence=confidence,
                    type=correction_type,
                    position=(start_pos, end_pos)
                ))
        
        # Calculate overall confidence and determine if confirmation needed
        if not corrections:
            overall_confidence = 1.0
            should_confirm = False
        else:
            # Overall confidence is the minimum of all corrections
            overall_confidence = min(c.confidence for c in corrections)
            # Ask for confirmation if any correction needs it or overall confidence is low
            should_confirm = (
                overall_confidence < self.CONFIDENCE_AUTO_NOTIFY or
                any(c.confidence < self.CONFIDENCE_AUTO_NOTIFY for c in corrections)
            )
        
        return CorrectionResult(
            corrected_text=corrected_text,
            corrections=corrections,
            should_confirm=should_confirm,
            confidence=overall_confidence
        )
    
    def _tokenize(self, text: str) -> List[Dict]:
        """
        Tokenize text into words with position information.
        
        Returns list of dicts with 'word', 'start', 'end' keys.
        """
        # Tokenize words, excluding possessive apostrophes
        pattern = r'\b[\w]+\b'
        tokens = []
        
        for match in re.finditer(pattern, text):
            word = match.group()
            # Skip if this is part of a possessive (e.g., "Apple's" → only take "Apple")
            # Check if there's an apostrophe immediately after this word
            next_pos = match.end()
            if next_pos < len(text) and text[next_pos:next_pos+2] in ["'s", "'t", "'d", "'m", "'ll", "'re", "'ve"]:
                # This is possessive/contraction - include just the word part
                pass
            
            tokens.append({
                'word': word,
                'start': match.start(),
                'end': match.end()
            })
        
        return tokens
    
    def _calculate_context_boost(
        self,
        word: str,
        all_words: List[Dict],
        current_word_info: Dict
    ) -> float:
        """
        Calculate confidence boost based on surrounding context.
        
        Context clues that increase confidence:
        - Financial keywords nearby (revenue, profit, earnings, etc.)
        - Company-related words (company, corporation, stock, etc.)
        - Comparison words (vs, versus, compared to, etc.)
        
        Returns:
            Float between 0.0 and 0.15 (boost amount)
        """
        boost = 0.0
        word_lower = word.lower()
        current_idx = all_words.index(current_word_info)
        
        # Get surrounding words (2 before, 2 after)
        context_range = 2
        start_idx = max(0, current_idx - context_range)
        end_idx = min(len(all_words), current_idx + context_range + 1)
        surrounding_words = [all_words[i]['word'].lower() for i in range(start_idx, end_idx) if i != current_idx]
        
        # Financial context keywords
        financial_keywords = {
            'revenue', 'profit', 'earnings', 'margin', 'growth', 'sales',
            'income', 'cash', 'flow', 'debt', 'equity', 'assets',
            'dividend', 'eps', 'ebitda', 'valuation', 'pe', 'ratio',
        }
        
        # Company context keywords
        company_keywords = {
            'company', 'corporation', 'corp', 'inc', 'stock', 'ticker',
            'share', 'shares', 'business', 'firm', 'enterprise',
        }
        
        # Comparison keywords
        comparison_keywords = {
            'vs', 'versus', 'compare', 'comparison', 'against', 'between',
            'than', 'better', 'worse', 'higher', 'lower',
        }
        
        # Query action keywords
        query_keywords = {
            'show', 'tell', 'what', 'how', 'give', 'get', 'find',
            'analyze', 'explain', 'understand',
        }
        
        # Count context matches
        financial_matches = sum(1 for w in surrounding_words if w in financial_keywords)
        company_matches = sum(1 for w in surrounding_words if w in company_keywords)
        comparison_matches = sum(1 for w in surrounding_words if w in comparison_keywords)
        query_matches = sum(1 for w in surrounding_words if w in query_keywords)
        
        # Apply boosts
        if financial_matches > 0:
            boost += 0.05  # Financial context boost
        if company_matches > 0:
            boost += 0.04  # Company context boost
        if comparison_matches > 0:
            boost += 0.03  # Comparison context boost
        if query_matches > 0:
            boost += 0.03  # Query context boost
        
        # Check for possessive form (e.g., "Microsoft's")
        current_pos = current_word_info['end']
        if current_pos < len(all_words) and all_words[current_pos:current_pos+2] in ["'s", "'t"]:
            boost += 0.05  # Possessive boost (likely a company name)
        
        # Cap the boost
        return min(0.15, boost)
    
    def suggest_corrections(
        self,
        text: str,
        max_suggestions: int = 3
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get correction suggestions for all potentially misspelled words.
        
        Useful for "did you mean?" features or autocomplete.
        
        Args:
            text: Input text
            max_suggestions: Maximum suggestions per word
            
        Returns:
            Dict mapping original words to list of (suggestion, confidence) tuples
        """
        suggestions = {}
        words = self._tokenize(text)
        
        for word_info in words:
            word = word_info['word']
            
            # Skip short words or known vocabulary
            if len(word) <= 2 or word.lower() in self.financial_vocabulary:
                continue
            
            # Get suggestions from all correctors
            word_suggestions = []
            
            # Company suggestions
            company_suggestions = self.company_corrector.suggest_companies(word, max_suggestions)
            word_suggestions.extend(company_suggestions)
            
            # Metric suggestions
            metric_suggestions = self.metric_corrector.suggest_metrics(word, max_suggestions)
            word_suggestions.extend(metric_suggestions)
            
            # Sort by confidence and deduplicate
            if word_suggestions:
                word_suggestions = sorted(
                    set(word_suggestions),
                    key=lambda x: x[1],
                    reverse=True
                )[:max_suggestions]
                suggestions[word] = word_suggestions
        
        return suggestions
    
    def format_correction_message(self, result: CorrectionResult) -> str:
        """
        Format a user-friendly message about corrections made.
        
        Args:
            result: CorrectionResult to format
            
        Returns:
            Human-readable correction message
        """
        if not result.corrections:
            return ""
        
        if len(result.corrections) == 1:
            c = result.corrections[0]
            if result.should_confirm:
                return f"Did you mean '{c.corrected}' instead of '{c.original}'?"
            else:
                return f"Auto-corrected '{c.original}' to '{c.corrected}'"
        else:
            # Multiple corrections
            if result.should_confirm:
                corrections_str = ", ".join(
                    f"'{c.original}' → '{c.corrected}'"
                    for c in result.corrections
                )
                return f"Did you mean: {corrections_str}?"
            else:
                corrections_str = ", ".join(
                    f"'{c.original}' → '{c.corrected}'"
                    for c in result.corrections
                )
                return f"Auto-corrected: {corrections_str}"

