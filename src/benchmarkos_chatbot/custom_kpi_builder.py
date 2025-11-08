"""
Custom KPI Builder - User-Defined Financial Metrics

Allows users to define custom KPIs using natural language and simple formulas.
Integrates with existing analytics engine for calculation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from enum import Enum

LOGGER = logging.getLogger(__name__)


class KPIOperator(Enum):
    """Supported mathematical operators for custom KPIs."""
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    POWER = "^"
    AVERAGE = "avg"
    MAX = "max"
    MIN = "min"
    SUM = "sum"


@dataclass
class CustomKPI:
    """User-defined custom KPI specification."""
    
    kpi_id: str  # Normalized ID (e.g., "efficiency_score")
    display_name: str  # User-friendly name (e.g., "Efficiency Score")
    formula: str  # Original formula (e.g., "(ROE + ROIC) / 2")
    formula_normalized: str  # Normalized formula for calculation
    base_metrics: List[str]  # Required base metrics (e.g., ["roe", "roic"])
    operator_tree: Dict[str, Any]  # Parsed operator tree for calculation
    unit: str  # "percentage", "currency", "ratio", "number"
    description: Optional[str] = None
    category: str = "Custom Metrics"
    validation_rules: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "kpi_id": self.kpi_id,
            "display_name": self.display_name,
            "formula": self.formula,
            "formula_normalized": self.formula_normalized,
            "base_metrics": self.base_metrics,
            "operator_tree": self.operator_tree,
            "unit": self.unit,
            "description": self.description,
            "category": self.category,
            "validation_rules": self.validation_rules or {},
        }


class CustomKPIBuilder:
    """
    Builder for user-defined custom KPIs.
    
    Supports:
    - Natural language KPI definitions
    - Formula parsing and validation
    - Metric dependency resolution
    - Calculation execution
    - KPI library management
    """
    
    # Recognized base metrics (from existing system)
    BASE_METRICS = {
        "revenue", "net_income", "operating_income", "gross_profit",
        "total_assets", "total_liabilities", "shareholders_equity",
        "cash_from_operations", "free_cash_flow", "eps_diluted",
        "eps_basic", "current_assets", "current_liabilities",
        "cash_and_cash_equivalents", "capital_expenditures",
        "depreciation_and_amortization", "ebit", "ebitda",
        "shares_outstanding", "market_cap", "enterprise_value",
        "dividends_paid", "share_repurchases", "long_term_debt",
        "short_term_debt", "total_debt", "working_capital",
    }
    
    # Recognized derived metrics (can also be used)
    DERIVED_METRICS = {
        "roe", "roa", "roic", "profit_margin", "net_margin",
        "operating_margin", "gross_margin", "ebitda_margin",
        "debt_to_equity", "current_ratio", "quick_ratio",
        "free_cash_flow_margin", "revenue_cagr", "eps_cagr",
        "pe_ratio", "pb_ratio", "ev_ebitda", "peg_ratio",
        "dividend_yield", "tsr", "asset_turnover",
    }
    
    ALL_METRICS = BASE_METRICS | DERIVED_METRICS
    
    def __init__(self):
        """Initialize custom KPI builder."""
        self.custom_kpis: Dict[str, CustomKPI] = {}
    
    def detect_kpi_definition(self, user_input: str) -> Optional[Dict[str, str]]:
        """
        Detect if user is trying to define a custom KPI.
        
        Patterns:
        - "Define custom metric: [name] = [formula]"
        - "Create KPI: [name] = [formula]"
        - "Define [name] as [formula]"
        - "Create custom KPI [name] = [formula]"
        
        Returns:
            Dictionary with 'name' and 'formula', or None
        """
        lowered = user_input.strip()
        
        # Pattern 1: "Define custom metric: Name = Formula"
        match = re.search(
            r"(?:define|create)\s+(?:custom\s+)?(?:metric|kpi)\s*:\s*([a-zA-Z][\w\s]*?)\s*=\s*(.+)",
            lowered,
            re.IGNORECASE
        )
        if match:
            return {"name": match.group(1).strip(), "formula": match.group(2).strip()}
        
        # Pattern 2: "Define Name as Formula"
        match = re.search(
            r"(?:define|create)\s+([a-zA-Z][\w\s]+?)\s+as\s+(.+)",
            lowered,
            re.IGNORECASE
        )
        if match:
            return {"name": match.group(1).strip(), "formula": match.group(2).strip()}
        
        # Pattern 3: "Create custom KPI Name = Formula"
        match = re.search(
            r"(?:define|create)\s+(?:custom\s+)?(?:metric|kpi)\s+([a-zA-Z][\w\s]+?)\s*=\s*(.+)",
            lowered,
            re.IGNORECASE
        )
        if match:
            return {"name": match.group(1).strip(), "formula": match.group(2).strip()}
        
        return None
    
    def parse_formula(self, formula: str) -> Dict[str, Any]:
        """
        Parse a formula string into operator tree and extract dependencies.
        
        Supported formats:
        - Simple: "ROE + ROIC"
        - With parentheses: "(ROE + ROIC) / 2"
        - Functions: "avg(ROE, ROIC)"
        - Complex: "Revenue * (1 - COGS/Revenue)"
        
        Returns:
            Dictionary with:
            - operator_tree: Parsed tree structure
            - base_metrics: List of required metrics
            - operators: List of operators used
            - complexity: "simple", "moderate", "complex"
        """
        formula_clean = formula.strip()
        
        # Extract metric names (alphanumeric identifiers)
        metric_pattern = r'\b([a-zA-Z][a-zA-Z0-9_]*)\b'
        potential_metrics = set(re.findall(metric_pattern, formula_clean.lower()))
        
        # Filter out operators, functions, and keywords
        keywords = {"avg", "max", "min", "sum", "abs", "sqrt", "if", "then", "else", "and", "or"}
        base_metrics = [
            metric for metric in potential_metrics
            if metric in self.ALL_METRICS
        ]
        
        # Detect operators
        operators_used = []
        if "+" in formula_clean:
            operators_used.append("+")
        if "-" in formula_clean:
            operators_used.append("-")
        if "*" in formula_clean:
            operators_used.append("*")
        if "/" in formula_clean:
            operators_used.append("/")
        if "^" in formula_clean or "**" in formula_clean:
            operators_used.append("^")
        
        # Detect functions
        functions_used = []
        for func in ["avg", "max", "min", "sum", "abs", "sqrt"]:
            if func in formula_clean.lower():
                functions_used.append(func)
        
        # Determine complexity
        complexity = "simple"
        if len(operators_used) > 2 or len(functions_used) > 0:
            complexity = "moderate"
        if "(" in formula_clean and len(operators_used) > 3:
            complexity = "complex"
        
        # Build simplified operator tree (for simple formulas)
        operator_tree = {
            "type": "expression",
            "formula": formula_clean,
            "metrics": base_metrics,
            "operators": operators_used,
            "functions": functions_used,
        }
        
        return {
            "operator_tree": operator_tree,
            "base_metrics": base_metrics,
            "operators": operators_used,
            "functions": functions_used,
            "complexity": complexity,
        }
    
    def infer_unit(self, formula: str, base_metrics: List[str]) -> str:
        """
        Infer the output unit based on formula and input metrics.
        
        Rules:
        - If all inputs are percentages and formula is average/sum → percentage
        - If formula includes division by revenue → percentage (margin)
        - If formula includes currency metrics → currency
        - Default → ratio
        
        Returns:
            Unit type: "percentage", "currency", "ratio", "number"
        """
        formula_lower = formula.lower()
        
        # Check for percentage metrics
        percentage_metrics = {
            "roe", "roa", "roic", "profit_margin", "net_margin",
            "operating_margin", "gross_margin", "ebitda_margin",
            "revenue_cagr", "eps_cagr", "dividend_yield"
        }
        
        # Check for currency metrics
        currency_metrics = {
            "revenue", "net_income", "operating_income", "gross_profit",
            "free_cash_flow", "cash_and_cash_equivalents", "market_cap",
            "enterprise_value", "total_assets", "total_liabilities"
        }
        
        # If averaging percentages
        if "avg" in formula_lower and any(m in percentage_metrics for m in base_metrics):
            return "percentage"
        
        # If dividing by revenue (likely a margin)
        if "/" in formula and "revenue" in base_metrics:
            return "percentage"
        
        # If using currency metrics
        if any(m in currency_metrics for m in base_metrics):
            # If dividing currency by currency → ratio
            if "/" in formula:
                return "ratio"
            # If adding/subtracting currency → currency
            if "+" in formula or "-" in formula:
                return "currency"
        
        # Default to ratio
        return "ratio"
    
    def validate_formula(self, formula: str, base_metrics: List[str]) -> List[str]:
        """
        Validate formula for errors and missing metrics.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for required base metrics
        missing_metrics = [m for m in base_metrics if m not in self.ALL_METRICS]
        if missing_metrics:
            errors.append(f"Unknown metrics: {', '.join(missing_metrics)}")
        
        # Check for balanced parentheses
        if formula.count("(") != formula.count(")"):
            errors.append("Unbalanced parentheses in formula")
        
        # Check for division by zero risk
        if re.search(r"/\s*0\b", formula):
            errors.append("Division by zero detected")
        
        # Check for empty formula
        if not formula.strip():
            errors.append("Formula cannot be empty")
        
        # Check for at least one metric
        if not base_metrics:
            errors.append("Formula must include at least one financial metric")
        
        return errors
    
    def create_custom_kpi(
        self,
        name: str,
        formula: str,
        description: Optional[str] = None
    ) -> Optional[CustomKPI]:
        """
        Create a custom KPI from natural language definition.
        
        Args:
            name: Display name for the KPI
            formula: Formula expression
            description: Optional description
            
        Returns:
            CustomKPI object if successful, None if validation fails
        """
        # Parse formula
        parsed = self.parse_formula(formula)
        base_metrics = parsed["base_metrics"]
        operator_tree = parsed["operator_tree"]
        
        # Validate formula
        errors = self.validate_formula(formula, base_metrics)
        if errors:
            LOGGER.error(f"Custom KPI validation failed: {errors}")
            return None
        
        # Normalize KPI ID
        kpi_id = re.sub(r'[^\w]+', '_', name.lower()).strip('_')
        
        # Infer unit
        unit = self.infer_unit(formula, base_metrics)
        
        # Create custom KPI
        custom_kpi = CustomKPI(
            kpi_id=kpi_id,
            display_name=name,
            formula=formula,
            formula_normalized=formula,  # Could normalize operators here
            base_metrics=base_metrics,
            operator_tree=operator_tree,
            unit=unit,
            description=description,
        )
        
        # Store in library
        self.custom_kpis[kpi_id] = custom_kpi
        
        LOGGER.info(f"Custom KPI created: {kpi_id} = {formula}")
        LOGGER.info(f"  - Base metrics: {base_metrics}")
        LOGGER.info(f"  - Unit: {unit}")
        LOGGER.info(f"  - Complexity: {parsed['complexity']}")
        
        return custom_kpi
    
    def calculate_custom_kpi(
        self,
        kpi_id: str,
        metric_values: Dict[str, float]
    ) -> Optional[float]:
        """
        Calculate a custom KPI value given base metric values.
        
        Args:
            kpi_id: Custom KPI identifier
            metric_values: Dictionary of base metric values
            
        Returns:
            Calculated KPI value, or None if calculation fails
        """
        if kpi_id not in self.custom_kpis:
            LOGGER.error(f"Custom KPI not found: {kpi_id}")
            return None
        
        custom_kpi = self.custom_kpis[kpi_id]
        
        # Check if all required metrics are available
        missing = [m for m in custom_kpi.base_metrics if m not in metric_values]
        if missing:
            LOGGER.warning(f"Missing metrics for {kpi_id}: {missing}")
            return None
        
        # Build evaluation context (both lowercase and uppercase for flexibility)
        eval_context = {}
        for metric in custom_kpi.base_metrics:
            value = metric_values.get(metric) or metric_values.get(metric.upper()) or metric_values.get(metric.lower())
            if value is not None:
                eval_context[metric] = value
                eval_context[metric.upper()] = value  # Support uppercase in formulas
        
        # Normalize formula for Python eval
        formula_eval = custom_kpi.formula_normalized
        
        # Replace ^ with **  for exponentiation
        formula_eval = formula_eval.replace("^", "**")
        
        # Add safe functions
        safe_functions = {
            "avg": lambda *args: sum(args) / len(args) if args else 0,
            "max": max,
            "min": min,
            "sum": sum,
            "abs": abs,
        }
        eval_context.update(safe_functions)
        
        try:
            # Evaluate formula (SECURITY NOTE: In production, use safer evaluation)
            result = eval(formula_eval, {"__builtins__": {}}, eval_context)
            return float(result)
        except Exception as e:
            LOGGER.error(f"Failed to calculate custom KPI {kpi_id}: {e}")
            return None
    
    def list_custom_kpis(self) -> List[CustomKPI]:
        """Get list of all custom KPIs."""
        return list(self.custom_kpis.values())
    
    def get_custom_kpi(self, kpi_id: str) -> Optional[CustomKPI]:
        """Get a specific custom KPI by ID."""
        return self.custom_kpis.get(kpi_id)
    
    def delete_custom_kpi(self, kpi_id: str) -> bool:
        """Delete a custom KPI from the library."""
        if kpi_id in self.custom_kpis:
            del self.custom_kpis[kpi_id]
            LOGGER.info(f"Deleted custom KPI: {kpi_id}")
            return True
        return False


