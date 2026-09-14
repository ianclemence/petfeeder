/*
 * commands.h — Serial Command Handler
 * ====================================
 * This file handles commands sent from the PC (via Python bridge).
 *
 * HOW IT WORKS (for students):
 *   - The Arduino can receive text commands through the USB cable
 *   - The Python bridge sends commands like "SET_THRESHOLD:25\n"
 *   - We read the command, parse it, and update settings
 *
 * AVAILABLE COMMANDS:
 *   SET_THRESHOLD:xx  - Change detection distance (cm)
 *   SET_COOLDOWN:xx   - Change cooldown time (seconds)
 *   SET_ZONE1:xx      - Change Zone 1 distance (cm)
 *   SET_ZONE2:xx      - Change Zone 2 distance (cm)
 *   OPEN              - Manually open the food gate
 *   CLOSE             - Manually close the food gate
 *   STATUS            - Request current sensor status
 */

#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>
#include "config.h"

// Read a command from serial (one line ending with \n)
String read_command() {
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();  // Remove whitespace and \r
  return cmd;
}

// Send current status back to the PC
// Format: STATUS:state:distance:zone:threshold:cooldown
void send_status() {
  Serial.print("STATUS:");
  // We'll pass feeding state from the main file
  Serial.print("IDLE:");  // Placeholder, will be overridden
  Serial.print(read_distance_cm(), 1);
  Serial.print(":0:");
  Serial.print(detection_range_cm, 1);
  Serial.print(":");
  Serial.println(cooldown_seconds);
}

// Process a command from the serial port.
// Returns a command string that the main loop should act on,
// or empty string if no action needed.
String process_command(String cmd) {
  if (cmd.startsWith("SET_THRESHOLD:")) {
    float val = cmd.substring(14).toFloat();
    if (val > 0 && val <= 200) {
      detection_range_cm = val;
      Serial.print("ACK:THRESHOLD:");
      Serial.println(detection_range_cm, 1);
    } else {
      Serial.println("ERR:INVALID_THRESHOLD");
    }

  } else if (cmd.startsWith("SET_COOLDOWN:")) {
    float val = cmd.substring(13).toFloat();
    if (val >= 0 && val <= 300) {
      cooldown_seconds = (unsigned long)val;
      Serial.print("ACK:COOLDOWN:");
      Serial.println(cooldown_seconds);
    } else {
      Serial.println("ERR:INVALID_COOLDOWN");
    }

  } else if (cmd.startsWith("SET_ZONE1:")) {
    float val = cmd.substring(10).toFloat();
    if (val > 0 && val <= 200) {
      zone1_close_cm = val;
      Serial.print("ACK:ZONE1:");
      Serial.println(zone1_close_cm, 1);
    }

  } else if (cmd.startsWith("SET_ZONE2:")) {
    float val = cmd.substring(10).toFloat();
    if (val > 0 && val <= 200) {
      zone2_medium_cm = val;
      Serial.print("ACK:ZONE2:");
      Serial.println(zone2_medium_cm, 1);
    }

  } else if (cmd == "OPEN") {
    return "OPEN";  // Tell main loop to open gate

  } else if (cmd == "CLOSE") {
    return "CLOSE";  // Tell main loop to close gate

  } else if (cmd == "STATUS") {
    // Status is handled specially in main loop
    return "STATUS";

  } else if (cmd.length() > 0) {
    Serial.println("ERR:UNKNOWN_CMD");
  }

  return "";  // No action needed
}

#endif
