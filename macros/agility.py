"""
Agility macro for screen2serial bot.

State machine:
    WARMUP -> AGI_CLICK -> (loop: click fixed point, 2s delay) -> ...
    Any state -> (Page Down) -> WARMUP

This macro repeatedly clicks a fixed screen position (1425, 132) with a 2 second
delay between clicks. Use for simple agility obstacle or similar.
"""

import time

from logic import (
    AppState,
    Stats,
    WARMUP,
    Point,
    make_initial_state,
    make_initial_stats,
    transition_state,
    accumulate_state_time,
    increment_clicks,
    click_point,
)


# =========================
# AGILITY STATES
# =========================
AGI_CLICK = "agi_click"

ALL_AGI_STATES = (WARMUP, AGI_CLICK)


# =========================
# AGILITY CONFIG
# =========================
AGI_CLICK_X = 1425
AGI_CLICK_Y = 132
AGI_DELAY_SECONDS = 1.5

AGI_CLICK_POINT = Point(x=AGI_CLICK_X, y=AGI_CLICK_Y)


# =========================
# AGILITY HANDLERS
# =========================

def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for user to start."""
    if should_start:
        print("[WARMUP] Starting agility macro...")
        return transition_state(state, now, AGI_CLICK), stats
    return state, stats


def handle_agi_click(
    state: AppState,
    stats: Stats,
    ser,
) -> tuple[AppState, Stats]:
    """Click fixed point (1425, 132) and wait 2 seconds."""
    print(f"[AGI_CLICK] Clicking ({AGI_CLICK_X}, {AGI_CLICK_Y})")
    click_point(ser, AGI_CLICK_POINT)
    time.sleep(AGI_DELAY_SECONDS)
    return state, increment_clicks(stats)


def process_agility_state(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process agility state machine."""

    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats

    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == AGI_CLICK:
        return handle_agi_click(state, stats, ser)

    return state, stats


# =========================
# AGILITY MAIN LOOP
# =========================

def print_status(state: AppState, stats: Stats) -> None:
    """Print current agility status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Clicks: {stats.clicks}")
    print("=" * 40)


def create_agility_state() -> tuple[AppState, Stats]:
    """Create initial state and stats for agility."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_AGI_STATES),
    )


def run_agility(
    ser,
    check_keyboard: callable,
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run the agility macro loop.

    Clicks (1425, 132) every 2 seconds. Page Up to start, Page Down to stop.

    Args:
        ser: Serial connection for mouse control
        check_keyboard: Function that returns (should_start, should_stop) tuple
        debug: Unused; kept for signature compatibility with other macros

    Returns:
        Final (state, stats) tuple when the loop exits
    """
    state, stats = create_agility_state()
    last_loop_time = time.time()
    last_status_print = 0

    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - AGILITY")
    print("=" * 50)
    print(f"Click: ({AGI_CLICK_X}, {AGI_CLICK_Y}) every {AGI_DELAY_SECONDS}s")
    print("")
    print("Controls:")
    print("  Page Up   = Start")
    print("  Page Down = Stop (return to warmup)")
    print("")
    print("State: WARMUP - Press Page Up to start")
    print("=" * 50)
    print("")

    while True:
        now = time.time()

        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now

        should_start, should_stop = check_keyboard()

        old_state = state.name
        state, stats = process_agility_state(
            state, stats, now, ser, should_start, should_stop
        )

        if state.name != old_state:
            print_status(state, stats)
        elif int(now) - last_status_print >= 30:
            print_status(state, stats)
            last_status_print = int(now)

        if state.name == WARMUP:
            time.sleep(0.1)
        else:
            # AGI_CLICK: handler already sleeps 2s, so short poll after
            time.sleep(0.05)

    return state, stats
