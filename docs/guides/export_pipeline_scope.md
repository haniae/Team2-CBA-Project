# Executive Export Pipeline Scope

> Framework for Phase 1–3 deliverables surfaced on 2025-10-19.

## Goals

- Automate generation of presentation-ready one-pagers (PDF) for Phase 1.
- Support interactive dashboard exports (PDF + PPT) with peer selections for Phase 2.
- Deliver full analytical workbooks (Excel) with linked data, formulas, and provenance for Phase 3.
- Maintain repeatable, auditable pipelines that align with the KPI standardisation catalogue.

## Deliverable Matrix

| Phase | Artifact | Core Contents | Generation Notes |
|-------|----------|---------------|------------------|
| Phase 1 | PDF executive summary (1 page) | KPI scorecard (top 5 KPIs), valuation snapshot, headline insights | Render HTML template server-side via headless Chromium; embed source footnotes; use current CFI payload. |
| Phase 2 | Interactive dashboard export | Multi-page PDF/PPT capturing drill-down views + selected peer group | Capture chart states per peer selection; integrate Plotly image export; append appendix with methodology. |
| Phase 2 | Peer comparison deck (PPT) | Benchmark charts, football field, KPI trend slides | Use python-pptx with templated layouts; inject SVG/PNG assets from Plotly exports; include commentary slots. |
| Phase 3 | Excel analytical workbook | Raw financial statements, KPI calc tabs, assumptions sheet, source links | Build via xlsxwriter/openpyxl; structure tabs `Summary`, `KPI_Calcs`, `Financials`, `Source_Log`; include named ranges for formulas. |
| Phase 3 | Data room package | ZIP: Excel workbook + JSON payload + source manifest | Generate after Excel worksheet; manifest includes timestamps, filing references. |

## Pipeline Architecture

1. **Render Service (HTML → PDF/PNG)**  
   - Use Playwright/Chromium in headless mode.  
   - Inputs: dashboard route + query params (ticker, peer_group, drilldown state).  
   - Outputs: PDF, PNG thumbnails for embedding.

2. **Deck Builder (PPT)**  
   - Template-driven using python-pptx.  
   - Slide types: Cover, KPI Grid, Trendlines, Valuation, Appendix.  
   - Media assets sourced from Render Service (ensures visual parity).

3. **Workbook Generator (Excel)**  
   - Library: xlsxwriter (fast write) + openpyxl (post-format) for formula insertion.  
   - Data feed: same JSON payload as dashboard + raw statement tables from database.  
   - Include macros? Optional future step (Phase 3.5) for refresh buttons.

4. **Manifest & Packaging**  
   - YAML/JSON manifest capturing ticker, peers, data timestamp, KPI list, file hashes.  
   - Archive as ZIP for download + store in S3 bucket (naming convention `{ticker}_{yyyymmdd}_exec_pack.zip`).

## Implementation Backlog

1. Establish `/export` service module in backend with pluggable renderers (`pdf`, `ppt`, `xlsx`).  
2. Create Jinja/React server templates mirroring current dashboard layout for consistent styling.  
3. Wire long-running tasks to existing task queue (Celery/RQ) if generation exceeds synchronous limits.  
4. Provide CLI wrappers under `scripts/export/` for regression testing and CI validation.  
5. Define monitoring: log render duration, connection to data freshness flags, capture Playwright crashes.  
6. Security: redline sensitive data via export filters; ensure OAuth/session gating for S3 downloads.  
7. QA checklist: pixel diff for PDFs, formula validation in Excel, hyperlink verification for source links.  

## Dependencies & Risk

- **Dependencies**: Plotly static image export, Chromium runtime, python-pptx/xlsxwriter, KPI dataset completeness.  
- **Risks**: Large peer groups increase render times; maintaining parity between interactive dashboard and static exports; file size growth for Excel when embedding source tables.  
- **Mitigations**: Limit peers per export (max 5), cache rendered images, stream workbook writing to avoid memory spikes.
