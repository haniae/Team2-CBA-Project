"""Advanced hallucination detection and prevention system."""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from .response_verifier import FinancialFact, VerificationResult

LOGGER = logging.getLogger(__name__)


@dataclass
class HallucinationWarning:
    """Warning about potential hallucination."""
    fact: Optional[FinancialFact]
    reason: str
    severity: str  # "low", "medium", "high", "critical"
    suggested_action: str
    confidence: float  # 0.0 to 1.0


@dataclass
class HallucinationReport:
    """Report of potential hallucinations in response."""
    warnings: List[HallucinationWarning]
    total_warnings: int
    critical_warnings: int
    has_hallucination: bool
    confidence_score: float


def detect_hallucinations(
    response: str,
    context: str,
    verification_results: List[VerificationResult],
    facts: List[FinancialFact]
) -> HallucinationReport:
    """
    Detect potential hallucinations in LLM response.
    
    Checks for:
    1. Numbers not found in context
    2. Numbers with high deviation from context
    3. Missing source citations
    4. Unverified facts
    5. Suspicious patterns (astronomical percentages, etc.)
    
    Args:
        response: LLM-generated response
        context: Context provided to LLM
        verification_results: Results from verify_response
        facts: Extracted financial facts
    
    Returns:
        HallucinationReport with warnings and recommendations
    """
    warnings: List[HallucinationWarning] = []
    
    # Check 1: Unverified facts (not found in context)
    for result in verification_results:
        if not result.is_correct:
            # Check if fact exists in context at all
            fact_in_context = _check_fact_in_context(result.fact, context)
            
            if not fact_in_context:
                severity = "critical" if result.fact.metric in ["revenue", "net_income", "ebitda"] else "high"
                warnings.append(HallucinationWarning(
                    fact=result.fact,
                    reason=f"Fact not found in context: {result.fact.metric} = {result.fact.value}{result.fact.unit or ''}",
                    severity=severity,
                    suggested_action="Remove or mark as unavailable",
                    confidence=0.9
                ))
            elif result.deviation > 0.10:  # >10% deviation
                severity = "high" if result.deviation > 0.20 else "medium"
                warnings.append(HallucinationWarning(
                    fact=result.fact,
                    reason=f"High deviation from context: {result.deviation*100:.1f}% difference",
                    severity=severity,
                    suggested_action="Verify against source data",
                    confidence=0.7
                ))
    
    # Check 2: Missing source citations for key facts
    source_count = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', response))
    if source_count < 3:
        # Check if response contains financial numbers but few sources
        if len(facts) > 0 and source_count < len(facts) / 2:
            warnings.append(HallucinationWarning(
                fact=facts[0] if facts else None,
                reason=f"Response contains {len(facts)} financial facts but only {source_count} sources",
                severity="medium",
                suggested_action="Add more source citations",
                confidence=0.6
            ))
    
    # Check 3: Suspicious patterns (astronomical percentages, etc.)
    suspicious_patterns = [
        (r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*%', lambda m: float(m.group(1).replace(',', '')) > 1000, 
         "Percentage > 1000% is likely an error"),
        (r'\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*([BMKT])', 
         lambda m: float(m.group(1).replace(',', '')) > 10000 and m.group(2) in ['B', 'T'],
         "Extremely large dollar amount may be incorrect"),
    ]
    
    for pattern, check, reason in suspicious_patterns:
        for match in re.finditer(pattern, response):
            if check(match):
                # Try to find associated fact
                position = match.start()
                associated_fact = _find_fact_at_position(facts, position)
                
                if associated_fact:
                    warnings.append(HallucinationWarning(
                        fact=associated_fact,
                        reason=reason,
                        severity="critical",
                        suggested_action="Verify calculation or remove",
                        confidence=0.95
                    ))
    
    # Check 4: Numbers mentioned but not in context
    all_numbers = _extract_all_numbers(response)
    context_numbers = _extract_all_numbers(context)
    
    for number, position in all_numbers:
        if number not in context_numbers:
            # Check if it's a reasonable calculation or truly missing
            if not _is_likely_calculation(number, context_numbers):
                associated_fact = _find_fact_at_position(facts, position)
                if associated_fact:
                    warnings.append(HallucinationWarning(
                        fact=associated_fact,
                        reason="Number not found in context and not a clear calculation",
                        severity="medium",
                        suggested_action="Verify source or remove",
                        confidence=0.65
                    ))
    
    # Check 5: High confidence unverified facts
    for result in verification_results:
        if not result.is_correct and result.confidence < 0.5:
            warnings.append(HallucinationWarning(
                fact=result.fact,
                reason=f"Low confidence verification ({result.confidence*100:.1f}%)",
                severity="medium",
                suggested_action="Mark as uncertain or remove",
                confidence=0.7
            ))
    
    critical_warnings = sum(1 for w in warnings if w.severity == "critical")
    has_hallucination = critical_warnings > 0 or len([w for w in warnings if w.severity in ["high", "critical"]]) > 2
    
    # Calculate overall confidence
    if warnings:
        avg_confidence = sum(w.confidence for w in warnings) / len(warnings)
        confidence_score = 1.0 - (avg_confidence * 0.5)  # Lower confidence if warnings exist
    else:
        confidence_score = 1.0
    
    return HallucinationReport(
        warnings=warnings,
        total_warnings=len(warnings),
        critical_warnings=critical_warnings,
        has_hallucination=has_hallucination,
        confidence_score=confidence_score
    )


