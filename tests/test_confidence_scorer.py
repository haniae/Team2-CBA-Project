"""Tests for confidence scorer - confidence calculation."""

import pytest
from benchmarkos_chatbot.confidence_scorer import (
    calculate_confidence,
    add_confidence_footer,
    calculate_confidence_from_verified_response,
    ConfidenceScore
)
from benchmarkos_chatbot.response_verifier import (
    VerificationResult,
    FinancialFact,
    VerifiedResponse
)


class TestCalculateConfidence:
    """Test confidence score calculation."""
    
    @pytest.fixture
    def sample_verification_results(self):
        """Create sample verification results."""
        fact1 = FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $394.3B",
            position=0
        )
        
        fact2 = FinancialFact(
            value=25.3,
            unit="%",
            metric="margin",
            ticker="AAPL",
            period="2024",
            context="Margin is 25.3%",
            position=50
        )
        
        return [
            VerificationResult(
                fact=fact1,
                is_correct=True,
                actual_value=394.3,
                deviation=0.0,
                confidence=1.0,
                source="SEC",
                message="Verified"
            ),
            VerificationResult(
                fact=fact2,
                is_correct=True,
                actual_value=25.3,
                deviation=0.0,
                confidence=1.0,
                source="SEC",
                message="Verified"
            )
        ]
    
    def test_calculate_confidence_all_correct(self, sample_verification_results):
        """Test confidence calculation with all facts correct."""
        response = "Apple's revenue is $394.3B with a margin of 25.3%"
        
        confidence = calculate_confidence(
            response,
            sample_verification_results,
            source_count=3
        )
        
        assert isinstance(confidence, ConfidenceScore)
        assert confidence.score >= 0.9  # High confidence
        assert confidence.verified_facts == 2
        assert confidence.total_facts == 2
        assert confidence.discrepancies == 0
    
    def test_calculate_confidence_with_discrepancies(self):
        """Test confidence calculation with discrepancies."""
        fact = FinancialFact(
            value=400.0,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Revenue is $400.0B",
            position=0
        )
        
        results = [
            VerificationResult(
                fact=fact,
                is_correct=False,
                actual_value=394.3,
                deviation=1.4,  # ~1.4% deviation
                confidence=0.7,
                source="SEC",
                message="Mismatch"
            )
        ]
        
        response = "Apple's revenue is $400.0B"
        
        confidence = calculate_confidence(
            response,
            results,
            source_count=1
        )
        
        assert confidence.score < 1.0
        assert confidence.discrepancies == 1
    
    def test_calculate_confidence_missing_sources(self, sample_verification_results):
        """Test confidence calculation with missing sources."""
        response = "Apple's revenue is $394.3B"
        
        confidence = calculate_confidence(
            response,
            sample_verification_results,
            source_count=0  # No sources
        )
        
        assert confidence.score < 1.0
        assert confidence.missing_sources == 1
    
    def test_calculate_confidence_outdated_data(self, sample_verification_results):
        """Test confidence calculation with outdated data."""
        response = "Apple's revenue is $394.3B"
        
        confidence = calculate_confidence(
            response,
            sample_verification_results,
            source_count=3,
            data_age_days=400  # More than 1 year old
        )
        
        assert confidence.score < 1.0
        assert confidence.outdated_data == 1


class TestAddConfidenceFooter:
    """Test confidence footer addition."""
    
    def test_add_confidence_footer(self):
        """Test adding confidence footer to response."""
        response = "Apple's revenue is $394.3B"
        
        confidence = ConfidenceScore(
            score=0.95,
            factors=["+All 2 facts verified"],
            verified_facts=2,
            total_facts=2,
            unverified_facts=0,
            discrepancies=0,
            missing_sources=0,
            outdated_data=0
        )
        
        result = add_confidence_footer(response, confidence)
        
        assert "Confidence: 95%" in result
        assert "Verified: 2/2 facts" in result
    
    def test_add_confidence_footer_with_details(self):
        """Test adding confidence footer with detailed breakdown."""
        response = "Apple's revenue is $394.3B"
        
        confidence = ConfidenceScore(
            score=0.85,
            factors=["+All 2 facts verified", "-1 discrepancy (20%)"],
            verified_facts=2,
            total_facts=2,
            unverified_facts=0,
            discrepancies=1,
            missing_sources=0,
            outdated_data=0
        )
        
        result = add_confidence_footer(response, confidence, include_details=True)
        
        assert "Confidence: 85%" in result
        assert "Confidence Factors:" in result


class TestCalculateConfidenceFromVerifiedResponse:
    """Test confidence calculation from VerifiedResponse."""
    
    def test_calculate_from_verified_response(self):
        """Test confidence calculation from VerifiedResponse object."""
        fact = FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Revenue is $394.3B",
            position=0
        )
        
        result = VerificationResult(
            fact=fact,
            is_correct=True,
            actual_value=394.3,
            deviation=0.0,
            confidence=1.0,
            source="SEC",
            message="Verified"
        )
        
        verified_response = VerifiedResponse(
            original_response="Apple's revenue is $394.3B",
            verified_response="Apple's revenue is $394.3B",
            facts=[fact],
            results=[result],
            correct_facts=1,
            total_facts=1,
            has_errors=False,
            confidence_score=1.0
        )
        
        confidence = calculate_confidence_from_verified_response(
            verified_response,
            source_count=2
        )
        
        assert isinstance(confidence, ConfidenceScore)
        assert confidence.verified_facts == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


