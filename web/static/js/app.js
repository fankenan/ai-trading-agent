/**
 * AI量化交易Agent - 前端JavaScript
 * 负责API调用、图表渲染、页面交互
 */

// ============================================================
// 全局应用对象
// ============================================================
const App = (() => {
    'use strict';

    // 图表实例缓存
    let charts = {
        kline: null,
        equity: null,
        scoreRadar: null,
        portfolio: null
    };

    // 定时器
    let timers = {
        marketRefresh: null,
        clock: null
    };

    // Chart.js 全局配置
    const chartDefaults = {
        color: '#a0a0b8',
        borderColor: '#2a2a4a',
        font: {
            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
        }
    };

    // ============================================================
    // 初始化
    // ============================================================
    function init() {
        console.log('[App] AI量化交易Agent Dashboard 初始化...');
        Chart.defaults.color = chartDefaults.color;
        Chart.defaults.borderColor = chartDefaults.borderColor;
        Chart.defaults.font.family = chartDefaults.font.family;

        initNavigation();
        initClock();
        initDefaultDates();
        loadInitialData();
        startAutoRefresh();
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // ============================================================
    // 导航切换
    // ============================================================
    function initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const sections = document.querySelectorAll('.panel-section');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = item.getAttribute('data-section');

                // 更新导航高亮
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');

                // 切换面板显示
                sections.forEach(s => s.classList.remove('active'));
                const target = document.getElementById(targetId);
                if (target) {
                    target.classList.add('active');
                }
            });
        });
    }

    // ============================================================
    // 时钟
    // ============================================================
    function initClock() {
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
            const el = document.getElementById('currentTime');
            if (el) el.textContent = timeStr;
        }
        updateClock();
        timers.clock = setInterval(updateClock, 1000);
    }

    // ============================================================
    // 设置默认日期
    // ============================================================
    function initDefaultDates() {
        const today = new Date();
        const threeMonthsAgo = new Date(today);
        threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);

        const formatDate = (d) => d.toISOString().split('T')[0];

        const btStart = document.getElementById('btStartDate');
        const btEnd = document.getElementById('btEndDate');
        const reportDate = document.getElementById('reportDate');

        if (btStart) btStart.value = formatDate(threeMonthsAgo);
        if (btEnd) btEnd.value = formatDate(today);
        if (reportDate) reportDate.value = formatDate(today);
    }

    // ============================================================
    // 初始数据加载
    // ============================================================
    async function loadInitialData() {
        await Promise.allSettled([
            refreshMarket(),
            refreshScore(),
            refreshDecision(),
            refreshPortfolio()
        ]);
    }

    // ============================================================
    // 自动刷新
    // ============================================================
    function startAutoRefresh() {
        // 每30秒刷新市场数据
        timers.marketRefresh = setInterval(() => {
            refreshMarket().catch(() => {});
        }, 30000);
    }

    // ============================================================
    // API调用封装
    // ============================================================
    async function apiGet(url, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? `${url}?${query}` : url;
        const response = await fetch(fullUrl, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.message || `请求失败 (${response.status})`);
        }
        return await response.json();
    }

    async function apiPost(url, data = {}) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.message || `请求失败 (${response.status})`);
        }
        return await response.json();
    }

    // ============================================================
    // 加载状态管理
    // ============================================================
    function showLoading(text = '加载中...') {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.querySelector('.loading-text').textContent = text;
            overlay.style.display = 'flex';
        }
    }

    function hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    // ============================================================
    // 通知提示
    // ============================================================
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        // 3秒后自动移除
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
    }

    // ============================================================
    // 市场数据
    // ============================================================
    async function refreshMarket() {
        try {
            const symbol = document.getElementById('klineSymbol')?.value || 'btcusdt';
            const period = document.getElementById('klinePeriod')?.value || 'daily';

            const result = await apiGet('/api/market', { symbol, period, limit: 100 });

            if (result.success && result.data) {
                updateMarketCards(result.data);
                updateKlineChart(result.data);
                updateIndicators(result.data.indicators || {});
            }
        } catch (err) {
            console.warn('[App] 市场数据加载失败:', err.message);
        }
    }

    function updateMarketCards(data) {
        // 更新BTC数据
        if (data.ticker) {
            setText('btcPrice', formatPrice(data.ticker.price || data.ticker.close || 0));

            const change = data.ticker.change_percent || data.ticker.price_change_percent || 0;
            const changeEl = document.getElementById('btcChange');
            if (changeEl) {
                changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
                changeEl.className = 'stat-change ' + (change >= 0 ? 'up' : 'down');
            }

            setText('btcVolume', formatVolume(data.ticker.volume || 0));
        }

        // 更新K线最新价
        if (data.kline && data.kline.length > 0) {
            const latest = data.kline[data.kline.length - 1];
            const prev = data.kline.length > 1 ? data.kline[data.kline.length - 2] : latest;

            if (data.symbol === 'btcusdt') {
                setText('btcPrice', formatPrice(latest.close || 0));
                const changePercent = prev.close ? ((latest.close - prev.close) / prev.close * 100) : 0;
                const changeEl = document.getElementById('btcChange');
                if (changeEl) {
                    changeEl.textContent = (changePercent >= 0 ? '+' : '') + changePercent.toFixed(2) + '%';
                    changeEl.className = 'stat-change ' + (changePercent >= 0 ? 'up' : 'down');
                }
                setText('btcVolume', formatVolume(latest.volume || 0));
            }
        }
    }

    function updateKlineChart(data) {
        const kline = data.kline || [];
        if (kline.length === 0) return;

        const labels = kline.map(item => item.date || item.time || '');
        const closes = kline.map(item => item.close || 0);
        const highs = kline.map(item => item.high || 0);
        const lows = kline.map(item => item.low || 0);
        const volumes = kline.map(item => item.volume || 0);

        // 销毁旧图表
        if (charts.kline) {
            charts.kline.destroy();
        }

        const ctx = document.getElementById('klineChart');
        if (!ctx) return;

        charts.kline = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '收盘价',
                        data: closes,
                        borderColor: '#e94560',
                        backgroundColor: 'rgba(233, 69, 96, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        fill: true,
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: '最高价',
                        data: highs,
                        borderColor: 'rgba(46, 213, 115, 0.5)',
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [3, 3],
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: '最低价',
                        data: lows,
                        borderColor: 'rgba(30, 144, 255, 0.5)',
                        borderWidth: 1,
                        pointRadius: 0,
                        borderDash: [3, 3],
                        tension: 0.1,
                        yAxisID: 'y'
                    },
                    {
                        label: '成交量',
                        data: volumes,
                        type: 'bar',
                        backgroundColor: 'rgba(30, 144, 255, 0.2)',
                        borderColor: 'rgba(30, 144, 255, 0.4)',
                        borderWidth: 1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        labels: {
                            usePointStyle: true,
                            padding: 16
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 33, 62, 0.95)',
                        borderColor: '#2a2a4a',
                        borderWidth: 1,
                        padding: 12,
                        titleFont: { weight: 'bold' }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            maxTicksLimit: 10,
                            maxRotation: 0
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        position: 'left',
                        grid: {
                            color: 'rgba(255,255,255,0.05)'
                        }
                    },
                    y1: {
                        position: 'right',
                        grid: {
                            display: false
                        },
                        ticks: {
                            callback: (v) => formatVolume(v)
                        }
                    }
                }
            }
        });
    }

    function updateIndicators(indicators) {
        setText('ma7', formatPrice(indicators.ma_7));
        setText('ma25', formatPrice(indicators.ma_25));
        setText('ma99', formatPrice(indicators.ma_99));

        const rsi = indicators.rsi_14;
        const rsiEl = document.getElementById('rsi14');
        if (rsiEl) {
            rsiEl.textContent = rsi !== undefined ? rsi.toFixed(2) : '--';
            rsiEl.style.color = rsi > 70 ? '#e94560' : rsi < 30 ? '#2ed573' : '#eaeaea';
        }

        if (indicators.macd) {
            const macdVal = indicators.macd.macd || indicators.macd.value || indicators.macd;
            setText('macd', Array.isArray(macdVal) ? (macdVal[macdVal.length - 1]?.toFixed(4) || '--') : formatPrice(macdVal));
        }

        if (indicators.bollinger) {
            setText('bollUpper', formatPrice(indicators.bollinger.upper || indicators.bollinger[0]));
            setText('bollMiddle', formatPrice(indicators.bollinger.middle || indicators.bollinger[1]));
            setText('bollLower', formatPrice(indicators.bollinger.lower || indicators.bollinger[2]));
        }
    }

    // ============================================================
    // 回测系统
    // ============================================================
    async function runBacktest() {
        const strategy = document.getElementById('btStrategy')?.value || 'ma';
        const symbol = document.getElementById('btSymbol')?.value || 'btcusdt';
        const period = document.getElementById('btPeriod')?.value || 'daily';
        const capital = document.getElementById('btCapital')?.value || '100000';
        const startDate = document.getElementById('btStartDate')?.value || '';
        const endDate = document.getElementById('btEndDate')?.value || '';

        showLoading('正在执行回测...');

        try {
            const result = await apiPost('/api/backtest', {
                strategy,
                symbol,
                period,
                initial_capital: parseFloat(capital),
                start_date: startDate,
                end_date: endDate
            });

            if (result.success) {
                showToast('回测执行完成', 'success');
                displayBacktestResult(result.data);
            } else {
                showToast(result.message || '回测失败', 'error');
            }
        } catch (err) {
            showToast('回测执行失败: ' + err.message, 'error');
        } finally {
            hideLoading();
        }
    }

    async function getBacktestResult() {
        showLoading('加载回测结果...');
        try {
            const result = await apiGet('/api/backtest/result');
            if (result.success) {
                displayBacktestResult(result.data);
            } else {
                showToast(result.message || '暂无回测结果', 'warning');
            }
        } catch (err) {
            showToast('获取回测结果失败: ' + err.message, 'error');
        } finally {
            hideLoading();
        }
    }

    function displayBacktestResult(data) {
        // 显示结果区域
        const area = document.getElementById('backtestResultArea');
        if (area) area.style.display = 'block';

        // 更新摘要数据
        const summary = data.summary || {};
        setText('btTotalReturn', formatPercent(summary.total_return));
        setText('btAnnualReturn', formatPercent(summary.annual_return));
        setText('btMaxDrawdown', formatPercent(summary.max_drawdown));
        setText('btSharpe', (summary.sharpe_ratio || 0).toFixed(2));
        setText('btWinRate', formatPercent(summary.win_rate));
        setText('btTotalTrades', summary.total_trades || 0);

        // 颜色标记
        setChangeColor('btTotalReturn', summary.total_return);
        setChangeColor('btAnnualReturn', summary.annual_return);
        setChangeColor('btMaxDrawdown', summary.max_drawdown, true);

        // 权益曲线
        renderEquityChart(data.equity_curve || []);

        // 交易记录
        renderTradeTable(data.trades || []);
    }

    function renderEquityChart(equityCurve) {
        if (charts.equity) {
            charts.equity.destroy();
        }

        const ctx = document.getElementById('equityChart');
        if (!ctx || equityCurve.length === 0) return;

        const labels = equityCurve.map(item => item.date || item.time || '');
        const values = equityCurve.map(item => item.equity || item.value || 0);
        const benchmark = equityCurve.map(item => item.benchmark || 0);

        const datasets = [{
            label: '策略权益',
            data: values,
            borderColor: '#e94560',
            backgroundColor: 'rgba(233, 69, 96, 0.1)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.1
        }];

        if (benchmark.some(v => v > 0)) {
            datasets.push({
                label: '基准',
                data: benchmark,
                borderColor: 'rgba(30, 144, 255, 0.6)',
                borderWidth: 1,
                pointRadius: 0,
                borderDash: [5, 5],
                tension: 0.1
            });
        }

        charts.equity = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { usePointStyle: true, padding: 16 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 33, 62, 0.95)',
                        borderColor: '#2a2a4a',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: { maxTicksLimit: 8, maxRotation: 0 },
                        grid: { display: false }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            callback: (v) => formatPrice(v)
                        }
                    }
                }
            }
        });
    }

    function renderTradeTable(trades) {
        const tbody = document.getElementById('tradeTableBody');
        if (!tbody) return;

        if (trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无交易记录</td></tr>';
            return;
        }

        tbody.innerHTML = trades.slice(-50).reverse().map(trade => {
            const pnl = trade.pnl || trade.profit || 0;
            const pnlClass = pnl >= 0 ? 'up' : 'down';
            const direction = trade.direction || trade.side || '--';
            const dirClass = direction === 'buy' || direction === 'long' ? 'up' : 'down';
            return `
                <tr>
                    <td>${trade.time || trade.date || '--'}</td>
                    <td style="color:var(--text-${dirClass === 'up' ? 'up' : 'down'})">${direction}</td>
                    <td>${formatPrice(trade.price || 0)}</td>
                    <td>${trade.amount || trade.quantity || trade.qty || '--'}</td>
                    <td style="color:var(--text-${pnlClass === 'up' ? 'up' : 'down'})">${pnl >= 0 ? '+' : ''}${formatPrice(pnl)}</td>
                </tr>
            `;
        }).join('');
    }

    // ============================================================
    // 新闻提交
    // ============================================================
    async function submitNews() {
        const title = document.getElementById('newsTitle')?.value?.trim() || '';
        const content = document.getElementById('newsContent')?.value?.trim() || '';
        const source = document.getElementById('newsSource')?.value?.trim() || '手动输入';

        if (!title && !content) {
            showToast('请输入新闻标题或内容', 'warning');
            return;
        }

        showLoading('正在处理新闻事件...');

        try {
            const result = await apiPost('/api/news', {
                title,
                content,
                source
            });

            if (result.success) {
                showToast('新闻事件已提交处理', 'success');
                // 清空输入
                document.getElementById('newsTitle').value = '';
                document.getElementById('newsContent').value = '';
                // 更新事件列表
                prependNewsEvent(result.data);
            } else {
                showToast(result.message || '提交失败', 'error');
            }
        } catch (err) {
            showToast('新闻提交失败: ' + err.message, 'error');
        } finally {
            hideLoading();
        }
    }

    function prependNewsEvent(event) {
        const list = document.getElementById('newsEventList');
        if (!list) return;

        // 移除空状态
        const emptyState = list.querySelector('.empty-state');
        if (emptyState) emptyState.remove();

        const sentiment = event.classified?.sentiment || event.score_impact?.sentiment || 'neutral';
        const sentimentLabel = { positive: '利好', negative: '利空', neutral: '中性' };
        const category = event.classified?.category || event.category || '--';

        const html = `
            <div class="event-item">
                <div class="event-item-header">
                    <span class="event-item-title">${escapeHtml(event.title || '无标题')}</span>
                    <span class="event-item-time">${event.submit_time || '--'}</span>
                </div>
                <div class="event-item-content">${escapeHtml(event.content || '').substring(0, 200)}</div>
                <div class="event-item-meta">
                    <span class="event-tag ${sentiment}">${sentimentLabel[sentiment] || sentiment}</span>
                    <span class="event-tag neutral">${escapeHtml(category)}</span>
                    <span class="event-tag neutral">${escapeHtml(event.source || '--')}</span>
                    ${event.is_duplicate ? '<span class="event-tag duplicate">重复</span>' : ''}
                </div>
            </div>
        `;

        list.insertAdjacentHTML('afterbegin', html);
    }

    // ============================================================
    // 评分系统
    // ============================================================
    async function refreshScore() {
        try {
            const result = await apiGet('/api/score');
            if (result.success && result.data) {
                updateScoreDisplay(result.data.scores || {});
            }
        } catch (err) {
            console.warn('[App] 评分数据加载失败:', err.message);
        }
    }

    function updateScoreDisplay(scores) {
        const scoreFields = {
            'trend': { bar: 'scoreTrend', num: 'scoreTrendNum' },
            'momentum': { bar: 'scoreMomentum', num: 'scoreMomentumNum' },
            'volatility': { bar: 'scoreVolatility', num: 'scoreVolatilityNum' },
            'volume': { bar: 'scoreVolume', num: 'scoreVolumeNum' },
            'sentiment': { bar: 'scoreSentiment', num: 'scoreSentimentNum' }
        };

        const radarData = [];
        const radarLabels = ['趋势', '动量', '波动率', '成交量', '情绪'];

        Object.entries(scoreFields).forEach(([key, els]) => {
            const value = scores[key] || scores[key + '_score'] || 0;
            const normalized = Math.min(100, Math.max(0, value));

            const barEl = document.getElementById(els.bar);
            const numEl = document.getElementById(els.num);

            if (barEl) {
                barEl.style.width = normalized + '%';
                barEl.className = 'progress-fill ' + (normalized >= 70 ? 'high' : normalized >= 40 ? 'medium' : 'low');
            }
            if (numEl) {
                numEl.textContent = normalized.toFixed(0);
            }

            radarData.push(normalized);
        });

        // 更新系统评分卡片
        const totalScore = scores.total || scores.comprehensive || (radarData.length > 0 ? (radarData.reduce((a, b) => a + b, 0) / radarData.length) : 0);
        setText('systemScore', totalScore.toFixed(0));

        // 雷达图
        renderScoreRadar(radarLabels, radarData);
    }

    function renderScoreRadar(labels, data) {
        if (charts.scoreRadar) {
            charts.scoreRadar.destroy();
        }

        const ctx = document.getElementById('scoreRadarChart');
        if (!ctx) return;

        charts.scoreRadar = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: '综合评分',
                    data: data,
                    backgroundColor: 'rgba(233, 69, 96, 0.2)',
                    borderColor: '#e94560',
                    borderWidth: 2,
                    pointBackgroundColor: '#e94560',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            color: '#6c6c80',
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: 'rgba(255,255,255,0.08)'
                        },
                        angleLines: {
                            color: 'rgba(255,255,255,0.08)'
                        },
                        pointLabels: {
                            color: '#a0a0b8',
                            font: { size: 12 }
                        }
                    }
                }
            }
        });
    }

    // ============================================================
    // 决策系统
    // ============================================================
    async function refreshDecision() {
        try {
            const result = await apiGet('/api/decision');
            if (result.success && result.data) {
                updateDecisionDisplay(result.data.decision || {});
            }
        } catch (err) {
            console.warn('[App] 决策数据加载失败:', err.message);
        }
    }

    function updateDecisionDisplay(decision) {
        const direction = decision.direction || decision.action || decision.signal || '--';
        const dirEl = document.getElementById('decisionDirection');
        if (dirEl) {
            dirEl.textContent = formatDirection(direction);
            dirEl.className = 'decision-value-large ' + getDirectionClass(direction);
        }

        // 顶部决策卡片
        const topDecisionEl = document.getElementById('currentDecision');
        if (topDecisionEl) {
            topDecisionEl.textContent = formatDirection(direction);
            topDecisionEl.className = 'stat-value decision-value ' + getDirectionClass(direction);
        }

        setText('decisionConf', '置信度: ' + (decision.confidence || '--'));
        setText('decisionConfDetail', (decision.confidence || '--'));
        setText('decisionPosition', decision.position_size || decision.suggested_position || '--');
        setText('decisionStopLoss', decision.stop_loss ? formatPrice(decision.stop_loss) : '--');
        setText('decisionTakeProfit', decision.take_profit ? formatPrice(decision.take_profit) : '--');

        // 入场/失效条件
        const entryConditions = decision.entry_conditions || decision.entry_rules || [];
        const exitConditions = decision.exit_conditions || decision.exit_rules || decision.invalid_conditions || [];

        const entryList = document.getElementById('entryConditions');
        if (entryList) {
            entryList.innerHTML = entryConditions.length > 0
                ? entryConditions.map(c => `<li>${escapeHtml(typeof c === 'string' ? c : JSON.stringify(c))}</li>`).join('')
                : '<li>暂无入场条件</li>';
        }

        const exitList = document.getElementById('exitConditions');
        if (exitList) {
            exitList.innerHTML = exitConditions.length > 0
                ? exitConditions.map(c => `<li>${escapeHtml(typeof c === 'string' ? c : JSON.stringify(c))}</li>`).join('')
                : '<li>暂无失效条件</li>';
        }
    }

    // ============================================================
    // 模拟交易
    // ============================================================
    async function refreshPortfolio() {
        try {
            const result = await apiGet('/api/portfolio');
            if (result.success && result.data) {
                updatePortfolioDisplay(result.data);
            }
        } catch (err) {
            console.warn('[App] 持仓数据加载失败:', err.message);
        }
    }

    function updatePortfolioDisplay(data) {
        const account = data.account || {};
        setText('totalAsset', formatPrice(account.total_asset || account.total || 0));
        setText('availableBalance', formatPrice(account.available || account.balance || 0));
        setText('positionValue', formatPrice(account.position_value || 0));

        const pnl = account.total_pnl || account.unrealized_pnl || 0;
        const pnlEl = document.getElementById('totalPnl');
        if (pnlEl) {
            pnlEl.textContent = (pnl >= 0 ? '+' : '') + formatPrice(pnl);
            pnlEl.style.color = pnl >= 0 ? 'var(--text-up)' : 'var(--text-down)';
        }

        // 持仓表格
        renderPositionTable(data.positions || []);

        // 交易历史
        renderHistoryTable(data.history || []);

        // 权益曲线
        renderPortfolioChart(data.equity_curve || []);
    }

    function renderPositionTable(positions) {
        const tbody = document.getElementById('positionTableBody');
        if (!tbody) return;

        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">暂无持仓</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const pnl = pos.pnl || pos.unrealized_pnl || 0;
            const pnlPercent = pos.pnl_percent || pos.unrealized_pnl_percent || 0;
            const pnlClass = pnl >= 0 ? 'up' : 'down';
            return `
                <tr>
                    <td>${pos.symbol || '--'}</td>
                    <td style="color:var(--text-${pos.side === 'long' || pos.direction === 'buy' ? 'up' : 'down'})">${pos.side || pos.direction || '--'}</td>
                    <td>${pos.quantity || pos.amount || '--'}</td>
                    <td>${formatPrice(pos.entry_price || pos.open_price || 0)}</td>
                    <td>${formatPrice(pos.current_price || pos.mark_price || 0)}</td>
                    <td style="color:var(--text-${pnlClass === 'up' ? 'up' : 'down'})">${pnl >= 0 ? '+' : ''}${formatPrice(pnl)}</td>
                    <td style="color:var(--text-${pnlClass === 'up' ? 'up' : 'down'})">${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%</td>
                </tr>
            `;
        }).join('');
    }

    function renderHistoryTable(history) {
        const tbody = document.getElementById('historyTableBody');
        if (!tbody) return;

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state">暂无交易记录</td></tr>';
            return;
        }

        tbody.innerHTML = history.slice(-30).reverse().map(trade => {
            const pnl = trade.pnl || trade.profit || 0;
            const pnlClass = pnl >= 0 ? 'up' : 'down';
            const status = trade.status || '已成交';
            return `
                <tr>
                    <td>${trade.time || trade.created_at || '--'}</td>
                    <td>${trade.symbol || '--'}</td>
                    <td style="color:var(--text-${(trade.side || trade.direction) === 'buy' || (trade.side || trade.direction) === 'long' ? 'up' : 'down'})">${trade.side || trade.direction || '--'}</td>
                    <td>${formatPrice(trade.price || 0)}</td>
                    <td>${trade.quantity || trade.amount || '--'}</td>
                    <td style="color:var(--text-${pnlClass === 'up' ? 'up' : 'down'})">${pnl >= 0 ? '+' : ''}${formatPrice(pnl)}</td>
                    <td>${status}</td>
                </tr>
            `;
        }).join('');
    }

    function renderPortfolioChart(equityCurve) {
        if (charts.portfolio) {
            charts.portfolio.destroy();
        }

        const ctx = document.getElementById('portfolioChart');
        if (!ctx || equityCurve.length === 0) return;

        const labels = equityCurve.map(item => item.date || item.time || '');
        const values = equityCurve.map(item => item.equity || item.value || item.total_asset || 0);

        charts.portfolio = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '总资产',
                    data: values,
                    borderColor: '#2ed573',
                    backgroundColor: 'rgba(46, 213, 115, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { usePointStyle: true, padding: 16 }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(22, 33, 62, 0.95)',
                        borderColor: '#2a2a4a',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: { maxTicksLimit: 8, maxRotation: 0 },
                        grid: { display: false }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            callback: (v) => formatPrice(v)
                        }
                    }
                }
            }
        });
    }

    // ============================================================
    // 报告系统
    // ============================================================
    async function generateReport() {
        const type = document.getElementById('reportType')?.value || 'daily';
        const date = document.getElementById('reportDate')?.value || '';

        showLoading('正在生成报告...');

        try {
            const result = await apiGet('/api/report', { type, date });
            if (result.success && result.data) {
                showToast('报告生成完成', 'success');
                displayReport(result.data);
            } else {
                showToast(result.message || '报告生成失败', 'error');
            }
        } catch (err) {
            showToast('报告生成失败: ' + err.message, 'error');
        } finally {
            hideLoading();
        }
    }

    function displayReport(data) {
        const container = document.getElementById('reportContent');
        if (!container) return;

        const report = data.report || {};
        const typeLabels = { daily: '日报', weekly: '周报', monthly: '月报' };

        let html = `
            <h4>${typeLabels[data.type] || '报告'} - ${data.date || '--'}</h4>
            <p>生成时间: ${data.generate_time || '--'}</p>
        `;

        // 如果报告是文本格式
        if (typeof report === 'string') {
            html += `<div style="white-space:pre-wrap;">${escapeHtml(report)}</div>`;
        }
        // 如果报告是结构化数据
        else if (typeof report === 'object') {
            // 摘要指标
            if (report.summary || report.metrics) {
                const metrics = report.summary || report.metrics;
                html += '<div class="report-metrics">';
                Object.entries(metrics).forEach(([key, value]) => {
                    html += `
                        <div class="report-metric">
                            <div class="report-metric-label">${escapeHtml(key)}</div>
                            <div class="report-metric-value">${escapeHtml(String(value))}</div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            // 内容段落
            if (report.content) {
                html += `<p>${escapeHtml(report.content)}</p>`;
            }

            // 各章节
            if (report.sections) {
                report.sections.forEach(section => {
                    html += `<h4>${escapeHtml(section.title || '')}</h4>`;
                    if (section.content) {
                        html += `<p>${escapeHtml(section.content)}</p>`;
                    }
                });
            }

            // 原始JSON（备用展示）
            if (Object.keys(report).length > 0 && !report.summary && !report.content && !report.sections) {
                html += `<div style="white-space:pre-wrap; font-size:0.8rem; color:#6c6c80;">${escapeHtml(JSON.stringify(report, null, 2))}</div>`;
            }
        }

        container.innerHTML = html;
    }

    // ============================================================
    // 工具函数
    // ============================================================
    function setText(elementId, text) {
        const el = document.getElementById(elementId);
        if (el) el.textContent = text;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatPrice(price) {
        const num = parseFloat(price);
        if (isNaN(num)) return '--';
        if (num >= 1000) return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (num >= 1) return num.toFixed(2);
        return num.toFixed(4);
    }

    function formatVolume(volume) {
        const num = parseFloat(volume);
        if (isNaN(num)) return '--';
        if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
        return num.toFixed(2);
    }

    function formatPercent(value) {
        const num = parseFloat(value);
        if (isNaN(num)) return '--';
        return (num >= 0 ? '+' : '') + num.toFixed(2) + '%';
    }

    function setChangeColor(elementId, value, inverse = false) {
        const el = document.getElementById(elementId);
        if (!el) return;
        const num = parseFloat(value);
        if (isNaN(num)) return;
        if (inverse) {
            el.style.color = num <= 0 ? 'var(--text-up)' : 'var(--text-down)';
        } else {
            el.style.color = num >= 0 ? 'var(--text-up)' : 'var(--text-down)';
        }
    }

    function formatDirection(direction) {
        const map = {
            'buy': '做多 (买入)',
            'sell': '做空 (卖出)',
            'long': '做多',
            'short': '做空',
            'hold': '观望 (持有)',
            'neutral': '观望 (中性)',
            'close_long': '平多',
            'close_short': '平空'
        };
        return map[String(direction).toLowerCase()] || String(direction);
    }

    function getDirectionClass(direction) {
        const d = String(direction).toLowerCase();
        if (d === 'buy' || d === 'long') return 'buy';
        if (d === 'sell' || d === 'short') return 'sell';
        return 'hold';
    }

    // ============================================================
    // 公开API
    // ============================================================
    return {
        refreshMarket,
        runBacktest,
        getBacktestResult,
        submitNews,
        refreshScore,
        refreshDecision,
        refreshPortfolio,
        generateReport
    };

})();
