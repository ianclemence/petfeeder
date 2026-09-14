"""
Pet Feeder Bridge v2.0 - Serial-to-Web Bridge
===============================================
Features:
  - Real-time distance streaming from Arduino
  - Adjustable threshold and cooldown from dashboard
  - CSV data logging for analysis
  - Multi-zone support

Usage:
  python bridge/server.py
  Then open http://localhost:8080
"""

import csv
import json
import os
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import serial

# ---- CONFIGURATION ----
SERIAL_PORT = "COM5"
BAUD_RATE = 115200
WEB_PORT = 8080
LOG_DIR = Path(__file__).parent.parent / "logs"
CSV_FILE = LOG_DIR / "feeder_data.csv"

# ---- GLOBAL STATE ----
state = {
    "distance": 999.0,
    "feeding": False,
    "last_feed": None,
    "status": "waiting",
    "zone": 0,
    "threshold": 20.0,
    "cooldown": 15,
    "zone1": 15.0,
    "zone2": 30.0,
    "history": [],
}
state_lock = threading.Lock()
serial_port = None


def init_csv():
    """Create CSV log file with headers if it doesn't exist."""
    LOG_DIR.mkdir(exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "distance_cm", "zone", "feeding", "event"])


def log_to_csv(distance, zone, feeding, event=""):
    """Append one row to the CSV log."""
    try:
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                round(distance, 1),
                zone,
                feeding,
                event,
            ])
    except Exception as e:
        print(f"[LOG] CSV write error: {e}")


def send_command(cmd):
    """Send a command to Arduino via serial."""
    global serial_port
    if serial_port and serial_port.is_open:
        serial_port.write(f"{cmd}\n".encode())
        serial_port.flush()
        return True
    return False


def serial_reader():
    """Read lines from Arduino, update global state."""
    global serial_port

    while serial_port is None:
        time.sleep(0.1)

    print("[BRIDGE] Connected! Reading sensor data...")
    while True:
        try:
            raw = serial_port.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            # DIST:12.5:1 (distance:zone)
            if line.startswith("DIST:"):
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        dist = float(parts[1])
                        zone = int(parts[2]) if len(parts) > 2 else 0
                        with state_lock:
                            state["distance"] = dist
                            state["zone"] = zone
                            state["history"].append({
                                "t": time.time(),
                                "d": dist,
                                "z": zone,
                            })
                            if len(state["history"]) > 120:
                                state["history"] = state["history"][-120:]
                        log_to_csv(dist, zone, state["feeding"])
                    except (ValueError, IndexError):
                        pass

            elif line == "OPENED":
                with state_lock:
                    state["feeding"] = True
                    state["status"] = "feeding"
                log_to_csv(state["distance"], state["zone"], True, "OPENED")
                print("[BRIDGE] Servo OPENED")

            elif line == "CLOSED":
                with state_lock:
                    state["feeding"] = False
                    state["status"] = "idle"
                    state["last_feed"] = time.time()
                log_to_csv(state["distance"], state["zone"], False, "CLOSED")
                print("[BRIDGE] Servo CLOSED")

            elif line.startswith("ACK:THRESHOLD:"):
                try:
                    val = float(line.split(":")[2])
                    with state_lock:
                        state["threshold"] = val
                    print(f"[BRIDGE] Threshold set to {val}cm")
                except: pass

            elif line.startswith("ACK:COOLDOWN:"):
                try:
                    val = int(line.split(":")[2])
                    with state_lock:
                        state["cooldown"] = val
                    print(f"[BRIDGE] Cooldown set to {val}s")
                except: pass

            elif line.startswith("ACK:ZONE1:"):
                try:
                    val = float(line.split(":")[2])
                    with state_lock:
                        state["zone1"] = val
                except: pass

            elif line.startswith("ACK:ZONE2:"):
                try:
                    val = float(line.split(":")[2])
                    with state_lock:
                        state["zone2"] = val
                except: pass

            elif line.startswith("EVENT:"):
                print(f"[BRIDGE] {line}")

        except serial.SerialException:
            print("[BRIDGE] Serial lost! Waiting...")
            time.sleep(2)
        except Exception as e:
            print(f"[BRIDGE] Error: {e}")
            time.sleep(0.5)


class FeederHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent.parent / "web"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            self._send_json(200)

        elif parsed.path == "/api/csv":
            self._send_csv()

        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/api/feed":
            self._send_command("OPEN")

        elif parsed.path == "/api/close":
            self._send_command("CLOSE")

        elif parsed.path == "/api/threshold":
            val = params.get("val", [None])[0]
            if val:
                self._send_command(f"SET_THRESHOLD:{val}")
                self._send_json(200)
            else:
                self.send_error(400, "Missing val param")

        elif parsed.path == "/api/cooldown":
            val = params.get("val", [None])[0]
            if val:
                self._send_command(f"SET_COOLDOWN:{val}")
                self._send_json(200)
            else:
                self.send_error(400, "Missing val param")

        elif parsed.path == "/api/zone1":
            val = params.get("val", [None])[0]
            if val:
                self._send_command(f"SET_ZONE1:{val}")
                self._send_json(200)
            else:
                self.send_error(400, "Missing val param")

        elif parsed.path == "/api/zone2":
            val = params.get("val", [None])[0]
            if val:
                self._send_command(f"SET_ZONE2:{val}")
                self._send_json(200)
            else:
                self.send_error(400, "Missing val param")

        else:
            self.send_error(404, "Not Found")

    def _send_json(self, code):
        with state_lock:
            data = {
                "distance": state["distance"],
                "feeding": state["feeding"],
                "status": state["status"],
                "last_feed": state["last_feed"],
                "zone": state["zone"],
                "threshold": state["threshold"],
                "cooldown": state["cooldown"],
                "zone1": state["zone1"],
                "zone2": state["zone2"],
                "history": state["history"][-60:],
            }
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_csv(self):
        """Send the CSV file for download."""
        try:
            with open(CSV_FILE, "r") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=feeder_data.csv")
            self.end_headers()
            self.wfile.write(content.encode())
        except FileNotFoundError:
            self.send_error(404, "No data logged yet")

    def _send_command(self, cmd):
        if send_command(cmd):
            self._send_json(200)
        else:
            self.send_error(503, "Serial not connected")

    def log_message(self, format, *args):
        pass


def main():
    global serial_port

    print("=" * 50)
    print("  AUTOMATIC PET FEEDER v2.0 - Web Dashboard Bridge")
    print("=" * 50)

    init_csv()

    print(f"[BRIDGE] Opening {SERIAL_PORT} at {BAUD_RATE} baud...")
    try:
        serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)
    except serial.SerialException as e:
        print(f"[BRIDGE] ERROR: Cannot open {SERIAL_PORT}: {e}")
        sys.exit(1)

    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", WEB_PORT), FeederHandler)
    print(f"[BRIDGE] Dashboard: http://localhost:{WEB_PORT}")
    print(f"[BRIDGE] CSV Log: {CSV_FILE}")
    print("[BRIDGE] Press Ctrl+C to stop")
    print("-" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Shutting down...")
        server.shutdown()
        serial_port.close()


if __name__ == "__main__":
    main()
