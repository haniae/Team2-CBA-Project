"""Utilities for converting raw market data into BenchmarkOS KPIs."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Iterable, Mapping, Optional, Sequence

from .data_sources import PriceBar


US_GAAP = "us-gaap"


@dataclass(frozen=True)
class FinancialFact:
    fiscal_year: int
    value: float
    end: Optional[str] = None


@dataclass(frozen=True)
class CompanyProfile:
    ticker: str
    name: str
    cik: str


def _series_from_facts(
    facts: Mapping,
    tag: str,
    units: str = "USD",
    form_filter: Iterable[str] = ("10-K",),
) -> Sequence[FinancialFact]:
    entries = (
        facts.get("facts", {})
        .get(US_GAAP, {})
        .get(tag, {})
        .get("units", {})
        .get(units, [])
    )
    seen_years = set()
    series: list[FinancialFact] = []
    for entry in entries:
        if entry.get("form") not in form_filter:
            continue
        fiscal_year = entry.get("fy")
        value = entry.get("val")
        if fiscal_year is None or value is None:
            continue
        year_int = int(fiscal_year)
        if year_int in seen_years:
            continue
        seen_years.add(year_int)
        series.append(
            FinancialFact(
                fiscal_year=year_int,
                value=float(value),
                end=entry.get("end"),
            )
        )
    series.sort(key=lambda fact: fact.fiscal_year)
    return series


def _calc_cagr(series: Sequence[FinancialFact], periods: int) -> Optional[float]:
    if len(series) < periods + 1:
        return None
    start = series[-periods - 1].value
    end = series[-1].value
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / periods) - 1


def _latest_margin(
    numerator: Sequence[FinancialFact], denominator: Sequence[FinancialFact]
) -> Optional[float]:
    if not numerator or not denominator:
        return None
    latest_year = min(numerator[-1].fiscal_year, denominator[-1].fiscal_year)
    num_value = next(
        (item.value for item in reversed(numerator) if item.fiscal_year == latest_year),
        None,
    )
    den_value = next(
        (item.value for item in reversed(denominator) if item.fiscal_year == latest_year),
        None,
    )
    if num_value is None or den_value in (None, 0):
        return None
    return num_value / den_value


def compute_financial_metrics(facts: Mapping) -> Dict[str, object]:
    revenue = list(_series_from_facts(facts, "Revenues"))
    net_income = list(_series_from_facts(facts, "NetIncomeLoss"))
    operating_income = list(_series_from_facts(facts, "OperatingIncomeLoss"))
    eps = list(
        _series_from_facts(
            facts,
            "EarningsPerShareDiluted",
            units="USD/shares",
        )
    )

    metrics: Dict[str, object] = {
        "revenue_series": revenue,
        "net_income_series": net_income,
        "operating_income_series": operating_income,
        "eps_series": eps,
    }

    metrics["revenue_cagr_3y"] = _calc_cagr(revenue, 3)
    metrics["net_margin"] = _latest_margin(net_income, revenue)
    metrics["operating_margin"] = _latest_margin(operating_income, revenue)

    return metrics


def compute_price_metrics(price_history: Sequence[PriceBar]) -> Dict[str, Optional[float]]:
    price_history = sorted(price_history, key=lambda bar: bar.timestamp)
    closes = [bar.close for bar in price_history]
    metrics: Dict[str, Optional[float]] = {}
    if len(closes) < 2:
        return metrics

    total_return = closes[-1] / closes[0] - 1
    metrics["total_return"] = total_return

    # Estimate daily returns using consecutive prices.
    daily_returns = [
        (current / previous) - 1 for previous, current in zip(closes, closes[1:]) if previous
    ]
    if daily_returns:
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
        metrics["annualised_volatility"] = sqrt(variance) * sqrt(252)
    else:
        metrics["annualised_volatility"] = None

    span_days = (price_history[-1].timestamp - price_history[0].timestamp).days
    if span_days >= 365:
        years = span_days / 365.0
        metrics["cagr"] = (closes[-1] / closes[0]) ** (1 / years) - 1
    else:
        metrics["cagr"] = None

    running_max = closes[0]
    drawdowns = []
    for price in closes:
        if price > running_max:
            running_max = price
        drawdowns.append(price / running_max - 1)
    metrics["max_drawdown"] = min(drawdowns)

    return metrics


def render_summary(
    profile: CompanyProfile,
    financial_metrics: Mapping[str, object],
    price_metrics: Mapping[str, Optional[float]],
    filings: Sequence[Mapping[str, Optional[str]]],
) -> str:
    def fmt_pct(value: Optional[float]) -> str:
        if value is None:
            return "N/A"
        return f"{value * 100:.1f}%"

    def fmt_currency(series: Sequence[FinancialFact]) -> str:
        if not series:
            return "N/A"
        latest = series[-1]
        billions = latest.value / 1_000_000_000
        return f"${billions:,.1f}B FY{latest.fiscal_year}"

    def fmt_eps(series: Sequence[FinancialFact]) -> Optional[str]:
        if not series:
            return None
        latest = series[-1]
        return f"${latest.value:.2f} FY{latest.fiscal_year}"

    lines = [
        f"{profile.name} ({profile.ticker}) — CIK {profile.cik}",
        "Key Financial KPIs:",
        f"• Revenue latest: {fmt_currency(financial_metrics['revenue_series'])}",
        f"• Revenue CAGR (3y): {fmt_pct(financial_metrics.get('revenue_cagr_3y'))}",
        f"• Net margin: {fmt_pct(financial_metrics.get('net_margin'))}",
        f"• Operating margin: {fmt_pct(financial_metrics.get('operating_margin'))}",
    ]

    eps_value = fmt_eps(financial_metrics.get("eps_series", []))
    if eps_value:
        lines.append(f"• Diluted EPS: {eps_value}")

    lines.append("")
    lines.append("Market Performance (adjusted close):")
    lines.append(
        f"• Total return over sample: {fmt_pct(price_metrics.get('total_return'))}"
    )
    lines.append(f"• CAGR: {fmt_pct(price_metrics.get('cagr'))}")
    lines.append(
        f"• Annualised volatility: {fmt_pct(price_metrics.get('annualised_volatility'))}"
    )
    lines.append(f"• Max drawdown: {fmt_pct(price_metrics.get('max_drawdown'))}")

    if filings:
        lines.append("")
        lines.append("Recent SEC Filings:")
        for item in filings[:5]:
            accession = item.get("accession_number") or "N/A"
            lines.append(
                f"• {item.get('form')} filed {item.get('filing_date')} (report {item.get('report_date')}) — {accession}"
            )

    lines.append("")
    lines.append(
        "Use these baselines to drive BenchmarkOS benchmarking workflows, risk controls, and scenario planning."
    )

    return "\n".join(lines)

