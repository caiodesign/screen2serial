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


def load_template(path: str) -> np.ndarray:
    """Load template image without blur (matching opencv_tutorials approach)."""
    template = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if template is None:
        raise RuntimeError(f"Template not found: {path}")

    # Convert to grayscale if needed (handles RGBA/RGB/BGR)
    if len(template.shape) == 3:
        if template.shape[2] == 4:
            # RGBA - convert to grayscale
            template = cv2.cvtColor(template, cv2.COLOR_BGRA2GRAY)
        else:
            # BGR - convert to grayscale
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    return template


def create_screen_capturer() -> tuple[mss, dict]:
    """Create mss screen capturer and get primary monitor."""
    sct = mss()
    monitor = sct.monitors[1]
    return sct, monitor


def grab_screen(sct: mss, monitor: dict) -> np.ndarray:
    """Capture the screen and return BGR frame."""
    screenshot = np.array(sct.grab(monitor))
    return screenshot[:, :, :3]


def crop_frame(
    frame: np.ndarray,
    center_x: int,
    center_y: int,
    crop_size: int,
) -> np.ndarray:
    """Crop a square region around the center point."""
    half = crop_size // 2
    return frame[
        center_y - half : center_y + half,
        center_x - half : center_x + half,
    ]


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


def compute_target_y(center_y: int, crop_size: int, y_margin: int) -> int:
    """Calculate the target Y coordinate for clicking."""
    return center_y + (crop_size // 2) + y_margin


def validate_template_size(template: np.ndarray, crop_size: int) -> None:
    """
    Validate that template is smaller than crop size.
    Template matching requires the template to be smaller than the search area.
    """
    tmpl_h, tmpl_w = template.shape[:2]

    if tmpl_w >= crop_size or tmpl_h >= crop_size:
        raise RuntimeError(
            f"CRITICAL: Template ({tmpl_w}x{tmpl_h}) must be smaller than crop size ({crop_size}x{crop_size})! "
            f"Template matching cannot work if template >= search area. "
            f"Either:\n"
            f"  1. Increase CROP_SIZE in config.py (recommended: at least {max(tmpl_w, tmpl_h) + 50})\n"
            f"  2. Use a smaller template image"
        )

    # Warn if template is close to crop size (less room for matching)
    margin = min(crop_size - tmpl_w, crop_size - tmpl_h)
    if margin < 20:
        print(f"[WARNING] Template ({tmpl_w}x{tmpl_h}) is very close to crop size ({crop_size}x{crop_size}). "
              f"Only {margin}px margin for movement. Consider increasing CROP_SIZE for better detection.")
    else:
        print(f"[INFO] Template size: {tmpl_w}x{tmpl_h}, Crop size: {crop_size}x{crop_size}, Margin: {margin}px")
