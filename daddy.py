import cv2
import numpy as np
import time
import serial
import pyautogui
from mss import mss
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
TEMPLATE_PATH = "family.png"
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

CENTER_X = 364
CENTER_Y = 201
CROP_SIZE = 100
Y_MARGIN = 30

MATCH_THRESHOLD = 0.70
SCAN_INTERVAL = 2.0

# Verification
VERIFY_REQUIRED = 2          # consecutive matches

# Timeouts (seconds)
COLLECTING_TIMEOUT = 30
COOLDOWN_TIME = 5

# Click hesitation
HESITATION_MIN = 0.05
HESITATION_MAX = 0.25

# Debug
DEBUG = True
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"     # "fail" or "all"

# =========================
# STATES
# =========================
WAITING = "waiting"
VERIFY = "verify"
STARTING = "starting"
COLLECTING = "collecting"
COOLDOWN = "cooldown"

state = WAITING
state_since = time.time()

# =========================
# STATS
# =========================
stats = {
    "clicks": 0,
    "verify_fail": 0,
    "resets": 0,
    "state_time": {
        WAITING: 0,
        VERIFY: 0,
        STARTING: 0,
        COLLECTING: 0,
        COOLDOWN: 0,
    }
}

verify_count = 0
last_loop_time = time.time()

# =========================
# INIT SERIAL
# =========================
def open_serial(port, baud):
    for _ in range(5):
        try:
            ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)
            return ser
        except Exception:
            time.sleep(2)
    raise RuntimeError("Failed to open serial port")

ser = open_serial(SERIAL_PORT, BAUD_RATE)

# =========================
# LOAD TEMPLATE
# =========================
template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
if template is None:
    raise RuntimeError("family.png not found")
template = cv2.GaussianBlur(template, (5, 5), 0)

# =========================
# SCREEN CAPTURE
# =========================
sct = mss()
monitor = sct.monitors[1]

half = CROP_SIZE // 2
target_y = CENTER_Y + half + Y_MARGIN

# =========================
# DEBUG SETUP
# =========================
if DEBUG:
    os.makedirs(DEBUG_DIR, exist_ok=True)

print("Started detection loop")
print(f"Initial state: {state}")

# =========================
# MAIN LOOP
# =========================
while True:
    now = time.time()

    # Track state time
    stats["state_time"][state] += now - last_loop_time
    last_loop_time = now

    # Capture screen
    screenshot = np.array(sct.grab(monitor))
    frame = screenshot[:, :, :3]

    # Crop
    crop = frame[
        CENTER_Y - half : CENTER_Y + half,
        CENTER_X - half : CENTER_X + half
    ]

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Template match
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, _ = cv2.minMaxLoc(result)
    matched = confidence >= MATCH_THRESHOLD

    print(f"[{state}] confidence={confidence:.3f}")

    # =========================
    # DEBUG CAPTURE
    # =========================
    if DEBUG and (DEBUG_SAVE_MODE == "all" or not matched):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = f"{DEBUG_DIR}/{ts}_{state}_{confidence:.3f}"

        # Crop
        cv2.imwrite(f"{base}_crop.png", gray)

        # Template
        cv2.imwrite(f"{base}_template.png", template)

        # Heatmap
        heatmap = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = heatmap.astype(np.uint8)
        heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        cv2.imwrite(f"{base}_heatmap.png", heatmap)

        # Annotated crop
        annotated = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        cv2.putText(
            annotated,
            f"{state} conf={confidence:.3f}",
            (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0) if matched else (0, 0, 255),
            1,
            cv2.LINE_AA
        )
        cv2.imwrite(f"{base}_annotated.png", annotated)

    # =========================
    # STATE MACHINE
    # =========================
    if state == WAITING:
        if matched:
            verify_count = 1
            state = VERIFY
            state_since = now

    elif state == VERIFY:
        if matched:
            verify_count += 1
            if verify_count >= VERIFY_REQUIRED:
                state = STARTING
                state_since = now
        else:
            stats["verify_fail"] += 1
            state = WAITING
            state_since = now

    elif state == STARTING:
        mx, my = pyautogui.position()
        dx = CENTER_X - mx
        dy = target_y - my

        ser.write(f"M{dx},{dy}\n".encode())

        t = (confidence - MATCH_THRESHOLD) / (1.0 - MATCH_THRESHOLD)
        t = max(0.0, min(1.0, t))
        time.sleep(HESITATION_MAX - t * (HESITATION_MAX - HESITATION_MIN))

        ser.write(b"L\n")

        stats["clicks"] += 1
        state = COLLECTING
        state_since = now

    elif state == COLLECTING:
        if not matched:
            state = COOLDOWN
            state_since = now
        elif now - state_since > COLLECTING_TIMEOUT:
            stats["resets"] += 1
            state = COOLDOWN
            state_since = now

    elif state == COOLDOWN:
        if now - state_since >= COOLDOWN_TIME:
            state = WAITING
            state_since = now

    # =========================
    # PERIODIC STATS LOG
    # =========================
    if int(now) % 30 == 0:
        print("---- STATS ----")
        print(stats)
        print("----------------")

    time.sleep(SCAN_INTERVAL)
