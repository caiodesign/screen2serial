# Arduino Setup

This guide explains how to set up the Arduino for hardware-level mouse/keyboard control.

## Why Arduino?

Software-based input (pyautogui, pynput) can be detected by anti-cheat systems. Arduino acts as a USB HID device, making inputs indistinguishable from real hardware.

## Requirements

### Hardware

- Arduino with native USB HID support:
  - **Arduino Leonardo** (recommended)
  - **Arduino Pro Micro** (compact)
  - **Arduino Due**
  - **Teensy** boards
- USB cable

> **Note**: Arduino Uno and Mega do NOT support native USB HID. They use a separate chip for USB communication.

### Software

- Arduino IDE
- Mouse library (built-in)
- Keyboard library (built-in)

## Arduino Code

Upload this sketch to your Arduino:

```cpp
#include <Mouse.h>
#include <Keyboard.h>

String inputString = "";
bool stringComplete = false;

// Random delay helper
int randRange(int minVal, int maxVal) {
    return random(minVal, maxVal + 1);
}

void setup() {
    Serial.begin(9600);
    inputString.reserve(200);
    Mouse.begin();
    Keyboard.begin();
    randomSeed(analogRead(0));
}

void loop() {
    if (stringComplete) {
        processCommand(inputString);
        inputString = "";
        stringComplete = false;
    }
}

void serialEvent() {
    while (Serial.available()) {
        char inChar = (char)Serial.read();
        if (inChar == '\n') {
            stringComplete = true;
        } else {
            inputString += inChar;
        }
    }
}

void processCommand(String cmd) {
    cmd.trim();

    if (cmd.length() == 0) return;

    char cmdType = cmd.charAt(0);

    switch (cmdType) {
        case 'M': // Move: M{dx},{dy}
            handleMove(cmd.substring(1));
            break;

        case 'L': // Left click
            handleLeftClick();
            break;

        case 'R': // Right click
            handleRightClick();
            break;

        case 'S': // Shift commands
            handleShiftCommand(cmd.substring(1));
            break;

        case 'K': // Key press: K{key}
            handleKeyPress(cmd.substring(1));
            break;
    }
}

void handleMove(String params) {
    int commaIndex = params.indexOf(',');
    if (commaIndex == -1) return;

    int dx = params.substring(0, commaIndex).toInt();
    int dy = params.substring(commaIndex + 1).toInt();

    // Move in small steps for smoother motion
    int steps = max(abs(dx), abs(dy)) / 10;
    steps = max(steps, 1);

    float stepX = (float)dx / steps;
    float stepY = (float)dy / steps;

    for (int i = 0; i < steps; i++) {
        Mouse.move((int)stepX, (int)stepY, 0);
        delay(randRange(1, 3));
    }

    // Move any remainder
    int movedX = (int)(stepX * steps);
    int movedY = (int)(stepY * steps);
    Mouse.move(dx - movedX, dy - movedY, 0);
}

void handleLeftClick() {
    delay(randRange(5, 15));
    Mouse.press(MOUSE_LEFT);
    delay(randRange(18, 40));
    Mouse.release(MOUSE_LEFT);
}

void handleRightClick() {
    delay(randRange(5, 15));
    Mouse.press(MOUSE_RIGHT);
    delay(randRange(18, 40));
    Mouse.release(MOUSE_RIGHT);
}

void handleShiftCommand(String subcmd) {
    if (subcmd == "H") {
        // Hold shift
        Keyboard.press(KEY_LEFT_SHIFT);
    } else if (subcmd == "R") {
        // Release shift
        Keyboard.release(KEY_LEFT_SHIFT);
    } else if (subcmd == "L") {
        // Shift + left click
        Keyboard.press(KEY_LEFT_SHIFT);
        delay(randRange(10, 20));
        handleLeftClick();
        delay(randRange(10, 20));
        Keyboard.release(KEY_LEFT_SHIFT);
    }
}

void handleKeyPress(String key) {
    key.toLowerCase();

    int keyCode = 0;

    if (key == "f1") keyCode = KEY_F1;
    else if (key == "f2") keyCode = KEY_F2;
    else if (key == "f3") keyCode = KEY_F3;
    else if (key == "f4") keyCode = KEY_F4;
    else if (key == "f5") keyCode = KEY_F5;
    else if (key == "f6") keyCode = KEY_F6;
    else if (key == "f7") keyCode = KEY_F7;
    else if (key == "f8") keyCode = KEY_F8;
    else if (key == "f9") keyCode = KEY_F9;
    else if (key == "f10") keyCode = KEY_F10;
    else if (key == "f11") keyCode = KEY_F11;
    else if (key == "f12") keyCode = KEY_F12;
    else if (key == "esc") keyCode = KEY_ESC;
    else if (key == "tab") keyCode = KEY_TAB;
    else if (key == "enter") keyCode = KEY_RETURN;
    else if (key == "space") keyCode = ' ';
    else if (key.length() == 1) keyCode = key.charAt(0);

    if (keyCode != 0) {
        delay(randRange(5, 15));
        Keyboard.press(keyCode);
        delay(randRange(18, 40));
        Keyboard.release(keyCode);
    }
}
```

