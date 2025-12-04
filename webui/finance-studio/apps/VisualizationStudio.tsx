// Visualization Studio app component

import React, { useState, useEffect } from 'react';
import { getVisualizationData, getDrilldownTransactions } from '../api';
import type { SourceConfig, ConsolidationFilters, DrilldownTransaction } from '../types';

export function VisualizationStudio() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [vizData, setVizData] = useState<any>(null);
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
  const [drilldownData, setDrilldownData] = useState<DrilldownTransaction[] | null>(null);

  useEffect(() => {
    loadVisualizationData();
  }, []);

  const loadVisualizationData = async () => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: ['Global', 'EMEA', 'Americas', 'APAC'],
        periods: ['2025-Q1', '2025-Q2'],
      };

      const data = await getVisualizationData({ sources, filters, view: 'visual' });
      setVizData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load visualization data');
    } finally {
      setLoading(false);
    }
  };

  const handleViewTransactions = async () => {
    try {
      const transactions = await getDrilldownTransactions('Revenue', selectedMarket || undefined);
      setDrilldownData(transactions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions');
    }
  };

  const handleResetFilters = () => {
    setSelectedMarket(null);
    setSelectedProduct(null);
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!vizData) return <div>No data available</div>;

  const { kpis, entity_breakdown } = vizData;

  return (
    <div className="visualization-studio">
      <div className="dashboard-controls">
        <div className="filter-group">
          <label>Filter by Market/Region</label>
          <select
            value={selectedMarket || ''}
            onChange={(e) => setSelectedMarket(e.target.value || null)}
          >
            <option value="">All Markets</option>
            {Object.keys(entity_breakdown || {}).map((market) => (
              <option key={market} value={market}>
                {market}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Filter by Product Line</label>
          <select
            value={selectedProduct || ''}
            onChange={(e) => setSelectedProduct(e.target.value || null)}
          >
            <option value="">All Products</option>
            <option value="Product A">Product A</option>
            <option value="Product B">Product B</option>
            <option value="Product C">Product C</option>
          </select>
        </div>

        <button className="reset-filters-button" onClick={handleResetFilters}>
          Reset Filters
        </button>
      </div>

      <div className="dashboard-layout">
        <div className="kpi-cards-row">
          <div className="kpi-card-large">
            <div className="kpi-label">Total Revenue (EUR)</div>
            <div className="kpi-value-large">
              €{(kpis.total_revenue / 1000000).toFixed(2)}M
            </div>
            <div className="kpi-delta positive">+5.2% vs prior period</div>
          </div>

          <div className="kpi-card-large">
            <div className="kpi-label">Contribution Margin (EUR)</div>
            <div className="kpi-value-large">
              €{((kpis.gross_profit || 0) / 1000000).toFixed(2)}M
            </div>
            <div className="kpi-delta positive">+3.8% vs prior period</div>
          </div>
        </div>

        <div className="charts-section">
          <div className="chart-container">
            <h3>Contribution margin by market (Q1, Q2)</h3>
            <div className="bar-chart-placeholder">
              {Object.entries(entity_breakdown || {}).map(([market, data]: [string, any]) => (
                <div key={market} className="bar-chart-item">
                  <div className="bar-label">{market}</div>
                  <div className="bar-wrapper">
                    <div
                      className="bar"
                      style={{
                        width: `${(data.revenue / kpis.total_revenue) * 100}%`,
                        backgroundColor: selectedMarket === market ? '#0066FF' : '#8b5cf6',
                      }}
                    >
                      €{(data.revenue / 1000).toFixed(0)}K
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <button className="view-transactions-button" onClick={handleViewTransactions}>
              View Transactions
            </button>
          </div>

          <div className="chart-container">
            <h3>Net sales by market</h3>
            <div className="pie-chart-placeholder">
              {Object.entries(entity_breakdown || {}).map(([market, data]: [string, any], idx) => {
                const percentage = (data.revenue / kpis.total_revenue) * 100;
                const colors = ['#0066FF', '#0f766e', '#8b5cf6', '#f59e0b'];
                return (
                  <div key={market} className="pie-slice" style={{ backgroundColor: colors[idx % colors.length] }}>
                    <span>{market}: {percentage.toFixed(1)}%</span>
                  </div>
                );
              })}
            </div>
            <button className="view-transactions-button" onClick={handleViewTransactions}>
              View Transactions
            </button>
          </div>
        </div>

        <div className="detail-table-section">
          <h3>Detail Data</h3>
          <div className="detail-table-container">
            <table className="detail-table">
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Revenue</th>
                  <th>Gross Profit</th>
                  <th>Margin %</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(entity_breakdown || {})
                  .filter(([market]) => !selectedMarket || market === selectedMarket)
                  .map(([market, data]: [string, any]) => (
                    <tr key={market}>
                      <td>{market}</td>
                      <td>€{(data.revenue / 1000).toFixed(0)}K</td>
                      <td>€{((data.gross_profit || 0) / 1000).toFixed(0)}K</td>
                      <td>
                        {data.revenue > 0
                          ? (((data.gross_profit || 0) / data.revenue) * 100).toFixed(1)
                          : 0}%
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {drilldownData && (
        <div className="drilldown-modal">
          <div className="drilldown-content">
            <div className="drilldown-header">
              <h3>Transaction Details</h3>
              <button className="close-button" onClick={() => setDrilldownData(null)}>
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
                      <td>€{txn.amount.toLocaleString()}</td>
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

