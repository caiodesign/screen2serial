"""
Thieving macro for screen2serial bot.

State machine:
    WARMUP -> PICK_FOOD (find yellow, click, delay 2.8–3.1s, loop) ->
    when 16 food collected (4x4) -> DROP_INVENTORY (shift+click each of 4x7 slots) ->
    back to PICK_FOOD (reset).

    Any state -> (PageDown) -> WARMUP

Collects food by clicking yellow highlights; after 16 picks, shift-clicks
each inventory slot (4 columns x 7 rows) to drop/use, then repeats.
"""

import time
from dataclasses import dataclass

import config

from logic import (
    AppState,
    Stats,
    WARMUP,
    make_initial_state,
    make_initial_stats,
    transition_state,
    accumulate_state_time,
    increment_actions,
    increment_cycles,
    create_screen_capturer,
    Region,
    Point,
    ColorRange,
    find_closest_by_color,
    click_point,
    random_delay,
    drop_items,
)

# =========================
# THIEVING STATES
# =========================
THIEF_PICK_FOOD = "thief_pick_food"
THIEF_DROP_INVENTORY = "thief_drop_inventory"

ALL_THIEF_STATES = (
    WARMUP,
    THIEF_PICK_FOOD,
    THIEF_DROP_INVENTORY,
)

# =========================
# THIEVING CONFIG
# =========================
# Yellow highlight (e.g. pickpocket target) – BGR: (0, 255, 255)
# #FFFF00 / #FFFFFF00 -> R=255 G=255 B=0 -> BGR (0, 255, 255)
FOOD_COLOR: ColorRange = ((0, 250, 250), (15, 255, 255))
FOOD_COLOR_MIN_AREA = 30

# Delay between each pick (one food per click)
PICK_DELAY_MIN = 2.8
PICK_DELAY_MAX = 3.1

# Food count before we run drop inventory (4 columns x 4 rows = 16)
FOOD_SLOTS_TO_FILL = 4 * 4  # 16

# Inventory grid: 4 columns x 7 rows
INVENTORY_COLS = 4
INVENTORY_ROWS = 7

# Search region (game area, not inventory)
PICK_REGION = Region(
    x_start=config.REGION_X_START,
    y_start=config.REGION_Y_START,
    x_end=config.REGION_X_END,
    y_end=config.REGION_Y_END,
)

INVENTORY_REGION = Region(
    x_start=config.INVENTORY_X_START,
    y_start=config.INVENTORY_Y_START,
    x_end=config.INVENTORY_X_END,
    y_end=config.INVENTORY_Y_END,
)


@dataclass
class ThievingContext:
    """Mutable context for thieving macro."""
    food_picked: int  # Number of food items picked this cycle

    @classmethod
    def create(cls) -> "ThievingContext":
        return cls(food_picked=0)


def _inventory_slot_centers() -> list[Point]:
    """Return center Point for each inventory slot (4 cols x 7 rows), row by row."""
    x_start = INVENTORY_REGION.x_start
    y_start = INVENTORY_REGION.y_start
    w = INVENTORY_REGION.x_end - x_start
    h = INVENTORY_REGION.y_end - y_start
    slot_w = w // INVENTORY_COLS
    slot_h = h // INVENTORY_ROWS
    points: list[Point] = []
    for row in range(INVENTORY_ROWS):
        for col in range(INVENTORY_COLS):
            cx = x_start + col * slot_w + slot_w // 2
            cy = y_start + row * slot_h + slot_h // 2
            points.append(Point(x=cx, y=cy))
    return points


# =========================
# THIEVING HANDLERS
# =========================

