"""Application configuration helpers.

The :mod:`config` module centralises runtime options so the rest of the
codebase can remain free of hard-coded paths or secrets. Settings are loaded
once at startup via :func:`load_settings` and then passed into other
components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
DatabaseType = Literal["sqlite", "postgresql"]


@dataclass(frozen=True)
# Immutable snapshot of validated configuration so downstream modules avoid reading environment
# variables directly.
class Settings:
    """A container object for runtime configuration.

    Attributes
    ----------
    database_type:
        Type of database to use: "sqlite" or "postgresql"
    database_path:
        Location of the SQLite database file (only used when database_type is "sqlite")
    postgres_host:
        PostgreSQL server hostname
    postgres_port:
        PostgreSQL server port
    postgres_database:
        PostgreSQL database name
    postgres_user:
        PostgreSQL username
    postgres_password:
        PostgreSQL password
    postgres_schema:
        PostgreSQL schema name (default: "sec")
    llm_provider:
        Which language model integration to use. Options: ``"local"`` for a
        lightweight echo model (default) or ``"openai"`` for the
        :class:`~finanlyzeos_chatbot.llm_client.OpenAILLMClient`.
    openai_model:
        The chat completion model name to request from the OpenAI API when the
        provider is set to ``"openai"``.
    sec_api_user_agent:
        SEC requires a descriptive User-Agent string for EDGAR API access.
    edgar_base_url:
        Base URL for EDGAR data endpoints.
    yahoo_quote_url:
        Base endpoint for Yahoo Finance real-time quotes.
    yahoo_quote_batch_size:
        Maximum number of tickers to request per Yahoo Finance batch call.
    http_request_timeout:
        Number of seconds to wait before timing out HTTP requests.
    max_ingestion_workers:
        Size of the worker pool used for concurrent ingestion tasks.
    cache_dir:
        Directory used to persist intermediate ingestion artefacts.
    enable_bloomberg:
        Whether Bloomberg real-time quote integration should be attempted.
    bloomberg_host / bloomberg_port / bloomberg_timeout:
        Connection details for a Bloomberg Session (if enabled).
    """

    database_type: DatabaseType = "sqlite"
    database_path: Path = field(default_factory=lambda: Path("finanlyzeos_chatbot.sqlite3"))
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_database: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_schema: str = "sec"
    llm_provider: LLMProvider = "local"
    openai_model: str = "gpt-4o-mini"
    sec_api_user_agent: str = "FinanlyzeOSBot/1.0 (support@finanlyzeos.com)"
    edgar_base_url: str = "https://data.sec.gov"
    yahoo_quote_url: str = "https://query1.finance.yahoo.com/v7/finance/quote"
    yahoo_quote_batch_size: int = 50
    http_request_timeout: float = 30.0
    max_ingestion_workers: int = 8
    cache_dir: Path = field(default_factory=lambda: Path.cwd() / "cache")
    enable_bloomberg: bool = False
    bloomberg_host: Optional[str] = None
    bloomberg_port: Optional[int] = None
    bloomberg_timeout: float = 30.0
    disable_quote_refresh: bool = False
    enable_external_backfill: bool = False
    use_companyfacts_bulk: bool = False
    companyfacts_bulk_url: str = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
    companyfacts_bulk_refresh_hours: int = 24
    use_stooq_fallback: bool = False
    stooq_quote_url: str = "https://stooq.com/q/l/"
    stooq_symbol_suffix: str = ".us"
    stooq_timeout: float = 20.0
    ingestion_year_buffer: int = 2
    enable_enhanced_routing: bool = False
    prefer_conversational_mode: bool = True
    verification_enabled: bool = True
    verification_strict_mode: bool = False  # Reject responses with unverified facts
    max_allowed_deviation: float = 0.05  # 5% tolerance
    min_confidence_threshold: float = 0.85  # 85% minimum confidence
    cross_validation_enabled: bool = True
    auto_correct_enabled: bool = True
    include_macro_context: bool = True
    # Private Company API Settings
    enable_private_companies: bool = False
    private_api_url: Optional[str] = None
    private_api_key: Optional[str] = None
    private_api_secret: Optional[str] = None
    private_api_timeout: float = 30.0

    @property
    def sqlite_uri(self) -> str:
        """Return a URI suitable for :mod:`sqlite3.connect`."""
        return f"file:{self.database_path}?cache=shared"

    @property
    def postgres_dsn(self) -> str:
        """Return a PostgreSQL connection string."""
        if self.database_type != "postgresql":
            raise ValueError("postgres_dsn is only available when database_type is 'postgresql'")
        
        if not all([self.postgres_host, self.postgres_database, self.postgres_user]):
            raise ValueError(
                "PostgreSQL requires POSTGRES_HOST, POSTGRES_DATABASE, and POSTGRES_USER "
                "to be set in environment variables"
            )
        
        # Build connection string
        password_part = f":{self.postgres_password}" if self.postgres_password else ""
        port_part = f":{self.postgres_port}" if self.postgres_port else ""
        
        return (
            f"postgresql://{self.postgres_user}{password_part}@"
            f"{self.postgres_host}{port_part}/{self.postgres_database}"
        )

    @property
    def database_uri(self) -> str:
        """Return the appropriate database URI based on database_type."""
        if self.database_type == "sqlite":
            return self.sqlite_uri
        elif self.database_type == "postgresql":
            return self.postgres_dsn
        else:
            raise ValueError(f"Unknown database type: {self.database_type}")


def _env_flag(name: str, *, default: bool = False) -> bool:
    """Interpret environment variables that are meant to behave as booleans."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float_env(name: str, *, default: float) -> float:
    """Parse a float from an environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float (received {value!r}).") from exc


def load_settings() -> Settings:
    """Load configuration from environment variables.

    All environment variables are optional; sensible defaults are provided to
    make local development easy.
    """

    # Database configuration
    database_type_env = os.getenv("DATABASE_TYPE", "sqlite").lower()
    if database_type_env not in ("sqlite", "postgresql"):
        raise ValueError(
            "DATABASE_TYPE must be either 'sqlite' or 'postgresql' (received "
            f"{database_type_env!r})."
        )
    database_type: DatabaseType = database_type_env  # type: ignore[assignment]

    default_sqlite_path = Path.cwd() / "data" / "sqlite" / "finanlyzeos_chatbot.sqlite3"
    database_path = Path(os.getenv("DATABASE_PATH", default_sqlite_path)).expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    # PostgreSQL configuration
    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_port_env = os.getenv("POSTGRES_PORT", "5432")
    postgres_port = None
    if postgres_port_env:
        try:
            postgres_port = int(postgres_port_env)
        except ValueError as exc:
            raise ValueError("POSTGRES_PORT must be an integer.") from exc
    
    postgres_database = os.getenv("POSTGRES_DATABASE")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    postgres_schema = os.getenv("POSTGRES_SCHEMA", "sec")

    # Validate PostgreSQL settings if using PostgreSQL
    if database_type == "postgresql":
        if not postgres_host:
            raise ValueError("POSTGRES_HOST must be set when DATABASE_TYPE is 'postgresql'")
        if not postgres_database:
            raise ValueError("POSTGRES_DATABASE must be set when DATABASE_TYPE is 'postgresql'")
        if not postgres_user:
            raise ValueError("POSTGRES_USER must be set when DATABASE_TYPE is 'postgresql'")

    # LLM configuration
    llm_provider: LLMProvider = os.getenv("LLM_PROVIDER", "local").lower()  # type: ignore[assignment]
    if llm_provider not in ("local", "openai"):
        raise ValueError(
            "LLM_PROVIDER must be either 'local' or 'openai' (received "
            f"{llm_provider!r})."
        )

    sec_user_agent = os.getenv("SEC_API_USER_AGENT", 
        "FinanlyzeOSBot/1.0 (support@finanlyzeos.com)"
    ).strip()
    if not sec_user_agent:
        raise ValueError("SEC_API_USER_AGENT must not be empty.")

    edgar_base_url = os.getenv("EDGAR_BASE_URL", "https://data.sec.gov").rstrip("/")
    yahoo_quote_url = os.getenv("YAHOO_QUOTE_URL", 
        "https://query1.finance.yahoo.com/v7/finance/quote"
    ).rstrip("/")

    yahoo_batch_env = os.getenv("YAHOO_QUOTE_BATCH_SIZE", "50")
    try:
        yahoo_quote_batch_size = int(yahoo_batch_env)
    except ValueError as exc:
        raise ValueError("YAHOO_QUOTE_BATCH_SIZE must be an integer.") from exc
    if yahoo_quote_batch_size <= 0:
        raise ValueError("YAHOO_QUOTE_BATCH_SIZE must be positive.")

    timeout_env = os.getenv("HTTP_REQUEST_TIMEOUT", "30")
    try:
        http_request_timeout = float(timeout_env)
    except ValueError as exc:
        raise ValueError("HTTP_REQUEST_TIMEOUT must be numeric.") from exc
    if http_request_timeout <= 0:
        raise ValueError("HTTP_REQUEST_TIMEOUT must be positive.")

    worker_env = os.getenv("INGESTION_MAX_WORKERS", "8")
    try:
        max_ingestion_workers = max(1, int(worker_env))
    except ValueError as exc:
        raise ValueError("INGESTION_MAX_WORKERS must be an integer.") from exc

    cache_dir = Path(os.getenv("DATA_CACHE_DIR", Path.cwd() / "cache")).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    enable_bloomberg = _env_flag("ENABLE_BLOOMBERG", default=False)
    bloomberg_host = os.getenv("BLOOMBERG_HOST")
    bloomberg_port_env = os.getenv("BLOOMBERG_PORT")
    bloomberg_port = None
    if bloomberg_port_env:
        try:
            bloomberg_port = int(bloomberg_port_env)
        except ValueError as exc:
            raise ValueError("BLOOMBERG_PORT must be an integer.") from exc
    bloomberg_timeout_env = os.getenv("BLOOMBERG_TIMEOUT", "30")
    try:
        bloomberg_timeout = float(bloomberg_timeout_env)
    except ValueError as exc:
        raise ValueError("BLOOMBERG_TIMEOUT must be numeric.") from exc
    if bloomberg_timeout <= 0:
        raise ValueError("BLOOMBERG_TIMEOUT must be positive.")

    use_companyfacts_bulk = _env_flag("USE_COMPANYFACTS_BULK", default=False)
    companyfacts_bulk_url = os.getenv(
        "COMPANYFACTS_BULK_URL",
        "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
    ).strip()
    if not companyfacts_bulk_url:
        raise ValueError("COMPANYFACTS_BULK_URL must not be empty.")
    companyfacts_refresh_env = os.getenv("COMPANYFACTS_BULK_REFRESH_HOURS", "24")
    try:
        companyfacts_bulk_refresh_hours = max(1, int(companyfacts_refresh_env))
    except ValueError as exc:
        raise ValueError("COMPANYFACTS_BULK_REFRESH_HOURS must be an integer.") from exc

    use_stooq_fallback = _env_flag("USE_STOOQ_FALLBACK", default=False)
    stooq_quote_url = os.getenv("STOOQ_QUOTE_URL", "https://stooq.com/q/l/").strip()
    if not stooq_quote_url:
        raise ValueError("STOOQ_QUOTE_URL must not be empty.")
    stooq_symbol_suffix = os.getenv("STOOQ_SYMBOL_SUFFIX", ".us").strip()
    if not stooq_symbol_suffix:
        stooq_symbol_suffix = ".us"
    stooq_timeout_env = os.getenv("STOOQ_TIMEOUT", "20")
    try:
        stooq_timeout = float(stooq_timeout_env)
    except ValueError as exc:
        raise ValueError("STOOQ_TIMEOUT must be numeric.") from exc
    if stooq_timeout <= 0:
        raise ValueError("STOOQ_TIMEOUT must be positive.")
    ingestion_year_buffer_env = os.getenv("INGESTION_YEAR_BUFFER", "2")
    try:
        ingestion_year_buffer = max(1, int(ingestion_year_buffer_env))
    except ValueError as exc:
        raise ValueError("INGESTION_YEAR_BUFFER must be an integer.") from exc

    return Settings(
        database_type=database_type,
        database_path=database_path,
        postgres_host=postgres_host,
        postgres_port=postgres_port,
        postgres_database=postgres_database,
        postgres_user=postgres_user,
        postgres_password=postgres_password,
        postgres_schema=postgres_schema,
        llm_provider=llm_provider,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        sec_api_user_agent=sec_user_agent,
        edgar_base_url=edgar_base_url,
        yahoo_quote_url=yahoo_quote_url,
        yahoo_quote_batch_size=yahoo_quote_batch_size,
        http_request_timeout=http_request_timeout,
        max_ingestion_workers=max_ingestion_workers,
        cache_dir=cache_dir,
        enable_bloomberg=enable_bloomberg,
        bloomberg_host=bloomberg_host,
        bloomberg_port=bloomberg_port,
        bloomberg_timeout=bloomberg_timeout,
        disable_quote_refresh=_env_flag("DISABLE_QUOTE_REFRESH", default=False),
        enable_external_backfill=_env_flag("ENABLE_EXTERNAL_BACKFILL", default=False),
        use_companyfacts_bulk=use_companyfacts_bulk,
        companyfacts_bulk_url=companyfacts_bulk_url,
        companyfacts_bulk_refresh_hours=companyfacts_bulk_refresh_hours,
        use_stooq_fallback=use_stooq_fallback,
        stooq_quote_url=stooq_quote_url,
        stooq_symbol_suffix=stooq_symbol_suffix,
        stooq_timeout=stooq_timeout,
        ingestion_year_buffer=ingestion_year_buffer,
        enable_enhanced_routing=_env_flag("ENABLE_ENHANCED_ROUTING", default=False),
        prefer_conversational_mode=_env_flag("PREFER_CONVERSATIONAL_MODE", default=True),
        verification_enabled=_env_flag("VERIFICATION_ENABLED", default=True),
        verification_strict_mode=_env_flag("VERIFICATION_STRICT_MODE", default=False),
        max_allowed_deviation=_parse_float_env("MAX_ALLOWED_DEVIATION", default=0.05),
        min_confidence_threshold=_parse_float_env("MIN_CONFIDENCE_THRESHOLD", default=0.85),
        cross_validation_enabled=_env_flag("CROSS_VALIDATION_ENABLED", default=True),
        auto_correct_enabled=_env_flag("AUTO_CORRECT_ENABLED", default=True),
        include_macro_context=_env_flag("ENABLE_MACRO_CONTEXT", default=True),
        enable_private_companies=_env_flag("ENABLE_PRIVATE_COMPANIES", default=False),
        private_api_url=os.getenv("PRIVATE_API_URL"),
        private_api_key=os.getenv("PRIVATE_API_KEY"),
        private_api_secret=os.getenv("PRIVATE_API_SECRET"),
        private_api_timeout=_parse_float_env("PRIVATE_API_TIMEOUT", default=30.0),
    )


# The module-level import of os happens at the bottom to keep the public API
# obvious when scanning from the top of the file.
import os  # noqa: E402  (placed at end intentionally)


