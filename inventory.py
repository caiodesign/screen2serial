import cv2
import numpy as np
import random
from dataclasses import dataclass
from mss import mss

import config


@dataclass(frozen=True)
class InventoryCell:
    """Represents a single inventory cell."""
    row: int
    col: int
    x: int  # top-left x
    y: int  # top-left y
    width: int
    height: int
    has_item: bool
    is_resource: bool


@dataclass(frozen=True)
class InventoryState:
    """Represents the full inventory state."""
    cells: tuple[InventoryCell, ...]
    is_full: bool
    resource_cells: tuple[InventoryCell, ...]


def load_inventory_templates() -> tuple[np.ndarray, np.ndarray]:
    """Load and preprocess inventory templates."""
    resource_template = cv2.imread(config.RESOURCE_TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    bg_template = cv2.imread(config.INVENTORY_BG_TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)

    if resource_template is None:
        raise RuntimeError(f"Resource template not found: {config.RESOURCE_TEMPLATE_PATH}")
    if bg_template is None:
        raise RuntimeError(f"Background template not found: {config.INVENTORY_BG_TEMPLATE_PATH}")

    return resource_template, bg_template


def compute_cell_dimensions() -> tuple[int, int]:
    """Calculate the dimensions of each inventory cell."""
    total_width = config.INVENTORY_X_END - config.INVENTORY_X_START
    total_height = config.INVENTORY_Y_END - config.INVENTORY_Y_START

    cell_width = total_width // config.INVENTORY_COLS
    cell_height = total_height // config.INVENTORY_ROWS

    return cell_width, cell_height


def get_cell_bounds(row: int, col: int) -> tuple[int, int, int, int]:
    """Get the screen coordinates for a cell (x, y, width, height)."""
    cell_width, cell_height = compute_cell_dimensions()

    x = config.INVENTORY_X_START + (col * cell_width)
    y = config.INVENTORY_Y_START + (row * cell_height)

    return x, y, cell_width, cell_height


def grab_inventory_region(sct: mss, monitor: dict) -> np.ndarray:
    """Capture the inventory region of the screen."""
    region = {
        "left": monitor["left"] + config.INVENTORY_X_START,
        "top": monitor["top"] + config.INVENTORY_Y_START,
        "width": config.INVENTORY_X_END - config.INVENTORY_X_START,
        "height": config.INVENTORY_Y_END - config.INVENTORY_Y_START,
    }
    screenshot = np.array(sct.grab(region))
    return screenshot[:, :, :3]


def extract_cell_image(
    inventory_frame: np.ndarray,
    row: int,
    col: int,
) -> np.ndarray:
    """Extract a single cell from the inventory frame."""
    cell_width, cell_height = compute_cell_dimensions()

    x_start = col * cell_width
    y_start = row * cell_height
    x_end = x_start + cell_width
    y_end = y_start + cell_height

    cell = inventory_frame[y_start:y_end, x_start:x_end]
    return cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)


def match_cell_against_template(
    cell_gray: np.ndarray,
    template: np.ndarray,
) -> float:
    """Match a cell against a template, return confidence score."""
    # Resize template to match cell size if needed
    cell_h, cell_w = cell_gray.shape[:2]
    tmpl_h, tmpl_w = template.shape[:2]

    if tmpl_h > cell_h or tmpl_w > cell_w:
        # Template is larger than cell, resize template
        scale = min(cell_h / tmpl_h, cell_w / tmpl_w) * 0.9
        new_w = int(tmpl_w * scale)
        new_h = int(tmpl_h * scale)
        template = cv2.resize(template, (new_w, new_h))

    result = cv2.matchTemplate(cell_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val


def analyze_cell(
    cell_gray: np.ndarray,
    row: int,
    col: int,
    bg_template: np.ndarray,
    resource_template: np.ndarray,
) -> InventoryCell:
    """Analyze a single cell to determine its contents."""
    x, y, width, height = get_cell_bounds(row, col)

    # Check if cell matches background (empty)
    bg_confidence = match_cell_against_template(cell_gray, bg_template)
    is_empty = bg_confidence >= config.INVENTORY_BG_THRESHOLD

    # Check if cell contains a resource
    resource_confidence = match_cell_against_template(cell_gray, resource_template)
    is_resource = resource_confidence >= config.INVENTORY_RESOURCE_THRESHOLD

    return InventoryCell(
        row=row,
        col=col,
        x=x,
        y=y,
        width=width,
        height=height,
        has_item=not is_empty,
        is_resource=is_resource,
    )


def analyze_inventory(
    sct: mss,
    monitor: dict,
    bg_template: np.ndarray,
    resource_template: np.ndarray,
) -> InventoryState:
    """Capture and analyze the full inventory."""
    inventory_frame = grab_inventory_region(sct, monitor)

    cells = []
    resource_cells = []

    for row in range(config.INVENTORY_ROWS):
        for col in range(config.INVENTORY_COLS):
            cell_gray = extract_cell_image(inventory_frame, row, col)
            cell = analyze_cell(
                cell_gray, row, col, bg_template, resource_template
            )
            cells.append(cell)

            if cell.is_resource:
                resource_cells.append(cell)

    # Inventory is full if all cells have items
    is_full = all(cell.has_item for cell in cells)

    return InventoryState(
        cells=tuple(cells),
        is_full=is_full,
        resource_cells=tuple(resource_cells),
    )


def compute_random_click_position(cell: InventoryCell) -> tuple[int, int]:
    """
    Compute a random click position within the cell.
    Stays away from edges for safety.
    """
    margin_x = max(5, cell.width // 6)
    margin_y = max(5, cell.height // 6)

    # Random position within the safe area
    x = cell.x + margin_x + random.randint(0, cell.width - 2 * margin_x)
    y = cell.y + margin_y + random.randint(0, cell.height - 2 * margin_y)

    return x, y


def is_inventory_full(
    sct: mss,
    monitor: dict,
    bg_template: np.ndarray,
) -> bool:
    """
    Check if inventory is full by only scanning the last cell.
    If the last cell (row 6, col 3) has an item, inventory is full.
    """
    inventory_frame = grab_inventory_region(sct, monitor)

    last_row = config.INVENTORY_ROWS - 1
    last_col = config.INVENTORY_COLS - 1

    cell_gray = extract_cell_image(inventory_frame, last_row, last_col)

    # Check if cell matches background (empty)
    bg_confidence = match_cell_against_template(cell_gray, bg_template)
    is_empty = bg_confidence >= config.INVENTORY_BG_THRESHOLD

    return not is_empty
