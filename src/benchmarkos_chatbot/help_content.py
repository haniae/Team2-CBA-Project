"""Shared help content utilities with optional user customisation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Sequence

DEFAULT_PROMPTS: List[str] = [
    "What is Apple's revenue?",
    "Show Microsoft's EBITDA margin",
    "Is Tesla overvalued?",
    "Compare AAPL and MSFT profitability",
    "Why is Tesla's margin declining?",
    "What's my portfolio exposure?",
    "Optimize my portfolio to maximize Sharpe",
    "What if the market drops 20%?",
]

DEFAULT_SECTIONS: List[Dict[str, Any]] = [
    {
        "icon": "📊",
        "title": "Company Metrics & Analysis",
        "command": "What is [TICKER]'s [metric]?",
        "purpose": "Get single metrics, trends, or comprehensive company analysis.",
        "examples": [
            "What is Apple's revenue?",
            "Show Microsoft's EBITDA margin",
            "What's Tesla's free cash flow?",
            "What is Google's net income?",
            "Show NVDA's gross margin",
            "What is META's return on equity?",
        ],
        "delivers": "Direct answers, YoY growth, 3-5 year CAGRs, business drivers, SEC sources.",
    },
    {
        "icon": "🔍",
        "title": "Why Questions (Deep Analysis)",
        "command": "Why is [TICKER]'s [metric] [trend]?",
        "purpose": "Get multi-factor explanations for changes in financial metrics.",
        "examples": [
            "Why is Tesla's margin declining?",
            "Why is Apple's revenue growing?",
            "Why is Microsoft more profitable?",
            "Why did NVDA's stock price increase?",
        ],
        "delivers": "3-5 key drivers, quantified impacts, business context, forward outlook.",
    },
    {
        "icon": "🆚",
        "title": "Comparisons",
        "command": "Compare [TICKER1] vs [TICKER2] [metric]",
        "purpose": "Compare companies, metrics, or multi-company analysis.",
        "examples": [
            "Is Microsoft more profitable than Apple?",
            "Compare Apple vs Microsoft margins",
            "Which is better: Tesla or Ford profitability?",
            "Compare AAPL, MSFT, and GOOGL revenue growth",
            "Compare FAANG stocks",
        ],
        "delivers": "Side-by-side metrics, relative strengths, structural differences, investment implications.",
    },
    {
        "icon": "💰",
        "title": "Valuation & Multiples",
        "command": "What's [TICKER]'s [valuation metric]?",
        "purpose": "Get valuation metrics, multiples, and fair value analysis.",
        "examples": [
            "What's Apple's P/E ratio?",
            "Is Tesla overvalued?",
            "What's Microsoft's EV/EBITDA?",
            "Compare Apple's P/E to the S&P 500 average",
            "What's Amazon's PEG ratio?",
        ],
        "delivers": "Valuation metrics (P/E, EV/EBITDA, P/B, PEG), peer comparison, historical ranges.",
    },
    {
        "icon": "💪",
        "title": "Financial Health & Risk",
        "command": "What's [TICKER]'s [risk metric]?",
        "purpose": "Assess balance sheet strength, leverage, and risk factors.",
        "examples": [
            "What's Tesla's debt-to-equity ratio?",
            "How leveraged is Apple?",
            "What's Microsoft's net debt?",
            "What are the key risks for Tesla?",
            "What's Apple's interest coverage ratio?",
        ],
        "delivers": "Balance sheet metrics, leverage ratios, credit analysis, risk factors from 10-K.",
    },
    {
        "icon": "📈",
        "title": "Profitability & Margins",
        "command": "What's [TICKER]'s [margin metric]?",
        "purpose": "Analyze margins, profitability trends, and operating efficiency.",
        "examples": [
            "What's Apple's gross margin?",
            "What's Apple's gross margin trend?",
            "Which is more profitable: Microsoft or Google?",
            "What's driving Tesla's margin compression?",
            "Compare EBITDA margins across FAANG",
        ],
        "delivers": "Margin breakdown, multi-year trends, peer comparison, drivers of margin changes.",
    },
    {
        "icon": "🚀",
        "title": "Growth & Performance",
        "command": "What's [TICKER]'s [growth metric]?",
        "purpose": "Analyze revenue growth, earnings growth, and growth outlook.",
        "examples": [
            "Is Apple growing faster than Microsoft?",
            "What's Tesla's revenue CAGR?",
            "How fast is Amazon growing?",
            "What's Apple's earnings growth?",
            "What's the revenue forecast for Microsoft?",
        ],
        "delivers": "Historical growth rates (3-5 years), segment breakdown, growth drivers, analyst forecasts.",
    },
    {
        "icon": "💵",
        "title": "Cash Flow & Capital Allocation",
        "command": "What's [TICKER]'s [cash flow metric]?",
        "purpose": "Analyze cash generation, capital allocation, and shareholder returns.",
        "examples": [
            "What's Apple's free cash flow?",
            "How much cash does Microsoft generate?",
            "How is Amazon allocating capital?",
            "What's Microsoft's dividend yield?",
            "Is Apple doing share buybacks?",
        ],
        "delivers": "Cash flow statements, FCF trends, capex plans, dividend history, buyback programs.",
    },
    {
        "icon": "🎯",
        "title": "Investment Analysis",
        "command": "Should I invest in [TICKER]?",
        "purpose": "Get investment thesis, bull/bear cases, and recommendations.",
        "examples": [
            "Should I invest in Apple or Microsoft?",
            "What's the bull case for Tesla?",
            "What's the bear case for Apple?",
            "What are the catalysts for Amazon?",
            "Why is Netflix stock down?",
        ],
        "delivers": "Investment thesis, bull/bear arguments, catalysts, valuation vs fundamentals, risk/reward.",
    },
    {
        "icon": "🏆",
        "title": "Market Position & Competition",
        "command": "Who are [TICKER]'s competitors?",
        "purpose": "Analyze competitive landscape, market share, and competitive advantages.",
        "examples": [
            "Who are Apple's main competitors?",
            "What's Tesla's market share?",
            "What's Apple's moat?",
            "Is Apple losing share to Samsung?",
            "How competitive is the smartphone market?",
        ],
        "delivers": "Competitor analysis, market share data, competitive advantages, industry structure.",
    },
    {
        "icon": "👔",
        "title": "Management & Strategy",
        "command": "How is [TICKER]'s management performing?",
        "purpose": "Assess management performance, corporate strategy, and governance.",
        "examples": [
            "How is Apple's management performing?",
            "What's Tesla's strategy for growth?",
            "How is Microsoft allocating capital?",
            "What's Apple's board composition?",
            "Is Apple's capital allocation shareholder-friendly?",
        ],
        "delivers": "Management track record, strategic initiatives, capital allocation, governance structure.",
    },
    {
        "icon": "🏭",
        "title": "Sector & Industry Analysis",
        "command": "How is the [sector] performing?",
        "purpose": "Analyze sector trends, industry dynamics, and macro factors.",
        "examples": [
            "How is the tech sector performing?",
            "What's the outlook for semiconductors?",
            "Compare retail vs e-commerce stocks",
            "What are the trends in the auto industry?",
            "How is AI affecting tech stocks?",
        ],
        "delivers": "Sector metrics, industry trends, competitive dynamics, regulatory changes, macro factors.",
    },
    {
        "icon": "📊",
        "title": "Analyst & Institutional Views",
        "command": "What do analysts think of [TICKER]?",
        "purpose": "Get analyst ratings, price targets, and institutional ownership data.",
        "examples": [
            "What do analysts think of Apple?",
            "What's the price target for Microsoft?",
            "What's the institutional ownership of Apple?",
            "Have there been recent upgrades on Tesla?",
            "Who are the largest holders of Microsoft?",
        ],
        "delivers": "Analyst ratings (Buy/Hold/Sell), price targets, institutional holdings, insider transactions.",
    },
    {
        "icon": "🌍",
        "title": "Macroeconomic Context",
        "command": "How do [economic factors] affect [TICKER]?",
        "purpose": "Analyze economic sensitivity, interest rate impact, and inflation effects.",
        "examples": [
            "How do interest rates affect tech stocks?",
            "What's the impact of inflation on Apple?",
            "How is Apple affected by recession?",
            "How do currency fluctuations impact Microsoft's earnings?",
            "What's the recession risk for tech?",
        ],
        "delivers": "Economic sensitivity analysis, historical correlations, geographic revenue breakdown, hedging strategies.",
    },
    {
        "icon": "🌱",
        "title": "ESG & Sustainability",
        "command": "What's [TICKER]'s ESG score?",
        "purpose": "Get ESG scores, environmental initiatives, and governance ratings.",
        "examples": [
            "What's Apple's ESG score?",
            "How sustainable is Tesla's business?",
            "What's Microsoft's carbon footprint?",
            "Does Microsoft have good governance?",
            "What are Amazon's environmental initiatives?",
        ],
        "delivers": "ESG scores, environmental initiatives, social policies, governance structure, controversies.",
    },
    {
        "icon": "📈",
        "title": "Dashboard & Visualizations",
        "command": "Show dashboard for [TICKER]",
        "purpose": "Get comprehensive interactive dashboards with charts and metrics.",
        "examples": [
            "Dashboard AAPL",
            "Show dashboard for Apple",
            "Full dashboard for Microsoft",
            "Comprehensive dashboard Tesla",
        ],
        "delivers": "Interactive charts, KPI cards, trend visualizations, comparison views, export options.",
    },
    {
        "icon": "🌐",
        "title": "Segment & Geographic Analysis",
        "command": "What's [TICKER]'s [segment/region] revenue?",
        "purpose": "Analyze business segments, geographic revenue, and product mix.",
        "examples": [
            "What's Apple's exposure to China?",
            "Where does Microsoft's revenue come from?",
            "How important is iPhone to Apple?",
            "What's the outlook for Tesla's Cybertruck?",
            "Is AWS Amazon's most profitable business?",
        ],
        "delivers": "Segment breakdown, geographic revenue, product mix, customer demographics, growth by segment.",
    },
    {
        "icon": "🧾",
        "title": "Facts from SEC Filings",
        "command": "Fact TICKER YEAR [metric]",
        "purpose": "Retrieve exactly what was reported in 10-K/10-Q filings.",
        "example": "Fact TSLA 2022 revenue",
        "delivers": "Original value, adjustment notes, and source reference.",
    },
    {
        "icon": "🧮",
        "title": "Scenario Modelling",
        "command": "Scenario TICKER NAME rev=+X% margin=+Y% mult=+Z",
        "purpose": "Run what-if cases for growth, margin shifts, or valuation moves.",
        "example": "Scenario NVDA Bull rev=+8% margin=+1.5% mult=+0.5",
        "delivers": "Projected revenue, margins, EPS/FCF change, implied valuation.",
    },
    {
        "icon": "📊",
        "title": "Portfolio Management",
        "command": [
            "Show my portfolio holdings",
            "What's my sector exposure?",
            "Optimize my portfolio",
            "What if the market drops 20%?",
        ],
        "purpose": "Manage portfolios, analyze exposures, optimize, and run scenarios.",
        "examples": [
            "Show my portfolio holdings",
            "List portfolios",
            "What's my sector exposure?",
            "Show my factor exposure",
            "Optimize my portfolio to maximize Sharpe",
            "What if the market drops 20%?",
            "Stress test my portfolio with 20% drop",
            "Attribute my portfolio performance",
        ],
        "delivers": "Holdings, exposures, optimization results, scenario analysis, performance attribution.",
    },
    {
        "icon": "⚙️",
        "title": "Data Management",
        "command": [
            "Ingest TICKER [years]",
            "Ingest status TICKER",
            "Audit TICKER [year]",
        ],
        "purpose": "Refresh data, track ingestion progress, or review the audit log.",
        "examples": [
            "Ingest META 5 — refreshes five fiscal years of filings and quotes.",
            "Audit META 2023 — lists the latest import activity and KPI updates.",
        ],
    },
]

def _parse_user_tips(raw: str) -> List[str]:
    """Interpret user-supplied HELP_TIPS content from the environment."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    tips: Iterable[str]
    if isinstance(parsed, list):
        tips = [str(entry) for entry in parsed]
    elif isinstance(parsed, str):
        tips = [parsed]
    else:
        # Fallback: split on pipes or newlines
        separators = "|" if "|" in raw else "\n"
        tips = raw.split(separators) if separators in raw else [raw]

    cleaned = [tip.strip() for tip in tips if str(tip).strip()]
    return cleaned


