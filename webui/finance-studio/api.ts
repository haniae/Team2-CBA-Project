// Finance Studio API client

import type {
  ConsolidationRequest,
  ConsolidatedTable,
  VisualizationData,
  DrilldownTransaction,
} from './types';

const API_BASE = window.API_BASE || '';

export async function consolidateData(
  request: ConsolidationRequest
): Promise<ConsolidatedTable> {
  const response = await fetch(`${API_BASE}/api/finance-studio/consolidate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Consolidation failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getPLConsolidation(
  request: ConsolidationRequest
): Promise<ConsolidatedTable> {
  const response = await fetch(`${API_BASE}/api/finance-studio/pl-consolidation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`P&L consolidation failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getVarianceAnalysis(
  request: ConsolidationRequest
): Promise<ConsolidatedTable> {
  const response = await fetch(`${API_BASE}/api/finance-studio/variance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Variance analysis failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getThreeStatementData(
  request: ConsolidationRequest,
  statementType: string = 'pl'
): Promise<ConsolidatedTable> {
  const response = await fetch(
    `${API_BASE}/api/finance-studio/three-statement?statement_type=${statementType}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    }
  );
  if (!response.ok) {
    throw new Error(`Three-statement data failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getVisualizationData(
  request: ConsolidationRequest
): Promise<VisualizationData> {
  const response = await fetch(`${API_BASE}/api/finance-studio/visualizations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Visualization data failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getDrilldownTransactions(
  lineItem: string,
  entity?: string,
  period?: string,
  statementType: string = 'pl',
  scenario?: string
): Promise<DrilldownTransaction[]> {
  const params = new URLSearchParams({
    line_item: lineItem,
    statement_type: statementType,
  });
  if (entity) params.append('entity', entity);
  if (period) params.append('period', period);
  if (scenario) params.append('scenario', scenario);

  const response = await fetch(
    `${API_BASE}/api/finance-studio/drilldown?${params.toString()}`
  );
  if (!response.ok) {
    throw new Error(`Drilldown failed: ${response.statusText}`);
  }
  const data = await response.json();
  return data.transactions || [];
}

export async function exportData(
  request: ConsolidationRequest,
  format: 'excel' | 'csv' = 'csv'
): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/api/finance-studio/export?format=${format}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    }
  );
  if (!response.ok) {
    throw new Error(`Export failed: ${response.statusText}`);
  }
  return response.blob();
}

