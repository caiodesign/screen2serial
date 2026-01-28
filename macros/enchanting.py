"""
Enchanting macro for screen2serial bot.

State machine:
    WARMUP -> CHECK_INVENTORY -> SCAN_ITEMS -> OPEN_MAGIC ->
    FIND_ENCHANT_SPELL -> FIND_ENCHANT_LEVEL -> ENCHANT_LOOP ->
    (loop until count=0) -> DONE
    
    Any state -> (PageDown) -> WARMUP

This macro enchants jade amulets using the level 2 jewellery enchant spell.
"""

import time
from dataclasses import dataclass

import config

from logic import (
    # State
    AppState,
    Stats,
    WARMUP,
    make_initial_state,
    make_initial_stats,
    transition_state,
    update_state_data,
    accumulate_state_time,
    increment_clicks,
    increment_actions,
    increment_cycles,
    # Capture
    create_screen_capturer,
    # Vision (non-debug)
    Region,
    Point,
    get_last_item_bottom_right,
    # Actions
    click_point,
    random_delay,
    open_inventory,
    open_magic_tab,
)

# Import vision functions - use debug versions when DEBUG=True
if config.DEBUG:
    from logic import (
        find_template_debug as find_template,
        find_all_templates_debug as find_all_templates,
        template_exists_debug as template_exists,
    )
else:
    from logic import (
        find_template,
        find_all_templates,
        template_exists,
    )


# =========================
# DEBUG HELPER - Save images to disk for debugging vision
# =========================
import os
import cv2
import numpy as np

def _debug_save_search(sct, monitor, template_path: str, region, state_name: str):
    """
    DEBUG: Save the captured region and template to disk for inspection.
    This helps verify what's actually being searched vs what debug window shows.
    """
    debug_dir = "debug_captures"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Log the parameters
    print(f"\n{'='*60}")
    print(f"[DEBUG {state_name}]")
    print(f"  Template path: {template_path}")
    print(f"  Region: X={region.x_start}-{region.x_end}, Y={region.y_start}-{region.y_end}")
    print(f"  Region size: {region.x_end - region.x_start}x{region.y_end - region.y_start}")
    
    # Capture the region
    capture_region = {
        "left": monitor["left"] + region.x_start,
        "top": monitor["top"] + region.y_start,
        "width": region.x_end - region.x_start,
        "height": region.y_end - region.y_start,
    }
    screenshot = sct.grab(capture_region)
    captured = np.array(screenshot)
    captured_bgr = cv2.cvtColor(captured, cv2.COLOR_BGRA2BGR)
    
    # Save captured region
    captured_path = os.path.join(debug_dir, f"{state_name}_captured_region.png")
    cv2.imwrite(captured_path, captured_bgr)
    print(f"  Saved captured region: {captured_path}")
    
    # Load and save the template for comparison
    if os.path.exists(template_path):
        template = cv2.imread(template_path)
        template_save_path = os.path.join(debug_dir, f"{state_name}_template.png")
        cv2.imwrite(template_save_path, template)
        print(f"  Saved template copy: {template_save_path}")
        print(f"  Template size: {template.shape[1]}x{template.shape[0]}")
    else:
        print(f"  WARNING: Template not found at {template_path}")
    
    print(f"{'='*60}\n")


def _debug_save_screen(sct, monitor, region, name: str):
    """DEBUG: Save a screen capture without template matching."""
    debug_dir = "debug_captures"
    os.makedirs(debug_dir, exist_ok=True)
    
    capture_region = {
        "left": monitor["left"] + region.x_start,
        "top": monitor["top"] + region.y_start,
        "width": region.x_end - region.x_start,
        "height": region.y_end - region.y_start,
    }
    screenshot = sct.grab(capture_region)
    captured = np.array(screenshot)
    captured_bgr = cv2.cvtColor(captured, cv2.COLOR_BGRA2BGR)
    
    path = os.path.join(debug_dir, f"{name}.png")
    cv2.imwrite(path, captured_bgr)
    print(f"[DEBUG] Saved screen: {path}")


