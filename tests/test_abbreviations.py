"""
Tests for abbreviation and acronym detection (Phase 4.2).
"""

import pytest
from src.finanlyzeos_chatbot.parsing.abbreviations import (
    AbbreviationDetector,
    AbbreviationType,
    AbbreviationMatch,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestTimePeriodAbbreviations:
    """Test time period abbreviation detection"""
    
    def test_yoy_detection(self):
        """Test YoY detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show YoY revenue growth")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'YOY'
        assert abbrevs[0].expansion == 'Year over Year'
        assert abbrevs[0].abbrev_type == AbbreviationType.TIME_PERIOD
    
    def test_qoq_detection(self):
        """Test QoQ detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Analyze QoQ growth")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'QOQ'
        assert abbrevs[0].expansion == 'Quarter over Quarter'
    
    def test_ytd_detection(self):
        """Test YTD detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show YTD performance")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'YTD'
        assert abbrevs[0].expansion == 'Year to Date'
    
    def test_mtd_detection(self):
        """Test MTD detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("MTD revenue")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Month to Date'
    
    def test_ttm_detection(self):
        """Test TTM detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("TTM earnings")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Trailing Twelve Months'


class TestMetricAbbreviations:
    """Test financial metric abbreviation detection"""
    
    def test_pe_ratio_detection(self):
        """Test P/E ratio detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("What's the P/E ratio?")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() in ['P/E', 'PE']
        assert abbrevs[0].expansion == 'Price to Earnings'
        assert abbrevs[0].abbrev_type == AbbreviationType.METRIC
    
    def test_roi_detection(self):
        """Test ROI detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show me the ROI")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'ROI'
        assert abbrevs[0].expansion == 'Return on Investment'
    
    def test_roe_detection(self):
        """Test ROE detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("What's the ROE?")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Return on Equity'
    
    def test_ebitda_detection(self):
        """Test EBITDA detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show EBITDA margins")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'EBITDA'
        assert 'Earnings Before Interest' in abbrevs[0].expansion
    
    def test_eps_detection(self):
        """Test EPS detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("What's the EPS?")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Earnings Per Share'
    
    def test_cagr_detection(self):
        """Test CAGR detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Calculate CAGR")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Compound Annual Growth Rate'
    
    def test_fcf_detection(self):
        """Test FCF detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show FCF trends")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Free Cash Flow'


class TestBusinessAbbreviations:
    """Test business model abbreviation detection"""
    
    def test_b2b_detection(self):
        """Test B2B detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("B2B companies")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'B2B'
        assert abbrevs[0].expansion == 'Business to Business'
        assert abbrevs[0].abbrev_type == AbbreviationType.BUSINESS
    
    def test_saas_detection(self):
        """Test SaaS detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("SaaS revenue models")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Software as a Service'
    
    def test_ipo_detection(self):
        """Test IPO detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("When is the IPO?")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Initial Public Offering'
    
    def test_esg_detection(self):
        """Test ESG detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("ESG metrics")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Environmental, Social, and Governance'


class TestGeneralAbbreviations:
    """Test general business abbreviation detection"""
    
    def test_ceo_detection(self):
        """Test CEO detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Who is the CEO?")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Chief Executive Officer'
        assert abbrevs[0].abbrev_type == AbbreviationType.GENERAL
    
    def test_cfo_detection(self):
        """Test CFO detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("CFO statement")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Chief Financial Officer'


class TestAbbreviationExpansion:
    """Test abbreviation expansion functionality"""
    
    def test_expand_yoy(self):
        """Test expanding YoY in text"""
        detector = AbbreviationDetector()
        
        expanded = detector.expand_text("Show YoY growth")
        assert "Year over Year" in expanded
        assert "YoY" not in expanded
    
    def test_expand_multiple(self):
        """Test expanding multiple abbreviations"""
        detector = AbbreviationDetector()
        
        expanded = detector.expand_text("YoY revenue and QoQ growth")
        assert "Year over Year" in expanded
        assert "Quarter over Quarter" in expanded
    
    def test_expand_pe_ratio(self):
        """Test expanding P/E"""
        detector = AbbreviationDetector()
        
        expanded = detector.expand_text("What's the P/E ratio?")
        assert "Price to Earnings" in expanded


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_with_context(self):
        """Test high confidence with relevant context"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("YoY revenue growth comparison")
        assert len(abbrevs) > 0
        # Should have high confidence (YoY + growth + compare context)
        assert abbrevs[0].confidence >= 0.90
    
    def test_good_confidence_basic(self):
        """Test good confidence for basic detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show ROI")
        assert len(abbrevs) > 0
        # Should have at least base confidence
        assert abbrevs[0].confidence >= 0.85


class TestHasAbbreviation:
    """Test quick abbreviation check"""
    
    def test_has_abbreviation_positive(self):
        """Test has_abbreviation returns True for abbreviation"""
        detector = AbbreviationDetector()
        
        assert detector.has_abbreviation("Show YoY growth") is True
    
    def test_has_abbreviation_negative(self):
        """Test has_abbreviation returns False for no abbreviation"""
        detector = AbbreviationDetector()
        
        assert detector.has_abbreviation("Show revenue") is False


class TestIntegrationWithParsing:
    """Test integration with parsing pipeline"""
    
    def test_parsing_detects_abbreviation(self):
        """Test that parsing detects abbreviations"""
        result = parse_to_structured("Show YoY revenue growth")
        
        assert "abbreviations" in result
        assert len(result["abbreviations"]) > 0
    
    def test_parsing_populates_details(self):
        """Test that parsing populates abbreviation details"""
        result = parse_to_structured("What's the P/E ratio?")
        
        assert "abbreviations" in result
        abbrev = result["abbreviations"][0]
        assert abbrev["type"] == "metric"
        assert "Price to Earnings" in abbrev["expansion"]
        assert abbrev["confidence"] > 0


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("")
        assert len(abbrevs) == 0
    
    def test_no_abbreviation(self):
        """Test text without abbreviation"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show me revenue")
        assert len(abbrevs) == 0
    
    def test_case_insensitive(self):
        """Test case insensitive detection"""
        detector = AbbreviationDetector()
        
        abbrevs_upper = detector.detect_abbreviations("Show YOY growth")
        abbrevs_lower = detector.detect_abbreviations("Show yoy growth")
        abbrevs_mixed = detector.detect_abbreviations("Show YoY growth")
        
        assert len(abbrevs_upper) > 0
        assert len(abbrevs_lower) > 0
        assert len(abbrevs_mixed) > 0


class TestMultipleAbbreviations:
    """Test multiple abbreviations in one query"""
    
    def test_multiple_abbreviations_detection(self):
        """Test detecting multiple abbreviations"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show YTD revenue, QoQ growth, and ROI")
        # Should detect at least 2 abbreviations
        assert len(abbrevs) >= 2
    
    def test_abbreviations_sorted_by_position(self):
        """Test abbreviations are sorted by position"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("YoY revenue and QoQ growth")
        # Should be sorted by position (YoY before QoQ)
        if len(abbrevs) >= 2:
            assert abbrevs[0].position < abbrevs[1].position


class TestExpandedTimePeriodAbbreviations:
    """Test expanded time period abbreviations"""
    
    def test_wow_detection(self):
        """Test WoW detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show WoW trends")
        assert len(abbrevs) > 0
        assert abbrevs[0].abbreviation.upper() == 'WOW'
        assert abbrevs[0].expansion == 'Week over Week'
    
    def test_wtd_detection(self):
        """Test WTD detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("WTD performance")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Week to Date'
    
    def test_htd_detection(self):
        """Test HTD detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("HTD revenue")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Half Year to Date'


