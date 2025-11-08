"""Response correction system to automatically fix verified inaccuracies."""

import re
import logging
from typing import List, Optional
from dataclasses import dataclass

from .response_verifier import VerificationResult, FinancialFact

LOGGER = logging.getLogger(__name__)


@dataclass
class Correction:
    """A single correction applied to response."""
    original_value: float
    corrected_value: float
    position: int
    context: str
    reason: str


def correct_response(
    response: str,
    verification_results: List[VerificationResult]
) -> str:
    """
    Automatically correct verified inaccuracies in responses.
    
    Args:
        response: Original LLM-generated response
        verification_results: List of verification results with corrections
    
    Returns:
        Corrected response with corrections applied
    """
    if not verification_results:
        return response
    
    # Sort results by position (reverse order to avoid position shifts)
    sorted_results = sorted(
        [r for r in verification_results if not r.is_correct and r.actual_value is not None],
        key=lambda r: r.fact.position,
        reverse=True
    )
    
    corrected_response = response
    
    for result in sorted_results:
        fact = result.fact
        actual_value = result.actual_value
        
        # Format the corrected value
        if fact.unit == "B":
            corrected_str = f"${actual_value:.1f}B"
        elif fact.unit == "M":
            corrected_str = f"${actual_value * 1000:.1f}M"
        elif fact.unit == "%":
            corrected_str = f"{actual_value:.1f}%"
        elif fact.unit == "x":
            corrected_str = f"{actual_value:.1f}x"
        else:
            corrected_str = f"{actual_value:.2f}"
        
        # Find and replace the incorrect value
        # Look for the value in the response near the fact position
        context_start = max(0, fact.position - 20)
        context_end = min(len(response), fact.position + 100)
        context = response[context_start:context_end]
        
        # Try to find the original value string
        original_patterns = [
            rf'\${fact.value:.1f}B',
            rf'\${fact.value:.1f}M',
            rf'{fact.value:.1f}%',
            rf'{fact.value:.1f}x',
            rf'{fact.value:.2f}',
        ]
        
        for pattern in original_patterns:
            if re.search(pattern, context):
                # Replace in the full response
                corrected_response = re.sub(
                    pattern,
                    corrected_str,
                    corrected_response,
                    count=1  # Only replace first occurrence
                )
                break
    
    return corrected_response


def add_verification_footer(
    response: str,
    verification_results: List[VerificationResult],
    include_corrections: bool = True
) -> str:
    """
    Add verification summary footer to response.
    
    Args:
        response: Response text (may already be corrected)
        verification_results: List of verification results
        include_corrections: Whether to include correction details
    
    Returns:
        Response with verification footer appended
    """
    # Find existing footer or end of response
    footer_marker = "\n\n---\n"
    if footer_marker in response:
        # Remove existing footer
        response = response.split(footer_marker)[0]
    
    total_facts = len(verification_results)
    correct_facts = sum(1 for r in verification_results if r.is_correct)
    corrections_applied = sum(
        1 for r in verification_results
        if not r.is_correct and r.actual_value is not None
    )
    
    # Build footer
    footer = "\n\n---\n"
    footer += f"**Verified:** {correct_facts}/{total_facts} facts correct"
    
    if corrections_applied > 0 and include_corrections:
        footer += f" | {corrections_applied} corrections applied"
    
    if include_corrections and corrections_applied > 0:
        footer += "\n\n**Corrections Applied:**\n"
        for result in verification_results:
            if not result.is_correct and result.actual_value is not None:
                fact = result.fact
                footer += f"- {fact.metric or 'Value'}: "
                footer += f"{result.actual_value:.2f} (was {fact.value:.2f})\n"
    
    return response + footer


def apply_corrections_with_notes(
    response: str,
    verification_results: List[VerificationResult]
) -> str:
    """
    Apply corrections with explicit notes about what was corrected.
    
    This version adds correction notes in the response itself.
    """
    if not verification_results:
        return response
    
    # Get incorrect results
    incorrect_results = [
        r for r in verification_results
        if not r.is_correct and r.actual_value is not None
    ]
    
    if not incorrect_results:
        return response
    
    # Sort by position (reverse order)
    sorted_results = sorted(
        incorrect_results,
        key=lambda r: r.fact.position,
        reverse=True
    )
    
    corrected_response = response
    
    for result in sorted_results:
        fact = result.fact
        actual_value = result.actual_value
        
        # Format values
        if fact.unit == "B":
            original_str = f"${fact.value:.1f}B"
            corrected_str = f"${actual_value:.1f}B"
        elif fact.unit == "M":
            original_str = f"${fact.value * 1000:.1f}M"
            corrected_str = f"${actual_value * 1000:.1f}M"
        elif fact.unit == "%":
            original_str = f"{fact.value:.1f}%"
            corrected_str = f"{actual_value:.1f}%"
        elif fact.unit == "x":
            original_str = f"{fact.value:.1f}x"
            corrected_str = f"{actual_value:.1f}x"
        else:
            original_str = f"{fact.value:.2f}"
            corrected_str = f"{actual_value:.2f}"
        
        # Find and replace with note
        context_start = max(0, fact.position - 20)
        context_end = min(len(response), fact.position + 100)
        context = response[context_start:context_end]
        
        # Try to find the original value
        original_patterns = [
            rf'\${fact.value:.1f}B',
            rf'\${fact.value:.1f}M',
            rf'{fact.value:.1f}%',
            rf'{fact.value:.1f}x',
            rf'{fact.value:.2f}',
        ]
        
        for pattern in original_patterns:
            if re.search(pattern, context):
                # Replace with corrected value and note
                replacement = f"{corrected_str} (corrected from {original_str})"
                corrected_response = re.sub(
                    pattern,
                    replacement,
                    corrected_response,
                    count=1
                )
                break
    
    return corrected_response


