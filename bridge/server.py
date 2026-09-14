"""
Pet Feeder Bridge v2.0 — Serial-to-Web Bridge
===============================================
Bridges the Arduino's serial output to a web dashboard.

LEARNING GOALS (for students):
  1. How serial communication works between Arduino and PC
  2. How a Python HTTP server serves web pages
  3. How threading lets us read serial AND serve web requests at the same time
  4. How CSV files store data for later analysis

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
from datetime import datetime, date
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import serial
import serial.tools.list_ports

# ---- CONFIGURATION ----
BAUD_RATE = 115200          # Must match the Arduino's Serial.begin() value
WEB_PORT = 8080             # Port for the web dashboard
LOG_DIR = Path(__file__).parent.parent / "logs"
CSV_FILE = LOG_DIR / "feeder_data.csv"


def find_arduino():
    """Auto-detect Arduino/CH340 serial port.
    Instead of hardcoding 'COM4', this scans all serial ports
    and looks for keywords that match common Arduino clones.
    """
    keywords = ["CH340", "Arduino", "USB-SERIAL", "USB Serial"]
    for port in serial.tools.list_ports.comports():
        desc = port.description or ""
        mfg = port.manufacturer or ""
        for kw in keywords:
            if kw.lower() in desc.lower() or kw.lower() in mfg.lower():
                print(f"[BRIDGE] Found device: {desc} on {port.device}")
                return port.device
    return None


# ---- GLOBAL STATE ----
# This dictionary holds the latest data from the Arduino.
# Multiple threads access it, so we use a lock to prevent conflicts.
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
    """Create the CSV log file with column headers if it doesn't exist.
    CSV = Comma-Separated Values. Each line is one data point.
    This lets you open the data in Excel or Google Sheets later.
    """
    LOG_DIR.mkdir(exist_ok=True)
    if not CSV_FILE.exists():
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "distance_cm", "zone", "feeding", "event"])


def log_to_csv(distance, zone, feeding, event=""):
    """Append one row to the CSV log file.
    'a' mode means append (add to end), not overwrite.
    """
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


def get_feeding_stats():
    """Calculate feeding statistics from the CSV log.
    This reads the log file and counts how many feeds happened today,
    calculates the average time between feeds, etc.
    """
    stats = {
        "feeds_today": 0,
        "total_feeds": 0,
        "avg_interval_seconds": 0,
    }

    if not CSV_FILE.exists():
        return stats

    feed_times = []
    today_str = date.today().isoformat()

    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("event") == "OPENED":
                    stats["total_feeds"] += 1
                    ts = row.get("timestamp", "")
                    feed_times.append(ts)
                    if ts.startswith(today_str):
                        stats["feeds_today"] += 1

        # Calculate average interval between feeds
        if len(feed_times) >= 2:
            # Parse the last 20 feed timestamps to compute average gap
            recent = feed_times[-20:]
            timestamps = []
            for ts in recent:
                try:
                    timestamps.append(datetime.fromisoformat(ts))
                except ValueError:
                    pass
            if len(timestamps) >= 2:
                total_seconds = 0
                for i in range(1, len(timestamps)):
                    gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
                    total_seconds += gap
                stats["avg_interval_seconds"] = round(total_seconds / (len(timestamps) - 1))

    except Exception as e:
        print(f"[STATS] Error reading CSV: {e}")

    return stats


def send_command(cmd):
    """Send a command string to the Arduino via serial.
    The \n at the end tells the Arduino "this is the end of the command."
    """
    global serial_port
    if serial_port and serial_port.is_open:
        serial_port.write(f"{cmd}\n".encode())
        serial_port.flush()
        return True
    return False


def serial_reader():
    """Read lines from Arduino and update the global state.
    This runs in a separate thread so it doesn't block the web server.
    """
    global serial_port

    # Wait until the serial port is connected
    while serial_port is None:
        time.sleep(0.1)

    print("[BRIDGE] Connected! Reading sensor data...")
    while True:
        try:
            raw = serial_port.readline()
            if not raw:
                continue

            # Decode bytes to string, ignoring any bad characters
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            # Parse different message types from Arduino

            # DIST:12.5:1 — distance in cm and zone number
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
                            # Keep only the last 120 data points for the chart
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
                except Exception:
                    pass

            elif line.startswith("ACK:COOLDOWN:"):
                try:
                    val = int(line.split(":")[2])
                    with state_lock:
                        state["cooldown"] = val
                    print(f"[BRIDGE] Cooldown set to {val}s")
                except Exception:
                    pass

            elif line.startswith("ACK:ZONE1:"):
                try:
                    val = float(line.split(":")[2])
                    with state_lock:
                        state["zone1"] = val
                except Exception:
                    pass

            elif line.startswith("ACK:ZONE2:"):
                try:
                    val = float(line.split(":")[2])
                    with state_lock:
                        state["zone2"] = val
                except Exception:
                    pass

            elif line.startswith("EVENT:"):
                print(f"[BRIDGE] {line}")

        except serial.SerialException:
            print("[BRIDGE] Serial lost! Waiting...")
            time.sleep(2)
        except Exception as e:
            print(f"[BRIDGE] Error: {e}")
            time.sleep(0.5)


class FeederHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that serves the web dashboard and API."""

    def __init__(self, *args, **kwargs):
        # Serve static files from the web/ directory
        super().__init__(*args, directory=str(Path(__file__).parent.parent / "web"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            self._send_json(200)

        elif parsed.path == "/api/csv":
            self._send_csv()

        elif parsed.path == "/api/stats":
            self._send_stats()

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

    def _send_stats(self):
        """Send feeding statistics as JSON."""
        stats = get_feeding_stats()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(stats).encode())

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
        pass  # Suppress default HTTP request logging


def main():
    global serial_port

    print("=" * 50)
    print("  AUTOMATIC PET FEEDER v2.0 - Web Dashboard Bridge")
    print("=" * 50)

    init_csv()

    serial_port_path = find_arduino()
    if not serial_port_path:
        print("[BRIDGE] ERROR: No Arduino/CH340 found. Check USB connection.")
        sys.exit(1)

    print(f"[BRIDGE] Opening {serial_port_path} at {BAUD_RATE} baud...")
    try:
        serial_port = serial.Serial(serial_port_path, BAUD_RATE, timeout=0.1)
        time.sleep(2)  # Wait for Arduino to reset after serial connection
    except serial.SerialException as e:
        print(f"[BRIDGE] ERROR: Cannot open {serial_port_path}: {e}")
        sys.exit(1)

    # Start the serial reader in a background thread
    # daemon=True means the thread will stop when the main program stops
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
