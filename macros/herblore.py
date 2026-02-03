"""
Herblore macro for screen2serial bot.

State machine:
    WARMUP -> CHECK_INVENTORY -> SCAN_ITEMS -> CLEAN_LOOP ->
    (loop until all items clicked) -> FIND_BANKER -> CLICK_BANKER -> 
    WAIT_BANK -> ... -> CHECK_INVENTORY (cycle)
    
    Any state -> (PageDown) -> WARMUP

This macro cleans grimy herbs by clicking above each item in the inventory.
After all items are cleaned, it finds the banker to deposit/withdraw.
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
    ColorRange,
    load_template,
    crop_template,
    sort_by_grid,
    # Color detection
    find_by_color,
    # Actions
    click_point,
    random_delay,
    open_inventory,
    press_key,
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
# HERBLORE STATES
# =========================
HERB_CHECK_INVENTORY = "herb_check_inventory"
HERB_SCAN_ITEMS = "herb_scan_items"
HERB_CLEAN_LOOP = "herb_clean_loop"
HERB_DONE = "herb_done"

# Banking states
HERB_FIND_BANKER = "herb_find_banker"
HERB_CLICK_BANKER = "herb_click_banker"
HERB_WAIT_BANK = "herb_wait_bank"

ALL_HERB_STATES = (
    WARMUP,
    HERB_CHECK_INVENTORY,
    HERB_SCAN_ITEMS,
    HERB_CLEAN_LOOP,
    HERB_DONE,
    HERB_FIND_BANKER,
    HERB_CLICK_BANKER,
    HERB_WAIT_BANK,
)


# =========================
# HERBLORE CONFIG
# =========================
MENU_MATCH_THRESHOLD = 0.80
HERB_ITEM_THRESHOLD = 0.60

# Use color-based matching for grimy herbs (better detection of brownish/dark tint)
# Grayscale matching loses the color distinction between grimy and clean herbs
USE_COLOR_MATCHING = True

# Reduced delays for faster clicking
HERB_CLICK_DELAY_MIN = 0.35 
HERB_CLICK_DELAY_MAX = 0.47

# Banker detection by color (RuneLite NPC highlight)
# RGBA (0, 255, 255, 255) = Cyan -> BGR format: (255, 255, 0)
BANKER_COLOR: ColorRange = ((250, 250, 0), (255, 255, 5))
BANKER_COLOR_MIN_AREA = 50  # Minimum pixel area for valid banker detection

# Grimy herb template path
GRIMY_HERB_TEMPLATE = "images/item/misc/grimy_tarromin.png"

INVENTORY_REGION = Region(
    x_start=config.INVENTORY_X_START,
    y_start=config.INVENTORY_Y_START,
    x_end=config.INVENTORY_X_END,
    y_end=config.INVENTORY_Y_END,
)

# Menu region (bottom bar where tabs are located)
MENU_REGION = Region(
    x_start=config.MENU_REGION_X_START,
    y_start=config.MENU_REGION_Y_START,
    x_end=config.MENU_REGION_X_END,
    y_end=config.MENU_REGION_Y_END,
)

# Banker search region (generic detection area)
BANKER_REGION = Region(
    x_start=config.REGION_X_START,
    y_start=config.REGION_Y_START,
    x_end=config.REGION_X_END,
    y_end=config.REGION_Y_END,
)

# Bank interface regions
BANK_INTERFACE_REGION = Region(
    x_start=config.BANK_INTERFACE_X_START,
    y_start=config.BANK_INTERFACE_Y_START,
    x_end=config.BANK_INTERFACE_X_END,
    y_end=config.BANK_INTERFACE_Y_END,
)

BANK_CONTROLS_REGION = Region(
    x_start=config.BANK_INTERFACE_X_START,
    y_start=config.BANK_CONTROLS_Y_START,
    x_end=config.BANK_INTERFACE_X_END,
    y_end=config.BANK_CONTROLS_Y_END,
)


@dataclass
class HerbloreContext:
    """Mutable context for herblore macro."""
    item_positions: list[Point]  # All found item positions to click
    current_item_index: int  # Current index in item_positions
    items_total: int  # Total items found in scan
    banker_pos: Point | None  # Position of banker NPC when found
    bank_wait_start: float | None  # Timestamp when we started waiting for bank
    bank_herb_template: object | None  # Cropped template for bank stacks
    last_deposit_pos: Point | None  # Last item position for depositing
    
    @classmethod
    def create(cls) -> "HerbloreContext":
        return cls(
            item_positions=[],
            current_item_index=0,
            items_total=0,
            banker_pos=None,
            bank_wait_start=None,
            bank_herb_template=None,
            last_deposit_pos=None,
        )


# =========================
# HERBLORE HANDLERS
# =========================

def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for user to start."""
    if should_start:
        print("[WARMUP] Starting herblore macro...")
        return transition_state(state, now, HERB_CHECK_INVENTORY), stats
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
        MENU_MATCH_THRESHOLD,
    )
    
    if is_open:
        print("[CHECK_INVENTORY] Inventory is open - scanning items...")
        return transition_state(state, now, HERB_SCAN_ITEMS), stats
    else:
        print("[CHECK_INVENTORY] Inventory not open - pressing ESC...")
        open_inventory(ser)
        random_delay(0.3, 0.5)
        # Stay in this state to verify it opened
        return state, stats


