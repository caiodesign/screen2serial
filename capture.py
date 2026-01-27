import cv2
import numpy as np
from dataclasses import dataclass
from mss import mss


@dataclass(frozen=True)
class MatchResult:
    """Immutable result from template matching."""
    gray: np.ndarray
    result: np.ndarray
    confidence: float
    matched: bool


def load_template(path: str) -> np.ndarray:
    """Load and preprocess template image."""
    template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise RuntimeError(f"Template not found: {path}")
    return cv2.GaussianBlur(template, (5, 5), 0)


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
    """Convert to grayscale and blur."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def match_template(
    gray: np.ndarray,
    template: np.ndarray,
    threshold: float,
) -> MatchResult:
    """Perform template matching and return result."""
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, _ = cv2.minMaxLoc(result)
    return MatchResult(
        gray=gray,
        result=result,
        confidence=confidence,
        matched=confidence >= threshold,
    )


def compute_target_y(center_y: int, crop_size: int, y_margin: int) -> int:
    """Calculate the target Y coordinate for clicking."""
    return center_y + (crop_size // 2) + y_margin
