/*
 * Automatic Pet Feeder - Arduino Firmware
 * ========================================
 * Uses HC-SR04 ultrasonic sensor to detect pet proximity.
 * When pet is detected close enough, a servo opens to dispense food.
 * 
 * No timer - purely distance-triggered with cooldown to prevent overfeeding.
 * 
 * Serial Protocol (115200 baud):
 *   PC -> Arduino: "OPEN" / "CLOSE" / "DISTANCE"
 *   Arduino -> PC: "DIST:xx.x" / "OPENED" / "CLOSED" / "ACK"
 * 
 * Hardware:
 *   - Arduino UNO (clone with CH340)
 *   - HC-SR04 Ultrasonic Sensor (Trig=D9, Echo=D10)
 *   - SG90 Micro Servo (Signal=D6)
 */

#include <Servo.h>

// ---- PIN DEFINITIONS ----
const int TRIG_PIN   = 9;   // HC-SR04 Trigger
const int ECHO_PIN   = 10;  // HC-SR04 Echo
const int SERVO_PIN  = 6;   // SG90 Servo signal

// ---- FEEDING PARAMETERS ----
const float DETECT_DISTANCE_CM = 20.0;  // Pet must be within 20cm
const unsigned long COOLDOWN_MS = 15000; // 15s between feeds
const int SERVO_OPEN_ANGLE  = 90;       // Gate open position
const int SERVO_CLOSE_ANGLE = 0;        // Gate closed position
const unsigned long HOLD_TIME_MS = 3000; // Food dispense duration

// ---- STATE VARIABLES ----
Servo feederServo;
bool feeding = false;
unsigned long feedStartTime = 0;
unsigned long lastFeedTime  = 0;
unsigned long lastDistanceTime = 0;
const unsigned long DISTANCE_INTERVAL = 500; // Send distance every 500ms

/*
 * Read distance from HC-SR04 sensor.
 * Sends a 10µs pulse on TRIG, measures echo duration.
 * Returns distance in centimeters (0 = no echo / out of range).
 */
float readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  if (duration == 0) return 999.0; // No echo = far away
  return (duration * 0.034) / 2.0; // Speed of sound formula
}

/*
 * Parse a command string from Serial (e.g. "OPEN\n").
 * Returns the command without newline characters.
 */
String readCommand() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();
  return cmd;
}

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  feederServo.attach(SERVO_PIN);
  feederServo.write(SERVO_CLOSE_ANGLE); // Start closed

  Serial.println("BOOT:PetFeeder v1.0");
  Serial.println("ACK:READY");
}

void loop() {
  unsigned long now = millis();

  // ---- SERIAL COMMAND HANDLING ----
  if (Serial.available() > 0) {
    String cmd = readCommand();

    if (cmd == "OPEN") {
      feeding = true;
      feedStartTime = now;
      feederServo.write(SERVO_OPEN_ANGLE);
      Serial.println("OPENED");

    } else if (cmd == "CLOSE") {
      feeding = false;
      feederServo.write(SERVO_CLOSE_ANGLE);
      Serial.println("CLOSED");

    } else if (cmd == "DISTANCE") {
      float dist = readDistanceCM();
      Serial.print("DIST:");
      Serial.println(dist, 1);

    } else if (cmd == "STATUS") {
      float dist = readDistanceCM();
      Serial.print("STATUS:");
      Serial.print(feeding ? "FEEDING" : "IDLE");
      Serial.print(":");
      Serial.println(dist, 1);

    } else {
      Serial.println("ERR:UNKNOWN_CMD");
    }
  }

  // ---- AUTO SEND DISTANCE (heartbeat) ----
  if (now - lastDistanceTime >= DISTANCE_INTERVAL) {
    lastDistanceTime = now;
    float dist = readDistanceCM();
    Serial.print("DIST:");
    Serial.println(dist, 1);
  }

  // ---- AUTOMATIC FEEDING LOGIC ----
  if (!feeding) {
    float dist = readDistanceCM();
    bool petDetected = (dist > 0 && dist < DETECT_DISTANCE_CM);
    bool cooldownExpired = (now - lastFeedTime >= COOLDOWN_MS);

    if (petDetected && cooldownExpired) {
      // Pet detected within range AND cooldown has passed -> dispense food
      feeding = true;
      feedStartTime = now;
      feederServo.write(SERVO_OPEN_ANGLE);
      Serial.println("EVENT:PET_DETECTED");
      Serial.println("OPENED");
    }
  }

  // ---- AUTO CLOSE AFTER HOLD TIME ----
  if (feeding && (now - feedStartTime >= HOLD_TIME_MS)) {
    feeding = false;
    feederServo.write(SERVO_CLOSE_ANGLE);
    lastFeedTime = now;
    Serial.println("CLOSED");
    Serial.println("EVENT:FEED_COMPLETE");
  }
}
