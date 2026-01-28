"""
Debug proxy module for vision functions.

This module wraps pure vision functions with debug visualization capabilities.
Import from here instead of vision.py when DEBUG=True to see live debug windows.

The pure functions in vision.py remain untouched - all debug logic is isolated here.
"""

import functools
import cv2
import numpy as np
from typing import Callable, Any

import config
from .vision import (
    find_template as _find_template,
    find_all_templates as _find_all_templates,
    template_exists as _template_exists,
    count_template as _count_template,
    find_closest_template as _find_closest_template,
    Region,
    Point,
    _get_template,
    _capture_region,
)


# Window names for debug visualization
WINDOW_REGION = "Debug: Captured Region"
WINDOW_TEMPLATE = "Debug: Template"


def _draw_match_result(
    gray: np.ndarray,
    template: np.ndarray,
    result: Any,
    region: Region,
    threshold: float,
    is_match: bool,
) -> np.ndarray:
    """Draw match result on the captured region image."""
    # Convert to BGR for colored drawing
    output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    tmpl_h, tmpl_w = template.shape[:2]
    
    if result is not None:
        # For Point results (find_template returns Point)
        if isinstance(result, Point):
            # Convert absolute coords back to relative for drawing
            rel_x = result.x - region.x_start - (tmpl_w // 2)
            rel_y = result.y - region.y_start - (tmpl_h // 2)
            top_left = (rel_x, rel_y)
            bottom_right = (rel_x + tmpl_w, rel_y + tmpl_h)
            confidence = result.confidence
        # For list results (find_all_templates returns list[Point])
        elif isinstance(result, list) and len(result) > 0:
            # Draw all matches
            for pt in result:
                rel_x = pt.x - region.x_start - (tmpl_w // 2)
                rel_y = pt.y - region.y_start - (tmpl_h // 2)
                color = (0, 255, 0)  # Green for all found items
                cv2.rectangle(output, (rel_x, rel_y), (rel_x + tmpl_w, rel_y + tmpl_h), color, 2)
            confidence = result[0].confidence if result else 0.0
            top_left = None  # Already drew rectangles
        # For bool results (template_exists)
        elif isinstance(result, bool):
            # Need to re-run match to get location for visualization
            match_result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(match_result)
            top_left = max_loc
            bottom_right = (max_loc[0] + tmpl_w, max_loc[1] + tmpl_h)
            confidence = max_val
        else:
            top_left = None
            confidence = 0.0
    else:
        # No match - still show where best match would be
        match_result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(match_result)
        top_left = max_loc
        bottom_right = (max_loc[0] + tmpl_w, max_loc[1] + tmpl_h)
        confidence = max_val
    
    # Draw rectangle if we have coordinates
    if top_left is not None:
        color = (0, 255, 0) if is_match else (0, 0, 255)  # Green if match, red if not
        cv2.rectangle(output, top_left, bottom_right, color, 2)
    
    # Add text overlay with match info
    text_color = (0, 255, 0) if is_match else (0, 0, 255)
    cv2.putText(
        output,
        f"Conf: {confidence:.3f} / Thresh: {threshold:.2f}",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        text_color,
        2,
    )
    cv2.putText(
        output,
        f"Region: ({region.x_start},{region.y_start})-({region.x_end},{region.y_end})",
        (10, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        output,
        f"Match: {'YES' if is_match else 'NO'}",
        (10, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        text_color,
        2,
    )
    
    return output


def _show_debug_visualization(
    sct,
    monitor: dict,
    template,
    region: Region,
    threshold: float,
    result: Any,
    is_match: bool,
) -> bool:
    """
    Show debug windows with captured region and template.
    
    Returns False if 'q' was pressed to quit, True otherwise.
    """
    # Get template as numpy array
    tmpl = _get_template(template)
    
    # Capture the region for visualization
    gray = _capture_region(sct, monitor, region)
    
    # Draw match result on region
    region_display = _draw_match_result(gray, tmpl, result, region, threshold, is_match)
    
    # Scale down if too large
    max_display_height = 600
    if region_display.shape[0] > max_display_height:
        scale = max_display_height / region_display.shape[0]
        region_display = cv2.resize(region_display, None, fx=scale, fy=scale)
    
    # Prepare template display (scale up small templates for visibility)
    template_display = cv2.cvtColor(tmpl, cv2.COLOR_GRAY2BGR)
    min_display_size = 150
    if tmpl.shape[0] < min_display_size or tmpl.shape[1] < min_display_size:
        scale_factor = max(min_display_size / tmpl.shape[0], min_display_size / tmpl.shape[1])
        template_display = cv2.resize(
            template_display, None,
            fx=scale_factor, fy=scale_factor,
            interpolation=cv2.INTER_NEAREST
        )
    
    # Add template info text
    cv2.putText(
        template_display,
        f"Size: {tmpl.shape[1]}x{tmpl.shape[0]}",
        (5, template_display.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (255, 255, 255),
        1,
    )
    
    # Show windows
    cv2.imshow(WINDOW_REGION, region_display)
    cv2.imshow(WINDOW_TEMPLATE, template_display)
    
    # Handle window mode
    mode = getattr(config, 'DEBUG_WINDOW_MODE', 'live')
    
    if mode == "pause_on_fail" and not is_match:
        # Wait for any key press when match fails
        print(f"[DEBUG] Match FAILED - Press any key to continue...")
        cv2.waitKey(0)
    else:
        # Non-blocking wait, check for 'q' to quit
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            cv2.destroyAllWindows()
            return False
    
    return True


def with_debug_window(func: Callable) -> Callable:
    """
    Decorator that adds debug visualization to vision functions.
    
    The decorated function will show debug windows after each call,
    displaying the captured region and template used for matching.
    """
    @functools.wraps(func)
    def wrapper(sct, monitor, template, region: Region, threshold: float = 0.8, *args, **kwargs):
        # Call the original pure function
        result = func(sct, monitor, template, region, threshold, *args, **kwargs)
        
        # Determine if it was a match
        if result is None:
            is_match = False
        elif isinstance(result, bool):
            is_match = result
        elif isinstance(result, list):
            is_match = len(result) > 0
        elif isinstance(result, Point):
            is_match = True
        elif isinstance(result, int):
            is_match = result > 0
        else:
            is_match = result is not None
        
        # Show debug visualization
        _show_debug_visualization(sct, monitor, template, region, threshold, result, is_match)
        
        return result
    
    return wrapper


# =========================
# WRAPPED VISION FUNCTIONS
# =========================
# These are the debug-enabled versions of the pure vision functions.
# Import these when DEBUG=True.

find_template = with_debug_window(_find_template)
find_all_templates = with_debug_window(_find_all_templates)
template_exists = with_debug_window(_template_exists)
count_template = with_debug_window(_count_template)


def find_closest_template_debug(
    sct,
    monitor: dict,
    template,
    region: Region,
    from_pos: tuple[int, int],
    threshold: float = 0.8,
) -> Point | None:
    """Debug wrapper for find_closest_template (has extra from_pos param)."""
    result = _find_closest_template(sct, monitor, template, region, from_pos, threshold)
    is_match = result is not None
    _show_debug_visualization(sct, monitor, template, region, threshold, result, is_match)
    return result


# Re-export unchanged utilities
from .vision import (
    Region,
    Point,
    sort_by_position,
    get_last_item_bottom_right,
)