## Serial Protocol

| Command       | Format         | Description                    |
| ------------- | -------------- | ------------------------------ |
| Move          | `M{dx},{dy}\n` | Relative mouse move            |
| Left Click    | `L\n`          | Press and release left button  |
| Right Click   | `R\n`          | Press and release right button |
| Shift Hold    | `SH\n`         | Hold shift key down            |
| Shift Release | `SR\n`         | Release shift key              |
| Shift Click   | `SL\n`         | Shift + left click             |
| Key Press     | `K{key}\n`     | Press a key (f1, esc, etc.)    |

### Examples

```
M100,50       # Move right 100px, down 50px
M-200,0       # Move left 200px
L             # Left click
R             # Right click
SH            # Hold shift
L             # Click while shift held
L             # Another click
SR            # Release shift
Kf1           # Press F1
Kesc          # Press Escape
```

## Configuration

### Finding the Serial Port

**Windows:**

1. Open Device Manager
2. Look under "Ports (COM & LPT)"
3. Find "Arduino Leonardo" or similar
4. Note the COM port (e.g., COM5)

**macOS:**

```bash
ls /dev/tty.*
# Look for /dev/tty.usbmodem* or /dev/tty.usbserial*
```

**Linux:**

```bash
ls /dev/ttyACM*
# Usually /dev/ttyACM0
```

### Setting in config.py

```python
# Windows
SERIAL_PORT = "COM5"

# macOS
SERIAL_PORT = "/dev/tty.usbmodem14101"

# Linux
SERIAL_PORT = "/dev/ttyACM0"

BAUD_RATE = 9600
```

## Troubleshooting

### "Failed to open serial port"

1. Check the port name is correct
2. Close Arduino IDE Serial Monitor (only one connection allowed)
3. Verify Arduino is connected and recognized by OS
4. Try unplugging and replugging

### Mouse moves erratically

1. Reduce move step size in Arduino code
2. Increase delays between moves
3. Check for loose USB connection

### Keys not working

1. Verify key names match Arduino code (lowercase)
2. Check Keyboard.begin() was called
3. Try with simple keys first (letters, F1-F12)

### Permissions (Linux)

Add user to dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

## Advanced: Human-like Motion

The Arduino code includes smoothing, but you can enhance it:

```cpp
// Bezier curve mouse movement
void humanMove(int targetX, int targetY) {
    int startX = 0, startY = 0;  // relative start

    // Control points for curve
    int cp1x = startX + random(-50, 50);
    int cp1y = startY + random(-50, 50);
    int cp2x = targetX + random(-50, 50);
    int cp2y = targetY + random(-50, 50);

    int steps = 20 + random(0, 10);
    int lastX = 0, lastY = 0;

    for (int i = 0; i <= steps; i++) {
        float t = (float)i / steps;
        float u = 1 - t;

        // Cubic bezier
        int x = u*u*u*startX + 3*u*u*t*cp1x + 3*u*t*t*cp2x + t*t*t*targetX;
        int y = u*u*u*startY + 3*u*u*t*cp1y + 3*u*t*t*cp2y + t*t*t*targetY;

        Mouse.move(x - lastX, y - lastY, 0);
        lastX = x;
        lastY = y;

        delay(random(5, 15));
    }
}
```

## Safety Notes

1. **Test carefully** - The Arduino has full control of your mouse/keyboard
2. **Have an emergency plan** - Know how to unplug quickly
3. **Use delays** - Never flood with commands
4. **Monitor behavior** - Watch for unexpected inputs
