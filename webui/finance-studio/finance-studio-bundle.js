// Finance Studio - Full vanilla JS implementation
// This provides complete functionality without requiring React compilation

(function() {
  'use strict';

  const API_BASE = window.API_BASE || '';

  // API client functions
  async function apiCall(endpoint, options = {}) {
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API_BASE || ''}${endpoint}`;
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorDetail = errorText;
        try {
          const errorJson = JSON.parse(errorText);
          errorDetail = errorJson.detail || errorJson.message || errorText;
        } catch (e) {
          // Not JSON, use text as-is
        }
        throw new Error(`API call failed (${response.status}): ${errorDetail}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return response.json();
      } else {
        return response.text();
      }
    } catch (error) {
      console.error('API call error:', error);
      throw error;
    }
  }

  async function getPLConsolidation(sources, filters) {
    return apiCall('/api/finance-studio/pl-consolidation', {
      method: 'POST',
      body: JSON.stringify({ sources, filters, view: 'pl' }),
    });
  }

  async function getThreeStatementData(sources, filters, statementType = 'pl') {
    return apiCall(`/api/finance-studio/three-statement?statement_type=${encodeURIComponent(statementType)}`, {
      method: 'POST',
      body: JSON.stringify({ sources, filters, view: statementType }),
    });
  }

  async function getVisualizationData(sources, filters) {
    return apiCall('/api/finance-studio/visualizations', {
      method: 'POST',
      body: JSON.stringify({ sources, filters, view: 'visual' }),
    });
  }

  async function getDrilldownTransactions(lineItem, entity, period, statementType = 'pl', scenario) {
    const params = new URLSearchParams({ line_item: lineItem, statement_type: statementType });
    if (entity) params.append('entity', entity);
    if (period) params.append('period', period);
    if (scenario) params.append('scenario', scenario);
    const data = await apiCall(`/api/finance-studio/drilldown?${params.toString()}`);
    return data.transactions || [];
  }

  // App tiles data - must be defined before functions that use it
  const APP_TILES = [
    { id: 'data-consolidation', title: 'Data Consolidation Studio', description: 'Transform raw data from multiple sources into a clean, standardized finance table you can trust.', icon: '📊', color: '#0066FF' },
    { id: 'board-reports', title: 'Board-Ready Reports', description: 'Generate 3-statement, board-ready reports with real-time BvA and drill-down to transaction level.', icon: '📋', color: '#0f766e' },
    { id: 'visualization', title: 'Visualization Studio', description: 'Interactive charts and dashboards with drill-down from KPI to transaction detail.', icon: '📈', color: '#8b5cf6' },
    { id: 'three-statement', title: '3-Statement Modeling Studio', description: 'One governed model for P&L, balance sheet, and cash flow across entities, currencies, and hierarchies.', icon: '💼', color: '#f59e0b' },
    { id: 'entity-rollup', title: 'Entity Rollup & Drilldown', description: 'Roll up multiple subsidiaries or regions into a single P&L, with drill-down on demand.', icon: '🏢', color: '#10b981' },
    { id: 'export-bridge', title: 'Export & BI Bridge', description: 'Export consolidated tables into Excel, CSV, or BI tools with one click.', icon: '📤', color: '#ef4444' },
  ];

  function getAppTilesHTML() {
    return APP_TILES.map(app => `
      <div class="app-tile">
        <div class="app-tile-icon" style="background-color: ${app.color}15; color: ${app.color}">
          <span class="app-tile-icon-emoji">${app.icon}</span>
        </div>
        <div class="app-tile-content">
          <h3 class="app-tile-title">${app.title}</h3>
          <p class="app-tile-description">${app.description}</p>
          <button class="app-tile-launch-button" data-app-id="${app.id}" style="background-color: ${app.color}">
            Launch
          </button>
        </div>
      </div>
    `).join('');
  }

  function formatCurrency(value) {
    if (!value) return '-';
    if (Math.abs(value) >= 1000000) return `$${(value / 1000000).toFixed(2)}M`;
    if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  }

  function getVarianceColor(variancePct) {
    if (!variancePct) return '';
    return variancePct > 0 ? '#10b981' : '#ef4444';
  }

  // Data Consolidation Studio
  function renderDataConsolidationStudio() {
    return `
      <div class="data-consolidation-studio">
        <div class="consolidation-config-panel">
          <h2>Source Selection & Configuration</h2>
          
          <div class="config-section">
            <label>Data Sources</label>
            <div class="multi-select-buttons" id="data-sources-buttons">
              <button class="multi-select-button selected" data-source="excel">Excel / CSV</button>
              <button class="multi-select-button" data-source="edgar">EDGAR / SEC filings</button>
              <button class="multi-select-button" data-source="internal_db">Internal SQL DB</button>
              <button class="multi-select-button" data-source="google_sheets">Google Sheets</button>
            </div>
          </div>

          <div class="config-section">
            <label>Period</label>
            <div class="period-selector">
              <select id="consolidation-year">
                <option value="2025" selected>2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
                <option value="2022">2022</option>
              </select>
              <div class="granularity-toggle">
                <button class="granularity-btn" data-gran="Monthly">Monthly</button>
                <button class="granularity-btn active" data-gran="Quarterly">Quarterly</button>
                <button class="granularity-btn" data-gran="Yearly">Yearly</button>
              </div>
            </div>
          </div>

          <div class="config-section">
            <label>Entities</label>
            <div class="multi-select-buttons" id="consolidation-entities">
              <button class="multi-select-button selected" data-entity="Global">Global</button>
              <button class="multi-select-button" data-entity="EMEA">EMEA</button>
              <button class="multi-select-button" data-entity="Americas">Americas</button>
              <button class="multi-select-button" data-entity="APAC">APAC</button>
            </div>
          </div>

          <button class="transform-button" id="transform-consolidate-btn">
            Transform & Consolidate
          </button>
        </div>

        <div id="consolidation-results" style="display: none;"></div>
      </div>
    `;
  }

  function setupDataConsolidationStudio() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;

    root.innerHTML = renderDataConsolidationStudio();

    let selectedSources = ['excel'];
    let selectedEntities = ['Global'];
    let granularity = 'Quarterly';
    let year = '2025';

    // Source selection
    root.querySelectorAll('#data-sources-buttons button').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('selected');
        const source = btn.dataset.source;
        if (selectedSources.includes(source)) {
          selectedSources = selectedSources.filter(s => s !== source);
        } else {
          selectedSources.push(source);
        }
      });
    });

    // Entity selection
    root.querySelectorAll('#consolidation-entities button').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('selected');
        const entity = btn.dataset.entity;
        if (selectedEntities.includes(entity)) {
          selectedEntities = selectedEntities.filter(e => e !== entity);
        } else {
          selectedEntities.push(entity);
        }
      });
    });

    // Granularity
    root.querySelectorAll('.granularity-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        root.querySelectorAll('.granularity-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        granularity = btn.dataset.gran;
      });
    });

    // Year
    root.querySelector('#consolidation-year').addEventListener('change', (e) => {
      year = e.target.value;
    });

    // Transform button
    root.querySelector('#transform-consolidate-btn').addEventListener('click', async () => {
      const btn = root.querySelector('#transform-consolidate-btn');
      const resultsDiv = root.querySelector('#consolidation-results');
      
      btn.disabled = true;
      btn.textContent = 'Transforming...';
      resultsDiv.style.display = 'none';

      try {
        const sources = selectedSources.map(id => ({ source_id: id, connection_info: {} }));
        const periods = granularity === 'Quarterly' 
          ? [`${year}-Q1`, `${year}-Q2`, `${year}-Q3`, `${year}-Q4`]
          : granularity === 'Monthly'
          ? Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, '0')}`)
          : [year];

        const result = await getPLConsolidation(sources, {
          entities: selectedEntities,
          periods,
          scenarios: ['Actual', 'Budget', 'Forecast'],
        });

        // Calculate KPIs
        const revenueRows = result.rows.filter(r => r.lineItem === 'Revenue' || r.line_item === 'Revenue');
        const grossProfitRows = result.rows.filter(r => r.lineItem === 'Gross Profit' || r.line_item === 'Gross Profit');
        const ebitdaRows = result.rows.filter(r => r.lineItem === 'EBITDA' || r.line_item === 'EBITDA');

        const totalRevenue = revenueRows.reduce((sum, r) => sum + (r.actual || 0), 0);
        const totalGrossProfit = grossProfitRows.reduce((sum, r) => sum + (r.actual || 0), 0);
        const totalEbitda = ebitdaRows.reduce((sum, r) => sum + (r.actual || 0), 0);

        const grossProfitPct = totalRevenue > 0 ? (totalGrossProfit / totalRevenue) * 100 : 0;
        const ebitdaPct = totalRevenue > 0 ? (totalEbitda / totalRevenue) * 100 : 0;

        // Group rows by line item and period
        const grouped = {};
        result.rows.forEach(row => {
          const lineItem = row.lineItem || row.line_item;
          const period = row.period;
          const key = `${lineItem}-${period}`;
          if (!grouped[key]) grouped[key] = [];
          grouped[key].push(row);
        });

        // Build table
        const resultPeriods = [...new Set(result.rows.map(r => r.period).filter(Boolean))];
        const lineItems = [...new Set(result.rows.map(r => r.lineItem || r.line_item))];

        let tableHTML = `
          <div class="kpi-banner">
            <div class="kpi-card">
              <div class="kpi-label">Total Revenue</div>
              <div class="kpi-value">${formatCurrency(totalRevenue)}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">Gross Profit %</div>
              <div class="kpi-value">${grossProfitPct.toFixed(1)}%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">EBITDA %</div>
              <div class="kpi-value">${ebitdaPct.toFixed(1)}%</div>
            </div>
          </div>

          <div class="consolidation-results">
            <h2>P&L Consolidation Results</h2>
            <div class="pl-grid-container">
              <table class="pl-grid">
                <thead>
                  <tr>
                    <th>Line Item</th>
                    ${resultPeriods.map(p => `<th colspan="3">${p}</th>`).join('')}
                  </tr>
                  <tr>
                    <th></th>
                    ${resultPeriods.map(() => '<th>Actual</th><th>Forecast</th><th>Variance %</th>').join('')}
                  </tr>
                </thead>
                <tbody>
        `;

        lineItems.forEach(lineItem => {
          const firstRow = result.rows.find(r => (r.lineItem || r.line_item) === lineItem);
          const isParent = firstRow?.level === 'parent';
          tableHTML += `
            <tr class="pl-row ${isParent ? 'parent-row' : 'child-row'}">
              <td class="line-item-cell" style="padding-left: ${isParent ? '0' : '24px'}">${lineItem}</td>
          `;
          
          resultPeriods.forEach(period => {
            const periodRows = result.rows.filter(r => 
              (r.lineItem || r.line_item) === lineItem && r.period === period
            );
            const row = periodRows[0] || firstRow;
            const actual = row?.actual || 0;
            const forecast = row?.forecast || 0;
            const variancePct = row?.variancePct || row?.variance_pct || 0;
            const color = getVarianceColor(variancePct);
            
            tableHTML += `
              <td>${formatCurrency(actual)}</td>
              <td>${formatCurrency(forecast)}</td>
              <td style="color: ${color}; background-color: ${color ? color + '20' : 'transparent'}">
                ${variancePct ? `${variancePct > 0 ? '+' : ''}${variancePct.toFixed(1)}%` : '-'}
              </td>
            `;
          });
          
          tableHTML += '</tr>';
        });

        tableHTML += `
                </tbody>
              </table>
            </div>
          </div>
        `;

        resultsDiv.innerHTML = tableHTML;
        resultsDiv.style.display = 'block';
      } catch (error) {
        alert('Error: ' + error.message);
        console.error(error);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Transform & Consolidate';
      }
    });
  }

  // Board-Ready Reports
  function renderBoardReadyReports() {
    return `
      <div class="board-ready-reports">
        <div class="report-config-bar">
          <div class="config-group">
            <label>Statement Type</label>
            <select id="statement-type">
              <option value="P&L" selected>P&L</option>
              <option value="Balance Sheet">Balance Sheet</option>
              <option value="Cash Flow">Cash Flow</option>
            </select>
          </div>
          <div class="config-group">
            <label>Scenario</label>
            <select id="report-scenario">
              <option value="Actual vs Budget" selected>Actual vs Budget</option>
              <option value="Actual vs Forecast">Actual vs Forecast</option>
              <option value="Multi-Scenario">Multi-Scenario</option>
            </select>
          </div>
          <div class="config-group">
            <label>Period</label>
            <select id="report-period">
              <option value="Quarter" selected>Quarter</option>
              <option value="Year">Year</option>
              <option value="Custom Range">Custom Range</option>
            </select>
          </div>
          <button class="generate-button" id="generate-report-btn">Generate Report</button>
        </div>
        <div id="report-results" style="display: none;"></div>
      </div>
    `;
  }

  function setupBoardReadyReports() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;
    root.innerHTML = renderBoardReadyReports();

    root.querySelector('#generate-report-btn').addEventListener('click', async () => {
      const btn = root.querySelector('#generate-report-btn');
      const resultsDiv = root.querySelector('#report-results');
      
      btn.disabled = true;
      btn.textContent = 'Generating...';

      try {
        const statementType = root.querySelector('#statement-type').value;
        const scenario = root.querySelector('#report-scenario').value;
        const statementTypeMap = { 'P&L': 'pl', 'Balance Sheet': 'balance_sheet', 'Cash Flow': 'cashflow' };

        const result = await getThreeStatementData(
          [{ source_id: 'internal_db', connection_info: {} }],
          {
            entities: ['Global'],
            periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
            scenarios: scenario.includes('Budget') ? ['Actual', 'Budget'] : ['Actual', 'Forecast'],
          },
          statementTypeMap[statementType] || 'pl'
        );

        let tableHTML = `
          <div class="report-panel">
            <div class="report-header">
              <h2>Board-Ready View – ${statementType} – ${root.querySelector('#report-period').value}</h2>
            </div>
            <div class="statement-table-container">
              <table class="statement-table">
                <thead>
                  <tr>
                    <th>Line Item</th>
                    <th>Actual</th>
                    <th>${scenario.includes('Budget') ? 'Budget' : 'Forecast'}</th>
                    <th>Variance (Abs)</th>
                    <th>Variance %</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
        `;

        result.rows.forEach((row, idx) => {
          const lineItem = row.lineItem || row.line_item;
          const actual = row.actual || 0;
          const budget = scenario.includes('Budget') ? (row.budget || 0) : (row.forecast || 0);
          const varianceAbs = row.varianceAbs || row.variance_abs || (actual - budget);
          const variancePct = row.variancePct || row.variance_pct || (budget !== 0 ? (varianceAbs / budget * 100) : 0);
          const color = getVarianceColor(variancePct);
          const isChild = row.level === 'child';

          tableHTML += `
            <tr class="${isChild ? 'child-row' : 'parent-row'}">
              <td style="padding-left: ${isChild ? '24px' : '0'}">${lineItem}</td>
              <td>${formatCurrency(actual)}</td>
              <td>${formatCurrency(budget)}</td>
              <td>${formatCurrency(varianceAbs)}</td>
              <td style="color: ${color}; background-color: ${color ? color + '20' : 'transparent'}">
                ${variancePct ? `${variancePct > 0 ? '+' : ''}${variancePct.toFixed(1)}%` : '-'}
              </td>
              <td><button class="drilldown-button" data-line-item="${lineItem}" data-entity="${row.entity || ''}" data-period="${row.period || ''}">Drill Down</button></td>
            </tr>
          `;
        });

        tableHTML += `
                </tbody>
              </table>
            </div>
          </div>
        `;

        resultsDiv.innerHTML = tableHTML;
        resultsDiv.style.display = 'block';

        // Add drilldown handlers
        resultsDiv.querySelectorAll('.drilldown-button').forEach(btn => {
          btn.addEventListener('click', async () => {
            const lineItem = btn.dataset.lineItem;
            const entity = btn.dataset.entity;
            const period = btn.dataset.period;
            
            try {
              const transactions = await getDrilldownTransactions(lineItem, entity, period, statementTypeMap[statementType] || 'pl');
              
              let modalHTML = `
                <div class="drilldown-modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                  <div class="drilldown-content" style="background: white; border-radius: 12px; padding: 1.5rem; max-width: 90vw; max-height: 90vh; overflow: auto;">
                    <div class="drilldown-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0;">
                      <h3>Drill-down – ${lineItem} – ${period}</h3>
                      <button class="close-button" onclick="this.closest('.drilldown-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    <table class="drilldown-table" style="width: 100%; border-collapse: collapse;">
                      <thead>
                        <tr>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Date</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Entity</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Cost Center</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Account</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Amount</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Description</th>
                        </tr>
                      </thead>
                      <tbody>
              `;

              transactions.forEach(txn => {
                modalHTML += `
                  <tr>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.date}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.entity}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.cost_center}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.account}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">$${txn.amount.toLocaleString()}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.description}</td>
                  </tr>
                `;
              });

              modalHTML += `
                      </tbody>
                    </table>
                  </div>
                </div>
              `;

              document.body.insertAdjacentHTML('beforeend', modalHTML);
            } catch (error) {
              alert('Error loading drilldown: ' + error.message);
            }
          });
        });
      } catch (error) {
        alert('Error: ' + error.message);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Report';
      }
    });
  }

  // Visualization Studio
  function renderVisualizationStudio() {
    return `
      <div class="visualization-studio">
        <div class="dashboard-controls">
          <div class="filter-group">
            <label>Filter by Market/Region</label>
            <select id="market-filter">
              <option value="">All Markets</option>
              <option value="Global">Global</option>
              <option value="EMEA">EMEA</option>
              <option value="Americas">Americas</option>
              <option value="APAC">APAC</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Filter by Product Line</label>
            <select id="product-filter">
              <option value="">All Products</option>
              <option value="Product A">Product A</option>
              <option value="Product B">Product B</option>
              <option value="Product C">Product C</option>
            </select>
          </div>
          <button class="reset-filters-button" id="reset-filters-btn">Reset Filters</button>
        </div>
        <div id="visualization-results"></div>
      </div>
    `;
  }

  function setupVisualizationStudio() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;
    root.innerHTML = renderVisualizationStudio();

    async function loadVisualizations() {
      const resultsDiv = root.querySelector('#visualization-results');
      resultsDiv.innerHTML = '<div class="loading">Loading dashboard...</div>';

      try {
        const data = await getVisualizationData(
          [{ source_id: 'internal_db', connection_info: {} }],
          {
            entities: ['Global', 'EMEA', 'Americas', 'APAC'],
            periods: ['2025-Q1', '2025-Q2'],
          }
        );

        const { kpis, entity_breakdown } = data;
        const selectedMarket = root.querySelector('#market-filter').value;

        let html = `
          <div class="dashboard-layout">
            <div class="kpi-cards-row">
              <div class="kpi-card-large">
                <div class="kpi-label">Total Revenue (EUR)</div>
                <div class="kpi-value-large">€${(kpis.total_revenue / 1000000).toFixed(2)}M</div>
                <div class="kpi-delta positive">+5.2% vs prior period</div>
              </div>
              <div class="kpi-card-large">
                <div class="kpi-label">Contribution Margin (EUR)</div>
                <div class="kpi-value-large">€${((kpis.gross_profit || 0) / 1000000).toFixed(2)}M</div>
                <div class="kpi-delta positive">+3.8% vs prior period</div>
              </div>
            </div>

            <div class="charts-section">
              <div class="chart-container">
                <h3>Contribution margin by market (Q1, Q2)</h3>
                <div class="bar-chart-placeholder">
        `;

        Object.entries(entity_breakdown || {}).forEach(([market, data]) => {
          if (!selectedMarket || market === selectedMarket) {
            const percentage = (data.revenue / kpis.total_revenue) * 100;
            html += `
              <div class="bar-chart-item">
                <div class="bar-label">${market}</div>
                <div class="bar-wrapper">
                  <div class="bar" style="width: ${percentage}%; background-color: ${selectedMarket === market ? '#0066FF' : '#8b5cf6'}">
                    €${(data.revenue / 1000).toFixed(0)}K
                  </div>
                </div>
              </div>
            `;
          }
        });

        html += `
                </div>
              </div>

              <div class="chart-container">
                <h3>Net sales by market</h3>
                <button class="view-transactions-btn" data-line-item="Revenue" style="margin-bottom: 1rem; padding: 0.5rem 1rem; background: #0066FF; color: white; border: none; border-radius: 6px; cursor: pointer;">View Transactions</button>
                <div class="pie-chart-placeholder">
        `;

        const colors = ['#0066FF', '#0f766e', '#8b5cf6', '#f59e0b'];
        Object.entries(entity_breakdown || {}).forEach(([market, data], idx) => {
          if (!selectedMarket || market === selectedMarket) {
            const percentage = kpis.total_revenue > 0 ? (data.revenue / kpis.total_revenue) * 100 : 0;
            html += `
              <div class="pie-slice clickable-chart-item" 
                   data-market="${market}"
                   style="background-color: ${colors[idx % colors.length]}; padding: 0.75rem; border-radius: 6px; color: white; margin-bottom: 0.5rem; cursor: pointer; transition: opacity 0.2s;"
                   onmouseover="this.style.opacity='0.8'" 
                   onmouseout="this.style.opacity='1'">
                <span>${market}: ${percentage.toFixed(1)}% (${formatCurrency(data.revenue)})</span>
              </div>
            `;
          }
        });

        html += `
                </div>
              </div>
            </div>

            <div class="detail-table-section">
              <h3>Detail Data</h3>
              <div class="detail-table-container">
                <table class="detail-table">
                  <thead>
                    <tr>
                      <th>Market</th>
                      <th>Revenue</th>
                      <th>Gross Profit</th>
                      <th>Margin %</th>
                    </tr>
                  </thead>
                  <tbody>
        `;

        Object.entries(entity_breakdown || {}).forEach(([market, data]) => {
          if (!selectedMarket || market === selectedMarket) {
            const margin = data.revenue > 0 ? (((data.gross_profit || 0) / data.revenue) * 100) : 0;
            html += `
              <tr>
                <td>${market}</td>
                <td>€${(data.revenue / 1000).toFixed(0)}K</td>
                <td>€${((data.gross_profit || 0) / 1000).toFixed(0)}K</td>
                <td>${margin.toFixed(1)}%</td>
              </tr>
            `;
          }
        });

        html += `
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        `;

        resultsDiv.innerHTML = html;

        // Add click handlers for interactive charts
        resultsDiv.querySelectorAll('.clickable-chart-item').forEach(item => {
          item.addEventListener('click', () => {
            const market = item.dataset.market;
            // Filter detail table
            const detailRows = resultsDiv.querySelectorAll('.detail-table tbody tr');
            detailRows.forEach(row => {
              const marketCell = row.querySelector('td:first-child');
              if (marketCell && marketCell.textContent.trim() === market) {
                row.style.display = '';
                row.style.backgroundColor = '#f0f9ff';
              } else {
                row.style.display = 'none';
              }
            });
          });
        });

        // Add "View transactions" button handlers
        resultsDiv.querySelectorAll('.view-transactions-btn').forEach(btn => {
          btn.addEventListener('click', async () => {
            const lineItem = btn.dataset.lineItem || 'Revenue';
            try {
              const transactions = await getDrilldownTransactions(lineItem, selectedMarket, '2025-Q1', 'pl');
              
              let modalHTML = `
                <div class="drilldown-modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                  <div class="drilldown-content" style="background: white; border-radius: 12px; padding: 1.5rem; max-width: 90vw; max-height: 90vh; overflow: auto;">
                    <div class="drilldown-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0;">
                      <h3>Transactions – ${lineItem}</h3>
                      <button class="close-button" onclick="this.closest('.drilldown-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    <table class="drilldown-table" style="width: 100%; border-collapse: collapse;">
                      <thead>
                        <tr>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Date</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Entity</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Amount</th>
                          <th style="padding: 0.75rem; background: #f8fafc; text-align: left; font-weight: 600;">Description</th>
                        </tr>
                      </thead>
                      <tbody>
              `;

              transactions.forEach(txn => {
                modalHTML += `
                  <tr>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.date}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.entity}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">$${txn.amount.toLocaleString()}</td>
                    <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">${txn.description}</td>
                  </tr>
                `;
              });

              modalHTML += `
                      </tbody>
                    </table>
                  </div>
                </div>
              `;

              document.body.insertAdjacentHTML('beforeend', modalHTML);
            } catch (error) {
              alert('Error loading transactions: ' + error.message);
            }
          });
        });
      } catch (error) {
        resultsDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
      }
    }

    root.querySelector('#market-filter').addEventListener('change', loadVisualizations);
    root.querySelector('#reset-filters-btn').addEventListener('click', () => {
      root.querySelector('#market-filter').value = '';
      root.querySelector('#product-filter').value = '';
      // Reset table display
      const detailRows = root.querySelectorAll('.detail-table tbody tr');
      detailRows.forEach(row => {
        row.style.display = '';
        row.style.backgroundColor = '';
      });
      loadVisualizations();
    });

    loadVisualizations();
  }

  // 3-Statement Modeling
  function renderThreeStatementModeling() {
    return `
      <div class="three-statement-modeling">
        <div class="model-overview-header">
          <h2>Global Finance Model</h2>
          <p class="model-tagline">Multi-entity, multi-currency, hierarchical.</p>
          <div class="model-badges">
            <span class="badge">Governed</span>
            <span class="badge">Versioned</span>
          </div>
        </div>
        <div class="info-banner">
          <p>This governed model replaces scattered Excel files with a single source of truth for P&L, balance sheet, and cash flow.</p>
        </div>
        <div class="statement-preview">
          <div class="statement-tabs">
            <button class="statement-tab active" data-statement="pl">P&L</button>
            <button class="statement-tab" data-statement="balance_sheet">Balance Sheet</button>
            <button class="statement-tab" data-statement="cashflow">Cash Flow</button>
          </div>
          <div id="statement-results"></div>
        </div>
      </div>
    `;
  }

  function setupThreeStatementModeling() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;
    root.innerHTML = renderThreeStatementModeling();

    async function loadStatement(statementType) {
      const resultsDiv = root.querySelector('#statement-results');
      resultsDiv.innerHTML = '<div class="loading">Loading statement...</div>';

      try {
        const result = await getThreeStatementData(
          [{ source_id: 'internal_db', connection_info: {} }],
          {
            entities: ['Global'],
            periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
            scenarios: ['Actual'],
          },
          statementType
        );

        let html = `
          <div class="statement-table-container">
            <table class="statement-table">
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
        `;

        result.rows.forEach(row => {
          const lineItem = row.lineItem || row.line_item;
          const isChild = row.level === 'child';
          html += `
            <tr class="${isChild ? 'child-row' : 'parent-row'}">
              <td style="padding-left: ${isChild ? '24px' : '0'}">${lineItem}</td>
              <td>${row.entity || '-'}</td>
              <td>${row.period || '-'}</td>
              <td>${formatCurrency(row.actual || 0)}</td>
              <td>${formatCurrency(row.budget || 0)}</td>
              <td>${formatCurrency(row.forecast || 0)}</td>
            </tr>
          `;
        });

        html += `
              </tbody>
            </table>
          </div>
        `;

        resultsDiv.innerHTML = html;
      } catch (error) {
        resultsDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
      }
    }

    root.querySelectorAll('.statement-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        root.querySelectorAll('.statement-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        loadStatement(tab.dataset.statement);
      });
    });

    root.querySelectorAll('.scenario-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        root.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const activeTab = root.querySelector('.statement-tab.active');
        if (activeTab) {
          loadStatement(activeTab.dataset.statement);
        }
      });
    });

    root.querySelector('#export-model-excel-btn').addEventListener('click', async () => {
      try {
        const result = await getThreeStatementData(
          [{ source_id: 'internal_db', connection_info: {} }],
          {
            entities: ['Global'],
            periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
            scenarios: ['Actual'],
          },
          'pl'
        );

        let html = `
          <html>
            <head>
              <meta charset="utf-8">
              <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
                .parent-row { font-weight: 600; }
              </style>
            </head>
            <body>
              <h2>Global Finance Model Export</h2>
              <table>
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
        `;

        result.rows.forEach(row => {
          const isParent = row.level === 'parent';
          html += `
            <tr class="${isParent ? 'parent-row' : ''}">
              <td style="padding-left: ${isParent ? '0' : '24px'}">${row.lineItem || row.line_item}</td>
              <td>${row.entity || '-'}</td>
              <td>${row.period || '-'}</td>
              <td>${row.actual || 0}</td>
              <td>${row.budget || 0}</td>
              <td>${row.forecast || 0}</td>
            </tr>
          `;
        });

        html += `
                </tbody>
              </table>
            </body>
          </html>
        `;

        const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `finance-model-${new Date().toISOString().split('T')[0]}.xls`;
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        alert('Error exporting model: ' + error.message);
      }
    });

    loadStatement('pl');
  }

  // Entity Rollup
  function setupEntityRollup() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;
    root.innerHTML = `
      <div class="entity-rollup">
        <div class="rollup-config">
          <h2>Entity Selection</h2>
          <div class="multi-select-buttons" id="rollup-entities">
            <button class="multi-select-button selected" data-entity="Global">Global</button>
            <button class="multi-select-button selected" data-entity="EMEA">EMEA</button>
            <button class="multi-select-button selected" data-entity="Americas">Americas</button>
            <button class="multi-select-button" data-entity="APAC">APAC</button>
          </div>
          <button class="rollup-button" id="rollup-btn">Roll Up Entities</button>
        </div>
        <div id="rollup-results" style="display: none;"></div>
      </div>
    `;

    let selectedEntities = ['Global', 'EMEA', 'Americas'];

    root.querySelectorAll('#rollup-entities button').forEach(btn => {
      btn.addEventListener('click', () => {
        btn.classList.toggle('selected');
        const entity = btn.dataset.entity;
        if (selectedEntities.includes(entity)) {
          selectedEntities = selectedEntities.filter(e => e !== entity);
        } else {
          selectedEntities.push(entity);
        }
      });
    });

    root.querySelector('#rollup-btn').addEventListener('click', async () => {
      const btn = root.querySelector('#rollup-btn');
      const resultsDiv = root.querySelector('#rollup-results');
      
      btn.disabled = true;
      btn.textContent = 'Rolling up...';
      resultsDiv.style.display = 'none';

      try {
        const sources = [{ source_id: 'internal_db', connection_info: {} }];
        const result = await getPLConsolidation(sources, {
          entities: selectedEntities,
          periods: ['2025-Q1', '2025-Q2', '2025-Q3'],
          scenarios: ['Actual'],
        });

        // Group by line item and aggregate across entities
        const groupedByLineItem = {};
        result.rows.forEach(row => {
          const lineItem = row.lineItem || row.line_item;
          if (!groupedByLineItem[lineItem]) {
            groupedByLineItem[lineItem] = {
              lineItem,
              level: row.level,
              entities: {},
              total: 0,
            };
          }
          const entity = row.entity || 'Global';
          if (!groupedByLineItem[lineItem].entities[entity]) {
            groupedByLineItem[lineItem].entities[entity] = 0;
          }
          groupedByLineItem[lineItem].entities[entity] += row.actual || 0;
          groupedByLineItem[lineItem].total += row.actual || 0;
        });

        let html = `
          <div class="rollup-results-section">
            <h2>Consolidated P&L by Entity</h2>
            <div class="rollup-table-container">
              <table class="rollup-table">
                <thead>
                  <tr>
                    <th>Line Item</th>
                    ${selectedEntities.map(e => `<th>${e}</th>`).join('')}
                    <th>Total</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
        `;

        Object.values(groupedByLineItem).forEach(item => {
          const isParent = item.level === 'parent';
          html += `
            <tr class="rollup-row ${isParent ? 'parent-row' : 'child-row'}" data-line-item="${item.lineItem}">
              <td style="padding-left: ${isParent ? '0' : '24px'}; font-weight: ${isParent ? '600' : '400'}">
                ${item.lineItem}
              </td>
              ${selectedEntities.map(entity => `
                <td>${formatCurrency(item.entities[entity] || 0)}</td>
              `).join('')}
              <td style="font-weight: 600">${formatCurrency(item.total)}</td>
              <td>
                <button class="expand-button" data-line-item="${item.lineItem}">
                  ${isParent ? '▼' : ''}
                </button>
              </td>
            </tr>
          `;
        });

        html += `
                </tbody>
              </table>
            </div>
          </div>
        `;

        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';

        // Add expand/collapse functionality
        resultsDiv.querySelectorAll('.expand-button').forEach(btn => {
          btn.addEventListener('click', () => {
            const lineItem = btn.dataset.lineItem;
            const row = btn.closest('tr');
            const nextRow = row.nextElementSibling;
            // Toggle visibility of child rows
            if (nextRow && nextRow.classList.contains('child-row')) {
              nextRow.style.display = nextRow.style.display === 'none' ? '' : 'none';
            }
          });
        });
      } catch (error) {
        alert('Error: ' + error.message);
        console.error(error);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Roll Up Entities';
      }
    });
  }

  // Export Bridge
  function setupExportBridge() {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;
    root.innerHTML = `
      <div class="export-bridge">
        <div class="export-header">
          <h2>Export & BI Bridge</h2>
          <p>Export consolidated tables into Excel, CSV, or BI tools with one click.</p>
        </div>
        <div class="export-actions">
          <button class="load-preview-button" id="load-preview-btn">Load Preview</button>
        </div>
        <div id="export-results" style="display: none;"></div>
        <div class="export-options">
          <h3>Export Options</h3>
          <div class="export-buttons">
            <button class="export-button" id="export-csv-btn">Download as CSV</button>
            <button class="export-button" id="export-excel-btn">Download as Excel</button>
            <button class="export-button" id="copy-api-btn">Copy API URL for BI Tools</button>
          </div>
        </div>
      </div>
    `;

    root.querySelector('#load-preview-btn').addEventListener('click', async () => {
      try {
        const result = await getPLConsolidation(
          [{ source_id: 'internal_db', connection_info: {} }],
          { entities: ['Global'], periods: ['2025-Q1', '2025-Q2'] }
        );

        let html = `
          <div class="preview-section">
            <h3>Preview (Last Consolidated Result)</h3>
            <div class="preview-table-container">
              <table class="preview-table">
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
        `;

        result.rows.slice(0, 10).forEach(row => {
          html += `
            <tr>
              <td>${row.lineItem || row.line_item}</td>
              <td>${row.entity || '-'}</td>
              <td>${row.period || '-'}</td>
              <td>${formatCurrency(row.actual || 0)}</td>
              <td>${formatCurrency(row.budget || 0)}</td>
              <td>${formatCurrency(row.forecast || 0)}</td>
            </tr>
          `;
        });

        html += `
                </tbody>
              </table>
            </div>
          </div>
        `;

        root.querySelector('#export-results').innerHTML = html;
        root.querySelector('#export-results').style.display = 'block';
      } catch (error) {
        alert('Error: ' + error.message);
      }
    });

    root.querySelector('#export-csv-btn').addEventListener('click', async () => {
      try {
        const result = await getPLConsolidation(
          [{ source_id: 'internal_db', connection_info: {} }],
          { entities: ['Global'], periods: ['2025-Q1', '2025-Q2'] }
        );

        // Convert to CSV
        const headers = ['Line Item', 'Entity', 'Period', 'Actual', 'Budget', 'Forecast', 'Variance %'];
        const csvRows = [headers.join(',')];
        
        result.rows.forEach(row => {
          const values = [
            `"${row.lineItem || row.line_item}"`,
            `"${row.entity || ''}"`,
            `"${row.period || ''}"`,
            row.actual || 0,
            row.budget || 0,
            row.forecast || 0,
            row.variancePct || row.variance_pct || 0,
          ];
          csvRows.push(values.join(','));
        });

        const csv = csvRows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `finance-export-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        alert('Error exporting CSV: ' + error.message);
      }
    });

    root.querySelector('#export-excel-btn').addEventListener('click', async () => {
      try {
        const result = await getPLConsolidation(
          [{ source_id: 'internal_db', connection_info: {} }],
          { entities: ['Global'], periods: ['2025-Q1', '2025-Q2'] }
        );

        // Create Excel-like HTML table and download
        let html = `
          <html>
            <head>
              <meta charset="utf-8">
              <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
              </style>
            </head>
            <body>
              <table>
                <thead>
                  <tr>
                    <th>Line Item</th>
                    <th>Entity</th>
                    <th>Period</th>
                    <th>Actual</th>
                    <th>Budget</th>
                    <th>Forecast</th>
                    <th>Variance %</th>
                  </tr>
                </thead>
                <tbody>
        `;

        result.rows.forEach(row => {
          html += `
            <tr>
              <td>${row.lineItem || row.line_item}</td>
              <td>${row.entity || ''}</td>
              <td>${row.period || ''}</td>
              <td>${row.actual || 0}</td>
              <td>${row.budget || 0}</td>
              <td>${row.forecast || 0}</td>
              <td>${row.variancePct || row.variance_pct || 0}</td>
            </tr>
          `;
        });

        html += `
                </tbody>
              </table>
            </body>
          </html>
        `;

        const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `finance-export-${new Date().toISOString().split('T')[0]}.xls`;
        a.click();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        alert('Error exporting Excel: ' + error.message);
      }
    });

    root.querySelector('#copy-api-btn').addEventListener('click', () => {
      const apiUrl = `${window.location.origin}${API_BASE || ''}/api/finance-studio/consolidate`;
      navigator.clipboard.writeText(apiUrl).then(() => {
        const btn = root.querySelector('#copy-api-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied!';
        setTimeout(() => {
          btn.textContent = originalText;
        }, 2000);
      }).catch(() => {
        alert('Failed to copy. URL: ' + apiUrl);
      });
    });
  }

  // Main initialization
  function initFinanceStudio() {
    try {
      const root = document.getElementById('finance-studio-root');
      if (!root) {
        console.warn('Finance Studio root element not found');
        return;
      }

      console.log('Initializing Finance Studio...');

      // Check if APP_TILES is defined
      if (!APP_TILES || APP_TILES.length === 0) {
        console.error('APP_TILES is not defined or empty!');
        root.innerHTML = '<div style="padding: 2rem; text-align: center;"><h2>Finance Studio</h2><p style="color: #ef4444;">Error: APP_TILES not defined</p></div>';
        return;
      }

      const tilesHTML = getAppTilesHTML();
      console.log('Generated tiles HTML length:', tilesHTML.length);
      console.log('Number of app tiles:', APP_TILES.length);

      if (!tilesHTML || tilesHTML.trim().length === 0) {
        console.error('getAppTilesHTML() returned empty string!');
        root.innerHTML = '<div style="padding: 2rem; text-align: center;"><h2>Finance Studio</h2><p style="color: #ef4444;">Error: Failed to generate app tiles</p></div>';
        return;
      }

      root.innerHTML = `
        <div class="finance-studio-landing">
          <div class="finance-studio-header-section">
            <h1>Finance Studio</h1>
            <p class="finance-studio-subtitle">
              Interactive apps for consolidation, reporting, visualization, and modeling.
            </p>
          </div>
          <div class="app-tiles-grid">
            ${tilesHTML}
          </div>
        </div>
      `;

      // Add click handlers for app tiles
      const buttons = root.querySelectorAll('.app-tile-launch-button');
      console.log('Found', buttons.length, 'app tile buttons');
      
      if (buttons.length === 0) {
        console.warn('No app tile buttons found! HTML:', root.innerHTML.substring(0, 200));
      }
      
      buttons.forEach(button => {
        button.addEventListener('click', (e) => {
          const appId = e.target.dataset.appId || e.target.closest('button')?.dataset.appId;
          console.log('Launching app:', appId);
          if (appId) {
            loadApp(appId);
          }
        });
      });
      
      console.log('Finance Studio initialized successfully');
    } catch (error) {
      console.error('Error in initFinanceStudio:', error);
      const root = document.getElementById('finance-studio-root');
      if (root) {
        root.innerHTML = '<div style="padding: 2rem; text-align: center;"><h2>Finance Studio</h2><p style="color: #ef4444;">Error initializing: ' + error.message + '</p><pre style="text-align: left; font-size: 0.75rem; max-width: 600px; margin: 1rem auto; background: #fee2e2; padding: 1rem; border-radius: 8px;">' + error.stack + '</pre></div>';
      }
    }
  }

  function loadApp(appId) {
    const root = document.getElementById('finance-studio-root');
    if (!root) return;

    root.innerHTML = `
      <div class="finance-studio-app-view">
        <div class="finance-studio-header">
          <button onclick="window.financeStudioBackToTiles()" class="back-button">← Back</button>
          <h1>Finance Studio</h1>
        </div>
        <div class="finance-studio-app-content">
        </div>
      </div>
    `;

    const contentDiv = root.querySelector('.finance-studio-app-content');
    
    switch(appId) {
      case 'data-consolidation':
        contentDiv.innerHTML = renderDataConsolidationStudio();
        setupDataConsolidationStudio();
        break;
      case 'board-reports':
        contentDiv.innerHTML = renderBoardReadyReports();
        setupBoardReadyReports();
        break;
      case 'visualization':
        contentDiv.innerHTML = renderVisualizationStudio();
        setupVisualizationStudio();
        break;
      case 'three-statement':
        contentDiv.innerHTML = renderThreeStatementModeling();
        setupThreeStatementModeling();
        break;
      case 'entity-rollup':
        setupEntityRollup();
        break;
      case 'export-bridge':
        setupExportBridge();
        break;
      default:
        contentDiv.innerHTML = '<p>App not found</p>';
    }
  }

  window.financeStudioBackToTiles = function() {
    initFinanceStudio();
  };

  // Export for use in app.js
  window.initFinanceStudio = initFinanceStudio;

  // Auto-initialize if root exists and is visible
  function tryAutoInit() {
    const root = document.getElementById('finance-studio-root');
    if (root) {
      // Check if the parent view is visible
      const view = document.getElementById('finance-studio-view');
      if (view && !view.classList.contains('hidden')) {
        console.log('Finance Studio view is visible, initializing...');
        initFinanceStudio();
        return true;
      }
    }
    return false;
  }

  // Try multiple times
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(tryAutoInit, 100);
      setTimeout(tryAutoInit, 500);
      setTimeout(tryAutoInit, 1000);
    });
  } else {
    setTimeout(tryAutoInit, 100);
    setTimeout(tryAutoInit, 500);
    setTimeout(tryAutoInit, 1000);
  }
  
  // Also listen for when the view becomes visible
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
        const view = document.getElementById('finance-studio-view');
        if (view && !view.classList.contains('hidden')) {
          const root = document.getElementById('finance-studio-root');
          if (root && (!root.innerHTML.trim() || root.innerHTML.includes('Loading'))) {
            console.log('Finance Studio view became visible, initializing...');
            initFinanceStudio();
          }
        }
      }
    });
  });
  
  // Observe the finance-studio-view element
  setTimeout(() => {
    const view = document.getElementById('finance-studio-view');
    if (view) {
      observer.observe(view, { attributes: true, attributeFilter: ['class'] });
    }
  }, 500);
})();
