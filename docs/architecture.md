# Architecture

This document describes the system architecture and design principles of screen2serial.

## Design Principles

### 1. Pure Functions in Logic

The `logic/` module contains only pure functions - given the same inputs, they always produce the same outputs with no side effects. This makes the code:

- **Testable**: Functions can be unit tested without mocking
- **Predictable**: No hidden state or surprises
- **Composable**: Functions can be combined freely

```python
# Pure function example from state.py
def increment_clicks(stats: Stats) -> Stats:
    """Returns a NEW Stats object, never mutates the input."""
    return Stats(
        clicks=stats.clicks + 1,
        actions=stats.actions,
        cycles=stats.cycles,
        state_time=stats.state_time,
        extra=stats.extra,
    )
```

### 2. Immutable Data Structures

State and statistics are stored in frozen dataclasses:

```python
@dataclass(frozen=True)
class AppState:
    name: str
    since: float
    data: dict[str, Any]

@dataclass(frozen=True)
class Stats:
    clicks: int
    actions: int
    cycles: int
    state_time: dict[str, float]
    extra: dict[str, Any]
```

State transitions create new objects rather than mutating existing ones.

### 3. Self-Contained Macros

Each macro is fully self-contained with:

- Its own state definitions
- Its own handler functions
- Its own template loading
- Its own main loop

This makes macros independent and easy to add/remove.

## Layer Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                           main.py                              │
│                                                                │
│  - Parse CLI arguments (--macro, --debug, --list)              │
│  - Initialize serial connection                                │
│  - Start keyboard listener                                     │
│  - Dispatch to selected macro                                  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                         macros/*                               │
│                                                                │
│  Each macro:                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Define states (WC_SEARCHING, WC_COLLECTING, etc.)     │  │
│  │ 2. Load templates internally                             │  │
│  │ 3. Create screen capturer                                │  │
│  │ 4. Run state machine loop                                │  │
│  │ 5. Call logic functions for actual work                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                          logic/*                               │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   state    │  │  capture   │  │   vision   │               │
│  │            │  │            │  │            │               │
│  │ AppState   │  │ grab_      │  │ find_      │               │
│  │ Stats      │  │   region   │  │   template │               │
│  │ transition │  │ match_     │  │ find_all_  │               │
│  │   _state   │  │   template │  │   templates│               │
│  └────────────┘  └────────────┘  └────────────┘               │
│                                                                │
│  ┌────────────┐  ┌────────────┐                               │
│  │  actions   │  │ serial_io  │                               │
│  │            │  │            │                               │
│  │ click_at   │  │ send_move  │                               │
│  │ drop_items │  │ send_click │                               │
│  │ press_key  │  │ send_key   │                               │
│  └────────────┘  └────────────┘                               │
└────────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                         Arduino                                │
│                                                                │
│  - Receives serial commands (M, L, R, K, SH, SR, etc.)         │
│  - Executes as HID device (hardware-level input)               │
│  - Adds small random delays for human-like behavior            │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

### State Machine Flow

```
┌─────────┐    PageUp     ┌─────────────┐
│ WARMUP  │──────────────▶│  SEARCHING  │
└─────────┘               └──────┬──────┘
     ▲                           │
     │                     found │
     │ PageDown                  ▼
     │                    ┌─────────────┐
     └────────────────────│ COLLECTING  │
     │                    └──────┬──────┘
     │                           │
     │                     done  │
     │                           ▼
     │                    ┌─────────────┐
     └────────────────────│  DROPPING   │
                          └─────────────┘
```

### Template Matching Flow

```
Screen Capture          Template              Match Result
     │                     │                       │
     ▼                     ▼                       │
┌─────────┐         ┌─────────────┐                │
│ mss.grab │───────▶│ matchTemplate│──────────────▶│
└─────────┘         └─────────────┘                │
     │                                             │
     ▼                                             ▼
┌─────────────┐                            ┌─────────────┐
│ BGR → Gray  │                            │ MatchResult │
│ (preprocess)│                            │ .confidence │
└─────────────┘                            │ .matched    │
                                           │ .max_loc    │
                                           └─────────────┘
```

## Module Responsibilities

### main.py

- CLI argument parsing
- Serial port initialization
- Keyboard listener setup
- Macro dispatching

### logic/state.py

- `AppState` and `Stats` dataclasses
- State transition functions
- Stats accumulation functions

### logic/capture.py

- Screen capture via mss
- Template loading
- Template matching
- Debug visualization

### logic/vision.py

- `Region` and `Point` dataclasses
- Multi-template detection
- Position sorting
- Inventory state detection

### logic/actions.py

- Mouse movement and clicks
- Keyboard presses
- Item dropping
- Random delays

### logic/serial_io.py

- Serial port management
- Arduino command protocol
- Hesitation calculation

### macros/\*

- State machine definitions
- Handler functions per state
- Template paths
- Main loop

## Configuration

All configuration lives in `config.py`:

```python
# Serial
SERIAL_PORT = "COM5"
BAUD_RATE = 9600

# Regions
REGION_X_START = 0
REGION_X_END = 1575
# ...

# Thresholds
MATCH_THRESHOLD = 0.50
```

Macros read config values but don't modify them.

## Thread Model

```
┌─────────────────────────────────────────┐
│              Main Thread                │
│                                         │
│  main() loop:                           │
│    1. Check keyboard flags              │
│    2. Capture screen                    │
│    3. Process state                     │
│    4. Sleep based on state              │
└────────────────────────────────────────┘
              │
              │ shared globals
              ▼
┌─────────────────────────────────────────┐
│           Keyboard Thread               │
│                                         │
│  pynput.Listener:                       │
│    - on_press → set _should_start/stop  │
└─────────────────────────────────────────┘
```

The keyboard listener runs in a separate thread, setting global flags that the main loop checks each iteration.
