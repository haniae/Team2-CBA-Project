"""Application configuration helpers.

The :mod:`config` module centralises runtime options so the rest of the
codebase can remain free of hard-coded paths or secrets.  Settings are loaded
once at startup via :func:`load_settings` and then passed into other
components.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

try:  # pragma: no cover - trivial import guard
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - executed only when dependency missing
    def load_dotenv() -> None:
        """Fallback no-op when python-dotenv is not installed."""

        return None

load_dotenv()  # Load variables from a .env file if it exists.


LLMProvider = Literal["local", "openai"]


@dataclass(frozen=True)
class Settings:
    """A container object for runtime configuration.

    Attributes
    ----------
    database_path:
        Location of the SQLite database file used to persist conversations.
    llm_provider:
        Which language model integration to use. Options: ``"local"`` for a
        lightweight echo model (default) or ``"openai"`` for the
        :class:`~benchmarkos_chatbot.llm_client.OpenAILLMClient`.
    openai_model:
        The chat completion model name to request from the OpenAI API when the
        provider is set to ``"openai"``.
    openai_api_key:
        Optional API key to authenticate with OpenAI. If missing, the
        application will raise a clear error as soon as a remote call is
        attempted.
    """

    database_path: Path
    llm_provider: LLMProvider
    openai_model: str
    openai_api_key: Optional[str]

    @property
    def sqlite_uri(self) -> str:
        """Return a URI suitable for :mod:`sqlite3.connect`."""

        return f"file:{self.database_path}?cache=shared"


def load_settings() -> Settings:
    """Load configuration from environment variables.

    All environment variables are optional; sensible defaults are provided to
    make local development easy.
    """

    database_path = Path(
        os.getenv("DATABASE_PATH", Path.cwd() / "benchmarkos_chatbot.sqlite3")
    ).expanduser()

    llm_provider: LLMProvider = os.getenv("LLM_PROVIDER", "local").lower()  # type: ignore[assignment]
    if llm_provider not in ("local", "openai"):
        raise ValueError(
            "LLM_PROVIDER must be either 'local' or 'openai' (received "
            f"{llm_provider!r})."
        )

    return Settings(
        database_path=database_path,
        llm_provider=llm_provider,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


# The module-level import of os happens at the bottom to keep the public API
# obvious when scanning from the top of the file.
import os  # noqa: E402  (placed at end intentionally)

