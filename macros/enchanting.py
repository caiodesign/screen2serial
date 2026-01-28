"""
Enchanting macro for screen2serial bot.

State machine:
    WARMUP -> CHECK_INVENTORY -> SCAN_ITEMS -> OPEN_MAGIC ->
    FIND_ENCHANT_SPELL -> FIND_ENCHANT_LEVEL -> ENCHANT_LOOP ->
    (loop until count=0) -> FIND_BANKER -> CLICK_BANKER -> 
    WAIT_BANK -> ... -> CHECK_INVENTORY (cycle)
    
    Any state -> (PageDown) -> WARMUP

This macro enchants jade amulets using the level 2 jewellery enchant spell.
After all items are enchanted, it finds the banker to deposit/withdraw.
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
# ENCHANTING STATES
# =========================
ENCH_CHECK_INVENTORY = "ench_check_inventory"
ENCH_SCAN_ITEMS = "ench_scan_items"
ENCH_OPEN_MAGIC = "ench_open_magic"
ENCH_FIND_SPELL = "ench_find_spell"
ENCH_FIND_LEVEL = "ench_find_level"
ENCH_LOOP = "ench_loop"
ENCH_DONE = "ench_done"

# Banking states
ENCH_NEED_BANK = "ench_need_bank"
ENCH_FIND_BANKER = "ench_find_banker"
ENCH_CLICK_BANKER = "ench_click_banker"
ENCH_WAIT_BANK = "ench_wait_bank"

ALL_ENCH_STATES = (
    WARMUP,
    ENCH_CHECK_INVENTORY,
    ENCH_SCAN_ITEMS,
    ENCH_OPEN_MAGIC,
    ENCH_FIND_SPELL,
    ENCH_FIND_LEVEL,
    ENCH_LOOP,
    ENCH_DONE,
    ENCH_NEED_BANK,
    ENCH_FIND_BANKER,
    ENCH_CLICK_BANKER,
    ENCH_WAIT_BANK,
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

# Banker search region (central area of game screen, excluding inventory and chat)
# X: slices 2 & 3 of 4 (331-993px)
# Y: slices 2-5 of 6 (133-667px)
BANKER_REGION = Region(
    x_start=config.BANKER_REGION_X_START,
    y_start=config.BANKER_REGION_Y_START,
    x_end=config.BANKER_REGION_X_END,
    y_end=config.BANKER_REGION_Y_END,
)


@dataclass
class EnchantingContext:
    """Mutable context for enchanting macro."""
    last_item_pos: Point | None  # Fixed position to click (always the same slot)
    items_remaining: int
    enchant_level_pos: Point | None
    banker_pos: Point | None  # Position of banker NPC when found
    bank_wait_start: float | None  # Timestamp when we started waiting for bank
    
    @classmethod
    def create(cls) -> "EnchantingContext":
        return cls(
            last_item_pos=None,
            items_remaining=0,
            enchant_level_pos=None,
            banker_pos=None,
            bank_wait_start=None,
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
    """Scan inventory for jade amulets and find the last item position."""
    items = find_all_templates(
        sct, monitor,
        config.JADE_AMULET_TEMPLATE,
        INVENTORY_REGION,
        config.ENCHANT_ITEM_THRESHOLD,
    )
    
    if not items:
        print("[SCAN_ITEMS] No jade amulets found - looking for banker...")
        return transition_state(state, now, ENCH_FIND_BANKER), stats
    
    # Find the last item (bottom-right priority) and save its position
    # We will click this SAME position every time (item gets enchanted in place)
    last_item = get_last_item_bottom_right(items)
    ctx.last_item_pos = last_item
    ctx.items_remaining = len(items)
    
    print(f"[SCAN_ITEMS] Found {ctx.items_remaining} jade amulets")
    print(f"[SCAN_ITEMS] Last item at ({last_item.x}, {last_item.y}) - will click this position {ctx.items_remaining} times")
    print("[SCAN_ITEMS] Opening magic...")
    return transition_state(state, now, ENCH_OPEN_MAGIC), stats


def handle_open_magic(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
) -> tuple[AppState, Stats]:
    """Open magic interface by pressing KEY_MAGIC."""
    print("[OPEN_MAGIC] Opening magic interface...")
    open_magic_tab(ser)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    return transition_state(state, now, ENCH_FIND_SPELL), stats


def handle_find_spell(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
) -> tuple[AppState, Stats]:
    """Find enchant spell in magic interface (first 40px Y).
    
    NOTE: In RuneLite, F6 opens directly to the last-used spell submenu
    (the enchant level selection popup), NOT the magic spell book.
    So if we don't find the spell here, we proceed to ENCH_FIND_LEVEL
    since we might already be in the enchant level selection window.
    """
    spell_pos = find_template(
        sct, monitor,
        config.ENCHANT_SPELL_TEMPLATE,
        SPELL_REGION,
        config.ENCHANT_SPELL_THRESHOLD,
    )
    
    if spell_pos is None:
        # F6 might have opened directly to enchant level popup - proceed to check
        print("[FIND_SPELL] Enchant spell not found - checking if already in level selection...")
        return transition_state(state, now, ENCH_FIND_LEVEL), stats
    
    print(f"[FIND_SPELL] Found enchant spell at ({spell_pos.x}, {spell_pos.y}) - clicking...")
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
    
    print(f"[FIND_LEVEL] Found level 2 enchant at ({level_pos.x}, {level_pos.y}) - clicking...")
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
    1. Click the SAME last item position (items get enchanted in place)
    2. Click enchant level 2 (saved position)
    3. Decrement counter and repeat until all items enchanted
    """
    if ctx.items_remaining <= 0:
        print("[ENCHANT_LOOP] All items enchanted!")
        return transition_state(state, now, ENCH_DONE), increment_cycles(stats)
    
    if ctx.last_item_pos is None:
        print("[ENCHANT_LOOP] ERROR: No item position saved!")
        return transition_state(state, now, ENCH_DONE), increment_cycles(stats)
    
    print(f"[ENCHANT_LOOP] Enchanting item {ctx.items_remaining} at ({ctx.last_item_pos.x}, {ctx.last_item_pos.y})")
    
    # 1. Click the last item position (always the same slot)
    click_point(ser, ctx.last_item_pos)
    random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    # 2. Decrement counter (item is now enchanted)
    ctx.items_remaining -= 1
    
    # 3. Click enchant level 2 again (use saved position, no rescan)
    if ctx.items_remaining > 0 and ctx.enchant_level_pos is not None:
        click_point(ser, ctx.enchant_level_pos)
        random_delay(config.ENCHANT_CLICK_DELAY_MIN, config.ENCHANT_CLICK_DELAY_MAX)
    
    return state, increment_actions(stats)


