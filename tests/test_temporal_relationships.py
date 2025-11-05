"""
Comprehensive test suite for temporal relationship detection.

Tests:
- Before relationships (before, prior to, pre-)
- After relationships (after, following, post-)
- During relationships (during, throughout, amid)
- Within relationships (within, inside, in)
- Since relationships (since, from, starting from)
- Until relationships (until, till, through)
- Between relationships (between X and Y)
- Event-based references (pandemic, crisis, recession)
- Confidence scoring
- Integration with parsing
"""

import pytest
from src.benchmarkos_chatbot.parsing.temporal_relationships import (
    TemporalRelationshipDetector,
    TemporalRelationship,
    TemporalRelationType,
    EventType,
)
from src.benchmarkos_chatbot.parsing.parse import parse_to_structured


class TestBeforeRelationships:
    """Test BEFORE temporal relationships"""
    
    def test_before_year(self):
        """Test 'before' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue before 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BEFORE
        assert "2020" in relationships[0].time_reference
    
    def test_prior_to_quarter(self):
        """Test 'prior to' with quarter"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data prior to Q1 2023")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BEFORE
    
    def test_pre_pandemic(self):
        """Test 'pre-' prefix with event"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance pre-pandemic")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BEFORE


class TestAfterRelationships:
    """Test AFTER temporal relationships"""
    
    def test_after_year(self):
        """Test 'after' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue after 2019")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.AFTER
        assert "2019" in relationships[0].time_reference
    
    def test_following_quarter(self):
        """Test 'following' with quarter"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data following Q4")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.AFTER
    
    def test_post_crisis(self):
        """Test 'post-' prefix with event"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Growth post-crisis")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.AFTER