# =========================
# ENCHANTING STATES
# =========================
ENCH_CHECK_INVENTORY = "ench_check_inventory"
ENCH_SCAN_ITEMS = "ench_scan_items"
ENCH_OPEN_MAGIC = "ench_open_magic"
ENCH_FIND_SPELL = "ench_find_spell"
ENCH_FIND_LEVEL = "ench_find_level"
ENCH_LOOP = "ench_loop"
ENCH_NEED_BANK = "ench_need_bank"
ENCH_DONE = "ench_done"

ALL_ENCH_STATES = (
    WARMUP,
    ENCH_CHECK_INVENTORY,
    ENCH_SCAN_ITEMS,
    ENCH_OPEN_MAGIC,
    ENCH_FIND_SPELL,
    ENCH_FIND_LEVEL,
    ENCH_LOOP,
    ENCH_NEED_BANK,
    ENCH_DONE,
)


# =========================
# ENCHANTING CONFIG
# =========================
INVENTORY_REGION = Region(
    x_start=config.INVENTORY_X_START,
    y_start=config.INVENTORY_Y_START,
    x_end=config.INVENTORY_X_END,
    y_end=config.INVENTORY_Y_END,
)

# Region for scanning spells (first 40px Y of inventory area)
SPELL_REGION = Region(
    x_start=config.INVENTORY_X_START,
    y_start=config.INVENTORY_Y_START,
    x_end=config.INVENTORY_X_END,
    y_end=config.INVENTORY_Y_START + config.SPELL_SCAN_Y_LIMIT,
)

# Menu region (bottom bar where tabs are located)
MENU_REGION = Region(
    x_start=config.MENU_REGION_X_START,
    y_start=config.MENU_REGION_Y_START,
    x_end=config.MENU_REGION_X_END,
    y_end=config.MENU_REGION_Y_END,
)


@dataclass
class EnchantingContext:
    """Mutable context for enchanting macro."""
    item_locations: list[Point]
    items_remaining: int
    enchant_level_pos: Point | None
    
    @classmethod
    def create(cls) -> "EnchantingContext":
        return cls(
            item_locations=[],
            items_remaining=0,
            enchant_level_pos=None,
        )


# =========================
# ENCHANTING HANDLERS
# =========================

