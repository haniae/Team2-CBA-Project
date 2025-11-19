"""Generate ticker -> company name mappings for the S&P 1500 universe."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict

import requests

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = ROOT / "data" / "tickers" / "universe_sp1500.txt"
TICKER_NAMES_PATH = ROOT / "docs" / "guides" / "ticker_names.md"
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "Mozilla/5.0 (compatible; GPT-5.1-Codex/1.0; +https://openai.com/)"


def load_universe() -> list[str]:
    if not UNIVERSE_PATH.exists():
        raise FileNotFoundError(f"Universe file missing: {UNIVERSE_PATH}")
    tickers: list[str] = []
    for line in UNIVERSE_PATH.read_text(encoding="utf-8").splitlines():
        token = line.strip().upper()
        if not token or token.startswith("#"):
            continue
        tickers.append(token)
    return tickers


def load_existing_names() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not TICKER_NAMES_PATH.exists():
        return mapping
    pattern = re.compile(r"-\s+(?P<name>.+?)\s+\((?P<ticker>[A-Z0-9.\-]+)\)")
    for raw in TICKER_NAMES_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        mapping[match.group("ticker").upper()] = match.group("name").strip()
    return mapping


def fetch_sec_names() -> Dict[str, str]:
    response = requests.get(
        SEC_TICKER_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    entries = payload.values() if isinstance(payload, dict) else payload
    mapping: Dict[str, str] = {}
    for entry in entries:
        ticker = str(entry.get("ticker") or "").strip().upper()
        name = str(entry.get("title") or entry.get("name") or "").strip()
        if not ticker or not name:
            continue
        mapping[ticker] = name
        if "." in ticker:
            mapping.setdefault(ticker.replace(".", "-"), name)
        if "-" in ticker:
            mapping.setdefault(ticker.replace("-", "."), name)
    return mapping


def build_name_map() -> Dict[str, str]:
    universe = load_universe()
    existing = load_existing_names()
    sec_names = fetch_sec_names()

    name_map: Dict[str, str] = {}
    for ticker in universe:
        name = (
            existing.get(ticker)
            or sec_names.get(ticker)
            or sec_names.get(ticker.replace(".", "-"))
            or sec_names.get(ticker.replace("-", "."))
        )
        name_map[ticker] = name or ticker
    return name_map


def write_markdown(name_map: Dict[str, str]) -> None:
    lines = ["## Coverage Universe", ""]
    for ticker in sorted(name_map.keys()):
        lines.append(f"- {name_map[ticker]} ({ticker})")
    lines.append("")
    TICKER_NAMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    TICKER_NAMES_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(name_map)} entries to {TICKER_NAMES_PATH}")


def main() -> None:
    try:
        name_map = build_name_map()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    write_markdown(name_map)


if __name__ == "__main__":
    main()

