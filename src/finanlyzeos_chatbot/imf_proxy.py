"""IMF sector proxy loader that supplies fallback KPI values when filings are missing."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

LOGGER = logging.getLogger(__name__)

DATA_PATHS = [
    Path(__file__).resolve().parents[2] / "data" / "external" / "imf_sector_kpis.json",
    Path(__file__).resolve().parent / "static" / "data" / "imf_sector_kpis.json",
]

UNIVERSE_PATHS = [
    Path(__file__).resolve().parents[2] / "webui" / "data" / "company_universe.json",
    Path(__file__).resolve().parent / "static" / "data" / "company_universe.json",
]


@lru_cache(maxsize=1)
def _load_proxy_table() -> Dict[str, Dict[str, float]]:
    for path in DATA_PATHS:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # pragma: no cover - protect against malformed files
                LOGGER.warning("Unable to parse IMF proxy table at %s", path)
    return {}


@lru_cache(maxsize=1)
def _load_company_universe() -> Dict[str, Dict[str, str]]:
    for path in UNIVERSE_PATHS:
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # pragma: no cover
                LOGGER.warning("Unable to parse company universe at %s", path)
                continue
            mapping: Dict[str, Dict[str, str]] = {}
            if isinstance(payload, list):
                for entry in payload:
                    ticker = str(entry.get("ticker") or "").upper()
                    if not ticker:
                        continue
                    mapping[ticker] = {
                        "sector": entry.get("sector") or "",
                        "sub_industry": entry.get("sub_industry") or "",
                        "country": entry.get("country") or entry.get("hq_country") or "",
                    }
            return mapping
    return {}


def sector_for_ticker(ticker: str) -> Optional[str]:
    """Return the GICS sector for the supplied ticker."""
    universe = _load_company_universe()
    record = universe.get(ticker.upper())
    if record:
        sector = record.get("sector")
        if sector:
            return sector
    return None


def metric_for(ticker: str, metric: str) -> Optional[float]:
    """Look up a proxy value for ``metric`` using the ticker's sector."""
    proxies = _load_proxy_table()
    if not proxies:
        return None
    sector = sector_for_ticker(ticker)
    candidates = []
    if sector and sector in proxies:
        candidates.append(proxies[sector])
    if "GLOBAL" in proxies:
        candidates.append(proxies["GLOBAL"])
    for table in candidates:
        value = table.get(metric)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                LOGGER.debug("IMF proxy value for %s/%s is not numeric: %s", ticker, metric, value)
    return None


def available_metrics() -> Dict[str, Dict[str, float]]:
    """Expose the raw proxy table for diagnostics."""
    return _load_proxy_table().copy()
