---
title: Competitive Benchmarking Agent (CBA) – Product Design Specification
version: 1.1
last_updated: 2025-10-12
status: Draft
owners:
  - name: BenchmarkOS PMO
    email: pmo@finanlyzeos.ai
contributors:
  - Engineering: Platform, Data, ML, Web
  - Product: FP&A, IR, CorpDev liaisons
  - Compliance: Risk & Controls
---

## 1. Executive Summary
The Competitive Benchmarking Agent (CBA) delivers investor-grade peer comparisons in minutes by automating ingestion, normalization, analysis, and presentation of SEC filings, market data, and earnings transcripts. The platform enforces a standardized KPI dictionary, guarantees click-through lineage to primary sources, and supports high-urgency workflows for FP&A, Investor Relations, Corporate Strategy, Consulting, and Banking teams. This specification hardens the existing PDS by detailing scope, architecture, data governance, success metrics, and release planning required to ship an institutional-grade MVP with a clean upgrade path toward multi-dimensional benchmarking.

### Objectives
1. Cut peer-comparison cycle time from days to <5 minutes with on-demand analysis packs.
2. Achieve ≥95% metric accuracy compared with hand-audited reference sets while providing statistical confidence intervals.
3. Provide end-to-end auditability (source, transformation, formula, and policy context) to meet SOX and regulatory expectations.
4. Ship reusable UI components for dashboards, executive summaries, and export formats that integrate with enterprise workflows.
5. Establish a scalable technical foundation for expanding coverage to Top-100 and Fortune 500 cohorts, including future “what-if” scenario modeling.

## 2. Scope Definition

### 2.1 In-Scope (MVP – “Phase 1”)
- Coverage: Top 5 companies per peer group (expands to Top 10 in Phase 2), limited to 10-K and 10-Q filings plus end-of-day market prices.
- KPI Dictionary (First 5 metrics):
  - Revenue CAGR (3-year).
  - EBITDA margin (TTM).
  - ROIC (standardized numerator/denominator).
  - EV/EBITDA.
  - Free Cash Flow (FCF) margin.
- Data ingestion from SEC EDGAR, Yahoo Finance (historical/pricing), and transcript repository (structured text).
- Normalization rules for GAAP/IFRS differences, share-based compensation adjustments, and extraordinary items exclusions.
- Audit graph: linking each computed metric to original filing section, timestamp, and transformation lineage.
- Delivery outputs:
  - Web executive dashboard with drill-ins.
  - One-page PDF executive summary (rendered via templated service).
  - JSON/CSV export with source references.
- User Personas: FP&A Analyst, IR Manager, CorpDev Associate.
- Authentication via corporate SSO (OpenID Connect); roles: Viewer, Editor, Admin.
- Alerting: Email and Slack notifications for filing updates and >10% change in selected metrics.

### 2.2 Out-of-Scope (MVP)
- Real-time intraday market streaming (Phase 2+).
- Non-SEC jurisdictions (e.g., SEDAR, TSE) – backlog item.
- Scenario modeling, Monte Carlo, and “what-if” valuations (Phase 3).
- Detailed Excel workbook generation and PowerPoint templates (Phase 2/3).
- Segment/geo/product-level benchmarking (future expansion).
- Fortune 500 coverage (Phase 3).

### 2.3 Assumptions & Dependencies
- Access to SEC EDGAR API without rate-throttling issues (fallback scraping handled).
- Yahoo Finance licensing for commercial usage is secured.
- Corporate SSO integration is approved by IT security.
- Dedicated compliance reviewer assigned for audit graph validation.

## 3. Competitive Positioning
| Capability | CBA | Generic LLM | Bloomberg / FactSet |
|------------|-----|-------------|----------------------|
| KPI standardization | ✅ Single dictionary & audit rules | ❌ inconsistent, prompt-driven | ⚠️ multiple templates, manual |
| Source traceability | ✅ Click-through, audited graph | ❌ references missing | ⚠️ manual research workflow |
| Turnaround time | Minutes | Minutes (but low fidelity) | Hours/days (manual assembly) |
| Workflow integration | SSO, exports, notifications | Minimal | High licensing cost, manual prep |
| Coverage expansion | Programmatic | Prompt-based | Expensive seat-based |

## 4. Data Strategy

