# Logic Module Reference

The `logic/` module contains pure functions organized by domain. All functions are designed to be testable and composable.

## Module Overview

| File           | Purpose                              |
| -------------- | ------------------------------------ |
| `state.py`     | State machine infrastructure         |
| `capture.py`   | Screen capture and template matching |
| `vision.py`    | Image recognition functions          |
| `actions.py`   | Mouse/keyboard actions               |
| `serial_io.py` | Arduino communication                |

---

## state.py - State Management

### Data Structures

#### AppState

```python
@dataclass(frozen=True)
class AppState:
    name: str                    # Current state name (e.g., "warmup", "wc_searching")
    since: float                 # Timestamp when entered this state
    data: dict[str, Any]         # Arbitrary state data (e.g., last_scan time)
```

#### Stats

```python
@dataclass(frozen=True)
class Stats:
    clicks: int                  # Total clicks performed
    actions: int                 # Main actions (drops, enchants, etc.)
    cycles: int                  # Full cycles completed
    state_time: dict[str, float] # Time spent in each state
    extra: dict[str, Any]        # Macro-specific stats
```

### Functions

#### make_initial_state

```python
def make_initial_state(initial_name: str = WARMUP) -> AppState
```

Create a new AppState starting in the given state.

#### make_initial_stats

```python
def make_initial_stats(all_states: tuple[str, ...]) -> Stats
```

Create Stats with time tracking for the specified states.

#### transition_state

```python
def transition_state(
    state: AppState,
    now: float,
    to: str,
    **data_updates,
) -> AppState
```

Transition to a new state, optionally updating data.

```python
# Example
new_state = transition_state(state, time.time(), WC_COLLECTING, last_scan=now)
```

#### update_state_data

```python
def update_state_data(state: AppState, **data_updates) -> AppState
```

Update state data without changing state name.

#### accumulate_state_time

```python
def accumulate_state_time(stats: Stats, state_name: str, delta: float) -> Stats
```

Add time to a state's accumulator.

#### increment_clicks / increment_actions / increment_cycles

```python
def increment_clicks(stats: Stats) -> Stats
def increment_actions(stats: Stats, count: int = 1) -> Stats
def increment_cycles(stats: Stats) -> Stats
```

Increment the respective counter.

---

## capture.py - Screen Capture

### Data Structures

#### MatchResult

```python
@dataclass(frozen=True)
class MatchResult:
    gray: np.ndarray           # Grayscale image searched
    result: np.ndarray         # Match result matrix
    confidence: float          # Best match confidence (0.0-1.0)
    matched: bool              # True if confidence >= threshold
    max_loc: tuple[int, int]   # (x, y) of best match
```

### Functions

#### load_template

```python
def load_template(path: str) -> np.ndarray
```

Load a template image and convert to grayscale.

#### create_screen_capturer

```python
def create_screen_capturer() -> tuple[mss, dict]
```

Create mss instance and get primary monitor info.

#### grab_region

```python
def grab_region(
    sct: mss,
    monitor: dict,
    x_start: int,
    y_start: int,
    x_end: int,
    y_end: int,
) -> np.ndarray
```

Capture a specific screen region as BGR image.

#### preprocess_crop

```python
def preprocess_crop(crop: np.ndarray) -> np.ndarray
```

Convert BGR image to grayscale for matching.

#### match_template

```python
def match_template(
    gray: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> MatchResult
```

Perform template matching and return result.

#### validate_template_size

```python
def validate_template_size(template: np.ndarray, region_width: int, region_height: int) -> None
```

Raise error if template is larger than region (would fail matching).

#### show_live_windows

```python
def show_live_windows(
    gray_frame: np.ndarray,
    template: np.ndarray,
    match_result,
    threshold: float,
) -> bool
```

Show debug windows with live detection. Returns False if 'q' pressed.

---

## vision.py - Image Recognition

### Data Structures

#### Region

```python
@dataclass(frozen=True)
class Region:
    x_start: int
    y_start: int
    x_end: int
    y_end: int

    @property
    def width(self) -> int

    @property
    def height(self) -> int
```

#### Point

```python
@dataclass(frozen=True)
class Point:
    x: int              # Absolute screen X coordinate
    y: int              # Absolute screen Y coordinate
    confidence: float   # Match confidence (optional)
```

### Functions

#### template_exists

