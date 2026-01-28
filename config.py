# =========================
# PATHS & SERIAL
# =========================
TEMPLATE_PATH = "images/resource/tree.png"
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
RESOURCE_TEMPLATE_PATH = "images/resource/wood.pn"

# Inventory matching threshold
INVENTORY_RESOURCE_THRESHOLD = 0.70  # similarity threshold for resource detection

# =========================
# DROPPING
# =========================
DROP_MOVE_DELAY = 1.3    # Delay before moving to the next item (seconds)
DROP_CLICK_DELAY = 0.3   # Delay after clicking before moving to next item

# =========================
# KEYBOARD CONTROLS (Bot)
# =========================
START_KEY = "page_up"    # Key to start the bot (warmup -> searching)
STOP_KEY = "page_down"   # Key to stop the bot (any state -> warmup)

# =========================
# KEYBINDINGS (Game UI Tabs)
# =========================
KEY_COMBAT = "f1"        # Combat options tab
KEY_SKILLS = "f2"        # Skills tab
KEY_QUESTS = "f3"        # Quest list tab
KEY_INVENTORY = "esc"    # Inventory tab
KEY_EQUIPMENT = "f4"     # Worn equipment tab
KEY_PRAYER = "f5"        # Prayer tab
KEY_MAGIC = "f6"         # Magic spellbook tab
KEY_SETTINGS = "f10"     # Settings tab

# =========================
# ENCHANTING
# =========================
# Templates
JADE_AMULET_TEMPLATE = "images/item/equip/jade_amulet.png"
ENCHANT_SPELL_TEMPLATE = "images/magic/magic_jewell_enchant.png"
ENCHANT_LEVEL_2_TEMPLATE = "images/magic/magic_jewell_enchant_level_2.png"

# Spell scan region (first 40px Y of inventory area for finding spells)
SPELL_SCAN_Y_LIMIT = 40

# Menu region (bottom bar where inventory/magic/etc tabs are)
MENU_REGION_X_START = 1030
MENU_REGION_X_END = 1580
MENU_REGION_Y_START = 980
MENU_REGION_Y_END = 1035

# Menu templates
INVENTORY_OPENED_TEMPLATE = "images/menu/inventory-opened.png"
INVENTORY_CLOSED_TEMPLATE = "images/menu/inventory.png"

# Menu detection threshold
MENU_MATCH_THRESHOLD = 0.80

# Enchanting thresholds
ENCHANT_ITEM_THRESHOLD = 0.70
ENCHANT_SPELL_THRESHOLD = 0.70

# Enchanting timing (fast: 0.2-0.4s)
ENCHANT_CLICK_DELAY_MIN = 0.2
ENCHANT_CLICK_DELAY_MAX = 0.4

# =========================
# DEBUG
# =========================
DEBUG = False
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"