# -----------------------------
# Natural Language Interface
# -----------------------------


def detect_custom_kpi_query(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Detect if user is asking about custom KPIs.
    
    Patterns:
    - "Define custom metric: Name = Formula"
    - "Calculate [custom_kpi_name] for Apple"
    - "Compare [custom_kpi_name] for AAPL, MSFT"
    - "List my custom KPIs"
    - "Delete custom KPI [name]"
    
    Returns:
        Dictionary with query type and parameters, or None
    """
    lowered = user_input.lower().strip()
    
    # Define custom KPI
    if re.search(r"(?:define|create)\s+(?:custom\s+)?(?:metric|kpi)", lowered):
        builder = CustomKPIBuilder()
        definition = builder.detect_kpi_definition(user_input)
        if definition:
            return {
                "type": "define",
                "name": definition["name"],
                "formula": definition["formula"]
            }
    
    # Calculate custom KPI
    calc_match = re.search(
        r"(?:calculate|compute|show|get)\s+([a-zA-Z][\w\s]+?)\s+(?:for|of)\s+([A-Z]{1,5}|[A-Z][a-z]+)",
        user_input
    )
    if calc_match:
        kpi_name = calc_match.group(1).strip()
        ticker = calc_match.group(2).strip()
        return {
            "type": "calculate",
            "kpi_name": kpi_name,
            "ticker": ticker
        }
    
    # List custom KPIs
    if re.search(r"(?:list|show)\s+(?:my\s+)?custom\s+(?:kpis?|metrics?)", lowered):
        return {"type": "list"}
    
    # Delete custom KPI
    delete_match = re.search(
        r"(?:delete|remove)\s+(?:custom\s+)?(?:kpi|metric)\s+([a-zA-Z][\w\s]+)",
        lowered
    )
    if delete_match:
        return {
            "type": "delete",
            "kpi_name": delete_match.group(1).strip()
        }
    
    return None


# Example usage and test cases
if __name__ == "__main__":
    # Example 1: Simple average
    builder = CustomKPIBuilder()
    
    kpi1 = builder.create_custom_kpi(
        name="Efficiency Score",
        formula="(ROE + ROIC) / 2",
        description="Average of ROE and ROIC"
    )
    
    if kpi1:
        print(f"✅ Created: {kpi1.display_name}")
        print(f"   Formula: {kpi1.formula}")
        print(f"   Metrics needed: {kpi1.base_metrics}")
        print(f"   Unit: {kpi1.unit}")
        
        # Calculate example
        test_values = {"roe": 0.286, "roic": 0.200}
        result = builder.calculate_custom_kpi("efficiency_score", test_values)
        if result is not None:
            print(f"   Example calculation: {result:.3f}")
        else:
            print(f"   Calculation failed (check formula compatibility)")
    
    # Example 2: Complex formula
    kpi2 = builder.create_custom_kpi(
        name="Quality Score",
        formula="ROE * profit_margin * (1 + revenue_cagr)",
        description="Composite quality metric"
    )
    
    if kpi2:
        print(f"\n✅ Created: {kpi2.display_name}")
        print(f"   Formula: {kpi2.formula}")
        print(f"   Metrics needed: {kpi2.base_metrics}")
        print(f"   Complexity: {kpi2.operator_tree.get('complexity', 'unknown')}")
    
    # Example 3: Invalid formula
    kpi3 = builder.create_custom_kpi(
        name="Bad Formula",
        formula="InvalidMetric + AnotherBadOne"
    )
    
    if kpi3:
        print(f"\n✅ Created: {kpi3.display_name}")
    else:
        print(f"\n❌ Failed to create 'Bad Formula' (validation error - expected)")

