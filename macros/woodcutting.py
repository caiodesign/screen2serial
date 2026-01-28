"""
Woodcutting macro for screen2serial bot.

State machine:
    WARMUP -> (PageUp) -> SEARCHING -> (found) -> COLLECTING -> (threshold drops) -> DROPPING -> SEARCHING
    Any state -> (PageDown) -> WARMUP

This macro is fully self-contained with its own:
- State definitions
- Handler functions
- Main loop
"""

import time
import numpy as np

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
    grab_region,
    preprocess_crop,
    match_template,
    MatchResult,
    show_live_windows,
    # Serial
    compute_hesitation,
    # Vision
    Region,
    find_all_templates,
    sort_by_position,
    # Actions
    click_at,
    drop_items,
    random_delay,
)
import config


# =========================
# WOODCUTTING STATES
# =========================
WC_SEARCHING = "wc_searching"
WC_COLLECTING = "wc_collecting"
WC_DROPPING = "wc_dropping"

ALL_WC_STATES = (WARMUP, WC_SEARCHING, WC_COLLECTING, WC_DROPPING)


# =========================
# WOODCUTTING CONFIG
# =========================
INVENTORY_REGION = Region(
    x_start=config.INVENTORY_X_START,
    y_start=config.INVENTORY_Y_START,
    x_end=config.INVENTORY_X_END,
    y_end=config.INVENTORY_Y_END,
)


# =========================
# WOODCUTTING HANDLERS
# =========================

def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for user to start."""
    if should_start:
        print("[WARMUP] Starting search...")
        return transition_state(state, now, WC_SEARCHING), stats
    return state, stats


def handle_searching(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
    template_h: int,
    template_w: int,
) -> tuple[AppState, Stats]:
    """Handle SEARCHING state - looking for trees."""
    if match_result.matched:
        print(f"[SEARCHING] Tree found! Confidence: {match_result.confidence:.3f}")
        
        # Calculate target position (center of matched area + offset below)
        match_x, match_y = match_result.max_loc
        target_x = config.REGION_X_START + match_x + (template_w // 2)
        target_y = config.REGION_Y_START + match_y + (template_h // 2) + 100
        
        # Hesitate based on confidence
        hesitation = compute_hesitation(
            match_result.confidence,
            config.MATCH_THRESHOLD,
            config.HESITATION_MIN,
            config.HESITATION_MAX,
        )
        random_delay(hesitation * 0.8, hesitation * 1.2)
        
        # Click at target position
        click_at(ser, target_x, target_y, double_click=True)
        
        return (
            transition_state(state, now, WC_COLLECTING, last_scan=now),
            increment_clicks(stats),
        )
    
    return state, stats


def handle_collecting(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
) -> tuple[AppState, Stats]:
    """
    Handle COLLECTING state - monitor tree while cutting.
    
    Scans every COLLECTING_SCAN_INTERVAL seconds.
    When tree disappears, transition to DROPPING.
    """
    last_scan = state.data.get("last_scan", 0.0)
    time_since_last_scan = now - last_scan
    
    if time_since_last_scan >= config.COLLECTING_SCAN_INTERVAL:
        # Update last scan time
        new_state = update_state_data(state, last_scan=now)
        
        if not match_result.matched:
            print(f"[COLLECTING] Tree gone (confidence: {match_result.confidence:.3f}) - Moving to drop")
            return (
                transition_state(state, now, WC_DROPPING),
                increment_cycles(stats),
            )
        else:
            if config.DEBUG:
                print(f"[COLLECTING] Still cutting... (confidence: {match_result.confidence:.3f})")
        
        return new_state, stats
    
    return state, stats


def handle_dropping(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    resource_template: np.ndarray,
) -> tuple[AppState, Stats]:
    """
    Handle DROPPING state - find and drop all logs in inventory.
    """
    print("[DROPPING] Scanning inventory for logs...")
    
    # Find all logs in inventory
    items = find_all_templates(
        sct, monitor,
        resource_template,
        INVENTORY_REGION,
        config.INVENTORY_RESOURCE_THRESHOLD,
    )
    
    if not items:
        print("[DROPPING] No logs found - Back to searching")
        return transition_state(state, now, WC_SEARCHING), stats
    
    print(f"[DROPPING] Found {len(items)} logs - Dropping...")
    
    # Sort items for efficient dropping
    sorted_items = sort_by_position(items)
    
    # Drop all items
    dropped_count = drop_items(
        ser,
        sorted_items,
        click_delay=config.DROP_CLICK_DELAY,
        move_delay=config.DROP_MOVE_DELAY,
    )
    
    print(f"[DROPPING] Dropped {dropped_count} logs - Back to searching")
    
    return (
        transition_state(state, now, WC_SEARCHING),
        increment_actions(stats, dropped_count),
    )


def process_woodcutting_state(
    state: AppState,
    stats: Stats,
    match_result: MatchResult,
    now: float,
    ser,
    sct,
    monitor,
    template_h: int,
    template_w: int,
    resource_template,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process woodcutting state machine."""
    
    # Stop always returns to warmup
    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats
    
    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == WC_SEARCHING:
        return handle_searching(state, stats, match_result, now, ser, template_h, template_w)
    elif state.name == WC_COLLECTING:
        return handle_collecting(state, stats, match_result, now)
    elif state.name == WC_DROPPING:
        return handle_dropping(state, stats, now, ser, sct, monitor, resource_template)
    
    return state, stats