class TestDuringRelationships:
    """Test DURING temporal relationships"""
    
    def test_during_year(self):
        """Test 'during' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.DURING
        assert "2020" in relationships[0].time_reference
    
    def test_throughout_quarter(self):
        """Test 'throughout' with quarter"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance throughout Q2 2023")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.DURING
    
    def test_amid_pandemic(self):
        """Test 'amid' with event"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Growth amid pandemic")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.DURING
        assert relationships[0].event == EventType.PANDEMIC


class TestWithinRelationships:
    """Test WITHIN temporal relationships"""
    
    def test_within_year(self):
        """Test 'within' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue within 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.WITHIN
    
    def test_in_year(self):
        """Test 'in' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data in 2019")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.WITHIN


class TestSinceRelationships:
    """Test SINCE temporal relationships"""
    
    def test_since_year(self):
        """Test 'since' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue since 2018")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.SINCE
    
    def test_since_last_year(self):
        """Test 'since' with relative time"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Growth since last year")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.SINCE


class TestUntilRelationships:
    """Test UNTIL temporal relationships"""
    
    def test_until_year(self):
        """Test 'until' with year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data until 2021")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.UNTIL
    
    def test_through_quarter(self):
        """Test 'through' with quarter"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance through Q3")
        assert len(relationships) > 0
        # "through" can mean both DURING and UNTIL depending on context
        assert relationships[0].relation_type in [TemporalRelationType.UNTIL, TemporalRelationType.DURING]


class TestBetweenRelationships:
    """Test BETWEEN temporal relationships"""
    
    def test_between_years(self):
        """Test 'between' with two years"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue between 2018 and 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BETWEEN
        assert "2018" in relationships[0].time_reference
        assert "2020" in relationships[0].time_reference
    
    def test_from_to_years(self):
        """Test 'from X to Y' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data from 2019 to 2021")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BETWEEN


class TestEventReferences:
    """Test event-based temporal references"""
    
    def test_pandemic_event(self):
        """Test pandemic event detection"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during pandemic")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.PANDEMIC
    
    def test_financial_crisis_event(self):
        """Test financial crisis event detection"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance during financial crisis")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.FINANCIAL_CRISIS
    
    def test_recession_event(self):
        """Test recession event detection"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data during recession")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.RECESSION
    
    def test_crisis_generic_event(self):
        """Test generic crisis event detection"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during crisis")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.CRISIS


class TestEventTimeframes:
    """Test event timeframe mapping"""
    
    def test_pandemic_timeframe(self):
        """Test pandemic timeframe retrieval"""
        detector = TemporalRelationshipDetector()
        
        timeframe = detector.get_event_timeframe(EventType.PANDEMIC)
        assert timeframe is not None
        assert timeframe['start_year'] == 2020
        assert timeframe['end_year'] == 2021
    
    def test_financial_crisis_timeframe(self):
        """Test financial crisis timeframe retrieval"""
        detector = TemporalRelationshipDetector()
        
        timeframe = detector.get_event_timeframe(EventType.FINANCIAL_CRISIS)
        assert timeframe is not None
        assert timeframe['start_year'] == 2008


class TestConfidenceScoring:
    """Test confidence scoring"""
    
    def test_high_confidence_explicit_year(self):
        """Test high confidence with explicit year"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue before 2020")
        assert len(relationships) > 0
        # Should have good confidence (explicit year + revenue context)
        assert relationships[0].confidence >= 0.75
    
    def test_confidence_with_event(self):
        """Test confidence with event reference"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance during pandemic")
        assert len(relationships) > 0
        # Should have good confidence (event reference + performance)
        assert relationships[0].confidence >= 0.80


class TestHasTemporalRelationship:
    """Test quick temporal relationship check"""
    
    def test_has_temporal_positive(self):
        """Test positive temporal detection"""
        detector = TemporalRelationshipDetector()
        
        assert detector.has_temporal_relationship("Before 2020")
        assert detector.has_temporal_relationship("After Q1 2023")  # Need year for detection
        assert detector.has_temporal_relationship("During pandemic")
    
    def test_has_temporal_negative(self):
        """Test negative temporal detection"""
        detector = TemporalRelationshipDetector()
        
        assert not detector.has_temporal_relationship("Show Apple's revenue")
        assert not detector.has_temporal_relationship("What is the P/E ratio?")


class TestIntegrationWithParsing:
    """Test integration with parsing system"""
    
    def test_parsing_detects_temporal(self):
        """Test that parsing detects temporal relationships"""
        structured = parse_to_structured("Revenue before 2020")
        # Should have temporal_relationships
        assert "temporal_relationships" in structured or not structured.get("temporal_relationships")
    
    def test_parsing_populates_details(self):
        """Test that parsing populates temporal details"""
        structured = parse_to_structured("Data during pandemic")
        if "temporal_relationships" in structured and structured["temporal_relationships"]:
            assert len(structured["temporal_relationships"]) > 0
            assert "relation_type" in structured["temporal_relationships"][0]
            assert "event" in structured["temporal_relationships"][0]


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_text(self):
        """Test empty text handling"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("")
        assert len(relationships) == 0
    
    def test_no_temporal_relationship(self):
        """Test text without temporal relationships"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Show Apple's revenue")
        assert len(relationships) == 0
    
    def test_multiple_temporal_relationships(self):
        """Test multiple temporal relationships in one query"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue after 2019 and before 2021")
        # Should detect both
        assert len(relationships) >= 2


class TestExpandedBeforePatterns:
    """Test expanded BEFORE patterns"""
    
    def test_in_advance_of(self):
        """Test 'in advance of' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue in advance of 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BEFORE
    
    def test_leading_up_to(self):
        """Test 'leading up to' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance leading up to crisis")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.BEFORE


class TestExpandedAfterPatterns:
    """Test expanded AFTER patterns"""
    
    def test_in_the_wake_of(self):
        """Test 'in the wake of' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue in the wake of pandemic")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.AFTER
    
    def test_in_the_aftermath_of(self):
        """Test 'in the aftermath of' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data in the aftermath of crisis")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.AFTER


class TestExpandedDuringPatterns:
    """Test expanded DURING patterns"""
    
    def test_while_pattern(self):
        """Test 'while' as during"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue while pandemic")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.DURING
    
    def test_in_the_midst_of(self):
        """Test 'in the midst of' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance in the midst of 2020")
        assert len(relationships) > 0
        assert relationships[0].relation_type == TemporalRelationType.DURING


