```
#include <Mouse.h>
#include <Keyboard.h>

const unsigned long CLICK_COOLDOWN_MS = 300;
unsigned long lastClickTime = 0;

// -------------------------
// Utility: random range
// -------------------------
int randRange(int minVal, int maxVal) {
  return random(minVal, maxVal + 1);
}

// -------------------------
// Smooth mouse movement
// -------------------------
void smoothMove(int dx, int dy) {
  int dist = max(abs(dx), abs(dy));

  // Distance-based step calculation:
  // - Short moves (< 50px): More steps for precision
  // - Medium moves (50-200px): Balanced
  // - Long moves (> 200px): Fewer steps for speed
  int steps;
  if (dist < 50) {
    steps = constrain(dist, 5, 25);      // Short: detailed movement
  } else if (dist < 200) {
    steps = constrain(dist / 5, 12, 30); // Medium: balanced
  } else {
    steps = constrain(dist / 12, 20, 40); // Long: faster movement
  }

  float stepX = dx / (float)steps;
  float stepY = dy / (float)steps;

  float currentX = 0;
  float currentY = 0;

  for (int i = 0; i < steps; i++) {
    currentX += stepX;
    currentY += stepY;

    int moveX = round(currentX);
    int moveY = round(currentY);

    // subtract what we've already applied
    currentX -= moveX;
    currentY -= moveY;

    // micro jitter (reduced for less randomness on fast moves)
    if (dist < 100) {
      moveX += randRange(-1, 1);
      moveY += randRange(-1, 1);
    }

    Mouse.move(moveX, moveY, 0);
    delay(randRange(3, 8));  // Faster: was 5-15ms, now 3-8ms
  }
}

// -------------------------
// Randomized left click
// -------------------------
void randomizedLeftClick(bool shiftHeld) {
  unsigned long now = millis();
  if (now - lastClickTime < CLICK_COOLDOWN_MS) return;

  if (shiftHeld) {
    Keyboard.press(KEY_LEFT_SHIFT);
    delay(randRange(10, 25));
  }

  Mouse.press(MOUSE_LEFT);
  delay(randRange(18, 40));     // variable press duration
  Mouse.release(MOUSE_LEFT);

  if (shiftHeld) {
    delay(randRange(10, 25));
    Keyboard.release(KEY_LEFT_SHIFT);
  }

  lastClickTime = now;
}

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    delay(10);
  }

  randomSeed(analogRead(A0));  // seed randomness

  Mouse.begin();
  Keyboard.begin();
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // -------------------------
    // Smooth move: Mdx,dy
    // -------------------------
    if (cmd.startsWith("M")) {
      int commaIndex = cmd.indexOf(',');
      if (commaIndex > 1) {
        int dx = cmd.substring(1, commaIndex).toInt();
        int dy = cmd.substring(commaIndex + 1).toInt();
        smoothMove(dx, dy);
      }
      return;
    }

    // -------------------------
    // Shift Hold
    // -------------------------
    if (cmd == "SH") {
      Keyboard.press(KEY_LEFT_SHIFT);
      return;
    }

    // -------------------------
    // Shift Release
    // -------------------------
    if (cmd == "SR") {
      Keyboard.release(KEY_LEFT_SHIFT);
      return;
    }

    // -------------------------
    // Shift + Left Click
    // -------------------------
    if (cmd == "SL") {
      randomizedLeftClick(true);
      return;
    }

    // -------------------------
    // Left Click
    // -------------------------
    if (cmd == "L") {
      randomizedLeftClick(false);
      return;
    }

    if (cmd.startsWith("K")) {
      String key = cmd.substring(1);

      if (key == "f1") Keyboard.press(KEY_F1);
      else if (key == "f2") Keyboard.press(KEY_F2);
      else if (key == "f3") Keyboard.press(KEY_F3);
      else if (key == "f4") Keyboard.press(KEY_F4);
      else if (key == "f5") Keyboard.press(KEY_F5);
      else if (key == "f6") Keyboard.press(KEY_F6);
      else if (key == "f10") Keyboard.press(KEY_F10);
      else if (key == "esc") Keyboard.press(KEY_ESC);
      else if (key == "space") Keyboard.press(' ');
      else if (key == "1") Keyboard.press('1');
      else if (key == "2") Keyboard.press('2');
      else if (key == "3") Keyboard.press('3');
      else if (key == "4") Keyboard.press('4');
      else if (key == "5") Keyboard.press('5');
      else if (key == "6") Keyboard.press('6');
      else if (key == "7") Keyboard.press('7');
      else if (key == "8") Keyboard.press('8');
      else if (key == "9") Keyboard.press('9');
      else if (key == "10") { Keyboard.press('1'); Keyboard.press('0'); }

      delay(randRange(30, 60));
      Keyboard.releaseAll();
      return;
    }

    // -------------------------
    // Legacy instant down move
    // -------------------------
    if (cmd.startsWith("D")) {
      int pixels = cmd.substring(1).toInt();
      Mouse.move(0, pixels, 0);
      return;
    }
  }
}
```