# =========================
# WOODCUTTING MAIN LOOP
# =========================

def print_status(state: AppState, stats: Stats) -> None:
    """Print current woodcutting status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Clicks: {stats.clicks} | Drops: {stats.actions} | Cycles: {stats.cycles}")
    print("=" * 40)


def create_woodcutting_state() -> tuple[AppState, Stats]:
    """Create initial state and stats for woodcutting."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_WC_STATES),
    )


def run_woodcutting(
    # Screen capture
    sct,
    monitor,
    # Serial connection
    ser,
    # Templates
    template: np.ndarray,
    resource_template: np.ndarray | None,
    # Region config
    region_x_start: int,
    region_y_start: int,
    region_x_end: int,
    region_y_end: int,
    # Matching config
    match_threshold: float,
    search_scan_interval: float,
    # Keyboard input function (returns should_start, should_stop)
    check_keyboard: callable,
    # Debug options
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run the woodcutting macro loop.
    
    Args:
        sct: Screen capture context (mss instance)
        monitor: Monitor info for screen capture
        ser: Serial connection for mouse control
        template: Template image for tree detection
        resource_template: Template for log detection in inventory (optional)
        region_x_start, region_y_start, region_x_end, region_y_end: Detection region
        match_threshold: Confidence threshold for template matching
        search_scan_interval: How often to scan while searching (seconds)
        check_keyboard: Function that returns (should_start, should_stop) tuple
        debug: Enable debug mode with visual windows
        
    Returns:
        Final (state, stats) tuple when the loop exits
    """
    # Initialize woodcutting-specific state
    state, stats = create_woodcutting_state()
    
    template_h, template_w = template.shape[:2]
    last_loop_time = time.time()
    last_status_print = 0
    
    while True:
        now = time.time()
        
        # Track state time
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now
        
        # Check keyboard input
        should_start, should_stop = check_keyboard()
        
        # Capture and match (only when not in warmup)
        match_result = None
        if state.name != WARMUP:
            frame = grab_region(
                sct, monitor,
                region_x_start, region_y_start,
                region_x_end, region_y_end,
            )
            gray = preprocess_crop(frame)
            match_result = match_template(gray, template, match_threshold)
            
            if debug:
                print(f"[{state.name}] confidence={match_result.confidence:.3f} at {match_result.max_loc}")
                
                if not show_live_windows(gray, template, match_result, match_threshold):
                    print("Quitting...")
                    break
        
        # Create dummy match result for warmup state
        if match_result is None:
            match_result = MatchResult(
                gray=np.array([]),
                result=np.array([]),
                confidence=0.0,
                matched=False,
                max_loc=(0, 0),
            )
        
        # Process woodcutting state machine
        old_state = state.name
        state, stats = process_woodcutting_state(
            state, stats, match_result, now, ser, sct, monitor,
            template_h, template_w, resource_template,
            should_start, should_stop,
        )
        
        # Print status on state change or every 30 seconds
        if state.name != old_state:
            print_status(state, stats)
        elif int(now) - last_status_print >= 30:
            print_status(state, stats)
            last_status_print = int(now)
        
        # Determine scan interval based on state
        if state.name == WARMUP:
            time.sleep(0.1)  # Fast polling for keyboard in warmup
        elif state.name == WC_SEARCHING:
            time.sleep(search_scan_interval)
        elif state.name == WC_COLLECTING:
            time.sleep(0.1)  # Fast loop, actual scan interval handled in handler
        elif state.name == WC_DROPPING:
            pass  # No sleep, dropping handles its own timing
    
    return state, stats
