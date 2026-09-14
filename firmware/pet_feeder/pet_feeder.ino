/*
 * Automatic Pet Feeder v2.0 - Arduino Firmware
 * ==============================================
 * Features:
 *   - Adjustable detection threshold (via serial command)
 *   - Adjustable cooldown between feeds (via serial command)
 *   - LED feedback on D13 (built-in LED)
 *   - Multi-zone: 3 distance zones = different servo angles
 *   - All settings configurable from web dashboard
 *
 * Serial Commands:
 *   SET_THRESHOLD:xx   - Set detection distance in cm (default 20)
 *   SET_COOLDOWN:xx    - Set cooldown in seconds (default 15)
 *   SET_ZONE1:xx       - Set zone 1 distance (default 15cm -> 90°)
 *   SET_ZONE2:xx       - Set zone 2 distance (default 30cm -> 45°)
 *   OPEN / CLOSE       - Manual servo control
 *   STATUS             - Request current status
 *
 * Hardware:
 *   - Arduino UNO (CH340 clone)
 *   - HC-SR04 (Trig=D9, Echo=D10)
 *   - SG90 Servo (Signal=D6)
 *   - Built-in LED (D13)
 */

#include <Servo.h>

// ---- PIN DEFINITIONS ----
const int TRIG_PIN   = 9;
const int ECHO_PIN   = 10;
const int SERVO_PIN  = 6;
const int LED_PIN    = 13;  // Built-in LED

// ---- DEFAULT SETTINGS (overridable via serial) ----
float threshold_cm  = 20.0;   // Default detection range
unsigned long cooldown_ms = 15000; // Default 15 seconds

// Multi-zone distances (closer = more food)
float zone1_cm = 15.0;   // Very close -> 90° (full dispense)
float zone2_cm = 30.0;   // Medium close -> 45° (half dispense)

// Servo angles per zone
const int ZONE_FULL_ANGLE  = 90;   // Zone 1: full portion
const int ZONE_HALF_ANGLE  = 45;   // Zone 2: half portion
const int CLOSE_ANGLE      = 0;    // Closed

// Timing
const unsigned long HOLD_TIME_MS     = 3000;   // 3s dispense
const unsigned long DISTANCE_INTERVAL = 500;   // Send every 500ms
const unsigned long LED_BLINK_INTERVAL = 200;  // LED blink speed

// ---- STATE ----
Servo feederServo;
bool feeding = false;
unsigned long feedStartTime = 0;
unsigned long lastFeedTime  = 0;
unsigned long lastDistanceTime = 0;
unsigned long lastLedBlink = 0;
bool ledState = false;
int currentZone = 0;  // 0=none, 1=full, 2=half

// ---- READ DISTANCE ----
float readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return 999.0;
  return (duration * 0.034) / 2.0;
}

// ---- DETERMINE ZONE ----
// Returns: 0=no pet, 1=very close (full), 2=medium (half)
int getZone(float dist) {
  if (dist <= 0 || dist >= 999) return 0;
  if (dist < zone1_cm) return 1;       // Very close -> full portion
  if (dist < zone2_cm) return 2;       // Medium -> half portion
  return 0;                             // Too far
}

// ---- READ SERIAL COMMAND ----
String readCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  return cmd;
}

// ---- SEND STATUS ----
void sendStatus() {
  float dist = readDistanceCM();
  int zone = getZone(dist);
  Serial.print("STATUS:");
  Serial.print(feeding ? "FEEDING" : "IDLE");
  Serial.print(":");
  Serial.print(dist, 1);
  Serial.print(":");
  Serial.print(zone);
  Serial.print(":");
  Serial.print(threshold_cm, 1);
  Serial.print(":");
  Serial.println(cooldown_ms / 1000);
}

// ---- SETUP ----
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  feederServo.attach(SERVO_PIN);
  feederServo.write(CLOSE_ANGLE);

  Serial.println("BOOT:PetFeeder v2.0");
  Serial.println("ACK:READY");
}

