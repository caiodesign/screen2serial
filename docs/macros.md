# Creating Macros

This guide explains how to create new automation macros for screen2serial.

## Macro Structure

Every macro follows the same pattern:

```
macros/your_macro.py
├── States (constants)
├── Config (regions, templates)
├── Handlers (one per state)
├── State machine (process_*_state)
└── Main loop (run_your_macro)
```

## Step-by-Step Guide

### 1. Create the File

Create `macros/your_macro.py`:

```python
"""
Your macro description.

State machine:
    WARMUP -> STATE_A -> STATE_B -> ... -> WARMUP
"""

import time
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
    create_screen_capturer,
    load_template,
    # Vision
    Region,
    Point,
    find_template,
    find_all_templates,
    # Actions
    click_point,
    random_delay,
)
import config
```

### 2. Define States

```python
# =========================
# YOUR MACRO STATES
# =========================
YM_STATE_A = "ym_state_a"
YM_STATE_B = "ym_state_b"
YM_STATE_C = "ym_state_c"

ALL_YM_STATES = (WARMUP, YM_STATE_A, YM_STATE_B, YM_STATE_C)
```

State naming convention:

- Use a short prefix (WC*, ENCH*, YM\_)
- Use lowercase with underscores
- Be descriptive (searching, collecting, banking)

### 3. Define Configuration

```python
# =========================
# YOUR MACRO CONFIG
# =========================
TEMPLATE_PATH = "images/your/template.png"
ITEM_TEMPLATE_PATH = "images/your/item.png"

DETECTION_REGION = Region(
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
```

### 4. Create Handlers

Each state needs a handler function:

```python
def handle_warmup(
    state: AppState,
    stats: Stats,
    now: float,
    should_start: bool,
) -> tuple[AppState, Stats]:
    """Handle WARMUP state - waiting for user to start."""
    if should_start:
        print("[WARMUP] Starting...")
        return transition_state(state, now, YM_STATE_A), stats
    return state, stats


def handle_state_a(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
) -> tuple[AppState, Stats]:
    """Handle STATE_A - describe what this state does."""
    # Your logic here
    result = find_template(sct, monitor, TEMPLATE_PATH, DETECTION_REGION, 0.8)

    if result:
        print(f"[STATE_A] Found at ({result.x}, {result.y})")
        click_point(ser, result)
        return transition_state(state, now, YM_STATE_B), increment_clicks(stats)

    return state, stats
```

Handler best practices:

- Always return `(state, stats)` tuple
- Use `transition_state()` to change states
- Use `update_state_data()` to store data without changing state
- Print status messages with state prefix: `[STATE_NAME]`

### 5. Create State Machine Processor

```python
def process_your_macro_state(
    state: AppState,
    stats: Stats,
    now: float,
    ser,
    sct,
    monitor,
    should_start: bool,
    should_stop: bool,
) -> tuple[AppState, Stats]:
    """Process your macro state machine."""

    # Stop always returns to warmup
    if should_stop:
        print("[STOP] Returning to warmup")
        return transition_state(state, now, WARMUP), stats

    if state.name == WARMUP:
        return handle_warmup(state, stats, now, should_start)
    elif state.name == YM_STATE_A:
        return handle_state_a(state, stats, now, ser, sct, monitor)
    elif state.name == YM_STATE_B:
        return handle_state_b(state, stats, now, ser)
    elif state.name == YM_STATE_C:
        return handle_state_c(state, stats, now)

    return state, stats
```

### 6. Create State Factory

```python
def create_your_macro_state() -> tuple[AppState, Stats]:
    """Create initial state and stats."""
    return (
        make_initial_state(WARMUP),
        make_initial_stats(ALL_YM_STATES),
    )
```

### 7. Create Main Loop

