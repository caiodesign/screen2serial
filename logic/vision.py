"""
Pure image recognition functions.

These functions receive data and return simple results without any mouse/click logic.
Inspired by osrs_basic_botting_functions/functions.py patterns like:
- Image_count()
- Image_Rec_single()
- image_Rec_clicker()
- Image_Rec_single_closest()
- mini_map_bool()
- Image_to_Text()
- find_Object()
- find_Object_closest()
"""

import cv2
import numpy as np
import pytesseract
from dataclasses import dataclass
from mss import mss

from .capture import load_template, grab_region, preprocess_crop


# Minimum distance (pixels) between two detections to consider them different items
MIN_DETECTION_DISTANCE = 30

# Type alias for color range: ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
ColorRange = tuple[tuple[int, int, int], tuple[int, int, int]]


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


def _get_template(template, grayscale: bool = True) -> np.ndarray:
    """
    Get template as numpy array.
    Accepts either a path string or an already-loaded numpy array.
    
    Args:
        template: Path string or numpy array
        grayscale: If True, load as grayscale. If False, load as BGR color.
    """
    if isinstance(template, str):
        return load_template(template, grayscale=grayscale)
    return template


def _capture_region(sct: mss, monitor: dict, region: Region) -> np.ndarray:
    """Capture a region and return grayscale image."""
    frame = grab_region(
        sct, monitor,
        region.x_start, region.y_start,
        region.x_end, region.y_end,
    )
    return preprocess_crop(frame)


def _capture_region_bgr(sct: mss, monitor: dict, region: Region) -> np.ndarray:
    """Capture a region and return BGR image (for color detection)."""
    return grab_region(
        sct, monitor,
        region.x_start, region.y_start,
        region.x_end, region.y_end,
    )


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
    use_color: bool = False,
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
        use_color: If True, use BGR color matching instead of grayscale.
                   Better for items with distinctive colors (e.g., grimy herbs).
    
    Returns:
        Point with absolute screen coordinates of center, or None if not found
    """
    capture_fn = _capture_region_bgr if use_color else _capture_region
    
    tmpl = _get_template(template, grayscale=not use_color)
    image = capture_fn(sct, monitor, region)
    
    result = cv2.matchTemplate(image, tmpl, cv2.TM_CCOEFF_NORMED)
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
    use_color: bool = False,
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
        use_color: If True, use BGR color matching instead of grayscale.
                   Better for items with distinctive colors (e.g., grimy herbs).
    
    Returns:
        List of Points with absolute screen coordinates
    """
    capture_fn = _capture_region_bgr if use_color else _capture_region
    
    tmpl = _get_template(template, grayscale=not use_color)
    image = capture_fn(sct, monitor, region)
    
    result = cv2.matchTemplate(image, tmpl, cv2.TM_CCOEFF_NORMED)
    
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


def detect_text(
    image: np.ndarray,
    x_range: tuple[int, int] | None = None,
    y_range: tuple[int, int] | None = None,
    preprocess: str | None = None,
    config: str = "--psm 7",
) -> str:
    """
    Detect text in an image using OCR (pytesseract).
    
    Inspired by: Image_to_Text()
    
    Args:
        image: Input image as numpy array (BGR or grayscale)
        x_range: Optional (x_start, x_end) to crop horizontally
        y_range: Optional (y_start, y_end) to crop vertically
        preprocess: Optional preprocessing mode:
            - "thresh": Binary threshold (good for clean text)
            - "blur": Median blur (reduces noise)
            - "adaptive": Adaptive threshold (good for varying lighting)
            - None: No preprocessing (default)
        config: Tesseract config string (default: --psm 7 for single line)
            Common options:
            - --psm 6: Assume uniform block of text
            - --psm 7: Treat as single text line
            - --psm 8: Treat as single word
            - --psm 13: Raw line (no OSD/script detection)
    
    Returns:
        Detected text string (stripped of whitespace)
    
    Note:
        Requires Tesseract OCR to be installed on the system.
        macOS: brew install tesseract
        Windows: https://github.com/UB-Mannheim/tesseract/wiki
        Linux: apt-get install tesseract-ocr
    """
    # Crop image if ranges provided
    img = image.copy()
    
    if y_range is not None:
        y_start, y_end = y_range
        img = img[y_start:y_end, :]
    
    if x_range is not None:
        x_start, x_end = x_range
        img = img[:, x_start:x_end]
    
    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Apply preprocessing if specified
    if preprocess == "thresh":
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    elif preprocess == "blur":
        gray = cv2.medianBlur(gray, 3)
    elif preprocess == "adaptive":
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
        )
    
    # Run OCR
    text = pytesseract.image_to_string(gray, config=config)
    
    return text.strip()


