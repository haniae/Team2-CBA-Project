"""
Contextual metric inference engine.

Infers financial metrics from contextual clues when not explicitly stated.

Examples:
- "Apple made $400B" → infers 'revenue'
- "Trading at 35x" → infers 'pe_ratio'
- "Earned $5 per share" → infers 'eps'
- "Market cap is $3T" → infers 'market_cap'
- "Margins are 36%" → infers 'margins'
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from collections import OrderedDict
import re


@dataclass
class InferredMetric:
    """Represents an inferred metric from context"""
    metric_id: str          # Canonical metric identifier
    confidence: float       # Confidence score (0.0 to 1.0)
    context: str           # What triggered the inference
    value: Optional[str]   # Extracted value if present
    position: int          # Position in text where detected
    
    def __repr__(self):
        return (f"InferredMetric(metric_id={self.metric_id}, "
                f"confidence={self.confidence:.2f}, "
                f"value={self.value})")


class MetricInferenceEngine:
    """
    Infer financial metrics from contextual patterns.
    
    Uses value patterns, verb patterns, and context to infer which metric
    is being discussed even when not explicitly named.
    """
    
    # Contextual patterns that strongly indicate specific metrics
    # IMPORTANT: Order matters - check most specific patterns first
    # Using OrderedDict to guarantee order - MASSIVELY EXPANDED
    CONTEXTUAL_PATTERNS = OrderedDict([
        # EPS patterns (CHECK FIRST - before revenue to avoid "earned" confusion)
        ('eps', [
            r'\b(?:earned|made|reported|posted)\s+\$[\d\.]+\s+(?:per\s+share|a\s+share|EPS)\b',
            r'\bEPS\s+(?:of|is|was|came\s+in\s+at)?\s+\$[\d\.]+\b',
            r'\b\$[\d\.]+\s+(?:per\s+share|EPS|a\s+share)\b',
            r'\bearnings\s+per\s+share\s+(?:of|is|was)?\s+\$[\d\.]+\b',
            # NEW: More variations
            r'\bdelivered\s+\$[\d\.]+\s+(?:per\s+share|EPS)\b',
            r'\bproduced\s+\$[\d\.]+\s+(?:per\s+share|in\s+EPS)\b',
        ]),
        
        # Revenue patterns (after EPS check)
        ('revenue', [
            # Made/earned/generated + $ amount (but not per share)
            r'\b(?:made|generated|brought\s+in|posted|reported)\s+\$[\d\.,]+[BMK]\b',
            r'\b\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:revenue|sales)\b',
            r'\b(?:revenue|sales)\s+(?:of|was|is|reached?|totaled?)\s+\$[\d\.,]+[BMK]?\b',
            # Revenue-specific verbs
            r'\b(?:sold|sales\s+of|revenues?\s+of)\s+\$[\d\.,]+[BMK]?\b',
            r'\btopline\s+(?:of|was|is)?\s+\$[\d\.,]+[BMK]?\b',
            # NEW: More variations
            r'\b(?:booking|booked|recorded)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:revenue|sales)\b',
            r'\b(?:delivered|producing|produced)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:revenue|sales)\b',
        ]),
        
        # Net income/profit patterns
        ('net_income', [
            r'\b(?:profit|net\s+income|earnings|income)\s+(?:of|was|is|totaled?)\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:profit|net\s+income|income)\b',
            r'\bbottom\s+line\s+(?:of|was|is)?\s+\$[\d\.,]+[BMK]?\b',
            # NEW: More variations
            r'\b(?:posted|reported|delivered)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:profit|net\s+income)\b',
            r'\b(?:earned|made)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:profit|net\s+income)\b',
        ]),
        
        # P/E ratio patterns
        ('pe_ratio', [
            r'\btrading\s+at\s+(\d+(?:\.\d+)?)[xX×]\b',
            r'\bP/E\s+(?:ratio\s+)?(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\b(\d+(?:\.\d+)?)[xX×]\s+(?:earnings|P/E)\b',
            r'\bprice\s+to\s+earnings\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
            # NEW: More variations
            r'\bmultiple\s+(?:of|is)?\s+(\d+(?:\.\d+)?)[xX×]?\b',
            r'\bvaluation\s+multiple\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
        ]),
        
        # Market cap patterns
        ('market_cap', [
            r'\bvalued\s+at\s+\$[\d\.,]+[BMT]\b',
            r'\bmarket\s+cap(?:italization)?\s+(?:of|is|was)?\s+\$[\d\.,]+[BMT]\b',
            r'\bworth\s+\$[\d\.,]+[BMT]\b',
            r'\b\$[\d\.,]+[BMT]\s+market\s+cap\b',
            # NEW: More variations
            r'\bmarket\s+value\s+(?:of|is)?\s+\$[\d\.,]+[BMT]\b',
            r'\bvaluation\s+(?:of|is)?\s+\$[\d\.,]+[BMT]\b',
        ]),
        
        # Margin patterns (percentage)
        ('margin', [
            r'\bmargins?\s+(?:of|are|is|was|were)\s+(\d+(?:\.\d+)?)%\b',
            r'\b(\d+(?:\.\d+)?)%\s+(?:profit\s+)?margins?\b',
            r'\bmargins?\s+(?:at|around)\s+(\d+(?:\.\d+)?)%\b',
            # NEW: More variations
            r'\b(?:operating|gross|net)\s+margins?\s+(?:of|are)?\s+(\d+(?:\.\d+)?)%\b',
            r'\bprofitability\s+(?:of|is)?\s+(\d+(?:\.\d+)?)%\b',
        ]),
        
        # Growth rate patterns
        ('growth_rate', [
            r'\bgrowing\s+at\s+(\d+(?:\.\d+)?)%\b',
            r'\b(\d+(?:\.\d+)?)%\s+growth\b',
            r'\bgrowth\s+(?:rate\s+)?(?:of|is|was)\s+(\d+(?:\.\d+)?)%\b',
            r'\bCAGR\s+(?:of|is)\s+(\d+(?:\.\d+)?)%\b',
            # NEW: More variations
            r'\b(?:YoY|year-over-year|y-o-y)\s+growth\s+(?:of|is)?\s+(\d+(?:\.\d+)?)%\b',
            r'\bexpanding\s+at\s+(\d+(?:\.\d+)?)%\b',
            r'\bgrowth\s+rate:\s+(\d+(?:\.\d+)?)%\b',
        ]),
        
        # Dividend patterns
        ('dividend', [
            r'\b(?:paid|pays?|paying|distributed)\s+\$[\d\.]+\s+(?:dividend|per\s+share)\b',
            r'\bdividend\s+(?:of|is|was)?\s+\$[\d\.]+\b',
            r'\b\$[\d\.]+\s+dividend\b',
            r'\bdividend\s+yield\s+(?:of|is)?\s+(\d+(?:\.\d+)?)%\b',
            # NEW: More variations
            r'\b(?:payout|distribution)\s+(?:of|is)?\s+\$[\d\.]+\b',
            r'\breturning\s+\$[\d\.]+\s+to\s+shareholders\b',
        ]),
        
        # Cash flow patterns
        ('free_cash_flow', [
            r'\b(?:FCF|free\s+cash\s+flow)\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:FCF|free\s+cash\s+flow)\b',
            r'\bgenerated\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:free\s+)?cash\s+flow\b',
            # NEW: More variations
            r'\b(?:produced|generating)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:FCF|free\s+cash\s+flow)\b',
            r'\bcash\s+generation\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
        ]),
        
        # Debt patterns
        ('total_debt', [
            r'\b(?:debt|borrowing|borrowings)\s+(?:of|is|was|stands\s+at)?\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+in\s+debt\b',
            r'\bowes\s+\$[\d\.,]+[BMK]?\b',
            # NEW: More variations
            r'\b(?:carrying|holds?)\s+\$[\d\.,]+[BMK]?\s+in\s+debt\b',
            r'\bleverage\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
        ]),
        
        # Return metrics
        ('roe', [
            r'\bROE\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)%\b',
            r'\breturn\s+on\s+equity\s+(?:of|is)?\s+(\d+(?:\.\d+)?)%\b',
        ]),
        ('roa', [
            r'\bROA\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)%\b',
            r'\breturn\s+on\s+assets\s+(?:of|is)?\s+(\d+(?:\.\d+)?)%\b',
        ]),
        
        # NEW: EBITDA patterns
        ('ebitda', [
            r'\bEBITDA\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+(?:in\s+)?EBITDA\b',
        ]),
        
        # NEW: Operating income patterns
        ('operating_income', [
            r'\b(?:operating\s+income|EBIT)\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+(?:in\s+)?operating\s+income\b',
        ]),
        
        # NEW: Book value patterns
        ('book_value', [
            r'\bbook\s+value\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
            r'\b\$[\d\.,]+[BMK]?\s+book\s+value\b',
        ]),
        
        # NEW: Operating cash flow patterns
        ('operating_cash_flow', [
            r'\$[\d\.,]+[BMK]?\s+in\s+operating\s+cash\s+flow\b',  # "$25B in operating cash flow" - CHECK FIRST (no \b before $)
            r'\b(?:OCF|operating\s+cash\s+flow)\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:OCF|operating\s+cash\s+flow)\b',  # No \b before $
            r'\$[\d\.,]+[BMK]?\s+operating\s+cash\s+flow\b',  # "$25B operating cash flow" (no \b before $)
            r'\b(?:generated|produced)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:operating\s+)?cash\s+flow\b',
        ]),
        
        # NEW: Working capital patterns
        ('working_capital', [
            r'\bworking\s+capital\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+working\s+capital\b',  # "$8B working capital" (no \b before $)
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?working\s+capital\b',  # No \b before $
            r'\bWC\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
        ]),
        
        # NEW: Current ratio patterns
        ('current_ratio', [
            r'\bcurrent\s+ratio\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\b(\d+(?:\.\d+)?)\s+current\s+ratio\b',
            r'\b(?:liquidity\s+)?ratio\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
        ]),
        
        # NEW: Quick ratio patterns
        ('quick_ratio', [
            r'\bquick\s+ratio\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\b(\d+(?:\.\d+)?)\s+quick\s+ratio\b',
            r'\bacid\s+test\s+(?:ratio\s+)?(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
        ]),
        
        # NEW: Debt-to-equity patterns
        ('debt_to_equity', [
            r'\bdebt[\s\-]to[\s\-]equity\s+(?:ratio\s+)?(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\b(\d+(?:\.\d+)?)\s+debt[\s\-]to[\s\-]equity\b',
            r'\bD/E\s+(?:ratio\s+)?(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
            r'\bD/E\s+ratio\s+(\d+(?:\.\d+)?)\b',  # "D/E ratio 0.3"
        ]),
        
        # NEW: Interest coverage patterns
        ('interest_coverage', [
            r'\binterest\s+coverage\s+(?:ratio\s+)?(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\binterest\s+coverage\s+ratio\s+(\d+(?:\.\d+)?)\b',  # "interest coverage ratio 5.2"
            r'\b(\d+(?:\.\d+)?)\s+interest\s+coverage\b',
            r'\btimes\s+interest\s+earned\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
        ]),
        
        # NEW: Inventory turnover patterns
        ('inventory_turnover', [
            r'\binventory\s+turnover\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\binventory\s+turnover\s+(\d+(?:\.\d+)?)\b',  # "inventory turnover 8.3"
            r'\b(\d+(?:\.\d+)?)\s+inventory\s+turnover\b',
            r'\bturnover\s+ratio\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
        ]),
        
        # NEW: Asset turnover patterns
        ('asset_turnover', [
            r'\basset\s+turnover\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\basset\s+turnover\s+(\d+(?:\.\d+)?)\b',  # "asset turnover 1.2"
            r'\b(\d+(?:\.\d+)?)\s+asset\s+turnover\b',
        ]),
        
        # NEW: Price-to-sales patterns
        ('price_to_sales', [
            r'\bP/S\s+(?:ratio\s+)?(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\bprice[\s\-]to[\s\-]sales\s+(?:ratio\s+)?(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
            r'\bprice[\s\-]to[\s\-]sales\s+(\d+(?:\.\d+)?)\b',  # "price to sales 4.2"
            r'\b(\d+(?:\.\d+)?)\s+price[\s\-]to[\s\-]sales\b',
        ]),
        
        # NEW: EV/EBITDA patterns
        ('ev_ebitda', [
            r'\bEV/EBITDA\s+(?:of|is|was)?\s+(\d+(?:\.\d+)?)\b',
            r'\b(\d+(?:\.\d+)?)\s+EV/EBITDA\b',
            r'\benterprise\s+value\s+to\s+EBITDA\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\b',
            r'\benterprise\s+value\s+to\s+EBITDA\s+(\d+(?:\.\d+)?)\b',  # "enterprise value to EBITDA 15.0"
        ]),
        
        # NEW: Dividend yield patterns
        ('dividend_yield', [
            r'\bdividend\s+yield\s+(\d+(?:\.\d+)?)\s*%',  # "dividend yield 3.0%" - CHECK FIRST (removed \b before %)
            r'\bdividend\s+yield\s+(?:of|is|was)\s+(\d+(?:\.\d+)?)\s*%',  # "dividend yield of 2.5%" (removed \b before %)
            r'\b(\d+(?:\.\d+)?)\s*%\s+dividend\s+yield\b',
            r'\byield\s+(?:of|is)?\s+(\d+(?:\.\d+)?)\s*%',
        ]),
        
        # NEW: Payout ratio patterns
        ('payout_ratio', [
            r'\bpayout\s+ratio\s+(\d+(?:\.\d+)?)\s*%',  # "payout ratio 40%" - CHECK FIRST (removed \b before %)
            r'\bdividend\s+payout\s+(\d+(?:\.\d+)?)\s*%',  # "dividend payout 35%" - CHECK SECOND (removed \b before %)
            r'\bpayout\s+ratio\s+(?:of|is|was)\s+(\d+(?:\.\d+)?)\s*%',  # (removed \b before %)
            r'\b(\d+(?:\.\d+)?)\s*%\s+payout\s+ratio\b',
            r'\bdividend\s+payout\s+(?:of|is)\s+(\d+(?:\.\d+)?)\s*%',  # (removed \b before %)
        ]),
        
        # NEW: Gross profit patterns
        ('gross_profit', [
            r'\$[\d\.,]+[BMK]?\s+gross\s+profit\b',  # "$80B gross profit" - CHECK FIRST (no \b before $)
            r'\bgross\s+profit\s+\$[\d\.,]+[BMK]?\b',  # "gross profit $100B"
            r'\bgross\s+profit\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?gross\s+profit\b',  # No \b before $
            r'\b(?:made|earned|generated)\s+\$[\d\.,]+[BMK]?\s+(?:in\s+)?gross\s+profit\b',
        ]),
        
        # NEW: Operating expenses patterns
        ('operating_expenses', [
            r'\$[\d\.,]+[BMK]?\s+operating\s+expenses?\b',  # "$25B operating expenses" - CHECK FIRST (no \b before $)
            r'\bOPEX\s+\$[\d\.,]+[BMK]?\b',  # "OPEX $20B" - CHECK SECOND
            r'\boperating\s+expenses?\s+\$[\d\.,]+[BMK]?\b',  # "operating expenses $30B"
            r'\boperating\s+expenses?\s+(?:of|is|was|are|were)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?operating\s+expenses?\b',  # No \b before $
            r'\bOPEX\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
        ]),
        
        # NEW: R&D expenses patterns
        ('rd_expenses', [
            r'\$[\d\.,]+[BMK]?\s+R&D\s+expenses?\b',  # "$12B R&D expenses" - CHECK FIRST (no \b before $)
            r'\$[\d\.,]+[BMK]?\s+R\s*&\s*D\s+expenses?\b',  # "$12B R&D expenses" (with &) - CHECK SECOND (no \b before $)
            r'\bR&D\s+expenses?\s+\$[\d\.,]+[BMK]?\b',  # "R&D expenses $15B"
            r'\bR&D\s+(?:expenses?|spending|costs?)\s+(?:of|is|was|are|were)?\s+\$[\d\.,]+[BMK]?\b',
            r'\bresearch\s+and\s+development\s+\$[\d\.,]+[BMK]?\b',  # "research and development $10B"
            r'\bresearch\s+and\s+development\s+(?:expenses?|spending|costs?)\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:R&D|research\s+and\s+development)\b',  # No \b before $
        ]),
        
        # NEW: CAPEX patterns
        ('capex', [
            r'\$[\d\.,]+[BMK]?\s+CAPEX\b',  # "$15B CAPEX" - CHECK FIRST (no \b before $)
            r'\bCAPEX\s+\$[\d\.,]+[BMK]?\b',  # "CAPEX $15B" - CHECK SECOND
            r'\bCAPEX\s+(?:of|is|was)?\s+\$[\d\.,]+[BMK]?\b',
            r'\bcapital\s+expenditures?\s+\$[\d\.,]+[BMK]?\b',  # "capital expenditures $18B"
            r'\bcapital\s+expenditures?\s+(?:of|is)?\s+\$[\d\.,]+[BMK]?\b',
            r'\$[\d\.,]+[BMK]?\s+(?:in\s+)?(?:CAPEX|capital\s+expenditures?)\b',  # No \b before $
        ]),
    ])
    
    def __init__(self):
        """Initialize the metric inference engine"""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Pre-compile all regex patterns for efficiency"""
        compiled = {}
        for metric_id, patterns in self.CONTEXTUAL_PATTERNS.items():
            compiled[metric_id] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def infer_metrics(self, text: str, existing_metrics: Optional[List[str]] = None) -> List[InferredMetric]:
        """
        Infer metrics from contextual patterns in text.
        
        Args:
            text: The query text to analyze
            existing_metrics: List of already detected metrics (to avoid duplicates)
            
        Returns:
            List of InferredMetric objects
        """
        if not text:
            return []
        
        existing_metrics = existing_metrics or []
        inferred = []
        
        # Check each metric's contextual patterns
        for metric_id, patterns in self._compiled_patterns.items():
            # Skip if metric already detected
            if metric_id in existing_metrics:
                continue
            
            # Check all patterns for this metric
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # Extract value if captured
                    value = None
                    if match.groups():
                        value = match.group(1) if len(match.groups()) >= 1 else None
                    
                    # Calculate confidence based on pattern strength
                    confidence = self._calculate_confidence(text, metric_id, match)
                    
                    inferred.append(InferredMetric(
                        metric_id=metric_id,
                        confidence=confidence,
                        context=match.group(0),
                        value=value,
                        position=match.start()
                    ))
                    break  # Only one inference per metric
        
        # Sort by confidence (highest first)
        inferred.sort(key=lambda x: x.confidence, reverse=True)
        
        return inferred
    
    def _calculate_confidence(self, text: str, metric_id: str, match: re.Match) -> float:
        """Calculate confidence for an inferred metric"""
        confidence = 0.7  # Base confidence for pattern match
        
        # Boost for explicit metric name in match
        matched_text = match.group(0).lower()
        if metric_id in matched_text or metric_id.replace('_', ' ') in matched_text:
            confidence += 0.15
        
        # Boost for value patterns (specific amounts increase confidence)
        if re.search(r'\$[\d\.,]+[BMK]?', matched_text):
            confidence += 0.10  # Dollar amount present
        if re.search(r'\d+(?:\.\d+)?%', matched_text):
            confidence += 0.10  # Percentage present
        if re.search(r'\d+(?:\.\d+)?[xX×]', matched_text):
            confidence += 0.10  # Multiple (ratio) present
        
        # Boost for specific action verbs that strongly indicate metrics
        strong_verbs = {
            'revenue': ['made', 'generated', 'earned', 'posted', 'reported'],
            'eps': ['earned', 'reported'],
            'pe_ratio': ['trading'],
            'market_cap': ['valued', 'worth'],
            'dividend': ['paid', 'pays', 'paying'],
        }
        if metric_id in strong_verbs:
            for verb in strong_verbs[metric_id]:
                if verb in matched_text:
                    confidence += 0.05
                    break
        
        return min(1.0, confidence)
    
    def infer_from_value_pattern(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Infer metric from value patterns like "$400B" or "36%"
        
        Args:
            text: Text containing value pattern
            
        Returns:
            Tuple of (metric_id, value) if inferred, None otherwise
        """
        # Large dollar amounts typically indicate revenue or market cap
        large_amount = re.search(r'\$(\d+(?:\.\d+)?)\s*([BMT])\b', text, re.IGNORECASE)
        if large_amount:
            amount = float(large_amount.group(1))
            unit = large_amount.group(2).upper()
            
            # Check context for clues
            if re.search(r'\b(made|earned|generated|sales|revenue)\b', text, re.IGNORECASE):
                return ('revenue', large_amount.group(0))
            elif re.search(r'\b(valued|worth|market\s+cap)\b', text, re.IGNORECASE):
                return ('market_cap', large_amount.group(0))
            else:
                # Default to revenue for large amounts
                if unit in ['B', 'T'] or (unit == 'M' and amount >= 100):
                    return ('revenue', large_amount.group(0))
        
        # Per share amounts typically indicate EPS or dividend
        per_share = re.search(r'\$(\d+(?:\.\d+)?)\s+(?:per\s+share|a\s+share)', text, re.IGNORECASE)
        if per_share:
            if re.search(r'\b(earned|earnings|EPS)\b', text, re.IGNORECASE):
                return ('eps', per_share.group(0))
            elif re.search(r'\b(dividend|paid|payout)\b', text, re.IGNORECASE):
                return ('dividend', per_share.group(0))
            else:
                return ('eps', per_share.group(0))  # Default to EPS
        
        # Percentages might indicate margins, growth, or returns
        percentage = re.search(r'(\d+(?:\.\d+)?)%', text)
        if percentage:
            if re.search(r'\b(margin|profitability)\b', text, re.IGNORECASE):
                return ('margin', percentage.group(0))
            elif re.search(r'\b(growth|growing|increase|CAGR)\b', text, re.IGNORECASE):
                return ('growth_rate', percentage.group(0))
            elif re.search(r'\b(ROE|return\s+on\s+equity)\b', text, re.IGNORECASE):
                return ('roe', percentage.group(0))
            elif re.search(r'\b(ROA|return\s+on\s+assets)\b', text, re.IGNORECASE):
                return ('roa', percentage.group(0))
            elif re.search(r'\b(yield|dividend\s+yield)\b', text, re.IGNORECASE):
                return ('dividend_yield', percentage.group(0))
        
        # Multiples (e.g., "35x") typically indicate P/E ratio
        multiple = re.search(r'(\d+(?:\.\d+)?)[xX×]', text)
        if multiple:
            if re.search(r'\b(trading|P/E|price\s+to\s+earnings)\b', text, re.IGNORECASE):
                return ('pe_ratio', multiple.group(0))
            elif re.search(r'\b(EV/EBITDA)\b', text, re.IGNORECASE):
                return ('ev_ebitda', multiple.group(0))
        
        return None

