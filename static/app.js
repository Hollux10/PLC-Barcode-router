document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('add-form');
    const formMsg = document.getElementById('form-msg');
    const settingsForm = document.getElementById('settings-form');
    const settingsMsg = document.getElementById('settings-msg');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);

        try {
            const response = await fetch('/add', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                formMsg.textContent = "Mapping added successfully!";
                formMsg.style.color = "var(--success)";
                form.reset();
                if (data.id) addMappingRow(data.id, formData.get('barcode'), formData.get('destination'));
                setTimeout(() => { formMsg.textContent = ""; }, 5000);
            } else {
                formMsg.textContent = "Error: " + data.message;
                formMsg.style.color = "var(--danger)";
            }
        } catch (err) {
            formMsg.textContent = "Network error occurred.";
            formMsg.style.color = "var(--danger)";
        }
    });

    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(settingsForm);
        const host = formData.get('host');
        const port = formData.get('port');

        // Send explicit booleans for checkboxes (unchecked boxes are absent from FormData otherwise)
        formData.set('log_to_file', formData.get('log_to_file') ? 'true' : 'false');
        formData.set('log_heartbeat', formData.get('log_heartbeat') ? 'true' : 'false');
        formData.set('heartbeat_enabled', formData.get('heartbeat_enabled') ? 'true' : 'false');

        try {
            const response = await fetch('/settings', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                settingsMsg.textContent = "Settings applied and server restarted!";
                settingsMsg.style.color = "var(--success)";
                document.getElementById('header-host').textContent = host;
                document.getElementById('header-port').textContent = port;
            } else {
                settingsMsg.textContent = "Error: " + data.message;
                settingsMsg.style.color = "var(--danger)";
            }
        } catch (err) {
            settingsMsg.textContent = "Network error occurred.";
            settingsMsg.style.color = "var(--danger)";
        }
        
        // clear message after 5 seconds
        setTimeout(() => { settingsMsg.textContent = ""; }, 5000);
    });

    const randomForm = document.getElementById('add-random-form');
    const randomFormMsg = document.getElementById('random-form-msg');

    if (randomForm) {
        randomForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(randomForm);

            try {
                const response = await fetch('/add-random', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.success) {
                    randomFormMsg.textContent = "Location random rule added!";
                    randomFormMsg.style.color = "var(--success)";
                    randomForm.reset();
                    if (data.id) addRandomRuleRow(data.id, formData.get('location'), formData.get('destinations'));
                    setTimeout(() => { randomFormMsg.textContent = ""; }, 5000);
                } else {
                    randomFormMsg.textContent = "Error: " + data.message;
                    randomFormMsg.style.color = "var(--danger)";
                }
            } catch (err) {
                randomFormMsg.textContent = "Network error occurred.";
                randomFormMsg.style.color = "var(--danger)";
            }
        });
    }
});

function openLogsWindow() {
    if (window.logsWindow && !window.logsWindow.closed) {
        window.logsWindow.focus();
        return;
    }
    window.logsWindow = window.open('/logs-page', 'plc-logs',
        'width=900,height=650,resizable=yes,scrollbars=yes');
}

async function refreshConnectionStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();

        const led = document.getElementById('conn-led');
        const statusEl = document.getElementById('conn-status');
        const plcIpEl = document.getElementById('conn-plc-ip');
        const portEl = document.getElementById('conn-port');

        if (data.connected) {
            led.className = 'led led-connected';
            statusEl.textContent = 'Connected';
            statusEl.style.color = 'var(--success)';
            plcIpEl.textContent = data.plc_ip || '--';
        } else {
            led.className = 'led led-disconnected';
            statusEl.textContent = 'Disconnected';
            statusEl.style.color = 'var(--danger)';
            plcIpEl.textContent = '--';
        }
        portEl.textContent = data.port;
    } catch (err) {
        const led = document.getElementById('conn-led');
        if (led) led.className = 'led led-disconnected';
    }
}

// Poll PLC connection status every 2 seconds
setInterval(refreshConnectionStatus, 2000);
refreshConnectionStatus();

function addMappingRow(id, barcode, destination) {
    const tbody = document.querySelector('#mappings-table tbody');
    if (!tbody) return;
    const emptyRow = document.getElementById('empty-row');
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement('tr');
    tr.dataset.id = id;

    const tdBarcode = document.createElement('td');
    tdBarcode.className = 'font-mono';
    tdBarcode.textContent = barcode;

    const tdDest = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'dest-badge';
    badge.textContent = destination;
    tdDest.appendChild(badge);

    const tdAction = document.createElement('td');
    const btn = document.createElement('button');
    btn.className = 'btn delete-btn';
    btn.textContent = 'Delete';
    btn.addEventListener('click', () => deleteMapping(id));
    tdAction.appendChild(btn);

    tr.appendChild(tdBarcode);
    tr.appendChild(tdDest);
    tr.appendChild(tdAction);
    tbody.insertBefore(tr, tbody.firstChild);
}

function addRandomRuleRow(id, location, destinations) {
    const tbody = document.querySelector('#random-table tbody');
    if (!tbody) return;
    const emptyRow = document.getElementById('empty-random-row');
    if (emptyRow) emptyRow.remove();

    const tr = document.createElement('tr');
    tr.dataset.id = id;

    const tdLocation = document.createElement('td');
    tdLocation.className = 'font-mono';
    tdLocation.textContent = location;

    const tdDest = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'dest-badge';
    badge.style.background = 'rgba(59, 130, 246, 0.2)';
    badge.style.color = '#93c5fd';
    badge.textContent = destinations;
    tdDest.appendChild(badge);

    const tdAction = document.createElement('td');
    const btn = document.createElement('button');
    btn.className = 'btn delete-btn';
    btn.textContent = 'Delete';
    btn.addEventListener('click', () => deleteRandomRule(id));
    tdAction.appendChild(btn);

    tr.appendChild(tdLocation);
    tr.appendChild(tdDest);
    tr.appendChild(tdAction);
    tbody.insertBefore(tr, tbody.firstChild);
}

async function deleteMapping(id) {
    if (!confirm('Are you sure you want to delete this mapping?')) return;

    try {
        const response = await fetch(`/delete/${id}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            const row = document.querySelector(`tr[data-id="${id}"]`);
            if (row) {
                row.remove();
            }
        } else {
            alert('Failed to delete mapping.');
        }
    } catch (err) {
        alert('Network error.');
    }
}

async function deleteRandomRule(id) {
    if (!confirm('Are you sure you want to delete this location rule?')) return;

    try {
        const response = await fetch(`/delete-random/${id}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.success) {
            const row = document.querySelector(`#random-table tr[data-id="${id}"]`);
            if (row) {
                row.remove();
            }
        } else {
            alert('Failed to delete location rule.');
        }
    } catch (err) {
        alert('Network error.');
    }
}
