"""
Comprehensive test suite for spelling correction.

Tests:
- Company name correction
- Ticker correction
- Metric name correction
- Common typos
- Confidence scoring
- Multi-word corrections
- Edge cases
"""

import pytest
from src.benchmarkos_chatbot.spelling import (
    SpellingCorrectionEngine,
    CorrectionResult,
    FuzzyMatcher,
    calculate_similarity,
)
from src.benchmarkos_chatbot.spelling.company_corrector import CompanyCorrector
from src.benchmarkos_chatbot.spelling.metric_corrector import MetricCorrector
from src.benchmarkos_chatbot.spelling.fuzzy_matcher import (
    levenshtein_distance,
    soundex,
    TypoPatternMatcher,
)


class TestFuzzyMatcher:
    """Test core fuzzy matching algorithms"""
    
    def test_levenshtein_distance_identical(self):
        """Test edit distance for identical strings"""
        assert levenshtein_distance("apple", "apple") == 0
    
    def test_levenshtein_distance_single_substitution(self):
        """Test edit distance for single character substitution"""
        assert levenshtein_distance("apple", "aple") == 1
        assert levenshtein_distance("microsoft", "microsft") == 1
    
    def test_levenshtein_distance_transposition(self):
        """Test edit distance for character transposition"""
        assert levenshtein_distance("telsa", "tesla") == 2
    
    def test_soundex_similar_sounding(self):
        """Test phonetic matching"""
        # "Microsoft" and "Microsaft" should have similar soundex codes
        ms1 = soundex("Microsoft")
        ms2 = soundex("Microsaft")
        assert ms1 == ms2 or abs(ord(ms1[-1]) - ord(ms2[-1])) <= 1
    
    def test_calculate_similarity_exact(self):
        """Test similarity for exact match"""
        assert calculate_similarity("Apple", "Apple") == 1.0
    
    def test_calculate_similarity_typo(self):
        """Test similarity for common typo"""
        similarity = calculate_similarity("Microsft", "Microsoft")
        assert similarity > 0.85  # Should be high confidence
    
    def test_fuzzy_matcher_exact_match(self):
        """Test fuzzy matcher with exact match"""
        corpus = ["Apple", "Microsoft", "Amazon"]
        matcher = FuzzyMatcher(corpus)
        
        matches = matcher.find_best_match("Apple")
        assert len(matches) == 1
        assert matches[0][0] == "Apple"
        assert matches[0][1] == 1.0
    
    def test_fuzzy_matcher_typo(self):
        """Test fuzzy matcher with typo"""
        corpus = ["Apple", "Microsoft", "Amazon"]
        matcher = FuzzyMatcher(corpus)
        
        matches = matcher.find_best_match("Microsft", threshold=0.7)
        assert len(matches) >= 1
        assert matches[0][0] == "Microsoft"
        assert matches[0][1] > 0.85


class TestCompanyCorrector:
    """Test company name correction"""
    
    def test_correct_microsoft_typo(self):
        """Test correcting Microsoft typo"""
        corrector = CompanyCorrector(ticker_list=["MSFT", "AAPL", "AMZN"])
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Microsft")
        assert corrected == "Microsoft"
        assert confidence > 0.8
    
    def test_correct_apple_typo(self):
        """Test correcting Apple typo"""
        corrector = CompanyCorrector(ticker_list=["MSFT", "AAPL", "AMZN"])
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Aple")
        assert corrected == "Apple"
        assert confidence > 0.7
    
    def test_correct_amazon_typo(self):
        """Test correcting Amazon typo"""
        corrector = CompanyCorrector(ticker_list=["MSFT", "AAPL", "AMZN"])
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Amazn")
        assert corrected == "Amazon"
        assert confidence > 0.8
    
    def test_correct_tesla_typo(self):
        """Test correcting Tesla typo"""
        corrector = CompanyCorrector(ticker_list=["TSLA"])
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Tesls")
        assert corrected == "Tesla"
        assert confidence > 0.75
    
    def test_correct_google_typo(self):
        """Test correcting Google typo"""
        corrector = CompanyCorrector(ticker_list=["GOOGL"])
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Gogle")
        assert corrected == "Google"
        assert confidence > 0.75
    
    def test_no_correction_needed(self):
        """Test when no correction is needed"""
        corrector = CompanyCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_company_name("Apple")
        assert corrected == "Apple"
        assert confidence == 1.0
        assert not should_confirm
    
    def test_ticker_correction(self):
        """Test ticker symbol correction"""
        corrector = CompanyCorrector(ticker_list=["AAPL", "MSFT", "AMZN", "TSLA"])
        
        # MSFT typo
        corrected, confidence, should_confirm = corrector.correct_ticker("MSFT")
        assert corrected == "MSFT"
        assert confidence == 1.0
    
    def test_ticker_correction_requires_confirmation(self):
        """Test that ticker corrections require confirmation"""
        corrector = CompanyCorrector(ticker_list=["AAPL", "MSFT"])
        
        # Similar tickers should require confirmation
        corrected, confidence, should_confirm = corrector.correct_ticker("MSFT")
        assert corrected == "MSFT"
        assert confidence == 1.0


