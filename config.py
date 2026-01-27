# =========================
# PATHS & SERIAL
# =========================
TEMPLATE_PATH = "family.png"
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

# =========================
# DETECTION REGION
# =========================
CENTER_X = 364
CENTER_Y = 201
CROP_SIZE = 100
Y_MARGIN = 30

# =========================
# MATCHING
# =========================
MATCH_THRESHOLD = 0.70
SCAN_INTERVAL = 2.0

# =========================
# VERIFICATION
# =========================
VERIFY_REQUIRED = 1  # consecutive matches needed

# =========================
# TIMEOUTS (seconds)
# =========================
COLLECTING_TIMEOUT = 30
COOLDOWN_TIME = 5

# =========================
# CLICK HESITATION
# =========================
HESITATION_MIN = 0.05
HESITATION_MAX = 0.25

# =========================
# DEBUG
# =========================
DEBUG = True
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"
