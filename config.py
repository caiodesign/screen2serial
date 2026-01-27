# =========================
# PATHS & SERIAL
# =========================
TEMPLATE_PATH = "family.png"
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

# =========================
# DETECTION REGION
# =========================
REGION_X_START = 0
REGION_X_END = 1575
REGION_Y_START = 30
REGION_Y_END = 827

# =========================
# MATCHING
# =========================
MATCH_THRESHOLD = 0.50  # Lowered from 0.70 for testing (opencv_tutorials uses 0.5)
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
INVENTORY_X_START = 1636
INVENTORY_X_END = 1873
INVENTORY_Y_START = 652
INVENTORY_Y_END = 978
INVENTORY_ROWS = 7
INVENTORY_COLS = 4

# Inventory margins (pixels)
INVENTORY_OUTER_MARGIN_X = 12  # total horizontal outer margin (6px each side)
INVENTORY_OUTER_MARGIN_Y = 6   # total vertical outer margin (3px each side)
INVENTORY_ITEM_PADDING_X = 6   # padding on each side of item (left AND right)
INVENTORY_ITEM_PADDING_Y = 3   # padding on each side of item (top AND bottom)

# Sample size for inventory detection (small center region)
INVENTORY_SAMPLE_SIZE = 14     # pixels to sample from center of each cell

# Inventory templates
RESOURCE_TEMPLATE_PATH = "resource.png"
INVENTORY_BG_TEMPLATE_PATH = "inventory-bg-texture.png"

# Inventory matching threshold (lower = more strict)
INVENTORY_BG_THRESHOLD = 0.85  # similarity threshold for empty slot
INVENTORY_RESOURCE_THRESHOLD = 0.70  # similarity threshold for resource

# =========================
# DEBUG
# =========================
DEBUG = False
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"
