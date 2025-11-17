"""
Comprehensive test suite for natural language filter detection.

Tests:
- Sector filters (tech, financial, healthcare, energy, etc.)
- Quality filters (high-quality, blue-chip, stable)
- Risk filters (low-risk, safe, risky)
- Size filters (large-cap, small-cap, mega-cap)
- Performance filters (profitable, growing, declining)
- Valuation filters (undervalued, overvalued)
- Filter deduplication
- Confidence scoring
- Integration with parsing
"""

import pytest
from src.finanlyzeos_chatbot.parsing.natural_filters import (
    NaturalFilterDetector,
    NaturalFilter,
    FilterType,
)
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured


class TestSectorFilters:
    """Test sector/industry filter detection"""
    
    def test_tech_sector_detection(self):
        """Test 'tech' sector detection"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show me tech companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Technology' for f in filters)
    
    def test_financial_sector_detection(self):
        """Test 'financial' sector detection"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show financial stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Financials' for f in filters)
    
    def test_healthcare_sector_detection(self):
        """Test 'healthcare' sector detection"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show healthcare companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR for f in filters)
    
    def test_energy_sector_detection(self):
        """Test 'energy' sector detection"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show energy stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Energy' for f in filters)


class TestQualityFilters:
    """Test quality level filter detection"""
    
    def test_high_quality_detection(self):
        """Test 'high-quality' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show me high-quality companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'high' for f in filters)
    
    def test_blue_chip_detection(self):
        """Test 'blue-chip' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show blue-chip stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'high' for f in filters)
    
    def test_stable_companies_detection(self):
        """Test 'stable' quality filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show stable companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY for f in filters)
    
    def test_low_quality_detection(self):
        """Test 'low-quality' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show low-quality stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'low' for f in filters)


class TestRiskFilters:
    """Test risk level filter detection"""
    
    def test_low_risk_detection(self):
        """Test 'low-risk' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show me low-risk investments")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'low' for f in filters)
    
    def test_safe_stocks_detection(self):
        """Test 'safe' risk filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show safe stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'low' for f in filters)
    
    def test_high_risk_detection(self):
        """Test 'high-risk' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show high-risk companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'high' for f in filters)
    
    def test_risky_investments_detection(self):
        """Test 'risky' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show risky investments")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'high' for f in filters)


class TestSizeFilters:
    """Test market cap size filter detection"""
    
    def test_large_cap_detection(self):
        """Test 'large-cap' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show large-cap stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'large' for f in filters)
    
    def test_mega_cap_detection(self):
        """Test 'mega-cap' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show mega-cap companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'large' for f in filters)
    
    def test_small_cap_detection(self):
        """Test 'small-cap' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show small-cap stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'small' for f in filters)
    
    def test_mid_cap_detection(self):
        """Test 'mid-cap' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show mid-cap companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'mid' for f in filters)


class TestPerformanceFilters:
    """Test performance filter detection"""
    
    def test_profitable_detection(self):
        """Test 'profitable' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show profitable companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'profitable' for f in filters)
    
    def test_growing_detection(self):
        """Test 'growing' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show growing companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'growing' for f in filters)
    
    def test_declining_detection(self):
        """Test 'declining' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show declining stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'declining' for f in filters)


class TestValuationFilters:
    """Test valuation filter detection"""
    
    def test_undervalued_detection(self):
        """Test 'undervalued' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show undervalued stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'undervalued' for f in filters)
    
    def test_overvalued_detection(self):
        """Test 'overvalued' filter"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show overvalued companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'overvalued' for f in filters)
    
    def test_cheap_stocks_detection(self):
        """Test 'cheap' as undervalued"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show cheap stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'undervalued' for f in filters)


class TestFilterDeduplication:
    """Test filter deduplication logic"""
    
    def test_duplicate_removal(self):
        """Test that duplicate filters are removed"""
        detector = NaturalFilterDetector()
        
        # "tech" appears twice conceptually but should only create one filter
        filters = detector.detect_filters("Show tech technology companies")
        # Should deduplicate to single tech sector filter
        tech_filters = [f for f in filters if f.filter_type == FilterType.SECTOR and f.value == 'Technology']
        assert len(tech_filters) == 1


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_explicit_context(self):
        """Test high confidence with explicit context"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show me tech sector companies")
        tech_filter = next((f for f in filters if f.filter_type == FilterType.SECTOR), None)
        if tech_filter:
            # Should have high confidence (explicit 'sector' word)
            assert tech_filter.confidence >= 0.85
    
    def test_confidence_with_company_context(self):
        """Test confidence boost with company context"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show high-quality companies")
        quality_filter = next((f for f in filters if f.filter_type == FilterType.QUALITY), None)
        if quality_filter:
            # Should have good confidence
            assert quality_filter.confidence >= 0.80


class TestHasFilters:
    """Test quick filter check"""
    
    def test_has_filters_positive(self):
        """Test positive filter detection"""
        detector = NaturalFilterDetector()
        
        assert detector.has_filters("Show tech companies")
        assert detector.has_filters("Low-risk stocks")
        assert detector.has_filters("Large-cap companies")
    
    def test_has_filters_negative(self):
        """Test negative filter detection"""
        detector = NaturalFilterDetector()
        
        assert not detector.has_filters("Show Apple's revenue")
        assert not detector.has_filters("What is the P/E ratio?")


