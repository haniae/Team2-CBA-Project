"""Language model client abstractions.

The project intentionally isolates interactions with large language models so
that you can switch providers or add advanced features (streaming, tool use,
retrieval augmentation) without rewriting the core chatbot logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol


class LLMClient(Protocol):
    """Minimal protocol every language-model client must satisfy."""

    def generate_reply(self, messages: Iterable[Mapping[str, str]]) -> str:
        """Return a response for the supplied chat messages."""


@dataclass
class LocalEchoLLM:
    """A deterministic implementation that simply echoes the last user input.

    Useful for development and unit testing without relying on external
    network calls.
    """

    def generate_reply(self, messages: Iterable[Mapping[str, str]]) -> str:
        last_user_message = ""
        for message in messages:
            if message["role"] == "user":
                last_user_message = message["content"]
        return (
            "(local-echo) I received: " + last_user_message
            if last_user_message
            else "(local-echo) No user prompt supplied."
        )


class OpenAILLMClient:
    """Wrapper around the OpenAI Chat Completions API."""

    def __init__(self, model: str, api_key: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - executed only if missing
            raise RuntimeError(
                "The 'openai' package is required to use OpenAILLMClient. "
                "Install it with `pip install openai`."
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate_reply(self, messages: Iterable[Mapping[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),
        )
        return response.choices[0].message.content or ""


def build_llm_client(provider: str, *, model: str, api_key: str | None) -> LLMClient:
    """Factory that instantiates the desired language model client."""

    if provider == "local":
        return LocalEchoLLM()

    if provider == "openai":
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY must be set when using the OpenAI provider."
            )
        return OpenAILLMClient(model=model, api_key=api_key)

    raise ValueError(f"Unsupported provider: {provider}")
