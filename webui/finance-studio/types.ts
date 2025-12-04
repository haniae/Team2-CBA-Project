// Finance Studio TypeScript types

export type FinanceView = 'pl' | 'variance' | 'three-statement' | 'visual';

export interface SourceConfig {
  source_id: string;
  connection_info: Record<string, any>;
}

export interface ConsolidationFilters {
  entities?: string[];
  periods?: string[];
  scenarios?: string[];
}

export interface ConsolidatedRow {
  lineItem: string;
  entity?: string;
  period?: string;
  scenario?: string;
  actual?: number;
  budget?: number;
  forecast?: number;
  varianceAbs?: number;
  variancePct?: number;
  level?: 'parent' | 'child' | 'grandchild';
}

export interface ConsolidatedTable {
  view: FinanceView;
  periodLabel?: string;
  rows: ConsolidatedRow[];
}

export interface ConsolidationRequest {
  sources: SourceConfig[];
  filters: ConsolidationFilters;
  view: string;
}

export interface VisualizationData {
  kpis: {
    total_revenue: number;
    gross_profit: number;
    gross_profit_pct: number;
    ebitda: number;
    ebitda_pct: number;
  };
  entity_breakdown: Record<string, { revenue: number; gross_profit: number }>;
  periods: string[];
  raw_data: ConsolidatedTable;
}

export interface DrilldownTransaction {
  date: string;
  entity: string;
  cost_center: string;
  account: string;
  amount: number;
  description: string;
}

export type FinanceStudioAppId =
  | 'data-consolidation'
  | 'board-reports'
  | 'visualization'
  | 'three-statement'
  | 'entity-rollup'
  | 'export-bridge';

