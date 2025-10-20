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
from pptx.util import Inches, Pt
from .dashboard_utils import build_cfi_dashboard_payload


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
        return "—"
    return f"{number * 100:.1f}%"


def _format_multiple(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:.1f}×"


def _format_currency(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
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
        return "—"
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
    limit: int = 20,
) -> List[Tuple[str, str, str]]:
    rows: List[Tuple[str, str, str]] = []
    for entry in list(sources or [])[:limit]:
        label = entry.get("label") or entry.get("metric") or "Metric"
        period = entry.get("period") or ""
        source = entry.get("source") or ""
        rows.append((label, period, source))
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
    rec = meta.get("recommendation") or "—"
    target_price = _format_currency(meta.get("target_price"))
    scenario = meta.get("scenario") or meta.get("live_scenario") or "Consensus"
    pdf.multi_cell(0, 6, f"Recommendation: {rec} • Target Price: {target_price} • Scenario: {scenario}")
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
            pdf.multi_cell(0, 6, f"- {label}: Market {market} • DCF {dcf} • Comps {comps}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Source Footnotes", ln=1)
    pdf.set_font("Helvetica", "", 10)
    if not sources:
        pdf.multi_cell(0, 5, "Source details unavailable.")
    else:
        for label, period, source in _collect_source_rows(sources):
            line = f"- {label}"
            if period:
                line += f" ({period})"
            if source:
                line += f" — {source}"
            pdf.multi_cell(0, 5, line)

    pdf_output = pdf.output(dest="S").encode("latin1")
    return pdf_output


def _build_ppt(payload: Dict[str, Any]) -> bytes:
    meta = payload.get("meta", {})
    kpis = payload.get("kpi_summary", [])
    sources = payload.get("sources", [])

    presentation = Presentation()

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_slide.shapes.title.text = f"{meta.get('company', 'Dashboard')}"
    subtitle = title_slide.shapes.placeholders[1]
    subtitle.text = f"{meta.get('ticker', '')} • Recommendation: {meta.get('recommendation', '—')} • Target { _format_currency(meta.get('target_price')) }"

    kpi_slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    kpi_slide.shapes.title.text = "KPI Scorecard"
    rows = len(_collect_kpi_rows(kpis)) + 1
    cols = 3
    table = kpi_slide.shapes.add_table(rows, cols, Inches(0.5), Inches(1.5), Inches(9.0), Inches(4.5)).table
    table.columns[0].width = Inches(3.6)
    table.columns[1].width = Inches(2.0)
    table.columns[2].width = Inches(3.0)
    headers = ("Metric", "Value", "Period / Source")
    for col, text in enumerate(headers):
        table.cell(0, col).text = text
        table.cell(0, col).text_frame.paragraphs[0].font.bold = True
    for row_index, (label, value_text, period, source) in enumerate(_collect_kpi_rows(kpis), start=1):
        table.cell(row_index, 0).text = label
        table.cell(row_index, 1).text = value_text
        meta_text = period or ""
        if source:
            meta_text = f"{meta_text} • {source}" if meta_text else source
        table.cell(row_index, 2).text = meta_text

    sources_slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    sources_slide.shapes.title.text = "Source Footnotes"
    bullet_frame = sources_slide.shapes.placeholders[1].text_frame
    bullet_frame.clear()
    source_rows = _collect_source_rows(sources)
    if not source_rows:
        bullet_frame.text = "Source details unavailable."
    else:
        for index, (label, period, source) in enumerate(source_rows):
            paragraph = bullet_frame.add_paragraph() if index else bullet_frame.paragraphs[0]
            text = label
            if period:
                text += f" ({period})"
            if source:
                text += f" — {source}"
            paragraph.text = text
            paragraph.level = 0
            paragraph.font.size = Pt(14)

    buffer = BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


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

    ws_sources = wb.create_sheet("Sources")
    ws_sources.append(("Metric", "Period", "Source", "Last Updated", "Value"))
    for entry in payload.get("sources", []):
        ws_sources.append(
            (
                entry.get("label") or entry.get("metric"),
                entry.get("period"),
                entry.get("source"),
                entry.get("updated_at"),
                entry.get("value"),
            )
        )
    for column in ("A", "B", "C", "D", "E"):
        ws_sources.column_dimensions[column].width = 26
    for row in ws_sources.iter_rows(min_row=2, max_col=5):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True)

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
        filename = f"{slug}-benchmarkos-{today}.pdf"
        return ExportResult(content=content, media_type="application/pdf", filename=filename)
    if format_normalized in {"ppt", "pptx"}:
        content = _build_ppt(payload)
        filename = f"{slug}-benchmarkos-{today}.pptx"
        return ExportResult(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=filename,
        )
    if format_normalized in {"xlsx", "excel"}:
        content = _build_excel(payload)
        filename = f"{slug}-benchmarkos-{today}.xlsx"
        return ExportResult(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )
    raise ValueError(f"Unsupported export format '{fmt}'.")
