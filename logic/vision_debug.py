"""
Debug proxy module for vision functions.

This module wraps pure vision functions with debug visualization capabilities.
Import from here instead of vision.py when DEBUG=True to see live debug windows.

The pure functions in vision.py remain untouched - all debug logic is isolated here.

Uses a background thread for OpenCV windows to prevent "not responding" issues.
"""

import functools
import cv2
import numpy as np
import threading
import queue
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


# =========================
# THREADED WINDOW MANAGER
# =========================

class DebugWindowManager:
    """
    Manages OpenCV debug windows in a background thread.
    
    This prevents the "not responding" issue by keeping the window
    event loop running independently of the main bot loop.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one window manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._frame_queue = queue.Queue(maxsize=1)  # Only keep latest frame
        self._running = False
        self._thread = None
        self._should_pause = threading.Event()
        self._pause_acknowledged = threading.Event()
        self._initialized = True
    
    def start(self):
        """Start the background window thread."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._window_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the background window thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        cv2.destroyAllWindows()
    
    def update(self, region_frame: np.ndarray, template_frame: np.ndarray, is_match: bool):
        """
        Send new frames to display.
        
        Non-blocking - drops old frames if queue is full.
        """
        self.start()  # Auto-start on first use
        
        try:
            # Clear old frame if any
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
            
            # Add new frame
            self._frame_queue.put_nowait((region_frame.copy(), template_frame.copy(), is_match))
        except queue.Full:
            pass  # Skip this frame
    
    def pause_for_inspection(self):
        """
        Pause and wait for user keypress (used in pause_on_fail mode).
        
        This signals the window thread to wait for a keypress.
        """
        self._pause_acknowledged.clear()
        self._should_pause.set()
        # Wait for the window thread to acknowledge and handle the pause
        self._pause_acknowledged.wait(timeout=60.0)  # 60 second timeout
    
    def _window_loop(self):
        """Background thread that manages OpenCV windows."""
        while self._running:
            try:
                # Check for new frames (with timeout to keep event loop responsive)
                try:
                    region_frame, template_frame, is_match = self._frame_queue.get(timeout=0.05)
                    cv2.imshow(WINDOW_REGION, region_frame)
                    cv2.imshow(WINDOW_TEMPLATE, template_frame)
                except queue.Empty:
                    pass
                
                # Check if we should pause for inspection
                if self._should_pause.is_set():
                    self._should_pause.clear()
                    print("[DEBUG] Match FAILED - Press any key in debug window to continue...")
                    cv2.waitKey(0)  # Wait for any key
                    self._pause_acknowledged.set()
                else:
                    # Process window events (non-blocking)
                    key = cv2.waitKey(30) & 0xFF  # 30ms for responsive windows
                    if key == ord('q'):
                        print("[DEBUG] 'q' pressed - closing debug windows")
                        cv2.destroyAllWindows()
                        self._running = False
                        break
                        
            except Exception as e:
                print(f"[DEBUG] Window error: {e}")
                break
        
        cv2.destroyAllWindows()


# Global window manager instance
_window_manager = None


def _get_window_manager() -> DebugWindowManager:
    """Get or create the singleton window manager."""
    global _window_manager
    if _window_manager is None:
        _window_manager = DebugWindowManager()
    return _window_manager


# =========================
# VISUALIZATION HELPERS
# =========================

def _draw_match_result(
    gray: np.ndarray,
    template: np.ndarray,
    result: Any,
    region: Region,
    threshold: float,
    is_match: bool,
    template_name: str = "unknown",
) -> np.ndarray:
    """Draw match result on the captured region image."""
    # Convert to BGR for colored drawing
    output = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    tmpl_h, tmpl_w = template.shape[:2]
    top_left = None
    bottom_right = None
    confidence = 0.0
    
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
    if top_left is not None and bottom_right is not None:
        color = (0, 255, 0) if is_match else (0, 0, 255)  # Green if match, red if not
        cv2.rectangle(output, top_left, bottom_right, color, 2)
    
    # Add text overlay with match info
    text_color = (0, 255, 0) if is_match else (0, 0, 255)
    cv2.putText(
        output,
        f"Template: {template_name}",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 0),  # Yellow for visibility
        1,
    )
    cv2.putText(
        output,
        f"Conf: {confidence:.3f} / Thresh: {threshold:.2f}",
        (10, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        text_color,
        2,
    )
    cv2.putText(
        output,
        f"Region: ({region.x_start},{region.y_start})-({region.x_end},{region.y_end})",
        (10, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        output,
        f"Match: {'YES' if is_match else 'NO'}",
        (10, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        text_color,
        2,
    )
    
    return output


def _show_debug_visualization(
    gray: np.ndarray,
    tmpl: np.ndarray,
    region: Region,
    threshold: float,
    result: Any,
    is_match: bool,
    template_name: str = "unknown",
) -> None:
    """
    Send debug visualization to the background window thread.
    
    Args:
        gray: Pre-captured grayscale region (same one used for matching)
        tmpl: Pre-loaded template (same one used for matching)
        region: Region info for display
        threshold: Threshold used for matching
        result: Result from the vision function
        is_match: Whether the match was successful
        template_name: Name/path of the template for display
    """
    
    # Draw match result on region
    region_display = _draw_match_result(gray, tmpl, result, region, threshold, is_match, template_name)
    
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
    
    # Send to window manager (non-blocking)
    manager = _get_window_manager()
    manager.update(region_display, template_display, is_match)
    
    # Handle pause_on_fail mode
    mode = getattr(config, 'DEBUG_WINDOW_MODE', 'live')
    if mode == "pause_on_fail" and not is_match:
        manager.pause_for_inspection()


def with_debug_window(func: Callable) -> Callable:
    """
    Decorator that adds debug visualization to vision functions.
    
    The decorated function will show debug windows after each call,
    displaying the captured region and template used for matching.
    
    IMPORTANT: Captures screenshot BEFORE calling the function so we display
    exactly what was (approximately) used for matching, not a later frame.
    """
    @functools.wraps(func)
    def wrapper(sct, monitor, template, region: Region, threshold: float = 0.8, *args, **kwargs):
        # Capture BEFORE calling the function - this is what we'll display
        # This ensures we show the same (or very close) frame used for matching
        tmpl = _get_template(template)
        gray = _capture_region(sct, monitor, region)
        
        # Extract template name for debug display
        if isinstance(template, str):
            # Get just the filename from the path
            import os
            template_name = os.path.basename(template)
        else:
            template_name = f"array_{tmpl.shape}"
        
        # Call the original pure function (it will do its own capture internally,
        # but timing should be nearly identical)
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
        
        # Show debug visualization using the pre-captured frame
        _show_debug_visualization(gray, tmpl, region, threshold, result, is_match, template_name)
        
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
    import os
    
    # Capture BEFORE calling the function
    tmpl = _get_template(template)
    gray = _capture_region(sct, monitor, region)
    
    # Extract template name for debug display
    if isinstance(template, str):
        template_name = os.path.basename(template)
    else:
        template_name = f"array_{tmpl.shape}"
    
    result = _find_closest_template(sct, monitor, template, region, from_pos, threshold)
    is_match = result is not None
    _show_debug_visualization(gray, tmpl, region, threshold, result, is_match, template_name)
    return result


# Re-export unchanged utilities
from .vision import (
    Region,
    Point,
    sort_by_position,
    get_last_item_bottom_right,
)


# Cleanup function for graceful shutdown
def cleanup_debug_windows():
    """Stop the debug window manager. Call this on program exit."""
    global _window_manager
    if _window_manager is not None:
        _window_manager.stop()
        _window_manager = None
