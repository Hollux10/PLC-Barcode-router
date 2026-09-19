import socket
import threading
import logging
from database import get_destination, get_settings
import time
from collections import deque
import os

# Keep a recent log history in memory for the UI to fetch
log_history = deque(maxlen=200)

# Offload event reason codes: code -> human readable label
OFFLOAD_REASONS = {
    "OFL": "Attempt to offload",
    "SUP": "Offload is confirmed",
    "WRO": "Wrong Offload",
    "FUL": "Chute Unavailable",
    "PRK": "Awaiting Host Decision",
    "MIS": "Item lost",
    "RCR": "Item has passed a specified point on the sorter",
    "IFC": "Offload was attempted but not successful",
    "NCG": "Cage/Container not in position",
    "NCH": "Chute has not been Assigned",
}

# Offload session state (counted only while a session is active)
_offload_lock = threading.Lock()
_offload_session_active = False
_offload_session_paused = False
_offload_session_started = None
_offload_session_started_str = None
_offload_counts = {}
_offload_events = deque(maxlen=200)
_offload_by_dest = {}
_offload_trends = {}

# Destination sent to the PLC for each item, keyed by (location, item index).
# Used to detect wrong offloads: item sent to one destination but confirmed (SUP) at another.
_offload_sent = {}

def _remember_sent_destination(loc_id, item_index, dest):
    """Record the destination we sent to the PLC for an item (from a 042 scan)."""
    with _offload_lock:
        _offload_sent[(str(loc_id).strip(), str(item_index).strip())] = (None if dest is None else int(dest))

def start_offload_session():
    """Reset counters and begin counting offload events."""
    global _offload_session_active, _offload_session_paused, _offload_counts, _offload_events
    global _offload_by_dest, _offload_trends, _offload_session_started, _offload_session_started_str
    global _offload_sent
    with _offload_lock:
        _offload_session_active = True
        _offload_session_paused = False
        _offload_session_started = time.time()
        _offload_session_started_str = time.strftime("%Y-%m-%d %H:%M:%S")
        _offload_counts = {code: 0 for code in OFFLOAD_REASONS}
        _offload_events.clear()
        _offload_by_dest = {}
        _offload_trends = {}
        _offload_sent = {}
    add_log("Offload session started.", "info")
    return True

def clear_offload_session():
    """Clear all offload event counts and events."""
    global _offload_session_active, _offload_session_paused, _offload_counts, _offload_events
    global _offload_by_dest, _offload_trends, _offload_session_started, _offload_session_started_str
    global _offload_sent
    with _offload_lock:
        _offload_session_active = False
        _offload_session_paused = False
        _offload_session_started = None
        _offload_session_started_str = None
        _offload_counts = {code: 0 for code in OFFLOAD_REASONS}
        _offload_events.clear()
        _offload_by_dest = {}
        _offload_trends = {}
        _offload_sent = {}
    add_log("Offload session cleared.", "info")
    return True

def toggle_offload_pause():
    """Pause or resume recording without clearing collected data."""
    global _offload_session_paused
    with _offload_lock:
        if not _offload_session_active:
            return False
        _offload_session_paused = not _offload_session_paused
        state = _offload_session_paused
    if state:
        add_log("Offload session paused.", "warning")
    else:
        add_log("Offload session resumed.", "info")
    return state

def get_offload_status():
    with _offload_lock:
        attempts = _offload_counts.get("OFL", 0)
        confirmed = _offload_counts.get("SUP", 0)
        success_rate = (confirmed / attempts * 100) if attempts else 0

        by_dest = []
        for dest, dcounts in sorted(_offload_by_dest.items()):
            dest_attempts = dcounts.get("OFL", 0)
            dest_confirmed = dcounts.get("SUP", 0)
            dest_wrong = dcounts.get("WRO", 0)
            by_dest.append({
                "destination": dest,
                "counts": dict(dcounts),
                "total": sum(dcounts.values()),
                "attempts": dest_attempts,
                "confirmed": dest_confirmed,
                "wrong": dest_wrong,
                "success_rate": round(dest_confirmed / dest_attempts * 100, 1) if dest_attempts else 0,
            })

        trends = []
        for t in sorted(_offload_trends.keys()):
            bucket = _offload_trends[t]
            dests = bucket.get("dests", {})
            entries = []
            for dest, dcounts in sorted(dests.items()):
                entries.append({
                    "destination": dest,
                    "attempts": dcounts.get("OFL", 0),
                    "confirmed": dcounts.get("SUP", 0),
                    "wrong": dcounts.get("WRO", 0),
                    "total": sum(dcounts.values()),
                })
            trends.append({
                "time": t,
                "attempts": sum(e["attempts"] for e in entries),
                "confirmed": sum(e["confirmed"] for e in entries),
                "total": sum(e["total"] for e in entries),
                "dests": entries,
            })

        return {
            "session_active": _offload_session_active,
            "paused": _offload_session_paused,
            "counts": dict(_offload_counts),
            "events": list(_offload_events),
            "reasons": dict(OFFLOAD_REASONS),
            "total": sum(_offload_counts.values()),
            "attempts": attempts,
            "confirmed": confirmed,
            "wrong_offloads": _offload_counts.get("WRO", 0),
            "success_rate": round(success_rate, 1),
            "by_dest": by_dest,
            "trends": trends,
        }

