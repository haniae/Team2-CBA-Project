// Portfolio Dashboard JavaScript

let currentPortfolioId = null;
let holdingsData = [];
let sortColumn = null;
let sortDirection = 'asc';
let filteredHoldingsData = [];
let currentPage = 1;
let pageSize = 25;
let tableFilters = {
    sector: '',
    weightMin: '',
    weightMax: '',
    peMin: '',
    peMax: '',
    search: ''
};
let chartRefreshInterval = null;
let allSectors = new Set();

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    loadPortfolioList();
    initializeDragAndDrop();
    
    const portfolioSelect = document.getElementById('portfolio-select');
    portfolioSelect.addEventListener('change', function() {
        if (this.value) {
            loadPortfolioDashboard(this.value);
        } else {
            stopAutoRefresh();
        }
    });
    
    const holdingsFilter = document.getElementById('holdings-filter');
    if (holdingsFilter) {
        holdingsFilter.addEventListener('input', function() {
            tableFilters.search = this.value;
            applyFilters();
        });
    }
    
    // Initialize filter controls
    initializeTableFilters();
    
    // Initialize pagination
    initializePagination();
});

// Load list of available portfolios
async function loadPortfolioList() {
    try {
        const response = await fetch('/api/portfolio/list');
        const portfolios = await response.json();
        
        const select = document.getElementById('portfolio-select');
        select.innerHTML = '<option value="">Select portfolio...</option>';
        
        portfolios.forEach(portfolio => {
            const option = document.createElement('option');
            option.value = portfolio.portfolio_id;
            option.textContent = `${portfolio.name} (${portfolio.portfolio_id})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading portfolio list:', error);
        showError('Failed to load portfolio list');
    }
}

// Load portfolio dashboard data
async function loadPortfolioDashboard(portfolioId) {
    currentPortfolioId = portfolioId;
    currentPage = 1;
    
    try {
        // Load holdings, summary, and exposure in parallel
        const [holdingsResponse, summaryResponse, exposureResponse] = await Promise.all([
            fetch(`/api/portfolio/${portfolioId}/holdings`),
            fetch(`/api/portfolio/${portfolioId}/summary`),
            fetch(`/api/portfolio/${portfolioId}/exposure`)
        ]);
        
        if (!holdingsResponse.ok) throw new Error('Failed to load holdings');
        if (!summaryResponse.ok) throw new Error('Failed to load summary');
        if (!exposureResponse.ok) throw new Error('Failed to load exposure');
        
        const holdings = await holdingsResponse.json();
        const summary = await summaryResponse.json();
        const exposure = await exposureResponse.json();
        
        // Store holdings data
        holdingsData = holdings.holdings || [];
        
        // Extract all sectors for filter
        allSectors.clear();
        holdingsData.forEach(h => {
            if (h.sector) allSectors.add(h.sector);
        });
        updateSectorFilter();
        
        // Display all sections
        document.getElementById('action-buttons').style.display = 'flex';
        document.getElementById('holdings-section').style.display = 'block';
        document.getElementById('exposure-section').style.display = 'block';
        document.getElementById('factors-section').style.display = 'block';
        document.getElementById('top-holdings-section').style.display = 'block';
        document.getElementById('policy-section').style.display = 'block';
        
        // Reset filters
        resetFilters();
        
        // Render all components
        renderStats(summary);
        applyFilters(); // This will call renderHoldingsTable with filtered data
        renderSectorChart(exposure);
        renderFactorChart(exposure);
        renderTopHoldingsChart(holdingsData);
        
        // Mock policy compliance data (replace with real data when API is ready)
        renderPolicyCompliance(mockPolicyCompliance());
        
        // Start auto-refresh
        startAutoRefresh();
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
        showError('Failed to load portfolio data. Please ensure the portfolio has been uploaded.');
    }
}

// Render statistics cards
function renderStats(summary) {
    const statsDiv = document.getElementById('dashboard-stats');
    
    const stats = [
        {
            label: 'Total Value',
            value: formatCurrency(summary.total_market_value),
        },
        {
            label: 'Holdings',
            value: summary.num_holdings,
        },
        {
            label: 'Weighted Avg P/E',
            value: summary.weighted_avg_pe ? summary.weighted_avg_pe.toFixed(2) : 'N/A',
        },
        {
            label: 'Div Yield',
            value: summary.weighted_avg_dividend_yield ? (summary.weighted_avg_dividend_yield * 100).toFixed(2) + '%' : 'N/A',
        },
        {
            label: 'Sectors',
            value: summary.num_sectors,
        },
        {
            label: 'Top 10 Concentration',
            value: (summary.top_10_weight * 100).toFixed(2) + '%',
        }
    ];
    
    statsDiv.innerHTML = stats.map(stat => `
        <div class="stat-card">
            <h3>${stat.label}</h3>
            <div class="stat-value">${stat.value}</div>
        </div>
    `).join('');
}

// Render holdings table with pagination
function renderHoldingsTable(holdings) {
    const tbody = document.getElementById('holdings-body');
    
    if (!holdings || holdings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 40px;">No holdings data available</td></tr>';
        updatePaginationControls(0);
        return;
    }
    
    // Apply pagination
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const paginatedHoldings = holdings.slice(startIndex, endIndex);
    
    tbody.innerHTML = paginatedHoldings.map(holding => `
        <tr>
            <td class="ticker">${holding.ticker}</td>
            <td>${holding.name || 'N/A'}</td>
            <td class="weight">${((holding.weight || 0) * 100).toFixed(2)}%</td>
            <td>${holding.shares ? holding.shares.toLocaleString() : 'N/A'}</td>
            <td>${holding.price ? formatCurrency(holding.price) : 'N/A'}</td>
            <td>${holding.market_value ? formatCurrency(holding.market_value) : 'N/A'}</td>
            <td>${holding.sector || 'N/A'}</td>
            <td>${holding.pe_ratio ? holding.pe_ratio.toFixed(2) : 'N/A'}</td>
            <td>${holding.dividend_yield ? (holding.dividend_yield * 100).toFixed(2) + '%' : 'N/A'}</td>
        </tr>
    `).join('');
    
    document.getElementById('holdings-count').textContent = `${holdings.length} holdings`;
    updatePaginationControls(holdings.length);
}

// Initialize table filters
function initializeTableFilters() {
    // Sector filter is updated dynamically
    const weightMin = document.getElementById('filter-weight-min');
    const weightMax = document.getElementById('filter-weight-max');
    const peMin = document.getElementById('filter-pe-min');
    const peMax = document.getElementById('filter-pe-max');
    
    if (weightMin) weightMin.addEventListener('input', () => { tableFilters.weightMin = weightMin.value; applyFilters(); });
    if (weightMax) weightMax.addEventListener('input', () => { tableFilters.weightMax = weightMax.value; applyFilters(); });
    if (peMin) peMin.addEventListener('input', () => { tableFilters.peMin = peMin.value; applyFilters(); });
    if (peMax) peMax.addEventListener('input', () => { tableFilters.peMax = peMax.value; applyFilters(); });
}

// Update sector filter dropdown
function updateSectorFilter() {
    const sectorFilter = document.getElementById('filter-sector');
    if (!sectorFilter) return;
    
    sectorFilter.innerHTML = '<option value="">All Sectors</option>';
    Array.from(allSectors).sort().forEach(sector => {
        const option = document.createElement('option');
        option.value = sector;
        option.textContent = sector;
        sectorFilter.appendChild(option);
    });
    
    sectorFilter.addEventListener('change', () => {
        tableFilters.sector = sectorFilter.value;
        applyFilters();
    });
}

// Apply all filters
function applyFilters() {
    filteredHoldingsData = holdingsData.filter(holding => {
        // Search filter
        if (tableFilters.search) {
            const searchLower = tableFilters.search.toLowerCase();
            const matchesSearch = 
                holding.ticker?.toLowerCase().includes(searchLower) ||
                holding.name?.toLowerCase().includes(searchLower) ||
                holding.sector?.toLowerCase().includes(searchLower);
            if (!matchesSearch) return false;
        }
        
        // Sector filter
        if (tableFilters.sector && holding.sector !== tableFilters.sector) {
            return false;
        }
        
        // Weight filters
        const weight = (holding.weight || 0) * 100;
        if (tableFilters.weightMin && weight < parseFloat(tableFilters.weightMin)) return false;
        if (tableFilters.weightMax && weight > parseFloat(tableFilters.weightMax)) return false;
        
        // P/E filters
        const pe = holding.pe_ratio || 0;
        if (tableFilters.peMin && pe < parseFloat(tableFilters.peMin)) return false;
        if (tableFilters.peMax && pe > parseFloat(tableFilters.peMax)) return false;
        
        return true;
    });
    
    // Apply current sort
    if (sortColumn) {
        filteredHoldingsData.sort((a, b) => {
            let aVal = a[sortColumn];
            let bVal = b[sortColumn];
            
            if (sortColumn === 'weight' || sortColumn === 'price' || sortColumn === 'market_value' || 
                sortColumn === 'pe_ratio' || sortColumn === 'dividend_yield') {
                aVal = aVal || 0;
                bVal = bVal || 0;
            } else {
                aVal = (aVal || '').toString();
                bVal = (bVal || '').toString();
            }
            
            if (sortDirection === 'asc') {
                return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
            } else {
                return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
            }
        });
    }
    
    currentPage = 1; // Reset to first page
    renderHoldingsTable(filteredHoldingsData);
}

// Reset all filters
function resetFilters() {
    tableFilters = {
        sector: '',
        weightMin: '',
        weightMax: '',
        peMin: '',
        peMax: '',
        search: ''
    };
    const holdingsFilter = document.getElementById('holdings-filter');
    if (holdingsFilter) holdingsFilter.value = '';
    const sectorFilter = document.getElementById('filter-sector');
    if (sectorFilter) sectorFilter.value = '';
    const weightMin = document.getElementById('filter-weight-min');
    if (weightMin) weightMin.value = '';
    const weightMax = document.getElementById('filter-weight-max');
    if (weightMax) weightMax.value = '';
    const peMin = document.getElementById('filter-pe-min');
    if (peMin) peMin.value = '';
    const peMax = document.getElementById('filter-pe-max');
    if (peMax) peMax.value = '';
}

// Initialize pagination
function initializePagination() {
    const pageSizeSelect = document.getElementById('page-size-select');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', function() {
            pageSize = parseInt(this.value);
            currentPage = 1;
            renderHoldingsTable(filteredHoldingsData);
        });
    }
}

// Update pagination controls
function updatePaginationControls(totalItems) {
    const totalPages = Math.ceil(totalItems / pageSize);
    const paginationDiv = document.getElementById('pagination-controls');
    if (!paginationDiv) return;
    
    paginationDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <span>Page ${currentPage} of ${totalPages || 1}</span>
            <button class="btn btn-secondary" onclick="changePage(-1)" ${currentPage === 1 ? 'disabled' : ''}>Previous</button>
            <button class="btn btn-secondary" onclick="changePage(1)" ${currentPage >= totalPages ? 'disabled' : ''}>Next</button>
            <select id="page-size-select" style="padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px;">
                <option value="25" ${pageSize === 25 ? 'selected' : ''}>25 per page</option>
                <option value="50" ${pageSize === 50 ? 'selected' : ''}>50 per page</option>
                <option value="100" ${pageSize === 100 ? 'selected' : ''}>100 per page</option>
            </select>
            <button class="btn btn-secondary" onclick="exportFilteredTable()">Export Filtered CSV</button>
        </div>
    `;
    
    // Re-initialize page size listener
    const pageSizeSelect = document.getElementById('page-size-select');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', function() {
            pageSize = parseInt(this.value);
            currentPage = 1;
            renderHoldingsTable(filteredHoldingsData);
        });
    }
}

