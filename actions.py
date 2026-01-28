"""
Pure mouse/keyboard action functions.

These functions perform actions without business logic.
All mouse/keyboard control goes through Arduino serial commands.

Inspired by osrs_basic_botting_functions/functions.py patterns like:
- pick_item()
- pick_item_right()
- drop_item() / release_drop_item()
- random_breaks()
"""

import time
import random
import serial
import pyautogui  # Only used for reading mouse position, not for control

from serial_io import (
    send_move,
    send_click,
    send_right_click,
    send_shift_hold,
    send_shift_release,
    send_key,
)
from vision import Point
import config


def get_mouse_position() -> tuple[int, int]:
    """
    Get current mouse position.
    
    Note: Uses pyautogui only for READING position, not for control.
    All control goes through Arduino.
    
    Returns:
        (x, y) tuple of current mouse coordinates
    """
    pos = pyautogui.position()
    return (pos.x, pos.y)


def random_delay(min_sec: float, max_sec: float) -> None:
    """
    Sleep for a random duration between min and max seconds.
    
    Inspired by: random_breaks()
    
    Args:
        min_sec: Minimum sleep time in seconds
        max_sec: Maximum sleep time in seconds
    """
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def click_at(
    ser: serial.Serial,
    x: int,
    y: int,
    randomize: int = 0,
    double_click: bool = False,
) -> None:
    """
    Move to position and click via Arduino.
    
    Inspired by: pick_item()
    
    Args:
        ser: Serial connection to Arduino
        x: Target X coordinate
        y: Target Y coordinate
        randomize: Add random offset (pixels) to x and y
        double_click: If True, click twice with small delay
    """
    mx, my = get_mouse_position()
    
    # Apply randomization
    target_x = x
    target_y = y
    if randomize > 0:
        target_x += random.randint(-randomize, randomize)
        target_y += random.randint(-randomize, randomize)
    
    # Calculate delta
    dx = target_x - mx
    dy = target_y - my
    
    # Move and click via Arduino
    send_move(ser, dx, dy)
    random_delay(0.05, 0.15)
    
    send_click(ser)
    
    if double_click:
        random_delay(0.12, 0.25)
        send_click(ser)


def click_point(
    ser: serial.Serial,
    point: Point,
    randomize: int = 0,
    double_click: bool = False,
) -> None:
    """
    Move to Point and click.
    
    Convenience wrapper around click_at() that accepts a Point.
    
    Args:
        ser: Serial connection to Arduino
        point: Target Point
        randomize: Add random offset (pixels) to x and y
        double_click: If True, click twice with small delay
    """
    click_at(ser, point.x, point.y, randomize=randomize, double_click=double_click)


def click_at_right(
    ser: serial.Serial,
    x: int,
    y: int,
    option: int = 1,
    randomize: int = 0,
) -> None:
    """
    Right-click at position and select menu option via Arduino.
    
    Inspired by: pick_item_right()
    
    Note: Requires Arduino to support "R" command for right-click.
    The menu option is selected by moving down Y pixels based on option number.
    
    Args:
        ser: Serial connection to Arduino
        x: Target X coordinate
        y: Target Y coordinate
        option: Menu option number (1=first, 2=second, etc.)
        randomize: Add random offset (pixels) to x and y
    """
    mx, my = get_mouse_position()
    
    # Apply randomization
    target_x = x
    target_y = y
    if randomize > 0:
        target_x += random.randint(-randomize, randomize)
        target_y += random.randint(-randomize, randomize)
    
    # Calculate delta and move
    dx = target_x - mx
    dy = target_y - my
    send_move(ser, dx, dy)
    random_delay(0.1, 0.2)
    
    # Right click via Arduino
    send_right_click(ser)
    random_delay(0.15, 0.3)
    
    # Move to menu option (each option is ~15 pixels apart, starting at ~40 pixels down)
    option_y_offset = 40 + (option - 1) * 15
    menu_x_offset = random.randint(0, 20)
    
    send_move(ser, menu_x_offset, option_y_offset)
    random_delay(0.05, 0.15)
    
    # Click to select
    send_click(ser)