def generate_report():
    """Build a PDF report from the current offload session data."""
    from pdf_report import build_report_pdf

    status = get_offload_status()

    now = time.time()
    started_epoch = None
    started_display = "Not recorded"
    with _offload_lock:
        started_epoch = _offload_session_started
        started_display = _offload_session_started_str or "Not recorded"

    if started_epoch:
        duration = now - started_epoch
        duration_str = f"{int(duration // 60)} min {int(duration % 60)} s"
    else:
        duration_str = "-"

    data = {
        "title": "Offload Session Report",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "started": started_display,
        "duration": duration_str,
        "total": status["total"],
        "attempts": status["attempts"],
        "confirmed": status["confirmed"],
        "wrong_offloads": status["wrong_offloads"],
        "success_rate": status["success_rate"],
        "counts": [
            {"code": code, "label": label, "count": status["counts"].get(code, 0)}
            for code, label in status["reasons"].items()
        ],
        "by_dest": status["by_dest"],
        "events": status["events"],
    }
    try:
        return build_report_pdf(data)
    except Exception as e:
        add_log(f"Failed to generate PDF report: {e}", "error")
        return None

def _record_offload(loc_id, item_index, dest, reason):
    with _offload_lock:
        if not _offload_session_active or _offload_session_paused:
            return
        code = reason.upper()
        event = {
            "time": time.strftime("%H:%M:%S"),
            "location": loc_id,
            "item": item_index,
            "destination": dest,
            "reason": code,
            "sent_destination": None,
            "wrong_offload": False,
        }

        # Wrong offload: the item was sent to one destination, but the PLC
        # confirms (SUP) at a different one. Report such events as WRO.
        if code == "SUP":
            sent = _offload_sent.get((str(loc_id).strip(), str(item_index).strip()))
            try:
                confirmed_val = int(dest)
            except (TypeError, ValueError):
                confirmed_val = None
            if sent is not None:
                event["sent_destination"] = f"{sent:05d}"
            if sent is not None and confirmed_val is not None and sent != 0 and sent != confirmed_val:
                code = "WRO"
                event["reason"] = "WRO"
                event["wrong_offload"] = True
                add_log(f"Wrong offload | Loc={loc_id} | Item={item_index} | Sent={event['sent_destination']} | Confirmed={dest}", "warning")

        _offload_counts[code] = _offload_counts.get(code, 0) + 1
        dest_info = _offload_by_dest.setdefault(dest, {})
        dest_info[code] = dest_info.get(code, 0) + 1

        minute = time.strftime("%H:%M")
        bucket = _offload_trends.setdefault(minute, {})
        dests = bucket.setdefault("dests", {})
        dcounts = dests.setdefault(dest, {})
        dcounts[code] = dcounts.get(code, 0) + 1

        _offload_events.appendleft(event)

_server_thread = None
_running = False
_server_socket = None
_file_log_lock = threading.Lock()

# Current PLC connection state (for the dashboard status widget)
_connection_lock = threading.Lock()
_current_plc = {"connected": False, "ip": None, "port": None}

def get_connection_status():
    """Return the current PLC connection state."""
    with _connection_lock:
        return dict(_current_plc)

MAX_FILE_SIZE = 2048 * 1024  # 2048 kB in bytes

