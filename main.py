"""Convenience shim so `python main.py` continues to launch the CLI utility.

Historically the rich CLI lived at the repository root. The implementation now
resides under ``scripts.utility.main`` but tests and documentation still import
``main`` directly. This wrapper keeps that import path stable while delegating
all real work to the new location.
"""

from __future__ import annotations

from scripts.utility import main as cli_main

_try_table_command = cli_main._try_table_command

__all__ = ["_try_table_command", "main"]


def main() -> None:
    """Proxy that executes the richer CLI defined in scripts.utility.main."""
    cli_main.main()


if __name__ == "__main__":
    main()