def _check_fact_in_context(fact: FinancialFact, context: str) -> bool:
    """Check if a fact appears in the context."""
    # Normalize value for comparison
    value_str = f"{fact.value:.2f}"
    
    # Check for exact match or close match
    patterns = [
        rf'\${fact.value:.1f}[BMKT]',
        rf'{fact.value:.1f}%',
        rf'{fact.value:.2f}',
        rf'{fact.value:.0f}',
    ]
    
    for pattern in patterns:
        if re.search(pattern, context, re.IGNORECASE):
            return True
    
    return False


def _extract_all_numbers(text: str) -> List[Tuple[float, int]]:
    """Extract all numbers from text with their positions."""
    numbers = []
    
    # Pattern for financial numbers
    patterns = [
        (r'\$([\d,]+\.?\d*)\s*([BMKT])', lambda m: float(m.group(1).replace(',', '')) * (1000 if m.group(2) == 'T' else (1 if m.group(2) == 'B' else (0.001 if m.group(2) == 'M' else 0.000001)))),
        (r'([\d,]+\.?\d*)\s*%', lambda m: float(m.group(1).replace(',', ''))),
        (r'([\d,]+\.?\d*)\s*x', lambda m: float(m.group(1).replace(',', ''))),
        (r'([\d,]+\.?\d*)', lambda m: float(m.group(1).replace(',', ''))),
    ]
    
    for pattern, converter in patterns:
        for match in re.finditer(pattern, text):
            try:
                value = converter(match)
                numbers.append((value, match.start()))
            except (ValueError, AttributeError):
                continue
    
    return numbers


def _is_likely_calculation(number: float, context_numbers: List[float]) -> bool:
    """Check if a number is likely a calculation from context numbers."""
    # Simple heuristic: if number is close to sum/product of context numbers
    for ctx_num in context_numbers:
        if abs(number - ctx_num) < ctx_num * 0.01:  # Within 1%
            return True
        if ctx_num > 0 and abs(number / ctx_num - 1.0) < 0.1:  # Close ratio
            return True
    return False


def _find_fact_at_position(facts: List[FinancialFact], position: int) -> Optional[FinancialFact]:
    """Find fact closest to a character position."""
    if not facts:
        return None
    
    closest = min(facts, key=lambda f: abs(f.position - position))
    if abs(closest.position - position) < 50:  # Within 50 characters
        return closest
    return None


def add_hallucination_warning(
    response: str,
    report: HallucinationReport
) -> str:
    """
    Add hallucination warning to response if needed.
    
    Args:
        response: Original response
        report: Hallucination detection report
    
    Returns:
        Response with warning footer if hallucinations detected
    """
    if not report.has_hallucination and report.critical_warnings == 0:
        return response
    
    warning_footer = "\n\n---\n\n"
    warning_footer += "⚠️ **Data Verification Notice:**\n\n"
    
    if report.critical_warnings > 0:
        warning_footer += f"🚨 **CRITICAL:** {report.critical_warnings} critical data verification issue(s) detected.\n\n"
    
    if report.total_warnings > 0:
        warning_footer += f"**Verification Summary:**\n"
        warning_footer += f"- Total warnings: {report.total_warnings}\n"
        warning_footer += f"- Critical: {report.critical_warnings}\n"
        warning_footer += f"- Confidence: {report.confidence_score*100:.1f}%\n\n"
        
        if report.critical_warnings > 0:
            warning_footer += "**Recommendation:** Please verify the data points marked above against source documents.\n\n"
    
    warning_footer += "**Note:** This response has been automatically verified. Some data points may need manual verification.\n"
    
    return response + warning_footer

