# =========================
# PATHS & SERIAL
# =========================
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

# =========================
# DETECTION REGION (for searching resources)
# =========================
# Main area: 1580x1010 with 28px top border.
# Exclude 256px from left/right, and 208px from top/bottom of main area.
REGION_X_START = 256
REGION_X_END = 1324
REGION_Y_START = 236
REGION_Y_END = 830

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
KEY_COMBAT = "f1"           # Combat options tab
KEY_SKILLS = "f2"           # Skills tab
KEY_QUESTS = "f3"           # Quest list tab
KEY_INVENTORY = "esc"       # Inventory tab
KEY_EQUIPMENT = "f4"        # Worn equipment tab
KEY_PRAYER = "f5"           # Prayer tab
KEY_MAGIC = "f6"            # Magic spellbook tab
KEY_SETTINGS = "f10"        # Settings tab
KEY_CHAT_CONFIRM = 'space'  # Confirm chat message
KEY_CHAT_CANCEL = 'esc'     # Cancel chat message
KEY_CHAT_OPTION_1 = '1'     # Option 1 in chat menu
KEY_CHAT_OPTION_2 = '2'     # Option 2 in chat menu
KEY_CHAT_OPTION_3 = '3'     # Option 3 in chat menu
KEY_CHAT_OPTION_4 = '4'     # Option 4 in chat menu
KEY_CHAT_OPTION_5 = '5'     # Option 5 in chat menu
KEY_CHAT_OPTION_6 = '6'     # Option 6 in chat menu
KEY_CHAT_OPTION_7 = '7'     # Option 7 in chat menu
KEY_CHAT_OPTION_8 = '8'     # Option 8 in chat menu
KEY_CHAT_OPTION_9 = '9'     # Option 9 in chat menu
KEY_CHAT_OPTION_10 = '10'   # Option 10 in chat menu

# Menu region (bottom bar where inventory/magic/etc tabs are)
MENU_REGION_X_START = 1030
MENU_REGION_X_END = 1580
MENU_REGION_Y_START = 980
MENU_REGION_Y_END = 1035

# =========================
# BANKING (Grand Exchange)
# =========================
# Bank interface region (full bank UI)
BANK_INTERFACE_X_START = 347
BANK_INTERFACE_X_END = 958
BANK_INTERFACE_Y_START = 28
BANK_INTERFACE_Y_END = 827

# Bank controls detection region (top bar)
BANK_CONTROLS_Y_START = 28
BANK_CONTROLS_Y_END = 100

# Stacked item label crop (remove top pixels)
BANK_STACK_CROP_TOP_PX = 8

# Banker detection threshold
BANKER_MATCH_THRESHOLD = 0.60

# Bank controls detection threshold
BANK_CONTROLS_MATCH_THRESHOLD = 0.80

# Banking timing
BANK_CLICK_DELAY_MIN = 0.8
BANK_CLICK_DELAY_MAX = 1.2
BANK_WAIT_TIMEOUT = 1.0  # Max seconds to wait for bank to open

# =========================
# MOUSE MOVEMENT
# =========================
MOUSE_ARRIVAL_TIMEOUT = 3.5  # Max seconds to wait for mouse to reach target
MOUSE_ARRIVAL_TOLERANCE = 12  # Pixels tolerance for considering mouse "arrived"

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

# =========================
# IMAGE TEMPLATES
# =========================
TEMPLATE_PATH = "images/resource/tree.png"
RESOURCE_TEMPLATE_PATH = "images/resource/wood.pn"

JADE_AMULET_TEMPLATE = "images/item/equip/jade_amulet.png"
ENCHANT_SPELL_TEMPLATE = "images/magic/magic_jewell_enchant.png"
ENCHANT_LEVEL_2_TEMPLATE = "images/magic/magic_jewell_enchant_level_2.png"

INVENTORY_OPENED_TEMPLATE = "images/menu/inventory-opened.png"
INVENTORY_CLOSED_TEMPLATE = "images/menu/inventory.png"

GE_BANKER_TEMPLATE = "images/npc/ge_banker.png"
BANK_CONTROLS_TEMPLATE = "images/ui/bank-controls.png"
AMULET_OF_CHEM_TEMPLATE = "images/item/equip/amulet_of_chemistry.png"

# =========================
# COLOR DETECTION (BGR format)
# =========================
# Color presets for RuneLite highlight plugins
# Each color is a tuple: ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
# These work with cv2.inRange() to create masks

# Red highlights (enemies, danger)
COLOR_RED = ((0, 0, 180), (80, 80, 255))

# Green highlights (friendly, available)
COLOR_GREEN = ((0, 180, 0), (80, 255, 80))

# Amber/Yellow highlights (warning, caution)
COLOR_AMBER = ((0, 200, 200), (60, 255, 255))

# Cyan/Blue highlights (clickable objects - trees, rocks, NPCs)
COLOR_CYAN = ((200, 200, 0), (255, 255, 5))

# Purple/Magenta highlights (ground items, loot)
COLOR_PURPLE = ((150, 0, 100), (255, 60, 160))

# Minimum contour area to consider valid (filters noise)
COLOR_MIN_CONTOUR_AREA = 10
