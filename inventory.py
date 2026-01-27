"""
Inventory scanning and dropping logic.

Scans the inventory region for resources using template matching,
finds all matching positions, and returns their center coordinates.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from mss import mss

import config
from capture import load_template, grab_region, preprocess_crop


@dataclass(frozen=True)
class InventoryItem:
    """Represents a found item in the inventory."""
    x: int  # Absolute screen X coordinate (center of item)
    y: int  # Absolute screen Y coordinate (center of item)
    confidence: float


def find_resources_in_inventory(
    sct: mss,
    monitor: dict,
    template: np.ndarray,
    threshold: float = None,
) -> list[InventoryItem]:
    """
    Scan the inventory region and find all resources matching the template.
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Grayscale template image of the resource
        threshold: Match threshold (defaults to config.INVENTORY_RESOURCE_THRESHOLD)
    
    Returns:
        List of InventoryItem with absolute screen coordinates for each found resource
    """
    if threshold is None:
        threshold = config.INVENTORY_RESOURCE_THRESHOLD
    
    # Capture the inventory region
    frame = grab_region(
        sct, monitor,
        config.INVENTORY_X_START, config.INVENTORY_Y_START,
        config.INVENTORY_X_END, config.INVENTORY_Y_END,
    )
    gray = preprocess_crop(frame)
    
    # Template matching
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    
    # Find all matches above threshold
    locations = np.where(result >= threshold)
    
    # Get template dimensions for calculating center points
    template_h, template_w = template.shape[:2]
    
    # Group nearby matches to avoid duplicates
    # Use non-maximum suppression approach
    items = []
    points = list(zip(locations[1], locations[0]))  # (x, y) pairs
    
    if not points:
        return items
    
    # Get confidence values for each point
    confidences = [result[y, x] for x, y in points]
    
    # Apply non-maximum suppression
    boxes = []
    for (x, y), conf in zip(points, confidences):
        boxes.append([x, y, x + template_w, y + template_h, conf])
    
    boxes = np.array(boxes)
    picked_indices = non_max_suppression(boxes, overlap_thresh=0.3)
    
    # Convert to InventoryItem with absolute screen coordinates
    for idx in picked_indices:
        x, y = int(boxes[idx][0]), int(boxes[idx][1])
        conf = boxes[idx][4]
        
        # Calculate center point in absolute screen coordinates
        center_x = config.INVENTORY_X_START + x + (template_w // 2)
        center_y = config.INVENTORY_Y_START + y + (template_h // 2)
        
        items.append(InventoryItem(x=center_x, y=center_y, confidence=conf))
    
    return items


def non_max_suppression(boxes: np.ndarray, overlap_thresh: float = 0.3) -> list[int]:
    """
    Apply non-maximum suppression to avoid detecting the same item multiple times.
    
    Args:
        boxes: Array of [x1, y1, x2, y2, confidence] for each detection
        overlap_thresh: Overlap threshold for suppression
    
    Returns:
        List of indices to keep
    """
    if len(boxes) == 0:
        return []
    
    # Convert to float for division
    boxes = boxes.astype(float)
    
    # Get coordinates
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    scores = boxes[:, 4]
    
    # Calculate area of each box
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    
    # Sort by confidence score (highest first)
    idxs = np.argsort(scores)[::-1]
    
    picked = []
    
    while len(idxs) > 0:
        # Pick the box with highest confidence
        i = idxs[0]
        picked.append(i)
        
        # Calculate overlap with remaining boxes
        xx1 = np.maximum(x1[i], x1[idxs[1:]])
        yy1 = np.maximum(y1[i], y1[idxs[1:]])
        xx2 = np.minimum(x2[i], x2[idxs[1:]])
        yy2 = np.minimum(y2[i], y2[idxs[1:]])
        
        # Calculate intersection area
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        intersection = w * h
        
        # Calculate overlap ratio
        overlap = intersection / area[idxs[1:]]
        
        # Remove boxes with high overlap
        remaining = np.where(overlap <= overlap_thresh)[0]
        idxs = idxs[remaining + 1]  # +1 because we removed index 0
    
    return picked


def get_drop_order(items: list[InventoryItem]) -> list[InventoryItem]:
    """
    Sort items for efficient dropping (top to bottom, left to right).
    
    Args:
        items: List of InventoryItem to sort
    
    Returns:
        Sorted list of items
    """
    # Sort by Y first (top to bottom), then by X (left to right)
    return sorted(items, key=lambda item: (item.y, item.x))
