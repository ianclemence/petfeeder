/*
 * config.h — Pet Feeder Settings
 * ==============================
 * All the values you can change are in this file.
 * This makes it easy to customize without hunting through the main code.
 *
 * HOW IT WORKS:
 *   - "threshold" = how close the pet must be to trigger feeding
 *   - "cooldown"  = minimum seconds between automatic feeds
 *   - "zones"     = different distances = different food portions
 *   - The pet being closer = more food dispensed
 */

#ifndef CONFIG_H
#define CONFIG_H

// ---- PIN NUMBERS ----
// These are the Arduino pins where each component is connected.
// If you wire things differently, change these numbers.
const int TRIG_PIN = 9;   // Ultrasonic sensor trigger pin
const int ECHO_PIN = 10;  // Ultrasonic sensor echo pin
const int SERVO_PIN = 6;  // Servo motor signal pin
const int LED_PIN = 13;   // Built-in LED (on the Arduino board itself)

// ---- DETECTION SETTINGS ----
// How close does the pet need to be before we dispense food?
float detection_range_cm = 20.0;

// How many seconds must pass between automatic feeds?
// This prevents the feeder from dumping all the food at once.
unsigned long cooldown_seconds = 15;

// ---- ZONE DISTANCES (closer = more food) ----
// Zone 1: Very close to sensor -> full portion (larger servo angle)
// Zone 2: Medium distance     -> half portion (smaller servo angle)
// Beyond these distances      -> no food
float zone1_close_cm = 15.0;    // Within this = full portion
float zone2_medium_cm = 30.0;   // Within this = half portion

// ---- SERVO ANGLES ----
// How far does the food gate open for each zone?
const int ZONE_FULL_ANGLE = 90;  // Full portion: gate opens wide
const int ZONE_HALF_ANGLE = 45;  // Half portion: gate opens halfway
const int CLOSE_ANGLE = 0;       // Gate fully closed

// ---- TIMING ----
const unsigned long HOLD_TIME_MS = 3000;       // How long gate stays open (3 seconds)
const unsigned long DISTANCE_INTERVAL = 500;   // Send distance every 500ms
const unsigned long LED_BLINK_INTERVAL = 200;  // LED blink speed during feeding

#endif