```python
def template_exists(
    sct: mss,
    monitor: dict,
    template,             # str path or np.ndarray
    region: Region,
    threshold: float = 0.8,
) -> bool
```

Check if template exists in region.

#### find_template

```python
def find_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> Point | None
```

Find best match of template. Returns center point or None.

#### find_all_templates

```python
def find_all_templates(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> list[Point]
```

Find all occurrences of template with deduplication.

#### count_template

```python
def count_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> int
```

Count occurrences of template in region.

#### find_closest_template

```python
def find_closest_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    from_pos: tuple[int, int],
    threshold: float = 0.8,
) -> Point | None
```

Find the match closest to a given position.

#### sort_by_position

```python
def sort_by_position(
    items: list[Point],
    top_to_bottom: bool = True,
    left_to_right: bool = True,
) -> list[Point]
```

Sort points by position (useful for drop order).

#### get_last_item_bottom_right

```python
def get_last_item_bottom_right(items: list[Point]) -> Point | None
```

Get the bottom-right most point (for enchanting).

---

## actions.py - Mouse/Keyboard Actions

### Functions

#### get_mouse_position

```python
def get_mouse_position() -> tuple[int, int]
```

Get current mouse (x, y) coordinates.

#### random_delay

```python
def random_delay(min_sec: float, max_sec: float) -> None
```

Sleep for random duration between min and max.

#### click_at

```python
def click_at(
    ser: serial.Serial,
    x: int,
    y: int,
    randomize: int = 0,
    double_click: bool = False,
) -> None
```

Move to position and click via Arduino.

#### click_point

```python
def click_point(
    ser: serial.Serial,
    point: Point,
    randomize: int = 0,
    double_click: bool = False,
) -> None
```

Same as `click_at` but accepts a Point.

#### click_at_right

```python
def click_at_right(
    ser: serial.Serial,
    x: int,
    y: int,
    option: int = 1,
    randomize: int = 0,
) -> None
```

Right-click and select menu option.

#### drop_items

```python
def drop_items(
    ser: serial.Serial,
    items: list[Point],
    click_delay: float = 0.15,
    move_delay: float = 0.08,
) -> int
```

Drop all items via shift-click. Returns count dropped.

#### move_to / move_to_point

```python
def move_to(ser: serial.Serial, x: int, y: int, randomize: int = 0) -> None
def move_to_point(ser: serial.Serial, point: Point, randomize: int = 0) -> None
```

Move mouse without clicking.

#### Keyboard Tab Functions

```python
def press_key(ser: serial.Serial, key: str) -> None
def open_combat_tab(ser: serial.Serial) -> None    # F1
def open_skills_tab(ser: serial.Serial) -> None    # F2
def open_quests_tab(ser: serial.Serial) -> None    # F3
def open_inventory(ser: serial.Serial) -> None     # ESC
def open_equipment_tab(ser: serial.Serial) -> None # F4
def open_prayer_tab(ser: serial.Serial) -> None    # F5
def open_magic_tab(ser: serial.Serial) -> None     # F6
def open_settings(ser: serial.Serial) -> None      # F10
```

---

## serial_io.py - Arduino Communication

### Functions

#### open_serial

```python
def open_serial(port: str, baud: int, retries: int = 5) -> serial.Serial
```

Open serial connection with retries.

#### send_move

```python
def send_move(ser: serial.Serial, dx: int, dy: int) -> None
```

Send relative mouse move command: `M{dx},{dy}\n`

#### send_click

```python
def send_click(ser: serial.Serial) -> None
```

Send left click: `L\n`

#### send_right_click

```python
def send_right_click(ser: serial.Serial) -> None
```

Send right click: `R\n`

#### send_shift_click

```python
def send_shift_click(ser: serial.Serial) -> None
```

Send shift+click: `SL\n`

#### send_shift_hold / send_shift_release

```python
def send_shift_hold(ser: serial.Serial) -> None    # SH\n
def send_shift_release(ser: serial.Serial) -> None # SR\n
```

Hold/release shift key.

#### send_key

```python
def send_key(ser: serial.Serial, key: str) -> None
```

Send key press: `K{key}\n` (e.g., `Kf1\n`, `Kesc\n`)

#### compute_hesitation

```python
def compute_hesitation(
    confidence: float,
    threshold: float,
    hesitation_min: float,
    hesitation_max: float,
) -> float
```

Calculate delay based on match confidence. Higher confidence = less delay.
