"""Simple, business-friendly ML forecast formatter.

Produces a clear summary, a small table, and plain-language takeaways.
Avoids technical jargon (no hyperparameters, diagnostics, or method internals).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple


def _fmt_currency(value: float) -> str:
	abs_v = abs(value)
	if abs_v >= 1_000_000_000:
		return f"${value/1_000_000_000:.1f}B"
	if abs_v >= 1_000_000:
		return f"${value/1_000_000:.1f}M"
	return f"${value:,.0f}"


def _sanitize_ci(values: Sequence[float], lows: Sequence[float], highs: Sequence[float]) -> Tuple[List[float], List[float]]:
	adj_low: List[float] = []
	adj_high: List[float] = []
	for i, v in enumerate(values):
		lo = lows[i] if i < len(lows) else v
		hi = highs[i] if i < len(highs) else v
		if hi < lo:
			lo, hi = hi, lo
		# widen near-zero bands to a minimal width (10% of value or $1M) for readability
		width = hi - lo
		min_width = max(abs(v) * 0.10, 1_000_000.0)
		if width < min_width:
			half = min_width / 2.0
			lo = v - half
			hi = v + half
		adj_low.append(lo)
		adj_high.append(hi)
	return adj_low, adj_high


def _format_table(periods: Sequence[int], values: Sequence[float], lows: Sequence[float], highs: Sequence[float]) -> str:
	header = "| Year | Estimate | Range (Low–High) |\n|---:|---:|---:|"
	rows: List[str] = []
	for y, v, lo, hi in zip(periods, values, lows, highs):
		rows.append(f"| {y} | {_fmt_currency(v)} | {_fmt_currency(lo)} – {_fmt_currency(hi)} |")
	return "\n".join([header, *rows])


def _confidence_label(conf: float) -> str:
	if conf >= 0.8:
		return "high"
	if conf >= 0.6:
		return "moderate"
	return "low"


def _model_sources(name: str) -> List[Tuple[str, str]]:
	n = (name or "").strip().lower()
	links: List[Tuple[str, str]] = []
	if n == "arima":
		links.append(("ARIMA (statsmodels) Documentation", "https://www.statsmodels.org/stable/tsa.html"))
	elif n == "prophet":
		links.append(("Prophet Documentation", "https://facebook.github.io/prophet/"))
	elif n == "ets":
		links.append(("ETS - statsmodels", "https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html"))
	elif n in {"lstm", "gru", "transformer", "ensemble"}:
		links.append(("Forecasting overview", "https://otexts.com/fpp3/"))
	else:
		links.append(("Time Series Forecasting Overview", "https://otexts.com/fpp3/"))
	return links


def _ticker_sources(ticker: str) -> List[Tuple[str, str]]:
	t = (ticker or "").upper()
	return [
		(f"{t} on Yahoo Finance", f"https://finance.yahoo.com/quote/{t}/"),
		(f"{t} Filings on SEC EDGAR", f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={t}")
	]


def format_finance_forecast(
	*,
	ticker: str,
	metric: str,
	model_name: str,
	periods: Sequence[int],
	values: Sequence[float],
	lows: Sequence[float],
	highs: Sequence[float],
	confidence: float,
	explainability: Optional[Dict[str, any]] = None,
	sector_note: Optional[str] = None,
	user_query: Optional[str] = None,
) -> str:
	adj_low, adj_high = _sanitize_ci(values, lows, highs)
	conf_label = _confidence_label(confidence)

	# Summary (one short paragraph)
	summary: str = ""
	if periods and values:
		years = f"{periods[0]}–{periods[-1]}" if len(periods) > 1 else f"{periods[0]}"
		first_v = values[0]
		last_v = values[-1]
		dir_word = "higher" if last_v >= first_v else "lower"
		summary = f"{ticker.upper()} {metric.title()} over {years} is expected to be {dir_word} by the end of the period."
	if not summary:
		summary = f"{ticker.upper()} {metric.title()} outlook."

	# Forecast table
	table_md = _format_table(periods, values, adj_low, adj_high)

	# Two short takeaways (plain language)
	takeaways: List[str] = []
	if len(values) >= 2:
		change = values[-1] - values[0]
		if change != 0:
			takeaways.append(f"Net change across the period: {_fmt_currency(abs(change))} {'up' if change>0 else 'down'}.")
	if conf_label:
		takeaways.append(f"Confidence: {conf_label}.")

	# Optional simple drivers if provided (non-technical)
	driver_lines: List[str] = []
	if explainability:
		features = None
		drivers_dict = explainability.get("drivers") or {}
		if isinstance(drivers_dict, dict):
			features = drivers_dict.get("features")
		if not features:
			features = explainability.get("feature_importance")
		if isinstance(features, dict):
			top = sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
			if top:
				driver_lines.append("What likely drives this:")
				for name, _ in top:
					driver_lines.append(f"- {str(name)}")

	# Sources
	model_links = _model_sources(model_name)
	ticker_links = _ticker_sources(ticker)

	sections: List[str] = [
		summary,
		"",
		table_md,
	]
	if takeaways:
		sections.extend(["", "- " + "\n- ".join(takeaways)])
	if driver_lines:
		sections.extend(["", "\n".join(driver_lines)])
	if sector_note:
		sections.extend(["", sector_note])
	if model_links or ticker_links:
		sections.extend(["", *([f"- [{label}]({url})" for (label, url) in (ticker_links + model_links)])])

	return "\n".join(sections).strip()


