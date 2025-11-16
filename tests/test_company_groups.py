"""
Tests for company group detection (Phase 4.1).
"""

import pytest
from src.finanlyzeos_chatbot.parsing.company_groups import (
    CompanyGroupDetector,
    GroupType,
    CompanyGroup,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestTechAcronymGroups:
    """Test tech acronym group detection"""
    
    def test_faang_detection(self):
        """Test FAANG group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show me revenue for FAANG")
        assert len(groups) > 0
        assert groups[0].name in ['FAANG', 'faang']
        assert groups[0].group_type == GroupType.TECH_ACRONYM
        assert len(groups[0].tickers) == 5
        assert 'META' in groups[0].tickers
        assert 'AAPL' in groups[0].tickers
    
    def test_fang_detection(self):
        """Test FANG group detection (without Apple)"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Compare FANG stocks")
        assert len(groups) > 0
        assert len(groups[0].tickers) == 4
        assert 'AAPL' not in groups[0].tickers
    
    def test_mag7_detection(self):
        """Test Magnificent 7 detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze MAG7 performance")
        assert len(groups) > 0
        assert len(groups[0].tickers) == 7
        assert 'NVDA' in groups[0].tickers
        assert 'TSLA' in groups[0].tickers
    
    def test_magnificent_7_full_name(self):
        """Test full 'Magnificent 7' name"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("How is the Magnificent 7 doing?")
        assert len(groups) > 0
        assert len(groups[0].tickers) == 7
    
    def test_mamaa_detection(self):
        """Test MAMAA group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Compare MAMAA companies")
        assert len(groups) > 0
        assert len(groups[0].tickers) == 5
        assert 'MSFT' in groups[0].tickers


class TestIndustryGroups:
    """Test industry group detection"""
    
    def test_big_tech_detection(self):
        """Test Big Tech group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show me Big Tech performance")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDUSTRY
        assert len(groups[0].tickers) >= 5
        assert 'AAPL' in groups[0].tickers
        assert 'MSFT' in groups[0].tickers
    
    def test_big_banks_detection(self):
        """Test Big Banks group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze Big Banks")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDUSTRY
        assert 'JPM' in groups[0].tickers
        assert 'BAC' in groups[0].tickers
    
    def test_big_pharma_detection(self):
        """Test Big Pharma group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Big Pharma revenue trends")
        assert len(groups) > 0
        assert 'JNJ' in groups[0].tickers
        assert 'PFE' in groups[0].tickers
    
    def test_big_oil_detection(self):
        """Test Big Oil group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("How is Big Oil performing?")
        assert len(groups) > 0
        assert 'XOM' in groups[0].tickers
        assert 'CVX' in groups[0].tickers


class TestIndexGroups:
    """Test index-based group detection"""
    
    def test_dow_30_detection(self):
        """Test Dow 30 group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show Dow 30 companies")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDEX
        assert len(groups[0].tickers) >= 5
    
    def test_djia_detection(self):
        """Test DJIA detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze DJIA stocks")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDEX


class TestGroupExpansion:
    """Test group expansion functionality"""
    
    def test_expand_faang(self):
        """Test expanding FAANG to tickers"""
        detector = CompanyGroupDetector()
        
        tickers = detector.expand_group("FAANG")
        assert tickers is not None
        assert len(tickers) == 5
        assert 'META' in tickers
        assert 'GOOGL' in tickers
    
    def test_expand_mag7(self):
        """Test expanding MAG7 to tickers"""
        detector = CompanyGroupDetector()
        
        tickers = detector.expand_group("MAG7")
        assert tickers is not None
        assert len(tickers) == 7
    
    def test_expand_unknown_group(self):
        """Test expanding unknown group returns None"""
        detector = CompanyGroupDetector()
        
        tickers = detector.expand_group("UNKNOWN")
        assert tickers is None


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_tech_acronym(self):
        """Test high confidence for tech acronyms"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show FAANG stocks")
        assert len(groups) > 0
        # Tech acronyms should have very high confidence
        assert groups[0].confidence >= 0.95
    
    def test_good_confidence_industry_group(self):
        """Test good confidence for industry groups"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Big Tech performance")
        assert len(groups) > 0
        # Industry groups should have high confidence
        assert groups[0].confidence >= 0.90


class TestHasGroup:
    """Test quick group check"""
    
    def test_has_group_positive(self):
        """Test has_group returns True for group"""
        detector = CompanyGroupDetector()
        
        assert detector.has_group("Show me FAANG stocks") is True
    
    def test_has_group_negative(self):
        """Test has_group returns False for no group"""
        detector = CompanyGroupDetector()
        
        assert detector.has_group("Show me Apple revenue") is False


class TestIntegrationWithParsing:
    """Test integration with parsing pipeline"""
    
    def test_parsing_detects_group(self):
        """Test that parsing detects groups"""
        result = parse_to_structured("Show revenue for FAANG")
        
        assert "company_groups" in result
        assert len(result["company_groups"]) > 0
    
    def test_parsing_expands_tickers(self):
        """Test that parsing expands groups to tickers"""
        result = parse_to_structured("Show revenue for FAANG")
        
        # Check that tickers are populated with FAANG members
        tickers = [t['ticker'] for t in result['tickers']]
        assert 'META' in tickers or 'AAPL' in tickers or 'AMZN' in tickers
    
    def test_parsing_populates_details(self):
        """Test that parsing populates group details"""
        result = parse_to_structured("Analyze MAG7 performance")
        
        assert "company_groups" in result
        group = result["company_groups"][0]
        assert group["type"] == "tech_acronym"
        assert len(group["tickers"]) == 7
        assert group["confidence"] > 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("")
        assert len(groups) == 0
    
    def test_no_group(self):
        """Test text without group"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show me Apple revenue")
        assert len(groups) == 0
    
    def test_case_insensitive(self):
        """Test case insensitive detection"""
        detector = CompanyGroupDetector()
        
        groups_upper = detector.detect_groups("Show FAANG")
        groups_lower = detector.detect_groups("Show faang")
        
        assert len(groups_upper) > 0
        assert len(groups_lower) > 0


