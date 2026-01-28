"""
Main entry point for the screen2serial bot.

This is a thin orchestrator that:
1. Sets up hardware (serial, screen capture)
2. Loads templates
3. Sets up keyboard input
4. Runs the selected macro (woodcutting by default)
"""

from pynput import keyboard

import config
from logic import load_template, create_screen_capturer, validate_template_size, open_serial
from macros.woodcutting import run_woodcutting


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


def main() -> None:
    """Main entry point."""
    # Load templates
    template = load_template(config.TEMPLATE_PATH)
    
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
    
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()
    
    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - WOODCUTTING")
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
    print("State: WARMUP - Press Page Up to start")
    print("=" * 50)
    print("")
    
    try:
        # Run the woodcutting macro (it manages its own state internally)
        run_woodcutting(
            sct=sct,
            monitor=monitor,
            ser=ser,
            template=template,
            resource_template=resource_template,
            region_x_start=config.REGION_X_START,
            region_y_start=config.REGION_Y_START,
            region_x_end=config.REGION_X_END,
            region_y_end=config.REGION_Y_END,
            match_threshold=config.MATCH_THRESHOLD,
            search_scan_interval=config.SEARCH_SCAN_INTERVAL,
            check_keyboard=check_keyboard_flags,
            debug=config.DEBUG,
        )
    finally:
        # Cleanup
        listener.stop()


if __name__ == "__main__":
    main()
