"""
Main entry point for the screen2serial bot.

State machine:
    WARMUP -> (F1) -> SEARCHING -> (found) -> COLLECTING -> (threshold drops) -> DROPPING -> SEARCHING
    Any state -> (F2) -> WARMUP
"""

import time
import numpy as np
import pyautogui
from pynput import keyboard

import config
from state import (
    AppState,
    Stats,
    WARMUP,
    SEARCHING,
    COLLECTING,
    DROPPING,
    make_initial_state,
    make_initial_stats,
    transition_state,
    accumulate_state_time,
    increment_clicks,
    increment_drops,
    increment_resources,
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
    send_shift_click,
    compute_hesitation,
)
from inventory import (
    find_resources_in_inventory,
    get_drop_order,
)


# Global flag for keyboard control
_should_start = False
_should_stop = False


def on_key_press(key):
    """Handle keyboard press events."""
    global _should_start, _should_stop
    
    try:
        # Check for Page Up/Page Down keys
        if key == keyboard.Key.page_up:
            _should_start = True
        elif key == keyboard.Key.page_down:
            _should_stop = True
    except AttributeError:
        pass


def check_keyboard_flags() -> tuple[bool, bool]:
    """Check and reset keyboard flags. Returns (should_start, should_stop)."""
    global _should_start, _should_stop
    start = _should_start
    stop = _should_stop
    _should_start = False
    _should_stop = False
    return start, stop


def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for F1 to start."""
    if should_start:
        print("[WARMUP] F1 pressed - Starting search...")
        return transition_state(state, now, SEARCHING), stats
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
    """Handle SEARCHING state - looking for resources."""
    if match_result.matched:
        print(f"[SEARCHING] Resource found! Confidence: {match_result.confidence:.3f}")
        
        # Calculate target position
        mx, my = pyautogui.position()
        match_x, match_y = match_result.max_loc
        
        # Target is center of the matched area, offset by region start
        # Add offset below to avoid mouse entering detection zone
        target_x = config.REGION_X_START + match_x + (template_w // 2)
        target_y = config.REGION_Y_START + match_y + (template_h // 2) + 100
        
        dx = target_x - mx
        dy = target_y - my
        
        # Move mouse and click
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
            transition_state(state, now, COLLECTING, last_scan=now),
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
    Handle COLLECTING state - monitor resource while collecting.
    
    Scans every COLLECTING_SCAN_INTERVAL seconds.
    When confidence drops below threshold, transition to DROPPING.
    """
    # Check if it's time to scan
    time_since_last_scan = now - state.last_scan
    
    if time_since_last_scan >= config.COLLECTING_SCAN_INTERVAL:
        # Update last scan time
        new_state = transition_state(state, state.since, state.name, last_scan=now)
        
        if not match_result.matched:
            print(f"[COLLECTING] Resource gone (confidence: {match_result.confidence:.3f}) - Moving to drop phase")
            return (
                transition_state(state, now, DROPPING),
                increment_resources(stats),
            )
        else:
            if config.DEBUG:
                print(f"[COLLECTING] Still collecting... (confidence: {match_result.confidence:.3f})")
        
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
    Handle DROPPING state - find and drop all resources in inventory.
    
    1. Scan inventory for resources
    2. Shift+click each resource with DROP_CLICK_DELAY between clicks
    3. Transition back to SEARCHING
    """
    print("[DROPPING] Scanning inventory for resources...")
    
    # Find all resources in inventory
    items = find_resources_in_inventory(sct, monitor, resource_template)
    
    if not items:
        print("[DROPPING] No resources found in inventory - Back to searching")
        return transition_state(state, now, SEARCHING), stats
    
    print(f"[DROPPING] Found {len(items)} resources - Dropping...")
    
    # Sort items for efficient dropping
    sorted_items = get_drop_order(items)
    
    # Drop each item
    dropped_count = 0
    for item in sorted_items:
        # Wait before moving to next item (human-like delay)
        if dropped_count > 0:
            time.sleep(config.DROP_MOVE_DELAY)
        
        # Move to item position
        mx, my = pyautogui.position()
        dx = item.x - mx
        dy = item.y - my
        
        send_move(ser, dx, dy)
        time.sleep(0.1)  # Small delay for mouse to arrive
        
        # Shift+click to drop
        send_shift_click(ser)
        
        dropped_count += 1
        
        if config.DEBUG:
            print(f"[DROPPING] Dropped item {dropped_count}/{len(sorted_items)} at ({item.x}, {item.y})")
        
        # Small delay after click
        time.sleep(config.DROP_CLICK_DELAY)
    
    print(f"[DROPPING] Dropped {dropped_count} items - Back to searching")
    
    return (
        transition_state(state, now, SEARCHING),
        increment_drops(stats, dropped_count),
    )


def process_state_machine(
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
    """Process state machine and return new state and stats."""
    
    # F2 always returns to warmup
    if should_stop:
        print("[STOP] F2 pressed - Returning to warmup")
        return transition_state(state, now, WARMUP), stats
    
    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == SEARCHING:
        return handle_searching(state, stats, match_result, now, ser, template_h, template_w)
    elif state.name == COLLECTING:
        return handle_collecting(state, stats, match_result, now)
    elif state.name == DROPPING:
        return handle_dropping(state, stats, now, ser, sct, monitor, resource_template)
    
    return state, stats


def print_status(state: AppState, stats: Stats) -> None:
    """Print current status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Clicks: {stats.clicks} | Drops: {stats.drops} | Resources: {stats.resources_collected}")
    print("=" * 40)