def load_user_tips() -> List[str] | None:
    """Return user-defined tips sourced from the HELP_TIPS environment variable."""
    raw = os.getenv("HELP_TIPS")
    if not raw:
        return None
    custom = _parse_user_tips(raw)
    return custom or None


HELP_TIPS: List[str] = load_user_tips() or []


def build_help_text(tips: Sequence[str] | None = None) -> str:
    """Compose the multiline help text used by the chatbot and CLI."""

    tips = list(tips or HELP_TIPS)
    lines: List[str] = [
        "📘 BenchmarkOS Copilot — Quick Reference",
        "",
        "How to ask:",
    ]

    lines.extend(f"• {prompt}" for prompt in DEFAULT_PROMPTS)
    lines.append("")
    lines.append("──────────────────────────────────────")

    for idx, section in enumerate(DEFAULT_SECTIONS):
        lines.append(f"{section['icon']} {section['title'].upper()}")

        command = section["command"]
        if isinstance(command, (list, tuple)):
            for i, entry in enumerate(command):
                prefix = "Command:" if i == 0 else "         "
                lines.append(f"{prefix} {entry}")
        else:
            lines.append(f"Command: {command}")

        if purpose := section.get("purpose"):
            lines.append(f"Purpose: {purpose}")
        if example := section.get("example"):
            lines.append(f"Example: {example}")
        if delivers := section.get("delivers"):
            lines.append(f"Delivers: {delivers}")

        if examples := section.get("examples"):
            lines.append("Examples:")
            lines.extend(f"• {item}" for item in examples)

        lines.append("")
        if idx != len(DEFAULT_SECTIONS) - 1:
            lines.append("──────────────────────────────────────")

    if tips:
        lines.append("──────────────────────────────────────")
        lines.append("💡 TIPS")
        for tip in tips:
            lines.append(f"• {tip}")

    return "\n".join(lines)


def get_help_metadata() -> Dict[str, Any]:
    """Return structured help data for the web UI."""
    return {
        "prompts": DEFAULT_PROMPTS,
        "sections": DEFAULT_SECTIONS,
        "tips": HELP_TIPS,
    }


HELP_TEXT = build_help_text()