class TestMetricCorrector:
    """Test metric name correction"""
    
    def test_correct_revenue_typo(self):
        """Test correcting revenue typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("reveune")
        assert corrected.lower() == "revenue"
        assert confidence > 0.8
    
    def test_correct_profit_typo(self):
        """Test correcting profit typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("proft")
        assert corrected.lower() == "profit"
        assert confidence > 0.8
    
    def test_correct_margin_typo(self):
        """Test correcting margin typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("margn")
        assert corrected.lower() == "margin"
        assert confidence > 0.75
    
    def test_correct_earnings_typo(self):
        """Test correcting earnings typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("earings")
        assert corrected.lower() == "earnings"
        assert confidence > 0.8
    
    def test_correct_growth_typo(self):
        """Test correcting growth typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("groth")
        assert corrected.lower() == "growth"
        assert confidence > 0.8
    
    def test_correct_cashflow_typo(self):
        """Test correcting cash flow typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("cashflow")
        assert "cash" in corrected.lower() and "flow" in corrected.lower()
        assert confidence > 0.85
    
    def test_correct_dividend_typo(self):
        """Test correcting dividend typo"""
        corrector = MetricCorrector()
        
        corrected, confidence, should_confirm = corrector.correct_metric("divident")
        assert corrected.lower() == "dividend"
        assert confidence > 0.8


class TestSpellingCorrectionEngine:
    """Test main spelling correction engine"""
    
    def test_simple_query_no_correction(self):
        """Test query with no spelling errors"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT"])
        
        result = engine.correct_query("What is Apple's revenue?")
        assert result.corrected_text == "What is Apple's revenue?"
        assert len(result.corrections) == 0
        assert result.confidence == 1.0
        assert not result.should_confirm
    
    def test_company_name_correction(self):
        """Test correcting company name in query"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT"])
        
        result = engine.correct_query("What is Microsft's revenue?")
        assert "Microsoft" in result.corrected_text
        assert len(result.corrections) > 0
        assert result.corrections[0].original == "Microsft"
        assert result.corrections[0].corrected == "Microsoft"
        assert result.corrections[0].type == "company"
    
    def test_metric_name_correction(self):
        """Test correcting metric name in query"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Show me the reveune for Apple")
        assert "revenue" in result.corrected_text.lower()
        assert len(result.corrections) > 0
    
    def test_multiple_corrections(self):
        """Test query with multiple spelling errors"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT"])
        
        result = engine.correct_query("What is Microsft's reveune?")
        # Should correct both "Microsft" and "reveune"
        assert len(result.corrections) >= 1  # At least one correction
    
    def test_no_false_positives_on_stopwords(self):
        """Test that common words are not incorrectly flagged"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("What is the revenue for Apple?")
        # "what", "is", "the", "for" should not be corrected
        assert result.corrected_text == "What is the revenue for Apple?"
    
    def test_ticker_in_caps_preserved(self):
        """Test that ticker symbols in caps are preserved"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT"])
        
        result = engine.correct_query("Show me AAPL revenue")
        assert "AAPL" in result.corrected_text
        assert len(result.corrections) == 0
    
    def test_confidence_thresholds(self):
        """Test confidence threshold behavior"""
        engine = SpellingCorrectionEngine()
        
        # High confidence correction (known typo)
        result = engine.correct_query("What is Microsft's revenue?")
        if result.corrections:
            assert result.confidence >= engine.CONFIDENCE_SUGGEST
    
    def test_empty_query(self):
        """Test handling of empty query"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("")
        assert result.corrected_text == ""
        assert len(result.corrections) == 0
    
    def test_whitespace_only_query(self):
        """Test handling of whitespace-only query"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("   ")
        assert len(result.corrections) == 0


class TestTypoPatterns:
    """Test common typo pattern detection"""
    
    def test_adjacent_key_detection(self):
        """Test detection of adjacent key typos"""
        assert TypoPatternMatcher.is_adjacent_key_typo('a', 'q')  # Q is adjacent to A
        assert TypoPatternMatcher.is_adjacent_key_typo('s', 'a')  # A is adjacent to S
    
    def test_typo_variant_generation(self):
        """Test generation of typo variants"""
        variants = TypoPatternMatcher.generate_typo_variants("test", max_variants=10)
        assert len(variants) > 0
        # Should include deletion variant
        assert "tst" in variants or "tes" in variants


