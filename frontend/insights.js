const API_BASE = 'http://localhost:8000';

let currentTrades = [];
let demoMode = false;

// Toast notification (reuse from app.js)
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAPIHealth();
    refreshAnalytics();
    startAutoRefresh();
});

async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE}/`);
        document.getElementById('apiStatus').classList.add('online');
        document.getElementById('apiStatusText').textContent = 'API Online';
    } catch (error) {
        document.getElementById('apiStatusText').textContent = 'API Offline';
    }
}

async function refreshAnalytics() {
    try {
        // Get profit analysis
        const analysisResponse = await fetch(`${API_BASE}/analytics/profit/analyze`);
        const analysis = await analysisResponse.json();

        updateMetrics(analysis);

        // Get trade history
        const tradesResponse = await fetch(`${API_BASE}/analytics/trades/history?limit=50`);
        const trades = await tradesResponse.json();
        currentTrades = trades;

        updateTradeList(trades);
        updateTopPerformers(analysis);
        drawEquityCurve(trades);

        if (!demoMode) {
            showToast('Analytics Updated', `Loaded ${trades.length} historical trades`, 'success');
        }
    } catch (error) {
        console.error('Failed to load analytics:', error);
        showToast('Load Failed', 'Could not load analytics data', 'error');
    }
}

async function loadDemoData() {
    try {
        const response = await fetch(`${API_BASE}/analytics/demo/generate`);
        const data = await response.json();

        currentTrades = data.trades;
        demoMode = true;

        updateTradeList(data.trades);
        drawEquityCurve(data.trades);

        // Calculate demo metrics
        const wins = data.trades.filter(t => t.pnl > 0);
        const losses = data.trades.filter(t => t.pnl < 0);

        const demoAnalysis = {
            total_trades: data.trades.length,
            winning_trades: wins.length,
            losing_trades: losses.length,
            win_rate: (wins.length / data.trades.length * 100).toFixed(2),
            total_pnl: data.total_pnl,
            avg_win: (wins.reduce((sum, t) => sum + t.pnl, 0) / wins.length).toFixed(2),
            avg_loss: (losses.reduce((sum, t) => sum + t.pnl, 0) / losses.length).toFixed(2),
            largest_win: Math.max(...wins.map(t => t.pnl)).toFixed(2),
            largest_loss: Math.min(...losses.map(t => t.pnl)).toFixed(2),
            profit_factor: (wins.reduce((sum, t) => sum + t.pnl, 0) / Math.abs(losses.reduce((sum, t) => sum + t.pnl, 0))).toFixed(2),
            sharpe_ratio: 1.8,
            max_drawdown: 150
        };

        updateMetrics(demoAnalysis);
        showToast('Demo Loaded', `${data.trades.length} demo trades generated`, 'success');
    } catch (error) {
        showToast('Demo Failed', error.message, 'error');
    }
}

function updateMetrics(analysis) {
    document.getElementById('totalPnL').textContent = `$${analysis.total_pnl}`;
    document.getElementById('totalPnL').className = 'metric-value ' + (analysis.total_pnl >= 0 ? 'positive' : 'negative');

    document.getElementById('winRate').textContent = `${analysis.win_rate}%`;
    document.getElementById('totalTrades').textContent = analysis.total_trades;
    document.getElementById('profitFactor').textContent = analysis.profit_factor;
    document.getElementById('sharpeRatio').textContent = analysis.sharpe_ratio;
    document.getElementById('maxDrawdown').textContent = `$${analysis.max_drawdown}`;
}

function updateTradeList(trades) {
    const container = document.getElementById('liveTradeList');

    if (!trades || trades.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                <p>No trades yet. Start trading or load demo data.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = trades.slice(-20).reverse().map(trade => `
        <div class="trade-item">
            <div class="trade-left">
                <span class="symbol-badge"><i class="fab fa-bitcoin"></i> ${trade.symbol}</span>
                <span style="color: var(--text-secondary); margin-left: 0.5rem;">${trade.strategy}</span>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
                    ${new Date(trade.timestamp).toLocaleString()}
                </div>
            </div>
            <div class="trade-right">
                <div class="stat-value ${trade.pnl >= 0 ? 'positive' : 'negative'}" style="font-size: 1.1rem;">
                    $${trade.pnl.toFixed(2)}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">
                    ${trade.reason}
                </div>
            </div>
        </div>
    `).join('');
}

function updateTopPerformers(analysis) {
    const container = document.getElementById('topPerformers');

    if (!analysis.by_symbol || Object.keys(analysis.by_symbol).length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary);">No data available</p>';
        return;
    }

    const performers = Object.entries(analysis.by_symbol)
        .sort((a, b) => b[1].pnl - a[1].pnl)
        .slice(0, 5);

    container.innerHTML = performers.map(([symbol, data]) => `
        <div class="stat-item">
            <span class="stat-label"><i class="fab fa-bitcoin"></i> ${symbol}</span>
            <span class="stat-value ${data.pnl >= 0 ? 'positive' : 'negative'}">
                $${data.pnl.toFixed(2)} (${data.trades} trades)
            </span>
        </div>
    `).join('');
}

function drawEquityCurve(trades) {
    const canvas = document.getElementById('equityCanvas');
    const ctx = canvas.getContext('2d');

    // Set canvas size
    canvas.width = canvas.offsetWidth;
    canvas.height = 300;

    const width = canvas.width;
    const height = canvas.height;
    const padding = { top: 20, right: 20, bottom: 40, left: 60 };

    ctx.clearRect(0, 0, width, height);

    if (!trades || trades.length === 0) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No data to display', width / 2, height / 2);
        return;
    }

    // Calculate cumulative PnL
    let cumulative = 0;
    const points = trades.map((trade, i) => {
        cumulative += trade.pnl;
        return { x: i, y: cumulative };
    });

    const maxPnL = Math.max(...points.map(p => p.y));
    const minPnL = Math.min(...points.map(p => p.y));
    const range = maxPnL - minPnL || 1;

    // Draw grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + (height - padding.top - padding.bottom) * i / 5;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(width - padding.right, y);
        ctx.stroke();
    }

    // Draw equity curve
    ctx.strokeStyle = cumulative >= 0 ? '#00ff88' : '#ff4466';
    ctx.lineWidth = 2;
    ctx.beginPath();

    points.forEach((point, i) => {
        const x = padding.left + (width - padding.left - padding.right) * (i / (points.length - 1));
        const y = padding.top + (height - padding.top - padding.bottom) * (1 - (point.y - minPnL) / range);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Draw labels
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'right';

    for (let i = 0; i <= 5; i++) {
        const value = maxPnL - (range * i / 5);
        const y = padding.top + (height - padding.top - padding.bottom) * i / 5;
        ctx.fillText(`$${value.toFixed(0)}`, padding.left - 10, y + 4);
    }
}

function calculateProfit() {
    const initialCapital = parseFloat(document.getElementById('initialCapital').value);
    const riskPercent = parseFloat(document.getElementById('riskPercent').value);
    const strategyFilter = document.getElementById('strategyFilter').value;

    let filteredTrades = currentTrades;
    if (strategyFilter !== 'all') {
        filteredTrades = currentTrades.filter(t => t.strategy === strategyFilter);
    }

    if (filteredTrades.length === 0) {
        showToast('No Trades', 'No trades found for selected filter', 'error');
        return;
    }

    // Calculate what P&L would be with risk management
    let capital = initialCapital;
    let peak = initialCapital;
    let maxDD = 0;
    let trades = 0;

    const results = filteredTrades.map(trade => {
        const riskAmount = capital * (riskPercent / 100);
        const returnPct = (trade.exit_price - trade.entry_price) / trade.entry_price;
        const pnl = riskAmount * returnPct * 10; // Simplified

        capital += pnl;
        trades++;

        if (capital > peak) peak = capital;
        const dd = (peak - capital) / peak * 100;
        if (dd > maxDD) maxDD = dd;

        return { ...trade, adjustedPnL: pnl, capital };
    });

    const finalCapital = capital;
    const totalReturn = ((finalCapital - initialCapital) / initialCapital * 100).toFixed(2);

    const resultsContainer = document.getElementById('calculatorResults');
    resultsContainer.innerHTML = `
        <div class="stat-item">
            <span class="stat-label"><i class="fas fa-dollar-sign"></i> Initial Capital</span>
            <span class="stat-value">$${initialCapital.toFixed(2)}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label"><i class="fas fa-chart-line"></i> Final Capital</span>
            <span class="stat-value ${finalCapital >= initialCapital ? 'positive' : 'negative'}">
                $${finalCapital.toFixed(2)}
            </span>
        </div>
        <div class="stat-item">
            <span class="stat-label"><i class="fas fa-percent"></i> Total Return</span>
            <span class="stat-value ${totalReturn >= 0 ? 'positive' : 'negative'}">
                ${totalReturn}%
            </span>
        </div>
        <div class="stat-item">
            <span class="stat-label"><i class="fas fa-arrow-down"></i> Max Drawdown</span>
            <span class="stat-value negative">${maxDD.toFixed(2)}%</span>
        </div>
        <div class="stat-item">
            <span class="stat-label"><i class="fas fa-hashtag"></i> Trades Analyzed</span>
            <span class="stat-value">${trades}</span>
        </div>
    `;

    showToast('Calculation Complete', `Analyzed ${trades} trades with ${riskPercent}% risk`, 'success');
}

function startAutoRefresh() {
    // Refresh every 10 seconds if not in demo mode
    setInterval(() => {
        if (!demoMode) {
            refreshAnalytics();
        }
    }, 10000);
}
