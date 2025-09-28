"""Core chatbot orchestration logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Mapping

from . import database
from .config import Settings
from .llm_client import LLMClient, build_llm_client

SYSTEM_PROMPT = """You are BenchmarkOS, an institutional-grade finance analyst.\n\
You deliver precise, compliant insights grounded in the latest SEC filings,\
market data, and risk controls. Provide actionable intelligence in clear\
professional language. If you are unsure, request clarification or state\
explicitly that more data is required."""


@dataclass
class Conversation:
    """Tracks a single chat session."""

    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Mapping[str, str]] = field(default_factory=list)

    def as_llm_messages(self) -> List[Mapping[str, str]]:
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self.messages]


@dataclass
class BenchmarkOSChatbot:
    """High-level interface wrapping the entire chatbot pipeline."""

    settings: Settings
    llm_client: LLMClient
    conversation: Conversation = field(default_factory=Conversation)

    @classmethod
    def create(cls, settings: Settings) -> "BenchmarkOSChatbot":
        llm_client = build_llm_client(
            settings.llm_provider,
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

        database.initialise(settings.database_path)
        return cls(settings=settings, llm_client=llm_client)

    def ask(self, user_input: str) -> str:
        """Generate a reply and persist both sides of the exchange."""

        timestamp = datetime.utcnow()
        database.log_message(
            self.settings.database_path,
            self.conversation.conversation_id,
            role="user",
            content=user_input,
            created_at=timestamp,
        )
        self.conversation.messages.append({"role": "user", "content": user_input})

        llm_messages = self.conversation.as_llm_messages()
        reply = self.llm_client.generate_reply(llm_messages)

        database.log_message(
            self.settings.database_path,
            self.conversation.conversation_id,
            role="assistant",
            content=reply,
            created_at=datetime.utcnow(),
        )
        self.conversation.messages.append({"role": "assistant", "content": reply})
        return reply

    def history(self) -> Iterable[database.Message]:
        """Return the stored conversation from the database."""

        return database.fetch_conversation(
            self.settings.database_path, self.conversation.conversation_id
        )

    def reset(self) -> None:
        """Start a fresh conversation while keeping the same configuration."""

        self.conversation = Conversation()
