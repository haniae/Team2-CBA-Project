"""Minimal script to interact with the BenchmarkOS chatbot programmatically."""

from __future__ import annotations

from benchmarkos_chatbot import BenchmarkOSChatbot, load_settings


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

        reply = bot.ask(prompt)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":  # pragma: no cover - CLI convenience script
    main()
