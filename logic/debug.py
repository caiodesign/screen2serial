import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

# State name is now just a string type


def ensure_debug_dir(debug_dir: str) -> None:
    """Create debug directory if it doesn't exist."""
    Path(debug_dir).mkdir(exist_ok=True)


def should_save_debug(debug: bool, save_mode: str, matched: bool) -> bool:
    """Determine if we should save debug captures."""
    if not debug:
        return False
    return save_mode == "all" or not matched


def make_debug_base_path(debug_dir: str, state: str, confidence: float) -> str:
    """Generate base path for debug files."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{debug_dir}/{ts}_{state}_{confidence:.3f}"


def create_heatmap(result: np.ndarray) -> np.ndarray:
    """Create a colored heatmap from template matching result."""
    heatmap = cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX)
    heatmap = heatmap.astype(np.uint8)
    return cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)


def create_annotated_crop(
    gray: np.ndarray,
    state: StateName,
    confidence: float,
    matched: bool,
) -> np.ndarray:
    """Create an annotated version of the crop with state and confidence."""
    annotated = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    color = (0, 255, 0) if matched else (0, 0, 255)
    cv2.putText(
        annotated,
        f"{state} conf={confidence:.3f}",
        (5, 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        1,
        cv2.LINE_AA,
    )
    return annotated


def save_debug_captures(
    base_path: str,
    gray: np.ndarray,
    template: np.ndarray,
    result: np.ndarray,
    state: StateName,
    confidence: float,
    matched: bool,
) -> None:
    """Save all debug captures to disk."""
    # Crop
    cv2.imwrite(f"{base_path}_crop.png", gray)

    # Template
    cv2.imwrite(f"{base_path}_template.png", template)

    # Heatmap
    heatmap = create_heatmap(result)
    cv2.imwrite(f"{base_path}_heatmap.png", heatmap)

    # Annotated
    annotated = create_annotated_crop(gray, state, confidence, matched)
    cv2.imwrite(f"{base_path}_annotated.png", annotated)
