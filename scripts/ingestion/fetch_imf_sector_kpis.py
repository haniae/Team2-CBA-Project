#!/usr/bin/env python3
"""
Fetch IMF macro data and translate it into sector-level KPI proxies.

This script writes a JSON file at ``data/external/imf_sector_kpis.json`` that the
backfill pipeline can use as a fallback whenever company filings are missing.

Out of the box it pulls United States GDP growth statistics from the IMF World
Economic Outlook (WEO) dataset and applies them to a single GLOBAL sector entry.
You can customise the ``IMF_METRIC_CONFIG`` list below to target different
countries, indicators, or to publish sector-specific overrides.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

BASE_URL = "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "external" / "imf_sector_kpis.json"


@dataclass
class SeriesSpec:
    metric: str
    dataset: str
    indicator: str
    frequency: str = "A"
    country: str = "USA"
    window: int = 5
    scale: float = 0.01
    sectors: Iterable[str] = ("GLOBAL",)
    aggregator: str = "mean"  # "mean" or "last"


# Default configuration — feel free to edit.
IMF_METRIC_CONFIG: List[SeriesSpec] = [
    SeriesSpec(
        metric="revenue_cagr",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.01,
    ),
    SeriesSpec(
        metric="eps_cagr",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.01,
    ),
    SeriesSpec(
        metric="ebitda_growth",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.01,
    ),
    SeriesSpec(
        metric="ebitda_margin",
        dataset="IFS",
        indicator="NCPI_XGDP",
        scale=0.01,
        window=1,
    ),
    SeriesSpec(
        metric="net_margin",
        dataset="IFS",
        indicator="NCO_NGDP",
        scale=0.01,
        window=1,
    ),
    SeriesSpec(
        metric="free_cash_flow_margin",
        dataset="IFS",
        indicator="NCO_NGDP",
        scale=0.008,
        window=1,
    ),
    SeriesSpec(
        metric="cash_conversion",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.05,
        window=1,
        aggregator="last",
    ),
    SeriesSpec(
        metric="debt_to_equity",
        dataset="IFS",
        indicator="GGXWDG_NGDP",
        scale=0.01,
        window=1,
        aggregator="last",
    ),
    SeriesSpec(
        metric="peg_ratio",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.1,
        window=1,
        aggregator="last",
    ),
    SeriesSpec(
        metric="dividend_yield",
        dataset="WEO:2023-10",
        indicator="GGX_WB_GDP",
        scale=0.0005,
        window=1,
        aggregator="last",
    ),
    SeriesSpec(
        metric="tsr",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.01,
    ),
    SeriesSpec(
        metric="share_buyback_intensity",
        dataset="WEO:2023-10",
        indicator="NGDP_RPCH",
        scale=0.0005,
        window=1,
        aggregator="last",
    ),
]


def _build_key(spec: SeriesSpec) -> str:
    return f"{spec.frequency}.{spec.country}.{spec.indicator}"


def _fetch_series(spec: SeriesSpec, timeout: float = 60.0) -> Dict[str, float]:
    key = _build_key(spec)
    url = f"{BASE_URL}/{spec.dataset}/{key}"
    headers = {"Accept": "application/json"}
    response = requests.get(url, timeout=timeout, headers=headers)
    response.raise_for_status()
    payload = response.json()
    try:
        series = payload["CompactData"]["DataSet"]["Series"]
    except KeyError as exc:
        raise RuntimeError(f"Unexpected IMF payload structure for {url}") from exc
    observations: Dict[str, float] = {}
    for obs in series.get("Obs", []):
        period = obs.get("@TIME_PERIOD")
        value = obs.get("@OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            observations[period] = float(value) * spec.scale
        except (TypeError, ValueError):
            continue
    return observations


def _aggregate(observations: Dict[str, float], spec: SeriesSpec) -> Optional[float]:
    if not observations:
        return None
    sorted_periods = sorted(
        observations.keys(),
        key=lambda p: datetime.strptime(p, "%Y"),
        reverse=True,
    )
    window = sorted_periods[: spec.window]
    if not window:
        return None
    values = [observations[period] for period in window]
    if spec.aggregator == "last":
        return values[0]
    return sum(values) / len(values)


def build_proxy_table(config: Iterable[SeriesSpec], timeout: float = 60.0) -> Dict[str, Dict[str, float]]:
    table: Dict[str, Dict[str, float]] = {}
    for spec in config:
        observations = _fetch_series(spec, timeout=timeout)
        value = _aggregate(observations, spec)
        if value is None:
            continue
        for sector in spec.sectors:
            table.setdefault(sector, {})[spec.metric] = round(value, 6)
    return table


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Pull IMF KPI proxies and persist them locally.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to the JSON proxy file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds (default: 60)",
    )
    args = parser.parse_args(argv)

    try:
        proxy_table = build_proxy_table(IMF_METRIC_CONFIG, timeout=args.timeout)
    except Exception as exc:
        print(f"[error] Unable to fetch IMF data: {exc}")
        return 1

    if not proxy_table:
        print("[warn] No IMF proxies generated; output not updated.")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proxy_table, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[info] Wrote IMF KPI proxies to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
