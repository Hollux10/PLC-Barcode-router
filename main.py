from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import database
import tcp_server
import os
import sys
import webbrowser
import threading

# Determine base path (PyInstaller unpacks assets into a temporary _MEIPASS folder)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# Initialize database on startup
database.init_db()

# Start TCP server in background
tcp_server.run_server_in_background()

app = FastAPI()

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    mappings = database.get_all_mappings()
    random_rules = database.get_all_random_rules()
    settings = database.get_settings()
    return templates.TemplateResponse(
        name="index.html", 
        context={"request": request, "mappings": mappings, "random_rules": random_rules, "settings": settings}
    )

@app.post("/add")
async def add_mapping(barcode: str = Form(...), destination: int = Form(...)):
    success, msg, new_id = database.add_mapping(barcode, destination)
    return {"success": success, "message": msg, "id": new_id}

@app.delete("/delete/{mapping_id}")
async def delete_mapping(mapping_id: int):
    success = database.delete_mapping(mapping_id)
    return {"success": success}

@app.post("/add-random")
async def add_random_rule(location: str = Form(...), destinations: str = Form(...)):
    success, msg, new_id = database.add_random_rule(location, destinations)
    return {"success": success, "message": msg, "id": new_id}

@app.delete("/delete-random/{rule_id}")
async def delete_random_rule(rule_id: int):
    success = database.delete_random_rule(rule_id)
    return {"success": success}

@app.get("/settings")
async def get_settings():
    return database.get_settings()

@app.post("/settings")
async def update_settings(
    host: str = Form(...),
    port: int = Form(...),
    log_to_file: bool = Form(True),
    log_file_count: int = Form(5),
    routing_mode: str = Form("barcode"),
    log_heartbeat: bool = Form(True),
    heartbeat_interval: int = Form(10),
    heartbeat_enabled: bool = Form(True)
):
    success = database.update_settings(host, port, log_to_file, log_file_count, routing_mode, log_heartbeat, heartbeat_interval, heartbeat_enabled)
    if success:
        tcp_server.restart_server()
        return {"success": True, "message": "Settings updated and server restarted"}
    return {"success": False, "message": "Failed to update settings"}

@app.get("/logs")
async def get_logs():
    return {"logs": list(tcp_server.log_history)}

@app.get("/status")
async def get_status():
    settings = database.get_settings()
    plc = tcp_server.get_connection_status()
    return {
        "connected": plc.get("connected", False),
        "plc_ip": plc.get("ip"),
        "plc_port": plc.get("port"),
        "host": settings.get("host", "0.0.0.0"),
        "port": settings.get("port", 8080),
        "running": tcp_server._running,
    }

@app.get("/logs-page", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse(name="logs.html", context={"request": request})

@app.get("/offload", response_class=HTMLResponse)
async def offload_page(request: Request):
    return templates.TemplateResponse(name="offload.html", context={"request": request})

@app.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request):
    return templates.TemplateResponse(name="trends.html", context={"request": request})

@app.get("/offload/data")
async def offload_data():
    return tcp_server.get_offload_status()

@app.post("/offload/start")
async def offload_start():
    tcp_server.start_offload_session()
    return {"success": True}

@app.post("/offload/pause")
async def offload_pause():
    paused = tcp_server.toggle_offload_pause()
    return {"success": True, "paused": paused}

@app.get("/offload/report")
async def offload_report():
    pdf = tcp_server.generate_report()
    if not pdf:
        return {"success": False, "message": "No session data to report"}
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="offload_report.pdf"'},
    )

@app.post("/offload/clear")
async def offload_clear():
    tcp_server.clear_offload_session()
    return {"success": True}

if __name__ == "__main__":
    # Automatically open browser window after 1.5 seconds
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    uvicorn.run(app, host="0.0.0.0", port=5000)
