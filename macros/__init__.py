"""
Macros package for screen2serial bot.

Each macro is fully self-contained with:
- Its own state definitions (e.g., WC_SEARCHING, WC_COLLECTING)
- Its own handler functions
- Its own main loop
- Its own template loading and screen capture setup

Macros use shared infrastructure from logic (AppState, Stats, transitions)
but define their own states and behavior.

To add a new macro:
1. Create a new file (e.g., combat.py)
2. Define states: CB_SEARCHING, CB_ATTACKING, CB_HEALING, etc.
3. Define handlers for each state
4. Define run_combat() main loop with signature: run_combat(ser, check_keyboard, debug=False)
5. Register in MACRO_REGISTRY below
"""

from typing import Callable

from .woodcutting import (
    run_woodcutting,
    create_woodcutting_state,
    # State constants for external use if needed
    WC_SEARCHING,
    WC_COLLECTING,
    WC_DROPPING,
)

from .enchanting import (
    run_enchanting,
    create_enchanting_state,
    # State constants
    ENCH_CHECK_INVENTORY,
    ENCH_SCAN_ITEMS,
    ENCH_OPEN_MAGIC,
    ENCH_FIND_SPELL,
    ENCH_FIND_LEVEL,
    ENCH_LOOP,
    ENCH_NEED_BANK,
    ENCH_DONE,
)

from .herblore import (
    run_herblore,
    create_herblore_state,
    # State constants
    HERB_CHECK_INVENTORY,
    HERB_SCAN_ITEMS,
    HERB_CLEAN_LOOP,
    HERB_DONE,
)


# =========================
# MACRO REGISTRY
# =========================
# Maps macro name -> (run_function, description)
# All run functions have signature: run_xxx(ser, check_keyboard, debug=False)
MACRO_REGISTRY: dict[str, tuple[Callable, str]] = {
    "woodcutting": (run_woodcutting, "Chop trees and drop logs"),
    "enchanting": (run_enchanting, "Enchant jade amulets"),
    "herblore": (run_herblore, "Clean grimy herbs"),
}


def get_available_macros() -> list[str]:
    """Return list of available macro names."""
    return list(MACRO_REGISTRY.keys())


def get_macro(name: str) -> Callable | None:
    """
    Get a macro run function by name.
    
    Returns None if macro not found.
    """
    entry = MACRO_REGISTRY.get(name)
    return entry[0] if entry else None


def get_macro_description(name: str) -> str | None:
    """Get a macro description by name."""
    entry = MACRO_REGISTRY.get(name)
    return entry[1] if entry else None


__all__ = [
    # Registry
    "MACRO_REGISTRY",
    "get_available_macros",
    "get_macro",
    "get_macro_description",
    # Woodcutting
    "run_woodcutting",
    "create_woodcutting_state",
    "WC_SEARCHING",
    "WC_COLLECTING",
    "WC_DROPPING",
    # Enchanting
    "run_enchanting",
    "create_enchanting_state",
    "ENCH_CHECK_INVENTORY",
    "ENCH_SCAN_ITEMS",
    "ENCH_OPEN_MAGIC",
    "ENCH_FIND_SPELL",
    "ENCH_FIND_LEVEL",
    "ENCH_LOOP",
    "ENCH_NEED_BANK",
    "ENCH_DONE",
    # Herblore
    "run_herblore",
    "create_herblore_state",
    "HERB_CHECK_INVENTORY",
    "HERB_SCAN_ITEMS",
    "HERB_CLEAN_LOOP",
    "HERB_DONE",
]
