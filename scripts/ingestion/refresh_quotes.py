#!/usr/bin/env python
"""Refresh market quotes and recompute valuation metrics."""

from __future__ import annotations

from finanlyzeos_chatbot import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from finanlyzeos_chatbot.data_sources import QuoteLoader


def main() -> None:
    settings = load_settings()
    engine = AnalyticsEngine(settings)
    loader = QuoteLoader(settings)

    tickers = engine.database.list_tracked_tickers()
    if not tickers:
        print("No tickers found in the datastore.")
        return

    print(f"Refreshing quotes for {len(tickers)} tickers …")
    loader.load_quotes(tickers)

    print("Recomputing valuation metrics …")
    engine.refresh_metrics(force=True)
    print("Quote refresh complete.")


if __name__ == "__main__":
    main()
