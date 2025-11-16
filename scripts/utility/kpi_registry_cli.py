"""
CLI utilities for inspecting and exporting analyst-defined artefacts.

Provides commands to list custom KPIs, analysis templates, and data source
preferences with metadata for audit and compliance reviews.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

from finanlyzeos_chatbot import load_settings
from finanlyzeos_chatbot.custom_kpis import CustomKPICalculator
from finanlyzeos_chatbot.template_processor import TemplateProcessor
from finanlyzeos_chatbot.analytics_workspace import DataSourcePreferencesManager


def _default_database_path() -> Path:
    settings = load_settings()
    return Path(settings.database_path)


def _echo_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


@click.group(help="Analyst workspace inspection CLI.")
@click.option(
    "--database",
    "database_path",
    type=click.Path(path_type=Path, exists=False, dir_okay=False),
    default=None,
    help="Path to the SQLite database. Defaults to the configured database for the project.",
)
@click.pass_context
def cli(ctx: click.Context, database_path: Optional[Path]) -> None:
    path = database_path or _default_database_path()
    ctx.obj = {
        "database": path,
        "calculator": CustomKPICalculator(path),
        "processor": TemplateProcessor(path),
        "preferences": DataSourcePreferencesManager(path),
    }


@cli.group(help="Inspect custom KPI definitions.")
def kpis() -> None:
    """KPI subcommands."""


@kpis.command("list", help="List custom KPIs for a user.")
@click.option("--user", "user_id", default="default", show_default=True, help="User ID scope.")
@click.pass_context
def list_kpis(ctx: click.Context, user_id: str) -> None:
    calculator: CustomKPICalculator = ctx.obj["calculator"]
    kpis = calculator.list_kpis(user_id)
    if not kpis:
        click.echo("No custom KPIs found.")
        return
    for kpi in kpis:
        click.echo(f"{kpi.kpi_id} | {kpi.name} | {kpi.formula}")


@kpis.command("show", help="Show full definition for a KPI.")
@click.argument("kpi_id")
@click.pass_context
def show_kpi(ctx: click.Context, kpi_id: str) -> None:
    calculator: CustomKPICalculator = ctx.obj["calculator"]
    kpi = calculator.get_kpi(kpi_id)
    if not kpi:
        raise click.ClickException(f"KPI {kpi_id} not found.")
    _echo_json(kpi.to_dict())


@kpis.command("export", help="Export KPI definitions to JSON.")
@click.option("--user", "user_id", default="default", show_default=True, help="User ID scope.")
@click.option("--output", type=click.Path(path_type=Path, dir_okay=False), required=True, help="Output file path.")
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    show_default=True,
    help="Export format.",
)
@click.pass_context
def export_kpis(ctx: click.Context, user_id: str, output: Path, export_format: str) -> None:
    calculator: CustomKPICalculator = ctx.obj["calculator"]
    kpis = [kpi.to_dict() for kpi in calculator.list_kpis(user_id)]
    output.parent.mkdir(parents=True, exist_ok=True)
    if export_format == "yaml":
        if yaml is None:
            raise click.ClickException("pyyaml is required for YAML export. Install with `pip install pyyaml`.")
        output.write_text(yaml.safe_dump(kpis, sort_keys=False), encoding="utf-8")
    else:
        output.write_text(json.dumps(kpis, indent=2, default=str), encoding="utf-8")
    click.echo(f"Exported {len(kpis)} KPIs to {output} ({export_format.upper()})")


@cli.group(help="Inspect analysis templates.")
def templates() -> None:
    """Template subcommands."""


@templates.command("list", help="List analysis templates for a user.")
@click.option("--user", "user_id", default="default", show_default=True, help="User ID scope.")
@click.pass_context
def list_templates(ctx: click.Context, user_id: str) -> None:
    processor: TemplateProcessor = ctx.obj["processor"]
    templates = processor.list_analysis_templates(user_id)
    if not templates:
        click.echo("No analysis templates found.")
        return
    for template in templates:
        click.echo(f"{template['template_id']} | {template['name']} | KPIs: {len(template['kpi_ids'])}")


@templates.command("show", help="Show template details.")
@click.argument("template_id")
@click.pass_context
def show_template(ctx: click.Context, template_id: str) -> None:
    processor: TemplateProcessor = ctx.obj["processor"]
    template = processor.get_analysis_template(template_id)
    if not template:
        raise click.ClickException(f"Template {template_id} not found.")
    _echo_json(template)


@templates.command("render", help="Render a template for tickers/parameters.")
@click.argument("template_id")
@click.option("--ticker", "tickers", multiple=True, required=True, help="Ticker symbols (repeatable).")
@click.option("--parameter", "parameters", multiple=True, help="Runtime parameter overrides key=value.")
@click.pass_context
def render_template(ctx: click.Context, template_id: str, tickers: List[str], parameters: List[str]) -> None:
    processor: TemplateProcessor = ctx.obj["processor"]
    params: Dict[str, Any] = {}
    for item in parameters:
        if "=" not in item:
            raise click.ClickException(f"Invalid parameter '{item}'. Expected key=value format.")
        key, value = item.split("=", 1)
        if value.isdigit():
            params[key] = int(value)
        else:
            params[key] = value
    payload = processor.render_analysis_template(template_id, tickers, parameters=params)
    _echo_json(payload)


@cli.group(help="Inspect data source preferences.")
def prefs() -> None:
    """Preference subcommands."""


@prefs.command("list", help="List data source preferences for a user.")
@click.option("--user", "user_id", default="default", show_default=True, help="User ID scope.")
@click.pass_context
def list_prefs(ctx: click.Context, user_id: str) -> None:
    manager: DataSourcePreferencesManager = ctx.obj["preferences"]
    prefs = manager.list(user_id)
    if not prefs:
        click.echo("No data source preferences found.")
        return
    for pref in prefs:
        click.echo(f"{pref.preference_id} | {pref.name} | order={pref.source_order}")


@prefs.command("show", help="Show data source preference details.")
@click.argument("preference_id")
@click.pass_context
def show_pref(ctx: click.Context, preference_id: str) -> None:
    manager: DataSourcePreferencesManager = ctx.obj["preferences"]
    pref = manager.get(preference_id)
    if not pref:
        raise click.ClickException(f"Preference {preference_id} not found.")
    _echo_json(pref.to_dict())


def main() -> None:
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()


