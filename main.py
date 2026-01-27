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
    grab_screen,
    crop_frame,
    preprocess_crop,
    match_template,
    MatchResult,
    compute_target_y,
)
from serial_io import (
    open_serial,
    send_move,
    send_click,
    compute_hesitation,
)
from debug import (
    ensure_debug_dir,
    should_save_debug,
    make_debug_base_path,
    save_debug_captures,
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


def process_state_machine(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
) -> tuple[AppState, Stats]:
    """Process state machine and return new state and stats."""
    matched = match_result.matched

    if state.name == WAITING:
        return handle_waiting(state, stats, matched, now)
    elif state.name == VERIFY:
        return handle_verify(state, stats, matched, now)
    elif state.name == STARTING:
        return handle_starting(state, stats, match_result, now, ser)
    elif state.name == COLLECTING:
        return handle_collecting(state, stats, matched, now)
    elif state.name == COOLDOWN:
        return handle_cooldown(state, stats, now)

    return state, stats


def main() -> None:
    """Main entry point."""
    # Initialize
    if config.DEBUG:
        ensure_debug_dir(config.DEBUG_DIR)

    template = load_template(config.TEMPLATE_PATH)
    sct, monitor = create_screen_capturer()
    ser = open_serial(config.SERIAL_PORT, config.BAUD_RATE)

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

        # Debug captures
        if should_save_debug(config.DEBUG, config.DEBUG_SAVE_MODE, match_result.matched):
            base_path = make_debug_base_path(
                config.DEBUG_DIR, state.name, match_result.confidence
            )
            save_debug_captures(
                base_path,
                match_result.gray,
                template,
                match_result.result,
                state.name,
                match_result.confidence,
                match_result.matched,
            )

        # State machine
        state, stats = process_state_machine(state, stats, match_result, now, ser)

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