# =============================================================================
# COLOR DETECTION FUNCTIONS
# =============================================================================
# These functions detect objects by color range instead of template matching.
# Useful with RuneLite highlight plugins that mark objects with specific colors.


def _find_color_contours(
    image: np.ndarray,
    color: ColorRange,
    min_area: int = 10,
) -> list[tuple[int, int, int, int, float]]:
    """
    Find all contours matching a color range.
    
    Args:
        image: BGR image to search
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        min_area: Minimum contour area to consider valid
    
    Returns:
        List of (x, y, w, h, area) tuples for each contour's bounding rect
    """
    lower = np.array(color[0], dtype="uint8")
    upper = np.array(color[1], dtype="uint8")
    
    # Create mask for pixels within color range
    mask = cv2.inRange(image, lower, upper)
    
    # Apply threshold and find contours
    _, thresh = cv2.threshold(mask, 40, 255, 0)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    # Filter by area and get bounding rectangles
    results = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(contour)
            results.append((x, y, w, h, area))
    
    return results


def color_exists(
    sct: mss,
    monitor: dict,
    color: ColorRange,
    region: Region,
    min_area: int = 10,
) -> bool:
    """
    Check if a color exists in region.
    
    Inspired by: find_Object() existence check
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        region: Region to search in
        min_area: Minimum contour area to consider valid
    
    Returns:
        True if color found, False otherwise
    """
    image = _capture_region_bgr(sct, monitor, region)
    contours = _find_color_contours(image, color, min_area)
    return len(contours) > 0


def find_by_color(
    sct: mss,
    monitor: dict,
    color: ColorRange,
    region: Region,
    min_area: int = 10,
) -> Point | None:
    """
    Find the largest object matching a color in region.
    
    Inspired by: find_Object()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        region: Region to search in
        min_area: Minimum contour area to consider valid
    
    Returns:
        Point with absolute screen coordinates of center, or None if not found
    """
    image = _capture_region_bgr(sct, monitor, region)
    contours = _find_color_contours(image, color, min_area)
    
    if not contours:
        return None
    
    # Find largest contour by area
    largest = max(contours, key=lambda c: c[4])
    x, y, w, h, area = largest
    
    # Calculate center in absolute screen coordinates
    center_x = region.x_start + x + (w // 2)
    center_y = region.y_start + y + (h // 2)
    
    # Use area as confidence (normalized wouldn't make sense here)
    return Point(x=center_x, y=center_y, confidence=float(area))


def find_all_by_color(
    sct: mss,
    monitor: dict,
    color: ColorRange,
    region: Region,
    min_area: int = 10,
) -> list[Point]:
    """
    Find all objects matching a color in region.
    
    Inspired by: find_Object_closest() contour iteration
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        region: Region to search in
        min_area: Minimum contour area to consider valid
    
    Returns:
        List of Points with absolute screen coordinates, sorted by area (largest first)
    """
    image = _capture_region_bgr(sct, monitor, region)
    contours = _find_color_contours(image, color, min_area)
    
    if not contours:
        return []
    
    # Sort by area descending (largest first)
    contours.sort(key=lambda c: c[4], reverse=True)
    
    points = []
    for x, y, w, h, area in contours:
        center_x = region.x_start + x + (w // 2)
        center_y = region.y_start + y + (h // 2)
        points.append(Point(x=center_x, y=center_y, confidence=float(area)))
    
    return points


def find_closest_by_color(
    sct: mss,
    monitor: dict,
    color: ColorRange,
    region: Region,
    from_pos: tuple[int, int],
    min_area: int = 10,
) -> Point | None:
    """
    Find the closest object matching a color to a given position.
    
    Inspired by: find_Object_closest()
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        region: Region to search in
        from_pos: (x, y) position to measure distance from
        min_area: Minimum contour area to consider valid
    
    Returns:
        Point closest to from_pos, or None if no matches found
    """
    items = find_all_by_color(sct, monitor, color, region, min_area)
    
    if not items:
        return None
    
    def distance_to(point: Point) -> float:
        return ((point.x - from_pos[0])**2 + (point.y - from_pos[1])**2) ** 0.5
    
    return min(items, key=distance_to)


def count_by_color(
    sct: mss,
    monitor: dict,
    color: ColorRange,
    region: Region,
    min_area: int = 10,
) -> int:
    """
    Count objects matching a color in region.
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        color: Color range ((B_lo, G_lo, R_lo), (B_hi, G_hi, R_hi))
        region: Region to search in
        min_area: Minimum contour area to consider valid
    
    Returns:
        Number of contours found
    """
    image = _capture_region_bgr(sct, monitor, region)
    contours = _find_color_contours(image, color, min_area)
    return len(contours)
