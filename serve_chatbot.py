"""Convenience launcher for the BenchmarkOS web chatbot."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


def _ensure_uvicorn() -> None:
    """Ensure `uvicorn` can be imported, raising a helpful error otherwise.
    """
    try:
        import uvicorn  # noqa: F401
    except ImportError as exc:  # pragma: no cover - runtime safety guard
        message = (
            "uvicorn is required to run the web chatbot. Install it with "
            "'pip install uvicorn[standard]' and try again."
        )
        raise SystemExit(message) from exc


def main(argv: list[str] | None = None) -> NoReturn:
    """Start the FastAPI application using uvicorn with the provided settings.
    """
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
    
    try:
        # Test import before starting server
        try:
            from benchmarkos_chatbot.web import app
            print(f"✓ Successfully imported FastAPI app")
        except Exception as e:
            print(f"✗ Failed to import FastAPI app: {e}")
            import traceback
            traceback.print_exc()
            raise SystemExit(1)
        
        print(f"🚀 Starting BenchmarkOS Chatbot on http://{args.host}:{args.port}")
        print(f"📝 API docs available at http://{args.host}:{args.port}/docs")
        
        uvicorn.run(
            "benchmarkos_chatbot.web:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        raise SystemExit(0)
    except Exception as e:
        print(f"✗ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main(sys.argv[1:])
