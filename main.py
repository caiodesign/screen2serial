from re import M
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
    grab_region,
    preprocess_crop,
    match_template,
    MatchResult,
    validate_template_size,
    show_live_windows,
)
from serial_io import (
    open_serial,
    send_move,
    send_click,
    compute_hesitation,
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
    template_h: int,
    template_w: int,
) -> tuple[AppState, Stats]:
    """Handle STARTING state - move and click at the matched location."""
    mx, my = pyautogui.position()
    
    # Calculate target position based on match location + region offset
    # match_result.max_loc is relative to the captured region
    match_x, match_y = match_result.max_loc
    
    # Target is center of the matched area, offset by the region start coordinates
    # Add 30 pixels below to avoid mouse entering the detection zone
    target_x = config.REGION_X_START + match_x + (template_w // 2)
    target_y = config.REGION_Y_START + match_y + (template_h // 2) + 100
    
    dx = target_x - mx
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


def process_state_machine(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
    template_h: int,
    template_w: int,
) -> tuple[AppState, Stats]:
    """Process state machine and return new state and stats."""
    matched = match_result.matched

    if state.name == WAITING:
        return handle_waiting(state, stats, matched, now)
    elif state.name == VERIFY:
        return handle_verify(state, stats, matched, now)
    elif state.name == STARTING:
        return handle_starting(state, stats, match_result, now, ser, template_h, template_w)
    elif state.name == COLLECTING:
        return handle_collecting(state, stats, matched, now)
    elif state.name == COOLDOWN:
        return handle_cooldown(state, stats, now)

    return state, stats


def main() -> None:
    """Main entry point."""
    template = load_template(config.TEMPLATE_PATH)
    template_h, template_w = template.shape[:2]

    # Calculate region dimensions
    region_width = config.REGION_X_END - config.REGION_X_START
    region_height = config.REGION_Y_END - config.REGION_Y_START

    # Validate template size vs region size (critical for matching to work)
    validate_template_size(template, region_width, region_height)

    sct, monitor = create_screen_capturer()
    ser = open_serial(config.SERIAL_PORT, config.BAUD_RATE)

    state = make_initial_state()
    stats = make_initial_stats()
    last_loop_time = time.time()

    print(f"Region: ({config.REGION_X_START}, {config.REGION_Y_START}) to ({config.REGION_X_END}, {config.REGION_Y_END})")
    print(f"Region size: {region_width}x{region_height}")
    print("Started detection loop - Press 'q' in the window to quit")
    print(f"Initial state: {state.name}")

    while True:
        now = time.time()

        # Track state time
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now

        # Capture the region
        frame = grab_region(
            sct, monitor,
            config.REGION_X_START, config.REGION_Y_START,
            config.REGION_X_END, config.REGION_Y_END,
        )
        gray = preprocess_crop(frame)
        match_result = match_template(gray, template, config.MATCH_THRESHOLD)

        if config.DEBUG:
            print(f"[{state.name}] confidence={match_result.confidence:.3f} at {match_result.max_loc}")

            # Show live windows with captured region and template
            if not show_live_windows(gray, template, match_result, config.MATCH_THRESHOLD):
                print("Quitting...")
                break

        # State machine
        state, stats = process_state_machine(
            state, stats, match_result, now, ser, template_h, template_w
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