def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for user to start."""
    if should_start:
        print("[WARMUP] Starting enchanting macro...")
        return transition_state(state, now, ENCH_CHECK_INVENTORY), stats
    return state, stats


def handle_check_inventory(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
) -> tuple[AppState, Stats]:
    """Check if inventory is opened using template matching in menu region."""
    is_open = template_exists(
        sct, monitor,
        config.INVENTORY_OPENED_TEMPLATE,
        MENU_REGION,
        config.MENU_MATCH_THRESHOLD,
    )
    
    if is_open:
        print("[CHECK_INVENTORY] Inventory is open - scanning items...")
        return transition_state(state, now, ENCH_SCAN_ITEMS), stats
    else:
        print("[CHECK_INVENTORY] Inventory not open - pressing ESC...")
        open_inventory(ser)
        random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
        # Stay in this state to verify it opened
        return state, stats


def handle_scan_items(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """Scan inventory for jade amulets and save locations."""
    items = find_all_templates(
        sct, monitor,
        config.JADE_AMULET_TEMPLATE,
        INVENTORY_REGION,
        config.ENCHANT_ITEM_THRESHOLD,
    )
    
    if not items:
        print("[SCAN_ITEMS] No jade amulets found - need to bank")
        return transition_state(state, now, ENCH_NEED_BANK), stats
    
    # Save item locations and count
    ctx.item_locations = items
    ctx.items_remaining = len(items)
    
    print(f"[SCAN_ITEMS] Found {ctx.items_remaining} jade amulets - opening magic...")
    return transition_state(state, now, ENCH_OPEN_MAGIC), stats


def handle_open_magic(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
) -> tuple[AppState, Stats]:
    """Open magic interface by pressing KEY_MAGIC."""
    # DEBUG: Save screen BEFORE pressing F6
    _debug_save_screen(sct, monitor, INVENTORY_REGION, "OPEN_MAGIC_before_F6")
    
    print("[OPEN_MAGIC] Opening magic interface (pressing F6)...")
    open_magic_tab(ser)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    # DEBUG: Save screen AFTER pressing F6
    _debug_save_screen(sct, monitor, INVENTORY_REGION, "OPEN_MAGIC_after_F6")
    
    return transition_state(state, now, ENCH_FIND_SPELL), stats


def handle_find_spell(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
) -> tuple[AppState, Stats]:
    """Find enchant spell in magic interface (first 60px Y)."""
    
    # DEBUG: Save what we're actually searching for
    _debug_save_search(
        sct, monitor,
        config.ENCHANT_SPELL_TEMPLATE,
        SPELL_REGION,
        "FIND_SPELL"
    )
    
    spell_pos = find_template(
        sct, monitor,
        config.ENCHANT_SPELL_TEMPLATE,
        SPELL_REGION,
        config.ENCHANT_SPELL_THRESHOLD,
    )
    
    if spell_pos is None:
        print("[FIND_SPELL] Spell not found - returning to WARMUP")
        return transition_state(state, now, WARMUP), stats
    
    print(f"[FIND_SPELL] Found spell at ({spell_pos.x}, {spell_pos.y}) - clicking and transitioning to FIND_LEVEL...")
    click_point(ser, spell_pos)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    return transition_state(state, now, ENCH_FIND_LEVEL), increment_clicks(stats)


def handle_find_level(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """Find enchant level 2 in enchants interface and save position."""
    
    # DEBUG: Save what we're actually searching for
    _debug_save_search(
        sct, monitor,
        config.ENCHANT_LEVEL_2_TEMPLATE,
        INVENTORY_REGION,
        "FIND_LEVEL"
    )
    
    level_pos = find_template(
        sct, monitor,
        config.ENCHANT_LEVEL_2_TEMPLATE,
        INVENTORY_REGION,
        config.ENCHANT_SPELL_THRESHOLD,
    )
    
    if level_pos is None:
        print("[FIND_LEVEL] ERROR: Cannot find level 2 enchant!")
        return transition_state(state, now, WARMUP), stats
    
    # Save position for reuse in loop
    ctx.enchant_level_pos = level_pos
    
    print(f"[FIND_LEVEL] Found level 2 at ({level_pos.x}, {level_pos.y}) - clicking...")
    click_point(ser, level_pos)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    return transition_state(state, now, ENCH_LOOP), increment_clicks(stats)


def handle_enchant_loop(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """
    Main enchanting loop:
    1. Click last item (bottom-right priority)
    2. Click enchant level 2 (saved position)
    3. Repeat until all items enchanted
    """
    if ctx.items_remaining <= 0:
        print("[ENCHANT_LOOP] All items enchanted!")
        return transition_state(state, now, ENCH_DONE), increment_cycles(stats)
    
    # Get last item (bottom-right priority)
    last_item = get_last_item_bottom_right(ctx.item_locations)
    
    if last_item is None:
        print("[ENCHANT_LOOP] No items left in list!")
        return transition_state(state, now, ENCH_DONE), increment_cycles(stats)
    
    print(f"[ENCHANT_LOOP] Enchanting item {len(ctx.item_locations)}/{ctx.items_remaining + len(ctx.item_locations) - 1} at ({last_item.x}, {last_item.y})")
    
    # 1. Click the last item (inventory is now open after clicking enchant level 2)
    click_point(ser, last_item)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    # 2. Remove clicked item from list
    ctx.item_locations = [p for p in ctx.item_locations if p != last_item]
    ctx.items_remaining -= 1
    
    # 3. Click enchant level 2 again (use saved position, no rescan)
    if ctx.items_remaining > 0 and ctx.enchant_level_pos is not None:
        click_point(ser, ctx.enchant_level_pos)
        random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    return state, increment_actions(stats)


def handle_need_bank(
    state: AppState,
    stats: Stats,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle when no items found - need to interact with banker."""
    print("[NEED_BANK] No items to enchant - banking logic not yet implemented")
    # Future: Add banking logic here
    return state, stats