def handle_done(
    state: AppState,
    stats: Stats,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle completion - all items enchanted, proceed to banking."""
    print("[DONE] Enchanting complete! Looking for banker...")
    return transition_state(state, now, ENCH_FIND_BANKER), stats


def handle_find_banker(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """Search for banker NPC in the designated game area."""
    banker_pos = find_template(
        sct, monitor,
        config.GE_BANKER_TEMPLATE,
        BANKER_REGION,
        config.BANKER_MATCH_THRESHOLD,
    )
    
    if banker_pos is None:
        print("[FIND_BANKER] Banker not found - retrying...")
        random_delay(0.5, 1.0)
        return state, stats
    
    ctx.banker_pos = banker_pos
    print(f"[FIND_BANKER] Found banker at ({banker_pos.x}, {banker_pos.y})")
    return transition_state(state, now, ENCH_CLICK_BANKER), stats


def handle_click_banker(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """Click on the banker NPC to open bank interface."""
    if ctx.banker_pos is None:
        print("[CLICK_BANKER] ERROR: No banker position saved!")
        return transition_state(state, now, ENCH_FIND_BANKER), stats
    
    print(f"[CLICK_BANKER] Clicking banker at ({ctx.banker_pos.x}, {ctx.banker_pos.y})")
    click_point(ser, ctx.banker_pos)
    random_delay(config.BANK_CLICK_DELAY_MIN, config.BANK_CLICK_DELAY_MAX)
    
    # Start waiting for bank to open
    ctx.bank_wait_start = now
    return transition_state(state, now, ENCH_WAIT_BANK), increment_clicks(stats)


def handle_wait_bank(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor,
    ctx: EnchantingContext,
) -> tuple[AppState, Stats]:
    """Wait for bank interface to open."""
    # TODO: Add bank interface detection template
    # For now, just wait a fixed time and assume it opened
    
    if ctx.bank_wait_start is None:
        ctx.bank_wait_start = now
    
    elapsed = now - ctx.bank_wait_start
    
    # Timeout - try clicking banker again
    if elapsed > config.BANK_WAIT_TIMEOUT:
        print(f"[WAIT_BANK] Timeout after {elapsed:.1f}s - retrying banker click")
        ctx.bank_wait_start = None
        return transition_state(state, now, ENCH_FIND_BANKER), stats
    
    # TODO: Replace with actual bank interface detection
    # For now, assume bank opened after 2 seconds
    if elapsed >= 2.0:
        print("[WAIT_BANK] Bank should be open (TODO: add bank interface detection)")
        # TODO: Transition to deposit/withdraw states
        # For now, go back to warmup as placeholder
        print("[WAIT_BANK] Banking logic complete - returning to warmup (TODO: implement deposit/withdraw)")
        ctx.bank_wait_start = None
        return transition_state(state, now, WARMUP), stats
    
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
        return handle_open_magic(state, stats, now, ser)
    elif state.name == ENCH_FIND_SPELL:
        return handle_find_spell(state, stats, now, ser, sct, monitor)
    elif state.name == ENCH_FIND_LEVEL:
        return handle_find_level(state, stats, now, ser, sct, monitor, ctx)
    elif state.name == ENCH_LOOP:
        return handle_enchant_loop(state, stats, now, ser, ctx)
    elif state.name == ENCH_DONE:
        return handle_done(state, stats, now)
    # Banking states
    elif state.name == ENCH_FIND_BANKER:
        return handle_find_banker(state, stats, now, sct, monitor, ctx)
    elif state.name == ENCH_CLICK_BANKER:
        return handle_click_banker(state, stats, now, ser, ctx)
    elif state.name == ENCH_WAIT_BANK:
        return handle_wait_bank(state, stats, now, sct, monitor, ctx)
    
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
        elif state.name == ENCH_DONE:
            time.sleep(0.5)  # Brief pause before banking
        elif state.name == ENCH_WAIT_BANK:
            time.sleep(0.2)  # Moderate polling while waiting for bank
        elif state.name in (ENCH_FIND_BANKER,):
            time.sleep(0.3)  # Moderate polling while searching for banker
        else:
            time.sleep(0.05)  # Fast during active enchanting
    
    return state, stats
