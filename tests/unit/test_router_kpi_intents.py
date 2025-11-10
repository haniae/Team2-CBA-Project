from __future__ import annotations

from benchmarkos_chatbot.parsing.parse import parse_to_structured
from benchmarkos_chatbot.routing import EnhancedIntent, enhance_structured_parse


def test_router_compute_kpi_financial_year():
    text = "Calculate Gross Margin for TSLA financial year 2024"
    structured = parse_to_structured(text)
    routing = enhance_structured_parse(text, structured)
    assert routing.intent == EnhancedIntent.COMPUTE_KPI
    assert routing.slots
    assert routing.slots.get("period", {}).get("year") == 2024
    assert routing.slots.get("tickers") == ["TSLA"]


def test_router_source_lookup_when_period_missing():
    text = "Calculate Gross Margin for TSLA"
    structured = parse_to_structured(text)
    routing = enhance_structured_parse(text, structured)
    assert routing.intent == EnhancedIntent.SOURCE_LOOKUP
    assert routing.missing_slots is not None
    assert "period" in routing.missing_slots


def test_router_handles_metric_ticker_phrase():
    text = "Gross Margin TSLA FY2024"
    structured = parse_to_structured(text)
    routing = enhance_structured_parse(text, structured)
    assert routing.intent == EnhancedIntent.SOURCE_LOOKUP
    assert routing.missing_slots is not None
    assert "period" in routing.missing_slots

