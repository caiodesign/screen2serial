# =========================
# PATHS & SERIAL
# =========================
TEMPLATE_PATH = "family.png"
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

# =========================
# DETECTION REGION (for searching resources)
# =========================
REGION_X_START = 0
REGION_X_END = 1575
REGION_Y_START = 30
REGION_Y_END = 827

# =========================
# MATCHING
# =========================
MATCH_THRESHOLD = 0.50  # Lowered from 0.70 for testing (opencv_tutorials uses 0.5)

# =========================
# SCAN INTERVALS (seconds)
# =========================
SEARCH_SCAN_INTERVAL = 0.5    # How often to scan while searching
COLLECTING_SCAN_INTERVAL = 2.0  # How often to scan while collecting

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

# Inventory templates
RESOURCE_TEMPLATE_PATH = "resource.png"

# Inventory matching threshold
INVENTORY_RESOURCE_THRESHOLD = 0.70  # similarity threshold for resource detection

# =========================
# DROPPING
# =========================
DROP_MOVE_DELAY = 1.3    # Delay before moving to the next item (seconds)
DROP_CLICK_DELAY = 0.3   # Delay after clicking before moving to next item

# =========================
# KEYBOARD CONTROLS
# =========================
START_KEY = "page_up"    # Key to start the bot (warmup -> searching)
STOP_KEY = "page_down"   # Key to stop the bot (any state -> warmup)

# =========================
# DEBUG
# =========================
DEBUG = False
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"
