"""
Main entry point for the screen2serial bot.

This is a thin orchestrator that:
1. Parses command-line arguments to select a macro
2. Sets up serial connection
3. Sets up keyboard input
4. Dispatches to the selected macro

Usage:
    python main.py --macro woodcutting
    python main.py --macro enchanting
    python main.py --list  # List available macros
"""

import argparse
import sys

from pynput import keyboard

import config
from logic import open_serial
from macros import get_available_macros, get_macro, get_macro_description


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


def list_macros() -> None:
    """Print available macros and exit."""
    print("\nAvailable macros:")
    print("-" * 40)
    for name in get_available_macros():
        description = get_macro_description(name)
        print(f"  {name:15} - {description}")
    print("-" * 40)
    print("\nUsage: python main.py --macro <name>")
    print("")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Screen2Serial Bot - Automation via Arduino",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py --macro woodcutting
    python main.py --macro enchanting --debug
    python main.py --list
        """,
    )
    
    parser.add_argument(
        "--macro", "-m",
        type=str,
        help="Name of the macro to run",
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available macros and exit",
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Handle --list flag
    if args.list:
        list_macros()
        sys.exit(0)
    
    # Require --macro if not listing
    if not args.macro:
        print("Error: --macro is required. Use --list to see available macros.")
        sys.exit(1)
    
    # Get the macro function
    macro_fn = get_macro(args.macro)
    if macro_fn is None:
        print(f"Error: Unknown macro '{args.macro}'")
        list_macros()
        sys.exit(1)
    
    # Initialize serial connection
    ser = open_serial(config.SERIAL_PORT, config.BAUD_RATE)
    
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.start()
    
    try:
        # Run the selected macro
        macro_fn(
            ser=ser,
            check_keyboard=check_keyboard_flags,
            debug=args.debug,
        )
    finally:
        # Cleanup
        listener.stop()


if __name__ == "__main__":
    main()
