"""
Company group detection and expansion for natural language queries.

Handles:
- Popular tech groups: FAANG, MAMAA, Magnificent 7, etc.
- Industry groups: Big Tech, Big Banks, Big Pharma, etc.
- Index groups: Dow 30, S&P 500 leaders, etc.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import re


class GroupType(Enum):
    """Types of company groups"""
    TECH_ACRONYM = "tech_acronym"      # FAANG, MAMAA, etc.
    INDUSTRY = "industry"               # Big Tech, Big Banks, etc.
    INDEX = "index"                     # Dow 30, S&P leaders, etc.
    CATEGORY = "category"               # Dividend aristocrats, growth stocks, etc.
    CUSTOM = "custom"                   # User-defined or specific


@dataclass
class CompanyGroup:
    """
    Represents a detected company group.
    """
    name: str                    # Group name (e.g., "FAANG")
    group_type: GroupType       # Type of group
    tickers: List[str]          # Constituent tickers
    confidence: float           # Confidence score (0.0 to 1.0)
    position: int              # Position in text
    
    def __repr__(self):
        return (f"CompanyGroup(name='{self.name}', "
                f"type={self.group_type.value}, "
                f"tickers={self.tickers}, "
                f"confidence={self.confidence:.2f})")


class CompanyGroupDetector:
    """
    Detect and expand company groups in natural language queries.
    """
    
    # Tech acronym groups - EXPANDED
    TECH_ACRONYM_GROUPS = {
        'FAANG': ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
        'FANG': ['META', 'AMZN', 'NFLX', 'GOOGL'],
        'MAMAA': ['META', 'AAPL', 'MSFT', 'AMZN', 'GOOGL'],
        'MANAA': ['META', 'AAPL', 'NFLX', 'AMZN', 'GOOGL'],
        'GAFAM': ['GOOGL', 'AAPL', 'META', 'AMZN', 'MSFT'],
        'MAG7': ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        'MAGNIFICENT7': ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        'MAG 7': ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        'MAGNIFICENT 7': ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'],
        # NEW: More tech acronyms
        'MATANA': ['MSFT', 'AAPL', 'TSLA', 'AMZN', 'NVDA', 'GOOGL'],
        'GRANOLAS': ['GSK', 'ROCHE', 'ASML', 'NESN', 'NOVO', 'L\'OREAL', 'LVMH', 'AZN', 'SAP', 'SANOFI'],  # European tech
    }
    
    # Industry groups - MASSIVELY EXPANDED
    INDUSTRY_GROUPS = {
        'BIG TECH': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
        'BIG BANKS': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS'],
        'BIG PHARMA': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'LLY'],
        'BIG OIL': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
        'BIG RETAIL': ['WMT', 'TGT', 'COST', 'HD', 'LOW'],
        'TECH GIANTS': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA'],
        'MEGA CAP TECH': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
        # NEW: More industry groups
        'BIG AUTO': ['TSLA', 'F', 'GM', 'TM', 'HMC'],
        'BIG AIRLINES': ['DAL', 'UAL', 'AAL', 'LUV', 'ALK'],
        'BIG DEFENSE': ['LMT', 'BA', 'RTX', 'NOC', 'GD'],
        'BIG TELECOM': ['VZ', 'T', 'TMUS', 'CMCSA'],
        'BIG MEDIA': ['DIS', 'CMCSA', 'NFLX', 'WBD', 'PARA'],
        'CLOUD COMPANIES': ['MSFT', 'AMZN', 'GOOGL', 'CRM', 'ORCL'],
        'CHIP MAKERS': ['NVDA', 'AMD', 'INTC', 'TSM', 'QCOM'],
        'SEMICONDUCTOR': ['NVDA', 'AMD', 'INTC', 'TSM', 'QCOM', 'AVGO'],
        'PAYMENT PROCESSORS': ['V', 'MA', 'PYPL', 'SQ'],
        'STREAMING': ['NFLX', 'DIS', 'PARA', 'WBD'],
    }
    
    # Index-based groups - EXPANDED
    INDEX_GROUPS = {
        'DOW 30': ['AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'MCD', 'CAT', 'V', 'BA', 'JNJ'],  # Top 10 for brevity
        'DJIA': ['AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'MCD', 'CAT', 'V', 'BA', 'JNJ'],
        # NEW: More index groups
        'S&P 500 LEADERS': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'V', 'UNH'],
        'NASDAQ 100 LEADERS': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST', 'NFLX'],
    }
    
    # NEW: Category-based groups
    CATEGORY_GROUPS = {
        'DIVIDEND ARISTOCRATS': ['JNJ', 'PG', 'KO', 'PEP', 'MCD', 'WMT'],
        'GROWTH STOCKS': ['NVDA', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX'],
        'VALUE STOCKS': ['BRK.B', 'JPM', 'JNJ', 'XOM', 'CVX', 'PG'],
        'BLUE CHIPS': ['AAPL', 'MSFT', 'JNJ', 'JPM', 'WMT', 'PG', 'KO'],
        'MEGA CAPS': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK.B'],
    }
    
    # NEW: False positive patterns (DON'T detect as groups)
    FALSE_POSITIVE_PATTERNS = [
        # Company names that contain group keywords
        r'\b(?:big\s+lots|big\s+5\s+sporting)\b',
        # Questions about groups
        r'\b(?:what|which)\s+(?:is|are)\s+(?:in\s+)?(?:the\s+)?(?:FAANG|MAG7)\b',
        r'\bhow\s+many\s+(?:companies|stocks)\s+in\b',
    ]
    
    # Pattern templates for detection
    TECH_ACRONYM_PATTERN = r'\b({acronyms})\b'
    INDUSTRY_PATTERN = r'\b(big\s+(?:tech|banks?|pharma|oil|retail|auto|airlines?|defense|telecom|media)|tech\s+giants?|mega\s+cap\s+tech|cloud\s+companies|chip\s+makers?|semiconductors?|payment\s+processors?|streaming)\b'
    INDEX_PATTERN = r'\b(dow\s+30|djia|dow\s+jones|s&p\s+500\s+leaders?|nasdaq\s+100\s+leaders?)\b'
    CATEGORY_PATTERN = r'\b(dividend\s+aristocrats?|growth\s+stocks?|value\s+stocks?|blue\s+chips?|mega\s+caps?)\b'
    
    def __init__(self):
        """Initialize the company group detector"""
        # Create acronym pattern
        acronym_list = '|'.join(re.escape(k) for k in self.TECH_ACRONYM_GROUPS.keys())
        self._acronym_pattern = re.compile(
            self.TECH_ACRONYM_PATTERN.format(acronyms=acronym_list),
            re.IGNORECASE
        )
        
        # Create industry pattern
        self._industry_pattern = re.compile(self.INDUSTRY_PATTERN, re.IGNORECASE)
        
        # Create index pattern
        self._index_pattern = re.compile(self.INDEX_PATTERN, re.IGNORECASE)
        
        # Create category pattern
        self._category_pattern = re.compile(self.CATEGORY_PATTERN, re.IGNORECASE)
        
        # Create false positive patterns
        self._false_positive_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.FALSE_POSITIVE_PATTERNS
        ]
    
    def detect_groups(self, text: str) -> List[CompanyGroup]:
        """
        Detect all company groups in text.
        
        Args:
            text: The query text to analyze
            
        Returns:
            List of CompanyGroup objects
        """
        if not text:
            return []
        
        # NEW: Check for false positives first
        if self._is_false_positive(text):
            return []
        
        groups = []
        
        # Detect tech acronym groups
        groups.extend(self._detect_tech_acronyms(text))
        
        # Detect industry groups
        groups.extend(self._detect_industry_groups(text))
        
        # Detect index groups
        groups.extend(self._detect_index_groups(text))
        
        # Detect category groups
        groups.extend(self._detect_category_groups(text))
        
        # Sort by position
        groups.sort(key=lambda x: x.position)
        
        return groups
    
    def _detect_tech_acronyms(self, text: str) -> List[CompanyGroup]:
        """Detect tech acronym groups (FAANG, MAG7, etc.)"""
        groups = []
        
        for match in self._acronym_pattern.finditer(text):
            group_name = match.group(0).upper()
            
            # Normalize group name
            normalized_name = self._normalize_group_name(group_name)
            
            if normalized_name in self.TECH_ACRONYM_GROUPS:
                tickers = self.TECH_ACRONYM_GROUPS[normalized_name]
                confidence = self._calculate_confidence(text, "tech_acronym", group_name)
                
                groups.append(CompanyGroup(
                    name=group_name,
                    group_type=GroupType.TECH_ACRONYM,
                    tickers=tickers,
                    confidence=confidence,
                    position=match.start()
                ))
        
        return groups
    
    def _detect_industry_groups(self, text: str) -> List[CompanyGroup]:
        """Detect industry groups (Big Tech, Big Banks, etc.)"""
        groups = []
        
        for match in self._industry_pattern.finditer(text):
            group_name = match.group(0)
            normalized_name = group_name.upper()
            
            if normalized_name in self.INDUSTRY_GROUPS:
                tickers = self.INDUSTRY_GROUPS[normalized_name]
                confidence = self._calculate_confidence(text, "industry", group_name)
                
                groups.append(CompanyGroup(
                    name=group_name,
                    group_type=GroupType.INDUSTRY,
                    tickers=tickers,
                    confidence=confidence,
                    position=match.start()
                ))
        
        return groups
    
    def _detect_index_groups(self, text: str) -> List[CompanyGroup]:
        """Detect index-based groups (Dow 30, etc.)"""
        groups = []
        
        for match in self._index_pattern.finditer(text):
            group_name = match.group(0)
            normalized_name = 'DOW 30' if 'dow' in group_name.lower() else group_name.upper()
            
            if normalized_name in self.INDEX_GROUPS:
                tickers = self.INDEX_GROUPS[normalized_name]
                confidence = self._calculate_confidence(text, "index", group_name)
                
                groups.append(CompanyGroup(
                    name=group_name,
                    group_type=GroupType.INDEX,
                    tickers=tickers,
                    confidence=confidence,
                    position=match.start()
                ))
        
        return groups
    
    def _detect_category_groups(self, text: str) -> List[CompanyGroup]:
        """Detect category groups (dividend aristocrats, growth stocks, etc.)"""
        groups = []
        
        for match in self._category_pattern.finditer(text):
            group_name = match.group(0)
            normalized_name = group_name.upper()
            
            # Handle plurals
            if normalized_name.endswith('S') and normalized_name[:-1] in self.CATEGORY_GROUPS:
                normalized_name = normalized_name[:-1]
            
            if normalized_name in self.CATEGORY_GROUPS:
                tickers = self.CATEGORY_GROUPS[normalized_name]
                confidence = self._calculate_confidence_enhanced(text, "category", group_name)
                
                groups.append(CompanyGroup(
                    name=group_name,
                    group_type=GroupType.CATEGORY,
                    tickers=tickers,
                    confidence=confidence,
                    position=match.start()
                ))
        
        return groups
    
    def _is_false_positive(self, text: str) -> bool:
        """Check if text contains false positive patterns"""
        for pattern in self._false_positive_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _normalize_group_name(self, name: str) -> str:
        """Normalize group name for lookup (ENHANCED)"""
        # Handle variations
        name_upper = name.upper()
        
        # MAG 7 variations
        if 'MAG' in name_upper and '7' in name_upper:
            return 'MAG7'
        if 'MAGNIFICENT' in name_upper and '7' in name_upper:
            return 'MAGNIFICENT7'
        
        # Handle plurals for categories
        if name_upper.endswith('S') and name_upper[:-1] in self.CATEGORY_GROUPS:
            return name_upper[:-1]
        
        return name_upper
    
    def _calculate_confidence(self, text: str, group_type: str, group_name: str) -> float:
        """Calculate confidence (LEGACY - use _calculate_confidence_enhanced)"""
        return self._calculate_confidence_enhanced(text, group_type, group_name)
    
    def _calculate_confidence_enhanced(self, text: str, group_type: str, group_name: str) -> float:
        """
        Calculate confidence for group detection (ENHANCED).
        Context-aware scoring similar to other Phase 1-4 features.
        """
        confidence = 0.88  # Base confidence (groups are usually explicit)
        
        # Boost for tech acronyms (very explicit and well-known)
        if group_type == "tech_acronym":
            confidence += 0.10
        
        # Boost for industry groups with clear modifiers
        if group_type == "industry":
            if any(word in text.lower() for word in ['big', 'mega', 'giants']):
                confidence += 0.06
        
        # Boost for category groups (specific investment categories)
        if group_type == "category":
            confidence += 0.04
        
        # Boost for financial context
        financial_context = ['revenue', 'profit', 'performance', 'compare', 'analyze', 'show']
        if any(term in text.lower() for term in financial_context):
            confidence += 0.04
        
        # Penalty if surrounded by unrelated context
        if len(text.split()) > 20:  # Long text might have group as incidental mention
            confidence -= 0.04
        
        # Penalty if no clear action/query context
        if not any(word in text.lower() for word in ['show', 'get', 'analyze', 'compare', 'what', 'how']):
            confidence -= 0.03
        
        return min(1.0, max(0.7, confidence))
    
    def has_group(self, text: str) -> bool:
        """
        Quick check if text contains company groups.
        
        Returns:
            True if group detected, False otherwise
        """
        if not text:
            return False
        
        groups = self.detect_groups(text)
        return len(groups) > 0
    
    def expand_group(self, group_name: str) -> Optional[List[str]]:
        """
        Expand a group name to its constituent tickers (ENHANCED).
        
        Args:
            group_name: Name of the group to expand
            
        Returns:
            List of tickers or None if group not found
        """
        normalized_name = self._normalize_group_name(group_name.upper())
        
        # Check all group types
        if normalized_name in self.TECH_ACRONYM_GROUPS:
            return self.TECH_ACRONYM_GROUPS[normalized_name]
        elif normalized_name in self.INDUSTRY_GROUPS:
            return self.INDUSTRY_GROUPS[normalized_name]
        elif normalized_name in self.INDEX_GROUPS:
            return self.INDEX_GROUPS[normalized_name]
        elif normalized_name in self.CATEGORY_GROUPS:
            return self.CATEGORY_GROUPS[normalized_name]
        
        return None