def handle_scan_items(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor,
    ctx: HerbloreContext,
) -> tuple[AppState, Stats]:
    """Scan inventory for grimy herbs and collect all item positions."""
    items = find_all_templates(
        sct, monitor,
        GRIMY_HERB_TEMPLATE,
        INVENTORY_REGION,
        HERB_ITEM_THRESHOLD,
        use_color=USE_COLOR_MATCHING,
    )
    
    if not items:
        print("[SCAN_ITEMS] No grimy herbs found - looking for banker...")
        return transition_state(state, now, HERB_FIND_BANKER), stats
    
    # Sort items by grid position (row by row, left to right)
    sorted_items = sort_by_grid(items)
    
    # Store all item positions - we will click above each one
    ctx.item_positions = sorted_items
    ctx.current_item_index = 0
    ctx.items_total = len(sorted_items)
    
    # Save the last position for depositing later
    ctx.last_deposit_pos = sorted_items[-1]
    
    print(f"[SCAN_ITEMS] Found {ctx.items_total} grimy herbs (sorted row by row)")
    return transition_state(state, now, HERB_CLEAN_LOOP), stats


def handle_clean_loop(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    ctx: HerbloreContext,
) -> tuple[AppState, Stats]:
    """
    Main herb cleaning loop:
    1. Click ABOVE each item position (items get cleaned)
    2. Move to next item until all items are processed
    """
    if ctx.current_item_index >= len(ctx.item_positions):
        print("[CLEAN_LOOP] All herbs cleaned!")
        return transition_state(state, now, HERB_DONE), increment_cycles(stats)
    
    # Get current item position
    item_pos = ctx.item_positions[ctx.current_item_index]
    
    # Calculate click position ABOVE the item
    click_pos = Point(x=item_pos.x, y=item_pos.y)
    
    remaining = len(ctx.item_positions) - ctx.current_item_index
    print(f"[CLEAN_LOOP] Cleaning herb {ctx.current_item_index + 1}/{ctx.items_total} at ({click_pos.x}, {click_pos.y})")
    
    # Click above the item
    click_point(ser, click_pos)
    random_delay(HERB_CLICK_DELAY_MIN, HERB_CLICK_DELAY_MAX)
    
    # Move to next item
    ctx.current_item_index += 1
    
    return state, increment_actions(stats)


