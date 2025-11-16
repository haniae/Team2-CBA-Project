"""Mapping of KPI identifiers to compute rules executed by the backfill pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type hinting only
    from .kpi_backfill import Context

ComputationResult = Tuple[Optional[float], str, str, str, Optional[str]]


@dataclass(frozen=True)
class Rule:
    metric_id: str
    compute: Callable[["Context"], ComputationResult]
    requires: List[str]


POLICY: Dict[str, Rule] = {}


def _register(metric_id: str, method_name: str, requires: List[str]) -> None:
    def _compute(ctx: "Context") -> ComputationResult:
        method = getattr(ctx, method_name)
        return method()

    POLICY[metric_id] = Rule(metric_id, _compute, requires)


def register_rules() -> None:
    """Populate the global POLICY mapping exactly once."""
    if POLICY:
        return

    _register("revenue_cagr", "compute_revenue_cagr", ["revenue"])
    _register("eps_cagr", "compute_eps_cagr", ["eps_diluted", "net_income", "shares_outstanding"])
    _register("ebitda_growth", "compute_ebitda_growth", ["ebitda", "operating_income", "depreciation_and_amortization"])
    _register("ebitda_margin", "compute_ebitda_margin", ["ebitda", "revenue"])
    _register("operating_margin", "compute_operating_margin", ["operating_income", "revenue"])
    _register("net_margin", "compute_net_margin", ["net_income", "revenue"])
    _register("profit_margin", "compute_profit_margin", ["net_income", "revenue"])
    _register("return_on_assets", "compute_return_on_assets", ["net_income", "total_assets"])
    _register("return_on_equity", "compute_return_on_equity", ["net_income", "shareholders_equity"])
    _register(
        "return_on_invested_capital",
        "compute_return_on_invested_capital",
        ["operating_income", "income_tax_expense", "shareholders_equity", "cash_and_cash_equivalents"],
    )
    _register(
        "free_cash_flow_margin",
        "compute_free_cash_flow_margin",
        ["free_cash_flow", "cash_from_operations", "capital_expenditures", "revenue"],
    )
    _register("cash_conversion", "compute_cash_conversion", ["cash_from_operations", "net_income"])
    _register(
        "debt_to_equity",
        "compute_debt_to_equity",
        ["long_term_debt", "short_term_debt", "shareholders_equity"],
    )
    _register("pe_ratio", "compute_pe_ratio", ["eps_diluted", "price"])
    _register("ev_ebitda", "compute_ev_ebitda", ["ebitda", "market_cap"])
    _register("pb_ratio", "compute_pb_ratio", ["shareholders_equity", "price", "shares_outstanding"])
    _register("peg_ratio", "compute_peg_ratio", ["eps_cagr", "pe_ratio"])
    _register("dividend_yield", "compute_dividend_yield", ["dividends_per_share", "price"])
    _register("tsr", "compute_tsr", ["price"])
    _register(
        "share_buyback_intensity",
        "compute_share_buyback_intensity",
        ["share_repurchases", "market_cap"],
    )

