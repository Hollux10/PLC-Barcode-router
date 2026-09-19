# PLC Barcode Router

A Windows tool that runs a TCP server to communicate with a barcode sorter PLC, looks up the destination for scanned barcodes, and sends the destination back to the PLC. It also tracks and reports offload events.

## What it does

1. Listens on a TCP port for the PLC to connect.
2. Receives barcode scan messages (`042`) from the PLC (IDC's comunication protocol v3).
3. Routes each barcode:
   - **Barcode mode** (default): looks up the destination from the `routing` table in `routing.db`.
   - **Random mode**: picks a random destination from a location's rule in the `random_routing` table.
4. Sends a `050` response back with the 5-digit destination.
5. Responds to heartbeat messages (`001`).
6. Records offload events (`044`) - attempted (OFL), confirmed (SUP), wrong offload (WRO), etc.
7. Provides a web UI (FastAPI + Jinja2) to manage mappings, view logs/offload stats, and download PDF reports.

## Getting started

### Dependencies (Python 3.11+)

```
fastapi
uvicorn
jinja2
pydantic
python-multipart
```

Install with:

```
pip install -r requirements.txt
```

### Run from source

```
python main.py
```

This:
- Creates/opens `routing.db` in the current folder.
- Starts the TCP server using settings from the DB (default host `0.0.0.0`, port `8080` — note these are the WEB UI default settings; the PLC TCP listener uses the `host`/`port` configured via the UI Settings page).
- Serves the web UI on **http://localhost:5000** and opens the browser automatically.

### Build a standalone EXE (PyInstaller)

```
pyinstaller main.spec --onefile
```

Output goes to `dist/main.exe`. Copy `dist/main.exe` and `dist/routing.db` together on the target machine (the EXE reads/writes `routing.db` from its own folder).

## Web UI

Available at `http://localhost:5000`:

| Page | Purpose |
|------|---------|
| **Home (`/`)** | Manage barcode→destination mappings, random routing rules, and app settings. |
| **Logs (`/logs-page`)** | Live list of recent protocol traffic (in-memory, last 200 entries). |
| **Offload (`/offload`)** | Start/pause/clear an offload counting session; view stats per destination; download PDF report. |
| **Trends (`/trends`)** | Per-minute offload trends chart. |

### Settings (via the Home page)

- **Host / Port** — where the TCP server listens for the PLC. Set these to the machine's actual LAN IP, e.g. `10.9.0.123:3000`. If binding to a specific IP fails with `WinError 10049` (address not valid), use `0.0.0.0` or confirm the IP is configured on the NIC.
- **Log to file** — writes protocol traffic to `Protocol.txt` (rotated when it exceeds 2 MB; keep up to `log_file_count` rotated files, e.g. `Protocol_1.txt`, `Protocol_2.txt`, ...).
- **Routing mode** — `barcode` (use the barcode mapping table) or `random` (use per-location random rules). Changing it restarts the TCP server.

## Protocol

Connected PLC sends STX (`\x02`)\[...\]ETX (`\x03`) framed messages.

```
001 or 001|0000|00000          Heartbeat request
001|0000|00000                 Heartbeat response

042|<loc>|<index>|<barcode>    Barcode scan (pipe-delimited)
042<loc[4]><index[5]><barcode> Barcode scan (fixed-width fallback)
050|<loc>|<index>|<dest[5]>    Destination response

044|<loc>|<index>|<dest>|<reason>  Offload event (no response)
```

Offload reason codes recorded:
- `OFL` Attempt to offload
- `SUP` Offload is confirmed
- `WRO` Wrong offload (item sent to one chute, confirmed at another)
- `FUL` Chute unavailable
- `PRK` Awaiting host decision
- `MIS` Item lost
- `RCR` Item passed a specified point on the sorter
- `IFC` Offload attempted but not successful
- `NCG` Cage/Container not in position
- `NCH` Chute has not been assigned

## File layout

```
main.py          FastAPI web app + startup
tcp_server.py    TCP server, protocol parsing, offload session tracking
database.py      SQLite helpers (routing, random rules, settings)
pdf_report.py    Dependency-free PDF generator for offload reports
test_client.py   Simple script that sends a fake 042 scan to test the server
requirements.txt Python dependencies
Protocol.txt     Rotating protocol log file (generated at runtime)
routing.db       SQLite database (created at runtime)
main.spec        PyInstaller build spec
dist/            Built EXEs
static/          CSS/JS for the web UI
templates/       Jinja2 HTML templates
```

## Testing

Run the server, then send a fake scan:

```
python test_client.py
```

Note: `test_client.py` connects to `127.0.0.1:8080` while the default TCP listener port may differ — update `HOST`/`PORT` in the file (or the server settings / routing mode) to match.

## Troubleshooting

- **`WinError 10049` "The requested address is not valid in its context"** — the configured host IP is not assigned to an adapter on this machine right now. Set Host to `0.0.0.0`, or to an IP that's actually on the NIC.
- **PLC connects briefly then disconnects** — the PLC reconnects per transaction; that's normal in the captured log.
- **Missing barcode responses to `00000`** — the barcode isn't in the mapping table, or routing mode is set to `random` with no rule for that location.
- **PDF report fails** — on older versions the report generator had a signature bug (`text_at()` unexpected keyword); the current `_Builder.text_at` accepts `size=`, so rebuild the EXE (`pyinstaller main.spec`) after any changes.