def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP – wait for user to start."""
    if should_start:
        print("[WARMUP] Starting thieving macro...")
        return transition_state(state, now, THIEF_PICK_FOOD), stats
    return state, stats


def handle_pick_food(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: ThievingContext,
) -> tuple[AppState, Stats]:
    """Find yellow (food) highlight, click it, delay 2.8–3.1s, then loop. After 16 picks go to drop."""
    if ctx.food_picked >= FOOD_SLOTS_TO_FILL:
        print(f"[PICK_FOOD] Collected {ctx.food_picked} food – switching to drop inventory")
        return transition_state(state, now, THIEF_DROP_INVENTORY), stats

    screen_center = (
        (PICK_REGION.x_start + PICK_REGION.x_end) // 2,
        (PICK_REGION.y_start + PICK_REGION.y_end) // 2,
    )
    pos = find_closest_by_color(
        sct, monitor,
        FOOD_COLOR,
        PICK_REGION,
        screen_center,
        FOOD_COLOR_MIN_AREA,
    )

    if pos is None:
        print("[PICK_FOOD] No yellow (food) found – retrying...")
        random_delay(0.4, 0.7)
        return state, stats

    print(f"[PICK_FOOD] Clicking food at ({pos.x}, {pos.y}) ({ctx.food_picked + 1}/{FOOD_SLOTS_TO_FILL})")
    click_point(ser, pos)
    ctx.food_picked += 1
    random_delay(PICK_DELAY_MIN, PICK_DELAY_MAX)
    return state, increment_actions(stats)


def handle_drop_inventory(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    ctx: ThievingContext,
) -> tuple[AppState, Stats]:
    """Shift+left click each inventory slot (4x7), then reset and go back to picking."""
    slots = _inventory_slot_centers()
    print(f"[DROP_INVENTORY] Shift-clicking {len(slots)} inventory slots...")
    dropped = drop_items(
        ser,
        slots,
        click_delay=config.DROP_CLICK_DELAY,
    )
    print(f"[DROP_INVENTORY] Done. Dropped {dropped} slots. Resetting pick count.")
    ctx.food_picked = 0
    return transition_state(state, now, THIEF_PICK_FOOD), increment_cycles(stats)


def process_thieving_state(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    ctx: ThievingContext,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process thieving state machine."""
    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats

    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == THIEF_PICK_FOOD:
        return handle_pick_food(state, stats, now, ser, sct, monitor, ctx)
    elif state.name == THIEF_DROP_INVENTORY:
        return handle_drop_inventory(state, stats, now, ser, ctx)

    return state, stats


# =========================
# THIEVING MAIN LOOP
# =========================

def print_status(state: AppState, stats: Stats, ctx: ThievingContext) -> None:
    """Print current thieving status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Food picked this cycle: {ctx.food_picked}/{FOOD_SLOTS_TO_FILL}")
    print(f"Actions: {stats.actions} | Cycles: {stats.cycles}")
    print("=" * 40)


def create_thieving_state() -> tuple[AppState, Stats, ThievingContext]:
    """Create initial state, stats, and context for thieving."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_THIEF_STATES),
        ThievingContext.create(),
    )


def run_thieving(
    ser,
    check_keyboard: callable,
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run the thieving macro loop.

    Collects food by clicking yellow highlights; after 16 picks,
    shift-clicks each inventory slot (4x7), then repeats.
    """
    sct, monitor = create_screen_capturer()
    state, stats, ctx = create_thieving_state()

    last_loop_time = time.time()
    last_status_print = 0

    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - THIEVING")
    print("=" * 50)
    print(f"Pick region: ({PICK_REGION.x_start}, {PICK_REGION.y_start}) to ({PICK_REGION.x_end}, {PICK_REGION.y_end})")
    print(f"Inventory: 4 cols x 7 rows, drop after {FOOD_SLOTS_TO_FILL} food")
    print("")
    print("Controls:")
    print("  Page Up   = Start")
    print("  Page Down = Stop (return to warmup)")
    print("")
    print("State: WARMUP – Press Page Up to start")
    print("=" * 50)
    print("")

    while True:
        now = time.time()
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now

        should_start, should_stop = check_keyboard()
        old_state = state.name
        state, stats = process_thieving_state(
            state, stats, now, ser, sct, monitor, ctx,
            should_start, should_stop,
        )

        if state.name != old_state:
            print_status(state, stats, ctx)
        elif int(now) - last_status_print >= 30:
            print_status(state, stats, ctx)
            last_status_print = int(now)

        if state.name == WARMUP:
            time.sleep(0.1)
        elif state.name == THIEF_DROP_INVENTORY:
            time.sleep(0.05)
        else:
            time.sleep(0.02)

    return state, stats