class TestMultipleGroups:
    """Test multiple groups in one query"""
    
    def test_multiple_groups_detection(self):
        """Test detecting multiple groups"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Compare FAANG vs Big Banks")
        # Should detect at least one group
        assert len(groups) >= 1


class TestExpandedTechAcronyms:
    """Test expanded tech acronym groups"""
    
    def test_matana_detection(self):
        """Test MATANA group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze MATANA stocks")
        assert len(groups) > 0
        assert len(groups[0].tickers) == 6
        assert 'NVDA' in groups[0].tickers
        assert 'TSLA' in groups[0].tickers


class TestExpandedIndustryGroups:
    """Test expanded industry groups"""
    
    def test_big_auto_detection(self):
        """Test Big Auto group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show Big Auto revenue")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDUSTRY
        assert 'TSLA' in groups[0].tickers
        assert 'F' in groups[0].tickers
    
    def test_big_airlines_detection(self):
        """Test Big Airlines group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze Big Airlines performance")
        assert len(groups) > 0
        assert 'DAL' in groups[0].tickers
        assert 'UAL' in groups[0].tickers
    
    def test_big_defense_detection(self):
        """Test Big Defense group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Compare Big Defense stocks")
        assert len(groups) > 0
        assert 'LMT' in groups[0].tickers
        assert 'BA' in groups[0].tickers
    
    def test_cloud_companies_detection(self):
        """Test Cloud Companies group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show Cloud Companies revenue")
        assert len(groups) > 0
        assert 'MSFT' in groups[0].tickers
        assert 'AMZN' in groups[0].tickers
    
    def test_chip_makers_detection(self):
        """Test Chip Makers group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze Chip Makers")
        assert len(groups) > 0
        assert 'NVDA' in groups[0].tickers
        assert 'AMD' in groups[0].tickers
    
    def test_semiconductor_detection(self):
        """Test Semiconductor group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Semiconductor companies performance")
        assert len(groups) > 0
        assert 'NVDA' in groups[0].tickers
        assert 'INTC' in groups[0].tickers
    
    def test_payment_processors_detection(self):
        """Test Payment Processors group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Payment Processors trends")
        assert len(groups) > 0
        assert 'V' in groups[0].tickers
        assert 'MA' in groups[0].tickers
    
    def test_streaming_detection(self):
        """Test Streaming group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Streaming services revenue")
        assert len(groups) > 0
        assert 'NFLX' in groups[0].tickers
        assert 'DIS' in groups[0].tickers