class TestExpandedMetricAbbreviations:
    """Test expanded metric abbreviations"""
    
    def test_arr_detection(self):
        """Test ARR detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show ARR growth")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Annual Recurring Revenue'
    
    def test_mrr_detection(self):
        """Test MRR detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("MRR trends")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Monthly Recurring Revenue'
    
    def test_ltv_detection(self):
        """Test LTV detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Customer LTV analysis")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Lifetime Value'
    
    def test_cac_detection(self):
        """Test CAC detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("CAC payback period")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Customer Acquisition Cost'
    
    def test_wacc_detection(self):
        """Test WACC detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Calculate WACC")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Weighted Average Cost of Capital'
    
    def test_npv_detection(self):
        """Test NPV detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("NPV calculation")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Net Present Value'
    
    def test_irr_detection(self):
        """Test IRR detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("IRR analysis")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Internal Rate of Return'
    
    def test_capex_detection(self):
        """Test CAPEX detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("CAPEX spending")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Capital Expenditures'


class TestExpandedBusinessAbbreviations:
    """Test expanded business abbreviations"""
    
    def test_smb_detection(self):
        """Test SMB detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("SMB sector analysis")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Small and Medium Business'
    
    def test_vc_detection(self):
        """Test VC detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("VC funding rounds")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Venture Capital'
    
    def test_ai_detection(self):
        """Test AI detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("AI companies revenue")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Artificial Intelligence'
    
    def test_kpi_detection(self):
        """Test KPI detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("KPI tracking")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Key Performance Indicator'


