const API_BASE = '';

// Status polling
let statusInterval = null;
let totalPnL = 0;

// Toast notification system
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-triangle';

    toast.innerHTML = `
        <i class="fas ${icon} toast-icon"></i>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Currency formatter
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Loading state helpers
function setLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    if (loading) {
        btn.classList.add('loading');
        btn.disabled = true;
    } else {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    checkAPIHealth();
    startStatusPolling();
});

function initializeEventListeners() {
    // V4 Controls
    document.getElementById('v4Start').addEventListener('click', startV4Runner);
    document.getElementById('v4Stop').addEventListener('click', stopV4Runner);
    document.getElementById('v4Refresh').addEventListener('click', refreshV4Status);

    // Analysis
    document.getElementById('checkRegime').addEventListener('click', checkRegime);
    document.getElementById('selectUniverse').addEventListener('click', selectUniverse);

    // Legacy
    document.getElementById('v3Start').addEventListener('click', startV3Runner);
}

// API Health Check
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE}/`);
        const data = await response.json();
        updateAPIStatus(true);
    } catch (error) {
        updateAPIStatus(false);
    }
}

function updateAPIStatus(online) {
    const statusDot = document.getElementById('apiStatus');
    const statusText = document.getElementById('apiStatusText');

    if (online) {
        statusDot.classList.add('online');
        statusText.textContent = 'API Online';
    } else {
        statusDot.classList.remove('online');
        statusText.textContent = 'API Offline';
    }
}

