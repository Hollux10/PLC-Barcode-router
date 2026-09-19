document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('count-grid');
    const tbody = document.querySelector('#offload-table tbody');
    const destTbody = document.querySelector('#dest-table tbody');
    const badge = document.getElementById('session-badge');
    const startBtn = document.getElementById('start-session');
    const pauseBtn = document.getElementById('pause-session');
    const clearBtn = document.getElementById('clear-session');
    const reportModal = document.getElementById('report-modal');
    const reportYes = document.getElementById('report-yes');
    const reportNo = document.getElementById('report-no');

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
            grid.innerHTML = '';
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No offload events yet. Start a session to begin counting.</td></tr>';
            if (destTbody) destTbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No destination data yet. Start a session to begin counting.</td></tr>';
        } catch (err) {
            console.error('Failed to clear session', err);
        }
    }

    function renderCounts(status) {
        const counts = status.counts || {};
        const reasons = status.reasons || {};
        const total = Object.values(counts).reduce((sum, n) => sum + (n || 0), 0);

        grid.innerHTML = '';

        const successCard = document.createElement('div');
        successCard.className = 'count-card count-success';

        const successCode = document.createElement('div');
        successCode.className = 'count-code';
        successCode.textContent = 'SUCCESS RATE';

        const successNum = document.createElement('div');
        successNum.className = 'count-number';
        successNum.textContent = status.success_rate !== undefined ? status.success_rate + '%' : '--';

        const successLabel = document.createElement('div');
        successLabel.className = 'count-label';
        successLabel.textContent = `${status.confirmed || 0} confirmed / ${status.attempts || 0} attempts`;

        const bar = document.createElement('div');
        bar.className = 'success-bar';
        const barFill = document.createElement('div');
        barFill.className = 'success-bar-fill';
        barFill.style.width = (status.success_rate !== undefined ? status.success_rate : 0) + '%';
        bar.appendChild(barFill);

        successCard.appendChild(successCode);
        successCard.appendChild(successNum);
        successCard.appendChild(bar);
        successCard.appendChild(successLabel);
        grid.appendChild(successCard);

        for (const [code, label] of Object.entries(reasons)) {
            const count = counts[code] || 0;
            const card = document.createElement('div');
            card.className = 'count-card' + (code === 'WRO' ? ' count-wrong' : '');

            const codeEl = document.createElement('div');
            codeEl.className = 'count-code';
            codeEl.textContent = code;

            const numEl = document.createElement('div');
            numEl.className = 'count-number';
            numEl.textContent = count;

            const labelEl = document.createElement('div');
            labelEl.className = 'count-label';
            labelEl.textContent = label;

            card.appendChild(codeEl);
            card.appendChild(numEl);
            card.appendChild(labelEl);
            grid.appendChild(card);
        }

        const totalCard = document.createElement('div');
        totalCard.className = 'count-card count-total';

        const totCode = document.createElement('div');
        totCode.className = 'count-code';
        totCode.textContent = 'TOTAL';

        const totNum = document.createElement('div');
        totNum.className = 'count-number';
        totNum.textContent = total;

        const totLabel = document.createElement('div');
        totLabel.className = 'count-label';
        totLabel.textContent = 'All offload events';

        totalCard.appendChild(totCode);
        totalCard.appendChild(totNum);
        totalCard.appendChild(totLabel);
        grid.appendChild(totalCard);
    }

    function renderEvents(events) {
        tbody.innerHTML = '';
        if (!events || events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No offload events yet. Start a session to begin counting.</td></tr>';
            return;
        }

        events.slice(0, 100).forEach(ev => {
            const tr = document.createElement('tr');
            if (ev.wrong_offload) tr.classList.add('row-wrong');

            const tdTime = document.createElement('td');
            tdTime.className = 'font-mono';
            tdTime.textContent = ev.time;

            const tdLoc = document.createElement('td');
            tdLoc.className = 'font-mono';
            tdLoc.textContent = ev.location;

            const tdItem = document.createElement('td');
            tdItem.className = 'font-mono';
            tdItem.textContent = ev.item;

            const tdSent = document.createElement('td');
            tdSent.className = 'font-mono';
            tdSent.textContent = ev.sent_destination || '-';

            const tdDest = document.createElement('td');
            tdDest.className = 'font-mono';
            tdDest.textContent = ev.destination;

            const tdReason = document.createElement('td');
            const badgeEl = document.createElement('span');
            badgeEl.className = 'dest-badge' + (ev.wrong_offload ? ' badge-wrong' : '');
            badgeEl.textContent = ev.reason;
            tdReason.appendChild(badgeEl);

            tr.appendChild(tdTime);
            tr.appendChild(tdLoc);
            tr.appendChild(tdItem);
            tr.appendChild(tdSent);
            tr.appendChild(tdDest);
            tr.appendChild(tdReason);
            tbody.appendChild(tr);
        });
    }

    function renderDestinations(status) {
        if (!destTbody) return;
        const byDest = status.by_dest || [];
        destTbody.innerHTML = '';

        if (byDest.length === 0) {
            destTbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No destination data yet. Start a session to begin counting.</td></tr>';
            return;
        }

        byDest.slice().sort((a, b) => b.total - a.total).forEach(d => {
            const tr = document.createElement('tr');

            const tdDest = document.createElement('td');
            tdDest.className = 'font-mono';
            tdDest.textContent = d.destination;

            const tdTotal = document.createElement('td');
            tdTotal.textContent = d.total;

            const tdAttempts = document.createElement('td');
            tdAttempts.className = 'font-mono';
            tdAttempts.textContent = d.attempts;

            const tdConfirmed = document.createElement('td');
            tdConfirmed.className = 'font-mono';
            tdConfirmed.textContent = d.confirmed;

            const tdWrong = document.createElement('td');
            if (d.wrong) {
                const wrongEl = document.createElement('span');
                wrongEl.className = 'dest-badge badge-wrong';
                wrongEl.textContent = d.wrong;
                tdWrong.appendChild(wrongEl);
            } else {
                tdWrong.textContent = '0';
            }

            const tdRate = document.createElement('td');
            const rateEl = document.createElement('span');
            rateEl.className = 'dest-badge rate-chip';
            rateEl.textContent = d.success_rate + '%';
            if (d.success_rate >= 80) {
                rateEl.style.background = 'rgba(16, 185, 129, 0.2)';
                rateEl.style.color = 'var(--success)';
            } else if (d.success_rate >= 50) {
                rateEl.style.background = 'rgba(251, 191, 36, 0.2)';
                rateEl.style.color = '#fbbf24';
            } else {
                rateEl.style.background = 'rgba(239, 68, 68, 0.2)';
                rateEl.style.color = 'var(--danger)';
            }
            tdRate.appendChild(rateEl);

            tr.appendChild(tdDest);
            tr.appendChild(tdTotal);
            tr.appendChild(tdAttempts);
            tr.appendChild(tdConfirmed);
            tr.appendChild(tdWrong);
            tr.appendChild(tdRate);
            destTbody.appendChild(tr);
        });
    }

    async function fetchStatus() {
        try {
            const response = await fetch('/offload/data');
            const data = await response.json();
            renderCounts(data);
            renderEvents(data.events);
            renderDestinations(data);
            setBadge(data.session_active, data.paused);
            setControls(data.session_active, data.paused);
        } catch (err) {
            console.error('Failed to fetch offload status', err);
        }
    }

    setInterval(fetchStatus, 1000);
    fetchStatus();
});