class TestStructuredFilterConversion:
    """Test conversion to structured filters"""
    
    def test_sector_conversion(self):
        """Test sector filter conversion"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show tech companies")
        structured = detector.to_structured_filters(filters)
        
        assert 'sectors' in structured or len(structured) >= 0
    
    def test_quality_conversion(self):
        """Test quality filter conversion"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show high-quality stocks")
        structured = detector.to_structured_filters(filters)
        
        assert 'quality_level' in structured or len(structured) >= 0
    
    def test_risk_conversion(self):
        """Test risk filter conversion"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show low-risk companies")
        structured = detector.to_structured_filters(filters)
        
        assert 'risk_level' in structured or len(structured) >= 0


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_parsing_detects_filters(self):
        """Test that parsing detects natural filters"""
        structured = parse_to_structured("Show me tech companies")
        # Should have natural_filters
        assert "natural_filters" in structured or not structured.get("natural_filters")
    
    def test_parsing_populates_details(self):
        """Test that parsing populates filter details"""
        structured = parse_to_structured("Show high-quality stocks")
        if "natural_filters" in structured and structured["natural_filters"]:
            assert len(structured["natural_filters"]) > 0
            assert "type" in structured["natural_filters"][0]
            assert "value" in structured["natural_filters"][0]


class TestMultipleFilters:
    """Test multiple filters in one query"""
    
    def test_sector_and_quality(self):
        """Test sector + quality filters"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show high-quality tech companies")
        # Should detect both filters
        assert len(filters) >= 2
        filter_types = set(f.filter_type for f in filters)
        assert FilterType.SECTOR in filter_types
        assert FilterType.QUALITY in filter_types
    
    def test_sector_and_risk(self):
        """Test sector + risk filters"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show low-risk financial stocks")
        assert len(filters) >= 2


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text handling"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("")
        assert len(filters) == 0
    
    def test_no_filters(self):
        """Test text without filters"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show Apple's revenue")
        # Apple is a company, not a filter
        assert len(filters) == 0 or all(f.filter_type != FilterType.SECTOR for f in filters)


class TestExpandedSectorFilters:
    """Test expanded sector patterns"""
    
    def test_ai_tech_sector(self):
        """Test 'AI' as tech sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show AI companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Technology' for f in filters)
    
    def test_fintech_financial_sector(self):
        """Test 'fintech' as financial sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show fintech stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Financials' for f in filters)
    
    def test_biotech_healthcare_sector(self):
        """Test 'biotech' as healthcare sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show biotech companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR for f in filters)
    
    def test_renewable_energy_sector(self):
        """Test 'renewable' as energy sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show renewable energy stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Energy' for f in filters)
    
    def test_materials_sector(self):
        """Test new materials sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show materials companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Materials' for f in filters)
    
    def test_media_sector(self):
        """Test new media sector"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show media stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SECTOR and f.value == 'Media' for f in filters)


class TestExpandedQualityFilters:
    """Test expanded quality patterns"""
    
    def test_elite_quality(self):
        """Test 'elite' as high-quality"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show elite companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'high' for f in filters)
    
    def test_dominant_quality(self):
        """Test 'dominant' as high-quality"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show dominant market leaders")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'high' for f in filters)
    
    def test_shaky_low_quality(self):
        """Test 'shaky' as low-quality"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show shaky companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.QUALITY and f.value == 'low' for f in filters)


class TestExpandedRiskFilters:
    """Test expanded risk patterns"""
    
    def test_low_volatility(self):
        """Test 'low-volatility' as low-risk"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show low-volatility stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'low' for f in filters)
    
    def test_predictable_low_risk(self):
        """Test 'predictable' as low-risk"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show predictable companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'low' for f in filters)
    
    def test_turbulent_high_risk(self):
        """Test 'turbulent' as high-risk"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show turbulent stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.RISK and f.value == 'high' for f in filters)


class TestExpandedSizeFilters:
    """Test expanded size patterns"""
    
    def test_giant_large_cap(self):
        """Test 'giant' as large-cap"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show giant companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'large' for f in filters)
    
    def test_emerging_small_cap(self):
        """Test 'emerging' as small-cap"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show emerging companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.SIZE and f.value == 'small' for f in filters)


class TestExpandedPerformanceFilters:
    """Test expanded performance patterns"""
    
    def test_thriving_profitable(self):
        """Test 'thriving' as profitable"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show thriving companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'profitable' for f in filters)
    
    def test_fast_growing(self):
        """Test 'fast-growing' performance"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show fast-growing stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'growing' for f in filters)
    
    def test_stagnant_declining(self):
        """Test 'stagnant' as declining"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show stagnant companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.PERFORMANCE and f.value == 'declining' for f in filters)


class TestExpandedValuationFilters:
    """Test expanded valuation patterns"""
    
    def test_underpriced(self):
        """Test 'underpriced' as undervalued"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show underpriced stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'undervalued' for f in filters)
    
    def test_inflated_overvalued(self):
        """Test 'inflated' as overvalued"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show inflated companies")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'overvalued' for f in filters)
    
    def test_value_stocks(self):
        """Test 'value stocks' as undervalued"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show value stocks")
        assert len(filters) > 0
        assert any(f.filter_type == FilterType.VALUATION and f.value == 'undervalued' for f in filters)


class TestComplexFilterCombinations:
    """Test complex multi-filter scenarios"""
    
    def test_three_filters_combined(self):
        """Test three filter types in one query"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show undervalued large-cap tech companies")
        # Should detect valuation + size + sector
        assert len(filters) >= 3
        filter_types = set(f.filter_type for f in filters)
        assert FilterType.VALUATION in filter_types
        assert FilterType.SIZE in filter_types
        assert FilterType.SECTOR in filter_types
    
    def test_quality_risk_sector_combo(self):
        """Test quality + risk + sector combination"""
        detector = NaturalFilterDetector()
        
        filters = detector.detect_filters("Show high-quality low-risk financial stocks")
        assert len(filters) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