def _rotate_and_write_file_log(line: str, max_files: int):
    """
    Writes a line to Protocol.txt. If Protocol.txt exceeds 2048 kB (2MB):
    - Shift existing Protocol_N.txt files: Protocol_4.txt -> Protocol_5.txt, etc.
    - Protocol.txt -> Protocol_1.txt
    - Create a fresh Protocol.txt
    - Files beyond max_files are removed.
    """
    with _file_log_lock:
        try:
            base_file = "Protocol.txt"
            
            # Check size of active log file
            if os.path.exists(base_file) and os.path.getsize(base_file) >= MAX_FILE_SIZE:
                # Rotate existing numbered files from highest index down to 1
                for i in range(max_files - 1, 0, -1):
                    src = f"Protocol_{i}.txt" if i > 1 else "Protocol_1.txt"
                    dst = f"Protocol_{i+1}.txt"
                    
                    if i + 1 > max_files:
                        # Remove files exceeding file count limit
                        if os.path.exists(f"Protocol_{i}.txt"):
                            os.remove(f"Protocol_{i}.txt")
                        continue

                    if os.path.exists(src):
                        if os.path.exists(dst):
                            os.remove(dst)
                        os.rename(src, dst)

                # Rename Protocol.txt to Protocol_1.txt
                if os.path.exists(base_file):
                    if os.path.exists("Protocol_1.txt"):
                        os.remove("Protocol_1.txt")
                    os.rename(base_file, "Protocol_1.txt")

            # Append log line to Protocol.txt
            with open(base_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logging.error(f"Failed to write log file: {e}")

def add_log(msg: str, msg_type="info"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    time_only = time.strftime("%H:%M:%S")
    
    log_entry = {"time": time_only, "message": msg, "type": msg_type}
    log_history.appendleft(log_entry)
    
    log_line = f"[{timestamp}] [{msg_type.upper()}] {msg}"
    logging.info(log_line)

    # Check database settings to see if file logging is enabled
    try:
        settings = get_settings()
        if settings.get("log_to_file", False):
            max_files = settings.get("log_file_count", 5)
            _rotate_and_write_file_log(log_line, max_files)
    except Exception:
        pass

def process_plc_message(data: str) -> str:
    """
    Heartbeat Request:
      001 or 001|0000|00000
    Heartbeat Response:
      001|0000|00000

    Barcode Scan Request (Pipe-delimited):
      042|3001|12345|ABCDEFG
    Barcode Scan Response:
      050|3001|12345|00010 (echo location and index, append 5-digit destination)

    Barcode Scan Request (Fixed-width fallback):
      042 + 4-char loc + 5-char item + barcode
    """
    if data.startswith("001"):
        settings = get_settings()
        if settings.get("log_heartbeat", True):
            add_log("RX 001 | Heartbeat received", "receive")
        response = "001|0000|00000"
        if settings.get("log_heartbeat", True):
            add_log(f"TX 001 | Heartbeat response: '{response}'", "send")
        return response

    if not data.startswith("042"):
        if data.startswith("044"):
            # Offload event: 044|location|item_index|destination|reason
            if "|" in data:
                parts = data.split("|")
                if len(parts) >= 5:
                    loc_id     = parts[1]
                    item_index = parts[2]
                    dest       = parts[3]
                    reason     = parts[4].strip().upper()
                    add_log(f"RX 044 | Offload event | Loc={loc_id} | Item={item_index} | Dest={dest} | Reason={reason}", "receive")
                    _record_offload(loc_id, item_index, dest, reason)
                    return None
            add_log(f"RX 044 | Malformed offload event: '{data}'", "warning")
            return None

        add_log(f"RX | Raw: '{data}'", "receive")
        return None

    # Check routing mode setting ('barcode' vs 'random')
    settings = get_settings()
    mode = settings.get("routing_mode", "barcode")

    # Check for pipe-delimited format: 042|location|index|barcode
    if "|" in data:
        parts = data.split("|")
        if len(parts) >= 4:
            msg_id = parts[0]
            loc_id = parts[1]
            item_index = parts[2]
            barcode = "|".join(parts[3:]).strip()

            add_log(f"RX 042 | Loc={loc_id} | Index={item_index} | Barcode='{barcode}'", "receive")

            if mode == "random":
                from database import get_random_destination
                dest = get_random_destination(loc_id)
                mode_label = f"Random for Loc {loc_id}"
            else:
                dest = get_destination(barcode)
                mode_label = f"Barcode Map"

            dest_str = f"{dest:05d}" if dest is not None else "00000"
            _remember_sent_destination(loc_id, item_index, dest)

            response = f"050|{loc_id}|{item_index}|{dest_str}"
            log_type = "send" if dest is not None else "error"
            add_log(f"TX 050 [{mode_label}] | Loc={loc_id} | Index={item_index} | Dest={dest_str}", log_type)
            return response

    # Fallback to fixed-width format if no pipes present
    if len(data) < 12:
        add_log(f"Message too short ({len(data)} chars): '{data}'", "warning")
        return None

    loc_id     = data[3:7]
    item_index = data[7:12]
    barcode    = data[12:].strip()

    add_log(f"RX 042 | Loc={loc_id} | Index={item_index} | Barcode='{barcode}'", "receive")

    if mode == "random":
        from database import get_random_destination
        dest = get_random_destination(loc_id)
        mode_label = f"Random for Loc {loc_id}"
    else:
        dest = get_destination(barcode)
        mode_label = f"Barcode Map"

    dest_str = f"{dest:05d}" if dest is not None else "00000"
    _remember_sent_destination(loc_id, item_index, dest)

    response = f"050|{loc_id}|{item_index}|{dest_str}"
    log_type = "send" if dest is not None else "error"
    add_log(f"TX 050 [{mode_label}] | Loc={loc_id} | Index={item_index} | Dest={dest_str}", log_type)
    return response


def handle_client(conn, addr):
    add_log(f"PLC connected from {addr[0]}:{addr[1]}", "info")
    with _connection_lock:
        _current_plc["connected"] = True
        _current_plc["ip"] = addr[0]
        _current_plc["port"] = addr[1]
    conn.settimeout(1.0)
    buffer = b""
    with conn:
        while _running:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break

                buffer += chunk

                # Process all complete framed messages delimited by STX (\x02) and ETX (\x03)
                while b'\x03' in buffer:
                    # Find end of first complete frame
                    etx_idx = buffer.find(b'\x03')
                    raw_frame = buffer[:etx_idx]
                    buffer = buffer[etx_idx + 1:]  # Keep remaining data in buffer

                    # Strip leading STX (\x02) if present
                    if b'\x02' in raw_frame:
                        stx_idx = raw_frame.find(b'\x02')
                        raw_frame = raw_frame[stx_idx + 1:]

                    # Decode single message frame
                    try:
                        text = raw_frame.decode("utf-8")
                    except UnicodeDecodeError:
                        text = raw_frame.decode("latin-1")

                    cleaned_text = text.replace('\x02', '').replace('\x03', '').strip()
                    if cleaned_text:
                        response_str = process_plc_message(cleaned_text)
                        if response_str:
                            # Wrap response in STX/ETX framing
                            conn.sendall(b'\x02' + response_str.encode("utf-8") + b'\x03')

            except socket.timeout:
                continue
            except ConnectionResetError:
                break
            except Exception as e:
                add_log(f"Client error: {e}", "error")
                break

    with _connection_lock:
        _current_plc["connected"] = False
        _current_plc["ip"] = None
        _current_plc["port"] = None
    add_log(f"PLC disconnected from {addr[0]}:{addr[1]}", "warning")


def _start_tcp_server_loop():
    global _server_socket, _running
    settings = get_settings()
    host = settings.get("host", "0.0.0.0")
    port = settings.get("port", 8080)

    _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    _server_socket.settimeout(1.0)

    try:
        _server_socket.bind((host, port))
        _server_socket.listen()
        add_log(f"TCP Server listening on {host}:{port}", "info")

        while _running:
            try:
                conn, addr = _server_socket.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if _running:
                    add_log(f"Accept error: {e}", "error")
    except Exception as e:
        add_log(f"Failed to start TCP server on {host}:{port} — {e}", "error")
    finally:
        if _server_socket:
            _server_socket.close()
            _server_socket = None
        add_log("TCP Server stopped.", "info")


def run_server_in_background():
    global _running, _server_thread
    if _running:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    _running = True
    _server_thread = threading.Thread(target=_start_tcp_server_loop, daemon=True)
    _server_thread.start()


def stop_server():
    global _running, _server_thread
    _running = False
    if _server_thread:
        _server_thread.join(timeout=3.0)
        _server_thread = None


def restart_server():
    add_log("Restarting TCP Server with new settings...", "warning")
    stop_server()
    run_server_in_background()
