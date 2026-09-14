# Automatic Pet Feeder

An Arduino-based automatic pet feeder that uses an ultrasonic distance sensor to detect when a pet is nearby and automatically dispenses food by opening a servo-controlled gate.

**No timer** — purely proximity-triggered with a cooldown to prevent overfeeding.

## Project Structure

```
catfeeding/
├── firmware/
│   └── pet_feeder/
│       └── pet_feeder.ino    # Arduino firmware (C++)
├── bridge/
│   ├── server.py             # Python serial-to-web bridge
│   └── requirements.txt      # Python dependencies
├── web/
│   └── index.html            # Browser dashboard
└── README.md                 # This file
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

### Dashboard (HTML/JS)

1. Polls the Python bridge every second for current status
2. Displays distance with color coding (green = pet detected, red = far)
3. Shows real-time distance chart
4. Manual feed button for testing

## Customization

Edit the top of `firmware/pet_feeder/pet_feeder.ino`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DETECT_DISTANCE_CM` | 20.0 | How close the pet must be (cm) |
| `COOLDOWN_MS` | 15000 | Minimum time between feeds (ms) |
| `SERVO_OPEN_ANGLE` | 90 | How far the gate opens (degrees) |
| `HOLD_TIME_MS` | 3000 | How long the gate stays open (ms) |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot open COM4" | Close Arduino Serial Monitor or any other serial program |
| No distance readings | Check TRIG/D9 and ECHO/D10 wiring |
| Servo doesn't move | Check servo power (5V) and signal wire (D6) |
| Dashboard shows "Disconnected" | Make sure `python server.py` is running |
| CH340 not recognized | Install CH340 driver from https://www.wch-ic.com/downloads/CH341SER_EXE.html |
