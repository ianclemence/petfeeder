/*
 * Automatic Pet Feeder v2.0 — Main Program
 * ==========================================
 * This is the main file that ties everything together.
 * The actual logic is split into separate files for clarity:
 *   - config.h       : All settings (distances, angles, timing)
 *   - sensor.h       : Reading distance from the ultrasonic sensor
 *   - servo_control.h: Opening and closing the food gate
 *   - commands.h     : Handling commands from the PC
 *
 * LEARNING GOAL: Students should understand how #include works.
 *   When you write #include "config.h", it's like pasting the
 *   contents of config.h right there. This lets us organize
 *   code into logical pieces instead of one giant file.
 */

#include "config.h"
#include "sensor.h"
#include "servo_control.h"
#include "commands.h"

// ---- STATE VARIABLES ----
// These track what the feeder is currently doing.
bool is_feeding = false;            // Is the gate open right now?
unsigned long feed_start_time = 0;  // When did the current feed start?
unsigned long last_feed_time = 0;   // When did the last feed end?
unsigned long last_distance_time = 0;  // Last time we sent distance
unsigned long last_led_blink = 0;   // Last time we toggled the LED
bool led_state = false;             // Is the LED on or off?
int current_zone = 0;               // Which zone triggered the feed (0=none, 1=full, 2=half)

// ---- HELPER: Send status to PC ----
void send_full_status() {
  float dist = read_distance_cm();
  int zone = get_zone(dist);
  Serial.print("STATUS:");
  Serial.print(is_feeding ? "FEEDING" : "IDLE");
  Serial.print(":");
  Serial.print(dist, 1);
  Serial.print(":");
  Serial.print(zone);
  Serial.print(":");
  Serial.print(detection_range_cm, 1);
  Serial.print(":");
  Serial.println(cooldown_seconds);
}

// ---- SETUP ----
// This runs once when the Arduino powers on or is reset.
void setup() {
  Serial.begin(115200);  // Start serial communication at 115200 bits per second

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  servo_setup();  // Initialize the servo (from servo_control.h)

  Serial.println("BOOT:PetFeeder v2.0");
  Serial.println("ACK:READY");
}

// ---- MAIN LOOP ----
// This runs over and over, as fast as the Arduino can go.
// We use timing checks (millis()) instead of delay() so the
// Arduino can do multiple things at once (like read serial
// AND measure distance AND blink the LED).
void loop() {
  unsigned long now = millis();

  // ---- HANDLE SERIAL COMMANDS ----
  if (Serial.available() > 0) {
    String cmd = read_command();
    String action = process_command(cmd);

    if (action == "OPEN") {
      is_feeding = true;
      feed_start_time = now;
      current_zone = 1;
      open_gate(ZONE_FULL_ANGLE);
      digitalWrite(LED_PIN, HIGH);
      Serial.println("OPENED");

    } else if (action == "CLOSE") {
      is_feeding = false;
      current_zone = 0;
      close_gate();
      digitalWrite(LED_PIN, LOW);
      Serial.println("CLOSED");

    } else if (action == "STATUS") {
      send_full_status();
    }
  }

  // ---- SEND DISTANCE HEARTBEAT ----
  // Every 500ms, send the current distance to the PC
  // so the dashboard can show a live graph.
  if (now - last_distance_time >= DISTANCE_INTERVAL) {
    last_distance_time = now;
    float dist = read_distance_cm();
    int zone = get_zone(dist);
    Serial.print("DIST:");
    Serial.print(dist, 1);
    Serial.print(":");
    Serial.println(zone);
  }

  // ---- BLINK LED DURING FEEDING ----
  // This gives a visual indicator that food is being dispensed.
  if (is_feeding) {
    if (now - last_led_blink >= LED_BLINK_INTERVAL) {
      last_led_blink = now;
      led_state = !led_state;
      digitalWrite(LED_PIN, led_state ? HIGH : LOW);
    }
  }

  // ---- AUTOMATIC FEEDING ----
  // If we're not already feeding, check if a pet is nearby.
  if (!is_feeding) {
    float dist = read_distance_cm();
    int zone = get_zone(dist);
    bool cooldown_expired = (now - last_feed_time >= cooldown_seconds * 1000);

    if (zone > 0 && cooldown_expired) {
      is_feeding = true;
      feed_start_time = now;
      current_zone = zone;

      // Choose servo angle based on zone
      int angle = (zone == 1) ? ZONE_FULL_ANGLE : ZONE_HALF_ANGLE;
      open_gate(angle);

      Serial.print("EVENT:ZONE");
      Serial.print(zone);
      Serial.println("_DETECTED");
      Serial.println("OPENED");
    }
  }

  // ---- AUTO-CLOSE AFTER HOLD TIME ----
  // After the gate has been open long enough, close it.
  if (is_feeding && (now - feed_start_time >= HOLD_TIME_MS)) {
    is_feeding = false;
    current_zone = 0;
    close_gate();
    last_feed_time = now;
    digitalWrite(LED_PIN, LOW);
    Serial.println("CLOSED");
    Serial.println("EVENT:FEED_COMPLETE");
  }
}
