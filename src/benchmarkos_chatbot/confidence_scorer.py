"""Confidence scoring for chatbot responses based on verification results."""

import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

from .response_verifier import VerificationResult, VerifiedResponse

LOGGER = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Confidence score for a response with breakdown of factors."""
    score: float  # 0.0 to 1.0 (0% to 100%)
    factors: List[str]  # List of factors affecting confidence
    verified_facts: int
    total_facts: int
    unverified_facts: int
    discrepancies: int
    missing_sources: int
    outdated_data: int


def calculate_confidence(
    response: str,
    verification_results: List[VerificationResult],
    source_count: int = 0,
    data_age_days: Optional[int] = None
) -> ConfidenceScore:
    """
    Calculate confidence score for a response based on verification results.
    
    Args:
        response: LLM-generated response text
        verification_results: List of verification results for each fact
        source_count: Number of sources cited in response
        data_age_days: Age of data in days (None if unknown)
    
    Returns:
        ConfidenceScore with score and factors
    """
    factors = []
    base_confidence = 1.0
    
    # Count facts
    total_facts = len(verification_results)
    verified_facts = sum(1 for r in verification_results if r.is_correct)
    unverified_facts = total_facts - verified_facts
    
    # Deduct for unverified facts
    if unverified_facts > 0:
        deduction = min(0.1 * unverified_facts, 0.5)  # Max 50% deduction
        base_confidence -= deduction
        factors.append(f"-{unverified_facts} unverified facts ({deduction*100:.1f}%)")
    
    # Deduct for discrepancies
    discrepancies = sum(1 for r in verification_results if not r.is_correct and r.actual_value is not None)
    if discrepancies > 0:
        deduction = min(0.2 * discrepancies, 0.4)  # Max 40% deduction
        base_confidence -= deduction
        factors.append(f"-{discrepancies} discrepancies ({deduction*100:.1f}%)")
    
    # Deduct for missing sources (only if facts are unverified)
    # If all facts are verified, source count is less critical
    if verified_facts < total_facts or total_facts == 0:
        # Only penalize sources if we have unverified facts
        if source_count == 0:
            base_confidence -= 0.15
            factors.append("-No sources cited (15%)")
        elif source_count < 3:
            base_confidence -= 0.05
            factors.append(f"-Only {source_count} sources cited (5%)")
    else:
        # All facts verified - don't penalize for fewer sources
        # Just note it as informational
        if source_count < 3 and source_count > 0:
            # Don't deduct, but note it
            pass
    
    # Deduct for outdated data
    outdated_data = 0
    if data_age_days is not None:
        if data_age_days > 365:
            base_confidence -= 0.1
            outdated_data = 1
            factors.append(f"-Data is {data_age_days} days old (10%)")
        elif data_age_days > 180:
            base_confidence -= 0.05
            outdated_data = 1
            factors.append(f"-Data is {data_age_days} days old (5%)")
    
    # Ensure confidence is between 0 and 1
    confidence_score = max(0.0, min(1.0, base_confidence))
    
    # Add positive factors
    if verified_facts == total_facts and total_facts > 0:
        factors.insert(0, f"+All {total_facts} facts verified (100%)")
        # If all facts verified and we have any sources, give bonus for accuracy
        if source_count > 0:
            factors.append(f"+{source_count} sources cited")
    if source_count >= 5:
        factors.insert(0, f"+Comprehensive sources ({source_count} citations)")
    
    return ConfidenceScore(
        score=confidence_score,
        factors=factors,
        verified_facts=verified_facts,
        total_facts=total_facts,
        unverified_facts=unverified_facts,
        discrepancies=discrepancies,
        missing_sources=1 if source_count == 0 else 0,
        outdated_data=outdated_data
    )


def add_confidence_footer(
    response: str,
    confidence: ConfidenceScore,
    include_details: bool = False
) -> str:
    """
    Append confidence score footer to response.
    
    Args:
        response: Original response text
        confidence: Confidence score object
        include_details: Whether to include detailed breakdown
    
    Returns:
        Response with confidence footer appended
    """
    # Find existing footer or end of response
    footer_marker = "\n\n---\n"
    if footer_marker in response:
        # Remove existing footer
        response = response.split(footer_marker)[0]
    
    # Build footer
    footer = "\n\n---\n"
    footer += f"**Confidence: {confidence.score*100:.0f}%**"
    footer += f" | Verified: {confidence.verified_facts}/{confidence.total_facts} facts"
    
    if confidence.total_facts > 0:
        footer += f" | Sources: {confidence.total_facts - confidence.missing_sources} citations"
    
    if include_details and confidence.factors:
        footer += "\n\n**Confidence Factors:**\n"
        for factor in confidence.factors[:5]:  # Limit to top 5 factors
            footer += f"- {factor}\n"
    
    return response + footer


def calculate_confidence_from_verified_response(
    verified_response: VerifiedResponse,
    source_count: int = 0,
    data_age_days: Optional[int] = None
) -> ConfidenceScore:
    """
    Calculate confidence score from a VerifiedResponse object.
    
    Convenience wrapper around calculate_confidence.
    """
    return calculate_confidence(
        verified_response.original_response,
        verified_response.results,
        source_count=source_count,
        data_age_days=data_age_days
    )

