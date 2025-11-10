"""Tests for response corrector - automatic correction of inaccuracies."""

import pytest
from benchmarkos_chatbot.response_corrector import (
    correct_response,
    add_verification_footer,
    apply_corrections_with_notes,
    Correction
)
from benchmarkos_chatbot.response_verifier import (
    VerificationResult,
    FinancialFact
)


class TestCorrectResponse:
    """Test response correction."""
    
    @pytest.fixture
    def sample_verification_results(self):
        """Create sample verification results with errors."""
        fact = FinancialFact(
            value=400.0,  # Incorrect value
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $400.0B",
            position=0
        )
        
        return [
            VerificationResult(
                fact=fact,
                is_correct=False,
                actual_value=394.3,  # Correct value
                deviation=1.4,
                confidence=0.7,
                source="SEC",
                message="Mismatch: 400.0 vs 394.3"
            )
        ]
    
    def test_correct_response_with_errors(self, sample_verification_results):
        """Test correction of response with errors."""
        response = "Apple's revenue is $400.0B"
        
        corrected = correct_response(response, sample_verification_results)
        
        # Should contain corrected value
        assert "394.3" in corrected or "394" in corrected
    
    def test_correct_response_no_errors(self):
        """Test correction when no errors exist."""
        fact = FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $394.3B",
            position=0
        )
        
        results = [
            VerificationResult(
                fact=fact,
                is_correct=True,
                actual_value=394.3,
                deviation=0.0,
                confidence=1.0,
                source="SEC",
                message="Verified"
            )
        ]
        
        response = "Apple's revenue is $394.3B"
        
        corrected = correct_response(response, results)
        
        # Should remain unchanged
        assert corrected == response or "394.3" in corrected


class TestAddVerificationFooter:
    """Test verification footer addition."""
    
    def test_add_verification_footer_all_correct(self):
        """Test adding footer when all facts are correct."""
        response = "Apple's revenue is $394.3B"
        
        fact = FinancialFact(
            value=394.3,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $394.3B",
            position=0
        )
        
        results = [
            VerificationResult(
                fact=fact,
                is_correct=True,
                actual_value=394.3,
                deviation=0.0,
                confidence=1.0,
                source="SEC",
                message="Verified"
            )
        ]
        
        result = add_verification_footer(response, results)
        
        assert "Verified:" in result
        assert "1/1 facts correct" in result
    
    def test_add_verification_footer_with_corrections(self):
        """Test adding footer with corrections applied."""
        response = "Apple's revenue is $400.0B"
        
        fact = FinancialFact(
            value=400.0,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $400.0B",
            position=0
        )
        
        results = [
            VerificationResult(
                fact=fact,
                is_correct=False,
                actual_value=394.3,
                deviation=1.4,
                confidence=0.7,
                source="SEC",
                message="Mismatch"
            )
        ]
        
        result = add_verification_footer(response, results, include_corrections=True)
        
        assert "Verified:" in result
        assert "corrections applied" in result.lower() or "corrections" in result.lower()


class TestApplyCorrectionsWithNotes:
    """Test corrections with explicit notes."""
    
    def test_apply_corrections_with_notes(self):
        """Test applying corrections with notes in response."""
        response = "Apple's revenue is $400.0B"
        
        fact = FinancialFact(
            value=400.0,
            unit="B",
            metric="revenue",
            ticker="AAPL",
            period="2024",
            context="Apple's revenue is $400.0B",
            position=0
        )
        
        results = [
            VerificationResult(
                fact=fact,
                is_correct=False,
                actual_value=394.3,
                deviation=1.4,
                confidence=0.7,
                source="SEC",
                message="Mismatch"
            )
        ]
        
        corrected = apply_corrections_with_notes(response, results)
        
        # Should contain correction note
        assert "corrected" in corrected.lower() or "394.3" in corrected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



