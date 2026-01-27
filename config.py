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
# INVENTORY MANAGEMENT
# =========================
INVENTORY_X_START = 1654
INVENTORY_X_END = 1852
INVENTORY_Y_START = 666
INVENTORY_Y_END = 969
INVENTORY_ROWS = 7
INVENTORY_COLS = 4

# Inventory templates
RESOURCE_TEMPLATE_PATH = "resource.png"
INVENTORY_BG_TEMPLATE_PATH = "inventory-bg-texture.png"

# Inventory matching threshold (lower = more strict)
INVENTORY_BG_THRESHOLD = 0.85  # similarity threshold for empty slot
INVENTORY_RESOURCE_THRESHOLD = 0.70  # similarity threshold for resource

# =========================
# DEBUG
# =========================
DEBUG = True
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"
