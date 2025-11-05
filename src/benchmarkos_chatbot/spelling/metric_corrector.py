"""
Metric name spelling correction.

Handles typos in financial metric names and synonyms.
"""

from typing import List, Tuple, Optional, Dict
from .fuzzy_matcher import FuzzyMatcher, calculate_similarity


class MetricCorrector:
    """
    Correct spelling errors in metric names.
    """
    
    def __init__(self):
        """Initialize metric corrector with common financial metrics"""
        self.metrics = self._build_metric_corpus()
        self.metric_matcher = FuzzyMatcher(self.metrics, case_sensitive=False)
        self.common_typos = self._build_common_typos()
    
    def _build_metric_corpus(self) -> List[str]:
        """Build corpus of metric names and synonyms"""
        return [
            # Revenue metrics
            'revenue', 'sales', 'income', 'earnings',
            'total revenue', 'net sales', 'gross revenue',
            
            # Profitability
            'profit', 'net income', 'net profit', 'bottom line',
            'gross profit', 'operating income', 'EBIT', 'EBITDA',
            'profit margin', 'net margin', 'gross margin', 'operating margin',
            'profitability',
            
            # Per-share metrics
            'EPS', 'earnings per share', 'book value per share',
            'revenue per share', 'cash per share',
            
            # Growth metrics
            'growth', 'revenue growth', 'earnings growth',
            'year-over-year growth', 'YoY growth', 'QoQ growth',
            
            # Cash flow
            'cash flow', 'free cash flow', 'operating cash flow',
            'FCF', 'OCF', 'investing cash flow', 'financing cash flow',
            
            # Returns
            'ROE', 'ROA', 'ROIC', 'return on equity', 'return on assets',
            'return on invested capital', 'return on investment', 'ROI',
            
            # Valuation
            'P/E ratio', 'PE ratio', 'price to earnings',
            'P/B ratio', 'PB ratio', 'price to book',
            'P/S ratio', 'PS ratio', 'price to sales',
            'EV/EBITDA', 'enterprise value', 'market cap', 'market capitalization',
            'valuation', 'fair value',
            
            # Dividends
            'dividend', 'dividend yield', 'dividend per share',
            'payout ratio', 'dividend growth',
            
            # Balance sheet
            'assets', 'total assets', 'current assets',
            'liabilities', 'total liabilities', 'current liabilities',
            'equity', 'shareholders equity', 'book value',
            'debt', 'total debt', 'long-term debt', 'short-term debt',
            'debt to equity', 'debt ratio',
            
            # Efficiency
            'asset turnover', 'inventory turnover', 'receivables turnover',
            'working capital', 'current ratio', 'quick ratio',
            
            # Other
            'shares outstanding', 'float', 'beta',
            'volume', 'average volume', 'price', 'stock price',
        ]
    
    def _build_common_typos(self) -> Dict[str, str]:
        """Map common typos to correct metric names"""
        return {
            # Revenue (expanded)
            'reveune': 'revenue',
            'revenu': 'revenue',
            'revanue': 'revenue',
            'revnue': 'revenue',
            'reveneue': 'revenue',
            'reveneu': 'revenue',
            'revneue': 'revenue',
            'revenuw': 'revenue',
            'revvenue': 'revenue',
            'revenuee': 'revenue',
            'revenuw': 'revenue',
            'revenues': 'revenue',
            
            # Profit (expanded)
            'proft': 'profit',
            'profi': 'profit',
            'proffit': 'profit',
            'prfit': 'profit',
            'proofit': 'profit',
            'prpfit': 'profit',
            'profitt': 'profit',
            'profti': 'profit',
            'prfit': 'profit',
            'profits': 'profit',
            
            # Margin (expanded)
            'margn': 'margin',
            'marjin': 'margin',
            'magin': 'margin',
            'marginn': 'margin',
            'margon': 'margin',
            'margen': 'margin',
            'maring': 'margin',
            'margni': 'margin',
            'margins': 'margin',
            
            # Earnings (expanded)
            'earings': 'earnings',
            'earning': 'earnings',
            'earnigs': 'earnings',
            'earnins': 'earnings',
            'earnngs': 'earnings',
            'earnigns': 'earnings',
            'earinngs': 'earnings',
            'eanings': 'earnings',
            'eaarnings': 'earnings',
            
            # Growth (expanded)
            'groth': 'growth',
            'growt': 'growth',
            'groeth': 'growth',
            'grtowth': 'growth',
            'growwth': 'growth',
            'grwoth': 'growth',
            'growthh': 'growth',
            'gorowth': 'growth',
            'grwth': 'growth',
            
            # Profitability (expanded)
            'profitibility': 'profitability',
            'proftability': 'profitability',
            'profitabilty': 'profitability',
            'profitabilit': 'profitability',
            'profitabliity': 'profitability',
            'proftibility': 'profitability',
            'profitabilty': 'profitability',
            
            # Cash flow (expanded)
            'cashflow': 'cash flow',
            'cach flow': 'cash flow',
            'cash flo': 'cash flow',
            'casflow': 'cash flow',
            'cashflo': 'cash flow',
            'cash flwo': 'cash flow',
            'cahs flow': 'cash flow',
            'cash floww': 'cash flow',
            'csh flow': 'cash flow',
            
            # Valuation (expanded)
            'valution': 'valuation',
            'valuaton': 'valuation',
            'valuaion': 'valuation',
            'valation': 'valuation',
            'valuatiion': 'valuation',
            'valuaton': 'valuation',
            'valuuation': 'valuation',
            'vlauation': 'valuation',
            
            # Dividend (expanded)
            'divident': 'dividend',
            'dividnd': 'dividend',
            'divdend': 'dividend',
            'dividned': 'dividend',
            'divident': 'dividend',
            'dividennd': 'dividend',
            'diviend': 'dividend',
            'dividenn': 'dividend',
            'dividdend': 'dividend',
            'dividends': 'dividend',
            
            # Debt (expanded)
            'det': 'debt',
            'deb': 'debt',
            'debtt': 'debt',
            'debit': 'debt',
            'dbet': 'debt',
            'debts': 'debt',
            
            # Assets (expanded)
            'asets': 'assets',
            'asstes': 'assets',
            'asses': 'assets',
            'aseets': 'assets',
            'assts': 'assets',
            'assetss': 'assets',
            'assest': 'assets',
            'asets': 'assets',
            'assetts': 'assets',
            'asset': 'assets',
            
            # Equity (expanded)
            'equty': 'equity',
            'equit': 'equity',
            'eqity': 'equity',
            'equitty': 'equity',
            'equityy': 'equity',
            'euity': 'equity',
            'eqiuty': 'equity',
            'equiy': 'equity',
            
            # Liabilities (expanded)
            'liabilites': 'liabilities',
            'liabilties': 'liabilities',
            'liablities': 'liabilities',
            'liabiliites': 'liabilities',
            'liabillities': 'liabilities',
            'liabiities': 'liabilities',
            'liabilites': 'liabilities',
            'liability': 'liabilities',
            
            # EPS - Earnings Per Share
            'eps': 'EPS',
            'epss': 'EPS',
            'eeps': 'EPS',
            'esp': 'EPS',
            
            # EBITDA (expanded)
            'ebitda': 'EBITDA',
            'ebitdaa': 'EBITDA',
            'ebitdda': 'EBITDA',
            'ebiitda': 'EBITDA',
            'ebidta': 'EBITDA',
            'ebtida': 'EBITDA',
            
            # EBIT (expanded)
            'ebit': 'EBIT',
            'ebitt': 'EBIT',
            'ebiit': 'EBIT',
            
            # ROE - Return on Equity
            'roe': 'ROE',
            'roee': 'ROE',
            'reo': 'ROE',
            
            # ROA - Return on Assets
            'roa': 'ROA',
            'roaa': 'ROA',
            'rao': 'ROA',
            
            # ROIC - Return on Invested Capital
            'roic': 'ROIC',
            'roiic': 'ROIC',
            'roicc': 'ROIC',
            
            # P/E Ratio
            'p/e': 'P/E ratio',
            'pe ratio': 'P/E ratio',
            'pe': 'P/E ratio',
            'price to earnings': 'P/E ratio',
            'price earnings': 'P/E ratio',
            
            # Market Cap (expanded)
            'market cap': 'market cap',
            'marketcap': 'market cap',
            'market capitalization': 'market cap',
            'mkt cap': 'market cap',
            'marekt cap': 'market cap',
            'market caap': 'market cap',
            
            # Free Cash Flow
            'fcf': 'free cash flow',
            'free cashflow': 'free cash flow',
            'freecashflow': 'free cash flow',
            'free cash flo': 'free cash flow',
            
            # Operating Cash Flow
            'ocf': 'operating cash flow',
            'operating cashflow': 'operating cash flow',
            'operatingcashflow': 'operating cash flow',
            
            # Net Income (expanded)
            'net income': 'net income',
            'netincome': 'net income',
            'net incom': 'net income',
            'nett income': 'net income',
            'net incme': 'net income',
            
            # Gross Profit (expanded)
            'gross profit': 'gross profit',
            'grossprofit': 'gross profit',
            'gros profit': 'gross profit',
            'gross proft': 'gross profit',
            
            # Operating Income (expanded)
            'operating income': 'operating income',
            'operatingincome': 'operating income',
            'operating incom': 'operating income',
            'operting income': 'operating income',
            
            # Sales (expanded)
            'sales': 'sales',
            'salez': 'sales',
            'salles': 'sales',
            'sles': 'sales',
            'sale': 'sales',
        }
    
    def correct_metric(
        self,
        query: str,
        min_confidence: float = 0.6
    ) -> Tuple[Optional[str], float, bool]:
        """
        Correct a potentially misspelled metric name.
        
        Args:
            query: The query string (potentially misspelled)
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (corrected_metric, confidence, should_confirm)
            - corrected_metric: Corrected metric name or None
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
        exact = self.metric_matcher.find_exact(query_clean)
        if exact:
            return exact, 1.0, False
        
        # Fuzzy match
        matches = self.metric_matcher.find_best_match(
            query_clean,
            threshold=min_confidence,
            top_n=3
        )
        
        if not matches:
            return None, 0.0, False
        
        best_match, confidence = matches[0]
        
        # Determine if we should ask for confirmation
        should_confirm = confidence < 0.85
        
        return best_match, confidence, should_confirm
    
    def suggest_metrics(
        self,
        query: str,
        max_suggestions: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Suggest possible metric names for a query.
        
        Args:
            query: Query string
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of (metric_name, confidence) tuples
        """
        if not query or len(query) < 2:
            return []
        
        # Try prefix matching first
        prefix_matches = self.metric_matcher.find_with_prefix(query, max_results=max_suggestions)
        if prefix_matches:
            suggestions = []
            for match in prefix_matches:
                similarity = calculate_similarity(query, match)
                suggestions.append((match, similarity))
            return sorted(suggestions, key=lambda x: x[1], reverse=True)[:max_suggestions]
        
        # Fall back to fuzzy matching
        return self.metric_matcher.find_best_match(
            query,
            threshold=0.5,
            top_n=max_suggestions
        )