### 4.1 Source Inventory & SLAs
| Source | Data | Frequency | SLA | Connector |
|--------|------|-----------|-----|-----------|
| SEC EDGAR | 10-K, 10-Q (XBRL + HTML) | Hourly poll | 30 min ingestion | SEC API + S3 cache |
| Yahoo Finance | Prices, multiples | Daily close | 15 min ingestion | REST API |
| Transcripts | Earnings call text | Within 2 hours of release | 60 min ingestion | Vendor SFTP |
| Internal Catalog | KPI dictionary, peer sets | On update | Immediate | Postgres config |

Data is staged in raw object storage (S3) with metadata captured in Postgres before transformation. All fetch jobs emit event metadata (source, timestamp, checksum) to the audit graph.

### 4.2 Normalization & KPI Rulebook
Create a “KPI Rules” table:
```
id | metric_key | formula | required_fields | adjustments | validation | owner | last_reviewed
```
- Formula describes canonical SQL/DBT/transform expression.
- Adjustments detail GAAP/IFRS alignment, e.g., “exclude stock-based compensation from operating expenses for EBITDA.”
- Validation includes expected ranges and comparative tests (e.g., ratio vs. sector median).
- Owner accountable for updates.

### 4.3 Accuracy & QA Plan
- Build “golden dataset” covering 50 company-period pairs audited manually.
- Automated acceptance: mean absolute percentage error (MAPE) < 5% for all MVP metrics.
- Statistical confidence intervals calculated using bootstrap on historical data where applicable.
- Introduce sampling QA: 10 random metrics per week flagged for manual review; track pass/fail in QA log (Postgres table `qa_metric_review`).

### 4.4 Data Retention & Versioning
- Raw filings retained indefinitely (regulatory requirement).
- Processed tables versioned by effective date + ingestion batch id.
- Metric outputs stored with semantic version: `metric_version` increments on formula change; older versions accessible for audit.
- Deletion policy: derived caches older than 24 months pruned, except for audit retention flagged records.

## 5. Architecture Overview

### 5.1 High-Level Diagram (described)
1. **Ingestion Layer**: Async workers (Celery) pull filings/prices → push to raw S3 + Postgres metadata.
2. **Normalization Pipeline**: DBT or Pandas + SQL transformations executed via orchestration service; outputs persisted to `analytics` schema.
3. **Audit Graph Service**: Neo4j or graph-compatible Postgres extension storing node/edge lineage.
4. **Metric Engine**: Python service using `analytics_engine.py`; writes metric snapshots, confidence bounds, and annotations.
5. **API Layer**: FastAPI (`web.py`) serves REST + streaming endpoints, including `/metrics`, `/audit`, `/compare`, `/chat`.
6. **UI (webui)**: React/Vite (Phase 2) + static assets (Phase 1) delivering dashboards, chat, exports.
7. **Notification Service**: Event-driven (AWS SNS/SES or Slack webhook) triggered by metric deltas or new filings.
8. **Storage**: Postgres (primary), S3 (object storage), Redis (caching), Neo4j/S3 for audit graph, Elastic for search.

### 5.2 Technology Stack Choices
- **Backend**: Python 3.11, FastAPI, Celery, DBT-lite (or custom SQL pipeline).
- **Database**: PostgreSQL 15 with Timescale extension for time-series metrics.
- **Object Storage**: AWS S3 (development can use MinIO).
- **Search**: OpenSearch for transcript retrieval.
- **Queue**: RabbitMQ or Redis Streams.
- **UI**: React 18 + TypeScript (Phase 2), existing vanilla JS for Phase 1.
- **Authentication**: Auth0 with OIDC; roles managed via JWT claims.
- **Infrastructure**: Terraform-managed AWS (ECS Fargate, RDS). Local dev uses Docker Compose.

### 5.3 API Contracts
- `/metrics/{peer_set}`: GET – returns metric table with metadata: `value`, `ci_lower`, `ci_upper`, `source_node`.
- `/audit/{metric_id}`: GET – adjacency list showing lineage nodes.
- `/ingestion/status`: GET – pipeline health.
- `/alerts/register`: POST – subscribe to triggers.
- Message schemas documented in `docs/api_contracts.md` (to be created).

## 6. Audit & Compliance