// Change page
function changePage(delta) {
    const totalPages = Math.ceil(filteredHoldingsData.length / pageSize);
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderHoldingsTable(filteredHoldingsData);
    }
}

// Export filtered table to CSV
function exportFilteredTable() {
    if (!filteredHoldingsData || filteredHoldingsData.length === 0) {
        alert('No data to export');
        return;
    }
    
    const headers = ['Ticker', 'Name', 'Weight (%)', 'Shares', 'Price', 'Market Value', 'Sector', 'P/E', 'Dividend Yield'];
    const rows = filteredHoldingsData.map(h => [
        h.ticker || '',
        h.name || '',
        ((h.weight || 0) * 100).toFixed(2),
        h.shares || '',
        h.price || '',
        h.market_value || '',
        h.sector || '',
        h.pe_ratio || '',
        h.dividend_yield ? (h.dividend_yield * 100).toFixed(2) + '%' : ''
    ]);
    
    const csv = [
        headers.join(','),
        ...rows.map(r => r.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `portfolio_holdings_${currentPortfolioId}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    showSuccess('Holdings exported to CSV');
}

// Initialize drag-and-drop file upload
function initializeDragAndDrop() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    
    if (!uploadZone || !fileInput) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.add('drag-over');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.remove('drag-over');
        }, false);
    });
    
    uploadZone.addEventListener('drop', handleDrop, false);
    uploadZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
}

// Handle file drop
async function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// Handle file select
async function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

// Handle files (upload)
async function handleFiles(files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    showProgressModal('Uploading portfolio file...', 0);
    
    try {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateProgress(percentComplete);
            }
        });
        
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                closeProgressModal();
                showSuccess(`Portfolio uploaded successfully: ${result.portfolio_id}`);
                loadPortfolioList();
                // Auto-select the new portfolio
                setTimeout(() => {
                    const select = document.getElementById('portfolio-select');
                    select.value = result.portfolio_id;
                    select.dispatchEvent(new Event('change'));
                }, 500);
            } else {
                closeProgressModal();
                const error = JSON.parse(xhr.responseText);
                showError(`Upload failed: ${error.detail || error.message}`);
            }
        });
        
        xhr.addEventListener('error', () => {
            closeProgressModal();
            showError('Upload failed. Please try again.');
        });
        
        xhr.open('POST', '/api/portfolio/upload');
        xhr.send(formData);
        
    } catch (error) {
        closeProgressModal();
        console.error('Upload error:', error);
        showError('Failed to upload file: ' + error.message);
    }
}

// Show progress modal
function showProgressModal(message, progress) {
    let modal = document.getElementById('progress-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'progress-modal';
        modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;';
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; padding: 32px; max-width: 500px; width: 90%;">
                <h3 style="margin: 0 0 20px 0;">${message}</h3>
                <div style="background: #f3f4f6; border-radius: 8px; height: 24px; overflow: hidden;">
                    <div id="progress-bar" style="background: #667eea; height: 100%; width: ${progress}%; transition: width 0.3s;"></div>
                </div>
                <p id="progress-text" style="margin: 12px 0 0 0; text-align: center; color: #666;">${progress.toFixed(0)}%</p>
                <button id="cancel-operation" onclick="cancelOperation()" style="margin-top: 20px; padding: 8px 16px; background: #f3f4f6; border: none; border-radius: 6px; cursor: pointer;">Cancel</button>
            </div>
        `;
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
    updateProgress(progress);
}

// Update progress
function updateProgress(percent) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    if (progressBar) progressBar.style.width = percent + '%';
    if (progressText) progressText.textContent = percent.toFixed(0) + '%';
}

// Close progress modal
function closeProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) modal.style.display = 'none';
}

