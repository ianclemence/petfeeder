/*
 * sensor.h — Ultrasonic Distance Sensor
 * ======================================
 * This file handles reading distance from the HC-SR04 sensor.
 *
 * HOW IT WORKS (for students):
 *   1. We send a short "pulse" (10 microseconds) on the TRIG pin
 *   2. The sensor sends out an ultrasonic sound wave
 *   3. The sound bounces off objects and comes back
 *   4. We measure how long the echo took (in microseconds)
 *   5. Distance = (time * speed of sound) / 2
 *      - Divide by 2 because the sound went there AND back
 *      - Speed of sound = 0.034 cm/microsecond
 */

#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>
#include "config.h"

// Read the distance from the ultrasonic sensor.
// Returns the distance in centimeters.
// Returns 999.0 if nothing is detected (timeout).
float read_distance_cm() {
  // Step 1: Make sure the trigger pin is LOW
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // Step 2: Send the trigger pulse (10 microseconds HIGH)
  // This tells the sensor "start measuring!"
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Step 3: Measure how long the echo pin stays HIGH
  // pulseIn() waits for the pin to go HIGH, then times how long it stays HIGH
  // The 30000 microsecond timeout prevents hanging if nothing is detected
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);

  // Step 4: No echo received = nothing in range
  if (duration == 0) return 999.0;

  // Step 5: Convert time to distance
  // duration * 0.034 gives total round-trip distance in cm
  // Divide by 2 because sound traveled to the object AND back
  return (duration * 0.034) / 2.0;
}

// Determine which "zone" the pet is in based on distance.
// Returns:
//   0 = no pet detected (too far away)
//   1 = very close (full portion)
//   2 = medium distance (half portion)
int get_zone(float distance) {
  if (distance <= 0 || distance >= 999) return 0;  // Invalid reading
  if (distance < zone1_close_cm) return 1;          // Very close -> full portion
  if (distance < zone2_medium_cm) return 2;         // Medium -> half portion
  return 0;                                          // Too far -> no food
}

#endif