### 6.1 Audit Graph Specification
Node types: `SourceDocument`, `Extraction`, `Normalization`, `Metric`, `Adjustment`, `Export`.
Edges encode `derived_from`, `adjusted_by`, `version_of`.
Each node stores:
- `source_reference` (URL, filing accession, section id).
- `timestamp`, `version`, `actor` (service/user), `checksum`.
- Human-readable `explanation`.

### 6.2 Controls & Policies
- **Access Control**: RBAC enforced by API; Admin can grant peer-group edit rights.
- **Change Management**: KPI dictionary edits go through approval queue (dual control). Changes recorded in `config_kpi_changelog` table with diff.
- **Logging**: Centralized structured logs (JSON) shipped to CloudWatch/OpenSearch; retention ≥ 2 years.
- **SOX Alignment**: Documented controls: Data completeness, accuracy checks, user access reviews. Quarterly attestation cycle.
- **Incident Response**: On failed QA or data inconsistency, system flags and auto-notifies compliance lead with rollback options.

## 7. User Experience

### 7.1 Persona Workflows
1. **FP&A Analyst**
   - Trigger: earnings prep.
   - Flow: select peer set → review dashboard → export PDF → send to CFO.
   - Needs: metric trends, variance vs. plan, drill-down to filing snippet.
2. **IR Manager**
   - Trigger: investor Q&A.
   - Flow: monitor alerts → open transcript summary → respond with sourced answer.
   - Needs: real-time alerts, quick lookups, traceability.
3. **CorpDev Associate**
   - Trigger: acquisition diligence.
   - Flow: custom peer grouping → scenario workbook (Phase 2/3) → share with team.
   - Needs: flexible filtering, historical trends, consistent adjustments.

### 7.2 UI Requirements (Phase 1)
- **Dashboard**: KPI cards, trend charts (sparkline or slopegraph), table comparison, highlight deltas > threshold.
- **Audit Drawer**: when selecting a metric, show lineage path with clickable node list (modal).
- **Chat Interface**: Streaming responses with citations; auto-scroll anchor; bubble design consistent with brand.
- **Exports**: Buttons for PDF/CSV; PDF generated via backend service with template referencing brand guidelines.

### 7.3 Accessibility & UX Standards
- WCAG 2.1 AA compliance: contrast ratios, keyboard navigation, screen reader labels (`aria-*` attributes).
- Localization: copy stored in i18n files (English default; infrastructure ready for localization).
- Performance: page load < 2.5s on 3G, interactive chat streaming <200ms to first token.

## 8. Notifications & Alerts
- Alert types:
  1. Filing ingested for tracked peers.
  2. Metric delta beyond configured threshold (default 10% QoQ).
  3. Data quality issue (failed QA check).
- Delivery channels: Email (SES) and Slack (webhook). Later phases add Teams/Webhooks.
- User preferences stored per role; Admin can enforce mandatory alerts.

## 9. Testing & QA Strategy

| Layer | Tests | Tooling | Frequency |
|-------|-------|---------|-----------|
| Unit | Metric formulas, transformers | PyTest, Hypothesis | CI on PR |
| Integration | Ingestion pipelines, API endpoints | PyTest + Docker Compose environment | Nightly |
| Data QA | Golden dataset comparison, drift detection | Custom scripts | Nightly + on demand |
| UI | Component snapshots, e2e (dashboard, chat) | Playwright | Release branch |
| Performance | Load testing (100 concurrent sessions) | Locust | Pre-release |
| Security | SAST, dependency scans | GitHub Advanced Security | On push |

QA sign-off requires green pipeline, manual spot-check by analytics QA, and compliance review of audit graph sampling.

## 10. Roadmap & Milestones

### Phase 0 (Weeks 0-2)
- Finalize KPI dictionary v1.
- Set up infrastructure (Postgres, S3, Celery workers).
- Implement ingestion scaffolding.

### Phase 1 (Weeks 3-8) – MVP
- Deliver Top-5 coverage, 5 metrics, audit graph MVP.
- Release dashboard + PDF export.
- Accuracy target achieved & documented.

### Phase 2 (Weeks 9-14)
- Expand to Top-10 coverage, add 5 more metrics (e.g., ROA, ROE, EV/EBITDA, TSR).
- Deploy interactive React front-end.
- Introduce scenario planning backlog design.
- Add Excel workbook export (beta).

### Phase 3 (Weeks 15-22)
- Fortune 100 coverage, 20+ metrics.
- Integrate real-time market feeds, transcripts search.
- Implement what-if analysis engine.
- Provide PowerPoint template generation.

