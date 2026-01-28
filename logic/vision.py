"""
Pure image recognition functions.

These functions receive data and return simple results without any mouse/click logic.
Inspired by osrs_basic_botting_functions/functions.py patterns like:
- Image_count()
- Image_Rec_single()
- image_Rec_clicker()
- Image_Rec_single_closest()
- mini_map_bool()
"""

import cv2
import numpy as np
from dataclasses import dataclass
from mss import mss

from .capture import load_template, grab_region, preprocess_crop


# Minimum distance (pixels) between two detections to consider them different items
MIN_DETECTION_DISTANCE = 30


@dataclass(frozen=True)
class Region:
    """Defines a screen region for capture."""
    x_start: int
    y_start: int
    x_end: int
    y_end: int
    
    @property
    def width(self) -> int:
        return self.x_end - self.x_start
    
    @property
    def height(self) -> int:
        return self.y_end - self.y_start


@dataclass(frozen=True)
class Point:
    """A point on the screen with optional confidence."""
    x: int
    y: int
    confidence: float = 0.0


def _get_template(template) -> np.ndarray:
    """
    Get template as numpy array.
    Accepts either a path string or an already-loaded numpy array.
    """
    if isinstance(template, str):
        return load_template(template)
    return template


def _capture_region(sct: mss, monitor: dict, region: Region) -> np.ndarray:
    """Capture a region and return grayscale image."""
    frame = grab_region(
        sct, monitor,
        region.x_start, region.y_start,
        region.x_end, region.y_end,
    )
    return preprocess_crop(frame)


