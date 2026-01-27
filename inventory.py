import cv2
import numpy as np
import random
import os
import time
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

    # Apply same preprocessing as main detection (GaussianBlur)
    resource_template = cv2.GaussianBlur(resource_template, (5, 5), 0)
    bg_template = cv2.GaussianBlur(bg_template, (5, 5), 0)

    # Save processed templates in debug mode for comparison
    if config.DEBUG:
        debug_dir = os.path.join(config.DEBUG_DIR, "inventory")
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(f"{debug_dir}/template_resource_PROCESSED.png", resource_template)
        cv2.imwrite(f"{debug_dir}/template_bg_PROCESSED.png", bg_template)
        print(f"[DEBUG] Saved processed templates to {debug_dir}/")

    return resource_template, bg_template


def compute_item_dimensions() -> tuple[int, int]:
    """Calculate the dimensions of the actual item content (without padding)."""
    total_width = config.INVENTORY_X_END - config.INVENTORY_X_START
    total_height = config.INVENTORY_Y_END - config.INVENTORY_Y_START

    # Total padding: each item has padding on both sides
    total_padding_x = config.INVENTORY_COLS * (config.INVENTORY_ITEM_PADDING_X * 2)
    total_padding_y = config.INVENTORY_ROWS * (config.INVENTORY_ITEM_PADDING_Y * 2)

    # Usable space = total - outer margins - all item padding
    items_width = total_width - config.INVENTORY_OUTER_MARGIN_X - total_padding_x
    items_height = total_height - config.INVENTORY_OUTER_MARGIN_Y - total_padding_y

    item_width = items_width // config.INVENTORY_COLS
    item_height = items_height // config.INVENTORY_ROWS

    return item_width, item_height


def compute_cell_dimensions() -> tuple[int, int]:
    """Calculate the dimensions of each inventory cell (item + its padding)."""
    item_width, item_height = compute_item_dimensions()

    # Cell = item + padding on each side
    cell_width = item_width + (config.INVENTORY_ITEM_PADDING_X * 2)
    cell_height = item_height + (config.INVENTORY_ITEM_PADDING_Y * 2)

    return cell_width, cell_height


def get_cell_bounds(row: int, col: int) -> tuple[int, int, int, int]:
    """Get the screen coordinates for a cell (x, y, width, height)."""
    cell_width, cell_height = compute_cell_dimensions()

    # Outer margin is split on each side
    outer_margin_x = config.INVENTORY_OUTER_MARGIN_X // 2
    outer_margin_y = config.INVENTORY_OUTER_MARGIN_Y // 2

    x = config.INVENTORY_X_START + outer_margin_x + (col * cell_width)
    y = config.INVENTORY_Y_START + outer_margin_y + (row * cell_height)

    return x, y, cell_width, cell_height


def grab_inventory_region(sct: mss, monitor: dict) -> np.ndarray:
    """Capture the inventory region of the screen (usable area without outer margins)."""
    outer_margin_x = config.INVENTORY_OUTER_MARGIN_X // 2
    outer_margin_y = config.INVENTORY_OUTER_MARGIN_Y // 2

    total_width = config.INVENTORY_X_END - config.INVENTORY_X_START
    total_height = config.INVENTORY_Y_END - config.INVENTORY_Y_START

    region = {
        "left": monitor["left"] + config.INVENTORY_X_START + outer_margin_x,
        "top": monitor["top"] + config.INVENTORY_Y_START + outer_margin_y,
        "width": total_width - config.INVENTORY_OUTER_MARGIN_X,
        "height": total_height - config.INVENTORY_OUTER_MARGIN_Y,
    }
    screenshot = np.array(sct.grab(region))
    return screenshot[:, :, :3]


