# CFI Dashboard Interaction Requirements

> Drafted to prioritise Phase 2 feature work requested on 2025-10-19.

## Objectives

- Enable analysts to drill from headline KPIs into underlying financial statements, historical trendlines, and source citations without leaving the dashboard.
- Allow configurable peer groups so users can benchmark against saved universes or ad hoc selections.
- Keep the Phase 1 read-only experience intact while extending the payload so Phase 2 front-end work can iterate without further backend churn.

## Interaction Model

| Area | Interaction | Description | Data contract additions |
|------|-------------|-------------|-------------------------|
| KPI scorecard | KPI drill-down | Click a KPI to load its time-series, calculation context, and source lineage inside a side panel. | `interactions.kpis.drilldowns[*]` |
| Financial charts | Series focus | Toggle specific tickers/segments and swap between absolute vs % change. | `interactions.charts.controls` |
| Peer configuration | Peer selector | Dropdown + multi-select to choose default peer list, saved sets, or manual tickers (up to 5). | `peer_config` block |
| Source traceability | View sources | Inline icon or context menu surfaces EDGAR links / ingestion metadata. | `interactions.sources` |

### Drill-down behaviour

- **Modal host**: Embed in dashboard surface (`cfi-dashboard__drilldown-host`), with payload referencing reusable layouts (`metric`, `table`, `rich_text`, etc.).
- **Data path**: Each KPI maps to a `drilldown` definition:
  ```json
  {
    "id": "revenue_cagr",
    "title": "Revenue CAGR — Detail",
    "layout": ["headline", "sparkline", "explanation", "sources"],
    "data_refs": {
      "series": "series.revenue_cagr",
      "explanation": "nlg.revenue_cagr"
    }
  }
  ```
- **Payload expectations**: backend guarantees referenced `data_refs` exist or hides the interaction.

### Peer selector requirements

- **Default**: Use analytics engine benchmark label (e.g. `S&P 500 Avg`). Provide at least one saved peer set.
- **Contract**:
  ```json
  {
    "default_peer_group": "mega_cap_tech",
    "available_peer_groups": [
      {"id": "mega_cap_tech", "label": "Mega-cap Tech", "tickers": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]},
      {"id": "custom", "label": "Custom", "tickers": []}
    ],
    "max_peers": 5
  }
  ```
- **Front-end stub**: populate selector UI but degrade gracefully by using payload defaults if selector absent.

## Data Contract Updates

- Additional top-level keys (see implementation in `dashboard_utils.py`):
  - `interactions`: `kpis`, `charts`, `sources` metadata.
  - `peer_config`: definitions driving selectors and shareable URLs.
- Extended `series` block to include raw KPI trendlines when drill-down references them.

## Next steps

1. Implement selector + drilldown containers in `cfi_dashboard.html` (Phase 2).
2. Build fetch handlers in `app.js` to request extended payload when users change peers.
3. Wire backend endpoints to honour `peer_group` query param and return scoped metrics.