### Phase 4 (Post-MVP Enhancements)
- Segment/geo/product-level analytics.
- Historical trend analysis across ≥5 years.
- Advanced AI assistants for scenario modeling.

## 11. Resourcing & Budget (MVP)
| Role | Headcount | Duration | Notes |
|------|-----------|----------|-------|
| Product Lead | 1 FTE | Full project | Owner of roadmap, stakeholder alignment |
| Engineering Lead | 1 FTE | Full project | Oversees backend & infrastructure |
| Data Engineer | 2 FTE | Phases 0-2 | Ingestion pipelines, normalization |
| ML Engineer | 1 FTE | Phases 1-3 | NLP, metric accuracy, LLM integration |
| Frontend Engineer | 1 FTE | Phases 1-2 | Dashboard, chat experience |
| Compliance Specialist | 0.5 FTE | Phase 1-3 | Audit trail validation |
| QA Analyst | 0.5 FTE | Phase 1-3 | Manual testing, golden datasets |

Estimate infrastructure costs: ~$6k/month (AWS dev + staging), rising to ~$12k/month with production scaling.

## 12. Success Metrics & KPIs
- **Cycle Time**: ≤5 minutes from data refresh to publishable pack.
- **Accuracy**: ≥95% metrics within ±5% of audited values.
- **Adoption**: 80% of FP&A/IR teams using dashboard weekly within 60 days.
- **Audit Completeness**: 100% metrics with lineage nodes (no orphan data).
- **Alert Engagement**: >60% of alerts acknowledged within 2 hours.
- **Satisfaction**: NPS ≥ +35 from pilot users.

## 13. Launch Plan
- **Beta Program (Weeks 7-8)**: Enroll 3 pilot clients (2 internal, 1 external). Collect feedback via structured surveys and weekly check-ins.
- **Training**: 90-minute enablement session; distribute how-to guides and quick reference cards.
- **Support**: Dedicated Slack/Teams channel + email queue monitored by support engineer (response SLA: 4 business hours).
- **Post-launch Review**: 30-day adoption checkpoint and metrics review; iterate backlog.

## 14. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Data feed throttling | Delays ingestion | Implement backoff, caching; acquire paid API keys |
| KPI definition disputes | Slows rollout | Establish governance committee, maintain changelog |
| Accuracy below target | Credibility risk | Expand QA sampling, add manual override workflow |
| Compliance audit failure | Regulatory risk | Run readiness assessments, document controls |
| Scope creep | Delays MVP | Enforce stage gate reviews, explicit change control |

## 15. Appendices
### 15.1 KPI Dictionary (v1.0 Extract)
| Metric | Formula | Notes |
|--------|---------|-------|
| Revenue CAGR | `((Revenue_t / Revenue_t-3)^(1/3)) - 1` | Uses normalized revenue; excludes acquisitions with restatements. |
| EBITDA Margin | `Normalized EBITDA / Revenue` | Adjust for stock-based comp, restructuring charges. |
| ROIC | `(NOPAT) / (Invested Capital)` | Average invested capital over two-period window. |
| EV/EBITDA | `(Market Cap + Net Debt) / EBITDA` | Market Cap from Yahoo Finance; Net Debt from filings. |
| FCF Margin | `Free Cash Flow / Revenue` | FCF = CFO - Capex; CFO derived from cash flow statement. |

Complete dictionary maintained in Postgres `kpi_rules` table and exported to `docs/kpi_dictionary.csv`.

### 15.2 Glossary
- **CBA**: Competitive Benchmarking Agent.
- **KPI**: Key Performance Indicator.
- **Audit Graph**: Graph-based lineage mapping data provenance.
- **FP&A**: Financial Planning & Analysis.
- **TSR**: Total Shareholder Return.
- **SOX**: Sarbanes-Oxley Act.

### 15.3 References
- EY benchmarking validation report (2025-07).
- FI Consulting pilot outcomes (2025-08).
- Capital One internal POC feedback (2025-09).
- Mizuho research partnership agreement (2025-09).

---
**Next Actions**  
- Product lead to socialize this PDS with stakeholders for sign-off.  
- Engineering to translate architecture into detailed implementation tickets.  
- Compliance to validate audit graph and controls checklist before MVP freeze.
