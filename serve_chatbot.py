"""Convenience launcher for the BenchmarkOS web chatbot."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def _ensure_uvicorn() -> None:
    try:
        import uvicorn  # noqa: F401
    except ImportError as exc:  # pragma: no cover - runtime safety guard
        message = (
            "uvicorn is required to run the web chatbot. Install it with "
            "'pip install uvicorn[standard]' and try again."
        )
        raise SystemExit(message) from exc


def main(argv: list[str] | None = None) -> NoReturn:
    parser = argparse.ArgumentParser(
        description="Start the FastAPI-powered BenchmarkOS chatbot UI",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable autoreload (development use only)",
    )

    args = parser.parse_args(argv)
    _ensure_uvicorn()

    import uvicorn

    uvicorn.run(
        "benchmarkos_chatbot.web:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

    raise SystemExit(0)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main(sys.argv[1:])