// Cancel operation
function cancelOperation() {
    // TODO: Implement cancellation for long-running operations
    closeProgressModal();
}

// Start auto-refresh for charts
function startAutoRefresh() {
    stopAutoRefresh();
    chartRefreshInterval = setInterval(() => {
        if (currentPortfolioId) {
            refreshCharts();
        }
    }, 30000); // 30 seconds
    
    // Update last refreshed time
    updateLastRefreshedTime();
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (chartRefreshInterval) {
        clearInterval(chartRefreshInterval);
        chartRefreshInterval = null;
    }
}

// Refresh charts (reload exposure data)
async function refreshCharts() {
    if (!currentPortfolioId) return;
    
    try {
        const exposureResponse = await fetch(`/api/portfolio/${currentPortfolioId}/exposure`);
        if (exposureResponse.ok) {
            const exposure = await exposureResponse.json();
            renderSectorChart(exposure);
            renderFactorChart(exposure);
            updateLastRefreshedTime();
        }
    } catch (error) {
        console.error('Error refreshing charts:', error);
    }
}

// Update last refreshed time
function updateLastRefreshedTime() {
    const refreshIndicator = document.getElementById('last-refreshed');
    if (refreshIndicator) {
        const now = new Date();
        refreshIndicator.textContent = `Last updated: ${now.toLocaleTimeString()}`;
    }
}

