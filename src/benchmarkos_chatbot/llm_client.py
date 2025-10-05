"""Language model client abstractions.

The project intentionally isolates interactions with large language models so
that you can switch providers or add advanced features (streaming, tool use,
retrieval augmentation) without rewriting the core chatbot logic.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

# Language-model integrations live here. Implement the LLMClient protocol and register new
# providers in `build_llm_client` without touching chatbot logic.

try:  # pragma: no cover - optional dependency
    import keyring  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    keyring = None


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
        """Generate a reply using the configured language model backend."""
        last_user_message = ""
        for message in messages:
            if message["role"] == "user":
                last_user_message = message["content"]
        return (
            "(local-echo) I received: " + last_user_message
            if last_user_message
            else "(local-echo) No user prompt supplied."
        )


def _resolve_openai_api_key() -> str:
    """Return the OpenAI API key from the safest available source.

    Resolution order:
    1. `OPENAI_API_KEY` environment variable.
    2. Secret stored in the user's keyring under the "benchmarkos-chatbot" service.
    3. Plain-text fallback file at ~/.config/benchmarkos-chatbot/openai_api_key.

    Raises
    ------
    RuntimeError
        If no key can be located. This keeps secrets out of source control while
        still providing clear guidance to the caller.
    """

    env_value = os.getenv("OPENAI_API_KEY")
    if env_value:
        return env_value

    if keyring is not None:
        try:
            stored = keyring.get_password("benchmarkos-chatbot", "openai-api-key")
        except Exception:  # pragma: no cover - defensive fallback
            stored = None
        if stored:
            return stored

    fallback_path = Path.home() / ".config" / "benchmarkos-chatbot" / "openai_api_key"
    try:
        fallback_text = fallback_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        fallback_text = ""
    except OSError:  # pragma: no cover - e.g. permissions
        fallback_text = ""
    if fallback_text:
        return fallback_text

    raise RuntimeError(
        "OpenAI API key not found. Set OPENAI_API_KEY, store it in your keyring "
        "(service 'benchmarkos-chatbot'), or place it in "
        f"{fallback_path}"
    )


class OpenAILLMClient:
    """Wrapper around the OpenAI Chat Completions API."""

    def __init__(self, model: str) -> None:
        """Initialise the OpenAI client wrapper with model and auth settings."""
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - executed only if missing
            raise RuntimeError(
                "The 'openai' package is required to use OpenAILLMClient. "
                "Install it with `pip install openai`."
            ) from exc

        resolved_key = _resolve_openai_api_key()
        self._client = OpenAI(api_key=resolved_key)
        self._model = model

    def generate_reply(self, messages: Iterable[Mapping[str, str]]) -> str:
        """Generate a reply using the configured language model backend."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=list(messages),
        )
        return response.choices[0].message.content or ""


def build_llm_client(
    provider: str,
    *,
    model: str,
) -> LLMClient:
    """Factory that instantiates the desired language model client."""

    if provider == "local":
        return LocalEchoLLM()

    if provider == "openai":
        return OpenAILLMClient(model=model)

    raise ValueError(f"Unsupported provider: {provider}")
