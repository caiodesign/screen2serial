import cv2
import numpy as np
import os
from dataclasses import dataclass
from mss import mss


@dataclass(frozen=True)
class MatchResult:
    """Immutable result from template matching."""
    gray: np.ndarray
    result: np.ndarray
    confidence: float
    matched: bool
    max_loc: tuple[int, int]  # Location of best match


def load_template(path: str, grayscale: bool = True) -> np.ndarray:
    """Load template image without blur (matching opencv_tutorials approach).
    
    Args:
        path: Path to the template image
        grayscale: If True, convert to grayscale. If False, keep BGR color.
    """
    template = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if template is None:
        raise RuntimeError(f"Template not found: {path}")

    if grayscale:
        # Convert to grayscale if needed (handles RGBA/RGB/BGR)
        if len(template.shape) == 3:
            if template.shape[2] == 4:
                # RGBA - convert to grayscale
                template = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
            else:
                # BGR - convert to grayscale
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        # Keep color but ensure BGR format
        if len(template.shape) == 3 and template.shape[2] == 4:
            # RGBA - convert to BGR
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2BGR)
        elif len(template.shape) == 2:
            # Grayscale - convert to BGR
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    return template


def crop_template(
    template: np.ndarray,
    top: int = 0,
    bottom: int = 0,
    left: int = 0,
    right: int = 0,
) -> np.ndarray:
    """
    Crop a template by removing pixels from each edge.

    Use when stacked labels or borders interfere with matching.
    """
    h, w = template.shape[:2]
    if top < 0 or bottom < 0 or left < 0 or right < 0:
        raise ValueError("crop_template values must be >= 0")
    if top + bottom >= h or left + right >= w:
        raise ValueError("crop_template crop exceeds template size")
    if top == bottom == left == right == 0:
        return template
    return template[top : h - bottom, left : w - right]




def create_screen_capturer() -> tuple[mss, dict]:
    """Create mss screen capturer and get primary monitor."""
    sct = mss()
    monitor = sct.monitors[1]
    return sct, monitor


def grab_screen(sct: mss, monitor: dict) -> np.ndarray:
    """Capture the screen and return BGR frame."""
    screenshot = np.array(sct.grab(monitor))
    return screenshot[:, :, :3]


def grab_region(
    sct: mss,
    monitor: dict,
    x_start: int,
    y_start: int,
    x_end: int,
    y_end: int,
) -> np.ndarray:
    """Capture a specific region of the screen."""
    region = {
        "left": monitor["left"] + x_start,
        "top": monitor["top"] + y_start,
        "width": x_end - x_start,
        "height": y_end - y_start,
    }
    screenshot = np.array(sct.grab(region))
    return screenshot[:, :, :3]  # Remove alpha channel


def preprocess_crop(crop: np.ndarray) -> np.ndarray:
    """Convert to grayscale only - no blur (matching opencv_tutorials approach)."""
    return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)


def match_template(
    gray: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> MatchResult:
    """Perform template matching and return result."""
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, max_loc = cv2.minMaxLoc(result)
    return MatchResult(
        gray=gray,
        result=result,
        confidence=confidence,
        matched=confidence >= threshold,
        max_loc=max_loc,
    )


def save_match_debug(
    debug_dir: str,
    gray: np.ndarray,
    template: np.ndarray,
    result: np.ndarray,
    confidence: float,
    max_loc: tuple[int, int],
    threshold: float,
) -> None:
    """
    Save debug images for analyzing template matching issues.
    Similar to osrs_basic_botting_functions approach.
    """
    os.makedirs(debug_dir, exist_ok=True)

    import time
    timestamp = int(time.time() * 1000)
    prefix = f"{debug_dir}/match_{timestamp}_conf{confidence:.3f}"

    # Save the grayscale crop being searched
    cv2.imwrite(f"{prefix}_gray.png", gray)

    # Save the template
    cv2.imwrite(f"{prefix}_template.png", template)

    # Save the result heatmap (normalized to 0-255 for visualization)
    result_normalized = (result * 255).astype(np.uint8)
    cv2.imwrite(f"{prefix}_result.png", result_normalized)

    # Draw rectangle on gray image where best match was found
    gray_with_match = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    h, w = template.shape[:2]
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    color = (0, 255, 0) if confidence >= threshold else (0, 0, 255)
    cv2.rectangle(gray_with_match, top_left, bottom_right, color, 2)
    cv2.imwrite(f"{prefix}_match_location.png", gray_with_match)

    # Log info
    print(f"[DEBUG] Saved match debug to {prefix}_*.png")
    print(f"[DEBUG] Template size: {w}x{h}, Crop size: {gray.shape[1]}x{gray.shape[0]}")
    print(f"[DEBUG] Best match at: {max_loc}, confidence: {confidence:.4f}, threshold: {threshold}")


def validate_template_size(template: np.ndarray, region_width: int, region_height: int) -> None:
    """
    Validate that template is smaller than the capture region.
    Template matching requires the template to be smaller than the search area.
    """
    tmpl_h, tmpl_w = template.shape[:2]

    if tmpl_w >= region_width or tmpl_h >= region_height:
        raise RuntimeError(
            f"CRITICAL: Template ({tmpl_w}x{tmpl_h}) must be smaller than region ({region_width}x{region_height})! "
            f"Template matching cannot work if template >= search area."
        )

    print(f"[INFO] Template size: {tmpl_w}x{tmpl_h}, Region size: {region_width}x{region_height}")


def draw_match_on_frame(
    frame: np.ndarray,
    template: np.ndarray,
    match_result,
    threshold: float,
) -> np.ndarray:
    """Draw the match location on the frame."""
    output = frame.copy()
    h, w = template.shape[:2]
    top_left = match_result.max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    
    # Green if matched, red if not
    color = (0, 255, 0) if match_result.confidence >= threshold else (0, 0, 255)
    cv2.rectangle(output, top_left, bottom_right, color, 2)
    
    # Add confidence text
    text = f"Conf: {match_result.confidence:.3f}"
    cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    return output


def show_live_windows(
    gray_frame: np.ndarray,
    template: np.ndarray,
    match_result,
    threshold: float,
) -> bool:
    """
    Show live windows with the captured frame and template.
    Returns False if 'q' was pressed to quit.
    """
    # Draw match location on frame
    frame_with_match = draw_match_on_frame(
        cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR),
        template,
        match_result,
        threshold,
    )
    
    # Scale down if frame is too large for display
    max_display_height = 600
    scale = 1.0
    if frame_with_match.shape[0] > max_display_height:
        scale = max_display_height / frame_with_match.shape[0]
        frame_with_match = cv2.resize(frame_with_match, None, fx=scale, fy=scale)
    
    # Show the captured region with match rectangle
    cv2.imshow("Captured Region (Gray)", frame_with_match)
    
    # Show the template (scaled up for visibility if small)
    template_display = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
    if template.shape[0] < 200:
        scale_factor = 200 / template.shape[0]
        template_display = cv2.resize(template_display, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_NEAREST)
    cv2.imshow("Template (Gray)", template_display)
    
    # Check for 'q' key to quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        cv2.destroyAllWindows()
        return False
    
    return True
