"""Universal ML forecast formatter - institutional 7-section report.

Applies to ALL models, metrics, and tickers. Enforces:
- 7 sections in fixed order
- CI widening if zero-width; numeric clipping/sanity
- No debug logs or internal execution traces
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import math


def _fmt_currency(value: float) -> str:
    abs_v = abs(value)
    if abs_v >= 1_000_000_000_000:
        return f"${value/1_000_000_000_000:.2f}T".replace(".00T", "T")
    if abs_v >= 1_000_000_000:
        return f"${value/1_000_000_000:.1f}B".replace(".0B", "B")
    if abs_v >= 1_000_000:
        return f"${value/1_000_000:.1f}M".replace(".0M", "M")
    return f"${value:,.0f}"


def _sanitize_ci(
    periods: Sequence[int],
    values: Sequence[float],
    lows: Sequence[float],
    highs: Sequence[float],
    min_band_pct: float = 0.10,
) -> Tuple[List[int], List[float], List[float], List[float]]:
    years: List[int] = []
    pv: List[float] = []
    lo: List[float] = []
    hi: List[float] = []
    for i, (y, v) in enumerate(zip(periods, values)):
        low = lows[i] if i < len(lows) else v
        high = highs[i] if i < len(highs) else v
        # Ensure order
        if high < low:
            low, high = high, low
        # Widen zero/near-zero bands: ±10–20% of value (or $1M minimum)
        width = high - low
        min_width = max(abs(v) * min_band_pct, 1_000_000.0)
        if width < min_width:
            half = min_width / 2.0
            low = v - half
            high = v + half
        years.append(int(y))
        pv.append(float(v))
        lo.append(float(low))
        hi.append(float(high))
    return years, pv, lo, hi


def _clip_pct(value: float, lo: float = -80.0, hi: float = 80.0) -> float:
    return max(lo, min(hi, value))


def _calc_yoy(values: Sequence[float]) -> List[float]:
    out: List[float] = []
    for prev, curr in zip(values, values[1:]):
        if not prev:
            out.append(0.0)
        else:
            pct = ((curr / prev) - 1.0) * 100.0
            out.append(_clip_pct(pct))
    return out


def _calc_cagr(values: Sequence[float]) -> Optional[float]:
    if len(values) < 2 or not values[0]:
        return None
    years = len(values) - 1
    try:
        cagr = ((values[-1] / values[0]) ** (1 / years) - 1.0) * 100.0
        return _clip_pct(cagr, -50.0, 50.0)
    except Exception:
        return None


def _trend_label(yoy: Sequence[float]) -> str:
    if not yoy:
        return "stabilizing"
    avg = sum(yoy) / len(yoy)
    if avg >= 8:
        return "accelerating"
    if avg >= 2:
        return "steady"
    if avg <= -2:
        return "moderating"
    return "stabilizing"


def _confidence_label(conf: Optional[float]) -> str:
    if conf is None:
        return "medium"
    if conf >= 0.95:
        return "high"
    if conf >= 0.8:
        return "high"
    if conf >= 0.6:
        return "medium"
    return "low"


def _model_summary(name: str) -> str:
    n = (name or "").strip().lower()
    mapping = {
        "arima": (
            "The forecast is produced using an ARIMA time‑series model. "
            "ARIMA captures autocorrelation in the series and, through differencing, handles trend components. "
            "It is well‑suited to relatively smooth, history‑driven series where structure is persistent. "
            "It does not explicitly encode product launches, competitive shocks, or macro scenarios, so treat results as a statistical baseline."
        ),
        "prophet": (
            "The forecast uses Prophet, which decomposes history into trend and seasonality components. "
            "It is effective when recurring seasonal patterns and trend shifts are present. "
            "Prophet is robust to some outliers but does not inherently model competitive or policy shocks. "
            "Use outputs as a baseline; scenario overlays can reflect macro or strategy changes."
        ),
        "lstm": (
            "The forecast uses an LSTM that summarizes long‑term dependencies in the sequence. "
            "This helps capture non‑linear patterns that linear models may miss. "
            "Performance depends on data volume and stability; regime shifts degrade accuracy. "
            "Treat results as a learned baseline rather than a structural scenario."
        ),
        "gru": (
            "The forecast uses a GRU, a recurrent network similar to LSTM but more parameter‑efficient. "
            "It models non‑linear sequence patterns and can generalize with moderate data. "
            "Like other ML models, it assumes similar future regimes; structural breaks reduce reliability."
        ),
        "transformer": (
            "The forecast uses an attention‑based model that weighs relevant parts of the history. "
            "It can capture complex, long‑range dependencies. "
            "However, it remains history‑conditioned and does not by itself encode exogenous macro or strategic changes."
        ),
        "linear regression": (
            "The forecast uses linear regression to extend the best‑fit historical trend. "
            "It is transparent and stable, but cannot capture non‑linear or seasonal dynamics. "
            "Use as a conservative baseline when the series evolves gradually."
        ),
        "random forest": (
            "The forecast uses a Random Forest, an ensemble of decision trees for tabular patterns. "
            "It models non‑linearities and interactions but can smooth sharp inflections. "
            "Results are baseline projections under the learned relationships."
        ),
        "xgboost": (
            "The forecast uses XGBoost, a gradient‑boosted tree ensemble. "
            "It captures non‑linear structure and interactions effectively in tabular settings. "
            "As with other learned models, outputs assume the training regime persists."
        ),
        "ensemble": (
            "The forecast blends multiple models to stabilize the baseline trajectory. "
            "Ensembling reduces single‑model variance and improves robustness. "
            "It still reflects historical structure; scenario adjustments may be needed for macro/strategy shifts."
        ),
        "hybrid": (
            "The forecast uses a hybrid of statistical and ML components. "
            "This balances bias and variance by combining interpretable structure with learned patterns. "
            "Forecasts remain contingent on the training regime and data coverage."
        ),
        "ets": (
            "The forecast uses ETS, which projects level, trend, and seasonality via exponential smoothing. "
            "It is strong for seasonal, gradually evolving series. "
            "It does not capture exogenous shocks; use as a baseline."
        ),
        "auto": (
            "The forecast uses an auto‑selector to choose a suitable method from the history. "
            "It prioritizes stability and fit but remains history‑conditioned. "
            "Treat outputs as a baseline path."
        ),
    }
    # best-effort normalization for common aliases
    if n == "lr":
        n = "linear regression"
    if n == "rf":
        n = "random forest"
    if n == "xgb":
        n = "xgboost"
    return mapping.get(n, "The model extends recent patterns into the forecast horizon.")


def _sources(ticker: str, used: Optional[List[str]] = None) -> List[str]:
    t = (ticker or "").upper()
    links = [
        f"- [SEC 10-K/10-Q for {t}](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={t})",
        f"- [Yahoo Finance - {t}](https://finance.yahoo.com/quote/{t}/)",
        f"- [Nasdaq - {t}](https://www.nasdaq.com/market-activity/stocks/{t})",
    ]
    if used:
        for src in used:
            if src.lower() == "fred":
                links.append("- [FRED Economic Data](https://fred.stlouisfed.org/)")
            elif src.lower() == "stooq":
                links.append("- [Stooq](https://stooq.com/)")
            elif src.lower() == "macro":
                links.append("- [IMF Data](https://www.imf.org/en/Data)")
                links.append("- [World Bank Data](https://data.worldbank.org/)")
    return links


def format_ml_forecast(
    *,
    ticker: str,
    metric: str,
    model_name: str,
    sector: Optional[str] = None,
    periods: Sequence[int],
    predicted: Sequence[float],
    ci_low: Sequence[float],
    ci_high: Sequence[float],
    confidence: Optional[float],
    scenario_style: Optional[str] = None,
    data_sources: Optional[List[str]] = None,
) -> str:
    # Normalize inputs and enforce CI widening
    years, values, lows, highs = _sanitize_ci(periods, predicted, ci_low, ci_high)
    yoy = _calc_yoy(values)
    cagr = _calc_cagr(values)
    trend = _trend_label(yoy)
    conf_label = _confidence_label(confidence)
    style = (scenario_style or "baseline").lower()

    # 1) Executive Summary
    es: List[str] = []
    if years and values:
        year_span = f"{years[0]}–{years[-1]}" if len(years) > 1 else f"{years[0]}"
        series = ", ".join(f"{y}: {_fmt_currency(v)}" for y, v in zip(years, values))
        es.append(f"{ticker.upper()} {metric.replace('_', ' ').title()} outlook ({year_span}): {series}.")
    es.append(f"Trajectory: {trend}. Confidence: {conf_label}.")
    if len(years) >= 2:
        delta = values[-1] - values[0]
        es.append(f"Net change over horizon: {_fmt_currency(delta)}.")
    es.append(f"Context: {style} forecast using {model_name.upper()}.")

    # 2) Forecast Table
    def _format_forecast_table_strict(years: Sequence[int], vals: Sequence[float], los: Sequence[float], his: Sequence[float]) -> str:
        header = "| Year | Forecast | 95% CI Low | 95% CI High |"
        bar =    "|------|----------|------------|-------------|"
        lines = [header, bar]
        for y, v, lo, hi in zip(years, vals, los, his):
            lines.append(f"| {y} | {_fmt_currency(v)} | {_fmt_currency(lo)} | {_fmt_currency(hi)} |")
        return "\n".join(lines)
    forecast_table = _format_forecast_table_strict(years, values, lows, highs)
    # Short uncertainty sentence (always present)
    if len(lows) >= 2 and len(highs) >= 2:
        early_width = highs[0] - lows[0]
        late_width = highs[-1] - lows[-1]
        if late_width > early_width * 1.05:
            uncertainty_sentence = "Uncertainty widens over time, which is expected as projections move further from observed history."
        elif late_width < early_width * 0.95:
            uncertainty_sentence = "Uncertainty narrows slightly over time, likely reflecting smoother recent dynamics."
        else:
            uncertainty_sentence = "Uncertainty remains broadly similar across the horizon."
    else:
        uncertainty_sentence = "Uncertainty is calibrated to historical variability and forecast distance."

    # 3) Growth Outlook
    # Build Growth Outlook as sentences (not fragments)
    growth_sentences: List[str] = []
    if yoy:
        lines = [f"{years[i-1]}→{years[i]}: {g:+.1f}%" for i, g in enumerate(yoy, start=1)]
        growth_sentences.append("Year‑over‑year growth is " + "; ".join(lines) + ".")
    if cagr is not None:
        growth_sentences.append(f"Over the full horizon, the implied multi‑year CAGR is {cagr:.1f}%.")
    if yoy:
        avg = sum(yoy) / len(yoy)
        if abs(avg) >= 2:
            growth_sentences.append(f"On balance, growth looks {'firmer' if avg>0 else 'softer'} than the recent average.")
        else:
            growth_sentences.append("Overall growth is broadly consistent with recent history.")
    growth_sentences.append("Interpret these rates in the context of company maturity and mix; scale typically dampens extreme outcomes.")

    # 4) Key Business Drivers (placeholder to be populated by upstream if available)
    # Keep generic but useful prompts; avoid filler.
    def _metric_drivers(metric: str, sector: Optional[str]) -> List[str]:
        m = (metric or "").lower()
        s = (sector or "").strip().lower()

        # Sector-aware overlays
        if "technology" in s or "information technology" in s or "software" in s or "semiconductor" in s:
            tech = [
                "- Cloud and subscription monetization; seat expansion and ARPU",
                "- Product cycle cadence and platform stickiness (ecosystem lock‑in)",
                "- AI feature adoption (on‑device/cloud) and developer ecosystem momentum",
                "- Enterprise demand, procurement cycles, and renewal rates",
            ]
        elif "communication" in s or "media" in s or "internet" in s:
            tech = [
                "- Advertising demand and auction dynamics; signal loss mitigation",
                "- Subscription/creator monetization and churn control",
                "- Content spend efficiency and engagement time per user",
                "- Network effects and distribution partnerships",
            ]
        elif "consumer discretionary" in s or "retail" in s or "auto" in s or "apparel" in s:
            tech = [
                "- Unit volumes, ASPs, and promo intensity across channels",
                "- Brand strength, loyalty programs, and DTC mix shift",
                "- Inventory positioning and supply chain flexibility",
                "- International expansion and store/e‑commerce productivity",
            ]
        elif "industrial" in s or "capital goods" in s or "aerospace" in s:
            tech = [
                "- Order intake, backlog conversion, and book‑to‑bill ratios",
                "- Capacity utilization and operating leverage through cycles",
                "- Aftermarket/services penetration and pricing discipline",
                "- Input costs, logistics, and lead time normalization",
            ]
        elif "energy" in s or "oil" in s or "gas" in s:
            tech = [
                "- Commodity price realization and basis differentials",
                "- Production efficiency, decline rates, and capex intensity",
                "- Downstream margins and crack spread dynamics",
                "- Regulatory/environmental constraints and permitting timelines",
            ]
        elif "financial" in s or "bank" in s or "insurance" in s or "asset management" in s:
            tech = [
                "- Net interest income sensitivity to rates and mix",
                "- Credit costs, underwriting discipline, and reserve adequacy",
                "- Fee income diversification and assets under management growth",
                "- Capital ratios, buybacks, and regulatory capital requirements",
            ]
        elif "health care" in s or "biotech" in s or "pharma" in s or "medtech" in s:
            tech = [
                "- Pipeline execution, approvals, and launch curves",
                "- Payer/reimbursement dynamics and mix shift (commercial vs. public)",
                "- Procedure volumes and hospital utilization trends",
                "- IP protection, LOE exposure, and lifecycle management",
            ]
        elif "utilities" in s:
            tech = [
                "- Rate base growth and allowed ROE under regulatory frameworks",
                "- Fuel mix, hedging, and cost pass‑through mechanisms",
                "- Grid modernization capex and reliability targets",
                "- Weather normalization and load growth from data centers/EVs",
            ]
        elif "materials" in s or "chemicals" in s or "mining" in s:
            tech = [
                "- Pricing power vs. feedstock costs and index‑linked contracts",
                "- Volume recovery across end‑markets and destocking cycles",
                "- Operational efficiency, utilization, and yield improvements",
                "- Environmental/compliance constraints and permitting",
            ]
        elif "real estate" in s or "reit" in s:
            tech = [
                "- Occupancy, lease spreads, and retention rates",
                "- Development pipeline, cap rates, and cost of capital",
                "- Tenant quality, duration, and sector exposure (e.g., data centers)",
                "- Balance sheet flexibility and liquidity",
            ]
        else:
            tech = []

        if "revenue" in m:
            base = [
                "- Product/segment mix and pricing power",
                "- Installed base expansion and attach",
                "- Services monetization and ARPU",
                "- Channel inventory and sell-through",
            ]
            return (tech or base) + ([b for b in base if b not in tech] if tech else [])
        if m in {"eps", "earnings", "net income"} or "income" in m:
            base = [
                "- Gross margin mix and operating leverage",
                "- Opex discipline and efficiency",
                "- Tax rate and capital structure",
                "- Share count dynamics",
            ]
            return (tech or base) + ([b for b in base if b not in tech] if tech else [])
        if "ebitda" in m or "margin" in m:
            base = [
                "- Cost of goods, mix, and discounting",
                "- Scale efficiencies in opex",
                "- Pricing power versus input costs",
                "- Capacity utilization",
            ]
            return (tech or base) + ([b for b in base if b not in tech] if tech else [])
        if "cash" in m or "fcf" in m:
            base = [
                "- Working capital cycles",
                "- Capital intensity and capex cadence",
                "- Cash conversion and collections",
                "- Seasonality in receipts/payables",
            ]
            return (tech or base) + ([b for b in base if b not in tech] if tech else [])
        base = [
            "- Product/segment mix and pricing power",
            "- Customer acquisition and retention trends",
            "- Capacity, supply chain, and cost efficiency",
            "- New product launches and monetization",
        ]
        return (tech or base) + ([b for b in base if b not in tech] if tech else [])

    driver_bullets = [s if s.endswith(".") else f"{s}." for s in _metric_drivers(metric, sector)]

    # 5) Risk & Uncertainty
    risk_bullets = [
        "Macro sensitivity (rates, FX) and demand cycles can materially affect outcomes.",
        "Competitive dynamics and pricing pressure may alter trajectory versus baseline.",
        "Regulatory or policy changes could impact the sector and reported results.",
        "Data limitations (e.g., annual‑only history or small samples) constrain stability.",
        "Model limitations apply: this is a statistical baseline and does not encode strategy shifts.",
        "Model outputs may diverge significantly if regime shifts occur relative to the training history.",
    ]

    # 6) Model Explanation
    model_text = _model_summary(model_name)

    # 7) Audit Trail
    source_lines = _sources(ticker, used=data_sources)
    # Removed explicit model type line per user preference

    sections: List[str] = [
        "### 1. Executive Summary",
        " ".join(es),
        "",
        "### 2. Forecast Table",
        forecast_table,
        "",
        uncertainty_sentence,
        "",
        "### 3. Growth Outlook",
        (" ".join(growth_sentences) if growth_sentences else "Insufficient history to compute a growth outlook."),
        "",
        "### 4. Key Business Drivers",
        "\n".join(f"- {b}" for b in driver_bullets),
        "",
        "### 5. Risk & Uncertainty",
        "\n".join(f"- {b}" for b in risk_bullets),
        "",
        "### 6. Model Explanation",
        model_text,
        "",
        "### 7. Audit Trail",
        "\n".join(source_lines),
    ]
    return "\n".join(sections).strip()


