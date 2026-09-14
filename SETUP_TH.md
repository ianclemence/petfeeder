# คู่มือการติดตั้งระบบให้อาหารสัตว์อัตโนมัติ — สำหรับนักศึกษา

## ความต้องการเบื้องต้น

### อุปกรณ์ฮาร์ดแวร์
- Arduino UNO (CH340 clone)
- เซ็นเซอร์อัลตราโซนิก HC-SR04
- เซอร์โว SG90
- สาย jumper (ตัวผู้-ตัวผู้)
- สาย USB Type-B

### ซอฟต์แวร์
- Python 3.8+ — https://python.org
- Arduino CLI — `winget install Arduino.CLI`
- Git — https://git-scm.com
- ไดร์เวอร์ CH340 (ถ้า Arduino ไม่ถูกตรวจจับ) — https://www.wch-ic.com/downloads/CH341SER_EXE.html

---

## แผนผังการเดินสาย

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

| Arduino | อุปกรณ์ | หน้าที่ |
|---------|---------|--------|
| 5V | HC-SR04 VCC | จ่ายไฟให้เซ็นเซอร์ |
| GND | HC-SR04 GND | ต่อสายดินเซ็นเซอร์ |
| D9 | HC-SR04 TRIG | ส่งสัญญาณอัลตราโซนิก |
| D10 | HC-SR04 ECHO | อ่านสัญญาณสะท้อน |
| 5V | เซอร์โว RED (+) | จ่ายไฟเซอร์โว |
| GND | เซอร์โว BROWN (-) | ต่อสายดินเซอร์โว |
| D6 | เซอร์โว ORANGE | ควบคุมมุมเซอร์โว |

---

## ขั้นตอนการติดตั้ง

### ขั้นตอนที่ 1 — คัดลอกคลังเก็บ (Clone Repository)

```bash
git clone https://github.com/ianclemence/petfeeding-detector.git
cd petfeeding-detector
```

### ขั้นตอนที่ 2 — ติดตั้ง dependencies ของ Python

```bash
cd bridge
pip install -r requirements.txt
cd ..
```

### ขั้นตอนที่ 3 — ค้นหาพอร์ต COM ของคุณ

**Windows:**
1. เปิด Device Manager
2. ขยาย "Ports (COM & LPT)"
3. ค้นหา "USB-SERIAL CH340 (COMx)" — จดหมายเลขพอร์ตไว้

**Mac/Linux:**
```bash
ls /dev/tty.*
# หรือ
ls /dev/ttyUSB*
```

### ขั้นตอนที่ 4 — อัปเดตพอร์ต COM ใน server.py

เปิดไฟล์ `bridge/server.py` และเปลี่ยนบรรทัดที่ 29 ให้ตรงกับพอร์ตของคุณ:

```python
SERIAL_PORT = "COM5"  # เปลี่ยนเป็นพอร์ตของคุณ เช่น "COM3", "COM7"
```

### ขั้นตอนที่ 5 — อัปโหลดเฟิร์มแวร์ไปยัง Arduino

```bash
arduino-cli compile --fqbn arduino:avr:uno firmware/pet_feeder/pet_feeder.ino
arduino-cli upload --fqbn arduino:avr:uno --port COMx firmware/pet_feeder/pet_feeder.ino
```

เปลี่ยน `COMx` เป็นหมายเลขพอร์ตจริงของคุณ

> **หมายเหตุ:** ปิด Arduino Serial Monitor ก่อนทำการอัปโหลด

### ขั้นตอนที่ 6 — เริ่มต้น Bridge Server

```bash
cd bridge
python server.py
```

คุณควรเห็นผลลัพธ์ดังนี้:
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

### ขั้นตอนที่ 7 — เปิดหน้า Dashboard

เปิดเบราว์เซอร์และไปที่: **http://localhost:8080**

### ขั้นตอนที่ 8 — ทดสอบระบบ

1. **ค่าระยะทาง** — วางมือใกล้เซ็นเซอร์ (<20 ซม.) แล้วดูค่าระยะทางอัปเดต
2. **ให้อาหารอัตโนมัติ** — อยู่ใกล้เซ็นเซอร์ไม่เกิน 20 ซม. เป็นเวลา 3 วินาทีขึ้นไป เซอร์โวจะเปิด
3. **ให้อา蜢ด้วยตนเอง** — คลิกปุ่ม "Manual Feed"
4. **ตั้งค่า** — ปรับเลื่อนค่า threshold และ cooldown
5. **กราฟ** — ดูกราฟประวัติระยะทางแบบเรียลไทม์
6. **บันทึก CSV** — คลิก "Download CSV Log" เพื่อส่งออกข้อมูล

---

## การปรับแต่ง

แก้ไขส่วนบนของไฟล์ `firmware/pet_feeder/pet_feeder.ino`:

| พารามิเตอร์ | ค่าเริ่มต้น | คำอธิบาย |
|-------------|-----------| สัตว์ต้องอยู่ใกล้แค่ไหน (ซม.) |
| `DETECT_DISTANCE_CM` | 20.0 | ระยะทางตรวจจับ (ซม.) |
| `COOLDOWN_MS` | 15000 | เวลาขั้นต่ำระหว่างการให้อาหาร (มิลลิวินาที) |
| `SERVO_OPEN_ANGLE` | 90 | /Gate เปิดกว้างแค่ไหน (องศา) |
| `HOLD_TIME_MS` | 3000 |  Gate เปิดค้างไว้นานแค่ไหน (มิลลิวินาที) |

---

## การแก้ไขปัญหา

| ปัญหา | วิธีแก้ |
|-------|--------|
| "Cannot open COMx" | ปิด Arduino Serial Monitor และอัปเดตพอร์ต COM ใน `server.py` |
| ไม่มีค่าระยะทาง | ตรวจสอบการเดินสาย TRIG/D9 และ ECHO/D10 |
| เซอร์โวไม่ขยับ | ตรวจสอบไฟเลี้ยงเซอร์โว (5V) และสายสัญญาณ (D6) |
| Dashboard แสดง "Disconnected" | ตรวจสอบว่า `python server.py` กำลังทำงานอยู่ |
| ไม่พบ CH340 | ติดตั้งไดร์เวอร์ CH340 จากลิงก์ด้านบน |
| ไม่พบ Python | เพิ่ม Python ลงใน PATH ระหว่างติดตั้ง หรือใช้ `py` แทน `python` |
| ไม่พบ `pip` | ใช้ `python -m pip install -r requirements.txt` |

---

## โครงสร้างโปรเจกต์

```
petfeeding-detector/
├── firmware/
│   └── pet_feeder/
│       └── pet_feeder.ino    # โค้ด Arduino (C++)
├── bridge/
│   ├── server.py             # Python bridge สำหรับแปลง Serial เป็น Web
│   └── requirements.txt      # dependencies ของ Python
├── web/
│   └── index.html            # หน้า Dashboard บนเบราว์เซอร์
├── logs/                     # บันทึกข้อมูล CSV (ไม่ commit)
├── README.md                 # บทนำโครงการ (อังกฤษ)
├── README_TH.md              # บทนำโครงการ (ไทย)
├── SETUP.md                  # คู่มือติดตั้ง (อังกฤษ)
├── SETUP_TH.md              # ไฟล์นี้ (ไทย)
└── .gitignore
```
