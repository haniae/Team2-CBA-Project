"""Core chatbot orchestration logic."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Mapping, Optional

from . import database
from .config import Settings
from .data_pipeline import BenchmarkOSDataPipeline
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
    data_pipeline: BenchmarkOSDataPipeline = field(
        default_factory=BenchmarkOSDataPipeline.create_default
    )

    @classmethod
    def create(cls, settings: Settings) -> "BenchmarkOSChatbot":
        llm_client = build_llm_client(
            settings.llm_provider,
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

        database.initialise(settings.database_path)
        return cls(
            settings=settings,
            llm_client=llm_client,
            data_pipeline=BenchmarkOSDataPipeline.create_default(),
        )

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

        internal_response = self._maybe_handle_internal_command(user_input)
        if internal_response is not None:
            database.log_message(
                self.settings.database_path,
                self.conversation.conversation_id,
                role="assistant",
                content=internal_response,
                created_at=datetime.utcnow(),
            )
            self.conversation.messages.append(
                {"role": "assistant", "content": internal_response}
            )
            return internal_response

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

    def _maybe_handle_internal_command(self, user_input: str) -> Optional[str]:
        """Handle structured commands such as deliverable tracking."""

        normalized = user_input.strip().lower()
        if not normalized:
            return None

        deliverable_response = self._handle_deliverable_command(normalized)
        if deliverable_response:
            return deliverable_response

        financial_response = self._handle_financial_command(user_input)
        if financial_response:
            return financial_response

        return None

    def _handle_deliverable_command(self, normalized_input: str) -> Optional[str]:
        if "deliverable" not in normalized_input:
            return None

        if any(
            keyword in normalized_input
            for keyword in ["list", "show", "display", "what", "status", "progress"]
        ):
            return self._render_deliverables()

        status = self._extract_status_keyword(normalized_input)
        if status is None:
            return None

        position = self._extract_deliverable_position(normalized_input)
        if position is None:
            return None

        updated = database.update_deliverable_status(
            self.settings.database_path, position, status
        )
        return (
            f"Updated deliverable {position:02d} to '{updated.status}'.\n"
            f"{updated.title}"
        )

    def _handle_financial_command(self, user_input: str) -> Optional[str]:
        normalized = user_input.lower()
        keywords = [
            "sec",
            "filing",
            "analysis",
            "report",
            "kpi",
            "benchmark",
            "market",
            "price",
            "data",
        ]
        if not any(keyword in normalized for keyword in keywords):
            return None

        tickers = set(self.data_pipeline.registry.companies)
        candidates = re.findall(r"\b[A-Z]{1,5}\b", user_input.upper())
        ticker = next((token for token in candidates if token in tickers), None)
        if ticker is None:
            return None

        try:
            return self.data_pipeline.build_financial_report(ticker)
        except KeyError:
            return (
                f"Ticker {ticker} is not yet registered in BenchmarkOS. "
                "Update data_pipeline.CompanyRegistry to include its CIK."
            )
        except Exception as exc:  # pragma: no cover - defensive logging path
            return f"Unable to build financial report for {ticker}: {exc}"  # noqa: TRY003

    @staticmethod
    def _extract_deliverable_position(normalized_input: str) -> Optional[int]:
        match = re.search(r"deliverable\s*(\d+)", normalized_input)
        if not match:
            match = re.search(r"\b(\d{1,2})\b", normalized_input)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _extract_status_keyword(normalized_input: str) -> Optional[str]:
        keyword_map = {
            "complete": "Complete",
            "completed": "Complete",
            "done": "Complete",
            "in progress": "In Progress",
            "progress": "In Progress",
            "blocked": "Blocked",
            "not started": "Not Started",
            "reset": "Not Started",
        }

        for phrase, status in sorted(keyword_map.items(), key=lambda item: -len(item[0])):
            if phrase in normalized_input:
                return status
        return None

    def _render_deliverables(self) -> str:
        deliverables = database.list_deliverables(self.settings.database_path)
        if not deliverables:
            return "No deliverables are currently tracked."

        status_emoji = {
            "Complete": "✅",
            "In Progress": "🔄",
            "Blocked": "⛔",
            "Not Started": "⬜",
        }

        lines = ["Core Deliverables (Sep 21-28):"]
        for item in deliverables:
            emoji = status_emoji.get(item.status, "•")
            owner = f" — Owner: {item.owner}" if item.owner else ""
            due = f" — Due: {item.due_window}" if item.due_window else ""
            lines.append(
                f"{item.position:02d}. {emoji} {item.title}{owner}{due} [{item.status}]"
            )

        lines.append(
            "\nUpdate a deliverable by typing 'mark deliverable 3 complete' "
            "or 'set deliverable 5 in progress'."
        )
        return "\n".join(lines)