// Render sector exposure chart
function renderSectorChart(exposure) {
    const sectorExposure = exposure.sector_exposure || {};
    
    const sectors = Object.keys(sectorExposure);
    const values = Object.values(sectorExposure).map(v => v * 100);
    
    const data = [{
        x: values,
        y: sectors,
        type: 'bar',
        orientation: 'h',
        marker: {
            color: '#667eea'
        }
    }];
    
    const layout = {
        title: 'Sector Exposure',
        xaxis: { title: 'Weight (%)' },
        yaxis: { title: '' },
        margin: { l: 150, r: 50, t: 50, b: 50 },
        height: 400
    };
    
    Plotly.newPlot('sectorChart', data, layout, { responsive: true });
}

// Render factor exposure chart
function renderFactorChart(exposure) {
    const factorExposure = exposure.factor_exposure || {};
    
    const factors = Object.keys(factorExposure);
    const values = Object.values(factorExposure);
    
    const data = [{
        type: 'scatterpolar',
        r: values,
        theta: factors,
        fill: 'toself',
        marker: { color: '#764ba2' }
    }];
    
    const layout = {
        polar: {
            radialaxis: {
                visible: true,
                range: [-1, 1]
            }
        },
        title: 'Factor Exposure',
        showlegend: false,
        height: 400
    };
    
    Plotly.newPlot('factorChart', data, layout, { responsive: true });
}

