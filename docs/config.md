# Configuration Reference

All configuration values are defined in `config.py`. This document explains each setting.

## Serial Connection

```python
SERIAL_PORT = "COM5"    # Serial port for Arduino
BAUD_RATE = 9600        # Baud rate (must match Arduino)
```

| Setting       | Description                                       |
| ------------- | ------------------------------------------------- |
| `SERIAL_PORT` | Platform-specific port (COM5, /dev/ttyACM0, etc.) |
| `BAUD_RATE`   | Communication speed (9600 is standard)            |

## Detection Region

The main screen area to search for targets (trees, NPCs, etc.):

```python
REGION_X_START = 0
REGION_X_END = 1575
REGION_Y_START = 30
REGION_Y_END = 827
```

```
┌────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ <- Y_START (30)
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░ DETECTION REGION ░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ <- Y_END (827)
│                                        │
│                              [INVENTORY]│
└────────────────────────────────────────┘
 ^                           ^
X_START (0)              X_END (1575)
```

## Inventory Region

The inventory area for detecting items:

```python
INVENTORY_X_START = 1636
INVENTORY_X_END = 1873
INVENTORY_Y_START = 652
INVENTORY_Y_END = 978
```

## Template Matching

```python
MATCH_THRESHOLD = 0.50   # Minimum confidence (0.0-1.0)
```

| Value | Meaning                                         |
| ----- | ----------------------------------------------- |
| 0.50  | Permissive (more matches, more false positives) |
| 0.70  | Balanced                                        |
| 0.85  | Strict (fewer matches, fewer false positives)   |

Adjust based on template quality and lighting conditions.

## Scan Intervals

```python
SEARCH_SCAN_INTERVAL = 0.5      # Seconds between scans while searching
COLLECTING_SCAN_INTERVAL = 2.0  # Seconds between scans while collecting
```

Lower = more responsive but higher CPU usage.

## Click Hesitation

Human-like delay before clicking based on confidence:

```python
HESITATION_MIN = 0.05   # Minimum delay (high confidence)
HESITATION_MAX = 0.25   # Maximum delay (low confidence)
```

Formula: `hesitation = MAX - (confidence_ratio * (MAX - MIN))`

## Dropping Timing

```python
DROP_MOVE_DELAY = 1.3    # Delay before moving to next item
DROP_CLICK_DELAY = 0.3   # Delay after clicking
```

These prevent actions from being too fast and mechanical.

## Keyboard Controls (Bot)

```python
START_KEY = "page_up"    # Start the macro
STOP_KEY = "page_down"   # Stop the macro
```

## Game UI Keybindings

Keys sent to the game for tab switching:

```python
KEY_COMBAT = "f1"           # Combat options tab
KEY_SKILLS = "f2"           # Skills tab
KEY_QUESTS = "f3"           # Quest list tab
KEY_INVENTORY = "esc"       # Inventory tab
KEY_EQUIPMENT = "f4"        # Worn equipment tab
KEY_PRAYER = "f5"           # Prayer tab
KEY_MAGIC = "f6"            # Magic spellbook tab
KEY_SETTINGS = "f10"        # Settings tab
KEY_CHAT_CONFIRM = "space"  # Confirm chat message
KEY_CHAT_CANCEL = "esc"     # Cancel chat message
KEY_CHAT_OPTION_1 = "1"     # Option 1 in chat menu
KEY_CHAT_OPTION_2 = "2"     # Option 2 in chat menu
KEY_CHAT_OPTION_3 = "3"     # Option 3 in chat menu
KEY_CHAT_OPTION_4 = "4"     # Option 4 in chat menu
KEY_CHAT_OPTION_5 = "5"     # Option 5 in chat menu
KEY_CHAT_OPTION_6 = "6"     # Option 6 in chat menu
KEY_CHAT_OPTION_7 = "7"     # Option 7 in chat menu
KEY_CHAT_OPTION_8 = "8"     # Option 8 in chat menu
KEY_CHAT_OPTION_9 = "9"     # Option 9 in chat menu
KEY_CHAT_OPTION_10 = "10"   # Option 10 in chat menu
```

## Bank Interface Settings

```python
BANK_INTERFACE_X_START = 347
BANK_INTERFACE_X_END = 958
BANK_INTERFACE_Y_START = 28
BANK_INTERFACE_Y_END = 827

BANK_CONTROLS_Y_START = 28
BANK_CONTROLS_Y_END = 100

BANK_STACK_CROP_TOP_PX = 8

BANKER_MATCH_THRESHOLD = 0.60
BANK_CONTROLS_MATCH_THRESHOLD = 0.80

BANK_CLICK_DELAY_MIN = 0.8
BANK_CLICK_DELAY_MAX = 1.2
BANK_WAIT_TIMEOUT = 1.0
```

## Debug Settings

```python
DEBUG = False            # Enable debug mode globally
DEBUG_DIR = "debug_captures"
DEBUG_SAVE_MODE = "fail" # "fail" = only save failed matches, "all" = save all
```

## Macro-Specific Config

For macro-specific settings, keep them in the macro file (e.g. `macros/enchanting.py`, `macros/woodcutting.py`):

```python
MY_MACRO_TEMPLATE = "images/my_macro/target.png"
MY_MACRO_THRESHOLD = 0.75
MY_MACRO_SCAN_INTERVAL = 0.3
```

Then use these values directly in the macro file.

## Image Templates

```python
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
```

## Environment-Specific Config

For settings that vary between machines, consider environment variables:

```python
import os

SERIAL_PORT = os.environ.get("SERIAL_PORT", "COM5")
```

Then set before running:

```bash
# Windows
set SERIAL_PORT=COM3
python main.py --macro woodcutting

# Linux/macOS
SERIAL_PORT=/dev/ttyACM0 python main.py --macro woodcutting
```

## Resolution Considerations

Current settings assume 1920x1080 resolution. For different resolutions:

1. Recalculate region boundaries
2. Re-capture template images at new resolution
3. Adjust inventory icon positions

Example for 2560x1440:

```python
# Scale factor: 2560/1920 = 1.33
REGION_X_END = int(1575 * 1.33)  # ~2095
INVENTORY_X_START = int(1636 * 1.33)  # ~2175
```