```python
def print_status(state: AppState, stats: Stats) -> None:
    """Print current status."""
    print("=" * 40)
    print(f"State: {state.name.upper()}")
    print(f"Clicks: {stats.clicks} | Actions: {stats.actions} | Cycles: {stats.cycles}")
    print("=" * 40)


def run_your_macro(
    ser,
    check_keyboard: callable,
    debug: bool = False,
) -> tuple[AppState, Stats]:
    """
    Run your macro loop.

    Args:
        ser: Serial connection for mouse control
        check_keyboard: Function that returns (should_start, should_stop)
        debug: Enable debug mode

    Returns:
        Final (state, stats) tuple
    """
    # Load templates
    template = load_template(TEMPLATE_PATH)

    # Initialize screen capture
    sct, monitor = create_screen_capturer()

    # Print banner
    print("")
    print("=" * 50)
    print("  SCREEN2SERIAL BOT - YOUR MACRO")
    print("=" * 50)
    print("Controls:")
    print("  Page Up   = Start")
    print("  Page Down = Stop")
    print("")
    print("State: WARMUP - Press Page Up to start")
    print("=" * 50)
    print("")

    # Initialize state
    state, stats = create_your_macro_state()

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

        # Process state machine
        old_state = state.name
        state, stats = process_your_macro_state(
            state, stats, now, ser, sct, monitor,
            should_start, should_stop,
        )

        # Print status on state change or every 30 seconds
        if state.name != old_state:
            print_status(state, stats)
        elif int(now) - last_status_print >= 30:
            print_status(state, stats)
            last_status_print = int(now)

        # Sleep based on state
        if state.name == WARMUP:
            time.sleep(0.1)  # Fast polling for keyboard
        else:
            time.sleep(0.2)  # Adjust per state needs

    return state, stats
```

### 8. Register the Macro

In `macros/__init__.py`:

```python
from .your_macro import (
    run_your_macro,
    create_your_macro_state,
    YM_STATE_A,
    YM_STATE_B,
    YM_STATE_C,
)

MACRO_REGISTRY = {
    "woodcutting": (run_woodcutting, "Chop trees and drop logs"),
    "enchanting": (run_enchanting, "Enchant jade amulets"),
    "your_macro": (run_your_macro, "Description of your macro"),  # Add this
}
```

## Common Patterns

### Using State Data

Store temporary data that persists across loop iterations:

```python
# Set data on state transition
state = transition_state(state, now, NEXT_STATE,
    last_scan=now,
    target_position=(100, 200),
)

# Read data in handler
last_scan = state.data.get("last_scan", 0.0)
target = state.data.get("target_position")

# Update data without changing state
state = update_state_data(state, last_scan=now)
```

### Scan Intervals

Don't scan every frame - use intervals:

```python
def handle_collecting(state, stats, now, ...):
    last_scan = state.data.get("last_scan", 0.0)

    if now - last_scan < SCAN_INTERVAL:
        return state, stats  # Too soon, skip

    # Do the scan
    state = update_state_data(state, last_scan=now)
    # ... rest of logic
```

### Multiple Templates

Find all items and process them:

```python
items = find_all_templates(sct, monitor, ITEM_TEMPLATE, INVENTORY_REGION, 0.7)

if not items:
    return transition_state(state, now, NEXT_STATE), stats

# Process first/last/closest item
first_item = items[0]
last_item = get_last_item_bottom_right(items)
closest = min(items, key=lambda p: distance(p, player_pos))
```

### Context Objects

For macros with lots of mutable state, use a context dataclass:

```python
@dataclass
class YourMacroContext:
    items: list[Point]
    count: int
    target: Point | None

    @classmethod
    def create(cls) -> "YourMacroContext":
        return cls(items=[], count=0, target=None)
```

Pass it to handlers:

```python
def handle_state_a(state, stats, now, ser, ctx):
    ctx.items = find_all_templates(...)
    ctx.count = len(ctx.items)
    # ...
```

## Testing Your Macro

1. Run with debug mode to see detection windows:

   ```bash
   python main.py --macro your_macro --debug
   ```

2. Check template matching confidence values

3. Adjust thresholds if needed

4. Test state transitions by pressing Page Up/Down

## Checklist

- [ ] States defined with unique prefix
- [ ] All states included in `ALL_*_STATES` tuple
- [ ] Handler for each state
- [ ] State machine processor handles all states
- [ ] PageDown returns to WARMUP from any state
- [ ] Main loop prints banner
- [ ] Registered in `MACRO_REGISTRY`
- [ ] Exports added to `__all__`
