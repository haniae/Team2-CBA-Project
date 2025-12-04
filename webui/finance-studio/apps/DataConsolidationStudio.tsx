// Data Consolidation Studio app component

import React, { useState } from 'react';
import { getPLConsolidation } from '../api';
import type { SourceConfig, ConsolidationFilters, ConsolidatedRow } from '../types';

const DATA_SOURCES = [
  { id: 'excel', label: 'Excel / CSV' },
  { id: 'edgar', label: 'EDGAR / SEC filings' },
  { id: 'internal_db', label: 'Internal SQL DB' },
  { id: 'google_sheets', label: 'Google Sheets' },
];

const YEARS = ['2022', '2023', '2024', '2025'];
const ENTITIES = ['Global', 'EMEA', 'Americas', 'APAC'];

export function DataConsolidationStudio() {
  const [selectedSources, setSelectedSources] = useState<string[]>(['excel']);
  const [selectedYear, setSelectedYear] = useState('2025');
  const [selectedEntities, setSelectedEntities] = useState<string[]>(['Global']);
  const [granularity, setGranularity] = useState<'Monthly' | 'Quarterly' | 'Yearly'>('Quarterly');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consolidatedData, setConsolidatedData] = useState<ConsolidatedRow[] | null>(null);
  const [kpis, setKpis] = useState<{
    totalRevenue: number;
    grossProfitPct: number;
    ebitdaPct: number;
  } | null>(null);

  const handleTransform = async () => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = selectedSources.map((id) => ({
        source_id: id,
        connection_info: {},
      }));

      const filters: ConsolidationFilters = {
        entities: selectedEntities,
        periods: granularity === 'Quarterly' 
          ? [`${selectedYear}-Q1`, `${selectedYear}-Q2`, `${selectedYear}-Q3`, `${selectedYear}-Q4`]
          : granularity === 'Monthly'
          ? Array.from({ length: 12 }, (_, i) => `${selectedYear}-${String(i + 1).padStart(2, '0')}`)
          : [selectedYear],
        scenarios: ['Actual', 'Budget', 'Forecast'],
      };

      const result = await getPLConsolidation({ sources, filters, view: 'pl' });
      setConsolidatedData(result.rows);

      // Calculate KPIs
      const revenueRows = result.rows.filter((r) => r.lineItem === 'Revenue');
      const grossProfitRows = result.rows.filter((r) => r.lineItem === 'Gross Profit');
      const ebitdaRows = result.rows.filter((r) => r.lineItem === 'EBITDA');

      const totalRevenue = revenueRows.reduce((sum, r) => sum + (r.actual || 0), 0);
      const totalGrossProfit = grossProfitRows.reduce((sum, r) => sum + (r.actual || 0), 0);
      const totalEbitda = ebitdaRows.reduce((sum, r) => sum + (r.actual || 0), 0);

      setKpis({
        totalRevenue,
        grossProfitPct: totalRevenue > 0 ? (totalGrossProfit / totalRevenue) * 100 : 0,
        ebitdaPct: totalRevenue > 0 ? (totalEbitda / totalRevenue) * 100 : 0,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to consolidate data');
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (sourceId: string) => {
    setSelectedSources((prev) =>
      prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId]
    );
  };

  const toggleEntity = (entity: string) => {
    setSelectedEntities((prev) =>
      prev.includes(entity) ? prev.filter((e) => e !== entity) : [...prev, entity]
    );
  };

  const getVarianceColor = (variancePct?: number): string => {
    if (!variancePct) return '';
    return variancePct > 0 ? 'var(--color-success)' : 'var(--color-error)';
  };

  // Group rows by line item and period
  const groupedRows = consolidatedData
    ? consolidatedData.reduce((acc, row) => {
        const key = `${row.lineItem}-${row.period}`;
        if (!acc[key]) acc[key] = [];
        acc[key].push(row);
        return acc;
      }, {} as Record<string, ConsolidatedRow[]>)
    : {};

  return (
    <div className="data-consolidation-studio">
      <div className="consolidation-config-panel">
        <h2>Source Selection & Configuration</h2>
        
        <div className="config-section">
          <label>Data Sources</label>
          <div className="multi-select-buttons">
            {DATA_SOURCES.map((source) => (
              <button
                key={source.id}
                className={`multi-select-button ${selectedSources.includes(source.id) ? 'selected' : ''}`}
                onClick={() => toggleSource(source.id)}
              >
                {source.label}
              </button>
            ))}
          </div>
        </div>

        <div className="config-section">
          <label>Period</label>
          <div className="period-selector">
            <select value={selectedYear} onChange={(e) => setSelectedYear(e.target.value)}>
              {YEARS.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
            <div className="granularity-toggle">
              {(['Monthly', 'Quarterly', 'Yearly'] as const).map((gran) => (
                <button
                  key={gran}
                  className={granularity === gran ? 'active' : ''}
                  onClick={() => setGranularity(gran)}
                >
                  {gran}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="config-section">
          <label>Entities</label>
          <div className="multi-select-buttons">
            {ENTITIES.map((entity) => (
              <button
                key={entity}
                className={`multi-select-button ${selectedEntities.includes(entity) ? 'selected' : ''}`}
                onClick={() => toggleEntity(entity)}
              >
                {entity}
              </button>
            ))}
          </div>
        </div>

        <button
          className="transform-button"
          onClick={handleTransform}
          disabled={loading || selectedSources.length === 0}
        >
          {loading ? 'Transforming...' : 'Transform & Consolidate'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {kpis && (
        <div className="kpi-banner">
          <div className="kpi-card">
            <div className="kpi-label">Total Revenue</div>
            <div className="kpi-value">
              ${(kpis.totalRevenue / 1000000).toFixed(2)}M
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Gross Profit %</div>
            <div className="kpi-value">{kpis.grossProfitPct.toFixed(1)}%</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">EBITDA %</div>
            <div className="kpi-value">{kpis.ebitdaPct.toFixed(1)}%</div>
          </div>
        </div>
      )}

      {consolidatedData && (
        <div className="consolidation-results">
          <h2>P&L Consolidation Results</h2>
          <div className="pl-grid-container">
            <table className="pl-grid">
              <thead>
                <tr>
                  <th>Line Item</th>
                  {Array.from(new Set(consolidatedData.map((r) => r.period).filter(Boolean))).map(
                    (period) => (
                      <th key={period} colSpan={3}>
                        {period}
                      </th>
                    )
                  )}
                </tr>
                <tr>
                  <th></th>
                  {Array.from(new Set(consolidatedData.map((r) => r.period).filter(Boolean))).map(
                    (period) => (
                      <React.Fragment key={period}>
                        <th>Actual</th>
                        <th>Forecast</th>
                        <th>Variance %</th>
                      </React.Fragment>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {Object.entries(groupedRows).map(([key, rows]) => {
                  const firstRow = rows[0];
                  const isParent = firstRow.level === 'parent';
                  return (
                    <tr
                      key={key}
                      className={`pl-row ${isParent ? 'parent-row' : 'child-row'}`}
                    >
                      <td className="line-item-cell" style={{ paddingLeft: isParent ? '0' : '24px' }}>
                        {firstRow.lineItem}
                      </td>
                      {Array.from(
                        new Set(consolidatedData.map((r) => r.period).filter(Boolean))
                      ).map((period) => {
                        const periodRows = rows.filter((r) => r.period === period);
                        const row = periodRows[0] || firstRow;
                        return (
                          <React.Fragment key={period}>
                            <td>${((row.actual || 0) / 1000).toFixed(0)}K</td>
                            <td>${((row.forecast || 0) / 1000).toFixed(0)}K</td>
                            <td
                              style={{
                                color: getVarianceColor(row.variancePct),
                                backgroundColor: row.variancePct
                                  ? `${getVarianceColor(row.variancePct)}20`
                                  : 'transparent',
                              }}
                            >
                              {row.variancePct ? `${row.variancePct > 0 ? '+' : ''}${row.variancePct.toFixed(1)}%` : '-'}
                            </td>
                          </React.Fragment>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