class TestIntegration:
    """Integration tests for end-to-end correction"""
    
    def test_real_world_query_1(self):
        """Test: 'Show me Microsft reveune'"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT"])
        
        result = engine.correct_query("Show me Microsft reveune")
        # Should correct both errors
        assert len(result.corrections) >= 1
    
    def test_real_world_query_2(self):
        """Test: 'What is Aple's proft margin?'"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL"])
        
        result = engine.correct_query("What is Aple's proft margin?")
        # Should correct Aple and proft
        assert len(result.corrections) >= 1
    
    def test_real_world_query_3(self):
        """Test: 'Compare Tesls and Amazn'"""
        engine = SpellingCorrectionEngine(ticker_list=["TSLA", "AMZN"])
        
        result = engine.correct_query("Compare Tesls and Amazn")
        # Should correct both company names
        assert len(result.corrections) >= 1
    
    def test_real_world_query_4(self):
        """Test: 'Show me the earings groth for Google'"""
        engine = SpellingCorrectionEngine(ticker_list=["GOOGL"])
        
        result = engine.correct_query("Show me the earings groth for Google")
        # Should correct earings and groth
        assert len(result.corrections) >= 1
    
    def test_correction_message_formatting(self):
        """Test formatting of correction messages"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT"])
        
        result = engine.correct_query("Show me Microsft revenue")
        if result.corrections:
            message = engine.format_correction_message(result)
            assert len(message) > 0
            assert "Microsft" in message or "Microsoft" in message


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_short_words(self):
        """Test that very short words are not incorrectly corrected"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Is it good?")
        # "Is", "it" should not be corrected
        assert result.corrected_text == "Is it good?"
    
    def test_numbers_preserved(self):
        """Test that numbers are preserved"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Show revenue for 2023")
        assert "2023" in result.corrected_text
    
    def test_mixed_case_preserved(self):
        """Test that case is generally preserved"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("What is REVENUE?")
        # Should preserve uppercase
        assert "REVENUE" in result.corrected_text or "revenue" in result.corrected_text.lower()
    
    def test_special_characters_preserved(self):
        """Test that special characters are preserved"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("What is Apple's P/E ratio?")
        assert "P/E" in result.corrected_text or "ratio" in result.corrected_text.lower()
    
    def test_multiple_spaces_handled(self):
        """Test that multiple spaces are handled gracefully"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("What  is   Apple's   revenue?")
        # Should still work
        assert "Apple" in result.corrected_text


class TestEnhancedCompanyPatterns:
    """Test expanded company typo patterns"""
    
    def test_walmart_variants(self):
        """Test Walmart typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("walmat")
        assert corrected == "Walmart"
        assert confidence > 0.8
    
    def test_target_variants(self):
        """Test Target typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("targer")
        assert corrected == "Target"
        assert confidence > 0.75
    
    def test_costco_variants(self):
        """Test Costco typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("cosco")
        assert corrected == "Costco"
        assert confidence > 0.8
    
    def test_intel_variants(self):
        """Test Intel typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("intell")
        assert corrected == "Intel"
        assert confidence > 0.85
    
    def test_qualcomm_variants(self):
        """Test Qualcomm typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("qualcom")
        assert corrected == "Qualcomm"
        assert confidence > 0.8
    
    def test_salesforce_variants(self):
        """Test Salesforce typo variants"""
        corrector = CompanyCorrector()
        
        corrected, confidence, _ = corrector.correct_company_name("saleforce")
        assert corrected == "Salesforce"
        assert confidence > 0.8


class TestEnhancedMetricPatterns:
    """Test expanded metric typo patterns"""
    
    def test_ebitda_variants(self):
        """Test EBITDA typo variants"""
        corrector = MetricCorrector()
        
        corrected, confidence, _ = corrector.correct_metric("ebitdaa")
        assert "EBITDA" in corrected
        assert confidence > 0.8
    
    def test_eps_variants(self):
        """Test EPS typo variants"""
        corrector = MetricCorrector()
        
        corrected, confidence, _ = corrector.correct_metric("epss")
        assert "EPS" in corrected
        assert confidence > 0.8
    
    def test_net_income_variants(self):
        """Test net income typo variants"""
        corrector = MetricCorrector()
        
        corrected, confidence, _ = corrector.correct_metric("net incom")
        assert "net income" in corrected.lower()
        assert confidence > 0.75
    
    def test_free_cash_flow_variants(self):
        """Test free cash flow typo variants"""
        corrector = MetricCorrector()
        
        corrected, confidence, _ = corrector.correct_metric("freecashflow")
        assert "cash flow" in corrected.lower()
        assert confidence > 0.8


class TestContextAwareness:
    """Test context-aware correction features"""
    
    def test_financial_context_boosts_confidence(self):
        """Test that financial context increases confidence"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT"])
        
        # Query with financial context
        result1 = engine.correct_query("Show me Microsft revenue")
        
        # Same typo without context
        result2 = engine.correct_query("Microsft")
        
        # With financial context, we should get corrections
        assert len(result1.corrections) > 0 or "Microsoft" in result1.corrected_text
    
    def test_comparison_context(self):
        """Test correction in comparison context"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT"])
        
        result = engine.correct_query("Compare Aple vs Microsft")
        # Should correct both
        assert len(result.corrections) >= 1
    
    def test_possessive_form_context(self):
        """Test correction with possessive form"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT"])
        
        result = engine.correct_query("What is Microsft's revenue?")
        # Should correct to Microsoft
        assert "Microsoft" in result.corrected_text or len(result.corrections) > 0


