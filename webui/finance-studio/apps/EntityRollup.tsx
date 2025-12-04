// Entity Rollup & Drilldown app component

import React, { useState } from 'react';
import { consolidateData } from '../api';
import type { SourceConfig, ConsolidationFilters, ConsolidatedRow } from '../types';

const ENTITIES = ['Global', 'EMEA', 'Americas', 'APAC'];

export function EntityRollup() {
  const [selectedEntities, setSelectedEntities] = useState<string[]>(['Global', 'EMEA', 'Americas']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consolidatedData, setConsolidatedData] = useState<ConsolidatedRow[] | null>(null);
  const [expandedEntities, setExpandedEntities] = useState<Set<string>>(new Set());

  const handleRollup = async () => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: selectedEntities,
        periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
      };

      const result = await consolidateData({ sources, filters, view: 'pl' });
      setConsolidatedData(result.rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rollup entities');
    } finally {
      setLoading(false);
    }
  };

  const toggleEntity = (entity: string) => {
    setSelectedEntities((prev) =>
      prev.includes(entity) ? prev.filter((e) => e !== entity) : [...prev, entity]
    );
  };

  const toggleExpand = (entity: string) => {
    setExpandedEntities((prev) => {
      const next = new Set(prev);
      if (next.has(entity)) {
        next.delete(entity);
      } else {
        next.add(entity);
      }
      return next;
    });
  };

  // Group rows by line item and entity
  const groupedData = consolidatedData
    ? consolidatedData.reduce((acc, row) => {
        const key = row.lineItem;
        if (!acc[key]) acc[key] = {};
        if (!acc[key][row.entity || 'Global']) acc[key][row.entity || 'Global'] = [];
        acc[key][row.entity || 'Global'].push(row);
        return acc;
      }, {} as Record<string, Record<string, ConsolidatedRow[]>>)
    : {};

  return (
    <div className="entity-rollup">
      <div className="rollup-config">
        <h2>Entity Selection</h2>
        <div className="entity-selector">
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
        <button className="rollup-button" onClick={handleRollup} disabled={loading}>
          {loading ? 'Rolling up...' : 'Roll Up Entities'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {consolidatedData && (
        <div className="rollup-results">
          <h2>Consolidated P&L</h2>
          <div className="rollup-table-container">
            <table className="rollup-table">
              <thead>
                <tr>
                  <th>Line Item</th>
                  {selectedEntities.map((entity) => (
                    <th key={entity}>{entity}</th>
                  ))}
                  <th>Total</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(groupedData).map(([lineItem, entityData]) => {
                  const isExpanded = expandedEntities.has(lineItem);
                  const totals = selectedEntities.reduce(
                    (acc, entity) => {
                      const rows = entityData[entity] || [];
                      const sum = rows.reduce((s, r) => s + (r.actual || 0), 0);
                      return acc + sum;
                    },
                    0
                  );

                  return (
                    <React.Fragment key={lineItem}>
                      <tr className="parent-row">
                        <td>
                          <button
                            className="expand-button"
                            onClick={() => toggleExpand(lineItem)}
                          >
                            {isExpanded ? '−' : '+'}
                          </button>
                          {lineItem}
                        </td>
                        {selectedEntities.map((entity) => {
                          const rows = entityData[entity] || [];
                          const sum = rows.reduce((s, r) => s + (r.actual || 0), 0);
                          return <td key={entity}>${(sum / 1000).toFixed(0)}K</td>;
                        })}
                        <td className="total-cell">${(totals / 1000).toFixed(0)}K</td>
                        <td>
                          <button className="drilldown-button">Drill Down</button>
                        </td>
                      </tr>
                      {isExpanded &&
                        selectedEntities.map((entity) => {
                          const rows = entityData[entity] || [];
                          if (rows.length === 0) return null;
                          return (
                            <tr key={`${lineItem}-${entity}`} className="child-row">
                              <td style={{ paddingLeft: '40px' }}>{entity}</td>
                              {selectedEntities.map((e) => {
                                if (e !== entity) return <td key={e}>-</td>;
                                const sum = rows.reduce((s, r) => s + (r.actual || 0), 0);
                                return <td key={e}>${(sum / 1000).toFixed(0)}K</td>;
                              })}
                              <td>-</td>
                              <td>-</td>
                            </tr>
                          );
                        })}
                    </React.Fragment>
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

