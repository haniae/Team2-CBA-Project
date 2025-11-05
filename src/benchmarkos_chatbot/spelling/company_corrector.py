"""
Company name and ticker spelling correction.

Handles typos in company names and ticker symbols using:
- SEC company name database
- Common company name patterns
- Ticker symbol fuzzy matching
"""

from typing import List, Tuple, Optional, Dict
import re
from .fuzzy_matcher import FuzzyMatcher, calculate_similarity


class CompanyCorrector:
    """
    Correct spelling errors in company names and ticker symbols.
    """
    
    def __init__(self, sec_index=None, ticker_list: Optional[List[str]] = None):
        """
        Initialize company corrector.
        
        Args:
            sec_index: Optional SEC index for company name lookups
            ticker_list: Optional list of valid ticker symbols
        """
        self.sec_index = sec_index
        self.ticker_list = ticker_list or []
        
        # Build common company names corpus
        self.company_names = self._build_company_corpus()
        
        # Create fuzzy matchers
        self.company_matcher = FuzzyMatcher(self.company_names, case_sensitive=False)
        self.ticker_matcher = FuzzyMatcher(self.ticker_list, case_sensitive=True) if self.ticker_list else None
        
        # Common typos for well-known companies
        self.common_typos = self._build_common_typos()
    
    def _build_company_corpus(self) -> List[str]:
        """Build corpus of company names from various sources"""
        companies = set()
        
        # Add from SEC index if available
        if self.sec_index and hasattr(self.sec_index, 'items'):
            for entry in self.sec_index.items():
                if isinstance(entry, dict) and 'name' in entry:
                    companies.add(entry['name'])
                elif isinstance(entry, tuple) and len(entry) >= 2:
                    companies.add(entry[1])  # name is usually second element
        
        # Add well-known companies
        companies.update([
            'Apple', 'Microsoft', 'Amazon', 'Google', 'Alphabet',
            'Meta', 'Facebook', 'Tesla', 'Netflix', 'Nvidia',
            'JPMorgan', 'Bank of America', 'Wells Fargo', 'Citigroup',
            'Walmart', 'Target', 'Costco', 'Home Depot',
            'Johnson & Johnson', 'Pfizer', 'Moderna',
            'ExxonMobil', 'Chevron', 'ConocoPhillips',
            'Disney', 'Comcast', 'AT&T', 'Verizon',
            'Coca-Cola', 'PepsiCo', 'Starbucks', 'McDonald\'s',
            'Boeing', 'Lockheed Martin', 'General Electric',
            'Intel', 'AMD', 'Qualcomm', 'Cisco',
            'IBM', 'Oracle', 'Salesforce', 'Adobe',
        ])
        
        return sorted(companies)
    
    def _build_common_typos(self) -> Dict[str, str]:
        """Map common typos to correct company names"""
        return {
            # Microsoft variants (expanded)
            'microsft': 'Microsoft',
            'microsfot': 'Microsoft',
            'microsof': 'Microsoft',
            'micosoft': 'Microsoft',
            'micorsoft': 'Microsoft',
            'micros0ft': 'Microsoft',
            'microsotf': 'Microsoft',
            'micorsoft': 'Microsoft',
            'mirosoft': 'Microsoft',
            'miscrosoft': 'Microsoft',
            'microsft': 'Microsoft',
            'mcrosoft': 'Microsoft',
            'micrsoft': 'Microsoft',
            
            # Apple variants (expanded)
            'aple': 'Apple',
            'appel': 'Apple',
            'appl': 'Apple',
            'appple': 'Apple',
            'aplle': 'Apple',
            'aplpe': 'Apple',
            'aplle': 'Apple',
            'appe': 'Apple',
            
            # Amazon variants (expanded)
            'amazn': 'Amazon',
            'amzon': 'Amazon',
            'amazom': 'Amazon',
            'amazun': 'Amazon',
            'amzaon': 'Amazon',
            'amazno': 'Amazon',
            'ammazon': 'Amazon',
            'amazin': 'Amazon',
            'aamazon': 'Amazon',
            'amaazon': 'Amazon',
            
            # Google/Alphabet (expanded)
            'gogle': 'Google',
            'googel': 'Google',
            'googl': 'Google',
            'gooogle': 'Google',
            'googlr': 'Google',
            'googlle': 'Google',
            'goolge': 'Google',
            'goole': 'Google',
            'googke': 'Google',
            'goofle': 'Google',
            
            # Tesla (expanded)
            'tesls': 'Tesla',
            'telsa': 'Tesla',
            'teslas': 'Tesla',
            'telsas': 'Tesla',
            'tesle': 'Tesla',
            'tesal': 'Tesla',
            'tsla': 'Tesla',
            'teslaa': 'Tesla',
            
            # Meta/Facebook (expanded)
            'facbook': 'Facebook',
            'facebok': 'Facebook',
            'facebook': 'Facebook',
            'faceboook': 'Facebook',
            'faecbook': 'Facebook',
            'fcebook': 'Facebook',
            'faceook': 'Facebook',
            'facbeook': 'Facebook',
            'meta': 'Meta',
            'mets': 'Meta',
            'metta': 'Meta',
            
            # Netflix (expanded)
            'netfix': 'Netflix',
            'netflx': 'Netflix',
            'netflic': 'Netflix',
            'netfllix': 'Netflix',
            'netfli': 'Netflix',
            'neflix': 'Netflix',
            'neflx': 'Netflix',
            'netflixx': 'Netflix',
            
            # Nvidia (expanded)
            'nividia': 'Nvidia',
            'nvidea': 'Nvidia',
            'nvida': 'Nvidia',
            'nviida': 'Nvidia',
            'nvidai': 'Nvidia',
            'nvifia': 'Nvidia',
            'nvdia': 'Nvidia',
            'nviia': 'Nvidia',
            
            # JPMorgan variants
            'jpmorgan': 'JPMorgan',
            'jp morgan': 'JPMorgan',
            'jpmorgam': 'JPMorgan',
            'jpmorgan': 'JPMorgan',
            'jpmorgsn': 'JPMorgan',
            'jpmogan': 'JPMorgan',
            
            # Bank of America
            'bank of america': 'Bank of America',
            'bankofamerica': 'Bank of America',
            'bofa': 'Bank of America',
            'boa': 'Bank of America',
            'bank of americaa': 'Bank of America',
            
            # Goldman Sachs
            'goldman': 'Goldman Sachs',
            'goldman sachs': 'Goldman Sachs',
            'goldmansachs': 'Goldman Sachs',
            'goldman sacks': 'Goldman Sachs',
            'golman sachs': 'Goldman Sachs',
            
            # Walmart
            'walmart': 'Walmart',
            'walmat': 'Walmart',
            'wal mart': 'Walmart',
            'wallmart': 'Walmart',
            'walmartt': 'Walmart',
            
            # Target
            'targer': 'Target',
            'targett': 'Target',
            'targt': 'Target',
            
            # Costco
            'costco': 'Costco',
            'costko': 'Costco',
            'cosco': 'Costco',
            
            # Disney
            'disney': 'Disney',
            'disnay': 'Disney',
            'diseny': 'Disney',
            'disnei': 'Disney',
            
            # Coca-Cola
            'coca cola': 'Coca-Cola',
            'cocacola': 'Coca-Cola',
            'coke': 'Coca-Cola',
            'coca-cola': 'Coca-Cola',
            'coca kola': 'Coca-Cola',
            
            # PepsiCo
            'pepsi': 'PepsiCo',
            'pepsico': 'PepsiCo',
            'pepisco': 'PepsiCo',
            'pepsicoo': 'PepsiCo',
            
            # Starbucks
            'starbucks': 'Starbucks',
            'starbucks': 'Starbucks',
            'starbcks': 'Starbucks',
            'starbukcs': 'Starbucks',
            'starrbucks': 'Starbucks',
            
            # Intel
            'intel': 'Intel',
            'intell': 'Intel',
            'intle': 'Intel',
            
            # AMD
            'amd': 'AMD',
            'amdd': 'AMD',
            
            # Qualcomm
            'qualcomm': 'Qualcomm',
            'qualcom': 'Qualcomm',
            'qualcoom': 'Qualcomm',
            'quallcomm': 'Qualcomm',
            
            # Cisco
            'cisco': 'Cisco',
            'cysco': 'Cisco',
            'cisoc': 'Cisco',
            
            # Oracle
            'oracle': 'Oracle',
            'oracl': 'Oracle',
            'oracel': 'Oracle',
            'oraclle': 'Oracle',
            
            # Salesforce
            'salesforce': 'Salesforce',
            'sales force': 'Salesforce',
            'saleforce': 'Salesforce',
            'salesfroce': 'Salesforce',
            
            # Adobe
            'adobe': 'Adobe',
            'adoobe': 'Adobe',
            'adbe': 'Adobe',
            
            # Berkshire Hathaway
            'berkshire': 'Berkshire Hathaway',
            'berkshire hathaway': 'Berkshire Hathaway',
            'berkshirehathaway': 'Berkshire Hathaway',
            'berkshiire': 'Berkshire Hathaway',
            'birkshire': 'Berkshire Hathaway',
        }
    
    def correct_company_name(
        self,
        query: str,
        min_confidence: float = 0.6
    ) -> Tuple[Optional[str], float, bool]:
        """
        Correct a potentially misspelled company name.
        
        Args:
            query: The query string (potentially misspelled)
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (corrected_name, confidence, should_confirm)
            - corrected_name: Corrected company name or None
            - confidence: Confidence score (0.0 to 1.0)
            - should_confirm: Whether to ask user for confirmation
        """
        if not query or len(query) < 2:
            return None, 0.0, False
        
        query_clean = query.strip()
        query_lower = query_clean.lower()
        
        # Check common typos first (highest confidence)
        if query_lower in self.common_typos:
            return self.common_typos[query_lower], 0.95, False
        
        # Check exact match
        exact = self.company_matcher.find_exact(query_clean)
        if exact:
            return exact, 1.0, False
        
        # Fuzzy match
        matches = self.company_matcher.find_best_match(query_clean, threshold=min_confidence, top_n=3)
        
        if not matches:
            return None, 0.0, False
        
        best_match, confidence = matches[0]
        
        # Determine if we should ask for confirmation
        should_confirm = confidence < 0.85
        
        return best_match, confidence, should_confirm
    
    def correct_ticker(
        self,
        query: str,
        min_confidence: float = 0.7
    ) -> Tuple[Optional[str], float, bool]:
        """
        Correct a potentially misspelled ticker symbol.
        
        Ticker correction is more conservative because:
        - Tickers are short (2-5 chars), so small typos matter more
        - False positives are more costly
        
        Args:
            query: The query string (potentially misspelled ticker)
            min_confidence: Minimum confidence threshold
            
        Returns:
            Tuple of (corrected_ticker, confidence, should_confirm)
        """
        if not self.ticker_matcher or not query:
            return None, 0.0, False
        
        query_clean = query.strip().upper()
        
        # For very short queries (1-2 chars), require exact match
        if len(query_clean) <= 2:
            exact = self.ticker_matcher.find_exact(query_clean)
            if exact:
                return exact, 1.0, False
            return None, 0.0, False
        
        # Check exact match
        exact = self.ticker_matcher.find_exact(query_clean)
        if exact:
            return exact, 1.0, False
        
        # Fuzzy match with higher threshold for tickers
        matches = self.ticker_matcher.find_best_match(
            query_clean,
            threshold=min_confidence,
            top_n=3
        )
        
        if not matches:
            return None, 0.0, False
        
        best_match, confidence = matches[0]
        
        # For tickers, always confirm if not exact match
        should_confirm = confidence < 0.95
        
        return best_match, confidence, should_confirm
    
    def suggest_companies(
        self,
        query: str,
        max_suggestions: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Suggest possible company names for a query.
        
        Useful for autocomplete or "did you mean?" features.
        
        Args:
            query: Query string
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of (company_name, confidence) tuples
        """
        if not query or len(query) < 2:
            return []
        
        # Try prefix matching first (for autocomplete-style queries)
        prefix_matches = self.company_matcher.find_with_prefix(query, max_results=max_suggestions)
        if prefix_matches:
            # Calculate similarity for prefix matches
            suggestions = []
            for match in prefix_matches:
                similarity = calculate_similarity(query, match)
                suggestions.append((match, similarity))
            return sorted(suggestions, key=lambda x: x[1], reverse=True)[:max_suggestions]
        
        # Fall back to fuzzy matching
        return self.company_matcher.find_best_match(query, threshold=0.5, top_n=max_suggestions)