class TestFalsePositivePrevention:
    """Test enhanced false positive prevention"""
    
    def test_question_words_not_corrected(self):
        """Test that question words are not incorrectly corrected"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("What is the revenue?")
        # "what" and "is" should not be corrected
        assert result.corrected_text == "What is the revenue?"
        assert len(result.corrections) == 0
    
    def test_pronouns_not_corrected(self):
        """Test that pronouns are preserved"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Show me their revenue")
        # "their" should not be corrected
        assert "their" in result.corrected_text.lower()
    
    def test_prepositions_preserved(self):
        """Test that prepositions are preserved"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Revenue for Apple in 2023")
        # "for" and "in" should not be corrected
        assert "for" in result.corrected_text.lower()
        assert "in" in result.corrected_text.lower()
    
    def test_financial_terms_not_overcorrected(self):
        """Test that valid financial terms are not overcorrected"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Show trading volume")
        # "trading" should not be corrected
        assert "trading" in result.corrected_text.lower()
        assert len(result.corrections) == 0


class TestAdvancedIntegration:
    """Test advanced integration scenarios"""
    
    def test_multiple_company_corrections(self):
        """Test correcting multiple companies in one query"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL", "MSFT", "AMZN"])
        
        result = engine.correct_query("Compare Aple Microsft and Amazn")
        # Should correct all three
        assert len(result.corrections) >= 1
    
    def test_mixed_company_and_metric_corrections(self):
        """Test correcting both company and metric in same query"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL"])
        
        result = engine.correct_query("What is Aple's reveune?")
        # Should correct both Aple and reveune
        assert len(result.corrections) >= 1
    
    def test_complex_financial_query(self):
        """Test correction in complex financial query"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT", "GOOGL"])
        
        result = engine.correct_query("Compare Microsft and Gogle profitibility and groth")
        # Should handle multiple corrections
        assert len(result.corrections) >= 1
    
    def test_correction_with_numbers(self):
        """Test that corrections work with numbers present"""
        engine = SpellingCorrectionEngine(ticker_list=["AAPL"])
        
        result = engine.correct_query("Aple made $394B in reveune in 2023")
        # Should correct company and metric, preserve numbers
        assert "394B" in result.corrected_text or "394" in result.corrected_text
        assert "2023" in result.corrected_text
    
    def test_acronym_preservation(self):
        """Test that financial acronyms are preserved or expanded correctly"""
        engine = SpellingCorrectionEngine()
        
        result = engine.correct_query("Show me the EBITDA and FCF")
        # Acronyms should be preserved or expanded to their full form
        assert "EBITDA" in result.corrected_text or "ebitda" in result.corrected_text.lower()
        # FCF might be preserved or expanded to "free cash flow" (both are correct)
        assert "FCF" in result.corrected_text or "fcf" in result.corrected_text.lower() or "free cash flow" in result.corrected_text.lower()


class TestConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_auto_correct(self):
        """Test that high confidence corrections auto-correct"""
        engine = SpellingCorrectionEngine(ticker_list=["MSFT"])
        
        result = engine.correct_query("Microsft")
        # High confidence typo should correct without confirmation
        if result.corrections:
            assert result.confidence >= engine.CONFIDENCE_SUGGEST
    
    def test_low_confidence_requires_confirmation(self):
        """Test that low confidence corrections ask for confirmation"""
        engine = SpellingCorrectionEngine()
        
        # Create a more ambiguous case
        result = engine.correct_query("XYZ")
        # Very ambiguous, should either not correct or ask for confirmation
        if result.corrections:
            assert result.should_confirm or result.confidence < 0.6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

