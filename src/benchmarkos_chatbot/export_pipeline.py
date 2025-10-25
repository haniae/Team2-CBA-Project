"""Utilities for generating executive exports from dashboard payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Iterable, List, Tuple

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
from .dashboard_utils import build_cfi_dashboard_payload
from .cfi_ppt_builder import build_cfi_ppt


@dataclass(frozen=True)
class ExportResult:
    """Return type used by export generators."""

    content: bytes
    media_type: str
    filename: str


def _safe_slug(value: str, fallback: str = "benchmarkos") -> str:
    characters = [ch.lower() if ch.isalnum() else "-" for ch in value or ""]
    slug = "".join(characters).strip("-")
    return slug or fallback


def _format_percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{number * 100:.1f}%"


def _format_multiple(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{number:.1f}x"


def _format_currency(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    magnitude = abs(number)
    if magnitude >= 1_000_000_000:
        return f"${number / 1_000_000_000:.1f}B"
    if magnitude >= 1_000_000:
        return f"${number / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:,.2f}"


def _format_value(entry: Dict[str, Any]) -> str:
    value = entry.get("value")
    entry_type = entry.get("type")
    if value in (None, ""):
        return "N/A"
    if entry_type == "percent":
        return _format_percent(value)
    if entry_type == "multiple":
        return _format_multiple(value)
    return _format_currency(value)


def _collect_kpi_rows(
    kpis: Iterable[Dict[str, Any]],
    limit: int = 20,
) -> List[Tuple[str, str, str, str]]:
    rows: List[Tuple[str, str, str, str]] = []
    for entry in list(kpis or [])[:limit]:
        label = entry.get("label") or entry.get("id") or "Metric"
        value_text = _format_value(entry)
        period = entry.get("period") or ""
        source = entry.get("source") or ""
        rows.append((label, value_text, period, source))
    return rows


def _collect_source_rows(
    sources: Iterable[Dict[str, Any]],
    limit: int = 50,
) -> List[Tuple[str, str, str]]:
    """Collect source rows with text, url, and display text."""
    rows: List[Tuple[str, str, str]] = []
    for entry in list(sources or [])[:limit]:
        # Support both old format (label/period/source) and new format (text/url)
        text = entry.get("text") or ""
        url = entry.get("url") or ""
        
        # Fallback to old format
        if not text:
            label = entry.get("label") or entry.get("metric") or "Metric"
            period = entry.get("period") or ""
            source = entry.get("source") or ""
            parts = [label]
            if period:
                parts.append(f"({period})")
            if source:
                parts.append(f"- {source}")
            text = " ".join(parts)
        
        # Extract ticker from text if present (support both bullet and bell separators)
        display_text = text
        for delimiter in (" \u2022 ", " \x07 "):
            if delimiter in text:
                parts = text.split(delimiter)
                ticker = parts[0] if parts else ""
                rest = delimiter.join(parts[1:]) if len(parts) > 1 else ""
                display_text = f"{ticker}: {rest}" if rest else ticker
                break
        
        rows.append((display_text, url, text))
    return rows


def _build_pdf(payload: Dict[str, Any]) -> bytes:
    meta = payload.get("meta", {})
    kpis = payload.get("kpi_summary", [])
    sources = payload.get("sources", [])
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    company = meta.get("company") or meta.get("ticker") or "BenchmarkOS Dashboard"
    ticker = meta.get("ticker") or ""
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"{company} {f'({ticker})' if ticker else ''}".strip(), ln=1)

    pdf.set_font("Helvetica", "", 11)
    rec = meta.get("recommendation") or "N/A"
    target_price = _format_currency(meta.get("target_price"))
    scenario = meta.get("scenario") or meta.get("live_scenario") or "Consensus"
    pdf.multi_cell(0, 6, f"Recommendation: {rec} | Target Price: {target_price} | Scenario: {scenario}")
    if meta.get("date"):
        pdf.multi_cell(0, 6, f"Report Date: {meta['date']}")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "KPI Scorecard", ln=1)
    pdf.set_font("Helvetica", "", 11)
    for label, value_text, period, source in _collect_kpi_rows(kpis):
        line = f"- {label}: {value_text}"
        if period:
            line += f" ({period})"
        pdf.multi_cell(0, 6, line)
        if source:
            pdf.set_font("Helvetica", "I", 9)
            pdf.multi_cell(0, 5, f"   Source: {source}")
            pdf.set_font("Helvetica", "", 11)
        pdf.ln(1)

    valuation = payload.get("valuation_table") or []
    if valuation:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, "Valuation Summary", ln=1)
        pdf.set_font("Helvetica", "", 11)
        for row in valuation:
            label = row.get("Label") or "Metric"
            market = _format_currency(row.get("Market"))
            dcf = _format_currency(row.get("DCF"))
            comps = _format_currency(row.get("Comps"))
            pdf.multi_cell(0, 6, f"- {label}: Market {market} | DCF {dcf} | Comps {comps}")

    key_financials = payload.get("key_financials") or {}
    columns = key_financials.get("columns") or []
    rows = key_financials.get("rows") or []
    if columns and rows:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, "Key Financial Highlights", ln=1)
        pdf.set_font("Helvetica", "", 10)
        header_line = "Period: " + ", ".join(str(col) for col in columns)
        pdf.multi_cell(0, 5, header_line)
        for entry in rows[:6]:
            values = entry.get("values") or []
            formatted = []
            for value in values:
                if isinstance(value, (int, float)):
                    formatted.append(f"{value:,.0f}")
                else:
                    formatted.append(str(value or "N/A"))
            pdf.multi_cell(0, 5, f"{entry.get('label')}: " + ", ".join(formatted))

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Sources & Citations", ln=1)
    pdf.set_font("Helvetica", "", 9)
    if not sources:
        pdf.multi_cell(0, 5, "Source details unavailable.")
    else:
        for display_text, url, full_text in _collect_source_rows(sources):
            # If URL is available, make it clickable
            if url:
                # Add bullet point
                pdf.cell(5, 5, "-")
                # Add clickable link
                pdf.set_text_color(0, 0, 255)  # Blue text for links
                pdf.set_font("Helvetica", "U", 9)  # Underlined
                pdf.cell(0, 5, display_text[:100], ln=1, link=url)  # Truncate long text
                pdf.set_text_color(0, 0, 0)  # Reset to black
                pdf.set_font("Helvetica", "", 9)  # Reset font
                # Add URL on next line
                pdf.cell(5, 4, "")  # Indent
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(100, 100, 100)  # Gray
                pdf.multi_cell(0, 4, f"Link: {url[:80]}...")  # Show URL
                pdf.set_text_color(0, 0, 0)  # Reset
                pdf.set_font("Helvetica", "", 9)
            else:
                # No URL, just show text
                pdf.multi_cell(0, 5, f"- {display_text[:120]}")
            pdf.ln(1)

    pdf_output = pdf.output(dest="S").encode("latin1")
    return pdf_output


def _build_ppt(payload: Dict[str, Any]) -> bytes:
    """Generate CFI-style professional PowerPoint deck."""
    return build_cfi_ppt(payload)


def _build_excel(payload: Dict[str, Any]) -> bytes:
    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "Summary"

    meta = payload.get("meta", {})
    ws_summary["A1"] = "Company"
    ws_summary["B1"] = meta.get("company")
    ws_summary["A2"] = "Ticker"
    ws_summary["B2"] = meta.get("ticker")
    ws_summary["A3"] = "Recommendation"
    ws_summary["B3"] = meta.get("recommendation")
    ws_summary["A4"] = "Target Price"
    ws_summary["B4"] = payload.get("price", {}).get("Target Price")
    if ws_summary["B4"].value is not None:
        ws_summary["B4"].number_format = "$#,##0.00"
    ws_summary["A5"] = "Scenario"
    ws_summary["B5"] = meta.get("scenario") or meta.get("live_scenario")
    ws_summary["A7"] = "KPI Scorecard"
    ws_summary["A7"].font = Font(bold=True)

    headers = ("Metric", "Value", "Period", "Source")
    ws_summary.append(headers)
    for entry in payload.get("kpi_summary", []):
        row = ws_summary.max_row + 1
        ws_summary.append((entry.get("label"), entry.get("value"), entry.get("period"), entry.get("source")))
        value_cell = ws_summary.cell(row=row, column=2)
        entry_type = entry.get("type")
        if entry_type == "percent":
            value_cell.number_format = "0.0%"
        elif entry_type == "multiple":
            value_cell.number_format = "0.0#"
        else:
            value_cell.number_format = "#,##0.00"
    for column in ("A", "B", "C", "D"):
        ws_summary.column_dimensions[column].width = 24

    key_financials = payload.get("key_financials") or {}
    columns = key_financials.get("columns") or []
    rows = key_financials.get("rows") or []
    if columns and rows:
        ws_financials = wb.create_sheet("Financials")
        ws_financials.append(["Metric", *columns])
        for entry in rows:
            values = entry.get("values") or []
            ws_financials.append([entry.get("label"), *values])
        for column_index in range(1, len(columns) + 2):
            letter = chr(ord("A") + column_index - 1)
            ws_financials.column_dimensions[letter].width = 18
        for row in ws_financials.iter_rows(min_row=2, min_col=2, max_col=len(columns) + 1):
            for cell in row:
                cell.number_format = "#,##0.00"

    ws_sources = wb.create_sheet("Sources")
    ws_sources.append(("Citation", "Link", "Details"))
    
    # Add comprehensive sources with clickable links
    source_rows = _collect_source_rows(payload.get("sources", []))
    for display_text, url, full_text in source_rows:
        row_num = ws_sources.max_row + 1
        
        # Add display text in column A
        ws_sources.cell(row=row_num, column=1, value=display_text)
        
        # Add clickable hyperlink in column B
        if url:
            cell = ws_sources.cell(row=row_num, column=2, value="Click here")
            cell.hyperlink = url
            cell.font = Font(color="0563C1", underline="single")  # Blue underlined
            cell.style = "Hyperlink"
            
            # Add full URL text in column C for reference
            ws_sources.cell(row=row_num, column=3, value=url)
        else:
            ws_sources.cell(row=row_num, column=2, value="N/A")
            ws_sources.cell(row=row_num, column=3, value="No link available")
    
    # Set column widths
    ws_sources.column_dimensions["A"].width = 60  # Citation text
    ws_sources.column_dimensions["B"].width = 15  # Link
    ws_sources.column_dimensions["C"].width = 80  # Full URL
    
    # Format cells
    for row in ws_sources.iter_rows(min_row=2, max_col=3):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    series_map = payload.get("kpi_series") or {}
    if series_map:
        ws_trends = wb.create_sheet("Trends")
        ws_trends.append(("Metric", "Year", "Value"))
        for metric_id, series in series_map.items():
            label = metric_id
            for kpi in payload.get("kpi_summary", []):
                if kpi.get("id") == metric_id or kpi.get("label") == metric_id:
                    label = kpi.get("label") or metric_id
                    break
            years = series.get("years") or []
            values = series.get("values") or []
            for year, value in zip(years, values):
                ws_trends.append((label, year, value))
        ws_trends.column_dimensions["A"].width = 28
        ws_trends.column_dimensions["B"].width = 12
        ws_trends.column_dimensions["C"].width = 18
        for cell in ws_trends["C"][1:]:
            cell.number_format = "#,##0.00"

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_export_payload(engine: "AnalyticsEngine", ticker: str) -> Dict[str, Any]:
    payload = build_cfi_dashboard_payload(engine, ticker)
    if not payload:
        raise ValueError(f"No dashboard payload available for {ticker}.")
    return payload


def generate_dashboard_export(engine: "AnalyticsEngine", ticker: str, fmt: str) -> ExportResult:
    payload = build_export_payload(engine, ticker)
    meta = payload.get("meta", {})
    ticker_label = meta.get("ticker") or ticker
    slug = _safe_slug(ticker_label)
    today = datetime.utcnow().strftime("%Y%m%d")
    format_normalized = (fmt or "").lower()

    if format_normalized in {"pdf"}:
        content = _build_pdf(payload)
        filename = f"BenchmarkOS_{ticker_label}_{today}.pdf"
        return ExportResult(content=content, media_type="application/pdf", filename=filename)
    if format_normalized in {"ppt", "pptx"}:
        content = _build_ppt(payload)
        filename = f"BenchmarkOS_{ticker_label}_{today}.pptx"
        return ExportResult(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=filename,
        )
    if format_normalized in {"xlsx", "excel"}:
        content = _build_excel(payload)
        filename = f"BenchmarkOS_{ticker_label}_{today}.xlsx"
        return ExportResult(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )
    raise ValueError(f"Unsupported export format '{fmt}'.")