// Render top holdings pie chart
function renderTopHoldingsChart(holdings) {
    // Get top 10 holdings
    const topHoldings = holdings
        .sort((a, b) => (b.weight || 0) - (a.weight || 0))
        .slice(0, 10);
    
    const labels = topHoldings.map(h => h.ticker);
    const values = topHoldings.map(h => (h.weight || 0) * 100);
    
    const data = [{
        labels: labels,
        values: values,
        type: 'pie',
        hole: 0.4,
        marker: {
            colors: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe', 
                     '#43e97b', '#fa709a', '#fee140', '#fa8d72', '#7873f5']
        }
    }];
    
    const layout = {
        title: 'Top 10 Holdings',
        showlegend: true,
        height: 400
    };
    
    Plotly.newPlot('topHoldingsChart', data, layout, { responsive: true });
}

// Render policy compliance
function renderPolicyCompliance(policies) {
    const complianceDiv = document.getElementById('policy-compliance');
    
    complianceDiv.innerHTML = policies.map(policy => `
        <div class="compliance-item ${policy.status}">
            <div class="compliance-status ${policy.status}"></div>
            <div class="compliance-details">
                <div class="compliance-label">${policy.label}</div>
                <div class="compliance-value">${policy.detail}</div>
            </div>
        </div>
    `).join('');
}

// Mock policy compliance (replace with real API call)
function mockPolicyCompliance() {
    return [
        { label: 'Max Position Size', detail: '5.0% / Limit: 5.0%', status: 'compliant' },
        { label: 'Tech Sector Limit', detail: '28.5% / Limit: 35%', status: 'compliant' },
        { label: 'Tracking Error', detail: '2.1% / Limit: 2.5%', status: 'compliant' },
        { label: 'Healthcare Sector', detail: '18.2% / Limit: 25%', status: 'warning' },
    ];
}

