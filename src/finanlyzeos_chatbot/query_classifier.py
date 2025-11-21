"""Query classification system for fast path routing."""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

LOGGER = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels for routing decisions."""
    SIMPLE = "simple"        # Direct database lookup, no RAG needed
    MEDIUM = "medium"        # Basic RAG retrieval
    COMPLEX = "complex"      # Full RAG pipeline with all features


class QueryType(Enum):
    """Types of queries for specialized handling."""
    FACTUAL = "factual"           # Simple fact lookup (revenue, price, etc.)
    COMPARISON = "comparison"     # Compare companies/metrics
    ANALYSIS = "analysis"         # Deep analysis requiring context
    FORECAST = "forecast"         # ML forecasting queries
    HELP = "help"                # Help/documentation requests
    COMMAND = "command"           # System commands (ingest, etc.)


class QueryClassifier:
    """Classifies queries for optimal routing and performance."""
    
    def __init__(self):
        # Simple factual query patterns (fast path)
        self.simple_patterns = [
            # Direct metric queries
            r'\b(?:what|show|get|give)\s+(?:me\s+)?(?:the\s+)?(?:current\s+)?(?:latest\s+)?(revenue|price|market\s+cap|pe\s+ratio|earnings|profit|sales)\s+(?:of\s+|for\s+)?([A-Z]{1,5})\b',
            r'\b([A-Z]{1,5})\s+(revenue|price|market\s+cap|pe\s+ratio|earnings|profit|sales)\b',
            r'\bhow\s+much\s+(?:is\s+)?([A-Z]{1,5})\s+(?:worth|valued|trading)\b',
            r'\b([A-Z]{1,5})\s+(?:stock\s+)?price\b',
            
            # Simple status queries
            r'\b(?:is\s+)?([A-Z]{1,5})\s+(?:a\s+)?(?:good\s+)?(?:buy|investment|stock)\b',
            r'\bwhat\s+(?:is\s+)?([A-Z]{1,5})\b',
        ]
        
        # Complex analysis patterns (full RAG pipeline)
        self.complex_patterns = [
            # Analysis and comparison
            r'\b(?:analyze|analysis|compare|comparison|evaluate|assessment)\b',
            r'\b(?:why|how|explain|reason|cause|impact|effect)\b.*\b(?:revenue|earnings|performance|growth)\b',
            r'\b(?:trend|trends|pattern|patterns|outlook|forecast|prediction)\b',
            r'\b(?:competitive|competition|vs|versus|against|compared\s+to)\b',
            r'\b(?:risk|risks|opportunity|opportunities|threat|threats)\b',
            
            # Multi-step queries
            r'\b(?:and|also|additionally|furthermore|moreover)\b.*\b(?:what|how|why|show|compare)\b',
            r'\b(?:first|second|third|then|next|finally|also)\b',
        ]
        
        # Forecast patterns
        self.forecast_patterns = [
            r'\b(?:forecast|predict|projection|future|next\s+year|2024|2025|2026)\b',
            r'\b(?:will|expected|estimate|target|guidance)\b.*\b(?:revenue|earnings|growth)\b',
            r'\b(?:ml|machine\s+learning|ai|artificial\s+intelligence)\s+(?:forecast|prediction)\b',
        ]
        
        # Command patterns
        self.command_patterns = [
            r'\bingest\s+[A-Z]{1,5}\b',
            r'\b(?:help|documentation|docs|manual)\b',
            r'\b(?:status|health|system)\b',
        ]
        
        # Compile patterns for performance
        self.simple_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.simple_patterns]
        self.complex_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.complex_patterns]
        self.forecast_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.forecast_patterns]
        self.command_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.command_patterns]
    
    def classify_query(self, query: str) -> Tuple[QueryComplexity, QueryType, Dict[str, any]]:
        """
        Classify a query for optimal routing.
        
        Returns:
            Tuple of (complexity, type, metadata)
        """
        query_lower = query.lower().strip()
        metadata = {"original_query": query, "tickers": self._extract_tickers(query)}
        
        # Check for commands first
        if any(pattern.search(query) for pattern in self.command_regex):
            return QueryComplexity.SIMPLE, QueryType.COMMAND, metadata
        
        # Check for forecasting queries
        if any(pattern.search(query) for pattern in self.forecast_regex):
            return QueryComplexity.COMPLEX, QueryType.FORECAST, metadata
        
        # Check for simple factual queries
        if any(pattern.search(query) for pattern in self.simple_regex):
            # Additional checks for simplicity
            if len(query.split()) <= 8 and len(metadata["tickers"]) <= 2:
                return QueryComplexity.SIMPLE, QueryType.FACTUAL, metadata
        
        # Check for complex analysis queries
        if any(pattern.search(query) for pattern in self.complex_regex):
            return QueryComplexity.COMPLEX, QueryType.ANALYSIS, metadata
        
        # Check for comparison queries
        if self._is_comparison_query(query):
            complexity = QueryComplexity.COMPLEX if len(metadata["tickers"]) > 2 else QueryComplexity.MEDIUM
            return complexity, QueryType.COMPARISON, metadata
        
        # Default classification based on query length and ticker count
        word_count = len(query.split())
        ticker_count = len(metadata["tickers"])
        
        if word_count <= 6 and ticker_count <= 1:
            return QueryComplexity.SIMPLE, QueryType.FACTUAL, metadata
        elif word_count <= 15 and ticker_count <= 3:
            return QueryComplexity.MEDIUM, QueryType.ANALYSIS, metadata
        else:
            return QueryComplexity.COMPLEX, QueryType.ANALYSIS, metadata
    
    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols from query."""
        # Simple ticker extraction (1-5 uppercase letters)
        ticker_pattern = r'\b[A-Z]{1,5}\b'
        potential_tickers = re.findall(ticker_pattern, query)
        
        # Filter out common words that look like tickers
        common_words = {'THE', 'AND', 'OR', 'FOR', 'TO', 'OF', 'IN', 'ON', 'AT', 'BY', 'IS', 'ARE', 'WAS', 'WERE', 'BE', 'BEEN', 'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'MAY', 'MIGHT', 'CAN', 'GET', 'GOT', 'PUT', 'SET', 'LET', 'ALL', 'ANY', 'NEW', 'OLD', 'BIG', 'TOP', 'LOW', 'HIGH', 'GOOD', 'BAD', 'BEST', 'LAST', 'NEXT', 'FIRST', 'YEAR', 'YEARS', 'DAY', 'DAYS', 'TIME', 'TIMES', 'WAY', 'WAYS', 'WORK', 'WORKS', 'MAKE', 'MAKES', 'TAKE', 'TAKES', 'COME', 'COMES', 'LOOK', 'LOOKS', 'USE', 'USES', 'FIND', 'FINDS', 'GIVE', 'GIVES', 'TELL', 'TELLS', 'ASK', 'ASKS', 'TRY', 'TRIES', 'TURN', 'TURNS', 'MOVE', 'MOVES', 'PLAY', 'PLAYS', 'SHOW', 'SHOWS', 'HELP', 'HELPS', 'CALL', 'CALLS', 'WANT', 'WANTS', 'NEED', 'NEEDS', 'SEEM', 'SEEMS', 'FEEL', 'FEELS', 'KNOW', 'KNOWS', 'THINK', 'THINKS', 'SEE', 'SEES', 'HEAR', 'HEARS', 'LEAVE', 'LEAVES', 'KEEP', 'KEEPS', 'START', 'STARTS', 'STOP', 'STOPS', 'OPEN', 'OPENS', 'CLOSE', 'CLOSES', 'WRITE', 'WRITES', 'READ', 'READS', 'COUNT', 'COUNTS', 'PART', 'PARTS', 'GROUP', 'GROUPS', 'PLACE', 'PLACES', 'CASE', 'CASES', 'POINT', 'POINTS', 'HAND', 'HANDS', 'EYE', 'EYES', 'FACE', 'FACES', 'FACT', 'FACTS', 'LIFE', 'LIVES', 'WEEK', 'WEEKS', 'MONTH', 'MONTHS', 'STATE', 'STATES', 'AREA', 'AREAS', 'BOOK', 'BOOKS', 'LINE', 'LINES', 'RIGHT', 'RIGHTS', 'STUDY', 'STUDIES', 'LOT', 'LOTS', 'WATER', 'WATERS', 'WORD', 'WORDS', 'MONEY', 'MONEYS', 'STORY', 'STORIES', 'JOB', 'JOBS', 'NIGHT', 'NIGHTS', 'END', 'ENDS', 'SIDE', 'SIDES', 'KIND', 'KINDS', 'HEAD', 'HEADS', 'HOUSE', 'HOUSES', 'SERVICE', 'SERVICES', 'FRIEND', 'FRIENDS', 'FATHER', 'FATHERS', 'POWER', 'POWERS', 'HOUR', 'HOURS', 'GAME', 'GAMES', 'OFFICE', 'OFFICES', 'DOOR', 'DOORS', 'HEALTH', 'HEALTHS', 'PERSON', 'PERSONS', 'ART', 'ARTS', 'WAR', 'WARS', 'HISTORY', 'HISTORIES', 'PARTY', 'PARTIES', 'RESULT', 'RESULTS', 'CHANGE', 'CHANGES', 'MORNING', 'MORNINGS', 'REASON', 'REASONS', 'RESEARCH', 'RESEARCHES', 'GIRL', 'GIRLS', 'GUY', 'GUYS', 'MOMENT', 'MOMENTS', 'AIR', 'AIRS', 'TEACHER', 'TEACHERS', 'FORCE', 'FORCES', 'EDUCATION', 'EDUCATIONS'}
        
        return [ticker for ticker in potential_tickers if ticker not in common_words]
    
    def _is_comparison_query(self, query: str) -> bool:
        """Check if query is asking for comparison."""
        comparison_indicators = [
            'vs', 'versus', 'compared to', 'compare', 'comparison', 'against',
            'better than', 'worse than', 'difference between', 'which is better'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in comparison_indicators)
    
    def get_fast_path_config(self, complexity: QueryComplexity) -> Dict[str, any]:
        """Get configuration for fast path processing."""
        if complexity == QueryComplexity.SIMPLE:
            return {
                "use_rag": False,
                "use_reranking": False,
                "use_multi_hop": False,
                "use_claim_verification": False,
                "max_sec_results": 0,
                "max_uploaded_results": 0,
                "skip_context_building": True,
            }
        elif complexity == QueryComplexity.MEDIUM:
            return {
                "use_rag": True,
                "use_reranking": False,
                "use_multi_hop": False,
                "use_claim_verification": False,
                "max_sec_results": 3,
                "max_uploaded_results": 2,
                "skip_context_building": False,
            }
        else:  # COMPLEX
            return {
                "use_rag": True,
                "use_reranking": True,
                "use_multi_hop": True,
                "use_claim_verification": True,
                "max_sec_results": 5,
                "max_uploaded_results": 3,
                "skip_context_building": False,
            }


# Global classifier instance
_classifier = QueryClassifier()


def classify_query(query: str) -> Tuple[QueryComplexity, QueryType, Dict[str, any]]:
    """Classify a query using the global classifier."""
    return _classifier.classify_query(query)


def get_fast_path_config(complexity: QueryComplexity) -> Dict[str, any]:
    """Get fast path configuration for a complexity level."""
    return _classifier.get_fast_path_config(complexity)
