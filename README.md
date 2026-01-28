# Screen2Serial

A modular automation bot that uses computer vision (OpenCV) for screen detection and an Arduino for hardware-level mouse/keyboard input. The architecture separates pure logic functions from macro-specific business logic, making it easy to add new automation tasks.

## Features

- **Hardware-level input**: Mouse and keyboard commands sent via Arduino (undetectable by software)
- **Template matching**: OpenCV-based screen detection for finding UI elements
- **Modular macros**: Each automation task is self-contained with its own state machine
- **Pure functions**: Core logic is separated from side effects for testability
- **Command-line interface**: Select macros via CLI arguments

## Quick Start

### Prerequisites

- Python 3.10+
- Arduino with USB HID capability (Leonardo, Pro Micro, etc.)
- Serial connection to Arduino

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd screen2serial

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# List available macros
python main.py --list

# Run a specific macro
python main.py --macro woodcutting

# Run with debug mode (shows live detection windows)
python main.py --macro enchanting --debug
```

### Controls

| Key       | Action                  |
| --------- | ----------------------- |
| Page Up   | Start the macro         |
| Page Down | Stop (return to warmup) |
| q         | Quit (in debug window)  |

## Project Structure

```
screen2serial/
├── main.py              # CLI entry point (macro dispatcher)
├── config.py            # Global configuration values
├── requirements.txt     # Python dependencies
│
├── logic/               # Pure functions (no side effects)
│   ├── __init__.py      # Public API exports
│   ├── state.py         # State machine infrastructure
│   ├── actions.py       # Mouse/keyboard actions via Arduino
│   ├── vision.py        # Template matching & image recognition
│   ├── capture.py       # Screen capture utilities
│   └── serial_io.py     # Arduino serial communication
│
├── macros/              # Self-contained automation macros
│   ├── __init__.py      # Macro registry
│   ├── woodcutting.py   # Woodcutting macro
│   └── enchanting.py    # Enchanting macro
│
├── images/              # Template images for detection
│   ├── resource/        # Tree, wood, etc.
│   ├── item/            # Items (amulets, runes)
│   ├── magic/           # Spell icons
│   ├── menu/            # UI tabs
│   └── ui/              # UI elements
│
└── docs/                # Documentation
    ├── architecture.md  # System design overview
    ├── logic.md         # Logic module reference
    ├── macros.md        # Creating new macros
    ├── arduino.md       # Arduino setup guide
    └── config.md        # Configuration reference
```

## Architecture Overview

The project follows a clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│              (CLI parsing, keyboard listener)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      macros/*                               │
│         (State machines, business logic, templates)         │
│                                                             │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │ woodcutting │  │ enchanting  │  │  (future)   │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       logic/*                               │
│              (Pure functions, no side effects)              │
│                                                             │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│   │  state  │ │ actions │ │ vision  │ │ capture │          │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      serial_io                              │
│              (Arduino communication protocol)               │
└─────────────────────────────────────────────────────────────┘
```

## Adding a New Macro

1. Create `macros/your_macro.py`
2. Define states and handlers
3. Implement `run_your_macro(ser, check_keyboard, debug=False)`
4. Register in `macros/__init__.py`:

```python
MACRO_REGISTRY = {
    "your_macro": (run_your_macro, "Description here"),
    # ...
}
```

See [docs/macros.md](docs/macros.md) for detailed guide.

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow
- [Logic Module](docs/logic.md) - Pure function reference
- [Creating Macros](docs/macros.md) - Step-by-step macro guide
- [Arduino Setup](docs/arduino.md) - Hardware configuration
- [Configuration](docs/config.md) - Config values reference

## Dependencies

| Package       | Purpose                              |
| ------------- | ------------------------------------ |
| opencv-python | Template matching, image processing  |
| numpy         | Array operations                     |
| mss           | Fast screen capture                  |
| pyautogui     | Mouse position reading (not control) |
| pyserial      | Arduino communication                |
| pynput        | Keyboard event listening             |

## License

MIT License - See LICENSE file for details.