def handle_done(
    state: AppState,
    stats: Stats,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle completion - all items enchanted."""
    print("[DONE] Enchanting complete!")
    # Could transition to NEED_BANK or WARMUP depending on desired behavior
    return state, stats


def process_enchanting_state(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: EnchantingContext,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process enchanting state machine."""
    
    # Stop always returns to warmup
    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats
    
    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == ENCH_CHECK_INVENTORY:
        return handle_check_inventory(state, stats, now, ser, sct, monitor)
    elif state.name == ENCH_SCAN_ITEMS:
        return handle_scan_items(state, stats, now, sct, monitor, ctx)
    elif state.name == ENCH_OPEN_MAGIC:
        return handle_open_magic(state, stats, now, ser, sct, monitor)
    elif state.name == ENCH_FIND_SPELL:
        return handle_find_spell(state, stats, now, ser, sct, monitor)
    elif state.name == ENCH_FIND_LEVEL:
        return handle_find_level(state, stats, now, ser, sct, monitor, ctx)
    elif state.name == ENCH_LOOP:
        return handle_enchant_loop(state, stats, now, ser, ctx)
    elif state.name == ENCH_NEED_BANK:
        return handle_need_bank(state, stats, now)
    elif state.name == ENCH_DONE:
        return handle_done(state, stats, now)
    
    return state, stats


# =========================
# ENCHANTING MAIN LOOP
# =========================

def print_status(state: AppState, stats: Stats, ctx: EnchantingContext) -> None:
    """Print current enchanting status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Items remaining: {ctx.items_remaining}")
    print(f"Clicks: {stats.clicks} | Enchanted: {stats.actions} | Cycles: {stats.cycles}")
    print("=" * 40)


def create_enchanting_state() -> tuple[AppState, Stats, EnchantingContext]:
    """Create initial state, stats, and context for enchanting."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_ENCH_STATES),
        EnchantingContext.create(),
    )


def run_enchanting(
    # Serial connection
    ser,
    # Keyboard input function (returns should_start, should_stop)
    check_keyboard: callable,
    # Debug options
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run the enchanting macro loop.
    
    This macro is fully self-contained:
    - Creates screen capture internally
    - Reads config values internally
    
    Args:
        ser: Serial connection for mouse control
        check_keyboard: Function that returns (should_start, should_stop) tuple
        debug: Enable debug mode
        
    Returns:
        Final (state, stats) tuple when the loop exits
    """
    # Initialize screen capture
    sct, monitor = create_screen_capturer()
    
    # Initialize enchanting-specific state
    state, stats, ctx = create_enchanting_state()
    
    last_loop_time = time.time()
    last_status_print = 0
    
    # Print banner
    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - ENCHANTING")
    print("=" * 50)
    print(f"Inventory: ({config.INVENTORY_X_START}, {config.INVENTORY_Y_START}) to ({config.INVENTORY_X_END}, {config.INVENTORY_Y_END})")
    print("")
    print("Controls:")
    print("  Page Up   = Start enchanting")
    print("  Page Down = Stop (return to warmup)")
    print("")
    print("State: WARMUP - Press Page Up to start")
    print("=" * 50)
    print("")
    
    while True:
        now = time.time()
        
        # Track state time
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now
        
        # Check keyboard input
        should_start, should_stop = check_keyboard()
        
        # Process enchanting state machine
        old_state = state.name
        state, stats = process_enchanting_state(
            state, stats, now, ser, sct, monitor, ctx,
            should_start, should_stop,
        )
        
        # Print status on state change or every 30 seconds
        if state.name != old_state:
            print_status(state, stats, ctx)
        elif int(now) - last_status_print >= 30:
            print_status(state, stats, ctx)
            last_status_print = int(now)
        
        # Determine sleep interval based on state
        if state.name == WARMUP:
            time.sleep(0.1)  # Fast polling for keyboard in warmup
        elif state.name in (ENCH_DONE, ENCH_NEED_BANK):
            time.sleep(1.0)  # Slow polling when waiting
        else:
            time.sleep(0.05)  # Fast during active enchanting
    
    return state, stats
