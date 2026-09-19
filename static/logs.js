document.addEventListener('DOMContentLoaded', () => {
    const terminal = document.getElementById('terminal');

    let lastLogsCount = 0;

    async function fetchLogs() {
        try {
            const response = await fetch('/logs');
            const data = await response.json();
            renderLogs(data.logs);
        } catch (err) {
            console.error("Failed to fetch logs", err);
        }
    }

    function renderLogs(logs) {
        const isNearBottom = terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight < 50 || lastLogsCount === 0;

        terminal.innerHTML = '';
        if (logs.length === 0) {
            terminal.innerHTML = '<div class="log-entry log-info"><span class="log-msg">Waiting for PLC connections...</span></div>';
            return;
        }

        const recentLogs = [...logs].reverse().slice(-40);

        recentLogs.forEach(log => {
            const entry = document.createElement('div');
            entry.className = `log-entry log-${log.type}`;

            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            timeSpan.textContent = `[${log.time}]`;

            const msgSpan = document.createElement('span');
            msgSpan.className = 'log-msg';
            msgSpan.textContent = log.message;

            entry.appendChild(timeSpan);
            entry.appendChild(msgSpan);
            terminal.appendChild(entry);
        });

        if (isNearBottom) {
            terminal.scrollTop = terminal.scrollHeight;
        }

        lastLogsCount = logs.length;
    }

    setInterval(fetchLogs, 1000);
    fetchLogs();
});