def template_exists(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> bool:
    """
    Check if template exists in region.
    
    Inspired by: mini_map_bool()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Template image path (str) or numpy array
        region: Region to search in
        threshold: Match threshold (0.0-1.0)
    
    Returns:
        True if template found, False otherwise
    """
    tmpl = _get_template(template)
    gray = _capture_region(sct, monitor, region)
    
    result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    
    return max_val >= threshold


def find_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> Point | None:
    """
    Find the best match of template in region.
    
    Inspired by: Image_Rec_single()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Template image path (str) or numpy array
        region: Region to search in
        threshold: Match threshold (0.0-1.0)
    
    Returns:
        Point with absolute screen coordinates of center, or None if not found
    """
    tmpl = _get_template(template)
    gray = _capture_region(sct, monitor, region)
    
    result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if max_val < threshold:
        return None
    
    # Calculate center point in absolute screen coordinates
    tmpl_h, tmpl_w = tmpl.shape[:2]
    center_x = region.x_start + max_loc[0] + (tmpl_w // 2)
    center_y = region.y_start + max_loc[1] + (tmpl_h // 2)
    
    return Point(x=center_x, y=center_y, confidence=max_val)


def count_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> int:
    """
    Count occurrences of template in region.
    
    Inspired by: Image_count()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Template image path (str) or numpy array
        region: Region to search in
        threshold: Match threshold (0.0-1.0)
    
    Returns:
        Number of unique matches found
    """
    items = find_all_templates(sct, monitor, template, region, threshold)
    return len(items)


def find_all_templates(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    threshold: float = 0.8,
) -> list[Point]:
    """
    Find all occurrences of template in region.
    
    Inspired by: image_Rec_clicker() (but without clicking)
    
    Uses distance-based deduplication to avoid counting overlapping matches.
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Template image path (str) or numpy array
        region: Region to search in
        threshold: Match threshold (0.0-1.0)
    
    Returns:
        List of Points with absolute screen coordinates
    """
    tmpl = _get_template(template)
    gray = _capture_region(sct, monitor, region)
    
    result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    
    # Find all matches above threshold
    locations = np.where(result >= threshold)
    
    if len(locations[0]) == 0:
        return []
    
    # Get template dimensions for calculating center points
    tmpl_h, tmpl_w = tmpl.shape[:2]
    
    # Get all detection points with their confidence
    points = list(zip(locations[1], locations[0]))  # (x, y) pairs
    
    # Get confidence values and create list of (x, y, confidence)
    detections = []
    for x, y in points:
        conf = result[y, x]
        # Calculate center point (relative to region)
        center_x = x + (tmpl_w // 2)
        center_y = y + (tmpl_h // 2)
        detections.append((center_x, center_y, conf))
    
    # Sort by confidence (highest first)
    detections.sort(key=lambda d: d[2], reverse=True)
    
    # Filter out duplicates using distance-based deduplication
    unique_items: list[Point] = []
    
    for cx, cy, conf in detections:
        # Check if this detection is too close to an already picked item
        is_duplicate = False
        for item in unique_items:
            # Compare in relative coordinates (before adding region offset)
            rel_item_x = item.x - region.x_start
            rel_item_y = item.y - region.y_start
            dist = ((cx - rel_item_x)**2 + (cy - rel_item_y)**2) ** 0.5
            if dist < MIN_DETECTION_DISTANCE:
                is_duplicate = True
                break
        
        if not is_duplicate:
            # Convert to absolute screen coordinates
            abs_x = region.x_start + cx
            abs_y = region.y_start + cy
            unique_items.append(Point(x=abs_x, y=abs_y, confidence=conf))
    
    return unique_items


def find_closest_template(
    sct: mss,
    monitor: dict,
    template,
    region: Region,
    from_pos: tuple[int, int],
    threshold: float = 0.8,
) -> Point | None:
    """
    Find the closest match of template to a given position.
    
    Inspired by: Image_Rec_single_closest()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Template image path (str) or numpy array
        region: Region to search in
        from_pos: (x, y) position to measure distance from
        threshold: Match threshold (0.0-1.0)
    
    Returns:
        Point closest to from_pos, or None if no matches found
    """
    items = find_all_templates(sct, monitor, template, region, threshold)
    
    if not items:
        return None
    
    # Find item with minimum distance to from_pos
    def distance_to(point: Point) -> float:
        return ((point.x - from_pos[0])**2 + (point.y - from_pos[1])**2) ** 0.5
    
    return min(items, key=distance_to)


def sort_by_position(
    items: list[Point],
    top_to_bottom: bool = True,
    left_to_right: bool = True,
) -> list[Point]:
    """
    Sort points by position (useful for efficient drop order).
    
    Args:
        items: List of Points to sort
        top_to_bottom: If True, sort Y ascending (top first)
        left_to_right: If True, sort X ascending (left first)
    
    Returns:
        Sorted list of Points
    """
    y_mult = 1 if top_to_bottom else -1
    x_mult = 1 if left_to_right else -1
    
    return sorted(items, key=lambda p: (p.y * y_mult, p.x * x_mult))


def get_last_item_bottom_right(items: list[Point]) -> Point | None:
    """
    Get the last item using bottom-right priority.
    
    Priority: bottom row first, then rightmost column in that row.
    Useful for enchanting where we want to click the last unenchanted item.
    
    Args:
        items: List of Points (item positions)
    
    Returns:
        The bottom-right most Point, or None if list is empty
    """
    if not items:
        return None
    # Sort by Y descending (bottom first), then X descending (right first)
    sorted_items = sorted(items, key=lambda p: (-p.y, -p.x))
    return sorted_items[0]


def is_inventory_opened(
    sct: mss,
    monitor: dict,
    icon_x: int = 960,
    icon_y: int = 960,
    icon_size: int = 36,
    threshold: float = 0.10,
) -> bool:
    """
    Check if inventory tab is opened by detecting red background on menu icon.
    
    Uses HSV color detection to distinguish:
    - Opened inventory: Red background on icon
    - Closed inventory: Gray background on icon
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        icon_x: X coordinate of inventory icon center
        icon_y: Y coordinate of inventory icon center
        icon_size: Size of region to capture around icon
        threshold: Minimum ratio of red pixels to consider "opened"
    
    Returns:
        True if inventory is opened (red detected), False otherwise
    """
    # Capture small region around the menu icon
    half_size = icon_size // 2
    frame = grab_region(
        sct, monitor,
        icon_x - half_size, icon_y - half_size,
        icon_x + half_size, icon_y + half_size,
    )
    
    # Convert BGR to HSV for color detection
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Red HSV ranges (red wraps around hue wheel at 0 and 180)
    # Lower red range: H=0-10
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    # Upper red range: H=170-180
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    # Create masks for both red ranges
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    
    # Calculate ratio of red pixels
    total_pixels = mask1.size
    red_pixels = np.count_nonzero(mask1) + np.count_nonzero(mask2)
    red_ratio = red_pixels / total_pixels
    
    return red_ratio >= threshold