class TestExpandedGeneralAbbreviations:
    """Test expanded general abbreviations"""
    
    def test_gaap_detection(self):
        """Test GAAP detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("GAAP accounting standards")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Generally Accepted Accounting Principles'
    
    def test_nyse_detection(self):
        """Test NYSE detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("NYSE listed companies")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'New York Stock Exchange'
    
    def test_etf_detection(self):
        """Test ETF detection"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("ETF holdings")
        assert len(abbrevs) > 0
        assert abbrevs[0].expansion == 'Exchange Traded Fund'


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_what_does_stand_for_not_detected(self):
        """Test 'what does X stand for' doesn't trigger"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("What does ROI stand for?")
        # Should NOT detect (meta question about abbreviation)
        assert len(abbrevs) == 0
    
    def test_define_not_detected(self):
        """Test 'define X' doesn't trigger"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Define EBITDA for me")
        # Should NOT detect (request for definition)
        assert len(abbrevs) == 0


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_with_multiple_context(self):
        """Test high confidence with multiple context clues"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Analyze YoY revenue growth trend performance")
        assert len(abbrevs) > 0
        # Should have very high confidence (temporal abbrev + growth + trend + performance)
        assert abbrevs[0].confidence >= 0.95
    
    def test_confidence_with_slash(self):
        """Test confidence boost for slash abbreviations"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show P/E ratio")
        assert len(abbrevs) > 0
        # Should have confidence boost for slash
        assert abbrevs[0].confidence >= 0.90
    
    def test_confidence_uppercase_abbrev(self):
        """Test confidence boost for uppercase abbreviations"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("EBITDA margins")
        assert len(abbrevs) > 0
        # Should have confidence boost for uppercase
        assert abbrevs[0].confidence >= 0.88


class TestComplexAbbreviationScenarios:
    """Test complex abbreviation scenarios"""
    
    def test_multiple_types_in_one_query(self):
        """Test multiple abbreviation types in one query"""
        detector = AbbreviationDetector()
        
        abbrevs = detector.detect_abbreviations("Show YoY EPS growth for B2B SaaS companies")
        # Should detect: YoY (time), EPS (metric), B2B (business), SaaS (business)
        assert len(abbrevs) >= 3
        
        # Check different types are detected
        types = {a.abbrev_type for a in abbrevs}
        assert AbbreviationType.TIME_PERIOD in types
        assert AbbreviationType.METRIC in types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