// ---- MAIN LOOP ----
void loop() {
  unsigned long now = millis();

  // ---- SERIAL COMMAND HANDLING ----
  if (Serial.available() > 0) {
    String cmd = readCommand();

    if (cmd.startsWith("SET_THRESHOLD:")) {
      float val = cmd.substring(14).toFloat();
      if (val > 0 && val <= 200) {
        threshold_cm = val;
        Serial.print("ACK:THRESHOLD:");
        Serial.println(threshold_cm, 1);
      } else {
        Serial.println("ERR:INVALID_THRESHOLD");
      }

    } else if (cmd.startsWith("SET_COOLDOWN:")) {
      float val = cmd.substring(13).toFloat();
      if (val >= 0 && val <= 300) {
        cooldown_ms = (unsigned long)(val * 1000);
        Serial.print("ACK:COOLDOWN:");
        Serial.println(cooldown_ms / 1000);
      } else {
        Serial.println("ERR:INVALID_COOLDOWN");
      }

    } else if (cmd.startsWith("SET_ZONE1:")) {
      float val = cmd.substring(10).toFloat();
      if (val > 0 && val <= 200) {
        zone1_cm = val;
        Serial.print("ACK:ZONE1:");
        Serial.println(zone1_cm, 1);
      }

    } else if (cmd.startsWith("SET_ZONE2:")) {
      float val = cmd.substring(10).toFloat();
      if (val > 0 && val <= 200) {
        zone2_cm = val;
        Serial.print("ACK:ZONE2:");
        Serial.println(zone2_cm, 1);
      }

    } else if (cmd == "OPEN") {
      feeding = true;
      feedStartTime = now;
      currentZone = 1;
      feederServo.write(ZONE_FULL_ANGLE);
      digitalWrite(LED_PIN, HIGH);
      Serial.println("OPENED");

    } else if (cmd == "CLOSE") {
      feeding = false;
      currentZone = 0;
      feederServo.write(CLOSE_ANGLE);
      digitalWrite(LED_PIN, LOW);
      Serial.println("CLOSED");

    } else if (cmd == "STATUS") {
      sendStatus();

    } else {
      Serial.println("ERR:UNKNOWN_CMD");
    }
  }

  // ---- AUTO SEND DISTANCE (heartbeat) ----
  if (now - lastDistanceTime >= DISTANCE_INTERVAL) {
    lastDistanceTime = now;
    float dist = readDistanceCM();
    int zone = getZone(dist);
    Serial.print("DIST:");
    Serial.print(dist, 1);
    Serial.print(":");
    Serial.println(zone);
  }

  // ---- LED BLINKING during feeding ----
  if (feeding) {
    if (now - lastLedBlink >= LED_BLINK_INTERVAL) {
      lastLedBlink = now;
      ledState = !ledState;
      digitalWrite(LED_PIN, ledState ? HIGH : LOW);
    }
  }

  // ---- AUTOMATIC FEEDING LOGIC ----
  if (!feeding) {
    float dist = readDistanceCM();
    int zone = getZone(dist);
    bool cooldownExpired = (now - lastFeedTime >= cooldown_ms);

    if (zone > 0 && cooldownExpired) {
      feeding = true;
      feedStartTime = now;
      currentZone = zone;

      // Different angle per zone
      int angle = (zone == 1) ? ZONE_FULL_ANGLE : ZONE_HALF_ANGLE;
      feederServo.write(angle);

      Serial.print("EVENT:ZONE");
      Serial.print(zone);
      Serial.println("_DETECTED");
      Serial.println("OPENED");
    }
  }

  // ---- AUTO CLOSE AFTER HOLD TIME ----
  if (feeding && (now - feedStartTime >= HOLD_TIME_MS)) {
    feeding = false;
    currentZone = 0;
    feederServo.write(CLOSE_ANGLE);
    lastFeedTime = now;
    digitalWrite(LED_PIN, LOW);
    Serial.println("CLOSED");
    Serial.println("EVENT:FEED_COMPLETE");
  }
}