def extract_cell_image(
    inventory_frame: np.ndarray,
    row: int,
    col: int,
) -> np.ndarray:
    """Extract a small center sample from a cell."""
    cell_width, cell_height = compute_cell_dimensions()
    sample_size = config.INVENTORY_SAMPLE_SIZE

    # Calculate cell position in the inventory frame
    cell_x = col * cell_width
    cell_y = row * cell_height

    # Calculate center of the cell
    center_x = cell_x + cell_width // 2
    center_y = cell_y + cell_height // 2

    # Extract small region from center
    half_sample = sample_size // 2
    x_start = center_x - half_sample
    y_start = center_y - half_sample
    x_end = x_start + sample_size
    y_end = y_start + sample_size

    cell = inventory_frame[y_start:y_end, x_start:x_end]
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    # Apply same preprocessing as main detection (GaussianBlur)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def match_cell_against_template(
    cell_gray: np.ndarray,
    template: np.ndarray,
) -> float:
    """Match a cell sample against a template, return confidence score."""
    cell_h, cell_w = cell_gray.shape[:2]
    tmpl_h, tmpl_w = template.shape[:2]

    # Resize template to match sample size if needed
    if tmpl_h != cell_h or tmpl_w != cell_w:
        template = cv2.resize(template, (cell_w, cell_h))

    # Direct pixel comparison using normalized correlation
    result = cv2.matchTemplate(cell_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val


def analyze_cell(
    cell_gray: np.ndarray,
    row: int,
    col: int,
    bg_template: np.ndarray,
    resource_template: np.ndarray,
    save_debug: bool = False,
) -> InventoryCell:
    """Analyze a single cell to determine its contents."""
    x, y, width, height = get_cell_bounds(row, col)

    # Check if cell matches background (empty)
    bg_confidence = match_cell_against_template(cell_gray, bg_template)
    is_empty = bg_confidence >= config.INVENTORY_BG_THRESHOLD

    # Check if cell contains a resource
    resource_confidence = match_cell_against_template(cell_gray, resource_template)
    is_resource = resource_confidence >= config.INVENTORY_RESOURCE_THRESHOLD

    # Save debug images for first few cells to help diagnose
    if save_debug and config.DEBUG:
        debug_dir = os.path.join(config.DEBUG_DIR, "inventory")
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(
            f"{debug_dir}/cell_r{row}_c{col}_bg{bg_confidence:.3f}_res{resource_confidence:.3f}.png",
            cell_gray
        )

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

    # Save the full inventory frame in debug mode
    if config.DEBUG:
        debug_dir = os.path.join(config.DEBUG_DIR, "inventory")
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(f"{debug_dir}/inventory_frame_FULL.png", inventory_frame)

    cells = []
    resource_cells = []

    for row in range(config.INVENTORY_ROWS):
        for col in range(config.INVENTORY_COLS):
            cell_gray = extract_cell_image(inventory_frame, row, col)
            # Save debug for first row and last row to help diagnose
            save_debug = config.DEBUG and (row == 0 or row == config.INVENTORY_ROWS - 1)
            cell = analyze_cell(
                cell_gray, row, col, bg_template, resource_template, save_debug=save_debug
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
    Compute a random click position within the actual item area.
    Accounts for item padding and adds extra safety margin.
    """
    # Item padding on each side
    padding_x = config.INVENTORY_ITEM_PADDING_X
    padding_y = config.INVENTORY_ITEM_PADDING_Y

    # Add a small extra safety margin inside the item
    safety = 3
    total_margin_x = padding_x + safety
    total_margin_y = padding_y + safety

    # Random position within the safe item area
    safe_width = cell.width - (2 * total_margin_x)
    safe_height = cell.height - (2 * total_margin_y)

    x = cell.x + total_margin_x + random.randint(0, max(0, safe_width))
    y = cell.y + total_margin_y + random.randint(0, max(0, safe_height))

    return x, y


def save_inventory_debug(cell_gray: np.ndarray, bg_template: np.ndarray, bg_confidence: float, is_empty: bool) -> None:
    """Save debug images when inventory detection seems wrong."""
    if not config.DEBUG:
        return

    debug_dir = os.path.join(config.DEBUG_DIR, "inventory")
    os.makedirs(debug_dir, exist_ok=True)

    timestamp = int(time.time() * 1000)
    
    # Save with clear names for easy comparison
    # Cell capture (what we're scanning)
    cv2.imwrite(f"{debug_dir}/cell_CAPTURED_latest.png", cell_gray)
    cv2.imwrite(f"{debug_dir}/{timestamp}_cell_conf{bg_confidence:.3f}_isEmpty{is_empty}.png", cell_gray)


def is_inventory_full(
    sct: mss,
    monitor: dict,
    bg_template: np.ndarray,
    debug: bool = False,
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

    if debug or not is_empty:
        print(f"[INVENTORY CHECK] Last cell bg_confidence={bg_confidence:.3f}, threshold={config.INVENTORY_BG_THRESHOLD}, is_empty={is_empty}")
        # Save debug images when we think inventory is full (helps diagnose false positives)
        save_inventory_debug(cell_gray, bg_template, bg_confidence, is_empty)

    return not is_empty
