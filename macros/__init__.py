"""
Macros package for screen2serial bot.

Each macro is fully self-contained with:
- Its own state definitions (e.g., WC_SEARCHING, WC_COLLECTING)
- Its own handler functions
- Its own main loop

Macros use shared infrastructure from state.py (AppState, Stats, transitions)
but define their own states and behavior.

To add a new macro:
1. Create a new file (e.g., combat.py)
2. Define states: CB_SEARCHING, CB_ATTACKING, CB_HEALING, etc.
3. Define handlers for each state
4. Define run_combat() main loop
5. Export from this __init__.py
"""

from .woodcutting import (
    run_woodcutting,
    create_woodcutting_state,
    # State constants for external use if needed
    WC_SEARCHING,
    WC_COLLECTING,
    WC_DROPPING,
)

__all__ = [
    "run_woodcutting",
    "create_woodcutting_state",
    "WC_SEARCHING",
    "WC_COLLECTING",
    "WC_DROPPING",
]
