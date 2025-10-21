"""Minimal script to interact with the BenchmarkOS chatbot programmatically."""

from __future__ import annotations

import time

from benchmarkos_chatbot import BenchmarkOSChatbot, load_settings


class ProgressPrinter:
    """Minimal CLI progress reporter that surfaces chatbot pipeline steps."""

    _STAGE_LABELS = {
        "start": "Startup",
        "message_logged": "Conversation",
        "cache_lookup": "Cache",
        "cache_hit": "Cache",
        "cache_miss": "Cache",
        "cache_skip": "Cache",
        "cache_store": "Cache",
        "help_lookup": "Help",
        "help_complete": "Help",
        "intent_normalised": "Intent",
        "intent_analysis_start": "Intent",
        "intent_analysis_complete": "Intent",
        "intent_routed_structured": "Intent",
        "intent_routed_natural": "Intent",
        "intent_metrics_detected": "Intent",
        "intent_metrics_missing": "Intent",
        "intent_attempt": "Intent",
        "intent_complete": "Intent",
        "summary_cache_hit": "Summary",
        "summary_build_start": "Summary",
        "summary_build_complete": "Summary",
        "summary_unavailable": "Summary",
        "summary_attempt": "Summary",
        "summary_complete": "Summary",
        "ticker_resolution_start": "Context",
        "ticker_resolution_complete": "Context",
        "metrics_dispatch": "Context",
        "metrics_fetch_start": "Context",
        "metrics_fetch_progress": "Context",
        "metrics_fetch_complete": "Context",
        "metrics_fetch_notice": "Context",
        "metrics_fetch_missing": "Context",
        "context_sources_scan": "Context",
        "context_cache_hit": "Context",
        "context_build_start": "Context",
        "context_build_ready": "Context",
        "context_sources_ready": "Context",
        "context_sources_empty": "Context",
        "llm_query_start": "LLM",
        "llm_query_complete": "LLM",
        "fallback": "Fallback",
        "finalize": "Finalising",
        "complete": "Done",
    }

    _COMPLETED_STAGES = {
        "cache_hit",
        "cache_miss",
        "cache_store",
        "help_complete",
        "intent_complete",
        "summary_complete",
        "summary_cache_hit",
        "summary_build_complete",
        "summary_unavailable",
        "context_build_ready",
        "context_sources_ready",
        "context_sources_empty",
        "llm_query_complete",
        "metrics_fetch_complete",
        "ticker_resolution_complete",
        "complete",
    }

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def __call__(self, stage: str, message: str) -> None:
        elapsed = time.perf_counter() - self._start
        label = self._STAGE_LABELS.get(stage, stage.replace("_", " ").title())
        symbol = self._symbol(stage)
        print(f"{symbol} [{elapsed:5.2f}s] {label}: {message}", flush=True)

    def _symbol(self, stage: str) -> str:
        if stage == "fallback":
            return "[!]"
        if stage in self._COMPLETED_STAGES or stage.endswith("_complete") or stage.endswith("_ready"):
            return "[OK]"
        return "[>>]"


def main() -> None:
    """Launch a simple REPL that uses the analytics-enabled chatbot."""

    settings = load_settings()
    bot = BenchmarkOSChatbot.create(settings)

    print("BenchmarkOS Chatbot quick runner (type 'exit' to quit)\n")
    while True:
        try:
            prompt = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if prompt.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        progress = ProgressPrinter()
        reply = bot.ask(prompt, progress_callback=progress)
        print(f"\nBot: {reply}\n")


if __name__ == "__main__":  # pragma: no cover - CLI convenience script
    main()
