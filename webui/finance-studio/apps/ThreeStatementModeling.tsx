// 3-Statement Modeling Studio app component

import React, { useState } from 'react';
import { getThreeStatementData } from '../api';
import type { SourceConfig, ConsolidationFilters, ConsolidatedRow } from '../types';

const ENTITIES = ['Global', 'EMEA', 'Americas', 'APAC'];
const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY'];
const SCENARIOS = ['Actual', 'Budget', 'Forecast', 'Upside', 'Downside'];
const STATEMENT_TYPES = ['P&L', 'Balance Sheet', 'Cash Flow'];

export function ThreeStatementModeling() {
  const [selectedEntities, setSelectedEntities] = useState<string[]>(['Global']);
  const [selectedCurrencies, setSelectedCurrencies] = useState<string[]>(['USD']);
  const [selectedScenario, setSelectedScenario] = useState('Actual');
  const [activeStatement, setActiveStatement] = useState('P&L');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statementData, setStatementData] = useState<ConsolidatedRow[] | null>(null);

  const handleLoadStatement = async (statementType: string) => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: selectedEntities,
        periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
        scenarios: [selectedScenario],
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
      setStatementData(result.rows);
      setActiveStatement(statementType);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statement');
    } finally {
      setLoading(false);
    }
  };

  const toggleEntity = (entity: string) => {
    setSelectedEntities((prev) =>
      prev.includes(entity) ? prev.filter((e) => e !== entity) : [...prev, entity]
    );
  };

  return (
    <div className="three-statement-modeling">
      <div className="model-overview-header">
        <h2>Global Finance Model</h2>
        <p className="model-tagline">Multi-entity, multi-currency, hierarchical.</p>
        <div className="model-badges">
          <span className="badge">Governed</span>
          <span className="badge">Versioned</span>
        </div>
      </div>

      <div className="info-banner">
        <p>
          This governed model replaces scattered Excel files with a single source of truth for
          P&L, balance sheet, and cash flow.
        </p>
      </div>

      <div className="model-config-panel">
        <div className="config-tabs">
          <div className="config-tab">
            <h3>Entities & Hierarchy</h3>
            <div className="entity-tree">
              <div className="tree-node">
                <span>Global</span>
                <div className="tree-children">
                  {['EMEA', 'Americas', 'APAC'].map((region) => (
                    <div key={region} className="tree-node">
                      <span>{region}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="entity-selector">
              <label>Selected Entities</label>
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
          </div>

          <div className="config-tab">
            <h3>Currencies</h3>
            <div className="currency-list">
              {CURRENCIES.map((currency) => (
                <div key={currency} className="currency-item">
                  <span>{currency}</span>
                  <span className="fx-rate">FX: 1.00</span>
                </div>
              ))}
            </div>
          </div>

          <div className="config-tab">
            <h3>Scenarios</h3>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
            >
              {SCENARIOS.map((scenario) => (
                <option key={scenario} value={scenario}>
                  {scenario}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="statement-preview">
        <div className="statement-tabs">
          {STATEMENT_TYPES.map((type) => (
            <button
              key={type}
              className={`statement-tab ${activeStatement === type ? 'active' : ''}`}
              onClick={() => handleLoadStatement(type)}
              disabled={loading}
            >
              {type}
            </button>
          ))}
        </div>

        {error && <div className="error-message">{error}</div>}

        {statementData && (
          <div className="statement-table-container">
            <table className="statement-table">
              <thead>
                <tr>
                  <th>Line Item</th>
                  <th>Entity</th>
                  <th>Period</th>
                  <th>Actual</th>
                  <th>Budget</th>
                  <th>Forecast</th>
                </tr>
              </thead>
              <tbody>
                {statementData.map((row, idx) => (
                  <tr key={idx} className={row.level === 'parent' ? 'parent-row' : 'child-row'}>
                    <td style={{ paddingLeft: row.level === 'child' ? '24px' : '0' }}>
                      {row.lineItem}
                    </td>
                    <td>{row.entity || '-'}</td>
                    <td>{row.period || '-'}</td>
                    <td>${((row.actual || 0) / 1000).toFixed(0)}K</td>
                    <td>${((row.budget || 0) / 1000).toFixed(0)}K</td>
                    <td>${((row.forecast || 0) / 1000).toFixed(0)}K</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="export-section">
          <button className="export-button" onClick={() => alert('Export to Excel - Coming soon')}>
            Export to Excel
          </button>
        </div>
      </div>
    </div>
  );
}

