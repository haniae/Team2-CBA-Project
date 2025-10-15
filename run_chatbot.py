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
        "intent_attempt": "Intent",
        "intent_complete": "Intent",
        "summary_attempt": "Summary",
        "summary_complete": "Summary",
        "context_build_start": "Context",
        "context_build_ready": "Context",
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
        "context_build_ready",
        "llm_query_complete",
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
