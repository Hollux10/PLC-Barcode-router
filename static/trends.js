document.addEventListener('DOMContentLoaded', () => {
    const badge = document.getElementById('session-badge');
    const startBtn = document.getElementById('start-session');
    const pauseBtn = document.getElementById('pause-session');
    const clearBtn = document.getElementById('clear-session');
    const reportModal = document.getElementById('report-modal');
    const reportYes = document.getElementById('report-yes');
    const reportNo = document.getElementById('report-no');
    const overallChart = document.getElementById('trend-overall');
    const destChart = document.getElementById('trend-dest');
    const overallLabels = document.getElementById('trend-overall-labels');
    const destLabels = document.getElementById('trend-dest-labels');
    const legendEl = document.getElementById('trend-legend');
    const tbody = document.querySelector('#trend-table tbody');

    const PALETTE = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#eab308'];
    const destColors = {};
    let colorIdx = 0;

    function colorFor(dest) {
        if (!(dest in destColors)) {
            destColors[dest] = PALETTE[colorIdx % PALETTE.length];
            colorIdx++;
        }
        return destColors[dest];
    }

    function setBadge(active, paused) {
        if (active && paused) {
            badge.textContent = 'Session Paused';
            badge.style.color = '#fbbf24';
            badge.style.borderColor = '#fbbf24';
            badge.style.background = 'rgba(251, 191, 36, 0.2)';
            badge.style.boxShadow = '0 0 10px rgba(251, 191, 36, 0.3)';
        } else if (active) {
            badge.textContent = 'Session Running';
            badge.style.color = 'var(--success)';
            badge.style.borderColor = 'var(--success)';
            badge.style.background = 'rgba(16, 185, 129, 0.2)';
            badge.style.boxShadow = '0 0 10px rgba(16, 185, 129, 0.3)';
        } else {
            badge.textContent = 'Session Stopped';
            badge.style.color = 'var(--text-muted)';
            badge.style.borderColor = 'var(--border-color)';
            badge.style.background = 'transparent';
            badge.style.boxShadow = 'none';
        }
    }

    function setControls(active, paused) {
        startBtn.disabled = active;
        pauseBtn.disabled = !active;
        pauseBtn.textContent = paused ? 'Resume' : 'Pause';
    }

    async function startSession() {
        try {
            await fetch('/offload/start', { method: 'POST' });
            setBadge(true, false);
            setControls(true, false);
        } catch (err) {
            console.error('Failed to start session', err);
        }
    }

    async function pauseSession() {
        try {
            await fetch('/offload/pause', { method: 'POST' });
            fetchStatus();
        } catch (err) {
            console.error('Failed to toggle pause', err);
        }
    }

    async function clearSession() {
        try {
            await fetch('/offload/clear', { method: 'POST' });
            setBadge(false, false);
            setControls(false, false);
            overallChart.innerHTML = '<div class="trend-empty">No data yet. Start a session to begin collecting trends.</div>';
            destChart.innerHTML = '<div class="trend-empty">No data yet. Start a session to begin collecting trends.</div>';
            overallLabels.innerHTML = '';
            destLabels.innerHTML = '';
            legendEl.innerHTML = '';
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No trend data yet. Start a session to begin collecting.</td></tr>';
        } catch (err) {
            console.error('Failed to clear session', err);
        }
    }

    function renderCharts(trends) {
        if (!trends || trends.length === 0) {
            overallChart.innerHTML = '<div class="trend-empty">No data yet. Start a session to begin collecting trends.</div>';
            destChart.innerHTML = '<div class="trend-empty">No data yet. Start a session to begin collecting trends.</div>';
            overallLabels.innerHTML = '';
            destLabels.innerHTML = '';
            legendEl.innerHTML = '';
            return;
        }

        const buckets = trends.slice(-90);
        const maxAttempts = Math.max(...buckets.map(b => b.attempts), 1);
        const maxConfirmed = Math.max(...buckets.map(b => b.confirmed), 1);
        const maxVal = Math.max(maxAttempts, maxConfirmed, 1);

        function buildCol(b, bars) {
            const col = document.createElement('div');
            col.className = 'trend-col';
            bars.forEach(([heightPct, klass, bg]) => {
                const bar = document.createElement('div');
                bar.className = 'trend-bar ' + (klass || '');
                bar.style.height = heightPct + '%';
                if (bg) bar.style.background = bg;
                col.appendChild(bar);
            });
            return col;
        }

        overallLabels.innerHTML = '';
        destLabels.innerHTML = '';
        overallChart.innerHTML = '';
        destChart.innerHTML = '';

        buckets.forEach(b => {
            const att = (b.attempts / maxVal) * 100;
            const conf = (b.confirmed / maxVal) * 100;
            const overallCol = buildCol(b, [
                [Math.max(att, 1), 'trend-attempt', '#475569'],
                [Math.max(conf, 1), 'trend-confirmed', null]
            ]);
            overallChart.appendChild(overallCol);

            const lbl = document.createElement('div');
            lbl.className = 'trend-xlabel';
            lbl.textContent = b.dests.length ? b.time : '';
            overallLabels.appendChild(lbl);
        });

        buckets.forEach(b => {
            const totalAttempts = Math.max(1, b.attempts);
            const col = document.createElement('div');
            col.className = 'trend-col';
            b.dests.forEach(d => {
                const seg = document.createElement('div');
                seg.className = 'trend-seg';
                seg.style.height = Math.max((d.attempts / totalAttempts) * 100, 1) + '%';
                seg.style.background = colorFor(d.destination);
                col.appendChild(seg);
            });
            destChart.appendChild(col);
        });

        buckets.forEach(b => {
            const lbl = document.createElement('div');
            lbl.className = 'trend-xlabel';
            lbl.textContent = b.dests.length ? b.time : '';
            destLabels.appendChild(lbl);
        });

        const uniqueDests = [...new Set(buckets.flatMap(b => b.dests.map(d => d.destination)))];
        legendEl.innerHTML = '';
        uniqueDests.forEach(dest => {
            const item = document.createElement('span');
            item.className = 'legend-item';
            const swatch = document.createElement('span');
            swatch.className = 'legend-swatch';
            swatch.style.background = colorFor(dest);
            const text = document.createElement('span');
            text.textContent = 'Destination ' + dest;
            item.appendChild(swatch);
            item.appendChild(text);
            legendEl.appendChild(item);
        });
    }

    function renderTable(trends) {
        if (!trends || trends.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No trend data yet. Start a session to begin collecting.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        trends.slice().reverse().slice(0, 200).forEach(b => {
            const tr = document.createElement('tr');

            const tdTime = document.createElement('td');
            tdTime.className = 'font-mono';
            tdTime.textContent = b.time;

            const tdAtt = document.createElement('td');
            tdAtt.className = 'font-mono';
            tdAtt.textContent = b.attempts;

            const tdConf = document.createElement('td');
            tdConf.className = 'font-mono';
            tdConf.textContent = b.confirmed;

            const wrongTotal = (b.dests || []).reduce((sum, d) => sum + (d.wrong || 0), 0);
            const tdWrong = document.createElement('td');
            if (wrongTotal > 0) {
                const wrongEl = document.createElement('span');
                wrongEl.className = 'dest-badge badge-wrong';
                wrongEl.textContent = wrongTotal;
                tdWrong.appendChild(wrongEl);
            } else {
                tdWrong.textContent = '0';
            }

            const tdRate = document.createElement('td');
            const rate = b.attempts ? Math.round(b.confirmed / b.attempts * 100) : 0;
            const rateEl = document.createElement('span');
            rateEl.className = 'dest-badge';
            rateEl.textContent = rate + '%';
            rateEl.style.background = rate >= 80 ? 'rgba(16,185,129,0.2)' : (rate >= 50 ? 'rgba(251,191,36,0.2)' : 'rgba(239,68,68,0.2)');
            rateEl.style.color = rate >= 80 ? 'var(--success)' : (rate >= 50 ? '#fbbf24' : 'var(--danger)');
            tdRate.appendChild(rateEl);

            const tdDests = document.createElement('td');
            b.dests.forEach(d => {
                const chip = document.createElement('span');
                chip.className = 'dest-badge';
                chip.style.background = 'transparent';
                chip.style.border = '1px solid ' + colorFor(d.destination);
                chip.style.color = colorFor(d.destination);
                chip.textContent = `${d.destination} (A:${d.attempts} C:${d.confirmed} W:${d.wrong || 0})`;
                chip.style.marginRight = '0.4rem';
                tdDests.appendChild(chip);
            });

            tr.appendChild(tdTime);
            tr.appendChild(tdAtt);
            tr.appendChild(tdConf);
            tr.appendChild(tdWrong);
            tr.appendChild(tdRate);
            tr.appendChild(tdDests);
            tbody.appendChild(tr);
        });
    }

    async function fetchStatus() {
        try {
            const response = await fetch('/offload/data');
            const data = await response.json();
            setBadge(data.session_active, data.paused);
            setControls(data.session_active, data.paused);
            renderCharts(data.trends);
            renderTable(data.trends);
        } catch (err) {
            console.error('Failed to fetch trends', err);
        }
    }

    startBtn.addEventListener('click', startSession);
    pauseBtn.addEventListener('click', pauseSession);
    clearBtn.addEventListener('click', requestEndSession);
    reportYes.addEventListener('click', async () => {
        reportModal.style.display = 'none';
        await generateAndDownloadReport();
        clearSession();
    });
    reportNo.addEventListener('click', () => {
        reportModal.style.display = 'none';
        clearSession();
    });

    function requestEndSession() {
        reportModal.style.display = 'flex';
    }

    async function generateAndDownloadReport() {
        try {
            const response = await fetch('/offload/report');
            if (!response.ok) {
                const err = await response.json().catch(() => null);
                if (err && err.message) alert(err.message);
                return;
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'offload_report.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 5000);
        } catch (err) {
            console.error('Report generation failed', err);
        }
    }

    setInterval(fetchStatus, 2000);
    fetchStatus();
});