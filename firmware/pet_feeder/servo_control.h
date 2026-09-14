/*
 * servo_control.h — Servo Motor Control
 * ======================================
 * This file controls the servo motor that opens/closes the food gate.
 *
 * HOW IT WORKS (for students):
 *   - A servo motor can be set to any angle from 0 to 180 degrees
 *   - We use it to open a "gate" that lets food fall through
 *   - 0 degrees = gate closed (no food)
 *   - 90 degrees = gate fully open (full portion)
 *   - 45 degrees = gate halfway open (half portion)
 *
 * THE SERVO LIBRARY:
 *   - #include <Servo.h> gives us the Servo class
 *   - .attach(pin) tells Arduino which pin the servo is on
 *   - .write(angle) moves the servo to that angle
 */

#ifndef SERVO_CONTROL_H
#define SERVO_CONTROL_H

#include <Arduino.h>
#include <Servo.h>
#include "config.h"

// Create a Servo object to control our food gate
Servo feeder_servo;

// Initialize the servo (call this in setup())
void servo_setup() {
  feeder_servo.attach(SERVO_PIN);
  feeder_servo.write(CLOSE_ANGLE);  // Start with gate closed
}

// Open the food gate to the specified angle
void open_gate(int angle) {
  feeder_servo.write(angle);
}

// Close the food gate completely
void close_gate() {
  feeder_servo.write(CLOSE_ANGLE);
}

#endif