def main() -> None:
    """Main entry point."""
    # Load templates
    template = load_template(config.TEMPLATE_PATH)
    template_h, template_w = template.shape[:2]
    
    # Load resource template for inventory scanning
    try:
        resource_template = load_template(config.RESOURCE_TEMPLATE_PATH)
        print(f"[INFO] Loaded resource template: {config.RESOURCE_TEMPLATE_PATH}")
    except RuntimeError:
        print(f"[WARNING] Resource template not found: {config.RESOURCE_TEMPLATE_PATH}")
        print("[WARNING] Dropping will be skipped if no resource template is available")
        resource_template = None
    
    # Calculate region dimensions
    region_width = config.REGION_X_END - config.REGION_X_START
    region_height = config.REGION_Y_END - config.REGION_Y_START
    
    # Validate template size
    validate_template_size(template, region_width, region_height)
    
    # Initialize screen capture and serial
    sct, monitor = create_screen_capturer()
    ser = open_serial(config.SERIAL_PORT, config.BAUD_RATE)
    
    # Initialize state
    state = make_initial_state()
    stats = make_initial_stats()
    last_loop_time = time.time()
    last_status_print = 0
    
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()
    
    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT")
    print("=" * 50)
    print(f"Region: ({config.REGION_X_START}, {config.REGION_Y_START}) to ({config.REGION_X_END}, {config.REGION_Y_END})")
    print(f"Region size: {region_width}x{region_height}")
    print(f"Inventory: ({config.INVENTORY_X_START}, {config.INVENTORY_Y_START}) to ({config.INVENTORY_X_END}, {config.INVENTORY_Y_END})")
    print("")
    print("Controls:")
    print("  Page Up   = Start (begin searching)")
    print("  Page Down = Stop (return to warmup)")
    print("  q         = Quit (in debug window)")
    print("")
    print("State: WARMUP - Press F1 to start")
    print("=" * 50)
    print("")
    
    while True:
        now = time.time()
        
        # Track state time
        delta = now - last_loop_time
        stats = accumulate_state_time(stats, state.name, delta)
        last_loop_time = now
        
        # Check keyboard input
        should_start, should_stop = check_keyboard_flags()
        
        # Capture and match (only when not in warmup)
        match_result = None
        if state.name != WARMUP:
            frame = grab_region(
                sct, monitor,
                config.REGION_X_START, config.REGION_Y_START,
                config.REGION_X_END, config.REGION_Y_END,
            )
            gray = preprocess_crop(frame)
            match_result = match_template(gray, template, config.MATCH_THRESHOLD)
            
            if config.DEBUG:
                print(f"[{state.name}] confidence={match_result.confidence:.3f} at {match_result.max_loc}")
                
                if not show_live_windows(gray, template, match_result, config.MATCH_THRESHOLD):
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
        
        # Process state machine
        old_state = state.name
        state, stats = process_state_machine(
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
        elif state.name == SEARCHING:
            time.sleep(config.SEARCH_SCAN_INTERVAL)
        elif state.name == COLLECTING:
            time.sleep(0.1)  # Fast loop, actual scan interval handled in handler
        elif state.name == DROPPING:
            pass  # No sleep, dropping handles its own timing
    
    # Cleanup
    listener.stop()


if __name__ == "__main__":
    main()
