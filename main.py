import time
import pyautogui

import config
from state import (
    AppState,
    Stats,
    WAITING,
    VERIFY,
    STARTING,
    COLLECTING,
    COOLDOWN,
    DROPPING,
    make_initial_state,
    make_initial_stats,
    transition_state,
    accumulate_state_time,
    increment_clicks,
    increment_verify_fail,
    increment_resets,
)
from capture import (
    load_template,
    create_screen_capturer,
    grab_screen,
    crop_frame,
    preprocess_crop,
    match_template,
    MatchResult,
    compute_target_y,
    save_match_debug,
    validate_template_size,
)
from serial_io import (
    open_serial,
    send_move,
    send_click,
    send_shift_click,
    compute_hesitation,
)
from debug import (
    ensure_debug_dir,
    should_save_debug,
)
from inventory import (
    load_inventory_templates,
    analyze_inventory,
    compute_random_click_position,
    is_inventory_full,
    InventoryState,
)


def handle_waiting(
    state: AppState,
    stats: Stats,
    matched: bool,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle WAITING state - looking for initial match."""
    if matched:
        return transition_state(state, now, VERIFY, verify_count=1), stats
    return state, stats


def handle_verify(
    state: AppState,
    stats: Stats,
    matched: bool,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle VERIFY state - confirming consecutive matches."""
    if matched:
        new_count = state.verify_count + 1
        if new_count >= config.VERIFY_REQUIRED:
            return transition_state(state, now, STARTING, verify_count=new_count), stats
        return transition_state(state, now, VERIFY, verify_count=new_count), stats
    else:
        return (
            transition_state(state, now, WAITING, verify_count=0),
            increment_verify_fail(stats),
        )


def handle_starting(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
) -> tuple[AppState, Stats]:
    """Handle STARTING state - move and click."""
    mx, my = pyautogui.position()
    target_y = compute_target_y(config.CENTER_Y, config.CROP_SIZE, config.Y_MARGIN)

    dx = config.CENTER_X - mx
    dy = target_y - my

    send_move(ser, dx, dy)

    hesitation = compute_hesitation(
        match_result.confidence,
        config.MATCH_THRESHOLD,
        config.HESITATION_MIN,
        config.HESITATION_MAX,
    )
    time.sleep(hesitation)

    send_click(ser)

    return (
        transition_state(state, now, COLLECTING),
        increment_clicks(stats),
    )


def handle_collecting(
    state: AppState,
    stats: Stats,
    matched: bool,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle COLLECTING state - waiting for collection to end."""
    if not matched:
        return transition_state(state, now, COOLDOWN), stats
    elif now - state.since > config.COLLECTING_TIMEOUT:
        return (
            transition_state(state, now, COOLDOWN),
            increment_resets(stats),
        )
    return state, stats


def handle_cooldown(
    state: AppState,
    stats: Stats,
    now: float,
) -> tuple[AppState, Stats]:
    """Handle COOLDOWN state - waiting before resuming."""
    if now - state.since >= config.COOLDOWN_TIME:
        return transition_state(state, now, WAITING, verify_count=0), stats
    return state, stats


def handle_dropping(
    state: AppState,
    stats: Stats,
    now: float,
    sct,
    monitor: dict,
    bg_template,
    resource_template,
    ser,
) -> tuple[AppState, Stats]:
    """Handle DROPPING state - drop all resources from inventory."""
    inventory_state = analyze_inventory(sct, monitor, bg_template, resource_template)

    # Count cells with items (even if not identified as resources)
    cells_with_items = sum(1 for c in inventory_state.cells if c.has_item)

    print(f"[INVENTORY] Cells with items: {cells_with_items}, Resources identified: {len(inventory_state.resource_cells)}")

    if not inventory_state.resource_cells:
        # No resources found - likely a detection issue. Go to cooldown to avoid infinite loop.
        print("[INVENTORY] No resources to drop! Possible detection issue. Entering cooldown.")
        return transition_state(state, now, COOLDOWN), stats

    print(f"[INVENTORY] Dropping {len(inventory_state.resource_cells)} resource(s)...")

    for cell in inventory_state.resource_cells:
        click_x, click_y = compute_random_click_position(cell)
        print(f"  Dropping at cell ({cell.row}, {cell.col}) -> ({click_x}, {click_y})")
        send_shift_click(ser, click_x, click_y)
        time.sleep(0.5)

    print("[INVENTORY] Done dropping, returning to WAITING")
    return transition_state(state, now, WAITING, verify_count=0), stats


def process_state_machine(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
    sct=None,
    monitor=None,
    bg_template=None,
    resource_template=None,
    inventory_full: bool = False,
) -> tuple[AppState, Stats]:
    """Process state machine and return new state and stats."""
    matched = match_result.matched

    if state.name == WAITING:
        # Check inventory first - if full, go drop resources
        if inventory_full:
            return transition_state(state, now, DROPPING), stats
        return handle_waiting(state, stats, matched, now)
    elif state.name == VERIFY:
        return handle_verify(state, stats, matched, now)
    elif state.name == STARTING:
        return handle_starting(state, stats, match_result, now, ser)
    elif state.name == COLLECTING:
        return handle_collecting(state, stats, matched, now)
    elif state.name == COOLDOWN:
        return handle_cooldown(state, stats, now)
    elif state.name == DROPPING:
        return handle_dropping(
            state, stats, now, sct, monitor, bg_template, resource_template, ser
        )

    return state, stats


def main() -> None:
    """Main entry point."""
    # Initialize
    if config.DEBUG:
        ensure_debug_dir(config.DEBUG_DIR)

    template = load_template(config.TEMPLATE_PATH)

    # Validate template size vs crop size (critical for matching to work)
    validate_template_size(template, config.CROP_SIZE)

    sct, monitor = create_screen_capturer()
    ser = open_serial(config.SERIAL_PORT, config.BAUD_RATE)

    # Load inventory templates
    try:
        resource_template, bg_template = load_inventory_templates()
        inventory_enabled = True
        print("Inventory management enabled")
    except RuntimeError as e:
        print(f"Inventory management disabled: {e}")
        inventory_enabled = False
        resource_template = None
        bg_template = None

    state = make_initial_state()
    stats = make_initial_stats()
    last_loop_time = time.time()

    print("Started detection loop")
    print(f"Initial state: {state.name}")

    while True:
        now = time.time()

        # Track state time
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now

        # Capture and match
        frame = grab_screen(sct, monitor)
        crop = crop_frame(frame, config.CENTER_X, config.CENTER_Y, config.CROP_SIZE)
        gray = preprocess_crop(crop)
        match_result = match_template(gray, template, config.MATCH_THRESHOLD)

        print(f"[{state.name}] confidence={match_result.confidence:.3f}")

        # Debug captures - save detailed match debug when not matching
        if should_save_debug(config.DEBUG, config.DEBUG_SAVE_MODE, match_result.matched):
            save_match_debug(
                config.DEBUG_DIR,
                match_result.gray,
                template,
                match_result.result,
                match_result.confidence,
                match_result.max_loc,
                config.MATCH_THRESHOLD,
            )

        # Check if inventory is full (only scan last cell)
        inventory_full = False
        if inventory_enabled and state.name == WAITING:
            inventory_full = is_inventory_full(sct, monitor, bg_template)

        # State machine
        state, stats = process_state_machine(
            state, stats, match_result, now, ser,
            sct=sct,
            monitor=monitor,
            bg_template=bg_template,
            resource_template=resource_template,
            inventory_full=inventory_full,
        )

        # Periodic stats log
        if int(now) % 30 == 0:
            print("---- STATS ----")
            print(f"clicks: {stats.clicks}")
            print(f"verify_fail: {stats.verify_fail}")
            print(f"resets: {stats.resets}")
            print(f"state_time: {stats.state_time}")
            print("----------------")

        time.sleep(config.SCAN_INTERVAL)


if __name__ == "__main__":
    main()
