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
# Note: These values assume RuneLite sidebar is open (342px width)
INVENTORY_X_START = 1324
INVENTORY_X_END = 1561
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
SPELL_SCAN_Y_LIMIT = 60

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
ENCHANT_ITEM_THRESHOLD = 0.60
ENCHANT_SPELL_THRESHOLD = 0.60

# Enchanting timing
ENCHANT_CLICK_DELAY_MIN = 0.84
ENCHANT_CLICK_DELAY_MAX = 0.95

# =========================
# BANKING (Grand Exchange)
# =========================
# Banker NPC template
GE_BANKER_TEMPLATE = "images/npc/ge_banker.png"

# Banker search region calculation:
# X: 1580px total - 256px inventory = 1324px, divide by 4 = 331px slices
#    Use slices 2 & 3: from 331px to 993px
# Y: 1008px total - 208px chat = 800px, divide by 6 = 133px slices
#    Use slices 2, 3, 4, 5: from 133px to 667px
BANKER_REGION_X_START = 331
BANKER_REGION_X_END = 993
BANKER_REGION_Y_START = 133
BANKER_REGION_Y_END = 667

# Banker detection threshold
BANKER_MATCH_THRESHOLD = 0.60

# Banking timing
BANK_CLICK_DELAY_MIN = 0.8
BANK_CLICK_DELAY_MAX = 1.2
BANK_WAIT_TIMEOUT = 5.0  # Max seconds to wait for bank to open

# =========================
# MOUSE MOVEMENT
# =========================
MOUSE_ARRIVAL_TIMEOUT = 3.5  # Max seconds to wait for mouse to reach target
MOUSE_ARRIVAL_TOLERANCE = 5  # Pixels tolerance for considering mouse "arrived"

# =========================
# DEBUG
# =========================
DEBUG = False
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail"  # "fail" or "all"

# Debug window mode for vision_debug.py
# "live" - Windows update on every vision call, non-blocking, press 'q' to close
# "pause_on_fail" - Only shows window when match fails, pauses until keypress
DEBUG_WINDOW_MODE = "live"