def handle_done(
    state: AppState,
    stats: Stats,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle completion - all items cleaned, proceed to banking."""
    print("[DONE] Herb cleaning complete! Looking for banker...")
    return transition_state(state, now, HERB_FIND_BANKER), stats


def handle_find_banker(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor,
    ctx: HerbloreContext,
) -> tuple[AppState, Stats]:
    """Search for banker NPC by color highlight in the designated game area."""
    banker_pos = find_by_color(
        sct, monitor,
        BANKER_COLOR,
        BANKER_REGION,
        BANKER_COLOR_MIN_AREA,
    )
    
    if banker_pos is None:
        print("[FIND_BANKER] Banker color not found - retrying...")
        random_delay(0.5, 1.0)
        return state, stats
    
    ctx.banker_pos = banker_pos
    print(f"[FIND_BANKER] Found banker by color at ({banker_pos.x}, {banker_pos.y})")
    return transition_state(state, now, HERB_CLICK_BANKER), stats


def handle_click_banker(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    ctx: HerbloreContext,
) -> tuple[AppState, Stats]:
    """Click on the banker NPC to open bank interface."""
    if ctx.banker_pos is None:
        print("[CLICK_BANKER] ERROR: No banker position saved!")
        return transition_state(state, now, HERB_FIND_BANKER), stats
    
    print(f"[CLICK_BANKER] Clicking banker at ({ctx.banker_pos.x}, {ctx.banker_pos.y})")
    click_point(ser, ctx.banker_pos)
    random_delay(config.BANK_CLICK_DELAY_MIN, config.BANK_CLICK_DELAY_MAX)

    # Dialogue flow: space, wait, then option 1
    press_key(ser, config.KEY_CHAT_CONFIRM)
    time.sleep(1.0)
    press_key(ser, config.KEY_CHAT_OPTION_1)
    
    # Start waiting for bank to open
    ctx.bank_wait_start = time.time()
    return transition_state(state, now, HERB_WAIT_BANK), increment_clicks(stats)


def handle_wait_bank(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: HerbloreContext,
) -> tuple[AppState, Stats]:
    """Wait for bank interface to open."""
    if ctx.bank_wait_start is None:
        ctx.bank_wait_start = now
    
    elapsed = now - ctx.bank_wait_start
    
    is_bank_open = template_exists(
        sct, monitor,
        config.BANK_CONTROLS_TEMPLATE,
        BANK_CONTROLS_REGION,
        config.BANK_CONTROLS_MATCH_THRESHOLD,
    )

    if is_bank_open:
        print("[WAIT_BANK] Bank interface detected - banking items...")

        # Deposit cleaned herbs using saved slot position
        if ctx.last_deposit_pos is not None:
            click_point(ser, ctx.last_deposit_pos)
            random_delay(HERB_CLICK_DELAY_MIN, HERB_CLICK_DELAY_MAX)
            stats = increment_clicks(stats)
        else:
            print("[WAIT_BANK] Warning: No last item position saved for deposit")

        # Withdraw grimy herbs from bank (scan entire bank interface)
        if ctx.bank_herb_template is None:
            ctx.bank_herb_template = crop_template(
                load_template(GRIMY_HERB_TEMPLATE, grayscale=not USE_COLOR_MATCHING),
                top=config.BANK_STACK_CROP_TOP_PX,
            )

        herb_pos = find_template(
            sct, monitor,
            ctx.bank_herb_template,
            BANK_INTERFACE_REGION,
            HERB_ITEM_THRESHOLD,
            use_color=USE_COLOR_MATCHING,
        )

        if herb_pos is not None:
            click_point(ser, herb_pos)
            random_delay(HERB_CLICK_DELAY_MIN, HERB_CLICK_DELAY_MAX)
            stats = increment_clicks(stats)
        else:
            print("[WAIT_BANK] No grimy herbs found in bank - returning to warmup")
            ctx.bank_wait_start = None
            return transition_state(state, now, WARMUP), stats

        ctx.bank_wait_start = None
        return transition_state(state, now, HERB_CHECK_INVENTORY), stats

    # Timeout - try clicking banker again
    if elapsed > config.BANK_WAIT_TIMEOUT:
        print(f"[WAIT_BANK] Timeout after {elapsed:.1f}s - retrying banker click")
        ctx.bank_wait_start = None
        return transition_state(state, now, HERB_FIND_BANKER), stats
    
    return state, stats


def process_herblore_state(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: HerbloreContext,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process herblore state machine."""
    
    # Stop always returns to warmup
    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats
    
    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == HERB_CHECK_INVENTORY:
        return handle_check_inventory(state, stats, now, ser, sct, monitor)
    elif state.name == HERB_SCAN_ITEMS:
        return handle_scan_items(state, stats, now, sct, monitor, ctx)
    elif state.name == HERB_CLEAN_LOOP:
        return handle_clean_loop(state, stats, now, ser, ctx)
    elif state.name == HERB_DONE:
        return handle_done(state, stats, now)
    # Banking states
    elif state.name == HERB_FIND_BANKER:
        return handle_find_banker(state, stats, now, sct, monitor, ctx)
    elif state.name == HERB_CLICK_BANKER:
        return handle_click_banker(state, stats, now, ser, ctx)
    elif state.name == HERB_WAIT_BANK:
        return handle_wait_bank(state, stats, now, ser, sct, monitor, ctx)
    
    return state, stats


# =========================
# HERBLORE MAIN LOOP
# =========================

def print_status(state: AppState, stats: Stats, ctx: HerbloreContext) -> None:
    """Print current herblore status."""
    remaining = max(0, len(ctx.item_positions) - ctx.current_item_index)
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Items remaining: {remaining}/{ctx.items_total}")
    print(f"Clicks: {stats.clicks} | Cleaned: {stats.actions} | Cycles: {stats.cycles}")
    print("=" * 40)


def create_herblore_state() -> tuple[AppState, Stats, HerbloreContext]:
    """Create initial state, stats, and context for herblore."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_HERB_STATES),
        HerbloreContext.create(),
    )


def run_herblore(
    # Serial connection
    ser,
    # Keyboard input function (returns should_start, should_stop)
    check_keyboard: callable,
    # Debug options
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run the herblore macro loop.
    
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
    
    # Initialize herblore-specific state
    state, stats, ctx = create_herblore_state()

    # Preload cropped herb template for bank matching
    ctx.bank_herb_template = crop_template(
        load_template(GRIMY_HERB_TEMPLATE, grayscale=not USE_COLOR_MATCHING),
        top=config.BANK_STACK_CROP_TOP_PX,
    )
    
    last_loop_time = time.time()
    last_status_print = 0
    
    # Print banner
    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - HERBLORE")
    print("=" * 50)
    print(f"Inventory: ({config.INVENTORY_X_START}, {config.INVENTORY_Y_START}) to ({config.INVENTORY_X_END}, {config.INVENTORY_Y_END})")
    print("")
    print("Controls:")
    print("  Page Up   = Start herb cleaning")
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
        
        # Process herblore state machine
        old_state = state.name
        state, stats = process_herblore_state(
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
        elif state.name == HERB_DONE:
            time.sleep(0.5)  # Brief pause before banking
        elif state.name == HERB_WAIT_BANK:
            time.sleep(0.2)  # Moderate polling while waiting for bank
        elif state.name in (HERB_FIND_BANKER,):
            time.sleep(0.3)  # Moderate polling while searching for banker
        else:
            time.sleep(0.02)  # Very fast during active cleaning
    
    return state, stats