def drop_items(
    ser: serial.Serial,
    items: list[Point],
    click_delay: float = 0.15,
    move_delay: float = 0.08,
) -> int:
    """
    Drop all items by shift-clicking each position via Arduino.
    
    Inspired by: drop_wood() pattern - hold shift, click all items, release shift
    
    Args:
        ser: Serial connection to Arduino
        items: List of Points to click (item positions)
        click_delay: Delay between clicks
        move_delay: Delay after moving to each item
    
    Returns:
        Number of items dropped
    """
    if not items:
        return 0
    
    # Hold shift for the entire dropping sequence
    send_shift_hold(ser)
    random_delay(0.08, 0.12)
    
    dropped_count = 0
    
    for item in items:
        # Wait before moving to next item (skip first)
        if dropped_count > 0:
            random_delay(move_delay * 0.8, move_delay * 1.2)
        
        # Move to item position
        mx, my = get_mouse_position()
        dx = item.x - mx
        dy = item.y - my
        
        send_move(ser, dx, dy)
        random_delay(0.08, 0.12)
        
        # Click to drop (shift is held)
        send_click(ser)
        random_delay(0.30, 0.40)  # Wait for Arduino cooldown
        send_click(ser)  # Double click for reliability
        
        dropped_count += 1
        
        # Small delay after click
        random_delay(click_delay * 0.8, click_delay * 1.2)
    
    # Release shift after all items dropped
    send_shift_release(ser)
    
    return dropped_count


def move_to(
    ser: serial.Serial,
    x: int,
    y: int,
    randomize: int = 0,
) -> None:
    """
    Move mouse to position without clicking via Arduino.
    
    Args:
        ser: Serial connection to Arduino
        x: Target X coordinate
        y: Target Y coordinate
        randomize: Add random offset (pixels) to x and y
    """
    mx, my = get_mouse_position()
    
    target_x = x
    target_y = y
    if randomize > 0:
        target_x += random.randint(-randomize, randomize)
        target_y += random.randint(-randomize, randomize)
    
    dx = target_x - mx
    dy = target_y - my
    
    send_move(ser, dx, dy)


def move_to_point(
    ser: serial.Serial,
    point: Point,
    randomize: int = 0,
) -> None:
    """
    Move mouse to Point without clicking.
    
    Args:
        ser: Serial connection to Arduino
        point: Target Point
        randomize: Add random offset (pixels) to x and y
    """
    move_to(ser, point.x, point.y, randomize=randomize)


# =========================
# KEYBOARD ACTIONS (Game UI Tabs)
# =========================

def press_key(ser: serial.Serial, key: str) -> None:
    """
    Press a key via Arduino.
    
    Args:
        ser: Serial connection to Arduino
        key: Key name from config (f1, f2, f3, f4, f5, f6, f10, esc)
    """
    send_key(ser, key)
    random_delay(0.05, 0.12)


def open_combat_tab(ser: serial.Serial) -> None:
    """Open Combat options tab (F1)."""
    press_key(ser, config.KEY_COMBAT)


def open_skills_tab(ser: serial.Serial) -> None:
    """Open Skills tab (F2)."""
    press_key(ser, config.KEY_SKILLS)


def open_quests_tab(ser: serial.Serial) -> None:
    """Open Quest list tab (F3)."""
    press_key(ser, config.KEY_QUESTS)


def open_inventory(ser: serial.Serial) -> None:
    """Open Inventory tab (ESC)."""
    press_key(ser, config.KEY_INVENTORY)


def open_equipment_tab(ser: serial.Serial) -> None:
    """Open Worn equipment tab (F4)."""
    press_key(ser, config.KEY_EQUIPMENT)


def open_prayer_tab(ser: serial.Serial) -> None:
    """Open Prayer tab (F5)."""
    press_key(ser, config.KEY_PRAYER)


def open_magic_tab(ser: serial.Serial) -> None:
    """Open Magic spellbook tab (F6)."""
    press_key(ser, config.KEY_MAGIC)


def open_settings(ser: serial.Serial) -> None:
    """Open Settings tab (F10)."""
    press_key(ser, config.KEY_SETTINGS)