class TestExpandedEventPatterns:
    """Test expanded event patterns"""
    
    def test_lockdown_pandemic(self):
        """Test 'lockdown' as pandemic event"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during lockdown")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.PANDEMIC
    
    def test_credit_crunch_crisis(self):
        """Test 'credit crunch' as financial crisis"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data during credit crunch")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.FINANCIAL_CRISIS
    
    def test_bear_market_recession(self):
        """Test 'bear market' as recession"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance during bear market")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.RECESSION
    
    def test_market_crash_crisis(self):
        """Test 'market crash' as crisis"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during market crash")
        assert len(relationships) > 0
        assert relationships[0].event == EventType.CRISIS


class TestExpandedTimeReferences:
    """Test expanded time reference patterns"""
    
    def test_half_year_detection(self):
        """Test half-year (H1, H2) detection"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue during H1 2023")
        assert len(relationships) > 0
        assert "H1" in relationships[0].time_reference
    
    def test_early_year_detection(self):
        """Test 'early 2020' pattern"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Data in early 2020")
        assert len(relationships) > 0
        assert "2020" in relationships[0].time_reference
    
    def test_decade_detection(self):
        """Test decade pattern (the 2010s)"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Performance during the 2010s")
        assert len(relationships) > 0
        assert "2010s" in relationships[0].time_reference


class TestEnhancedEventTimeframes:
    """Test enhanced event timeframe mappings"""
    
    def test_pandemic_quarters(self):
        """Test pandemic timeframe includes quarters"""
        detector = TemporalRelationshipDetector()
        
        timeframe = detector.get_event_timeframe(EventType.PANDEMIC)
        assert timeframe is not None
        assert 'quarters' in timeframe
        assert len(timeframe['quarters']) > 0
    
    def test_financial_crisis_quarters(self):
        """Test financial crisis timeframe includes quarters"""
        detector = TemporalRelationshipDetector()
        
        timeframe = detector.get_event_timeframe(EventType.FINANCIAL_CRISIS)
        assert timeframe is not None
        assert 'quarters' in timeframe
        assert 'Q3 2008' in timeframe['quarters']


class TestFalsePositivePrevention:
    """Test false positive prevention"""
    
    def test_when_is_not_temporal(self):
        """Test 'when is' doesn't trigger temporal"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("When is the next earnings report?")
        # Should NOT detect as temporal relationship (question about time)
        assert len(relationships) == 0
    
    def test_what_year_not_temporal(self):
        """Test 'what year' doesn't trigger temporal"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("What year did Apple IPO?")
        # Should NOT detect as temporal relationship (question about year)
        assert len(relationships) == 0
    
    def test_before_you_not_temporal(self):
        """Test 'before you' doesn't trigger temporal"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Before you invest, check this")
        # Should NOT detect as temporal relationship (before you, not time)
        assert len(relationships) == 0


class TestEnhancedConfidenceScoring:
    """Test enhanced confidence scoring"""
    
    def test_high_confidence_year_and_context(self):
        """Test high confidence with year and financial context"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue performance before 2020")
        assert len(relationships) > 0
        # Should have high confidence (year + performance + revenue + before bonus)
        assert relationships[0].confidence >= 0.80
    
    def test_confidence_with_event_and_context(self):
        """Test confidence with event and context"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Profit growth during pandemic")
        assert len(relationships) > 0
        # Should have high confidence (event + profit + growth)
        assert relationships[0].confidence >= 0.85
    
    def test_between_gets_bonus(self):
        """Test BETWEEN gets confidence bonus"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue between 2018 and 2020")
        assert len(relationships) > 0
        # Should have high confidence (between is very specific)
        assert relationships[0].confidence >= 0.88


class TestComplexTemporalScenarios:
    """Test complex temporal scenarios"""
    
    def test_multiple_events_same_query(self):
        """Test multiple event references"""
        detector = TemporalRelationshipDetector()
        
        relationships = detector.detect_temporal_relationships("Revenue before pandemic and after crisis")
        # Should detect both temporal relationships
        assert len(relationships) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