// V4 Runner Functions
async function startV4Runner() {
    const mode = document.getElementById('v4Mode').value;
    const symbolsText = document.getElementById('v4Symbols').value;
    const symbols = symbolsText.split(',').map(s => s.trim());

    // Fix: Get all checked checkboxes within the checkbox-group
    const strategies = [];
    document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked').forEach(cb => {
        strategies.push(cb.value);
    });

    if (strategies.length === 0) {
        showToast('Error', 'Please select at least one strategy', 'error');
        return;
    }

    setLoading('v4Start', true);

    try {
        const response = await fetch(`${API_BASE}/v4/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode,
                symbols,
                strategies,
                use_regime: true,
                use_universe: true
            })
        });

        const data = await response.json();

        if (response.ok) {
            showToast('V4 Engine Started', `Running in ${mode} mode with ${symbols.length} symbols`, 'success');
            setTimeout(refreshV4Status, 1000);
        } else {
            showToast('Start Failed', data.detail || 'Unknown error', 'error');
        }
    } catch (error) {
        showToast('Connection Error', error.message, 'error');
    } finally {
        setLoading('v4Start', false);
    }
}

async function stopV4Runner() {
    setLoading('v4Stop', true);

    try {
        const response = await fetch(`${API_BASE}/v4/stop`, { method: 'POST' });
        const data = await response.json();

        showToast('V4 Engine Stopped', 'All trading activity halted', 'info');
        setTimeout(refreshV4Status, 1000);
    } catch (error) {
        showToast('Stop Failed', error.message, 'error');
    } finally {
        setLoading('v4Stop', false);
    }
}

async function refreshV4Status() {
    try {
        const response = await fetch(`${API_BASE}/v4/status`);
        const data = await response.json();

        // Update status badge
        const statusBadge = document.getElementById('v4Status');
        if (data.status === 'running') {
            statusBadge.textContent = 'RUNNING';
            statusBadge.classList.add('running');
        } else {
            statusBadge.textContent = 'OFFLINE';
            statusBadge.classList.remove('running');
        }

        // Calculate total PnL
        totalPnL = 0;

        // Update stats
        const statsDiv = document.getElementById('v4Stats');
        if (data.stats && data.stats.length > 0) {
            let html = '<h3 style="margin-bottom: 1rem; font-size: 0.875rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;"><i class="fas fa-chart-line"></i> Active Engines</h3>';

            data.stats.forEach(stat => {
                const pnlClass = stat.pnl >= 0 ? 'positive' : 'negative';
                totalPnL += stat.pnl;

                html += `
                    <div class="stat-item">
                        <span class="stat-label">
                            <span class="symbol-badge"><i class="fab fa-bitcoin"></i> ${stat.symbol.replace('/USDT', '').replace('/USD', '')}</span>
                            <span style="color: var(--text-secondary); margin-left: 0.5rem;">${stat.strategy}</span>
                        </span>
                        <span class="stat-value ${pnlClass}">
                            ${stat.state} | ${formatCurrency(stat.pnl)} | ${stat.trades} trades
                        </span>
                    </div>
                `;
            });

            statsDiv.innerHTML = html;
        } else {
            statsDiv.innerHTML = '';
        }

        // Update header total PnL
        document.getElementById('totalPnL').textContent = formatCurrency(totalPnL);
        document.getElementById('totalPnL').className = totalPnL >= 0 ? '' : 'negative';

    } catch (error) {
        console.error('Failed to refresh status:', error);
    }
}

function startStatusPolling() {
    statusInterval = setInterval(() => {
        refreshV4Status();
    }, 5000); // Poll every 5 seconds
}

// Analysis Functions
async function checkRegime() {
    const symbol = document.getElementById('regimeSymbol').value;
    const dateInput = document.getElementById('regimeDate').value;

    const payload = { symbol };
    if (dateInput) {
        payload.date = `${dateInput}T00:00:00`;
    }

    setLoading('checkRegime', true);

    try {
        const response = await fetch(`${API_BASE}/analyze/regime`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            const resultDiv = document.getElementById('regimeResult');
            const regimeClass = data.regime === 'TRENDING' ? 'trending' : 'ranging';
            resultDiv.innerHTML = `
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <span class="regime-badge ${regimeClass}">
                        <i class="fas ${data.regime === 'TRENDING' ? 'fa-arrow-trend-up' : 'fa-wave-square'}"></i>
                        ${data.regime}
                    </span>
                </div>
                <div class="stat-item">
                    <span class="stat-label"><i class="fab fa-bitcoin"></i> Symbol</span>
                    <span class="stat-value">${data.symbol}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label"><i class="fas fa-calendar"></i> Date</span>
                    <span class="stat-value">${new Date(data.date).toLocaleDateString()}</span>
                </div>
            `;
            showToast('Regime Analysis Complete', `${symbol} is ${data.regime}`, 'success');
        } else {
            showToast('Analysis Failed', data.detail || 'Unknown error', 'error');
        }
    } catch (error) {
        showToast('Connection Error', error.message, 'error');
    } finally {
        setLoading('checkRegime', false);
    }
}

async function selectUniverse() {
    const minVolume = parseFloat(document.getElementById('minVolume').value);
    const minPrice = parseFloat(document.getElementById('minPrice').value);

    setLoading('selectUniverse', true);

    try {
        const response = await fetch(`${API_BASE}/analyze/universe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                min_volume: minVolume,
                min_price: minPrice,
                blacklist: []
            })
        });

        const data = await response.json();

        if (response.ok) {
            const resultDiv = document.getElementById('universeResult');
            resultDiv.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label"><i class="fas fa-list"></i> Candidates</span>
                    <span class="stat-value">${data.candidates_count}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label"><i class="fas fa-check-circle"></i> Selected</span>
                    <span class="stat-value positive">${data.selected_count}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label"><i class="fas fa-coins"></i> Symbols</span>
                    <span class="stat-value" style="font-size: 0.75rem; line-height: 1.4;">
                        ${data.selected.map(s => `<span class="symbol-badge">${s.replace('/USDT', '').replace('/USD', '')}</span>`).join(' ')}
                    </span>
                </div>
            `;
            showToast('Universe Selection Complete', `${data.selected_count} symbols selected from ${data.candidates_count}`, 'success');
        } else {
            showToast('Selection Failed', data.detail || 'Unknown error', 'error');
        }
    } catch (error) {
        showToast('Connection Error', error.message, 'error');
    } finally {
        setLoading('selectUniverse', false);
    }
}

// Legacy Functions
async function startV3Runner() {
    const symbolsText = document.getElementById('v3Symbols').value;
    const symbols = symbolsText.split(',').map(s => s.trim());

    setLoading('v3Start', true);

    try {
        const response = await fetch(`${API_BASE}/legacy/v3/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbols,
                log_level: 'INFO'
            })
        });

        const data = await response.json();

        const resultDiv = document.getElementById('v3Result');
        resultDiv.innerHTML = `
            <div class="stat-item">
                <span class="stat-label"><i class="fas fa-check"></i> Status</span>
                <span class="stat-value positive">${data.status}</span>
            </div>
            <div class="stat-item" style="word-break: break-all;">
                <span class="stat-label"><i class="fas fa-terminal"></i> Command</span>
                <span class="stat-value" style="font-size: 0.75rem;">${data.command}</span>
            </div>
        `;

        showToast('V3 Runner Started', 'Launched in new console window', 'success');
    } catch (error) {
        showToast('Launch Failed', error.message, 'error');
    } finally {
        setLoading('v3Start', false);
    }
}