// Sort table
function sortTable(column) {
    // Map column names from HTML to data property names
    const columnMap = {
        'ticker': 'ticker',
        'name': 'name',
        'weight': 'weight',
        'shares': 'shares',
        'price': 'price',
        'marketValue': 'market_value',
        'sector': 'sector',
        'pe': 'pe_ratio',
        'divYield': 'dividend_yield'
    };
    
    const mappedColumn = columnMap[column] || column;
    
    if (sortColumn === mappedColumn) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = mappedColumn;
        sortDirection = 'asc';
    }
    
    applyFilters(); // This will apply sort to filtered data
    updateSortIndicators();
}

// Update sort indicators in table header
function updateSortIndicators() {
    const headers = document.querySelectorAll('.holdings-table th');
    headers.forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
    });
    
    if (sortColumn) {
        const columnMap = {
            'ticker': 0, 'name': 1, 'weight': 2, 'shares': 3, 'price': 4,
            'marketValue': 5, 'sector': 6, 'pe': 7, 'divYield': 8
        };
        const index = columnMap[sortColumn];
        if (index !== undefined) {
            headers[index].classList.add(sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    }
}

// Open optimization modal
async function openOptimizationModal() {
    if (!currentPortfolioId) {
        alert('Please select a portfolio first');
        return;
    }
    
    const modal = document.getElementById('optimization-modal');
    const content = document.getElementById('optimization-content');
    
    modal.style.display = 'block';
    showProgressModal('Loading optimization options...', 0);
    
    try {
        // Fetch current holdings and constraints
        const [holdingsResponse, constraintsResponse] = await Promise.all([
            fetch(`/api/portfolio/${currentPortfolioId}/holdings`),
            fetch(`/api/portfolio/${currentPortfolioId}/constraints`)
        ]);
        
        const holdings = await holdingsResponse.json();
        const constraints = await constraintsResponse.json();
        
        closeProgressModal();
        
        content.innerHTML = `
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">
                    Objective:
                </label>
                <select id="opt-objective" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 6px;">
                    <option value="maximize_sharpe">Maximize Sharpe Ratio</option>
                    <option value="minimize_tracking_error">Minimize Tracking Error</option>
                    <option value="maximize_return">Maximize Return</option>
                </select>
            </div>
            
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">
                    Constraints:
                </label>
                <div id="constraints-list" style="max-height: 200px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px;">
                    ${constraints.length > 0 ? constraints.map(c => `
                        <label style="display: block; padding: 8px; margin-bottom: 4px;">
                            <input type="checkbox" checked style="margin-right: 8px;">
                            <strong>${c.constraint_type}</strong>: ${c.dimension || 'N/A'}
                        </label>
                    `).join('') : '<p style="color: #666;">No constraints defined</p>'}
                </div>
            </div>
            
            <div style="display: flex; gap: 12px; margin-top: 24px;">
                <button class="btn btn-primary" onclick="runOptimization()" style="flex: 1;">
                    Run Optimization
                </button>
                <button class="btn btn-secondary" onclick="closeOptimizationModal()" style="flex: 1;">
                    Cancel
                </button>
            </div>
        `;
        
    } catch (error) {
        closeProgressModal();
        console.error('Error loading optimization options:', error);
        content.innerHTML = `
            <div class="error">Failed to load optimization options. Please try again.</div>
            <button class="btn btn-secondary" onclick="closeOptimizationModal()" style="margin-top: 12px;">Close</button>
        `;
    }
}

// Close optimization modal
function closeOptimizationModal() {
    document.getElementById('optimization-modal').style.display = 'none';
}

// Run optimization
async function runOptimization() {
    const objective = document.getElementById('opt-objective').value;
    const content = document.getElementById('optimization-content');
    
    showProgressModal('Running optimization... This may take a few moments.', 0);
    
    try {
        const response = await fetch(`/api/portfolio/${currentPortfolioId}/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                objective: objective
            })
        });
        
        closeProgressModal();
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || error.message || 'Optimization failed');
        }
        
        const result = await response.json();
        
        content.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h3 style="margin-bottom: 12px;">Optimization Results</h3>
                <div style="background: #f9fafb; padding: 16px; border-radius: 6px;">
                    <div style="margin-bottom: 8px;"><strong>Status:</strong> ${result.status}</div>
                    ${result.iterations ? `<div style="margin-bottom: 8px;"><strong>Iterations:</strong> ${result.iterations}</div>` : ''}
                    ${result.objective_value !== undefined ? `<div><strong>Objective Value:</strong> ${result.objective_value.toFixed(4)}</div>` : ''}
                </div>
            </div>
            
            ${result.proposed_trades && result.proposed_trades.length > 0 ? `
                <div style="margin-bottom: 20px;">
                    <h3 style="margin-bottom: 12px;">Proposed Trades (${result.proposed_trades.length})</h3>
                    <div style="max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 6px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f3f4f6;">
                                    <th style="padding: 8px; text-align: left; font-size: 12px;">Ticker</th>
                                    <th style="padding: 8px; text-align: left; font-size: 12px;">Action</th>
                                    <th style="padding: 8px; text-align: right; font-size: 12px;">Shares</th>
                                    <th style="padding: 8px; text-align: right; font-size: 12px;">From</th>
                                    <th style="padding: 8px; text-align: right; font-size: 12px;">To</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${result.proposed_trades.map(trade => `
                                    <tr>
                                        <td style="padding: 8px;">${trade.ticker}</td>
                                        <td style="padding: 8px;">
                                            <span style="background: ${trade.action === 'BUY' ? '#d1fae5' : '#fee2e2'}; 
                                                         color: ${trade.action === 'BUY' ? '#065f46' : '#991b1b'}; 
                                                         padding: 2px 8px; border-radius: 4px; font-size: 12px;">
                                                ${trade.action}
                                            </span>
                                        </td>
                                        <td style="padding: 8px; text-align: right;">${trade.shares || 0}</td>
                                        <td style="padding: 8px; text-align: right;">${((trade.from_weight || 0) * 100).toFixed(2)}%</td>
                                        <td style="padding: 8px; text-align: right;">${((trade.to_weight || 0) * 100).toFixed(2)}%</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : '<p style="color: #666;">No trades proposed.</p>'}
            
            ${result.policy_flags && result.policy_flags.length > 0 ? `
                <div style="margin-bottom: 20px;">
                    <h3 style="margin-bottom: 12px;">Policy Flags</h3>
                    <div style="background: #fef3c7; padding: 12px; border-radius: 6px; border-left: 4px solid #f59e0b;">
                        ${result.policy_flags.map(flag => `<div style="margin-bottom: 4px;">⚠️ ${flag}</div>`).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div style="display: flex; gap: 12px; margin-top: 24px;">
                ${result.proposed_trades && result.proposed_trades.length > 0 ? `
                    <button class="btn btn-success" onclick="exportOptimizationResults()" style="flex: 1;">
                        Export to CSV
                    </button>
                ` : ''}
                <button class="btn btn-secondary" onclick="closeOptimizationModal()" style="flex: 1;">
                    Close
                </button>
            </div>
        `;
        
        // Store results globally for export
        window.lastOptimizationResults = result;
        
    } catch (error) {
        closeProgressModal();
        console.error('Optimization error:', error);
        content.innerHTML = `
            <div class="error">Optimization failed: ${error.message}</div>
            <button class="btn btn-secondary" onclick="openOptimizationModal()" style="margin-top: 12px;">Try Again</button>
        `;
    }
}

// Export optimization results
function exportOptimizationResults() {
    if (!window.lastOptimizationResults || !window.lastOptimizationResults.proposed_trades) {
        alert('No optimization results to export');
        return;
    }
    
    const trades = window.lastOptimizationResults.proposed_trades;
    const csv = [
        ['Ticker', 'Action', 'Shares', 'From Weight', 'To Weight'].join(','),
        ...trades.map(t => [
            t.ticker,
            t.action,
            t.shares || 0,
            ((t.from_weight || 0) * 100).toFixed(2) + '%',
            ((t.to_weight || 0) * 100).toFixed(2) + '%'
        ].join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `portfolio_optimization_${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    showSuccess('Optimization results exported to CSV');
}

// Run attribution
async function runAttribution() {
    if (!currentPortfolioId) {
        alert('Please select a portfolio first');
        return;
    }
    
    alert('Attribution feature coming soon. This will show Brinson attribution with waterfall charts.');
}

// Run stress test
async function runStressTest() {
    if (!currentPortfolioId) {
        alert('Please select a portfolio first');
        return;
    }
    
    alert('Stress test feature coming soon. This will show scenario analysis.');
}

// Toggle export menu
function toggleExportMenu() {
    const menu = document.getElementById('export-menu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

// Close export menu when clicking outside
document.addEventListener('click', function(event) {
    const exportDropdown = event.target.closest('.export-dropdown');
    const exportMenu = document.getElementById('export-menu');
    
    if (!exportDropdown && exportMenu && exportMenu.style.display === 'block') {
        exportMenu.style.display = 'none';
    }
});

// Export portfolio in specified format
async function exportPortfolio(format, buttonElement) {
    if (!currentPortfolioId) {
        alert('Please select a portfolio first');
        return;
    }
    
    // Close export menu
    const exportMenu = document.getElementById('export-menu');
    if (exportMenu) exportMenu.style.display = 'none';
    
    // Get the button that triggered this
    const button = buttonElement || (window.event ? window.event.target : null);
    const originalText = button ? button.textContent : '';
    
    if (button) {
        button.textContent = 'Generating...';
        button.disabled = true;
    }
    
    showProgressModal(`Generating ${format.toUpperCase()} export...`, 0);
    
    try {
        // Determine endpoint and filename based on format
        let endpoint, filename;
        switch(format) {
            case 'pptx':
                endpoint = `/api/portfolio/${currentPortfolioId}/export/pptx`;
                filename = `portfolio_${currentPortfolioId}_${new Date().toISOString().split('T')[0]}.pptx`;
                break;
            case 'pdf':
                endpoint = `/api/portfolio/${currentPortfolioId}/export/pdf`;
                filename = `portfolio_${currentPortfolioId}_${new Date().toISOString().split('T')[0]}.pdf`;
                break;
            case 'xlsx':
                endpoint = `/api/portfolio/${currentPortfolioId}/export/xlsx`;
                filename = `portfolio_${currentPortfolioId}_${new Date().toISOString().split('T')[0]}.xlsx`;
                break;
            default:
                closeProgressModal();
                alert('Invalid export format');
                return;
        }
        
        // Fetch export file
        const response = await fetch(endpoint);
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }
        
        // Get blob from response
        const blob = await response.blob();
        updateProgress(100);
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        closeProgressModal();
        
        // Restore button
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        
        // Show success message
        showSuccess(`Successfully exported ${format.toUpperCase()} file`);
        
    } catch (error) {
        closeProgressModal();
        console.error('Export error:', error);
        alert(`Failed to export portfolio: ${error.message}`);
        
        // Restore button
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
}

// Show error message
function showError(message) {
    const statsDiv = document.getElementById('dashboard-stats');
    if (statsDiv) {
        statsDiv.innerHTML = `<div class="error">${message}</div>`;
    } else {
        alert(message);
    }
}

// Show success message
function showSuccess(message) {
    // Create or update success notification
    let notification = document.getElementById('success-notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'success-notification';
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4caf50; color: white; padding: 16px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; font-size: 14px; max-width: 300px;';
        document.body.appendChild(notification);
    }
    
    notification.textContent = message;
    notification.style.display = 'block';
    
    // Hide after 3 seconds
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// Format currency with M/B notation
function formatCurrency(value) {
    if (!value) return 'N/A';
    const abs = Math.abs(value);
    let formatted;
    if (abs >= 1e9) {
        formatted = `$${(value / 1e9).toFixed(2)}B`;
    } else if (abs >= 1e6) {
        formatted = `$${(value / 1e6).toFixed(2)}M`;
    } else if (abs >= 1e3) {
        formatted = `$${(value / 1e3).toFixed(2)}K`;
    } else {
        formatted = `$${value.toFixed(2)}`;
    }
    return formatted;
}

