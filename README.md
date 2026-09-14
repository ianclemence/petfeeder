# Automatic Pet Feeder

> [README ภาษาไทย](README_TH.md) | [คู่มือติดตั้งภาษาไทย](SETUP_TH.md) | [English Setup Guide](SETUP.md)

An Arduino-based automatic pet feeder that uses an ultrasonic distance sensor to detect when a pet is nearby and automatically dispenses food by opening a servo-controlled gate.

**No timer** — purely proximity-triggered with a cooldown to prevent overfeeding.

## For Students — What You'll Learn

| Concept | Where | What It Teaches |
|---------|-------|-----------------|
| **Modular code** | `firmware/*.h` | Splitting code into files with `#include` |
| **Ultrasonic sensing** | `sensor.h` | How sound waves measure distance |
| **Servo control** | `servo_control.h` | PWM signals and motor angles |
| **Serial protocol** | `commands.h` | Device-to-PC communication |
| **HTTP server** | `server.py` | Python networking basics |
| **CSV logging** | `server.py` | Data storage and analysis |
| **JSON APIs** | `server.py` | REST endpoint design |
| **Real-time dashboard** | `index.html` | Polling, canvas charts, DOM updates |

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
├── README.md                 # This file
├── README_TH.md              # บทนำโครงการ (Thai)
├── SETUP.md                  # Setup guide (English)
└── SETUP_TH.md               # คู่มือติดตั้ง (Thai)
```

## Hardware Requirements

| Component | Purpose | Pin |
|-----------|---------|-----|
| Arduino UNO (CH340 clone) | Microcontroller | USB to PC |
| HC-SR04 Ultrasonic Sensor | Detects pet distance | Trig=D9, Echo=D10 |
| SG90 Micro Servo | Opens/closes food gate | Signal=D6 |
| Jumper wires (M-M) | Connections | — |
| USB Type-B cable | Power + programming | — |

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

## Setup Instructions

### Step 1: Install Python Dependencies

```bash
cd bridge
pip install -r requirements.txt
```

### Step 2: Flash the Firmware

The firmware has already been flashed to your Arduino on COM4. If you need to re-flash:

```bash
# Using arduino-cli (no Arduino IDE needed)
arduino-cli compile --fqbn arduino:avr:uno firmware/pet_feeder/pet_feeder.ino
arduino-cli upload --fqbn arduino:avr:uno --port COM4 firmware/pet_feeder/pet_feeder.ino
```

### Step 3: Start the Web Dashboard

```bash
cd bridge
python server.py
```

Then open **http://localhost:8080** in your browser.

## How It Works

### Firmware (Arduino)

1. The HC-SR04 sensor measures distance every 500ms using ultrasonic pulses
2. If a pet is detected within 20cm AND the 15-second cooldown has passed:
   - Servo opens to 90° (dispenses food)
   - Waits 3 seconds (hold time)
   - Servo closes back to 0°
3. All events are sent to the PC via Serial at 115200 baud

### Bridge (Python)

1. Opens COM4 and reads serial messages from Arduino
2. Stores the latest distance and feeding state in memory
3. Serves a web dashboard on port 8080
4. Passes commands (feed/stop) from the dashboard to Arduino
5. Logs all events to a CSV file for analysis
6. Provides feeding statistics (feeds today, average interval)

### Dashboard (HTML/JS)

1. Polls the Python bridge every second for current status
2. Displays distance with color coding (green = pet detected, red = far)
3. Shows real-time distance chart
4. Shows feeding stats (today, all-time, average interval)
5. Manual feed button for testing

## Customization

Edit `firmware/pet_feeder/config.h`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `detection_range_cm` | 20.0 | How close the pet must be (cm) |
| `cooldown_seconds` | 15 | Minimum time between feeds (seconds) |
| `zone1_close_cm` | 15.0 | Full portion zone distance (cm) |
| `zone2_medium_cm` | 30.0 | Half portion zone distance (cm) |
| `ZONE_FULL_ANGLE` | 90 | How far the gate opens for full portion (degrees) |
| `ZONE_HALF_ANGLE` | 45 | How far the gate opens for half portion (degrees) |
| `HOLD_TIME_MS` | 3000 | How long the gate stays open (ms) |

## Common Mistakes (and How to Fix Them)

| Mistake | What Happens | How to Fix |
|---------|-------------|------------|
| **Wrong COM port** | "Cannot open COM4" | Check Device Manager for your Arduino's port, update in `server.py` |
| **Servo jitters** | Gate opens/closes randomly | Use external 5V power for servo, not just USB power |
| **Distance stuck at 999** | No pet ever detected | Check TRIG/D9 and ECHO/D10 wiring — they might be swapped |
| **Coiled servo** | Servo doesn't move | Red wire must go to 5V, brown to GND, orange to D6 |
| **Dashboard won't load** | Page shows "Connecting" | Make sure `python server.py` is running in the terminal |
| **CH340 not detected** | Arduino not found | Install CH340 driver: https://www.wch-ic.com/downloads/CH341SER_EXE.html |
| **Compiler error** | "fatal error: Servo.h" | Run `arduino-cli lib install Servo` first |
| **Data not saving** | No CSV file created | Check that the `logs/` folder exists and is writable |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot open COM4" | Close Arduino Serial Monitor or any other serial program |
| No distance readings | Check TRIG/D9 and ECHO/D10 wiring |
| Servo doesn't move | Check servo power (5V) and signal wire (D6) |
| Dashboard shows "Disconnected" | Make sure `python server.py` is running |
| CH340 not recognized | Install CH340 driver from https://www.wch-ic.com/downloads/CH341SER_EXE.html |
