// Export & BI Bridge app component

import React, { useState } from 'react';
import { exportData, consolidateData } from '../api';
import type { SourceConfig, ConsolidationFilters, ConsolidatedRow } from '../types';

export function ExportBridge() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ConsolidatedRow[] | null>(null);
  const [exportFormat, setExportFormat] = useState<'excel' | 'csv'>('csv');

  const handleLoadPreview = async () => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: ['Global'],
        periods: ['2025-Q1', '2025-Q2'],
      };

      const result = await consolidateData({ sources, filters, view: 'pl' });
      setPreviewData(result.rows.slice(0, 10)); // Show first 10 rows as preview
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'excel' | 'csv') => {
    setLoading(true);
    setError(null);

    try {
      const sources: SourceConfig[] = [{ source_id: 'internal_db', connection_info: {} }];
      const filters: ConsolidationFilters = {
        entities: ['Global'],
        periods: ['2025-Q1', '2025-Q2'],
      };

      const blob = await exportData({ sources, filters, view: 'pl' }, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance-export-${new Date().toISOString().split('T')[0]}.${format === 'csv' ? 'csv' : 'xlsx'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyApiUrl = () => {
    const apiUrl = `${window.API_BASE || ''}/api/finance-studio/consolidate`;
    navigator.clipboard.writeText(apiUrl);
    alert('API URL copied to clipboard!');
  };

  return (
    <div className="export-bridge">
      <div className="export-header">
        <h2>Export & BI Bridge</h2>
        <p>Export consolidated tables into Excel, CSV, or BI tools with one click.</p>
      </div>

      <div className="export-actions">
        <button className="load-preview-button" onClick={handleLoadPreview} disabled={loading}>
          {loading ? 'Loading...' : 'Load Preview'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {previewData && (
        <div className="preview-section">
          <h3>Preview (Last Consolidated Result)</h3>
          <div className="preview-table-container">
            <table className="preview-table">
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
                {previewData.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.lineItem}</td>
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
        </div>
      )}

      <div className="export-options">
        <h3>Export Options</h3>
        <div className="export-buttons">
          <button
            className="export-button"
            onClick={() => handleExport('csv')}
            disabled={loading || !previewData}
          >
            Download as CSV
          </button>
          <button
            className="export-button"
            onClick={() => handleExport('excel')}
            disabled={loading || !previewData}
          >
            Download as Excel
          </button>
          <button className="export-button" onClick={handleCopyApiUrl}>
            Copy API URL for BI Tools
          </button>
        </div>
      </div>

      <div className="bi-integration-section">
        <h3>BI Tool Integration</h3>
        <p>Use the API URL to connect your BI tools:</p>
        <code className="api-url">
          {window.API_BASE || ''}/api/finance-studio/consolidate
        </code>
        <p className="api-note">
          POST request with JSON body containing sources, filters, and view parameters.
        </p>
      </div>
    </div>
  );
}