class TestExpandedIndexGroups:
    """Test expanded index groups"""
    
    def test_sp500_leaders_detection(self):
        """Test S&P 500 Leaders group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show S&P 500 leaders")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDEX
        assert len(groups[0].tickers) >= 5
    
    def test_nasdaq100_leaders_detection(self):
        """Test Nasdaq 100 Leaders group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Nasdaq 100 leaders performance")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.INDEX


class TestCategoryGroups:
    """Test category groups"""
    
    def test_dividend_aristocrats_detection(self):
        """Test Dividend Aristocrats group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show Dividend Aristocrats")
        assert len(groups) > 0
        assert groups[0].group_type == GroupType.CATEGORY
        assert 'JNJ' in groups[0].tickers
        assert 'PG' in groups[0].tickers
    
    def test_growth_stocks_detection(self):
        """Test Growth Stocks group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze Growth Stocks")
        assert len(groups) > 0
        assert 'NVDA' in groups[0].tickers
        assert 'TSLA' in groups[0].tickers
    
    def test_value_stocks_detection(self):
        """Test Value Stocks group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Compare Value Stocks")
        assert len(groups) > 0
        assert 'BRK.B' in groups[0].tickers
        assert 'JPM' in groups[0].tickers
    
    def test_blue_chips_detection(self):
        """Test Blue Chips group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Show Blue Chips performance")
        assert len(groups) > 0
        assert 'AAPL' in groups[0].tickers
        assert 'MSFT' in groups[0].tickers
    
    def test_mega_caps_detection(self):
        """Test Mega Caps group detection"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Mega Caps revenue")
        assert len(groups) > 0
        assert 'AAPL' in groups[0].tickers
        assert 'NVDA' in groups[0].tickers


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_what_is_in_faang_not_group(self):
        """Test 'what is in FAANG' doesn't trigger group expansion"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("What is in FAANG?")
        # Should NOT detect as group expansion (question about group composition)
        assert len(groups) == 0
    
    def test_how_many_companies_not_group(self):
        """Test 'how many companies in' doesn't trigger"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("How many companies in MAG7?")
        # Should NOT detect (meta question about group)
        assert len(groups) == 0


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_with_context(self):
        """Test high confidence with financial context"""
        detector = CompanyGroupDetector()
        
        groups = detector.detect_groups("Analyze FAANG revenue performance")
        assert len(groups) > 0
        # Should have very high confidence (acronym + analyze + revenue)
        assert groups[0].confidence >= 0.98
    
    def test_confidence_penalty_long_text(self):
        """Test confidence penalty for long text"""
        detector = CompanyGroupDetector()
        
        short_text = "Show FAANG revenue"
        long_text = "I was reading an article about FAANG companies and their impact on the economy and wondering if you could show me some other data about technology companies in general"
        
        groups_short = detector.detect_groups(short_text)
        groups_long = detector.detect_groups(long_text)
        
        # Short text should have higher confidence
        if len(groups_long) > 0:
            assert groups_short[0].confidence > groups_long[0].confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

