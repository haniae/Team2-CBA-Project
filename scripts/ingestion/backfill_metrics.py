#!/usr/bin/env python
"""Refresh derived KPI snapshots and optional enrichments."""

from __future__ import annotations

from finanlyzeos_chatbot import load_settings
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine

try:
    from finanlyzeos_chatbot.external_data import ingest_imf_kpis
except Exception:  # pragma: no cover - optional dependency
    ingest_imf_kpis = None


def main() -> None:
    settings = load_settings()
    engine = AnalyticsEngine(settings)

    print("Refreshing KPI snapshots …")
    engine.refresh_metrics(force=True)

    try:
        print("Refreshing scenario caches …")
        engine.refresh_scenarios(force=True)
    except AttributeError:
        # Older versions of AnalyticsEngine may not expose refresh_scenarios.
        pass

    if ingest_imf_kpis is not None:
        try:
            print("Updating IMF baseline KPIs …")
            ingest_imf_kpis(settings)
        except Exception as exc:  # noqa: BLE001
            print(f"IMF enrichment skipped: {exc}")

    print("Metric backfill complete.")


if __name__ == "__main__":
    main()
