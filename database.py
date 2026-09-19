import os
import sqlite3
import sys
import threading

def _get_db_path():
    base = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "routing.db")

DB_FILE = _get_db_path()
# Lock to ensure thread-safe sqlite access if needed, though SQLite handles it well if using separate connections.
# For simplicity, we create a connection per thread.

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            destination INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            host TEXT NOT NULL,
            port INTEGER NOT NULL
        )
    ''')
    # Drop legacy plc_ip/plc_port columns if they exist from an older version
    try:
        cursor.execute("ALTER TABLE settings DROP COLUMN plc_ip")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE settings DROP COLUMN plc_port")
    except Exception:
        pass
    # Add log_to_file/log_file_count/routing_mode columns if upgrading
    try:
        cursor.execute("ALTER TABLE settings ADD COLUMN log_to_file INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE settings ADD COLUMN log_file_count INTEGER NOT NULL DEFAULT 5")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE settings ADD COLUMN routing_mode TEXT NOT NULL DEFAULT 'barcode'")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE settings ADD COLUMN log_heartbeat INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS random_routing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            destinations TEXT NOT NULL
        )
    ''')

    # Insert default settings if not exists
    cursor.execute("INSERT OR IGNORE INTO settings (id, host, port, log_to_file, log_file_count, routing_mode) VALUES (1, '0.0.0.0', 8080, 1, 5, 'barcode')")
    conn.commit()
    conn.close()

def get_settings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT host, port, log_to_file, log_file_count, routing_mode, log_heartbeat FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "host": row[0],
            "port": row[1],
            "log_to_file": bool(row[2]),
            "log_file_count": row[3] if row[3] else 5,
            "routing_mode": row[4] if row[4] else 'barcode',
            "log_heartbeat": bool(row[5]) if row[5] is not None else True,
        }
    return {"host": "0.0.0.0", "port": 8080, "log_to_file": True, "log_file_count": 5, "routing_mode": "barcode", "log_heartbeat": True}

def update_settings(host: str, port: int, log_to_file: bool = False, log_file_count: int = 5, routing_mode: str = "barcode", log_heartbeat: bool = True):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET host = ?, port = ?, log_to_file = ?, log_file_count = ?, routing_mode = ?, log_heartbeat = ? WHERE id = 1",
                   (host, port, 1 if log_to_file else 0, log_file_count, routing_mode, 1 if log_heartbeat else 0))
    conn.commit()
    conn.close()
    return True

def get_all_mappings():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, barcode, destination FROM routing ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "barcode": row[1], "destination": row[2]} for row in rows]

def add_mapping(barcode: str, destination: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO routing (barcode, destination) VALUES (?, ?)", (barcode, destination))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return True, "Mapping added successfully", new_id
    except sqlite3.IntegrityError:
        return False, "Barcode already exists", None
    except Exception as e:
        return False, str(e), None

def delete_mapping(mapping_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM routing WHERE id = ?", (mapping_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def get_destination(barcode: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT destination FROM routing WHERE barcode = ?", (barcode,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_all_random_rules():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, location, destinations FROM random_routing ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "location": row[1], "destinations": row[2]} for row in rows]

def add_random_rule(location: str, destinations: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO random_routing (location, destinations) VALUES (?, ?)", (location, destinations))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return True, "Location random rule added", new_id
    except Exception as e:
        return False, str(e), None

def delete_random_rule(rule_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM random_routing WHERE id = ?", (rule_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def get_random_destination(location: str):
    import random
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT destinations FROM random_routing WHERE location = ?", (location,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        # Parse comma-separated destinations e.g. "10, 20, 100"
        raw_list = [d.strip() for d in row[0].split(",") if d.strip().isdigit()]
        if raw_list:
            chosen = random.choice(raw_list)
            return int(chosen)
    return None
