// Board-Ready Reports app component

import React, { useState } from 'react';
import { getThreeStatementData, getDrilldownTransactions } from '../api';
import type { SourceConfig, ConsolidationFilters, ConsolidatedRow, DrilldownTransaction } from '../types';

const STATEMENT_TYPES = ['P&L', 'Balance Sheet', 'Cash Flow'];
const SCENARIOS = ['Actual vs Budget', 'Actual vs Forecast', 'Multi-Scenario'];
const PERIODS = ['Year', 'Quarter', 'Custom Range'];

export function BoardReadyReports() {
  const [statementType, setStatementType] = useState('P&L');
  const [scenario, setScenario] = useState('Actual vs Budget');
  const [period, setPeriod] = useState('Quarter');
  const [selectedEntities, setSelectedEntities] = useState<string[]>(['Global']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ConsolidatedRow[] | null>(null);
  const [drilldownData, setDrilldownData] = useState<DrilldownTransaction[] | null>(null);
  const [selectedRow, setSelectedRow] = useState<ConsolidatedRow | null>(null);

  const handleGenerateReport = async () => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: selectedEntities,
        periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
        scenarios: scenario.includes('Budget') ? ['Actual', 'Budget'] : ['Actual', 'Forecast'],
      };

      const statementTypeMap: Record<string, string> = {
        'P&L': 'pl',
        'Balance Sheet': 'balance_sheet',
        'Cash Flow': 'cashflow',
      };

      const result = await getThreeStatementData(
        { sources, filters, view: statementTypeMap[statementType] || 'pl' },
        statementTypeMap[statementType] || 'pl'
      );
      setReportData(result.rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const handleDrilldown = async (row: ConsolidatedRow) => {
    setSelectedRow(row);
    try {
      const transactions = await getDrilldownTransactions(
        row.lineItem,
        row.entity,
        row.period,
        statementType.toLowerCase().replace(' ', '_'),
        row.scenario
      );
      setDrilldownData(transactions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load drilldown');
    }
  };

  const getVarianceColor = (variancePct?: number): string => {
    if (!variancePct) return '';
    return variancePct > 0 ? 'var(--color-success)' : 'var(--color-error)';
  };

  return (
    <div className="board-ready-reports">
      <div className="report-config-bar">
        <div className="config-group">
          <label>Statement Type</label>
          <select value={statementType} onChange={(e) => setStatementType(e.target.value)}>
            {STATEMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <div className="config-group">
          <label>Scenario</label>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {SCENARIOS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="config-group">
          <label>Period</label>
          <select value={period} onChange={(e) => setPeriod(e.target.value)}>
            {PERIODS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <button className="generate-button" onClick={handleGenerateReport} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {reportData && (
        <div className="report-panel">
          <div className="report-header">
            <h2>Board-Ready View – {statementType} – {period}</h2>
          </div>

          <div className="statement-table-container">
            <table className="statement-table">
              <thead>
                <tr>
                  <th>Line Item</th>
                  <th>Actual</th>
                  <th>{scenario.includes('Budget') ? 'Budget' : 'Forecast'}</th>
                  <th>Variance (Abs)</th>
                  <th>Variance %</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reportData.map((row, idx) => (
                  <tr key={idx} className={row.level === 'parent' ? 'parent-row' : 'child-row'}>
                    <td style={{ paddingLeft: row.level === 'child' ? '24px' : '0' }}>
                      {row.lineItem}
                    </td>
                    <td>${((row.actual || 0) / 1000).toFixed(0)}K</td>
                    <td>
                      ${((scenario.includes('Budget') ? row.budget : row.forecast) || 0) / 1000}K
                    </td>
                    <td>${((row.varianceAbs || 0) / 1000).toFixed(0)}K</td>
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
                    <td>
                      <button
                        className="drilldown-button"
                        onClick={() => handleDrilldown(row)}
                      >
                        Drill Down
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {drilldownData && selectedRow && (
        <div className="drilldown-modal">
          <div className="drilldown-content">
            <div className="drilldown-header">
              <h3>
                Drill-down – {selectedRow.lineItem} – {selectedRow.period}
              </h3>
              <button
                className="close-button"
                onClick={() => {
                  setDrilldownData(null);
                  setSelectedRow(null);
                }}
              >
                ×
              </button>
            </div>
            <div className="drilldown-table-container">
              <table className="drilldown-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Entity</th>
                    <th>Cost Center</th>
                    <th>Account</th>
                    <th>Amount</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {drilldownData.map((txn, idx) => (
                    <tr key={idx}>
                      <td>{txn.date}</td>
                      <td>{txn.entity}</td>
                      <td>{txn.cost_center}</td>
                      <td>{txn.account}</td>
                      <td>${txn.amount.toLocaleString()}</td>
                      <td>{txn.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

