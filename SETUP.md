# Pet Feeder Project — Student Setup Guide

## Prerequisites

### Hardware
- Arduino UNO (CH340 clone)
- HC-SR04 Ultrasonic Sensor
- SG90 Micro Servo
- Jumper wires (M-M)
- USB Type-B cable

### Software
- Python 3.8+ — https://python.org
- Arduino CLI — `winget install Arduino.CLI`
- Git — https://git-scm.com
- CH340 Driver (if Arduino not detected) — https://www.wch-ic.com/downloads/CH341SER_EXE.html

---

## Wiring Diagram

```
  Arduino UNO            HC-SR04            SG90 Servo
 ┌──────────┐         ┌──────────┐       ┌──────────┐
 │          │         │          │       │          │
 │      5V  ├─────────┤ VCC      │       │          │
 │      GND ├─────────┤ GND      │       │          │
 │       D9 ├─────────┤ TRIG     │       │          │
 │      D10 ├─────────┤ ECHO     │       │          │
 │          │         │          │       │          │
 │      5V  ├────────────────────────────┤ RED (+)  │
 │      GND ├────────────────────────────┤ BROWN (-)│
 │       D6 ├────────────────────────────┤ ORANGE   │
 └──────────┘                           └──────────┘
```

| Arduino | Component | Purpose |
|---------|-----------|---------|
| 5V | HC-SR04 VCC | Power sensor |
| GND | HC-SR04 GND | Ground sensor |
| D9 | HC-SR04 TRIG | Trigger ultrasonic pulse |
| D10 | HC-SR04 ECHO | Read echo response |
| 5V | Servo RED (+) | Power servo |
| GND | Servo BROWN (-) | Ground servo |
| D6 | Servo ORANGE | Control servo angle |

---

## Step-by-Step Setup

### Step 1 — Clone the Repository

```bash
git clone https://github.com/ianclemence/petfeeding-detector.git
cd petfeeding-detector
```

### Step 2 — Install Python Dependencies

```bash
cd bridge
pip install -r requirements.txt
cd ..
```

### Step 3 — Find Your COM Port

**Windows:**
1. Open Device Manager
2. Expand "Ports (COM & LPT)"
3. Look for "USB-SERIAL CH340 (COMx)" — note the port number

**Mac/Linux:**
```bash
ls /dev/tty.*
# or
ls /dev/ttyUSB*
```

### Step 4 — Update COM Port in server.py

Open `bridge/server.py` and change line 29 to match your port:

```python
SERIAL_PORT = "COM5"  # change to your port, e.g., "COM3", "COM7"
```

### Step 5 — Flash the Firmware to Arduino

```bash
arduino-cli compile --fqbn arduino:avr:uno firmware/pet_feeder/pet_feeder.ino
arduino-cli upload --fqbn arduino:avr:uno --port COMx firmware/pet_feeder/pet_feeder.ino
```

Replace `COMx` with your actual port number.

> **Note:** Close the Arduino Serial Monitor before flashing.

### Step 6 — Start the Bridge Server

```bash
cd bridge
python server.py
```

You should see:
```
==================================================
  AUTOMATIC PET FEEDER v1.0 - Web Dashboard Bridge
==================================================
[BRIDGE] Opening COM5 at 115200 baud...
[BRIDGE] Connected! Reading sensor data...
[BRIDGE] Dashboard: http://localhost:8080
[BRIDGE] Press Ctrl+C to stop
--------------------------------------------------
```

### Step 7 — Open the Dashboard

Open your browser and go to: **http://localhost:8080**

### Step 8 — Test the System

1. **Distance Reading** — Place your hand near the sensor (<20cm), watch the distance update
2. **Auto Feed** — Stay within 20cm for 3+ seconds, the servo should open
3. **Manual Feed** — Click the "Manual Feed" button
4. **Settings** — Adjust threshold and cooldown sliders
5. **Chart** — Watch the real-time distance history graph
6. **CSV Log** — Click "Download CSV Log" to export data

---

## Customization

Edit the top of `firmware/pet_feeder/pet_feeder.ino`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DETECT_DISTANCE_CM` | 20.0 | How close the pet must be (cm) |
| `COOLDOWN_MS` | 15000 | Minimum time between feeds (ms) |
| `SERVO_OPEN_ANGLE` | 90 | How far the gate opens (degrees) |
| `HOLD_TIME_MS` | 3000 | How long the gate stays open (ms) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot open COMx" | Close Arduino Serial Monitor, update COM port in `server.py` |
| No distance readings | Check TRIG/D9 and ECHO/D10 wiring |
| Servo doesn't move | Check servo power (5V) and signal wire (D6) |
| Dashboard shows "Disconnected" | Make sure `python server.py` is running |
| CH340 not recognized | Install CH340 driver from the link above |
| Python not found | Add Python to PATH during install, or use `py` instead of `python` |
| `pip` not found | Use `python -m pip install -r requirements.txt` |

---

## Project Structure

```
petfeeder/
├── firmware/
│   └── pet_feeder/
│       ├── pet_feeder.ino    # Main program (setup + loop)
│       ├── config.h          # All settings you can change
│       ├── sensor.h          # Ultrasonic distance reading
│       ├── servo_control.h   # Servo motor control
│       └── commands.h        # Serial command handling
├── bridge/
│   ├── server.py             # Python serial-to-web bridge
│   └── requirements.txt      # Python dependencies
├── web/
│   └── index.html            # Browser dashboard
├── logs/                     # CSV data logs (auto-created)
├── README.md                 # Project overview
├── README_TH.md              # บทนำโครงการ (Thai)
├── SETUP.md                  # This file (English)
├── SETUP_TH.md               # คู่มือติดตั้ง (Thai)
└── .gitignore
```
