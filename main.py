"""Command-line entry point for the BenchmarkOS chatbot."""

from __future__ import annotations

from pathlib import Path

from benchmarkos_chatbot import BenchmarkOSChatbot, load_settings


def main() -> None:
    settings = load_settings()
    chatbot = BenchmarkOSChatbot.create(settings)

    print("BenchmarkOS Chatbot (type 'help' for guided commands, 'exit' to quit)\n")
    if chatbot.ingestion_report:
        companies = ", ".join(chatbot.ingestion_report.companies)
        print(
            "Loaded financial dataset from"
            f" {chatbot.ingestion_report.source_path.name} covering: {companies}."
        )
        print(
            f"Normalised {chatbot.ingestion_report.records_loaded} data points with"
            " consistent adjustments.\n"
        )

    while True:
        try:
            user_input = input("You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        response = chatbot.ask(user_input)
        print(f"Bot: {response}\n")

    db_path = Path(settings.database_path)
    if db_path.exists():
        print(f"Conversation saved to {db_path}")


if __name__ == "__main__":  # pragma: no cover - CLI not unit tested
    main()