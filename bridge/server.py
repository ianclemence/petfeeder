"""
Pet Feeder Bridge - Serial-to-Web Bridge
=========================================
Reads distance data from Arduino on COM4 (115200 baud)
and exposes it via a simple HTTP server for the web dashboard.

How it works:
  1. Python opens COM4 and reads serial messages from Arduino
  2. Arduino sends "DIST:xx.x" every 500ms with current distance
  3. Python stores the latest reading in memory
  4. Web dashboard polls http://localhost:8080/api/status every second
  5. Dashboard can send "feed" command via POST /api/feed

Usage:
  python bridge/server.py
  Then open http://localhost:8080 in your browser
"""

import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import serial

# ---- CONFIGURATION ----
SERIAL_PORT = "COM4"
BAUD_RATE = 115200
WEB_PORT = 8080
SERIAL_TIMEOUT = 0.1  # Non-blocking serial reads

# ---- GLOBAL STATE ----
state = {
    "distance": 999.0,
    "feeding": False,
    "last_feed": None,
    "status": "waiting",
    "history": [],  # Last 60 readings for the chart
}
state_lock = threading.Lock()

# ---- SERIAL READER THREAD ----
def serial_reader():
    """
    Continuously reads lines from Arduino serial port.
    Parses distance values and feeding events.
    Runs in a background thread so the web server isn't blocked.
    """
    print(f"[BRIDGE] Connecting to {SERIAL_PORT} at {BAUD_RATE} baud...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        time.sleep(2)  # Wait for Arduino to reset after serial connection
        print("[BRIDGE] Connected! Reading sensor data...")
    except serial.SerialException as e:
        print(f"[BRIDGE] ERROR: Cannot open {SERIAL_PORT}: {e}")
        print("[BRIDGE] Make sure Arduino is plugged in and no other program is using the port.")
        return

    while True:
        try:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            # Parse distance messages: "DIST:12.5"
            if line.startswith("DIST:"):
                try:
                    dist = float(line.split(":")[1])
                    with state_lock:
                        state["distance"] = dist
                        # Keep last 60 readings for chart
                        state["history"].append({"t": time.time(), "d": dist})
                        if len(state["history"]) > 60:
                            state["history"] = state["history"][-60:]
                except ValueError:
                    pass

            # Parse feeding events
            elif line == "OPENED":
                with state_lock:
                    state["feeding"] = True
                    state["status"] = "feeding"
                print("[BRIDGE] Servo OPENED - dispensing food")

            elif line == "CLOSED":
                with state_lock:
                    state["feeding"] = False
                    state["status"] = "idle"
                    state["last_feed"] = time.time()
                print("[BRIDGE] Servo CLOSED - feeding complete")

            elif line.startswith("EVENT:"):
                event = line.split(":")[1]
                print(f"[BRIDGE] Event: {event}")

            elif line.startswith("STATUS:"):
                # STATUS:FEEDING:12.5 or STATUS:IDLE:999.0
                parts = line.split(":")
                if len(parts) == 3:
                    with state_lock:
                        state["feeding"] = parts[1] == "FEEDING"
                        state["status"] = "feeding" if state["feeding"] else "idle"
                        try:
                            state["distance"] = float(parts[2])
                        except ValueError:
                            pass

        except serial.SerialException:
            print("[BRIDGE] Serial connection lost! Reconnecting...")
            time.sleep(2)
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
                time.sleep(2)
                print("[BRIDGE] Reconnected!")
            except:
                print("[BRIDGE] Reconnect failed. Will retry...")
                time.sleep(3)

        except Exception as e:
            print(f"[BRIDGE] Unexpected error: {e}")
            time.sleep(1)


# ---- HTTP REQUEST HANDLER ----
class FeederHandler(SimpleHTTPRequestHandler):
    """
    Handles web requests:
      GET  /              -> Serves index.html from web/ folder
      GET  /api/status    -> Returns JSON with current distance + state
      POST /api/feed      -> Sends OPEN command to Arduino
      POST /api/close     -> Sends CLOSE command to Arduino
    """

    def __init__(self, *args, **kwargs):
        # Serve files from the web/ directory
        super().__init__(*args, directory=str(Path(__file__).parent.parent / "web"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            self._send_json(200)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/feed":
            self._send_command("OPEN")
        elif parsed.path == "/api/close":
            self._send_command("CLOSE")
        else:
            self.send_error(404, "Not Found")

    def _send_json(self, code):
        """Send the current state as JSON response."""
        with state_lock:
            data = {
                "distance": state["distance"],
                "feeding": state["feeding"],
                "status": state["status"],
                "last_feed": state["last_feed"],
                "history": state["history"][-30:],  # Last 30 for chart
            }
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_command(self, cmd):
        """Send a command to Arduino via serial."""
        try:
            # We need access to the serial port - use a global reference
            if hasattr(self.server, "serial_port") and self.server.serial_port:
                self.server.serial_port.write(f"{cmd}\n".encode())
                self.server.serial_port.flush()
                self._send_json(200)
            else:
                self.send_error(503, "Serial port not connected")
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        # Suppress default HTTP logging to keep console clean
        if "/api/" in str(args[0]) if args else False:
            pass  # Still log API calls
        else:
            pass  # Suppress static file logs


# ---- MAIN SERVER ----
def main():
    print("=" * 50)
    print("  AUTOMATIC PET FEEDER - Web Dashboard Bridge")
    print("=" * 50)

    # Start serial reader in background thread
    reader_thread = threading.Thread(target=serial_reader, daemon=True)
    reader_thread.start()

    # Start web server
    server = HTTPServer(("0.0.0.0", WEB_PORT), FeederHandler)

    # Attach serial port reference to server for command sending
    try:
        server.serial_port = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        time.sleep(2)
    except:
        server.serial_port = None
        print("[BRIDGE] WARNING: Could not attach serial port for commands")

    print(f"[BRIDGE] Web server running at http://localhost:{WEB_PORT}")
    print("[BRIDGE] Open your browser to view the dashboard")
    print("[BRIDGE] Press Ctrl+C to stop")
    print("-" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
